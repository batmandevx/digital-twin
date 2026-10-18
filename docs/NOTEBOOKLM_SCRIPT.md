# Sanjeevani Twin: NotebookLM source script

> **How to use this file.** Upload it to NotebookLM as a source, together with `README.md`,
> `docs/Presentation.pdf` and `docs/Architecture_Diagram.pdf`. Then open **Audio Overview → Customize**
> (or **Video Overview → Customize**) and paste the steering prompt from Part 1.

---

## Part 1: Steering prompt (paste into NotebookLM "Customize")

```
Audience: the expert jury of the Happiest Health Digital Twin Challenge 2026: clinicians, data
scientists and health-system leaders. Make it a compelling, story-driven deep dive into
"Sanjeevani Twin".

Open with the story of Rajesh, 51, from Lucknow, on Navratri 2026: his twin warns of a glucose
spike 90 minutes before it happens. Then explain clearly what makes this a true digital twin and
not just a predictor: a personalised physiology model that can be simulated, combined with AI.

Cover, in this order: the problem in India; how the twin is built from EHR plus wearables; the
three verbs Predict, Explain, Simulate; the 3D dashboard and the ghost twin; the results versus
baselines; why the hybrid beats pure machine learning; honesty of the evaluation; India-specific
design; impact and roadmap.

Use the exact numbers from the sources. Do not invent statistics, partners or clinical trials.
Say clearly that all patient data is synthetic and that this is a research prototype, not a
medical device. Have one host play a sceptical judge who asks hard questions (synthetic data,
overfitting, alert fatigue, deployment) and let the other answer from the sources. End with the
line: "Prediction is useful. Simulation changes care."
```

---

## Part 2: The story (main source narrative)

### The cold open: 16 October 2026, 12:15 pm, Lucknow
It is the sixth day of Navratri. Rajesh Kumar Verma is 51, vegetarian, and has lived with Type 2
Diabetes for nearly seven years. He takes 1,000 mg of metformin a day, and his HbA1c is 7.2%. Like
millions of families, he is observing the full nine-day Navratri fast. His glucose right now is
151 mg/dL, comfortably in range. Nothing looks wrong.

But his **digital twin**, a living mathematical copy of his physiology, has noticed something.
This morning's meal log contains fasting foods: a fruit plate and, yesterday, kuttu puri. The twin
concludes that today is a fasting day and that lunch will probably be **sabudana khichdi**, one of
the highest-glycaemic foods in the Indian diet. It simulates Rajesh's body forward in time.

The verdict: an **80% probability that his glucose will cross 180 mg/dL in about 1 hour 30
minutes**, peaking around **236 mg/dL**. That is a 90-minute warning before anything visible
happens.

The twin also explains *why*. The meal's glycaemic load adds about +28 mg/dL to the peak, and
sitting still after eating adds about +5. Then it tests fixes on the virtual Rajesh before asking
the real one to change anything. It sends a nudge in English and Hindi:

> "आज दोपहर के भोजन में फल लें। शुगर लगभग 79 mg/dL कम बढ़ेगा।"
> *"Have fruit for lunch today. Your sugar will rise about 79 mg/dL less."*

What actually happened? Rajesh's real CGM peaked at **285 mg/dL**. The warning was real.
This is **Sanjeevani Twin**.

### The name
*Sanjeevani* (pronounced sun-JEE-vuh-nee) is the life-restoring herb of the Ramayana. Hanuman
carried an entire mountain to bring it in time. Our twin's job is the same: to bring the right
information *in time*.

### The problem
- India has about **101 million people with diabetes and 136 million with prediabetes**
  (ICMR-INDIAB study, *Lancet Diabetes & Endocrinology*, 2023).
- Care is **reactive**. HbA1c is measured every three months, while the post-meal spikes that drive
  complications happen every day, between visits, and nobody sees them.
- Wearables and continuous glucose monitors now produce streams of data. But doctors receive
  **numbers, not foresight**.
