"""Zero-dependency HTTP server for the Sanjeevani clinician dashboard.

    python -m sanjeevani.api.server  [--port 8000]
"""
import os

os.environ.setdefault("OMP_NUM_THREADS", "2")   # single-row predictions: avoid thread spin-up

import argparse
import json
import mimetypes

mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
import time
import traceback
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import numpy as np

from ..config import DASHBOARD_DIR
from .engine import Engine

ENGINE = None


def _default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.bool_):
        return bool(o)
    raise TypeError(type(o))


class Handler(BaseHTTPRequestHandler):
    server_version = "Sanjeevani/1.0"

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, default=_default).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path.startswith("/api/"):
                return self._api(u.path[5:], q, None)
            path = (DASHBOARD_DIR / u.path.lstrip("/")).resolve()
            if u.path in ("/", "") or not path.exists():
                path = DASHBOARD_DIR / "index.html"
            if DASHBOARD_DIR.resolve() not in path.resolve().parents and path != DASHBOARD_DIR / "index.html":
                return self._send(403, {"error": "forbidden"})
            ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            self._send(200, path.read_bytes(), ctype)
        except Exception as e:  # pragma: no cover
            traceback.print_exc()
            self._send(500, {"error": str(e)})

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        try:
            return self._api(u.path[5:], {}, body)
        except Exception as e:  # pragma: no cover
            traceback.print_exc()
            self._send(500, {"error": str(e)})

    def _api(self, route, q, body):
        E = ENGINE
        t = int((body or q).get("t", 0) or 0)
        parts = route.strip("/").split("/")
        if parts[0] == "cohort":
            return self._send(200, E.cohort(E.clamp_t(t)))
        if parts[0] == "patient" and len(parts) == 2:
            if parts[1] not in E.twins:
                return self._send(404, {"error": "unknown patient"})
            return self._send(200, E.patient(parts[1], t))
        if parts[0] == "whatif":
            return self._send(200, E.whatif(body["pid"], t, body.get("cfg", {})))
        if parts[0] == "optimise":
            return self._send(200, E.optimise(q.get("pid") or body["pid"], t))
        if parts[0] == "fhir" and len(parts) == 2 and parts[1] in E.twins:
            from ..config import PATIENT_DIR
            return self._send(200, (PATIENT_DIR / parts[1] / "ehr_fhir.json").read_bytes())
        if parts[0] == "insights" and len(parts) == 2 and parts[1] in E.twins:
            return self._send(200, E.insights(parts[1], t))
        if parts[0] == "fhir-out" and len(parts) == 2 and parts[1] in E.twins:
            return self._send(200, E.fhir_out(parts[1], t))
        if parts[0] == "metrics":
            return self._send(200, E.metrics)
        if parts[0] == "meta":
            from ..config import START, T_MIN, CALIB_DAYS, DAY, FESTIVALS, NAVRATRI_DAYS
            return self._send(200, dict(start=START.isoformat(), t_min=CALIB_DAYS * DAY, t_max=T_MIN - 5,
                                        festivals=FESTIVALS, navratri=sorted(NAVRATRI_DAYS),
                                        default=dict(pid="SNJ-001", t=DEFAULT_T)))
        return self._send(404, {"error": "unknown route"})


DEFAULT_T = 11 * 1440 + 12 * 60 + 15        # 16 Oct 2026 12:15, Navratri - Rajesh before lunch


def main():
    global ENGINE
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    t0 = time.time()
    print("Loading digital twins ...")
    ENGINE = Engine()
    print(f"  {len(ENGINE.twins)} twins ready in {time.time() - t0:.1f}s")
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"Sanjeevani dashboard -> http://{a.host}:{a.port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
