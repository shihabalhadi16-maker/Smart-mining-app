"""نظام التعدين السوداني v39.0 - الحل النهائي لمشكلة MODFLOW"""
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


# ============================================================
# ============ الحل النهائي: تحميل MODFLOW 6 مباشرة ============
# ============================================================
MODFLOW_URL = "https://github.com/MODFLOW-ORG/modflow6/releases/download/6.4.4/mf6.4.4_linux.zip"
MODFLOW_DIR = "/tmp/modflow6"


@st.cache_resource(show_spinner=False)
def setup_modflow():
    """
    تحميل MODFLOW 6 مباشرة من GitHub إلى مجلد مؤقت
    الحل النهائي الذي يعمل على Streamlit Cloud
    """
    try:
        Path(MODFLOW_DIR).mkdir(parents=True, exist_ok=True)
        mf6_path = os.path.join(MODFLOW_DIR, "mf6")
        
        # إذا كان موجوداً مسبقاً
        if os.path.exists(mf6_path) and os.access(mf6_path, os.X_OK):
            os.environ["PATH"] = MODFLOW_DIR + os.pathsep + os.environ.get("PATH", "")
            return "already_installed"
        
        # تحميل الملف من GitHub
        with st.spinner("⏳ جاري تحميل MODFLOW 6..."):
            response = requests.get(MODFLOW_URL, timeout=180, stream=True)
            if response.status_code != 200:
                return f"download_failed_{response.status_code}"
            
            # حفظ ZIP في الذاكرة
            zip_data = io.BytesIO(response.content)
            
            # فك الضغط
            with zipfile.ZipFile(zip_data, 'r') as zf:
                # البحث عن ملف mf6 داخل ZIP
                mf6_file = None
                for name in zf.namelist():
                    if name.endswith("mf6") and not name.endswith("/"):
                        mf6_file = name
                        break
                
                if not mf6_file:
                    return "mf6_not_in_zip"
                
                # استخراج الملف
                zf.extract(mf6_file, MODFLOW_DIR)
                extracted_path = os.path.join(MODFLOW_DIR, mf6_file)
                
                # نقل الملف إلى المجلد الرئيسي
                if extracted_path != mf6_path:
                    shutil.move(extracted_path, mf6_path)
        
        # إعطاء صلاحيات التنفيذ
        os.chmod(mf6_path, os.stat(mf6_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        
        # إضافة المجلد إلى PATH
        os.environ["PATH"] = MODFLOW_DIR + os.pathsep + os.environ.get("PATH", "")
        
        # التحقق
        if shutil.which("mf6"):
            return "installed"
        return "installed_but_not_in_path"
        
    except requests.exceptions.Timeout:
        return "timeout"
    except requests.exceptions.ConnectionError:
        return "connection_error"
    except Exception as e:
        return f"error: {str(e)[:100]}"


# تشغيل الإعداد
_modflow_status = setup_modflow()

# إضافة مسار MODFLOW إلى PATH دائماً
if os.path.exists(MODFLOW_DIR):
    os.environ["PATH"] = MODFLOW_DIR + os.pathsep + os.environ.get("PATH", "")


# ============================================================
# ============ الاستيرادات الاختيارية ============
# ============================================================
try:
    from data_sources import (
        get_preset_locations_for_app, get_data_summary,
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
            "toxicity_level": lvl}

def analyze_cyanide(w, s):
    wl, sl = 0.07, 10.0
    wr, sr = w / wl, s / sl
    mr = max(wr, sr)
    lvl = "منخفض" if mr <= 1 else "متوسط" if mr <= 3 else "مرتفع" if mr <= 10 else "مرتفع جدا"
    return {"water": {"value": w, "limit": wl, "ratio": round(wr, 2),
                      "status": "safe" if w <= wl else "exceeded"},
            "soil": {"value": s, "limit": sl, "ratio": round(sr, 2),
                     "status": "safe" if s <= sl else "exceeded"},
            "toxicity_level": lvl}

def weighted_toxicity(hgw, hgs, cnw, cns):
    w = (hgw/0.006*0.40) + (hgs/1.0*0.20) + (cnw/0.07*0.30) + (cns/10.0*0.10)
    if w <= 1.0: cat, act = "آمن", "لا يتطلب تدخل"
    elif w <= 3.0: cat, act = "تحت المراقبة", "مراقبة دورية"
    elif w <= 10.0: cat, act = "خطر", "تدخل عاجل"
    else: cat, act = "خطر داهم", "إيقاف النشاط"
    return {"index": round(w, 2), "category": cat, "action": act}


# ============================================================
# ============ Satellite ============
# ============================================================
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
TEMPLATES = {
    "low": {"level": "منخفض", "assessment": "خطورة منخفضة.",
        "recs": ["مراقبة سنوية.", "فحص سنوي.", "توثيق."]},
    "moderate": {"level": "متوسط", "assessment": "خطورة متوسطة.",
        "recs": ["مراقبة ربع سنوية.", "2-3 آبار.", "خطة طوارئ."]},
    "high": {"level": "مرتفع", "assessment": "خطورة مرتفعة.",
        "recs": ["HDPE Liner.", "معالجة السيانيد.", "4-6 آبار.", "EIA."]},
    "very_high": {"level": "مرتفع جدا", "assessment": "خطر داهم.",
        "recs": ["إيقاف النشاط.", "HDPE + معالجة.", "8-10 آبار.", "إخلاء."]},
}

def gen_report(site, coords, idx, values, travel=None, sat=None, tox=None):
    key = "very_high" if idx >= 180 else "high" if idx >= 140 else \
          "moderate" if idx >= 100 else "low"
    tpl = TEMPLATES[key]
    L = ["=" * 60, "تقرير تقييم هشاشة المياه الجوفية", "=" * 60, "",
         f"التاريخ: {datetime.date.today().strftime('%Y-%m-%d')}",
         f"الموقع: {site}", f"الإحداثيات: {coords[0]}, {coords[1]}", "",
         f"مؤشر DRASTIC: {idx} / 230", f"المستوى: {tpl['level']}", "",
         f"D: {values.get('depth', 'N/A')}",
         f"R: {values.get('recharge', 'N/A')}",
         f"A: {values.get('aquifer', 'N/A')}",
         f"S: {values.get('soil', 'N/A')}",
         f"T: {values.get('slope', 'N/A')}",
         f"I: {values.get('vadose', 'N/A')}",
         f"C: {values.get('conductivity', 'N/A')}", ""]
    if travel and isinstance(travel, dict):
        L.append(f"زمن الوصول: {travel.get('years', 0)} سنة")
    L.append("")
    L.append("التوصيات:")
    for i, rec in enumerate(tpl["recs"], 1):
        L.append(f"{i}. {rec}")
    return "\n".join(L)


def gen_html(rep, site):
    return ("<!DOCTYPE html><html dir='rtl' lang='ar'><head>"
         "<meta charset='UTF-8'><title>" + site + "</title>"
         "<style>body{font-family:Arial;direction:rtl;text-align:right;"
         "padding:30px;max-width:900px;margin:auto;line-height:1.9;}"
         "pre{white-space:pre-wrap;background:#f8f9fa;padding:25px;"
         "border-radius:8px;font-family:inherit;}</style></head>"
         "<body><pre>" + rep + "</pre></body></html>")


# ============================================================
# ============ GIS ============
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
    for s in sites:
        try:
            kml += f'<Placemark><name>{s.get("name","")}</name>'
            kml += f'<description>DRASTIC: {s.get("index",0)}</description>'
            kml += f'<Point><coordinates>{s.get("lon",0)},{s.get("lat",0)},0</coordinates></Point>'
            kml += '</Placemark>\n'
        except Exception:
            continue
    kml += '</Document></kml>'
    return kml


# ============================================================
# ============ Safe Map ============
# ============================================================
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
st.markdown("""
<div class="header-container">
    <div class="header-title">⛏️ نظام التعدين السوداني v39.0</div>
    <div class="header-subtitle">جامعة الخرطوم - كلية الهندسة</div>
    <div class="header-subtitle">DRASTIC + MODFLOW + DRASTIC-P + Dynamic + Validation</div>
</div>
""", unsafe_allow_html=True)

if DS_OK:
    preset = get_preset_locations_for_app()
    summary = get_data_summary()
else:
    preset = {"موقع تجريبي": {"coords": (19.53, 33.32), "depth": 15.0,
              "conductivity": 5.0, "recharge": 100.0,
              "aquifer": "massive_sandstone", "soil": "sand",
              "slope": 4.0, "vadose": "sand_gravel", "source": "افتراضي"}}
    summary = {}


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

# عرض حالة MODFLOW
st.sidebar.markdown("### 🔧 حالة النظام")
if _modflow_status == "already_installed":
    st.sidebar.success("✅ MODFLOW مثبت مسبقاً")
elif _modflow_status == "installed":
    st.sidebar.success("✅ تم تثبيت MODFLOW الآن")
elif _modflow_status == "installed_but_not_in_path":
    st.sidebar.warning("⚠️ مثبت لكن ليس في PATH")
elif _modflow_status == "timeout":
    st.sidebar.error("❌ انتهت مهلة التحميل")
elif _modflow_status == "connection_error":
    st.sidebar.error("❌ خطأ في الاتصال")
elif _modflow_status.startswith("download_failed"):
    st.sidebar.error(f"❌ فشل التحميل: {_modflow_status}")
else:
    st.sidebar.warning(f"⚠️ {_modflow_status}")

# تشخيص الملفات
with st.sidebar.expander("🔍 تشخيص الملفات"):
    st.write(f"data_sources: {'✅' if DS_OK else '❌'}")
    st.write(f"modflow_engine: {'✅' if MODFLOW_OK else '❌'}")
    st.write(f"hydro_data: {'✅' if HYDRO_OK else '❌'}")
    st.write(f"advanced_modules: {'✅' if ADV_OK else '❌'}")
    # مسار MODFLOW
    mf6_path = shutil.which("mf6") if shutil else None
    st.write(f"mf6 path: {mf6_path or 'غير موجود'}")

if "ci" in st.session_state:
    st.sidebar.success(f"✅ مؤشر حالي: {st.session_state['ci']}")
else:
    st.sidebar.warning("⚠️ لم يتم حساب مؤشر بعد")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📚 المراجع")
st.sidebar.caption("• EPA/600/2-87/035")
st.sidebar.caption("• دراسة القاش 2025")
st.sidebar.caption("• دراسة أم درمان 2023")


# ============================================================
# ============ MODE 1: النظام الأساسي ============
# ============================================================
if mode == "🏠 النظام الأساسي":
    tabs = st.tabs(["📍 المدخلات", "📊 الجماعي", "🛡️ الحلول", "📄 التقرير",
                    "🗺️ الخريطة", "📈 الحساسية", "☠️ السمية",
                    "📚 التاريخ", "🌍 GIS", "🎲 Monte Carlo"])

    with tabs[0]:
        st.header("اختيار الموقع والمدخلات")
        site = st.selectbox("الموقع:", list(preset.keys()))
        sd = preset[site]

        st.markdown("---")
        st.subheader("بيانات الأقمار الصناعية")
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

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            depth = st.slider("D - عمق المياه (م):", 0.5, 100.0,
                              float(sd.get("depth", 15.0)), 0.5)
            recharge = st.slider("R - التغذية (مم):", 0.0, 400.0,
                                 float(sd.get("recharge", 150.0)), 10.0)
            slope = st.slider("T - الميل (%):", 0.0, 30.0,
                              float(sd.get("slope", 4.0)), 0.5)
            conductivity = st.slider("C - التوصيلية (م/يوم):", 0.01, 100.0,
                                      float(sd.get("conductivity", 5.0)), 0.1)
        with c2:
            aquifer = st.selectbox("A:", VALID_AQUIFERS)
            soil = st.selectbox("S:", VALID_SOILS)
            vadose = st.selectbox("I:", VALID_VADOSE)
            porosity = st.slider("θ:", 0.02, 0.55, 0.25, 0.01)

        gradient = st.slider("i - التدرج:", 0.0001, 0.5, 0.01, 0.0001,
                              format="%.4f")

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
            z1.metric("DRASTIC", f"{idx} / 230")
            z2.metric("المستوى", risk["level"])
            if risk["color"] == "red": st.error(risk["action"])
            elif risk["color"] == "orange": st.warning(risk["action"])
            elif risk["color"] == "yellow": st.info(risk["action"])
            else: st.success(risk["action"])

            st.markdown("---")
            st.subheader("زمن وصول الملوثات")
            w1, w2, w3, w4 = st.columns(4)
            w1.metric("سنوات", travel["years"])
            w2.metric("أيام", travel["days"])
            w3.metric("السرعة", travel["velocity"])
            w4.metric("i", travel["gradient"])
        except ValueError as e:
            st.error("خطأ: " + str(e))

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

        f = st.file_uploader("📤 ارفع ملف:", type=["csv", "xlsx"])
        if f:
            try:
                df = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)
                results = []
                for i, row in df.iterrows():
                    errs, warns, q = validate_bulk_row(row, i)
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
                        results.append({"الموقع": row.get("name", f"S{i}"),
                            "المؤشر": ix, "المستوى": rk["level"],
                            "الجودة": q})
                    except Exception:
                        results.append({"الموقع": row.get("name", f"S{i}"),
                            "المؤشر": 0, "المستوى": "فشل",
                            "الجودة": "ضعيف"})
                dfr = pd.DataFrame(results)
                st.dataframe(dfr, width="stretch")
                st.download_button("📥 نتائج CSV",
                    data=dfr.to_csv(index=False).encode("utf-8-sig"),
                    file_name="results.csv", mime="text/csv")
            except Exception as e:
                st.error("خطأ: " + str(e))

    with tabs[2]:
        st.header("محاكي الحلول")
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

    with tabs[3]:
        st.header("توليد التقرير")
        if "ci" in st.session_state:
            if st.button("توليد", type="primary"):
                rep = gen_report(st.session_state["cs"],
                                st.session_state["cc"],
                                st.session_state["ci"],
                                st.session_state["cv"],
                                st.session_state.get("ct"),
                                st.session_state.get("sat_data"))
                st.session_state["rep"] = rep
            if "rep" in st.session_state:
                st.text_area("التقرير:", st.session_state["rep"], height=400)
                st.download_button("TXT",
                    data=st.session_state["rep"].encode("utf-8"),
                    file_name="report.txt", mime="text/plain")
                st.download_button("HTML",
                    data=gen_html(st.session_state["rep"],
                                  st.session_state["cs"]).encode("utf-8"),
                    file_name="report.html", mime="text/html")
        else:
            st.warning("افتح تبويب المدخلات")

    with tabs[4]:
        st.header("🗺️ الخريطة")
        if DS_OK:
            c1, c2 = st.columns(2)
            with c1:
                show_mining = st.checkbox("مواقع التعدين", value=True)
                show_wells = st.checkbox("الآبار", value=True)
            with c2:
                show_buffers = st.checkbox("نطاقات التأثير", value=True)
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
                    if show_buffers:
                        folium.Circle([lat, lon], radius=500, color="red",
                            fill=True, fill_opacity=0.2).add_to(m)
                        folium.Circle([lat, lon], radius=1000, color="orange",
                            fill=True, fill_opacity=0.12).add_to(m)
                        folium.Circle([lat, lon], radius=2000, color="yellow",
                            fill=True, fill_opacity=0.08).add_to(m)
                    folium.Marker([lat, lon], popup=n, tooltip=n,
                        icon=folium.Icon(color="red",
                            icon="exclamation-triangle",
                            prefix="fa")).add_to(m)

            st_folium(m, height=600, key="map_main")
        else:
            st.warning("data_sources.py غير متوفر")

    with tabs[5]:
        st.header("تحليل الحساسية")
        if "ci" in st.session_state:
            var = st.slider("التغيير (%):", 5, 30, 10, 5) / 100.0
            r = sensitivity_analysis(st.session_state["cv"], var)
            st.success("الأكثر تأثيراً: " + str(r["most_sensitive"]))
            for p in r["parameters"]:
                pdd = r["parameters"][p]
                with st.expander(f"{p} — تأثير: {pdd['sensitivity']}%"):
                    st.metric("القيمة الأصلية", pdd["original_phys"])
                    st.metric("القيمة المعدلة", pdd["modified_phys"])
                    st.metric("المؤشر الجديد", pdd["new_index"])
            chart = pd.DataFrame({
                "المعامل": list(r["parameters"].keys()),
                "الحساسية": [r["parameters"][p]["sensitivity"]
                            for p in r["parameters"]]}).set_index("المعامل")
            st.bar_chart(chart)
        else:
            st.warning("افتح تبويب المدخلات")

    with tabs[6]:
        st.header("تحليل السمية")
        if "ci" in st.session_state:
            c1, c2 = st.columns(2)
            with c1:
                hgw = st.number_input("Hg مياه (mg/L):", 0.0, 10.0, 0.05,
                                       0.001, format="%.4f")
                hgs = st.number_input("Hg تربة (mg/kg):", 0.0, 100.0, 0.5, 0.1)
            with c2:
                cnw = st.number_input("CN مياه (mg/L):", 0.0, 10.0, 0.10,
                                       0.01, format="%.4f")
                cns = st.number_input("CN تربة (mg/kg):", 0.0, 100.0, 5.0, 0.5)

            if st.button("تحليل", type="primary"):
                st.session_state["tox_result"] = weighted_toxicity(hgw, hgs, cnw, cns)
            if "tox_result" in st.session_state:
                tox = st.session_state["tox_result"]
                c1, c2, c3 = st.columns(3)
                c1.metric("المؤشر", tox["index"])
                c2.metric("التصنيف", tox["category"])
                c3.metric("الإجراء", tox["action"])
        else:
            st.warning("افتح تبويب المدخلات")

    with tabs[7]:
        st.header("📚 التاريخ")
        if "history" in st.session_state and st.session_state["history"]:
            df = pd.DataFrame(st.session_state["history"])
            st.dataframe(df, width="stretch")
            st.download_button("📥 CSV",
                data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name="history.csv", mime="text/csv")
        else:
            st.info("لا توجد تقييمات محفوظة")

    with tabs[8]:
        st.header("🌍 تصدير GIS")
        if DS_OK:
            sites = []
            for name, data in preset.items():
                try:
                    coords = data.get("coords", (0, 0))
                    D_p = float(data.get("depth", 15.0))
                    R_p = float(data.get("recharge", 100.0))
                    A_p = str(data.get("aquifer", "massive_sandstone"))
                    S_p = str(data.get("soil", "sand"))
                    T_p = float(data.get("slope", 4.0))
                    I_p = str(data.get("vadose", "sand_gravel"))
                    C_p = float(data.get("conductivity", 5.0))
                    ix = calc_index(get_d_rating(D_p), get_r_rating(R_p),
                                   get_a_rating(A_p), get_s_rating(S_p),
                                   get_t_rating(T_p), get_i_rating(I_p),
                                   get_c_rating(C_p))
                    rk = classify(ix)
                    sites.append({"name": name, "lat": coords[0],
                        "lon": coords[1], "index": ix, "level": rk["level"]})
                except Exception:
                    continue
            if sites:
                df_s = pd.DataFrame(sites)
                st.dataframe(df_s, width="stretch")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.download_button("GeoJSON",
                        data=sites_to_geojson(sites).encode("utf-8"),
                        file_name="sites.geojson",
                        mime="application/geo+json")
                with c2:
                    st.download_button("KML",
                        data=sites_to_kml(sites).encode("utf-8"),
                        file_name="sites.kml",
                        mime="application/vnd.google-earth.kml+xml")
                with c3:
                    st.download_button("CSV",
                        data=df_s.to_csv(index=False).encode("utf-8-sig"),
                        file_name="sites.csv", mime="text/csv")

    with tabs[9]:
        st.header("🎲 Monte Carlo")
        if "ci" in st.session_state:
            n_iter = st.slider("المحاكاات:", 100, 5000, 1000, 100)
            var_pct = st.slider("الاختلاف (%):", 5, 30, 15, 5)
            if st.button("تشغيل", type="primary"):
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
                    st.metric("P>140", f"{mc['prob_over_140']}%")
                with c2:
                    st.metric("P>180", f"{mc['prob_over_180']}%")
        else:
            st.warning("افتح تبويب المدخلات")


# ============================================================
# ============ MODE 2: Validation ============
# ============================================================
elif mode == "✅ التحقق الفعلي" and ADV_OK:
    st.header("✅ التحقق الفعلي")
    sample_val = pd.DataFrame({
        "site_name": ["S1", "S2", "S3", "S4"],
        "drastic_index": [150, 80, 130, 165],
        "actual_contaminated": [1, 0, 0, 1]})
    st.download_button("📥 قالب",
        data=sample_val.to_csv(index=False).encode("utf-8-sig"),
        file_name="validation.csv", mime="text/csv")

    f = st.file_uploader("ارفع:", type=["csv", "xlsx"], key="val_f")
    if f:
        try:
            df = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)
            if "drastic_index" in df.columns and "actual_contaminated" in df.columns:
                threshold = st.slider("العتبة:", 100, 200, 140, 5)
                metrics = calculate_confusion_matrix(
                    df["drastic_index"].values,
                    df["actual_contaminated"].values, threshold)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Accuracy", f"{metrics['accuracy']}%")
                c2.metric("Precision", f"{metrics['precision']}%")
                c3.metric("Recall", f"{metrics['recall']}%")
                c4.metric("F1", f"{metrics['f1_score']}%")
                c1, c2, c3 = st.columns(3)
                c1.metric("Kappa", metrics["kappa"])
                c2.metric("MCC", metrics["mcc"])
                c3.metric("Specificity", f"{metrics['specificity']}%")
                cm = metrics["confusion_matrix"]
                cm_df = pd.DataFrame({
                    "ملوث": [cm["TP"], cm["FN"]],
                    "نظيف": [cm["FP"], cm["TN"]]},
                    index=["توقع ملوث", "توقع نظيف"])
                st.dataframe(cm_df, width="stretch")
                st.text(generate_validation_report(metrics))
            else:
                st.error("أعمدة مفقودة")
        except Exception as e:
            st.error(str(e))