- Indian physiology and lifestyle break tools built elsewhere:
  - the **"thin-fat" South-Asian phenotype**: high insulin resistance even at a normal BMI
  - rice- and roti-heavy thalis and late dinners
  - **festival fasting**, where "fasting" foods like sabudana spike harder than normal meals
  - real-world gaps in medication adherence

### The core idea: a twin, not a predictor
A predictor gives you a number. A **digital twin is a model of the person that you can simulate**:
you can ask it "what if?".

Sanjeevani has a mechanistic heart: an extended **Bergman minimal model**, a well-established
mathematical description of how glucose, insulin, the gut, exercise, the body clock, sleep and
stress interact. We personalise it for every patient.

**Step 1: the health record sets the starting point.**
The twin reads a standard **FHIR R4** health record:
- BMI and waist circumference (weighted for South-Asian adiposity) give a starting estimate of
  insulin sensitivity.
- Diabetes duration and the **TCF7L2 rs7903146 gene variant**, the strongest known genetic risk
  factor for Type 2 Diabetes, give a starting estimate of how well the pancreas secretes insulin.
- Fasting glucose sets the liver's baseline.

**Step 2: wearables refine it.**
- **Onboarding:** over the first 3 days of CGM data, the twin calibrates itself to the patient,
  in about a second per patient on an ordinary laptop.
- **Live sync:** every 5 minutes, new CGM readings keep the twin in step with the real body.
- **Nightly re-calibration:** every night it re-estimates insulin sensitivity and the liver
  set-point. It also learns the patient's own **dawn phenomenon**, the early-morning glucose rise.

**Step 3: wearables become physiology.**
- Sleep stages become sleep debt, which lowers insulin sensitivity.
- Heart-rate variability and heart rate become an estimate of stress, which raises the liver's
  glucose output.
- Steps become muscle glucose uptake.
- Missed metformin doses become a higher liver set-point.

**Step 4: AI corrects what physics misses.**
Gradient-boosting models learn the twin's remaining errors, using 52 features that each depend
only on data available at the moment of prediction. The outputs:
- glucose forecasts at 30, 60 and 120 minutes, with **80% prediction intervals** calibrated by
  conformal prediction
- a calibrated probability of a new spike above 180 mg/dL in the next 2 hours

### Three verbs: Predict, Explain, Simulate
1. **Predict.** A 2-hour spike warning with a countdown, a forecast cone and an honest uncertainty band.
2. **Explain.** For every warning, the twin re-runs itself 32 times, switching each possible
   cause on and off, and computes exact **Shapley values**. The causes are meal glycaemic load,
   post-meal inactivity, sleep debt, stress and a missed dose. Clinicians see *why*, not just *what*.
3. **Simulate.** The **What-If Lab** lets a doctor "prescribe a simulation": a post-meal walk, a
   low-GI swap to millets or brown rice, an earlier dinner, more sleep, or a different metformin
   dose. The twin re-simulates the next 24 hours instantly. **"Find the best plan"** searches 54
   possible tomorrows at once and ranks them by benefit per unit of effort. For Rajesh, the best
   plan was a 20-minute walk after lunch and dinner plus a low-GI swap. It **lowered his peak by
   96 mg/dL**, cut hyperglycaemia by **72%**, and projected his HbA1c to fall from **7.2% to about
   7.1%** over 90 days if he sustained it.

### The experience: a 3D living twin
- **The body.** A holographic human body made of about 30,000 particles assembles itself on screen.
- **The organs** glow from the twin's real internal state:
  - pancreas: insulin output
  - liver: glucose output
  - gut: carbohydrates being absorbed
  - heart: beats at the measured heart rate, sending out shockwaves
  - brain: stress
  - muscles: activity
- **The bloodstream** is coloured by glucose: teal in range, amber and red when high.
- **The 3D glucose ribbon** spirals around the body showing the last 24 hours. Spikes literally
  bulge outward, and the 2-hour forecast continues as glowing dots.
