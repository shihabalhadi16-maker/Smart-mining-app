"""
تطوير النموذج — v61
=====================================
- معايرة α و β (Grid Search)
- مقارنة النماذج (3 نماذج — بعد إزالة DRASTIC-Lu المُختلق)
- أوزان AHP مع فحص الاتساق

v61 Changes:
  * REMOVED: DRASTIC-Lu (multiplicative land-use formula had NO source)
  * Threshold for DRASTIC-T unified on 144.4 (was 140)
  * AHP-DRASTIC now reports Consistency Ratio (CR < 0.10 required)
  * Docstring explicitly labels AHP weights as exploratory

References
----------
- Saaty, T.L. (1980). The Analytic Hierarchy Process. McGraw-Hill.
- Aller et al. (1987). DRASTIC. EPA/600/2-87/035.
- Landis & Koch (1977). The measurement of observer agreement. Biometrics.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score, roc_auc_score, confusion_matrix

# ============================================================
# Canonical constants (v61)
# ============================================================
CN_LIMIT = 0.05       # mg/L (EU 98/83/EC)
HG_LIMIT = 0.001      # mg/L (EU 98/83/EC)  ← was 0.0007
MAX_CN_SCORE = 30.0
MAX_HG_SCORE = 30.0
MAX_TOXICITY_BONUS = 50.0
DEFAULT_THRESHOLD_DT = 144.4    # unified
DRASTIC_MAX = 226
DTOX_MAX = 276                  # 226 + 50


# ============================================================
# 1. معايرة α و β — Grid Search
# ============================================================
def calibrate_alpha_beta(df, thresholds_dict, alpha_range=None, beta_range=None):
    """
    Grid Search لإيجاد أفضل α و β

    Parameters
    ----------
    df : DataFrame
        يجب أن يحتوي على: DRASTIC, cn_water_mg_l, hg_water_mg_l, actual_contaminated
    thresholds_dict : dict
        {'DRASTIC': 100, 'DRASTIC-T': 144.4}
    alpha_range, beta_range : list
        نطاقات البحث

    Returns
    -------
    dict with best_kappa, best_balanced, results
    """
    if alpha_range is None:
        alpha_range = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    if beta_range is None:
        beta_range = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

    results = []
    y_true = df["actual_contaminated"].values
    base_drastic = df["DRASTIC"].values
    cn = df["cn_water_mg_l"].values
    hg = df["hg_water_mg_l"].values
    th_dt = thresholds_dict.get("DRASTIC-T", DEFAULT_THRESHOLD_DT)   # ← v61

    for alpha in alpha_range:
        for beta in beta_range:
            dts = []
            for i in range(len(df)):
                cn_score = min(MAX_CN_SCORE, (cn[i] / CN_LIMIT) * MAX_CN_SCORE)
                hg_score = min(MAX_HG_SCORE, (hg[i] / HG_LIMIT) * MAX_HG_SCORE)
                bonus = min(MAX_TOXICITY_BONUS, alpha * cn_score + beta * hg_score)
                dts.append(base_drastic[i] + bonus)

            dts = np.array(dts)
            y_pred = (dts >= th_dt).astype(int)

            try:
                kappa = cohen_kappa_score(y_true, y_pred)
                acc = np.mean(y_true == y_pred) * 100
                tp = np.sum((y_true == 1) & (y_pred == 1))
                fn = np.sum((y_true == 1) & (y_pred == 0))
                recall = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0

                results.append({
                    "alpha": round(alpha, 2), "beta": round(beta, 2),
                    "kappa": round(kappa, 3),
                    "accuracy": round(acc, 1),
                    "recall": round(recall, 1),
                })
            except Exception:
                continue

    results_df = pd.DataFrame(results)

    if results_df.empty:
        return {"error": "No valid results"}

    best_idx = results_df["kappa"].idxmax()
    best = results_df.loc[best_idx]

    results_df["score"] = results_df["kappa"] * 0.5 + results_df["recall"] / 100 * 0.5
    best_balanced_idx = results_df["score"].idxmax()
    best_balanced = results_df.loc[best_balanced_idx]

    return {
        "best_kappa": {
            "alpha": float(best["alpha"]), "beta": float(best["beta"]),
            "kappa": float(best["kappa"]), "accuracy": float(best["accuracy"]),
            "recall": float(best["recall"]),
        },
        "best_balanced": {
            "alpha": float(best_balanced["alpha"]), "beta": float(best_balanced["beta"]),
            "kappa": float(best_balanced["kappa"]),
            "accuracy": float(best_balanced["accuracy"]),
            "recall": float(best_balanced["recall"]),
        },
        "results": results_df,
        "warning": "Grid-search values are fitted on the SAME data. "
                   "Not a validation result; use nested CV or external data.",
    }


# ============================================================
# 2. أوزان AHP (مع فحص الاتساق)
# ============================================================
def calculate_ahp_weights():
    """
    حساب أوزان AHP للـ 7 معايير + Consistency Ratio.

    ⚠️ مصفوفة المقارنة أدناه تقديرية (قرار الباحث) وليست مرجعاً منشوراً.
    يجب اعتبار الأوزان استكشافية حتى تُدعَم بمسح خبراء.

    Returns
    -------
    dict with weights, raw_weights, consistency_ratio, is_consistent
    """
    comparison = np.array([
        [1,   2,   3,   4,   7,   2,   3],
        [1/2, 1,   2,   3,   5,   1,   2],
        [1/3, 1/2, 1,   2,   4,   1,   1],
        [1/4, 1/3, 1/2, 1,   3,   1/2, 1/2],
        [1/7, 1/5, 1/4, 1/3, 1,   1/5, 1/4],
        [1/2, 1,   1,   2,   5,   1,   2],
        [1/3, 1/2, 1,   2,   4,   1/2, 1],
    ])

    n = comparison.shape[0]
    eigvals, eigvecs = np.linalg.eig(comparison)
    max_idx = int(np.argmax(eigvals.real))
    lambda_max = float(eigvals.real[max_idx])
    weights = eigvecs[:, max_idx].real
    weights = np.abs(weights) / np.abs(weights).sum()

    # Consistency Ratio (Saaty)
    CI = (lambda_max - n) / (n - 1) if n > 1 else 0.0
    # Random Index (Saaty 1980) for n=7
    RI_TABLE = {1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12,
                6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
    RI = RI_TABLE.get(n, 1.32)
    CR = CI / RI if RI > 0 else 0.0

    weights_scaled = np.round(weights * 7 / weights.max(), 1)
    weights_scaled = np.clip(weights_scaled, 1, 5)

    return {
        "D": float(weights_scaled[0]), "R": float(weights_scaled[1]),
        "A": float(weights_scaled[2]), "S": float(weights_scaled[3]),
        "T": float(weights_scaled[4]), "I": float(weights_scaled[5]),
        "C": float(weights_scaled[6]),
        "raw_weights": weights.tolist(),
        "consistency_ratio": round(float(CR), 4),
        "is_consistent": bool(CR < 0.10),
        "note": "AHP pair-wise matrix is the author's judgement, not a "
                "published source. Treat weights as exploratory.",
    }


# ============================================================
# 3. مقارنة النماذج (v61: DRASTIC-Lu REMOVED)
# ============================================================
def compare_models(df, get_rating_funcs, calc_index_func):
    """
    مقارنة 3 نماذج (v61: DRASTIC-Lu أُزيل):
    1. DRASTIC (الأساسي)          — Aller 1987
    2. DRASTIC-T (الحالي)          — هذه الدراسة
    3. AHP-DRASTIC (استكشافي)     — Saaty 1980

    Parameters
    ----------
    df : DataFrame
    get_rating_funcs : tuple (get_d, get_r, get_a, get_s, get_t, get_i, get_c)
    calc_index_func : function

    Returns
    -------
    dict with results for each model
    """
    get_d, get_r, get_a, get_s, get_t, get_i, get_c = get_rating_funcs
    y_true = df["actual_contaminated"].values
    n = len(df)

    # Conductivity: accept both column names
    cond_col = "conductivity_m_d" if "conductivity_m_d" in df.columns else "conductivity"

    D_r = np.array([get_d(float(v)) for v in df["depth_m"]])
    R_r = np.array([get_r(float(v)) for v in df["recharge_mm"]])
    A_r = np.array([get_a(str(v)) for v in df["aquifer"]])
    S_r = np.array([get_s(str(v)) for v in df["soil"]])
    T_r = np.array([get_t(float(v)) for v in df["slope_pct"]])
    I_r = np.array([get_i(str(v)) for v in df["vadose"]])
    C_r = np.array([get_c(float(v)) for v in df[cond_col]])
    cn = df["cn_water_mg_l"].values
    hg = df["hg_water_mg_l"].values

    results = {}

    # 1. DRASTIC
    drastic = D_r*5 + R_r*4 + A_r*3 + S_r*2 + T_r*1 + I_r*5 + C_r*3
    results["DRASTIC"] = evaluate_model(y_true, drastic, 100)
    results["DRASTIC"]["values"] = drastic.tolist()

    # 2. DRASTIC-T  (v61: log-score matching drastic_core.hazard_score)
    drastic_t = []
    for i in range(n):
        cn_score = _log_hazard_score(cn[i], CN_LIMIT, MAX_CN_SCORE)
        hg_score = _log_hazard_score(hg[i], HG_LIMIT, MAX_HG_SCORE)
        bonus = min(MAX_TOXICITY_BONUS, 0.5 * cn_score + 0.5 * hg_score)
        drastic_t.append(drastic[i] + bonus)
    drastic_t = np.array(drastic_t)
    results["DRASTIC-T"] = evaluate_model(y_true, drastic_t, DEFAULT_THRESHOLD_DT)
    results["DRASTIC-T"]["values"] = drastic_t.tolist()

    # 3. AHP-DRASTIC  (v61: consistency flag included)
    ahp = calculate_ahp_weights()
    drastic_ahp = (D_r*ahp["D"] + R_r*ahp["R"] + A_r*ahp["A"] +
                   S_r*ahp["S"] + T_r*ahp["T"] + I_r*ahp["I"] + C_r*ahp["C"])
    results["AHP-DRASTIC"] = evaluate_model(y_true, drastic_ahp, 100)
    results["AHP-DRASTIC"]["values"] = drastic_ahp.tolist()
    results["AHP-DRASTIC"]["weights"] = ahp

    # REMOVED in v61: DRASTIC-Lu  (multiplicative land-use, no source)

    return results


# ============================================================
# Helpers
# ============================================================
def _log_hazard_score(conc, limit, max_score, hq_ref=1000.0):
    """Matches drastic_core.hazard_score: 0 if compliant, log10 otherwise."""
    if conc is None or conc <= 0:
        return 0.0
    hq = conc / limit
    if hq <= 1:
        return 0.0
    return min(max_score, max_score * np.log10(hq) / np.log10(hq_ref))


def evaluate_model(y_true, y_score, threshold):
    """تقييم نموذج واحد"""
    try:
        y_pred = (y_score >= threshold).astype(int)

        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        if cm.size == 4:
            tn, fp, fn, tp = cm.ravel()
        else:
            tn = fp = fn = tp = 0

        kappa = cohen_kappa_score(y_true, y_pred) if len(np.unique(y_true)) > 1 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        accuracy = (tp + tn) / max(1, (tp + tn + fp + fn))

        try:
            auc = roc_auc_score(y_true, y_score)
        except Exception:
            auc = 0.5

        return {
            "kappa": round(float(kappa), 3),
            "recall": round(float(recall) * 100, 1),
            "precision": round(float(precision) * 100, 1),
            "accuracy": round(float(accuracy) * 100, 1),
            "auc": round(float(auc), 3),
            "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn),
            "threshold": threshold,
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    ahp = calculate_ahp_weights()
    print(f"v61 — AHP Consistency Ratio = {ahp['consistency_ratio']} "
          f"({'OK' if ahp['is_consistent'] else 'INCONSISTENT'})")
    print("DRASTIC-Lu has been removed.")
