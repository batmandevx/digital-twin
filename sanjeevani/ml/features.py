"""Feature construction at prediction anchors (strictly causal: only data at
or before the anchor time t is used)."""
import warnings

import numpy as np

from ..config import DAY, CGM_STEP, HORIZONS, SPIKE_MGDL, START
from ..twin.core import CGM_LAG

STATIC = ["age", "bmi", "waist", "hba1c", "years_dx", "metformin_g", "on_su", "insulin_u", "tcf7l2", "prs"]
CONTEXT = ["g_now", "d15", "d30", "d60", "mean_3h", "std_3h", "max_3h", "carbs_3h", "min_since_meal",
           "exp_carbs_2h", "min_to_exp_meal", "steps_1h", "steps_3h", "stress_now", "stress_3h", "hr_1h",
           "hrv_1h", "sleep_last", "deep_frac", "sleep_debt", "tod_sin", "tod_cos", "weekend", "gb_mult"]
TWIN = ["tw_30", "tw_60", "tw_120", "tw0_60", "tw0_120", "tw_peak", "tw_tpeak", "tw_G", "tw_X",
        "tw_I", "tw_gut", "tw_E", "tw_SI", "tw_gamma", "tw_Gb", "tw_err30", "tw_err60", "tw_si_adapt"]
HYBRID_FEATURES = STATIC + CONTEXT + TWIN
ML_ONLY_FEATURES = STATIC + CONTEXT


def _window(arr5, e, n):
    """Values arr5[e-n+1 .. e] for each anchor epoch e -> [A, n]."""
    idx = e[:, None] - np.arange(n)[::-1][None, :]
    return arr5[np.clip(idx, 0, len(arr5) - 1)]