- **The DNA helix** shows the patient's TCF7L2 genotype.
- **Data streams** from the health record, CGM, heart rate, HRV, sleep and steps visibly flow into
  the organs they inform. This is the fusion of static and dynamic data, made visible.
- **Click any organ** and the camera flies in to show that organ's personalised parameters.
- **The ghost twin.** In the What-If Lab the screen splits into two bodies: tomorrow on *current
  habits* and tomorrow *with the plan*. Both play as a 24-hour time-lapse. At 2:20 pm on Navratri,
  Rajesh-on-current-habits sits at **273 mg/dL**; Rajesh-with-the-plan sits at **212**. You don't
  have to read a chart to understand that.
- **The rest of the dashboard:**
  - **Clinic triage:** 40 live twins ranked by predicted risk and time to event
  - **AI insights:** a *personal glycaemic index* that simulates all 28 Indian foods on this
    patient's own physiology, plus a clinical brief mined from 14 days of data
  - **Track record:** the twin shows what it predicted 1 and 2 hours ago next to what actually
    happened
  - **FHIR export** of every prediction
  - a **guided tour** for judges

### The results (10 held-out patients, about 108 patient-days, never seen in training)

| Model | 2-hour error (RMSE) | Spike AUROC | False alerts per day |
|---|---|---|---|
| Assume no change (persistence) | 52.8 mg/dL | n/a | n/a |
| Physics twin alone | 34.4 mg/dL | 0.80 | 0.85 |
| Machine learning alone (no twin) | 28.1 mg/dL | 0.896 | 0.88 |
| **Sanjeevani hybrid** | **27.6 mg/dL** | **0.905** | **0.65** |

- **48% lower** 2-hour error than assuming glucose stays the same.
- **99.0%** of 2-hour forecasts fall in the clinically safe zones A and B of the Clarke Error Grid.
- Median warning of **105 minutes** before real spikes, across 457 real excursion events.
- The 80% prediction intervals actually cover about **76–78%** of outcomes, and the spike
  probabilities are well calibrated.

### Why hybrid beats pure machine learning
1. **Data efficiency.** Trained on just **2 patients**, the hybrid's 2-hour error is **31.3 vs
   38.1 mg/dL** for pure ML, 18% better. With **zero** training patients, the calibrated physics
   twin alone already scores 34.4. A new clinic can start on day one.
2. **Fewer false alarms.** Under the same alert policy (the most sensitive threshold that still
   keeps precision at or above 75%), the hybrid produces **26% fewer false alarms** (0.65 vs 0.88
   per patient-day) with **higher precision (82% vs 79%)**. Alert fatigue is what kills clinical
   tools.
3. **The twin is the backbone.** Remove the twin's forecasts and the classifier's AUROC drops by
   0.154, about eight times more than removing any single wearable signal.
4. **Only a twin can explain and simulate.** A black box cannot answer "what if he walks after lunch?"

### Personalisation is real, not decoration
Correlation between the twin's estimates and each patient's hidden true physiology, before and
after calibration:

| Parameter | From the health record alone | After calibration |
|---|---|---|
| Insulin sensitivity | 0.76 | **0.89** |
| Beta-cell (pancreas) function | 0.65 | **0.83** |
| Basal glucose | 0.86 | **0.98** |

### Honest evaluation (the part judges should trust)
- **All data is synthetic.** No real patient data is used, in line with the DPDP Act 2023 and
  HIPAA. The cohort is 40 synthetic Indian adults with Type 2 Diabetes, followed for 14 days
  (5–18 October 2026, spanning Navratri), with four regional cuisines, late dinners, work stress
  and fasting.
- **The simulated "real world" contains things the twin is never told about:**
  - the dawn phenomenon
  - unlogged snacks
  - errors of about ±22% in carb estimates
  - day-to-day drift in insulin sensitivity
  - hidden stress
  - CGM lag, noise and dropouts

  So the test is not circular.
