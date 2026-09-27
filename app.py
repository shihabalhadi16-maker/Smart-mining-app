"""DRASTIC Sudan v26.0 - All Features in One File"""
import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import datetime
import requests
import json
from datetime import timedelta

st.set_page_config(page_title="DRASTIC Sudan", page_icon="", layout="wide")

try:
    from data_sources import (
        get_preset_locations_for_app, get_data_summary,
        KNOWN_MINING_SITES, NARIS_WELLS, DARFUR_WELLS, KHARTOUM_LOCALITIES,
    )
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
    m = {"massive_shale": 2, "metamorphic_igneous": 3,
         "weathered_metamorphic_igneous": 4, "thin_bedded_sequences": 6,
         "massive_sandstone": 6, "massive_limestone": 6,
         "sand_and_gravel": 8, "basalt": 9, "karst_limestone": 10}
    return m.get(a, 6)

def get_s_rating(s):
    m = {"thin_or_absent": 10, "gravel": 10, "sand": 9, "peat": 8,
         "shrinking_aggregated_clay": 7, "sandy_loam": 6, "loam": 5,
         "silty_loam": 4, "clay_loam": 3, "muck": 2, "nonshrinking_clay": 1}
    return m.get(s, 5)

def get_t_rating(t):
    if t < 0: raise ValueError("Neg")
    if t <= 2.0: return 10
    if t <= 6.0: return 9
    if t <= 12.0: return 5
    if t <= 18.0: return 3
    return 1

def get_i_rating(i):
    m = {"confining_layer": 1, "silt_clay": 1, "shale": 3,
         "metamorphic_igneous": 4, "limestone": 6, "sandstone": 6,
         "sand_gravel_silt_clay": 6, "sand_gravel": 8,
         "basalt": 9, "karst_limestone": 10}
    return m.get(i, 6)

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
    return {"mitigated_index": round(m, 1), "reduction_pct": round(red, 1),
            "methods": methods}

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
        res[p] = {"original": v, "modified": round(nv, 2), "new_index": ni,
                  "change": ch,
                  "sensitivity": round(abs(ch) / base * 100, 3) if base > 0 else 0}
    sr = dict(sorted(res.items(), key=lambda x: x[1]["sensitivity"], reverse=True))
    return {"base_index": base, "variation": variation, "parameters": sr,
            "most_sensitive": list(sr.keys())[0] if sr else None}


# ==================== Hg + CN ====================
def analyze_mercury(w, s):
    wl, sl = 0.006, 1.0
    wr, sr = w / wl, s / sl
    mr = max(wr, sr)
    if mr <= 1.0: lvl, col = "منخفض", "green"
    elif mr <= 3.0: lvl, col = "متوسط", "yellow"
    elif mr <= 10.0: lvl, col = "مرتفع", "orange"
    else: lvl, col = "مرتفع جدا", "red"
    return {"water": {"value": w, "limit": wl, "ratio": round(wr, 2),
                      "status": "safe" if w <= wl else "exceeded"},
            "soil": {"value": s, "limit": sl, "ratio": round(sr, 2),
                     "status": "safe" if s <= sl else "exceeded"},
            "toxicity_level": lvl, "toxicity_color": col, "max_ratio": round(mr, 2)}

def analyze_cyanide(w, s):
    wl, sl = 0.07, 10.0
    wr, sr = w / wl, s / sl
    mr = max(wr, sr)
    if mr <= 1.0: lvl, col = "منخفض", "green"
    elif mr <= 3.0: lvl, col = "متوسط", "yellow"
    elif mr <= 10.0: lvl, col = "مرتفع", "orange"
    else: lvl, col = "مرتفع جدا", "red"
    return {"water": {"value": w, "limit": wl, "ratio": round(wr, 2),
                      "status": "safe" if w <= wl else "exceeded"},
            "soil": {"value": s, "limit": sl, "ratio": round(sr, 2),
                     "status": "safe" if s <= sl else "exceeded"},
            "toxicity_level": lvl, "toxicity_color": col, "max_ratio": round(mr, 2)}

