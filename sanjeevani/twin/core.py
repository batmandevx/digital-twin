"""Personalised digital twin: EHR priors -> Bayesian calibration -> real-time
data assimilation -> forecasting.
"""
import numpy as np

from .. import physiology as phys
from ..config import DAY, CGM_STEP, CALIB_DAYS, T_MIN
from .patient import PatientRecord, SLOTS
from ..foods import FOODS

FIT = ("Gb", "SI", "gamma", "SG", "dawn")
PRIOR_SD = dict(Gb=0.08, SI=0.45, gamma=0.45, SG=0.2, dawn=0.8)     # log-space prior widths
ADAPT_SI = np.exp(np.linspace(-0.4, 0.4, 9))             # daily insulin-sensitivity multipliers
ADAPT_GB = np.array([0.93, 0.965, 1.0, 1.035, 1.07])     # daily hepatic set-point multipliers
CGM_LAG = 10                                             # minutes, plasma -> interstitial
OBS_GAIN = 0.22                                          # assimilation gain per CGM sample


def ehr_priors(prof):
    """Map clinical record -> prior physiology (population relationships).

    * fasting glucose  -> basal glucose
    * BMI, waist, age  -> insulin sensitivity (South-Asian adiposity is more
      metabolically harmful at a given BMI, so waist carries extra weight)
    * diabetes duration, TCF7L2 risk alleles -> beta-cell responsiveness
      (TCF7L2 rs7903146-T impairs insulin secretion)
    * sulfonylurea -> lowered secretion threshold; basal insulin -> Ib
    """
    L = prof["labs"]
    si = np.exp(np.log(3.2e-4) - 0.04 * (L["bmi"] - 24) - 0.01 * (L["waist"] - 90)
                - 0.008 * (prof.get("age", 50) - 50))
    gamma = 0.08 * np.exp(-0.03 * prof["years_dx"] - 0.1 * prof["tcf7l2"])
    return dict(Gb=float(L["fpg"]) - 4.0, SG=0.012, SI=float(np.clip(si, 1.2e-4, 1e-3)),
                gamma=float(np.clip(gamma, 0.02, 0.2)), Ib=12.0 + 0.5 * prof["insulin_u"],
                BW=float(L["weight"]), k_ex=0.012, egp_stress=0.35, circ_amp=0.2, sleep_sens=0.085,
                h_shift=30.0 if prof["on_sulfonylurea"] else 0.0, dawn=0.15)


def _slice_inputs(inputs, a, b, B=1):
    return {k: np.broadcast_to(v[a:b], (B, b - a)).copy() for k, v in inputs.items()}


def calibrate(rec: PatientRecord, rng=None, n=384, rounds=3, days=CALIB_DAYS):
    """MAP fit of FIT parameters to the onboarding CGM via batched
    cross-entropy search (no gradients, ~1-2 s per patient)."""
    rng = rng or np.random.default_rng(0)
    prior = ehr_priors(rec.profile)
    T = days * DAY
    cgm = rec.cgm_min[:T]
    obs_idx = np.where(~np.isnan(cgm))[0]
    obs_idx = obs_idx[obs_idx >= CGM_LAG + 120]               # skip warm-up
    y = cgm[obs_idx]
    mu = np.zeros(len(FIT))
    sd = np.ones(len(FIT))
    best = None
    for r in range(rounds):
        z = rng.normal(mu, sd, size=(n, len(FIT)))
        if best is not None:
            z[0] = best[0]
        params = {k: np.full(n, v, dtype=float) for k, v in prior.items()}
        for j, k in enumerate(FIT):
            params[k] = prior[k] * np.exp(PRIOR_SD[k] * z[:, j])
        inp = _slice_inputs(rec.inputs, 0, T, n)
        inp["egp_extra"] = params["dawn"][:, None] * phys.dawn_profile(T)[None, :]
        G, _, _ = phys.simulate(params, phys.steady_state(params), inp, tod0=np.zeros(n))
        pred = G[:, obs_idx - CGM_LAG]
        mse = np.mean((pred - y) ** 2, axis=1)
        loss = mse + 25.0 * np.sum(z ** 2, axis=1)
        order = np.argsort(loss)
        elite = z[order[:24]]
        best = (z[order[0]], loss[order[0]], mse[order[0]])
        mu, sd = elite.mean(0), np.maximum(elite.std(0), 0.06)
    zb = best[0]
    fitted = dict(prior)
    for j, k in enumerate(FIT):
        fitted[k] = float(prior[k] * np.exp(PRIOR_SD[k] * zb[j]))
    unc = {k: float(PRIOR_SD[k] * sd[j]) for j, k in enumerate(FIT)}  # posterior log-sd (approx.)
    return dict(params=fitted, prior=prior, calib_rmse=float(np.sqrt(best[2])), log_sd=unc)


