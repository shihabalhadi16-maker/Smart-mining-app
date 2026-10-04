"""
نظام التعدين السوداني v55.2
=====================================
جامعة الخرطوم - كلية الهندسة

الميزات:
- منافذ رفع متعددة (Sidebar + Main)
- DRASTIC-T (Toxicity-Weighted)
- عتبات قابلة للتعديل
- حقل verified للمواقع (11 موثق من 40)
- نقل الملوثات (Ogata-Banks)
- خريطة بألوان مميزة
"""
import streamlit as st
import subprocess, os, sys, shutil, stat, zipfile, io
import folium
from streamlit_folium import st_folium
import pandas as pd
import numpy as np
import datetime, requests, json
from datetime import timedelta
from pathlib import Path

try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False

st.set_page_config(
    page_title="نظام التعدين السوداني v55.2",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS
# ============================================================
st.markdown("""
<style>
    html, body, [class*="css"] { font-family: 'Segoe UI', 'Tahoma', 'Arial', sans-serif; font-size: 15px; }
    .stButton > button { border-radius: 8px; font-weight: 600; padding: 10px 24px; border: none; }
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, #5c2c16 0%, #c19a6b 100%); color: white; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; flex-wrap: wrap; background-color: #faf8f3; padding: 8px; border-radius: 12px; border: 1px solid #e0d4b8; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 10px 16px; font-size: 0.9em; font-weight: 600; background-color: transparent; color: #5c2c16; }
    .stTabs [aria-selected="true"] { background-color: #5c2c16 !important; color: white !important; }
    div[data-testid="stMetric"] { background: linear-gradient(135deg, #ffffff 0%, #f9f5ec 100%); border: 2px solid #d4af37; border-radius: 12px; padding: 16px 20px; box-shadow: 0 3px 10px rgba(212, 175, 55, 0.12); }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #f5eedc 0%, #faf8f3 100%); border-right: 3px solid #c19a6b; }
    .header-container { background: linear-gradient(135deg, #5c2c16 0%, #c19a6b 100%); padding: 28px 24px; border-radius: 16px; margin-bottom: 24px; color: white; text-align: center; box-shadow: 0 8px 24px rgba(92, 44, 22, 0.35); }
    .header-agri { background: linear-gradient(135deg, #2d5016 0%, #7cb342 100%) !important; }
    .header-title { font-size: 2.1em; font-weight: 700; margin: 0; }
    .header-subtitle { font-size: 1.05em; opacity: 0.95; margin: 6px 0 0 0; }
    .header-badge { display: inline-block; background: rgba(255, 255, 255, 0.2); padding: 4px 12px; border-radius: 20px; font-size: 0.85em; margin-top: 10px; }
    .section-header { display: flex; align-items: center; gap: 10px; margin: 16px 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid #f0e6d2; }
    .section-header h3 { color: #5c2c16; margin: 0; font-size: 1.25em; }
    .info-card { background: #faf8f3; border: 1px solid #e0d4b8; border-radius: 10px; padding: 16px; margin: 10px 0; }
    .upload-zone { background: linear-gradient(135deg, #fff9ec 0%, #f5e6c8 100%); border: 3px dashed #c19a6b; border-radius: 14px; padding: 22px; margin: 12px 0; text-align: center; }
    .upload-zone h4 { color: #5c2c16; margin: 0 0 6px 0; font-size: 1.1em; }
    .upload-zone p { color: #777; margin: 0; font-size: 0.85em; }
    .quality-box-ok { background:#e8f5e9; border-left:4px solid #4caf50; padding:10px 12px; border-radius:8px; margin:5px 0; }
    .quality-box-warn { background:#fff3e0; border-left:4px solid #ff9800; padding:10px 12px; border-radius:8px; margin:5px 0; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    @media (max-width: 768px) {
        .header-title { font-size: 1.5em !important; }
        .header-subtitle { font-size: 0.9em !important; }
        .header-container { padding: 18px 14px !important; }
        [data-testid="stHorizontalBlock"] { flex-direction: column !important; }
        [data-testid="stHorizontalBlock"] > div { width: 100% !important; margin-bottom: 8px; }
        .stTabs [data-baseweb="tab"] { padding: 8px 12px; font-size: 0.8em; }
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# MODFLOW Setup
# ============================================================
MODFLOW_URL = "https://github.com/MODFLOW-ORG/modflow6/releases/download/6.4.4/mf6.4.4_linux.zip"
MODFLOW_DIR = "/tmp/modflow6"

@st.cache_resource(show_spinner=False)
def setup_modflow():
    try:
        Path(MODFLOW_DIR).mkdir(parents=True, exist_ok=True)
        mf6_path = os.path.join(MODFLOW_DIR, "mf6")
        if os.path.exists(mf6_path) and os.access(mf6_path, os.X_OK):
            os.environ["PATH"] = MODFLOW_DIR + os.pathsep + os.environ.get("PATH", "")
            return "already_installed"
        with st.spinner("⏳ جاري تحميل MODFLOW 6..."):
            r = requests.get(MODFLOW_URL, timeout=180, stream=True)
            if r.status_code != 200:
                return f"download_failed_{r.status_code}"
            with zipfile.ZipFile(io.BytesIO(r.content), 'r') as zf:
                mf6_file = None
                for name in zf.namelist():
                    if name.endswith("mf6") and not name.endswith("/"):
                        mf6_file = name
                        break
                if not mf6_file:
                    return "mf6_not_in_zip"
                zf.extract(mf6_file, MODFLOW_DIR)
                ex = os.path.join(MODFLOW_DIR, mf6_file)
                if ex != mf6_path:
                    shutil.move(ex, mf6_path)
        os.chmod(mf6_path, os.stat(mf6_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        os.environ["PATH"] = MODFLOW_DIR + os.pathsep + os.environ.get("PATH", "")
        return "installed" if shutil.which("mf6") else "installed_but_not_in_path"
    except Exception as e:
        return f"error: {str(e)[:100]}"

_modflow_status = setup_modflow()
if os.path.exists(MODFLOW_DIR):
    os.environ["PATH"] = MODFLOW_DIR + os.pathsep + os.environ.get("PATH", "")


# ============================================================
# Imports
# ============================================================
try:
    from data_sources import (
        STATES_DATABASE, AGRICULTURAL_DATA,
        get_preset_locations_for_app, get_data_summary,
        get_sites_by_state, get_site_data, get_all_sites_as_dataframe,
        add_new_site, get_states_list, get_sites_list,
        get_agricultural_data_summary, get_agri_states_list,
        get_agri_sites_list, get_agri_site_data, add_new_agri_site,
        get_all_agri_sites_as_dataframe,
        KNOWN_MINING_SITES, NARIS_WELLS, DARFUR_WELLS, KHARTOUM_LOCALITIES,
        get_verified_sites_as_dataframe,
        get_all_sites_as_dataframe_with_flag)
    DS_OK = True
except ImportError as e:
    DS_OK = False
    _ds_error = str(e)

try:
    from modflow_engine import (is_modflow_available, build_and_run_model, estimate_travel_time_modflow)
    MODFLOW_OK = True
except ImportError:
    MODFLOW_OK = False

try:
    from hydro_data import (HYDRAULIC_CONDUCTIVITY, TRANSMISSIVITY, STORAGE_COEFFICIENT,
        EFFECTIVE_POROSITY, RECHARGE, CALIBRATION, GEOLOGICAL_LAYERS,
        get_default_k, get_default_recharge, get_default_porosity)
    HYDRO_OK = True
except ImportError:
    HYDRO_OK = False

try:
    from advanced_modules import (
        calculate_confusion_matrix, analyze_validation_by_level,
        generate_validation_report,
        calculate_cyanide_risk_index, calculate_mercury_risk_index,
        calculate_modified_drastic,
        project_drastic_change, estimate_mitigation_impact,
        calculate_dynamic_risk,
        model_contaminant_transport, calculate_travel_time_to_well,
        independent_validation, generate_independent_validation_report,
        fetch_satellite_data,
        calculate_sar, calculate_na_percent, calculate_ec_quality,
        calculate_nitrate_risk_index, calculate_agricultural_drastic,
        classify_irrigation_water)
    ADV_OK = True
except ImportError:
    ADV_OK = False


# ============================================================
# Arabic Dictionaries
# ============================================================
AQUIFER_AR = {"massive_shale": "صخر طيني ضخم", "metamorphic_igneous": "صخور متحولة/نارية",
    "weathered_metamorphic_igneous": "صخور متحولة/نارية متآكلة",
    "thin_bedded_sequences": "تتابعات رقيقة الطبقات", "massive_sandstone": "حجر رملي ضخم",
    "massive_limestone": "حجر جيري ضخم", "sand_and_gravel": "رمل وحصى",
    "basalt": "بازلت", "karst_limestone": "حجر جيري كارستي"}
SOIL_AR = {"thin_or_absent": "رقيقة أو معدومة", "gravel": "حصى", "sand": "رمل", "peat": "خث",
    "shrinking_aggregated_clay": "طين متقلص متكتل", "sandy_loam": "طين رملي",
    "loam": "طين طميي", "silty_loam": "طمي غريني", "clay_loam": "طين غريني",
    "muck": "طين عضوي", "nonshrinking_clay": "طين غير متقلص"}
VADOSE_AR = {"confining_layer": "طبقة كتيمة", "silt_clay": "غرين وطين",
    "shale": "صخر طيني", "metamorphic_igneous": "صخور متحولة/نارية",
    "limestone": "حجر جيري", "sandstone": "حجر رملي",
    "sand_gravel_silt_clay": "رمل وحصى وغرين وطين", "sand_gravel": "رمل وحصى",
    "basalt": "بازلت", "karst_limestone": "حجر جيري كارستي"}
LEVEL_AR = {"منخفض": "🟢 منخفض", "متوسط": "🟡 متوسط", "مرتفع": "🟠 مرتفع", "مرتفع جدا": "🔴 مرتفع جداً"}


# ============================================================
# DRASTIC Rating Functions
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
        "silty_loam": 4, "clay_loam": 3, "muck": 2, "nonshrinking_clay": 1}.get(s, 5)

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
    if d <= 0: raise ValueError("D>0")
    if not (0.01 < p < 0.60): raise ValueError("Porosity")
    if k <= 0: raise ValueError("K>0")
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
    return {"mitigated_index": round(m, 1), "reduction_pct": round(red, 1)}


# ============================================================
# DRASTIC-T (Toxicity-Weighted)
# ============================================================
def calc_drastic_t(base_drastic, cn_water, hg_water,
                    distance_m=100.0, seepage=1.0, bio_acc=1.0,
                    alpha=0.50, beta=0.50):
    CN_LIMIT = 0.05
    HG_LIMIT = 0.0007
    MAX_CN_SCORE = 30.0
    MAX_HG_SCORE = 30.0
    MAX_TOXICITY_BONUS = 50.0

    d_factor = max(0.1, min(1.0, 100.0 / max(1, distance_m)))
    s_factor = max(0.1, min(1.0, seepage))

    cn_ratio = cn_water / CN_LIMIT if CN_LIMIT > 0 else 0
    cri = cn_ratio * d_factor * s_factor
    cn_score = min(MAX_CN_SCORE, cri * 30.0)

    hg_ratio = hg_water / HG_LIMIT if HG_LIMIT > 0 else 0
    mri = hg_ratio * bio_acc
    hg_score = min(MAX_HG_SCORE, mri * 30.0)

    toxicity_bonus = min(MAX_TOXICITY_BONUS, alpha * cn_score + beta * hg_score)
    drastic_t = base_drastic + toxicity_bonus

    if drastic_t >= 180: level, color = "مرتفع جدا", "red"
    elif drastic_t >= 140: level, color = "مرتفع", "orange"
    elif drastic_t >= 100: level, color = "متوسط", "yellow"
    else: level, color = "منخفض", "green"

    return {"base_drastic": base_drastic, "cri": round(cri, 3), "mri": round(mri, 3),
            "cn_score": round(cn_score, 2), "hg_score": round(hg_score, 2),
            "toxicity_bonus": round(toxicity_bonus, 2),
            "drastic_t": round(drastic_t, 1), "drastic_p": round(drastic_t, 1),
            "modifier": round(1.0 + toxicity_bonus / max(base_drastic, 1), 3),
            "increase_pct": round((toxicity_bonus / base_drastic * 100) if base_drastic > 0 else 0, 1),
            "level": level, "color": color}

calc_drastic_p = calc_drastic_t


# ============================================================
# نموذج نقل الملوثات المُصحح (Ogata-Banks)
# ============================================================
def model_contaminant_transport_fixed(C0, K, porosity, gradient, distance, years,
                                        dispersivity=10.0, retardation=1.0, decay=0.0):
    try:
        from scipy import special as sp
        has_scipy = True
    except ImportError:
        has_scipy = False

    v = (K * gradient) / (porosity * retardation)
    if v <= 0:
        return {"error": "Velocity is zero or negative"}
    D = dispersivity * v
    if D <= 0:
        return {"error": "Dispersion coefficient is zero"}

    total_days = int(years * 365.25)
    times = np.linspace(1, total_days, min(200, max(10, total_days)))
    concentrations = []
    for t in times:
        if t <= 0:
            C = 0.0
        else:
            arg = (distance - v * t) / (2.0 * np.sqrt(D * t))
            if has_scipy:
                erfc_val = float(sp.erfc(arg))
            else:
                z = abs(arg)
                tt = 1.0 / (1.0 + 0.5 * z)
                erf_approx = 1 - tt * np.exp(-z*z - 1.26551223 +
                    tt * (1.00002368 + tt * (0.37409196 + tt * (0.09678418 +
                    tt * (-0.18628806 + tt * (0.27886807 + tt * (-1.13520398 +
                    tt * (1.48851587 + tt * (-0.82215223 + tt * 0.17087277)))))))))
                erfc_val = 1 - erf_approx if arg >= 0 else 1 + erf_approx
            C = (C0 / 2.0) * erfc_val
            if decay > 0:
                C *= np.exp(-decay * t)
            C = max(0.0, min(C0, C))
        concentrations.append(round(C, 6))

    df = pd.DataFrame({
        "السنة": [round(t / 365.25, 2) for t in times],
        "التركيز (mg/L)": concentrations,
        "المسافة المقطوعة (m)": [round(v * t, 1) for t in times],
        "النسبة من الحد (%)": [round(c / C0 * 100, 1) if C0 > 0 else 0 for c in concentrations]
    })

    return {"results": df, "C_final": concentrations[-1],
            "v_seepage": round(v, 6), "D_dispersion": round(D, 4),
            "t_travel_days": round(distance / v, 2),
            "t_travel_years": round(distance / v / 365.25, 3)}


# ============================================================
# Sensitivity & Monte Carlo
# ============================================================
def sensitivity_analysis(pv, variation=0.10):
    D = float(pv.get("depth", 15.0)); R = float(pv.get("recharge", 100.0))
    A = str(pv.get("aquifer", "massive_sandstone")); S = str(pv.get("soil", "sand"))
    T = float(pv.get("slope", 4.0)); I = str(pv.get("vadose", "sand_gravel"))
    C = float(pv.get("conductivity", 5.0))

    def ci(d, r, a, s, t, i, c):
        return calc_index(get_d_rating(d), get_r_rating(r), get_a_rating(a),
                          get_s_rating(s), get_t_rating(t), get_i_rating(i), get_c_rating(c))

    base = ci(D, R, A, S, T, I, C); res = {}
    D_m = max(0.5, min(100.0, D * (1 + variation))); ni = ci(D_m, R, A, S, T, I, C)
    res["D"] = {"original_phys": D, "modified_phys": round(D_m, 2), "new_index": ni,
                "change": ni - base, "sensitivity": round(abs(ni - base) / base * 100, 3)}
    R_m = max(0.0, min(400.0, R * (1 + variation))); ni = ci(D, R_m, A, S, T, I, C)
    res["R"] = {"original_phys": R, "modified_phys": round(R_m, 2), "new_index": ni,
                "change": ni - base, "sensitivity": round(abs(ni - base) / base * 100, 3)}
    for p, br, w in [("A", get_a_rating(A), 3), ("S", get_s_rating(S), 2), ("I", get_i_rating(I), 5)]:
        nr = max(1, min(10, br + 1)); ni = base - br * w + nr * w
        res[p] = {"original_phys": "rating", "modified_phys": "rating+1",
                  "new_index": ni, "change": ni - base,
                  "sensitivity": round(abs(ni - base) / base * 100, 3)}
    T_m = max(0.0, min(30.0, T * (1 + variation))); ni = ci(D, R, A, S, T_m, I, C)
    res["T"] = {"original_phys": T, "modified_phys": round(T_m, 2), "new_index": ni,
                "change": ni - base, "sensitivity": round(abs(ni - base) / base * 100, 3)}
    C_m = max(0.01, min(100.0, C * (1 + variation))); ni = ci(D, R, A, S, T, I, C_m)
    res["C"] = {"original_phys": C, "modified_phys": round(C_m, 2), "new_index": ni,
                "change": ni - base, "sensitivity": round(abs(ni - base) / base * 100, 3)}
    sr = dict(sorted(res.items(), key=lambda x: x[1]["sensitivity"], reverse=True))
    return {"base_index": base, "parameters": sr, "most_sensitive": list(sr.keys())[0] if sr else None}


def monte_carlo_analysis(pv, n_iter=1000, variation=0.15):
    np.random.seed(42)
    D = float(pv.get("depth", 15.0)); R = float(pv.get("recharge", 100.0))
    A_b = get_a_rating(str(pv.get("aquifer", "massive_sandstone")))
    S_b = get_s_rating(str(pv.get("soil", "sand")))
    T = float(pv.get("slope", 4.0)); I_b = get_i_rating(str(pv.get("vadose", "sand_gravel")))
    C = float(pv.get("conductivity", 5.0))

    D_s = np.clip(np.random.normal(D, max(0.5, D * variation), n_iter), 0.5, 100.0)
    R_s = np.clip(np.random.lognormal(np.log(max(1, R)) - 0.5 * variation**2, variation, n_iter), 0.0, 400.0) if R > 0 else np.zeros(n_iter)
    A_s = np.random.choice([max(1, A_b-1), A_b, min(10, A_b+1)], n_iter, p=[0.15, 0.70, 0.15])
    S_s = np.random.choice([max(1, S_b-1), S_b, min(10, S_b+1)], n_iter, p=[0.15, 0.70, 0.15])
    T_s = np.clip(np.random.normal(T, max(0.5, T * variation), n_iter), 0.0, 30.0)
    I_s = np.random.choice([max(1, I_b-1), I_b, min(10, I_b+1)], n_iter, p=[0.15, 0.70, 0.15])
    C_s = np.clip(np.random.lognormal(np.log(max(0.01, C)) - 0.5 * variation**2, variation, n_iter), 0.01, 100.0)

    D_r = np.select([D_s <= 1.5, D_s <= 4.6, D_s <= 9.1, D_s <= 15.2, D_s <= 22.9, D_s <= 30.5], [10, 9, 7, 5, 3, 2], default=1)
    R_r = np.select([R_s <= 50.8, R_s <= 101.6, R_s <= 177.8, R_s <= 254.0], [1, 3, 6, 8], default=9)
    T_r = np.select([T_s <= 2.0, T_s <= 6.0, T_s <= 12.0, T_s <= 18.0], [10, 9, 5, 3], default=1)
    C_r = np.select([C_s <= 4.074, C_s <= 12.222, C_s <= 28.518, C_s <= 40.740, C_s <= 81.480], [1, 2, 4, 6, 8], default=10)

    drastic = D_r*5 + R_r*4 + A_s*3 + S_s*2 + T_r*1 + I_s*5 + C_r*3
    results = np.sort(drastic.astype(int))
    def pct(p): return int(np.percentile(results, p))
    return {"mean": round(float(np.mean(results)), 1), "std": round(float(np.std(results)), 2),
            "min": int(results[0]), "max": int(results[-1]),
            "p5": pct(5), "p25": pct(25), "p50": pct(50), "p75": pct(75), "p95": pct(95),
            "ci_90": (pct(5), pct(95)), "ci_50": (pct(25), pct(75)),
            "prob_over_140": round(float(np.mean(results >= 140) * 100), 1),
            "prob_over_180": round(float(np.mean(results >= 180) * 100), 1),
            "samples": results}

def weighted_toxicity(hgw, hgs, cnw, cns):
    w = (hgw/0.006*0.40) + (hgs/1.0*0.20) + (cnw/0.07*0.30) + (cns/10.0*0.10)
    if w <= 1.0: cat, act = "آمن", "لا يتطلب تدخل"
    elif w <= 3.0: cat, act = "تحت المراقبة", "مراقبة دورية"
    elif w <= 10.0: cat, act = "خطر", "تدخل عاجل"
    else: cat, act = "خطر داهم", "إيقاف النشاط"
    return {"index": round(w, 2), "category": cat, "action": act}


# ============================================================
# Lists
# ============================================================
VALID_AQUIFERS = ["massive_shale", "metamorphic_igneous", "weathered_metamorphic_igneous",
    "thin_bedded_sequences", "massive_sandstone", "massive_limestone",
    "sand_and_gravel", "basalt", "karst_limestone"]
VALID_SOILS = ["thin_or_absent", "gravel", "sand", "peat", "shrinking_aggregated_clay",
    "sandy_loam", "loam", "silty_loam", "clay_loam", "muck", "nonshrinking_clay"]
VALID_VADOSE = ["confining_layer", "silt_clay", "shale", "metamorphic_igneous",
    "limestone", "sandstone", "sand_gravel_silt_clay", "sand_gravel", "basalt", "karst_limestone"]


# ============================================================
# حساب الإحصائيات (مع verified)
# ============================================================
if DS_OK:
    preset = get_preset_locations_for_app()
    summary = get_data_summary()
    n_states = summary.get('total_states', 0)

    try:
        _df_all = get_all_sites_as_dataframe_with_flag()
        n_sites_total = len(_df_all) if _df_all is not None else 0
        n_sites_verified = int(_df_all["verified"].sum()) if _df_all is not None else 0
    except Exception:
        n_sites_total = summary.get('total_sites', 0)
        n_sites_verified = 0

    agri_summary = get_agricultural_data_summary()
    n_agri_states = agri_summary.get('total_states', 0)

    try:
        _df_agri = get_all_agri_sites_as_dataframe()
        n_agri_sites = len(_df_agri) if _df_agri is not None else 0
    except Exception:
        n_agri_sites = agri_summary.get('total_sites', 0)
else:
    preset = {}
    n_states = n_sites_total = n_sites_verified = n_agri_states = n_agri_sites = 0


# ============================================================
# SIDEBAR — Upload Area
# ============================================================
st.sidebar.markdown("""
<div style="background: linear-gradient(135deg, #5c2c16 0%, #c19a6b 100%);
     padding: 16px; border-radius: 12px; color: white; text-align: center; margin-bottom: 16px;">
    <div style="font-size: 1.3em; font-weight: 700;">📤 منطقة رفع الملفات</div>
    <div style="font-size: 0.8em; opacity: 0.9;">ارفع ملفاتك من هنا في أي وقت</div>
</div>
""", unsafe_allow_html=True)

uploaded_val = st.sidebar.file_uploader(
    "🔵 ملف التحقق (Validation):",
    type=["csv", "xlsx"], key="uploader_validation")

uploaded_bulk = st.sidebar.file_uploader(
    "🟢 ملف التقييم الجماعي:",
    type=["csv", "xlsx"], key="uploader_bulk")

uploaded_extra = st.sidebar.file_uploader(
    "🟡 ملف إضافي (اختياري):",
    type=["csv", "xlsx"], key="uploader_extra")

if uploaded_val is not None:
    try:
        df_val_side = pd.read_csv(uploaded_val) if uploaded_val.name.endswith(".csv") else pd.read_excel(uploaded_val)
        st.session_state["df_validation"] = df_val_side
        st.sidebar.success(f"✅ ملف التحقق: {len(df_val_side)} صف")
        with st.sidebar.expander("👁️ معاينة"):
            st.dataframe(df_val_side.head(5), width="stretch")
    except Exception as e:
        st.sidebar.error(f"❌ {str(e)[:80]}")

if uploaded_bulk is not None:
    try:
        df_bulk_side = pd.read_csv(uploaded_bulk) if uploaded_bulk.name.endswith(".csv") else pd.read_excel(uploaded_bulk)
        st.session_state["df_bulk"] = df_bulk_side
        st.sidebar.success(f"✅ ملف الجماعي: {len(df_bulk_side)} صف")
    except Exception as e:
        st.sidebar.error(f"❌ {str(e)[:80]}")

if uploaded_extra is not None:
    try:
        df_extra_side = pd.read_csv(uploaded_extra) if uploaded_extra.name.endswith(".csv") else pd.read_excel(uploaded_extra)
        st.session_state["df_extra"] = df_extra_side
        st.sidebar.info(f"ℹ️ ملف إضافي: {len(df_extra_side)} صف")
    except Exception as e:
        st.sidebar.error(f"❌ {str(e)[:80]}")

if st.sidebar.button("🗑️ مسح جميع الملفات"):
    for k in ["df_validation", "df_bulk", "df_extra"]:
        st.session_state.pop(k, None)
    st.rerun()

st.sidebar.markdown("---")


# ============================================================
# SIDEBAR — Quality Summary
# ============================================================
if DS_OK:
    st.sidebar.markdown("### 📊 جودة البيانات")
    st.sidebar.markdown(f"""
    <div class="quality-box-ok">
        <div style="font-size:0.85em; color:#2e7d32;">✅ <b>موثق:</b> {n_sites_verified} موقع</div>
    </div>
    <div class="quality-box-warn">
        <div style="font-size:0.85em; color:#e65100;">ℹ️ <b>للعرض فقط:</b> {n_sites_total - n_sites_verified} موقع</div>
    </div>
    """, unsafe_allow_html=True)

st.sidebar.markdown("---")


# ============================================================
# SIDEBAR — Mode
# ============================================================
st.sidebar.markdown("## 🎛️ وضع التشغيل")

mode_options = ["🏠 النظام الأساسي (تعدين)"]
if ADV_OK:
    mode_options += ["🌾 القطاع الزراعي", "✅ التحقق الفعلي", "🚀 نقل الملوثات",
                     "🔬 التحقق المستقل", "🛰️ الأقمار الصناعية", "🧪 DRASTIC-T", "⏳ الديناميكي"]
if MODFLOW_OK:
    mode_options.append("🌊 MODFLOW")

mode = st.sidebar.radio("اختر الوضع:", mode_options, key="app_mode")
st.sidebar.markdown("---")

st.sidebar.markdown("### 🔧 حالة النظام")
status_icon = "✅" if _modflow_status in ["already_installed", "installed"] else "⚠️"
st.sidebar.info(f"{status_icon} MODFLOW: {_modflow_status}")

with st.sidebar.expander("📋 تشخيص الملفات"):
    st.write(f"**data_sources**: {'✅' if DS_OK else '❌'}")
    st.write(f"**modflow_engine**: {'✅' if MODFLOW_OK else '❌'}")
    st.write(f"**hydro_data**: {'✅' if HYDRO_OK else '❌'}")
    st.write(f"**advanced_modules**: {'✅' if ADV_OK else '❌'}")

if "ci" in st.session_state:
    st.sidebar.success(f"✅ مؤشر حالي: {st.session_state['ci']}")
else:
    st.sidebar.warning("⚠️ لم يتم حساب مؤشر")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📚 المراجع")
st.sidebar.caption("• Aller et al. (1987)")
st.sidebar.caption("• Elmedani et al. (2025)")
st.sidebar.caption("• Elkrail & Adlan (2019)")
st.sidebar.caption("• WHO (2022)")


# ============================================================
# Main Header (مع verified)
# ============================================================
st.markdown(f"""
<div class="header-container">
    <div class="header-title">⛏️ نظام التعدين السوداني</div>
    <div class="header-subtitle">جامعة الخرطوم - كلية الهندسة</div>
    <div class="header-subtitle">DRASTIC + DRASTIC-T + MODFLOW 6 + Monte Carlo</div>
    <div class="header-badge">الإصدار 55.2 | التعدين: {n_states} ولاية، {n_sites_total} موقع ({n_sites_verified} موثق) | الزراعة: {n_agri_states} ولاية، {n_agri_sites} موقع</div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# Main Upload Area
# ============================================================
with st.expander("📤 **منطقة رفع الملفات الرئيسية** — اضغط للتوسيع", expanded=False):
    st.markdown("""
    <div class="upload-zone">
        <h4>📂 ارفع ملفات البيانات هنا</h4>
        <p>يدعم ملفات CSV و Excel (XLSX)</p>
    </div>
    """, unsafe_allow_html=True)

    col_up1, col_up2, col_up3 = st.columns(3)
    with col_up1:
        st.markdown("##### 🔵 ملف التحقق")
        main_upload_val = st.file_uploader("ارفع ملف التحقق:", type=["csv", "xlsx"],
            key="main_uploader_val", label_visibility="collapsed")
        if main_upload_val is not None:
            try:
                df_mv = pd.read_csv(main_upload_val) if main_upload_val.name.endswith(".csv") else pd.read_excel(main_upload_val)
                st.session_state["df_validation"] = df_mv
                st.success(f"✅ {len(df_mv)} صف")
            except Exception as e:
                st.error(f"❌ {str(e)[:60]}")

    with col_up2:
        st.markdown("##### 🟢 ملف التقييم الجماعي")
        main_upload_bulk = st.file_uploader("ارفع ملف الجماعي:", type=["csv", "xlsx"],
            key="main_uploader_bulk", label_visibility="collapsed")
        if main_upload_bulk is not None:
            try:
                df_mb = pd.read_csv(main_upload_bulk) if main_upload_bulk.name.endswith(".csv") else pd.read_excel(main_upload_bulk)
                st.session_state["df_bulk"] = df_mb
                st.success(f"✅ {len(df_mb)} صف")
            except Exception as e:
                st.error(f"❌ {str(e)[:60]}")

    with col_up3:
        st.markdown("##### 🟡 ملف إضافي")
        main_upload_extra = st.file_uploader("ارفع ملف إضافي:", type=["csv", "xlsx"],
            key="main_uploader_extra", label_visibility="collapsed")
        if main_upload_extra is not None:
            try:
                df_me = pd.read_csv(main_upload_extra) if main_upload_extra.name.endswith(".csv") else pd.read_excel(main_upload_extra)
                st.session_state["df_extra"] = df_me
                st.info(f"ℹ️ {len(df_me)} صف")
            except Exception as e:
                st.error(f"❌ {str(e)[:60]}")

    st.markdown("---")
    st.markdown("##### 📥 تحميل قالب جاهز")
    sample_template = pd.DataFrame({
        "site_name": ["موقع 1", "موقع 2", "موقع 3"],
        "depth_m": [12.0, 15.0, 25.0], "recharge_mm": [20.0, 18.0, 10.0],
        "slope_pct": [3.0, 4.0, 6.0], "conductivity": [2.5, 3.0, 1.5],
        "aquifer": ["massive_sandstone", "sand_and_gravel", "massive_shale"],
        "soil": ["sand", "sandy_loam", "clay_loam"],
        "vadose": ["sand_gravel", "sandstone", "silt_clay"],
        "cn_water_mg_l": [0.025, 0.200, 0.001],
        "hg_water_mg_l": [0.011, 0.530, 0.0001],
        "actual_contaminated": [1, 1, 0]
    })
    st.download_button("📥 تحميل القالب (CSV)",
        data=sample_template.to_csv(index=False).encode("utf-8-sig"),
        file_name="template_sudan_mining.csv", mime="text/csv",
        use_container_width=True)

st.markdown("---")


# ============================================================
# MODE 1: النظام الأساسي
# ============================================================
if mode == "🏠 النظام الأساسي (تعدين)":
    tabs = st.tabs(["📍 المدخلات", "➕ إدخال يدوي", "📊 التقييم الجماعي",
                    "🛡️ الحلول", "📄 التقرير", "🗺️ الخريطة",
                    "📈 الحساسية", "☠️ السمية", "🌍 GIS", "🎲 Monte Carlo"])

    # ============ TAB 0: المدخلات ============
    with tabs[0]:
        st.markdown('<div class="section-header"><h3>📍 اختيار الولاية والموقع</h3></div>', unsafe_allow_html=True)
        if not DS_OK:
            st.error("❌ `data_sources.py` غير متوفر")
        else:
            c1, c2 = st.columns([1, 2])
            with c1:
                states = get_states_list()
                state = st.selectbox("**الولاية:**", states, key="state_selector")
            with c2:
                state_info = STATES_DATABASE[state]
                st.markdown(f'<div class="info-card" style="margin-top:28px;"><div style="font-size:0.9em; color:#5c2c16;">ℹ️ {state_info["description"]}<br><span style="font-size:0.85em; color:#666;">المصدر: {state_info["source"]}</span></div></div>', unsafe_allow_html=True)

            sites = get_sites_list(state)
            site_key = st.selectbox("**الموقع:**", sites, key="site_selector")
            site_data = get_site_data(state, site_key)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("النشاط", site_data.get("activity", "N/A"))
            c2.metric("الموسم", site_data.get("season", "N/A"))
            status = "🔴 ملوث" if site_data["actual_contaminated"] == 1 else "🟢 نظيف"
            c3.metric("الحالة", status)
            verified_badge = "✅ موثق" if site_data.get("verified", False) else "ℹ️ للعرض"
            c4.metric("التوثيق", verified_badge)

            st.markdown(f'<div class="info-card"><div style="font-weight:700; color:#5c2c16;">📍 الإحداثيات</div><div>الإحداثيات: <b>{site_data["coords"][0]}, {site_data["coords"][1]}</b></div></div>', unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.metric("D - عمق المياه", f"{site_data['depth_m']} م")
                st.metric("R - التغذية", f"{site_data['recharge_mm']} مم/سنة")
                st.metric("T - الميل", f"{site_data['slope_pct']} %")
                st.metric("C - التوصيلية", f"{site_data['conductivity']} م/يوم")
            with c2:
                st.metric("A - الوسط المائي", AQUIFER_AR.get(site_data['aquifer'], site_data['aquifer']))
                st.metric("S - التربة", SOIL_AR.get(site_data['soil'], site_data['soil']))
                st.metric("I - نطاق التهوية", VADOSE_AR.get(site_data['vadose'], site_data['vadose']))
                st.metric("θ - المسامية", "0.25")

            c1, c2 = st.columns(2)
            c1.metric("CN - سيانيد", f"{site_data['cn_water_mg_l']} mg/L")
            c2.metric("Hg - زئبق", f"{site_data['hg_water_mg_l']} mg/L")
            st.caption("**الحدود السودانية:** CN = 0.05 mg/L | Hg = 0.0007 mg/L")

            try:
                idx = calc_index(get_d_rating(site_data['depth_m']), get_r_rating(site_data['recharge_mm']),
                                 get_a_rating(site_data['aquifer']), get_s_rating(site_data['soil']),
                                 get_t_rating(site_data['slope_pct']), get_i_rating(site_data['vadose']),
                                 get_c_rating(site_data['conductivity']))
                risk = classify(idx)
                st.session_state["ci"] = idx
                st.session_state["cs"] = f"{state} - {site_data.get('name_ar', site_key)}"
                st.session_state["cv"] = {"depth": site_data['depth_m'], "recharge": site_data['recharge_mm'],
                    "aquifer": site_data['aquifer'], "soil": site_data['soil'], "slope": site_data['slope_pct'],
                    "vadose": site_data['vadose'], "conductivity": site_data['conductivity'],
                    "porosity": 0.25, "gradient": 0.01, "cn_water_mg_l": site_data['cn_water_mg_l'],
                    "hg_water_mg_l": site_data['hg_water_mg_l'], "actual_contaminated": site_data['actual_contaminated']}

                z1, z2, z3 = st.columns(3)
                z1.metric("مؤشر DRASTIC", f"{idx} / 230")
                z2.metric("المستوى", LEVEL_AR.get(risk["level"], risk["level"]))
                z3.metric("نسبة الخطورة", f"{round(idx/230*100, 1)}%")

                if risk["color"] == "red": st.error(f"🔴 {risk['action']}")
                elif risk["color"] == "orange": st.warning(f"🟠 {risk['action']}")
                elif risk["color"] == "yellow": st.info(f"🟡 {risk['action']}")
                else: st.success(f"🟢 {risk['action']}")
            except ValueError as e:
                st.error("خطأ: " + str(e))

    # ============ TAB 1: إدخال يدوي ============
    with tabs[1]:
        st.markdown('<div class="section-header"><h3>➕ إضافة موقع جديد</h3></div>', unsafe_allow_html=True)
        if DS_OK:
            c1, c2 = st.columns(2)
            with c1:
                new_state = st.text_input("الولاية:", value="سنار", key="new_state")
                new_site_key = st.text_input("اسم الموقع:", value="New_Site", key="new_site_key")
                new_name_ar = st.text_input("الاسم بالعربية:", value="موقع جديد", key="new_name_ar")
            with c2:
                new_lat = st.number_input("خط العرض:", -90.0, 90.0, 13.55, 0.01, key="new_lat", format="%.4f")
                new_lon = st.number_input("خط الطول:", -180.0, 180.0, 33.60, 0.01, key="new_lon", format="%.4f")
                new_activity = st.selectbox("النشاط:", ["تعدين أهلي", "زراعة", "حضري", "رعوي", "صناعي", "مرجعي"], key="new_activity")

            c1, c2 = st.columns(2)
            with c1:
                new_depth = st.number_input("D:", 0.5, 100.0, 15.0, 0.5, key="new_depth")
                new_recharge = st.number_input("R:", 0.0, 400.0, 20.0, 1.0, key="new_recharge")
                new_slope = st.number_input("T:", 0.0, 30.0, 3.0, 0.5, key="new_slope")
                new_conductivity = st.number_input("C:", 0.01, 200.0, 3.0, 0.1, key="new_conductivity")
            with c2:
                new_aquifer = st.selectbox("A:", VALID_AQUIFERS, key="new_aquifer")
                new_soil = st.selectbox("S:", VALID_SOILS, key="new_soil")
                new_vadose = st.selectbox("I:", VALID_VADOSE, key="new_vadose")

            c1, c2 = st.columns(2)
            with c1:
                new_cn = st.number_input("CN (mg/L):", 0.0, 10.0, 0.010, 0.001, key="new_cn", format="%.4f")
            with c2:
                new_hg = st.number_input("Hg (mg/L):", 0.0, 10.0, 0.001, 0.0001, key="new_hg", format="%.4f")

            c1, c2 = st.columns(2)
            with c1:
                new_contaminated = st.selectbox("الحالة:", ["نظيف (0)", "ملوث (1)"], key="new_contaminated")
            with c2:
                new_season = st.selectbox("الموسم:", ["-", "جاف", "رطب"], key="new_season")

            if st.button("💾 حفظ الموقع", type="primary"):
                if not new_state or not new_site_key:
                    st.error("❌ يجب إدخال الولاية واسم الموقع")
                else:
                    site_data = {"name_ar": new_name_ar, "coords": (new_lat, new_lon),
                        "depth_m": new_depth, "recharge_mm": new_recharge, "slope_pct": new_slope,
                        "conductivity": new_conductivity, "aquifer": new_aquifer, "soil": new_soil,
                        "vadose": new_vadose, "cn_water_mg_l": new_cn, "hg_water_mg_l": new_hg,
                        "actual_contaminated": 1 if new_contaminated == "ملوث (1)" else 0,
                        "season": new_season, "activity": new_activity, "verified": True}
                    add_new_site(new_state, new_site_key, site_data)
                    st.success(f"✅ تم حفظ **{new_name_ar}**")
                    st.rerun()

    # ============ TAB 2: التقييم الجماعي ============
    with tabs[2]:
        st.markdown('<div class="section-header"><h3>📊 التقييم الجماعي</h3></div>', unsafe_allow_html=True)
        st.info("💡 يمكنك رفع الملف من **الشريط الجانبي** أو **منطقة الرفع في الأعلى**")
        df_bulk = st.session_state.get("df_bulk", None) or st.session_state.get("df_validation", None)

        if df_bulk is None:
            st.warning("⚠️ لم يتم رفع ملف بعد")
        else:
            try:
                st.dataframe(df_bulk.head(10), width="stretch")
                required = ["depth_m", "recharge_mm", "slope_pct", "conductivity", "aquifer", "soil", "vadose"]
                missing = [c for c in required if c not in df_bulk.columns]
                has_tox = ("cn_water_mg_l" in df_bulk.columns and "hg_water_mg_l" in df_bulk.columns)

                if missing:
                    st.error(f"❌ أعمدة مفقودة: {missing}")
                else:
                    st.markdown("#### ⚙️ عتبات التصنيف")
                    c1, c2 = st.columns(2)
                    with c1:
                        th_d = st.number_input("عتبة DRASTIC:", 50, 200, 100, 10, key="bulk_th_d")
                    with c2:
                        th_dt = st.number_input("عتبة DRASTIC-T:", 50, 230, 140, 10, key="bulk_th_dt")

                    results, d_list, dp_list, actual_list = [], [], [], []
                    for i, row in df_bulk.iterrows():
                        try:
                            ix = calc_index(get_d_rating(float(row.get("depth_m", 15))),
                                            get_r_rating(float(row.get("recharge_mm", 100))),
                                            get_a_rating(str(row.get("aquifer", "massive_sandstone"))),
                                            get_s_rating(str(row.get("soil", "sand"))),
                                            get_t_rating(float(row.get("slope_pct", 4))),
                                            get_i_rating(str(row.get("vadose", "sand_gravel"))),
                                            get_c_rating(float(row.get("conductivity", 5))))
                            d_list.append(ix)
                            if has_tox:
                                cn_w = float(row.get("cn_water_mg_l", 0.0))
                                hg_w = float(row.get("hg_water_mg_l", 0.0))
                                result = calc_drastic_t(ix, cn_w, hg_w)
                                ix_t = result["drastic_t"]
                            else:
                                ix_t = ix; result = classify(ix)
                            dp_list.append(ix_t)
                            if "actual_contaminated" in row:
                                actual_list.append(int(row["actual_contaminated"]))
                            results.append({"الموقع": row.get("name", f"م{i+1}"), "DRASTIC": ix,
                                "DRASTIC-T": ix_t, "المستوى": result.get("level", "N/A"),
                                "الحالة": "🔴" if ix_t >= th_dt else "🟢"})
                        except Exception:
                            results.append({"الموقع": row.get("name", f"م{i+1}"), "DRASTIC": 0,
                                "DRASTIC-T": 0, "المستوى": "فشل", "الحالة": "❌"})

                    df_results = pd.DataFrame(results)
                    valid = df_results[df_results["DRASTIC"] > 0]
                    if not valid.empty:
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("إجمالي", len(df_results))
                        c2.metric("متوسط DRASTIC", round(valid["DRASTIC"].mean(), 1))
                        c3.metric("متوسط DRASTIC-T", round(valid["DRASTIC-T"].mean(), 1))
                        c4.metric(f"خطرة (≥{th_dt})", int((valid["DRASTIC-T"] >= th_dt).sum()))
                    st.dataframe(df_results, width="stretch")

                    if has_tox and actual_list and len(actual_list) == len(d_list):
                        st.markdown("---")
                        st.subheader("📊 المقاييس الإحصائية")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("**DRASTIC**")
                            md = calculate_confusion_matrix(d_list, actual_list, th_d)
                            st.metric("Kappa", md["kappa"]); st.metric("Recall", f"{md['recall']}%")
                            st.metric("Accuracy", f"{md.get('accuracy', 'N/A')}%")
                        with c2:
                            st.markdown("**DRASTIC-T**")
                            mp = calculate_confusion_matrix(dp_list, actual_list, th_dt)
                            st.metric("Kappa", mp["kappa"]); st.metric("Recall", f"{mp['recall']}%")
                            st.metric("Accuracy", f"{mp.get('accuracy', 'N/A')}%")

                    st.download_button("📥 تحميل النتائج (CSV)",
                        data=df_results.to_csv(index=False).encode("utf-8-sig"),
                        file_name="bulk_results.csv", mime="text/csv", width="stretch")
            except Exception as e:
                st.error(f"❌ خطأ: {e}")

    # ============ TAB 3: الحلول ============
    with tabs[3]:
        st.markdown('<div class="section-header"><h3>🛡️ الحلول</h3></div>', unsafe_allow_html=True)
        if "ci" in st.session_state:
            ci = st.session_state["ci"]
            c1, c2 = st.columns(2)
            with c1:
                h = st.checkbox("HDPE Liner"); tr = st.checkbox("Cyanide Treatment")
            with c2:
                mo = st.checkbox("Monitoring Wells")
            if h or tr or mo:
                r = mitigate(ci, h, tr, mo)
                c1, c2, c3 = st.columns(3)
                c1.metric("قبل", ci); c2.metric("بعد", r["mitigated_index"])
                c3.metric("التخفيض", f"{r['reduction_pct']}%")

    # ============ TAB 4: التقرير ============
    with tabs[4]:
        st.markdown('<div class="section-header"><h3>📄 التقرير</h3></div>', unsafe_allow_html=True)
        if "ci" in st.session_state:
            st.info(f"**الموقع:** {st.session_state['cs']}")
            st.metric("DRASTIC", st.session_state["ci"])
            st.metric("CN", st.session_state["cv"].get("cn_water_mg_l", "N/A"))
            st.metric("Hg", st.session_state["cv"].get("hg_water_mg_l", "N/A"))

    # ============ TAB 5: الخريطة (بألوان) ============
    with tabs[5]:
        st.markdown('<div class="section-header"><h3>🗺️ الخريطة التفاعلية</h3></div>', unsafe_allow_html=True)
        st.caption("🟢 أخضر: موقع موثق | 🟠 برتقالي: موقع للعرض فقط")
        
        if DS_OK:
            try:
                df_map = get_all_sites_as_dataframe_with_flag()
                m = folium.Map(location=[15.5, 32.5], zoom_start=6)
                for _, row in df_map.iterrows():
                    state = row["state"]
                    site_key = row["site_key"]
                    try:
                        coords = STATES_DATABASE[state]["sites"][site_key]["coords"]
                    except Exception:
                        continue
                    
                    verified = row.get("verified", False)
                    color = "green" if verified else "orange"
                    icon_type = "ok" if verified else "info-sign"
                    status = "✅ موثق" if verified else "ℹ️ للعرض فقط"
                    
                    popup_html = f"""
                    <div style="font-family: Arial; font-size: 12px;">
                        <b>{row['site_name']}</b><br>
                        <b>الحالة:</b> {status}<br>
                        <b>المصدر:</b> {row.get('source', 'N/A')}<br>
                        <b>CN:</b> {row.get('cn_water_mg_l', 'N/A')}<br>
                        <b>Hg:</b> {row.get('hg_water_mg_l', 'N/A')}
                    </div>
                    """
                    folium.Marker(
                        [coords[0], coords[1]],
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=f"{row['site_name']} ({status})",
                        icon=folium.Icon(color=color, icon=icon_type, prefix="glyphicon")
                    ).add_to(m)
                st_folium(m, height=600, key="map_main")
            except Exception as e:
                st.error(f"خطأ في الخريطة: {e}")

    # ============ TAB 6: الحساسية ============
    with tabs[6]:
        st.markdown('<div class="section-header"><h3>📈 الحساسية</h3></div>', unsafe_allow_html=True)
        if "ci" in st.session_state:
            r = sensitivity_analysis(st.session_state["cv"], 0.10)
            st.success(f"الأكثر تأثيراً: **{r['most_sensitive']}**")

    # ============ TAB 7: السمية ============
    with tabs[7]:
        st.markdown('<div class="section-header"><h3>☠️ السمية</h3></div>', unsafe_allow_html=True)
        if "ci" in st.session_state:
            cv = st.session_state["cv"]
            hgw = cv.get("hg_water_mg_l", 0.011); cnw = cv.get("cn_water_mg_l", 0.025)
            if st.button("تحليل", type="primary"):
                tox = weighted_toxicity(hgw, 0.5, cnw, 5.0)
                c1, c2, c3 = st.columns(3)
                c1.metric("المؤشر", tox["index"]); c2.metric("التصنيف", tox["category"])
                c3.metric("الإجراء", tox["action"])

    # ============ TAB 8: GIS (مع فلتر) ============
    with tabs[8]:
        st.markdown('<div class="section-header"><h3>🌍 GIS — قاعدة البيانات الكاملة</h3></div>', unsafe_allow_html=True)
        st.warning("⚠️ **تنبيه علمي**: بعض المواقع في هذه القائمة **مُقدَّرة** بناءً على خصائص جيولوجية عامة، وليست جميعها موثقة بأبحاث محكمة. المواقع المُعلَّمة بـ **verified = False** تُستخدم **للعرض البصري فقط**، ولا تُدخل في التحليل الإحصائي.")
        
        if DS_OK:
            try:
                df_all = get_all_sites_as_dataframe_with_flag()
                filter_mode = st.radio("عرض:", ["الكل", "الموثقة فقط", "للعرض فقط"], 
                                         horizontal=True, key="gis_filter")
                if filter_mode == "الموثقة فقط":
                    df_show = df_all[df_all["verified"] == True]
                elif filter_mode == "للعرض فقط":
                    df_show = df_all[df_all["verified"] == False]
                else:
                    df_show = df_all
                
                st.caption(f"📊 **{len(df_show)}** موقع")
                st.dataframe(df_show, width="stretch")
                st.download_button("📥 CSV", data=df_show.to_csv(index=False).encode("utf-8-sig"),
                    file_name="sites_filtered.csv", mime="text/csv")
            except Exception as e:
                st.error(f"خطأ: {e}")

    # ============ TAB 9: Monte Carlo ============
    with tabs[9]:
        st.markdown('<div class="section-header"><h3>🎲 Monte Carlo</h3></div>', unsafe_allow_html=True)
        if "ci" in st.session_state:
            n_iter = st.slider("المحاكاات:", 100, 5000, 1000, 100)
            var_pct = st.slider("الاختلاف (%):", 5, 30, 15, 5)
            if st.button("تشغيل", type="primary"):
                mc = monte_carlo_analysis(st.session_state["cv"], n_iter, var_pct / 100.0)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("المتوسط", mc["mean"]); c2.metric("الانحراف", mc["std"])
                c3.metric("CI 90%", f"{mc['ci_90'][0]}-{mc['ci_90'][1]}")
                c4.metric("P>140", f"{mc['prob_over_140']}%")


# ============================================================
# MODE 2: القطاع الزراعي
# ============================================================
elif mode == "🌾 القطاع الزراعي" and ADV_OK:
    st.markdown("""
    <div class="header-container header-agri">
        <div class="header-title">🌾 القطاع الزراعي</div>
        <div class="header-subtitle">تقييم جودة المياه الجوفية للري</div>
        <div class="header-subtitle">DRASTIC-Agri + SAR + Na% + EC + NRI</div>
    </div>
    """, unsafe_allow_html=True)

    if not DS_OK:
        st.error("❌ `data_sources.py` غير متوفر")
    else:
        try:
            agri_summary = get_agricultural_data_summary()
            st.info(f"📊 **البيانات الزراعية:** {agri_summary['total_states']} ولاية، {agri_summary['total_sites']} موقعاً")
            tabs_agri = st.tabs(["📍 اختيار الموقع", "💧 جودة مياه الري", "🌾 DRASTIC-Agri", "➕ إدخال زراعي", "📊 تصدير"])

            with tabs_agri[0]:
                st.markdown('<div class="section-header"><h3>📍 اختيار الولاية والموقع الزراعي</h3></div>', unsafe_allow_html=True)
                c1, c2 = st.columns([1, 2])
                with c1:
                    agri_states = get_agri_states_list()
                    agri_state = st.selectbox("**الولاية الزراعية:**", agri_states, key="agri_state_selector")
                with c2:
                    agri_info = AGRICULTURAL_DATA[agri_state]
                    st.markdown(f'<div class="info-card" style="margin-top:28px;"><div style="font-size:0.9em; color:#2d5016;">ℹ️ {agri_info["description"]}<br><span style="font-size:0.85em; color:#666;">المصدر: {agri_info["source"]}</span></div></div>', unsafe_allow_html=True)

                agri_sites = get_agri_sites_list(agri_state)
                agri_site_key = st.selectbox("**الموقع الزراعي:**", agri_sites, key="agri_site_selector")
                agri_site_data = get_agri_site_data(agri_state, agri_site_key)

                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                c1.metric("نوع المحصول", agri_site_data.get("crop_type", "N/A"))
                c2.metric("طريقة الري", agri_site_data.get("irrigation_method", "N/A"))
                c3.metric("الإحداثيات", f"{agri_site_data['coords'][0]:.2f}, {agri_site_data['coords'][1]:.2f}")

                st.session_state["agri_state"] = agri_state
                st.session_state["agri_site"] = agri_site_data

                try:
                    agri_idx = calc_index(get_d_rating(agri_site_data['depth_m']),
                                           get_r_rating(agri_site_data['recharge_mm']),
                                           get_a_rating(agri_site_data['aquifer']),
                                           get_s_rating(agri_site_data['soil']),
                                           get_t_rating(agri_site_data['slope_pct']),
                                           get_i_rating(agri_site_data['vadose']),
                                           get_c_rating(agri_site_data['conductivity']))
                    agri_risk = classify(agri_idx)
                    st.session_state["agri_ci"] = agri_idx

                    st.markdown("---")
                    st.subheader("📊 DRASTIC الأساسي")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("مؤشر DRASTIC", f"{agri_idx} / 230")
                    c2.metric("المستوى", LEVEL_AR.get(agri_risk["level"], agri_risk["level"]))
                    c3.metric("نسبة الخطورة", f"{round(agri_idx/230*100, 1)}%")

                    st.markdown("---")
                    st.subheader("💧 بيانات الموقع")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.metric("D", f"{agri_site_data['depth_m']} م")
                        st.metric("R", f"{agri_site_data['recharge_mm']} مم/سنة")
                        st.metric("T", f"{agri_site_data['slope_pct']} %")
                    with c2:
                        st.metric("C", f"{agri_site_data['conductivity']} م/يوم")
                        st.metric("NO3", f"{agri_site_data['no3_mg_l']} mg/L")
                        st.metric("EC", f"{agri_site_data['ec_ds_m']} dS/m")
                except Exception as e:
                    st.error(f"خطأ: {e}")

            with tabs_agri[1]:
                st.markdown('<div class="section-header"><h3>💧 جودة مياه الري</h3></div>', unsafe_allow_html=True)
                if "agri_site" not in st.session_state:
                    st.warning("⚠️ اختر موقعاً زراعياً أولاً")
                else:
                    site = st.session_state["agri_site"]
                    sar = calculate_sar(site['na_meq_l'], site['ca_meq_l'], site['mg_meq_l'])
                    na_pct = calculate_na_percent(site['na_meq_l'], site['ca_meq_l'], site['mg_meq_l'], site['k_meq_l'])
                    ec_res = calculate_ec_quality(site['ec_ds_m'])
                    overall = classify_irrigation_water(sar, na_pct, ec_res)
                    st.subheader("📊 النتائج")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("SAR", sar.get("sar", "N/A")); st.caption(sar.get("level", ""))
                    with c2:
                        st.metric("Na%", f"{na_pct.get('na_percent', 'N/A')}%"); st.caption(na_pct.get("level", ""))
                    with c3:
                        st.metric("EC", ec_res.get("ec", "N/A")); st.caption(ec_res.get("level", ""))
                    st.markdown("---")
                    st.subheader("🏆 التصنيف النهائي")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("الفئة", overall.get("class", "N/A"))
                    c2.metric("المستوى", overall.get("level", "N/A"))
                    c3.metric("التوصية", overall.get("action", "N/A"))
                    st.markdown("---")
                    st.subheader("🧪 الأيونات (meq/L)")
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Na⁺", site['na_meq_l']); c2.metric("Ca²⁺", site['ca_meq_l'])
                    c3.metric("Mg²⁺", site['mg_meq_l']); c4.metric("K⁺", site['k_meq_l'])
                    c5.metric("EC", f"{site['ec_ds_m']}")

            with tabs_agri[2]:
                st.markdown('<div class="section-header"><h3>🌾 DRASTIC-Agri</h3></div>', unsafe_allow_html=True)
                if "agri_ci" not in st.session_state:
                    st.warning("⚠️ اختر موقعاً زراعياً أولاً")
                else:
                    site = st.session_state["agri_site"]
                    base_drastic = st.session_state["agri_ci"]
                    st.info(f"**DRASTIC الأساسي:** {base_drastic}")
                    c1, c2 = st.columns(2)
                    with c1:
                        fertilizer = st.slider("استخدام الأسمدة:", 0.0, 1.0, float(site.get("fertilizer_use", 0.5)), 0.05)
                    with c2:
                        land_use = st.slider("معامل استخدام الأرض:", 0.0, 1.0, float(site.get("land_use_factor", 0.5)), 0.05)
                    alpha_agri = st.slider("α (وزن NRI):", 0.1, 1.5, 0.50, 0.05)
                    if st.button("🌾 حساب DRASTIC-Agri", type="primary"):
                        result = calculate_agricultural_drastic(base_drastic, site['no3_mg_l'],
                            fertilizer, land_use, site['depth_m'], alpha_agri)
                        st.session_state["agri_result"] = result
                    if "agri_result" in st.session_state:
                        mod = st.session_state["agri_result"]
                        st.markdown("---")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("DRASTIC", mod["base_drastic"])
                        c2.metric("DRASTIC-Agri", mod["drastic_agri"], delta=f"+{mod['increase_pct']}%")
                        c3.metric("المستوى", mod["level"])

            with tabs_agri[3]:
                st.markdown('<div class="section-header"><h3>➕ إضافة موقع زراعي جديد</h3></div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    new_agri_state = st.text_input("الولاية:", value="الجزيرة", key="new_agri_state")
                    new_agri_key = st.text_input("اسم الموقع:", value="New_Agri", key="new_agri_key")
                    new_agri_name = st.text_input("الاسم بالعربية:", value="موقع زراعي", key="new_agri_name")
                    new_agri_crop = st.text_input("نوع المحصول:", value="قمح", key="new_agri_crop")
                with c2:
                    new_agri_lat = st.number_input("خط العرض:", -90.0, 90.0, 14.40, 0.01, key="new_agri_lat", format="%.4f")
                    new_agri_lon = st.number_input("خط الطول:", -180.0, 180.0, 33.52, 0.01, key="new_agri_lon", format="%.4f")
                    new_agri_irr = st.selectbox("طريقة الري:", ["ري سطحي", "ري بالرش", "ري بالتنقيط", "ري غمر"], key="new_agri_irr")
                c1, c2 = st.columns(2)
                with c1:
                    na_depth = st.number_input("D:", 0.5, 100.0, 18.0, 0.5, key="na_depth")
                    na_recharge = st.number_input("R:", 0.0, 400.0, 20.0, 1.0, key="na_recharge")
                    na_slope = st.number_input("T:", 0.0, 30.0, 3.0, 0.5, key="na_slope")
                    na_cond = st.number_input("C:", 0.01, 200.0, 5.0, 0.1, key="na_cond")
                with c2:
                    na_aquifer = st.selectbox("A:", VALID_AQUIFERS, key="na_aquifer")
                    na_soil = st.selectbox("S:", VALID_SOILS, key="na_soil")
                    na_vadose = st.selectbox("I:", VALID_VADOSE, key="na_vadose")
                c1, c2, c3 = st.columns(3)
                with c1:
                    na_no3 = st.number_input("NO3:", 0.0, 500.0, 30.0, 1.0, key="na_no3")
                    na_na = st.number_input("Na⁺:", 0.0, 100.0, 5.0, 0.1, key="na_na")
                with c2:
                    na_ca = st.number_input("Ca²⁺:", 0.0, 100.0, 3.0, 0.1, key="na_ca")
                    na_mg = st.number_input("Mg²⁺:", 0.0, 100.0, 2.0, 0.1, key="na_mg")
                with c3:
                    na_k = st.number_input("K⁺:", 0.0, 100.0, 0.3, 0.1, key="na_k")
                    na_ec = st.number_input("EC (dS/m):", 0.0, 10.0, 0.8, 0.1, key="na_ec")
                if st.button("💾 حفظ الموقع الزراعي", type="primary"):
                    if not new_agri_state or not new_agri_key:
                        st.error("❌ يجب إدخال الولاية واسم الموقع")
                    else:
                        agri_site = {"name_ar": new_agri_name, "coords": (new_agri_lat, new_agri_lon),
                            "depth_m": na_depth, "recharge_mm": na_recharge, "slope_pct": na_slope,
                            "conductivity": na_cond, "aquifer": na_aquifer, "soil": na_soil,
                            "vadose": na_vadose, "no3_mg_l": na_no3, "na_meq_l": na_na,
                            "ca_meq_l": na_ca, "mg_meq_l": na_mg, "k_meq_l": na_k,
                            "ec_ds_m": na_ec, "crop_type": new_agri_crop, "irrigation_method": new_agri_irr}
                        add_new_agri_site(new_agri_state, new_agri_key, agri_site)
                        st.success(f"✅ تم حفظ **{new_agri_name}**")
                        st.rerun()

            with tabs_agri[4]:
                st.markdown('<div class="section-header"><h3>📊 تصدير البيانات الزراعية</h3></div>', unsafe_allow_html=True)
                df_agri = get_all_agri_sites_as_dataframe()
                st.dataframe(df_agri, width="stretch")
                st.download_button("📥 CSV", data=df_agri.to_csv(index=False).encode("utf-8-sig"),
                    file_name="agricultural_sites.csv", mime="text/csv")
        except Exception as e:
            st.error(f"❌ خطأ: {e}")


# ============================================================
# MODE 3: التحقق الفعلي
# ============================================================
elif mode == "✅ التحقق الفعلي" and ADV_OK:
    st.markdown('<div class="section-header"><h3>✅ التحقق الفعلي</h3></div>', unsafe_allow_html=True)

    # زر لتحميل المواقع الموثقة فقط
    if DS_OK:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("📥 تحميل المواقع الموثقة", type="primary"):
                try:
                    df_ver = get_verified_sites_as_dataframe()
                    st.session_state["df_validation"] = df_ver
                    st.success(f"✅ تم تحميل {len(df_ver)} موقع موثق")
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ: {e}")
        with col1:
            st.info(f"💡 **{n_sites_verified}** موقع موثق جاهز للتحليل (من أصل {n_sites_total})")

    st.markdown("---")
    st.info("💡 أو ارفع ملفاً يدوياً من **الشريط الجانبي** أو **منطقة الرفع الرئيسية**")

    df_val = st.session_state.get("df_validation", None)
    if df_val is None:
        st.warning("⚠️ لم يتم رفع ملف التحقق بعد")
    else:
        try:
            st.dataframe(df_val.head(10), width="stretch")
            required = ["depth_m", "recharge_mm", "slope_pct", "conductivity", "aquifer",
                        "soil", "vadose", "actual_contaminated"]
            missing = [c for c in required if c not in df_val.columns]

            if missing:
                st.error(f"❌ أعمدة مفقودة: {missing}")
            else:
                has_tox = ("cn_water_mg_l" in df_val.columns and "hg_water_mg_l" in df_val.columns)

                st.markdown("#### ⚙️ العتبات")
                c1, c2 = st.columns(2)
                with c1:
                    th_d = st.number_input("عتبة DRASTIC:", 50, 200, 100, 10, key="v_th_d")
                with c2:
                    th_dt = st.number_input("عتبة DRASTIC-T:", 50, 230, 140, 10, key="v_th_dt")

                d_list, dp_list, actual_list = [], [], []
                for i, row in df_val.iterrows():
                    try:
                        ix = calc_index(get_d_rating(float(row["depth_m"])),
                                        get_r_rating(float(row["recharge_mm"])),
                                        get_a_rating(str(row["aquifer"])),
                                        get_s_rating(str(row["soil"])),
                                        get_t_rating(float(row["slope_pct"])),
                                        get_i_rating(str(row["vadose"])),
                                        get_c_rating(float(row["conductivity"])))
                        d_list.append(ix)
                        if has_tox:
                            cn_w = float(row.get("cn_water_mg_l", 0.0))
                            hg_w = float(row.get("hg_water_mg_l", 0.0))
                            dp_list.append(calc_drastic_t(ix, cn_w, hg_w)["drastic_t"])
                        else:
                            dp_list.append(ix)
                        actual_list.append(int(row["actual_contaminated"]))
                    except Exception:
                        d_list.append(0); dp_list.append(0); actual_list.append(0)

                st.markdown("---")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("#### 🔵 DRASTIC")
                    md = calculate_confusion_matrix(d_list, actual_list, th_d)
                    st.metric("Kappa", md["kappa"]); st.metric("Recall", f"{md['recall']}%")
                    st.metric("Accuracy", f"{md.get('accuracy', 'N/A')}%")
                with c2:
                    st.markdown("#### 🟢 DRASTIC-T")
                    mp = calculate_confusion_matrix(dp_list, actual_list, th_dt)
                    st.metric("Kappa", mp["kappa"]); st.metric("Recall", f"{mp['recall']}%")
                    st.metric("Accuracy", f"{mp.get('accuracy', 'N/A')}%")

                if mp["kappa"] > md["kappa"]:
                    st.success(f"✅ DRASTIC-T أفضل! Kappa: {md['kappa']} → {mp['kappa']}")
                elif mp["kappa"] == md["kappa"]:
                    st.info("ℹ️ كلا النموذجين يعطيان نفس النتائج")
                else:
                    st.warning(f"⚠️ DRASTIC أفضل بـ Kappa: {md['kappa']} → {mp['kappa']}")
        except Exception as e:
            st.error(f"❌ خطأ: {e}")


# ============================================================
# MODE: نقل الملوثات
# ============================================================
elif mode == "🚀 نقل الملوثات" and ADV_OK:
    st.markdown('<div class="section-header"><h3>🚀 نمذجة نقل الملوثات (Ogata-Banks)</h3></div>', unsafe_allow_html=True)
    if "ci" not in st.session_state:
        st.warning("⚠️ افتح النظام الأساسي أولاً")
    else:
        cv = st.session_state["cv"]
        c1, c2 = st.columns(2)
        with c1:
            init_conc = st.number_input("التركيز الأولي (mg/L):", 0.001, 10.0, 0.10, 0.001, format="%.4f")
            distance = st.number_input("المسافة (m):", 10.0, 5000.0, 500.0, 50.0)
        with c2:
            gradient = st.number_input("التدرج:", 0.0001, 0.5, 0.01, 0.0001, format="%.4f")
            years = st.slider("السنوات:", 1, 30, 10, 1)
        porosity = st.slider("المسامية:", 0.02, 0.55, 0.25, 0.01)
        k_val = st.number_input("K (m/day):", 0.01, 500.0, float(cv.get("conductivity", 3.5)), 0.1)
        dispersivity = st.number_input("قابلية التشتت α (m):", 0.1, 100.0, 10.0, 0.5)

        if st.button("🚀 تشغيل (Ogata-Banks)", type="primary"):
            result = model_contaminant_transport_fixed(
                init_conc, k_val, porosity, gradient, distance, years, dispersivity)
            st.session_state["transport_result"] = result

        if "transport_result" in st.session_state:
            tr = st.session_state["transport_result"]
            if "error" in tr:
                st.error(f"❌ {tr['error']}")
            else:
                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                c1.metric("سرعة التسرب", f"{tr['v_seepage']:.6f} م/يوم")
                c2.metric("معامل التشتت D", f"{tr['D_dispersion']} m²/يوم")
                c3.metric("زمن الوصول", f"{tr['t_travel_years']} سنة")
                st.markdown("---")
                st.subheader("📊 نتائج النقل")
                st.dataframe(tr["results"], width="stretch")
                st.line_chart(tr["results"].set_index("السنة")["التركيز (mg/L)"])


# ============================================================
# MODE: التحقق المستقل
# ============================================================
elif mode == "🔬 التحقق المستقل" and ADV_OK:
    st.markdown('<div class="section-header"><h3>🔬 التحقق المستقل</h3></div>', unsafe_allow_html=True)
    df_val = st.session_state.get("df_validation", None)
    if df_val is None:
        st.warning("⚠️ ارفع ملف التحقق من الشريط الجانبي")
    else:
        try:
            df = df_val.copy()
            df["DRASTIC"] = df.apply(lambda row: calc_index(
                get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])),
                get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])),
                get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])),
                get_c_rating(float(row["conductivity"]))), axis=1)
            if st.button("🔬 تشغيل التحقق المستقل", type="primary"):
                with st.spinner("جاري التحقق..."):
                    result = independent_validation(df, "DRASTIC", "actual_contaminated", test_size=0.3)
                    st.session_state["ind_val_result"] = result
            if "ind_val_result" in st.session_state:
                r = st.session_state["ind_val_result"]
                if "error" in r:
                    st.error(r["error"])
                else:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("α الأمثل", r.get("best_alpha", "N/A"))
                    c2.metric("β الأمثل", r.get("best_beta", "N/A"))
                    c3.metric("Kappa (تدريب)", r.get("train_kappa", "N/A"))
                    c4.metric("Kappa (اختبار)", r.get("test_kappa", "N/A"))
        except Exception as e:
            st.error(f"❌ خطأ: {e}")


