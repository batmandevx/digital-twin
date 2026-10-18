"""Vectorised glucose-insulin physiology used by both the ground-truth
"virtual human" simulator and the personalised digital twin.

The model is an extended Bergman minimal model:

    dG/dt  = -(SG + X) G + SG Gb' + Ra(t) - k_ex A G + EGP_stress s + EGP_extra
    dX/dt  = -p2 X + p2 SI'(t) (I - Ib)
    dI/dt  = -n (I - Ib) + gamma m(t) max(G - h, 0)
    gut    : two parallel two-compartment chains (fast / slow carbohydrate)
    dE/dt  = (A - E) / 240           (exercise "memory" raising insulin sensitivity)

    m(t)   = circadian(t) * sleep(debt)  (scales both SI and beta-cell gamma)
    SI'(t) = SI * m(t) * (1 + 0.8 E)
    Gb'    = Gb * gb_mult(t)           (metformin adherence / dose effects)
    h      = Gb' - h_shift             (sulfonylureas lower the secretion threshold)

Every function operates on a batch dimension B (patients, parameter candidates,
forecast anchors or what-if scenarios), so thousands of futures can be
simulated in milliseconds with plain NumPy.
"""
import numpy as np

VG = 1.88          # glucose distribution volume (dL/kg)
P2 = 0.025         # remote-insulin rate (1/min)
N_CLEAR = 0.14     # insulin clearance (1/min)
K_FAST = 0.045     # fast gut absorption (1/min)
K_SLOW = 0.016     # slow gut absorption (1/min)
F_BIO = 0.62        # effective systemic carbohydrate appearance (after splanchnic uptake)

PARAMS = ("Gb", "SG", "SI", "gamma", "Ib", "BW", "k_ex", "egp_stress",
          "circ_amp", "sleep_sens", "h_shift")
STATES = ("G", "X", "I", "Qf1", "Qf2", "Qs1", "Qs2", "E")
INPUTS = ("carbs_fast", "carbs_slow", "steps", "sleep_debt", "stress",
          "gb_mult", "egp_extra")


def as_batch(params, B=None):
    p = {k: np.atleast_1d(np.asarray(v, dtype=np.float64)) for k, v in params.items()}
    if B is not None:
        p = {k: np.broadcast_to(v, (B,)).copy() for k, v in p.items()}
    return p


def steady_state(params):
    p = as_batch(params)
    B = len(p["Gb"])
    z = np.zeros(B)
    return dict(G=p["Gb"].copy(), X=z.copy(), I=p["Ib"].copy(), Qf1=z.copy(),
                Qf2=z.copy(), Qs1=z.copy(), Qs2=z.copy(), E=z.copy())


def empty_inputs(B, T):
    z = np.zeros((B, T))
    return dict(carbs_fast=z.copy(), carbs_slow=z.copy(), steps=z.copy(),
                sleep_debt=z.copy(), stress=z.copy(), gb_mult=np.ones((B, T)),
                egp_extra=z.copy())


