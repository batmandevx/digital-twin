# Sanjeevani Twin: demo video script (≈ 22 minutes)

The submission requires a video of at least 20 minutes. Record your screen with
OBS, QuickTime or a PowerPoint recording, and upload it to YouTube as **Unlisted**.
Paste the link into the README.

**Setup before recording**
1. `python run.py` → the dashboard opens at http://127.0.0.1:8000
2. Use a full-screen browser at 1600×900 or larger. Close other tabs.
3. Keep `docs/Presentation.pdf` open in another window for sections 1, 2 and 9.
4. Shortcuts: **Space** = play/pause replay · **← / →** = ±15 min · **T** = guided tour · **Esc** = reset view.

---

## 0:00–1:30 · Hook (slides 1–2)
> "Every day, millions of Indians with Type 2 Diabetes eat a meal that will push their glucose above 180,
> and nobody sees it coming. The doctor sees an HbA1c every three months. We built **Sanjeevani Twin**:
> a digital twin of each patient that sees the spike two hours early, explains why, and tests the fix
> on a virtual copy of the patient before the patient changes anything."

- India: ~101 million people with diabetes and ~136 million with prediabetes (ICMR-INDIAB 2023).
- Indian specifics break Western tools: the thin-fat phenotype, rice and roti loads, late dinners, Navratri fasting.

## 1:30–4:00 · What makes this a *twin* (slides 3–4)
- A predictor tells you a number. A twin is a **simulatable model of the person**.
- Two data streams fused, as the challenge asks:
  - **Static**: FHIR R4 EHR (labs, diagnoses, meds, TCF7L2 genotype, polygenic risk)
  - **Dynamic**: CGM, heart rate, HRV, sleep stages, steps, plus meal and medication logs
- Walk through the architecture diagram left to right: data, ingest, physiology core, hybrid AI, counterfactual reasoning, clinician UI.
- Emphasise: CPU-only, four Python dependencies, the whole pipeline reproduces in about 5 minutes.

## 4:00–6:00 · Data and honesty (slide 5)
- 40 synthetic Indian patients × 14 days, generated in the repo. Show `data/patients/SNJ-001/` with `ehr_fhir.json`, `wearables.csv` and `meals.csv`.
- **Sandbox rules**: no real patient data, DPDP Act 2023 and HIPAA-safe. The FHIR parser also accepts Synthea bundles.
- **Key point for judges:** the ground-truth simulator contains effects the twin *does not know*: dawn phenomenon, unlogged snacks, carb-count errors, daily insulin-sensitivity drift, latent stress, CGM lag and dropouts. So the evaluation is not circular.
- Patient-level split: 24 train, 6 calibration, 10 test. **All demo stories are held-out patients.**

## 6:00–9:00 · Live demo part 1: the command centre
1. The boot sequence plays: twins calibrating, streams ingesting.
2. **3D twin** (point at each element while talking):
   - The particle body assembles. Each organ glows from the twin's *state*: pancreas = insulin above basal, liver = hepatic output, gut = carbs absorbing, heart beats at the measured HR with shockwaves, brain = HRV-inferred stress, muscle = exercise memory.
   - The blood is coloured by glucose (teal = in range, amber/red = high).
   - The **24-h glucose ribbon** spirals around the body; spikes bulge outward, and the forecast continues as dots.
   - The **DNA helix** shows the TCF7L2 genotype that set the beta-cell prior.
   - Data streams (EHR, CGM, HR, HRV, sleep, steps) flow visibly into the organs they inform.
   - **Click the pancreas**: the camera flies in and a card explains the parameter and its live values. Double-click to return.
3. **Clinic triage** on the left: 40 twins ranked by predicted risk and time to event.

## 9:00–12:00 · Live demo part 2: Rajesh, Navratri, 16 Oct 12:15
- Header: 51 y, Lucknow, vegetarian, *held-out patient*, **"Navratri · fasting detected"**.
- Alert: **~80% spike risk, crossing 180 in ~1 h 30 m, peak ~236 with an 80% interval**. Read the countdown.
- "How does it know? The twin saw fasting foods in today's log and now expects a sabudana lunch. We call it *festival-aware anticipation*."
- **Why is the twin worried?** These are exact Shapley values over 32 counterfactual twin simulations: meal glycaemic load is about +28 mg/dL, post-meal inactivity about +5.
- **Nudge**: chosen by simulation, shown in English and Hindi. Press *Send to patient* (demo).
- Press **Space** to replay. The clock advances, the lunch is logged, the glucose climbs exactly as forecast, and the organs light up (gut, then pancreas). The real peak was 285 mg/dL.

## 12:00–14:30 · Forecast tab: track record
- The glucose chart shows CGM, the forecast cone (80% conformal interval), the physics-only line, and **dashed lines for what the twin predicted 1 h and 2 h ago**. "We show our track record on screen."
- Bottom strip: steps and sleep stages. Below that: sleep architecture, daily time in range with Navratri days marked, HRV and inferred stress.

## 14:30–17:30 · What-If Lab and ghost twin
1. Open **What-If Lab**. The 3D view splits into two bodies: **current habits (left)** and **with the prescribed plan (right, green)**. Both are time-lapsed through the next 24 h, and the chart cursor moves in sync.
2. Drag the sliders (walk after meals, low-GI swap, dinner earlier, sleep, metformin). The twin re-simulates instantly.
3. Click **Find the best plan**: 54 simulated tomorrows fan out on the chart, and the recommended plan is ranked by benefit per unit of effort.
4. Read the KPIs: time in range, peak drop, time above 250, **projected HbA1c in 90 days**.

## 17:30–19:30 · AI insights and records
- **AI clinical brief**: patterns mined from the patient's own data (biggest spike food, fasting effect, adherence, dawn phenomenon).
- **Personal glycaemic index**: every Indian food simulated on *this* patient's physiology.
- **Twin track record**: MAE and interval coverage over the last 24 h.
- **Adaptive twin**: daily Bayesian re-calibration of insulin sensitivity and hepatic set-point.
- **Records (FHIR)**: the input bundle, then *Export twin prediction as FHIR* (RiskAssessment, forecast Observations and a Communication). It is interoperable with ABDM-style systems.

## 19:30–21:30 · Model card and results (slides 7–8)
- Held-out results versus 4 baselines: 2-h RMSE 27.6 mg/dL against 52.8 for persistence; Clarke A+B 99.0%; spike AUROC 0.905; median warning 105 min.
- **Why hybrid**: with 2 training patients it is 18% more accurate than ML-only; the physics twin alone works with zero training patients; under the same alert policy it has 26% fewer false alarms and higher precision (82% vs 79%). It also explains and simulates, which a black box cannot.
- Calibration: conformal intervals around 78% for a nominal 80%; the reliability diagram is close to the diagonal (ECE about 0.05).
- Twin personalisation: correlation with hidden physiology rises from the EHR prior to the calibrated twin (S<sub>I</sub> 0.76 → 0.89).

## 21:30–22:30 · Impact and close (slides 12–13)
- Clinicians triage by foresight. Patients get small, culturally fitting, twin-tested nudges. The health system gets FHIR/ABHA readiness and CPU-only deployment for PHCs.
- Roadmap: validation on open CGM datasets, a silent-mode clinic pilot, hypertension and cardiovascular twins on the same engine.
- Close: *"Prediction is useful. Simulation changes care. Sanjeevani Twin: see the spike, know the cause, test the fix."*

> Tip: if you run short of 20 minutes, run the **Guided tour** (button at top right) once on camera and narrate over it.
> Also open `sanjeevani/physiology.py` and `sanjeevani/twin/core.py` and walk through the equations and calibration.
