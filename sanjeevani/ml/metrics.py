"""Clinical forecasting metrics, including Clarke Error Grid Analysis."""
import numpy as np


def clarke_zones(ref, pred):
    """Clarke et al. 1987 error-grid zone (A-E) for each (reference, prediction)."""
    ref = np.asarray(ref, float)
    pred = np.asarray(pred, float)
    z = np.full(len(ref), "B", dtype="<U1")
    a = ((ref <= 70) & (pred <= 70)) | (np.abs(pred - ref) <= 0.2 * ref)
    e = ((ref >= 180) & (pred <= 70)) | ((ref <= 70) & (pred >= 180))
    c = (((ref >= 70) & (ref <= 290)) & (pred >= ref + 110)) | \
        (((ref >= 130) & (ref <= 180)) & (pred <= (7 / 5) * ref - 182))
    d = ((ref >= 240) & ((pred >= 70) & (pred <= 180))) | \
        ((ref <= 175 / 3) & (pred <= 180) & (pred >= 70)) | \
        (((ref >= 175 / 3) & (ref <= 70)) & (pred >= (6 / 5) * ref))
    z[d] = "D"
    z[c] = "C"
    z[e] = "E"
    z[a] = "A"
    return z


def regression(y, p):
    m = ~np.isnan(y) & ~np.isnan(p)
    y, p = y[m], p[m]
    z = clarke_zones(y, p)
    return dict(n=int(m.sum()), rmse=float(np.sqrt(np.mean((p - y) ** 2))), mae=float(np.mean(np.abs(p - y))),
                mard=float(np.mean(np.abs(p - y) / y) * 100), clarke_A=float(np.mean(z == "A") * 100),
                clarke_AB=float(np.mean((z == "A") | (z == "B")) * 100))


def auc_roc(y, s):
    y = np.asarray(y).astype(bool)
    order = np.argsort(s)
    ranks = np.empty(len(s))
    ranks[order] = np.arange(1, len(s) + 1)
    n1, n0 = y.sum(), (~y).sum()
    return float((ranks[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else float("nan")


def auc_pr(y, s):
    y = np.asarray(y).astype(bool)
    order = np.argsort(-s)
    tp = np.cumsum(y[order])
    prec = tp / np.arange(1, len(y) + 1)
    return float(np.sum(prec[y[order]]) / max(1, y.sum()))


def best_f1_threshold(y, s):
    best = (0, 0.5)
    for t in np.linspace(0.05, 0.95, 91):
        pr = s >= t
        tp = np.sum(pr & (y == 1))
        if tp == 0:
            continue
        f1 = 2 * tp / (pr.sum() + (y == 1).sum())
        best = max(best, (f1, t))
    return float(best[1])


def threshold_for_precision(y, s, target=0.75):
    """Clinical alert policy: the most sensitive threshold whose precision is
    still >= target (limits alert fatigue). Falls back to max-F1."""
    best = None
    for t in np.linspace(0.05, 0.95, 181):
        pr = s >= t
        tp = np.sum(pr & (y == 1))
        if pr.sum() == 0:
            continue
        if tp / pr.sum() >= target:
            sens = tp / max(1, (y == 1).sum())
            if best is None or sens > best[0]:
                best = (sens, t)
    return float(best[1]) if best else best_f1_threshold(y, s)


def classification(y, s, thr):
    y = np.asarray(y).astype(bool)
    pr = s >= thr
    tp, fp, fn = np.sum(pr & y), np.sum(pr & ~y), np.sum(~pr & y)
    return dict(n=int(len(y)), prevalence=float(y.mean()), auroc=auc_roc(y, s), auprc=auc_pr(y, s),
                threshold=float(thr), sensitivity=float(tp / max(1, tp + fn)), precision=float(tp / max(1, tp + fp)),
                f1=float(2 * tp / max(1, 2 * tp + fp + fn)))


def reliability(y, s, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        m = (s >= a) & (s < b if b < 1 else s <= b)
        if m.sum() >= 15:
            out.append(dict(p=float(s[m].mean()), obs=float(np.mean(y[m])), n=int(m.sum())))
    return out


def event_lead_times(cgm5, anchors, probs, thr, step=5, thr_mgdl=180):
    """Event-level evaluation. An event is an upward crossing of thr_mgdl that
    follows >= 60 min below it. Returns detection stats and lead times (min)."""
    above = cgm5 >= thr_mgdl
    events = []
    for i in range(12, len(cgm5)):
        if above[i] and not np.isnan(cgm5[i]) and np.all(~above[i - 12:i]) and np.sum(~np.isnan(cgm5[i - 12:i])) >= 8:
            events.append(i * step)
    a = np.asarray(anchors)
    alert = probs >= thr
    leads, detected = [], 0
    for tc in events:
        m = (a >= tc - 120) & (a < tc) & alert
        if m.any():
            detected += 1
            leads.append(tc - a[m].min())
    # false alerts: alert onsets with no crossing within 150 min
    onsets = a[alert & ~np.r_[False, alert[:-1]]]
    ev = np.asarray(events)
    false = sum(1 for t in onsets if not np.any((ev > t) & (ev <= t + 150)) and
                not np.any(above[max(0, t // step):t // step + 1]))
    return dict(events=len(events), detected=detected, leads=leads, false_alerts=false)
