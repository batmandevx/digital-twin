"""Behaviour + sensor simulation ("virtual humans").

The ground truth deliberately contains mechanisms the digital twin does not
model: the dawn phenomenon, unlogged snacks, carbohydrate-estimation error,
day-to-day insulin-sensitivity drift, latent stress (the twin only sees HRV and
HR) and CGM lag/noise/dropouts. The twin is therefore misspecified in
realistic ways, which keeps the evaluation honest.
"""
import numpy as np

from ..config import DAY, N_DAYS, T_MIN, CGM_STEP, NAVRATRI_DAYS, START
from ..foods import FOODS
from .. import physiology as phys

FASTING_MEALS = ["sabudana_khichdi", "kuttu_puri_aloo"]
FASTING_LIGHT = ["fruit_plate", "sweet_lassi"]


def _weekday(d):
    return (START.weekday() + d) % 7          # 0 = Monday


def behaviour(p, rng):
    """Minute-level true behaviour for one patient over the full window."""
    T = T_MIN
    asleep = np.zeros(T, bool)
    stage = np.zeros(T // CGM_STEP, np.int8)        # 0 awake 1 light 2 deep 3 REM
    steps = np.zeros(T)
    stress = np.zeros(T)
    debt = np.zeros(T)
    gb_mult = np.ones(T)
    meals_true, meals_logged, meds_log, nights = [], [], [], []

    fasting_days = set()
    if p["navratri"] == "full":
        fasting_days = set(NAVRATRI_DAYS)
    elif p["navratri"] == "partial":
        fasting_days = {min(NAVRATRI_DAYS), max(NAVRATRI_DAYS)}

    # ---- sleep: night n ends on the morning of day n -----------------------
    wake_times = {}
    stress_days = {d for d in range(N_DAYS) if _weekday(d) < 5 and rng.random() < p["stress_prone"] * 0.55}
    for n in range(N_DAYS + 1):
        weekend = _weekday(n) >= 5 if n < N_DAYS else False
        bed = (n - 1) * DAY + int((23.0 + 0.55 * p["late_dinner"] + rng.normal(0, 0.45)
                                   + (0.5 if weekend else 0)) * 60)
        dur_h = rng.normal(p["sleep_h"] + (0.6 if weekend else 0) - (0.7 if (n - 1) in stress_days else 0), 0.6)
        dur_h = float(np.clip(dur_h, 3.8, 9.5))
        wake = bed + int(dur_h * 60)
        nights.append(dict(night=n, bed=bed, wake=wake, hours=dur_h))
        wake_times[n] = wake
        a, b = max(bed, 0), min(wake, T)
        if a < b:
            asleep[a:b] = True
            deep_scale = 1.0 - 0.35 * ((n - 1) in stress_days)
            for e in range(a // CGM_STEP, b // CGM_STEP):
                tm = e * CGM_STEP - bed                      # minutes into the night
                cyc = (tm % 90) / 90.0
                ncyc = tm // 90
                deep_p = max(0.0, 0.55 - 0.13 * ncyc) * deep_scale
                if rng.random() < 0.04:
                    s = 0
                elif cyc < 0.45 and rng.random() < deep_p * 1.6:
                    s = 2
                elif cyc > 0.72 and ncyc >= 1:
                    s = 3
                else:
                    s = 1
                stage[e] = s
        if n < N_DAYS:
            debt[n * DAY:(n + 1) * DAY] = max(0.0, 7.0 - dur_h)

    def add_meal(t, food, portion, logged_p, kind):
        if t < 0 or t >= T:
            return
        f = FOODS[food]
        carbs = f["carbs"] * portion
        meals_true.append(dict(minute=int(t), food=food, carbs=round(carbs, 1), kind=kind))
        if rng.random() < logged_p:
            est = carbs * float(np.exp(rng.normal(0, 0.22)))
            meals_logged.append(dict(minute=int(np.clip(t + rng.normal(0, 4), 0, T - 1)), food=food,
                                     carbs_est=round(est, 0), kind=kind))

    size = (p["weight_kg"] / 65.0) ** 0.3
    for d in range(N_DAYS):
        base = d * DAY
        weekend = _weekday(d) >= 5
        fasting = d in fasting_days
        wake = wake_times[d]
        por = lambda: size * float(np.exp(rng.normal(0, 0.15)))

        # breakfast
        tb = wake + int(rng.normal(50, 15))
        if fasting:
            add_meal(tb, rng.choice(FASTING_LIGHT), por(), 0.85, "breakfast")
        else:
            add_meal(tb, rng.choice(p["breakfasts"]), por(), 0.9, "breakfast")
        # mid-morning chai (rarely logged)
        if rng.random() < 0.45:
            add_meal(base + int(rng.normal(11 * 60, 30)), "chai_biscuit", por() * 0.8, 0.25, "snack")
        # lunch
        tl = base + int(rng.normal(13.4 * 60 + (40 if weekend else 0), 30))
        if fasting:
            add_meal(tl, rng.choice(FASTING_MEALS), por(), 0.9, "lunch")
        else:
            opts = list(p["meals"])
            if weekend and not p["veg"]:
                opts += ["chicken_biryani"] * 3
            food = rng.choice([m for m in opts if not (p["veg"] and m in ("chicken_biryani", "fish_rice"))] or opts)
            add_meal(tl, food, por(), 0.9, "lunch")
        # evening snack
        if rng.random() < 0.75:
            snack = rng.choice(["chai_biscuit", "samosa_chai", "banana", "sprouts_chaat", "roasted_chana"],
                               p=[0.4, 0.2, 0.15, 0.13, 0.12])
            add_meal(base + int(rng.normal(17.2 * 60, 30)), snack, por(), 0.45, "snack")
        # dinner
        td = base + int(rng.normal((20.5 + p["late_dinner"]) * 60, 30))
        if fasting:
            add_meal(td, rng.choice(FASTING_MEALS), por(), 0.9, "dinner")
        else:
            add_meal(td, rng.choice(p["meals"]), por() * 0.95, 0.88, "dinner")
        if d in (min(NAVRATRI_DAYS), max(NAVRATRI_DAYS)) and p["region"] in ("north", "west") and rng.random() < 0.8:
            add_meal(base + int(rng.normal(19 * 60, 40)), "mithai", por(), 0.6, "festival")

        # ---- activity ---------------------------------------------------
        awake_mask = ~asleep[base:base + DAY]
        for e in range(DAY // CGM_STEP):
            m0 = base + e * CGM_STEP
            if not awake_mask[e * CGM_STEP]:
                continue
            r = rng.random()
            spm = 0 if r < 0.45 else rng.uniform(1, 8) if r < 0.85 else rng.uniform(8, 40) if r < 0.97 else rng.uniform(40, 95)
            steps[m0:m0 + CGM_STEP] = spm * (0.75 if _weekday(d) < 5 and p["stress_prone"] > 0.5 else 1.0)
        if rng.random() < p["walker"] * 0.85:
            w0 = wake + int(rng.uniform(10, 40))
            steps[w0:w0 + int(rng.uniform(25, 45))] = rng.uniform(95, 118)
        for mt in (tl, td):
            if rng.random() < p["walker"] * 0.7:
                w0 = mt + int(rng.uniform(10, 25))
                steps[w0:w0 + int(rng.uniform(10, 22))] = rng.uniform(85, 105)

        # ---- stress -------------------------------------------------------
        if d in stress_days:
            s0 = base + int(rng.uniform(10, 16) * 60)
            stress[s0:s0 + int(rng.uniform(120, 300))] = rng.uniform(0.5, 1.0)
        if debt[base] > 1.5:
            stress[wake:wake + 240] = np.maximum(stress[wake:wake + 240], 0.3)

        # ---- medication (metformin morning + evening) -------------------------
        for dose_t, span in ((base + 8 * 60 + 30, 12 * 60), (base + 20 * 60 + 30, 12 * 60)):
            taken = rng.random() < p["adherence"]
            logged_taken = taken if rng.random() < 0.95 else (not taken)
            meds_log.append(dict(minute=dose_t, drug="metformin", dose_g=p["metformin"] / 2, taken=bool(logged_taken)))
            if not taken:
                gb_mult[dose_t:dose_t + span] *= 1 + 0.05 * p["metformin"]
    steps = np.clip(steps, 0, 140)
    return dict(asleep=asleep, stage=stage, steps=steps, stress=np.clip(stress, 0, 1), debt=debt,
                gb_mult=gb_mult, meals_true=meals_true, meals_logged=meals_logged, meds=meds_log,
                nights=nights, fasting_days=sorted(fasting_days), stress_days=sorted(stress_days))


dawn_profile = phys.dawn_profile


def carb_inputs(meals, T, key="carbs"):
    cf = np.zeros(T)
    cs = np.zeros(T)
    for m in meals:
        f = FOODS[m["food"]]
        cf[m["minute"]] += m[key] * f["fast"]
        cs[m["minute"]] += m[key] * (1 - f["fast"])
    return cf, cs


def simulate_truth(pop, behaviours, rng):
    """Run the ground-truth physiology for all patients at once (batch)."""
    B, T = len(pop), T_MIN
    params = {k: np.array([p["truth"][k] for p in pop]) for k in phys.PARAMS}
    inp = phys.empty_inputs(B, T)
    dawn = dawn_profile(T)
    si_noise = np.ones((B, T))
    for i, (p, bh) in enumerate(zip(pop, behaviours)):
        inp["carbs_fast"][i], inp["carbs_slow"][i] = carb_inputs(bh["meals_true"], T)
        inp["steps"][i] = bh["steps"]
        inp["sleep_debt"][i] = bh["debt"]
        inp["stress"][i] = bh["stress"]
        inp["gb_mult"][i] = bh["gb_mult"]
        inp["egp_extra"][i] = p["truth"]["dawn"] * dawn
        daily = np.exp(rng.normal(0, p["truth"]["si_daily_sd"], N_DAYS + 1))
        si_noise[i] = np.interp(np.arange(T), np.arange(N_DAYS + 1) * DAY, daily)
    G, _, _ = phys.simulate(params, phys.steady_state(params), inp, tod0=np.zeros(B), si_noise=si_noise)
    return G, inp


def sensors(p, bh, G, rng):
    """Turn true plasma glucose + behaviour into wearable/CGM streams (5-min)."""
    T = len(G)
    n = T // CGM_STEP
    # interstitial lag (first-order, tau = 10 min)
    Gi = np.empty(T)
    Gi[0] = G[0]
    for k in range(1, T):
        Gi[k] = Gi[k - 1] + (G[k] - Gi[k - 1]) / 10.0
    idx = np.arange(n) * CGM_STEP
    drift = 1 + 0.025 * np.sin(2 * np.pi * idx / (DAY * rng.uniform(3, 6)) + rng.uniform(0, 6))
    noise = np.zeros(n)
    for k in range(1, n):                                   # AR(1) sensor noise
        noise[k] = 0.7 * noise[k - 1] + rng.normal(0, 1)
    cgm = Gi[idx] * drift + noise * (2.2 + 0.015 * Gi[idx])
    cgm = np.clip(np.round(cgm), 40, 400).astype(float)
    for _ in range(rng.integers(1, 4)):                     # signal dropouts
        a = rng.integers(CGM_STEP * 12, n - 40)
        cgm[a:a + rng.integers(6, 30)] = np.nan
    cgm[:6] = np.nan                                        # sensor warm-up

    steps5 = bh["steps"].reshape(n, CGM_STEP).sum(1)
    stress5 = bh["stress"].reshape(n, CGM_STEP).mean(1)
    asleep5 = bh["asleep"][idx]
    debt5 = bh["debt"][idx]
    act = np.clip(steps5 / (CGM_STEP * 100.0), 0, 1.2)
    hr = (p["rhr"] + 38 * act + 11 * stress5 - 8 * asleep5 + 0.03 * (G[idx] - 140)
          + rng.normal(0, 2.0, n))
    stage_gain = np.select([bh["stage"] == 2, bh["stage"] == 3, bh["stage"] == 1], [1.4, 1.15, 1.2], 1.0)
    hrv = (p["hrv_base"] * stage_gain * (1 - 0.42 * stress5) * (1 - 0.3 * np.minimum(act, 1))
           * (1 - 0.035 * debt5) * np.exp(rng.normal(0, 0.12, n)))
    hrv[rng.random(n) < 0.08] = np.nan                       # motion artefacts
    return dict(cgm=cgm, hr=np.round(hr), hrv=np.round(hrv, 1), steps=np.round(steps5),
                sleep_stage=bh["stage"].astype(int), plasma=G[idx], interstitial=Gi[idx])
