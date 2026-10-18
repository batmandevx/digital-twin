# Sanjeevani Twin: NotebookLM source script (v2)

> **How to use this file**
> 1. In NotebookLM, create a notebook and add these sources: **this file**, `README.md`,
>    `docs/Presentation.pdf` and `docs/Architecture_Diagram.pdf`.
>    You can add the GitHub repo URL too: https://github.com/batmandevx/digital-twin
> 2. Open **Audio Overview → Customize**, choose the format and **Longer** length, and paste
>    one steering prompt from Part 1.
> 3. Generate, listen, and regenerate if a host misstates a number. Part 8 lists what must never
>    be said.

---

## Part 1: Steering prompts (pick one and paste into "Customize")

### A. Deep Dive for the jury (recommended)
```
You are presenting "Sanjeevani Twin" to the expert jury of the Happiest Health Digital Twin
Challenge 2026: diabetologists, data scientists and health-system leaders.

Open cold with the 12:15 pm Navratri story of Rajesh from Lucknow, including the honest detail that
the spike came 20 minutes earlier than forecast but stayed inside the twin's warning band. Then
follow the episode blueprint in the source: the problem, why a twin and not a predictor, how it
is built, Predict / Explain / Simulate, the ghost twin, results, why hybrid beats pure AI, honesty
of the evaluation, India-first design, and impact.

One host is a sharp, sceptical judge who presses on synthetic data, overfitting, alert fatigue and
deployment. The other answers only from the sources. Use the soundbites and analogies provided.
Quote numbers exactly. Never invent statistics, partners, trials or real patients. State that all
data is synthetic and that this is a research prototype. End with: "Prediction is useful.
Simulation changes care."
```

### B. Debate format: "Can AI alone manage diabetes?"
```
Debate: "Is a black-box AI enough to manage Type 2 Diabetes, or do we need a digital twin?"
Host 1 argues for pure machine learning. Host 2 argues for Sanjeevani Twin's hybrid of a
personalised physiology model plus AI. Use only evidence from the sources:
- data efficiency: 31.3 vs 38.1 mg/dL with 2 training patients
- false alarms: 0.65 vs 0.88 per day
- explainability through Shapley attribution
- what-if simulation and the ghost twin
Host 1 must concede the points the data supports, but should fairly raise the limits: synthetic
data and the need for real-world validation. Both hosts state that the data is synthetic. Close
with "Prediction is useful. Simulation changes care."
```

### C. Video Overview (visual explainer)
```
Make a visual explainer of Sanjeevani Twin for a hackathon jury. Structure it as:
1. Hook: a 90-minute spike warning on Navratri.
2. The problem in India.
3. The twin, built from health records plus wearables.
4. Predict, Explain, Simulate.
5. The 3D living twin and the ghost twin, showing two futures side by side.
6. Results table versus baselines.
7. Why hybrid beats pure AI.
8. Built for India.
9. Closing line.
Use short on-screen phrases and the exact numbers from the sources. Mention that the data is
synthetic and the system is a research prototype.
```

### D. Short fallback (if the box limits length)
```
Jury deep dive on Sanjeevani Twin. Open with Rajesh's Navratri spike warning. Explain twin vs
predictor, Predict/Explain/Simulate, ghost twin, results, why hybrid beats AI, honesty (synthetic
data), India-first design. Sceptical-judge host. Exact numbers only. End: "Prediction is useful.
Simulation changes care."
```

---

## Part 2: Episode blueprint (about 20–25 minutes; hosts should follow this order)

| # | Segment | Target | The one thing listeners must remember |
|---|---|---|---|
| 1 | Cold open: Rajesh, Navratri, 12:15 pm | 2 min | The twin saw the spike before his body did |
| 2 | The problem: diabetes care is reactive | 2 min | Doctors get numbers, not foresight |
| 3 | Twin vs predictor | 2 min | You can ask a twin "what if?" |
| 4 | How the twin is built | 4 min | Health record → personal physiology → synced every 5 minutes → re-tuned nightly |
| 5 | Predict · Explain · Simulate | 4 min | Warning, reason, fix, in that order |
| 6 | The 3D experience and ghost twin | 3 min | 273 vs 212: two futures side by side |
| 7 | Results | 3 min | 48% lower error; 105-minute median warning |
| 8 | Why hybrid beats pure AI | 2 min | Works with 2 patients; 26% fewer false alarms |
| 9 | The sceptical-judge round | 3 min | Synthetic data, handled honestly |
| 10 | Built for India and impact | 2 min | Festival-aware, Hindi, FHIR/ABHA, CPU-only |
| 11 | Close | 30 s | "Prediction is useful. Simulation changes care." |