# ============================================================
# MODE: الأقمار الصناعية
# ============================================================
elif mode == "🛰️ الأقمار الصناعية" and ADV_OK:
    st.markdown('<div class="section-header"><h3>🛰️ بيانات الأقمار الصناعية</h3></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        lat = st.number_input("خط العرض:", -90.0, 90.0, 13.55, 0.01, format="%.4f", key="sat_lat")
    with c2:
        lon = st.number_input("خط الطول:", -180.0, 180.0, 33.60, 0.01, format="%.4f", key="sat_lon")
    years = st.slider("عدد السنوات:", 1, 10, 3, 1)
    if st.button("🛰️ جلب البيانات", type="primary"):
        with st.spinner("جاري الجلب..."):
            sat = fetch_satellite_data(lat, lon, years)
            st.session_state["sat_result"] = sat
    if "sat_result" in st.session_state:
        s = st.session_state["sat_result"]
        if s.get("rainfall_mm") is not None:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("الأمطار", f"{s['rainfall_mm']} مم")
            c2.metric("الحرارة", f"{s['temperature_c']} °C")
            c3.metric("المناخ", s["aridity"])
            c4.metric("NDVI", s["ndvi_estimated"])
            st.caption(f"المصدر: {s['source']}")
        else:
            st.error(f"⚠️ فشل: {s.get('source', '')}")


# ============================================================
# MODE: DRASTIC-T
# ============================================================
elif mode == "🧪 DRASTIC-T" and ADV_OK:
    st.markdown('<div class="section-header"><h3>🧪 DRASTIC-T (Toxicity-Weighted)</h3></div>', unsafe_allow_html=True)
    if "ci" not in st.session_state:
        st.warning("⚠️ افتح النظام الأساسي أولاً")
    else:
        cv = st.session_state["cv"]
        cn_w = cv.get("cn_water_mg_l", 0.025); hg_w = cv.get("hg_water_mg_l", 0.011)
        c1, c2 = st.columns(2)
        c1.metric("CN", f"{cn_w} mg/L"); c2.metric("Hg", f"{hg_w} mg/L")
        cn_dist = st.number_input("المسافة (m):", 10.0, 5000.0, 100.0, 50.0)
        cn_seep = st.slider("التسرب:", 0.0, 1.0, 1.0, 0.05)
        alpha_t = st.slider("α (وزن CN):", 0.0, 1.0, 0.5, 0.05)
        beta_t = st.slider("β (وزن Hg):", 0.0, 1.0, 0.5, 0.05)
        if st.button("🧪 حساب", type="primary"):
            result = calc_drastic_t(st.session_state["ci"], cn_w, hg_w, cn_dist, cn_seep, 1.0, alpha_t, beta_t)
            st.session_state["mod_result"] = result
        if "mod_result" in st.session_state:
            mod = st.session_state["mod_result"]
            c1, c2, c3 = st.columns(3)
            c1.metric("DRASTIC", mod["base_drastic"])
            c2.metric("DRASTIC-T", mod["drastic_t"], delta=f"+{mod['increase_pct']}%")
            c3.metric("المستوى", LEVEL_AR.get(mod["level"], mod["level"]))
            with st.expander("🔬 تفاصيل"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("CN Score", mod["cn_score"]); c2.metric("Hg Score", mod["hg_score"])
                c3.metric("Bonus", mod["toxicity_bonus"]); c4.metric("Modifier", mod["modifier"])


# ============================================================
# MODE: الديناميكي
# ============================================================
elif mode == "⏳ الديناميكي" and ADV_OK:
    st.markdown('<div class="section-header"><h3>⏳ التقييم الديناميكي</h3></div>', unsafe_allow_html=True)
    if "ci" not in st.session_state:
        st.warning("⚠️ افتح النظام الأساسي أولاً")
    else:
        c1, c2 = st.columns(2)
        with c1:
            years = st.slider("السنوات:", 1, 50, 10, 1)
            mining = st.slider("توسع التعدين:", 0.0, 0.20, 0.05, 0.01)
        with c2:
            climate = st.slider("المناخ:", -0.10, 0.05, -0.02, 0.005)
            pop = st.slider("السكان:", 0.0, 0.10, 0.03, 0.01)
        cri0 = st.slider("CRI الآن:", 0.0, 10.0, 1.0, 0.1)
        mri0 = st.slider("MRI الآن:", 0.0, 10.0, 0.5, 0.1)
        if st.button("⏳ تشغيل", type="primary"):
            try:
                res = calculate_dynamic_risk(st.session_state["ci"], years, mining, climate, pop, cri0, mri0)
                st.session_state["dyn"] = res
            except Exception as e:
                st.error(f"خطأ: {e}")
        if "dyn" in st.session_state:
            res = st.session_state["dyn"]
            if isinstance(res, dict) and "combined" in res:
                df = res["combined"]
                st.dataframe(df, width="stretch")


# ============================================================
# MODE: MODFLOW
# ============================================================
elif mode == "🌊 MODFLOW" and MODFLOW_OK:
    st.markdown('<div class="section-header"><h3>🌊 MODFLOW 6</h3></div>', unsafe_allow_html=True)
    mf_ok, mf_msg = is_modflow_available()
    if not mf_ok:
        st.error(f"❌ {mf_msg}")
    else:
        st.success(f"✅ {mf_msg}")
        c1, c2 = st.columns(2)
        with c1:
            nlay = st.number_input("طبقات:", 1, 5, 1); nrow = st.number_input("صفوف:", 5, 50, 20)
            ncol = st.number_input("أعمدة:", 5, 50, 20)
            delr = st.number_input("عرض الخلية (m):", 50.0, 5000.0, 500.0, 50.0)
        with c2:
            delc = st.number_input("ارتفاع الخلية (m):", 50.0, 5000.0, 500.0, 50.0)
            top = st.number_input("السطح (m):", 100.0, 2000.0, 350.0, 10.0)
            botm = st.number_input("القاعدة (m):", 0.0, 1000.0, 250.0, 10.0)
            k_val = st.number_input("K (m/day):", 0.01, 500.0, 3.5, 0.1)
            rech = st.number_input("التغذية:", 0.0, 500.0, 15.0, 1.0)
        if st.button("🚀 تشغيل", type="primary"):
            progress = st.progress(0, text="جاري التشغيل...")
            try:
                ws = f"/tmp/mf_ws_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                progress.progress(50, text="⚙️ تشغيل MODFLOW 6...")
                res = build_and_run_model(workspace=ws, nlay=int(nlay), nrow=int(nrow),
                    ncol=int(ncol), delr=float(delr), delc=float(delc), top=float(top),
                    botm=float(botm), k_value=float(k_val), recharge_mm=float(rech))
                st.session_state["mf_res"] = res
                progress.progress(100, text="✅ اكتمل!")
                import time; time.sleep(0.5); progress.empty()
            except Exception as e:
                progress.empty(); st.error(f"❌ خطأ: {e}")
        if "mf_res" in st.session_state:
            res = st.session_state["mf_res"]
            if res.get("success"):
                st.success("✅ نجح!")
                c1, c2, c3 = st.columns(3)
                c1.metric("أدنى منسوب", f"{res['head_min']:.2f} m")
                c2.metric("أعلى منسوب", f"{res['head_max']:.2f} m")
                c3.metric("متوسط", f"{res['head_mean']:.2f} m")
                try:
                    import plotly.express as px
                    fig = px.imshow(res["heads"], color_continuous_scale="Viridis", title="منسوب المياه الجوفية")
                    st.plotly_chart(fig, width="stretch")
                except ImportError:
                    st.dataframe(pd.DataFrame(res["heads"]), width="stretch")
            else:
                st.error(f"❌ {res.get('error')}")


# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#666; padding:10px;">
    <b>نظام التعدين السوداني v55.2</b> - جامعة الخرطوم<br>
    <span style="font-size:0.85em;">DRASTIC + DRASTIC-T + MODFLOW + Transport + Agricultural + Satellite</span>
</div>
""", unsafe_allow_html=True)
