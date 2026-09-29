"""نظام التعدين السوداني v36.0 - النسخة الكاملة مع التصحيحات الفنية"""
import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import datetime
import requests
import json
import numpy as np
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
        st.set_page_config(
            page_title="نظام التعدين السوداني",
            page_icon=_logo,
            layout="wide",
            initial_sidebar_state="collapsed",
            menu_items={
                "Get Help": "mailto:your_email@example.com",
                "Report a bug": "mailto:your_email@example.com",
                "About": "نظام التعدين السوداني - جامعة الخرطوم"
            }
        )
    except Exception:
        st.set_page_config(page_title="نظام التعدين السوداني",
                           page_icon="⛏️", layout="wide")
else:
    st.set_page_config(page_title="نظام التعدين السوداني",
                       page_icon="⛏️", layout="wide")

# ============ CSS مخصص ============
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
    .stAlert { border-radius: 8px; }
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
    @media print {
        .stButton, .stDownloadButton, .stSlider { display: none; }
    }
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
# ============ DRASTIC RATING FUNCTIONS ============
# ============================================================
def get_d_rating(d):
    """Depth to water table (m) -> rating"""
    if d < 0: raise ValueError("Depth must be >= 0")
    if d <= 1.5: return 10
    if d <= 4.6: return 9
    if d <= 9.1: return 7
    if d <= 15.2: return 5
    if d <= 22.9: return 3
    if d <= 30.5: return 2
    return 1

def get_r_rating(r):
    """Net recharge (mm/year) -> rating"""
    if r < 0: raise ValueError("Recharge must be >= 0")
    if r <= 50.8: return 1
    if r <= 101.6: return 3
    if r <= 177.8: return 6
    if r <= 254.0: return 8
    return 9

def get_a_rating(a):
    """Aquifer media -> rating"""
    return {"massive_shale": 2, "metamorphic_igneous": 3,
        "weathered_metamorphic_igneous": 4, "thin_bedded_sequences": 6,
        "massive_sandstone": 6, "massive_limestone": 6,
        "sand_and_gravel": 8, "basalt": 9, "karst_limestone": 10}.get(a, 6)

def get_s_rating(s):
    """Soil media -> rating"""
    return {"thin_or_absent": 10, "gravel": 10, "sand": 9, "peat": 8,
        "shrinking_aggregated_clay": 7, "sandy_loam": 6, "loam": 5,
        "silty_loam": 4, "clay_loam": 3, "muck": 2,
        "nonshrinking_clay": 1}.get(s, 5)

def get_t_rating(t):
    """Topography (slope %) -> rating"""
    if t < 0: raise ValueError("Slope must be >= 0")
    if t <= 2.0: return 10
    if t <= 6.0: return 9
    if t <= 12.0: return 5
    if t <= 18.0: return 3
    return 1

def get_i_rating(i):
    """Impact of vadose zone -> rating"""
    return {"confining_layer": 1, "silt_clay": 1, "shale": 3,
        "metamorphic_igneous": 4, "limestone": 6, "sandstone": 6,
        "sand_gravel_silt_clay": 6, "sand_gravel": 8,
        "basalt": 9, "karst_limestone": 10}.get(i, 6)

def get_c_rating(c):
    """Hydraulic conductivity (m/day) -> rating"""
    if c < 0: raise ValueError("Conductivity must be >= 0")
    if c <= 4.074: return 1
    if c <= 12.222: return 2
    if c <= 28.518: return 4
    if c <= 40.740: return 6
    if c <= 81.480: return 8
    return 10

def calc_index(D, R, A, S, T, I, C):
    """DRASTIC index = sum(rating * weight)"""
    return (D*5) + (R*4) + (A*3) + (S*2) + (T*1) + (I*5) + (C*3)

def classify(idx):
    """Classify DRASTIC index"""
    if idx >= 180: return {"level": "مرتفع جدا", "color": "red", "action": "معالجة فورية"}
    if idx >= 140: return {"level": "مرتفع", "color": "orange", "action": "مراقبة عاجلة"}
    if idx >= 100: return {"level": "متوسط", "color": "yellow", "action": "مراقبة دورية"}
    return {"level": "منخفض", "color": "green", "action": "مراقبة روتينية"}


# ============================================================
# ============ تصحيح 1: calc_travel مع التدرج الهيدروليكي ============
# ============================================================
def calc_travel(d, p, k, i=0.01):
    """
    حساب زمن وصول الملوثات باستخدام قانون دارسي
    
    Parameters:
    -----------
    d : float - عمق المياه الجوفية (m)
    p : float - المسامية الفعالة (0.01 - 0.60)
    k : float - التوصيلية الهيدروليكية (m/day)
    i : float - التدرج الهيدروليكي (Hydraulic Gradient) - dimensionless
              القيم النموذجية: 0.001 - 0.05 (0.01 افتراضي)
    
    Returns:
    --------
    dict: days, years, velocity (m/day)
    
    Formula:
    --------
    v = K * i / n     (Darcy velocity)
    time = d / v
    """
    if d <= 0: raise ValueError("Depth must be > 0")
    if not (0.01 < p < 0.60): raise ValueError("Porosity must be between 0.01 and 0.60")
    if k <= 0: raise ValueError("Conductivity must be > 0")
    if not (0.0001 <= i <= 0.5): raise ValueError("Hydraulic gradient must be between 0.0001 and 0.5")
    
    v = (k * i) / p  # Darcy velocity (m/day)
    days = d / v
    return {
        "days": round(days, 2),
        "years": round(days / 365.25, 3),
        "velocity": round(v, 6),
        "gradient": i
    }