---

## Part 3: The story (main narrative source)

### 1. Cold open: Friday 16 October 2026, 12:15 pm, Lucknow
It's the sixth day of Navratri. Rajesh Kumar Verma is 51 and vegetarian. He has lived with Type 2
Diabetes for nearly seven years and takes 1,000 mg of metformin a day; his HbA1c is 7.2%. Like
millions of families, he is keeping the full nine-day fast. His glucose is **151 mg/dL**, in range.
He feels fine. Any alarm built on a glucose threshold would stay silent.

But his **digital twin**, a living mathematical copy of his metabolism that has been running
alongside him for eleven days, has noticed something. Yesterday's dinner was kuttu puri and this
morning's breakfast was a fruit plate. These are fasting foods. The twin infers that today is a
fasting day and that lunch will probably be **sabudana khichdi**, tapioca pearls that are among the
fastest-absorbing carbohydrates on an Indian plate. It runs Rajesh's body forward in time.

**The verdict: an 80% chance his glucose will cross 180 mg/dL, in about an hour and a half, with a
likely peak around 236 and a warning band reaching up to about 309.**

The twin then asks *why*. It re-runs Rajesh 32 times, switching each possible cause on and off.
The meal's glycaemic load adds about +28 mg/dL to the peak, and sitting still after eating adds
about +5.

Then it tests fixes on the *virtual* Rajesh before asking the *real* one to change anything, and
sends one message in English and Hindi:

> "आज दोपहर के भोजन में फल लें। शुगर लगभग 79 mg/dL कम बढ़ेगा।"
> *"Have fruit for lunch today. Your sugar will rise about 79 mg/dL less."*

**What actually happened?** Rajesh crossed 180 at 1:25 pm, about **70 minutes** later and 20
minutes sooner than the twin's estimate. His glucose peaked at **285 mg/dL**, higher than the
twin's central guess but **inside its warning band**. The twin was not perfect. It was *early
enough, honest about its uncertainty, and right about the danger*. That is what a clinician needs.

This is **Sanjeevani Twin**.

> *Soundbite:* "His glucose was fine. His future wasn't. The twin could see the difference."

### 2. Why the name
*Sanjeevani* (sun-JEE-vuh-nee) is the life-restoring herb of the Ramayana. Hanuman carried a whole
mountain to bring it to Lakshmana before dawn, because the herb only mattered if it arrived in
time. Sanjeevani Twin is built around the same idea: **the right information, in time**.

### 3. The problem: care that arrives too late
- India has about **101 million people with diabetes and about 136 million with prediabetes**
  (ICMR-INDIAB study, *Lancet Diabetes & Endocrinology*, 2023).
- Care is **reactive**. HbA1c, the main measure, is checked roughly every three months. It is an
  average, and averages hide the daily post-meal spikes that happen between visits, unseen.
- Continuous glucose monitors and fitness bands now stream data every few minutes. But a doctor
  with dozens of patients receives **numbers, not foresight**: a graph of what already happened.
- Indian bodies and Indian lives break tools designed elsewhere:
  - the **"thin-fat" South-Asian phenotype**: high insulin resistance even at a normal BMI
  - **rice-heavy thalis and late dinners**
  - **festival fasting**, where "fasting" foods can spike harder than an ordinary meal
  - gaps in medication adherence

> *Soundbite:* "Diabetes care in India is driving by looking in the rear-view mirror."

### 4. A twin, not a predictor
A **predictor** answers one question: what number comes next? A **digital twin** is a *model of
the person* that you can **simulate**. You can ask it questions:
- "What if he walks for 15 minutes after lunch?"
- "What if dinner is an hour earlier?"
- "What if he sleeps seven and a half hours tonight?"

> *Analogy:* "A predictor is a weather forecast. A digital twin is a flight simulator. You don't
> just learn there will be turbulence; you practise flying through it."

