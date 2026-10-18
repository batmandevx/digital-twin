// Sanjeevani Twin: dashboard controller
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const api = async (path, body) => {
  const r = await fetch("/api/" + path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  if (!r.ok) throw new Error(await r.text());
  return r.json();
};
const fmt = (v, d = 0) => (v == null || isNaN(v) ? "—" : Number(v).toFixed(d));
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const ICON = {
  spike: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg>',
  high: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17v.5"/></svg>',
  low: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12l7 7 7-7"/></svg>',
  watch: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/></svg>',
  stable: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5 9-10"/></svg>',
};
const STATUS = {
  spike: { label: "Spike predicted", cls: "b-spike" }, high: { label: "Above range", cls: "b-high" },
  low: { label: "Low risk", cls: "b-low" }, watch: { label: "Watch", cls: "b-watch" }, stable: { label: "Stable", cls: "b-stable" },
};
const badge = (st) => `<span class="badge ${STATUS[st].cls}">${ICON[st]}${STATUS[st].label}</span>`;
const zone = (g) => (g == null ? "stable" : g < 70 ? "low" : g > 250 ? "high" : g > 180 ? "watch" : "stable");
const zoneBadge = (g) => {
  if (g == null) return "";
  if (g < 70) return `<span class="badge b-low">${ICON.low}Below range</span>`;
  if (g > 250) return `<span class="badge b-spike">${ICON.high}Very high</span>`;
  if (g > 180) return `<span class="badge b-high">${ICON.high}Above range</span>`;
  return `<span class="badge b-stable">${ICON.stable}In range 70–180</span>`;
};

const S = { meta: null, t: 0, pid: "SNJ-001", cohort: null, P: null, playing: false, filter: "all", q: "", busy: false, twin: null, tab: "forecast", wi: null, opt: null };

// ------------------------------------------------------------------ starfield
(function stars() {
  const c = $("#bg-stars"), g = c.getContext("2d");
  let W, H, pts;
  const init = () => { W = c.width = innerWidth * devicePixelRatio; H = c.height = innerHeight * devicePixelRatio; pts = Array.from({ length: 140 }, () => [Math.random() * W, Math.random() * H, Math.random() * 1.4 + .3, Math.random() * 6]); };
  init(); addEventListener("resize", init);
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const draw = (t) => {
    g.clearRect(0, 0, W, H);
    for (const p of pts) { const a = .25 + .35 * Math.sin(t / 1400 + p[3]); g.fillStyle = `rgba(150,200,255,${a})`; g.beginPath(); g.arc(p[0], p[1], p[2] * devicePixelRatio, 0, 7); g.fill(); if (!reduce) p[1] = (p[1] + .04 * p[2]) % H; }
    requestAnimationFrame(draw);
  };
  requestAnimationFrame(draw);
})();

// ------------------------------------------------------------------ boot
const BOOT = [
  "Loading FHIR R4 records · <b>40 synthetic patients</b>",
  "Ingesting CGM, heart rate, HRV, sleep stages, steps",
  "Calibrating personal physiology · Bayesian · 3-day onboarding",
  "Assimilating live CGM into each digital twin",
  "Loading hybrid AI forecasters · conformal 80% intervals",
  "Rendering holographic twin",
];
async function boot() {
  const box = $("#boot-steps"), bar = $("#boot-bar");
  const step = (i) => { box.insertAdjacentHTML("beforeend", `<div>› ${BOOT[i]} <b>✓</b></div>`); bar.style.width = ((i + 1) / BOOT.length * 100) + "%"; };
  const fast = location.hash.includes("fast=1");
  const wait = (ms) => new Promise((r) => setTimeout(r, fast ? 0 : ms));
  try {
    step(0);
    S.meta = await api("meta");
    window.__START = S.meta.start;
    const h = new URLSearchParams(location.hash.slice(1));
    S.pid = h.get("pid") || S.meta.default.pid;
    S.t = +(h.get("t") || S.meta.default.t);
    await wait(250); step(1);
    const pc = api("cohort?t=" + S.t);
    await wait(250); step(2);
    S.cohort = await pc;
    await wait(200); step(3);
    S.P = await api(`patient/${S.pid}?t=${S.t}`);
    step(4);
    await wait(200);
    $("#app").hidden = false;
    await init3D();
    step(5);
    setupUI();
    renderAll();
    await wait(450);
    $("#boot").classList.add("done");
    if (fast) $("#boot").style.display = "none";
  } catch (e) {
    box.insertAdjacentHTML("beforeend", `<div style="color:var(--bad)">Could not reach the twin server. Start it with <b>python run.py</b>.<br>${esc(e.message)}</div>`);
    console.error(e);
  }
}

async function init3D() {
  try {
    const { Twin3D } = await Promise.race([import("./twin3d.js"),
      new Promise((_, rej) => setTimeout(() => rej(new Error("3D load timeout")), 8000))]);
    S.twin = new Twin3D($("#three-root"), $("#labels-layer"), {
      onOrganClick: (key, info) => showOrgan(key, info),
      onPlayback: (frac, i) => S.wiCursor?.(i),
      instant: location.hash.includes("fast=1"),
    });
  } catch (e) {
    console.warn("3D unavailable", e);
    $("#stage-fallback").hidden = false;
  }
}

// ------------------------------------------------------------------ UI wiring
function setupUI() {
  const m = S.meta;
  const days = Math.round((m.t_max + 5) / 1440);
  const start = new Date(m.start);
  $("#scrub-days").innerHTML = Array.from({ length: days }, (_, d) => {
    const dt = new Date(start.getTime() + d * 864e5);
    const fest = m.navratri.includes(d);
    const lab = d === 0 ? dt.toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" }) : dt.toLocaleDateString("en-IN", { day: "numeric", timeZone: "Asia/Kolkata" });
    return `<span class="${fest ? "fest" : ""}" title="${dt.toDateString()}${fest ? " · Navratri" : ""}">${lab}</span>`;
  }).join("");
  const rg = $("#scrub-range");
  rg.min = 0; rg.max = m.t_max; rg.value = S.t;
  const calibPct = m.t_min / m.t_max * 100;
  rg.style.background = `linear-gradient(90deg, rgba(255,255,255,.08) ${calibPct}%, rgba(55,226,255,.25) ${calibPct}%)`;
  rg.addEventListener("input", () => { const v = Math.max(m.t_min, +rg.value); rg.value = v; setTime(v, true); });
  $("#btn-play").addEventListener("click", togglePlay);
  $("#btn-tour").addEventListener("click", tourStart);
  $("#btn-back").addEventListener("click", () => setTime(S.t - 60));
  $("#btn-fwd").addEventListener("click", () => setTime(S.t + 60));
  addEventListener("keydown", (e) => {
    if (e.target.matches("input, select, textarea")) return;
    if (e.code === "Space") { e.preventDefault(); togglePlay(); }
    if (e.code === "ArrowRight") setTime(S.t + 15);
    if (e.code === "ArrowLeft") setTime(S.t - 15);
    if (e.key === "t" || e.key === "T") tourI >= 0 ? tourEnd() : tourStart();
    if (e.key === "Escape") { tourEnd(); S.twin?.resetView(); }
  });
  $("#speed").addEventListener("change", () => { if (S.playing) { togglePlay(); togglePlay(); } });
  $$("#cohort-filter .chip").forEach((b) => b.addEventListener("click", () => { $$("#cohort-filter .chip").forEach((x) => x.classList.remove("on")); b.classList.add("on"); S.filter = b.dataset.f; renderCohort(); }));
  $("#cohort-search").addEventListener("input", (e) => { S.q = e.target.value.toLowerCase(); renderCohort(); });
  $$(".tab").forEach((b) => b.addEventListener("click", () => setTab(b.dataset.tab)));
  $("#btn-labels").addEventListener("click", (e) => { const on = e.currentTarget.getAttribute("aria-pressed") !== "true"; e.currentTarget.setAttribute("aria-pressed", on); S.twin?.setLabels(on); });
  $("#btn-rotate").addEventListener("click", (e) => { const on = e.currentTarget.getAttribute("aria-pressed") !== "true"; e.currentTarget.setAttribute("aria-pressed", on); S.twin?.setAutoRotate(on); });
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) $("#btn-rotate").setAttribute("aria-pressed", "false");
  // what-if controls
  const upd = () => {
    $("#v-walk").textContent = $("#c-walk").value + " min";
    $("#v-swap").textContent = Math.round($("#c-swap").value * 100) + "%";
    $("#v-dinner").textContent = $("#c-dinner").value + " h";
    $("#v-sleep").textContent = $("#c-sleep").value + " h";
    $("#v-met").textContent = (+$("#c-met").value).toFixed(1) + " g/day";
  };
  let deb;
  $$(".wi-controls input").forEach((i) => i.addEventListener("input", () => { upd(); clearTimeout(deb); deb = setTimeout(() => runWhatIf(), 220); }));
  $("#btn-reset").addEventListener("click", () => { resetWhatIf(); runWhatIf(); });
  $("#btn-optimise").addEventListener("click", runOptimise);
  S.updWI = upd;
  addEventListener("resize", debounce(() => renderCharts(), 200));
  const h = new URLSearchParams(location.hash.slice(1));
  requestAnimationFrame(() => {
    setTab(h.get("tab") || "forecast");
    if (h.get("opt")) setTimeout(runOptimise, 300);
    if (h.get("tour")) setTimeout(tourStart, 1500);
    if (h.get("organ")) setTimeout(() => S.twin?.focusOrgan(h.get("organ")), 3800);
  });
}
const debounce = (f, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => f(...a), ms); }; };

