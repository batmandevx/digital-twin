"""Unit tests:  python -m unittest discover -s tests -v"""
import copy
import json
import unittest

import numpy as np

from sanjeevani import physiology as phys
from sanjeevani.config import DATA_DIR, DAY, PATIENT_DIR
from sanjeevani.ml.metrics import clarke_zones, auc_roc

P = dict(Gb=140, SG=0.012, SI=3e-4, gamma=0.07, Ib=12, BW=70, k_ex=0.012, egp_stress=0.35,
         circ_amp=0.2, sleep_sens=0.09, h_shift=0)


def run(T=360, carbs=0, fast=0.8, walk=False, tod=13 * 60, debt=0.0):
    inp = phys.empty_inputs(1, T)
    inp["carbs_fast"][0, 10] = carbs * fast
    inp["carbs_slow"][0, 10] = carbs * (1 - fast)
    inp["sleep_debt"][:] = debt
    if walk:
        inp["steps"][0, 25:40] = 100
    G, _, _ = phys.simulate(P, phys.steady_state(P), inp, tod0=[tod])
    return G[0]


class Physiology(unittest.TestCase):
    def test_steady_state_is_stable(self):
        G = run(carbs=0, tod=9 * 60)       # circadian peak sensitivity: no secretion term active
        self.assertLess(np.abs(G - P["Gb"]).max(), 1.0)

    def test_meal_raises_glucose_and_returns(self):
        G = run(carbs=85)
        self.assertGreater(G.max(), P["Gb"] + 60)
        self.assertLess(abs(G[-1] - P["Gb"]), 15)

    def test_interventions_have_physiological_sign(self):
        base = run(carbs=85).max()
        self.assertLess(run(carbs=85, walk=True).max(), base)            # walking helps
        self.assertLess(run(carbs=85, fast=0.38).max(), base)            # low-GI helps
        self.assertGreater(run(carbs=85, debt=2.5).max(), base)          # sleep debt hurts
        self.assertGreater(run(carbs=85, tod=22 * 60).max(), run(carbs=85, tod=8 * 60).max())  # late meal hurts

    def test_batch_equals_single(self):
        B = 4
        p = phys.as_batch(P, B)
        inp = phys.empty_inputs(B, 200)
        inp["carbs_fast"][:, 5] = [0, 20, 40, 60]
        G, _, _ = phys.simulate(p, phys.steady_state(p), inp, tod0=np.zeros(B))
        self.assertTrue(np.all(np.diff(G.max(1)) > 0))


class Metrics(unittest.TestCase):
    def test_clarke(self):
        z = clarke_zones(np.array([100, 100, 300, 50]), np.array([105, 150, 60, 200]))
        self.assertEqual(list(z), ["A", "B", "E", "E"])

    def test_auc(self):
        self.assertAlmostEqual(auc_roc(np.array([0, 0, 1, 1]), np.array([.1, .2, .8, .9])), 1.0)


@unittest.skipUnless((DATA_DIR / "manifest.json").exists(), "run `python run.py` once to generate data")
class TwinAndData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sanjeevani.twin.patient import load_patient
        cls.rec = load_patient("SNJ-001")

    def test_fhir_profile(self):
        pf = self.rec.profile
        self.assertEqual(pf["name"], "Rajesh Kumar Verma")
        self.assertIn("hba1c", pf["labs"])
        self.assertGreater(pf["metformin_g"], 0)
        self.assertIn("TCF7L2", pf["genetics"])

    def test_calibration_recovers_basal_glucose(self):
        from sanjeevani.twin.core import calibrate
        truth = json.loads((DATA_DIR / "_ground_truth" / "SNJ-001.json").read_text())["truth"]
        c = calibrate(self.rec, n=128, rounds=2)
        self.assertLess(abs(c["params"]["Gb"] - truth["Gb"]) / truth["Gb"], 0.1)
        self.assertLess(c["calib_rmse"], 30)

    def test_features_are_causal(self):
        """Corrupting data AFTER the anchor must not change any feature."""
        from sanjeevani.twin.core import calibrate, assimilate, DigitalTwin
        from sanjeevani.ml import features as F
        from sanjeevani.twin.patient import derive_inputs
        rec = self.rec
        c = calibrate(rec, n=64, rounds=1)
        tw = DigitalTwin(rec, c, None)
        st, _ = assimilate([rec], [c["params"]])
        tw.states = st[0]
        for t in (8 * DAY + 11 * 60, 9 * DAY + 3 * 60):          # daytime and mid-sleep anchors
            self._check_causal(rec, c, tw, t)

    def _check_causal(self, rec, c, tw, t):
        from sanjeevani.twin.core import assimilate, DigitalTwin
        from sanjeevani.ml import features as F
        from sanjeevani.twin.patient import derive_inputs
        X1, _ = F.build(tw, np.array([t]))

        rec2 = copy.deepcopy(rec)
        w = rec2.wear
        after = w["minute"] > t
        w.loc[after, "cgm_mgdl"] = 400.0
        w.loc[after, "steps"] = 0
        w.loc[after, "sleep_stage"] = 0
        w.loc[after, "hrv_rmssd_ms"] = 5.0
        w.loc[after, "heart_rate_bpm"] = 150
        rec2.meals = rec2.meals[rec2.meals["minute"] <= t]
        derive_inputs(rec2)
        tw2 = DigitalTwin(rec2, c, None)
        st2, _ = assimilate([rec2], [c["params"]])
        tw2.states = st2[0]
        X2, _ = F.build(tw2, np.array([t]))
        for k in F.HYBRID_FEATURES:
            a, b = float(X1[k][0]), float(X2[k][0])
            if np.isnan(a) and np.isnan(b):
                continue
            self.assertAlmostEqual(a, b, places=4, msg=f"feature {k} leaks future data")

    def test_synthetic_marker(self):
        b = json.loads((PATIENT_DIR / "SNJ-001" / "ehr_fhir.json").read_text())
        self.assertEqual(b["meta"]["tag"][0]["code"], "SYNTHETIC")


if __name__ == "__main__":
    unittest.main()