def lag_compensated(cgm_min):
    """CGM lags plasma by ~10 min; extrapolate each sample along its local slope."""
    out = cgm_min.copy()
    idx = np.where(~np.isnan(cgm_min))[0]
    prev = np.full_like(cgm_min, np.nan)
    prev[idx[1:]] = cgm_min[idx[:-1]]
    gap = np.zeros_like(cgm_min)
    gap[idx[1:]] = idx[1:] - idx[:-1]
    slope = np.where((gap > 0) & (gap <= 10), (cgm_min - prev) / np.maximum(gap, 1), 0.0)
    out[idx] = cgm_min[idx] + np.clip(slope[idx], -4, 4) * CGM_LAG
    return out


def assimilate(recs, params_list, si_mult=None, gb_adapt=None):
    """Run every twin over the whole window, nudged by the CGM (state observer).
    Returns states [B, n_epochs, n_states] sampled every CGM_STEP minutes and
    the open-loop (no assimilation) trajectory for fidelity reporting."""
    B = len(recs)
    params = {k: np.array([p[k] for p in params_list]) for k in phys.PARAMS}
    inp = {k: np.stack([r.inputs[k] for r in recs]) for k in phys.INPUTS}
    if gb_adapt is not None:
        inp["gb_mult"] = inp["gb_mult"] * np.stack(gb_adapt)
    si = np.stack(si_mult) if si_mult is not None else None
    cgm = np.stack([lag_compensated(r.cgm_min) for r in recs])
    _, _, states = phys.simulate(params, phys.steady_state(params), inp, tod0=np.zeros(B),
                                 cgm=cgm, gain=OBS_GAIN, record_states_every=CGM_STEP, si_noise=si)
    G_open, _, _ = phys.simulate(params, phys.steady_state(params), inp, tod0=np.zeros(B), si_noise=si)
    return states, G_open[:, ::CGM_STEP]