### 5. How the twin is built, in four steps
**Step 1: the health record sets the starting point.**
The twin reads a standard **FHIR** record ("fire", the global health-data standard), with codes
for labs, diagnoses and medicines.
- BMI and waist size give a first estimate of **insulin sensitivity**. Waist is weighted more for
  South-Asian bodies.
- Years with diabetes and the **TCF7L2 gene variant**, the strongest known common genetic risk
  factor for Type 2 Diabetes, give a first estimate of **how well the pancreas releases insulin**.
- Fasting glucose sets the liver's baseline.

**Step 2: three days of CGM data personalise it.**
In about a second per patient, on an ordinary laptop, the twin tunes its physiology to the
patient's actual glucose curves. Evidence that this personalisation is real: the twin's estimates
of each patient's hidden physiology correlate far better after tuning.

| What the twin estimates | From the record alone | After 3-day tuning |
|---|---|---|
| Insulin sensitivity | 0.76 | **0.89** |
| Pancreas (beta-cell) function | 0.65 | **0.83** |
| Liver baseline glucose | 0.86 | **0.98** |

**Step 3: it stays alive.**
- Every **5 minutes**, new CGM readings nudge the twin back in sync with the real body.
- **Every night**, it re-estimates insulin sensitivity and the liver set-point from the previous
  day, so it drifts with the person.
- It also **learns each patient's dawn phenomenon**, the early-morning rise in glucose.

**Step 4: wearables become physiology, and AI covers the rest.**
- Sleep stages become sleep debt, which lowers insulin sensitivity.
- Heart-rate variability and heart rate become an estimate of stress, which pushes the liver to
  release glucose.
- Steps become muscle glucose uptake.
- Missed metformin doses raise the liver's set-point.

A layer of machine learning then learns the twin's remaining errors, using 52 inputs that depend
only on information available at that moment. It produces glucose forecasts at 30, 60 and 120
minutes with honest 80% ranges, and a calibrated probability of a new spike in the next two hours.

> *Analogy:* "The physics is the skeleton. The AI is the muscle. Physics alone is stiff, and AI
> alone has no bones."

### 6. Predict · Explain · Simulate
1. **Predict.** A two-hour spike warning with a countdown, a forecast cone and an honest
   uncertainty band.
2. **Explain.** For every warning, the twin re-runs itself 32 times, switching each cause on and
   off (meal load, post-meal inactivity, sleep debt, stress, missed dose), and splits the blame
   fairly using **Shapley values**. The doctor sees *why*, not just *what*.
3. **Simulate.** In the **What-If Lab**, a doctor "prescribes a simulation":
   - a post-meal walk, or a low-GI swap to millets or brown rice
   - an earlier dinner, more sleep, or a different metformin dose

   The twin replays the next 24 hours instantly. **"Find the best plan"** searches **54 possible
   tomorrows at once** and ranks them by benefit per unit of effort. For Rajesh, the winning plan
   was a 20-minute walk after lunch and dinner plus a low-GI swap. It lowered his highest peak
   from about 313 to about 217 mg/dL (**96 mg/dL lower**) and cut time spent high by **72%**. If he
   kept it up, his HbA1c would project from **7.2% toward about 7.1%** in 90 days.

> *Soundbite:* "See the spike. Know the cause. Test the fix."

### 7. The experience: a living, 3D twin
- **The body.** A holographic human figure made of about 30,000 points of light assembles itself on
  screen. Its organs glow from the twin's real internal state:
  - pancreas: insulin output
  - liver: glucose output
  - gut: carbohydrates being absorbed
  - heart: beats at the measured heart rate, sending out shockwaves
  - brain: stress
  - leg muscles: activity
- **The bloodstream** is coloured by glucose: teal when safe, amber and red when high.
- **A 3D glucose ribbon** spirals around the body showing the last 24 hours. Spikes physically bulge
  outward, and the forecast continues as glowing dots.
- **A DNA helix** shows the patient's TCF7L2 genotype.
- **Six data streams** (health record, CGM, heart rate, HRV, sleep, steps) visibly flow into the
  organs they inform. The challenge's "fusion of static and dynamic data" becomes something you
  can watch.
- **Click an organ** and the camera flies inside it to show that organ's personalised numbers.
- **The ghost twin.** Open the What-If Lab and the scene splits into two Rajeshes: tomorrow on
  *current habits* and tomorrow *with the plan*, time-lapsed side by side. At 2:20 pm, the first
  sits at **273 mg/dL**; the plan's twin sits at **212**. No chart reading required.
