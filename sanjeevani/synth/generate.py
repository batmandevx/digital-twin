"""Generate the synthetic cohort: FHIR EHRs + wearable/CGM streams + logs.

    python -m sanjeevani.synth.generate
"""
import json
import shutil
from datetime import timedelta

import numpy as np
import pandas as pd

from ..config import (PATIENT_DIR, TRUTH_DIR, DATA_DIR, START, CGM_STEP, N_PATIENTS, SEED,
                      TEST_FRACTION, T_MIN)
from ..foods import FOODS
from .. import physiology as phys
from .population import build_population, PERSONAS
from .streams import behaviour, simulate_truth, sensors
from .ehr import build_bundle


def ts(minute):
    return (START + timedelta(minutes=int(minute))).isoformat(timespec="minutes")


def main(n=N_PATIENTS, seed=SEED, verbose=True):
    rng = np.random.default_rng(seed)
    pop = build_population(n, seed)
    behaviours = [behaviour(p, rng) for p in pop]
    G, _ = simulate_truth(pop, behaviours, rng)

    for d in (PATIENT_DIR, TRUTH_DIR):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    n_test = int(round(n * TEST_FRACTION))
    test_ids = {p["id"] for p in pop[:len(PERSONAS)]}
    rest = [p["id"] for p in pop[len(PERSONAS):]]
    test_ids |= set(rng.choice(rest, n_test - len(test_ids), replace=False))

    manifest = []
    minutes = np.arange(0, T_MIN, CGM_STEP)
    for i, (p, bh) in enumerate(zip(pop, behaviours)):
        s = sensors(p, bh, G[i], rng)
        mean_g = float(np.mean(G[i]))
        hba1c = float(np.clip(phys.hba1c_from_mean(mean_g) + rng.normal(0, 0.15), 5.9, 12))
        pdir = PATIENT_DIR / p["id"]
        pdir.mkdir()
        with open(pdir / "ehr_fhir.json", "w") as f:
            json.dump(build_bundle(p, hba1c, rng), f, indent=1, ensure_ascii=False)
        pd.DataFrame({
            "timestamp": [ts(m) for m in minutes], "minute": minutes, "cgm_mgdl": s["cgm"],
            "heart_rate_bpm": s["hr"], "hrv_rmssd_ms": s["hrv"], "steps": s["steps"].astype(int),
            "sleep_stage": s["sleep_stage"],
        }).to_csv(pdir / "wearables.csv", index=False)
        pd.DataFrame([{"timestamp": ts(m["minute"]), "minute": m["minute"], "food_id": m["food"],
                       "food": FOODS[m["food"]]["name"], "carbs_g_est": m["carbs_est"], "meal_type": m["kind"]}
                      for m in sorted(bh["meals_logged"], key=lambda r: r["minute"])],
                     columns=["timestamp", "minute", "food_id", "food", "carbs_g_est", "meal_type"]
                     ).to_csv(pdir / "meals.csv", index=False)
        pd.DataFrame([{"timestamp": ts(m["minute"]), **m} for m in bh["meds"]]).to_csv(pdir / "medications.csv", index=False)

        truth = {k: v for k, v in p.items() if k not in ("breakfasts", "meals")}
        truth.update(meals_true=bh["meals_true"], nights=bh["nights"], fasting_days=bh["fasting_days"],
                     stress_days=bh["stress_days"], mean_glucose=mean_g, hba1c_true=hba1c)
        with open(TRUTH_DIR / f"{p['id']}.json", "w") as f:
            json.dump(truth, f, indent=1, default=float)
        np.savez_compressed(TRUTH_DIR / f"{p['id']}_signals.npz", plasma=s["plasma"],
                            stress=bh["stress"][::CGM_STEP], steps_true=bh["steps"][::CGM_STEP])
        manifest.append(dict(id=p["id"], name=p["name"], split="test" if p["id"] in test_ids else "train",
                             persona=i < len(PERSONAS), story=p["story"]))
        if verbose:
            cg = s["cgm"][~np.isnan(s["cgm"])]
            print(f"{p['id']} {p['name']:24s} {manifest[-1]['split']:5s} HbA1c {hba1c:4.1f}  "
                  f"CGM mean {cg.mean():5.1f}  TIR {np.mean((cg >= 70) & (cg <= 180)) * 100:4.0f}%  "
                  f">250 {np.mean(cg > 250) * 100:3.0f}%  <70 {np.mean(cg < 70) * 100:3.1f}%  "
                  f"meals logged {len(bh['meals_logged'])}/{len(bh['meals_true'])}")
    with open(DATA_DIR / "manifest.json", "w") as f:
        json.dump(dict(start=START.isoformat(), cgm_step_min=CGM_STEP, patients=manifest), f, indent=1)
    return manifest


if __name__ == "__main__":
    main()