# ============================================================
# ============ MODE 3: DRASTIC-P ============
# ============================================================
elif mode == "🧪 DRASTIC-P" and ADV_OK:
    st.header("🧪 DRASTIC-P")
    if "ci" not in st.session_state:
        st.warning("افتح النظام الأساسي أولاً")
    else:
        st.info(f"DRASTIC: {st.session_state['ci']}")
        c1, c2 = st.columns(2)
        with c1:
            cn_w = st.number_input("CN مياه:", 0.0, 10.0, 0.05, 0.001,
                                    format="%.4f")
            cn_s = st.number_input("CN تربة:", 0.0, 100.0, 5.0, 0.5)
            cn_dist = st.number_input("المسافة:", 10.0, 5000.0, 500.0, 50.0)
            cn_seep = st.slider("التسرب:", 0.0, 1.0, 0.3, 0.05)
        with c2:
            hg_w = st.number_input("Hg مياه:", 0.0, 10.0, 0.005, 0.001,
                                    format="%.4f")
            hg_s = st.number_input("Hg تربة:", 0.0, 100.0, 0.5, 0.1)
            bio = st.slider("التراكم:", 1.0, 3.0, 1.5, 0.1)
            use = st.selectbox("الاستخدام:",
                ["drinking", "irrigation", "industrial"])
        amd = st.slider("AMD:", 0.0, 1.0, 0.2, 0.05)

        if st.button("🧪 حساب", type="primary"):
            cri = calculate_cyanide_risk_index(cn_w, cn_s, cn_dist, cn_seep)
            mri = calculate_mercury_risk_index(hg_w, hg_s, bio, use)
            mod = calculate_modified_drastic(st.session_state["ci"],
                                              cri["cri"], mri["mri"], amd)
            c1, c2, c3 = st.columns(3)
            c1.metric("DRASTIC", mod["base_drastic"])
            c2.metric("DRASTIC-P", mod["modified_drastic"],
                      delta=f"+{mod['increase_pct']}%")
            c3.metric("المستوى", mod["level"])
            c1, c2 = st.columns(2)
            with c1:
                st.metric("CRI", cri["cri"], cri["level"])
            with c2:
                st.metric("MRI", mri["mri"], mri["level"])


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
            years = st.slider("السنوات:", 1, 50, 10, 1)
            mining = st.slider("توسع التعدين:", 0.0, 0.20, 0.05, 0.01)
        with c2:
            climate = st.slider("المناخ:", -0.10, 0.05, -0.02, 0.005)
            pop = st.slider("السكان:", 0.0, 0.10, 0.03, 0.01)
        cri0 = st.slider("CRI الآن:", 0.0, 10.0, 1.0, 0.1)
        mri0 = st.slider("MRI الآن:", 0.0, 10.0, 0.5, 0.1)

        if st.button("⏳ تشغيل", type="primary"):
            res = calculate_dynamic_risk(st.session_state["ci"], years,
                                          mining, climate, pop, cri0, mri0)
            st.session_state["dyn"] = res

        if "dyn" in st.session_state:
            res = st.session_state["dyn"]
            df = res["combined"]
            c1, c2, c3 = st.columns(3)
            c1.metric("DRASTIC", st.session_state["ci"])
            c2.metric(f"DRASTIC-P س{years}", res["final_modified"])
            c3.metric("المستوى", res["final_level"])
            st.line_chart(df.set_index("السنة")[
                ["DRASTIC", "DRASTIC-Modified", "CRI", "MRI"]])
            st.dataframe(df, width="stretch")


