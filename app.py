"""
نظام التعدين السوداني v52.0
=====================================
مع DRASTIC-P في التقييم الجماعي
"""
import streamlit as st
import subprocess
import os
import sys
import shutil
import stat
import zipfile
import io
import folium
from streamlit_folium import st_folium
import pandas as pd
import numpy as np
import datetime
import requests
import json
from datetime import timedelta
from pathlib import Path

try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False

st.set_page_config(
    page_title="نظام التعدين السوداني",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# ============ CSS ============
# ============================================================
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: 'Segoe UI', 'Tahoma', 'Arial', sans-serif;
        font-size: 15px;
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        padding: 10px 24px;
        border: none;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #5c2c16 0%, #c19a6b 100%);
        color: white;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px; flex-wrap: wrap;
        background-color: #faf8f3;
        padding: 8px;
        border-radius: 12px;
        border: 1px solid #e0d4b8;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 16px;
        font-size: 0.95em;
        font-weight: 600;
        background-color: transparent;
        color: #5c2c16;
    }
    .stTabs [aria-selected="true"] {
        background-color: #5c2c16 !important;
        color: white !important;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f9f5ec 100%);
        border: 2px solid #d4af37;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 3px 10px rgba(212, 175, 55, 0.12);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f5eedc 0%, #faf8f3 100%);
        border-right: 3px solid #c19a6b;
    }
    .header-container {
        background: linear-gradient(135deg, #5c2c16 0%, #c19a6b 100%);
        padding: 28px 24px;
        border-radius: 16px;
        margin-bottom: 24px;
        color: white;
        text-align: center;
        box-shadow: 0 8px 24px rgba(92, 44, 22, 0.35);
    }
    .header-title { font-size: 2.1em; font-weight: 700; margin: 0; }
    .header-subtitle { font-size: 1.05em; opacity: 0.95; margin: 6px 0 0 0; }
    .header-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.2);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85em;
        margin-top: 10px;
    }
    .section-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 16px 0 12px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #f0e6d2;
    }
    .section-header h3 { color: #5c2c16; margin: 0; font-size: 1.25em; }
    .info-card {
        background: #faf8f3;
        border: 1px solid #e0d4b8;
        border-radius: 10px;
        padding: 16px;
        margin: 10px 0;
    }
    .info-card-title {
        color: #5c2c16;
        font-weight: 700;
        margin-bottom: 8px;
        font-size: 1.05em;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    @media (max-width: 768px) {
        .header-title { font-size: 1.5em !important; }
        .header-subtitle { font-size: 0.9em !important; }
        .header-container { padding: 18px 14px !important; }
        [data-testid="stHorizontalBlock"] { flex-direction: column !important; }
        [data-testid="stHorizontalBlock"] > div { width: 100% !important; margin-bottom: 8px; }
        .stTabs [data-baseweb="tab"] { padding: 8px 12px; font-size: 0.82em; }
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# ============ MODFLOW setup ============
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
            response = requests.get(MODFLOW_URL, timeout=180, stream=True)
            if response.status_code != 200:
                return f"download_failed_{response.status_code}"
            zip_data = io.BytesIO(response.content)
            with zipfile.ZipFile(zip_data, 'r') as zf:
                mf6_file = None
                for name in zf.namelist():
                    if name.endswith("mf6") and not name.endswith("/"):
                        mf6_file = name
                        break
                if not mf6_file:
                    return "mf6_not_in_zip"
                zf.extract(mf6_file, MODFLOW_DIR)
                extracted_path = os.path.join(MODFLOW_DIR, mf6_file)
                if extracted_path != mf6_path:
                    shutil.move(extracted_path, mf6_path)
        os.chmod(mf6_path, os.stat(mf6_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        os.environ["PATH"] = MODFLOW_DIR + os.pathsep + os.environ.get("PATH", "")
        if shutil.which("mf6"):
            return "installed"
        return "installed_but_not_in_path"
    except Exception as e:
        return f"error: {str(e)[:100]}"


_modflow_status = setup_modflow()
if os.path.exists(MODFLOW_DIR):
    os.environ["PATH"] = MODFLOW_DIR + os.pathsep + os.environ.get("PATH", "")


# ============================================================
# ============ Imports ============
# ============================================================
try:
    from data_sources import (
        STATES_DATABASE, get_preset_locations_for_app, get_data_summary,
        get_sites_by_state, get_site_data, get_all_sites_as_dataframe,
        add_new_site, get_states_list, get_sites_list,
        KNOWN_MINING_SITES, NARIS_WELLS, DARFUR_WELLS, KHARTOUM_LOCALITIES)
    DS_OK = True
except ImportError:
    DS_OK = False

try:
    from modflow_engine import (
        is_modflow_available, build_and_run_model,
        estimate_travel_time_modflow)
    MODFLOW_OK = True
except ImportError:
    MODFLOW_OK = False

try:
    from hydro_data import (
        HYDRAULIC_CONDUCTIVITY, TRANSMISSIVITY,
        STORAGE_COEFFICIENT, EFFECTIVE_POROSITY,
        RECHARGE, CALIBRATION, GEOLOGICAL_LAYERS,
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
        calculate_dynamic_risk)
    ADV_OK = True
except ImportError:
    ADV_OK = False


# ============================================================
# ============ Dictionaries ============
# ============================================================
AQUIFER_AR = {
    "massive_shale": "صخر طيني ضخم",
    "metamorphic_igneous": "صخور متحولة/نارية",
    "weathered_metamorphic_igneous": "صخور متحولة/نارية متآكلة",
    "thin_bedded_sequences": "تتابعات رقيقة الطبقات",
    "massive_sandstone": "حجر رملي ضخم",
    "massive_limestone": "حجر جيري ضخم",
    "sand_and_gravel": "رمل وحصى",
    "basalt": "بازلت",
    "karst_limestone": "حجر جيري كارستي"
}

SOIL_AR = {
    "thin_or_absent": "رقيقة أو معدومة",
    "gravel": "حصى", "sand": "رمل", "peat": "خث",
    "shrinking_aggregated_clay": "طين متقلص متكتل",
    "sandy_loam": "طين رملي", "loam": "طين طميي",
    "silty_loam": "طمي غريني", "clay_loam": "طين غريني",
    "muck": "طين عضوي", "nonshrinking_clay": "طين غير متقلص"
}

VADOSE_AR = {
    "confining_layer": "طبقة كتيمة", "silt_clay": "غرين وطين",
    "shale": "صخر طيني", "metamorphic_igneous": "صخور متحولة/نارية",
    "limestone": "حجر جيري", "sandstone": "حجر رملي",
    "sand_gravel_silt_clay": "رمل وحصى وغرين وطين",
    "sand_gravel": "رمل وحصى", "basalt": "بازلت",
    "karst_limestone": "حجر جيري كارستي"
}

LEVEL_AR = {
    "منخفض": "🟢 منخفض", "متوسط": "🟡 متوسط",
    "مرتفع": "🟠 مرتفع", "مرتفع جدا": "🔴 مرتفع جداً"
}


# ============================================================
# ============ DRASTIC functions ============
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
# ============ DRASTIC-P (core) ============
# ============================================================
def calc_drastic_p(base_drastic, cn_water, hg_water,
                    distance_m=100.0, seepage=1.0, bio_acc=1.0,
                    alpha=0.50, beta=0.50):
    """DRASTIC-P = DRASTIC × (1 + α×CRI + β×MRI)"""
    CN_LIMIT = 0.05
    HG_LIMIT = 0.0007

    cn_ratio = cn_water / CN_LIMIT if CN_LIMIT > 0 else 0
    d_factor = max(0.1, min(1.0, 100.0 / max(1, distance_m)))
    s_factor = max(0.1, min(1.0, seepage))
    cri = (cn_ratio * 0.5) * d_factor * s_factor

    hg_ratio = hg_water / HG_LIMIT if HG_LIMIT > 0 else 0
    mri = (hg_ratio * 0.6) * bio_acc

    modifier = 1.0 + (alpha * cri) + (beta * mri)
    drastic_p = min(230, base_drastic * modifier)

    if drastic_p >= 180:
        level, color = "مرتفع جدا", "red"
    elif drastic_p >= 140:
        level, color = "مرتفع", "orange"
    elif drastic_p >= 100:
        level, color = "متوسط", "yellow"
    else:
        level, color = "منخفض", "green"

    return {
        "base_drastic": base_drastic, "cri": round(cri, 3),
        "mri": round(mri, 3), "cn_ratio": round(cn_ratio, 2),
        "hg_ratio": round(hg_ratio, 2), "d_factor": round(d_factor, 3),
        "s_factor": round(s_factor, 3), "bio_acc": bio_acc,
        "modifier": round(modifier, 3),
        "drastic_p": round(drastic_p, 1),
        "increase_pct": round(((drastic_p - base_drastic) / base_drastic * 100)
                              if base_drastic > 0 else 0, 1),
        "level": level, "color": color,
        "cn_limit": CN_LIMIT, "hg_limit": HG_LIMIT
    }


# ============================================================
# ============ Sensitivity & Monte Carlo ============
# ============================================================
def sensitivity_analysis(pv, variation=0.10):
    D = float(pv.get("depth", 15.0))
    R = float(pv.get("recharge", 100.0))
    A = str(pv.get("aquifer", "massive_sandstone"))
    S = str(pv.get("soil", "sand"))
    T = float(pv.get("slope", 4.0))
    I = str(pv.get("vadose", "sand_gravel"))
    C = float(pv.get("conductivity", 5.0))

    def ci(d, r, a, s, t, i, c):
        return calc_index(get_d_rating(d), get_r_rating(r), get_a_rating(a),
                          get_s_rating(s), get_t_rating(t), get_i_rating(i),
                          get_c_rating(c))

    base = ci(D, R, A, S, T, I, C)
    res = {}
    D_m = max(0.5, min(100.0, D * (1 + variation)))
    ni = ci(D_m, R, A, S, T, I, C)
    res["D"] = {"original_phys": D, "modified_phys": round(D_m, 2),
                "new_index": ni, "change": ni - base,
                "sensitivity": round(abs(ni - base) / base * 100, 3)}
    R_m = max(0.0, min(400.0, R * (1 + variation)))
    ni = ci(D, R_m, A, S, T, I, C)
    res["R"] = {"original_phys": R, "modified_phys": round(R_m, 2),
                "new_index": ni, "change": ni - base,
                "sensitivity": round(abs(ni - base) / base * 100, 3)}
    for p, br, w in [("A", get_a_rating(A), 3), ("S", get_s_rating(S), 2),
                     ("I", get_i_rating(I), 5)]:
        nr = max(1, min(10, br + 1))
        ni = base - br * w + nr * w
        res[p] = {"original_phys": "rating", "modified_phys": "rating+1",
                  "new_index": ni, "change": ni - base,
                  "sensitivity": round(abs(ni - base) / base * 100, 3)}
    T_m = max(0.0, min(30.0, T * (1 + variation)))
    ni = ci(D, R, A, S, T_m, I, C)
    res["T"] = {"original_phys": T, "modified_phys": round(T_m, 2),
                "new_index": ni, "change": ni - base,
                "sensitivity": round(abs(ni - base) / base * 100, 3)}
    C_m = max(0.01, min(100.0, C * (1 + variation)))
    ni = ci(D, R, A, S, T, I, C_m)
    res["C"] = {"original_phys": C, "modified_phys": round(C_m, 2),
                "new_index": ni, "change": ni - base,
                "sensitivity": round(abs(ni - base) / base * 100, 3)}
    sr = dict(sorted(res.items(),
                     key=lambda x: x[1]["sensitivity"], reverse=True))
    return {"base_index": base, "parameters": sr,
            "most_sensitive": list(sr.keys())[0] if sr else None}


def monte_carlo_analysis(pv, n_iter=1000, variation=0.15):
    np.random.seed(42)
    D = float(pv.get("depth", 15.0))
    R = float(pv.get("recharge", 100.0))
    A_b = get_a_rating(str(pv.get("aquifer", "massive_sandstone")))
    S_b = get_s_rating(str(pv.get("soil", "sand")))
    T = float(pv.get("slope", 4.0))
    I_b = get_i_rating(str(pv.get("vadose", "sand_gravel")))
    C = float(pv.get("conductivity", 5.0))

    D_s = np.clip(np.random.normal(D, max(0.5, D * variation), n_iter), 0.5, 100.0)
    if R > 0:
        R_s = np.clip(np.random.lognormal(np.log(max(1, R)) - 0.5 * variation**2,
                                           variation, n_iter), 0.0, 400.0)
    else:
        R_s = np.zeros(n_iter)
    A_s = np.random.choice([max(1, A_b-1), A_b, min(10, A_b+1)],
                            n_iter, p=[0.15, 0.70, 0.15])
    S_s = np.random.choice([max(1, S_b-1), S_b, min(10, S_b+1)],
                            n_iter, p=[0.15, 0.70, 0.15])
    T_s = np.clip(np.random.normal(T, max(0.5, T * variation), n_iter), 0.0, 30.0)
    I_s = np.random.choice([max(1, I_b-1), I_b, min(10, I_b+1)],
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

    drastic = D_r*5 + R_r*4 + A_s*3 + S_s*2 + T_r*1 + I_s*5 + C_r*3
    results = np.sort(drastic.astype(int))

    def pct(p): return int(np.percentile(results, p))
    return {"mean": round(float(np.mean(results)), 1),
            "std": round(float(np.std(results)), 2),
            "min": int(results[0]), "max": int(results[-1]),
            "p5": pct(5), "p25": pct(25), "p50": pct(50),
            "p75": pct(75), "p95": pct(95),
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
# ============ Lists ============
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


# ============================================================
# ============ UI HEADER ============
# ============================================================
if DS_OK:
    preset = get_preset_locations_for_app()
    summary = get_data_summary()
    n_states = summary.get('total_states', 0)
    n_sites = summary.get('total_sites', 0)
else:
    preset = {}
    n_states = 0
    n_sites = 0

st.markdown(f"""
<div class="header-container">
    <div class="header-title">⛏️ نظام التعدين السوداني</div>
    <div class="header-subtitle">جامعة الخرطوم - كلية الهندسة</div>
    <div class="header-subtitle">DRASTIC + MODFLOW 6 + Monte Carlo + DRASTIC-P</div>
    <div class="header-badge">الإصدار 52.0 | {n_states} ولاية | {n_sites} موقعاً</div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# ============ SIDEBAR ============
# ============================================================
st.sidebar.markdown("## 🎛️ وضع التشغيل")
st.sidebar.markdown("---")

mode_options = ["🏠 النظام الأساسي"]
if ADV_OK:
    mode_options += ["✅ التحقق الفعلي", "🧪 DRASTIC-P", "⏳ الديناميكي"]
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
st.sidebar.markdown("### 📚 المراجع المعتمدة")
st.sidebar.caption("• EPA/600/2-87/035 (1987)")
st.sidebar.caption("• Elmedani et al. (2025)")
st.sidebar.caption("• Elkrail & Adlan (2019)")
st.sidebar.caption("• WHO Guidelines (2022)")


# ============================================================
# ============ MODE 1: النظام الأساسي ============
# ============================================================
if mode == "🏠 النظام الأساسي":
    tabs = st.tabs([
        "📍 المدخلات",
        "➕ إدخال يدوي",
        "📊 التقييم الجماعي",
        "🛡️ الحلول",
        "📄 التقرير",
        "🗺️ الخريطة",
        "📈 الحساسية",
        "☠️ السمية",
        "🌍 GIS",
        "🎲 Monte Carlo"
    ])

    # ============ TAB 0: المدخلات ============
    with tabs[0]:
        st.markdown('<div class="section-header"><h3>📍 اختيار الولاية والموقع</h3></div>',
                    unsafe_allow_html=True)

        if not DS_OK:
            st.error("❌ `data_sources.py` غير متوفر")
        else:
            c1, c2 = st.columns([1, 2])
            with c1:
                states = get_states_list()
                state = st.selectbox("**الولاية:**", states, key="state_selector")
            with c2:
                state_info = STATES_DATABASE[state]
                st.markdown(f"""
                <div class="info-card" style="margin-top:28px;">
                    <div style="font-size:0.9em; color:#5c2c16;">
                        ℹ️ {state_info['description']}<br>
                        <span style="font-size:0.85em; color:#666;">
                        المصدر: {state_info['source']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown('<div class="section-header"><h3>📌 الموقع</h3></div>',
                        unsafe_allow_html=True)

            sites = get_sites_list(state)
            site_key = st.selectbox("**الموقع:**", sites, key="site_selector")
            site_data = get_site_data(state, site_key)

            c1, c2, c3 = st.columns(3)
            c1.metric("النشاط", site_data.get("activity", "N/A"))
            c2.metric("الموسم", site_data.get("season", "N/A"))
            status = "🔴 ملوث" if site_data["actual_contaminated"] == 1 else "🟢 نظيف"
            c3.metric("الحالة", status)

            st.markdown(f"""
            <div class="info-card">
                <div class="info-card-title">📍 الإحداثيات والوصف</div>
                <div>الإحداثيات: <b>{site_data['coords'][0]}, {site_data['coords'][1]}</b></div>
                <div>الوصف: <b>{site_data.get('name_ar', site_key)}</b></div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="section-header"><h3>💧 القيم الهيدروجيولوجية</h3></div>',
                        unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.metric("D - عمق المياه", f"{site_data['depth_m']} م")
                st.metric("R - التغذية", f"{site_data['recharge_mm']} مم/سنة")
                st.metric("T - الميل", f"{site_data['slope_pct']} %")
                st.metric("C - التوصيلية", f"{site_data['conductivity']} م/يوم")
            with c2:
                st.metric("A - الوسط المائي",
                          AQUIFER_AR.get(site_data['aquifer'], site_data['aquifer']))
                st.metric("S - التربة",
                          SOIL_AR.get(site_data['soil'], site_data['soil']))
                st.metric("I - نطاق التهوية",
                          VADOSE_AR.get(site_data['vadose'], site_data['vadose']))
                st.metric("θ - المسامية", "0.25")

            st.markdown('<div class="section-header"><h3>🧪 قيم السيانيد والزئبق</h3></div>',
                        unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            c1.metric("CN - سيانيد", f"{site_data['cn_water_mg_l']} mg/L")
            c2.metric("Hg - زئبق", f"{site_data['hg_water_mg_l']} mg/L")
            st.caption("**الحدود السودانية:** CN = 0.05 mg/L | Hg = 0.0007 mg/L")

            try:
                D_r = get_d_rating(site_data['depth_m'])
                R_r = get_r_rating(site_data['recharge_mm'])
                A_r = get_a_rating(site_data['aquifer'])
                S_r = get_s_rating(site_data['soil'])
                T_r = get_t_rating(site_data['slope_pct'])
                I_r = get_i_rating(site_data['vadose'])
                C_r = get_c_rating(site_data['conductivity'])
                idx = calc_index(D_r, R_r, A_r, S_r, T_r, I_r, C_r)
                risk = classify(idx)

                st.session_state["ci"] = idx
                st.session_state["cs"] = f"{state} - {site_data.get('name_ar', site_key)}"
                st.session_state["cc"] = site_data['coords']
                st.session_state["cv"] = {
                    "depth": site_data['depth_m'],
                    "recharge": site_data['recharge_mm'],
                    "aquifer": site_data['aquifer'],
                    "soil": site_data['soil'],
                    "slope": site_data['slope_pct'],
                    "vadose": site_data['vadose'],
                    "conductivity": site_data['conductivity'],
                    "porosity": 0.25, "gradient": 0.01,
                    "cn_water_mg_l": site_data['cn_water_mg_l'],
                    "hg_water_mg_l": site_data['hg_water_mg_l'],
                    "actual_contaminated": site_data['actual_contaminated']
                }

                st.markdown('<div class="section-header"><h3>📊 نتائج DRASTIC</h3></div>',
                            unsafe_allow_html=True)

                x1, x2, x3, x4 = st.columns(4)
                x1.metric("D", D_r); x2.metric("R", R_r)
                x3.metric("A", A_r); x4.metric("S", S_r)
                y1, y2, y3, y4 = st.columns(4)
                y1.metric("T", T_r); y2.metric("I", I_r)
                y3.metric("C", C_r); y4.metric("θ", 0.25)

                st.markdown("---")

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
        st.markdown('<div class="section-header"><h3>➕ إضافة موقع جديد</h3></div>',
                    unsafe_allow_html=True)

        if not DS_OK:
            st.error("❌ `data_sources.py` غير متوفر")
        else:
            st.markdown("##### 📌 معلومات الموقع")
            c1, c2 = st.columns(2)
            with c1:
                new_state = st.text_input("الولاية:", value="سنار",
                                           key="new_state")
                new_site_key = st.text_input("اسم الموقع (إنجليزي):",
                                              value="New_Site",
                                              key="new_site_key")
                new_name_ar = st.text_input("الاسم بالعربية:",
                                             value="موقع جديد",
                                             key="new_name_ar")
            with c2:
                new_lat = st.number_input("خط العرض:", -90.0, 90.0,
                                           13.55, 0.01,
                                           key="new_lat", format="%.4f")
                new_lon = st.number_input("خط الطول:", -180.0, 180.0,
                                           33.60, 0.01,
                                           key="new_lon", format="%.4f")
                new_activity = st.selectbox("النشاط:",
                    ["تعدين أهلي", "زراعة", "حضري", "رعوي", "صناعي", "مرجعي"],
                    key="new_activity")

            st.markdown("##### 💧 القيم الهيدروجيولوجية")
            c1, c2 = st.columns(2)
            with c1:
                new_depth = st.number_input("D - عمق المياه (م):",
                                             0.5, 100.0, 15.0, 0.5,
                                             key="new_depth")
                new_recharge = st.number_input("R - التغذية (مم/سنة):",
                                                0.0, 400.0, 20.0, 1.0,
                                                key="new_recharge")
                new_slope = st.number_input("T - الميل (%):",
                                             0.0, 30.0, 3.0, 0.5,
                                             key="new_slope")
                new_conductivity = st.number_input("C - التوصيلية (م/يوم):",
                                                    0.01, 200.0, 3.0, 0.1,
                                                    key="new_conductivity")
            with c2:
                new_aquifer = st.selectbox("A - الوسط المائي:",
                    VALID_AQUIFERS, key="new_aquifer")
                new_soil = st.selectbox("S - التربة:",
                    VALID_SOILS, key="new_soil")
                new_vadose = st.selectbox("I - نطاق التهوية:",
                    VALID_VADOSE, key="new_vadose")

            st.markdown("##### 🧪 قيم السيانيد والزئبق")
            c1, c2 = st.columns(2)
            with c1:
                new_cn = st.number_input("CN - سيانيد (mg/L):",
                                          0.0, 10.0, 0.010, 0.001,
                                          key="new_cn", format="%.4f")
            with c2:
                new_hg = st.number_input("Hg - زئبق (mg/L):",
                                          0.0, 10.0, 0.001, 0.0001,
                                          key="new_hg", format="%.4f")

            st.markdown("##### 📊 الحالة")
            c1, c2 = st.columns(2)
            with c1:
                new_contaminated = st.selectbox("الحالة الفعلية:",
                    ["نظيف (0)", "ملوث (1)"], key="new_contaminated")
            with c2:
                new_season = st.selectbox("الموسم:",
                    ["-", "جاف", "رطب"], key="new_season")

            st.markdown("---")
            if st.button("💾 حفظ الموقع في قاعدة البيانات", type="primary"):
                if not new_state or not new_site_key:
                    st.error("❌ يجب إدخال الولاية واسم الموقع")
                else:
                    site_data = {
                        "name_ar": new_name_ar,
                        "coords": (new_lat, new_lon),
                        "depth_m": new_depth,
                        "recharge_mm": new_recharge,
                        "slope_pct": new_slope,
                        "conductivity": new_conductivity,
                        "aquifer": new_aquifer,
                        "soil": new_soil,
                        "vadose": new_vadose,
                        "cn_water_mg_l": new_cn,
                        "hg_water_mg_l": new_hg,
                        "actual_contaminated": 1 if new_contaminated == "ملوث (1)" else 0,
                        "season": new_season,
                        "activity": new_activity
                    }
                    add_new_site(new_state, new_site_key, site_data)
                    st.success(f"✅ تم حفظ **{new_name_ar}** في **{new_state}**")
                    st.rerun()

    # ============ TAB 2: التقييم الجماعي (مع DRASTIC-P) ============
    with tabs[2]:
        st.markdown('<div class="section-header"><h3>📊 التقييم الجماعي (DRASTIC + DRASTIC-P)</h3></div>',
                    unsafe_allow_html=True)
        st.markdown("ارفع ملف CSV يحتوي على **مواقع متعددة** مع **CN و Hg** لتفعيل DRASTIC-P.")

        # قالب CSV جديد مع CN و Hg
        sample_bulk = pd.DataFrame({
            "name": ["موقع 1", "موقع 2", "موقع 3", "موقع 4", "موقع 5"],
            "lat": [13.55, 13.50, 13.45, 15.45, 19.53],
            "lon": [33.60, 33.55, 33.50, 36.40, 33.32],
            "depth_m": [12.0, 15.0, 25.0, 20.0, 22.0],
            "recharge_mm": [20.0, 18.0, 10.0, 96.0, 12.0],
            "slope_pct": [3.0, 4.0, 6.0, 3.0, 3.0],
            "conductivity": [2.5, 3.0, 1.5, 30.0, 3.5],
            "aquifer": ["massive_sandstone", "sand_and_gravel",
                         "massive_shale", "sand_and_gravel", "massive_sandstone"],
            "soil": ["sand", "sandy_loam", "clay_loam", "sandy_loam", "sandy_loam"],
            "vadose": ["sand_gravel", "sandstone", "silt_clay",
                        "sand_gravel", "sand_gravel"],
            "cn_water_mg_l": [0.025, 0.200, 0.001, 0.020, 0.008],
            "hg_water_mg_l": [0.011, 0.530, 0.0001, 0.002, 0.002],
            "actual_contaminated": [1, 1, 0, 1, 0]
        })
        st.download_button(
            "📥 تحميل قالب CSV (مع DRASTIC-P)",
            data=sample_bulk.to_csv(index=False).encode("utf-8-sig"),
            file_name="bulk_template_drastic_p.csv",
            mime="text/csv")

        st.markdown("---")

        f_bulk = st.file_uploader("📤 ارفع ملف CSV أو Excel:",
                                   type=["csv", "xlsx"],
                                   key="bulk_uploader")

        if f_bulk:
            try:
                if f_bulk.name.endswith(".csv"):
                    df_bulk = pd.read_csv(f_bulk)
                else:
                    df_bulk = pd.read_excel(f_bulk)

                st.markdown("---")
                st.subheader("🔍 معاينة البيانات")
                st.dataframe(df_bulk.head(10), width="stretch")

                # التحقق من الأعمدة
                required_cols = ["depth_m", "recharge_mm", "slope_pct",
                                  "conductivity", "aquifer", "soil", "vadose"]
                missing_cols = [c for c in required_cols
                               if c not in df_bulk.columns]
                has_toxicity = ("cn_water_mg_l" in df_bulk.columns and
                                "hg_water_mg_l" in df_bulk.columns)

                if missing_cols:
                    st.error(f"❌ أعمدة مفقودة: {missing_cols}")
                else:
                    # إشعار حالة DRASTIC-P
                    if has_toxicity:
                        st.success("✅ سيتم حساب **DRASTIC-P** (بفضل وجود CN و Hg)")
                    else:
                        st.warning("⚠️ لن يتم حساب DRASTIC-P (لا توجد أعمدة CN و Hg). سيتم حساب DRASTIC فقط.")

                    # حساب DRASTIC و DRASTIC-P لكل موقع
                    results = []
                    drastic_list = []
                    drastic_p_list = []
                    actual_list = []

                    for i, row in df_bulk.iterrows():
                        try:
                            D_r = get_d_rating(float(row.get("depth_m", 15)))
                            R_r = get_r_rating(float(row.get("recharge_mm", 100)))
                            A_r = get_a_rating(str(row.get("aquifer",
                                                          "massive_sandstone")))
                            S_r = get_s_rating(str(row.get("soil", "sand")))
                            T_r = get_t_rating(float(row.get("slope_pct", 4)))
                            I_r = get_i_rating(str(row.get("vadose", "sand_gravel")))
                            C_r = get_c_rating(float(row.get("conductivity", 5)))
                            ix = calc_index(D_r, R_r, A_r, S_r, T_r, I_r, C_r)
                            rk = classify(ix)
                            drastic_list.append(ix)

                            # DRASTIC-P
                            if has_toxicity:
                                cn_w = float(row.get("cn_water_mg_l", 0.0))
                                hg_w = float(row.get("hg_water_mg_l", 0.0))
                                result = calc_drastic_p(ix, cn_w, hg_w)
                                ix_p = result["drastic_p"]
                                rk_p = {"level": result["level"]}
                                cri = result["cri"]
                                mri = result["mri"]
                                increase = result["increase_pct"]
                            else:
                                ix_p = ix
                                rk_p = rk
                                cri = 0
                                mri = 0
                                increase = 0

                            drastic_p_list.append(ix_p)

                            if "actual_contaminated" in row:
                                actual_list.append(int(row["actual_contaminated"]))

                            results.append({
                                "الموقع": row.get("name", f"موقع {i+1}"),
                                "lat": row.get("lat", 0),
                                "lon": row.get("lon", 0),
                                "DRASTIC": ix,
                                "DRASTIC-P": ix_p,
                                "الزيادة %": increase,
                                "CRI": cri,
                                "MRI": mri,
                                "المستوى": rk_p["level"],
                                "الحالة": "🔴" if ix_p >= 140 else "🟢"
                            })
                        except Exception as e:
                            results.append({
                                "الموقع": row.get("name", f"موقع {i+1}"),
                                "lat": 0, "lon": 0,
                                "DRASTIC": 0, "DRASTIC-P": 0,
                                "الزيادة %": 0, "CRI": 0, "MRI": 0,
                                "المستوى": "فشل", "الحالة": "❌"
                            })

                    df_results = pd.DataFrame(results)

                    # ===== إحصائيات =====
                    st.markdown("---")
                    st.subheader("📊 نتائج التقييم الجماعي")

                    valid = df_results[df_results["DRASTIC"] > 0]
                    if not valid.empty:
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("إجمالي المواقع", len(df_results))
                        c2.metric("متوسط DRASTIC",
                                  round(valid["DRASTIC"].mean(), 1))
                        c3.metric("متوسط DRASTIC-P",
                                  round(valid["DRASTIC-P"].mean(), 1))
                        c4.metric("مواقع خطرة (≥140)",
                                  int((valid["DRASTIC-P"] >= 140).sum()))

                    st.dataframe(df_results, width="stretch")

                    # ===== رسم بياني مقارن =====
                    if not valid.empty:
                        st.markdown("---")
                        st.subheader("📈 مقارنة DRASTIC vs DRASTIC-P")

                        chart_data = valid[["الموقع", "DRASTIC", "DRASTIC-P"]].set_index("الموقع")
                        st.bar_chart(chart_data)

                    # ===== مقاييس إحصائية =====
                    if has_toxicity and actual_list and len(actual_list) == len(df_bulk):
                        st.markdown("---")
                        st.subheader("📊 المقاييس الإحصائية")

                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("#### 🔵 DRASTIC التقليدي")
                            metrics_d = calculate_confusion_matrix(
                                drastic_list, actual_list, threshold=140)
                            st.metric("Accuracy", f"{metrics_d['accuracy']}%")
                            st.metric("Recall", f"{metrics_d['recall']}%")
                            st.metric("Kappa", metrics_d["kappa"])

                        with c2:
                            st.markdown("#### 🟢 DRASTIC-P")
                            metrics_p = calculate_confusion_matrix(
                                drastic_p_list, actual_list, threshold=140)
                            st.metric("Accuracy", f"{metrics_p['accuracy']}%")
                            st.metric("Recall", f"{metrics_p['recall']}%")
                            st.metric("Kappa", metrics_p["kappa"])

                        if metrics_p["kappa"] > metrics_d["kappa"]:
                            st.success(f"""
                            ✅ **DRASTIC-P أفضل من DRASTIC!**
                            - Kappa: {metrics_d['kappa']} → {metrics_p['kappa']}
                            - Recall: {metrics_d['recall']}% → {metrics_p['recall']}%
                            """)

                    # ===== تنزيل النتائج =====
                    st.markdown("---")
                    st.download_button(
                        "📥 تحميل النتائج (CSV)",
                        data=df_results.to_csv(index=False).encode("utf-8-sig"),
                        file_name="bulk_results_drastic_p.csv",
                        mime="text/csv",
                        width="stretch")

            except Exception as e:
                st.error(f"❌ خطأ في قراءة الملف: {e}")

    # ============ TAB 3: الحلول ============
    with tabs[3]:
        st.markdown('<div class="section-header"><h3>🛡️ محاكي الحلول</h3></div>',
                    unsafe_allow_html=True)

        if "ci" not in st.session_state:
            st.warning("⚠️ افتح تبويب **المدخلات** أولاً")
        else:
            ci = st.session_state["ci"]
            st.info(f"**الموقع:** {st.session_state['cs']} | **DRASTIC:** {ci}")

            c1, c2 = st.columns(2)
            with c1:
                h = st.checkbox("HDPE Liner")
                tr = st.checkbox("Cyanide Treatment")
            with c2:
                mo = st.checkbox("Monitoring Wells")

            if h or tr or mo:
                r = mitigate(ci, h, tr, mo)
                c1, c2, c3 = st.columns(3)
                c1.metric("قبل", ci)
                c2.metric("بعد", r["mitigated_index"])
                c3.metric("التخفيض", f"{r['reduction_pct']} %")

    # ============ TAB 4: التقرير ============
    with tabs[4]:
        st.markdown('<div class="section-header"><h3>📄 توليد التقرير</h3></div>',
                    unsafe_allow_html=True)

        if "ci" not in st.session_state:
            st.warning("⚠️ افتح تبويب **المدخلات** أولاً")
        else:
            if st.button("🔄 توليد التقرير", type="primary"):
                site = st.session_state["cs"]
                coords = st.session_state["cc"]
                idx = st.session_state["ci"]
                values = st.session_state["cv"]

                L = ["=" * 60,
                     "تقرير تقييم هشاشة المياه الجوفية",
                     "نظام التعدين السوداني v52.0",
                     "=" * 60, "",
                     f"التاريخ: {datetime.date.today().strftime('%Y-%m-%d')}",
                     f"الموقع: {site}",
                     f"الإحداثيات: {coords[0]}, {coords[1]}", "",
                     f"مؤشر DRASTIC: {idx} / 230", "",
                     f"CN (سيانيد): {values.get('cn_water_mg_l', 'N/A')} mg/L",
                     f"Hg (زئبق): {values.get('hg_water_mg_l', 'N/A')} mg/L", "",
                     "المراجع:",
                     "- EPA/600/2-87/035 (1987)",
                     "- Elmedani et al. (2025)",
                     "=" * 60]

                st.session_state["rep"] = "\n".join(L)

            if "rep" in st.session_state:
                st.text_area("التقرير:", st.session_state["rep"], height=400)
                st.download_button("📥 تحميل التقرير (TXT)",
                    data=st.session_state["rep"].encode("utf-8"),
                    file_name="report.txt", mime="text/plain")

    # ============ TAB 5: الخريطة ============
    with tabs[5]:
        st.markdown('<div class="section-header"><h3>🗺️ الخريطة التفاعلية</h3></div>',
                    unsafe_allow_html=True)

        if DS_OK:
            c1, c2 = st.columns(2)
            with c1:
                show_mining = st.checkbox("عرض مواقع التعدين", value=True)
                show_wells = st.checkbox("عرض الآبار", value=True)
            with c2:
                base_map = st.selectbox("الخلفية:",
                    ["عادية", "أقمار صناعية", "تضاريس"])

            tiles_options = {
                "عادية": {"tiles": "OpenStreetMap",
                           "attr": "© OpenStreetMap contributors"},
                "أقمار صناعية": {
                    "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                    "attr": "Tiles © Esri"},
                "تضاريس": {
                    "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
                    "attr": "Tiles © Esri"}}
            opt = tiles_options[base_map]
            m = folium.Map(location=[15.5, 32.5], zoom_start=6,
                           tiles=opt["tiles"], attr=opt["attr"],
                           control_scale=True)

            if show_wells:
                for n, d in NARIS_WELLS.items():
                    folium.Marker([d["coords"][1], d["coords"][0]],
                        popup=n, tooltip=n,
                        icon=folium.Icon(color="blue", icon="tint",
                                          prefix="fa")).add_to(m)
                for n, d in DARFUR_WELLS.items():
                    folium.Marker([d["coords"][1], d["coords"][0]],
                        popup=n, tooltip=n,
                        icon=folium.Icon(color="green", icon="tint",
                                          prefix="fa")).add_to(m)

            if show_mining:
                for n, d in KNOWN_MINING_SITES.items():
                    lat, lon = d["coords"][1], d["coords"][0]
                    folium.Marker([lat, lon], popup=n, tooltip=n,
                        icon=folium.Icon(color="red",
                            icon="exclamation-triangle",
                            prefix="fa")).add_to(m)

            st_folium(m, height=600, key="map_main")

    # ============ TAB 6: الحساسية ============
    with tabs[6]:
        st.markdown('<div class="section-header"><h3>📈 تحليل الحساسية</h3></div>',
                    unsafe_allow_html=True)

        if "ci" not in st.session_state:
            st.warning("⚠️ افتح تبويب **المدخلات** أولاً")
        else:
            var = st.slider("نسبة التغيير (%):", 5, 30, 10, 5) / 100.0
            r = sensitivity_analysis(st.session_state["cv"], var)
            st.success(f"🎯 الأكثر تأثيراً: **{r['most_sensitive']}**")
            st.metric("المؤشر الأساسي", r["base_index"])

    # ============ TAB 7: السمية ============
    with tabs[7]:
        st.markdown('<div class="section-header"><h3>☠️ تحليل السمية</h3></div>',
                    unsafe_allow_html=True)

        if "ci" not in st.session_state:
            st.warning("⚠️ افتح تبويب **المدخلات** أولاً")
        else:
            cv = st.session_state["cv"]
            hgw = cv.get("hg_water_mg_l", 0.011)
            cnw = cv.get("cn_water_mg_l", 0.025)

            st.info(f"**القيم:** CN = {cnw} mg/L | Hg = {hgw} mg/L")

            if st.button("🔄 تحليل السمية", type="primary"):
                st.session_state["tox_result"] = weighted_toxicity(hgw, 0.5, cnw, 5.0)

            if "tox_result" in st.session_state:
                tox = st.session_state["tox_result"]
                c1, c2, c3 = st.columns(3)
                c1.metric("المؤشر", tox["index"])
                c2.metric("التصنيف", tox["category"])
                c3.metric("الإجراء", tox["action"])

    # ============ TAB 8: GIS ============
    with tabs[8]:
        st.markdown('<div class="section-header"><h3>🌍 تصدير GIS</h3></div>',
                    unsafe_allow_html=True)

        if DS_OK:
            try:
                df_all = get_all_sites_as_dataframe()
                st.dataframe(df_all, width="stretch")
                st.download_button("📊 تحميل البيانات (CSV)",
                    data=df_all.to_csv(index=False).encode("utf-8-sig"),
                    file_name="sudan_sites.csv",
                    mime="text/csv",
                    width="stretch")
            except Exception as e:
                st.error(f"خطأ: {e}")

    # ============ TAB 9: Monte Carlo ============
    with tabs[9]:
        st.markdown('<div class="section-header"><h3>🎲 محاكاة Monte Carlo</h3></div>',
                    unsafe_allow_html=True)

        if "ci" not in st.session_state:
            st.warning("⚠️ افتح تبويب **المدخلات** أولاً")
        else:
            c1, c2 = st.columns(2)
            with c1:
                n_iter = st.slider("عدد المحاكاات:", 100, 5000, 1000, 100)
            with c2:
                var_pct = st.slider("معامل الاختلاف (%):", 5, 30, 15, 5)

            if st.button("🔄 تشغيل المحاكاة", type="primary"):
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


# ============================================================
# ============ MODE 2: Validation ============
# ============================================================
elif mode == "✅ التحقق الفعلي" and ADV_OK:
    st.markdown('<div class="section-header"><h3>✅ التحقق الفعلي من النموذج</h3></div>',
                unsafe_allow_html=True)

    if DS_OK:
        st.markdown("### 📥 توليد ملف CSV من قاعدة البيانات")

        if st.button("🔄 توليد ملف CSV", type="primary"):
            with st.spinner("جاري التوليد..."):
                st.session_state["df_all"] = get_all_sites_as_dataframe()

        if "df_all" in st.session_state:
            df_all = st.session_state["df_all"]
            st.success(f"✅ تم توليد ملف يحتوي على **{len(df_all)}** موقع")
            st.dataframe(df_all.head(10), width="stretch")
            st.download_button("📥 تحميل الملف (CSV)",
                data=df_all.to_csv(index=False).encode("utf-8-sig"),
                file_name="all_states_data.csv",
                mime="text/csv",
                width="stretch")

    st.markdown("---")
    st.markdown("### 📤 ارفع ملف CSV للتحقق")

    f = st.file_uploader("ارفع ملف CSV أو Excel:",
                          type=["csv", "xlsx"], key="val_f")

    if f:
        try:
            df = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)

            st.markdown("---")
            st.subheader("🔍 معاينة البيانات")
            st.dataframe(df.head(10), width="stretch")

            required = ["depth_m", "recharge_mm", "slope_pct",
                        "conductivity", "aquifer", "soil", "vadose",
                        "actual_contaminated"]
            missing = [c for c in required if c not in df.columns]
            has_toxicity = ("cn_water_mg_l" in df.columns and
                            "hg_water_mg_l" in df.columns)

            if missing:
                st.error(f"❌ أعمدة مفقودة: {missing}")
            else:
                drastic_list = []
                drastic_p_list = []
                actual_list = []

                for i, row in df.iterrows():
                    try:
                        D_r = get_d_rating(float(row["depth_m"]))
                        R_r = get_r_rating(float(row["recharge_mm"]))
                        A_r = get_a_rating(str(row["aquifer"]))
                        S_r = get_s_rating(str(row["soil"]))
                        T_r = get_t_rating(float(row["slope_pct"]))
                        I_r = get_i_rating(str(row["vadose"]))
                        C_r = get_c_rating(float(row["conductivity"]))
                        ix = calc_index(D_r, R_r, A_r, S_r, T_r, I_r, C_r)
                        drastic_list.append(ix)

                        if has_toxicity:
                            cn_w = float(row.get("cn_water_mg_l", 0.0))
                            hg_w = float(row.get("hg_water_mg_l", 0.0))
                            result = calc_drastic_p(ix, cn_w, hg_w)
                            drastic_p_list.append(result["drastic_p"])
                        else:
                            drastic_p_list.append(ix)

                        actual_list.append(int(row["actual_contaminated"]))
                    except Exception:
                        drastic_list.append(0)
                        drastic_p_list.append(0)
                        actual_list.append(int(row.get("actual_contaminated", 0)))

                st.markdown("---")
                st.subheader("📈 مقارنة DRASTIC vs DRASTIC-P")

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("#### 🔵 DRASTIC")
                    metrics_d = calculate_confusion_matrix(
                        drastic_list, actual_list, threshold=140)
                    st.metric("Accuracy", f"{metrics_d['accuracy']}%")
                    st.metric("Recall", f"{metrics_d['recall']}%")
                    st.metric("Kappa", metrics_d["kappa"])

                with c2:
                    st.markdown("#### 🟢 DRASTIC-P")
                    metrics_p = calculate_confusion_matrix(
                        drastic_p_list, actual_list, threshold=140)
                    st.metric("Accuracy", f"{metrics_p['accuracy']}%")
                    st.metric("Recall", f"{metrics_p['recall']}%")
                    st.metric("Kappa", metrics_p["kappa"])

                st.markdown("---")
                if metrics_p["kappa"] > metrics_d["kappa"]:
                    st.success(f"""
                    ✅ **DRASTIC-P أفضل من DRASTIC التقليدي!**
                    - Kappa: {metrics_d['kappa']} → {metrics_p['kappa']}
                    - Recall: {metrics_d['recall']}% → {metrics_p['recall']}%
                    """)

        except Exception as e:
            st.error(f"❌ خطأ في قراءة الملف: {e}")


# ============================================================
# ============ MODE 3: DRASTIC-P ============
# ============================================================
elif mode == "🧪 DRASTIC-P" and ADV_OK:
    st.markdown('<div class="section-header"><h3>🧪 DRASTIC-P</h3></div>',
                unsafe_allow_html=True)

    if "ci" not in st.session_state:
        st.warning("⚠️ افتح **النظام الأساسي** أولاً")
    else:
        st.info(f"**الموقع:** {st.session_state['cs']} | **DRASTIC:** {st.session_state['ci']}")

        cv = st.session_state["cv"]
        cn_w = cv.get("cn_water_mg_l", 0.025)
        hg_w = cv.get("hg_water_mg_l", 0.011)

        c1, c2 = st.columns(2)
        c1.metric("CN", f"{cn_w} mg/L")
        c2.metric("Hg", f"{hg_w} mg/L")

        cn_dist = st.number_input("المسافة لمصدر مياه (m):", 10.0,
                                   5000.0, 100.0, 50.0)
        cn_seep = st.slider("معدل التسرب:", 0.0, 1.0, 1.0, 0.05)

        if st.button("🧪 حساب DRASTIC-P", type="primary"):
            result = calc_drastic_p(
                st.session_state["ci"], cn_w, hg_w,
                distance_m=cn_dist, seepage=cn_seep, bio_acc=1.0)
            st.session_state["mod_result_v2"] = result

        if "mod_result_v2" in st.session_state:
            mod = st.session_state["mod_result_v2"]

            c1, c2, c3 = st.columns(3)
            c1.metric("DRASTIC", mod["base_drastic"])
            c2.metric("DRASTIC-P", mod["drastic_p"],
                      delta=f"+{mod['increase_pct']}%")
            c3.metric("المستوى", LEVEL_AR.get(mod["level"], mod["level"]))

            if mod["color"] == "red": st.error("🔴 خطر داهم")
            elif mod["color"] == "orange": st.warning("🟠 خطر مرتفع")
            elif mod["color"] == "yellow": st.info("🟡 خطر متوسط")
            else: st.success("🟢 خطر منخفض")


# ============================================================
# ============ MODE 4: Dynamic ============
# ============================================================
elif mode == "⏳ الديناميكي" and ADV_OK:
    st.markdown('<div class="section-header"><h3>⏳ التقييم الديناميكي</h3></div>',
                unsafe_allow_html=True)

    if "ci" not in st.session_state:
        st.warning("⚠️ افتح **النظام الأساسي** أولاً")
    else:
        c1, c2 = st.columns(2)
        with c1:
            years = st.slider("فترة التوقع:", 1, 50, 10, 1)
            mining = st.slider("معدل توسع التعدين:", 0.0, 0.20, 0.05, 0.01)
        with c2:
            climate = st.slider("تأثير المناخ:", -0.10, 0.05, -0.02, 0.005)
            pop = st.slider("النمو السكاني:", 0.0, 0.10, 0.03, 0.01)
        cri0 = st.slider("CRI الحالي:", 0.0, 10.0, 1.0, 0.1)
        mri0 = st.slider("MRI الحالي:", 0.0, 10.0, 0.5, 0.1)

        if st.button("⏳ تشغيل التقييم", type="primary"):
            with st.spinner("جاري الحساب..."):
                res = calculate_dynamic_risk(st.session_state["ci"], years,
                                              mining, climate, pop, cri0, mri0)
                st.session_state["dyn"] = res

        if "dyn" in st.session_state:
            res = st.session_state["dyn"]
            df = res["combined"]
            c1, c2, c3 = st.columns(3)
            c1.metric("DRASTIC", st.session_state["ci"])
            c2.metric(f"DRASTIC-P سنة {years}", res["final_modified"])
            c3.metric("المستوى النهائي",
                      LEVEL_AR.get(res["final_level"], res["final_level"]))
            st.line_chart(df.set_index("السنة")[
                ["DRASTIC", "DRASTIC-Modified", "CRI", "MRI"]])
            st.dataframe(df, width="stretch")


# ============================================================
# ============ MODE 5: MODFLOW ============
# ============================================================
elif mode == "🌊 MODFLOW" and MODFLOW_OK:
    st.markdown('<div class="section-header"><h3>🌊 محاكاة MODFLOW 6</h3></div>',
                unsafe_allow_html=True)

    mf_ok, mf_msg = is_modflow_available()
    if not mf_ok:
        st.error(f"❌ {mf_msg}")
    else:
        st.success(f"✅ {mf_msg}")

        c1, c2 = st.columns(2)
        with c1:
            nlay = st.number_input("طبقات:", 1, 5, 1)
            nrow = st.number_input("صفوف:", 5, 50, 20)
            ncol = st.number_input("أعمدة:", 5, 50, 20)
            delr = st.number_input("عرض الخلية (m):", 50.0, 5000.0, 500.0, 50.0)
        with c2:
            delc = st.number_input("ارتفاع الخلية (m):", 50.0, 5000.0, 500.0, 50.0)
            top = st.number_input("منسوب السطح (m):", 100.0, 2000.0, 350.0, 10.0)
            botm = st.number_input("القاعدة (m):", 0.0, 1000.0, 250.0, 10.0)
            k_val = st.number_input("K (m/day):", 0.01, 500.0, 3.5, 0.1)
            rech = st.number_input("التغذية (mm/year):", 0.0, 500.0, 15.0, 1.0)

        if st.button("🚀 تشغيل MODFLOW", type="primary"):
            progress = st.progress(0, text="⏳ بدء العملية...")
            try:
                progress.progress(30, text="🏗️ بناء النموذج...")
                ws = f"/tmp/mf_ws_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                progress.progress(50, text="⚙️ تشغيل MODFLOW 6...")

                res = build_and_run_model(
                    workspace=ws, nlay=int(nlay), nrow=int(nrow),
                    ncol=int(ncol), delr=float(delr), delc=float(delc),
                    top=float(top), botm=float(botm), k_value=float(k_val),
                    recharge_mm=float(rech))
                st.session_state["mf_res"] = res
                progress.progress(100, text="✅ اكتمل!")
                import time
                time.sleep(0.5)
                progress.empty()
            except Exception as e:
                progress.empty()
                st.error(f"❌ خطأ: {e}")

        if "mf_res" in st.session_state:
            res = st.session_state["mf_res"]
            if not res.get("success"):
                st.error(f"❌ {res.get('error')}")
            else:
                st.success("✅ نجح التشغيل!")
                c1, c2, c3 = st.columns(3)
                c1.metric("أدنى منسوب", f"{res['head_min']:.2f} m")
                c2.metric("أعلى منسوب", f"{res['head_max']:.2f} m")
                c3.metric("متوسط المنسوب", f"{res['head_mean']:.2f} m")

                try:
                    import plotly.express as px
                    fig = px.imshow(res["heads"],
                        labels={"x": "عمود", "y": "صف", "color": "منسوب (m)"},
                        color_continuous_scale="Viridis",
                        title="منسوب المياه الجوفية")
                    st.plotly_chart(fig, width="stretch")
                except ImportError:
                    st.dataframe(pd.DataFrame(res["heads"]), width="stretch")


# ============ FOOTER ============
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#666; padding:10px;">
    <b>نظام التعدين السوداني v52.0</b> - جامعة الخرطوم - كلية الهندسة<br>
    <span style="font-size:0.85em;">DRASTIC-P في التقييم الجماعي</span>
</div>
""", unsafe_allow_html=True)