def weighted_toxicity(hgw, hgs, cnw, cns):
    hwr, hsr = hgw / 0.006, hgs / 1.0
    cwr, csr = cnw / 0.07, cns / 10.0
    w = (hwr * 0.40) + (hsr * 0.20) + (cwr * 0.30) + (csr * 0.10)
    if w <= 1.0: cat, col, act = "آمن", "green", "لا يتطلب تدخل"
    elif w <= 3.0: cat, col, act = "تحت المراقبة", "yellow", "مراقبة دورية"
    elif w <= 10.0: cat, col, act = "خطر", "orange", "تدخل عاجل"
    else: cat, col, act = "خطر داهم", "red", "إيقاف النشاط"
    return {"index": round(w, 2), "category": cat, "color": col, "action": act}

def generate_alerts(idx, hg=None, cn=None, tox=None):
    al = []
    if idx >= 180:
        al.append({"icon": "🔴", "msg": "DRASTIC مرتفع جدا (" + str(idx) + ")",
                   "act": "إيقاف النشاط فورا"})
    elif idx >= 140:
        al.append({"icon": "🟠", "msg": "DRASTIC مرتفع (" + str(idx) + ")",
                   "act": "تدخل عاجل"})
    elif idx >= 100:
        al.append({"icon": "🟡", "msg": "DRASTIC متوسط (" + str(idx) + ")",
                   "act": "مراقبة ربع سنوية"})
    if hg:
        if hg["water"]["status"] == "exceeded":
            al.append({"icon": "⚠️", "msg": "Hg مياه (" + str(hg["water"]["ratio"]) + "x)",
                       "act": "تحذير + مياه بديلة"})
        if hg["soil"]["status"] == "exceeded":
            al.append({"icon": "⚠️", "msg": "Hg تربة (" + str(hg["soil"]["ratio"]) + "x)",
                       "act": "معالجة"})
    if cn:
        if cn["water"]["status"] == "exceeded":
            al.append({"icon": "☠️", "msg": "CN مياه (" + str(cn["water"]["ratio"]) + "x)",
                       "act": "إخلاء + طوارئ"})
        if cn["soil"]["status"] == "exceeded":
            al.append({"icon": "☠️", "msg": "CN تربة (" + str(cn["soil"]["ratio"]) + "x)",
                       "act": "معالجة عاجلة"})
    if tox and tox["index"] > 10:
        al.append({"icon": "🚨", "msg": "مؤشر السمية: " + str(tox["index"]),
                   "act": "تدخل فوري"})
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
        if not v: return None
        return round(sum(v) / years, 1)
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
        if not v: return None
        return round(sum(v) / len(v), 1)
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


# ==================== History (session) ====================
def save_to_history(site, coords, idx, level, values, travel, sat, tox):
    if "history" not in st.session_state:
        st.session_state["history"] = []
    st.session_state["history"].append({
        "التاريخ": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "الموقع": str(site),
        "lat": coords[0] if coords else 0,
        "lon": coords[1] if coords else 0,
        "المؤشر": idx,
        "المستوى": level,
        "العمق": values.get("depth", ""),
        "التغذية": values.get("recharge", ""),
        "زمن الوصول": travel if travel else 0,
        "الأمطار": sat.get("rainfall_mm", 0) if sat else 0,
        "مؤشر السمية": tox.get("index", 0) if tox else 0,
    })

def get_history_df():
    if "history" not in st.session_state or not st.session_state["history"]:
        return pd.DataFrame()
    return pd.DataFrame(st.session_state["history"])


# ==================== GIS ====================
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

