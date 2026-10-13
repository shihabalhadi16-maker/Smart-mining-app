"""
auto_calibration.py  v61 - drop-in replacement (same public names as v57.8)
Requires: drastic_core.py and drastic_bridge.py in the same folder.

What changed (see notes in the chat):
  * one set of rating functions (drastic_bridge) - no more private copies
  * Hg/CN scores come from drastic_core (log scale, EU limits)
  * SF is no longer searched (it only rescales alpha/beta): returned as 1.0
  * the threshold is FITTED (Youden), never typed in
  * reported kappa = NESTED leave-one-out estimate, not the fitted (optimistic) one
  * bad rows raise an error instead of silently becoming DRASTIC = 0
"""
import re
import numpy as np
import pandas as pd
import drastic_core as dc
from drastic_bridge import (get_d_rating, get_r_rating, get_a_rating, get_s_rating,
                            get_t_rating, get_i_rating, get_c_rating, calc_index)

SKLEARN_OK = True        # kept for compatibility: no sklearn needed any more
CN_LIMIT = dc.LIMITS_MG_L["EU"]["cn"]
HG_LIMIT = dc.LIMITS_MG_L["EU"]["hg"]
HQ_REF = 1000.0
MAX_TOXICITY_BONUS = 50.0
DEFAULT_THRESHOLD = 140
DEFAULT_WEIGHTS = {m: {"alpha": 1.0, "beta": 1.0, "SF": 1.0}     # null assumption
                   for m in ("industrial", "traditional", "mixed")}
OPTIMAL_THRESHOLDS = {m: 140.0 for m in DEFAULT_WEIGHTS}          # retired: fit instead
REQUIRED = ["depth_m", "recharge_mm", "slope_pct", "conductivity", "aquifer", "soil",
            "vadose", "cn_water_mg_l", "hg_water_mg_l", "actual_contaminated"]


def get_optimal_threshold(mining_type): return DEFAULT_THRESHOLD
def get_theoretical_weights(mining_type): return DEFAULT_WEIGHTS.get(mining_type, DEFAULT_WEIGHTS["traditional"])


def compute_cn_score(cn):
    return 0.0 if cn < 0 else dc.hazard_score(cn, CN_LIMIT, HQ_REF)


def compute_hg_score(hg):
    return 0.0 if hg < 0 else dc.hazard_score(hg, HG_LIMIT, HQ_REF)


def compute_drastic_for_row(row):
    return calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])),
                      get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])),
                      get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])),
                      get_c_rating(float(row["conductivity"])))


# ------------------------------------------------------------- helpers
def _prep(df):
    miss = [c for c in REQUIRED if c not in df.columns]
    if miss: raise ValueError(f"أعمدة مفقودة: {miss}")
    if len(df) < 5: raise ValueError(f"عدد المواقع قليل جداً ({len(df)}). مطلوب 5 على الأقل.")
    d = []
    for i, (_, r) in enumerate(df.iterrows()):
        try: d.append(compute_drastic_for_row(r))
        except Exception as e: raise ValueError(f"صف {i + 1}: {e}")
    y = df["actual_contaminated"].astype(int).values
    if len(np.unique(y)) < 2: raise ValueError("البيانات تحتوي على تصنيف واحد فقط")
    cn = np.array([compute_cn_score(float(v)) for v in df["cn_water_mg_l"]])
    hg = np.array([compute_hg_score(float(v)) for v in df["hg_water_mg_l"]])
    return np.array(d, float), cn, hg, y


def _kappa(y, p):
    po = (y == p).mean()
    pe = sum((y == c).mean() * (p == c).mean() for c in (0, 1))
    return 0.0 if pe >= 1 else float((po - pe) / (1 - pe))