def adapt_daily(twins, states, days_total, window=DAY, w_prior=60.0):
    """Adaptive twin: every midnight, re-estimate today's insulin-sensitivity
    and hepatic multipliers from the previous 24 h of CGM (random-walk prior
    toward yesterday's values). Strictly causal: day d uses data before d."""
    grid = np.array([(a, b) for a in ADAPT_SI for b in ADAPT_GB])
    K, P = len(grid), len(twins)
    prev = np.ones((P, 2))
    out = np.ones((P, days_total, 2))
    for d in range(CALIB_DAYS, days_total):
        a, b = d * DAY - window, d * DAY
        B = P * K
        params = {k: np.repeat([tw.params[k] for tw in twins], K) for k in phys.PARAMS}
        inp = {k: np.repeat(np.stack([tw.rec.inputs[k][a:b] for tw in twins]), K, axis=0) for k in phys.INPUTS}
        si_c = np.tile(grid[:, 0], P)                                          # absolute multipliers
        gb_c = np.tile(grid[:, 1], P)
        inp["gb_mult"] = inp["gb_mult"] * gb_c[:, None]
        st = phys.state_from_array(np.repeat(states[:, a // CGM_STEP], K, axis=0))
        G, _, _ = phys.simulate(params, st, inp, tod0=np.zeros(B),
                                si_noise=np.broadcast_to(si_c[:, None], (B, window)))
        for i, tw in enumerate(twins):
            cg = tw.rec.cgm_min[a:b]
            idx = np.where(~np.isnan(cg))[0]
            idx = idx[idx >= CGM_LAG + 60]
            if len(idx) < 60:
                out[i, d] = prev[i]
                continue
            g = G[i * K:(i + 1) * K][:, idx - CGM_LAG]
            mse = np.mean((g - cg[idx]) ** 2, axis=1)
            pen = w_prior * (((np.log(grid[:, 0]) - np.log(prev[i, 0])) / 0.15) ** 2 +
                             ((grid[:, 1] - prev[i, 1]) / 0.035) ** 2)
            prev[i] = grid[np.argmin(mse + pen)]
            out[i, d] = prev[i]
    return out


def expand_daily(daily, T):
    """[days, 2] multipliers -> per-minute arrays."""
    d = np.minimum(np.arange(T) // DAY, len(daily) - 1)
    return daily[d, 0], daily[d, 1]


class DigitalTwin:
    def __init__(self, rec: PatientRecord, calib: dict, states: np.ndarray, open_loop=None):
        self.rec = rec
        self.calib = calib
        self.params = calib["params"]
        self.states = states                  # [n_epochs, n_states]
        self.open_loop = open_loop
        T = len(rec.cgm_min)
        self.dawn_full = self.params.get("dawn", 0.0) * phys.dawn_profile(T)
        rec.inputs["egp_extra"] = self.dawn_full.copy()
        self.set_adapt(np.asarray(calib.get("adapt", np.ones((T // DAY, 2)).tolist())))

    def set_adapt(self, daily):
        self.calib["adapt"] = np.asarray(daily).tolist()
        self.si_mult, self.gb_adapt = expand_daily(np.asarray(daily), len(self.rec.cgm_min))

    def params_at(self, anchors):
        """Batch parameters reflecting the adaptive twin's state at each anchor."""
        anchors = np.asarray(anchors, dtype=int)
        p = phys.as_batch(self.params, len(anchors))
        p["SI"] = p["SI"] * self.si_mult[anchors]
        p["Gb"] = p["Gb"] * self.gb_adapt[anchors]
        return p

    # ------------------------------------------------------------------ inputs
    def future_inputs(self, anchors, H, habit=True, carb_scale=1.0):
        """Inputs for (t, t+H] given only information available at t."""
        A = len(anchors)
        r = self.rec
        inp = phys.empty_inputs(A, H)
        prof = r.habits["steps_profile"]
        ks = np.arange(1, H + 1)
        for i, t in enumerate(anchors):
            mins = (t + ks) % DAY
            inp["steps"][i] = prof[mins]
            inp["sleep_debt"][i] = r.inputs["sleep_debt"][t]
            inp["stress"][i] = r.inputs["stress"][t] * np.exp(-ks / 90.0)
            inp["gb_mult"][i] = r.inputs["gb_mult"][t]
            inp["egp_extra"][i] = self.params.get("dawn", 0.0) * phys.dawn_profile(H, t + 1)
        if habit:
            for i, t, off, carbs, fast in self.expected_meals(anchors, H):
                inp["carbs_fast"][i, off] += carbs * fast * carb_scale
                inp["carbs_slow"][i, off] += carbs * (1 - fast) * carb_scale
        return inp

    def fasting_today(self, t):
        """Festival-aware: fasting foods (e.g. Navratri sabudana/kuttu) logged in
        the last 16 h imply today's main meals will be fasting meals too."""
        m = self.rec.meals
        recent = m[(m["minute"] > t - 16 * 60) & (m["minute"] <= t)]
        return bool(any(FOODS.get(f, {}).get("slot") == "fast" for f in recent["food_id"]))

    def slot_meal(self, name, s, fasting):
        if fasting and name in ("lunch", "dinner"):
            f = FOODS["sabudana_khichdi"]
            return "sabudana_khichdi", f["carbs"], f["fast"]
        return s["food"], s["carbs"], s["fast"]

    def expected_meals(self, anchors, H):
        """Habit-aware anticipation: inject a patient's usual meal when its
        typical time falls in the horizon and no meal was logged recently."""
        r = self.rec
        meal_min = r.meals["minute"].values
        out = []
        for i, t in enumerate(anchors):
            recent = np.any((meal_min > t - 150) & (meal_min <= t))
            if recent:
                continue
            tod = t % DAY
            fasting = self.fasting_today(t)
            for name, s in r.habits["slots"].items():
                if s["prob"] < 0.5 or name == "snack":
                    continue
                _, carbs, fast = self.slot_meal(name, s, fasting)
                dt = (s["tod"] - tod) % DAY
                if 0 < dt <= H:
                    out.append((i, t, int(dt) - 1, carbs, fast))
                elif (DAY - dt) <= 45:                       # usual time just passed -> imminent
                    out.append((i, t, min(15, H - 1), carbs, fast))
        return out

    def state_at(self, anchors):
        e = np.asarray(anchors) // CGM_STEP
        return phys.state_from_array(self.states[e])

    # ----------------------------------------------------------------- forecast
    def forecast(self, anchors, H=120, habit=True):
        anchors = np.asarray(anchors, dtype=int)
        A = len(anchors)
        p = self.params_at(anchors)
        inp = self.future_inputs(anchors, H, habit)
        G, _, _ = phys.simulate(p, self.state_at(anchors), inp, tod0=(anchors + 1) % DAY)
        return G                                   # [A, H] plasma; CGM sees it CGM_LAG later

    def summary(self):
        p, pr = self.params, self.calib["prior"]
        return dict(
            insulin_sensitivity=p["SI"], beta_cell=p["gamma"], basal_glucose=p["Gb"], glucose_effectiveness=p["SG"],
            prior=dict(SI=pr["SI"], gamma=pr["gamma"], Gb=pr["Gb"], SG=pr["SG"]),
            calib_rmse=self.calib["calib_rmse"], log_sd=self.calib["log_sd"])