- **Clinic triage** ranks 40 live twins by predicted risk and time to event. At 12:15 that
  Navratri lunchtime, **11 of the 40** had a predicted spike.
- **AI insights**:
  - a **personal glycaemic index** that simulates all 28 Indian foods on *this* patient's body,
    not a population table
  - a clinical brief mined from 14 days of data
  - the twin's own **track record**: what it predicted 1 and 2 hours ago, plotted against what
    really happened
- **FHIR export** of every prediction, plus a one-click **guided tour** for judges.

> *Soundbite:* "Two futures, side by side, before the patient changes anything."

### 8. The results (10 patients the system had never seen, about 108 patient-days)

| Approach | Error at 2 hours (RMSE) | Spike detection (AUROC) | False alarms per patient per day |
|---|---|---|---|
| Assume nothing changes | 52.8 mg/dL | n/a | n/a |
| Physics twin alone | 34.4 mg/dL | 0.80 | 0.85 |
| Machine learning alone | 28.1 mg/dL | 0.896 | 0.88 |
| **Sanjeevani hybrid** | **27.6 mg/dL** | **0.905** | **0.65** |

- **48% lower error** at two hours than assuming glucose stays where it is.
- **99.0%** of two-hour forecasts land in the clinically safe zones A and B of the Clarke Error Grid.
- A median warning of **105 minutes** before real spikes, measured across 457 real excursions.
- **Honest uncertainty:** the 80% ranges actually contain about 76–78% of outcomes, and the risk
  percentages are well calibrated. When it says 80%, it means roughly 80%.

### 9. Why the hybrid beats pure AI (the scientific heart)
1. **It learns from very little data.** Trained on just **2 patients**, the hybrid's two-hour error
   is **31.3 mg/dL vs 38.1** for pure ML, 18% better. With **zero** training patients, the tuned
   physics twin alone already scores 34.4. A new clinic can start on day one.
2. **It cries wolf less.** Both systems used the same clinical alert rule: be as sensitive as
   possible while keeping at least 75% of alerts correct. Under that rule the hybrid produced
   **26% fewer false alarms** (0.65 vs 0.88 per patient per day) and its alerts were more often
   right (82% vs 79%). Alert fatigue is what kills clinical tools.
3. **The twin is the backbone.** Removing the twin's forecasts hurts spike detection about eight
   times more than removing any single wearable signal.
4. **Only a twin can explain and simulate.** A black box cannot answer "what if he walks after lunch?"

### 10. Honest by design
- **All data is synthetic, as the challenge rules require.** No real patients are involved. The
  cohort is 40 synthetic Indian adults with Type 2 Diabetes followed for 14 days spanning Navratri
  2026, across four regional cuisines, with late dinners, work stress and fasting.
- **The simulated world is harder than the twin.** It includes things the twin is never told
  about:
  - the dawn phenomenon and unlogged snacks
  - errors of about ±22% in carb estimates
  - day-to-day drift in insulin sensitivity and hidden stress
  - sensor lag, noise and dropouts

  So the test is not the model grading itself.
- **Strict separation:** 24 patients for training, 6 for tuning alert thresholds and uncertainty,
  and 10 for testing. Every demo patient, Rajesh included, is a test patient.
- **A built-in leak detector:** an automated test corrupts all data after the moment of prediction,
  during the day and in the middle of the night, and proves that nothing the model sees changes.
  It cannot peek into the future.
- **A stated limit:** real-world accuracy will be lower than on simulated data. The next step is
  validation on open real-world CGM datasets such as PhysioNet's BIG IDEAs, then a silent-mode
  clinic pilot.

> *Soundbite:* "We built the test to be harder than the model, and we show our misses on screen."

### 11. Built for India
- A **28-food Indian library** with Hindi names and glycaemic splits: idli, poha, rice-dal thali,
  biryani, millet roti, chole bhature, sabudana, kuttu, chai-biscuit, mithai and more.
- A **festival-aware twin** that recognises Navratri fasting from the meal log and anticipates
  fasting meals.
- **Nudges in Hindi and English**, each tested on the twin before it is sent.
- **FHIR in and out**, with ABHA-style health IDs, ready for the Ayushman Bharat Digital Mission.
- **Runs on a laptop CPU**: no GPU, no cloud, four Python libraries. Rebuilding everything takes a
  few minutes, and a prediction takes milliseconds. That suits primary health centres.

