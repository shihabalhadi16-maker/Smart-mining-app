"""DRASTIC Sudan v22.0 - With Comparison & PDF"""
import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import datetime
import requests
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


def get_d_rating(d):
    if d < 0: raise ValueError("Negative")
    if d <= 1.5: return 10
    if d <= 4.6: return 9
    if d <= 9.1: return 7
    if d <= 15.2: return 5
    if d <= 22.9: return 3
    if d <= 30.5: return 2
    return 1

def get_r_rating(r):
    if r < 0: raise ValueError("Negative")
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
    if t < 0: raise ValueError("Negative")
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
    if c < 0: raise ValueError("Negative")
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
    if d <= 0: raise ValueError("Depth > 0")
    if not (0.01 < p < 0.60): raise ValueError("Porosity")
    if k <= 0: raise ValueError("K > 0")
    v = (k * g) / p
    days = d / v
    return {"days": round(days, 2), "years": round(days / 365.25, 3),
            "velocity": round(v, 6)}

def mitigate(idx, hdpe=False, treatment=False, monitoring=False):
    m = float(idx)
    if hdpe: m *= 0.40
    if treatment: m *= 0.60
    if monitoring: m *= 0.85
    red = ((idx - m) / idx * 100) if idx > 0 else 0.0
    methods = []
    if hdpe: methods.append("HDPE Liner")
    if treatment: methods.append("Cyanide Treatment")
    if monitoring: methods.append("Monitoring Wells")
    return {"mitigated_index": round(m, 1),
            "reduction_pct": round(red, 1), "methods": methods}


def sensitivity_analysis(D, R, A, S, T, I, C, variation=0.10):
    base_idx = calc_index(D, R, A, S, T, I, C)
    base_vals = {"D": D, "R": R, "A": A, "S": S, "T": T, "I": I, "C": C}
    results = {}
    for param, val in base_vals.items():
        new_val = max(1, min(10, val * (1 + variation)))
        modified = dict(base_vals)
        modified[param] = new_val
        new_idx = calc_index(**modified)
        change = new_idx - base_idx
        results[param] = {
            "original": val,
            "modified": round(new_val, 2),
            "new_index": new_idx,
            "change": change,
            "sensitivity": round(abs(change) / base_idx * 100, 3) if base_idx > 0 else 0,
        }
    sorted_results = dict(sorted(results.items(),
                                  key=lambda x: x[1]["sensitivity"],
                                  reverse=True))
    return {
        "base_index": base_idx,
        "variation": variation,
        "parameters": sorted_results,
        "most_sensitive": list(sorted_results.keys())[0] if sorted_results else None,
    }


def get_rainfall(lat, lon, years=3):
    try:
        end_date = datetime.datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.datetime.now() - timedelta(days=365*years)).strftime('%Y-%m-%d')
        r = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={"latitude": lat, "longitude": lon,
                    "start_date": start_date, "end_date": end_date,
                    "daily": "precipitation_sum",
                    "timezone": "Africa/Khartoum"},
            timeout=30)
        data = r.json()
        daily = data.get("daily", {}).get("precipitation_sum", [])
        vals = [v for v in daily if v is not None]
        if not vals: return None
        return round(sum(vals) / years, 1)
    except Exception:
        return None

def get_temperature(lat, lon, years=3):
    try:
        end_date = datetime.datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.datetime.now() - timedelta(days=365*years)).strftime('%Y-%m-%d')
        r = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={"latitude": lat, "longitude": lon,
                    "start_date": start_date, "end_date": end_date,
                    "daily": "temperature_2m_mean",
                    "timezone": "Africa/Khartoum"},
            timeout=30)
        data = r.json()
        temps = data.get("daily", {}).get("temperature_2m_mean", [])
        vals = [v for v in temps if v is not None]
        if not vals: return None
        return round(sum(vals) / len(vals), 1)
    except Exception:
        return None

def classify_aridity(rain):
    if rain is None: return "غير محدد"
    if rain < 100: return "صحراوي"
    if rain < 250: return "شبه جاف"
    if rain < 500: return "شبه رطب"
    return "رطب"

