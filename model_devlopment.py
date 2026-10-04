"""
تطوير النموذج — v56.2
=====================================
- إضافة مواقع رمادية (Gray Zone)
- معايرة α و β (Grid Search)
- مقارنة النماذج (4 نماذج)
"""
import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score, roc_auc_score, confusion_matrix


# ============================================================
# 1. المواقع الرمادية (Gray Zone Sites)
# ============================================================
# ⚠️ ملاحظة: هذه مواقع **افتراضية** لاختبار المنهجية
# القيم مشتقة من النطاقات الفعلية بين المواقع الموثقة
GRAY_ZONE_SITES = [
    # مواقع بقيم متوسطة (CN 0.025-0.045، Hg 0.005-0.010)
    {"name": "GZ-01", "depth_m": 16.0, "recharge_mm": 16.0, "slope_pct": 3.5,
     "conductivity": 2.8, "aquifer": "massive_sandstone", "soil": "sand",
     "vadose": "sand_gravel", "cn_water_mg_l": 0.035, "hg_water_mg_l": 0.007,
     "actual_contaminated": 1, "type": "gray_zone"},
    {"name": "GZ-02", "depth_m": 18.0, "recharge_mm": 15.0, "slope_pct": 4.0,
     "conductivity": 3.2, "aquifer": "sand_and_gravel", "soil": "sandy_loam",
     "vadose": "sandstone", "cn_water_mg_l": 0.028, "hg_water_mg_l": 0.005,
     "actual_contaminated": 1, "type": "gray_zone"},
    {"name": "GZ-03", "depth_m": 20.0, "recharge_mm": 14.0, "slope_pct": 4.5,
     "conductivity": 3.5, "aquifer": "massive_sandstone", "soil": "sand",
     "vadose": "sand_gravel", "cn_water_mg_l": 0.042, "hg_water_mg_l": 0.009,
     "actual_contaminated": 0, "type": "gray_zone"},
    {"name": "GZ-04", "depth_m": 15.0, "recharge_mm": 18.0, "slope_pct": 3.0,
     "conductivity": 2.5, "aquifer": "massive_sandstone", "soil": "sandy_loam",
     "vadose": "sand_gravel", "cn_water_mg_l": 0.030, "hg_water_mg_l": 0.006,
     "actual_contaminated": 0, "type": "gray_zone"},
    {"name": "GZ-05", "depth_m": 22.0, "recharge_mm": 13.0, "slope_pct": 5.0,
     "conductivity": 3.8, "aquifer": "sand_and_gravel", "soil": "sand",
     "vadose": "sandstone", "cn_water_mg_l": 0.045, "hg_water_mg_l": 0.010,
     "actual_contaminated": 1, "type": "gray_zone"},
    {"name": "GZ-06", "depth_m": 14.0, "recharge_mm": 17.0, "slope_pct": 3.5,
     "conductivity": 2.7, "aquifer": "massive_sandstone", "soil": "sandy_loam",
     "vadose": "sand_gravel", "cn_water_mg_l": 0.038, "hg_water_mg_l": 0.008,
     "actual_contaminated": 0, "type": "gray_zone"},
]


