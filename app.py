"""نظام التعدين السوداني v50.0 - مع 18 ولاية وإدخال يدوي"""
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

st.set_page_config(page_title="نظام التعدين السوداني",
                   page_icon="⛏️", layout="wide",
                   initial_sidebar_state="expanded")

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
        font-weight: bold;
        background: linear-gradient(135deg, #c19a6b 0%, #5c2c16 100%);
        color: white;
        border: none;
        padding: 10px 20px;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; flex-wrap: wrap; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 16px;
        font-size: 0.95em;
        font-weight: 600;
        background-color: #f5eedc;
        border: 1px solid #e0d4b8;
    }
    .stTabs [aria-selected="true"] {
        background-color: #c19a6b !important;
        color: white !important;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f9f5ec 100%);
        border: 2px solid #d4af37;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 3px 8px rgba(212, 175, 55, 0.15);
    }
    [data-testid="stSidebar"] {
        background-color: #f5eedc;
        border-right: 3px solid #c19a6b;
    }
    .header-container {
        background: linear-gradient(135deg, #5c2c16 0%, #c19a6b 100%);
        padding: 24px;
        border-radius: 16px;
        margin-bottom: 24px;
        color: white;
        text-align: center;
        box-shadow: 0 6px 20px rgba(92, 44, 22, 0.3);
    }
    .header-title {
        font-size: 2.0em;
        font-weight: bold;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    .header-subtitle { font-size: 1.05em; opacity: 0.95; margin: 8px 0 0 0; }
    .stAlert { border-radius: 10px; border-left: 5px solid; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    @media (max-width: 768px) {
        .header-title { font-size: 1.4em !important; }
        .header-subtitle { font-size: 0.85em !important; }
        .header-container { padding: 16px !important; }
        [data-testid="stHorizontalBlock"] { flex-direction: column !important; }
        [data-testid="stHorizontalBlock"] > div { width: 100% !important; margin-bottom: 10px; }
        .stTabs [data-baseweb="tab"] { padding: 6px 10px; font-size: 0.8em; }
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# ============ تثبيت MODFLOW 6 ============
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
    except requests.exceptions.Timeout:
        return "timeout"
    except requests.exceptions.ConnectionError:
        return "connection_error"
    except Exception as e:
        return f"error: {str(e)[:100]}"


_modflow_status = setup_modflow()
if os.path.exists(MODFLOW_DIR):
    os.environ["PATH"] = MODFLOW_DIR + os.pathsep + os.environ.get("PATH", "")


# ============================================================
# ============ الاستيرادات ============
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
# ============ قواميس الترجمة ============
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
    "gravel": "حصى",
    "sand": "رمل",
    "peat": "خث",
    "shrinking_aggregated_clay": "طين متقلص متكتل",
    "sandy_loam": "طين رملي",
    "loam": "طين طميي",
    "silty_loam": "طمي غريني",
    "clay_loam": "طين غريني",
    "muck": "طين عضوي",
    "nonshrinking_clay": "طين غير متقلص"
}

VADOSE_AR = {
    "confining_layer": "طبقة كتيمة",
    "silt_clay": "غرين وطين",
    "shale": "صخر طيني",
    "metamorphic_igneous": "صخور متحولة/نارية",
    "limestone": "حجر جيري",
    "sandstone": "حجر رملي",
    "sand_gravel_silt_clay": "رمل وحصى وغرين وطين",
    "sand_gravel": "رمل وحصى",
    "basalt": "بازلت",
    "karst_limestone": "حجر جيري كارستي"
}

LEVEL_AR = {
    "منخفض": "🟢 منخفض",
    "متوسط": "🟡 متوسط",
    "مرتفع": "🟠 مرتفع",
    "مرتفع جدا": "🔴 مرتفع جداً"
}


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
# ============ DRASTIC-P ============
# ============================================================
def calc_drastic_p_sennar(base_drastic, cn_water, hg_water,
                           distance_m=100.0, seepage=1.0, bio_acc=1.0,
                           alpha=0.50, beta=0.50):
    """DRASTIC-P مُعاير ببيانات سنار"""
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


def fetch_satellite(lat, lon, years=3):
    try:
        end = datetime.datetime.now().strftime('%Y-%m-%d')
        start = (datetime.datetime.now() - timedelta(days=365*years)).strftime('%Y-%m-%d')
        r1 = requests.get("https://archive-api.open-meteo.com/v1/archive",
            params={"latitude": lat, "longitude": lon,
                    "start_date": start, "end_date": end,
                    "daily": "precipitation_sum",
                    "timezone": "Africa/Khartoum"}, timeout=30)
        rain_data = r1.json().get("daily", {}).get("precipitation_sum", [])
        rv = [x for x in rain_data if x is not None]
        rain = round(sum(rv) / years, 1) if rv else None

        r2 = requests.get("https://archive-api.open-meteo.com/v1/archive",
            params={"latitude": lat, "longitude": lon,
                    "start_date": start, "end_date": end,
                    "daily": "temperature_2m_mean",
                    "timezone": "Africa/Khartoum"}, timeout=30)
        temp_data = r2.json().get("daily", {}).get("temperature_2m_mean", [])
        tv = [x for x in temp_data if x is not None]
        temp = round(sum(tv) / len(tv), 1) if tv else None

        aridity = "غير محدد"
        if rain is not None:
            if rain < 100: aridity = "صحراوي"
            elif rain < 250: aridity = "شبه جاف"
            elif rain < 500: aridity = "شبه رطب"
            else: aridity = "رطب"

        return {"rainfall_mm": rain, "temperature_c": temp,
                "aridity": aridity,
                "ndvi_estimated": round(min(0.7, max(0.05, (rain or 0) / 1000.0)), 3) if rain else None,
                "source": "ERA5 via Open-Meteo"}
    except Exception:
        return {"rainfall_mm": None, "temperature_c": None,
                "aridity": "غير محدد", "ndvi_estimated": None,
                "source": "فشل الجلب"}


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


def validate_bulk_row(row, idx):
    errors, warnings = [], []
    try:
        d = float(row.get("depth_m", 15))
        if not (0.5 <= d <= 100): errors.append("D")
    except Exception: errors.append("D")
    try:
        r = float(row.get("recharge_mm", 100))
        if not (0 <= r <= 400): errors.append("R")
    except Exception: errors.append("R")
    try:
        t = float(row.get("slope_pct", 4))
        if not (0 <= t <= 30): errors.append("T")
    except Exception: errors.append("T")
    try:
        c = float(row.get("conductivity", 5))
        if not (0.01 <= c <= 100): errors.append("C")
    except Exception: errors.append("C")
    quality = "ضعيف" if errors else "متوسط" if warnings else "ممتاز"
    return errors, warnings, quality


# ============================================================
# ============ Report ============
# ============================================================
def gen_report(site, coords, idx, values, travel=None):
    L = ["=" * 60, "تقرير تقييم هشاشة المياه الجوفية", "=" * 60, "",
         f"التاريخ: {datetime.date.today().strftime('%Y-%m-%d')}",
         f"الموقع: {site}", f"الإحداثيات: {coords[0]}, {coords[1]}", "",
         f"مؤشر DRASTIC: {idx} / 230", "",
         f"D: {values.get('depth', 'N/A')}",
         f"R: {values.get('recharge', 'N/A')}",
         f"A: {AQUIFER_AR.get(values.get('aquifer', ''), values.get('aquifer', 'N/A'))}",
         f"S: {SOIL_AR.get(values.get('soil', ''), values.get('soil', 'N/A'))}",
         f"T: {values.get('slope', 'N/A')}",
         f"I: {VADOSE_AR.get(values.get('vadose', ''), values.get('vadose', 'N/A'))}",
         f"C: {values.get('conductivity', 'N/A')}", ""]
    if travel and isinstance(travel, dict):
        L.append(f"زمن الوصول: {travel.get('years', 0)} سنة")
    L.append("")
    L.append("ملاحظة: CRI و MRI مُعايران ببيانات سنار")
    return "\n".join(L)


def gen_html(rep, site):
    return ("<!DOCTYPE html><html dir='rtl' lang='ar'><head>"
         "<meta charset='UTF-8'><title>" + site + "</title>"
         "<style>body{font-family:Arial;direction:rtl;text-align:right;"
         "padding:30px;max-width:900px;margin:auto;line-height:1.9;}"
         "pre{white-space:pre-wrap;background:#f8f9fa;padding:25px;"
         "border-radius:8px;font-family:inherit;}</style></head>"
         "<body><pre>" + rep + "</pre></body></html>")


def create_safe_map(base_map, lat=15.5, lon=32.5, zoom=6):
    tiles_options = {
        "عادية": {"tiles": "OpenStreetMap",
                   "attr": "© OpenStreetMap contributors"},
        "أقمار صناعية": {
            "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            "attr": "Tiles © Esri"},
        "تضاريس": {
            "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
            "attr": "Tiles © Esri"}}
    opt = tiles_options.get(base_map, tiles_options["عادية"])
    return folium.Map(location=[lat, lon], zoom_start=zoom,
                       tiles=opt["tiles"], attr=opt["attr"],
                       control_scale=True)


# ============================================================
# ============ UI HEADER ============
# ============================================================
_col1, _col2, _col3 = st.columns([1, 3, 1])
with _col2:
    try:
        st.image("logo.png", width=180)
    except Exception:
        st.markdown("""
        <div style='text-align:center; font-size:4em;'>⛏️</div>
        """, unsafe_allow_html=True)

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
    <div class="header-title">⛏️ نظام التعدين السوداني v50.0</div>
    <div class="header-subtitle">جامعة الخرطوم - كلية الهندسة</div>
    <div class="header-subtitle">DRASTIC + MODFLOW + DRASTIC-P + Dynamic + Validation</div>
    <div class="header-subtitle" style="font-size:0.85em; margin-top:8px;">
        قاعدة بيانات: {n_states} ولاية، {n_sites} موقعاً
    </div>
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
if _modflow_status == "already_installed":
    st.sidebar.success("✅ MODFLOW مثبت مسبقاً")
elif _modflow_status == "installed":
    st.sidebar.success("✅ تم تثبيت MODFLOW")
else:
    st.sidebar.warning(f"⚠️ {_modflow_status}")

with st.sidebar.expander("🔍 تشخيص الملفات"):
    st.write(f"data_sources: {'✅' if DS_OK else '❌'}")
    st.write(f"modflow_engine: {'✅' if MODFLOW_OK else '❌'}")
    st.write(f"hydro_data: {'✅' if HYDRO_OK else '❌'}")
    st.write(f"advanced_modules: {'✅' if ADV_OK else '❌'}")
    if DS_OK:
        st.write(f"عدد الولايات: {n_states}")
        st.write(f"عدد المواقع: {n_sites}")

if "ci" in st.session_state:
    st.sidebar.success(f"✅ مؤشر حالي: {st.session_state['ci']}")
else:
    st.sidebar.warning("⚠️ لم يتم حساب مؤشر")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📚 المراجع")
st.sidebar.caption("• EPA/600/2-87/035")
st.sidebar.caption("• Elmedani et al. (2025)")
st.sidebar.caption("• Elkrail & Adlan (2019)")
st.sidebar.caption("• Mohammed et al. (2023)")
st.sidebar.caption("• UNEP Darfur Reports")


# ============================================================
# ============ MODE 1: النظام الأساسي ============
# ============================================================
if mode == "🏠 النظام الأساسي":
    tabs = st.tabs(["📍 المدخلات", "➕ إدخال يدوي", "📊 الجماعي",
                    "🛡️ الحلول", "📄 التقرير", "🗺️ الخريطة",
                    "📈 الحساسية", "☠️ السمية", "🌍 GIS", "🎲 Monte Carlo"])

    # ============ TAB 0: المدخلات ============
    with tabs[0]:
        st.header("اختيار الولاية والموقع")

        if not DS_OK:
            st.error("❌ data_sources.py غير متوفر")
        else:
            # ===== اختيار الولاية =====
            st.markdown("---")
            st.subheader("🗺️ اختيار الولاية")

            states = get_states_list()
            state = st.selectbox("الولاية:", states, key="state_selector")

            state_info = STATES_DATABASE[state]
            st.caption(f"ℹ️ {state_info['description']} — المصدر: {state_info['source']}")

            # ===== اختيار الموقع =====
            st.markdown("---")
            st.subheader("📍 اختيار الموقع")

            sites = get_sites_list(state)
            site_key = st.selectbox("الموقع:", sites, key="site_selector")

            site_data = get_site_data(state, site_key)

            # عرض معلومات الموقع
            c1, c2, c3 = st.columns(3)
            c1.metric("النشاط", site_data.get("activity", "N/A"))
            c2.metric("الموسم", site_data.get("season", "N/A"))
            c3.metric("الحالة",
                      "🔴 ملوث" if site_data["actual_contaminated"] == 1 else "🟢 نظيف")

            st.markdown(f"**📍 الإحداثيات**: {site_data['coords'][0]}, {site_data['coords'][1]}")
            st.markdown(f"**📖 الوصف**: {site_data.get('name_ar', site_key)}")

            # ===== عرض القيم =====
            st.markdown("---")
            st.subheader("📊 القيم المُستخدمة (من قاعدة البيانات)")

            c1, c2 = st.columns(2)
            with c1:
                st.metric("D (عمق)", f"{site_data['depth_m']} م")
                st.metric("R (تغذية)", f"{site_data['recharge_mm']} مم/سنة")
                st.metric("T (ميل)", f"{site_data['slope_pct']} %")
                st.metric("C (توصيلية)", f"{site_data['conductivity']} م/يوم")
            with c2:
                st.metric("A (وسط)", AQUIFER_AR.get(site_data['aquifer'], site_data['aquifer']))
                st.metric("S (تربة)", SOIL_AR.get(site_data['soil'], site_data['soil']))
                st.metric("I (نطاق تهوية)", VADOSE_AR.get(site_data['vadose'], site_data['vadose']))
                st.metric("θ (مسامية)", "0.25")

            # ===== قيم CN و Hg =====
            st.markdown("---")
            st.subheader("🧪 قيم السيانيد والزئبق")

            c1, c2 = st.columns(2)
            c1.metric("CN", f"{site_data['cn_water_mg_l']} mg/L")
            c2.metric("Hg", f"{site_data['hg_water_mg_l']} mg/L")
            st.caption(f"الحدود السودانية: CN = 0.05، Hg = 0.0007 mg/L")

            # ===== حساب DRASTIC =====
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

                # حفظ
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

                st.markdown("---")
                st.subheader("📊 نتائج DRASTIC")

                x1, x2, x3, x4 = st.columns(4)
                x1.metric("D", D_r); x2.metric("R", R_r)
                x3.metric("A", A_r); x4.metric("S", S_r)
                y1, y2, y3, y4 = st.columns(4)
                y1.metric("T", T_r); y2.metric("I", I_r)
                y3.metric("C", C_r); y4.metric("θ", 0.25)

                st.markdown("---")
                z1, z2, z3 = st.columns(3)
                z1.metric("DRASTIC", f"{idx} / 230")
                z2.metric("المستوى", LEVEL_AR.get(risk["level"], risk["level"]))
                z3.metric("نسبة الخطورة", f"{round(idx/230*100, 1)}%")

                if risk["color"] == "red": st.error(f"🔴 {risk['action']}")
                elif risk["color"] == "orange": st.warning(f"🟠 {risk['action']}")
                elif risk["color"] == "yellow": st.info(f"🟡 {risk['action']}")
                else: st.success(f"🟢 {risk['action']}")

            except ValueError as e:
                st.error("خطأ: " + str(e))

    # ============ TAB 1: إدخال يدوي (جديد) ============
    with tabs[1]:
        st.header("➕ إدخال موقع جديد")
        st.markdown("**أضف موقعاً جديداً إلى قاعدة البيانات بسهولة**")

        if not DS_OK:
            st.error("❌ data_sources.py غير متوفر")
        else:
            # ===== معلومات الموقع =====
            st.markdown("---")
            st.subheader("📍 معلومات الموقع")

            c1, c2 = st.columns(2)
            with c1:
                new_state = st.text_input("الولاية:", value="سنار", key="new_state")
                new_site_key = st.text_input("اسم الموقع (إنجليزي):",
                                              value="New_Site", key="new_site_key")
                new_name_ar = st.text_input("الاسم بالعربية:",
                                             value="موقع جديد", key="new_name_ar")
            with c2:
                new_lat = st.number_input("خط العرض:", -90.0, 90.0, 13.55, 0.01,
                                           key="new_lat", format="%.4f")
                new_lon = st.number_input("خط الطول:", -180.0, 180.0, 33.60, 0.01,
                                           key="new_lon", format="%.4f")
                new_activity = st.selectbox("النشاط:",
                    ["تعدين أهلي", "زراعة", "حضري", "رعوي", "صناعي", "مرجعي"],
                    key="new_activity")

            # ===== القيم الهيدروجيولوجية =====
            st.markdown("---")
            st.subheader("💧 القيم الهيدروجيولوجية")

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

            # ===== قيم CN و Hg =====
            st.markdown("---")
            st.subheader("🧪 قيم السيانيد والزئبق")

            c1, c2 = st.columns(2)
            with c1:
                new_cn = st.number_input("CN - سيانيد (mg/L):",
                                          0.0, 10.0, 0.010, 0.001,
                                          key="new_cn", format="%.4f")
            with c2:
                new_hg = st.number_input("Hg - زئبق (mg/L):",
                                          0.0, 10.0, 0.001, 0.0001,
                                          key="new_hg", format="%.4f")

            # ===== الحالة =====
            st.markdown("---")
            st.subheader("📊 الحالة")

            c1, c2 = st.columns(2)
            with c1:
                new_contaminated = st.selectbox("الحالة الفعلية:",
                    ["نظيف (0)", "ملوث (1)"], key="new_contaminated")
            with c2:
                new_season = st.selectbox("الموسم:",
                    ["-", "جاف", "رطب"], key="new_season")

            # ===== معاينة DRASTIC =====
            st.markdown("---")
            st.subheader("🔍 معاينة DRASTIC")

            try:
                D_r = get_d_rating(new_depth)
                R_r = get_r_rating(new_recharge)
                A_r = get_a_rating(new_aquifer)
                S_r = get_s_rating(new_soil)
                T_r = get_t_rating(new_slope)
                I_r = get_i_rating(new_vadose)
                C_r = get_c_rating(new_conductivity)
                preview_idx = calc_index(D_r, R_r, A_r, S_r, T_r, I_r, C_r)
                preview_risk = classify(preview_idx)

                c1, c2, c3 = st.columns(3)
                c1.metric("DRASTIC المتوقع", f"{preview_idx} / 230")
                c2.metric("المستوى", LEVEL_AR.get(preview_risk["level"], preview_risk["level"]))
                c3.metric("نسبة الخطورة", f"{round(preview_idx/230*100, 1)}%")
            except Exception:
                st.warning("⚠️ تحقق من القيم المدخلة")

            # ===== زر الحفظ =====
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
                    st.success(f"✅ تم حفظ الموقع '{new_name_ar}' في ولاية '{new_state}'")
                    st.info("ℹ️ الموقع محفوظ في الذاكرة. استخدم زر 'تصدير CSV' أدناه لحفظه بشكل دائم.")
                    st.rerun()

            # ===== تصدير كل المواقع =====
            st.markdown("---")
            st.subheader("📥 تصدير قاعدة البيانات")

            if st.button("🔄 تحديث قاعدة البيانات", key="refresh_db"):
                st.rerun()

            try:
                df_all = get_all_sites_as_dataframe()
                st.success(f"📊 عدد المواقع الحالي: {len(df_all)}")
                st.download_button(
                    "📥 تحميل قاعدة البيانات الكاملة (CSV)",
                    data=df_all.to_csv(index=False).encode("utf-8-sig"),
                    file_name="sudan_sites_database.csv",
                    mime="text/csv",
                    width="stretch")
            except Exception as e:
                st.warning(f"⚠️ تعذر تصدير البيانات: {e}")

    # ============ TAB 2: الجماعي ============
    with tabs[2]:
        st.header("📊 التقييم الجماعي")
        st.info("ارفع ملف CSV يحتوي على بيانات المواقع.")

    # ============ TAB 3: الحلول ============
    with tabs[3]:
        st.header("🛡️ محاكي الحلول")
        if "ci" in st.session_state:
            ci = st.session_state["ci"]
            c1, c2 = st.columns(2)
            with c1:
                h = st.checkbox("HDPE Liner")
                tr = st.checkbox("Cyanide Treatment")
            with c2:
                mo = st.checkbox("Monitoring Wells")
            if h or tr or mo:
                r = mitigate(ci, h, tr, mo)
                a, b, c = st.columns(3)
                a.metric("قبل", ci)
                b.metric("بعد", r["mitigated_index"])
                c.metric("التخفيض", f"{r['reduction_pct']} %")
        else:
            st.warning("افتح تبويب المدخلات")

    # ============ TAB 4: التقرير ============
    with tabs[4]:
        st.header("📄 توليد التقرير")
        if "ci" in st.session_state:
            if st.button("توليد التقرير", type="primary"):
                rep = gen_report(st.session_state["cs"],
                                st.session_state["cc"],
                                st.session_state["ci"],
                                st.session_state["cv"])
                st.session_state["rep"] = rep
            if "rep" in st.session_state:
                st.text_area("التقرير:", st.session_state["rep"], height=400)
                st.download_button("📥 TXT",
                    data=st.session_state["rep"].encode("utf-8"),
                    file_name="report.txt", mime="text/plain")
        else:
            st.warning("افتح تبويب المدخلات")

    # ============ TAB 5: الخريطة ============
    with tabs[5]:
        st.header("🗺️ الخريطة التفاعلية")
        if DS_OK:
            c1, c2 = st.columns(2)
            with c1:
                show_mining = st.checkbox("مواقع التعدين", value=True)
                show_wells = st.checkbox("الآبار", value=True)
            with c2:
                base_map = st.selectbox("الخلفية:",
                    ["عادية", "أقمار صناعية", "تضاريس"])

            m = create_safe_map(base_map)

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
        else:
            st.warning("data_sources.py غير متوفر")

    # ============ TAB 6: الحساسية ============
    with tabs[6]:
        st.header("📈 تحليل الحساسية")
        if "ci" in st.session_state:
            var = st.slider("نسبة التغيير (%):", 5, 30, 10, 5) / 100.0
            r = sensitivity_analysis(st.session_state["cv"], var)
            st.success(f"🎯 الأكثر تأثيراً: {r['most_sensitive']}")
            st.metric("المؤشر الأساسي", r["base_index"])
        else:
            st.warning("افتح تبويب المدخلات")

    # ============ TAB 7: السمية ============
    with tabs[7]:
        st.header("☠️ تحليل السمية")
        if "ci" in st.session_state:
            cv = st.session_state["cv"]
            hgw = cv.get("hg_water_mg_l", 0.011)
            cnw = cv.get("cn_water_mg_l", 0.025)

            st.info(f"القيم: CN = {cnw} mg/L، Hg = {hgw} mg/L")

            if st.button("تحليل السمية", type="primary"):
                st.session_state["tox_result"] = weighted_toxicity(hgw, 0.5, cnw, 5.0)
            if "tox_result" in st.session_state:
                tox = st.session_state["tox_result"]
                c1, c2, c3 = st.columns(3)
                c1.metric("المؤشر", tox["index"])
                c2.metric("التصنيف", tox["category"])
                c3.metric("الإجراء", tox["action"])
        else:
            st.warning("افتح تبويب المدخلات")

    # ============ TAB 8: GIS ============
    with tabs[8]:
        st.header("🌍 تصدير GIS")
        if DS_OK:
            try:
                df_all = get_all_sites_as_dataframe()
                st.dataframe(df_all, width="stretch")

                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("📊 CSV",
                        data=df_all.to_csv(index=False).encode("utf-8-sig"),
                        file_name="sudan_sites.csv", mime="text/csv",
                        width="stretch")
                with c2:
                    if "cs" in st.session_state:
                        st.info(f"الموقع الحالي: {st.session_state['cs']}")
            except Exception as e:
                st.error(f"خطأ: {e}")

    # ============ TAB 9: Monte Carlo ============
    with tabs[9]:
        st.header("🎲 محاكاة Monte Carlo")
        if "ci" in st.session_state:
            c1, c2 = st.columns(2)
            with c1:
                n_iter = st.slider("عدد المحاكاات:", 100, 5000, 1000, 100)
            with c2:
                var_pct = st.slider("معامل الاختلاف (%):", 5, 30, 15, 5)

            if st.button("تشغيل المحاكاة", type="primary"):
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
        else:
            st.warning("افتح تبويب المدخلات")


# ============================================================
# ============ MODE 2: Validation ============
# ============================================================
elif mode == "✅ التحقق الفعلي" and ADV_OK:
    st.header("✅ التحقق الفعلي من النموذج")

    if DS_OK:
        st.markdown("---")
        st.subheader("📥 تحميل بيانات كل الولايات")

        if st.button("🔄 توليد ملف CSV من قاعدة البيانات", type="primary"):
            with st.spinner("جاري التوليد..."):
                df_all = get_all_sites_as_dataframe()
                st.session_state["df_all"] = df_all

        if "df_all" in st.session_state:
            df_all = st.session_state["df_all"]
            st.success(f"✅ تم توليد ملف يحتوي على {len(df_all)} موقع")
            st.dataframe(df_all.head(10), width="stretch")

            st.download_button("📥 تحميل بيانات كل الولايات (CSV)",
                data=df_all.to_csv(index=False).encode("utf-8-sig"),
                file_name="all_states_data.csv",
                mime="text/csv", width="stretch")

    st.markdown("---")
    st.subheader("📤 ارفع ملف CSV للتحقق")

    f = st.file_uploader("ارفع ملف CSV أو Excel:", type=["csv", "xlsx"], key="val_f")

    if f:
        try:
            if f.name.endswith(".csv"):
                df = pd.read_csv(f)
            else:
                df = pd.read_excel(f)

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
                            result = calc_drastic_p_sennar(ix, cn_w, hg_w)
                            drastic_p_list.append(result["drastic_p"])
                        else:
                            drastic_p_list.append(ix)

                        actual_list.append(int(row["actual_contaminated"]))
                    except Exception:
                        drastic_list.append(0)
                        drastic_p_list.append(0)
                        actual_list.append(int(row.get("actual_contaminated", 0)))

                df["drastic_index"] = drastic_list
                df["drastic_p_index"] = drastic_p_list

                st.markdown("---")
                st.subheader("📊 نتائج DRASTIC و DRASTIC-P")
                result_df = df[["site_name", "drastic_index",
                                "drastic_p_index", "actual_contaminated"]].copy()
                result_df.columns = ["الموقع", "DRASTIC", "DRASTIC-P", "الفعلي"]
                st.dataframe(result_df, width="stretch")

                st.markdown("---")
                st.subheader("📈 مقارنة DRASTIC vs DRASTIC-P")

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("### 🔵 DRASTIC التقليدي")
                    metrics_d = calculate_confusion_matrix(
                        drastic_list, actual_list, threshold=140)
                    st.metric("Accuracy", f"{metrics_d['accuracy']}%")
                    st.metric("Recall", f"{metrics_d['recall']}%")
                    st.metric("Kappa", metrics_d["kappa"])

                with c2:
                    st.markdown("### 🟢 DRASTIC-P المُعاير")
                    metrics_p = calculate_confusion_matrix(
                        drastic_p_list, actual_list, threshold=140)
                    st.metric("Accuracy", f"{metrics_p['accuracy']}%")
                    st.metric("Recall", f"{metrics_p['recall']}%")
                    st.metric("Kappa", metrics_p["kappa"])

                st.markdown("---")
                st.subheader("🏆 الحكم النهائي")

                if metrics_p["kappa"] > metrics_d["kappa"]:
                    st.success(f"""
                    ✅ **DRASTIC-P أفضل من DRASTIC التقليدي!**
                    - Kappa: {metrics_d['kappa']} → {metrics_p['kappa']}
                    - Recall: {metrics_d['recall']}% → {metrics_p['recall']}%
                    """)

                st.download_button("📥 تحميل النتائج (CSV)",
                    data=result_df.to_csv(index=False).encode("utf-8-sig"),
                    file_name="validation_results.csv",
                    mime="text/csv", width="stretch")

        except Exception as e:
            st.error(f"❌ خطأ في قراءة الملف: {e}")


# ============================================================
# ============ MODE 3: DRASTIC-P ============
# ============================================================
elif mode == "🧪 DRASTIC-P" and ADV_OK:
    st.header("🧪 DRASTIC-P — المؤشر المعدل")

    if "ci" not in st.session_state:
        st.warning("افتح النظام الأساسي أولاً")
    else:
        st.info(f"الموقع: {st.session_state['cs']} | DRASTIC: {st.session_state['ci']}")

        cv = st.session_state["cv"]
        cn_w = cv.get("cn_water_mg_l", 0.025)
        hg_w = cv.get("hg_water_mg_l", 0.011)

        st.markdown("---")
        st.subheader("🧪 بيانات السيانيد والزئبق")

        c1, c2 = st.columns(2)
        c1.metric("CN", f"{cn_w} mg/L")
        c2.metric("Hg", f"{hg_w} mg/L")

        cn_dist = st.number_input("المسافة لمصدر مياه (m):", 10.0,
                                   5000.0, 100.0, 50.0)
        cn_seep = st.slider("معدل التسرب:", 0.0, 1.0, 1.0, 0.05)

        if st.button("🧪 حساب DRASTIC-P", type="primary"):
            result = calc_drastic_p_sennar(
                st.session_state["ci"], cn_w, hg_w,
                distance_m=cn_dist, seepage=cn_seep, bio_acc=1.0)
            st.session_state["mod_result_v2"] = result

        if "mod_result_v2" in st.session_state:
            mod = st.session_state["mod_result_v2"]

            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("DRASTIC", mod["base_drastic"])
            c2.metric("DRASTIC-P", mod["drastic_p"],
                      delta=f"+{mod['increase_pct']}%")
            c3.metric("المستوى", LEVEL_AR.get(mod["level"], mod["level"]))

            if mod["color"] == "red": st.error("🔴 خطر داهم")
            elif mod["color"] == "orange": st.warning("🟠 خطر مرتفع")
            elif mod["color"] == "yellow": st.info("🟡 خطر متوسط")
            else: st.success("🟢 خطر منخفض")

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("CRI", mod["cri"])
                st.metric("نسبة CN", f"{mod['cn_ratio']}x")
            with c2:
                st.metric("MRI", mod["mri"])
                st.metric("نسبة Hg", f"{mod['hg_ratio']}x")


# ============================================================
# ============ MODE 4: Dynamic ============
# ============================================================
elif mode == "⏳ الديناميكي" and ADV_OK:
    st.header("⏳ التقييم الديناميكي")

    if "ci" not in st.session_state:
        st.warning("افتح النظام الأساسي أولاً")
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
    st.header("🌊 محاكاة MODFLOW 6")

    mf_ok, mf_msg = is_modflow_available()
    if not mf_ok:
        st.error(f"❌ {mf_msg}")
    else:
        st.success(f"✅ {mf_msg}")

        if HYDRO_OK:
            location = st.selectbox("الموقع المرجعي:",
                ["Omdurman_2023", "North_Khartoum_2024", "Gash_Kassala_2025"])
        else:
            location = "Omdurman_2023"

        st.markdown("---")
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
st.caption("2026 جامعة الخرطوم - نظام التعدين السوداني v50.0 - "
           "18 ولاية + إدخال يدوي + معايرة سنار")