def estimate_recharge(rain, soil="sand"):
    if rain is None: return None
    ratios = {"sand": 0.20, "sandy_loam": 0.15, "loam": 0.12,
              "silty_loam": 0.10, "clay_loam": 0.07, "nonshrinking_clay": 0.04}
    return round(rain * ratios.get(soil, 0.12), 1)

def fetch_satellite_data(lat, lon, years=3):
    rain = get_rainfall(lat, lon, years)
    temp = get_temperature(lat, lon, years)
    return {
        "rainfall_mm": rain,
        "temperature_c": temp,
        "aridity": classify_aridity(rain),
        "ndvi_estimated": round(min(0.7, max(0.05, (rain or 0) / 1000.0)), 3) if rain else None,
        "source": "ERA5 (ECMWF) via Open-Meteo",
        "period": str(years) + " سنوات",
    }


TEMPLATES = {
    "low": {"level": "منخفض", "range": "23-99",
        "assessment": "خطورة منخفضة. حماية جيدة.",
        "recs": ["المراقبة السنوية.", "فحص سنوي للمياه.", "توثيق التغييرات.",
                 "التزام PPE.", "الإبلاغ عن الحوادث."]},
    "moderate": {"level": "متوسط", "range": "100-139",
        "assessment": "خطورة متوسطة. احتمال تسرب.",
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

def gen_report(site, coords, idx, ratings, values, travel=None, sat=None):
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
        L.append("  المصدر: " + str(sat.get("source")))
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
         "<style>"
         "body{font-family:Arial;direction:rtl;text-align:right;"
         "padding:30px;max-width:900px;margin:auto;line-height:1.9;}"
         "pre{white-space:pre-wrap;background:#f8f9fa;padding:25px;"
         "border-radius:8px;font-family:inherit;}"
         "@media print{body{background:#fff;padding:0;}pre{"
         "background:#fff;padding:0;border:none;}}"
         "</style></head><body><pre>" + rep +
         "</pre>"
         "<div style='text-align:center;margin-top:30px;color:#666;"
         "font-size:12px;'>"
         "لحفظ كـ PDF: Ctrl+P ثم Save as PDF"
         "</div>"
         "</body></html>")


st.title("نظام التقييم البيئي للتعدين")
st.markdown("### جامعة الخرطوم - كلية الهندسة")
st.markdown("#### DRASTIC Sudan v22.0")
st.markdown("---")

if DS_OK:
    preset = get_preset_locations_for_app()
    summary = get_data_summary()
else:
    preset = {"موقع تجريبي": {"coords": (19.53, 33.32),
              "depth": 15.0, "conductivity": 5.0, "source": "افتراضي"}}
    summary = {"Total Data Points": 1}

t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs([
    "المدخلات والنتائج", "الجماعي", "الحلول",
    "التقرير", "الخريطة", "الدقة", "تحليل الحساسية", "مقارنة موقعين"
])


with t1:
    st.header("اختيار الموقع والمدخلات")
    site = st.selectbox("اختر الموقع:", list(preset.keys()))
    sd = preset[site]
    st.caption("المصدر: " + sd.get("source", "غير محدد"))

    st.markdown("---")
    st.subheader("بيانات الاقمار الصناعية (ERA5)")
    st.caption("المصدر: ERA5 (ECMWF) عبر Open-Meteo")

    if st.button("جلب البيانات من Open-Meteo", key="fetch_sat"):
        with st.spinner("جاري جلب البيانات..."):
            sat_data = fetch_satellite_data(sd["coords"][0], sd["coords"][1], years=3)
            st.session_state["sat_data"] = sat_data

    if "sat_data" in st.session_state:
        s = st.session_state["sat_data"]
        if s.get("rainfall_mm") is None:
            st.warning("تعذر جلب البيانات.")
        else:
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("الامطار (مم/سنة)", s["rainfall_mm"])
            sc2.metric("الحرارة (C)", s["temperature_c"])
            sc3.metric("NDVI مقدر", s["ndvi_estimated"])
            sc4.metric("المناخ", s["aridity"])
            st.caption("المصدر: " + s["source"] + " | الفترة: " + s["period"])
            rec_est = estimate_recharge(s["rainfall_mm"])
            st.info("التغذية المقدرة: " + str(rec_est) + " مم/سنة")

    st.markdown("---")
    st.subheader("المدخلات")

    c1, c2 = st.columns(2)
    with c1:
        depth = st.slider("D - العمق (م):", 0.5, 100.0, float(sd["depth"]), 0.5)
        recharge = st.slider("R - التغذية (مم/سنة):", 0.0, 400.0, 150.0, 10.0)
        slope = st.slider("T - الانحدار (%):", 0.0, 30.0, 4.0, 0.5)
        conductivity = st.slider("C - النفاذية (م/يوم):", 0.01, 100.0,
                                  float(sd["conductivity"]), 0.1)
    with c2:
        aquifer = st.selectbox("A - الخزان:", [
            "massive_sandstone", "sand_and_gravel", "karst_limestone",
            "basalt", "massive_shale"])
        soil = st.selectbox("S - التربة:", [
            "sand", "sandy_loam", "loam",
            "silty_loam", "clay_loam", "nonshrinking_clay"])
        vadose = st.selectbox("I - غير المشبعة:", [
            "sand_gravel", "sandstone", "limestone",
            "silt_clay", "shale"])
        porosity = st.slider("theta - المسامية:", 0.02, 0.55, 0.25, 0.01)

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
        st.header("النتائج للموقع: " + site)
        x1, x2, x3, x4 = st.columns(4)
        x1.metric("D", D_r)
        x2.metric("R", R_r)
        x3.metric("A", A_r)
        x4.metric("S", S_r)
        y1, y2, y3, y4 = st.columns(4)
        y1.metric("T", T_r)
        y2.metric("I", I_r)
        y3.metric("C", C_r)
        y4.metric("theta", round(porosity, 2))
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
    except ValueError as e:
        st.error("خطأ: " + str(e))


with t2:
    st.header("التقييم الجماعي")
    sample = pd.DataFrame({
        "name": ["A", "B"], "lat": [19.53, 18.12],
        "lon": [33.32, 33.99], "depth_m": [15.0, 10.0],
        "recharge_mm": [80.0, 120.0], "slope_pct": [4.0, 8.0],
        "conductivity": [5.0, 10.0],
        "aquifer": ["massive_sandstone", "sand_and_gravel"],
        "soil": ["sand", "sandy_loam"],
        "vadose": ["sand_gravel", "sandstone"]})
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
                results.append({
                    "Site": row.get("name", "Site " + str(i)),
                    "lat": row.get("lat", 0), "lon": row.get("lon", 0),
                    "Index": ix, "Level": rk["level"]})
            dfr = pd.DataFrame(results)
            st.dataframe(dfr, use_container_width=True)
            st.download_button("النتائج",
                data=dfr.to_csv(index=False).encode("utf-8-sig"),
                file_name="results.csv", mime="text/csv")
        except Exception as e:
            st.error("خطأ: " + str(e))


with t3:
    st.header("محاكي الحلول")
    if "ci" in st.session_state:
        cur_idx = st.session_state["ci"]
        cur_site = st.session_state["cs"]
        st.info("الموقع: " + cur_site + " | المؤشر: " + str(cur_idx))
        c1, c2 = st.columns(2)
        with c1:
            h = st.checkbox("HDPE Liner", key="mit_h")
            tr = st.checkbox("Cyanide Treatment", key="mit_t")
        with c2:
            mo = st.checkbox("Monitoring Wells", key="mit_m")
        if h or tr or mo:
            r = mitigate(cur_idx, h, tr, mo)
            a, b, c = st.columns(3)
            a.metric("قبل", cur_idx)
            b.metric("بعد", r["mitigated_index"])
            c.metric("التخفيض", str(r["reduction_pct"]) + " %")
            st.progress(min(r["reduction_pct"] / 100, 1.0))
            nr = classify(int(r["mitigated_index"]))
            st.metric("المستوى الجديد", nr["level"])
    else:
        st.warning("افتح تبويب المدخلات أولا")


with t4:
    st.header("توليد التقرير")
    if "ci" in st.session_state:
        cur_idx = st.session_state["ci"]
        cur_site = st.session_state["cs"]
        key = get_tpl_key(cur_idx)
        st.info("الموقع: " + cur_site + " | المؤشر: " + str(cur_idx))
        if st.button("توليد", type="primary", key="gen"):
            rep = gen_report(cur_site, st.session_state["cc"], cur_idx,
                            st.session_state["cr"], st.session_state["cv"],
                            st.session_state.get("ct"),
                            st.session_state.get("sat_data"))
            st.session_state["rep"] = rep
            st.success("تم التوليد")
        if "rep" in st.session_state:
            st.text_area("التقرير:", st.session_state["rep"], height=400)
            safe = cur_site.replace(" ", "_")
            cc1, cc2 = st.columns(2)
            with cc1:
                st.download_button("TXT",
                    data=("\ufeff" + st.session_state["rep"]).encode("utf-8"),
                    file_name="rep_" + safe + ".txt",
                    mime="text/plain; charset=utf-8",
                    use_container_width=True)
            with cc2:
                st.download_button("HTML",
                    data=gen_html(st.session_state["rep"], cur_site).encode("utf-8"),
                    file_name="rep_" + safe + ".html",
                    mime="text/html; charset=utf-8",
                    use_container_width=True)
            st.warning("يحتاج مراجعة بشرية")
    else:
        st.warning("افتح تبويب المدخلات أولا")


with t5:
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


with t6:
    st.header("الدقة الإحصائية")
    sample = pd.DataFrame({
        "name": ["A", "B", "C", "D"],
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
                cm = pd.DataFrame({
                    "Contaminated": [tp, fn],
                    "Clean": [fp, tn]},
                    index=["Predicted Contaminated", "Predicted Clean"])
                st.dataframe(cm)
            else:
                st.error("Need: drastic_index, actual_status")
        except Exception as e:
            st.error("خطأ: " + str(e))


with t7:
    st.header("تحليل الحساسية (Sensitivity Analysis)")
    st.markdown("**الغرض:** تحديد المعاملات الأكثر تأثيراً على مؤشر DRASTIC.")

    if "ci" in st.session_state:
        ratings = st.session_state["cr"]
        D_r = ratings["D"]
        R_r = ratings["R"]
        A_r = ratings["A"]
        S_r = ratings["S"]
        T_r = ratings["T"]
        I_r = ratings["I"]
        C_r = ratings["C"]

        st.info("الموقع: " + st.session_state["cs"] +
                " | المؤشر الأساسي: " + str(st.session_state["ci"]))

        variation = st.slider("نسبة التغيير لكل معامل (%):",
                              5, 30, 10, 5) / 100.0

        result = sensitivity_analysis(D_r, R_r, A_r, S_r,
                                       T_r, I_r, C_r, variation)

        st.markdown("---")
        st.subheader("المعاملات مرتبة حسب التأثير")

        for param in result["parameters"]:
            p = result["parameters"][param]
            weight = {"D": 5, "R": 4, "A": 3, "S": 2,
                      "T": 1, "I": 5, "C": 3}[param]
            with st.expander("**" + param + "** — الوزن " + str(weight) +
                             " (التأثير: " + str(p["sensitivity"]) + "%)"):
                c1, c2, c3 = st.columns(3)
                c1.metric("الأصلي", p["original"])
                c2.metric("المعدل (+" + str(int(variation*100)) + "%)",
                          p["modified"])
                c3.metric("التغير في المؤشر", str(p["change"]))

        st.markdown("---")
        st.success("**المعامل الأكثر تأثيراً: " +
                   str(result["most_sensitive"]) + "**")

        chart_data = pd.DataFrame({
            "المعامل": list(result["parameters"].keys()),
            "الحساسية (%)": [result["parameters"][p]["sensitivity"]
                             for p in result["parameters"]]
        })
        st.bar_chart(chart_data.set_index("المعامل"))
    else:
        st.warning("افتح تبويب المدخلات أولا")


with t8:
    st.header("مقارنة موقعين")
    st.markdown("**اختر موقعين، عدّل المدخلات، ثم شاهد الفرق.**")

    if DS_OK:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("الموقع الأول")
            site_a = st.selectbox("اختر:", list(preset.keys()), key="site_a")
            sd_a = preset[site_a]
            depth_a = st.slider("D (م):", 0.5, 100.0, float(sd_a["depth"]), 0.5, key="d_a")
            recharge_a = st.slider("R (مم):", 0.0, 400.0, 150.0, 10.0, key="r_a")
            slope_a = st.slider("T (%):", 0.0, 30.0, 4.0, 0.5, key="t_a")
            cond_a = st.slider("C (م/يوم):", 0.01, 100.0, float(sd_a["conductivity"]), 0.1, key="c_a")
            aq_a = st.selectbox("A:", ["massive_sandstone", "sand_and_gravel",
                "karst_limestone", "basalt", "massive_shale"], key="aq_a")
            soil_a = st.selectbox("S:", ["sand", "sandy_loam", "loam",
                "silty_loam", "clay_loam", "nonshrinking_clay"], key="so_a")
            vd_a = st.selectbox("I:", ["sand_gravel", "sandstone", "limestone",
                "silt_clay", "shale"], key="vd_a")

        with c2:
            st.subheader("الموقع الثاني")
            site_b = st.selectbox("اختر:", list(preset.keys()), key="site_b")
            sd_b = preset[site_b]
            depth_b = st.slider("D (م):", 0.5, 100.0, float(sd_b["depth"]), 0.5, key="d_b")
            recharge_b = st.slider("R (مم):", 0.0, 400.0, 150.0, 10.0, key="r_b")
            slope_b = st.slider("T (%):", 0.0, 30.0, 4.0, 0.5, key="t_b")
            cond_b = st.slider("C (م/يوم):", 0.01, 100.0, float(sd_b["conductivity"]), 0.1, key="c_b")
            aq_b = st.selectbox("A:", ["massive_sandstone", "sand_and_gravel",
                "karst_limestone", "basalt", "massive_shale"], key="aq_b")
            soil_b = st.selectbox("S:", ["sand", "sandy_loam", "loam",
                "silty_loam", "clay_loam", "nonshrinking_clay"], key="so_b")
            vd_b = st.selectbox("I:", ["sand_gravel", "sandstone", "limestone",
                "silt_clay", "shale"], key="vd_b")

        try:
            D_a = get_d_rating(depth_a)
            R_a = get_r_rating(recharge_a)
            A_a = get_a_rating(aq_a)
            S_a = get_s_rating(soil_a)
            T_a = get_t_rating(slope_a)
            I_a = get_i_rating(vd_a)
            C_a = get_c_rating(cond_a)
            idx_a = calc_index(D_a, R_a, A_a, S_a, T_a, I_a, C_a)
            risk_a = classify(idx_a)

            D_b = get_d_rating(depth_b)
            R_b = get_r_rating(recharge_b)
            A_b = get_a_rating(aq_b)
            S_b = get_s_rating(soil_b)
            T_b = get_t_rating(slope_b)
            I_b = get_i_rating(vd_b)
            C_b = get_c_rating(cond_b)
            idx_b = calc_index(D_b, R_b, A_b, S_b, T_b, I_b, C_b)
            risk_b = classify(idx_b)

            st.markdown("---")
            st.header("النتائج المقارنة")

            m1, m2, m3 = st.columns(3)
            m1.metric(site_a, str(idx_a) + " / 230", risk_a["level"])
            m2.metric("الفرق", str(abs(idx_a - idx_b)),
                      "أعلى: " + (site_a if idx_a > idx_b else site_b))
            m3.metric(site_b, str(idx_b) + " / 230", risk_b["level"])

            st.markdown("---")
            st.subheader("جدول تفصيلي")

            comparison = pd.DataFrame({
                "المعامل": ["D (العمق)", "R (التغذية)", "A (الخزان)",
                            "S (التربة)", "T (الانحدار)", "I (غير المشبعة)",
                            "C (النفاذية)"],
                site_a: [D_a, R_a, A_a, S_a, T_a, I_a, C_a],
                site_b: [D_b, R_b, A_b, S_b, T_b, I_b, C_b],
                "الفرق": [D_a - D_b, R_a - R_b, A_a - A_b,
                          S_a - S_b, T_a - T_b, I_a - I_b, C_a - C_b],
            })
            st.dataframe(comparison, use_container_width=True)

            st.markdown("---")
            st.subheader("الرسم البياني")
            chart_df = pd.DataFrame({
                "المعامل": comparison["المعامل"],
                site_a: comparison[site_a],
                site_b: comparison[site_b],
            }).set_index("المعامل")
            st.bar_chart(chart_df)

            st.markdown("---")
            st.subheader("الخلاصة")

            if idx_a > idx_b:
                st.error("**" + site_a + "** أكثر خطورة بمقدار " +
                         str(idx_a - idx_b) + " نقطة")
            elif idx_b > idx_a:
                st.error("**" + site_b + "** أكثر خطورة بمقدار " +
                         str(idx_b - idx_a) + " نقطة")
            else:
                st.info("الموقعان متساويان في المؤشر")

            st.markdown("---")
            st.subheader("تصدير المقارنة")

            html_comp = (
                "<!DOCTYPE html><html dir='rtl' lang='ar'><head>"
                "<meta charset='UTF-8'><title>مقارنة</title>"
                "<style>body{font-family:Arial;direction:rtl;"
                "text-align:right;padding:30px;max-width:900px;"
                "margin:auto;line-height:1.9;}"
                "table{width:100%;border-collapse:collapse;margin:20px 0;}"
                "th,td{border:1px solid #ddd;padding:10px;text-align:center;}"
                "th{background:#f0f0f0;}"
                "@media print{body{background:#fff;padding:0;}}"
                "</style></head><body>"
                "<h1>تقرير مقارنة موقعين</h1>"
                "<h2>" + site_a + " vs " + site_b + "</h2>"
                "<p><strong>" + site_a + ":</strong> " +
                str(idx_a) + "/230 — " + risk_a["level"] + "</p>"
                "<p><strong>" + site_b + ":</strong> " +
                str(idx_b) + "/230 — " + risk_b["level"] + "</p>"
                "<table><tr><th>المعامل</th><th>" + site_a +
                "</th><th>" + site_b + "</th><th>الفرق</th></tr>" +
                "<tr><td>D</td><td>" + str(D_a) + "</td><td>" + str(D_b) +
                "</td><td>" + str(D_a - D_b) + "</td></tr>" +
                "<tr><td>R</td><td>" + str(R_a) + "</td><td>" + str(R_b) +
                "</td><td>" + str(R_a - R_b) + "</td></tr>" +
                "<tr><td>A</td><td>" + str(A_a) + "</td><td>" + str(A_b) +
                "</td><td>" + str(A_a - A_b) + "</td></tr>" +
                "<tr><td>S</td><td>" + str(S_a) + "</td><td>" + str(S_b) +
                "</td><td>" + str(S_a - S_b) + "</td></tr>" +
                "<tr><td>T</td><td>" + str(T_a) + "</td><td>" + str(T_b) +
                "</td><td>" + str(T_a - T_b) + "</td></tr>" +
                "<tr><td>I</td><td>" + str(I_a) + "</td><td>" + str(I_b) +
                "</td><td>" + str(I_a - I_b) + "</td></tr>" +
                "<tr><td>C</td><td>" + str(C_a) + "</td><td>" + str(C_b) +
                "</td><td>" + str(C_a - C_b) + "</td></tr>" +
                "<tr><th>المؤشر</th><th>" + str(idx_a) +
                "</th><th>" + str(idx_b) + "</th><th>" +
                str(abs(idx_a - idx_b)) + "</th></tr></table>"
                "<p style='text-align:center;margin-top:30px;color:#666;"
                "font-size:12px;'>لحفظ كـ PDF: Ctrl+P ثم Save as PDF</p>"
                "</body></html>"
            )

            st.download_button("تحميل المقارنة (HTML/PDF)",
                data=html_comp.encode("utf-8"),
                file_name="comparison.html",
                mime="text/html; charset=utf-8",
                use_container_width=True,
                key="dl_compare")

            st.info("افتح الملف في المتصفح ثم Ctrl+P → Save as PDF")
        except ValueError as e:
            st.error("خطأ: " + str(e))
    else:
        st.warning("data_sources.py غير متوفر")


st.markdown("---")
st.caption("2026 University of Khartoum - DRASTIC Sudan v22.0")
