// Sanjeevani: holographic 3D digital twin (three.js r160)
// * particle-sampled human body that assembles itself on load
// * organs glow from the twin's live physiological state; click to focus
// * glucose-coloured bloodstream, heartbeat shockwaves
// * 3D glucose ribbon: last 24 h + 2 h forecast spiralling around the body
// * DNA helix for the patient's genotype; data streams fusing into organs
// * "ghost twin" mode: today's path vs. the prescribed plan, side by side
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
const V = (x, y, z) => new THREE.Vector3(x, y, z);
const rand = Math.random;
const lerp = (a, b, t) => a + (b - a) * t;
const clamp01 = (x) => Math.max(0, Math.min(1, x));
const easeIO = (t) => (t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

// ---------------------------------------------------------------- body model
const TORSO = [[0.9, .165], [.97, .172], [1.05, .146], [1.15, .152], [1.27, .172], [1.36, .19], [1.42, .178], [1.47, .1]];
function torsoR(y) {
  for (let i = 0; i < TORSO.length - 1; i++) {
    const [y0, r0] = TORSO[i], [y1, r1] = TORSO[i + 1];
    if (y >= y0 && y <= y1) return lerp(r0, r1, (y - y0) / (y1 - y0));
  }
  return .1;
}
function unitDir() {
  let x, y, z, d;
  do { x = rand() * 2 - 1; y = rand() * 2 - 1; z = rand() * 2 - 1; d = x * x + y * y + z * z; } while (d > 1 || d < 1e-4);
  d = Math.sqrt(d); return [x / d, y / d, z / d];
}
function bodyParts() {
  const P = [];
  const ell = (c, r) => P.push({ kind: "e", c, r, area: 4 * Math.PI * ((r[0] + r[1] + r[2]) / 3) ** 2 });
  const cap = (a, b, ra, rb) => P.push({ kind: "c", a, b, ra, rb, area: Math.PI * (ra + rb) * a.distanceTo(b) });
  ell(V(0, 1.635, 0), [.094, .118, .104]);
  cap(V(0, 1.46, 0), V(0, 1.54, .005), .046, .042);
  P.push({ kind: "t", area: 2 * Math.PI * .16 * .57 * 1.3 });
  for (const s of [-1, 1]) {
    ell(V(s * .185, 1.405, 0), [.058, .05, .052]);
    cap(V(s * .2, 1.39, 0), V(s * .255, 1.13, -.005), .048, .039);
    cap(V(s * .255, 1.13, -.005), V(s * .292, .875, .03), .037, .029);
    ell(V(s * .302, .8, .036), [.026, .058, .02]);
    cap(V(s * .088, .93, 0), V(s * .1, .52, .01), .078, .053);
    cap(V(s * .1, .52, .01), V(s * .102, .1, -.01), .05, .034);
    ell(V(s * .1, .045, .045), [.038, .03, .088]);
  }
  return P;
}
function samplePart(p, shell) {
  const s = shell ? 1 : Math.cbrt(rand()) * .92;
  if (p.kind === "e") {
    const d = unitDir();
    return [p.c.x + d[0] * p.r[0] * s, p.c.y + d[1] * p.r[1] * s, p.c.z + d[2] * p.r[2] * s];
  }
  if (p.kind === "t") {
    const y = lerp(.9, 1.47, rand());
    const r = torsoR(y) * s, th = rand() * Math.PI * 2;
    return [Math.cos(th) * r, y, Math.sin(th) * r * (y > 1.2 ? .66 : .6) + (y > 1.2 && y < 1.36 ? .008 : 0)];
  }
  const t = rand();
  const c = p.a.clone().lerp(p.b, t);
  const ax = p.b.clone().sub(p.a).normalize();
  const e1 = new THREE.Vector3().crossVectors(ax, Math.abs(ax.y) < .9 ? V(0, 1, 0) : V(1, 0, 0)).normalize();
  const e2 = new THREE.Vector3().crossVectors(ax, e1);
  const r = lerp(p.ra, p.rb, t) * s, th = rand() * Math.PI * 2;
  c.addScaledVector(e1, Math.cos(th) * r).addScaledVector(e2, Math.sin(th) * r);
  return [c.x, c.y, c.z];
}
function sampleBody(n, shell) {
  const parts = bodyParts();
  const tot = parts.reduce((a, p) => a + p.area, 0);
  const pos = new Float32Array(n * 3), rnd = new Float32Array(n), sc = new Float32Array(n * 3);
  let k = 0;
  const put = (q) => {
    pos.set(q, k * 3); rnd[k] = rand();
    const d = unitDir(), R = 1.5 + rand() * 2.5;
    sc.set([d[0] * R, 1 + d[1] * R * .6, d[2] * R], k * 3); k++;
  };
  for (const p of parts) { const m = Math.round(n * p.area / tot); for (let i = 0; i < m && k < n; i++) put(samplePart(p, shell)); }
  while (k < n) put(samplePart(parts[2], shell));
  return { pos, rnd, sc };
}

// ------------------------------------------------------------------- shaders
const bodyVert = `
uniform float uTime; uniform float uScan; uniform float uPixel; uniform float uBreath; uniform float uSize; uniform float uAssemble;
attribute float aRnd; attribute vec3 aScatter;
varying float vTw; varying float vScan; varying float vY; varying float vAs;
void main(){
  float a = clamp((uAssemble - aRnd * .45) / .55, 0., 1.);
  a = 1. - pow(1. - a, 3.);
  vec3 p = position;
  float torso = smoothstep(.95, 1.08, p.y) * (1. - smoothstep(1.38, 1.47, p.y));
  p.xz *= 1. + torso * uBreath * .03;
  p.x += sin(uTime * 1.3 + aRnd * 40.) * .0012;
  p = mix(aScatter, p, a);
  vec4 mv = modelViewMatrix * vec4(p, 1.);
  gl_Position = projectionMatrix * mv;
  vTw = .55 + .45 * sin(uTime * 1.7 + aRnd * 60.);
  vScan = exp(-pow((p.y - uScan) * 26., 2.));
  vY = p.y; vAs = a;
  gl_PointSize = uPixel * uSize * (1.2 + 2.2 * vScan + aRnd * .9) * (.75 + .25 * vTw) * (3.2 / -mv.z) * (1. + (1. - a) * 1.5);
}`;
const bodyFrag = `
uniform vec3 uColA; uniform vec3 uColB; uniform vec3 uRiskCol; uniform float uRisk; uniform float uAlpha;
varying float vTw; varying float vScan; varying float vY; varying float vAs;
void main(){
  float d = length(gl_PointCoord - .5);
  if (d > .5) discard;
  float a = smoothstep(.5, .0, d);
  vec3 col = mix(uColA, uColB, smoothstep(.0, 1.75, vY));
  col = mix(col, uRiskCol, uRisk * .6);
  col += vScan * vec3(.55, .95, 1.);
  gl_FragColor = vec4(col, a * uAlpha * (.35 + .65 * vTw) * (.6 + 1.2 * vScan) * (.4 + .6 * vAs));
}`;
const flowVert = `
uniform float uPixel; attribute float aSize; attribute vec3 aColor; varying vec3 vCol;
void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.); gl_Position = projectionMatrix * mv;
  vCol = aColor; gl_PointSize = uPixel * aSize * (3.2 / -mv.z); }`;
const flowFrag = `
varying vec3 vCol;
void main(){ float d = length(gl_PointCoord - .5); if (d > .5) discard;
  gl_FragColor = vec4(vCol, smoothstep(.5, 0., d)); }`;

function canvasTex(draw) {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  draw(c.getContext("2d"));
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
const glowTexture = () => canvasTex((g) => {
  const grd = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grd.addColorStop(0, "rgba(255,255,255,1)"); grd.addColorStop(.25, "rgba(255,255,255,.55)");
  grd.addColorStop(.6, "rgba(255,255,255,.12)"); grd.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grd; g.fillRect(0, 0, 128, 128);
});
const ringTexture = () => canvasTex((g) => {
  g.strokeStyle = "rgba(255,255,255,1)"; g.lineWidth = 5; g.shadowColor = "#fff"; g.shadowBlur = 12;
  g.beginPath(); g.arc(64, 64, 52, 0, Math.PI * 2); g.stroke();
});

const GLU_STOPS = [[60, new THREE.Color("#5aa9ff")], [100, new THREE.Color("#2fe3b0")], [170, new THREE.Color("#3ee6ff")],
                   [200, new THREE.Color("#ffb547")], [260, new THREE.Color("#ff5470")]];
function glucoseColor(g) {
  if (g == null || isNaN(g)) return new THREE.Color("#3b4a6b");
  if (g <= GLU_STOPS[0][0]) return GLU_STOPS[0][1].clone();
  for (let i = 0; i < GLU_STOPS.length - 1; i++) {
    const [a, ca] = GLU_STOPS[i], [b, cb] = GLU_STOPS[i + 1];
    if (g <= b) return ca.clone().lerp(cb, (g - a) / (b - a));
  }
  return GLU_STOPS[GLU_STOPS.length - 1][1].clone();
}

export const ORGAN_INFO = {
  brain: { name: "Brain · autonomic stress", color: "#a08cff", text: "Stress is inferred from HRV suppression and heart rate beyond activity. It raises hepatic glucose output in the twin." },
  heart: { name: "Heart", color: "#ff4f7b", text: "Heart rate sets the circulation speed of the twin's bloodstream. Its elevation above activity is a stress signal." },
  liver: { name: "Liver · hepatic glucose", color: "#ffb547", text: "Basal glucose set-point, modulated by metformin adherence, the learned dawn phenomenon and daily adaptive drift." },
  pancreas: { name: "Pancreas · beta cells", color: "#37e2ff", text: "Insulin secretion follows glucose above the threshold. Responsiveness γ is personalised from duration, TCF7L2 genotype and CGM." },
  gut: { name: "Gut · carbohydrate absorption", color: "#ff8a3d", text: "Dual-speed absorption: high-GI foods (sabudana, white rice) use the fast channel; millets and legumes use the slow one." },
  stomach: { name: "Stomach", color: "#ff8a3d", text: "Meals enter the gut compartments at the logged time with Indian-food glycaemic splits." },
  muscleL: { name: "Skeletal muscle · uptake", color: "#2fe39a", text: "Steps drive insulin-independent glucose uptake now and raise insulin sensitivity for hours afterwards." },
  muscleR: { name: "Skeletal muscle · uptake", color: "#2fe39a", text: "Steps drive insulin-independent glucose uptake now and raise insulin sensitivity for hours afterwards." },
};

// ------------------------------------------------------------------- class
export class Twin3D {
  constructor(root, labelsLayer, opts = {}) {
    this.root = root;
    this.labelsLayer = labelsLayer;
    this.onOrganClick = opts.onOrganClick || (() => {});
    this.onPlayback = opts.onPlayback || (() => {});
    this.clock = new THREE.Clock();
    this.target = { glucose: 130, risk: 0, hr: 72, stress: 0, insulin: .2, gut: 0, exercise: 0, hepatic: .5, asleep: 0 };
    this.cur = { ...this.target };
    this.labels = {};
    this.autoRotate = !REDUCED;
    this.ghostOn = 0; this.ghostT = 0; this.ghostMix = 0;
    this.assemble = REDUCED || opts.instant ? 1 : 0;

    const w = root.clientWidth || 800, h = root.clientHeight || 560;
    const r = this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    r.setPixelRatio(Math.min(devicePixelRatio, 2));
    r.setSize(w, h);
    r.setClearColor(0x000000, 0);
    r.toneMapping = THREE.ACESFilmicToneMapping;
    root.appendChild(r.domElement);

    const scene = this.scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x040915, .1);
    const cam = this.camera = new THREE.PerspectiveCamera(34, w / h, .05, 60);
    this.homePos = V(.3, 1.1, 3.75);
    this.homeTarget = V(0, .9, 0);
    cam.position.set(0, 3.4, REDUCED ? 3.25 : 8.8);
    const ctl = this.controls = new OrbitControls(cam, r.domElement);
    ctl.target.copy(this.homeTarget);
    ctl.enableDamping = true; ctl.dampingFactor = .06;
    ctl.minDistance = .7; ctl.maxDistance = 6;
    ctl.minPolarAngle = .4; ctl.maxPolarAngle = 1.8;
    ctl.enablePan = false;
    ctl.autoRotate = false; ctl.autoRotateSpeed = .5;
    ctl.enabled = false;
    this.fly = { from: cam.position.clone(), to: this.homePos.clone(), tFrom: ctl.target.clone(), tTo: this.homeTarget.clone(), t: 0, dur: REDUCED || opts.instant ? .01 : 3.4 };

    this.pixel = r.getPixelRatio();
    this.glowTex = glowTexture();
    this.ringTex = ringTexture();

    this.world = new THREE.Group();
    scene.add(this.world);
    this.twin = new THREE.Group();
    this.world.add(this.twin);
    this.main = this.#makeRig(this.twin, 24000, 7000, "#1d6fd6", "#5ff0ff", 1.15);
    this.#buildOrgans();
    this.#buildPlatform();
    this.#buildStreams();
    this.#buildRibbon();
    this.#buildDNA();
    this.#buildGhost();

    this.composer = new EffectComposer(r);
    this.composer.addPass(new RenderPass(scene, cam));
    this.bloom = new UnrealBloomPass(new THREE.Vector2(w, h), .95, .55, .08);
    this.composer.addPass(this.bloom);
    this.composer.addPass(new OutputPass());

    this.#bindPicking();
    this.ro = new ResizeObserver(() => this.resize());
    this.ro.observe(root);
    this.#loop();
  }

  // ---------------------------------------------------------------- rigs
  #makeRig(group, nShell, nInner, colA, colB, size) {
    const mk = (n, shell, sz, alpha) => {
      const { pos, rnd, sc } = sampleBody(n, shell);
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      g.setAttribute("aRnd", new THREE.BufferAttribute(rnd, 1));
      g.setAttribute("aScatter", new THREE.BufferAttribute(sc, 3));
      const m = new THREE.ShaderMaterial({
        vertexShader: bodyVert, fragmentShader: bodyFrag, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
        uniforms: { uTime: { value: 0 }, uScan: { value: 1 }, uPixel: { value: this.pixel }, uBreath: { value: 0 }, uSize: { value: sz },
                    uColA: { value: new THREE.Color(colA) }, uColB: { value: new THREE.Color(colB) }, uAssemble: { value: 0 },
                    uRiskCol: { value: new THREE.Color("#ff3d6e") }, uRisk: { value: 0 }, uAlpha: { value: alpha } },
      });
      const pts = new THREE.Points(g, m);
      pts.frustumCulled = false;
      group.add(pts);
      m.userData.base = alpha;
      return m;
    };
    const mats = [mk(nShell, true, size, .9), mk(nInner, false, size * .8, .3)];
    const ring = new THREE.Mesh(new THREE.TorusGeometry(.32, .0025, 8, 120),
      new THREE.MeshBasicMaterial({ color: colB, transparent: true, opacity: .55, blending: THREE.AdditiveBlending, depthWrite: false }));
    ring.rotation.x = Math.PI / 2;
    group.add(ring);
    return { mats, ring, flow: this.#makeFlow(group) };
  }

  #makeFlow(group) {
    const H = V(.035, 1.3, .055);
    const loops = [];
    for (const s of [-1, 1]) {
      loops.push([H, V(s * .03, 1.12, .07), V(s * .07, .92, .05), V(s * .1, .55, .04), V(s * .102, .14, .02),
                  V(s * .1, .13, -.035), V(s * .095, .55, -.035), V(s * .06, .9, -.05), V(s * .01, 1.15, -.05)]);
      loops.push([H, V(s * .12, 1.38, .02), V(s * .215, 1.33, .01), V(s * .258, 1.12, .015), V(s * .29, .9, .04),
                  V(s * .3, .84, .02), V(s * .27, .95, -.015), V(s * .24, 1.15, -.02), V(s * .18, 1.36, -.02), V(s * .07, 1.33, -.01)]);
    }
    loops.push([H, V(.01, 1.46, .03), V(.04, 1.6, .06), V(0, 1.72, .02), V(-.04, 1.6, -.04), V(-.01, 1.46, -.02)]);
    const luts = loops.map((pts) => new THREE.CatmullRomCurve3(pts, true, "catmullrom", .5).getSpacedPoints(400));
    for (const lut of luts) {
      group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(lut),
        new THREE.LineBasicMaterial({ color: 0x2a6fd0, transparent: true, opacity: .16, blending: THREE.AdditiveBlending, depthWrite: false })));
    }
    const per = 70, n = per * luts.length;
    const F = { luts, n, per, u: new Float32Array(n), sp: new Float32Array(n), jit: new Float32Array(n * 3) };
    for (let i = 0; i < n; i++) { F.u[i] = rand(); F.sp[i] = .8 + rand() * .4; F.jit.set([(rand() - .5) * .012, (rand() - .5) * .012, (rand() - .5) * .012], i * 3); }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    g.setAttribute("aColor", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    const size = new Float32Array(n);
    for (let i = 0; i < n; i++) size[i] = 2.2 + rand() * 2.2;
    g.setAttribute("aSize", new THREE.BufferAttribute(size, 1));
    const pts = new THREE.Points(g, new THREE.ShaderMaterial({ vertexShader: flowVert, fragmentShader: flowFrag, transparent: true,
      depthWrite: false, blending: THREE.AdditiveBlending, uniforms: { uPixel: { value: this.pixel } } }));
    pts.frustumCulled = false;
    group.add(pts);
    F.geo = g;
    return F;
  }

  #animRig(rig, t, dt, glucose, risk, hr, asleep, alphaMul) {
    const scan = REDUCED ? 1.0 : .05 + (Math.sin(t * .55) * .5 + .5) * 1.7;
    const breath = Math.sin(t * (asleep ? 1.1 : 1.6));
    for (const m of rig.mats) {
      m.uniforms.uTime.value = t; m.uniforms.uScan.value = scan; m.uniforms.uBreath.value = breath;
      m.uniforms.uRisk.value = risk * (.65 + .35 * Math.sin(t * 3));
      m.uniforms.uAlpha.value = m.userData.base * alphaMul;
      m.uniforms.uAssemble.value = this.assemble;
    }
    rig.ring.position.y = scan;
    const rr = scan > .93 && scan < 1.47 ? torsoR(scan) * 1.35 : scan >= 1.47 ? .14 : .26;
    rig.ring.scale.setScalar(rr / .32);
    rig.ring.material.opacity = .45 * alphaMul * this.assemble;
    const F = rig.flow, gc = glucoseColor(glucose);
    const pos = F.geo.attributes.position.array, col = F.geo.attributes.aColor.array;
    const speed = (hr / 72) * .085 * dt * (REDUCED ? .2 : 1);
    const vis = alphaMul * this.assemble;
    for (let i = 0; i < F.n; i++) {
      F.u[i] = (F.u[i] + speed * F.sp[i]) % 1;
      const lut = F.luts[Math.floor(i / F.per)];
      const p = lut[Math.floor(F.u[i] * (lut.length - 1))];
      pos[i * 3] = p.x + F.jit[i * 3]; pos[i * 3 + 1] = p.y + F.jit[i * 3 + 1]; pos[i * 3 + 2] = p.z + F.jit[i * 3 + 2];
      const b = (.65 + .35 * Math.sin(F.u[i] * 40 + t * 3)) * vis;
      col[i * 3] = gc.r * b; col[i * 3 + 1] = gc.g * b; col[i * 3 + 2] = gc.b * b;
    }
    F.geo.attributes.position.needsUpdate = true;
    F.geo.attributes.aColor.needsUpdate = true;
  }

  // ---------------------------------------------------------------- organs
  #glow(color, scale, tex) {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex || this.glowTex, color, transparent: true, opacity: .6,
      blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false }));
    s.scale.setScalar(scale);
    return s;
  }

  #buildOrgans() {
    this.pickables = [];
    const add = (key, geo, pos, scale, color, glowScale, rot) => {
      const g = new THREE.Group();
      g.position.copy(pos);
      const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: .55, blending: THREE.AdditiveBlending, depthWrite: false });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.scale.copy(scale);
      if (rot) mesh.rotation.set(...rot);
      const wire = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color, wireframe: true, transparent: true, opacity: .25, blending: THREE.AdditiveBlending, depthWrite: false }));
      wire.scale.copy(scale).multiplyScalar(1.12);
      if (rot) wire.rotation.set(...rot);
      const glow = this.#glow(color, glowScale);
      const hit = new THREE.Mesh(new THREE.SphereGeometry(1, 8, 6), new THREE.MeshBasicMaterial({ visible: false }));
      hit.scale.setScalar(Math.max(scale.x, scale.y, scale.z) * 1.5);
      hit.userData.organ = key;
      g.add(mesh, wire, glow, hit);
      this.twin.add(g);
      this.pickables.push(hit);
      return { g, mesh, wire, glow, mat, base: glowScale };
    };
    const sph = new THREE.SphereGeometry(1, 32, 20);
    this.organs = {
      brain: add("brain", sph, V(0, 1.655, -.005), V(.074, .058, .082), "#a08cff", .34),
      heart: add("heart", sph, V(.035, 1.3, .055), V(.034, .042, .034), "#ff4f7b", .26, [0, 0, -.5]),
      liver: add("liver", sph, V(-.075, 1.145, .035), V(.088, .048, .062), "#ffb547", .3, [0, 0, .25]),
      stomach: add("stomach", sph, V(.065, 1.13, .045), V(.048, .038, .034), "#ff8a3d", .2, [0, 0, -.5]),
      pancreas: add("pancreas", sph, V(.025, 1.075, .02), V(.078, .02, .024), "#37e2ff", .3, [0, 0, .22]),
      gut: add("gut", new THREE.TorusKnotGeometry(1, .28, 90, 10, 2, 5), V(0, .99, .045), V(.048, .042, .03), "#ff8a3d", .32),
      muscleL: add("muscleL", new THREE.CapsuleGeometry(1, 5.2, 6, 16), V(-.095, .72, .01), V(.05, .05, .05), "#2fe39a", .3),
      muscleR: add("muscleR", new THREE.CapsuleGeometry(1, 5.2, 6, 16), V(.095, .72, .01), V(.05, .05, .05), "#2fe39a", .3),
    };
    this.shock = this.#glow("#ff4f7b", .05, this.ringTex);
    this.shock.position.copy(this.organs.heart.g.position);
    this.twin.add(this.shock);
    this.lastBeat = 0; this.shockT = 1;

    const L = (key, organ, side, color, name) => {
      const el = document.createElement("div");
      el.className = "olabel" + (side < 0 ? " left" : "");
      el.style.setProperty("--lc", color);
      el.innerHTML = `${name}<b></b>`;
      el.addEventListener("click", () => this.focusOrgan(organ));
      this.labelsLayer.appendChild(el);
      this.labels[key] = { el, organ, side, val: el.querySelector("b") };
    };
    L("brain", "brain", 1, "#a08cff", "Brain · stress");
    L("heart", "heart", 1, "#ff4f7b", "Heart");
    L("liver", "liver", -1, "#ffb547", "Liver · glucose output");
    L("pancreas", "pancreas", 1, "#37e2ff", "Pancreas · insulin");
    L("gut", "gut", -1, "#ff8a3d", "Gut · absorbing");
    L("muscle", "muscleR", 1, "#2fe39a", "Muscle · uptake");
  }

  #buildPlatform() {
    const plat = this.platform = new THREE.Group();
    const ringMat = (op, color = 0x37e2ff) => new THREE.MeshBasicMaterial({ color, transparent: true, opacity: op, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false });
    this.rings = [[.42, .43, .5], [.55, .555, .3], [.7, .703, .22], [.95, .953, .12]].map(([a, b, op], i) => {
      const m = new THREE.Mesh(new THREE.RingGeometry(a, b, 128, 1, 0, i % 2 ? Math.PI * 1.6 : Math.PI * 2), ringMat(op));
      m.rotation.x = -Math.PI / 2; plat.add(m); return m;
    });
    const tp = [];
    for (let i = 0; i < 120; i++) {
      const a = i / 120 * Math.PI * 2, r0 = .6, r1 = i % 10 ? .62 : .66;
      tp.push(Math.cos(a) * r0, 0, Math.sin(a) * r0, Math.cos(a) * r1, 0, Math.sin(a) * r1);
    }
    const tg = new THREE.BufferGeometry();
    tg.setAttribute("position", new THREE.Float32BufferAttribute(tp, 3));
    this.ticks = new THREE.LineSegments(tg, new THREE.LineBasicMaterial({ color: 0x37e2ff, transparent: true, opacity: .35, blending: THREE.AdditiveBlending }));
    plat.add(this.ticks);
    const disc = new THREE.Mesh(new THREE.CircleGeometry(1.1, 64), new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      uniforms: { uCol: { value: new THREE.Color("#1a8fd0") }, uT: { value: 0 } },
      vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.); }",
      fragmentShader: "uniform vec3 uCol; uniform float uT; varying vec2 vUv; void main(){ float d = length(vUv-.5)*2.; float a = pow(1.-clamp(d,0.,1.), 2.2)*.55; a += smoothstep(.02,.0,abs(d-fract(uT*.25)))*.25*(1.-d); gl_FragColor = vec4(uCol, a); }",
    }));
    disc.rotation.x = -Math.PI / 2; disc.position.y = -.002;
    this.disc = disc;
    plat.add(disc);
    const dp = [];
    for (let x = -3.5; x <= 3.5; x += .12) for (let z = -3; z <= 3; z += .12) if (x * x / 1.4 + z * z < 9) dp.push(x, -.01, z);
    const dg = new THREE.BufferGeometry();
    dg.setAttribute("position", new THREE.Float32BufferAttribute(dp, 3));
    this.scene.add(new THREE.Points(dg, new THREE.PointsMaterial({ color: 0x2b5c9e, size: .008, transparent: true, opacity: .5 })));
    const beam = new THREE.Mesh(new THREE.CylinderGeometry(.42, .5, 2.1, 64, 1, true), new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending,
      uniforms: { uCol: { value: new THREE.Color("#37e2ff") } },
      vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.); }",
      fragmentShader: "uniform vec3 uCol; varying vec2 vUv; void main(){ gl_FragColor = vec4(uCol, pow(1.-vUv.y, 3.)*.07); }",
    }));
    beam.position.y = 1.05;
    this.beam = beam;
    plat.add(beam);
    this.halo = new THREE.Mesh(new THREE.RingGeometry(.44, .5, 128), ringMat(0, 0xff4f7b));
    this.halo.rotation.x = -Math.PI / 2; this.halo.position.y = .003;
    plat.add(this.halo);
    this.world.add(plat);
  }

  #buildStreams() {
    const defs = [["EHR · FHIR", "#c4a7ff", "liver"], ["CGM", "#3ee6ff", "pancreas"], ["Heart rate", "#ff6b8e", "heart"],
                  ["HRV", "#a08cff", "brain"], ["Sleep", "#7aa8ff", "brain"], ["Steps", "#2fe39a", "muscleL"]];
    this.nodeGroup = new THREE.Group();
    this.world.add(this.nodeGroup);
    this.nodes = defs.map(([name, color, target], i) => {
      const a = i / defs.length * Math.PI * 2;
      const m = new THREE.Mesh(new THREE.OctahedronGeometry(.032, 0), new THREE.MeshBasicMaterial({ color, wireframe: true, transparent: true, opacity: .9 }));
      m.position.set(Math.cos(a) * 1.02, 1.05 + Math.sin(i * 1.7) * .22, Math.sin(a) * 1.02);
      m.add(this.#glow(color, .16));
      this.nodeGroup.add(m);
      const el = document.createElement("div");
      el.className = "slabel";
      el.textContent = name;
      el.style.borderColor = color + "66";
      this.labelsLayer.appendChild(el);
      return { m, el, color: new THREE.Color(color), target, pulse: 0 };
    });
    const per = 26, n = per * this.nodes.length;
    this.streams = { per, n, t: new Float32Array(n).map(() => rand()), sp: new Float32Array(n).map(() => .25 + rand() * .3) };
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    const col = new Float32Array(n * 3), size = new Float32Array(n);
    for (let i = 0; i < n; i++) { const c = this.nodes[Math.floor(i / per)].color; col.set([c.r, c.g, c.b], i * 3); size[i] = 2 + rand() * 2.5; }
    g.setAttribute("aColor", new THREE.BufferAttribute(col, 3));
    g.setAttribute("aSize", new THREE.BufferAttribute(size, 1));
    this.streamGeo = g;
    const pts = new THREE.Points(g, new THREE.ShaderMaterial({ vertexShader: flowVert, fragmentShader: flowFrag, transparent: true,
      depthWrite: false, blending: THREE.AdditiveBlending, uniforms: { uPixel: { value: this.pixel } } }));
    pts.frustumCulled = false;
    this.scene.add(pts);
    this.streamPts = pts;
  }

  // 3D glucose ribbon: 24 h history + 2 h forecast as a helix around the body
  #buildRibbon() {
    this.ribbon = new THREE.Group();
    this.world.add(this.ribbon);
    this.ribbonNow = this.#glow("#ffffff", .09);
    this.ribbon.add(this.ribbonNow);
    const el = document.createElement("div");
    el.className = "slabel ribbon-label";
    el.textContent = "NOW · 24 h glucose ribbon";
    this.labelsLayer.appendChild(el);
    this.ribbonLabel = el;
  }
  #helix(u, g) {
    const ang = u * Math.PI * 2 * 1.35 + Math.PI * .65;
    const r = .58 + clamp01((g - 70) / 230) * .3;
    return V(Math.cos(ang) * r, .14 + u * 1.72, Math.sin(ang) * r);
  }
  setRibbon(cgm, forecast) {
    for (const c of [...this.ribbon.children]) if (c !== this.ribbonNow) { this.ribbon.remove(c); c.geometry?.dispose(); }
    this.ribbonTube = null;
    const hist = cgm.map((v, i) => [i, v]).filter(([, v]) => v != null);
    if (hist.length < 10) return;
    const N = cgm.length + forecast.length;
    const pts = [], cols = [];
    for (let i = 0; i < hist.length; i += 2) { const [k, v] = hist[i]; pts.push(this.#helix(k / N, v)); cols.push(glucoseColor(v)); }
    const curve = new THREE.CatmullRomCurve3(pts);
    const seg = pts.length * 3, rad = 6;
    const geo = new THREE.TubeGeometry(curve, seg, .0065, rad, false);
    const cArr = new Float32Array(geo.attributes.position.count * 3);
    for (let i = 0; i <= seg; i++) {
      const c = cols[Math.min(cols.length - 1, Math.round(i / seg * (cols.length - 1)))];
      for (let j = 0; j <= rad; j++) cArr.set([c.r, c.g, c.b], (i * (rad + 1) + j) * 3);
    }
    geo.setAttribute("color", new THREE.BufferAttribute(cArr, 3));
    const tube = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: .95, blending: THREE.AdditiveBlending, depthWrite: false }));
    tube.userData.reveal = this.ribbonRevealed ? .999 : 0;
    this.ribbonRevealed = true;
    geo.setDrawRange(0, 0);
    this.ribbonTube = tube;
    this.ribbon.add(tube);
    const dl = [];
    for (let i = 0; i < hist.length; i += 4) {
      const [k, v] = hist[i];
      if (v > 180) { const p = this.#helix(k / N, v), q = this.#helix(k / N, 70); dl.push(p.x, p.y, p.z, q.x, q.y, q.z); }
    }
    if (dl.length) {
      const g2 = new THREE.BufferGeometry();
      g2.setAttribute("position", new THREE.Float32BufferAttribute(dl, 3));
      this.ribbon.add(new THREE.LineSegments(g2, new THREE.LineBasicMaterial({ color: 0xff7a90, transparent: true, opacity: .2, blending: THREE.AdditiveBlending })));
    }
    const fp = [], fc = [];
    forecast.forEach((v, i) => { const p = this.#helix((cgm.length + i) / N, v); fp.push(p.x, p.y, p.z); const c = glucoseColor(v); fc.push(c.r, c.g, c.b); });
    const fg = new THREE.BufferGeometry();
    fg.setAttribute("position", new THREE.Float32BufferAttribute(fp, 3));
    fg.setAttribute("aColor", new THREE.Float32BufferAttribute(fc, 3));
    fg.setAttribute("aSize", new THREE.Float32BufferAttribute(forecast.map(() => 7), 1));
    this.ribbon.add(new THREE.Points(fg, new THREE.ShaderMaterial({ vertexShader: flowVert, fragmentShader: flowFrag, transparent: true,
      depthWrite: false, blending: THREE.AdditiveBlending, uniforms: { uPixel: { value: this.pixel } } })));
    const last = hist[hist.length - 1];
    this.ribbonNow.position.copy(this.#helix(last[0] / N, last[1]));
    this.ribbonNow.material.color.copy(glucoseColor(last[1]));
  }

  #buildDNA() {
    const g = this.dna = new THREE.Group();
    const n = 46, pos = [], col = [], rungs = [];
    const c1 = new THREE.Color("#c4a7ff"), c2 = new THREE.Color("#37e2ff");
    for (let i = 0; i < n; i++) {
      const y = i * .012, a = i * .42;
      const p1 = [Math.cos(a) * .045, y, Math.sin(a) * .045], p2 = [Math.cos(a + Math.PI) * .045, y, Math.sin(a + Math.PI) * .045];
      pos.push(...p1, ...p2); col.push(c1.r, c1.g, c1.b, c2.r, c2.g, c2.b);
      if (i % 2 === 0) rungs.push(...p1, ...p2);
    }
    const pg = new THREE.BufferGeometry();
    pg.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    pg.setAttribute("aColor", new THREE.Float32BufferAttribute(col, 3));
    pg.setAttribute("aSize", new THREE.Float32BufferAttribute(new Array(n * 2).fill(5), 1));
    g.add(new THREE.Points(pg, new THREE.ShaderMaterial({ vertexShader: flowVert, fragmentShader: flowFrag, transparent: true,
      depthWrite: false, blending: THREE.AdditiveBlending, uniforms: { uPixel: { value: this.pixel } } })));
    const rg = new THREE.BufferGeometry();
    rg.setAttribute("position", new THREE.Float32BufferAttribute(rungs, 3));
    this.dnaRungs = new THREE.LineSegments(rg, new THREE.LineBasicMaterial({ color: 0x8f7cf0, transparent: true, opacity: .5, blending: THREE.AdditiveBlending }));
    g.add(this.dnaRungs);
    g.position.set(.74, .3, -.15);
    this.world.add(g);
    const el = document.createElement("div");
    el.className = "slabel dna-label";
    el.textContent = "Genotype";
    this.labelsLayer.appendChild(el);
    this.dnaLabel = el;
  }
  setGenetics(text, risk) {
    this.dnaLabel.textContent = text;
    this.dnaRungs.material.color.set(risk >= 2 ? "#ff5fae" : risk === 1 ? "#ffb547" : "#2fd59a");
  }

  #buildGhost() {
    this.ghost = new THREE.Group();
    this.ghost.visible = false;
    this.world.add(this.ghost);
    this.ghostRig = this.#makeRig(this.ghost, 15000, 3000, "#13805a", "#7dffc8", 1.05);
    const plate = new THREE.Mesh(new THREE.RingGeometry(.36, .37, 96), new THREE.MeshBasicMaterial({ color: 0x2fd59a, transparent: true, opacity: .5, side: THREE.DoubleSide, blending: THREE.AdditiveBlending }));
    plate.rotation.x = -Math.PI / 2; plate.position.y = .004;
    this.ghost.add(plate);
    const mk = (cls) => { const el = document.createElement("div"); el.className = "ghost-label " + cls; el.style.opacity = 0; this.labelsLayer.appendChild(el); return el; };
    this.gLabelMain = mk("gl-main");
    this.gLabelGhost = mk("gl-ghost");
    this.gLabelClock = mk("gl-clock");
  }

  // ---------------------------------------------------------------- public
  update(s) {
    Object.assign(this.target, {
      glucose: s.glucose ?? this.target.glucose, risk: clamp01(s.risk ?? 0), hr: s.hr ?? this.target.hr,
      stress: clamp01(s.stress ?? 0), insulin: clamp01((s.insulin ?? 0) / 45), gut: clamp01((s.gut ?? 0) / 70),
      exercise: clamp01((s.exercise ?? 0) / .35 + (s.steps ?? 0) / 500), hepatic: clamp01(((s.hepatic ?? 140) - 100) / 90),
      asleep: s.asleep ? 1 : 0,
    });
    this.status = s.status;
    const set = (k, v) => { if (this.labels[k]) this.labels[k].val.textContent = v; };
    set("brain", s.stress > .15 ? `${Math.round(s.stress * 100)}%` : "calm");
    set("heart", `${Math.round(s.hr ?? 0)} bpm`);
    set("liver", `${Math.round(s.hepatic ?? 0)} mg/dL`);
    set("pancreas", `+${Math.max(0, Math.round(s.insulin ?? 0))} µU/mL`);
    set("gut", `${Math.round(s.gut ?? 0)} g`);
    set("muscle", (s.steps ?? 0) > 150 ? "active ↑" : (s.exercise ?? 0) > .08 ? "primed" : "resting");
    for (const n of this.nodes) n.pulse = 1;
  }
  setAutoRotate(on) { this.autoRotate = on; if (this.controls.enabled) this.controls.autoRotate = on && !this.focused && !this.ghostOn; }
  setLabels(on) { this.labelsLayer.classList.toggle("labels-off", !on); }
  pulse() { this.assemble = Math.min(this.assemble, .55); }

  focusOrgan(key) {
    const o = this.organs[key];
    if (!o || this.ghostOn) return;
    const p = new THREE.Vector3();
    o.g.getWorldPosition(p);
    const dir = this.camera.position.clone().sub(this.controls.target).normalize();
    this.#flyTo(p.clone().addScaledVector(dir, .75), p, 1.2);
    this.focused = key;
    this.controls.autoRotate = false;
    this.onOrganClick(key, ORGAN_INFO[key]);
  }
  resetView() {
    this.focused = null;
    this.#flyTo(this.ghostOn ? V(0, 1.2, 4.6) : this.homePos, this.ghostOn ? V(0, .95, 0) : this.homeTarget, 1.2);
    this.controls.autoRotate = this.autoRotate && !this.ghostOn;
    this.onOrganClick(null);
  }
  #flyTo(pos, target, dur) {
    this.fly = { from: this.camera.position.clone(), to: pos, tFrom: this.controls.target.clone(), tTo: target, t: 0, dur };
  }

  /** Ghost-twin comparison: two futures side by side, played as a time-lapse. */
  setGhost(on, data) {
    if (data) this.ghostData = data;
    if (!!on === !!this.ghostOn) return;
    this.ghostOn = on ? 1 : 0;
    this.ghostT = 0;
    this.ghost.visible = true;
    if (this.focused) { this.focused = null; this.onOrganClick(null); }
    this.controls.autoRotate = false;
    if (on) this.#flyTo(V(0, 1.2, 4.6), V(0, .95, 0), 1.4);
    else this.#flyTo(this.homePos, this.homeTarget, 1.4);
    if (!on) setTimeout(() => { if (!this.ghostOn) { this.ghost.visible = false; this.controls.autoRotate = this.autoRotate; } }, 1400);
  }

  resize() {
    const w = this.root.clientWidth, h = this.root.clientHeight;
    if (!w || !h) return;
    this.renderer.setSize(w, h); this.composer.setSize(w, h);
    this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
  }

  #bindPicking() {
    const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
    let down = null;
    const el = this.renderer.domElement;
    el.addEventListener("pointerdown", (e) => { down = [e.clientX, e.clientY]; });
    el.addEventListener("pointerup", (e) => {
      if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 5) return;
      const r = el.getBoundingClientRect();
      ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      ray.setFromCamera(ndc, this.camera);
      const hit = ray.intersectObjects(this.pickables, false)[0];
      if (hit) this.focusOrgan(hit.object.userData.organ);
      else if (this.focused) this.resetView();
    });
    el.addEventListener("dblclick", () => this.resetView());
  }

  // ---------------------------------------------------------------- loop
  #loop() {
    const tick = () => {
      this.raf = requestAnimationFrame(tick);
      if (document.hidden) return;
      const dt = Math.min(this.clock.getDelta(), .05);
      const t = this.clock.elapsedTime;
      this.#animate(t, dt);
      this.controls.update();
      this.composer.render();
      this.#placeLabels();
    };
    tick();
  }

  #animate(t, dt) {
    const c = this.cur, T = this.target, k = 1 - Math.pow(.02, dt);
    for (const key in T) c[key] = lerp(c[key], T[key], k);
    this.assemble = Math.min(1, this.assemble + dt * .42);

    const F = this.fly;
    if (F && F.t < 1) {
      F.t = Math.min(1, F.t + dt / F.dur);
      const e = easeIO(F.t);
      this.camera.position.lerpVectors(F.from, F.to, e);
      this.controls.target.lerpVectors(F.tFrom, F.tTo, e);
      if (F.t >= 1 && !this.controls.enabled) { this.controls.enabled = true; this.controls.autoRotate = this.autoRotate && !this.ghostOn; }
    }

    this.ghostMix = lerp(this.ghostMix, this.ghostOn, 1 - Math.pow(.03, dt));
    const gm = this.ghostMix;
    this.twin.position.x = -.48 * gm;
    this.ghost.position.x = .48 * gm + .9 * (1 - gm);
    this.platform.position.x = -.48 * gm;
    this.platform.scale.setScalar(1 - .25 * gm);
    const side = gm < .5;
    this.nodeGroup.visible = side; this.streamPts.visible = side; this.ribbon.visible = side; this.dna.visible = side;

    let gMain = c.glucose, gGhost = c.glucose, riskMain = c.risk, riskGhost = 0;
    if (this.ghostOn && this.ghostData) {
      const D = this.ghostData, n = D.baseline.length;
      this.ghostT = (this.ghostT + dt * (REDUCED ? .3 : 1)) % 14;
      const i = Math.min(n - 1, Math.floor(this.ghostT / 14 * n));
      gMain = D.baseline[i]; gGhost = D.scenario[i];
      riskMain = clamp01((gMain - 170) / 80); riskGhost = clamp01((gGhost - 170) / 80);
      if (i !== this.lastGhostI) { this.lastGhostI = i; this.onPlayback(i / (n - 1), i); }
      const fmt = (g) => `<b style="color:#${glucoseColor(g).getHexString()}">${Math.round(g)}</b><small>mg/dL</small>`;
      this.gLabelMain.innerHTML = `<span>Current habits</span>${fmt(gMain)}`;
      this.gLabelGhost.innerHTML = `<span>With prescribed plan</span>${fmt(gGhost)}`;
      this.gLabelClock.innerHTML = D.clock ? D.clock(i) : "";
    }
    this.#animRig(this.main, t, dt, gMain, riskMain, c.hr, c.asleep, 1);
    if (this.ghost.visible) this.#animRig(this.ghostRig, t + 1.3, dt, gGhost, riskGhost, c.hr, 0, gm);
    this.twin.position.y = Math.sin(t * .8) * .006;

    const beatPhase = t * c.hr / 60;
    const beat = Math.pow(Math.max(0, Math.sin(beatPhase * Math.PI * 2)), 12);
    if (Math.floor(beatPhase) !== this.lastBeat) { this.lastBeat = Math.floor(beatPhase); this.shockT = 0; }
    this.shockT = Math.min(1, this.shockT + dt * 1.6);
    this.shock.scale.setScalar(.04 + this.shockT * .55);
    this.shock.material.opacity = (1 - this.shockT) * .5 * this.assemble * (1 - gm * .7);
    const O = this.organs, ease = this.assemble;
    const setO = (o, level, wob = 0) => {
      const lv = .25 + level * .9, foc = this.focused && o === O[this.focused] ? 1.5 : 1, dim = 1 - .65 * gm;
      o.mat.opacity = (.22 + level * .5) * ease * dim;
      o.wire.material.opacity = (.1 + level * .3) * ease * foc * dim;
      o.glow.material.opacity = (.18 + level * .75) * ease * dim;
      o.glow.scale.setScalar(o.base * (lv + wob) * foc);
    };
    setO(O.heart, .5 + beat * .5, beat * .25);
    O.heart.mesh.scale.set(.034 * (1 + beat * .18), .042 * (1 + beat * .18), .034 * (1 + beat * .18));
    setO(O.brain, c.stress, Math.sin(t * 4) * .04 * c.stress);
    setO(O.liver, c.hepatic);
    setO(O.pancreas, c.insulin, Math.sin(t * 5) * .05 * c.insulin);
    setO(O.gut, c.gut, Math.sin(t * 2.4) * .05 * c.gut);
    setO(O.stomach, c.gut * .8);
    O.gut.mesh.rotation.y = t * .6;
    setO(O.muscleL, c.exercise); setO(O.muscleR, c.exercise);

    this.rings.forEach((m, i) => { m.rotation.z = t * (i % 2 ? -.12 : .08) * (i + 1); });
    this.ticks.rotation.y = -t * .05;
    this.disc.material.uniforms.uT.value = t;
    this.halo.material.color.set(this.status === "low" ? "#5aa9ff" : "#ff4f7b");
    const alertOn = (this.status === "spike" || this.status === "high" || this.status === "low") && !this.ghostOn ? 1 : 0;
    const hp = (t * .7) % 1;
    this.halo.scale.setScalar(1 + hp * 1.2);
    this.halo.material.opacity = alertOn * (1 - hp) * .6;
    this.beam.material.uniforms.uCol.value.set("#37e2ff").lerp(new THREE.Color("#ff4f7b"), c.risk * .7);

    if (this.ribbonTube) {
      const tb = this.ribbonTube;
      tb.userData.reveal = Math.min(1, tb.userData.reveal + dt * .45);
      const cnt = tb.geometry.index.count;
      tb.geometry.setDrawRange(0, Math.floor(cnt * easeIO(tb.userData.reveal) / 3) * 3);
    }
    this.ribbon.rotation.y = t * .04;
    this.ribbonNow.scale.setScalar(.07 + Math.sin(t * 4) * .02);

    this.dna.rotation.y = t * .8;
    this.dna.position.y = .3 + Math.sin(t * .9) * .02;

    this.nodeGroup.rotation.y = t * .07;
    this.nodeGroup.updateMatrixWorld();
    const sp = this.streamGeo.attributes.position.array, S = this.streams;
    const a = new THREE.Vector3(), b = new THREE.Vector3(), m = new THREE.Vector3();
    for (let n = 0; n < this.nodes.length; n++) {
      const node = this.nodes[n];
      node.pulse = Math.max(0, node.pulse - dt * 1.5);
      node.m.rotation.y = t * 1.2; node.m.rotation.x = t * .7;
      node.m.scale.setScalar((1 + node.pulse * .8) * Math.max(.01, this.assemble));
      node.m.getWorldPosition(a);
      this.organs[node.target].g.getWorldPosition(b);
      m.copy(a).lerp(b, .5); m.y += .25;
      for (let j = 0; j < S.per; j++) {
        const i = n * S.per + j;
        S.t[i] = (S.t[i] + dt * S.sp[i] * (1 + node.pulse * 2) * (REDUCED ? .2 : 1)) % 1;
        const u = S.t[i], iu = 1 - u;
        sp[i * 3] = iu * iu * a.x + 2 * iu * u * m.x + u * u * b.x;
        sp[i * 3 + 1] = iu * iu * a.y + 2 * iu * u * m.y + u * u * b.y;
        sp[i * 3 + 2] = iu * iu * a.z + 2 * iu * u * m.z + u * u * b.z;
      }
    }
    this.streamGeo.attributes.position.needsUpdate = true;
    this.bloom.strength = (.85 + c.risk * .35) * (1 - .35 * gm);
  }

  #placeLabels() {
    const w = this.root.clientWidth, h = this.root.clientHeight;
    const v = new THREE.Vector3();
    const proj = (obj, dy = 0) => { obj.getWorldPosition(v); v.y += dy; v.project(this.camera); return [(v.x * .5 + .5) * w, (-v.y * .5 + .5) * h]; };
    const ghost = this.ghostMix > .5;
    for (const key in this.labels) {
      const L = this.labels[key];
      const [x, y] = proj(this.organs[L.organ].g);
      L.el.style.left = x + "px"; L.el.style.top = y + "px";
      const dim = this.focused && this.focused !== L.organ && !(this.focused.startsWith("muscle") && key === "muscle");
      L.el.style.opacity = ghost ? 0 : (dim ? .2 : this.assemble);
    }
    const camDir = this.controls.target.clone().sub(this.camera.position).normalize();
    for (const n of this.nodes) {
      n.m.getWorldPosition(v);
      const behind = v.clone().sub(this.controls.target).dot(camDir) > .3;
      const [x, y] = proj(n.m);
      n.el.style.left = x + "px"; n.el.style.top = (y - 22) + "px";
      n.el.style.opacity = ghost || this.focused ? 0 : behind ? .25 : this.assemble;
    }
    let [x, y] = proj(this.ribbonNow, .07);
    this.ribbonLabel.style.left = x + "px"; this.ribbonLabel.style.top = y + "px";
    this.ribbonLabel.style.opacity = ghost || this.focused || !this.ribbonTube ? 0 : .9 * this.assemble;
    this.dna.getWorldPosition(v); v.y += .62; v.project(this.camera);
    this.dnaLabel.style.left = ((v.x * .5 + .5) * w) + "px"; this.dnaLabel.style.top = ((-v.y * .5 + .5) * h) + "px";
    this.dnaLabel.style.opacity = ghost || this.focused ? 0 : .95 * this.assemble;
    const head = new THREE.Vector3();
    const put = (el, group) => {
      group.updateMatrixWorld();
      group.localToWorld(head.set(0, -.06, .2)); head.project(this.camera);
      el.style.left = ((head.x * .5 + .5) * w) + "px"; el.style.top = ((-head.y * .5 + .5) * h) + "px";
      el.style.opacity = this.ghostOn ? this.ghostMix : 0;
    };
    put(this.gLabelMain, this.twin);
    put(this.gLabelGhost, this.ghost);
    this.gLabelClock.style.left = (w / 2) + "px"; this.gLabelClock.style.top = "52px";
    this.gLabelClock.style.opacity = this.ghostOn ? this.ghostMix : 0;
  }
}