def mitigate(idx, hdpe=False, treat=False, mon=False):
    """تخفيف المؤشر بناءً على الحلول المطبقة"""
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
# ============ تصحيح 2: sensitivity_analysis على القيم الفيزيائية ============
# ============================================================
def sensitivity_analysis(physical_values, variation=0.10):
    """
    تحليل الحساسية بتطبيق التغيير على القيم الفيزيائية الأصلية
    
    Parameters:
    -----------
    physical_values : dict
        يحتوي على القيم الفيزيائية:
        D (depth_m), R (recharge_mm), A (aquifer_name),
        S (soil_name), T (slope_pct), I (vadose_name), C (conductivity)
    variation : float - نسبة التغيير (0.10 = 10%)
    
    Returns:
    --------
    dict: base_index, parameters (sensitivity per parameter), most_sensitive
    """
    # استخراج القيم الفيزيائية
    D_phys = float(physical_values.get("depth", 15.0))
    R_phys = float(physical_values.get("recharge", 100.0))
    A_phys = str(physical_values.get("aquifer", "massive_sandstone"))
    S_phys = str(physical_values.get("soil", "sand"))
    T_phys = float(physical_values.get("slope", 4.0))
    I_phys = str(physical_values.get("vadose", "sand_gravel"))
    C_phys = float(physical_values.get("conductivity", 5.0))
    
    # حساب المؤشر الأساسي
    def compute_index(d, r, a, s, t, i, c):
        return calc_index(
            get_d_rating(d), get_r_rating(r), get_a_rating(a),
            get_s_rating(s), get_t_rating(t), get_i_rating(i),
            get_c_rating(c))
    
    base = compute_index(D_phys, R_phys, A_phys, S_phys, T_phys, I_phys, C_phys)
    
    # كل معامل: نغير قيمته الفيزيائية ثم نعيد حساب التصنيف
    results = {}
    
    # D: تغيير فيزيائي
    D_mod = max(0.5, min(100.0, D_phys * (1 + variation)))
    new_idx = compute_index(D_mod, R_phys, A_phys, S_phys, T_phys, I_phys, C_phys)
    results["D"] = {"original_phys": D_phys, "modified_phys": round(D_mod, 2),
                    "original_rating": get_d_rating(D_phys),
                    "new_rating": get_d_rating(D_mod),
                    "new_index": new_idx, "change": new_idx - base,
                    "sensitivity": round(abs(new_idx - base) / base * 100, 3)}
    
    # R: تغيير فيزيائي
    R_mod = max(0.0, min(400.0, R_phys * (1 + variation)))
    new_idx = compute_index(D_phys, R_mod, A_phys, S_phys, T_phys, I_phys, C_phys)
    results["R"] = {"original_phys": R_phys, "modified_phys": round(R_mod, 2),
                    "original_rating": get_r_rating(R_phys),
                    "new_rating": get_r_rating(R_mod),
                    "new_index": new_idx, "change": new_idx - base,
                    "sensitivity": round(abs(new_idx - base) / base * 100, 3)}
    
    # A: قيمي - نغير التصنيف مباشرة ±1
    A_orig_r = get_a_rating(A_phys)
    A_new_r = max(1, min(10, A_orig_r + 1))
    new_idx = base - A_orig_r * 3 + A_new_r * 3
    results["A"] = {"original_phys": A_phys, "modified_phys": "rating +1",
                    "original_rating": A_orig_r, "new_rating": A_new_r,
                    "new_index": new_idx, "change": new_idx - base,
                    "sensitivity": round(abs(new_idx - base) / base * 100, 3)}
    
    # S: قيمي
    S_orig_r = get_s_rating(S_phys)
    S_new_r = max(1, min(10, S_orig_r + 1))
    new_idx = base - S_orig_r * 2 + S_new_r * 2
    results["S"] = {"original_phys": S_phys, "modified_phys": "rating +1",
                    "original_rating": S_orig_r, "new_rating": S_new_r,
                    "new_index": new_idx, "change": new_idx - base,
                    "sensitivity": round(abs(new_idx - base) / base * 100, 3)}
    
    # T: تغيير فيزيائي
    T_mod = max(0.0, min(30.0, T_phys * (1 + variation)))
    new_idx = compute_index(D_phys, R_phys, A_phys, S_phys, T_mod, I_phys, C_phys)
    results["T"] = {"original_phys": T_phys, "modified_phys": round(T_mod, 2),
                    "original_rating": get_t_rating(T_phys),
                    "new_rating": get_t_rating(T_mod),
                    "new_index": new_idx, "change": new_idx - base,
                    "sensitivity": round(abs(new_idx - base) / base * 100, 3)}
    
    # I: قيمي
    I_orig_r = get_i_rating(I_phys)
    I_new_r = max(1, min(10, I_orig_r + 1))
    new_idx = base - I_orig_r * 5 + I_new_r * 5
    results["I"] = {"original_phys": I_phys, "modified_phys": "rating +1",
                    "original_rating": I_orig_r, "new_rating": I_new_r,
                    "new_index": new_idx, "change": new_idx - base,
                    "sensitivity": round(abs(new_idx - base) / base * 100, 3)}
    
    # C: تغيير فيزيائي
    C_mod = max(0.01, min(100.0, C_phys * (1 + variation)))
    new_idx = compute_index(D_phys, R_phys, A_phys, S_phys, T_phys, I_phys, C_mod)
    results["C"] = {"original_phys": C_phys, "modified_phys": round(C_mod, 2),
                    "original_rating": get_c_rating(C_phys),
                    "new_rating": get_c_rating(C_mod),
                    "new_index": new_idx, "change": new_idx - base,
                    "sensitivity": round(abs(new_idx - base) / base * 100, 3)}
    
    sorted_results = dict(sorted(results.items(),
                                  key=lambda x: x[1]["sensitivity"], reverse=True))
    return {"base_index": base, "variation": variation,
            "parameters": sorted_results,
            "most_sensitive": list(sorted_results.keys())[0] if sorted_results else None}


# ============================================================
# ============ تصحيح 3: Monte Carlo بـ numpy وتوزيعات واقعية ============
# ============================================================
def monte_carlo_analysis(physical_values, n_iter=1000, variation=0.15):
    """
    محاكاة Monte Carlo باستخدام numpy مع توزيعات احتمالية واقعية
    
    يستخدم:
    - Log-Normal للـ K (التوصيلية الهيدروليكية) - توزيع شائع
    - Normal للـ D, R, T
    - Uniform للـ A, S, I (قيم قيمية)
    
    Parameters:
    -----------
    physical_values : dict - القيم الفيزيائية
    n_iter : int - عدد المحاكاات
    variation : float - معامل الاختلاف (Coefficient of Variation)
    """
    np.random.seed(42)  # للنتائج القابلة للتكرار
    
    # استخراج القيم
    D = float(physical_values.get("depth", 15.0))
    R = float(physical_values.get("recharge", 100.0))
    A_name = str(physical_values.get("aquifer", "massive_sandstone"))
    S_name = str(physical_values.get("soil", "sand"))
    T = float(physical_values.get("slope", 4.0))
    I_name = str(physical_values.get("vadose", "sand_gravel"))
    C = float(physical_values.get("conductivity", 5.0))
    
    # تحويل القيم القيمية إلى تصنيفات
    A_base = get_a_rating(A_name)
    S_base = get_s_rating(S_name)
    I_base = get_i_rating(I_name)
    
    # ===== توليد العينات =====
    # D: Normal distribution
    D_samples = np.random.normal(D, max(0.5, D * variation), n_iter)
    D_samples = np.clip(D_samples, 0.5, 100.0)
    
    # R: Log-Normal (شائع للتغذية)
    if R > 0:
        R_samples = np.random.lognormal(np.log(max(1, R)) - 0.5 * variation**2,
                                         variation, n_iter)
        R_samples = np.clip(R_samples, 0.0, 400.0)
    else:
        R_samples = np.zeros(n_iter)
    
    # A, S, I: تصنيفات - نأخذ قيماً من التصنيفات المجاورة
    A_ratings = [2, 3, 4, 6, 8, 9, 10]  # القيم المحتملة
    S_ratings = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    I_ratings = [1, 3, 4, 6, 8, 9, 10]
    
    A_samples = np.random.choice(
        [max(1, A_base - 1), A_base, min(10, A_base + 1)],
        size=n_iter, p=[0.15, 0.70, 0.15])
    S_samples = np.random.choice(
        [max(1, S_base - 1), S_base, min(10, S_base + 1)],
        size=n_iter, p=[0.15, 0.70, 0.15])
    I_samples = np.random.choice(
        [max(1, I_base - 1), I_base, min(10, I_base + 1)],
        size=n_iter, p=[0.15, 0.70, 0.15])
    
    # T: Normal
    T_samples = np.random.normal(T, max(0.5, T * variation), n_iter)
    T_samples = np.clip(T_samples, 0.0, 30.0)
    
    # C: Log-Normal (K عادة log-normal)
    C_samples = np.random.lognormal(np.log(max(0.01, C)) - 0.5 * variation**2,
                                     variation, n_iter)
    C_samples = np.clip(C_samples, 0.01, 100.0)
    
    # ===== حساب التصنيفات لكل عينة (باستخدام vectorization) =====
    # D rating
    D_ratings = np.select(
        [D_samples <= 1.5, D_samples <= 4.6, D_samples <= 9.1,
         D_samples <= 15.2, D_samples <= 22.9, D_samples <= 30.5],
        [10, 9, 7, 5, 3, 2], default=1)
    
    # R rating
    R_ratings = np.select(
        [R_samples <= 50.8, R_samples <= 101.6, R_samples <= 177.8, R_samples <= 254.0],
        [1, 3, 6, 8], default=9)
    
    # T rating
    T_ratings = np.select(
        [T_samples <= 2.0, T_samples <= 6.0, T_samples <= 12.0, T_samples <= 18.0],
        [10, 9, 5, 3], default=1)
    
    # C rating
    C_ratings = np.select(
        [C_samples <= 4.074, C_samples <= 12.222, C_samples <= 28.518,
         C_samples <= 40.740, C_samples <= 81.480],
        [1, 2, 4, 6, 8], default=10)
    
    # ===== حساب DRASTIC لكل عينة =====
    drastic_samples = (D_ratings * 5 + R_ratings * 4 + A_samples * 3 +
                       S_samples * 2 + T_ratings * 1 + I_samples * 5 +
                       C_ratings * 3)
    
    # ===== الإحصائيات =====
    results = np.sort(drastic_samples.astype(int))
    n = len(results)
    mean = float(np.mean(results))
    std = float(np.std(results))
    
    def pct(p):
        return int(np.percentile(results, p))
    
    over_140 = float(np.mean(results >= 140) * 100)
    over_180 = float(np.mean(results >= 180) * 100)
    
    return {
        "base": calc_index(get_d_rating(D), get_r_rating(R), A_base,
                           S_base, get_t_rating(T), I_base, get_c_rating(C)),
        "n": n, "mean": round(mean, 1), "std": round(std, 2),
        "min": int(results[0]), "max": int(results[-1]),
        "p5": pct(5), "p25": pct(25), "p50": pct(50),
        "p75": pct(75), "p95": pct(95),
        "ci_90": (pct(5), pct(95)), "ci_50": (pct(25), pct(75)),
        "prob_over_140": round(over_140, 1),
        "prob_over_180": round(over_180, 1),
        "samples": results  # للرسم البياني
    }


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


