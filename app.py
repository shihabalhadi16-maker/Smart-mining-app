"""نظام التعدين السوداني — Sudan Mining System v1.0"""
import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import datetime
import requests
import json
import random as _rnd
from datetime import timedelta

# ============ إعدادات الصفحة ============
st.set_page_config(
    page_title="نظام التعدين السوداني",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============ تنسيق بصري محسّن للجوال ============
st.markdown("""
<style>
    /* تحسينات للجوال */
    @media (max-width: 768px) {
        .stApp {
            font-size: 14px;
        }
        h1 {
            font-size: 24px !important;
        }
        h2 {
            font-size: 20px !important;
        }
        h3 {
            font-size: 18px !important;
        }
        div[data-testid="stMetricValue"] {
            font-size: 22px !important;
        }
    }
    
    /* التنسيق العام */
    .stApp {
        background-color: #f8f9fa;
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #d4af37;
        border-radius: 10px;
        padding: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .section-header {
        color: #5c2c16;
        border-bottom: 2px solid #c19a6b;
        padding-bottom: 5px;
        margin-bottom: 15px;
        font-weight: bold;
    }
    /* الأزرار الكبيرة */
    .stButton > button {
        border-radius: 8px;
        font-weight: bold;
    }
    /* التبويبات */
    .stTabs [data-baseweb="tab"] {
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# ============ Meta Tags للـ PWA ============
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#5c2c16">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="نظام التعدين">
<meta name="application-name" content="نظام التعدين السوداني">
<meta name="description" content="نظام تقييم هشاشة المياه الجوفية في مواقع التعدين التقليدي بالسودان">
""", unsafe_allow_html=True)

# ============ استيراد البيانات ============
try:
    from data_sources import (
        get_preset_locations_for_app, get_data_summary,
        KNOWN_MINING_SITES, NARIS_WELLS, DARFUR_WELLS, KHARTOUM_LOCALITIES)
    DS_OK = True
except ImportError:
    DS_OK = False


# ==================== DRASTIC ====================
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

def calc_travel(d, p, k, g=1.0):
    if d <= 0: raise ValueError("D>0")
    if not (0.01 < p < 0.60): raise ValueError("Porosity")
    if k <= 0: raise ValueError("K>0")
    v = (k * g) / p
    days = d / v
    return {"days": round(days, 2), "years": round(days / 365.25, 3),
            "velocity": round(v, 6)}

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

def sensitivity_analysis(D, R, A, S, T, I, C, variation=0.10):
    base = calc_index(D, R, A, S, T, I, C)
    bv = {"D": D, "R": R, "A": A, "S": S, "T": T, "I": I, "C": C}
    res = {}
    for p, v in bv.items():
        nv = max(1, min(10, v * (1 + variation)))
        md = dict(bv)
        md[p] = nv
        ni = calc_index(**md)
        ch = ni - base
        res[p] = {"original": v, "modified": round(nv, 2),
                  "new_index": ni, "change": ch,
                  "sensitivity": round(abs(ch) / base * 100, 3) if base > 0 else 0}
    sr = dict(sorted(res.items(), key=lambda x: x[1]["sensitivity"], reverse=True))
    return {"base_index": base, "variation": variation, "parameters": sr,
            "most_sensitive": list(sr.keys())[0] if sr else None}

def monte_carlo_analysis(D, R, A, S, T, I, C, n_iter=1000, variation=0.15):
    base = calc_index(D, R, A, S, T, I, C)
    bv = [D, R, A, S, T, I, C]
    wt = [5, 4, 3, 2, 1, 5, 3]
    results = []
    for _ in range(n_iter):
        total = 0
        for v, w in zip(bv, wt):
            nv = v * (1 + _rnd.uniform(-variation, variation))
            nv = max(1, min(10, nv))
            total += nv * w
        results.append(round(total))
    results.sort()
    n = len(results)
    mean = sum(results) / n
    var = sum((x - mean) ** 2 for x in results) / n
    std = var ** 0.5
    def pct(p):
        i = max(0, min(n - 1, int((p / 100) * n)))
        return results[i]
    over_140 = sum(1 for x in results if x >= 140) / n * 100
    over_180 = sum(1 for x in results if x >= 180) / n * 100
    return {"base": base, "n": n, "mean": round(mean, 1),
            "std": round(std, 2), "min": results[0], "max": results[-1],
            "p5": pct(5), "p25": pct(25), "p50": pct(50),
            "p75": pct(75), "p95": pct(95),
            "ci_90": (pct(5), pct(95)), "ci_50": (pct(25), pct(75)),
            "prob_over_140": round(over_140, 1),
            "prob_over_180": round(over_180, 1)}


# ==================== Validation ====================
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
                          aquifer, soil, vadose):
    errors = []
    warnings = []
    if not (0.5 <= depth <= 100): errors.append("D خارج النطاق")
    if not (0 <= recharge <= 400): errors.append("R خارج النطاق")
    if not (0 <= slope <= 30): errors.append("T خارج النطاق")
    if not (0.01 <= conductivity <= 100): errors.append("C خارج النطاق")
    if aquifer not in VALID_AQUIFERS: warnings.append("A غير معروف")
    if soil not in VALID_SOILS: warnings.append("S غير معروف")
    if vadose not in VALID_VADOSE: warnings.append("I غير معروف")
    return errors, warnings