function setTab(tab) {
  S.tab = tab;
  $$(".tab").forEach((b) => b.classList.toggle("on", b.dataset.tab === tab));
  $$(".tabpane").forEach((p) => p.classList.toggle("on", p.id === "tab-" + tab));
  const b = $(`.tab[data-tab="${tab}"]`), ink = $("#tab-ink");
  ink.style.left = b.offsetLeft + "px"; ink.style.width = b.offsetWidth + "px";
  if (tab === "whatif") { if (!S.wi) { resetWhatIf(); runWhatIf(); } else setGhost(true); }
  else setGhost(false);
  if (tab === "insights") renderInsights();
  if (tab === "model") renderModel();
  if (tab === "forecast") renderCharts();
  if (tab === "physiology") renderPhysio();
  if (tab === "records") renderRecords();
}

function togglePlay() {
  S.playing = !S.playing;
  document.body.classList.toggle("playing", S.playing);
  clearInterval(S.timer);
  if (S.playing) S.timer = setInterval(() => { if (!S.busy) setTime(S.t + 15); }, +$("#speed").value);
}

async function setTime(t, scrubbing) {
  const m = S.meta;
  t = Math.max(m.t_min, Math.min(m.t_max, Math.round(t / 5) * 5));
  if (t === S.t && S.P) return;
  S.t = t;
  $("#scrub-range").value = t;
  renderClock();
  if (scrubbing) { clearTimeout(S.scrubT); S.scrubT = setTimeout(() => load(), 120); return; }
  await load();
}

async function load(pidChanged) {
  if (S.busy) { S.pending = true; return; }
  S.busy = true;
  document.body.classList.add("loading");
  try {
    const [cohort, P] = await Promise.all([api("cohort?t=" + S.t), api(`patient/${S.pid}?t=${S.t}`)]);
    S.cohort = cohort; S.P = P;
    if (pidChanged) S.wi = null;
    renderAll();
    history.replaceState(null, "", `#pid=${S.pid}&t=${S.t}&tab=${S.tab}`);
  } catch (e) { console.error(e); }
  document.body.classList.remove("loading");
  S.busy = false;
  if (S.pending) { S.pending = false; load(); }
}

function selectPatient(pid) {
  if (pid === S.pid) return;
  S.pid = pid; S.opt = null; $("#opt-results").innerHTML = "";
  load(true).then(() => { if (S.tab === "whatif") { resetWhatIf(); runWhatIf(); } });
  S.twin?.pulse();
}

// ------------------------------------------------------------------ render
function renderAll() {
  renderClock(); renderCohort(); renderHead(); renderHUD(); renderAlert(); renderDrivers(); renderNudge();
  if (S.tab === "forecast") renderCharts();
  if (S.tab === "physiology") renderPhysio();
  if (S.tab === "records") renderRecords();
  if (S.tab === "insights") renderInsights();
  if (S.tab === "whatif" && S.wi) runWhatIf();
}

