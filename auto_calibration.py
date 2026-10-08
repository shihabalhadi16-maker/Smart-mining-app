"""
auto_calibration.py — معايرة أوزان DRASTIC-Tox تلقائياً
============================================================
جامعة الخرطوم — كلية الهندسة
نظام التعدين السوداني v57.6

الأسس العلمية:
    - Aller et al. (1987) — USEPA: DRASTIC الأصلي
    - Konaté et al. (2025) — All Earth: دمج CN + Hg في DRASTIC المعدل
    - Karan et al. (2018) — Land Degradation & Development: تحسين الأوزان
    - Landis & Koch (1977) — Biometrics: تفسير Kappa
    - Youden (1950) — Cancer: العتبة المثلى (J statistic)

الميزات:
    - auto_calibrate_weights()     : معايرة (α, β, SF)
    - find_optimal_threshold()      : العتبة المثلى بـ Youden's J
    - compare_with_defaults()       : مقارنة مع الأوزان الافتراضية
    - apply_calibration()           : تطبيق النتائج
    - interpret_kappa()             : تفسير Kappa

الاستخدام:
    from auto_calibration import (
        auto_calibrate_weights,
        find_optimal_threshold,
        compare_with_defaults,
        apply_calibration,
        interpret_kappa,
    )

    result = auto_calibrate_weights(df, mining_type="traditional", n_steps=15)
    if "error" not in result:
        print(f"أفضل Kappa: {result['best_kappa']}")
        print(f"α={result['best_alpha']}, β={result['best_beta']}, SF={result['best_SF']}")
"""

from typing import Optional
import numpy as np
import pandas as pd

# استيراد اختياري لـ sklearn
try:
    from sklearn.metrics import cohen_kappa_score, roc_curve
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False


# ============================================================
# ثوابت المعايرة (يمكن تعديلها)
# ============================================================
CN_LIMIT = 0.05          # mg/L — حد WHO للسيانيد
HG_LIMIT = 0.0007        # mg/L — حد WHO للزئبق
MAX_CN_SCORE = 30.0
MAX_HG_SCORE = 30.0
MAX_TOXICITY_BONUS = 50.0
DEFAULT_THRESHOLD = 140  # عتبة DRASTIC-Tox الافتراضية


# ============================================================
# DRASTIC Rating Functions (مطابقة لـ app.py)
# ============================================================
def get_d_rating(d: float) -> int:
    if d < 0: raise ValueError("Depth cannot be negative")
    if d <= 1.5: return 10
    if d <= 4.6: return 9
    if d <= 9.1: return 7
    if d <= 15.2: return 5
    if d <= 22.9: return 3
    if d <= 30.5: return 2
    return 1


def get_r_rating(r: float) -> int:
    if r < 0: raise ValueError("Recharge cannot be negative")
    if r <= 50.8: return 1
    if r <= 101.6: return 3
    if r <= 177.8: return 6
    if r <= 254.0: return 8
    return 9


def get_a_rating(a: str) -> int:
    return {"massive_shale": 2, "metamorphic_igneous": 3,
            "weathered_metamorphic_igneous": 4, "thin_bedded_sequences": 6,
            "massive_sandstone": 6, "massive_limestone": 6,
            "sand_and_gravel": 8, "basalt": 9, "karst_limestone": 10}.get(a, 6)


def get_s_rating(s: str) -> int:
    return {"thin_or_absent": 10, "gravel": 10, "sand": 9, "peat": 8,
            "shrinking_aggregated_clay": 7, "sandy_loam": 6, "loam": 5,
            "silty_loam": 4, "clay_loam": 3, "muck": 2,
            "nonshrinking_clay": 1}.get(s, 5)


def get_t_rating(t: float) -> int:
    if t < 0: raise ValueError("Slope cannot be negative")
    if t <= 2.0: return 10
    if t <= 6.0: return 9
    if t <= 12.0: return 5
    if t <= 18.0: return 3
    return 1


def get_i_rating(i: str) -> int:
    return {"confining_layer": 1, "silt_clay": 1, "shale": 3,
            "metamorphic_igneous": 4, "limestone": 6, "sandstone": 6,
            "sand_gravel_silt_clay": 6, "sand_gravel": 8,
            "basalt": 9, "karst_limestone": 10}.get(i, 6)