def validate_single_input(depth, recharge, slope, conductivity,
                          aquifer, soil, vadose, gradient=0.01):
    """التحقق من صحة المدخلات الفردية"""
    errors = []
    warnings = []
    if not (0.5 <= depth <= 100): errors.append("D خارج النطاق (0.5-100)")
    if not (0 <= recharge <= 400): errors.append("R خارج النطاق (0-400)")
    if not (0 <= slope <= 30): errors.append("T خارج النطاق (0-30)")
    if not (0.01 <= conductivity <= 100): errors.append("C خارج النطاق (0.01-100)")
    if not (0.0001 <= gradient <= 0.5):
        errors.append("i خارج النطاق (0.0001-0.5)")
    if aquifer not in VALID_AQUIFERS: warnings.append("A غير معروف")
    if soil not in VALID_SOILS: warnings.append("S غير معروف")
    if vadose not in VALID_VADOSE: warnings.append("I غير معروف")
    return errors, warnings


def validate_bulk_row(row, idx):
    """التحقق من صف واحد في التقييم الجماعي"""
    errors = []
    warnings = []
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
    if errors: quality = "ضعيف"
    elif warnings: quality = "متوسط"
    else: quality = "ممتاز"
    return errors, warnings, quality


def generate_quality_report(df, results_df):
    """تقرير جودة الملف"""
    L = ["=" * 60, "تقرير جودة الملف المُرفوع", "=" * 60, ""]
    L.append("عدد الصفوف: " + str(len(df)))
    L.append("عدد الأعمدة: " + str(len(df.columns)))
    L.append("")
    L.append("الأعمدة الإلزامية:")
    for col in REQUIRED_COLS:
        status = "موجود" if col in df.columns else "مفقود"
        L.append("  " + col + ": " + status)
    L.append("")
    if not results_df.empty and "الجودة" in results_df.columns:
        L.append("توزيع الجودة:")
        for q in ["ممتاز", "متوسط", "ضعيف"]:
            n = len(results_df[results_df["الجودة"] == q])
            L.append("  " + q + ": " + str(n))
    L.append("")
    L.append("=" * 60)
    return "\n".join(L)


# ============================================================
# ============ تصحيح 4: DRASTIC للمواقع المدمجة بقيم مخصصة ============
# ============================================================
def get_preset_sites_with_drastic(preset):
    """
    حساب DRASTIC لكل موقع مدمج باستخدام القيم المخصصة لكل موقع
    
    إذا كانت القيم الفيزيائية (recharge, aquifer, soil, slope, vadose)
    غير متوفرة في بيانات الموقع، يتم استخدام القيم الافتراضية.
    """
    sites = []
    for name, data in preset.items():
        try:
            coords = data.get("coords", (0, 0))
            
            # استخراج القيم الفيزيائية (مع قيم افتراضية)
            D_phys = float(data.get("depth", 15.0))
            R_phys = float(data.get("recharge", 100.0))  # mm/year
            A_phys = str(data.get("aquifer", "massive_sandstone"))
            S_phys = str(data.get("soil", "sand"))
            T_phys = float(data.get("slope", 4.0))
            I_phys = str(data.get("vadose", "sand_gravel"))
            C_phys = float(data.get("conductivity", 5.0))
            
            # حساب التصنيفات
            D_r = get_d_rating(D_phys)
            R_r = get_r_rating(R_phys)
            A_r = get_a_rating(A_phys)
            S_r = get_s_rating(S_phys)
            T_r = get_t_rating(T_phys)
            I_r = get_i_rating(I_phys)
            C_r = get_c_rating(C_phys)
            
            ix = calc_index(D_r, R_r, A_r, S_r, T_r, I_r, C_r)
            rk = classify(ix)
            
            sites.append({
                "name": str(name),
                "lat": float(coords[0]),
                "lon": float(coords[1]),
                "index": ix,
                "level": rk["level"],
                "color": rk["color"],
                "depth": D_phys,
                "recharge": R_phys,
                "conductivity": C_phys,
                "source": data.get("source", "غير محدد"),
                "type": "preset"
            })
        except Exception as e:
            print(f"Error processing {name}: {e}")
            continue
    return sites


# ============================================================
# ============ Mercury + Cyanide Analysis ============
# ============================================================
def analyze_mercury(w, s):
    """تحليل الزئبق - WHO 2022 limits"""
    wl, sl = 0.006, 1.0  # mg/L for water, mg/kg for soil
    wr, sr = w / wl, s / sl
    mr = max(wr, sr)
    if mr <= 1.0: lvl = "منخفض"
    elif mr <= 3.0: lvl = "متوسط"
    elif mr <= 10.0: lvl = "مرتفع"
    else: lvl = "مرتفع جدا"
    return {"water": {"value": w, "limit": wl, "ratio": round(wr, 2),
                      "status": "safe" if w <= wl else "exceeded"},
            "soil": {"value": s, "limit": sl, "ratio": round(sr, 2),
                     "status": "safe" if s <= sl else "exceeded"},
            "toxicity_level": lvl, "max_ratio": round(mr, 2)}

def analyze_cyanide(w, s):
    """تحليل السيانيد - WHO 2022 limits"""
    wl, sl = 0.07, 10.0
    wr, sr = w / wl, s / sl
    mr = max(wr, sr)
    if mr <= 1.0: lvl = "منخفض"
    elif mr <= 3.0: lvl = "متوسط"
    elif mr <= 10.0: lvl = "مرتفع"
    else: lvl = "مرتفع جدا"
    return {"water": {"value": w, "limit": wl, "ratio": round(wr, 2),
                      "status": "safe" if w <= wl else "exceeded"},
            "soil": {"value": s, "limit": sl, "ratio": round(sr, 2),
                     "status": "safe" if s <= sl else "exceeded"},
            "toxicity_level": lvl, "max_ratio": round(mr, 2)}

def weighted_toxicity(hgw, hgs, cnw, cns):
    """مؤشر سمية مرجح"""
    w = (hgw / 0.006 * 0.40) + (hgs / 1.0 * 0.20) + \
        (cnw / 0.07 * 0.30) + (cns / 10.0 * 0.10)
    if w <= 1.0: cat, act = "آمن", "لا يتطلب تدخل"
    elif w <= 3.0: cat, act = "تحت المراقبة", "مراقبة دورية"
    elif w <= 10.0: cat, act = "خطر", "تدخل عاجل"
    else: cat, act = "خطر داهم", "إيقاف النشاط"
    return {"index": round(w, 2), "category": cat, "action": act}

def generate_alerts(idx, hg=None, cn=None, tox=None):
    """توليد التنبيهات"""
    al = []
    if idx >= 180:
        al.append({"icon": "🔴", "msg": "DRASTIC " + str(idx), "act": "إيقاف النشاط"})
    elif idx >= 140:
        al.append({"icon": "🟠", "msg": "DRASTIC " + str(idx), "act": "تدخل عاجل"})
    elif idx >= 100:
        al.append({"icon": "🟡", "msg": "DRASTIC " + str(idx), "act": "مراقبة"})
    if hg:
        if hg["water"]["status"] == "exceeded":
            al.append({"icon": "⚠️", "msg": "Hg مياه " + str(hg["water"]["ratio"]) + "x", "act": "تحذير"})
        if hg["soil"]["status"] == "exceeded":
            al.append({"icon": "⚠️", "msg": "Hg تربة " + str(hg["soil"]["ratio"]) + "x", "act": "معالجة"})
    if cn:
        if cn["water"]["status"] == "exceeded":
            al.append({"icon": "☠️", "msg": "CN مياه " + str(cn["water"]["ratio"]) + "x", "act": "إخلاء"})
        if cn["soil"]["status"] == "exceeded":
            al.append({"icon": "☠️", "msg": "CN تربة " + str(cn["soil"]["ratio"]) + "x", "act": "معالجة"})
    if tox and tox["index"] > 10:
        al.append({"icon": "🚨", "msg": "سمية " + str(tox["index"]), "act": "تدخل فوري"})
    return al