function setGhost(on) {
  $("#stage-mode").classList.toggle("on", !!on);
  $("#stage").classList.toggle("ghosting", !!on);
  $("#stage-mode").textContent = "Ghost twin · next 24 h · time-lapse";
  if (!S.twin) return;
  if (on && S.wi) {
    const W = S.wi, start = new Date(S.meta.start).getTime();
    S.twin.setGhost(true, { baseline: W.baseline, scenario: W.scenario,
      clock: (i) => new Date(start + W.minutes[i] * 60000).toLocaleString("en-IN", { weekday: "short", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata" }) });
  } else S.twin.setGhost(false);
  if (!on) S.wiCursor?.(null);
}

function showOrgan(key, info) {
  const el = $("#organ-card");
  S.organ = key; S.organInfo = info;
  if (!key) { el.hidden = true; return; }
  const st = S.P.twin.state, tw = S.P.twin;
  const rows = {
    brain: [["Inferred stress", fmt(st.stress * 100) + "%"], ["HRV", fmt(st.hrv) + " ms"], ["HR", fmt(st.hr) + " bpm"]],
    heart: [["Heart rate", fmt(st.hr) + " bpm"], ["HRV (RMSSD)", fmt(st.hrv) + " ms"], ["Asleep", st.asleep ? "yes" : "no"]],
    liver: [["Hepatic set-point now", fmt(st.hepatic) + " mg/dL"], ["Learned dawn rise", fmt(S.P.dawn, 2) + " mg/dL/min"], ["Basal (calibrated)", fmt(tw.params.Gb) + " mg/dL"]],
    pancreas: [["Insulin above basal", fmt(st.insulin) + " µU/mL"], ["β-cell responsiveness", fmt(tw.params.gamma, 3) + " · p" + fmt(tw.pct.gamma)], ["Insulin sensitivity today", fmt(S.P.adapt_si * 100) + "% of baseline"]],
    gut: [["Carbs absorbing", fmt(st.gut) + " g"], ["Fast (high-GI) channel", fmt(st.gut_fast) + " g"], ["Meals in last 24 h", S.P.meals.length]],
    stomach: [["Carbs absorbing", fmt(st.gut) + " g"]],
    muscleL: [["Exercise memory E", fmt(st.exercise, 2)], ["Steps last hour", S.P.timeline.steps.slice(-12).reduce((a, b) => a + b, 0)]],
    muscleR: [["Exercise memory E", fmt(st.exercise, 2)], ["Steps last hour", S.P.timeline.steps.slice(-12).reduce((a, b) => a + b, 0)]],
  }[key] || [];
  el.style.setProperty("--oc", info.color);
  el.innerHTML = `<h4>${esc(info.name)}</h4><p>${esc(info.text)}</p><div class="kv">${rows.map(([a, b]) => `<span>${a}</span><b>${b}</b>`).join("")}</div><button class="ghost-btn" id="organ-close">Back to full body</button>`;
  el.hidden = false;
  $("#organ-close").addEventListener("click", () => S.twin.resetView());
}

function renderClock() {
  const d = new Date(new Date(S.meta.start).getTime() + S.t * 60000);
  $("#clock-time").textContent = d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata" });
  const day = Math.floor(S.t / 1440);
  const fest = S.meta.navratri.includes(day) ? " · ✦ Navratri" : "";
  $("#clock-date").textContent = d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Kolkata" }) + fest;
}

function renderCohort() {
  const pts = S.cohort.patients;
  const alerts = pts.filter((p) => p.status === "spike" || p.status === "low").length;
  const high = pts.filter((p) => p.status === "high").length;
  $("#cohort-count").textContent = `${pts.length} twins live`;
  $("#cohort-summary").innerHTML = `<div class="cs"><b style="color:var(--bad)">${alerts}</b><span>predicted events</span></div><div class="cs"><b style="color:var(--warn)">${high}</b><span>above range</span></div><div class="cs"><b style="color:var(--ok)">${pts.length - alerts - high}</b><span>stable / watch</span></div>`;
  let list = pts;
  if (S.filter === "alert") list = list.filter((p) => ["spike", "low", "high"].includes(p.status));
  if (S.filter === "persona") list = list.filter((p) => p.persona);
  if (S.q) list = list.filter((p) => (p.name + p.city + p.id).toLowerCase().includes(S.q));
  const col = (st) => ({ spike: "var(--bad)", high: "var(--warn)", low: "var(--low)", watch: "var(--warn)", stable: "var(--ok)" })[st];
  $("#cohort-list").innerHTML = list.map((p) => `
    <li class="pt ${p.id === S.pid ? "sel" : ""}" data-id="${p.id}" tabindex="0" aria-label="${esc(p.name)}, ${STATUS[p.status].label}">
      ${Charts.ring(p.p_spike, col(p.status), Math.round(p.p_spike * 100))}
      <div style="min-width:0">
        <div class="pt-name">${esc(p.name)}${p.persona ? '<span class="tag">story</span>' : ""}</div>
        <div class="pt-meta">${p.age} ${p.sex} · ${esc(p.city)} · A1c ${p.hba1c}</div>
        <div style="margin-top:4px">${badge(p.status)}${p.status === "spike" && p.eta ? `<span class="muted small" style="margin-left:6px">in ${p.eta} min</span>` : ""}</div>
      </div>
      <div class="pt-right"><div class="pt-g" style="color:${Charts.zoneColor(p.g_now)}">${fmt(p.g_now)}</div>${Charts.spark(p.spark)}</div>
    </li>`).join("");
  if (!S.scrolled) { S.scrolled = true; $("#cohort-list .pt.sel")?.scrollIntoView({ block: "nearest" }); }
  $$("#cohort-list .pt").forEach((li) => {
    li.addEventListener("click", () => selectPatient(li.dataset.id));
    li.addEventListener("keydown", (e) => { if (e.key === "Enter") selectPatient(li.dataset.id); });
  });
}

function renderHead() {
  const P = S.P, pf = P.profile;
  const ini = pf.name.split(" ").map((w) => w[0]).slice(0, 2).join("");
  const conds = pf.conditions.map((c) => `<span class="pill cond">${esc(c.name)}</span>`).join("");
  const meds = pf.medications.map((m) => `<span class="pill med">${esc(m.name)} ${m.dose ? fmt(m.dose) + " " + esc(m.unit || "") : ""}</span>`).join("");
  const fest = P.navratri ? `<span class="pill fest">✦ Navratri${P.fasting ? " · fasting detected" : ""}</span>` : "";
  $("#patient-head").innerHTML = `
    <div class="avatar">${esc(ini)}</div>
    <div style="min-width:0">
      <div class="ph-name">${esc(pf.name)} ${P.split === "test" ? '<span class="tag" title="This patient was never seen during model training">held-out · unseen in training</span>' : ""}</div>
      <div class="ph-meta">${pf.age} y · ${pf.sex === "M" ? "Male" : "Female"} · ${esc(pf.city)} · ${esc(pf.diet || "")} · T2D for ${pf.years_dx} y</div>
      ${P.story ? `<div class="ph-story">${esc(P.story)}</div>` : ""}
      <div class="ph-chips">${fest}${conds}${meds}</div>
    </div>
    <div class="ph-right">
      <span class="abha">ABHA ${esc(pf.abha || "—")}</span>
      <span class="pill">HbA1c <b>${pf.labs.hba1c}%</b></span>
      <span class="pill">GMI <b>${fmt(P.stats.gmi, 1)}%</b> · TIR <b>${fmt(P.stats.tir)}%</b></span>
    </div>`;
}

let lastG = null;
function renderHUD() {
  const P = S.P, pr = P.prediction, st = P.twin.state;
  const g = pr.g_now;
  const el = $("#hud-g");
  const from = lastG ?? g ?? 0;
  lastG = g;
  const t0 = performance.now();
  const step = (now) => { const k = Math.min(1, (now - t0) / 600); el.textContent = g == null ? "—" : Math.round(from + (g - from) * (1 - Math.pow(1 - k, 3))); if (k < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
  el.style.color = Charts.zoneColor(g);
  const tr = pr.trend ?? 0;
  $("#hud-trend").textContent = tr > 30 ? "⇈" : tr > 15 ? "↑" : tr > 6 ? "↗" : tr < -30 ? "⇊" : tr < -15 ? "↓" : tr < -6 ? "↘" : "→";
  $("#hud-trend").title = `${tr > 0 ? "+" : ""}${fmt(tr)} mg/dL in 15 min`;
  $("#hud-zone").innerHTML = zoneBadge(g);
  $("#hud-sync").textContent = Charts.hhmm(P.tod);
  const tl = P.timeline;
  const steps1h = tl.steps.slice(-12).reduce((a, b) => a + b, 0);
  const lastNight = P.nights[P.nights.length - 1];
  $("#hud-mini").innerHTML = `
    <div class="hm"><b>${fmt(st.hr)}</b><span>HR bpm</span></div>
    <div class="hm"><b>${fmt(st.hrv)}</b><span>HRV ms</span></div>
    <div class="hm"><b>${steps1h.toLocaleString("en-IN")}</b><span>steps · 1 h</span></div>
    <div class="hm"><b>${lastNight ? lastNight.hours.toFixed(1) + "h" : "—"}</b><span>sleep</span></div>`;
  const risk = pr.status === "spike" ? pr.p_spike : pr.status === "high" ? .75 : pr.status === "watch" ? pr.p_spike * .6 : 0;
  if (S.twin) {
    const key = S.pid + ":" + S.t;
    if (S.ribbonKey !== key) {
      S.ribbonKey = key;
      S.twin.setRibbon(tl.cgm, pr.forecast.map((f) => f.mid));
      const tcf = P.profile.genetics?.TCF7L2;
      S.twin.setGenetics(tcf ? `TCF7L2 ${tcf.genotype} · PRS ${fmt(P.profile.prs, 1)}` : "Genotype n/a", tcf ? tcf.risk_alleles : 0);
    }
    if (S.organ) showOrgan(S.organ, S.organInfo);
  }
  S.twin?.update({ glucose: g ?? st.G, risk, hr: st.hr, stress: st.stress, insulin: st.insulin, gut: st.gut, exercise: st.exercise,
                   steps: tl.steps[tl.steps.length - 1] * 12, hepatic: st.hepatic, asleep: st.asleep, status: pr.status });
}

function gauge(frac, color, big, small) {
  const r = 46, L = 2 * Math.PI * r;
  return `<div class="gauge"><svg viewBox="0 0 112 112"><circle class="g-tick" cx="56" cy="56" r="53"/><circle class="g-bg" cx="56" cy="56" r="${r}"/>
    <circle class="g-fg" cx="56" cy="56" r="${r}" stroke="${color}" stroke-dasharray="${L}" stroke-dashoffset="${L}" data-off="${L * (1 - frac)}" style="filter:drop-shadow(0 0 6px ${color})"/></svg>
    <div class="gauge-c"><div><b>${big}</b><span>${small}</span></div></div></div>`;
}
const dur = (m) => (m >= 60 ? `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")} m` : `${m} min`);

function renderAlert() {
  const P = S.P, pr = P.prediction, card = $("#alert-card");
  card.className = "panel alert-card" + (pr.status === "spike" || pr.status === "high" ? " is-spike" : pr.status === "low" ? " is-low" : "");
  const pct = Math.round(pr.p_spike * 100);
  let main, sub, color;
  if (pr.status === "spike") {
    color = "var(--bad)";
    main = `Spike above <em>180</em> ${pr.eta ? `in <em>${dur(pr.eta)}</em>` : "within 2 h"}`;
    sub = `Predicted peak <b>${fmt(pr.peak)}</b> mg/dL · 80% interval up to ${fmt(pr.peak_hi)}`;
  } else if (pr.status === "high") {
    color = "var(--warn)"; main = `Glucose is above range now`; sub = `Forecast peak ${fmt(pr.peak)} mg/dL in ${pr.t_peak} min. Consider an activity nudge.`;
  } else if (pr.status === "low") {
    color = "var(--low)"; main = `Hypoglycaemia watch`; sub = `Lower interval bound falls to ${fmt(Math.min(...pr.forecast.map((f) => f.lo)))} mg/dL. Check sulfonylurea timing and meals.`;
  } else if (pr.status === "watch") {
    color = "var(--warn)"; main = `Elevated risk, being watched`; sub = `Spike probability ${pct}% is below the alert threshold of ${Math.round(pr.thr * 100)}%.`;
  } else {
    color = "var(--ok)"; main = `Stable for the next 2 h`; sub = `No adverse event expected. Forecast peak is ${fmt(pr.peak)} mg/dL.`;
  }
  const cd = pr.status === "spike" && pr.eta ? `<div class="countdown" id="countdown">${String(Math.floor(pr.eta / 60)).padStart(2, "0")}:${String(pr.eta % 60).padStart(2, "0")}<small>until crossing</small></div>` : "";
  card.innerHTML = `
    <div class="al-top"><span class="al-title">2-hour twin forecast</span>${badge(pr.status)}</div>
    <div class="al-main">${gauge(pr.p_spike, color, pct + "%", "spike risk")}
      <div><div class="al-big">${main}</div><div class="al-sub">${sub}</div>${cd}</div></div>
    <div class="al-foot">
      <div><b>${fmt(pr.g_now)}</b><span>now mg/dL</span></div>
      <div><b>${fmt(pr.forecast[11]?.mid)}</b><span>in 60 min</span></div>
      <div><b>${fmt(pr.forecast[23]?.mid)}</b><span>in 120 min</span></div>
    </div>`;
  requestAnimationFrame(() => $$(".g-fg", card).forEach((c) => (c.style.strokeDashoffset = c.dataset.off)));
}

function renderDrivers() {
  const P = S.P, A = P.attribution, el = $("#drivers-card");
  const C = ["var(--c2)", "var(--c3)", "var(--c4)", "var(--c1)", "var(--c5)"];
  const order = ["meal", "inactivity", "sleep", "stress", "medication"];
  if (!A) {
    const tw = P.twin;
    el.innerHTML = `<div class="drv-head"><h2>Twin physiology now</h2><span class="muted small">personalised</span></div>
      <div class="kv" style="margin-top:10px">
        <span>Insulin sensitivity</span><b>${fmt(tw.params.SI, 2)} <span class="muted">· p${fmt(tw.pct.SI)}</span></b>
        <span>Beta-cell responsiveness</span><b>${fmt(tw.params.gamma, 3)} <span class="muted">· p${fmt(tw.pct.gamma)}</span></b>
        <span>Basal glucose</span><b>${fmt(tw.params.Gb)} mg/dL</b>
        <span>Carbs absorbing in gut</span><b>${fmt(tw.state.gut)} g</b>
        <span>Insulin above basal</span><b>${fmt(tw.state.insulin)} µU/mL</b>
        <span>Sleep debt today</span><b>${fmt(tw.state.sleep_debt, 1)} h</b>
      </div>
      <div class="drv-eq"><span>Driver attribution appears when the twin forecasts an excursion.</span></div>`;
    return;
  }
  const mx = Math.max(10, ...A.drivers.map((d) => d.mgdl));
  el.innerHTML = `<div class="drv-head"><h2>Why is the twin worried?</h2><span class="muted small">Shapley · 32 simulations</span></div>
    <div class="drv">${A.drivers.map((d) => `
      <div class="drv-row"><div><div class="drv-label"><span>${esc(d.label)}</span></div>
        <div class="drv-bar"><i data-w="${Math.max(0, d.mgdl) / mx * 100}" style="background:${C[order.indexOf(d.key)]}"></i></div></div>
        <div class="drv-val">${d.mgdl > 0 ? "+" : ""}${fmt(d.mgdl)}</div></div>`).join("")}</div>
    <div class="drv-eq"><span>Peak if every driver were ideal: <b>${fmt(A.peak_ideal)}</b></span><span>Current trajectory: <b>${fmt(A.peak_actual)}</b> mg/dL</span></div>`;
  requestAnimationFrame(() => $$("i[data-w]", el).forEach((b) => (b.style.width = b.dataset.w + "%")));
}

function renderNudge() {
  const R = S.P.recommendation, el = $("#nudge-card");
  el.innerHTML = `<div class="drv-head"><h2><svg viewBox="0 0 24 24"><path d="M21 12a8 8 0 01-11.6 7.1L4 20l1-4.6A8 8 0 1121 12z"/></svg>Personalised nudge</h2><span class="muted small">twin-tested</span></div>
    <div class="nudge-bubble">${esc(R.en)}</div>
    <div class="nudge-bubble hi" lang="hi">${esc(R.hi)}</div>
    <div class="nudge-actions">
      <button class="btn-primary" id="btn-send"><svg viewBox="0 0 24 24"><path d="M2 21l21-9L2 3v7l15 2-15 2z"/></svg>Send to patient</button>
      <button class="ghost-btn" id="btn-sim">Simulate</button>
    </div>
    ${R.options?.length ? `<div class="opts">${R.options.filter((o) => o.drop >= 1).sort((a, b) => b.drop - a.drop).map((o) => `<div class="opt"><span>${({ walk: "15-min post-meal walk", swap: "Low-GI swap", dinner_earlier: "Dinner 1 h earlier", sleep: "Sleep 7.5 h" })[o.kind]}</span><b>−${fmt(o.drop)} mg/dL</b></div>`).join("")}</div>` : ""}`;
  $("#btn-send").addEventListener("click", () => toast("✓ Nudge sent to the patient's phone in English and Hindi (demo, nothing transmitted)"));
  $("#btn-sim").addEventListener("click", () => {
    resetWhatIf();
    const k = R.kind;
    if (k === "walk" || k === "walk_now") $("#c-walk").value = 15;
    if (k === "swap") $("#c-swap").value = 1;
    if (k === "dinner_earlier") $("#c-dinner").value = 1;
    if (k === "sleep") $("#c-sleep").value = 7.5;
    S.updWI(); setTab("whatif"); runWhatIf();
    $(".workspace").scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("on"); clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("on"), 3200); }

// ------------------------------------------------------------------ forecast tab
function renderCharts() {
  const P = S.P;
  if (!P || S.tab !== "forecast") return;
  Charts.glucose($("#glucose-chart"), P);
  Charts.strip($("#strip-chart"), P);
  Charts.sleep($("#sleep-chart"), P.nights, $("#sleep-legend"));
  Charts.tir($("#tir-chart"), P.stats.daily);
  Charts.hrv($("#hrv-chart"), P);
  const s = P.stats, f = P.fidelity || {};
  const tbr = s.tbr || 0, tar = s.tar || 0, tir = s.tir || 0;
  $("#kpi-col").innerHTML = `
    <div class="kpi"><div class="k">Time in range · to date</div><div class="v">${fmt(tir)}<small>%</small></div>
      <div class="tir-bar" title="below / in range / above"><i style="width:${tbr}%;background:var(--low)"></i><i style="width:${tir}%;background:var(--ok)"></i><i style="width:${tar - (s.tar250 || 0)}%;background:var(--warn)"></i><i style="width:${s.tar250 || 0}%;background:var(--bad)"></i></div>
      <div class="d">${fmt(tar, 1)}% above 180 · ${fmt(s.tar250, 1)}% above 250 · ${fmt(tbr, 1)}% below 70</div></div>
    <div class="kpi"><div class="k">Glucose management indicator</div><div class="v">${fmt(s.gmi, 1)}<small>% (lab HbA1c ${P.profile.labs.hba1c}%)</small></div><div class="d">Mean ${fmt(s.mean)} mg/dL · CV ${fmt(s.cv)}%${s.cv > 36 ? " (high variability)" : ""}</div></div>
    <div class="kpi"><div class="k">Twin fidelity</div><div class="v">${fmt(P.twin.calib_rmse, 1)}<small>mg/dL onboarding RMSE</small></div><div class="d">Open-loop simulation error ${fmt(f.open_loop_rmse, 1)} mg/dL across 11 unseen days</div></div>
    <div class="kpi"><div class="k">Usual meals (learned)</div><div class="d" style="margin-top:6px">${Object.entries(P.habits.slots).map(([k, v]) => `<div class="tt-r" style="display:flex;justify-content:space-between"><span>${k} · ${Charts.hhmm(v.tod)}</span><b class="mono">${Math.round(v.carbs)} g</b></div>`).join("")}</div></div>`;
}

// ------------------------------------------------------------------ what-if
function resetWhatIf() {
  const P = S.P;
  $("#c-walk").value = 0; $("#c-swap").value = 0; $("#c-dinner").value = 0; $("#c-snack").checked = false;
  $("#c-sleep").value = Math.round((P.habits.sleep_hours || 7) * 2) / 2;
  const met = P.profile.medications.find((m) => /metformin/i.test(m.name));
  $("#c-met").value = met ? met.dose / 1000 : 0;
  S.updWI?.();
}
function wiCfg() {
  return { walk: +$("#c-walk").value, swap: +$("#c-swap").value, dinner_shift: +$("#c-dinner").value, sleep_h: +$("#c-sleep").value,
           metformin: +$("#c-met").value, skip_snack: $("#c-snack").checked };
}
async function runWhatIf(spaghetti) {
  const W = await api("whatif", { pid: S.pid, t: S.t, cfg: wiCfg() });
  S.wi = W;
  S.wiCursor = Charts.whatif($("#whatif-chart"), W, spaghetti);
  if (S.tab === "whatif") { S.twin?.setGhost(false); setGhost(true); }
  const b = W.kpi_baseline, s = W.kpi_scenario;
  const d = (a, c, good = "down", dg = 0, unit = "") => { const v = c - a; const ok = good === "down" ? v <= 0 : v >= 0; return Math.abs(v) < 0.05 ? "" : `<span class="delta ${ok ? "good" : "bad"}">${v > 0 ? "+" : ""}${v.toFixed(dg)}${unit}</span>`; };
  $("#wi-kpis").innerHTML = `
    <div class="kpi"><div class="k">Time in range</div><div class="v">${fmt(s.tir)}<small>%</small>${d(b.tir, s.tir, "up", 0, "%")}</div><div class="d">was ${fmt(b.tir)}%</div></div>
    <div class="kpi"><div class="k">Highest peak</div><div class="v">${fmt(s.peak)}<small>mg/dL</small>${d(b.peak, s.peak)}</div><div class="d">was ${fmt(b.peak)}</div></div>
    <div class="kpi"><div class="k">Time above 250</div><div class="v">${fmt(s.tar250, 1)}<small>%</small>${d(b.tar250, s.tar250, "down", 1)}</div><div class="d">mean glucose ${fmt(s.mean)} (was ${fmt(b.mean)})</div></div>
    <div class="kpi"><div class="k">Projected HbA1c · 90 days</div><div class="v">${fmt(W.hba1c_90d, 1)}<small>%</small>${d(W.hba1c_now, W.hba1c_90d, "down", 1)}</div><div class="d">from ${W.hba1c_now}% if the plan is sustained</div></div>`;
  const swappedFoods = new Set(W.meals_baseline.map((m) => m.food));
  $("#wi-meals").innerHTML = W.meals_scenario.map((m) => `<span class="wi-meal ${swappedFoods.has(m.food) ? "" : "swapped"}">${m.icon} ${Charts.hhmm(m.minute)} · ${esc(m.name)} · ${m.carbs} g</span>`).join("");
}
async function runOptimise() {
  const btn = $("#btn-optimise");
  btn.disabled = true; btn.lastChild.textContent = " Simulating 54 futures…";
  const O = await api("optimise?pid=" + S.pid + "&t=" + S.t);
  S.opt = O;
  const best = O.top[0];
  if (best) {
    $("#c-walk").value = best.cfg.walk; $("#c-swap").value = best.cfg.swap; $("#c-dinner").value = best.cfg.dinner_shift; $("#c-sleep").value = Math.round(best.cfg.sleep_h * 2) / 2;
    S.updWI();
  }
  await runWhatIf({ curves: O.curves });
  btn.disabled = false; btn.lastChild.textContent = " Find the best plan";
  const desc = (c) => {
    const L = [];
    if (c.walk) L.push(`${c.walk}-min walk after lunch and dinner`);
    if (c.swap) L.push(`${c.swap >= 1 ? "Full" : "Partial"} low-GI swap (millets / brown rice)`);
    if (c.dinner_shift) L.push(`Dinner ${c.dinner_shift} h earlier`);
    if (c.sleep_h > (S.P.habits.sleep_hours || 7) + .2) L.push(`Sleep ${c.sleep_h} h tonight`);
    return L.length ? L : ["No change"];
  };
  $("#opt-results").innerHTML = O.top.map((r, i) => `
    <div class="plan ${i === 0 ? "best" : ""}" data-i="${i}" style="animation-delay:${.9 + i * .15}s">
      <h4><span>${i === 0 ? "★ Recommended plan" : `Alternative ${i}`}</span><span class="muted small">effort ${r.effort.toFixed(1)}</span></h4>
      <ul>${desc(r.cfg).map((l) => `<li>${l}</li>`).join("")}</ul>
      <div class="pk"><div><b>${fmt(r.kpi.tir)}%</b>time in range</div><div><b>−${fmt(r.peak_drop)}</b>peak mg/dL</div><div><b>${fmt(r.benefit)}%</b>less hyperglycaemia</div></div>
    </div>`).join("");
  $$(".plan").forEach((el) => el.addEventListener("click", () => {
    const r = O.top[+el.dataset.i];
    $("#c-walk").value = r.cfg.walk; $("#c-swap").value = r.cfg.swap; $("#c-dinner").value = r.cfg.dinner_shift; $("#c-sleep").value = Math.round(r.cfg.sleep_h * 2) / 2;
    S.updWI(); runWhatIf();
    $$(".plan").forEach((p) => p.classList.toggle("best", p === el));
  }));
  toast(`Searched ${O.n} possible tomorrows in one batched twin simulation`);
}

// ------------------------------------------------------------------ physiology tab
function renderPhysio() {
  const P = S.P, tw = P.twin, st = tw.state, pf = P.profile;
  const card = (k, v, unit, pct, prior, text, invert) => `
    <div class="param"><div class="k">${k}</div><div class="v">${v}<small> ${unit}</small></div>
      <div class="pctbar" style="${invert ? "background:linear-gradient(90deg, rgba(47,213,154,.5), rgba(255,181,71,.45), rgba(255,84,112,.5))" : ""}"><i style="left:${pct}%"></i>${prior != null ? `<u style="left:${prior}%" title="EHR prior"></u>` : ""}</div>
      <div class="pct-legend"><span>${invert ? "better" : "worse"}</span><span>cohort percentile p${Math.round(pct)}</span><span>${invert ? "worse" : "better"}</span></div>
      <p>${text}</p></div>`;
  const shift = (a, b) => `${b > a ? "+" : ""}${((b / a - 1) * 100).toFixed(0)}%`;
  const tcf = pf.genetics?.TCF7L2;
  $("#physio").innerHTML = `
    ${card("Insulin sensitivity · S<sub>I</sub>", fmt(tw.params.SI, 2), "×10⁻⁴ /min per µU/mL", tw.pct.SI, null,
      `EHR prior ${fmt(tw.prior.SI, 2)} from BMI ${pf.labs.bmi} and waist ${pf.labs.waist} cm (South-Asian adiposity weighting). CGM calibration moved it ${shift(tw.prior.SI, tw.params.SI)}.`)}
    ${card("Beta-cell responsiveness · γ", fmt(tw.params.gamma, 3), "µU/mL/min per mg/dL", tw.pct.gamma, null,
      `Prior lowered for ${pf.years_dx} y diabetes duration and TCF7L2 rs7903146 ${tcf ? esc(tcf.genotype) : "n/a"} (${tcf ? tcf.risk_alleles : 0} risk alleles, impaired insulin secretion). Calibration ${shift(tw.prior.gamma, tw.params.gamma)}.`)}
    ${card("Basal glucose · G<sub>b</sub>", fmt(tw.params.Gb), "mg/dL", 100 - tw.pct.Gb, null,
      `Hepatic set-point from fasting plasma glucose ${fmt(pf.labs.fpg)} mg/dL. Metformin and missed doses modulate it live (now ${fmt(st.hepatic)}).`)}
    <div class="param" style="grid-column: span 2"><div class="k">Mechanistic core (extended Bergman minimal model)</div>
      <div class="eq">dG/dt = −(S<sub>G</sub> + X)·G + S<sub>G</sub>·G<sub>b</sub>′ + Ra(t) − k<sub>ex</sub>·A·G + EGP<sub>stress</sub>·s(t)
dX/dt = −p₂·X + p₂·S<sub>I</sub>·m(t)·(1 + 0.8E)·(I − I<sub>b</sub>)
dI/dt = −n·(I − I<sub>b</sub>) + γ·m(t)·max(G − h, 0)
gut  : fast + slow 2-compartment chains (glycaemic-index split per Indian food)
m(t) = circadian(t) × sleep-debt factor       E = exercise memory (τ = 4 h)</div>
      <p class="muted small" style="margin-top:8px">Personalised by MAP cross-entropy search over 3 onboarding days, then kept in sync with a CGM state observer every 5 minutes. A gradient-boosted residual learner corrects what the physics misses (dawn phenomenon, unlogged snacks, sensor lag).</p></div>
    <div class="param"><div class="k">Live state vector</div>
      <div class="kv" style="margin-top:8px">
        <span>Plasma glucose G</span><b>${fmt(st.G)} mg/dL</b>
        <span>Insulin above basal</span><b>${fmt(st.insulin)} µU/mL</b>
        <span>Remote insulin action X</span><b>${fmt(st.remote_insulin, 3)}</b>
        <span>Carbs in gut</span><b>${fmt(st.gut)} g</b>
        <span>Exercise memory E</span><b>${fmt(st.exercise, 2)}</b>
        <span>Inferred stress</span><b>${fmt(st.stress, 2)}</b>
        <span>Sleep debt</span><b>${fmt(st.sleep_debt, 1)} h</b>
        <span>Asleep</span><b>${st.asleep ? "yes" : "no"}</b>
      </div></div>`;
}

// ------------------------------------------------------------------ records tab
async function renderRecords() {
  const P = S.P, pf = P.profile, L = pf.labs;
  const a1c = (pf.lab_history.hba1c || []).map(([d, v]) => `<span>${d}</span><b>${v}%</b>`).join("");
  const gen = Object.entries(pf.genetics || {}).map(([g, v]) => `<span>${g} ${esc(v.variant)}</span><b>${esc(v.genotype)}</b>`).join("");
  $("#records").innerHTML = `
    <div class="chart-card rec"><h3>Latest labs &amp; vitals</h3><div class="kv">
      <span>HbA1c</span><b>${L.hba1c}%</b><span>Fasting glucose</span><b>${L.fpg} mg/dL</b><span>BMI</span><b>${L.bmi}</b><span>Waist</span><b>${L.waist} cm</b>
      <span>Blood pressure</span><b>${L.sbp}/${L.dbp}</b><span>LDL / HDL</span><b>${L.ldl} / ${L.hdl}</b><span>Triglycerides</span><b>${L.tg}</b>
      <span>eGFR</span><b>${L.egfr}</b><span>Urine ACR</span><b>${L.uacr} mg/g</b></div></div>
    <div class="chart-card rec"><h3>HbA1c history</h3><div class="kv">${a1c}</div>
      <h3 style="margin-top:14px">Genetics &amp; family</h3><div class="kv">${gen}<span>Polygenic risk (z)</span><b>${fmt(pf.prs, 2)}</b>
      ${pf.family_history.map((f) => `<span>${esc(f.relation)}</span><b>${esc(f.condition)}</b>`).join("")}</div></div>
    <div class="chart-card rec"><h3>Conditions &amp; medications</h3><div class="kv">
      ${pf.conditions.map((c) => `<span>${esc(c.name)}</span><b>${esc(c.onset)}</b>`).join("")}
      ${pf.medications.map((m) => `<span>${esc(m.name)}</span><b>${esc(m.sig)}</b>`).join("")}</div></div>
    <div class="chart-card rec" style="grid-column:1/-1"><div class="chart-head"><h3>FHIR R4 · <span id="fhir-mode">input bundle (LOINC / SNOMED-CT / RxNorm, Synthea-compatible)</span></h3>
      <div style="display:flex;gap:8px"><button class="ghost-btn" id="fhir-in">EHR input</button><button class="btn-primary" id="fhir-out" style="padding:7px 12px">Export twin prediction as FHIR</button><button class="ghost-btn" id="fhir-dl">Download</button></div></div>
      <div class="code" id="fhir">loading…</div></div>`;
  const show = async (kind) => {
    $("#fhir").textContent = "loading…";
    try {
      const b = await api(kind === "out" ? `fhir-out/${S.pid}?t=${S.t}` : "fhir/" + S.pid);
      S.fhirDoc = b;
      $("#fhir").textContent = JSON.stringify(b, null, 1);
      $("#fhir-mode").textContent = kind === "out" ? "output bundle: RiskAssessment + forecast Observations + Communication (nudge)" : "input bundle (LOINC / SNOMED-CT / RxNorm, Synthea-compatible)";
    } catch { $("#fhir").textContent = "unavailable"; }
  };
  $("#fhir-in").addEventListener("click", () => show("in"));
  $("#fhir-out").addEventListener("click", () => show("out"));
  $("#fhir-dl").addEventListener("click", () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(S.fhirDoc, null, 2)], { type: "application/fhir+json" }));
    a.download = `${S.pid}_fhir.json`; a.click();
  });
  show("in");
}

// ------------------------------------------------------------------ insights tab
async function renderInsights() {
  const box = $("#insights");
  const key = S.pid + ":" + S.t;
  if (S.insKey === key) return;
  S.insKey = key;
  box.innerHTML = '<div class="shimmer"></div><div class="shimmer"></div>';
  const I = await api(`insights/${S.pid}?t=${S.t}`);
  if (S.insKey !== key) return;
  const icon = { high: "!", medium: "▲", info: "i", good: "✓" };
  const eaten = new Set(S.P.meals.map((m) => m.food));
  const tr = I.track || {};
  const t60 = tr["60"], t120 = tr["120"], t30 = tr["30"];
  box.innerHTML = `
    <div class="chart-card"><div class="chart-head"><h3>AI clinical brief</h3><span class="muted small">mined from ${I.brief.n_meals_analysed} meals, sleep, activity &amp; meds</span></div>
      <div class="brief-head">${esc(I.brief.headline)}</div>
      ${I.brief.findings.map((f, i) => `<div class="finding ${f.severity}" style="animation-delay:${i * 70}ms"><div class="ic">${icon[f.severity]}</div><div><b>${esc(f.title)}</b><p>${esc(f.detail)}</p></div><div class="met">${f.metric ?? ""}</div></div>`).join("") || '<p class="muted">No notable patterns yet.</p>'}
    </div>
    <div class="chart-card"><div class="chart-head"><h3>Personal glycaemic index</h3><span class="muted small">twin-simulated peak rise · 1 serving at lunch</span></div>
      <p class="muted small" style="margin:0 0 8px">How <b>this</b> patient's physiology responds to each Indian food today, simulated on the adaptive twin rather than taken from a population table. Highlighted foods were eaten recently.</p>
      <div class="pgi-list" id="pgi"></div></div>
    <div class="chart-card"><div class="chart-head"><h3>Twin track record · last 24 h</h3><span class="muted small">60-min forecasts vs what happened</span></div>
      <div class="trk-stats">${[["30", t30], ["60", t60], ["120", t120]].filter(([, v]) => v).map(([h, v]) => `<div><b>${fmt(v.mae, 1)}</b><span>MAE ${h} min · ${v.n} forecasts</span></div><div><b>${fmt(v.coverage)}%</b><span>inside 80% band (${h} min)</span></div>`).slice(0, 4).join("")}</div>
      <div id="track-chart" class="chart"></div></div>
    <div class="chart-card"><div class="chart-head"><h3>Adaptive twin · daily re-calibration</h3><span class="muted small">multipliers vs onboarding</span></div>
      <p class="muted small" style="margin:0 0 6px">Every midnight the twin re-estimates insulin sensitivity and the hepatic set-point from the previous day's CGM, using a Bayesian random-walk prior. Learned dawn phenomenon: <b>${fmt(I.dawn, 2)} mg/dL/min</b>.</p>
      <div id="drift-chart" class="chart"></div></div>`;
  Charts.pgi($("#pgi"), I.pgi.foods, eaten);
  if (t60) Charts.track($("#track-chart"), t60);
  const day = Math.floor(S.t / 1440) + 1;
  Charts.drift($("#drift-chart"), I.adapt.si.slice(0, day), I.adapt.gb.slice(0, day));
}

// ------------------------------------------------------------------ guided tour
const TOUR = [
  { sel: ".cohort", title: "Clinic triage: 40 live digital twins", text: "Every patient has a personalised physiological twin, ranked by predicted risk and time to event. The rings show 2-hour spike probability.", at: () => {} },
  { sel: "#stage", title: "The living twin", text: "Organs glow from the twin's state: pancreas insulin, liver output, gut absorption, heart, stress and muscle uptake. Blood is coloured by glucose, and a 3D ribbon spirals through the last 24 hours. Data streams from the EHR and wearables fuse into the body.", at: () => {} },
  { sel: "#alert-card", title: "A spike, 90 minutes before it happens", text: "It is Navratri. Rajesh's twin sees fasting foods in today's log and expects a sabudana lunch. Spike risk is about 80%, crossing 180 in about 1 h 30 m, with a calibrated 80% interval.", at: () => {} },
  { sel: "#drivers-card", title: "Why: causal attribution", text: "Exact Shapley values over 32 counterfactual twin simulations: the meal's glycaemic load dominates, followed by post-meal inactivity.", at: () => {} },
  { sel: "#nudge-card", title: "A twin-tested nudge, in Hindi", text: "The smallest change with the biggest effect is chosen by simulation and written in English and Hindi, ready to send to the patient.", at: () => {} },
  { sel: ".workspace", title: "Track record you can see", text: "Dashed lines show what the twin forecast 1 h and 2 h ago, plotted against what actually happened. Trust is earned in the open.", at: () => setTab("forecast") },
  { sel: ".workspace", title: "What-If Lab: prescribe a simulation", text: "The twin searches 54 possible tomorrows and recommends the plan with the best benefit for the effort.", at: () => { setTab("whatif"); setTimeout(runOptimise, 400); } },
  { sel: "#stage", title: "Ghost twin: two futures, side by side", text: "Left: tomorrow on current habits. Right: tomorrow with the plan. Both are time-lapsed through 24 hours of simulated physiology, in sync with the chart below.", at: () => setTab("whatif") },
  { sel: ".workspace", title: "AI insights: the personal glycaemic index", text: "Patterns are mined from 14 days of data, and every Indian food is simulated on this patient's own physiology.", at: () => setTab("insights") },
  { sel: ".workspace", title: "Validated honestly", text: "Held-out patients, five baselines, Clarke error grid, conformal coverage, calibration and data efficiency. The hybrid beats them all.", at: () => setTab("model") },
];
let tourI = -1, tourTimer;
function tourGo(i) {
  clearTimeout(tourTimer);
  if (i < 0 || i >= TOUR.length) return tourEnd();
  tourI = i;
  const st = TOUR[i];
  st.at();
  setTimeout(() => {
    const el = $(st.sel);
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => {
      const r = el.getBoundingClientRect(), pad = 8;
      Object.assign($("#tour-spot").style, { left: r.left - pad + "px", top: r.top - pad + "px", width: r.width + pad * 2 + "px", height: r.height + pad * 2 + "px" });
      const card = $("#tour-card"), cw = 360;
      let x = r.right + 20, y = r.top;
      if (x + cw > innerWidth - 10) x = r.left - cw - 20;
      if (x < 10) { x = Math.min(innerWidth - cw - 10, Math.max(10, r.left)); y = Math.min(innerHeight - 220, r.bottom + 16); }
      card.style.left = x + "px"; card.style.top = Math.max(10, Math.min(innerHeight - 220, y)) + "px";
      const dur = i === 6 || i === 7 ? 9000 : 7000;
      card.innerHTML = `<div class="step">STEP ${i + 1} / ${TOUR.length}</div><h4>${st.title}</h4><p>${st.text}</p><div class="tbar"><i id="tbar"></i></div>
        <div class="tnav"><button class="ghost-btn" id="t-prev">← Back</button><button class="ghost-btn" id="t-end">End tour</button><button class="btn-primary" id="t-next" style="padding:6px 12px">Next →</button></div>`;
      $("#t-prev").onclick = () => tourGo(i - 1); $("#t-next").onclick = () => tourGo(i + 1); $("#t-end").onclick = tourEnd;
      requestAnimationFrame(() => { const b = $("#tbar"); b.style.transition = `width ${dur}ms linear`; b.style.width = "100%"; });
      tourTimer = setTimeout(() => tourGo(i + 1), dur);
    }, 550);
  }, 250);
}
async function tourStart() {
  if (S.pid !== "SNJ-001" || S.t !== S.meta.default.t) {
    S.pid = "SNJ-001"; S.t = S.meta.default.t; $("#scrub-range").value = S.t; renderClock(); await load(true);
  }
  if (S.playing) togglePlay();
  $("#tour").hidden = false;
  tourGo(0);
}
function tourEnd() { clearTimeout(tourTimer); tourI = -1; $("#tour").hidden = true; }

// ------------------------------------------------------------------ model card
let M = null;
async function renderModel() {
  M = M || await api("metrics");
  const R = M.regression, sp = M.spike, ev = M.events.hybrid;
  const red = (1 - R.hybrid["120"].rmse / R.persistence["120"].rmse) * 100;
  const names = { persistence: "Persistence (no change)", linear_trend: "Linear trend", twin_only: "Physics twin only", ml_only: "ML only (no twin)", hybrid: "Sanjeevani hybrid" };
  const regRows = Object.keys(names).map((k) => `<tr class="${k === "hybrid" ? "ours" : ""}"><td>${names[k]}</td>${["30", "60", "120"].map((h) => `<td>${R[k][h].rmse.toFixed(1)}</td>`).join("")}<td>${R[k]["120"].mard.toFixed(1)}%</td><td>${R[k]["120"].clarke_AB.toFixed(1)}%</td></tr>`).join("");
  const spNames = { trend: "Linear trend", twin_only: "Physics twin only", ml_only: "ML only (no twin)", hybrid: "Sanjeevani hybrid" };
  const spRows = Object.keys(spNames).map((k) => `<tr class="${k === "hybrid" ? "ours" : ""}"><td>${spNames[k]}</td><td>${sp[k].auroc.toFixed(3)}</td><td>${sp[k].auprc.toFixed(3)}</td><td>${(sp[k].sensitivity * 100).toFixed(0)}%</td><td>${(sp[k].precision * 100).toFixed(0)}%</td><td>${M.events[k] ? M.events[k].false_alerts_per_day.toFixed(2) : "—"}</td></tr>`).join("");
  $("#modelcard").innerHTML = `
    <div class="big-stats">
      <div class="bs"><b>${R.hybrid["120"].rmse.toFixed(1)}</b><span>mg/dL RMSE at 2 h · ${red.toFixed(0)}% lower than persistence</span></div>
      <div class="bs"><b>${sp.hybrid.auroc.toFixed(2)}</b><span>AUROC for a new spike above 180 within 2 h</span></div>
      <div class="bs"><b>${ev.median_lead.toFixed(0)} min</b><span>median warning time · ${ev.detected_30min.toFixed(0)}% of events flagged at least 30 min ahead</span></div>
      <div class="bs"><b>${M.coverage["120"].toFixed(0)}%</b><span>coverage of the conformal 80% interval (2 h)</span></div>
    </div>
    <div class="chart-card"><h3>Glucose forecast error on ${M.n_test_patients} held-out patients (${M.test_days.toFixed(0)} patient-days)</h3>
      <table class="mtable"><thead><tr><th>Model</th><th>RMSE 30m</th><th>60m</th><th>120m</th><th>MARD 2h</th><th>Clarke A+B</th></tr></thead><tbody>${regRows}</tbody></table></div>
    <div class="chart-card"><h3>2-hour spike prediction · ${ev.events} real excursion events</h3>
      <table class="mtable"><thead><tr><th>Model</th><th>AUROC</th><th>AUPRC</th><th>Sens.</th><th>Prec.</th><th>False alerts/day</th></tr></thead><tbody>${spRows}</tbody></table></div>
    <div class="chart-card"><div class="chart-head"><h3>Data efficiency: physics needs fewer patients</h3><div class="legend"><span><i class="sw line" style="--c:var(--c1)"></i>Twin + AI</span><span><i class="sw line" style="--c:var(--c2)"></i>ML only</span></div></div>
      <div id="lc-chart" class="chart"></div><p class="muted small">RMSE at 2 h (mg/dL) versus number of training patients. With zero training patients, the calibrated physics twin alone already scores ${M.learning_curve[0].hybrid_rmse.toFixed(1)}.</p></div>
    <div class="chart-card"><h3>What the classifier relies on (grouped permutation importance, AUROC drop)</h3><div id="imp-chart"></div></div>
    <div class="chart-card"><div class="chart-head"><h3>Clarke error grid · 2-h forecasts</h3><span class="muted small">${R.hybrid["120"].clarke_A.toFixed(1)}% zone A · ${R.hybrid["120"].clarke_AB.toFixed(1)}% A+B</span></div><div id="clarke-chart" class="chart"></div></div>
    <div class="chart-card"><div class="chart-head"><h3>Calibration of spike probability</h3><span class="muted small">reliability diagram</span></div><div id="rel-chart" class="chart"></div></div>
    <div class="chart-card" style="grid-column:1/-1"><h3>Intended use, data &amp; limitations</h3><ul class="notes">
      <li><b>Intended use:</b> decision support for clinicians managing adults with Type 2 Diabetes. It flags likely glucose excursions about 2 h ahead and tests lifestyle plans on a personalised simulation. It is not a medical device, and it does not dose insulin.</li>
      <li><b>Data:</b> 40 synthetic Indian patients × 14 days (FHIR R4 EHR, CGM at 5 min, HR, HRV, sleep stages, steps, meal and medication logs). There is no real patient data, in line with the DPDP Act 2023 and HIPAA. Held-out patients were never seen in training; conformal offsets and thresholds come from separate calibration patients.</li>
      <li><b>Honest misspecification:</b> the ground-truth simulator includes effects the twin does not model: dawn phenomenon, unlogged snacks, carb-count error, day-to-day insulin-sensitivity drift, latent stress, CGM lag, noise and dropouts.</li>
      <li><b>Limitations:</b> synthetic physiology is not a substitute for clinical validation. The next steps are retrospective validation on open CGM datasets (e.g. PhysioNet BIG IDEAs), then a prospective silent-mode pilot.</li></ul></div>`;
  Charts.learning($("#lc-chart"), M.learning_curve);
  Charts.hbars($("#imp-chart"), Object.entries(M.importance.auroc_drop).sort((a, b) => b[1] - a[1]).map(([k, v]) => ({ k, v: Math.max(0, v) })));
  Charts.clarke($("#clarke-chart"), M.clarke_points);
  Charts.reliability($("#rel-chart"), M.reliability);
}

boot();
