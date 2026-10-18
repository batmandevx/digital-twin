"""Synthetic Electronic Health Record as a FHIR R4 Bundle.

Codes follow LOINC / SNOMED-CT / RxNorm so the same ingest path also accepts
bundles produced by Synthea (https://synthetichealth.github.io/synthea/).
"""
from datetime import timedelta

import numpy as np

from ..config import START

LOINC = {
    "hba1c": ("4548-4", "Hemoglobin A1c/Hemoglobin.total in Blood", "%"),
    "fpg": ("1558-6", "Fasting glucose [Mass/volume] in Serum or Plasma", "mg/dL"),
    "bmi": ("39156-5", "Body mass index (BMI) [Ratio]", "kg/m2"),
    "weight": ("29463-7", "Body weight", "kg"),
    "height": ("8302-2", "Body height", "m"),
    "waist": ("8280-0", "Waist Circumference at umbilicus by Tape measure", "cm"),
    "sbp": ("8480-6", "Systolic blood pressure", "mm[Hg]"),
    "dbp": ("8462-4", "Diastolic blood pressure", "mm[Hg]"),
    "ldl": ("18262-6", "Cholesterol in LDL [Mass/volume] in Serum or Plasma by Direct assay", "mg/dL"),
    "hdl": ("2085-9", "Cholesterol in HDL [Mass/volume] in Serum or Plasma", "mg/dL"),
    "tg": ("2571-8", "Triglyceride [Mass/volume] in Serum or Plasma", "mg/dL"),
    "creatinine": ("2160-0", "Creatinine [Mass/volume] in Serum or Plasma", "mg/dL"),
    "egfr": ("33914-3", "Glomerular filtration rate/1.73 sq M.predicted", "mL/min/1.73m2"),
    "uacr": ("9318-7", "Albumin/Creatinine [Mass Ratio] in Urine", "mg/g"),
}
SNOMED = {
    "t2d": ("44054006", "Diabetes mellitus type 2"),
    "htn": ("38341003", "Hypertensive disorder"),
    "dyslipidemia": ("55822004", "Hyperlipidemia"),
    "osa": ("78275009", "Obstructive sleep apnea syndrome"),
    "pcos": ("69878008", "Polycystic ovaries"),
    "nafld": ("197321007", "Steatosis of liver"),
    "ckd2": ("431856006", "Chronic kidney disease stage 2"),
}
RXNORM = {
    "metformin": ("6809", "metformin"),
    "glimepiride": ("25789", "glimepiride"),
    "sitagliptin": ("593411", "sitagliptin"),
    "glargine": ("274783", "insulin glargine"),
    "telmisartan": ("73494", "telmisartan"),
    "atorvastatin": ("83367", "atorvastatin"),
}


def _iso(dt):
    return dt.isoformat(timespec="seconds")


def _obs(pid, key, value, when, extra=None):
    code, display, unit = LOINC[key]
    r = {"resourceType": "Observation", "status": "final",
         "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                   "code": "laboratory" if key not in ("bmi", "weight", "height", "waist", "sbp", "dbp") else "vital-signs"}]}],
         "code": {"coding": [{"system": "http://loinc.org", "code": code, "display": display}], "text": display},
         "subject": {"reference": f"Patient/{pid}"}, "effectiveDateTime": _iso(when),
         "valueQuantity": {"value": value, "unit": unit, "system": "http://unitsofmeasure.org", "code": unit}}
    if extra:
        r.update(extra)
    return r


