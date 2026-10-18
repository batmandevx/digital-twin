"""Load a patient's EHR + device streams and derive minute-level twin inputs.

Everything here uses only data a real deployment would have: the FHIR record,
the CGM, the wearable (HR, HRV, steps, sleep stages), the meal log and the
medication log. Nothing comes from the hidden ground truth.
"""
import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import PATIENT_DIR, DATA_DIR, T_MIN, DAY, CGM_STEP, CALIB_DAYS
from ..foods import FOODS
from ..ingest.fhir import load_bundle, profile_from_bundle

SLOTS = {"breakfast": (5 * 60, 11 * 60), "lunch": (11 * 60, 16 * 60), "snack": (16 * 60, 19 * 60),
         "dinner": (19 * 60, 25 * 60)}


@dataclass
class PatientRecord:
    pid: str
    profile: dict
    wear: pd.DataFrame
    meals: pd.DataFrame
    meds: pd.DataFrame
    split: str = "train"
    story: str = ""
    inputs: dict = field(default_factory=dict)    # minute-level arrays [T]
    cgm_min: np.ndarray = None                    # [T], NaN where no sample
    nights: list = field(default_factory=list)
    habits: dict = field(default_factory=dict)
    hrv_base: float = 30.0
    rhr: float = 70.0


def _sleep_episodes(stage):
    """Group 5-min sleep epochs into nights (gaps <= 30 min are merged)."""
    asleep = stage > 0
    eps, start, gap = [], None, 0
    for i, a in enumerate(asleep):
        if a:
            if start is None:
                start = i
            gap = 0
        elif start is not None:
            gap += 1
            if gap > 6:
                end = i - gap
                if (end - start) * CGM_STEP >= 180:
                    eps.append((start, end))
                start, gap = None, 0
    if start is not None and (len(asleep) - start) * CGM_STEP >= 180:
        eps.append((start, len(asleep) - 1))
    nights = []
    for a, b in eps:
        seg = stage[a:b + 1]
        mins = int((seg > 0).sum()) * CGM_STEP
        wake_min = (b + 1) * CGM_STEP
        nights.append(dict(bed=a * CGM_STEP, wake=wake_min, day=int(wake_min // DAY), hours=round(mins / 60, 2),
                           deep=round(float((seg == 2).mean()), 3), rem=round(float((seg == 3).mean()), 3),
                           light=round(float((seg == 1).mean()), 3), awake=round(float((seg == 0).mean()), 3)))
    return nights


def load_patient(pid, split="train", story=""):
    pdir = PATIENT_DIR / pid
    prof = profile_from_bundle(load_bundle(pdir / "ehr_fhir.json"))
    wear = pd.read_csv(pdir / "wearables.csv")
    meals = pd.read_csv(pdir / "meals.csv")
    meds = pd.read_csv(pdir / "medications.csv")
    rec = PatientRecord(pid, prof, wear, meals, meds, split, story)
    derive_inputs(rec)
    return rec


def load_cohort():
    with open(DATA_DIR / "manifest.json") as f:
        man = json.load(f)
    return [load_patient(p["id"], p["split"], p.get("story", "")) for p in man["patients"]]


def derive_inputs(rec: PatientRecord):
    T = T_MIN
    w = rec.wear
    n = len(w)
    rep = lambda a: np.repeat(np.asarray(a, dtype=float), CGM_STEP)[:T]

    cgm = np.full(T, np.nan)
    cgm[w["minute"].values] = w["cgm_mgdl"].values
    rec.cgm_min = cgm

    # meals (logged only) -> fast / slow carbohydrate channels
    cf, cs = np.zeros(T), np.zeros(T)
    for m in rec.meals.itertuples():
        f = FOODS.get(m.food_id, dict(fast=0.7))
        cf[int(m.minute)] += m.carbs_g_est * f["fast"]
        cs[int(m.minute)] += m.carbs_g_est * (1 - f["fast"])

    steps = rep(w["steps"].values / CGM_STEP)
    stage = w["sleep_stage"].values.astype(int)
    rec.nights = _sleep_episodes(stage)
    debt = np.zeros(T)                         # causal: a night's debt applies from its wake-up onward
    for i, nt in enumerate(rec.nights):
        end = rec.nights[i + 1]["wake"] if i + 1 < len(rec.nights) else T
        debt[nt["wake"]:end] = max(0.0, 7.0 - nt["hours"])

    # wearable-inferred stress: HRV suppression + HR elevation beyond activity
    calib = slice(0, CALIB_DAYS * DAY // CGM_STEP)
    act = np.clip(w["steps"].values / (CGM_STEP * 100.0), 0, 1.2)
    awake = stage == 0
    hrv = w["hrv_rmssd_ms"].values.astype(float)
    hr = w["heart_rate_bpm"].values.astype(float)
    quiet = awake & (act < 0.05)
    quiet_c = quiet.copy()
    quiet_c[calib.stop:] = False
    rec.hrv_base = float(np.nanmedian(np.where(quiet_c, hrv, np.nan)))
    rec.rhr = float(np.nanpercentile(np.where(quiet_c, hr, np.nan), 40))
    exp_hrv = rec.hrv_base * (1 - 0.3 * np.minimum(act, 1))
    s_hrv = np.clip((1 - hrv / exp_hrv) / 0.42, 0, 1)
    s_hr = np.clip((hr - (rec.rhr + 38 * act)) / 11.0, 0, 1)
    s = pd.Series(np.nanmean(np.vstack([s_hrv, s_hr]), axis=0)).interpolate(limit_direction="both")
    s = s.rolling(6, min_periods=1).mean().values
    s = np.where(awake, s, 0.0)
    s = np.where(s < 0.18, 0.0, s)                    # dead-band: ignore normal fluctuation
    stress = rep(s)

    # medication log -> metformin effect multiplier
    gb_mult = np.ones(T)
    met_total = rec.profile.get("metformin_g", 0.0)
    for m in rec.meds.itertuples():
        if not bool(m.taken):
            gb_mult[int(m.minute):int(m.minute) + 12 * 60] *= 1 + 0.05 * met_total

    rec.inputs = dict(carbs_fast=cf, carbs_slow=cs, steps=steps, sleep_debt=debt, stress=stress,
                      gb_mult=gb_mult, egp_extra=np.zeros(T))
    rec.habits = habit_profile(rec)
    return rec


def habit_profile(rec, days=CALIB_DAYS):
    """Typical meal slots learned from onboarding-period logs (+ activity profile)."""
    m = rec.meals[rec.meals["minute"] < days * DAY]
    tod = m["minute"] % DAY
    tod = np.where(tod < 5 * 60, tod + DAY, tod)               # after-midnight dinners
    slots = {}
    for name, (a, b) in SLOTS.items():
        sel = m[(tod >= a) & (tod < b)]
        if len(sel) == 0:
            continue
        sel_tod = np.where(sel["minute"] % DAY < 5 * 60, sel["minute"] % DAY + DAY, sel["minute"] % DAY)
        foods = sel["food_id"].value_counts()
        fast = float(np.mean([FOODS[f]["fast"] for f in sel["food_id"]]))
        slots[name] = dict(prob=min(1.0, sel["minute"].floordiv(DAY).nunique() / days),
                           tod=int(np.median(sel_tod)), carbs=float(sel["carbs_g_est"].median()),
                           fast=fast, food=foods.index[0])
    steps = rec.inputs["steps"][:days * DAY].reshape(days, DAY).mean(0)
    debt_nights = [n["hours"] for n in rec.nights if n["day"] <= days]
    return dict(slots=slots, steps_profile=steps,
                sleep_hours=float(np.median(debt_nights)) if debt_nights else 7.0)