def simulate(params, state, inputs, tod0, cgm=None, gain=0.0,
             si_noise=None, record_states_every=0):
    """Integrate the model with 1-minute Euler steps.

    params  : dict of arrays [B]
    state   : dict of arrays [B]  (copied, not modified)
    inputs  : dict of arrays [B, T] (per-minute values)
    tod0    : array [B] minute-of-day at the first step
    cgm     : optional [B, T] observations (NaN where missing) for nudging
              data assimilation, i.e. a simple fixed-gain state observer
    si_noise: optional [B, T] multiplicative SI perturbation (ground truth only)
    Returns (G trajectory [B, T], final state dict, optional recorded states).
    """
    p = as_batch(params)
    B, T = inputs["carbs_fast"].shape
    s = {k: np.array(v, dtype=np.float64, copy=True) for k, v in state.items()}
    G, X, I = s["G"], s["X"], s["I"]
    Qf1, Qf2, Qs1, Qs2, E = s["Qf1"], s["Qf2"], s["Qs1"], s["Qs2"], s["E"]

    Gb, SG, SI, gamma, Ib = p["Gb"], p["SG"], p["SI"], p["gamma"], p["Ib"]
    ra_scale = F_BIO * 1000.0 / (VG * p["BW"])
    k_ex, egp_s = p["k_ex"], p["egp_stress"]
    circ, sleep_s, h_shift = p["circ_amp"], p["sleep_sens"], p["h_shift"]

    cf, cs = inputs["carbs_fast"], inputs["carbs_slow"]
    steps, debt, stress = inputs["steps"], inputs["sleep_debt"], inputs["stress"]
    gbm, egpx = inputs["gb_mult"], inputs["egp_extra"]

    tod0 = np.broadcast_to(np.asarray(tod0, dtype=np.float64), (B,))
    out = np.empty((B, T))
    rec = []
    two_pi_day = 2 * np.pi / 1440.0
    for k in range(T):
        tod = tod0 + k
        c = 1.0 + circ * np.cos(two_pi_day * (tod - 540.0))      # most sensitive ~09:00
        sl = np.clip(1.0 - sleep_s * debt[:, k], 0.5, 1.0)
        m = c * sl                                   # circadian x sleep "metabolic fitness"
        si = SI * m * (1.0 + 0.8 * E)
        if si_noise is not None:
            si = si * si_noise[:, k]
        gb_eff = Gb * gbm[:, k]
        a = steps[:, k] * 0.01
        ra = ra_scale * (K_FAST * Qf2 + K_SLOW * Qs2)

        dG = (-(SG + X) * G + SG * gb_eff + ra - k_ex * a * G
              + egp_s * stress[:, k] + egpx[:, k])
        dX = -P2 * X + P2 * si * (I - Ib)
        dI = -N_CLEAR * (I - Ib) + gamma * m * np.maximum(G - (gb_eff - h_shift), 0.0)

        G = np.maximum(G + dG, 25.0)
        X = X + dX
        I = np.maximum(I + dI, 0.0)
        Qf2 = Qf2 + K_FAST * (Qf1 - Qf2)
        Qf1 = Qf1 + cf[:, k] - K_FAST * Qf1
        Qs2 = Qs2 + K_SLOW * (Qs1 - Qs2)
        Qs1 = Qs1 + cs[:, k] - K_SLOW * Qs1
        E = E + (a - E) / 240.0

        if cgm is not None:
            obs = cgm[:, k]
            m = ~np.isnan(obs)
            if m.any():
                G = np.where(m, G + gain * (np.nan_to_num(obs) - G), G)
        out[:, k] = G
        if record_states_every and (k % record_states_every == 0):
            rec.append(np.stack([G, X, I, Qf1, Qf2, Qs1, Qs2, E], axis=1).copy())

    final = dict(G=G, X=X, I=I, Qf1=Qf1, Qf2=Qf2, Qs1=Qs1, Qs2=Qs2, E=E)
    if record_states_every:
        return out, final, np.stack(rec, axis=1)   # [B, T/every, n_states]
    return out, final, None


def state_from_array(arr):
    """[B, n_states] -> state dict."""
    arr = np.atleast_2d(arr)
    return {name: arr[:, i].astype(np.float64) for i, name in enumerate(STATES)}


def dawn_profile(T, t0=0):
    """Shape of the dawn phenomenon (early-morning hepatic glucose output),
    a half-sine between 04:00 and 08:00. The amplitude is patient-specific."""
    tod = (t0 + np.arange(T)) % 1440
    x = (tod - 4 * 60) / (4 * 60)
    return np.where((x > 0) & (x < 1), np.sin(np.pi * x), 0.0)


def gmi(mean_glucose):
    """Glucose Management Indicator (% HbA1c-equivalent), Bergenstal 2018."""
    return 3.31 + 0.02392 * np.asarray(mean_glucose)


def hba1c_from_mean(mean_glucose):
    """ADAG relationship (Nathan 2008): eAG = 28.7 A1c - 46.7."""
    return (np.asarray(mean_glucose) + 46.7) / 28.7