# ============================================================
# ============ Satellite Data ============
# ============================================================
def get_rainfall(lat, lon, years=3):
    """جلب بيانات الأمطار من Open-Meteo"""
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
    """جلب بيانات الحرارة من Open-Meteo"""
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
    """تصنيف المناخ حسب الأمطار"""
    if r is None: return "غير محدد"
    if r < 100: return "صحراوي"
    if r < 250: return "شبه جاف"
    if r < 500: return "شبه رطب"
    return "رطب"

def estimate_recharge(r, soil="sand"):
    """تقدير التغذية من الأمطار"""
    if r is None: return None
    ratios = {"sand": 0.20, "sandy_loam": 0.15, "loam": 0.12,
              "silty_loam": 0.10, "clay_loam": 0.07, "nonshrinking_clay": 0.04}
    return round(r * ratios.get(soil, 0.12), 1)

def fetch_satellite(lat, lon, years=3):
    """جلب البيانات الفضائية"""
    rain = get_rainfall(lat, lon, years)
    temp = get_temperature(lat, lon, years)
    return {"rainfall_mm": rain, "temperature_c": temp,
            "aridity": classify_aridity(rain),
            "ndvi_estimated": round(min(0.7, max(0.05, (rain or 0) / 1000.0)), 3) if rain else None,
            "source": "ERA5 (ECMWF) via Open-Meteo"}


# ============================================================
# ============ History ============
# ============================================================
def save_to_history(site, coords, idx, level, values, travel, sat, tox):
    """حفظ التقييم في التاريخ"""
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
        "زمن الوصول": travel if travel else 0,
        "الأمطار": sat.get("rainfall_mm", 0) if sat else 0,
        "مؤشر السمية": tox.get("index", 0) if tox else 0})

def get_history_df():
    """الحصول على تاريخ التقييمات كـ DataFrame"""
    if "history" not in st.session_state or not st.session_state["history"]:
        return pd.DataFrame()
    return pd.DataFrame(st.session_state["history"])


# ============================================================
# ============ GIS Export ============
# ============================================================
def sites_to_geojson(sites):
    """تحويل المواقع إلى GeoJSON"""
    features = []
    for s in sites:
        try:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point",
                    "coordinates": [float(s.get("lon", 0)), float(s.get("lat", 0))]},
                "properties": {
                    "name": str(s.get("name", "")),
                    "drastic_index": int(s.get("index", 0)),
                    "risk_level": str(s.get("level", ""))}})
        except Exception:
            continue
    return json.dumps({"type": "FeatureCollection", "features": features},
                      ensure_ascii=False, indent=2)

def sites_to_kml(sites):
    """تحويل المواقع إلى KML"""
    kml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    kml += '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>\n'
    kml += '<name>Sudan Mining System - DRASTIC Sites</name>\n'
    for s in sites:
        try:
            kml += '  <Placemark><name>' + str(s.get("name", "")) + '</name>\n'
            kml += '    <description>DRASTIC: ' + str(s.get("index", 0)) + \
                   ' | ' + str(s.get("level", "")) + '</description>\n'
            kml += '    <Point><coordinates>' + str(s.get("lon", 0)) + ',' + \
                   str(s.get("lat", 0)) + ',0</coordinates></Point>\n'
            kml += '  </Placemark>\n'
        except Exception:
            continue
    kml += '</Document></kml>'
    return kml


# ============================================================
# ============ Report Templates ============
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
    """الحصول على مفتاح القالب حسب المؤشر"""
    if idx >= 180: return "very_high"
    if idx >= 140: return "high"
    if idx >= 100: return "moderate"
    return "low"

def gen_report(site, coords, idx, values, travel_data=None, sat=None, tox=None):
    """توليد التقرير النصي"""
    key = get_tpl_key(idx)
    tpl = TEMPLATES[key]
    today = datetime.date.today()
    ref = "GRAS-" + today.strftime("%Y%m%d") + "-" + key.upper()[:3]
    L = ["=" * 60, "تقرير تقييم هشاشة المياه الجوفية",
         "نظام التعدين السوداني - جامعة الخرطوم", "=" * 60, "",
         "الرقم المرجعي: " + ref,
         "التاريخ: " + today.strftime("%Y-%m-%d"),
         "الموقع: " + str(site),
         "الإحداثيات: " + str(coords[0]) + ", " + str(coords[1]), "",
         "مؤشر DRASTIC: " + str(idx) + " / 230",
         "المستوى: " + tpl["level"] + " (" + tpl["range"] + ")", "",
         "D: " + str(values.get("depth", "N/A")),
         "R: " + str(values.get("recharge", "N/A")),
         "A: " + str(values.get("aquifer", "N/A")),
         "S: " + str(values.get("soil", "N/A")),
         "T: " + str(values.get("slope", "N/A")),
         "I: " + str(values.get("vadose", "N/A")),
         "C: " + str(values.get("conductivity", "N/A")), ""]
    if travel_data:
        if isinstance(travel_data, dict):
            L.append("زمن الوصول: " + str(travel_data.get("years", 0)) + " سنة")
        else:
            L.append("زمن الوصول: " + str(round(travel_data, 2)) + " سنة")
        L.append("")
    if sat and sat.get("rainfall_mm"):
        L.append("بيانات الاقمار الصناعية:")
        L.append("  الامطار: " + str(sat.get("rainfall_mm")) + " مم")
        L.append("  الحرارة: " + str(sat.get("temperature_c")))
        L.append("  المناخ: " + str(sat.get("aridity")))
        L.append("")
    if tox:
        L.append("تحليل السمية:")
        L.append("  المؤشر: " + str(tox.get("index")))
        L.append("  التصنيف: " + str(tox.get("category")))
        L.append("")
    L.append("التقييم: " + tpl["assessment"])
    L.append("")
    L.append("التوصيات:")
    for i, rec in enumerate(tpl["recs"], 1):
        L.append(str(i) + ". " + rec)
    L += ["", "الامتثال: قانون التعدين 2015 - قانون البيئة 2001",
          "المراجع: EPA/600/2-87/035, Fetter 2001, WHO 2022", "",
          "توقيع المهندس: _______________________", "=" * 60]
    return "\n".join(L)

def gen_html(rep, site):
    """توليد HTML للتقرير"""
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
# ============ UI ============
# ============================================================
_col1, _col2, _col3 = st.columns([1, 2, 1])
with _col2:
    if PIL_OK:
        try:
            st.image("logo.png", use_container_width=True)
        except Exception:
            st.markdown("<h1 style='text-align:center;'>⛏️</h1>", unsafe_allow_html=True)

st.markdown("""
<div class="header-container">
    <div class="header-title">⛏️ نظام التعدين السوداني v36.0</div>
    <div class="header-subtitle">جامعة الخرطوم - كلية الهندسة</div>
    <div class="header-subtitle">نظام تقييم هشاشة المياه الجوفية</div>
</div>
""", unsafe_allow_html=True)

if DS_OK:
    preset = get_preset_locations_for_app()
    summary = get_data_summary()
else:
    preset = {"موقع تجريبي": {"coords": (19.53, 33.32),
              "depth": 15.0, "conductivity": 5.0,
              "recharge": 100.0, "aquifer": "massive_sandstone",
              "soil": "sand", "slope": 4.0, "vadose": "sand_gravel",
              "source": "افتراضي"}}
    summary = {"Total Data Points": 1}

tabs = st.tabs(["📍 المدخلات", "📊 الجماعي", "🛡️ الحلول", "📄 التقرير",
                "🗺️ الخريطة", "📊 الدقة", "📈 الحساسية", "⚖️ مقارنة",
                "☠️ السمية", "📚 التاريخ", "🌍 GIS", "🎲 Monte Carlo"])


