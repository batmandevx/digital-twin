"""Runtime engine: loads trained artefacts and answers dashboard queries."""
import gzip
import json
import pickle
from datetime import timedelta
from functools import lru_cache

import numpy as np

from ..config import (MODEL_DIR, DATA_DIR, DAY, CGM_STEP, START, HORIZONS, CALIB_DAYS, T_MIN,
                      SPIKE_MGDL, FESTIVALS, NAVRATRI_DAYS)
from ..foods import FOODS
from ..ml import features as F
from ..pipeline import predict, load_models
from ..twin.core import DigitalTwin, CGM_LAG
from ..twin.patient import load_cohort
from ..twin import scenarios as S
from ..twin import insights as INS
from ..physiology import gmi

SLOT_HI = dict(breakfast="नाश्ते", lunch="दोपहर के भोजन", dinner="रात के खाने", snack="शाम के नाश्ते")


def _r(x, n=1):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


class Engine:
    def __init__(self):
        recs = load_cohort()
        self.models = load_models()
        with open(MODEL_DIR / "twins.json") as f:
            cal = json.load(f)
        with open(MODEL_DIR / "metrics.json") as f:
            self.metrics = json.load(f)
        st = np.load(MODEL_DIR / "twin_states.npz")
        self.twins = {r.pid: DigitalTwin(r, cal[r.pid], st[r.pid].astype(np.float64), st[r.pid + "_open"])
                      for r in recs}
        self.order = [r.pid for r in recs]
        si = np.array([tw.params["SI"] for tw in self.twins.values()])
        ga = np.array([tw.params["gamma"] for tw in self.twins.values()])
        gb = np.array([tw.params["Gb"] for tw in self.twins.values()])
        self.pop = dict(SI=np.sort(si), gamma=np.sort(ga), Gb=np.sort(gb))
        with open(DATA_DIR / "manifest.json") as f:
            self.manifest = {p["id"]: p for p in json.load(f)["patients"]}

    # ------------------------------------------------------------ helpers
    @staticmethod
    def clamp_t(t):
        t = int(t) // CGM_STEP * CGM_STEP
        return int(np.clip(t, CALIB_DAYS * DAY, T_MIN - 5))

    @staticmethod
    def iso(minute):
        return (START + timedelta(minutes=int(minute))).isoformat(timespec="minutes")

    def pct(self, key, v):
        a = self.pop[key]
        return float(np.searchsorted(a, v) / len(a) * 100)

    @lru_cache(maxsize=4096)
    def predict_at(self, pid, t):
        tw = self.twins[pid]
        X, ex = F.build(tw, np.array([t]))
        P = predict(self.models, X)
        return self._post(tw, X, ex, P)

    def predict_many(self, t):
        """Batch prediction for the whole cohort (one model call per head)."""
        built = [F.build(self.twins[pid], np.array([t])) for pid in self.order]
        Xall = {k: np.concatenate([b[0][k] for b in built]) for k in built[0][0]}
        P = predict(self.models, Xall)
        out = {}
        for i, pid in enumerate(self.order):
            Pi = {h: P[h][:, i:i + 1] for h in HORIZONS}
            Pi["p_spike"] = P["p_spike"][i:i + 1]
            out[pid] = self._post(self.twins[pid], built[i][0], built[i][1], Pi)
        return out

    def _post(self, tw, X, ex, P):
        cg = tw.rec.wear["cgm_mgdl"].values
        g_now = X["g_now"][0]
        F_h = ex["F_habit"][0]
        # forecast cone: quantiles at 30/60/120 + twin shape in between (anchored at now)
        pts = [dict(m=0, lo=g_now, mid=g_now, hi=g_now)]
        for h in HORIZONS:
            pts.append(dict(m=h, lo=float(P[h][0][0]), mid=float(P[h][1][0]), hi=float(P[h][2][0])))
        mins = np.arange(5, 121, 5)
        hs = [p["m"] for p in pts]
        corr = np.interp(mins, hs, [p["mid"] for p in pts]) - np.interp(
            mins, hs, [g_now] + [F_h[h - 1 - CGM_LAG] for h in HORIZONS])
        twin_curve = np.array([F_h[max(0, m - 1 - CGM_LAG)] for m in mins])
        mid = twin_curve + corr
        lo = mid - (np.interp(mins, hs, [p["mid"] - p["lo"] for p in pts]))
        hi = mid + (np.interp(mins, hs, [p["hi"] - p["mid"] for p in pts]))
        p_spike = float(P["p_spike"][0])
        eligible = g_now < SPIKE_MGDL - 20
        cross = np.where(mid >= SPIKE_MGDL)[0]
        eta = int(mins[cross[0]]) if len(cross) else None
        thr = self.models["thr"]["hybrid"]
        if g_now >= SPIKE_MGDL:
            status = "high"
        elif eligible and p_spike >= thr:
            status = "spike"
        elif lo.min() < 75 or g_now < 80:
            status = "low"
        elif p_spike >= thr * 0.7:
            status = "watch"
        else:
            status = "stable"
        return dict(g_now=_r(g_now), p_spike=round(p_spike, 3), eta=eta, status=status,
                    peak=_r(mid.max()), peak_hi=_r(hi.max()), peak_lo=_r(lo.max()),
                    t_peak=int(mins[mid.argmax()]),
                    forecast=[dict(m=int(m), lo=_r(a), mid=_r(b), hi=_r(c), twin=_r(d))
                              for m, a, b, c, d in zip(mins, lo, mid, hi, twin_curve)],
                    trend=_r(X["d15"][0]), thr=thr, features={k: _r(X[k][0], 3) for k in
                                                              ("carbs_3h", "steps_1h", "stress_now", "sleep_debt",
                                                               "exp_carbs_2h", "min_to_exp_meal", "hrv_1h", "hr_1h")})

    # -------------------------------------------------------------- cohort
    @lru_cache(maxsize=256)
    def cohort(self, t):
        t = self.clamp_t(t)
        out = []
        many = self.predict_many(t)
        for pid in self.order:
            tw = self.twins[pid]
            pr = many[pid]
            cg = tw.rec.wear["cgm_mgdl"].values
            e = t // CGM_STEP
            spark = cg[max(0, e - 71):e + 1:3]
            pf = tw.rec.profile
            sev = dict(spike=3, high=2, low=2.5, watch=1, stable=0)[pr["status"]] + pr["p_spike"]
            out.append(dict(id=pid, name=pf["name"], age=pf["age"], sex=pf["sex"], city=pf["city"],
                            hba1c=pf["labs"]["hba1c"], split=tw.rec.split, persona=self.manifest[pid]["persona"],
                            g_now=pr["g_now"], status=pr["status"], p_spike=pr["p_spike"], eta=pr["eta"],
                            peak=pr["peak"], severity=sev,
                            spark=[None if np.isnan(v) else int(v) for v in spark]))
        out.sort(key=lambda r: -r["severity"])
        return dict(t=t, time=self.iso(t), patients=out)

    # ------------------------------------------------------------- patient
    def patient(self, pid, t):
        t = self.clamp_t(t)
        tw = self.twins[pid]
        r = tw.rec
        pf = r.profile
        pr = self.predict_at(pid, t)
        e = t // CGM_STEP
        w = r.wear
        lo_e = max(0, e - 24 * 12 + 1)
        seg = w.iloc[lo_e:e + 1]
        nan = lambda a: [None if (v is None or np.isnan(v)) else float(v) for v in a]
        timeline = dict(minute=seg["minute"].tolist(), cgm=nan(seg["cgm_mgdl"].values),
                        hr=nan(seg["heart_rate_bpm"].values), hrv=nan(seg["hrv_rmssd_ms"].values),
                        steps=seg["steps"].astype(int).tolist(), sleep=seg["sleep_stage"].astype(int).tolist(),
                        twin=np.round(tw.states[lo_e:e + 1, 0], 1).tolist(),
                        stress=np.round(r.inputs["stress"][seg["minute"].values], 2).tolist())
        ml = r.meals[(r.meals["minute"] > t - DAY) & (r.meals["minute"] <= t)]
        meals = [dict(minute=int(m.minute), food=m.food_id, name=m.food, carbs=int(m.carbs_g_est),
                      icon=FOODS.get(m.food_id, {}).get("icon", "🍽"), kind=m.meal_type) for m in ml.itertuples()]
        expected = [dict(minute=int(t + off + 1), carbs=round(c), food=None)
                    for _, _, off, c, _ in tw.expected_meals([t], 120)]
        fasting = tw.fasting_today(t)
        for ex in expected:
            tod = ex["minute"] % DAY
            slot = min(r.habits["slots"].items(), key=lambda kv: min(abs(kv[1]["tod"] - tod), DAY - abs(kv[1]["tod"] - tod)))
            food = tw.slot_meal(slot[0], slot[1], fasting)[0]
            ex["food"], ex["name"], ex["slot"] = food, FOODS[food]["name"], slot[0]
            ex["icon"], ex["fasting"] = FOODS[food]["icon"], fasting
        md = r.meds[(r.meds["minute"] > t - DAY) & (r.meds["minute"] <= t)]
        meds = [dict(minute=int(m.minute), drug=m.drug, taken=bool(m.taken)) for m in md.itertuples()]

        # 14-day / to-date stats
        cg_all = w["cgm_mgdl"].values[:e + 1]
        cg_all = cg_all[~np.isnan(cg_all)]
        daily = []
        for d in range(0, t // DAY + 1):
            c = w["cgm_mgdl"].values[d * 288:min((d + 1) * 288, e + 1)]
            c = c[~np.isnan(c)]
            if len(c):
                daily.append(dict(day=d, date=(START + timedelta(days=d)).strftime("%d %b"),
                                  tir=_r(np.mean((c >= 70) & (c <= 180)) * 100), mean=_r(c.mean()),
                                  tar=_r(np.mean(c > 180) * 100), tbr=_r(np.mean(c < 70) * 100),
                                  steps=int(w["steps"].values[d * 288:min((d + 1) * 288, e + 1)].sum()),
                                  festival=FESTIVALS.get(d), navratri=d in NAVRATRI_DAYS))
        nights = [n for n in r.nights if n["wake"] <= t][-7:]
        st = tw.states[e]
        attr = S.attribute(tw, t) if pr["status"] in ("spike", "watch", "high") else None
        if attr:
            # apportion the hybrid forecast's excess (not the raw physics peak) across drivers
            raw = attr["peak_actual"] - attr["peak_ideal"]
            target = max(0.0, pr["peak"] - attr["peak_ideal"])
            f = target / raw if raw > 1 else 0.0
            for d in attr["drivers"]:
                d["mgdl"] = round(d["mgdl"] * f, 1)
            attr["peak_physics"] = attr["peak_actual"]
            attr["peak_actual"] = pr["peak"]
        rec = self.recommend(tw, t, pr, attr)
        lab_hist = {k: v for k, v in pf["lab_history"].items()}
        sm = tw.summary()
        twin = dict(
            params=dict(SI=sm["insulin_sensitivity"] * 1e4, gamma=sm["beta_cell"], Gb=sm["basal_glucose"],
                        SG=sm["glucose_effectiveness"] * 1e3),
            prior=dict(SI=sm["prior"]["SI"] * 1e4, gamma=sm["prior"]["gamma"], Gb=sm["prior"]["Gb"]),
            pct=dict(SI=self.pct("SI", sm["insulin_sensitivity"]), gamma=self.pct("gamma", sm["beta_cell"]),
                     Gb=self.pct("Gb", sm["basal_glucose"])),
            calib_rmse=_r(sm["calib_rmse"]), uncertainty=sm["log_sd"],
            state=dict(G=_r(st[0]), insulin=_r(st[2] - tw.params["Ib"]), remote_insulin=_r(st[1] * 1e3, 3),
                       gut=_r(st[3:7].sum()), gut_fast=_r(st[3] + st[4]), exercise=_r(st[7], 3),
                       stress=_r(r.inputs["stress"][t], 2), sleep_debt=_r(r.inputs["sleep_debt"][t], 2),
                       hr=_r(w["heart_rate_bpm"].values[e], 0), hrv=_r(w["hrv_rmssd_ms"].values[e]),
                       hepatic=_r(tw.params["Gb"] * r.inputs["gb_mult"][t]),
                       asleep=bool(w["sleep_stage"].values[e] > 0)))
        past = []
        for back in (120, 60):
            tb = t - back
            if tb >= CALIB_DAYS * DAY:
                fp = self.predict_at(pid, tb)
                past.append(dict(made=tb, back=back, pts=[[tb + f["m"], f["mid"]] for f in fp["forecast"] if f["m"] <= back]))
        return dict(
            past_forecasts=past, adapt_si=_r(tw.si_mult[t], 3), dawn=_r(tw.params.get("dawn", 0), 3),
            fasting=fasting, festival=FESTIVALS.get(t // DAY), navratri=(t // DAY) in NAVRATRI_DAYS,
            id=pid, t=t, time=self.iso(t), day=t // DAY, tod=t % DAY, story=r.story, split=r.split,
            profile=dict(name=pf["name"], age=pf["age"], sex=pf["sex"], city=pf["city"], abha=pf.get("abha"),
                         diet=pf.get("diet"), region=pf.get("region"), conditions=pf["conditions"],
                         medications=pf["medications"], labs=pf["labs"], lab_history=lab_hist,
                         genetics=pf["genetics"], prs=pf["prs"], family_history=pf["family_history"],
                         years_dx=round(pf["years_dx"], 1)),
            prediction=pr, timeline=timeline, meals=meals, expected_meals=expected, meds=meds,
            stats=dict(tir=_r(np.mean((cg_all >= 70) & (cg_all <= 180)) * 100), mean=_r(cg_all.mean()),
                       gmi=_r(gmi(cg_all.mean()), 2), cv=_r(cg_all.std() / cg_all.mean() * 100),
                       tar=_r(np.mean(cg_all > 180) * 100), tbr=_r(np.mean(cg_all < 70) * 100),
                       tar250=_r(np.mean(cg_all > 250) * 100), daily=daily),
            nights=nights, twin=twin, attribution=attr, recommendation=rec,
            habits=dict(sleep_hours=_r(r.habits["sleep_hours"], 2),
                        slots={k: dict(tod=v["tod"], carbs=v["carbs"], food=FOODS[v["food"]]["name"], prob=_r(v["prob"], 2))
                               for k, v in r.habits["slots"].items()}),
            fidelity=self.metrics.get("twin_fidelity", {}).get(pid))

    def recommend(self, tw, t, pr, attr):
        """Choose the single most effective micro-intervention for the next meal."""
        cfgs = [dict(walk=15), dict(swap=1.0), dict(dinner_shift=1), dict(sleep_h=7.5)]
        G, meals = S.simulate_plans(tw, t, [dict()] + cfgs, H=360)
        peaks = G.max(1)
        drops = peaks[0] - peaks[1:]
        k = int(np.argmax(drops))
        nxt = S.day_plan(tw, t, 360)
        slot = next((m["slot"] for m in nxt if m["slot"] != "snack"), "lunch")
        food = next((m["food"] for m in nxt if m["slot"] == slot), None)
        just_ate = len(tw.rec.meals[(tw.rec.meals["minute"] > t - 60) & (tw.rec.meals["minute"] <= t)]) > 0
        if just_ate:
            k = 0
            G2, _ = S.simulate_plans(tw, t, [dict()], H=360)
            inp = tw.future_inputs([t], 120, habit=False)
            inp2 = {kk: v.copy() for kk, v in inp.items()}
            inp2["steps"][0, 5:20] = 100
            from .. import physiology as phys
            p = tw.params_at([t, t])
            b = {kk: np.concatenate([inp[kk], inp2[kk]]) for kk in inp}
            GG, _, _ = phys.simulate(p, tw.state_at([t, t]), b, tod0=np.full(2, (t + 1) % DAY))
            drop = float(GG[0].max() - GG[1].max())
            en = f"Take a brisk 15-minute walk now. The twin projects this lowers the coming peak by about {drop:.0f} mg/dL."
            hi = f"अभी 15 मिनट तेज़ चलें। आपका शुगर लगभग {drop:.0f} mg/dL कम बढ़ेगा।"
            return dict(kind="walk_now", drop=round(drop, 1), en=en, hi=hi, options=[])
        drop = float(drops[k])
        swap_to = FOODS[S.LOW_GI_SWAPS.get(food, "millet_roti_sabzi")]["name"] if food else "millet roti"
        swap_hi = FOODS[S.LOW_GI_SWAPS.get(food, "millet_roti_sabzi")]["hi"] if food else "ज्वार रोटी"
        slot_hi = SLOT_HI.get(slot, "भोजन")
        texts = [
            (f"After {slot}, take a 15-minute walk. Your twin predicts a peak about {drops[0]:.0f} mg/dL lower.",
             f"{slot_hi} के बाद 15 मिनट टहलें। आपका शुगर लगभग {drops[0]:.0f} mg/dL कम बढ़ेगा।"),
            (f"Swap today's {FOODS[food]['name'] if food else 'meal'} for {swap_to}. Predicted peak is {drops[1]:.0f} mg/dL lower.",
             f"आज {slot_hi} में {swap_hi} लें। शुगर लगभग {drops[1]:.0f} mg/dL कम बढ़ेगा।"),
            (f"Have dinner one hour earlier. Predicted peak is {drops[2]:.0f} mg/dL lower.",
             f"रात का खाना एक घंटा पहले खाएँ। शुगर लगभग {drops[2]:.0f} mg/dL कम बढ़ेगा।"),
            (f"Aim for 7.5 hours of sleep tonight. Tomorrow's peaks are about {drops[3]:.0f} mg/dL lower.",
             f"आज रात 7.5 घंटे की नींद लें। कल शुगर लगभग {drops[3]:.0f} mg/dL कम बढ़ेगा।"),
        ]
        kinds = ["walk", "swap", "dinner_earlier", "sleep"]
        return dict(kind=kinds[k], drop=round(drop, 1), en=texts[k][0], hi=texts[k][1], slot=slot,
                    options=[dict(kind=kinds[i], drop=round(float(drops[i]), 1), en=texts[i][0]) for i in range(4)])

    # ------------------------------------------------------------ insights
    def track_record(self, pid, t, hours=24):
        """How accurate has this twin been for this patient? Uses only past data."""
        tw = self.twins[pid]
        cg = tw.rec.wear["cgm_mgdl"].values.astype(float)
        a = np.arange(max(CALIB_DAYS * DAY, t - hours * 60), t - 30 + 1, 15)
        a = a[~np.isnan(cg[a // CGM_STEP])]
        if len(a) < 4:
            return None
        X, _ = F.build(tw, a)
        P = predict(self.models, X)
        out = {}
        for h in HORIZONS:
            m = a + h <= t
            y = cg[(a[m] + h) // CGM_STEP]
            ok = ~np.isnan(y)
            if ok.sum() < 3:
                continue
            pr = P[h][1][m][ok]
            inside = (y[ok] >= P[h][0][m][ok]) & (y[ok] <= P[h][2][m][ok])
            out[str(h)] = dict(mae=_r(np.mean(np.abs(pr - y[ok]))), n=int(ok.sum()), coverage=_r(inside.mean() * 100, 0),
                               pts=[[int(aa + h), _r(pp), _r(yy)] for aa, pp, yy in zip(a[m][ok], pr, y[ok])])
        return out

    def insights(self, pid, t):
        t = self.clamp_t(t)
        tw = self.twins[pid]
        return dict(pgi=INS.personal_glycaemic_index(tw, t), brief=INS.clinical_brief(tw, t),
                    track=self.track_record(pid, t), adapt=dict(
                        si=[_r(v, 3) for v in np.asarray(tw.calib["adapt"])[:, 0]],
                        gb=[_r(v, 3) for v in np.asarray(tw.calib["adapt"])[:, 1]]),
                    dawn=_r(tw.params.get("dawn", 0), 3))

    def fhir_out(self, pid, t):
        """Export the twin's current prediction as FHIR R4 resources."""
        t = self.clamp_t(t)
        pr = self.predict_at(pid, t)
        P = self.patient(pid, t)
        when = self.iso(t)
        ref = {"reference": f"Patient/{pid}"}
        dev = {"display": "Sanjeevani Twin hybrid digital twin v1.0 (research prototype)"}
        ents = [{"resourceType": "RiskAssessment", "id": f"risk-{pid}-{t}", "status": "final", "subject": ref,
                 "occurrenceDateTime": when, "performer": dev,
                 "method": {"text": "Personalised physiology twin + conformal gradient boosting"},
                 "prediction": [{"outcome": {"coding": [{"system": "http://snomed.info/sct", "code": "80394007",
                                                         "display": "Hyperglycemia"}], "text": "CGM glucose above 180 mg/dL within 2 hours"},
                                 "probabilityDecimal": pr["p_spike"],
                                 "whenRange": {"low": {"value": 0, "unit": "min"}, "high": {"value": 120, "unit": "min"}}}],
                 "basis": [{"display": d["label"] + f" (+{d['mgdl']} mg/dL)"} for d in (P["attribution"] or {}).get("drivers", []) if d["mgdl"] > 0],
                 "mitigation": P["recommendation"]["en"]}]
        for f in pr["forecast"]:
            if f["m"] in HORIZONS:
                ents.append({"resourceType": "Observation", "status": "preliminary", "subject": ref,
                             "category": [{"text": "twin-forecast"}],
                             "code": {"coding": [{"system": "http://loinc.org", "code": "2339-0",
                                                  "display": "Glucose [Mass/volume] in Blood"}], "text": f"Forecast glucose +{f['m']} min"},
                             "effectiveDateTime": self.iso(t + f["m"]), "issued": when, "device": dev,
                             "valueQuantity": {"value": f["mid"], "unit": "mg/dL", "system": "http://unitsofmeasure.org", "code": "mg/dL"},
                             "referenceRange": [{"low": {"value": f["lo"], "unit": "mg/dL"}, "high": {"value": f["hi"], "unit": "mg/dL"},
                                                 "text": "80% conformal prediction interval"}]})
        ents.append({"resourceType": "Communication", "status": "preparation", "subject": ref, "language": "hi",
                     "payload": [{"contentString": P["recommendation"]["en"]}, {"contentString": P["recommendation"]["hi"]}]})
        return {"resourceType": "Bundle", "type": "collection", "timestamp": when,
                "entry": [{"resource": e} for e in ents]}

    def whatif(self, pid, t, cfg):
        return S.what_if(self.twins[pid], self.clamp_t(t), cfg)

    def optimise(self, pid, t):
        return S.optimise(self.twins[pid], self.clamp_t(t))