def get_c_rating(c: float) -> int:
    if c < 0: raise ValueError("Conductivity cannot be negative")
    if c <= 4.074: return 1
    if c <= 12.222: return 2
    if c <= 28.518: return 4
    if c <= 40.740: return 6
    if c <= 81.480: return 8
    return 10


def calc_index(D: int, R: int, A: int, S: int, T: int, I: int, C: int) -> int:
    """DRASTIC = D×5 + R×4 + A×3 + S×2 + T×1 + I×5 + C×3 (المدى: 23-230)"""
    return (D * 5) + (R * 4) + (A * 3) + (S * 2) + (T * 1) + (I * 5) + (C * 3)


# ============================================================
# CN & Hg Scores
# ============================================================
def compute_cn_score(cn_mg_l: float) -> float:
    """CN Score = min(30, (CN ÷ 0.05) × 30)"""
    if cn_mg_l < 0:
        return 0.0
    return min(MAX_CN_SCORE, (cn_mg_l / CN_LIMIT) * 30.0)


def compute_hg_score(hg_mg_l: float) -> float:
    """Hg Score = min(30, (Hg ÷ 0.0007) × 30)"""
    if hg_mg_l < 0:
        return 0.0
    return min(MAX_HG_SCORE, (hg_mg_l / HG_LIMIT) * 30.0)


def compute_drastic_for_row(row: pd.Series) -> int:
    """يحسب DRASTIC لصف واحد من DataFrame."""
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


