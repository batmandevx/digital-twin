/* Sanjeevani: lightweight animated SVG charts (no dependencies). */
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const C = () => ({ c1: css("--c1"), c2: css("--c2"), c3: css("--c3"), c4: css("--c4"), c5: css("--c5"),
    ok: css("--ok"), warn: css("--warn"), bad: css("--bad"), low: css("--low"), ink: css("--ink"), muted: css("--muted"), grid: css("--grid") });
  const scale = (d0, d1, r0, r1) => { const f = (v) => r0 + (v - d0) / (d1 - d0 || 1) * (r1 - r0); f.inv = (p) => d0 + (p - r0) / (r1 - r0) * (d1 - d0); return f; };
  const hhmm = (m) => { m = ((m % 1440) + 1440) % 1440; return String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(Math.floor(m % 60)).padStart(2, "0"); };
  const path = (pts) => { let d = "", pen = false; for (const p of pts) { if (p == null || p[1] == null || isNaN(p[1])) { pen = false; continue; } d += (pen ? "L" : "M") + p[0].toFixed(1) + "," + p[1].toFixed(1); pen = true; } return d; };
  const svg = (el, w, h) => { el.innerHTML = ""; const s = document.createElementNS(NS, "svg"); s.setAttribute("viewBox", `0 0 ${w} ${h}`); s.setAttribute("width", w); s.setAttribute("height", h); el.appendChild(s); return s; };
  const add = (parent, tag, attrs = {}, text) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (text != null) e.textContent = text; parent.appendChild(e); return e; };
  const tipEl = () => document.getElementById("tooltip");
  const tip = (html, x, y) => { const t = tipEl(); t.innerHTML = html; t.style.left = x + "px"; t.style.top = y + "px"; t.classList.add("on"); };
  const hideTip = () => tipEl().classList.remove("on");
  const animateLine = (p) => { requestAnimationFrame(() => { const L = p.getTotalLength ? p.getTotalLength() : 1000; p.style.setProperty("--len", L); p.classList.add("drawn"); }); };
  const zoneColor = (g) => { const c = C(); return g == null ? c.muted : g < 70 ? c.low : g <= 180 ? c.ok : g <= 250 ? c.warn : c.bad; };

  function glucoseGradient(s, id, y) {
    const c = C();
    const defs = add(s, "defs");
    const lg = add(defs, "linearGradient", { id, gradientUnits: "userSpaceOnUse", x1: 0, x2: 0, y1: y(400), y2: y(40) });
    const stop = (v, col) => add(lg, "stop", { offset: ((v - 400) / (40 - 400)).toFixed(4), "stop-color": col });
    stop(400, c.bad); stop(252, c.bad); stop(248, c.warn); stop(182, c.warn); stop(178, c.ok); stop(72, c.ok); stop(68, c.low); stop(40, c.low);
    return defs;
  }

  // ------------------------------------------------------------- glucose
  function glucose(el, P) {
    const c = C();
    const W = el.clientWidth || 800, H = 300, m = { l: 40, r: 54, t: 34, b: 24 };
    const s = svg(el, W, H);
    const t = P.t, fc = P.prediction.forecast;
    let tl = P.timeline;
    const x = scale(t - 720, t + 125, m.l, W - m.r);
    const vals = tl.cgm.filter((v) => v != null).concat(fc.map((f) => f.hi));
    const ymax = Math.max(300, Math.ceil((Math.max(...vals) + 20) / 50) * 50);
    const y = scale(40, ymax, H - m.b, m.t);
    const defs = glucoseGradient(s, "gz", y);
    const cg = add(defs, "linearGradient", { id: "cone", x1: 0, x2: 1, y1: 0, y2: 0 });
    add(cg, "stop", { offset: 0, "stop-color": c.c1, "stop-opacity": .45 }); add(cg, "stop", { offset: 1, "stop-color": c.c1, "stop-opacity": .12 });

    // sleep bands
    let start = null;
    tl.sleep.forEach((st, i) => {
      const mm = tl.minute[i];
      if (mm < t - 720) return;
      if (st > 0 && start == null) start = mm;
      if ((st === 0 || i === tl.sleep.length - 1) && start != null) {
        add(s, "rect", { x: x(start), y: m.t, width: Math.max(0, x(mm) - x(start)), height: H - m.t - m.b, fill: "rgba(143,124,240,.06)" });
        add(s, "text", { x: x(start) + 6, y: m.t + 12, fill: c.muted, "font-size": 10 }, "☾ sleep");
        start = null;
      }
    });
    add(s, "rect", { class: "band-target", x: m.l, y: y(180), width: W - m.l - m.r, height: y(70) - y(180) });
    const g = add(s, "g", { class: "ax" });
    for (let v = 50; v <= ymax; v += 50) {
      add(g, "line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), class: "gridline" });
      add(g, "text", { x: m.l - 8, y: y(v) + 3, "text-anchor": "end" }, v);
    }
    const first = Math.ceil((t - 720) / 120) * 120;
    for (let mm = first; mm <= t + 120; mm += 120) add(g, "text", { x: x(mm), y: H - 6, "text-anchor": "middle" }, hhmm(mm));
    for (const [v, col, lab] of [[70, c.low, "70 low"], [180, c.warn, "180 high"], [250, c.bad, "250"]]) {
      add(s, "line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: col, class: "thr-line", opacity: .55 });
      add(s, "text", { x: W - m.r + 6, y: y(v) + 3, fill: c.muted, "font-size": 10 }, lab);
    }
    // twin (assimilated) + CGM, restricted to the visible 12 h
    const vis = tl.minute.map((mm) => mm >= t - 720);
    tl = { ...tl, minute: tl.minute.filter((_, i) => vis[i]), cgm: tl.cgm.filter((_, i) => vis[i]), twin: tl.twin.filter((_, i) => vis[i]),
           hr: tl.hr.filter((_, i) => vis[i]), steps: tl.steps.filter((_, i) => vis[i]) };
    const twin = add(s, "path", { d: path(tl.minute.map((mm, i) => [x(mm), y(tl.twin[i])])), fill: "none", stroke: c.c4, "stroke-width": 1, opacity: .35, "stroke-dasharray": "2 3" });
    const line = add(s, "path", { d: path(tl.minute.map((mm, i) => [x(mm), tl.cgm[i] == null ? null : y(tl.cgm[i])])), fill: "none", stroke: "url(#gz)", "stroke-width": 2.2, "stroke-linejoin": "round", "stroke-linecap": "round" });
    animateLine(line);
    // forecast cone
    const g0 = P.prediction.g_now;
    const pts = [{ m: 0, lo: g0, mid: g0, hi: g0, twin: g0 }].concat(fc);
    const top = pts.map((p) => [x(t + p.m), y(p.hi)]), bot = pts.slice().reverse().map((p) => [x(t + p.m), y(p.lo)]);
    add(s, "path", { class: "cone", d: path(top) + path(bot).replace("M", "L") + "Z", fill: "url(#cone)" });
    add(s, "path", { class: "cone", d: path(pts.map((p) => [x(t + p.m), y(p.twin)])), fill: "none", stroke: c.c4, "stroke-width": 1.6, "stroke-dasharray": "1 3", "stroke-linecap": "round" });
    const mid = add(s, "path", { class: "cone", d: path(pts.map((p) => [x(t + p.m), y(p.mid)])), fill: "none", stroke: c.c1, "stroke-width": 2.2, "stroke-dasharray": "6 4" });
    // peak label
    const pk = fc.reduce((a, b) => (b.mid > a.mid ? b : a), fc[0]);
    if (pk.mid > 175) {
      add(s, "circle", { cx: x(t + pk.m), cy: y(pk.mid), r: 4, fill: c.bad, stroke: css("--surface"), "stroke-width": 2, class: "cone" });
      add(s, "text", { x: x(t + pk.m), y: y(pk.hi) - 8, "text-anchor": "middle", fill: c.ink, "font-size": 11, "font-weight": 600, class: "cone" }, `peak ${Math.round(pk.mid)}`);
    }
    // track record: what the twin forecast 2 h and 1 h ago, against what happened
    for (const pf of P.past_forecasts || []) {
      const pts2 = [[pf.made, null]].concat(pf.pts).filter((q) => q[1] != null).map(([mm, v]) => [x(mm), y(v)]);
      const pp = add(s, "path", { d: path(pts2), fill: "none", stroke: pf.back === 120 ? c.c3 : c.c2, "stroke-width": 1.6, "stroke-dasharray": "2 3", opacity: .85, class: "cone" });
      const last = pf.pts[pf.pts.length - 1];
      if (last) add(s, "circle", { cx: x(last[0]), cy: y(last[1]), r: 3, fill: pf.back === 120 ? c.c3 : c.c2, class: "cone" });
      add(s, "circle", { cx: x(pf.made), cy: y(pf.pts[0] ? pf.pts[0][1] : 100), r: 2.5, fill: "none", stroke: pf.back === 120 ? c.c3 : c.c2, class: "cone" });
    }
    // now
    add(s, "line", { x1: x(t), x2: x(t), y1: m.t - 10, y2: H - m.b, class: "now-line" });
    add(s, "text", { x: x(t), y: m.t - 14, "text-anchor": "middle", fill: c.ink, "font-size": 10.5, "font-weight": 600 }, "NOW");
    add(s, "rect", { x: x(t) + 2, y: m.t - 24, width: x(t + 120) - x(t) - 2, height: 14, rx: 4, fill: "rgba(26,163,192,.12)" });
    add(s, "text", { x: (x(t) + x(t + 120)) / 2, y: m.t - 14, "text-anchor": "middle", fill: c.c1, "font-size": 10, "font-weight": 600 }, "2-h FORECAST");
    if (g0 != null) {
      add(s, "circle", { cx: x(t), cy: y(g0), r: 5, fill: zoneColor(g0), class: "pulse" });
      add(s, "circle", { cx: x(t), cy: y(g0), r: 4.5, fill: zoneColor(g0), stroke: css("--surface"), "stroke-width": 2 });
    }
    // meals
    const meal = (mm, icon, label, ghost) => {
      const gg = add(s, "g", { class: "meal-mk" });
      add(gg, "line", { x1: x(mm), x2: x(mm), y1: m.t + 2, y2: H - m.b, stroke: ghost ? c.c3 : "rgba(255,255,255,.12)", "stroke-dasharray": ghost ? "3 3" : "none" });
      add(gg, "circle", { cx: x(mm), cy: m.t + 2, r: 11, fill: ghost ? "rgba(196,131,31,.15)" : "rgba(13,24,54,.9)", stroke: ghost ? c.c3 : "rgba(255,255,255,.25)", "stroke-dasharray": ghost ? "3 2" : "none" });
      add(gg, "text", { x: x(mm), y: m.t + 7, "text-anchor": "middle" }, icon);
      gg.addEventListener("mousemove", (e) => tip(`<div class="tt-h">${hhmm(mm)} · ${ghost ? "expected (habit-aware twin)" : "logged meal"}</div>${label}`, e.clientX, e.clientY));
      gg.addEventListener("mouseleave", hideTip);
    };
    for (const ml of P.meals.filter((q) => q.minute >= t - 720)) meal(ml.minute, ml.icon, `${ml.name} · <b>${ml.carbs} g</b> carbs`);
    for (const ex of P.expected_meals) meal(ex.minute, ex.icon, `${ex.name}${ex.fasting ? " (fasting day)" : ""} · ~${ex.carbs} g`, true);

    // hover
    const cross = add(s, "line", { class: "crosshair", y1: m.t, y2: H - m.b, opacity: 0 });
    const hit = add(s, "rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: "transparent" });
    hit.addEventListener("mousemove", (e) => {
      const r = s.getBoundingClientRect();
      const px = (e.clientX - r.left) * (W / r.width);
      const mm = x.inv(px);
      cross.setAttribute("x1", px); cross.setAttribute("x2", px); cross.setAttribute("opacity", 1);
      let html;
      if (mm <= t) {
        const i = Math.max(0, Math.min(tl.minute.length - 1, Math.round((mm - tl.minute[0]) / 5)));
        html = `<div class="tt-h">${hhmm(tl.minute[i])}</div><div class="tt-r">CGM <b>${tl.cgm[i] ?? "—"}</b></div><div class="tt-r">Twin <b>${Math.round(tl.twin[i])}</b></div><div class="tt-r">HR <b>${tl.hr[i] ?? "—"}</b></div><div class="tt-r">Steps <b>${tl.steps[i]}</b></div>`;
      } else {
        const f = fc[Math.max(0, Math.min(fc.length - 1, Math.round((mm - t) / 5) - 1))];
        html = `<div class="tt-h">${hhmm(t + f.m)} · +${f.m} min forecast</div><div class="tt-r">Median <b>${Math.round(f.mid)}</b></div><div class="tt-r">80% interval <b>${Math.round(f.lo)}–${Math.round(f.hi)}</b></div><div class="tt-r">Physics only <b>${Math.round(f.twin)}</b></div>`;
      }
      tip(html, e.clientX, e.clientY);
    });
    hit.addEventListener("mouseleave", () => { hideTip(); cross.setAttribute("opacity", 0); });
    s.insertBefore(hit, s.querySelector(".meal-mk"));
  }

  // ------------------------------------------------------------- strip (steps + sleep)
  function strip(el, P) {
    const c = C();
    const W = el.clientWidth || 800, H = 52, m = { l: 40, r: 54 };
    const s = svg(el, W, H);
    const t = P.t, tl = P.timeline;
    const x = scale(t - 720, t + 125, m.l, W - m.r);
    const mx = Math.max(200, ...tl.steps);
    const bw = Math.max(1, (x(5) - x(0)) - .6);
    add(s, "text", { x: m.l - 8, y: 16, "text-anchor": "end", fill: c.muted, "font-size": 10 }, "steps");
    add(s, "text", { x: m.l - 8, y: 44, "text-anchor": "end", fill: c.muted, "font-size": 10 }, "sleep");
    tl.steps.forEach((v, i) => { if (v > 5 && tl.minute[i] >= t - 720) add(s, "rect", { x: x(tl.minute[i]), y: 26 - v / mx * 24, width: bw, height: v / mx * 24, fill: c.c5, rx: .5, opacity: .85 }); });
    const sc = [null, c.c1, c.c4, c.c2];
    tl.sleep.forEach((st, i) => { if (st > 0 && tl.minute[i] >= t - 720) add(s, "rect", { x: x(tl.minute[i]), y: 34, width: bw + .6, height: 12, fill: sc[st], opacity: st === 2 ? .95 : .6 }); });
    add(s, "line", { x1: x(t), x2: x(t), y1: 0, y2: H, class: "now-line" });
  }

  // ------------------------------------------------------------- sleep (stacked bars)
  function sleep(el, nights, legendEl) {
    const c = C();
    const W = el.clientWidth || 360, H = 190, m = { l: 46, r: 30, t: 6, b: 18 };
    const s = svg(el, W, H);
    const segs = [["deep", "Deep", c.c4], ["rem", "REM", c.c2], ["light", "Light", c.c1], ["awake", "Awake", "#53627f"]];
    if (legendEl) legendEl.innerHTML = segs.map(([, n, col]) => `<span><i class="sw box" style="background:${col}"></i>${n}</span>`).join("");
    const x = scale(0, 9, m.l, W - m.r);
    const n = Math.max(1, nights.length), bh = Math.min(18, (H - m.t - m.b) / n - 5);
    add(s, "line", { x1: x(7), x2: x(7), y1: m.t, y2: H - m.b, stroke: c.ok, class: "thr-line", opacity: .6 });
    add(s, "text", { x: x(7), y: H - 4, "text-anchor": "middle", fill: c.muted, "font-size": 10 }, "7 h target");
    nights.forEach((nt, i) => {
      const yy = m.t + i * (bh + 5);
      const d = new Date(Date.parse(window.__START) + nt.wake * 60000);
      add(s, "text", { x: m.l - 8, y: yy + bh / 2 + 3.5, "text-anchor": "end", fill: c.muted, "font-size": 10 }, d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", timeZone: "Asia/Kolkata" }));
      let x0 = 0;
      segs.forEach(([k, name, col], j) => {
        const v = nt[k] * (nt.hours / Math.max(.01, 1 - nt.awake)) * (k === "awake" ? 1 : 1);
        const hrs = k === "awake" ? nt.awake * nt.hours / Math.max(.01, 1 - nt.awake) : nt[k] * nt.hours / Math.max(.01, 1 - nt.awake);
        const wpx = Math.max(0, x(x0 + hrs) - x(x0) - 2);
        const r = add(s, "rect", { x: x(x0), y: yy, width: 0, height: bh, rx: 4, fill: col });
        setTimeout(() => { r.style.transition = "width .8s cubic-bezier(.2,.8,.2,1)"; r.setAttribute("width", wpx); }, 60 + i * 50);
        r.addEventListener("mousemove", (e) => tip(`<div class="tt-h">Night ending ${d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}</div><div class="tt-r">${name} <b>${hrs.toFixed(1)} h</b></div><div class="tt-r">Total sleep <b>${nt.hours.toFixed(1)} h</b></div>`, e.clientX, e.clientY));
        r.addEventListener("mouseleave", hideTip);
        x0 += hrs;
      });
      add(s, "text", { x: x(x0) + 5, y: yy + bh / 2 + 3.5, fill: c.ink, "font-size": 10.5, "font-family": "JetBrains Mono" }, nt.hours.toFixed(1) + "h");
    });
  }

  // ------------------------------------------------------------- daily TIR
  function tir(el, daily) {
    const c = C();
    const W = el.clientWidth || 360, H = 190, m = { l: 30, r: 8, t: 14, b: 30 };
    const s = svg(el, W, H);
    const x = scale(0, daily.length, m.l, W - m.r), y = scale(0, 100, H - m.b, m.t);
    for (const v of [0, 50, 70, 100]) {
      add(s, "line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: v === 70 ? c.ok : c.grid, class: v === 70 ? "thr-line" : "", opacity: v === 70 ? .6 : 1 });
      add(s, "text", { x: m.l - 6, y: y(v) + 3, "text-anchor": "end", fill: c.muted, "font-size": 10 }, v);
    }
    add(s, "text", { x: W - m.r, y: y(70) - 4, "text-anchor": "end", fill: c.muted, "font-size": 9.5 }, "70% goal");
    const bw = Math.max(4, (W - m.l - m.r) / daily.length - 4);
    daily.forEach((d, i) => {
      const xx = x(i) + 2;
      const r = add(s, "rect", { x: xx, y: y(0), width: bw, height: 0, rx: 4, fill: c.c1, opacity: d.navratri ? 1 : .8 });
      setTimeout(() => { r.style.transition = "all .7s cubic-bezier(.2,.8,.2,1)"; r.setAttribute("y", y(d.tir)); r.setAttribute("height", y(0) - y(d.tir)); }, 40 * i);
      if (d.navratri) add(s, "text", { x: xx + bw / 2, y: H - 2, "text-anchor": "middle", fill: c.warn, "font-size": 9 }, "✦");
      if (i % 2 === 0 || daily.length < 9) add(s, "text", { x: xx + bw / 2, y: H - m.b + 13, "text-anchor": "middle", fill: c.muted, "font-size": 9.5 }, d.date.split(" ")[0]);
      const hit = add(s, "rect", { x: xx - 2, y: m.t, width: bw + 4, height: H - m.t - m.b, fill: "transparent" });
      hit.addEventListener("mousemove", (e) => tip(`<div class="tt-h">${d.date}${d.navratri ? " · Navratri" : ""}${d.festival ? " · " + d.festival : ""}</div><div class="tt-r">Time in range <b>${d.tir}%</b></div><div class="tt-r">Above 180 <b>${d.tar}%</b></div><div class="tt-r">Mean <b>${d.mean}</b></div><div class="tt-r">Steps <b>${d.steps.toLocaleString("en-IN")}</b></div>`, e.clientX, e.clientY));
      hit.addEventListener("mouseleave", hideTip);
    });
  }

  // ------------------------------------------------------------- HRV + stress (small multiples)
  function hrv(el, P) {
    const c = C();
    const W = el.clientWidth || 360, H = 190, m = { l: 34, r: 8, t: 10 };
    const s = svg(el, W, H);
    const tl = P.timeline;
    const x = scale(tl.minute[0], tl.minute[tl.minute.length - 1], m.l, W - m.r);
    const vals = tl.hrv.filter((v) => v != null);
    const smooth = tl.hrv.map((_, i) => { const w = tl.hrv.slice(Math.max(0, i - 3), i + 4).filter((v) => v != null); return w.length ? w.reduce((a, b) => a + b, 0) / w.length : null; });
    const y1 = scale(Math.min(...vals) * .9, Math.max(...vals) * 1.05, 100, m.t);
    add(s, "text", { x: m.l, y: m.t + 2, fill: c.muted, "font-size": 10 }, "HRV (RMSSD, ms)");
    for (const v of [Math.round(Math.min(...vals)), Math.round(Math.max(...vals))]) add(s, "text", { x: m.l - 6, y: y1(v) + 3, "text-anchor": "end", fill: c.muted, "font-size": 9.5 }, v);
    const p1 = add(s, "path", { d: path(tl.minute.map((mm, i) => [x(mm), smooth[i] == null ? null : y1(smooth[i])])), fill: "none", stroke: c.c4, "stroke-width": 1.8 });
    animateLine(p1);
    const y2 = scale(0, 1, 172, 124);
    add(s, "text", { x: m.l, y: 120, fill: c.muted, "font-size": 10 }, "Inferred stress (0–1)");
    add(s, "line", { x1: m.l, x2: W - m.r, y1: y2(0), y2: y2(0), stroke: c.grid });
    const ap = tl.minute.map((mm, i) => [x(mm), y2(tl.stress[i])]);
    add(s, "path", { d: path(ap) + `L${x(tl.minute[tl.minute.length - 1])},${y2(0)}L${x(tl.minute[0])},${y2(0)}Z`, fill: c.c2, opacity: .35 });
    add(s, "path", { d: path(ap), fill: "none", stroke: c.c2, "stroke-width": 1.5 });
    for (let mm = Math.ceil(tl.minute[0] / 360) * 360; mm <= tl.minute[tl.minute.length - 1]; mm += 360)
      add(s, "text", { x: x(mm), y: H - 4, "text-anchor": "middle", fill: c.muted, "font-size": 9.5 }, hhmm(mm));
    const cross = add(s, "line", { class: "crosshair", y1: m.t, y2: 172, opacity: 0 });
    const hit = add(s, "rect", { x: m.l, y: 0, width: W - m.l - m.r, height: H, fill: "transparent" });
    hit.addEventListener("mousemove", (e) => {
      const r = s.getBoundingClientRect(); const px = (e.clientX - r.left) * (W / r.width);
      const i = Math.max(0, Math.min(tl.minute.length - 1, Math.round((x.inv(px) - tl.minute[0]) / 5)));
      cross.setAttribute("x1", px); cross.setAttribute("x2", px); cross.setAttribute("opacity", 1);
      tip(`<div class="tt-h">${hhmm(tl.minute[i])}</div><div class="tt-r">HRV <b>${tl.hrv[i] ?? "—"} ms</b></div><div class="tt-r">HR <b>${tl.hr[i] ?? "—"}</b></div><div class="tt-r">Stress <b>${tl.stress[i]}</b></div>`, e.clientX, e.clientY);
    });
    hit.addEventListener("mouseleave", () => { hideTip(); cross.setAttribute("opacity", 0); });
  }

  // ------------------------------------------------------------- what-if
  function whatif(el, W0, spaghetti) {
    const c = C();
    const W = el.clientWidth || 700, H = 320, m = { l: 40, r: 54, t: 34, b: 24 };
    const s = svg(el, W, H);
    const mins = W0.minutes;
    const x = scale(mins[0] - 5, mins[mins.length - 1], m.l, W - m.r);
    const all = W0.baseline.concat(W0.scenario).concat(spaghetti ? spaghetti.curves.flat() : []);
    const ymax = Math.max(260, Math.ceil((Math.max(...all) + 15) / 50) * 50);
    const y = scale(40, ymax, H - m.b, m.t);
    add(s, "rect", { class: "band-target", x: m.l, y: y(180), width: W - m.l - m.r, height: y(70) - y(180) });
    for (let v = 50; v <= ymax; v += 50) {
      add(s, "line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), class: "gridline" });
      add(s, "text", { x: m.l - 8, y: y(v) + 3, "text-anchor": "end", fill: c.muted, "font-size": 10.5 }, v);
    }
    for (const [v, col, lab] of [[70, c.low, "70"], [180, c.warn, "180"]]) {
      add(s, "line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: col, class: "thr-line", opacity: .55 });
      add(s, "text", { x: W - m.r + 6, y: y(v) + 3, fill: c.muted, "font-size": 10 }, lab);
    }
    for (let mm = Math.ceil(mins[0] / 180) * 180; mm <= mins[mins.length - 1]; mm += 180)
      add(s, "text", { x: x(mm), y: H - 6, "text-anchor": "middle", fill: c.muted, "font-size": 10.5 }, hhmm(mm));
    if (spaghetti) {
      const g = add(s, "g");
      spaghetti.curves.forEach((cv, i) => {
        const p = add(g, "path", { d: path(cv.map((v, j) => [x(mins[j]), y(v)])), fill: "none", stroke: c.c1, "stroke-width": 1, opacity: 0 });
        setTimeout(() => { p.style.transition = "opacity .4s"; p.setAttribute("opacity", .16); }, 18 * i);
      });
      add(s, "text", { x: m.l + 8, y: H - m.b - 8, fill: c.ink, "font-size": 11.5, "font-weight": 600 }, `${spaghetti.curves.length} simulated tomorrows`);
    }
    const base = add(s, "path", { d: path(W0.baseline.map((v, j) => [x(mins[j]), y(v)])), fill: "none", stroke: c.muted, "stroke-width": 2, opacity: .9 });
    const diff = [];
    W0.scenario.forEach((v, j) => diff.push([x(mins[j]), y(v)]));
    const area = add(s, "path", { d: path(W0.baseline.map((v, j) => [x(mins[j]), y(v)])) + path(diff.slice().reverse()).replace("M", "L") + "Z", fill: c.ok, opacity: 0 });
    setTimeout(() => { area.style.transition = "opacity .8s"; area.setAttribute("opacity", .14); }, spaghetti ? 1200 : 300);
    const scn = add(s, "path", { d: path(diff), fill: "none", stroke: c.c1, "stroke-width": 2.6, "stroke-linecap": "round" });
    animateLine(scn);
    if (!spaghetti) animateLine(base);
    // meal markers
    for (const ml of W0.meals_scenario) {
      add(s, "line", { x1: x(ml.minute), x2: x(ml.minute), y1: m.t + 2, y2: H - m.b, stroke: "rgba(255,255,255,.1)" });
      add(s, "circle", { cx: x(ml.minute), cy: m.t + 2, r: 11, fill: "rgba(13,24,54,.9)", stroke: "rgba(255,255,255,.25)" });
      add(s, "text", { x: x(ml.minute), y: m.t + 7, "text-anchor": "middle", "font-size": 13 }, ml.icon);
    }
    // direct labels at the end
    const lb = W0.baseline[W0.baseline.length - 1], ls = W0.scenario[W0.scenario.length - 1];
    const cross = add(s, "line", { class: "crosshair", y1: m.t, y2: H - m.b, opacity: 0 });
    const hit = add(s, "rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: "transparent" });
    hit.addEventListener("mousemove", (e) => {
      const r = s.getBoundingClientRect(); const px = (e.clientX - r.left) * (W / r.width);
      const j = Math.max(0, Math.min(mins.length - 1, Math.round((x.inv(px) - mins[0]) / 5)));
      cross.setAttribute("x1", px); cross.setAttribute("x2", px); cross.setAttribute("opacity", 1);
      const d = W0.scenario[j] - W0.baseline[j];
      tip(`<div class="tt-h">${hhmm(mins[j])}</div><div class="tt-r">Current habits <b>${Math.round(W0.baseline[j])}</b></div><div class="tt-r">With plan <b>${Math.round(W0.scenario[j])}</b></div><div class="tt-r">Difference <b style="color:${d <= 0 ? c.ok : c.bad}">${d > 0 ? "+" : ""}${Math.round(d)}</b></div>`, e.clientX, e.clientY);
    });
    hit.addEventListener("mouseleave", () => { hideTip(); cross.setAttribute("opacity", 0); });
    // playback cursor (driven by the 3D ghost-twin time-lapse)
    const cur = add(s, "g", { opacity: 0 });
    const cl = add(cur, "line", { y1: m.t, y2: H - m.b, stroke: "#fff", "stroke-width": 1.2, opacity: .6 });
    const cb = add(cur, "circle", { r: 4.5, fill: c.muted, stroke: css("--surface"), "stroke-width": 2 });
    const cs = add(cur, "circle", { r: 5, fill: c.c1, stroke: css("--surface"), "stroke-width": 2 });
    return (j) => {
      if (j == null) { cur.setAttribute("opacity", 0); return; }
      const xx = x(mins[j]);
      cur.setAttribute("opacity", 1);
      cl.setAttribute("x1", xx); cl.setAttribute("x2", xx);
      cb.setAttribute("cx", xx); cb.setAttribute("cy", y(W0.baseline[j]));
      cs.setAttribute("cx", xx); cs.setAttribute("cy", y(W0.scenario[j]));
    };
  }

  // ------------------------------------------------------------- personal glycaemic index
  function pgi(el, foods, highlight) {
    const c = C();
    const mx = Math.max(...foods.map((f) => f.rise));
    el.innerHTML = foods.map((f, i) => {
      const col = f.rise > 120 ? c.bad : f.rise > 80 ? c.warn : f.rise > 50 ? c.c1 : c.ok;
      return `<div class="pgi-row ${highlight && highlight.has(f.food) ? "eaten" : ""}" style="animation-delay:${i * 25}ms" title="${f.name}: +${f.rise} mg/dL peak rise, peak at ${f.t_peak} min">
        <span class="pgi-ic">${f.icon}</span><span class="pgi-name">${f.name}<small>${f.hi} · ${f.carbs} g carbs</small></span>
        <span class="pgi-bar"><i style="--w:${f.rise / mx * 100}%;background:${col}"></i></span><b>+${Math.round(f.rise)}</b></div>`;
    }).join("");
  }

  // ------------------------------------------------------------- track record (forecast vs actual)
  function track(el, tr) {
    const c = C();
    const W = el.clientWidth || 400, H = 200, m = { l: 34, r: 10, t: 10, b: 22 };
    const s = svg(el, W, H);
    const pts = tr.pts;
    if (!pts || !pts.length) { el.innerHTML = '<p class="muted small">Not enough history yet.</p>'; return; }
    const xs = pts.map((p) => p[0]);
    const vals = pts.flatMap((p) => [p[1], p[2]]);
    const x = scale(Math.min(...xs), Math.max(...xs), m.l, W - m.r), y = scale(Math.min(60, ...vals) - 5, Math.max(...vals) + 10, H - m.b, m.t);
    for (const v of [70, 180]) { add(s, "line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: v === 180 ? c.warn : c.low, class: "thr-line", opacity: .5 }); add(s, "text", { x: m.l - 4, y: y(v) + 3, "text-anchor": "end", fill: c.muted, "font-size": 9.5 }, v); }
    const act = add(s, "path", { d: path(pts.map((p) => [x(p[0]), y(p[2])])), fill: "none", stroke: c.ink, "stroke-width": 1.8, opacity: .85 });
    animateLine(act);
    pts.forEach((p, i) => {
      add(s, "line", { x1: x(p[0]), x2: x(p[0]), y1: y(p[1]), y2: y(p[2]), stroke: c.c1, opacity: .35 });
      const d = add(s, "circle", { cx: x(p[0]), cy: y(p[1]), r: 3.2, fill: c.c1, stroke: css("--surface"), "stroke-width": 1.5, opacity: 0 });
      setTimeout(() => { d.style.transition = "opacity .3s"; d.setAttribute("opacity", 1); }, 300 + i * 12);
      d.addEventListener("mousemove", (e) => tip(`<div class="tt-h">${hhmm(p[0])}</div><div class="tt-r">Twin said <b>${Math.round(p[1])}</b></div><div class="tt-r">Actual <b>${Math.round(p[2])}</b></div><div class="tt-r">Error <b>${Math.round(p[1] - p[2])}</b></div>`, e.clientX, e.clientY));
      d.addEventListener("mouseleave", hideTip);
    });
    for (let i = 0; i < pts.length; i += Math.ceil(pts.length / 6)) add(s, "text", { x: x(pts[i][0]), y: H - 5, "text-anchor": "middle", fill: c.muted, "font-size": 9.5 }, hhmm(pts[i][0]));
  }

  // ------------------------------------------------------------- adaptive drift
  function drift(el, si, gb) {
    const c = C();
    const W = el.clientWidth || 300, H = 120, m = { l: 34, r: 10, t: 10, b: 20 };
    const s = svg(el, W, H);
    const x = scale(0, si.length - 1, m.l, W - m.r), y = scale(.75, 1.4, H - m.b, m.t);
    add(s, "line", { x1: m.l, x2: W - m.r, y1: y(1), y2: y(1), stroke: c.grid });
    for (const v of [.8, 1, 1.2, 1.4]) add(s, "text", { x: m.l - 4, y: y(v) + 3, "text-anchor": "end", fill: c.muted, "font-size": 9.5 }, v.toFixed(1));
    const p1 = add(s, "path", { d: path(si.map((v, i) => [x(i), y(v)])), fill: "none", stroke: c.c1, "stroke-width": 2 });
    const p2 = add(s, "path", { d: path(gb.map((v, i) => [x(i), y(v)])), fill: "none", stroke: c.c3, "stroke-width": 2 });
    animateLine(p1); animateLine(p2);
    si.forEach((v, i) => { if (i % 2 === 0) add(s, "text", { x: x(i), y: H - 5, "text-anchor": "middle", fill: c.muted, "font-size": 9 }, "d" + (i + 1)); });
    add(s, "text", { x: W - m.r, y: y(si[si.length - 1]) - 6, "text-anchor": "end", fill: c.ink, "font-size": 10 }, "insulin sensitivity");
    add(s, "text", { x: W - m.r, y: y(gb[gb.length - 1]) + 14, "text-anchor": "end", fill: c.ink, "font-size": 10 }, "hepatic set-point");
  }

  // ------------------------------------------------------------- model card charts
  function learning(el, lc) {
    const c = C();
    const W = el.clientWidth || 480, H = 230, m = { l: 40, r: 70, t: 14, b: 32 };
    const s = svg(el, W, H);
    const rows = lc.filter((r) => r.n_patients > 0);
    const xs = rows.map((r) => r.n_patients);
    const x = scale(Math.log2(xs[0]), Math.log2(xs[xs.length - 1]), m.l, W - m.r);
    const ys = rows.flatMap((r) => [r.hybrid_rmse, r.ml_rmse]);
    const y = scale(Math.floor(Math.min(...ys) - 2), Math.ceil(Math.max(...ys) + 2), H - m.b, m.t);
    for (let v = Math.ceil(Math.min(...ys) - 2); v <= Math.max(...ys) + 2; v += 2) {
      add(s, "line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), class: "gridline" });
      add(s, "text", { x: m.l - 6, y: y(v) + 3, "text-anchor": "end", fill: c.muted, "font-size": 10 }, v);
    }
    xs.forEach((n) => add(s, "text", { x: x(Math.log2(n)), y: H - 14, "text-anchor": "middle", fill: c.muted, "font-size": 10 }, n));
    add(s, "text", { x: (m.l + W - m.r) / 2, y: H - 1, "text-anchor": "middle", fill: c.muted, "font-size": 10 }, "training patients (log scale)");
    const series = [["hybrid_rmse", "Twin + AI", c.c1], ["ml_rmse", "ML only", c.c2]];
    for (const [k, name, col] of series) {
      const p = add(s, "path", { d: path(rows.map((r) => [x(Math.log2(r.n_patients)), y(r[k])])), fill: "none", stroke: col, "stroke-width": 2 });
      animateLine(p);
      rows.forEach((r) => {
        const d = add(s, "circle", { cx: x(Math.log2(r.n_patients)), cy: y(r[k]), r: 4.5, fill: col, stroke: css("--surface"), "stroke-width": 2 });
        d.addEventListener("mousemove", (e) => tip(`<div class="tt-h">${r.n_patients} training patients</div><div class="tt-r">${name} <b>${r[k].toFixed(1)} mg/dL</b></div>`, e.clientX, e.clientY));
        d.addEventListener("mouseleave", hideTip);
      });
      const last = rows[rows.length - 1];
      add(s, "text", { x: W - m.r + 8, y: y(last[k]) + (k === "ml_rmse" ? -2 : 10), fill: c.ink, "font-size": 11 }, name);
    }
  }

  function clarke(el, pts) {
    const c = C();
    const W = Math.min(el.clientWidth || 300, 320), H = W, m = { l: 34, r: 8, t: 8, b: 30 };
    const s = svg(el, W, H);
    const x = scale(0, 400, m.l, W - m.r), y = scale(0, 400, H - m.b, m.t);
    const L = (pp, col = "rgba(255,255,255,.3)") => add(s, "path", { d: path(pp.map(([a, b]) => [x(a), y(b)])), fill: "none", stroke: col, "stroke-width": 1 });
    L([[0, 0], [400, 400]], "rgba(255,255,255,.15)");
    for (const seg of [[[0, 70], [175 / 3, 70]], [[175 / 3, 70], [400 / 1.2, 400]], [[70, 84], [70, 400]], [[0, 180], [70, 180]],
                       [[70, 180], [290, 400]], [[70, 0], [70, 56]], [[70, 56], [400, 320]], [[180, 0], [180, 70]], [[180, 70], [400, 70]],
                       [[240, 70], [240, 180]], [[240, 180], [400, 180]], [[130, 0], [180, 70]]]) L(seg);
    for (const [a, b] of pts) add(s, "circle", { cx: x(a), cy: y(b), r: 1.6, fill: c.c1, opacity: .5 });
    for (const v of [0, 100, 200, 300, 400]) {
      add(s, "text", { x: x(v), y: H - 16, "text-anchor": "middle", fill: c.muted, "font-size": 9.5 }, v);
      add(s, "text", { x: m.l - 4, y: y(v) + 3, "text-anchor": "end", fill: c.muted, "font-size": 9.5 }, v);
    }
    add(s, "text", { x: (m.l + W) / 2, y: H - 2, "text-anchor": "middle", fill: c.muted, "font-size": 10 }, "reference CGM (mg/dL)");
    for (const [lab, a, b] of [["A", 340, 370], ["B", 370, 260], ["B", 260, 370], ["C", 120, 330], ["D", 30, 130], ["D", 330, 130], ["E", 30, 300], ["E", 330, 30]])
      add(s, "text", { x: x(a), y: y(b), fill: c.ink, "font-size": 12, "font-weight": 700, opacity: .6 }, lab);
  }

  function reliability(el, rel) {
    const c = C();
    const W = Math.min(el.clientWidth || 300, 320), H = W, m = { l: 34, r: 8, t: 8, b: 30 };
    const s = svg(el, W, H);
    const x = scale(0, 1, m.l, W - m.r), y = scale(0, 1, H - m.b, m.t);
    add(s, "line", { x1: x(0), y1: y(0), x2: x(1), y2: y(1), stroke: "rgba(255,255,255,.2)", "stroke-dasharray": "3 4" });
    for (const v of [0, .5, 1]) {
      add(s, "text", { x: x(v), y: H - 16, "text-anchor": "middle", fill: c.muted, "font-size": 9.5 }, v);
      add(s, "text", { x: m.l - 4, y: y(v) + 3, "text-anchor": "end", fill: c.muted, "font-size": 9.5 }, v);
    }
    add(s, "path", { d: path(rel.map((r) => [x(r.p), y(r.obs)])), fill: "none", stroke: c.c1, "stroke-width": 2 });
    rel.forEach((r) => {
      const d = add(s, "circle", { cx: x(r.p), cy: y(r.obs), r: 4.5, fill: c.c1, stroke: css("--surface"), "stroke-width": 2 });
      d.addEventListener("mousemove", (e) => tip(`<div class="tt-r">Predicted <b>${(r.p * 100).toFixed(0)}%</b></div><div class="tt-r">Observed <b>${(r.obs * 100).toFixed(0)}%</b></div><div class="tt-r">n <b>${r.n}</b></div>`, e.clientX, e.clientY));
      d.addEventListener("mouseleave", hideTip);
    });
    add(s, "text", { x: (m.l + W) / 2, y: H - 2, "text-anchor": "middle", fill: c.muted, "font-size": 10 }, "predicted spike probability");
  }

  function hbars(el, items, fmt = (v) => v.toFixed(3), color) {
    const c = C();
    const mx = Math.max(...items.map((i) => i.v));
    el.innerHTML = items.map((i) => `<div class="drv-row"><div><div class="drv-label"><span>${i.k}</span></div><div class="drv-bar"><i data-w="${Math.max(1, i.v / mx * 100)}" style="background:${color || c.c1}"></i></div></div><div class="drv-val">${fmt(i.v)}</div></div>`).join("");
    requestAnimationFrame(() => el.querySelectorAll("i[data-w]").forEach((b) => (b.style.width = b.dataset.w + "%")));
  }

  // ------------------------------------------------------------- tiny inline svgs
  function spark(vals, w = 64, h = 18) {
    const v = vals.filter((a) => a != null);
    if (!v.length) return "";
    const x = scale(0, vals.length - 1, 1, w - 1), y = scale(60, Math.max(260, ...v), h - 1, 1);
    const pts = vals.map((a, i) => (a == null ? null : [x(i), y(a)]));
    const last = v[v.length - 1];
    return `<svg class="pt-spark" viewBox="0 0 ${w} ${h}"><rect x="0" y="${y(180)}" width="${w}" height="${y(70) - y(180)}" fill="rgba(47,213,154,.08)"/><path d="${path(pts)}" fill="none" stroke="${zoneColor(last)}" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
  }
  function ring(frac, color, label) {
    const r = 15, L = 2 * Math.PI * r;
    return `<div class="ring"><svg viewBox="0 0 38 38"><circle class="bgc" cx="19" cy="19" r="${r}"/><circle class="fgc" cx="19" cy="19" r="${r}" stroke="${color}" stroke-dasharray="${L}" stroke-dashoffset="${L * (1 - frac)}"/></svg><span>${label}</span></div>`;
  }

  window.Charts = { glucose, strip, sleep, tir, hrv, whatif, pgi, track, drift, learning, clarke, reliability, hbars, spark, ring, tip, hideTip, hhmm, zoneColor };
})();