# ============ TAB 1: المدخلات ============
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
            st.info("التغذية المقدرة: " +
                    str(estimate_recharge(s["rainfall_mm"])) + " مم/سنة")

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
        aquifer = st.selectbox("A - الوسط المائي:",
            VALID_AQUIFERS,
            index=VALID_AQUIFERS.index(sd.get("aquifer", "massive_sandstone"))
                  if sd.get("aquifer") in VALID_AQUIFERS else 0)
        soil = st.selectbox("S - التربة:",
            VALID_SOILS,
            index=VALID_SOILS.index(sd.get("soil", "sand"))
                  if sd.get("soil") in VALID_SOILS else 0)
        vadose = st.selectbox("I - نطاق التهوية:",
            VALID_VADOSE,
            index=VALID_VADOSE.index(sd.get("vadose", "sand_gravel"))
                  if sd.get("vadose") in VALID_VADOSE else 0)
        porosity = st.slider("θ - المسامية:", 0.02, 0.55, 0.25, 0.01)

    st.markdown("---")
    st.subheader("معاملات إضافية")
    c1, c2 = st.columns(2)
    with c1:
        gradient = st.slider(
            "i - التدرج الهيدروليكي:", 0.0001, 0.5, 0.01, 0.0001,
            format="%.4f",
            help="التدرج الهيدروليكي = فرق المناسيب / المسافة. "
                 "قيم نموذجية: 0.001 - 0.05")
    with c2:
        st.caption("ℹ️ التدرج الهيدروليكي يُستخدم في معادلة Darcy "
                   "لحساب سرعة تدفق المياه الجوفية.")

    errors, warnings = validate_single_input(
        depth, recharge, slope, conductivity, aquifer, soil, vadose, gradient)
    if errors:
        for e in errors:
            st.error("❌ " + e)
    if warnings:
        for w in warnings:
            st.warning("⚠️ " + w)

    try:
        D_r = get_d_rating(depth)
        R_r = get_r_rating(recharge)
        A_r = get_a_rating(aquifer)
        S_r = get_s_rating(soil)
        T_r = get_t_rating(slope)
        I_r = get_i_rating(vadose)
        C_r = get_c_rating(conductivity)
        idx = calc_index(D_r, R_r, A_r, S_r, T_r, I_r, C_r)
        risk = classify(idx)

        # حساب زمن الوصول بالمعادلة المصححة
        travel = calc_travel(depth, porosity, conductivity, gradient)

        # حفظ في session_state
        st.session_state["ci"] = idx
        st.session_state["cs"] = site
        st.session_state["cc"] = sd["coords"]
        st.session_state["cr"] = {"D": D_r, "R": R_r, "A": A_r,
            "S": S_r, "T": T_r, "I": I_r, "C": C_r}
        st.session_state["cv"] = {
            "depth": depth, "recharge": recharge,
            "aquifer": aquifer, "soil": soil, "slope": slope,
            "vadose": vadose, "conductivity": conductivity,
            "porosity": porosity, "gradient": gradient}
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
        z1.metric("مؤشر DRASTIC", str(idx) + " / 230")
        z2.metric("المستوى", risk["level"])
        if risk["color"] == "red": st.error(risk["action"])
        elif risk["color"] == "orange": st.warning(risk["action"])
        elif risk["color"] == "yellow": st.info(risk["action"])
        else: st.success(risk["action"])
        st.markdown("---")
        st.subheader("زمن وصول الملوثات (قانون دارسي)")
        w1, w2, w3, w4 = st.columns(4)
        w1.metric("سنوات", travel["years"])
        w2.metric("أيام", travel["days"])
        w3.metric("السرعة (م/يوم)", travel["velocity"])
        w4.metric("i", travel["gradient"])
        with st.expander("ℹ️ كيف تم الحساب؟"):
            st.markdown(f"""
            **معادلة دارسي:**
            $$v = \\frac{{K \\cdot i}}{{n}}$$
            
            - **K** (التوصيلية الهيدروليكية) = {conductivity} م/يوم
            - **i** (التدرج الهيدروليكي) = {gradient}
            - **n** (المسامية الفعالة) = {porosity}
            - **v** (السرعة) = {travel['velocity']} م/يوم
            - **زمن الوصول** = العمق / السرعة = {depth} / {travel['velocity']}
              = {travel['days']} يوم = {travel['years']} سنة
            """)
        st.markdown("---")
        if st.button("💾 حفظ في التاريخ", key="save_hist"):
            save_to_history(site, sd["coords"], idx, risk["level"],
                            st.session_state["cv"], travel,
                            st.session_state.get("sat_data"),
                            st.session_state.get("tox_result"))
            st.success("✅ تم الحفظ")
    except ValueError as e:
        st.error("خطأ: " + str(e))


# ============ TAB 2: التقييم الجماعي ============
with tabs[1]:
    st.header("📊 التقييم الجماعي")
    sample = pd.DataFrame({
        "name": ["A", "B"],
        "lat": [19.53, 18.12], "lon": [33.32, 33.99],
        "depth_m": [15.0, 10.0], "recharge_mm": [80.0, 120.0],
        "slope_pct": [4.0, 8.0], "conductivity": [5.0, 10.0],
        "aquifer": ["massive_sandstone", "sand_and_gravel"],
        "soil": ["sand", "sandy_loam"],
        "vadose": ["sand_gravel", "sandstone"]})
    st.download_button("📥 تحميل نموذج CSV",
        data=sample.to_csv(index=False).encode("utf-8-sig"),
        file_name="template.csv", mime="text/csv")

    f = st.file_uploader("📤 ارفع ملف CSV أو Excel:",
                          type=["csv", "xlsx"], key="bulk_v36")
    if f:
        try:
            df = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)
            st.markdown("---")
            st.subheader("🔍 فحص جودة الملف")
            c1, c2, c3 = st.columns(3)
            c1.metric("عدد الصفوف", len(df))
            c2.metric("عدد الأعمدة", len(df.columns))
            missing_cols = [col for col in REQUIRED_COLS
                           if col not in df.columns]
            c3.metric("أعمدة مفقودة", len(missing_cols))
            if missing_cols:
                st.warning("⚠️ أعمدة مفقودة:")
                for col in missing_cols:
                    st.caption("• " + col)
            else:
                st.success("✅ كل الأعمدة موجودة")

            results = []
            qualities = {"ممتاز": 0, "متوسط": 0, "ضعيف": 0}
            for i, row in df.iterrows():
                errs, warns, quality = validate_bulk_row(row, i)
                qualities[quality] += 1
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
                        "الموقع": row.get("name", "Site " + str(i)),
                        "lat": row.get("lat", 0),
                        "lon": row.get("lon", 0),
                        "المؤشر": ix,
                        "المستوى": rk["level"],
                        "الجودة": quality,
                        "ملاحظات": "، ".join(notes) if notes else "—"})
                except Exception as e:
                    results.append({
                        "الموقع": row.get("name", "Site " + str(i)),
                        "lat": row.get("lat", 0), "lon": row.get("lon", 0),
                        "المؤشر": 0, "المستوى": "فشل", "الجودة": "ضعيف",
                        "ملاحظات": "خطأ: " + str(e)})

            st.markdown("---")
            st.subheader("📈 توزيع الجودة")
            q1, q2, q3 = st.columns(3)
            q1.metric("✅ ممتاز", qualities["ممتاز"])
            q2.metric("⚠️ متوسط", qualities["متوسط"])
            q3.metric("❌ ضعيف", qualities["ضعيف"])

            total = sum(qualities.values())
            if total > 0:
                quality_pct = qualities["ممتاز"] / total * 100
                st.progress(quality_pct / 100)
                st.caption("نسبة الجودة الممتازة: " +
                           str(round(quality_pct, 1)) + "%")

            dfr = pd.DataFrame(results)
            st.markdown("---")
            st.subheader("📋 النتائج")
            if not dfr.empty:
                valid = dfr[dfr["المؤشر"] > 0]
                if not valid.empty:
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("الإجمالي", len(dfr))
                    k2.metric("المتوسط", round(valid["المؤشر"].mean(), 1))
                    k3.metric("الأعلى", valid["المؤشر"].max())
                    k4.metric("خطرة", len(valid[valid["المؤشر"] >= 140]))
            st.dataframe(dfr, use_container_width=True)

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("📥 نتائج CSV",
                    data=dfr.to_csv(index=False).encode("utf-8-sig"),
                    file_name="results.csv", mime="text/csv",
                    use_container_width=True)
            with c2:
                qr = generate_quality_report(df, dfr)
                st.download_button("📥 تقرير الجودة",
                    data=qr.encode("utf-8-sig"),
                    file_name="quality_report.txt", mime="text/plain",
                    use_container_width=True)

            if qualities["ضعيف"] > 0:
                st.error("⚠️ " + str(qualities["ضعيف"]) + " صف ضعيف الجودة")
            elif qualities["متوسط"] > 0:
                st.warning("⚠️ " + str(qualities["متوسط"]) + " صف متوسط")
            else:
                st.success("✅ كل الصفوف ممتازة")
        except Exception as e:
            st.error("خطأ: " + str(e))