def sites_to_kml(sites, doc="DRASTIC Sudan"):
    kml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    kml += '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>\n'
    kml += '<name>' + doc + '</name>\n'
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
        "recs": ["المراقبة السنوية.", "فحص سنوي للمياه.", "توثيق التغييرات.",
                 "التزام PPE.", "الإبلاغ عن الحوادث."]},
    "moderate": {"level": "متوسط", "range": "100-139",
        "assessment": "خطورة متوسطة.",
        "recs": ["مراقبة ربع سنوية.", "2-3 آبار مراقبة.", "تحسين إدارة المخلفات.",
                 "معالجة السيانيد.", "خطة طوارئ.", "تدريب العمال."]},
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
    L = []
    L.append("=" * 60)
    L.append("تقرير تقييم هشاشة المياه الجوفية")
    L.append("جامعة الخرطوم - كلية الهندسة")
    L.append("=" * 60)
    L.append("")
    L.append("الرقم المرجعي: " + ref)
    L.append("التاريخ: " + today.strftime("%Y-%m-%d"))
    L.append("الموقع: " + str(site))
    L.append("الإحداثيات: " + str(coords[0]) + ", " + str(coords[1]))
    L.append("")
    L.append("مؤشر DRASTIC: " + str(idx) + " / 230")
    L.append("المستوى: " + tpl["level"] + " (" + tpl["range"] + ")")
    L.append("")
    L.append("D: " + str(values.get("depth", "N/A")))
    L.append("R: " + str(values.get("recharge", "N/A")))
    L.append("A: " + str(values.get("aquifer", "N/A")))
    L.append("S: " + str(values.get("soil", "N/A")))
    L.append("T: " + str(values.get("slope", "N/A")))
    L.append("I: " + str(values.get("vadose", "N/A")))
    L.append("C: " + str(values.get("conductivity", "N/A")))
    L.append("")
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
    L.append("")
    L.append("الامتثال: قانون التعدين 2015 - قانون البيئة 2001")
    L.append("المراجع: EPA/600/2-87/035, Fetter 2001, WHO 2022")
    L.append("")
    L.append("توقيع المهندس: _______________________")
    L.append("=" * 60)
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
st.title("⛏️ نظام التقييم البيئي للتعدين")
st.markdown("### جامعة الخرطوم - كلية الهندسة")
st.markdown("#### DRASTIC Sudan v26.0")
st.markdown("---")

if DS_OK:
    preset = get_preset_locations_for_app()
    summary = get_data_summary()
else:
    preset = {"موقع تجريبي": {"coords": (19.53, 33.32),
              "depth": 15.0, "conductivity": 5.0, "source": "افتراضي"}}
    summary = {"Total Data Points": 1}


# ==================== Tabs ====================
tabs = st.tabs(["📍 المدخلات", "📊 الجماعي", "🛡️ الحلول", "📄 التقرير",
                "🗺️ الخريطة", "📊 الدقة", "📈 الحساسية", "⚖️ مقارنة",
                "☠️ السمية", "📚 التاريخ", "🌍 GIS"])


# ==================== Tab 1 ====================
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
            st.info("التغذية المقدرة: " + str(estimate_recharge(s["rainfall_mm"])) + " مم/سنة")

    st.markdown("---")
    st.subheader("المدخلات")
    c1, c2 = st.columns(2)
    with c1:
        depth = st.slider("D (م):", 0.5, 100.0, float(sd["depth"]), 0.5)
        recharge = st.slider("R (مم):", 0.0, 400.0, 150.0, 10.0)
        slope = st.slider("T (%):", 0.0, 30.0, 4.0, 0.5)
        conductivity = st.slider("C (م/يوم):", 0.01, 100.0,
                                  float(sd["conductivity"]), 0.1)
    with c2:
        aquifer = st.selectbox("A:", ["massive_sandstone", "sand_and_gravel",
            "karst_limestone", "basalt", "massive_shale"])
        soil = st.selectbox("S:", ["sand", "sandy_loam", "loam",
            "silty_loam", "clay_loam", "nonshrinking_clay"])
        vadose = st.selectbox("I:", ["sand_gravel", "sandstone",
            "limestone", "silt_clay", "shale"])
        porosity = st.slider("θ:", 0.02, 0.55, 0.25, 0.01)

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
        travel = calc_travel(depth, porosity, conductivity)

        st.session_state["ci"] = idx
        st.session_state["cs"] = site
        st.session_state["cc"] = sd["coords"]
        st.session_state["cr"] = {"D": D_r, "R": R_r, "A": A_r,
            "S": S_r, "T": T_r, "I": I_r, "C": C_r}
        st.session_state["cv"] = {"depth": depth, "recharge": recharge,
            "aquifer": aquifer, "soil": soil, "slope": slope,
            "vadose": vadose, "conductivity": conductivity}
        st.session_state["ct"] = travel["years"]

        st.markdown("---")
        st.header("النتائج: " + site)
        x1, x2, x3, x4 = st.columns(4)
        x1.metric("D", D_r); x2.metric("R", R_r)
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
        st.subheader("زمن وصول الملوثات")
        w1, w2, w3 = st.columns(3)
        w1.metric("سنوات", travel["years"])
        w2.metric("أيام", travel["days"])
        w3.metric("السرعة", travel["velocity"])

        st.markdown("---")
        if st.button("💾 حفظ التقييم في التاريخ", key="save_hist"):
            save_to_history(site, sd["coords"], idx, risk["level"],
                            st.session_state["cv"], travel["years"],
                            st.session_state.get("sat_data"),
                            st.session_state.get("tox_result"))
            st.success("✅ تم الحفظ")
    except ValueError as e:
        st.error("خطأ: " + str(e))


