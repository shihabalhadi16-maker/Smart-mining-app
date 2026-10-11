"""
Nested LOOCV for DRASTIC-Tox  (numpy + pandas only)

Input CSV columns:
  site, drastic, cn_water_mg_l, hg_water_mg_l, mining_type, actual_contaminated
  (drastic = base DRASTIC computed by your app, 23-230)

Usage:  python nested_loocv.py sites.csv

In every fold, alpha, beta AND the threshold are chosen on the 10 training
sites only, then applied to the single held-out site.
"""
import sys
import itertools
import numpy as np
import pandas as pd

CN_LIMIT = 0.05
HG_LIMIT = 0.0007          # TODO: document source (WHO = 0.006 mg/L)
HG_RATIO_MAX = 1000        # ratio mapped to score 30 in log mode
SF = {"traditional": 1.1, "industrial": 1.0, "mixed": 1.3}
DEFAULT_AB = {"traditional": (0.3, 1.0), "industrial": (0.7, 0.5), "mixed": (0.5, 0.9)}


def cn_score(cn):
    # same as app.py (natural log, saturates at ratio 100)
    return np.minimum(30.0, np.log1p(cn / CN_LIMIT) * 30.0 / np.log(101))


def hg_score(hg, mode):
    r = hg / HG_LIMIT
    if mode == "linear":                       # original (saturates at r = 1)
        return np.minimum(30.0, r * 30.0)
    return np.minimum(30.0, np.log1p(r) * 30.0 / np.log1p(HG_RATIO_MAX))


def tox_score(df, alpha, beta, hg_mode):
    base = np.minimum(50.0, alpha * cn_score(df.cn_water_mg_l.values)
                      + beta * hg_score(df.hg_water_mg_l.values, hg_mode))
    sf = df.mining_type.map(SF).values
    return df.drastic.values + base * sf


def youden_threshold(score, y):
    """Best threshold by Youden J; ties -> median of tied candidates."""
    s = np.sort(np.unique(score))
    cands = np.concatenate(([s[0] - 1], (s[:-1] + s[1:]) / 2, [s[-1] + 1]))
    best_j, best = -2, []
    for th in cands:
        pred = score >= th
        tpr = pred[y == 1].mean() if (y == 1).any() else 0
        fpr = pred[y == 0].mean() if (y == 0).any() else 0
        j = tpr - fpr
        if j > best_j + 1e-12:
            best_j, best = j, [th]
        elif abs(j - best_j) <= 1e-12:
            best.append(th)
    return float(np.median(best)), best_j


def kappa(y, p):
    n = len(y)
    po = (y == p).mean()
    pe = sum(((y == c).mean() * (p == c).mean()) for c in (0, 1))
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def auc(y, s):
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    gt = (pos[:, None] > neg[None, :]).sum()
    eq = (pos[:, None] == neg[None, :]).sum()
    return (gt + 0.5 * eq) / (len(pos) * len(neg))


def fit_fold(train, hg_mode, grid):
    """Pick (alpha, beta, threshold) on training data only."""
    y = train.actual_contaminated.values
    mt = train.mining_type.mode()[0]
    a0, b0 = DEFAULT_AB[mt]
    best = None
    for a, b in grid:
        sc = tox_score(train, a, b, hg_mode)
        th, j = youden_threshold(sc, y)
        key = (round(j, 6), -abs(a - a0) - abs(b - b0))   # tie -> nearest default
        if best is None or key > best[0]:
            best = (key, a, b, th)
    return best[1], best[2], best[3]


def nested_loocv(df, mode):
    """mode: 'drastic' | 'tox_linear' | 'tox_log'"""
    grid = list(itertools.product(np.arange(0, 1.01, 0.1), repeat=2))
    y = df.actual_contaminated.values
    scores, preds = np.zeros(len(df)), np.zeros(len(df), int)
    for i in range(len(df)):
        tr, te = df.drop(df.index[i]), df.iloc[[i]]
        if mode == "drastic":
            th, _ = youden_threshold(tr.drastic.values, tr.actual_contaminated.values)
            s = te.drastic.values[0]
        else:
            hm = "linear" if mode == "tox_linear" else "log"
            a, b, th = fit_fold(tr, hm, grid)
            s = tox_score(te, a, b, hm)[0]
        scores[i], preds[i] = s, int(s >= th)
    return y, scores, preds


def boot_ci(y, p, n=2000, seed=42):
    rng = np.random.default_rng(seed)
    ks = []
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) < 2:
            continue
        ks.append(kappa(y[idx], p[idx]))
    return np.percentile(ks, [2.5, 97.5]) if ks else (np.nan, np.nan)


def saturation_report(df):
    for m in ("linear", "log"):
        s = hg_score(df.hg_water_mg_l.values, m)
        print(f"Hg_score [{m:6s}] at cap(30): {(s >= 29.999).sum()}/{len(df)} sites")


if __name__ == "__main__":
    df = pd.read_csv(sys.argv[1]).reset_index(drop=True)
    print(f"n = {len(df)}  contaminated = {int(df.actual_contaminated.sum())}\n")
    saturation_report(df)
    print("\nNested LOOCV (alpha, beta, threshold fitted inside each fold)")
    print(f"{'model':12s} {'kappa':>7s} {'95% CI':>16s} {'AUC':>6s} {'recall':>7s} {'acc':>6s}")
    for m in ("drastic", "tox_linear", "tox_log"):
        y, s, p = nested_loocv(df, m)
        lo, hi = boot_ci(y, p)
        rec = p[y == 1].mean() if (y == 1).any() else np.nan
        print(f"{m:12s} {kappa(y, p):7.3f} [{lo:6.2f},{hi:6.2f}] "
              f"{auc(y, s):6.3f} {rec:7.2f} {(y == p).mean():6.2f}")
