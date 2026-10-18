"""End-to-end training + evaluation.

    python -m sanjeevani.pipeline

1. Load the cohort (FHIR EHR + wearable/CGM streams + logs).
2. Calibrate one physiological twin per patient on the 3-day onboarding window.
3. Assimilate the full CGM stream into each twin (state observer).
4. Build causal features at 15-minute anchors and learn the twin's residual
   (quantile gradient boosting) plus a 2-hour spike classifier.
5. Evaluate on held-out patients that were never seen in training against
   persistence, linear-trend, twin-only and ML-only baselines.
"""
import gzip
import json
import pickle
import time

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from .config import MODEL_DIR, DAY, N_DAYS, CALIB_DAYS, ANCHOR_STEP, HORIZONS, QUANTILES, CGM_STEP, SEED
from .twin.patient import load_cohort
from .twin.core import calibrate, assimilate, adapt_daily, DigitalTwin, CGM_LAG
from .ml import features as F
from .ml import metrics as M


def build_twins(recs, verbose=True):
    rng = np.random.default_rng(SEED)
    cals = []
    t0 = time.time()
    for r in recs:
        cals.append(calibrate(r, rng))
    if verbose:
        print(f"  calibrated {len(recs)} twins in {time.time() - t0:.1f}s "
              f"(median onboarding RMSE {np.median([c['calib_rmse'] for c in cals]):.1f} mg/dL)")
    twins = [DigitalTwin(r, c, None) for r, c in zip(recs, cals)]      # sets learned dawn input
    states, _ = assimilate(recs, [c["params"] for c in cals])
    t1 = time.time()
    daily = adapt_daily(twins, states, N_DAYS)
    for tw, dd in zip(twins, daily):
        tw.set_adapt(dd)
    states, open_loop = assimilate(recs, [c["params"] for c in cals],
                                   [tw.si_mult for tw in twins], [tw.gb_adapt for tw in twins])
    if verbose:
        print(f"  adaptive daily re-calibration in {time.time() - t1:.1f}s "
              f"(SI drift range {daily[:, :, 0].min():.2f}-{daily[:, :, 0].max():.2f})")
    for i, tw in enumerate(twins):
        tw.states, tw.open_loop = states[i], open_loop[i]
    return twins