# ============================================================
# ============ MODE 5: MODFLOW ============
# ============================================================
elif mode == "🌊 MODFLOW" and MODFLOW_OK:
    st.header("🌊 محاكاة MODFLOW")

    mf_ok, mf_msg = is_modflow_available()
    if not mf_ok:
        st.error(f"❌ {mf_msg}")
        st.info(f"""
        **حالة MODFLOW:**
        - _modflow_status: `{_modflow_status}`
        - مسار mf6: `{shutil.which('mf6') or 'غير موجود'}`
        - مجلد MODFLOW: `{MODFLOW_DIR}`
        
        **إذا استمر الخطأ:**
        تحقق من Logs في Streamlit Cloud.
        """)
    else:
        st.success(f"✅ {mf_msg}")

        if HYDRO_OK:
            location = st.selectbox("الموقع المرجعي:",
                ["Omdurman_2023", "North_Khartoum_2024", "Gash_Kassala_2025"])
            with st.expander(f"ℹ️ بيانات {location}"):
                info = HYDRAULIC_CONDUCTIVITY.get(location, {})
                if location == "Gash_Kassala_2025":
                    st.write(f"المنبع: {info['upstream']['value']} م/يوم")
                    st.write(f"كسلا: {info['kassala']['value']} م/يوم")
                    st.write(f"المصب: {info['downstream']['value']} م/يوم")
                else:
                    st.write(f"K: {info.get('min')} - {info.get('max')} م/يوم")
                st.write(f"المصدر: {info.get('source', 'N/A')}")
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
            top = st.number_input("منسوب السطح (m):", 10.0, 2000.0, 350.0, 10.0)
            botm = st.number_input("القاعدة (m):", 0.0, 1000.0, 50.0, 10.0)
            if HYDRO_OK:
                dk = get_default_k(location)
                dr = get_default_recharge("Omdurman" if "Omdurman" in location
                                            else "Gash_Kassala")
            else:
                dk, dr = 3.5, 15.0
            k_val = st.number_input("K (m/day):", 0.01, 500.0, float(dk), 0.1)
            rech = st.number_input("التغذية (mm/year):", 0.0, 500.0,
                                    float(dr) if dr < 500 else 15.0, 1.0)

        n_wells = st.number_input("عدد الآبار:", 0, 10, 0)
        wl, wr = [], []
        for i in range(int(n_wells)):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                l = st.number_input(f"طبقة {i+1}:", 0, nlay-1, 0, key=f"wl{i}")
            with c2:
                r = st.number_input(f"صف {i+1}:", 0, nrow-1, nrow//2, key=f"wr{i}")
            with c3:
                c = st.number_input(f"عمود {i+1}:", 0, ncol-1, ncol//2, key=f"wc{i}")
            with c4:
                rate = st.number_input(f"معدل {i+1}:", -10000.0, 10000.0,
                                        -1000.0, 100.0, key=f"rt{i}")
            wl.append((int(l), int(r), int(c)))
            wr.append(float(rate))

        if st.button("🚀 تشغيل MODFLOW", type="primary"):
            with st.spinner("جاري التشغيل..."):
                ws = f"/tmp/mf_ws_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                res = build_and_run_model(
                    workspace=ws, nlay=int(nlay), nrow=int(nrow),
                    ncol=int(ncol), delr=float(delr), delc=float(delc),
                    top=float(top), botm=float(botm), k_value=float(k_val),
                    recharge_mm=float(rech),
                    well_locations=wl if wl else None,
                    well_rates=wr if wr else None)
                st.session_state["mf_res"] = res

        if "mf_res" in st.session_state:
            res = st.session_state["mf_res"]
            if not res.get("success"):
                st.error(f"❌ {res.get('error')}")
            else:
                st.success("✅ نجح!")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("أدنى", f"{res['head_min']:.2f} m")
                c2.metric("أعلى", f"{res['head_max']:.2f} m")
                c3.metric("متوسط", f"{res['head_mean']:.2f} m")
                c4.metric("الحجم", f"{res['nrow']}×{res['ncol']}")

                try:
                    import plotly.express as px
                    fig = px.imshow(res["heads"],
                        labels={"x": "عمود", "y": "صف", "color": "منسوب (m)"},
                        color_continuous_scale="Viridis",
                        title="منسوب المياه الجوفية")
                    st.plotly_chart(fig, width="stretch")
                except ImportError:
                    st.dataframe(pd.DataFrame(res["heads"]), width="stretch")

                if HYDRO_OK:
                    por = get_default_porosity()
                else:
                    por = 0.20
                tr = estimate_travel_time_modflow(
                    res["heads"], float(k_val), por, float(delr))
                if tr:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("التدرج", f"{tr['mean_gradient']:.6f}")
                    c2.metric("السرعة (m/d)", f"{tr['velocity_m_day']:.4f}")
                    c3.metric("السرعة (m/y)", f"{tr['velocity_m_year']:.2f}")


# ============ FOOTER ============
st.markdown("---")
st.caption("2026 جامعة الخرطوم - نظام التعدين السوداني v39.0")