# ============ TAB 3: الحلول ============
with tabs[2]:
    st.header("محاكي الحلول")
    if "ci" in st.session_state:
        ci = st.session_state["ci"]
        st.info("الموقع: " + st.session_state["cs"] + " | المؤشر: " + str(ci))
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
            c.metric("التخفيض", str(r["reduction_pct"]) + " %")
            st.progress(min(r["reduction_pct"] / 100, 1.0))
            st.metric("المستوى الجديد",
                      classify(int(r["mitigated_index"]))["level"])
    else:
        st.warning("افتح تبويب المدخلات أولا")


# ============ TAB 4: التقرير ============
with tabs[3]:
    st.header("توليد التقرير")
    if "ci" in st.session_state:
        ci = st.session_state["ci"]
        cs = st.session_state["cs"]
        st.info("الموقع: " + cs + " | المؤشر: " + str(ci))
        if st.button("توليد", type="primary", key="gen"):
            rep = gen_report(cs, st.session_state["cc"], ci,
                            st.session_state["cv"],
                            st.session_state.get("ct"),
                            st.session_state.get("sat_data"),
                            st.session_state.get("tox_result"))
            st.session_state["rep"] = rep
            st.success("تم التوليد")
        if "rep" in st.session_state:
            st.text_area("التقرير:", st.session_state["rep"], height=400)
            safe = cs.replace(" ", "_")
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("TXT",
                    data=("\ufeff" + st.session_state["rep"]).encode("utf-8"),
                    file_name="rep_" + safe + ".txt",
                    mime="text/plain; charset=utf-8",
                    use_container_width=True)
            with c2:
                st.download_button("HTML/PDF",
                    data=gen_html(st.session_state["rep"], cs).encode("utf-8"),
                    file_name="rep_" + safe + ".html",
                    mime="text/html; charset=utf-8",
                    use_container_width=True)
            st.warning("يحتاج مراجعة بشرية")
    else:
        st.warning("افتح تبويب المدخلات أولا")


# ============ TAB 5: الخريطة ============
with tabs[4]:
    st.header("🗺️ الخريطة التفاعلية — وفق معايير US EPA و ESRI")

    if DS_OK:
        st.markdown("### ⚙️ لوحة التحكم")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            show_wells = st.checkbox("🔵 آبار NARIS", value=True)
            show_darfur = st.checkbox("🟢 آبار دارفور", value=True)
        with col2:
            show_mining = st.checkbox("🔴 مواقع التعدين", value=True)
            show_khartoum = st.checkbox("🟣 محليات الخرطوم", value=True)
        with col3:
            show_buffers = st.checkbox("⭕ نطاقات التأثير", value=True)
            buffer_size = st.selectbox(
                "حجم النطاق:",
                ["500 م", "1000 م", "2000 م", "الكل"], index=3)
        with col4:
            base_map = st.selectbox(
                "الخلفية:",
                ["خريطة عادية", "أقمار صناعية", "تضاريس"], index=0)
            map_height = st.slider("ارتفاع الخريطة:", 400, 900, 700, 50)

        st.markdown("---")

        tiles_map = {
            "خريطة عادية": "OpenStreetMap",
            "أقمار صناعية": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            "تضاريس": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        }
        attr_map = {
            "خريطة عادية": None,
            "أقمار صناعية": "Esri World Imagery",
            "تضاريس": "Esri Topo",
        }

        m = folium.Map(location=[15.5, 32.5], zoom_start=6,
                       tiles=tiles_map[base_map], attr=attr_map[base_map],
                       control_scale=True)

        # طبقة NARIS
        if show_wells:
            for n, d in NARIS_WELLS.items():
                folium.Marker(
                    [d["coords"][1], d["coords"][0]],
                    popup=folium.Popup(
                        "<b>" + n + "</b><br>NARIS Well<br>"
                        "العمق: " + str(d.get("depth", "N/A")) + " م",
                        max_width=250),
                    tooltip=n,
                    icon=folium.Icon(color="blue", icon="tint", prefix="fa"),
                ).add_to(m)

        # طبقة دارفور
        if show_darfur:
            for n, d in DARFUR_WELLS.items():
                folium.Marker(
                    [d["coords"][1], d["coords"][0]],
                    popup=folium.Popup(
                        "<b>" + n + "</b><br>Darfur Well (UNEP)",
                        max_width=250),
                    tooltip=n,
                    icon=folium.Icon(color="green", icon="tint", prefix="fa"),
                ).add_to(m)

        # ============================================================
        # تصحيح 5: مواقع التعدين بألوان DRASTIC
        # ============================================================
        if show_mining:
            # حساب DRASTIC لكل موقع تعدين
            mining_sites_with_drastic = []
            for n, d in KNOWN_MINING_SITES.items():
                lat, lon = d["coords"][1], d["coords"][0]
                
                # استخراج القيم الفيزيائية (مع قيم افتراضية)
                D_phys = float(d.get("depth", 15.0))
                R_phys = float(d.get("recharge", 100.0))
                A_phys = str(d.get("aquifer", "massive_sandstone"))
                S_phys = str(d.get("soil", "sand"))
                T_phys = float(d.get("slope", 4.0))
                I_phys = str(d.get("vadose", "sand_gravel"))
                C_phys = float(d.get("conductivity", 5.0))
                
                ix = calc_index(
                    get_d_rating(D_phys), get_r_rating(R_phys),
                    get_a_rating(A_phys), get_s_rating(S_phys),
                    get_t_rating(T_phys), get_i_rating(I_phys),
                    get_c_rating(C_phys))
                rk = classify(ix)
                
                mining_sites_with_drastic.append({
                    "name": n, "lat": lat, "lon": lon,
                    "index": ix, "level": rk["level"], "color": rk["color"],
                    "cyanide": d.get("cyanide_use", False),
                    "mercury": d.get("mercury_use", False),
                    "activity": d.get("activity", "N/A")})
                
                # نطاقات التأثير
                if show_buffers:
                    if buffer_size in ["500 م", "الكل"]:
                        folium.Circle([lat, lon], radius=500,
                            color="red", weight=2, fill=True,
                            fill_opacity=0.20,
                            popup="نطاق 500م — " + n).add_to(m)
                    if buffer_size in ["1000 م", "الكل"]:
                        folium.Circle([lat, lon], radius=1000,
                            color="orange", weight=1.5, fill=True,
                            fill_opacity=0.12,
                            popup="نطاق 1000م — " + n).add_to(m)
                    if buffer_size in ["2000 م", "الكل"]:
                        folium.Circle([lat, lon], radius=2000,
                            color="yellow", weight=1, fill=True,
                            fill_opacity=0.08,
                            popup="نطاق 2000م — " + n).add_to(m)
                
                # ===== لون العلامة حسب DRASTIC =====
                # red > orange > yellow > green
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(
                        f"<b>{n}</b><br>"
                        f"النشاط: {d.get('activity', 'N/A')}<br>"
                        f"<span style='color:red;'>DRASTIC: {ix} - {rk['level']}</span><br>"
                        f"سيانيد: {'✅' if d.get('cyanide_use') else '❌'}<br>"
                        f"زئبق: {'✅' if d.get('mercury_use') else '❌'}",
                        max_width=250),
                    tooltip=f"{n} (DRASTIC: {ix})",
                    icon=folium.Icon(
                        color=rk["color"] if rk["color"] != "yellow" else "beige",
                        icon="exclamation-triangle", prefix="fa"),
                ).add_to(m)

        # طبقة الخرطوم
        if show_khartoum:
            for n, d in KHARTOUM_LOCALITIES.items():
                folium.CircleMarker(
                    [d["coords"][1], d["coords"][0]],
                    radius=8, color="purple", weight=2,
                    fill=True, fill_opacity=0.5,
                    popup="<b>" + n + "</b><br>عدد الآبار: " +
                          str(d.get("wells_sampled", "N/A")),
                    tooltip=n).add_to(m)

        # Mouse Position
        folium.plugins.MousePosition(
            position="bottomright", separator=" | ",
            prefix="الإحداثيات:",
            lat_formatter="function(num) {return L.Util.formatNum(num, 4) + '°N';}",
            lng_formatter="function(num) {return L.Util.formatNum(num, 4) + '°E';}",
        ).add_to(m)

        st_folium(m, width=None, height=map_height, key="main_map_v36")

        st.markdown("---")
        st.markdown("### 🗺️ دليل الخريطة")
        leg1, leg2, leg3, leg4 = st.columns(4)
        with leg1:
            st.markdown("""
            **العلامات:**
            - 🔵 آبار NARIS
            - 🟢 آبار دارفور
            - 🟣 محليات الخرطوم
            """)
        with leg2:
            st.markdown("""
            **ألوان DRASTIC للتعدين:**
            - 🟢 منخفض (< 100)
            - 🟡 متوسط (100-139)
            - 🟠 مرتفع (140-179)
            - 🔴 مرتفع جدا (≥ 180)
            """)
        with leg3:
            st.markdown("""
            **نطاقات التأثير:**
            - 🔴 500 م — خطر مباشر
            - 🟠 1000 م — انتشار
            - 🟡 2000 م — تأثير عام
            """)
        with leg4:
            st.markdown("""
            **إرشادات:**
            - انقر على أي علامة للتفاصيل
            - استخدم الماوس للتكبير
            - الإحداثيات أسفل يمين
            """)

        st.markdown("---")
        st.markdown("### 📊 إحصائيات الخريطة")
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("آبار NARIS", len(NARIS_WELLS))
        s2.metric("آبار دارفور", len(DARFUR_WELLS))
        s3.metric("مواقع تعدين", len(KNOWN_MINING_SITES))
        s4.metric("محليات", len(KHARTOUM_LOCALITIES))
    else:
        st.warning("⚠️ ملف data_sources.py غير متوفر.")