def anchors_for(twin):
    a = np.arange(CALIB_DAYS * DAY + 60, N_DAYS * DAY - 125, ANCHOR_STEP)
    cg = twin.rec.wear["cgm_mgdl"].values
    return a[~np.isnan(cg[a // CGM_STEP])]


def dataset(twins):
    rows = []
    for tw in twins:
        a = anchors_for(tw)
        X, ex = F.build(tw, a)
        Y, lab = F.targets(tw, a)
        rows.append(dict(pid=tw.rec.pid, split=tw.rec.split, anchors=a, X=X, Y=Y, lab=lab))
    return rows


def stack(rows, key, names=None):
    if key == "X":
        return np.vstack([F.matrix(r["X"], names) for r in rows])
    raise KeyError


def gbm(**kw):
    base = dict(max_iter=350, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=40,
                l2_regularization=1.0, random_state=SEED)
    base.update(kw)
    return base


def train(rows, n_cal=6, seed=SEED):
    """Fit on training patients; conformal offsets and alert thresholds are
    estimated on a disjoint set of calibration patients (patient-level split)."""
    tr_all = [r for r in rows if r["split"] == "train"]
    rng = np.random.default_rng(seed)
    cal_ids = set(rng.choice([r["pid"] for r in tr_all], n_cal, replace=False)) if n_cal else set()
    tr = [r for r in tr_all if r["pid"] not in cal_ids]
    cal = [r for r in tr_all if r["pid"] in cal_ids]
    Xh = stack(tr, "X", F.HYBRID_FEATURES)
    Xm = stack(tr, "X", F.ML_ONLY_FEATURES)
    cat = lambda f: np.concatenate([f(r) for r in tr])
    g_now = cat(lambda r: r["X"]["g_now"])
    models = dict(hybrid={}, ml_only={})
    for h in HORIZONS:
        y = cat(lambda r: r["Y"][h])
        tw = cat(lambda r: r["X"][f"tw_{h}"])
        m = ~np.isnan(y)
        for q in QUANTILES:
            models["hybrid"][(h, q)] = HistGradientBoostingRegressor(
                **gbm(loss="quantile", quantile=q)).fit(Xh[m], (y - tw)[m])
        models["ml_only"][(h, 0.5)] = HistGradientBoostingRegressor(**gbm(loss="absolute_error")).fit(
            Xm[m], (y - g_now)[m])
    el = cat(lambda r: r["lab"]["eligible"])
    ys = cat(lambda r: r["lab"]["spike"])
    models["spike_hybrid"] = HistGradientBoostingClassifier(**gbm(max_iter=300)).fit(Xh[el], ys[el])
    models["spike_ml_only"] = HistGradientBoostingClassifier(**gbm(max_iter=300)).fit(Xm[el], ys[el])
    tw_peak = cat(lambda r: r["X"]["tw_peak"])[el][:, None]
    models["spike_twin_only"] = LogisticRegression().fit((tw_peak - 180) / 30, ys[el])
    models["conformal"] = {h: 0.0 for h in HORIZONS}
    src = cal if cal else tr
    Xc = {k: np.concatenate([r["X"][k] for r in src]) for k in F.HYBRID_FEATURES}
    elc = np.concatenate([r["lab"]["eligible"] for r in src])
    ysc = np.concatenate([r["lab"]["spike"] for r in src])[elc]
    if cal:
        # conformalized quantile regression (Romano et al. 2019), target 80 %
        raw = predict(models, Xc)
        for h in HORIZONS:
            y = np.concatenate([r["Y"][h] for r in cal])
            m = ~np.isnan(y)
            E = np.maximum(raw[h][0] - y, y - raw[h][2])[m]
            models["conformal"][h] = float(np.quantile(E, min(1.0, 0.8 * (1 + 1 / len(E)))))
    # isotonic re-calibration of spike probabilities on calibration patients
    raw_p = models["spike_hybrid"].predict_proba(F.matrix(Xc, F.HYBRID_FEATURES)[elc])[:, 1]
    models["iso"] = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(raw_p, ysc)
    Xcm = F.matrix(Xc, F.ML_ONLY_FEATURES)[elc]
    pk = ((Xc["tw_peak"][elc] - 180) / 30)[:, None]
    models["thr"] = dict(
        hybrid=M.threshold_for_precision(ysc, predict(models, Xc)["p_spike"][elc]),
        ml_only=M.threshold_for_precision(ysc, models["spike_ml_only"].predict_proba(Xcm)[:, 1]),
        twin_only=M.threshold_for_precision(ysc, models["spike_twin_only"].predict_proba(pk)[:, 1]))
    models["cal_patients"] = sorted(cal_ids)
    return models


def predict(models, X, A=None):
    """Hybrid forecast for a feature dict X -> quantiles per horizon and spike probability."""
    Xh = F.matrix(X, F.HYBRID_FEATURES)
    out = {}
    for h in HORIZONS:
        base = np.asarray(X[f"tw_{h}"])
        qs = np.sort(np.stack([base + models["hybrid"][(h, q)].predict(Xh) for q in QUANTILES]), axis=0)
        c = models.get("conformal", {}).get(h, 0.0)
        qs[0] -= c
        qs[2] += c
        out[h] = qs                                      # [3, A] sorted -> monotone quantiles
    p = models["spike_hybrid"].predict_proba(Xh)[:, 1]
    if "iso" in models:
        # blend keeps ranking resolution where isotonic steps are flat
        p = 0.85 * models["iso"].predict(p) + 0.15 * p
    out["p_spike"] = p
    return out


def evaluate(models, rows):
    te = [r for r in rows if r["split"] == "test"]
    res = dict(regression={}, spike={}, events={}, coverage={}, per_patient={})
    preds = {name: {h: [] for h in HORIZONS} for name in ("persistence", "linear_trend", "twin_only", "ml_only", "hybrid")}
    ys = {h: [] for h in HORIZONS}
    cover = {h: [] for h in HORIZONS}
    spike_y, spike_s = [], {k: [] for k in ("hybrid", "ml_only", "twin_only", "trend")}
    ev_tot = {k: dict(events=0, detected=0, leads=[], false_alerts=0) for k in ("hybrid", "ml_only", "twin_only")}
    clarke_pts = []
    days = 0.0
    for r in te:
        X = r["X"]
        Xm = F.matrix(X, F.ML_ONLY_FEATURES)
        hy = predict(models, X)
        g = X["g_now"]
        slope = np.where(np.isnan(X["d30"]), 0, X["d30"] / 30)
        for h in HORIZONS:
            y = r["Y"][h]
            ys[h].append(y)
            preds["persistence"][h].append(g)
            preds["linear_trend"][h].append(np.clip(g + slope * h, 40, 400))
            preds["twin_only"][h].append(X[f"tw_{h}"])
            preds["ml_only"][h].append(g + models["ml_only"][(h, 0.5)].predict(Xm))
            preds["hybrid"][h].append(hy[h][1])
            cover[h].append((y >= hy[h][0]) & (y <= hy[h][2]))
        el = r["lab"]["eligible"]
        spike_y.append(r["lab"]["spike"][el])
        p_h = hy["p_spike"]
        p_m = models["spike_ml_only"].predict_proba(Xm)[:, 1]
        p_t = models["spike_twin_only"].predict_proba(((X["tw_peak"] - 180) / 30)[:, None])[:, 1]
        spike_s["hybrid"].append(p_h[el])
        spike_s["ml_only"].append(p_m[el])
        spike_s["twin_only"].append(p_t[el])
        spike_s["trend"].append(np.clip((g + slope * 120 - 140) / 80, 0, 1)[el])
        days += len(r["anchors"]) * ANCHOR_STEP / DAY
        for k, p in (("hybrid", p_h), ("ml_only", p_m), ("twin_only", p_t)):
            e = M.event_lead_times(r["cgm5"], r["anchors"], np.where(np.isnan(p), 0, p), models["thr"][k])
            for kk in ("events", "detected", "false_alerts"):
                ev_tot[k][kk] += e[kk]
            ev_tot[k]["leads"] += e["leads"]
        res["per_patient"][r["pid"]] = dict(
            rmse_60=M.regression(r["Y"][60], hy[60][1])["rmse"],
            rmse_120=M.regression(r["Y"][120], hy[120][1])["rmse"])
        m = ~np.isnan(r["Y"][120])
        clarke_pts += list(zip(r["Y"][120][m][::6].round().tolist(), hy[120][1][m][::6].round().tolist()))
    for name, P in preds.items():
        res["regression"][name] = {h: M.regression(np.concatenate(ys[h]), np.concatenate(P[h])) for h in HORIZONS}
    for h in HORIZONS:
        c = np.concatenate(cover[h])
        y = np.concatenate(ys[h])
        res["coverage"][h] = float(np.mean(c[~np.isnan(y)]) * 100)
    sy = np.concatenate(spike_y)
    for k, s in spike_s.items():
        s = np.concatenate(s)
        thr = models["thr"].get(k, 0.5)
        res["spike"][k] = M.classification(sy, s, thr)
    res["reliability"] = M.reliability(sy, np.concatenate(spike_s["hybrid"]))
    res["ece"] = float(sum(abs(b["p"] - b["obs"]) * b["n"] for b in res["reliability"]) / max(1, sum(b["n"] for b in res["reliability"])))
    res["brier"] = float(np.mean((np.concatenate(spike_s["hybrid"]) - sy) ** 2))
    for k, e in ev_tot.items():
        L = np.array(e["leads"])
        res["events"][k] = dict(events=e["events"], detected=e["detected"],
                                detection_rate=e["detected"] / max(1, e["events"]) * 100,
                                detected_30min=float(np.sum(L >= 30) / max(1, e["events"]) * 100),
                                median_lead=float(np.median(L)) if len(L) else 0.0,
                                false_alerts_per_day=e["false_alerts"] / max(1e-9, days))
    res["clarke_points"] = clarke_pts[:1600]
    res["test_days"] = days
    res["n_test_patients"] = len(te)
    return res


def importance(models, rows, n=4000):
    """Grouped permutation importance of the spike classifier on test data."""
    te = [r for r in rows if r["split"] == "test"]
    X = np.vstack([F.matrix(r["X"], F.HYBRID_FEATURES)[r["lab"]["eligible"]] for r in te])
    y = np.concatenate([r["lab"]["spike"][r["lab"]["eligible"]] for r in te])
    rng = np.random.default_rng(1)
    idx = rng.choice(len(y), min(n, len(y)), replace=False)
    X, y = X[idx], y[idx]
    base = M.auc_roc(y, models["spike_hybrid"].predict_proba(X)[:, 1])
    groups = {
        "Twin physiology forecast": [f for f in F.TWIN],
        "CGM recent trend": ["g_now", "d15", "d30", "d60", "mean_3h", "std_3h", "max_3h"],
        "Meals (logged + habitual)": ["carbs_3h", "min_since_meal", "exp_carbs_2h", "min_to_exp_meal"],
        "Activity (steps)": ["steps_1h", "steps_3h"],
        "Stress (HRV / HR)": ["stress_now", "stress_3h", "hr_1h", "hrv_1h"],
        "Sleep": ["sleep_last", "deep_frac", "sleep_debt"],
        "Circadian / calendar": ["tod_sin", "tod_cos", "weekend"],
        "EHR, genetics & meds": F.STATIC + ["gb_mult"],
    }
    out = {}
    for g, cols in groups.items():
        ci = [F.HYBRID_FEATURES.index(c) for c in cols]
        drops = []
        for rep in range(3):
            Xp = X.copy()
            perm = rng.permutation(len(y))
            Xp[:, ci] = X[perm][:, ci]
            drops.append(base - M.auc_roc(y, models["spike_hybrid"].predict_proba(Xp)[:, 1]))
        out[g] = float(np.mean(drops))
    return dict(base_auroc=base, auroc_drop=out)


def learning_curve(rows, sizes=(2, 4, 8, 16, 24), reps=3):
    """Data efficiency: how many training patients does each approach need?"""
    tr_all = [r for r in rows if r["split"] == "train"]
    te = [r for r in rows if r["split"] == "test"]
    Xte_h = np.vstack([F.matrix(r["X"], F.HYBRID_FEATURES) for r in te])
    Xte_m = np.vstack([F.matrix(r["X"], F.ML_ONLY_FEATURES) for r in te])
    y_te = np.concatenate([r["Y"][120] for r in te])
    tw_te = np.concatenate([r["X"]["tw_120"] for r in te])
    g_te = np.concatenate([r["X"]["g_now"] for r in te])
    el_te = np.concatenate([r["lab"]["eligible"] for r in te])
    s_te = np.concatenate([r["lab"]["spike"] for r in te])[el_te]
    rng = np.random.default_rng(7)
    out = []
    for n in sizes:
        acc = dict(hybrid_rmse=[], ml_rmse=[], hybrid_auroc=[], ml_auroc=[])
        for rep in range(reps):
            sub = [tr_all[i] for i in rng.choice(len(tr_all), n, replace=False)]
            Xh = np.vstack([F.matrix(r["X"], F.HYBRID_FEATURES) for r in sub])
            Xm = np.vstack([F.matrix(r["X"], F.ML_ONLY_FEATURES) for r in sub])
            y = np.concatenate([r["Y"][120] for r in sub])
            tw = np.concatenate([r["X"]["tw_120"] for r in sub])
            g = np.concatenate([r["X"]["g_now"] for r in sub])
            m = ~np.isnan(y)
            kw = gbm(loss="absolute_error", max_iter=200)
            ph = HistGradientBoostingRegressor(**kw).fit(Xh[m], (y - tw)[m]).predict(Xte_h) + tw_te
            pm = HistGradientBoostingRegressor(**kw).fit(Xm[m], (y - g)[m]).predict(Xte_m) + g_te
            acc["hybrid_rmse"].append(M.regression(y_te, ph)["rmse"])
            acc["ml_rmse"].append(M.regression(y_te, pm)["rmse"])
            el = np.concatenate([r["lab"]["eligible"] for r in sub])
            ys = np.concatenate([r["lab"]["spike"] for r in sub])[el]
            ck = gbm(max_iter=200)
            acc["hybrid_auroc"].append(M.auc_roc(s_te, HistGradientBoostingClassifier(**ck).fit(Xh[el], ys).predict_proba(Xte_h[el_te])[:, 1]))
            acc["ml_auroc"].append(M.auc_roc(s_te, HistGradientBoostingClassifier(**ck).fit(Xm[el], ys).predict_proba(Xte_m[el_te])[:, 1]))
        out.append(dict(n_patients=n, **{k: float(np.mean(v)) for k, v in acc.items()}))
        print(f"  n={n:2d}  RMSE@120 hybrid {out[-1]['hybrid_rmse']:.1f} vs ML {out[-1]['ml_rmse']:.1f} | "
              f"AUROC hybrid {out[-1]['hybrid_auroc']:.3f} vs ML {out[-1]['ml_auroc']:.3f}")
    # zero-shot: physics twin alone needs no training patients at all
    out.insert(0, dict(n_patients=0, hybrid_rmse=M.regression(y_te, tw_te)["rmse"], ml_rmse=None,
                       hybrid_auroc=None, ml_auroc=None))
    return out


PART = 2_000_000


def save_models(models):
    """gzip-pickled models split into ~2 MB parts (friendly to slow git uploads)."""
    blob = gzip.compress(pickle.dumps(models), 6)
    for old in MODEL_DIR.glob("models.pkl.gz.part*"):
        old.unlink()
    for i in range(0, len(blob), PART):
        (MODEL_DIR / f"models.pkl.gz.part{i // PART}").write_bytes(blob[i:i + PART])


def load_models():
    parts = sorted(MODEL_DIR.glob("models.pkl.gz.part*"), key=lambda p: int(p.name.rsplit("part", 1)[1]))
    if not parts:
        raise FileNotFoundError("models not trained yet")
    return pickle.loads(gzip.decompress(b"".join(p.read_bytes() for p in parts)))


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    return o


def main():
    t0 = time.time()
    print("[1/5] loading cohort")
    recs = load_cohort()
    print(f"  {len(recs)} patients ({sum(r.split == 'test' for r in recs)} held-out)")
    print("[2/5] calibrating + assimilating digital twins")
    twins = build_twins(recs)
    print("[3/5] building causal features")
    rows = dataset(twins)
    for r, tw in zip(rows, twins):
        r["cgm5"] = tw.rec.wear["cgm_mgdl"].values.astype(float)
    print(f"  {sum(len(r['anchors']) for r in rows)} anchors")
    print("[4/5] training hybrid models")
    models = train(rows)
    print("[5/5] evaluating on held-out patients")
    res = evaluate(models, rows)
    res["importance"] = importance(models, rows)
    print("[+] data-efficiency experiment")
    res["learning_curve"] = learning_curve(rows)
    res["twin_fidelity"] = {tw.rec.pid: dict(
        calib_rmse=tw.calib["calib_rmse"],
        open_loop_rmse=float(np.sqrt(np.nanmean((tw.open_loop[CALIB_DAYS * 288:] -
                                                 tw.rec.wear["cgm_mgdl"].values[CALIB_DAYS * 288:]) ** 2))))
        for tw in twins}
    res["thresholds"] = models["thr"]
    res["conformal"] = models["conformal"]
    MODEL_DIR.mkdir(exist_ok=True)
    save_models(models)
    np.savez_compressed(MODEL_DIR / "twin_states.npz", **{tw.rec.pid: tw.states.astype(np.float32) for tw in twins},
                        **{tw.rec.pid + "_open": tw.open_loop.astype(np.float32) for tw in twins})
    with open(MODEL_DIR / "twins.json", "w") as f:
        json.dump({tw.rec.pid: tw.calib for tw in twins}, f, indent=1)
    with open(MODEL_DIR / "metrics.json", "w") as f:
        json.dump(_jsonable(res), f, indent=1)
    report(res)
    print(f"done in {time.time() - t0:.0f}s -> {MODEL_DIR}")


def report(res):
    print("\n  Glucose forecast on held-out patients (RMSE mg/dL | Clarke A+B %)")
    print("  " + "model".ljust(14) + "".join(f"{h:>6}min      " for h in HORIZONS))
    for name, d in res["regression"].items():
        print("  " + name.ljust(14) + "".join(f"{d[h]['rmse']:6.1f} | {d[h]['clarke_AB']:4.1f}  " for h in HORIZONS))
    print("  80% interval coverage (conformal):", {h: round(v, 1) for h, v in res["coverage"].items()})
    print("\n  2-hour spike prediction (>180 mg/dL)")
    for k, s in res["spike"].items():
        print(f"  {k:10s} AUROC {s['auroc']:.3f}  AUPRC {s['auprc']:.3f}  sens {s['sensitivity']:.2f}  prec {s['precision']:.2f}")
    for k, e in res["events"].items():
        print(f"  {k:10s} events {e['events']}  detected {e['detection_rate']:.0f}%  >=30min warning "
              f"{e['detected_30min']:.0f}%  median lead {e['median_lead']:.0f} min  false alerts/day {e['false_alerts_per_day']:.2f}")
    print("  importance (AUROC drop):", {k: round(v, 3) for k, v in res["importance"]["auroc_drop"].items()})


if __name__ == "__main__":
    main()