# ==================== Tab 2 ====================
with tabs[1]:
    st.header("التقييم الجماعي")
    sample = pd.DataFrame({"name": ["A", "B"], "lat": [19.53, 18.12],
        "lon": [33.32, 33.99], "depth_m": [15.0, 10.0],
        "recharge_mm": [80.0, 120.0], "slope_pct": [4.0, 8.0],
        "conductivity": [5.0, 10.0],
        "aquifer": ["massive_sandstone", "sand_and_gravel"],
        "soil": ["sand", "sandy_loam"], "vadose": ["sand_gravel", "sandstone"]})
    st.download_button("نموذج CSV",
        data=sample.to_csv(index=False).encode("utf-8-sig"),
        file_name="template.csv", mime="text/csv")
    f = st.file_uploader("ارفع ملف:", type=["csv", "xlsx"], key="up")
    if f:
        try:
            df = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)
            results = []
            for i, row in df.iterrows():
                D = get_d_rating(float(row.get("depth_m", 15)))
                R = get_r_rating(float(row.get("recharge_mm", 100)))
                A = get_a_rating(str(row.get("aquifer", "massive_sandstone")))
                S = get_s_rating(str(row.get("soil", "sand")))
                T = get_t_rating(float(row.get("slope_pct", 4)))
                I = get_i_rating(str(row.get("vadose", "sand_gravel")))
                C = get_c_rating(float(row.get("conductivity", 5)))
                ix = calc_index(D, R, A, S, T, I, C)
                rk = classify(ix)
                results.append({"Site": row.get("name", "Site " + str(i)),
                    "lat": row.get("lat", 0), "lon": row.get("lon", 0),
                    "Index": ix, "Level": rk["level"]})
            dfr = pd.DataFrame(results)
            st.dataframe(dfr, use_container_width=True)
            st.download_button("النتائج",
                data=dfr.to_csv(index=False).encode("utf-8-sig"),
                file_name="results.csv", mime="text/csv")
        except Exception as e:
            st.error("خطأ: " + str(e))


# ==================== Tab 3 ====================
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
            st.metric("المستوى الجديد", classify(int(r["mitigated_index"]))["level"])
    else:
        st.warning("افتح تبويب المدخلات أولا")


# ==================== Tab 4 ====================
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


# ==================== Tab 5 ====================
with tabs[4]:
    st.header("الخريطة")
    m = folium.Map(location=[15.5, 32.5], zoom_start=6)
    if DS_OK:
        for n, d in NARIS_WELLS.items():
            folium.Marker([d["coords"][1], d["coords"][0]],
                popup=n, icon=folium.Icon(color="blue")).add_to(m)
        for n, d in DARFUR_WELLS.items():
            folium.Marker([d["coords"][1], d["coords"][0]],
                popup=n, icon=folium.Icon(color="green")).add_to(m)
        for n, d in KNOWN_MINING_SITES.items():
            col = "red" if d.get("cyanide_use") else "orange"
            folium.Marker([d["coords"][1], d["coords"][0]],
                popup=n, icon=folium.Icon(color=col)).add_to(m)
        for n, d in KHARTOUM_LOCALITIES.items():
            folium.CircleMarker([d["coords"][1], d["coords"][0]],
                radius=8, color="purple", fill=True, popup=n).add_to(m)
    st_folium(m, width=None, height=600, key="map")