# ============ TAB 6: الدقة ============
with tabs[5]:
    st.header("الدقة الإحصائية")
    sample = pd.DataFrame({"name": ["A", "B", "C", "D"],
        "drastic_index": [150, 80, 130, 165],
        "actual_status": [1, 0, 0, 1]})
    st.download_button("نموذج",
        data=sample.to_csv(index=False).encode("utf-8-sig"),
        file_name="accuracy_template.csv", mime="text/csv")
    f2 = st.file_uploader("ارفع:", type=["csv", "xlsx"], key="acc")
    if f2:
        try:
            df = pd.read_csv(f2) if f2.name.endswith(".csv") else pd.read_excel(f2)
            if "drastic_index" in df.columns and "actual_status" in df.columns:
                preds = [1 if float(v) >= 140 else 0 for v in df["drastic_index"]]
                actuals = [int(v) for v in df["actual_status"]]
                tp = sum(1 for p, a in zip(preds, actuals) if p == 1 and a == 1)
                tn = sum(1 for p, a in zip(preds, actuals) if p == 0 and a == 0)
                fp = sum(1 for p, a in zip(preds, actuals) if p == 1 and a == 0)
                fn = sum(1 for p, a in zip(preds, actuals) if p == 0 and a == 1)
                total = tp + tn + fp + fn
                acc = (tp + tn) / total * 100 if total > 0 else 0
                prec = (tp / (tp + fp) * 100) if (tp + fp) > 0 else 0
                rec = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0
                spec = (tn / (tn + fp) * 100) if (tn + fp) > 0 else 0
                f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0
                po = (tp + tn) / total if total > 0 else 0
                pe = ((tp + fp) * (tp + fn) + (tn + fn) * (tn + fp)) / (total ** 2) if total > 0 else 0
                kappa = ((po - pe) / (1 - pe)) if (1 - pe) > 0 else 0

                a1, a2, a3, a4 = st.columns(4)
                a1.metric("Accuracy", str(round(acc, 2)) + " %")
                a2.metric("Recall", str(round(rec, 2)) + " %")
                a3.metric("Precision", str(round(prec, 2)) + " %")
                a4.metric("F1", str(round(f1, 2)) + " %")
                b1, b2, b3, b4 = st.columns(4)
                b1.metric("Kappa", round(kappa, 4))
                b2.metric("Specificity", str(round(spec, 2)) + " %")
                b3.metric("Total", total)
                b4.metric("TP/TN", str(tp) + "/" + str(tn))
                st.dataframe(pd.DataFrame({
                    "Contaminated": [tp, fn], "Clean": [fp, tn]},
                    index=["Pred Cont", "Pred Clean"]))
            else:
                st.error("Need: drastic_index, actual_status")
        except Exception as e:
            st.error("خطأ: " + str(e))


# ============ TAB 7: الحساسية ============
with tabs[6]:
    st.header("تحليل الحساسية")
    if "ci" in st.session_state:
        st.info("الموقع: " + st.session_state["cs"] +
                " | المؤشر: " + str(st.session_state["ci"]))
        variation = st.slider("نسبة التغيير (%):", 5, 30, 10, 5) / 100.0

        # استخدام القيم الفيزيائية
        result = sensitivity_analysis(st.session_state["cv"], variation)

        st.success("الأكثر تأثيراً: " + str(result["most_sensitive"]))
        st.metric("المؤشر الأساسي", result["base_index"])

        for p in result["parameters"]:
            pdd = result["parameters"][p]
            wt = {"D": 5, "R": 4, "A": 3, "S": 2, "T": 1, "I": 5, "C": 3}[p]
            with st.expander(p + " — وزن " + str(wt) +
                             " (تأثير: " + str(pdd["sensitivity"]) + "%)"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("القيمة الأصلية", pdd["original_phys"])
                c2.metric("القيمة المعدلة", pdd["modified_phys"])
                c3.metric("التصنيف الأصلي", pdd["original_rating"])
                c4.metric("التصنيف الجديد", pdd["new_rating"])
                st.metric("المؤشر الجديد", pdd["new_index"],
                          delta=str(pdd["change"]))

        chart = pd.DataFrame({
            "المعامل": list(result["parameters"].keys()),
            "الحساسية": [result["parameters"][p]["sensitivity"]
                        for p in result["parameters"]]}).set_index("المعامل")
        st.bar_chart(chart)
    else:
        st.warning("افتح تبويب المدخلات أولا")


# ============ TAB 8: المقارنة ============
with tabs[7]:
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

        A_name_a = sda.get("aquifer", "massive_sandstone")
        S_name_a = sda.get("soil", "sand")
        I_name_a = sda.get("vadose", "sand_gravel")
        A_name_b = sdb.get("aquifer", "massive_sandstone")
        S_name_b = sdb.get("soil", "sand")
        I_name_b = sdb.get("vadose", "sand_gravel")

        Dra = get_d_rating(da); Rra = get_r_rating(ra)
        Ara = get_a_rating(A_name_a); Sra = get_s_rating(S_name_a)
        Tra = get_t_rating(ta); Ira = get_i_rating(I_name_a)
        Cra = get_c_rating(ca)
        idxa = calc_index(Dra, Rra, Ara, Sra, Tra, Ira, Cra)

        Drb = get_d_rating(db_); Rrb = get_r_rating(rb)
        Arb = get_a_rating(A_name_b); Srb = get_s_rating(S_name_b)
        Trb = get_t_rating(tb); Irb = get_i_rating(I_name_b)
        Crb = get_c_rating(cb)
        idxb = calc_index(Drb, Rrb, Arb, Srb, Trb, Irb, Crb)

        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric(sa, str(idxa) + "/230")
        m2.metric("الفرق", str(abs(idxa - idxb)))
        m3.metric(sb, str(idxb) + "/230")
        st.dataframe(pd.DataFrame({
            "المعامل": ["D", "R", "A", "S", "T", "I", "C"],
            sa: [Dra, Rra, Ara, Sra, Tra, Ira, Cra],
            sb: [Drb, Rrb, Arb, Srb, Trb, Irb, Crb]}),
            use_container_width=True)
    else:
        st.warning("data_sources غير متوفر")


# ============ TAB 9: السمية ============
with tabs[8]:
    st.header("تحليل الزئبق والسيانيد")
    if "ci" in st.session_state:
        ci = st.session_state["ci"]
        cs = st.session_state["cs"]
        st.info("الموقع: " + cs + " | المؤشر: " + str(ci))
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**الزئبق (Hg)**")
            hgw = st.number_input("Hg مياه (mg/L):", 0.0, 10.0, 0.05,
                                   0.001, key="hgw", format="%.4f")
            hgs = st.number_input("Hg تربة (mg/kg):", 0.0, 100.0, 0.5,
                                   0.1, key="hgs")
        with c2:
            st.markdown("**السيانيد (CN)**")
            cnw = st.number_input("CN مياه (mg/L):", 0.0, 10.0, 0.10,
                                   0.01, key="cnw", format="%.4f")
            cns = st.number_input("CN تربة (mg/kg):", 0.0, 100.0, 5.0,
                                   0.5, key="cns")

        if st.button("تحليل", type="primary", key="analyze"):
            hg = analyze_mercury(hgw, hgs)
            cn = analyze_cyanide(cnw, cns)
            tox = weighted_toxicity(hgw, hgs, cnw, cns)
            alerts = generate_alerts(ci, hg, cn, tox)
            st.session_state["hg_r"] = hg
            st.session_state["cn_r"] = cn
            st.session_state["tox_result"] = tox
            st.session_state["alerts_r"] = alerts

        if "tox_result" in st.session_state:
            hg = st.session_state["hg_r"]
            cn = st.session_state["cn_r"]
            tox = st.session_state["tox_result"]
            alerts = st.session_state["alerts_r"]

            st.markdown("---")
            st.subheader("Hg")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("مياه", str(hg["water"]["value"]) + " mg/L",
                          "الحد: " + str(hg["water"]["limit"]))
                if hg["water"]["status"] == "safe": st.success("آمن")
                else: st.error("تجاوز " + str(hg["water"]["ratio"]) + "x")
            with c2:
                st.metric("تربة", str(hg["soil"]["value"]) + " mg/kg",
                          "الحد: " + str(hg["soil"]["limit"]))
                if hg["soil"]["status"] == "safe": st.success("آمن")
                else: st.error("تجاوز " + str(hg["soil"]["ratio"]) + "x")

            st.markdown("---")
            st.subheader("CN")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("مياه", str(cn["water"]["value"]) + " mg/L",
                          "الحد: " + str(cn["water"]["limit"]))
                if cn["water"]["status"] == "safe": st.success("آمن")
                else: st.error("تجاوز " + str(cn["water"]["ratio"]) + "x")
            with c2:
                st.metric("تربة", str(cn["soil"]["value"]) + " mg/kg",
                          "الحد: " + str(cn["soil"]["limit"]))
                if cn["soil"]["status"] == "safe": st.success("آمن")
                else: st.error("تجاوز " + str(cn["soil"]["ratio"]) + "x")

            st.markdown("---")
            st.subheader("مؤشر السمية")
            c1, c2, c3 = st.columns(3)
            c1.metric("المؤشر", tox["index"])
            c2.metric("التصنيف", tox["category"])
            c3.metric("الإجراء", tox["action"])

            st.markdown("---")
            st.subheader("التنبيهات")
            if alerts:
                for a in alerts:
                    st.warning(a["icon"] + " " + a["msg"] +
                               " | **" + a["act"] + "**")
            else:
                st.success("لا تنبيهات")
    else:
        st.warning("افتح تبويب المدخلات أولا")


# ============ TAB 10: التاريخ ============
with tabs[9]:
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
        st.markdown("---")
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 تصدير CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="history.csv", mime="text/csv")
        if st.button("مسح الكل", key="clr"):
            st.session_state["history"] = []
            st.rerun()


