"""
auto_calibration.py — معايرة أوزان DRASTIC-Tox
جامعة الخرطوم — v57.8
المراجع: Aller 1987، Konaté 2025، Karan 2018، Landis & Koch 1977، Youden 1950
"""

from typing import Optional
import numpy as np
import pandas as pd

try:
    from sklearn.metrics import cohen_kappa_score, roc_curve
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False

CN_LIMIT = 0.05
HG_LIMIT = 0.0007
MAX_CN_SCORE = 30.0
MAX_HG_SCORE = 30.0
MAX_TOXICITY_BONUS = 50.0
DEFAULT_THRESHOLD = 140

DEFAULT_WEIGHTS = {
    "industrial":  {"alpha": 0.7, "beta": 0.5, "SF": 1.0},
    "traditional": {"alpha": 0.3, "beta": 1.0, "SF": 1.1},
    "mixed":       {"alpha": 0.5, "beta": 0.9, "SF": 1.3},
}

OPTIMAL_THRESHOLDS = {
    "traditional": 106.5,
    "industrial":  128.0,
    "mixed":       117.0,
}


def get_d_rating(d):
    if d < 0: raise ValueError("Neg")
    if d <= 1.5: return 10
    if d <= 4.6: return 9
    if d <= 9.1: return 7
    if d <= 15.2: return 5
    if d <= 22.9: return 3
    if d <= 30.5: return 2
    return 1

def get_r_rating(r):
    if r < 0: raise ValueError("Neg")
    if r <= 50.8: return 1
    if r <= 101.6: return 3
    if r <= 177.8: return 6
    if r <= 254.0: return 8
    return 9

def get_a_rating(a):
    return {"massive_shale": 2, "metamorphic_igneous": 3,
            "weathered_metamorphic_igneous": 4, "thin_bedded_sequences": 6,
            "massive_sandstone": 6, "massive_limestone": 6,
            "sand_and_gravel": 8, "basalt": 9, "karst_limestone": 10}.get(a, 6)

def get_s_rating(s):
    return {"thin_or_absent": 10, "gravel": 10, "sand": 9, "peat": 8,
            "shrinking_aggregated_clay": 7, "sandy_loam": 6, "loam": 5,
            "silty_loam": 4, "clay_loam": 3, "muck": 2,
            "nonshrinking_clay": 1}.get(s, 5)

def get_t_rating(t):
    if t < 0: raise ValueError("Neg")
    if t <= 2.0: return 10
    if t <= 6.0: return 9
    if t <= 12.0: return 5
    if t <= 18.0: return 3
    return 1

def get_i_rating(i):
    return {"confining_layer": 1, "silt_clay": 1, "shale": 3,
            "metamorphic_igneous": 4, "limestone": 6, "sandstone": 6,
            "sand_gravel_silt_clay": 6, "sand_gravel": 8,
            "basalt": 9, "karst_limestone": 10}.get(i, 6)

def get_c_rating(c):
    if c < 0: raise ValueError("Neg")
    if c <= 4.074: return 1
    if c <= 12.222: return 2
    if c <= 28.518: return 4
    if c <= 40.740: return 6
    if c <= 81.480: return 8
    return 10

def calc_index(D, R, A, S, T, I, C):
    return (D*5) + (R*4) + (A*3) + (S*2) + (T*1) + (I*5) + (C*3)


def compute_cn_score(cn_mg_l):
    if cn_mg_l < 0: return 0.0
    return min(MAX_CN_SCORE, (cn_mg_l / CN_LIMIT) * 30.0)

def compute_hg_score(hg_mg_l):
    if hg_mg_l < 0: return 0.0
    return min(MAX_HG_SCORE, (hg_mg_l / HG_LIMIT) * 30.0)

def compute_drastic_for_row(row):
    try:
        return calc_index(
            get_d_rating(float(row["depth_m"])),
            get_r_rating(float(row["recharge_mm"])),
            get_a_rating(str(row["aquifer"])),
            get_s_rating(str(row["soil"])),
            get_t_rating(float(row["slope_pct"])),
            get_i_rating(str(row["vadose"])),
            get_c_rating(float(row["conductivity"])),
        )
    except Exception:
        return 0


def get_optimal_threshold(mining_type):
    return OPTIMAL_THRESHOLDS.get(mining_type, 106.5)

def get_theoretical_weights(mining_type):
    return DEFAULT_WEIGHTS.get(mining_type, DEFAULT_WEIGHTS["traditional"])


