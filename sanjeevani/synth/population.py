"""Synthetic Indian Type-2-diabetes population.

Each patient has (a) EHR-visible traits (demographics, labs, medications,
genetics), (b) hidden "true" physiology used only by the ground-truth
simulator, and (c) behavioural habits (diet, meal timing, sleep, activity,
adherence, festival fasting). Six hand-written personas serve as demo stories;
the rest are sampled at random. All names are synthetic.
"""
import numpy as np

REGIONS = {
    "north": dict(cities=["Lucknow", "Delhi", "Jaipur", "Ludhiana", "Kanpur", "Chandigarh"],
                  first_m=["Rajesh", "Sanjay", "Amit", "Vinod", "Rakesh", "Manoj", "Harpreet"],
                  first_f=["Sunita", "Neha", "Kavita", "Pooja", "Anita", "Simran", "Rekha"],
                  last=["Verma", "Sharma", "Gupta", "Singh", "Yadav", "Agarwal", "Mishra"],
                  breakfast=["aloo_paratha", "poha", "besan_chilla", "bread_omelette", "oats_milk"],
                  meals=["roti_dal_sabzi", "rice_dal_thali", "paneer_roti", "chole_bhature", "khichdi", "millet_roti_sabzi"]),
    "south": dict(cities=["Chennai", "Bengaluru", "Hyderabad", "Kochi", "Coimbatore", "Mysuru"],
                  first_m=["Ramesh", "Karthik", "Suresh", "Venkat", "Arun", "Prakash", "Rahul"],
                  first_f=["Lakshmi", "Divya", "Meena", "Priya", "Revathi", "Anjali", "Shalini"],
                  last=["Iyer", "Reddy", "Nair", "Rao", "Pillai", "Krishnan", "Naidu"],
                  breakfast=["idli_sambar", "masala_dosa", "upma", "oats_milk", "poha"],
                  meals=["rice_sambar_rasam", "rice_dal_thali", "chicken_biryani", "brown_rice_rajma", "khichdi", "roti_dal_sabzi"]),
    "east": dict(cities=["Kolkata", "Bhubaneswar", "Patna", "Guwahati"],
                 first_m=["Subhash", "Abhijit", "Debashish", "Rohit"],
                 first_f=["Ananya", "Rupa", "Moumita", "Sneha"],
                 last=["Banerjee", "Das", "Mukherjee", "Mohanty", "Ghosh"],
                 breakfast=["bread_omelette", "poha", "upma", "oats_milk"],
                 meals=["fish_rice", "rice_dal_thali", "khichdi", "roti_dal_sabzi", "chicken_biryani"]),
    "west": dict(cities=["Mumbai", "Pune", "Ahmedabad", "Surat", "Nagpur"],
                 first_m=["Nikhil", "Hemant", "Jignesh", "Sachin", "Arjun"],
                 first_f=["Snehal", "Hetal", "Aarti", "Madhuri", "Farida"],
                 last=["Patil", "Shah", "Deshmukh", "Joshi", "Mehta", "Kulkarni"],
                 breakfast=["poha", "upma", "besan_chilla", "bread_omelette", "oats_milk"],
                 meals=["roti_dal_sabzi", "rice_dal_thali", "khichdi", "paneer_roti", "millet_roti_sabzi"]),
}