# ============================================================
# 2. معايرة α و β — Grid Search
# ============================================================
def calibrate_alpha_beta(df, thresholds_dict, alpha_range=None, beta_range=None):
    """
    Grid Search لإيجاد أفضل α و β
    
    Parameters:
    -----------
    df : DataFrame
        يجب أن يحتوي على: DRASTIC (أو D_r, R_r, ...), CN, Hg, actual_contaminated
    thresholds_dict : dict
        dict {'DRASTIC': 100, 'DRASTIC-T': 140}
    alpha_range : list
        نطاق α (افتراضي: [0.1, 0.3, 0.5, 0.7, 0.9])
    beta_range : list
        نطاق β (افتراضي: [0.1, 0.3, 0.5, 0.7, 0.9])
    
    Returns:
    --------
    dict with: best_alpha, best_beta, best_kappa, results_df
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
    th_dt = thresholds_dict.get("DRASTIC-T", 140)
    
    for alpha in alpha_range:
        for beta in beta_range:
            # حساب DRASTIC-T
            dts = []
            for i in range(len(df)):
                # حساب toxicity bonus
                cn_score = min(30.0, (cn[i] / 0.05) * 30.0)
                hg_score = min(30.0, (hg[i] / 0.0007) * 30.0)
                bonus = min(50.0, alpha * cn_score + beta * hg_score)
                dts.append(base_drastic[i] + bonus)
            
            dts = np.array(dts)
            y_pred = (dts >= th_dt).astype(int)
            
            try:
                kappa = cohen_kappa_score(y_true, y_pred)
                acc = np.mean(y_true == y_pred) * 100
                recall = (np.sum((y_true==1)&(y_pred==1)) / 
                          max(1, np.sum(y_true==1))) * 100
                
                results.append({
                    "alpha": alpha,
                    "beta": beta,
                    "kappa": round(kappa, 3),
                    "accuracy": round(acc, 1),
                    "recall": round(recall, 1)
                })
            except Exception:
                continue
    
    results_df = pd.DataFrame(results)
    
    if results_df.empty:
        return {"error": "No valid results"}
    
    # أفضل توليفة (حسب Kappa)
    best_idx = results_df["kappa"].idxmax()
    best = results_df.loc[best_idx]
    
    # أفضل توليفة متوازنة (Kappa عالي + Recall عالي)
    results_df["score"] = results_df["kappa"] * 0.5 + results_df["recall"] / 100 * 0.5
    best_balanced_idx = results_df["score"].idxmax()
    best_balanced = results_df.loc[best_balanced_idx]
    
    return {
        "best_kappa": {
            "alpha": float(best["alpha"]),
            "beta": float(best["beta"]),
            "kappa": float(best["kappa"]),
            "accuracy": float(best["accuracy"]),
            "recall": float(best["recall"])
        },
        "best_balanced": {
            "alpha": float(best_balanced["alpha"]),
            "beta": float(best_balanced["beta"]),
            "kappa": float(best_balanced["kappa"]),
            "accuracy": float(best_balanced["accuracy"]),
            "recall": float(best_balanced["recall"])
        },
        "results": results_df
    }


# ============================================================
# 3. مقارنة النماذج
# ============================================================
def calculate_ahp_weights():
    """
    حساب أوزان AHP للـ 7 معايير
    (مبسطة — بدون مصفوفة المقارنات الكاملة)
    """
    # مصفوفة المقارنات (D, R, A, S, T, I, C)
    # D > I > R > C > A > S > T
    comparison = np.array([
        [1,   2,   3,   4,   7,   2,   3],   # D
        [1/2, 1,   2,   3,   5,   1,   2],   # R
        [1/3, 1/2, 1,   2,   4,   1,   1],   # A
        [1/4, 1/3, 1/2, 1,   3,   1/2, 1/2], # S
        [1/7, 1/5, 1/4, 1/3, 1,   1/5, 1/4], # T
        [1/2, 1,   1,   2,   5,   1,   2],   # I
        [1/3, 1/2, 1,   2,   4,   1/2, 1],   # C
    ])
    
    # حساب الأوزان (eigenvector)
    eigvals, eigvecs = np.linalg.eig(comparison)
    max_idx = np.argmax(eigvals.real)
    weights = eigvecs[:, max_idx].real
    weights = weights / weights.sum()
    
    # تحويل إلى سلم 1-5 (لتسهيل المقارنة)
    weights_scaled = np.round(weights * 7 / weights.max(), 1)
    weights_scaled = np.clip(weights_scaled, 1, 5)
    
    return {
        "D": float(weights_scaled[0]),
        "R": float(weights_scaled[1]),
        "A": float(weights_scaled[2]),
        "S": float(weights_scaled[3]),
        "T": float(weights_scaled[4]),
        "I": float(weights_scaled[5]),
        "C": float(weights_scaled[6]),
        "raw_weights": weights.tolist()
    }


def compare_models(df, get_rating_funcs, calc_index_func):
    """
    مقارنة 4 نماذج:
    1. DRASTIC (الأساسي)
    2. DRASTIC-T (الحالي)
    3. DRASTIC-Lu (مع استخدام الأرض)
    4. AHP-DRASTIC
    
    Returns:
    --------
    dict with results for each model
    """
    get_d, get_r, get_a, get_s, get_t, get_i, get_c = get_rating_funcs
    y_true = df["actual_contaminated"].values
    n = len(df)
    
    # تحويل المعايير إلى ratings
    D_r = np.array([get_d(float(v)) for v in df["depth_m"]])
    R_r = np.array([get_r(float(v)) for v in df["recharge_mm"]])
    A_r = np.array([get_a(str(v)) for v in df["aquifer"]])
    S_r = np.array([get_s(str(v)) for v in df["soil"]])
    T_r = np.array([get_t(float(v)) for v in df["slope_pct"]])
    I_r = np.array([get_i(str(v)) for v in df["vadose"]])
    C_r = np.array([get_c(float(v)) for v in df["conductivity"]])
    cn = df["cn_water_mg_l"].values
    hg = df["hg_water_mg_l"].values
    
    results = {}
    
    # 1. DRASTIC الأصلي
    drastic = D_r*5 + R_r*4 + A_r*3 + S_r*2 + T_r*1 + I_r*5 + C_r*3
    results["DRASTIC"] = evaluate_model(y_true, drastic, 100)
    results["DRASTIC"]["values"] = drastic.tolist()
    
    # 2. DRASTIC-T
    drastic_t = []
    for i in range(n):
        cn_score = min(30.0, (cn[i] / 0.05) * 30.0)
        hg_score = min(30.0, (hg[i] / 0.0007) * 30.0)
        bonus = min(50.0, 0.5 * cn_score + 0.5 * hg_score)
        drastic_t.append(drastic[i] + bonus)
    drastic_t = np.array(drastic_t)
    results["DRASTIC-T"] = evaluate_model(y_true, drastic_t, 140)
    results["DRASTIC-T"]["values"] = drastic_t.tolist()
    
    # 3. DRASTIC-Lu (معامل استخدام الأرض)
    # نستخدم CN كمؤشر لاستخدام الأرض
    land_use_factor = np.minimum(1.0, cn / 0.05)  # 0-1
    drastic_lu = drastic * (1 + 0.3 * land_use_factor)
    results["DRASTIC-Lu"] = evaluate_model(y_true, drastic_lu, 140)
    results["DRASTIC-Lu"]["values"] = drastic_lu.tolist()
    
    # 4. AHP-DRASTIC
    ahp = calculate_ahp_weights()
    drastic_ahp = (D_r*ahp["D"] + R_r*ahp["R"] + A_r*ahp["A"] + S_r*ahp["S"] +
                   T_r*ahp["T"] + I_r*ahp["I"] + C_r*ahp["C"])
    results["AHP-DRASTIC"] = evaluate_model(y_true, drastic_ahp, 100)
    results["AHP-DRASTIC"]["values"] = drastic_ahp.tolist()
    results["AHP-DRASTIC"]["weights"] = ahp
    
    return results


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
            "threshold": threshold
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# 4. دمج البيانات الأصلية + الرمادية
# ============================================================
def merge_with_gray_zone(df_original, gray_sites=None):
    """دمج المواقع الرمادية مع الأصلية"""
    if gray_sites is None:
        gray_sites = GRAY_ZONE_SITES
    
    df_gray = pd.DataFrame(gray_sites)
    df_combined = pd.concat([df_original, df_gray], ignore_index=True)
    return df_combined