# ==================== Tab 6 ====================
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


# ==================== Tab 7 ====================
with tabs[6]:
    st.header("تحليل الحساسية")
    if "ci" in st.session_state:
        r = st.session_state["cr"]
        st.info("الموقع: " + st.session_state["cs"] +
                " | المؤشر: " + str(st.session_state["ci"]))
        variation = st.slider("نسبة التغيير (%):", 5, 30, 10, 5) / 100.0
        result = sensitivity_analysis(r["D"], r["R"], r["A"], r["S"],
                                       r["T"], r["I"], r["C"], variation)
        for p in result["parameters"]:
            pd_ = result["parameters"][p]
            weight = {"D": 5, "R": 4, "A": 3, "S": 2, "T": 1, "I": 5, "C": 3}[p]
            with st.expander(p + " — وزن " + str(weight) +
                             " (تأثير: " + str(pd_["sensitivity"]) + "%)"):
                c1, c2, c3 = st.columns(3)
                c1.metric("الأصلي", pd_["original"])
                c2.metric("المعدل", pd_["modified"])
                c3.metric("التغير", pd_["change"])
        st.success("الأكثر تأثيراً: " + str(result["most_sensitive"]))
        chart = pd.DataFrame({
            "المعامل": list(result["parameters"].keys()),
            "الحساسية": [result["parameters"][p]["sensitivity"]
                        for p in result["parameters"]]}).set_index("المعامل")
        st.bar_chart(chart)
    else:
        st.warning("افتح تبويب المدخلات أولا")


# ==================== Tab 8 ====================
with tabs[7]:
    st.header("مقارنة موقعين")
    if DS_OK:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("الأول")
            sa = st.selectbox("اختر:", list(preset.keys()), key="sa")
            sda = preset[sa]
            da = st.slider("D:", 0.5, 100.0, float(sda["depth"]), 0.5, key="da")
            ra = st.slider("R:", 0.0, 400.0, 150.0, 10.0, key="ra")
            ta = st.slider("T:", 0.0, 30.0, 4.0, 0.5, key="ta")
            ca = st.slider("C:", 0.01, 100.0, float(sda["conductivity"]), 0.1, key="ca")
        with c2:
            st.subheader("الثاني")
            sb = st.selectbox("اختر:", list(preset.keys()), key="sb")
            sdb = preset[sb]
            db_ = st.slider("D:", 0.5, 100.0, float(sdb["depth"]), 0.5, key="db")
            rb = st.slider("R:", 0.0, 400.0, 150.0, 10.0, key="rb")
            tb = st.slider("T:", 0.0, 30.0, 4.0, 0.5, key="tb")
            cb = st.slider("C:", 0.01, 100.0, float(sdb["conductivity"]), 0.1, key="cb")

        Dra = get_d_rating(da); Rra = get_r_rating(ra)
        Ara = get_a_rating("massive_sandstone"); Sra = get_s_rating("sand")
        Tra = get_t_rating(ta); Ira = get_i_rating("sand_gravel")
        Cra = get_c_rating(ca)
        idxa = calc_index(Dra, Rra, Ara, Sra, Tra, Ira, Cra)

        Drb = get_d_rating(db_); Rrb = get_r_rating(rb)
        Arb = get_a_rating("massive_sandstone"); Srb = get_s_rating("sand")
        Trb = get_t_rating(tb); Irb = get_i_rating("sand_gravel")
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