def validate_bulk_row(row, idx):
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


# ==================== GIS Preset Sites ====================
def get_preset_sites_with_drastic(preset):
    sites = []
    for name, data in preset.items():
        try:
            coords = data.get("coords", (0, 0))
            depth_v = float(data.get("depth", 15))
            cond_v = float(data.get("conductivity", 5))
            D_r = get_d_rating(depth_v)
            R_r = get_r_rating(150.0)
            A_r = get_a_rating("massive_sandstone")
            S_r = get_s_rating("sand")
            T_r = get_t_rating(4.0)
            I_r = get_i_rating("sand_gravel")
            C_r = get_c_rating(cond_v)
            ix = calc_index(D_r, R_r, A_r, S_r, T_r, I_r, C_r)
            rk = classify(ix)
            sites.append({
                "name": str(name),
                "lat": float(coords[0]),
                "lon": float(coords[1]),
                "index": ix,
                "level": rk["level"]})
        except Exception:
            continue
    return sites


# ==================== Hg + CN ====================
def analyze_mercury(w, s):
    wl, sl = 0.006, 1.0
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
    w = (hgw / 0.006 * 0.40) + (hgs / 1.0 * 0.20) + \
        (cnw / 0.07 * 0.30) + (cns / 10.0 * 0.10)
    if w <= 1.0: cat, act = "آمن", "لا يتطلب تدخل"
    elif w <= 3.0: cat, act = "تحت المراقبة", "مراقبة دورية"
    elif w <= 10.0: cat, act = "خطر", "تدخل عاجل"
    else: cat, act = "خطر داهم", "إيقاف النشاط"
    return {"index": round(w, 2), "category": cat, "action": act}

def generate_alerts(idx, hg=None, cn=None, tox=None):
    al = []
    if idx >= 180: al.append({"icon": "🔴", "msg": "DRASTIC " + str(idx), "act": "إيقاف النشاط"})
    elif idx >= 140: al.append({"icon": "🟠", "msg": "DRASTIC " + str(idx), "act": "تدخل عاجل"})
    elif idx >= 100: al.append({"icon": "🟡", "msg": "DRASTIC " + str(idx), "act": "مراقبة"})
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


# ==================== Satellite ====================
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
            "source": "ERA5 (ECMWF) via Open-Meteo"}


# ==================== History ====================
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
        "زمن الوصول": travel if travel else 0,
        "الأمطار": sat.get("rainfall_mm", 0) if sat else 0,
        "مؤشر السمية": tox.get("index", 0) if tox else 0})

def get_history_df():
    if "history" not in st.session_state or not st.session_state["history"]:
        return pd.DataFrame()
    return pd.DataFrame(st.session_state["history"])


# ==================== GIS Export ====================
def sites_to_geojson(sites):
    features = []
    for s in sites:
        try:
            features.append({"type": "Feature",
                "geometry": {"type": "Point",
                    "coordinates": [float(s.get("lon", 0)), float(s.get("lat", 0))]},
                "properties": {"name": str(s.get("name", "")),
                    "index": int(s.get("index", 0)),
                    "level": str(s.get("level", ""))}})
        except Exception:
            continue
    return json.dumps({"type": "FeatureCollection", "features": features},
                      ensure_ascii=False, indent=2)

def sites_to_kml(sites):
    kml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    kml += '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>\n'
    kml += '<name>نظام التعدين السوداني</name>\n'
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


# ==================== Templates ====================
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
    ref = "SMS-" + today.strftime("%Y%m%d") + "-" + key.upper()[:3]
    L = ["=" * 60, "تقرير تقييم هشاشة المياه الجوفية",
         "نظام التعدين السوداني — جامعة الخرطوم", "=" * 60, "",
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
    if travel:
        L.append("زمن الوصول: " + str(round(travel, 2)) + " سنة")
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


# ==================== UI ====================
st.title("⛏️ نظام التعدين السوداني")
st.markdown("### جامعة الخرطوم — كلية الهندسة")
st.markdown("#### الإصدار 1.0")
st.markdown("---")

if DS_OK:
    preset = get_preset_locations_for_app()
    summary = get_data_summary()
else:
    preset = {"موقع تجريبي": {"coords": (19.53, 33.32),
              "depth": 15.0, "conductivity": 5.0, "source": "افتراضي"}}
    summary = {"Total Data Points": 1}

tabs = st.tabs(["📍 المدخلات", "📊 الجماعي", "🛡️ الحلول", "📄 التقرير",
                "🗺️ الخريطة", "📊 الدقة", "📈 الحساسية", "⚖️ مقارنة",
                "☠️ السمية", "📚 التاريخ", "🌍 GIS", "🎲 Monte Carlo"])


# ============ TAB 1 ============
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
        if s.get("rain 