def _auc(y, s):
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0: return float("nan")
    return float(((pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum())
                 / (len(pos) * len(neg)))


def _youden(s, y):
    u = np.sort(np.unique(s))
    cands = np.concatenate(([u[0] - 1], (u[:-1] + u[1:]) / 2, [u[-1] + 1]))
    best_j, best = -2.0, []
    for th in cands:
        p = s >= th
        j = (p[y == 1].mean() if (y == 1).any() else 0) - (p[y == 0].mean() if (y == 0).any() else 0)
        if j > best_j + 1e-12: best_j, best = j, [th]
        elif abs(j - best_j) <= 1e-12: best.append(th)
    return float(np.median(best)), float(best_j)


def _scores(d, cn, hg, a, b):
    return d + np.minimum(MAX_TOXICITY_BONUS, a * cn + b * hg)


def _fit(d, cn, hg, y, grid):
    best = None
    for a, b in grid:
        th, j = _youden(_scores(d, cn, hg, a, b), y)
        key = (round(j, 6), -(abs(a - 1) + abs(b - 1)))        # ties -> nearest equal weights
        if best is None or key > best[0]: best = (key, a, b, th, j)
    return best[1], best[2], best[3], best[4]


def _grid(n_steps, alpha_range, beta_range):
    A = np.linspace(*(alpha_range or (0.0, 1.0)), n_steps)
    B = np.linspace(*(beta_range or (0.0, 1.0)), n_steps)
    return [(float(a), float(b)) for a in A for b in B]


def _groups(df):
    """Location id per row. Dry/Wet pairs at the same place must stay together in CV."""
    if {"lat", "lon"} <= set(df.columns):
        key = [f"{a:.2f},{b:.2f}" for a, b in zip(df["lat"].astype(float), df["lon"].astype(float))]
    elif "coords" in df.columns:
        key = [",".join(f"{float(x):.2f}" for x in c) for c in df["coords"]]
    elif "site_key" in df.columns:
        key = [re.sub(r"_(Dry|Wet)$", "", str(k), flags=re.I) for k in df["site_key"]]
    else:
        key = [str(i) for i in range(len(df))]
    return pd.factorize(pd.Series(key))[0]


def _metrics(y, pred, sc):
    y = np.asarray(y); pred = np.asarray(pred); sc = np.asarray(sc)
    tp = int(((y == 1) & (pred == 1)).sum()); tn = int(((y == 0) & (pred == 0)).sum())
    fp = int(((y == 0) & (pred == 1)).sum()); fn = int(((y == 1) & (pred == 0)).sum())
    rec = tp / (tp + fn) if tp + fn else 0.0
    prec = tp / (tp + fp) if tp + fp else 0.0
    spec = tn / (tn + fp) if tn + fp else 0.0
    return {"kappa": round(_kappa(y, pred), 4), "auc": round(_auc(y, sc), 3),
            "recall": round(rec * 100, 2), "precision": round(prec * 100, 2),
            "specificity": round(spec * 100, 2),
            "accuracy": round(float((pred == y).mean() * 100), 1),
            "tp": tp, "tn": tn, "fp": fp, "fn": fn}


def _nested_raw(d, cn, hg, y, grid=None, fixed=None, groups=None):
    """Leave-one-GROUP-out (leave-one-row-out if groups is None).
    Weights (unless fixed) AND threshold are fitted on the training part only.
    Returns (pred, score) for every row."""
    n = len(y)
    g = np.arange(n) if groups is None else np.asarray(groups)
    pred = np.zeros(n, int); sc = np.zeros(n)
    for gid in np.unique(g):
        te = g == gid
        tr = ~te
        if tr.sum() < 3 or len(np.unique(y[tr])) < 2:
            a, b, th = 1.0, 1.0, DEFAULT_THRESHOLD          # cannot fit: fall back
        elif fixed is not None:
            a, b = fixed
            th, _ = _youden(_scores(d[tr], cn[tr], hg[tr], a, b), y[tr])
        else:
            a, b, th, _ = _fit(d[tr], cn[tr], hg[tr], y[tr], grid)
        s_te = _scores(d[te], cn[te], hg[te], a, b)
        sc[te] = s_te
        pred[te] = (s_te >= th).astype(int)
    return pred, sc


def _nested(d, cn, hg, y, grid=None, fixed=None, groups=None):
    pred, sc = _nested_raw(d, cn, hg, y, grid, fixed, groups)
    return _metrics(y, pred, sc)


def bootstrap_group_ci(y, pred, groups=None, n_boot=2000, seed=42):
    """95% CI of kappa by resampling LOCATIONS (predictions are kept as they are)."""
    y = np.asarray(y); pred = np.asarray(pred)
    g = np.arange(len(y)) if groups is None else np.asarray(groups)
    ids = np.unique(g); rng = np.random.default_rng(seed); ks = []
    for _ in range(n_boot):
        pick = rng.choice(ids, len(ids), replace=True)
        idx = np.concatenate([np.where(g == i)[0] for i in pick])
        if len(np.unique(y[idx])) == 2:
            ks.append(_kappa(y[idx], pred[idx]))
    if not ks:
        return (None, None)
    lo, hi = np.percentile(ks, [2.5, 97.5])
    return (round(float(lo), 3), round(float(hi), 3))


# ---- public aliases used by external_validation / model_development
prepare_arrays = _prep
location_groups = _groups
grouped_cv = _nested_raw
classification_metrics = _metrics
youden_threshold = _youden
kappa_score = _kappa
auc_score = _auc
score_grid = _grid


def interpret_kappa(kappa):
    if kappa >= 0.81: return {"level": "ممتاز", "color": "green", "en": "Almost Perfect"}
    if kappa >= 0.61: return {"level": "جيد", "color": "green", "en": "Substantial"}
    if kappa >= 0.41: return {"level": "متوسط", "color": "yellow", "en": "Moderate"}
    if kappa >= 0.21: return {"level": "مقبول", "color": "orange", "en": "Fair"}
    return {"level": "ضعيف", "color": "red", "en": "Slight/Poor"}


# ------------------------------------------------------------- public API
def auto_calibrate_weights(df, mining_type="traditional", n_steps=15, threshold=None,
                           alpha_range=None, beta_range=None, sf_range=None, fit_threshold=True):
    """alpha->CN weight, beta->Hg weight. `threshold` is ignored unless fit_threshold=False."""
    try:
        d, cn, hg, y = _prep(df)
    except ValueError as e:
        return {"error": str(e)}
    grid = _grid(n_steps, alpha_range, beta_range)
    a, b, th, j = _fit(d, cn, hg, y, grid)
    if not fit_threshold and threshold is not None:
        th = float(threshold)
    fitted = _scores(d, cn, hg, a, b)
    p = (fitted >= th).astype(int)
    grp = _groups(df)
    cv = _nested(d, cn, hg, y, grid, groups=grp)            # leave-one-LOCATION-out (honest)
    cv_naive = _nested(d, cn, hg, y, grid)                  # leave-one-row-out (leaky if pairs exist)
    n_loc = len(np.unique(grp))
    warn = [f"n={len(y)} صفاً في {n_loc} موقعاً مستقلاً: التقدير غير مستقر.",
            "best_kappa = leave-one-LOCATION-out المتداخل (وليس kappa التدريب)."]
    if n_loc < len(y):
        warn.append(f"{len(y) - n_loc} صفوف مكررة الموقع (جاف/رطب): CV العادي متسرّب، استُخدم التجميع.")
    if len(y) < 30: warn.append("أقل من 30 موقعاً: لا تعتمد الأوزان المعايَرة للنشر.")
    return {"mining_type": mining_type, "n_sites": len(y), "n_combinations_tested": len(grid),
            "threshold": round(th, 1), "best_alpha": round(a, 3), "best_beta": round(b, 3),
            "best_SF": 1.0, "best_kappa": cv["kappa"], "best_recall": cv["recall"],
            "resubstitution_kappa": round(_kappa(y, p), 4), "youden_J_fit": round(j, 3),
            "cv": cv, "cv_naive_leaky": cv_naive, "n_locations": n_loc, "warnings": warn, "all_results": [],
            "kappa_interpretation": interpret_kappa(cv["kappa"])}


def compare_with_defaults(df, mining_type, threshold=None):
    """Both models evaluated by nested leave-one-out; threshold fitted inside each fold."""
    try:
        d, cn, hg, y = _prep(df)
    except ValueError as e:
        return {"error": str(e)}
    default = _nested(d, cn, hg, y, fixed=(1.0, 1.0), groups=_groups(df))
    cal = auto_calibrate_weights(df, mining_type)
    if "error" in cal:
        return {"default_kappa": default["kappa"], "default_recall": default["recall"],
                "best_kappa": None, "error": cal["error"]}
    return {"default_kappa": default["kappa"], "default_recall": default["recall"],
            "best_alpha": cal["best_alpha"], "best_beta": cal["best_beta"], "best_SF": 1.0,
            "best_kappa": cal["best_kappa"], "best_recall": cal["best_recall"],
            "improvement": round(cal["best_kappa"] - default["kappa"], 4),
            "kappa_interpretation": cal["kappa_interpretation"]}


def find_optimal_threshold(df, mining_type, alpha=None, beta=None, SF=None):
    try:
        d, cn, hg, y = _prep(df)
    except ValueError as e:
        return {"error": str(e)}
    a = 1.0 if alpha is None else alpha
    b = 1.0 if beta is None else beta
    sf = 1.0 if SF is None else SF
    s = d + np.minimum(MAX_TOXICITY_BONUS, a * cn + b * hg) * sf
    th, j = _youden(s, y)
    p = s >= th
    sens, spec = float(p[y == 1].mean()), float(1 - p[y == 0].mean())
    pd_ = s >= DEFAULT_THRESHOLD
    dsens, dspec = float(pd_[y == 1].mean()), float(1 - pd_[y == 0].mean())
    rng = np.random.default_rng(42); ths = []
    for _ in range(300):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) == 2: ths.append(_youden(s[idx], y[idx])[0])
    ci = tuple(float(x) for x in np.round(np.percentile(ths, [2.5, 97.5]), 1)) if ths else (None, None)
    roc = [{"threshold": round(float(t), 1), "tpr": round(float((s >= t)[y == 1].mean()), 3),
            "fpr": round(float((s >= t)[y == 0].mean()), 3)} for t in np.sort(np.unique(s))]
    return {"mining_type": mining_type, "n_sites": len(y), "alpha_used": a, "beta_used": b, "SF_used": sf,
            "optimal_threshold": round(th, 1), "threshold_ci_95": ci, "J_max": round(j, 4),
            "sensitivity": round(sens, 3), "specificity": round(spec, 3),
            "default_threshold": DEFAULT_THRESHOLD, "default_J": round(dsens + dspec - 1, 4),
            "default_sensitivity": round(dsens, 3), "default_specificity": round(dspec, 3),
            "roc_data": roc, "note": "Threshold fitted on the same sites: optimistic; see threshold_ci_95."}


def apply_calibration(result, mining_type):
    if "error" in result:
        raise ValueError(f"لا يمكن تطبيق المعايرة: {result['error']}")
    labels = {"industrial": "🏭 صناعي (مُعاير)", "traditional": "⛏️ تقليدي (مُعاير)",
              "mixed": "🔀 مختلط (مُعاير)"}
    return {"mining_type": mining_type, "alpha": result["best_alpha"], "beta": result["best_beta"],
            "SF": result["best_SF"], "kappa": result["best_kappa"],
            "ar": labels.get(mining_type, f"{mining_type} (مُعاير)")}


if __name__ == "__main__":
    print("auto_calibration.py v61 - ready")