def build(twin, anchors, F_habit=None, F_nomeal=None):
    """Return (X dict of feature arrays [A], extras dict)."""
    r = twin.rec
    anchors = np.asarray(anchors, dtype=int)
    A = len(anchors)
    e = anchors // CGM_STEP
    cg = r.wear["cgm_mgdl"].values.astype(float)
    hr = r.wear["heart_rate_bpm"].values.astype(float)
    hrv = r.wear["hrv_rmssd_ms"].values.astype(float)
    st5 = r.wear["steps"].values.astype(float)
    win = _window(cg, e, 37)                               # last 3 h of CGM
    with np.errstate(all="ignore"):
        last = win[:, -3:]
        g_now = np.where(~np.isnan(last[:, -1]), last[:, -1],
                         np.where(~np.isnan(last[:, -2]), last[:, -2], last[:, -3]))
        X = dict(g_now=g_now, d15=g_now - win[:, -4], d30=g_now - win[:, -7], d60=g_now - win[:, -13],
                 mean_3h=np.nanmean(win, 1), std_3h=np.nanstd(win, 1), max_3h=np.nanmax(win, 1))

    mm = r.meals["minute"].values
    mc = r.meals["carbs_g_est"].values
    X["carbs_3h"] = np.array([mc[(mm > t - 180) & (mm <= t)].sum() for t in anchors])
    X["min_since_meal"] = np.array([min(600, t - mm[mm <= t].max()) if np.any(mm <= t) else 600 for t in anchors])
    exp = twin.expected_meals(anchors, 120)
    ec = np.zeros(A)
    et = np.full(A, 240.0)
    for i, _, off, carbs, _f in exp:
        ec[i] += carbs
        et[i] = min(et[i], off + 1)
    X["exp_carbs_2h"], X["min_to_exp_meal"] = ec, et
    X["steps_1h"] = _window(st5, e, 12).sum(1)
    X["steps_3h"] = _window(st5, e, 36).sum(1)
    stress = r.inputs["stress"]
    X["stress_now"] = stress[anchors]
    X["stress_3h"] = np.array([stress[max(0, t - 180):t + 1].mean() for t in anchors])
    with np.errstate(all="ignore"):
        X["hr_1h"] = np.nanmean(_window(hr, e, 12), 1) - r.rhr
        X["hrv_1h"] = np.nanmean(_window(hrv, e, 12), 1) / r.hrv_base
    day = anchors // DAY
    wakes = np.array([n["wake"] for n in r.nights])
    last = [np.searchsorted(wakes, t, side="right") - 1 for t in anchors]      # most recent *completed* night
    X["sleep_last"] = np.array([r.nights[j]["hours"] if j >= 0 else np.nan for j in last])
    X["deep_frac"] = np.array([r.nights[j]["deep"] if j >= 0 else np.nan for j in last])
    X["sleep_debt"] = r.inputs["sleep_debt"][anchors]
    tod = (anchors % DAY) / DAY * 2 * np.pi
    X["tod_sin"], X["tod_cos"] = np.sin(tod), np.cos(tod)
    X["weekend"] = (((START.weekday() + day) % 7) >= 5).astype(float)
    X["gb_mult"] = r.inputs["gb_mult"][anchors]

    pf = r.profile
    L = pf["labs"]
    for k, v in dict(age=pf["age"], bmi=L["bmi"], waist=L["waist"], hba1c=L["hba1c"], years_dx=pf["years_dx"],
                     metformin_g=pf["metformin_g"], on_su=float(pf["on_sulfonylurea"]), insulin_u=pf["insulin_u"],
                     tcf7l2=pf["tcf7l2"], prs=pf["prs"] if pf["prs"] is not None else 0.0).items():
        X[k] = np.full(A, float(v))

    # ---- twin-derived features (physics) ---------------------------------
    if F_habit is None:
        F_habit = twin.forecast(anchors, 120, habit=True)
    if F_nomeal is None:
        F_nomeal = twin.forecast(anchors, 120, habit=False)
    lagi = lambda h: h - 1 - CGM_LAG
    X["tw_30"], X["tw_60"], X["tw_120"] = (F_habit[:, lagi(h)] for h in HORIZONS)
    X["tw0_60"], X["tw0_120"] = F_nomeal[:, lagi(60)], F_nomeal[:, lagi(120)]
    seg = F_habit[:, :120 - CGM_LAG]
    X["tw_peak"] = seg.max(1)
    X["tw_tpeak"] = seg.argmax(1).astype(float) + CGM_LAG
    s = twin.states[e]
    X["tw_G"], X["tw_X"], X["tw_I"] = s[:, 0], s[:, 1] * 1e3, s[:, 2] - twin.params["Ib"]
    X["tw_gut"], X["tw_E"] = s[:, 3:7].sum(1), s[:, 7]
    X["tw_SI"] = np.full(A, twin.params["SI"] * 1e4)
    X["tw_si_adapt"] = twin.si_mult[anchors]
    # error feedback: how wrong was the twin's own forecast made 30 / 60 min ago?
    for h in (30, 60):
        prev = np.maximum(anchors - h, 0)
        Fp = twin.forecast(prev, h, habit=True)
        X[f"tw_err{h}"] = g_now - Fp[:, h - 1 - CGM_LAG]
    X["tw_gamma"] = np.full(A, twin.params["gamma"])
    X["tw_Gb"] = np.full(A, twin.params["Gb"])
    return X, dict(F_habit=F_habit, F_nomeal=F_nomeal)


def targets(twin, anchors):
    cg = twin.rec.wear["cgm_mgdl"].values.astype(float)
    e = np.asarray(anchors) // CGM_STEP
    n = len(cg)
    Y = {h: cg[np.clip(e + h // CGM_STEP, 0, n - 1)] for h in HORIZONS}
    fut = cg[np.clip(e[:, None] + np.arange(1, 25)[None, :], 0, n - 1)]       # next 120 min
    valid = np.sum(~np.isnan(fut), 1) >= 18
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        fmax = np.nanmax(fut, 1)
        fmin = np.nanmin(fut, 1)
    now = cg[e]
    # a *new* excursion: currently >= 20 mg/dL below the limit, crosses it within 2 h
    eligible = (now < SPIKE_MGDL - 20) & valid & ~np.isnan(now)
    spike = eligible & (fmax >= SPIKE_MGDL)
    return Y, dict(spike=spike.astype(float), valid=valid & ~np.isnan(now), fmax=fmax, fmin=fmin,
                   eligible=eligible)


def matrix(X, names):
    return np.column_stack([np.asarray(X[n], dtype=float) for n in names])
