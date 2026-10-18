"""Counterfactual reasoning on the digital twin.

* attribute()  - exact Shapley attribution of a predicted glucose peak to
                 physiological drivers (meal load, sleep debt, inactivity,
                 stress, missed medication) using 2^5 twin simulations.
* what_if()    - 24-hour simulation of a lifestyle / medication plan.
* optimise()   - searches 54 candidate micro-plans and ranks them by benefit
                 per unit of effort ("prescription search").
"""
import itertools
from math import factorial

import numpy as np

from .. import physiology as phys
from ..config import DAY, CGM_STEP, SPIKE_MGDL, HYPO_MGDL, SEVERE_MGDL
from ..foods import FOODS, LOW_GI_SWAPS

FACTORS = ["meal", "sleep", "inactivity", "stress", "medication"]
FACTOR_LABEL = dict(meal="Meal glycaemic load", sleep="Sleep debt", inactivity="Post-meal inactivity",
                    stress="Stress (HRV-inferred)", medication="Missed metformin")


def _concat_inputs(twin, t, back=180, H=120):
    s = max(0, t - back)
    past = {k: v[s:t + 1].copy() for k, v in twin.rec.inputs.items()}
    fut = twin.future_inputs([t], H, habit=True)
    return s, {k: np.concatenate([past[k], fut[k][0]]) for k in past}


def _apply(inp, fixed, start):
    out = {k: v.copy() for k, v in inp.items()}
    if "meal" in fixed:
        cf, cs = out["carbs_fast"], out["carbs_slow"]
        out["carbs_fast"], out["carbs_slow"] = cf * 0.6 * 0.45, cs * 0.6 + cf * 0.6 * 0.55
    if "sleep" in fixed:
        out["sleep_debt"][:] = 0
    if "stress" in fixed:
        out["stress"][:] = 0
    if "medication" in fixed:
        out["gb_mult"][:] = 1
    if "inactivity" in fixed:
        meals = np.where(inp["carbs_fast"] + inp["carbs_slow"] > 15)[0]
        for m in meals:
            out["steps"][m + 15:m + 30] = np.maximum(out["steps"][m + 15:m + 30], 100)
    return out


def attribute(twin, t, H=120):
    s, inp = _concat_inputs(twin, t, H=H)
    off = t - s
    combos = [frozenset(c) for r in range(len(FACTORS) + 1) for c in itertools.combinations(FACTORS, r)]
    B = len(combos)
    batch = {k: np.stack([_apply(inp, c, s)[k] for c in combos]) for k in inp}
    p = twin.params_at([s] * B)
    st = twin.state_at([s] * B)
    G, _, _ = phys.simulate(p, st, batch, tod0=np.full(B, s % DAY))
    peaks = G[:, off + 1:].max(1)
    v = {c: peaks[i] for i, c in enumerate(combos)}
    n = len(FACTORS)
    phi = {}
    for f in FACTORS:
        tot = 0.0
        for c in combos:
            if f in c:
                continue
            w = factorial(len(c)) * factorial(n - len(c) - 1) / factorial(n)
            tot += w * (v[c] - v[c | {f}])            # how much the peak drops when f is fixed
        phi[f] = float(tot)
    return dict(peak_actual=float(v[frozenset()]), peak_ideal=float(v[frozenset(FACTORS)]),
                drivers=sorted([dict(key=f, label=FACTOR_LABEL[f], mgdl=round(phi[f], 1)) for f in FACTORS],
                               key=lambda d: -d["mgdl"]))


# --------------------------------------------------------------------- what-if
def day_plan(twin, t, H=DAY, skip_snack=False):
    """The patient's habitual next 24 h (meals at their usual times)."""
    plan = []
    fasting = twin.fasting_today(t)
    for name, s in twin.rec.habits["slots"].items():
        if s["prob"] < 0.5 or (skip_snack and name == "snack"):
            continue
        dt = (s["tod"] - t % DAY) % DAY
        if 0 < dt <= H:
            food, carbs, fast = twin.slot_meal(name, s, fasting and dt < 16 * 60)
            plan.append(dict(slot=name, offset=int(dt), food=food, carbs=carbs, fast=fast))
    return sorted(plan, key=lambda m: m["offset"])