### 12. Impact
- **Clinicians** triage by foresight instead of hindsight.
- **Patients** get one small, specific, culturally fitting action, in their language, at the moment
  it matters.
- **Health systems** get interoperable, low-cost software.
- **Next:**
  - real-world validation and a clinic pilot
  - hypertension and cardiovascular-risk twins on the same engine
  - voice nudges in regional languages through ASHA community health workers

### 13. Close
> **"Prediction is useful. Simulation changes care. Sanjeevani Twin: see the spike, know the
> cause, test the fix."**

---

## Part 4: Soundbites and analogies (for the hosts to reuse)
- "His glucose was fine. His future wasn't."
- "Doctors get numbers, not foresight."
- "A predictor is a weather forecast; a digital twin is a flight simulator."
- "The physics is the skeleton; the AI is the muscle."
- "Warning, reason, fix, in that order."
- "Two futures, side by side, before the patient changes anything."
- "It works with two patients' worth of data, because it already understands physiology."
- "Fewer alarms, more of them right."
- "We show our misses on screen."
- "Like the herb in the Ramayana: the right medicine, in time."

## Part 5: Numbers card (say them exactly like this)
| Fact | Say it as |
|---|---|
| Rajesh's warning | "80% risk, about 90 minutes ahead; actual crossing at 70 minutes; real peak 285, inside the warning band" |
| Two-hour accuracy | "27.6 mg/dL error, 48% lower than assuming no change" |
| Safety grid | "99% of two-hour forecasts in the clinically safe zones" |
| Warning time | "a median of 105 minutes' warning across 457 real spikes" |
| Detection | "AUROC 0.905" ("about 0.9 out of 1") |
| False alarms | "0.65 a day vs 0.88 for pure AI, 26% fewer" |
| Small data | "with two training patients, 31.3 vs 38.1, 18% better" |
| Best plan for Rajesh | "peak down 96 mg/dL, 72% less time high" |
| Ghost twin | "273 on current habits vs 212 with the plan, at 2:20 pm" |
| Scale of problem | "about 101 million Indians with diabetes, 136 million with prediabetes (ICMR-INDIAB 2023)" |
| Cohort | "40 synthetic Indian patients, 14 days, 10 held out for testing" |

## Part 6: The sceptical-judge round (questions and answers)
**"It's all synthetic. Why should I believe any of this?"**
The rules require synthetic or anonymised data. We made the simulated world harder than our model,
with effects the twin is never told about, so the score is not self-graded. We say plainly that
real-world accuracy will be lower. The system already accepts standard FHIR records (including
Synthea) and standard wearable exports, so real-data validation is the next step, not a rebuild.

**"Isn't it just overfitting?"**
It is tested on 10 patients it never saw. Thresholds and uncertainty were tuned on 6 different
patients. An automated test proves no future data leaks into any prediction.

**"A CGM already has a high-glucose alarm. Why do I need this?"**
A CGM alarm fires when you're *already* high. Sanjeevani warns about 105 minutes earlier (median),
explains the cause, and tests a fix. That is the difference between a smoke alarm and a fire
marshal.

**"Won't doctors drown in alerts?"**
The alert rule keeps at least 75% of alerts correct. The hybrid averages about 0.65 false alerts
per patient per day, 26% fewer than pure AI, and clinic triage ranks patients so the most urgent
appear first.

**"Why not just use deep learning?"**
Deep learning needs large datasets, struggles to explain itself and cannot simulate "what if".
This hybrid works with very little data, explains every warning and runs on a laptop.

**"How would a hospital actually use it?"**
CGM and fitness-band data stream in next to a FHIR health record, and the twin tunes itself in 3
days. Predictions go out as FHIR resources, nudges go to the patient's phone, and the doctor sees
the triage dashboard. It is decision support only: it never doses insulin and is not a medical
device.

**"What about privacy?"**
No real data was used. The design follows interoperability standards (FHIR, ABHA-style IDs) and
runs locally on clinic hardware, without sending data to the cloud.

## Part 7: Sample two-host dialogue (tone and pacing model; about 4 minutes)

**Host A:** It's 12:15 on a Friday in Lucknow, the sixth day of Navratri. A 51-year-old man named
Rajesh has a glucose reading of 151. Perfectly fine.