def build_bundle(p, hba1c_now, rng):
    pid = p["id"]
    now = START - timedelta(days=2)
    birth_year = START.year - p["age"]
    abha = f"91-{rng.integers(1000, 9999)}-XXXX-{rng.integers(1000, 9999)}"
    first, *rest = p["name"].split(" ")
    entries = [{
        "resourceType": "Patient", "id": pid,
        "identifier": [{"system": "https://healthid.ndhm.gov.in", "value": abha,
                        "type": {"text": "ABHA number (synthetic, masked)"}}],
        "name": [{"use": "official", "family": rest[-1] if rest else "", "given": [first] + rest[:-1]}],
        "gender": "male" if p["sex"] == "M" else "female",
        "birthDate": f"{birth_year}-{rng.integers(1, 13):02d}-{rng.integers(1, 28):02d}",
        "address": [{"city": p["city"], "country": "IN"}],
        "extension": [{"url": "urn:sanjeevani:diet", "valueString": "vegetarian" if p["veg"] else "non-vegetarian"},
                      {"url": "urn:sanjeevani:region", "valueString": p["region"]},
                      {"url": "urn:sanjeevani:synthetic", "valueBoolean": True}],
    }]

    def cond(key, onset_years):
        code, disp = SNOMED[key]
        entries.append({"resourceType": "Condition", "clinicalStatus": {"coding": [{"code": "active"}]},
                        "code": {"coding": [{"system": "http://snomed.info/sct", "code": code, "display": disp}], "text": disp},
                        "subject": {"reference": f"Patient/{pid}"},
                        "onsetDateTime": _iso(now - timedelta(days=int(365 * onset_years)))})

    cond("t2d", p["years_dx"] + 0.3)
    if p["htn"]:
        cond("htn", max(0.5, p["years_dx"] * 0.6))
    if p["dyslipidemia"]:
        cond("dyslipidemia", max(0.5, p["years_dx"] * 0.5))
    if p["osa"]:
        cond("osa", 1)
    if p["pcos"]:
        cond("pcos", 8)
    if p["nafld"]:
        cond("nafld", 2)
    egfr = int(np.clip(rng.normal(98 - 0.7 * (p["age"] - 40) - 1.2 * p["years_dx"], 8), 45, 120))
    if p["name"] == "Gurpreet Singh Sandhu":
        egfr = 68
    if egfr < 90 and p["years_dx"] > 8:
        cond("ckd2", 2)

    # labs: last 5 quarterly visits, HbA1c drifts toward the current value
    a1c = hba1c_now
    hist = []
    for q in range(5):
        when = now - timedelta(days=91 * q + int(rng.integers(0, 10)))
        hist.append((when, round(a1c, 1)))
        a1c = float(np.clip(a1c + rng.normal(-0.05 if q < 2 else 0.1, 0.25), 6.0, 11.5))
    for when, v in hist:
        entries.append(_obs(pid, "hba1c", v, when))
        entries.append(_obs(pid, "fpg", int(p["fpg"] + rng.normal(0, 9) + 10 * (v - hba1c_now)), when))
    sbp = int(rng.normal(138 if p["htn"] else 124, 8))
    for key, val in (("bmi", p["bmi"]), ("weight", p["weight_kg"]), ("height", p["height_m"]),
                     ("waist", p["waist"]), ("sbp", sbp), ("dbp", int(sbp * 0.62 + rng.normal(0, 4))),
                     ("ldl", int(rng.normal(118 if p["dyslipidemia"] else 96, 18))),
                     ("hdl", int(rng.normal(38 if p["sex"] == "M" else 45, 6))),
                     ("tg", int(rng.normal(190 if p["dyslipidemia"] else 140, 35))),
                     ("creatinine", round(float(np.clip(rng.normal(0.95, 0.15) * 90 / egfr, 0.5, 1.8)), 2)),
                     ("egfr", egfr), ("uacr", int(np.clip(rng.lognormal(3.0 + 0.04 * p["years_dx"], 0.5), 5, 300)))):
        entries.append(_obs(pid, key, val, now))

    # genetics (simulated genotype)
    geno = {0: "C/C", 1: "C/T", 2: "T/T"}[p["tcf7l2"]]
    entries.append({"resourceType": "Observation", "status": "final",
                    "category": [{"coding": [{"code": "laboratory"}]}],
                    "code": {"coding": [{"system": "http://loinc.org", "code": "69548-6", "display": "Genetic variant assessment"}],
                             "text": "TCF7L2 rs7903146 genotype"},
                    "subject": {"reference": f"Patient/{pid}"}, "effectiveDateTime": _iso(now - timedelta(days=400)),
                    "valueCodeableConcept": {"text": geno},
                    "component": [{"code": {"text": "gene"}, "valueString": "TCF7L2"},
                                  {"code": {"text": "dbSNP"}, "valueString": "rs7903146"},
                                  {"code": {"text": "risk-allele-count"}, "valueInteger": p["tcf7l2"]}]})
    entries.append({"resourceType": "RiskAssessment", "status": "final", "subject": {"reference": f"Patient/{pid}"},
                    "method": {"text": "South-Asian T2D polygenic risk score (simulated)"},
                    "prediction": [{"outcome": {"text": "T2D PRS z-score"}, "relativeRisk": p["prs"]}]})
    if p["family_history"]:
        entries.append({"resourceType": "FamilyMemberHistory", "status": "completed", "patient": {"reference": f"Patient/{pid}"},
                        "relationship": {"text": rng.choice(["Father", "Mother", "Both parents"])},
                        "condition": [{"code": {"coding": [{"system": "http://snomed.info/sct", "code": "44054006"}],
                                                "text": "Diabetes mellitus type 2"}}]})

    def med(key, dose_text, dose_val, unit):
        code, disp = RXNORM[key]
        entries.append({"resourceType": "MedicationStatement", "status": "active", "subject": {"reference": f"Patient/{pid}"},
                        "medicationCodeableConcept": {"coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                                                                  "code": code, "display": disp}], "text": disp},
                        "dosage": [{"text": dose_text, "doseAndRate": [{"doseQuantity": {"value": dose_val, "unit": unit}}]}]})

    med("metformin", f"{int(p['metformin'] * 1000)} mg/day in two divided doses", p["metformin"] * 1000, "mg/day")
    if p["su"]:
        med("glimepiride", "2 mg once daily before breakfast", 2, "mg/day")
    if p["sitagliptin"]:
        med("sitagliptin", "100 mg once daily", 100, "mg/day")
    if p["insulin_u"]:
        med("glargine", f"{p['insulin_u']} units at bedtime", p["insulin_u"], "U/day")
    if p["htn"]:
        med("telmisartan", "40 mg once daily", 40, "mg/day")
    if p["dyslipidemia"]:
        med("atorvastatin", "20 mg at night", 20, "mg/day")

    return {"resourceType": "Bundle", "type": "collection", "id": f"bundle-{pid}",
            "meta": {"tag": [{"code": "SYNTHETIC", "display": "Synthetic data, not a real person"}]},
            "entry": [{"fullUrl": f"urn:uuid:{pid}-{i}", "resource": r} for i, r in enumerate(entries)]}