# ============ TAB 11: GIS ============
with tabs[10]:
    st.header("🌍 تصدير GIS")
    source = st.radio("المصدر:",
                      ["المواقع المدمجة (تقييم محسوب)",
                       "سجل التقييمات"],
                      key="gis_src_v36")
    sites = []
    if source == "المواقع المدمجة (تقييم محسوب)" and DS_OK:
        sites = get_preset_sites_with_drastic(preset)
        st.success("📌 " + str(len(sites)) + " موقع (مع مؤشر DRASTIC محسوب)")
    elif source == "سجل التقييمات":
        df_h = get_history_df()
        if not df_h.empty:
            for _, row in df_h.iterrows():
                try:
                    sites.append({
                        "name": row.get("الموقع", ""),
                        "lat": float(row.get("lat", 0)),
                        "lon": float(row.get("lon", 0)),
                        "index": int(float(row.get("المؤشر", 0))),
                        "level": row.get("المستوى", "")})
                except Exception:
                    continue
            st.success("📌 " + str(len(sites)) + " تقييم")

    if sites:
        preview_df = pd.DataFrame(sites)[["name", "lat", "lon",
                                            "index", "level"]]
        preview_df.columns = ["الموقع", "خط العرض", "خط الطول",
                              "المؤشر", "المستوى"]
        st.dataframe(preview_df, use_container_width=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button("📄 GeoJSON",
                data=sites_to_geojson(sites).encode("utf-8"),
                file_name="drastic_sites.geojson",
                mime="application/geo+json",
                use_container_width=True)
        with c2:
            st.download_button("🌍 KML",
                data=sites_to_kml(sites).encode("utf-8"),
                file_name="drastic_sites.kml",
                mime="application/vnd.google-earth.kml+xml",
                use_container_width=True)
        with c3:
            st.download_button("📊 CSV",
                data=preview_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="drastic_sites.csv", mime="text/csv",
                use_container_width=True)


# ============ TAB 12: Monte Carlo ============
with tabs[11]:
    st.header("🎲 محاكاة Monte Carlo")
    if "ci" in st.session_state:
        st.info("الموقع: " + st.session_state["cs"] +
                " | المؤشر الأساسي: " + str(st.session_state["ci"]))

        st.markdown("---")
        st.markdown("""
        **ملاحظة فنية:** تستخدم المحاكاة توزيعات احتمالية واقعية:
        - **Log-Normal**: للتوصيلية الهيدروليكية (K) والتغذية (R)
        - **Normal**: للعمق (D) والميل (T)
        - **Discrete**: للتصنيفات القيمية (A, S, I)
        """)

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
            st.markdown("---")
            st.subheader("النتائج")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("المتوسط", mc["mean"])
            c2.metric("الانحراف المعياري", mc["std"])
            c3.metric("الأدنى", mc["min"])
            c4.metric("الأعلى", mc["max"])

            st.markdown("---")
            st.subheader("فترات الثقة")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("CI 90%",
                          str(mc["ci_90"][0]) + " - " + str(mc["ci_90"][1]))
            with c2:
                st.metric("CI 50%",
                          str(mc["ci_50"][0]) + " - " + str(mc["ci_50"][1]))

            st.markdown("---")
            st.subheader("احتمالات التجاوز")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("احتمال > 140", str(mc["prob_over_140"]) + " %")
            with c2:
                st.metric("احتمال > 180", str(mc["prob_over_180"]) + " %")

            st.markdown("---")
            st.subheader("المئينات")
            pct_df = pd.DataFrame({
                "المئين": ["P5", "P25", "P50", "P75", "P95"],
                "المؤشر": [mc["p5"], mc["p25"], mc["p50"],
                          mc["p75"], mc["p95"]]}).set_index("المئين")
            st.dataframe(pct_df)
            st.bar_chart(pct_df)

            # رسم بياني للتوزيع
            st.markdown("---")
            st.subheader("التوزيع الاحتمالي")
            try:
                hist, edges = np.histogram(mc["samples"], bins=30)
                hist_df = pd.DataFrame({
                    "المؤشر": [int((edges[i] + edges[i+1]) / 2)
                              for i in range(len(hist))],
                    "التكرار": hist
                }).set_index("المؤشر")
                st.bar_chart(hist_df)
            except Exception:
                pass

            st.markdown("---")
            if mc["prob_over_140"] > 50:
                st.error("⚠️ احتمال مرتفع تجاوز 140 — خطر")
            elif mc["prob_over_140"] > 20:
                st.warning("⚠️ احتمال متوسط")
            else:
                st.success("✅ احتمال منخفض")

            if mc["prob_over_180"] > 10:
                st.error("🚨 احتمال مرتفع بالوصول لخطر داهم")
    else:
        st.warning("افتح تبويب المدخلات أولا")


st.markdown("---")
st.caption("2026 جامعة الخرطوم - نظام التعدين السوداني v36.0 - "
           "مع تصحيحات فنية (Darcy velocity, numpy Monte Carlo, "
           "physical sensitivity analysis)")