def auto_calibrate_weights(df, mining_type="traditional", n_steps=15,
                            threshold=DEFAULT_THRESHOLD,
                            alpha_range=None, beta_range=None, sf_range=None):
    if not SKLEARN_OK:
        return {"error": "scikit-learn غير مثبت"}

    required = ["depth_m", "recharge_mm", "slope_pct", "conductivity",
                "aquifer", "soil", "vadose", "cn_water_mg_l",
                "hg_water_mg_l", "actual_contaminated"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return {"error": f"أعمدة مفقودة: {missing}"}
    if len(df) < 5:
        return {"error": f"عدد المواقع قليل جداً ({len(df)}). مطلوب 5 على الأقل."}

    drastic_vals = np.array([compute_drastic_for_row(row) for _, row in df.iterrows()])
    actual = df["actual_contaminated"].astype(int).values
    if len(np.unique(actual)) < 2:
        return {"error": "البيانات تحتوي على تصنيف واحد فقط"}

    cn_scores = np.array([compute_cn_score(float(row.get("cn_water_mg_l", 0))) for _, row in df.iterrows()])
    hg_scores = np.array([compute_hg_score(float(row.get("hg_water_mg_l", 0))) for _, row in df.iterrows()])

    if alpha_range is None: alpha_range = (0.1, 0.9)
    if beta_range is None: beta_range = (0.1, 1.0)
    if sf_range is None: sf_range = (0.8, 1.5)

    alpha_values = np.linspace(alpha_range[0], alpha_range[1], n_steps)
    beta_values = np.linspace(beta_range[0], beta_range[1], n_steps)
    sf_values = np.linspace(sf_range[0], sf_range[1], n_steps)

    best = {"kappa": -999.0, "alpha": 0.5, "beta": 0.5, "SF": 1.0, "recall": 0.0}
    results = []

    for alpha in alpha_values:
        for beta in beta_values:
            base_bonus = np.minimum(MAX_TOXICITY_BONUS, alpha * cn_scores + beta * hg_scores)
            for SF in sf_values:
                dt_vals = drastic_vals + base_bonus * SF
                pred = (dt_vals >= threshold).astype(int)
                if len(np.unique(pred)) < 2:
                    continue
                try:
                    kappa = cohen_kappa_score(actual, pred)
                except Exception:
                    continue
                tp = int(np.sum((actual == 1) & (pred == 1)))
                fn = int(np.sum((actual == 1) & (pred == 0)))
                recall = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0.0
                results.append({"alpha": round(float(alpha), 3), "beta": round(float(beta), 3),
                                "SF": round(float(SF), 3), "kappa": round(float(kappa), 4),
                                "recall": round(float(recall), 2)})
                if kappa > best["kappa"]:
                    best = {"kappa": float(kappa), "alpha": round(float(alpha), 3),
                            "beta": round(float(beta), 3), "SF": round(float(SF), 3),
                            "recall": round(float(recall), 2)}

    if not results:
        return {"error": "لم تُنتج أي تركيبة تصنيفاً متوازناً. جرّب تغيير العتبة."}

    results_sorted = sorted(results, key=lambda x: (-x["kappa"], -x["recall"]))
    return {"mining_type": mining_type, "n_sites": len(df),
            "n_combinations_tested": len(results), "threshold": threshold,
            "best_alpha": best["alpha"], "best_beta": best["beta"],
            "best_SF": best["SF"], "best_kappa": round(best["kappa"], 4),
            "best_recall": best["recall"], "all_results": results_sorted[:20],
            "kappa_interpretation": interpret_kappa(best["kappa"])}


def find_optimal_threshold(df, mining_type, alpha=None, beta=None, SF=None):
    if not SKLEARN_OK:
        return {"error": "scikit-learn غير مثبت"}
    required = ["depth_m", "recharge_mm", "slope_pct", "conductivity",
                "aquifer", "soil", "vadose", "cn_water_mg_l",
                "hg_water_mg_l", "actual_contaminated"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return {"error": f"أعمدة مفقودة: {missing}"}
    if len(df) < 5:
        return {"error": f"عدد المواقع قليل جداً ({len(df)})."}

    if alpha is None or beta is None or SF is None:
        w = DEFAULT_WEIGHTS.get(mining_type, DEFAULT_WEIGHTS["traditional"])
        alpha = w["alpha"] if alpha is None else alpha
        beta = w["beta"] if beta is None else beta
        SF = w["SF"] if SF is None else SF

    drastic_vals = np.array([compute_drastic_for_row(row) for _, row in df.iterrows()])
    actual = df["actual_contaminated"].astype(int).values
    if len(np.unique(actual)) < 2:
        return {"error": "البيانات تحتوي على تصنيف واحد فقط"}

    cn_scores = np.array([compute_cn_score(float(row.get("cn_water_mg_l", 0))) for _, row in df.iterrows()])
    hg_scores = np.array([compute_hg_score(float(row.get("hg_water_mg_l", 0))) for _, row in df.iterrows()])

    base_bonus = np.minimum(MAX_TOXICITY_BONUS, alpha * cn_scores + beta * hg_scores)
    dt_vals = drastic_vals + base_bonus * SF

    fpr, tpr, thresholds = roc_curve(actual, dt_vals)
    J_values = tpr - fpr
    best_idx = int(np.argmax(J_values))
    best_threshold = float(thresholds[best_idx])
    best_J = float(J_values[best_idx])
    best_sens = float(tpr[best_idx])
    best_spec = float(1 - fpr[best_idx])

    default_threshold = DEFAULT_THRESHOLD
    default_pred = (dt_vals >= default_threshold).astype(int)
    if len(np.unique(default_pred)) >= 2:
        tp = int(np.sum((actual == 1) & (default_pred == 1)))
        fn = int(np.sum((actual == 1) & (default_pred == 0)))
        tn = int(np.sum((actual == 0) & (default_pred == 0)))
        fp = int(np.sum((actual == 0) & (default_pred == 1)))
        default_sens = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        default_spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        default_J = default_sens + default_spec - 1
    else:
        default_J = 0.0; default_sens = 0.0; default_spec = 0.0

    roc_data = [{"threshold": round(float(thresholds[i]), 1),
                 "tpr": round(float(tpr[i]), 3),
                 "fpr": round(float(fpr[i]), 3),
                 "J": round(float(J_values[i]), 3)} for i in range(len(thresholds))]

    return {"mining_type": mining_type, "n_sites": len(df),
            "alpha_used": alpha, "beta_used": beta, "SF_used": SF,
            "optimal_threshold": round(best_threshold, 1),
            "J_max": round(best_J, 4), "sensitivity": round(best_sens, 3),
            "specificity": round(best_spec, 3),
            "default_threshold": default_threshold,
            "default_J": round(default_J, 4),
            "default_sensitivity": round(default_sens, 3),
            "default_specificity": round(default_spec, 3),
            "roc_data": roc_data}


def interpret_kappa(kappa):
    if kappa >= 0.81: return {"level": "ممتاز", "color": "green", "en": "Almost Perfect"}
    elif kappa >= 0.61: return {"level": "جيد", "color": "green", "en": "Substantial"}
    elif kappa >= 0.41: return {"level": "متوسط", "color": "yellow", "en": "Moderate"}
    elif kappa >= 0.21: return {"level": "مقبول", "color": "orange", "en": "Fair"}
    else: return {"level": "ضعيف", "color": "red", "en": "Slight/Poor"}


def apply_calibration(result, mining_type):
    if "error" in result:
        raise ValueError(f"لا يمكن تطبيق المعايرة: {result['error']}")
    labels = {"industrial": "🏭 صناعي (مُعاير)",
              "traditional": "⛏️ تقليدي (مُعاير)",
              "mixed": "🔀 مختلط (مُعاير)"}
    return {"mining_type": mining_type, "alpha": result["best_alpha"],
            "beta": result["best_beta"], "SF": result["best_SF"],
            "kappa": result["best_kappa"],
            "ar": labels.get(mining_type, f"{mining_type} (مُعاير)")}


def compare_with_defaults(df, mining_type, threshold=DEFAULT_THRESHOLD):
    if not SKLEARN_OK:
        return {"error": "scikit-learn غير مثبت"}
    if mining_type not in DEFAULT_WEIGHTS:
        return {"error": f"نمط غير معروف: {mining_type}"}

    drastic_vals = np.array([compute_drastic_for_row(row) for _, row in df.iterrows()])
    actual = df["actual_contaminated"].astype(int).values
    cn_scores = np.array([compute_cn_score(float(row.get("cn_water_mg_l", 0))) for _, row in df.iterrows()])
    hg_scores = np.array([compute_hg_score(float(row.get("hg_water_mg_l", 0))) for _, row in df.iterrows()])

    w_def = DEFAULT_WEIGHTS[mining_type]
    base_bonus_def = np.minimum(MAX_TOXICITY_BONUS, w_def["alpha"] * cn_scores + w_def["beta"] * hg_scores)
    dt_def = drastic_vals + base_bonus_def * w_def["SF"]
    pred_def = (dt_def >= threshold).astype(int)

    try: kappa_def = cohen_kappa_score(actual, pred_def)
    except Exception: kappa_def = 0.0

    tp_def = int(np.sum((actual == 1) & (pred_def == 1)))
    fn_def = int(np.sum((actual == 1) & (pred_def == 0)))
    recall_def = (tp_def / (tp_def + fn_def) * 100) if (tp_def + fn_def) > 0 else 0.0

    cal_result = auto_calibrate_weights(df, mining_type, threshold=threshold)
    if "error" in cal_result:
        return {"default_kappa": round(float(kappa_def), 4),
                "default_recall": round(float(recall_def), 2),
                "best_kappa": None, "error": cal_result["error"]}

    return {"default_kappa": round(float(kappa_def), 4),
            "default_recall": round(float(recall_def), 2),
            "best_alpha": cal_result["best_alpha"],
            "best_beta": cal_result["best_beta"],
            "best_SF": cal_result["best_SF"],
            "best_kappa": cal_result["best_kappa"],
            "best_recall": cal_result["best_recall"],
            "improvement": round(cal_result["best_kappa"] - float(kappa_def), 4),
            "kappa_interpretation": cal_result["kappa_interpretation"]}


if __name__ == "__main__":
    print("auto_calibration.py v57.8 — جاهز للاستخدام")