def build_plan_inputs(twin, t, cfg, H=DAY):
    walk = float(cfg.get("walk", 0))
    swap = float(cfg.get("swap", 0))
    shift = float(cfg.get("dinner_shift", 0))
    sleep_h = float(cfg.get("sleep_h", twin.rec.habits["sleep_hours"]))
    met = cfg.get("metformin")
    base_met = twin.rec.profile.get("metformin_g", 0.0)
    inp = phys.empty_inputs(1, H)
    ks = np.arange(1, H + 1)
    inp["steps"][0] = twin.rec.habits["steps_profile"][(t + ks) % DAY]
    next_day = (t // DAY + 1) * DAY
    cut = int(np.clip(next_day + 6 * 60 - t, 0, H))
    inp["egp_extra"][0] = twin.params.get("dawn", 0.0) * phys.dawn_profile(H, t + 1)
    inp["sleep_debt"][0, :cut] = twin.rec.inputs["sleep_debt"][t]
    inp["sleep_debt"][0, cut:] = max(0.0, 7.0 - sleep_h)
    if met is not None:
        inp["gb_mult"][0] *= 1 - 0.045 * (float(met) - base_met)
    meals = []
    for m in day_plan(twin, t, H, skip_snack=bool(cfg.get("skip_snack"))):
        off = m["offset"]
        if m["slot"] == "dinner":
            off = max(1, off - int(shift * 60))
        carbs, fast, food = m["carbs"], m["fast"], m["food"]
        if swap > 0:
            carbs *= 1 - 0.25 * swap
            fast = fast - swap * max(0.0, fast - 0.38)
            if swap >= 0.5 and food in LOW_GI_SWAPS:
                food = LOW_GI_SWAPS[food]
        if off >= H:
            continue
        inp["carbs_fast"][0, off - 1] += carbs * fast
        inp["carbs_slow"][0, off - 1] += carbs * (1 - fast)
        if walk > 0 and m["slot"] != "snack":
            inp["steps"][0, off + 15:off + 15 + int(walk)] = 100
        meals.append(dict(slot=m["slot"], minute=int(t + off), food=food, name=FOODS[food]["name"],
                          icon=FOODS[food]["icon"], carbs=round(carbs)))
    return inp, meals


def kpis(G):
    g = np.asarray(G)
    mean = float(g.mean())
    return dict(excess=float(np.mean(np.maximum(g - SPIKE_MGDL, 0))),tir=float(np.mean((g >= HYPO_MGDL) & (g <= SPIKE_MGDL)) * 100),
                tar=float(np.mean(g > SPIKE_MGDL) * 100), tar250=float(np.mean(g > SEVERE_MGDL) * 100),
                tbr=float(np.mean(g < HYPO_MGDL) * 100), mean=mean, peak=float(g.max()),
                gmi=float(phys.gmi(mean)), cv=float(g.std() / mean * 100))


def simulate_plans(twin, t, cfgs, H=DAY):
    B = len(cfgs)
    built = [build_plan_inputs(twin, t, c, H) for c in cfgs]
    inp = {k: np.concatenate([b[0][k] for b in built]) for k in phys.INPUTS}
    p = twin.params_at([t] * B)
    G, _, _ = phys.simulate(p, twin.state_at([t] * B), inp, tod0=np.full(B, (t + 1) % DAY))
    return G, [b[1] for b in built]


def what_if(twin, t, cfg):
    base_cfg = dict(sleep_h=twin.rec.habits["sleep_hours"])
    G, meals = simulate_plans(twin, t, [base_cfg, {**base_cfg, **cfg}])
    kb, ks = kpis(G[0]), kpis(G[1])
    a1c = twin.rec.profile["labs"]["hba1c"]
    return dict(t=t, minutes=list(range(t + CGM_STEP, t + DAY + 1, CGM_STEP)),
                baseline=np.round(G[0, CGM_STEP - 1::CGM_STEP], 1).tolist(),
                scenario=np.round(G[1, CGM_STEP - 1::CGM_STEP], 1).tolist(),
                meals_baseline=meals[0], meals_scenario=meals[1], kpi_baseline=kb, kpi_scenario=ks,
                hba1c_now=a1c, hba1c_90d=round(a1c + 0.85 * (ks["gmi"] - kb["gmi"]), 2))


GRID = dict(walk=(0, 10, 20), swap=(0, 0.5, 1.0), dinner_shift=(0, 1, 2), sleep=("habit", 7.5))


def optimise(twin, t):
    hs = twin.rec.habits["sleep_hours"]
    cfgs = []
    for w, sw, ds, sl in itertools.product(*GRID.values()):
        cfgs.append(dict(walk=w, swap=sw, dinner_shift=ds, sleep_h=hs if sl == "habit" else max(hs, 7.5)))
    G, _ = simulate_plans(twin, t, cfgs)
    base = kpis(G[0])
    rows = []
    for c, g in zip(cfgs, G):
        k = kpis(g)
        effort = c["walk"] / 10 + 2 * c["swap"] + c["dinner_shift"] + (1.5 if c["sleep_h"] > hs + 0.2 else 0)
        gain = k["tir"] - base["tir"]
        benefit = (1 - k["excess"] / max(base["excess"], 1e-6)) * 100 if base["excess"] > 0.05 else gain * 5
        rows.append(dict(cfg=c, kpi=k, gain_tir=gain, effort=effort, benefit=benefit,
                         score=benefit - 7.0 * effort, peak_drop=base["peak"] - k["peak"]))
    order = sorted(range(len(rows)), key=lambda i: -rows[i]["score"])
    top = [rows[i] for i in order if rows[i]["effort"] > 0][:3]
    best = max(rows, key=lambda r: r["benefit"])
    curves = np.round(G[:, CGM_STEP - 1::CGM_STEP], 1)
    return dict(baseline=base, top=top, max_benefit=best, n=len(cfgs),
                curves=curves.tolist(), best_index=order[0] if rows[order[0]]["effort"] > 0 else order[1],
                cfgs=cfgs)
