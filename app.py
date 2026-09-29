"""
نظام التعدين السوداني v37.0 - النسخة الكاملة النهائية
يشمل:
- التقييم الأساسي DRASTIC
- Monte Carlo
- تحليل الحساسية
- تحليل السمية
- GIS
- التحقق الفعلي (Validation)
- DRASTIC-P (المؤشر المعدل للتعدين)
- التقييم الديناميكي (Dynamic)
"""
import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import numpy as np
import datetime
import requests
import json
import random as _rnd
from datetime import timedelta

# ============ استيراد PIL ============
try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False

# ============ إعدادات الصفحة ============
if PIL_OK:
    try:
        _logo = Image.open("logo.png")
        st.set_page_config(page_title="نظام التعدين السوداني",
                           page_icon=_logo, layout="wide",
                           initial_sidebar_state="expanded")
    except Exception:
        st.set_page_config(page_title="نظام التعدين السوداني",
                           page_icon="⛏️", layout="wide",
                           initial_sidebar_state="expanded")
else:
    st.set_page_config(page_title="نظام التعدين السوداني",
                       page_icon="⛏️", layout="wide",
                       initial_sidebar_state="expanded")

# ============ CSS ============
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: 'Segoe UI', 'Tahoma', 'Arial', sans-serif;
    }
    .stButton > button { border-radius: 8px; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 12px;
        font-size: 0.9em;
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #d4af37;
        border-radius: 10px;
        padding: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    [data-testid="stSidebar"] {
        background-color: #f5eedc;
        border-right: 2px solid #c19a6b;
    }
    .header-container {
        background: linear-gradient(135deg, #5c2c16 0%, #c19a6b 100%);
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        color: white;
        text-align: center;
    }
    .header-title { font-size: 1.8em; font-weight: bold; margin: 0; }
    .header-subtitle { font-size: 1.0em; opacity: 0.9; margin: 5px 0 0 0; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ============ استيراد data_sources ============
try:
    from data_sources import (
        get_preset_locations_for_app, get_data_summary,
        KNOWN_MINING_SITES, NARIS_WELLS, DARFUR_WELLS, KHARTOUM_LOCALITIES)
    DS_OK = True
except ImportError:
    DS_OK = False


# ============================================================
# ============ DRASTIC FUNCTIONS ============
# ============================================================
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

def classify(idx):
    if idx >= 180: return {"level": "مرتفع جدا", "color": "red", "action": "معالجة فورية"}
    if idx >= 140: return {"level": "مرتفع", "color": "orange", "action": "مراقبة عاجلة"}
    if idx >= 100: return {"level": "متوسط", "color": "yellow", "action": "مراقبة دورية"}
    return {"level": "منخفض", "color": "green", "action": "مراقبة روتينية"}

def calc_travel(d, p, k, i=0.01):
    """Darcy velocity: v = K*i/n"""
    if d <= 0: raise ValueError("D>0")
    if not (0.01 < p < 0.60): raise ValueError("Porosity")
    if k <= 0: raise ValueError("K>0")
    if not (0.0001 <= i <= 0.5): raise ValueError("Gradient")
    v = (k * i) / p
    days = d / v
    return {"days": round(days, 2), "years": round(days / 365.25, 3),
            "velocity": round(v, 6), "gradient": i}

def mitigate(idx, hdpe=False, treat=False, mon=False):
    m = float(idx)
    if hdpe: m *= 0.40
    if treat: m *= 0.60
    if mon: m *= 0.85
    red = ((idx - m) / idx * 100) if idx > 0 else 0.0
    methods = []
    if hdpe: methods.append("HDPE Liner")
    if treat: methods.append("Cyanide Treatment")
    if mon: methods.append("Monitoring Wells")
    return {"mitigated_index": round(m, 1),
            "reduction_pct": round(red, 1), "methods": methods}


# ============================================================
# ============ Sensitivity Analysis ============
# ============================================================
def sensitivity_analysis(physical_values, variation=0.10):
    """تحليل الحساسية على القيم الفيزيائية الأصلية"""
    D_phys = float(physical_values.get("depth", 15.0))
    R_phys = float(physical_values.get("recharge", 100.0))
    A_phys = str(physical_values.get("aquifer", "massive_sandstone"))
    S_phys = str(physical_values.get("soil", "sand"))
    T_phys = float(physical_values.get("slope", 4.0))
    I_phys = str(physical_values.get("vadose", "sand_gravel"))
    C_phys = float(physical_values.get("conductivity", 5.0))

    def compute_index(d, r, a, s, t, i, c):
        return calc_index(get_d_rating(d), get_r_rating(r), get_a_rating(a),
                          get_s_rating(s), get_t_rating(t), get_i_rating(i),
                          get_c_rating(c))

    base = compute_index(D_phys, R_phys, A_phys, S_phys, T_phys, I_phys, C_phys)
    results = {}

    D_mod = max(0.5, min(100.0, D_phys * (1 + variation)))
    ni = compute_index(D_mod, R_phys, A_phys, S_phys, T_phys, I_phys, C_phys)
    results["D"] = {"original_phys": D_phys, "modified_phys": round(D_mod, 2),
                    "original_rating": get_d_rating(D_phys),
                    "new_rating": get_d_rating(D_mod),
                    "new_index": ni, "change": ni - base,
                    "sensitivity": round(abs(ni - base) / base * 100, 3)}

    R_mod = max(0.0, min(400.0, R_phys * (1 + variation)))
    ni = compute_index(D_phys, R_mod, A_phys, S_phys, T_phys, I_phys, C_phys)
    results["R"] = {"original_phys": R_phys, "modified_phys": round(R_mod, 2),
                    "original_rating": get_r_rating(R_phys),
                    "new_rating": get_r_rating(R_mod),
                    "new_index": ni, "change": ni - base,
                    "sensitivity": round(abs(ni - base) / base * 100, 3)}

    for param, base_r, weight in [("A", get_a_rating(A_phys), 3),
                                   ("S", get_s_rating(S_phys), 2),
                                   ("I", get_i_rating(I_phys), 5)]:
        new_r = max(1, min(10, base_r + 1))
        ni = base - base_r * weight + new_r * weight
        results[param] = {"original_phys": "rating",
                          "modified_phys": "rating +1",
                          "original_rating": base_r,
                          "new_rating": new_r,
                          "new_index": ni, "change": ni - base,
                          "sensitivity": round(abs(ni - base) / base * 100, 3)}

    T_mod = max(0.0, min(30.0, T_phys * (1 + variation)))
    ni = compute_index(D_phys, R_phys, A_phys, S_phys, T_mod, I_phys, C_phys)
    results["T"] = {"original_phys": T_phys, "modified_phys": round(T_mod, 2),
                    "original_rating": get_t_rating(T_phys),
                    "new_rating": get_t_rating(T_mod),
                    "new_index": ni, "change": ni - base,
                    "sensitivity": round(abs(ni - base) / base * 100, 3)}

    C_mod = max(0.01, min(100.0, C_phys * (1 + variation)))
    ni = compute_index(D_phys, R_phys, A_phys, S_phys, T_phys, I_phys, C_mod)
    results["C"] = {"original_phys": C_phys, "modified_phys": round(C_mod, 2),
                    "original_rating": get_c_rating(C_phys),
                    "new_rating": get_c_rating(C_mod),
                    "new_index": ni, "change": ni - base,
                    "sensitivity": round(abs(ni - base) / base * 100, 3)}

    sorted_r = dict(sorted(results.items(),
                            key=lambda x: x[1]["sensitivity"], reverse=True))
    return {"base_index": base, "parameters": sorted_r,
            "most_sensitive": list(sorted_r.keys())[0] if sorted_r else None}


# ============================================================
# ============ Monte Carlo ============
# ============================================================
def monte_carlo_analysis(physical_values, n_iter=1000, variation=0.15):
    """محاكاة Monte Carlo باستخدام numpy"""
    np.random.seed(42)

    D = float(physical_values.get("depth", 15.0))
    R = float(physical_values.get("recharge", 100.0))
    A_base = get_a_rating(str(physical_values.get("aquifer", "massive_sandstone")))
    S_base = get_s_rating(str(physical_values.get("soil", "sand")))
    T = float(physical_values.get("slope", 4.0))
    I_base = get_i_rating(str(physical_values.get("vadose", "sand_gravel")))
    C = float(physical_values.get("conductivity", 5.0))

    D_s = np.clip(np.random.normal(D, max(0.5, D * variation), n_iter), 0.5, 100.0)
    if R > 0:
        R_s = np.clip(np.random.lognormal(np.log(max(1, R)) - 0.5 * variation**2,
                                           variation, n_iter), 0.0, 400.0)
    else:
        R_s = np.zeros(n_iter)
    A_s = np.random.choice([max(1, A_base - 1), A_base, min(10, A_base + 1)],
                            n_iter, p=[0.15, 0.70, 0.15])
    S_s = np.random.choice([max(1, S_base - 1), S_base, min(10, S_base + 1)],
                            n_iter, p=[0.15, 0.70, 0.15])
    T_s = np.clip(np.random.normal(T, max(0.5, T * variation), n_iter), 0.0, 30.0)
    I_s = np.random.choice([max(1, I_base - 1), I_base, min(10, I_base + 1)],
                            n_iter, p=[0.15, 0.70, 0.15])
    C_s = np.clip(np.random.lognormal(np.log(max(0.01, C)) - 0.5 * variation**2,
                                       variation, n_iter), 0.01, 100.0)

    D_r = np.select([D_s <= 1.5, D_s <= 4.6, D_s <= 9.1, D_s <= 15.2,
                     D_s <= 22.9, D_s <= 30.5], [10, 9, 7, 5, 3, 2], default=1)
    R_r = np.select([R_s <= 50.8, R_s <= 101.6, R_s <= 177.8, R_s <= 254.0],
                    [1, 3, 6, 8], default=9)
    T_r = np.select([T_s <= 2.0, T_s <= 6.0, T_s <= 12.0, T_s <= 18.0],
                    [10, 9, 5, 3], default=1)
    C_r = np.select([C_s <= 4.074, C_s <= 12.222, C_s <= 28.518,
                     C_s <= 40.740, C_s <= 81.480],
                    [1, 2, 4, 6, 8], default=10)

    drastic = (D_r * 5 + R_r * 4 + A_s * 3 + S_s * 2 +
               T_r * 1 + I_s * 5 + C_r * 3)
    results = np.sort(drastic.astype(int))
    n = len(results)

    def pct(p): return int(np.percentile(results, p))

    return {
        "base": calc_index(get_d_rating(D), get_r_rating(R), A_base, S_base,
                           get_t_rating(T), I_base, get_c_rating(C)),
        "n": n, "mean": round(float(np.mean(results)), 1),
        "std": round(float(np.std(results)), 2),
        "min": int(results[0]), "max": int(results[-1]),
        "p5": pct(5), "p25": pct(25), "p50": pct(50),
        "p75": pct(75), "p95": pct(95),
        "ci_90": (pct(5), pct(95)), "ci_50": (pct(25), pct(75)),
        "prob_over_140": round(float(np.mean(results >= 140) * 100), 1),
        "prob_over_180": round(float(np.mean(results >= 180) * 100), 1),
        "samples": results}


# ============================================================
# ============ Validation Module ============
# ============================================================
def calculate_confusion_matrix(predicted, actual, threshold=140):
    """حساب مصفوفة الالتباس والمقاييس الإحصائية"""
    predicted = np.array(predicted)
    actual = np.array(actual)
    pred_class = (predicted >= threshold).astype(int)

    tp = int(np.sum((pred_class == 1) & (actual == 1)))
    tn = int(np.sum((pred_class == 0) & (actual == 0)))
    fp = int(np.sum((pred_class == 1) & (actual == 0)))
    fn = int(np.sum((pred_class == 0) & (actual == 1)))
    total = tp + tn + fp + fn

    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0
    npv = tn / (tn + fn) if (tn + fn) > 0 else 0
    po = accuracy
    pe = ((tp + fp) * (tp + fn) + (tn + fn) * (tn + fp)) / (total ** 2) if total > 0 else 0
    kappa = ((po - pe) / (1 - pe)) if (1 - pe) > 0 else 0
    mcc_num = (tp * tn) - (fp * fn)
    mcc_den = np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = mcc_num / mcc_den if mcc_den > 0 else 0
    tpr = recall
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
    youden = tpr - fpr
    balanced_acc = (recall + specificity) / 2

    return {
        "confusion_matrix": {"TP": tp, "TN": tn, "FP": fp, "FN": fn, "Total": total},
        "accuracy": round(accuracy * 100, 2),
        "precision": round(precision * 100, 2),
        "recall": round(recall * 100, 2),
        "specificity": round(specificity * 100, 2),
        "f1_score": round(f1 * 100, 2),
        "npv": round(npv * 100, 2),
        "balanced_accuracy": round(balanced_acc * 100, 2),
        "kappa": round(kappa, 4),
        "mcc": round(mcc, 4),
        "youden_j": round(youden, 4),
        "threshold": threshold}

def analyze_validation_by_level(predicted, actual):
    """تحليل الدقة حسب المستوى"""
    predicted = np.array(predicted)
    actual = np.array(actual)
    levels = []
    for idx in predicted:
        if idx < 100: levels.append("منخفض")
        elif idx < 140: levels.append("متوسط")
        elif idx < 180: levels.append("مرتفع")
        else: levels.append("مرتفع جدا")

    df = pd.DataFrame({"predicted_index": predicted, "actual": actual,
                        "level": levels})
    results = []
    for level in ["منخفض", "متوسط", "مرتفع", "مرتفع جدا"]:
        sub = df[df["level"] == level]
        if len(sub) > 0:
            if level in ["مرتفع", "مرتفع جدا"]:
                correct = (sub["actual"] == 1).sum()
            elif level == "منخفض":
                correct = (sub["actual"] == 0).sum()
            else:
                correct = 0
            results.append({
                "المستوى": level, "العدد": len(sub),
                "التصنيفات الصحيحة": int(correct),
                "نسبة الدقة": round(correct / len(sub) * 100, 1)})
    return pd.DataFrame(results)

def generate_validation_report(metrics):
    L = ["=" * 60, "تقرير التحقق الفعلي (Model Validation)",
         "نظام التعدين السوداني", "=" * 60, "",
         "التاريخ: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "",
         "=" * 60, "مصفوفة الالتباس", "=" * 60]
    cm = metrics["confusion_matrix"]
    L.append(f"  True Positive  (TP): {cm['TP']}")
    L.append(f"  True Negative  (TN): {cm['TN']}")
    L.append(f"  False Positive (FP): {cm['FP']}")
    L.append(f"  False Negative (FN): {cm['FN']}")
    L.append(f"  المجموع: {cm['Total']}")
    L.append("")
    L.append("=" * 60 + "\nمقاييس الدقة\n" + "=" * 60)
    L.append(f"  Accuracy:             {metrics['accuracy']} %")
    L.append(f"  Precision:            {metrics['precision']} %")
    L.append(f"  Recall:               {metrics['recall']} %")
    L.append(f"  Specificity:          {metrics['specificity']} %")
    L.append(f"  F1-Score:             {metrics['f1_score']} %")
    L.append(f"  NPV:                  {metrics['npv']} %")
    L.append(f"  Balanced Accuracy:    {metrics['balanced_accuracy']} %")
    L.append(f"  Cohen's Kappa:        {metrics['kappa']}")
    L.append(f"  MCC:                  {metrics['mcc']}")
    L.append(f"  Youden's J:           {metrics['youden_j']}")
    return "\n".join(L)


# ============================================================
# ============ DRASTIC-P Module ============
# ============================================================
def calculate_cyanide_risk_index(cn_w, cn_s, dist, seepage):
    """CRI - مؤشر مخاطر السيانيد"""
    CN_W, CN_S = 0.07, 10.0
    w_ratio = cn_w / CN_W
    s_ratio = cn_s / CN_S
    distance_factor = max(0.1, min(1.0, 100.0 / max(1, dist)))
    seepage_factor = max(0.1, min(1.0, seepage))
    cri = (w_ratio * 0.5 + s_ratio * 0.3) * distance_factor * seepage_factor

    if cri <= 0.5: level, color, action = "منخفض", "green", "مراقبة روتينية"
    elif cri <= 2.0: level, color, action = "متوسط", "yellow", "مراقبة دورية"
    elif cri <= 5.0: level, color, action = "مرتفع", "orange", "تدخل عاجل"
    else: level, color, action = "مرتفع جدا", "red", "إيقاف فوري"

    return {"cri": round(cri, 3), "water_ratio": round(w_ratio, 2),
            "soil_ratio": round(s_ratio, 2),
            "distance_factor": round(distance_factor, 3),
            "seepage_factor": round(seepage_factor, 3),
            "level": level, "color": color, "action": action}

def calculate_mercury_risk_index(hg_w, hg_s, bio, use="drinking"):
    """MRI - مؤشر مخاطر الزئبق"""
    limits = {"drinking": {"water": 0.006, "soil": 1.0},
              "irrigation": {"water": 0.001, "soil": 1.0},
              "industrial": {"water": 0.05, "soil": 5.0}}
    lim = limits.get(use, limits["drinking"])
    w_ratio = hg_w / lim["water"]
    s_ratio = hg_s / lim["soil"]
    mri = (w_ratio * 0.6 + s_ratio * 0.4) * bio

    if mri <= 0.5: level, color, action = "منخفض", "green", "مراقبة روتينية"
    elif mri <= 2.0: level, color, action = "متوسط", "yellow", "مراقبة دورية"
    elif mri <= 5.0: level, color, action = "مرتفع", "orange", "تدخل عاجل"
    else: level, color, action = "مرتفع جدا", "red", "إيقاف فوري"

    return {"mri": round(mri, 3), "water_ratio": round(w_ratio, 2),
            "soil_ratio": round(s_ratio, 2), "level": level,
            "color": color, "action": action}

def calculate_modified_drastic(base, cri=0, mri=0, amd=0):
    """DRASTIC-P = DRASTIC × (1 + α×CRI + β×MRI + γ×AMD)"""
    alpha, beta, gamma = 0.15, 0.20, 0.10
    modifier = 1.0 + (alpha * cri) + (beta * mri) + (gamma * amd)
    modified = min(230, base * modifier)
    increase = ((modified - base) / base * 100) if base > 0 else 0

    if modified >= 180: level, color = "مرتفع جدا", "red"
    elif modified >= 140: level, color = "مرتفع", "orange"
    elif modified >= 100: level, color = "متوسط", "yellow"
    else: level, color = "منخفض", "green"

    return {"base_drastic": base, "modified_drastic": round(modified, 1),
            "modifier_factor": round(modifier, 3),
            "increase_pct": round(increase, 1),
            "cri": cri, "mri": mri, "amd_risk": amd,
            "level": level, "color": color}


# ============================================================
# ============ Dynamic Module ============
# ============================================================
def project_drastic_change(base, years=10, mining=0.05, climate=-0.02, pop=0.03):
    """توقع تغير DRASTIC مع الزمن"""
    proj = []
    for year in range(years + 1):
        if year == 0:
            proj.append({"السنة": 0, "المؤشر": round(base, 1),
                          "الزيادة_المئوية": 0})
            continue
        mf = 1 + (mining * year)
        cf = 1 + (climate * year)
        pf = 1 + (pop * year * 0.5)
        ni = min(230, base * mf * cf * pf)
        inc = ((ni - base) / base * 100) if base > 0 else 0
        proj.append({"السنة": year, "المؤشر": round(ni, 1),
                      "الزيادة_المئوية": round(inc, 1)})
    return {"base_index": base, "years": years, "projections": proj,
            "final_index": proj[-1]["المؤشر"],
            "total_increase_pct": proj[-1]["الزيادة_المئوية"]}

def estimate_mitigation_impact(base, years=10, mit_year=3):
    """تقدير تأثير الحلول"""
    rows = []
    for year in range(years + 1):
        mf = 1 + (0.05 * year)
        cf = 1 + (-0.02 * year)
        no_mit = min(230, base * mf * cf)
        if year >= mit_year:
            eff = max(0.3, 1 - 0.15 * min(year - mit_year + 1, 5))
        else:
            eff = 1.0
        with_mit = min(230, base * mf * cf * eff)
        diff = no_mit - with_mit
        rows.append({
            "السنة": year, "بدون تخفيف": round(no_mit, 1),
            "مع تخفيف": round(with_mit, 1),
            "الفرق": round(diff, 1),
            "التخفيض %": round(diff / no_mit * 100, 1) if no_mit > 0 else 0})
    return pd.DataFrame(rows)

def calculate_dynamic_risk(base, years, mining, climate, pop,
                            cri0=0, mri0=0):
    """التقييم الديناميكي الشامل"""
    drastic_proj = project_drastic_change(base, years, mining, climate, pop)
    combined = []
    for i, proj in enumerate(drastic_proj["projections"]):
        year = proj["السنة"]
        cri = cri0 * (1 + mining * year * 2)
        mri = mri0 * (1 + mining * year * 1.5)
        mod = calculate_modified_drastic(proj["المؤشر"], cri, mri,
                                          min(1.0, 0.1 * year))
        combined.append({
            "السنة": year, "DRASTIC": proj["المؤشر"],
            "CRI": round(cri, 2), "MRI": round(mri, 2),
            "DRASTIC-Modified": mod["modified_drastic"],
            "المستوى": mod["level"], "اللون": mod["color"]})
    return {"drastic_projection": drastic_proj,
            "combined": pd.DataFrame(combined),
            "final_modified": combined[-1]["DRASTIC-Modified"],
            "final_level": combined[-1]["المستوى"]}

def generate_dynamic_report(dyn, years):
    L = ["=" * 60, "تقرير التقييم الديناميكي", "=" * 60, "",
         f"فترة التوقع: {years} سنوات", "", "=" * 60,
         "تطور المؤشر مع الزمن", "=" * 60]
    for _, r in dyn["combined"].iterrows():
        L.append(f"سنة {int(r['السنة']):<3} | DRASTIC: {r['DRASTIC']:<6} | "
                 f"CRI: {r['CRI']:<5} | MRI: {r['MRI']:<5} | "
                 f"معدل: {r['DRASTIC-Modified']:<6} | {r['المستوى']}")
    L.append("")
    L.append(f"المؤشر النهائي: {dyn['final_modified']}")
    L.append(f"المستوى النهائي: {dyn['final_level']}")
    return "\n".join(L)


# ============================================================
# ============ Toxicity ============
# ============================================================
def analyze_mercury(w, s):
    wl, sl = 0.006, 1.0
    wr, sr = w / wl, s / sl
    mr = max(wr, sr)
    lvl = "منخفض" if mr <= 1 else "متوسط" if mr <= 3 else "مرتفع" if mr <= 10 else "مرتفع جدا"
    return {"water": {"value": w, "limit": wl, "ratio": round(wr, 2),
                      "status": "safe" if w <= wl else "exceeded"},
            "soil": {"value": s, "limit": sl, "ratio": round(sr, 2),
                     "status": "safe" if s <= sl else "exceeded"},
            "toxicity_level": lvl, "max_ratio": round(mr, 2)}

def analyze_cyanide(w, s):
    wl, sl = 0.07, 10.0
    wr, sr = w / wl, s / sl
    mr = max(wr, sr)
    lvl = "منخفض" if mr <= 1 else "متوسط" if mr <= 3 else "مرتفع" if mr <= 10 else "مرتفع جدا"
    return {"water": {"value": w, "limit": wl, "ratio": round(wr, 2),
                      "status": "safe" if w <= wl else "exceeded"},
            "soil": {"value": s, "limit": sl, "ratio": round(sr, 2),
                     "status": "safe" if s <= sl else "exceeded"},
            "toxicity_level": lvl, "max_ratio": round(mr, 2)}

def weighted_toxicity(hgw, hgs, cnw, cns):
    w = (hgw / 0.006 * 0.40) + (hgs / 1.0 * 0.20) + \
        (cnw / 0.07 * 0.30) + (cns / 10.0 * 0.10)
    if w <= 1.0: cat, act = "آمن", "لا يتطلب تدخل"
    elif w <= 3.0: cat, act = "تحت المراقبة", "مراقبة دورية"
    elif w <= 10.0: cat, act = "خطر", "تدخل عاجل"
    else: cat, act = "خطر داهم", "إيقاف النشاط"
    return {"index": round(w, 2), "category": cat, "action": act}


# ============================================================
# ============ Satellite ============
# ============================================================
def get_rainfall(lat, lon, years=3):
    try:
        end = datetime.datetime.now().strftime('%Y-%m-%d')
        start = (datetime.datetime.now() - timedelta(days=365*years)).strftime('%Y-%m-%d')
        r = requests.get("https://archive-api.open-meteo.com/v1/archive",
            params={"latitude": lat, "longitude": lon,
                    "start_date": start, "end_date": end,
                    "daily": "precipitation_sum",
                    "timezone": "Africa/Khartoum"}, timeout=30)
        d = r.json().get("daily", {}).get("precipitation_sum", [])
        v = [x for x in d if x is not None]
        return round(sum(v) / years, 1) if v else None
    except Exception:
        return None

def get_temperature(lat, lon, years=3):
    try:
        end = datetime.datetime.now().strftime('%Y-%m-%d')
        start = (datetime.datetime.now() - timedelta(days=365*years)).strftime('%Y-%m-%d')
        r = requests.get("https://archive-api.open-meteo.com/v1/archive",
            params={"latitude": lat, "longitude": lon,
                    "start_date": start, "end_date": end,
                    "daily": "temperature_2m_mean",
                    "timezone": "Africa/Khartoum"}, timeout=30)
        d = r.json().get("daily", {}).get("temperature_2m_mean", [])
        v = [x for x in d if x is not None]
        return round(sum(v) / len(v), 1) if v else None
    except Exception:
        return None

def classify_aridity(r):
    if r is None: return "غير محدد"
    if r < 100: return "صحراوي"
    if r < 250: return "شبه جاف"
    if r < 500: return "شبه رطب"
    return "رطب"

def estimate_recharge(r, soil="sand"):
    if r is None: return None
    ratios = {"sand": 0.20, "sandy_loam": 0.15, "loam": 0.12,
              "silty_loam": 0.10, "clay_loam": 0.07, "nonshrinking_clay": 0.04}
    return round(r * ratios.get(soil, 0.12), 1)

def fetch_satellite(lat, lon, years=3):
    rain = get_rainfall(lat, lon, years)
    temp = get_temperature(lat, lon, years)
    return {"rainfall_mm": rain, "temperature_c": temp,
            "aridity": classify_aridity(rain),
            "ndvi_estimated": round(min(0.7, max(0.05, (rain or 0) / 1000.0)), 3) if rain else None,
            "source": "ERA5 via Open-Meteo"}


# ============================================================
# ============ Validation ============
# ============================================================
VALID_AQUIFERS = ["massive_shale", "metamorphic_igneous",
    "weathered_metamorphic_igneous", "thin_bedded_sequences",
    "massive_sandstone", "massive_limestone", "sand_and_gravel",
    "basalt", "karst_limestone"]
VALID_SOILS = ["thin_or_absent", "gravel", "sand", "peat",
    "shrinking_aggregated_clay", "sandy_loam", "loam", "silty_loam",
    "clay_loam", "muck", "nonshrinking_clay"]
VALID_VADOSE = ["confining_layer", "silt_clay", "shale",
    "metamorphic_igneous", "limestone", "sandstone",
    "sand_gravel_silt_clay", "sand_gravel", "basalt", "karst_limestone"]
REQUIRED_COLS = ["depth_m", "recharge_mm", "slope_pct",
                 "conductivity", "aquifer", "soil", "vadose"]


def validate_single_input(d, r, t, c, a, s, i, g=0.01):
    errors, warnings = [], []
    if not (0.5 <= d <= 100): errors.append("D خارج النطاق (0.5-100)")
    if not (0 <= r <= 400): errors.append("R خارج النطاق (0-400)")
    if not (0 <= t <= 30): errors.append("T خارج النطاق (0-30)")
    if not (0.01 <= c <= 100): errors.append("C خارج النطاق (0.01-100)")
    if not (0.0001 <= g <= 0.5): errors.append("i خارج النطاق")
    if a not in VALID_AQUIFERS: warnings.append("A غير معروف")
    if s not in VALID_SOILS: warnings.append("S غير معروف")
    if i not in VALID_VADOSE: warnings.append("I غير معروف")
    return errors, warnings


def validate_bulk_row(row, idx):
    errors, warnings = [], []
    try:
        d = float(row.get("depth_m", 15))
        if not (0.5 <= d <= 100): errors.append("D خارج النطاق")
    except Exception: errors.append("D غير رقمي")
    try:
        r = float(row.get("recharge_mm", 100))
        if not (0 <= r <= 400): errors.append("R خارج النطاق")
    except Exception: errors.append("R غير رقمي")
    try:
        t = float(row.get("slope_pct", 4))
        if not (0 <= t <= 30): errors.append("T خارج النطاق")
    except Exception: errors.append("T غير رقمي")
    try:
        c = float(row.get("conductivity", 5))
        if not (0.01 <= c <= 100): errors.append("C خارج النطاق")
    except Exception: errors.append("C غير رقمي")
    if str(row.get("aquifer", "massive_sandstone")) not in VALID_AQUIFERS:
        warnings.append("A غير معروف")
    if str(row.get("soil", "sand")) not in VALID_SOILS:
        warnings.append("S غير معروف")
    if str(row.get("vadose", "sand_gravel")) not in VALID_VADOSE:
        warnings.append("I غير معروف")
    quality = "ضعيف" if errors else "متوسط" if warnings else "ممتاز"
    return errors, warnings, quality


# ============================================================
# ============ History ============
# ============================================================
def save_to_history(site, coords, idx, level, values, travel, sat, tox):
    if "history" not in st.session_state:
        st.session_state["history"] = []
    st.session_state["history"].append({
        "التاريخ": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "الموقع": str(site),
        "lat": coords[0] if coords else 0,
        "lon": coords[1] if coords else 0,
        "المؤشر": idx, "المستوى": level,
        "العمق": values.get("depth", ""),
        "التغذية": values.get("recharge", ""),
        "زمن الوصول": travel.get("years", 0) if isinstance(travel, dict) else (travel or 0),
        "الأمطار": sat.get("rainfall_mm", 0) if sat else 0,
        "مؤشر السمية": tox.get("index", 0) if tox else 0})

def get_history_df():
    if "history" not in st.session_state or not st.session_state["history"]:
        return pd.DataFrame()
    return pd.DataFrame(st.session_state["history"])


# ============================================================
# ============ Report ============
# ============================================================
TEMPLATES = {
    "low": {"level": "منخفض", "range": "23-99",
        "assessment": "خطورة منخفضة. حماية جيدة.",
        "recs": ["المراقبة السنوية.", "فحص سنوي للمياه.",
                 "توثيق التغييرات.", "التزام PPE.", "الإبلاغ عن الحوادث."]},
    "moderate": {"level": "متوسط", "range": "100-139",
        "assessment": "خطورة متوسطة.",
        "recs": ["مراقبة ربع سنوية.", "2-3 آبار مراقبة.",
                 "تحسين إدارة المخلفات.", "معالجة السيانيد.",
                 "خطة طوارئ.", "تدريب العمال."]},
    "high": {"level": "مرتفع", "range": "140-179",
        "assessment": "خطورة مرتفعة. تدخل عاجل.",
        "recs": ["HDPE Liner.", "معالجة السيانيد.", "4-6 آبار مراقبة.",
                 "مراقبة شهرية.", "EIA.", "تقليل السيانيد.", "إبلاغ المجلس."]},
    "very_high": {"level": "مرتفع جدا", "range": "180-230",
        "assessment": "خطورة مرتفعة جدا. خطر داهم.",
        "recs": ["إيقاف النشاط.", "HDPE + معالجة.", "8-10 آبار.",
                 "مراقبة أسبوعية.", "إخلاء إذا لزم.", "تقرير طارئ.",
                 "مياه بديلة.", "إعادة تأهيل."]},
}

def get_tpl_key(idx):
    if idx >= 180: return "very_high"
    if idx >= 140: return "high"
    if idx >= 100: return "moderate"
    return "low"

def gen_report(site, coords, idx, values, travel=None, sat=None, tox=None):
    key = get_tpl_key(idx)
    tpl = TEMPLATES[key]
    today = datetime.date.today()
    ref = "GRAS-" + today.strftime("%Y%m%d") + "-" + key.upper()[:3]
    L = ["=" * 60, "تقرير تقييم هشاشة المياه الجوفية",
         "نظام التعدين السوداني - جامعة الخرطوم", "=" * 60, "",
         f"الرقم المرجعي: {ref}",
         f"التاريخ: {today.strftime('%Y-%m-%d')}",
         f"الموقع: {site}",
         f"الإحداثيات: {coords[0]}, {coords[1]}", "",
         f"مؤشر DRASTIC: {idx} / 230",
         f"المستوى: {tpl['level']} ({tpl['range']})", "",
         f"D: {values.get('depth', 'N/A')}",
         f"R: {values.get('recharge', 'N/A')}",
         f"A: {values.get('aquifer', 'N/A')}",
         f"S: {values.get('soil', 'N/A')}",
         f"T: {values.get('slope', 'N/A')}",
         f"I: {values.get('vadose', 'N/A')}",
         f"C: {values.get('conductivity', 'N/A')}", ""]
    if travel:
        if isinstance(travel, dict):
            L.append(f"زمن الوصول: {travel.get('years', 0)} سنة "
                     f"({travel.get('days', 0)} يوم)")
            L.append(f"سرعة دارسي: {travel.get('velocity', 0)} م/يوم")
        else:
            L.append(f"زمن الوصول: {travel} سنة")
        L.append("")
    if sat and sat.get("rainfall_mm"):
        L.append("بيانات الاقمار الصناعية:")
        L.append(f"  الامطار: {sat.get('rainfall_mm')} مم")
        L.append(f"  الحرارة: {sat.get('temperature_c')}")
        L.append(f"  المناخ: {sat.get('aridity')}")
        L.append("")
    if tox:
        L.append("تحليل السمية:")
        L.append(f"  المؤشر: {tox.get('index')}")
        L.append(f"  التصنيف: {tox.get('category')}")
        L.append("")
    L.append("التقييم: " + tpl["assessment"])
    L.append("")
    L.append("التوصيات:")
    for i, rec in enumerate(tpl["recs"], 1):
        L.append(f"{i}. {rec}")
    L += ["", "الامتثال: قانون التعدين 2015 - قانون البيئة 2001",
          "المراجع: EPA/600/2-87/035, Fetter 2001, WHO 2022", "",
          "توقيع المهندس: _______________________", "=" * 60]
    return "\n".join(L)

def gen_html(rep, site):
    return ("<!DOCTYPE html><html dir='rtl' lang='ar'><head>"
         "<meta charset='UTF-8'><title>" + site + "</title>"
         "<style>body{font-family:Arial;direction:rtl;text-align:right;"
         "padding:30px;max-width:900px;margin:auto;line-height:1.9;}"
         "pre{white-space:pre-wrap;background:#f8f9fa;padding:25px;"
         "border-radius:8px;font-family:inherit;}"
         "@media print{body{background:#fff;padding:0;}"
         "pre{background:#fff;padding:0;border:none;}}"
         "</style></head><body><pre>" + rep + "</pre>"
         "<div style='text-align:center;margin-top:30px;color:#666;"
         "font-size:12px;'>لحفظ PDF: Ctrl+P → Save as PDF</div>"
         "</body></html>")


# ============================================================
# ============ GIS Export ============
# ============================================================
def sites_to_geojson(sites):
    features = []
    for s in sites:
        try:
            features.append({"type": "Feature",
                "geometry": {"type": "Point",
                    "coordinates": [float(s.get("lon", 0)), float(s.get("lat", 0))]},
                "properties": {"name": str(s.get("name", "")),
                    "drastic_index": int(s.get("index", 0)),
                    "risk_level": str(s.get("level", ""))}})
        except Exception:
            continue
    return json.dumps({"type": "FeatureCollection", "features": features},
                      ensure_ascii=False, indent=2)

def sites_to_kml(sites):
    kml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    kml += '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>\n'
    kml += '<name>Sudan Mining System</name>\n'
    for s in sites:
        try:
            kml += f'  <Placemark><name>{s.get("name", "")}</name>\n'
            kml += f'    <description>DRASTIC: {s.get("index", 0)} | {s.get("level", "")}</description>\n'
            kml += f'    <Point><coordinates>{s.get("lon", 0)},{s.get("lat", 0)},0</coordinates></Point>\n'
            kml += '  </Placemark>\n'
        except Exception:
            continue
    kml += '</Document></kml>'
    return kml

def get_preset_sites_with_drastic(preset):
    sites = []
    for name, data in preset.items():
        try:
            coords = data.get("coords", (0, 0))
            D_phys = float(data.get("depth", 15.0))
            R_phys = float(data.get("recharge", 100.0))
            A_phys = str(data.get("aquifer", "massive_sandstone"))
            S_phys = str(data.get("soil", "sand"))
            T_phys = float(data.get("slope", 4.0))
            I_phys = str(data.get("vadose", "sand_gravel"))
            C_phys = float(data.get("conductivity", 5.0))
            ix = calc_index(get_d_rating(D_phys), get_r_rating(R_phys),
                           get_a_rating(A_phys), get_s_rating(S_phys),
                           get_t_rating(T_phys), get_i_rating(I_phys),
                           get_c_rating(C_phys))
            rk = classify(ix)
            sites.append({"name": str(name), "lat": float(coords[0]),
                "lon": float(coords[1]), "index": ix, "level": rk["level"],
                "color": rk["color"], "source": data.get("source", "غير محدد")})
        except Exception:
            continue
    return sites


# ============================================================
# ============ UI HEADER ============
# ============================================================
_col1, _col2, _col3 = st.columns([1, 2, 1])
with _col2:
    if PIL_OK:
        try:
            st.image("logo.png", use_container_width=True)
        except Exception:
            st.markdown("<h1 style='text-align:center;'>⛏️</h1>",
                        unsafe_allow_html=True)

st.markdown("""
<div class="header-container">
    <div class="header-title">⛏️ نظام التعدين السوداني v37.0</div>
    <div class="header-subtitle">جامعة الخرطوم - كلية الهندسة</div>
    <div class="header-subtitle">نظام تقييم هشاشة المياه الجوفية المتكامل</div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# ============ SIDEBAR MODE SELECTOR ============
# ============================================================
st.sidebar.markdown("## 🎛️ وضع التشغيل")
st.sidebar.markdown("---")

mode = st.sidebar.radio(
    "اختر الوضع:",
    ["🏠 النظام الأساسي",
     "✅ التحقق الفعلي (Validation)",
     "🧪 DRASTIC-P (المؤشر المعدل)",
     "⏳ التقييم الديناميكي"],
    key="app_mode"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 معلومات")
st.sidebar.info(
    "**النظام الأساسي**: DRASTIC + Monte Carlo + الحساسية + السمية + GIS\n\n"
    "**التحقق الفعلي**: قياس دقة النموذج\n\n"
    "**DRASTIC-P**: دمج مخاطر التعدين (CN, Hg, AMD)\n\n"
    "**الديناميكي**: توقع 10-50 سنة"
)

st.sidebar.markdown("---")
if "ci" in st.session_state:
    st.sidebar.success(f"✅ مؤشر حالي: {st.session_state['ci']}")
else:
    st.sidebar.warning("⚠️ لم يتم حساب مؤشر بعد")


# ============================================================
# ============ PRESET LOADING ============
# ============================================================
if DS_OK:
    preset = get_preset_locations_for_app()
    summary = get_data_summary()
else:
    preset = {"موقع تجريبي": {"coords": (19.53, 33.32), "depth": 15.0,
              "conductivity": 5.0, "recharge": 100.0,
              "aquifer": "massive_sandstone", "soil": "sand",
              "slope": 4.0, "vadose": "sand_gravel", "source": "افتراضي"}}
    summary = {"Total": 1}


# ============================================================
# ============================================================
# ============ MODE 1: النظام الأساسي ============
# ============================================================
# ============================================================
if mode == "🏠 النظام الأساسي":
    tabs = st.tabs(["📍 المدخلات", "📊 الجماعي", "🛡️ الحلول", "📄 التقرير",
                    "🗺️ الخريطة", "📈 الحساسية", "⚖️ مقارنة",
                    "☠️ السمية", "📚 التاريخ", "🌍 GIS", "🎲 Monte Carlo"])

    # ============ TAB 0: المدخلات ============
    with tabs[0]:
        st.header("اختيار الموقع والمدخلات")
        site = st.selectbox("الموقع:", list(preset.keys()))
        sd = preset[site]
        st.caption("المصدر: " + sd.get("source", "غير محدد"))

        st.markdown("---")
        st.subheader("بيانات الاقمار الصناعية")
        if st.button("جلب البيانات", key="fetch_sat"):
            with st.spinner("جاري الجلب..."):
                st.session_state["sat_data"] = fetch_satellite(
                    sd["coords"][0], sd["coords"][1])
        if "sat_data" in st.session_state:
            s = st.session_state["sat_data"]
            if s.get("rainfall_mm"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("الأمطار", s["rainfall_mm"])
                c2.metric("الحرارة", s["temperature_c"])
                c3.metric("NDVI", s["ndvi_estimated"])
                c4.metric("المناخ", s["aridity"])
                st.caption("المصدر: " + s["source"])
                st.info(f"التغذية المقدرة: {estimate_recharge(s['rainfall_mm'])} مم/سنة")

        st.markdown("---")
        st.subheader("المدخلات الفيزيائية")
        c1, c2 = st.columns(2)
        with c1:
            depth = st.slider("D - عمق المياه (م):", 0.5, 100.0,
                              float(sd.get("depth", 15.0)), 0.5)
            recharge = st.slider("R - التغذية (مم/سنة):", 0.0, 400.0,
                                 float(sd.get("recharge", 150.0)), 10.0)
            slope = st.slider("T - الميل (%):", 0.0, 30.0,
                              float(sd.get("slope", 4.0)), 0.5)
            conductivity = st.slider("C - التوصيلية (م/يوم):", 0.01, 100.0,
                                      float(sd.get("conductivity", 5.0)), 0.1)
        with c2:
            aquifer = st.selectbox("A - الوسط المائي:", VALID_AQUIFERS,
                index=VALID_AQUIFERS.index(sd.get("aquifer", "massive_sandstone"))
                      if sd.get("aquifer") in VALID_AQUIFERS else 0)
            soil = st.selectbox("S - التربة:", VALID_SOILS,
                index=VALID_SOILS.index(sd.get("soil", "sand"))
                      if sd.get("soil") in VALID_SOILS else 0)
            vadose = st.selectbox("I - نطاق التهوية:", VALID_VADOSE,
                index=VALID_VADOSE.index(sd.get("vadose", "sand_gravel"))
                      if sd.get("vadose") in VALID_VADOSE else 0)
            porosity = st.slider("θ - المسامية:", 0.02, 0.55, 0.25, 0.01)

        st.markdown("---")
        st.subheader("معاملات إضافية")
        gradient = st.slider("i - التدرج الهيدروليكي:", 0.0001, 0.5, 0.01,
                              0.0001, format="%.4f",
                              help="التدرج = فرق المناسيب / المسافة (0.001-0.05)")

        errors, warnings = validate_single_input(
            depth, recharge, slope, conductivity, aquifer, soil, vadose, gradient)
        for e in errors: st.error("❌ " + e)
        for w in warnings: st.warning("⚠️ " + w)

        try:
            D_r = get_d_rating(depth); R_r = get_r_rating(recharge)
            A_r = get_a_rating(aquifer); S_r = get_s_rating(soil)
            T_r = get_t_rating(slope); I_r = get_i_rating(vadose)
            C_r = get_c_rating(conductivity)
            idx = calc_index(D_r, R_r, A_r, S_r, T_r, I_r, C_r)
            risk = classify(idx)
            travel = calc_travel(depth, porosity, conductivity, gradient)

            st.session_state["ci"] = idx
            st.session_state["cs"] = site
            st.session_state["cc"] = sd["coords"]
            st.session_state["cv"] = {
                "depth": depth, "recharge": recharge, "aquifer": aquifer,
                "soil": soil, "slope": slope, "vadose": vadose,
                "conductivity": conductivity, "porosity": porosity,
                "gradient": gradient}
            st.session_state["ct"] = travel

            st.markdown("---")
            st.header("النتائج: " + site)
            x1, x2, x3, x4 = st.columns(4)
            x1.metric("D", D_r, f"{depth} م")
            x2.metric("R", R_r, f"{recharge} مم")
            x3.metric("A", A_r); x4.metric("S", S_r)
            y1, y2, y3, y4 = st.columns(4)
            y1.metric("T", T_r); y2.metric("I", I_r)
            y3.metric("C", C_r); y4.metric("θ", round(porosity, 2))
            st.markdown("---")
            z1, z2 = st.columns(2)
            z1.metric("مؤشر DRASTIC", f"{idx} / 230")
            z2.metric("المستوى", risk["level"])
            if risk["color"] == "red": st.error(risk["action"])
            elif risk["color"] == "orange": st.warning(risk["action"])
            elif risk["color"] == "yellow": st.info(risk["action"])
            else: st.success(risk["action"])

            st.markdown("---")
            st.subheader("زمن وصول الملوثات (Darcy)")
            w1, w2, w3, w4 = st.columns(4)
            w1.metric("سنوات", travel["years"])
            w2.metric("أيام", travel["days"])
            w3.metric("السرعة (م/يوم)", travel["velocity"])
            w4.metric("i", travel["gradient"])
            with st.expander("ℹ️ طريقة الحساب (Darcy velocity)"):
                st.markdown(f"""
                **v = K × i / n**
                - K = {conductivity} م/يوم
                - i = {gradient}
                - n = {porosity}
                - v = {travel['velocity']} م/يوم
                - زمن الوصول = {depth} / {travel['velocity']} = {travel['days']} يوم
                """)

            if st.button("💾 حفظ في التاريخ", key="save_hist"):
                save_to_history(site, sd["coords"], idx, risk["level"],
                                st.session_state["cv"], travel,
                                st.session_state.get("sat_data"),
                                st.session_state.get("tox_result"))
                st.success("✅ تم الحفظ")
        except ValueError as e:
            st.error("خطأ: " + str(e))

    # ============ TAB 1: الجماعي ============
    with tabs[1]:
        st.header("📊 التقييم الجماعي")
        sample = pd.DataFrame({
            "name": ["A", "B"], "lat": [19.53, 18.12],
            "lon": [33.32, 33.99], "depth_m": [15.0, 10.0],
            "recharge_mm": [80.0, 120.0], "slope_pct": [4.0, 8.0],
            "conductivity": [5.0, 10.0],
            "aquifer": ["massive_sandstone", "sand_and_gravel"],
            "soil": ["sand", "sandy_loam"],
            "vadose": ["sand_gravel", "sandstone"]})
        st.download_button("📥 نموذج CSV",
            data=sample.to_csv(index=False).encode("utf-8-sig"),
            file_name="template.csv", mime="text/csv")

        f = st.file_uploader("📤 ارفع ملف:", type=["csv", "xlsx"],
                              key="bulk_v37")
        if f:
            try:
                df = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)
                st.markdown("---")
                st.subheader("🔍 فحص الجودة")
                c1, c2, c3 = st.columns(3)
                c1.metric("الصفوف", len(df))
                c2.metric("الأعمدة", len(df.columns))
                missing = [c for c in REQUIRED_COLS if c not in df.columns]
                c3.metric("مفقودة", len(missing))
                if missing:
                    st.warning("⚠️ مفقود: " + ", ".join(missing))
                else:
                    st.success("✅ كل الأعمدة موجودة")

                results = []
                qualities = {"ممتاز": 0, "متوسط": 0, "ضعيف": 0}
                for i, row in df.iterrows():
                    errs, warns, q = validate_bulk_row(row, i)
                    qualities[q] += 1
                    try:
                        D = get_d_rating(float(row.get("depth_m", 15)))
                        R = get_r_rating(float(row.get("recharge_mm", 100)))
                        A = get_a_rating(str(row.get("aquifer", "massive_sandstone")))
                        S = get_s_rating(str(row.get("soil", "sand")))
                        T = get_t_rating(float(row.get("slope_pct", 4)))
                        I = get_i_rating(str(row.get("vadose", "sand_gravel")))
                        C = get_c_rating(float(row.get("conductivity", 5)))
                        ix = calc_index(D, R, A, S, T, I, C)
                        rk = classify(ix)
                        notes = []
                        if errs: notes.append("أخطاء: " + " | ".join(errs))
                        if warns: notes.append("تحذيرات: " + " | ".join(warns))
                        results.append({
                            "الموقع": row.get("name", f"Site {i}"),
                            "المؤشر": ix, "المستوى": rk["level"],
                            "الجودة": q,
                            "ملاحظات": "، ".join(notes) if notes else "—"})
                    except Exception as e:
                        results.append({"الموقع": row.get("name", f"Site {i}"),
                            "المؤشر": 0, "المستوى": "فشل",
                            "الجودة": "ضعيف", "ملاحظات": f"خطأ: {e}"})

                st.markdown("---")
                st.subheader("📈 توزيع الجودة")
                q1, q2, q3 = st.columns(3)
                q1.metric("✅ ممتاز", qualities["ممتاز"])
                q2.metric("⚠️ متوسط", qualities["متوسط"])
                q3.metric("❌ ضعيف", qualities["ضعيف"])

                dfr = pd.DataFrame(results)
                if not dfr.empty:
                    valid = dfr[dfr["المؤشر"] > 0]
                    if not valid.empty:
                        k1, k2, k3, k4 = st.columns(4)
                        k1.metric("الإجمالي", len(dfr))
                        k2.metric("المتوسط", round(valid["المؤشر"].mean(), 1))
                        k3.metric("الأعلى", valid["المؤشر"].max())
                        k4.metric("خطرة", len(valid[valid["المؤشر"] >= 140]))
                st.dataframe(dfr, use_container_width=True)

                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("📥 نتائج CSV",
                        data=dfr.to_csv(index=False).encode("utf-8-sig"),
                        file_name="results.csv", mime="text/csv",
                        use_container_width=True)
                with c2:
                    rep_q = "\n".join(["تقرير جودة الملف", "=" * 40,
                        f"الصفوف: {len(df)}",
                        f"ممتاز: {qualities['ممتاز']}",
                        f"متوسط: {qualities['متوسط']}",
                        f"ضعيف: {qualities['ضعيف']}"])
                    st.download_button("📥 تقرير الجودة",
                        data=rep_q.encode("utf-8-sig"),
                        file_name="quality.txt", mime="text/plain",
                        use_container_width=True)
            except Exception as e:
                st.error("خطأ: " + str(e))

    # ============ TAB 2: الحلول ============
    with tabs[2]:
        st.header("محاكي الحلول")
        if "ci" in st.session_state:
            ci = st.session_state["ci"]
            st.info(f"الموقع: {st.session_state['cs']} | المؤشر: {ci}")
            c1, c2 = st.columns(2)
            with c1:
                h = st.checkbox("HDPE Liner", key="mit_h")
                tr = st.checkbox("Cyanide Treatment", key="mit_t")
            with c2:
                mo = st.checkbox("Monitoring Wells", key="mit_m")
            if h or tr or mo:
                r = mitigate(ci, h, tr, mo)
                a, b, c = st.columns(3)
                a.metric("قبل", ci)
                b.metric("بعد", r["mitigated_index"])
                c.metric("التخفيض", f"{r['reduction_pct']} %")
                st.progress(min(r["reduction_pct"] / 100, 1.0))
                st.metric("المستوى الجديد",
                          classify(int(r["mitigated_index"]))["level"])
        else:
            st.warning("افتح تبويب المدخلات أولا")

    # ============ TAB 3: التقرير ============
    with tabs[3]:
        st.header("توليد التقرير")
        if "ci" in st.session_state:
            if st.button("توليد", type="primary", key="gen"):
                rep = gen_report(st.session_state["cs"],
                                st.session_state["cc"],
                                st.session_state["ci"],
                                st.session_state["cv"],
                                st.session_state.get("ct"),
                                st.session_state.get("sat_data"),
                                st.session_state.get("tox_result"))
                st.session_state["rep"] = rep
                st.success("تم التوليد")
            if "rep" in st.session_state:
                st.text_area("التقرير:", st.session_state["rep"], height=400)
                safe = st.session_state["cs"].replace(" ", "_")
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("TXT",
                        data=("\ufeff" + st.session_state["rep"]).encode("utf-8"),
                        file_name=f"rep_{safe}.txt",
                        mime="text/plain; charset=utf-8",
                        use_container_width=True)
                with c2:
                    st.download_button("HTML/PDF",
                        data=gen_html(st.session_state["rep"],
                                      st.session_state["cs"]).encode("utf-8"),
                        file_name=f"rep_{safe}.html",
                        mime="text/html; charset=utf-8",
                        use_container_width=True)
        else:
            st.warning("افتح تبويب المدخلات أولا")

    # ============ TAB 4: الخريطة ============
    with tabs[4]:
        st.header("🗺️ الخريطة التفاعلية")

        if DS_OK:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                show_wells = st.checkbox("🔵 NARIS", value=True)
                show_darfur = st.checkbox("🟢 دارفور", value=True)
            with col2:
                show_mining = st.checkbox("🔴 التعدين", value=True)
                show_khartoum = st.checkbox("🟣 الخرطوم", value=True)
            with col3:
                show_buffers = st.checkbox("⭕ النطاقات", value=True)
                buffer_size = st.selectbox("الحجم:",
                    ["500 م", "1000 م", "2000 م", "الكل"], index=3)
            with col4:
                base_map = st.selectbox("الخلفية:",
                    ["عادية", "أقمار صناعية", "تضاريس"], index=0)
                map_height = st.slider("الارتفاع:", 400, 900, 700, 50)

            tiles_map = {
                "عادية": "OpenStreetMap",
                "أقمار صناعية": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                "تضاريس": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"}

            m = folium.Map(location=[15.5, 32.5], zoom_start=6,
                           tiles=tiles_map[base_map], control_scale=True)

            if show_wells:
                for n, d in NARIS_WELLS.items():
                    folium.Marker([d["coords"][1], d["coords"][0]],
                        popup=f"<b>{n}</b><br>NARIS",
                        tooltip=n,
                        icon=folium.Icon(color="blue", icon="tint", prefix="fa")
                    ).add_to(m)

            if show_darfur:
                for n, d in DARFUR_WELLS.items():
                    folium.Marker([d["coords"][1], d["coords"][0]],
                        popup=f"<b>{n}</b><br>Darfur",
                        tooltip=n,
                        icon=folium.Icon(color="green", icon="tint", prefix="fa")
                    ).add_to(m)

            if show_mining:
                for n, d in KNOWN_MINING_SITES.items():
                    lat, lon = d["coords"][1], d["coords"][0]
                    if show_buffers:
                        if buffer_size in ["500 م", "الكل"]:
                            folium.Circle([lat, lon], radius=500, color="red",
                                weight=2, fill=True, fill_opacity=0.2).add_to(m)
                        if buffer_size in ["1000 م", "الكل"]:
                            folium.Circle([lat, lon], radius=1000, color="orange",
                                weight=1.5, fill=True, fill_opacity=0.12).add_to(m)
                        if buffer_size in ["2000 م", "الكل"]:
                            folium.Circle([lat, lon], radius=2000, color="yellow",
                                weight=1, fill=True, fill_opacity=0.08).add_to(m)

                    D_p = float(d.get("depth", 15.0))
                    R_p = float(d.get("recharge", 100.0))
                    A_p = str(d.get("aquifer", "massive_sandstone"))
                    S_p = str(d.get("soil", "sand"))
                    T_p = float(d.get("slope", 4.0))
                    I_p = str(d.get("vadose", "sand_gravel"))
                    C_p = float(d.get("conductivity", 5.0))
                    ix = calc_index(get_d_rating(D_p), get_r_rating(R_p),
                                   get_a_rating(A_p), get_s_rating(S_p),
                                   get_t_rating(T_p), get_i_rating(I_p),
                                   get_c_rating(C_p))
                    rk = classify(ix)
                    color = "red" if rk["color"] == "red" else \
                            "orange" if rk["color"] == "orange" else \
                            "beige" if rk["color"] == "yellow" else "green"

                    folium.Marker([lat, lon],
                        popup=folium.Popup(
                            f"<b>{n}</b><br>"
                            f"النشاط: {d.get('activity', 'N/A')}<br>"
                            f"DRASTIC: {ix} - {rk['level']}<br>"
                            f"سيانيد: {'✅' if d.get('cyanide_use') else '❌'}<br>"
                            f"زئبق: {'✅' if d.get('mercury_use') else '❌'}",
                            max_width=250),
                        tooltip=f"{n} (DRASTIC: {ix})",
                        icon=folium.Icon(color=color,
                            icon="exclamation-triangle", prefix="fa")
                    ).add_to(m)

            if show_khartoum:
                for n, d in KHARTOUM_LOCALITIES.items():
                    folium.CircleMarker([d["coords"][1], d["coords"][0]],
                        radius=8, color="purple", weight=2, fill=True,
                        fill_opacity=0.5, popup=f"<b>{n}</b>").add_to(m)

            folium.plugins.MousePosition(position="bottomright",
                separator=" | ", prefix="الإحداثيات:",
            ).add_to(m)

            st_folium(m, width=None, height=map_height, key="map_v37")

            st.markdown("---")
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("NARIS", len(NARIS_WELLS))
            s2.metric("دارفور", len(DARFUR_WELLS))
            s3.metric("التعدين", len(KNOWN_MINING_SITES))
            s4.metric("الخرطوم", len(KHARTOUM_LOCALITIES))
        else:
            st.warning("⚠️ data_sources.py غير متوفر")

    # ============ TAB 5: الحساسية ============
    with tabs[5]:
        st.header("تحليل الحساسية")
        if "ci" in st.session_state:
            variation = st.slider("نسبة التغيير (%):", 5, 30, 10, 5) / 100.0
            result = sensitivity_analysis(st.session_state["cv"], variation)
            st.success("الأكثر تأثيراً: " + str(result["most_sensitive"]))
            st.metric("المؤشر الأساسي", result["base_index"])

            for p in result["parameters"]:
                pdd = result["parameters"][p]
                wt = {"D": 5, "R": 4, "A": 3, "S": 2, "T": 1, "I": 5, "C": 3}[p]
                with st.expander(f"{p} — وزن {wt} (تأثير: {pdd['sensitivity']}%)"):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("القيمة الأصلية", pdd["original_phys"])
                    c2.metric("القيمة المعدلة", pdd["modified_phys"])
                    c3.metric("تصنيف أصلي", pdd["original_rating"])
                    c4.metric("تصنيف جديد", pdd["new_rating"])
                    st.metric("مؤشر جديد", pdd["new_index"],
                              delta=str(pdd["change"]))

            chart = pd.DataFrame({
                "المعامل": list(result["parameters"].keys()),
                "الحساسية": [result["parameters"][p]["sensitivity"]
                            for p in result["parameters"]]}).set_index("المعامل")
            st.bar_chart(chart)
        else:
            st.warning("افتح تبويب المدخلات أولا")

    # ============ TAB 6: المقارنة ============
    with tabs[6]:
        st.header("مقارنة موقعين")
        if DS_OK:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("الأول")
                sa = st.selectbox("اختر:", list(preset.keys()), key="sa")
                sda = preset[sa]
                da = st.slider("D:", 0.5, 100.0, float(sda.get("depth", 15.0)), 0.5, key="da")
                ra = st.slider("R:", 0.0, 400.0, float(sda.get("recharge", 150.0)), 10.0, key="ra")
                ta = st.slider("T:", 0.0, 30.0, float(sda.get("slope", 4.0)), 0.5, key="ta")
                ca = st.slider("C:", 0.01, 100.0, float(sda.get("conductivity", 5.0)), 0.1, key="ca")
            with c2:
                st.subheader("الثاني")
                sb = st.selectbox("اختر:", list(preset.keys()), key="sb")
                sdb = preset[sb]
                db_ = st.slider("D:", 0.5, 100.0, float(sdb.get("depth", 15.0)), 0.5, key="db")
                rb = st.slider("R:", 0.0, 400.0, float(sdb.get("recharge", 150.0)), 10.0, key="rb")
                tb = st.slider("T:", 0.0, 30.0, float(sdb.get("slope", 4.0)), 0.5, key="tb")
                cb = st.slider("C:", 0.01, 100.0, float(sdb.get("conductivity", 5.0)), 0.1, key="cb")

            An_a = sda.get("aquifer", "massive_sandstone")
            Sn_a = sda.get("soil", "sand")
            In_a = sda.get("vadose", "sand_gravel")
            An_b = sdb.get("aquifer", "massive_sandstone")
            Sn_b = sdb.get("soil", "sand")
            In_b = sdb.get("vadose", "sand_gravel")

            idxa = calc_index(get_d_rating(da), get_r_rating(ra),
                             get_a_rating(An_a), get_s_rating(Sn_a),
                             get_t_rating(ta), get_i_rating(In_a),
                             get_c_rating(ca))
            idxb = calc_index(get_d_rating(db_), get_r_rating(rb),
                             get_a_rating(An_b), get_s_rating(Sn_b),
                             get_t_rating(tb), get_i_rating(In_b),
                             get_c_rating(cb))

            m1, m2, m3 = st.columns(3)
            m1.metric(sa, f"{idxa}/230")
            m2.metric("الفرق", str(abs(idxa - idxb)))
            m3.metric(sb, f"{idxb}/230")
            st.dataframe(pd.DataFrame({
                "المعامل": ["D", "R", "A", "S", "T", "I", "C"],
                sa: [get_d_rating(da), get_r_rating(ra), get_a_rating(An_a),
                     get_s_rating(Sn_a), get_t_rating(ta),
                     get_i_rating(In_a), get_c_rating(ca)],
                sb: [get_d_rating(db_), get_r_rating(rb), get_a_rating(An_b),
                     get_s_rating(Sn_b), get_t_rating(tb),
                     get_i_rating(In_b), get_c_rating(cb)]}),
                use_container_width=True)

    # ============ TAB 7: السمية ============
    with tabs[7]:
        st.header("تحليل الزئبق والسيانيد")
        if "ci" in st.session_state:
            ci = st.session_state["ci"]
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Hg**")
                hgw = st.number_input("Hg مياه (mg/L):", 0.0, 10.0, 0.05,
                                       0.001, key="hgw", format="%.4f")
                hgs = st.number_input("Hg تربة (mg/kg):", 0.0, 100.0, 0.5,
                                       0.1, key="hgs")
            with c2:
                st.markdown("**CN**")
                cnw = st.number_input("CN مياه (mg/L):", 0.0, 10.0, 0.10,
                                       0.01, key="cnw", format="%.4f")
                cns = st.number_input("CN تربة (mg/kg):", 0.0, 100.0, 5.0,
                                       0.5, key="cns")

            if st.button("تحليل", type="primary", key="analyze"):
                hg = analyze_mercury(hgw, hgs)
                cn = analyze_cyanide(cnw, cns)
                tox = weighted_toxicity(hgw, hgs, cnw, cns)
                st.session_state["hg_r"] = hg
                st.session_state["cn_r"] = cn
                st.session_state["tox_result"] = tox

            if "tox_result" in st.session_state:
                hg = st.session_state["hg_r"]
                cn = st.session_state["cn_r"]
                tox = st.session_state["tox_result"]

                st.markdown("---")
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Hg مياه", f"{hg['water']['value']} mg/L")
                    if hg["water"]["status"] == "safe": st.success("آمن")
                    else: st.error(f"تجاوز {hg['water']['ratio']}x")
                with c2:
                    st.metric("Hg تربة", f"{hg['soil']['value']} mg/kg")
                    if hg["soil"]["status"] == "safe": st.success("آمن")
                    else: st.error(f"تجاوز {hg['soil']['ratio']}x")

                c1, c2 = st.columns(2)
                with c1:
                    st.metric("CN مياه", f"{cn['water']['value']} mg/L")
                    if cn["water"]["status"] == "safe": st.success("آمن")
                    else: st.error(f"تجاوز {cn['water']['ratio']}x")
                with c2:
                    st.metric("CN تربة", f"{cn['soil']['value']} mg/kg")
                    if cn["soil"]["status"] == "safe": st.success("آمن")
                    else: st.error(f"تجاوز {cn['soil']['ratio']}x")

                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                c1.metric("مؤشر السمية", tox["index"])
                c2.metric("التصنيف", tox["category"])
                c3.metric("الإجراء", tox["action"])
        else:
            st.warning("افتح تبويب المدخلات أولا")

    # ============ TAB 8: التاريخ ============
    with tabs[8]:
        st.header("📚 تاريخ التقييمات")
        df = get_history_df()
        if df.empty:
            st.info("لا توجد تقييمات محفوظة بعد.")
        else:
            try:
                idx_col = df["المؤشر"].astype(float)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("الإجمالي", len(df))
                c2.metric("المتوسط", round(idx_col.mean(), 1))
                c3.metric("الأعلى", int(idx_col.max()))
                c4.metric("خطرة", int((idx_col >= 140).sum()))
            except Exception:
                st.metric("الإجمالي", len(df))
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 تصدير CSV",
                data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name="history.csv", mime="text/csv")
            if st.button("مسح الكل", key="clr"):
                st.session_state["history"] = []
                st.rerun()

    # ============ TAB 9: GIS ============
    with tabs[9]:
        st.header("🌍 تصدير GIS")
        source = st.radio("المصدر:",
                          ["المواقع المدمجة", "سجل التقييمات"],
                          key="gis_src_v37")
        sites = []
        if source == "المواقع المدمجة" and DS_OK:
            sites = get_preset_sites_with_drastic(preset)
            st.success(f"📌 {len(sites)} موقع")
        elif source == "سجل التقييمات":
            df_h = get_history_df()
            if not df_h.empty:
                for _, row in df_h.iterrows():
                    try:
                        sites.append({"name": row.get("الموقع", ""),
                            "lat": float(row.get("lat", 0)),
                            "lon": float(row.get("lon", 0)),
                            "index": int(float(row.get("المؤشر", 0))),
                            "level": row.get("المستوى", "")})
                    except Exception:
                        continue
                st.success(f"📌 {len(sites)} تقييم")

        if sites:
            preview = pd.DataFrame(sites)[["name", "lat", "lon", "index", "level"]]
            preview.columns = ["الموقع", "خط العرض", "خط الطول", "المؤشر", "المستوى"]
            st.dataframe(preview, use_container_width=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.download_button("📄 GeoJSON",
                    data=sites_to_geojson(sites).encode("utf-8"),
                    file_name="drastic_sites.geojson",
                    mime="application/geo+json", use_container_width=True)
            with c2:
                st.download_button("🌍 KML",
                    data=sites_to_kml(sites).encode("utf-8"),
                    file_name="drastic_sites.kml",
                    mime="application/vnd.google-earth.kml+xml",
                    use_container_width=True)
            with c3:
                st.download_button("📊 CSV",
                    data=preview.to_csv(index=False).encode("utf-8-sig"),
                    file_name="drastic_sites.csv", mime="text/csv",
                    use_container_width=True)

    # ============ TAB 10: Monte Carlo ============
    with tabs[10]:
        st.header("🎲 محاكاة Monte Carlo")
        if "ci" in st.session_state:
            st.info("التوزيعات: Log-Normal للتوصيلية، Normal للعمق والميل، Discrete للتصنيفات")

            c1, c2 = st.columns(2)
            with c1:
                n_iter = st.slider("عدد المحاكاات:", 100, 5000, 1000, 100)
            with c2:
                var_pct = st.slider("معامل الاختلاف (%):", 5, 30, 15, 5)

            if st.button("تشغيل المحاكاة", type="primary", key="run_mc"):
                with st.spinner("جاري المحاكاة..."):
                    st.session_state["mc_result"] = monte_carlo_analysis(
                        st.session_state["cv"], n_iter, var_pct / 100.0)

            if "mc_result" in st.session_state:
                mc = st.session_state["mc_result"]
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("المتوسط", mc["mean"])
                c2.metric("الانحراف", mc["std"])
                c3.metric("الأدنى", mc["min"])
                c4.metric("الأعلى", mc["max"])

                c1, c2 = st.columns(2)
                with c1:
                    st.metric("CI 90%", f"{mc['ci_90'][0]} - {mc['ci_90'][1]}")
                with c2:
                    st.metric("CI 50%", f"{mc['ci_50'][0]} - {mc['ci_50'][1]}")

                c1, c2 = st.columns(2)
                with c1:
                    st.metric("احتمال > 140", f"{mc['prob_over_140']} %")
                with c2:
                    st.metric("احتمال > 180", f"{mc['prob_over_180']} %")

                pct_df = pd.DataFrame({
                    "المئين": ["P5", "P25", "P50", "P75", "P95"],
                    "المؤشر": [mc["p5"], mc["p25"], mc["p50"],
                              mc["p75"], mc["p95"]]}).set_index("المئين")
                st.dataframe(pct_df)
                st.bar_chart(pct_df)

                if mc["prob_over_140"] > 50:
                    st.error("⚠️ احتمال مرتفع تجاوز 140")
                elif mc["prob_over_140"] > 20:
                    st.warning("⚠️ احتمال متوسط")
                else:
                    st.success("✅ احتمال منخفض")
        else:
            st.warning("افتح تبويب المدخلات أولا")


# ============================================================
# ============================================================
# ============ MODE 2: التحقق الفعلي ============
# ============================================================
# ============================================================
elif mode == "✅ التحقق الفعلي (Validation)":
    st.header("✅ التحقق الفعلي من النموذج")
    st.markdown("""
    **الهدف:** مقارنة توقعات النظام مع بيانات ميدانية حقيقية
    لقياس دقة النموذج إحصائياً (Accuracy, Kappa, MCC).
    """)

    st.markdown("---")
    sample_val = pd.DataFrame({
        "site_name": ["موقع 1", "موقع 2", "موقع 3", "موقع 4"],
        "drastic_index": [150, 80, 130, 165],
        "actual_contaminated": [1, 0, 0, 1]})
    st.download_button("📥 قالب التحقق",
        data=sample_val.to_csv(index=False).encode("utf-8-sig"),
        file_name="validation_template.csv", mime="text/csv")

    f_val = st.file_uploader("ارفع بيانات التحقق (CSV/Excel):",
                              type=["csv", "xlsx"], key="val_upload")
    if f_val:
        try:
            df_val = pd.read_csv(f_val) if f_val.name.endswith(".csv") \
                     else pd.read_excel(f_val)
            st.markdown("---")
            st.subheader("🔍 معاينة")
            st.dataframe(df_val.head(10), use_container_width=True)

            required = ["drastic_index", "actual_contaminated"]
            missing = [c for c in required if c not in df_val.columns]
            if missing:
                st.error(f"❌ أعمدة مفقودة: {missing}")
            else:
                threshold = st.slider("عتبة التصنيف:", 100, 200, 140, 5)
                metrics = calculate_confusion_matrix(
                    df_val["drastic_index"].values,
                    df_val["actual_contaminated"].values,
                    threshold=threshold)

                st.markdown("---")
                st.subheader("📊 المقاييس الإحصائية")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Accuracy", f"{metrics['accuracy']}%")
                c2.metric("Precision", f"{metrics['precision']}%")
                c3.metric("Recall", f"{metrics['recall']}%")
                c4.metric("F1-Score", f"{metrics['f1_score']}%")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Specificity", f"{metrics['specificity']}%")
                c2.metric("NPV", f"{metrics['npv']}%")
                c3.metric("Kappa", metrics["kappa"])
                c4.metric("MCC", metrics["mcc"])

                k = metrics["kappa"]
                if k >= 0.8: st.success(f"✅ Kappa = {k} — ممتاز")
                elif k >= 0.6: st.info(f"ℹ️ Kappa = {k} — جيد")
                elif k >= 0.4: st.warning(f"⚠️ Kappa = {k} — متوسط")
                else: st.error(f"❌ Kappa = {k} — ضعيف")

                st.markdown("---")
                st.subheader("🔢 مصفوفة الالتباس")
                cm = metrics["confusion_matrix"]
                cm_df = pd.DataFrame({
                    "ملوث فعلاً": [cm["TP"], cm["FN"]],
                    "نظيف فعلاً": [cm["FP"], cm["TN"]]},
                    index=["توقع ملوث", "توقع نظيف"])
                st.dataframe(cm_df, use_container_width=True)

                if len(df_val) >= 4:
                    st.markdown("---")
                    st.subheader("📈 الدقة حسب المستوى")
                    level_df = analyze_validation_by_level(
                        df_val["drastic_index"].values,
                        df_val["actual_contaminated"].values)
                    st.dataframe(level_df, use_container_width=True)

                rep_val = generate_validation_report(metrics)
                with st.expander("📄 التقرير الكامل"):
                    st.text(rep_val)

                st.download_button("📥 تحميل التقرير",
                    data=rep_val.encode("utf-8-sig"),
                    file_name="validation_report.txt", mime="text/plain")
        except Exception as e:
            st.error(f"خطأ: {e}")


# ============================================================
# ============================================================
# ============ MODE 3: DRASTIC-P ============
# ============================================================
# ============================================================
elif mode == "🧪 DRASTIC-P (المؤشر المعدل)":
    st.header("🧪 DRASTIC-P — المؤشر المعدل للتعدين")
    st.markdown("""
    **DRASTIC-P** يدمج DRASTIC مع مؤشرات مخاطر التعدين:
    - **CRI**: مؤشر مخاطر السيانيد
    - **MRI**: مؤشر مخاطر الزئبق
    - **AMD**: الصرف الحمضي للمناجم

    **المعادلة:** DRASTIC-P = DRASTIC × (1 + α×CRI + β×MRI + γ×AMD)
    """)

    if "ci" not in st.session_state:
        st.warning("⚠️ اذهب إلى **🏠 النظام الأساسي** واحسب المؤشر أولاً.")
    else:
        st.info(f"الموقع: {st.session_state['cs']} | "
                f"DRASTIC: {st.session_state['ci']}")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**السيانيد (CN)**")
            cn_w = st.number_input("CN مياه (mg/L):", 0.0, 10.0, 0.05,
                                    0.001, key="p_cnw", format="%.4f")
            cn_s = st.number_input("CN تربة (mg/kg):", 0.0, 100.0, 5.0,
                                    0.5, key="p_cns")
            cn_dist = st.number_input("المسافة لمصدر مياه (m):", 10.0,
                                       5000.0, 500.0, 50.0, key="p_cnd")
            cn_seep = st.slider("معدل التسرب:", 0.0, 1.0, 0.3, 0.05,
                                 key="p_cnseep")
        with c2:
            st.markdown("**الزئبق (Hg)**")
            hg_w = st.number_input("Hg مياه (mg/L):", 0.0, 10.0, 0.005,
                                    0.001, key="p_hgw", format="%.4f")
            hg_s = st.number_input("Hg تربة (mg/kg):", 0.0, 100.0, 0.5,
                                    0.1, key="p_hgs")
            bio = st.slider("التراكم الحيوي:", 1.0, 3.0, 1.5, 0.1,
                             key="p_bio")
            use = st.selectbox("استخدام المياه:",
                ["drinking", "irrigation", "industrial"], key="p_wuse")

        amd = st.slider("مخاطر AMD:", 0.0, 1.0, 0.2, 0.05, key="p_amd")

        if st.button("🧪 حساب DRASTIC-P", type="primary", key="calc_p"):
            cri = calculate_cyanide_risk_index(cn_w, cn_s, cn_dist, cn_seep)
            mri = calculate_mercury_risk_index(hg_w, hg_s, bio, use)
            mod = calculate_modified_drastic(st.session_state["ci"],
                                              cri["cri"], mri["mri"], amd)
            st.session_state["cri_result"] = cri
            st.session_state["mri_result"] = mri
            st.session_state["mod_result"] = mod

        if "mod_result" in st.session_state:
            mod = st.session_state["mod_result"]
            cri = st.session_state["cri_result"]
            mri = st.session_state["mri_result"]

            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("DRASTIC الأساسي", mod["base_drastic"])
            c2.metric("DRASTIC-P", mod["modified_drastic"],
                      delta=f"+{mod['increase_pct']}%")
            c3.metric("المستوى", mod["level"])

            if mod["color"] == "red": st.error("🔴 خطر داهم — تدخل فوري")
            elif mod["color"] == "orange": st.warning("🟠 خطر مرتفع — تدخل عاجل")
            elif mod["color"] == "yellow": st.info("🟡 خطر متوسط — مراقبة")
            else: st.success("🟢 خطر منخفض")

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**CRI**")
                st.metric("القيمة", cri["cri"])
                st.metric("المياه", f"{cri['water_ratio']}x")
                st.metric("التربة", f"{cri['soil_ratio']}x")
                st.metric("المستوى", cri["level"])
            with c2:
                st.markdown("**MRI**")
                st.metric("القيمة", mri["mri"])
                st.metric("المياه", f"{mri['water_ratio']}x")
                st.metric("التربة", f"{mri['soil_ratio']}x")
                st.metric("المستوى", mri["level"])


# ============================================================
# ============================================================
# ============ MODE 4: التقييم الديناميكي ============
# ============================================================
# ============================================================
elif mode == "⏳ التقييم الديناميكي":
    st.header("⏳ التقييم الديناميكي")
    st.markdown("""
    **الهدف:** توقع تطور مؤشر DRASTIC والمخاطر الخاصة مع الزمن
    بناءً على سيناريوهات التوسع والتغير المناخي والنمو السكاني.
    """)

    if "ci" not in st.session_state:
        st.warning("⚠️ اذهب إلى **🏠 النظام الأساسي** واحسب المؤشر أولاً.")
    else:
        st.info(f"الموقع: {st.session_state['cs']} | "
                f"DRASTIC: {st.session_state['ci']}")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            years = st.slider("فترة التوقع (سنوات):", 1, 50, 10, 1,
                               key="dyn_years")
            mining_rate = st.slider("معدل توسع التعدين:", 0.0, 0.20, 0.05,
                                     0.01, key="dyn_mining")
        with c2:
            climate = st.slider("تأثير المناخ:", -0.10, 0.05, -0.02, 0.005,
                                 key="dyn_climate")
            pop = st.slider("النمو السكاني:", 0.0, 0.10, 0.03, 0.01,
                             key="dyn_pop")

        base_cri = st.slider("CRI الحالي:", 0.0, 10.0, 1.0, 0.1, key="dyn_cri")
        base_mri = st.slider("MRI الحالي:", 0.0, 10.0, 0.5, 0.1, key="dyn_mri")

        if st.button("⏳ تشغيل", type="primary", key="run_dyn"):
            with st.spinner("جاري الحساب..."):
                st.session_state["dyn_result"] = calculate_dynamic_risk(
                    st.session_state["ci"], years, mining_rate, climate,
                    pop, base_cri, base_mri)

        if "dyn_result" in st.session_state:
            res = st.session_state["dyn_result"]
            df = res["combined"]

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("DRASTIC", st.session_state["ci"])
            c2.metric(f"DRASTIC-P سنة {years}", res["final_modified"])
            c3.metric("المستوى", res["final_level"])
            inc = res["final_modified"] - st.session_state["ci"]
            c4.metric("الزيادة", f"+{inc:.1f}",
                      delta=f"{inc/st.session_state['ci']*100:.1f}%")

            st.markdown("---")
            st.subheader("📈 التطور")
            chart = df.set_index("السنة")[
                ["DRASTIC", "DRASTIC-Modified", "CRI", "MRI"]]
            st.line_chart(chart)

            st.markdown("---")
            st.subheader("📋 الجدول")
            st.dataframe(df, use_container_width=True)

            st.markdown("---")
            st.subheader("🛡️ سيناريو التخفيف")
            mit_year = st.slider("سنة بدء التخفيف:", 1, years,
                                  max(1, years//3), key="mit_year")
            mit_df = estimate_mitigation_impact(st.session_state["ci"],
                                                  years, mit_year)
            st.dataframe(mit_df, use_container_width=True)
            st.line_chart(mit_df.set_index("السنة")[["بدون تخفيف", "مع تخفيف"]])

            st.markdown("---")
            rep = generate_dynamic_report(res, years)
            with st.expander("📄 التقرير"):
                st.text(rep)

            st.download_button("📥 تحميل التقرير",
                data=rep.encode("utf-8-sig"),
                file_name="dynamic_report.txt", mime="text/plain")
            st.download_button("📥 تحميل CSV",
                data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name="dynamic.csv", mime="text/csv")


# ============ FOOTER ============
st.markdown("---")
st.caption("2026 جامعة الخرطوم - نظام التعدين السوداني v37.0 - "
           "مع الوحدات المتقدمة (Validation, DRASTIC-P, Dynamic)")