**Host B:** And any normal alarm stays quiet. Nothing to see.

**Host A:** Except his *digital twin* sees something. It noticed fruit for breakfast and kuttu puri
last night, so it concluded he's fasting, and that lunch is probably sabudana khichdi.

**Host B:** The tapioca pearls. Delicious, and basically pure fast-acting carbohydrate.

**Host A:** So it simulates his body forward and says: 80% chance you cross 180 in about 90 minutes.

**Host B:** Okay, but I'm the judge here. Did it actually happen?

**Host A:** It did, and I like that the team is honest about the details. He crossed at about 70
minutes, so 20 minutes earlier than the twin's central estimate. He peaked at 285, higher than its
best guess of 236, but *inside* the warning band, which went up to about 309.

**Host B:** So it wasn't perfect, but it was early, and it was honest about its uncertainty.

**Host A:** Right. And that's the whole philosophy. This is Sanjeevani Twin.

**Host B:** Let me push on the word "twin". Everyone says AI predicts glucose. What's different here?

**Host A:** A predictor gives you a number. A twin is a model of the person you can *simulate*. The
team's analogy: a predictor is a weather forecast, a twin is a flight simulator. You can rehearse
the future.

**Host B:** So the doctor can ask, what if he walks after lunch?

**Host A:** Exactly. They call it the What-If Lab. The twin replays the next 24 hours instantly, and
there's a button, "Find the best plan", that simulates 54 possible tomorrows at once. For Rajesh,
a 20-minute walk after meals plus swapping to a low-GI option cut his highest peak by 96 mg/dL.

**Host B:** And the visual for that is the part I keep thinking about.

**Host A:** The ghost twin. The screen splits into two holographic Rajeshes, one on current habits
and one following the plan, time-lapsing through tomorrow. At 2:20 pm one is at 273 and the other is
at 212. You don't need to read a chart.

**Host B:** Now the sceptic in me: it's all synthetic data, isn't it?

**Host A:** It is, as the challenge rules require. But they made the simulated world harder than
the model. It has things the twin is never told about: the dawn phenomenon, unlogged snacks, carb
counts off by about a fifth, sensor noise. And they tested on 10 patients the system had never
seen.

**Host B:** And the numbers?

**Host A:** A 48% lower two-hour error than assuming nothing changes. A median warning of 105
minutes across 457 real spikes. And the stat I'd put on a billboard: under the same alert rule, 26%
fewer false alarms than pure AI.

**Host B:** Because alert fatigue is what kills these tools.

**Host A:** Exactly. Prediction is useful. Simulation changes care.

## Part 8: Guardrails (hosts must NOT say)
- that real patients, hospitals or clinical trials were involved (all data is synthetic)
- that it "cures", "reverses" or "treats" diabetes, or doses insulin (it is decision support)
- that it is approved, certified or a medical device
- that it is partnered with or endorsed by Happiest Health, ICMR or any company
- that it has won anything
- any number not in the sources; if unsure, round down and say "about"
- that the 80% band is a guarantee (it is calibrated, about 76–78% observed)

## Part 9: Pronunciation and glossary
- **Sanjeevani**: sun-JEE-vuh-nee · **Navratri**: nuv-RAA-tree · **Sabudana**: saa-boo-DAA-na
  (tapioca pearls) · **Kuttu**: KOO-too (buckwheat) · **Lucknow**: LUCK-now
- **CGM**: continuous glucose monitor, a skin sensor reading glucose every 5 minutes
- **HbA1c**: a three-month average blood-sugar marker
- **HRV**: heart-rate variability, a stress and recovery signal from wearables
- **FHIR**: pronounced "fire", the global health-record data standard
- **ABHA**: the Ayushman Bharat Health Account, India's digital health ID
- **TCF7L2**: a gene; one common variant strongly raises Type 2 Diabetes risk by impairing insulin
  release
- **Shapley values**: a fair way to split credit for an outcome among several causes
- **Conformal prediction**: a method that makes uncertainty ranges statistically honest
- **Clarke Error Grid**: the standard chart for judging whether a glucose estimate is safe to act on
- **AUROC**: a 0-to-1 score for how well alerts separate real spikes from non-spikes (0.5 is a coin
  flip, 1.0 is perfect)