# ============================================================
# ✅ دالة المعايرة الرئيسية (Grid Search)
# ============================================================
def auto_calibrate_weights(
    df: pd.DataFrame,
    mining_type: str = "traditional",
    n_steps: int = 15,
    threshold: int = DEFAULT_THRESHOLD,
    alpha_range: Optional[tuple] = None,
    beta_range: Optional[tuple] = None,
    sf_range: Optional[tuple] = None,
) -> dict:
    """
    بحث شبكي (Grid Search) عن أفضل تركيبة أوزان (α, β, SF)
    تُعطي أعلى قيمة Kappa.

    المعاملات:
    -----------
    df : pd.DataFrame
        يحتوي على الأعمدة الإلزامية:
        - depth_m, recharge_mm, slope_pct, conductivity
        - aquifer, soil, vadose
        - cn_water_mg_l, hg_water_mg_l
        - actual_contaminated (0 أو 1)

    mining_type : str
        "traditional" / "industrial" / "mixed"

    n_steps : int
        عدد القيم المُجرّبة لكل معامل.
        n_steps=15 → 15×15×15 = 3,375 تركيبة (سريع)
        n_steps=25 → 15,625 تركيبة (متوسط)
        n_steps=40 → 64,000 تركيبة (بطيء لكن دقيق)

    threshold : int
        عتبة DRASTIC-Tox للتصنيف الثنائي (افتراضي: 140)

    alpha_range : tuple, optional
        (min, max) لـ α. الافتراضي: (0.1, 0.9)
    beta_range : tuple, optional
        (min, max) لـ β. الافتراضي: (0.1, 1.0)
    sf_range : tuple, optional
        (min, max) لـ SF. الافتراضي: (0.8, 1.5)

    الإرجاع:
    --------
    dict يحتوي على:
        - best_alpha / best_beta / best_SF
        - best_kappa / best_recall
        - all_results: قائمة أفضل 20 تركيبة
        - error: إن فشلت المعايرة
    """
    if not SKLEARN_OK:
        return {"error": "scikit-learn غير مثبت. ثبّته: pip install scikit-learn"}

    # --- 1. التحقق من الأعمدة الإلزامية ---
    required = [
        "depth_m", "recharge_mm", "slope_pct", "conductivity",
        "aquifer", "soil", "vadose",
        "cn_water_mg_l", "hg_water_mg_l",
        "actual_contaminated",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return {"error": f"أعمدة مفقودة: {missing}"}

    if len(df) < 5:
        return {"error": f"عدد المواقع قليل جداً ({len(df)}). مطلوب 5 على الأقل."}

    # --- 2. حساب DRASTIC لكل موقع ---
    drastic_vals = np.array([compute_drastic_for_row(row) for _, row in df.iterrows()])

    # --- 3. استخراج actual_contaminated ---
    actual = df["actual_contaminated"].astype(int).values
    if len(np.unique(actual)) < 2:
        return {"error": "البيانات تحتوي على تصنيف واحد فقط (كلها ملوثة أو كلها نظيفة)"}

    # --- 4. حساب CN_score و Hg_score ---
    cn_scores = np.array([
        compute_cn_score(float(row.get("cn_water_mg_l", 0)))
        for _, row in df.iterrows()
    ])
    hg_scores = np.array([
        compute_hg_score(float(row.get("hg_water_mg_l", 0)))
        for _, row in df.iterrows()
    ])

    # --- 5. تحديد نطاقات البحث ---
    if alpha_range is None:
        alpha_range = (0.1, 0.9)
    if beta_range is None:
        beta_range = (0.1, 1.0)
    if sf_range is None:
        sf_range = (0.8, 1.5)

    alpha_values = np.linspace(alpha_range[0], alpha_range[1], n_steps)
    beta_values = np.linspace(beta_range[0], beta_range[1], n_steps)
    sf_values = np.linspace(sf_range[0], sf_range[1], n_steps)

    # --- 6. البحث الشبكي ---
    best = {"kappa": -999.0, "alpha": 0.5, "beta": 0.5, "SF": 1.0, "recall": 0.0}
    results = []

    for alpha in alpha_values:
        for beta in beta_values:
            base_bonus = np.minimum(
                MAX_TOXICITY_BONUS,
                alpha * cn_scores + beta * hg_scores
            )
            for SF in sf_values:
                bonus = base_bonus * SF
                dt_vals = drastic_vals + bonus
                pred = (dt_vals >= threshold).astype(int)

                # تجنّب التصنيفات الأحادية (كلها 0 أو كلها 1)
                if len(np.unique(pred)) < 2:
                    continue

                try:
                    kappa = cohen_kappa_score(actual, pred)
                except Exception:
                    continue

                # حساب Recall
                tp = int(np.sum((actual == 1) & (pred == 1)))
                fn = int(np.sum((actual == 1) & (pred == 0)))
                recall = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0.0

                results.append({
                    "alpha": round(float(alpha), 3),
                    "beta": round(float(beta), 3),
                    "SF": round(float(SF), 3),
                    "kappa": round(float(kappa), 4),
                    "recall": round(float(recall), 2),
                })

                if kappa > best["kappa"]:
                    best = {
                        "kappa": float(kappa),
                        "alpha": round(float(alpha), 3),
                        "beta": round(float(beta), 3),
                        "SF": round(float(SF), 3),
                        "recall": round(float(recall), 2),
                    }

    # --- 7. التحقق من وجود نتائج ---
    if not results:
        return {
            "error": "لم تُنتج أي تركيبة تصنيفاً متوازناً. "
                     "جرّب تغيير العتبة أو التحقق من البيانات."
        }

    # ترتيب النتائج
    results_sorted = sorted(results, key=lambda x: (-x["kappa"], -x["recall"]))

    return {
        "mining_type": mining_type,
        "n_sites": len(df),
        "n_combinations_tested": len(results),
        "threshold": threshold,
        "best_alpha": best["alpha"],
        "best_beta": best["beta"],
        "best_SF": best["SF"],
        "best_kappa": round(best["kappa"], 4),
        "best_recall": best["recall"],
        "all_results": results_sorted[:20],
        "kappa_interpretation": interpret_kappa(best["kappa"]),
    }


# ============================================================
# ✅ دالة العتبة المثلى — Youden's J (1950)
# ============================================================
def find_optimal_threshold(
    df: pd.DataFrame,
    mining_type: str,
    alpha: float = None,
    beta: float = None,
    SF: float = None,
) -> dict:
    """
    إيجاد العتبة المثالية لتصنيف DRASTIC-Tox باستخدام Youden's J.

    Youden's J = Sensitivity + Specificity − 1
    العتبة المثلى = العتبة التي تُعطي أعلى قيمة J

    المرجع:
        Youden, W.J. (1950). Index for rating diagnostic tests.
        Cancer, 3(1), 32-35.

    المعاملات:
    -----------
    df : pd.DataFrame
        يحتوي على الأعمدة الإلزامية (نفس متطلبات auto_calibrate_weights).

    mining_type : str
        "traditional" / "industrial" / "mixed"

    alpha, beta, SF : float, optional
        الأوزان المُعايرة. إن لم تُمرَّر، تُستخدم الافتراضية.

    الإرجاع:
    --------
    dict: {
        "optimal_threshold": float,
        "J_max": float,
        "sensitivity": float,
        "specificity": float,
        "roc_data": list,
        "default_threshold": int,
        "default_J": float,
        "default_sensitivity": float,
        "default_specificity": float,
    }
    """
    if not SKLEARN_OK:
        return {"error": "scikit-learn غير مثبت"}

    # --- 1. التحقق من الأعمدة ---
    required = [
        "depth_m", "recharge_mm", "slope_pct", "conductivity",
        "aquifer", "soil", "vadose",
        "cn_water_mg_l", "hg_water_mg_l",
        "actual_contaminated",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return {"error": f"أعمدة مفقودة: {missing}"}

    if len(df) < 5:
        return {"error": f"عدد المواقع قليل جداً ({len(df)}). مطلوب 5 على الأقل."}

    # --- 2. اختيار الأوزان ---
    if alpha is None or beta is None or SF is None:
        w = DEFAULT_WEIGHTS.get(mining_type, DEFAULT_WEIGHTS["traditional"])
        alpha = w["alpha"] if alpha is None else alpha
        beta = w["beta"] if beta is None else beta
        SF = w["SF"] if SF is None else SF

    # --- 3. حساب DRASTIC ---
    drastic_vals = np.array([compute_drastic_for_row(row) for _, row in df.iterrows()])
    actual = df["actual_contaminated"].astype(int).values

    if len(np.unique(actual)) < 2:
        return {"error": "البيانات تحتوي على تصنيف واحد فقط"}

    # --- 4. حساب CN/Hg Scores ---
    cn_scores = np.array([
        compute_cn_score(float(row.get("cn_water_mg_l", 0)))
        for _, row in df.iterrows()
    ])
    hg_scores = np.array([
        compute_hg_score(float(row.get("hg_water_mg_l", 0)))
        for _, row in df.iterrows()
    ])

    # --- 5. حساب DRASTIC-Tox ---
    base_bonus = np.minimum(
        MAX_TOXICITY_BONUS,
        alpha * cn_scores + beta * hg_scores
    )
    dt_vals = drastic_vals + base_bonus * SF

    # --- 6. حساب ROC و Youden's J ---
    fpr, tpr, thresholds = roc_curve(actual, dt_vals)
    J_values = tpr - fpr

    # إيجاد أفضل نقطة
    best_idx = int(np.argmax(J_values))
    best_threshold = float(thresholds[best_idx])
    best_J = float(J_values[best_idx])
    best_sens = float(tpr[best_idx])
    best_spec = float(1 - fpr[best_idx])

    # --- 7. مقارنة مع العتبة الافتراضية (140) ---
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
        default_J = 0.0
        default_sens = 0.0
        default_spec = 0.0

    # --- 8. بناء بيانات ROC للعرض ---
    roc_data = []
    for i in range(len(thresholds)):
        roc_data.append({
            "threshold": round(float(thresholds[i]), 1),
            "tpr": round(float(tpr[i]), 3),
            "fpr": round(float(fpr[i]), 3),
            "J": round(float(J_values[i]), 3),
        })

    return {
        "mining_type": mining_type,
        "n_sites": len(df),
        "alpha_used": alpha,
        "beta_used": beta,
        "SF_used": SF,
        "optimal_threshold": round(best_threshold, 1),
        "J_max": round(best_J, 4),
        "sensitivity": round(best_sens, 3),
        "specificity": round(best_spec, 3),
        "default_threshold": default_threshold,
        "default_J": round(default_J, 4),
        "default_sensitivity": round(default_sens, 3),
        "default_specificity": round(default_spec, 3),
        "roc_data": roc_data,
    }


# ============================================================
# تفسير Kappa (Landis & Koch, 1977)
# ============================================================
def interpret_kappa(kappa: float) -> dict:
    """
    تفسير قيمة Kappa وفق Landis & Koch (1977).

    المرجع:
        Landis, J.R., & Koch, G.G. (1977). The measurement of
        observer agreement for categorical data. Biometrics, 33(1), 159-174.
    """
    if kappa >= 0.81:
        return {"level": "ممتاز", "color": "green", "en": "Almost Perfect"}
    elif kappa >= 0.61:
        return {"level": "جيد", "color": "green", "en": "Substantial"}
    elif kappa >= 0.41:
        return {"level": "متوسط", "color": "yellow", "en": "Moderate"}
    elif kappa >= 0.21:
        return {"level": "مقبول", "color": "orange", "en": "Fair"}
    else:
        return {"level": "ضعيف", "color": "red", "en": "Slight/Poor"}


# ============================================================
# تطبيق الأوزان المُعايرة
# ============================================================
def apply_calibration(result: dict, mining_type: str) -> dict:
    """
    تحويل نتيجة المعايرة إلى قاموس أوزان قابل للاستخدام.

    الإرجاع:
    --------
    dict: {"mining_type": ..., "alpha": ..., "beta": ..., "SF": ...,
           "kappa": ..., "ar": "..."}
    """
    if "error" in result:
        raise ValueError(f"لا يمكن تطبيق المعايرة: {result['error']}")

    labels = {
        "industrial": "🏭 صناعي (مُعاير)",
        "traditional": "⛏️ تقليدي (مُعاير)",
        "mixed": "🔀 مختلط (مُعاير)",
    }

    return {
        "mining_type": mining_type,
        "alpha": result["best_alpha"],
        "beta": result["best_beta"],
        "SF": result["best_SF"],
        "kappa": result["best_kappa"],
        "ar": labels.get(mining_type, f"{mining_type} (مُعاير)"),
    }


# ============================================================
# الأوزان الافتراضية (مطابقة لـ app.py)
# ============================================================
DEFAULT_WEIGHTS = {
    "industrial":  {"alpha": 0.7, "beta": 0.5, "SF": 1.0},
    "traditional": {"alpha": 0.3, "beta": 1.0, "SF": 1.1},
    "mixed":       {"alpha": 0.5, "beta": 0.9, "SF": 1.3},
}


# ============================================================
# مقارنة مع الأوزان الافتراضية
# ============================================================
def compare_with_defaults(
    df: pd.DataFrame,
    mining_type: str,
    threshold: int = DEFAULT_THRESHOLD,
) -> dict:
    """
    مقارنة أداء الأوزان الافتراضية مقابل الأوزان المُعايرة.

    الإرجاع:
    --------
    dict: {"default_kappa": ..., "default_recall": ...,
           "best_kappa": ..., "best_recall": ..., "improvement": ...}
    """
    if not SKLEARN_OK:
        return {"error": "scikit-learn غير مثبت"}

    if mining_type not in DEFAULT_WEIGHTS:
        return {"error": f"نمط غير معروف: {mining_type}"}

    # حساب DRASTIC
    drastic_vals = np.array([compute_drastic_for_row(row) for _, row in df.iterrows()])
    actual = df["actual_contaminated"].astype(int).values

    # حساب CN_score و Hg_score
    cn_scores = np.array([
        compute_cn_score(float(row.get("cn_water_mg_l", 0)))
        for _, row in df.iterrows()
    ])
    hg_scores = np.array([
        compute_hg_score(float(row.get("hg_water_mg_l", 0)))
        for _, row in df.iterrows()
    ])

    # 1) أداء الأوزان الافتراضية
    w_def = DEFAULT_WEIGHTS[mining_type]
    base_bonus_def = np.minimum(
        MAX_TOXICITY_BONUS,
        w_def["alpha"] * cn_scores + w_def["beta"] * hg_scores
    )
    dt_def = drastic_vals + base_bonus_def * w_def["SF"]
    pred_def = (dt_def >= threshold).astype(int)

    try:
        kappa_def = cohen_kappa_score(actual, pred_def)
    except Exception:
        kappa_def = 0.0

    tp_def = int(np.sum((actual == 1) & (pred_def == 1)))
    fn_def = int(np.sum((actual == 1) & (pred_def == 0)))
    recall_def = (tp_def / (tp_def + fn_def) * 100) if (tp_def + fn_def) > 0 else 0.0

    # 2) تشغيل المعايرة
    cal_result = auto_calibrate_weights(df, mining_type, threshold=threshold)

    if "error" in cal_result:
        return {
            "default_kappa": round(float(kappa_def), 4),
            "default_recall": round(float(recall_def), 2),
            "best_kappa": None,
            "error": cal_result["error"],
        }

    return {
        "default_kappa": round(float(kappa_def), 4),
        "default_recall": round(float(recall_def), 2),
        "best_alpha": cal_result["best_alpha"],
        "best_beta": cal_result["best_beta"],
        "best_SF": cal_result["best_SF"],
        "best_kappa": cal_result["best_kappa"],
        "best_recall": cal_result["best_recall"],
        "improvement": round(cal_result["best_kappa"] - float(kappa_def), 4),
        "kappa_interpretation": cal_result["kappa_interpretation"],
    }


# ============================================================
# اختبار ذاتي (يُشغَّل بـ python auto_calibration.py)
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("auto_calibration.py v57.6 — اختبار ذاتي")
    print("=" * 60)

    # بيانات تجريبية
    test_df = pd.DataFrame({
        "depth_m": [12, 15, 20, 18, 25, 10, 22, 14, 30, 16, 19],
        "recharge_mm": [20, 18, 25, 15, 30, 22, 12, 28, 8, 24, 16],
        "slope_pct": [3, 4, 6, 2, 5, 3.5, 7, 2.5, 8, 4.5, 5.5],
        "conductivity": [3.0, 2.5, 5.0, 4.5, 6.0, 2.0, 7.5, 3.5, 8.0, 4.0, 5.5],
        "aquifer": ["massive_sandstone", "sand_and_gravel",
                    "metamorphic_igneous", "massive_sandstone",
                    "sand_and_gravel", "metamorphic_igneous",
                    "massive_sandstone", "sand_and_gravel",
                    "metamorphic_igneous", "massive_sandstone",
                    "sand_and_gravel"],
        "soil": ["sand", "sandy_loam", "gravel", "sand", "sandy_loam",
                 "gravel", "sand", "sandy_loam", "gravel", "sand", "sandy_loam"],
        "vadose": ["sand_gravel", "sandstone", "metamorphic_igneous",
                   "sand_gravel", "sandstone", "metamorphic_igneous",
                   "sand_gravel", "sandstone", "metamorphic_igneous",
                   "sand_gravel", "sandstone"],
        "cn_water_mg_l": [0.025, 0.011, 0.050, 0.030, 0.045,
                          0.020, 0.015, 0.035, 0.060, 0.022, 0.028],
        "hg_water_mg_l": [0.011, 0.008, 0.0015, 0.012, 0.020,
                          0.005, 0.0008, 0.015, 0.025, 0.010, 0.013],
        "actual_contaminated": [1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1],
    })

    # --- اختبار 1: المعايرة ---
    print("\n[1] اختبار auto_calibrate_weights()")
    result = auto_calibrate_weights(test_df, "traditional", n_steps=10)

    if "error" in result:
        print(f"   ❌ {result['error']}")
    else:
        print(f"   ✅ أفضل تركيبة:")
        print(f"      α (CN) = {result['best_alpha']}")
        print(f"      β (Hg) = {result['best_beta']}")
        print(f"      SF     = {result['best_SF']}")
        print(f"      Kappa  = {result['best_kappa']} ({result['kappa_interpretation']['level']})")
        print(f"      Recall = {result['best_recall']}%")

    # --- اختبار 2: العتبة المثلى ---
    print("\n[2] اختبار find_optimal_threshold()")
    opt = find_optimal_threshold(test_df, "traditional")

    if "error" in opt:
        print(f"   ❌ {opt['error']}")
    else:
        print(f"   ✅ العتبة المثلى: {opt['optimal_threshold']}")
        print(f"      J = {opt['J_max']}")
        print(f"      Sensitivity = {opt['sensitivity']}")
        print(f"      Specificity = {opt['specificity']}")
        print(f"      العتبة الافتراضية: {opt['default_threshold']} (J = {opt['default_J']})")

    # --- اختبار 3: المقارنة ---
    print("\n[3] اختبار compare_with_defaults()")
    cmp = compare_with_defaults(test_df, "traditional")

    if "error" in cmp:
        print(f"   ❌ {cmp['error']}")
    else:
        print(f"   الافتراضي: Kappa={cmp['default_kappa']}, Recall={cmp['default_recall']}%")
        if cmp.get("best_kappa"):
            print(f"   المُعاير:  Kappa={cmp['best_kappa']}, Recall={cmp['best_recall']}%")
            print(f"   التحسّن:   {cmp['improvement']:+.4f}")

    print("\n" + "=" * 60)
    print("✅ اكتمل الاختبار")
    print("=" * 60)