# ==================== Tab 9 ====================
with tabs[8]:
    st.header("تحليل الزئبق والسيانيد")
    st.markdown("**المعايير:** WHO (2022) + Minamata + ICMC (2002)")

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
            st.session_state["hg_r"] = analyze_mercury(hgw, hgs)
            st.session_state["cn_r"] = analyze_cyanide(cnw, cns)
            st.session_state["tox_r"] = weighted_toxicity(hgw, hgs, cnw, cns)
            st.session_state["alerts_r"] = generate_alerts(
                ci, st.session_state["hg_r"], st.session_state["cn_r"],
                st.session_state["tox_r"])

        if "tox_r" in st.session_state:
            hg = st.session_state["hg_r"]
            cn = st.session_state["cn_r"]
            tox = st.session_state["tox_r"]
            alerts = st.session_state["alerts_r"]

            st.markdown("---")
            st.subheader("Hg")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("مياه", str(hg["water"]["value"]) + " mg/L",
                          "الحد: " + str(hg["water"]["limit"]))
                st.success("آمن") if hg["water"]["status"] == "safe" else st.error("تجاوز " + str(hg["water"]["ratio"]) + "x")
            with c2:
                st.metric("تربة", str(hg["soil"]["value"]) + " mg/kg",
                          "الحد: " + str(hg["soil"]["limit"]))
                st.success("آمن") if hg["soil"]["status"] == "safe" else st.error("تجاوز " + str(hg["soil"]["ratio"]) + "x")

            st.markdown("---")
            st.subheader("CN")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("مياه", str(cn["water"]["value"]) + " mg/L",
                          "الحد: " + str(cn["water"]["limit"]))
                st.success("آمن") if cn["water"]["status"] == "safe" else st.error("تجاوز " + str(cn["water"]["ratio"]) + "x")
            with c2:
                st.metric("تربة", str(cn["soil"]["value"]) + " mg/kg",
                          "الحد: " + str(cn["soil"]["limit"]))
                st.success("آمن") if cn["soil"]["status"] == "safe" else st.error("تجاوز " + str(cn["soil"]["ratio"]) + "x")

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


# ==================== Tab 10 ====================
with tabs[9]:
    st.header("📚 تاريخ التقييمات")
    df = get_history_df()
    if df.empty:
        st.info("لا توجد تقييمات محفوظة بعد.")
        st.markdown("**اذهب لتبويب المدخلات واضغط 'حفظ التقييم'.**")
    else:
        st.subheader("إحصائيات")
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

        st.markdown("---")
        st.download_button("📥 تصدير CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="history.csv", mime="text/csv")

        if st.button("مسح الكل", key="clr"):
            st.session_state["history"] = []
            st.rerun()


# ==================== Tab 11 ====================
with tabs[10]:
    st.header("🌍 تصدير GIS")
    st.markdown("**صدّر البيانات لـ QGIS / ArcGIS / Google Earth**")

    st.markdown("---")
    source = st.radio("المصدر:",
                      ["المواقع المدمجة", "سجل التقييمات"],
                      key="gis_src")

    sites = []
    if source == "المواقع المدمجة" and DS_OK:
        for name, data in preset.items():
            try:
                coords = data.get("coords", (0, 0))
                sites.append({"name": str(name), "lat": float(coords[0]),
                             "lon": float(coords[1]), "index": 0,
                             "level": "غير محدد"})
            except Exception:
                continue
        st.info("📌 " + str(len(sites)) + " موقع مدمج")
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
            st.info("📌 " + str(len(sites)) + " تقييم")
        else:
            st.warning("لا توجد تقييمات. اذهب لتبويب المدخلات واحفظ.")

    if sites:
        st.markdown("---")
        st.subheader("معاينة")
        st.dataframe(pd.DataFrame(sites), use_container_width=True)

        st.markdown("---")
        st.subheader("تحميل")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button("📄 GeoJSON",
                data=sites_to_geojson(sites).encode("utf-8"),
                file_name="drastic_sites.geojson",
                mime="application/geo+json",
                use_container_width=True, key="dl_gj")
        with c2:
            st.download_button("🌍 KML",
                data=sites_to_kml(sites).encode("utf-8"),
                file_name="drastic_sites.kml",
                mime="application/vnd.google-earth.kml+xml",
                use_container_width=True, key="dl_kml")
        with c3:
            st.download_button("📊 CSV",
                data=pd.DataFrame(sites).to_csv(index=False).encode("utf-8-sig"),
                file_name="drastic_sites.csv",
                mime="text/csv",
                use_container_width=True, key="dl_csv")

        st.markdown("---")
        st.markdown("""
        **كيف تستخدم:**
        - **QGIS:** GeoJSON → Add Vector Layer
        - **Google Earth:** KML → File → Open
        - **Excel:** CSV → افتح مباشرة
        """)


st.markdown("---")
st.caption("2026 University of Khartoum - DRASTIC Sudan v26.0") 