- **Patient-level split:** 24 patients for training, 6 for calibration and 10 for testing. All six
  demo patients are test patients.
- **An automated test** corrupts every data point after the prediction time, at daytime and
  mid-sleep moments, and proves that no input to the model changes. The model never peeks into
  the future.
- **Real-world performance will be lower than on simulated data.** The next step is validation on
  open real CGM datasets such as PhysioNet's BIG IDEAs dataset, followed by a silent-mode pilot in
  a diabetes clinic.

### Built for India
- A 28-food Indian library with glycaemic splits and Hindi names: idli, poha, rice-dal thali,
  biryani, millet roti, sabudana, kuttu, chai-biscuit, mithai and more.
- A **festival-aware twin** that detects Navratri fasting from the meal log.
- Nudges in Hindi and English.
- **FHIR R4** in and out, with ABHA-style identifiers, ready for the Ayushman Bharat Digital Mission.
- Runs **CPU-only on a laptop**: no GPU, no cloud, four Python libraries. The whole pipeline
  rebuilds in a few minutes, and a prediction takes milliseconds. That makes it suitable for
  primary health centres.

### Impact
- **Clinicians** triage by foresight instead of hindsight.
- **Patients** get small, culturally fitting, twin-tested advice in their own language.
- **Health systems** get interoperable, low-cost software.
- **Roadmap:**
  - validation on real CGM data
  - a clinic pilot
  - hypertension and cardiovascular-risk twins on the same engine
  - voice nudges in regional languages through ASHA workers

### Closing line
**"Prediction is useful. Simulation changes care. Sanjeevani Twin: see the spike, know the
cause, test the fix."**

---

## Part 3: Hard questions a sceptical judge will ask (with answers)

**"It's all synthetic data. Why should I believe it?"**
The challenge rules require synthetic or anonymised data. We made the simulated world deliberately
harder than our model: it contains effects the twin is never told about, so the numbers are not
circular. We are explicit that real-world accuracy will be lower. The architecture also accepts
Synthea health records and standard CGM exports, so real-data validation is the next step rather
than a rebuild.

**"Isn't this overfitted?"**
Testing is on 10 patients the models never saw. Alert thresholds and intervals were tuned on 6
separate calibration patients. An automated test proves no future data leaks into any prediction.

**"Won't doctors drown in alerts?"**
The alert policy is clinical: the most sensitive threshold that still keeps precision at 75% or
above. The hybrid gives about 0.65 false alerts per patient per day, 26% fewer than pure ML.

**"Why not just use deep learning?"**
Deep learning needs large datasets and cannot simulate "what if". Our hybrid works with very few
patients and can explain and test interventions. It runs on a laptop CPU.

**"How would this actually be deployed?"**
CGM and fitness-band data come in alongside a FHIR health record. The twin calibrates in 3 days.
Predictions go out as FHIR RiskAssessment resources, and nudges go to the patient's phone. It is
decision support only: it never doses insulin and is not a medical device.

---

## Part 4: Pronunciation and glossary for the hosts
- **Sanjeevani**: sun-JEE-vuh-nee
- **Sabudana**: saa-boo-DAA-na (tapioca pearls, a common fasting food)
- **Kuttu**: KOO-too (buckwheat flour)
- **Navratri**: nuv-RAA-tree (a nine-day Hindu festival, often with fasting)
- **CGM**: continuous glucose monitor, a skin sensor reading glucose every 5 minutes
- **HbA1c**: a three-month average glucose marker
- **HRV**: heart-rate variability, a stress and recovery signal from wearables
- **FHIR**: pronounced "fire", the global standard for health-record data
- **ABHA**: the Ayushman Bharat Health Account, India's digital health ID
- **Shapley values**: a fair way to split credit for an outcome among several causes
- **Conformal prediction**: a method that makes uncertainty bands statistically honest
- **Clarke Error Grid**: the standard clinical chart for judging whether a glucose estimate is
  safe to act on