PERSONAS = [
    dict(name="Rajesh Kumar Verma", sex="M", age=52, region="north", city="Lucknow", veg=True,
         bmi=26.8, waist=99, years_dx=6, fpg=150, si=2.7e-4, gamma=0.055, metformin=1.0, su=False,
         insulin_u=0, sitagliptin=False, adherence=0.82, navratri="full", late_dinner=0.0,
         sleep_h=6.8, walker=0.3, stress_prone=0.3, tcf7l2=1, story="Observes a full nine-day Navratri fast. "
         "Sabudana and kuttu meals cause the sharpest spikes of his year."),
    dict(name="Lakshmi Narayanan", sex="F", age=58, region="south", city="Chennai", veg=True,
         bmi=24.1, waist=92, years_dx=11, fpg=136, si=2.6e-4, gamma=0.05, metformin=1.5, su=True,
         insulin_u=0, sitagliptin=False, adherence=0.9, navratri="none", late_dinner=0.0,
         sleep_h=7.0, walker=0.55, stress_prone=0.2, tcf7l2=2, story="'Thin-fat' phenotype at a normal BMI. "
         "Has rice-heavy lunches and is on glimepiride, so she spikes after lunch and can go low when lunch is late."),
    dict(name="Arjun Mehta", sex="M", age=34, region="west", city="Bengaluru", veg=False,
         bmi=24.6, waist=97, years_dx=1, fpg=134, si=3.0e-4, gamma=0.075, metformin=0.5, su=False,
         insulin_u=0, sitagliptin=False, adherence=0.7, navratri="none", late_dinner=1.6,
         sleep_h=5.4, walker=0.1, stress_prone=0.8, tcf7l2=0, story="Software engineer with late dinners, "
         "short sleep and sprint-deadline stress. His wearable signals explain his spikes better than his diet does."),
    dict(name="Farida Sheikh", sex="F", age=46, region="south", city="Hyderabad", veg=False,
         bmi=29.3, waist=101, years_dx=5, fpg=152, si=2.4e-4, gamma=0.06, metformin=1.0, su=False,
         insulin_u=0, sitagliptin=True, adherence=0.88, navratri="none", late_dinner=0.6,
         sleep_h=6.5, walker=0.25, stress_prone=0.4, tcf7l2=1, story="History of PCOS. Weekend biryani "
         "and evening chai-snacks drive her excursions."),
    dict(name="Gurpreet Singh Sandhu", sex="M", age=63, region="north", city="Ludhiana", veg=True,
         bmi=28.1, waist=104, years_dx=15, fpg=166, si=1.9e-4, gamma=0.035, metformin=2.0, su=False,
         insulin_u=14, sitagliptin=False, adherence=0.75, navratri="none", late_dinner=0.3,
         sleep_h=6.9, walker=0.35, stress_prone=0.2, tcf7l2=2, story="Long-standing diabetes on basal insulin "
         "with early CKD. His parathas and missed metformin doses show up clearly in his twin."),
    dict(name="Ananya Banerjee", sex="F", age=41, region="east", city="Kolkata", veg=False,
         bmi=23.4, waist=84, years_dx=2, fpg=118, si=6.2e-4, gamma=0.13, metformin=0.5, su=False,
         insulin_u=0, sitagliptin=False, adherence=0.96, navratri="none", late_dinner=0.0,
         sleep_h=7.4, walker=0.9, stress_prone=0.15, tcf7l2=0, story="Well-controlled morning walker who "
         "takes a walk after most meals. She is the 'what good looks like' reference twin."),
]


def _clip(x, lo, hi):
    return float(np.clip(x, lo, hi))


def sample_patient(rng, idx):
    region = rng.choice(list(REGIONS))
    R = REGIONS[region]
    sex = rng.choice(["M", "F"])
    first = rng.choice(R["first_m"] if sex == "M" else R["first_f"])
    age = int(np.clip(rng.normal(52, 10), 28, 76))
    bmi = _clip(rng.normal(26.0, 3.2), 20.5, 36)
    waist = _clip(78 + 1.7 * (bmi - 20) + (6 if sex == "M" else 0) + rng.normal(0, 5), 76, 120)
    years_dx = int(np.clip(rng.gamma(2.0, 3.5), 0, 25))
    tcf = int(rng.choice([0, 1, 2], p=[0.55, 0.37, 0.08]))
    log_si = (np.log(3.3e-4) - 0.045 * (bmi - 24) - 0.012 * (waist - 90)
              - 0.01 * (age - 50) + rng.normal(0, 0.25))
    si = _clip(np.exp(log_si), 1.4e-4, 9e-4)
    gamma = _clip(np.exp(np.log(0.085) - 0.035 * years_dx - 0.12 * tcf + rng.normal(0, 0.25)), 0.025, 0.16)
    fpg = _clip(rng.normal(146, 16) + 2.0 * years_dx - 30 * (si - 4e-4) / 1e-4 * 0.1, 108, 185)
    metformin = float(rng.choice([0.5, 1.0, 1.5, 2.0], p=[0.2, 0.4, 0.2, 0.2]))
    su = bool(rng.random() < 0.28)
    insulin_u = int(rng.choice([0, 0, 0, 0, 10, 16])) if years_dx > 8 else 0
    navratri = rng.choice(["none", "partial", "full"], p=[0.55, 0.3, 0.15]) if region in ("north", "west") else "none"
    return dict(
        name=f"{first} {rng.choice(R['last'])}", sex=sex, age=age, region=region,
        city=rng.choice(R["cities"]), veg=bool(rng.random() < (0.6 if region in ("north", "west") else 0.35)),
        bmi=round(bmi, 1), waist=round(waist), years_dx=years_dx, fpg=round(fpg), si=si, gamma=gamma,
        metformin=metformin, su=su, insulin_u=insulin_u, sitagliptin=bool(rng.random() < 0.25),
        adherence=_clip(rng.beta(8, 1.6), 0.55, 0.99), navratri=navratri,
        late_dinner=_clip(rng.exponential(0.5), 0, 2.2), sleep_h=_clip(rng.normal(6.7, 0.6), 5.0, 8.0),
        walker=_clip(rng.beta(2, 3), 0.02, 0.95), stress_prone=_clip(rng.beta(2, 4), 0.05, 0.9),
        tcf7l2=tcf, story="")


