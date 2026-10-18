"""FHIR R4 Bundle -> clinical profile used to personalise the twin.

Works with Sanjeevani's synthetic bundles and with Synthea output (both use
LOINC / SNOMED-CT / RxNorm codes). Unknown resources are ignored and missing
values fall back to population defaults, so partial records still work.
"""
import json
from datetime import date

LOINC_KEYS = {
    "4548-4": "hba1c", "1558-6": "fpg", "2345-7": "glucose", "39156-5": "bmi", "29463-7": "weight",
    "8302-2": "height", "8280-0": "waist", "8480-6": "sbp", "8462-4": "dbp", "18262-6": "ldl",
    "13457-7": "ldl", "2085-9": "hdl", "2571-8": "tg", "2160-0": "creatinine", "33914-3": "egfr",
    "62238-1": "egfr", "9318-7": "uacr",
}
DEFAULTS = dict(hba1c=7.5, fpg=145, bmi=25.5, weight=68, height=1.62, waist=92, sbp=130, dbp=82,
                ldl=105, hdl=42, tg=160, creatinine=0.95, egfr=90, uacr=20)


def _age(birth, ref=date(2026, 10, 5)):
    y, m, d = (int(x) for x in birth[:10].split("-"))
    return ref.year - y - ((ref.month, ref.day) < (m, d))


def load_bundle(path):
    with open(path) as f:
        return json.load(f)


def profile_from_bundle(bundle):
    res = [e["resource"] for e in bundle.get("entry", [])]
    prof = dict(conditions=[], medications=[], labs={}, lab_history={}, genetics={}, family_history=[],
                prs=None, diet=None, region=None, synthetic=False)
    for r in res:
        rt = r.get("resourceType")
        if rt == "Patient":
            prof["id"] = r.get("id")
            nm = (r.get("name") or [{}])[0]
            prof["name"] = " ".join(nm.get("given", []) + [nm.get("family", "")]).strip()
            prof["sex"] = "M" if r.get("gender") == "male" else "F"
            prof["age"] = _age(r["birthDate"]) if r.get("birthDate") else 50
            prof["city"] = (r.get("address") or [{}])[0].get("city", "")
            ids = r.get("identifier") or []
            prof["abha"] = next((i["value"] for i in ids if "ndhm" in i.get("system", "")), None)
            for ext in r.get("extension", []):
                if ext["url"].endswith("diet"):
                    prof["diet"] = ext.get("valueString")
                elif ext["url"].endswith("region"):
                    prof["region"] = ext.get("valueString")
                elif ext["url"].endswith("synthetic"):
                    prof["synthetic"] = ext.get("valueBoolean", False)
        elif rt == "Condition":
            c = r["code"]["coding"][0]
            prof["conditions"].append(dict(code=c.get("code"), name=r["code"].get("text") or c.get("display"),
                                           onset=r.get("onsetDateTime", "")[:10]))
        elif rt == "MedicationStatement":
            cc = r["medicationCodeableConcept"]
            dose = (r.get("dosage") or [{}])[0]
            q = (dose.get("doseAndRate") or [{}])[0].get("doseQuantity", {})
            prof["medications"].append(dict(name=cc.get("text") or cc["coding"][0].get("display"),
                                            rxnorm=cc["coding"][0].get("code"), dose=q.get("value"),
                                            unit=q.get("unit"), sig=dose.get("text", "")))
        elif rt == "Observation":
            code = r["code"]["coding"][0].get("code")
            if code == "69548-6":
                comp = {c["code"]["text"]: c.get("valueString", c.get("valueInteger")) for c in r.get("component", [])}
                prof["genetics"][comp.get("gene", "gene")] = dict(
                    variant=comp.get("dbSNP"), genotype=r.get("valueCodeableConcept", {}).get("text"),
                    risk_alleles=comp.get("risk-allele-count"))
                continue
            key = LOINC_KEYS.get(code)
            if key and "valueQuantity" in r:
                when = r.get("effectiveDateTime", "")[:10]
                prof["lab_history"].setdefault(key, []).append((when, r["valueQuantity"]["value"]))
        elif rt == "RiskAssessment":
            pred = (r.get("prediction") or [{}])[0]
            prof["prs"] = pred.get("relativeRisk")
        elif rt == "FamilyMemberHistory":
            prof["family_history"].append(dict(relation=r.get("relationship", {}).get("text"),
                                               condition=r["condition"][0]["code"].get("text")))
    for k, hist in prof["lab_history"].items():
        hist.sort()
        prof["labs"][k] = hist[-1][1]
    for k, v in DEFAULTS.items():
        prof["labs"].setdefault(k, v)
    if "fpg" not in prof["lab_history"] and "glucose" in prof["labs"]:
        prof["labs"]["fpg"] = prof["labs"]["glucose"]

    # convenience fields for the twin
    meds = {m["name"].lower(): m for m in prof["medications"]}
    met = next((m for n, m in meds.items() if "metformin" in n), None)
    prof["metformin_g"] = (met["dose"] or 1000) / 1000.0 if met else 0.0
    prof["on_sulfonylurea"] = any(s in n for n in meds for s in ("glimepiride", "gliclazide", "glipizide", "glibenclamide"))
    prof["on_dpp4"] = any("gliptin" in n for n in meds)
    ins = next((m for n, m in meds.items() if "insulin" in n), None)
    prof["insulin_u"] = float(ins["dose"] or 0) if ins else 0.0
    t2d = next((c for c in prof["conditions"] if c["code"] == "44054006"), None)
    prof["years_dx"] = max(0.0, (2026.75 - int(t2d["onset"][:4]))) if t2d and t2d["onset"] else 3.0
    prof["tcf7l2"] = int((prof["genetics"].get("TCF7L2") or {}).get("risk_alleles") or 0)
    return prof