def build_population(n, seed):
    rng = np.random.default_rng(seed)
    pats = [dict(p) for p in PERSONAS]
    names = {p["name"] for p in pats}
    while len(pats) < n:
        cand = sample_patient(rng, len(pats))
        if cand["name"] not in names:
            names.add(cand["name"])
            pats.append(cand)
    out = []
    for i, p in enumerate(pats):
        p["id"] = f"SNJ-{i + 1:03d}"
        R = REGIONS[p["region"]]
        p.setdefault("breakfasts", R["breakfast"])
        p.setdefault("meals", R["meals"])
        height = rng.normal(1.68 if p["sex"] == "M" else 1.55, 0.06)
        p["height_m"] = round(float(height), 2)
        p["weight_kg"] = round(float(p["bmi"] * height ** 2), 1)
        # hidden "true" physiology (never shown to the twin)
        p["truth"] = dict(
            Gb=float(p["fpg"]) - 4, SG=_clip(rng.normal(0.012, 0.0015), 0.008, 0.016), SI=p["si"],
            gamma=p["gamma"], Ib=_clip(rng.normal(12, 2.5) + 0.5 * p["insulin_u"], 7, 26),
            BW=p["weight_kg"], k_ex=_clip(rng.normal(0.012, 0.002), 0.007, 0.018),
            egp_stress=_clip(rng.normal(0.35, 0.08), 0.15, 0.6), circ_amp=_clip(rng.normal(0.22, 0.04), 0.12, 0.32),
            sleep_sens=_clip(rng.normal(0.09, 0.02), 0.04, 0.14), h_shift=34.0 if p["su"] else 0.0,
            dawn=_clip(rng.normal(0.22, 0.08), 0.05, 0.45), si_daily_sd=0.10)
        p["rhr"] = round(_clip(rng.normal(74, 6) - 8 * p["walker"], 56, 90))
        p["hrv_base"] = round(_clip(rng.normal(34, 7) - 0.25 * (p["age"] - 45) + 8 * p["walker"], 14, 60), 1)
        p["prs"] = round(float(rng.normal(0.4 * p["tcf7l2"] + 0.2, 0.8)), 2)   # polygenic risk z-score
        p["family_history"] = bool(rng.random() < 0.65 or p["tcf7l2"] == 2)
        p["htn"] = bool(rng.random() < 0.45 or p["age"] > 60)
        p["dyslipidemia"] = bool(rng.random() < 0.5)
        p["osa"] = bool(p["sleep_h"] < 5.8 and rng.random() < 0.5)
        p["pcos"] = p["sex"] == "F" and p["age"] < 50 and rng.random() < 0.3 or p["name"] == "Farida Sheikh"
        p["nafld"] = bool(p["waist"] > 98 and rng.random() < 0.6)
        out.append(p)
    return out
