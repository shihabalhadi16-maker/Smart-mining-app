"""DRASTIC Sudan v5.0 - Single File Version"""
import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import datetime

st.set_page_config(page_title="DRASTIC Sudan", page_icon="⛏️", layout="wide")

try:
    from data_sources import (
        get_preset_locations_for_app, get_data_summary,
        KNOWN_MINING_SITES, NARIS_WELLS, DARFUR_WELLS, KHARTOUM_LOCALITIES,
    )
    DS_OK = True
except ImportError:
    DS_OK = False


# === دوال DRASTIC ===
def get_d_rating(d):
    if d < 0: raise ValueError("سالب")
    if d <= 1.5: return 10
    if d <= 4.6: return 9
    if d <= 9.1: return 7
    if d <= 15.2: return 5
    if d <= 22.9: return 3
    if d <= 30.5: return 2
    return 1

def get_r_rating(r):
    if r < 0: raise ValueError("سالب")
    if r <= 50.8: return 1
    if r <= 101.6: return 3
    if r <= 177.8: return 6
    if r <= 254.0: return 8
    return 9

def get_a_rating(a):
    m = {"massive_shale": 2, "metamorphic_igneous": 3,
         "thin_bedded_sequences": 6, "massive_sandstone": 6,
         "massive_limestone": 6, "sand_and_gravel": 8,
         "basalt": 9, "karst_limestone": 10}
    return m.get(a, 6)

def get_s_rating(s):
    m = {"thin_or_absent": 10, "gravel": 10, "sand": 9, "peat": 8,
         "sandy_loam": 6, "loam": 5, "silty_loam": 4,
         "clay_loam": 3, "muck": 2, "nonshrinking_clay": 1}
    return m.get(s, 5)

def get_t_rating(t):
    if t < 0: raise ValueError("سالب")
    if t <= 2.0: return 10
    if t <= 6.0: return 9
    if t <= 12.0: return 5
    if t <= 18.0: return 3
    return 1

def get_i_rating(i):
    m = {"silt_clay": 1, "shale": 3, "limestone": 6, "sandstone": 6,
         "sand_gravel_silt_clay": 6, "sand_gravel": 8,
         "basalt": 9, "karst_limestone": 10}
    return m.get(i, 6)

def get_c_rating(c):
    if c < 0: raise ValueError("سالب")
    if c <= 4.074: return 1
    if c <= 12.222: return 2
    if c <= 28.518: return 4
    if c <= 40.740: return 6
    if c <= 81.480: return 8
    return 10

def calc_index(D, R, A, S, T, I, C):
    return (D*5) + (R*4) + (A*3) + (S*2) + (T*1) + (I*5) + (C*3)

def classify(idx):
    if idx >= 180:
        return {"level": "مرتفع جداً", "color": "red", "action": "معالجة فورية"}
    if idx >= 140:
        return {"level": "مرتفع", "color": "orange", "action": "مراقبة عاجلة"}
    if idx >= 100:
        return {"level": "متوسط", "color": "yellow", "action": "مراقبة دورية"}
    return {"level": "منخفض", "color": "green", "action": "مراقبة روتينية"}

def calc_travel(d, p, k, g=1.0):
    if d <= 0: raise ValueError("العمق > 0")
    if not (0.01 < p < 0.60): raise ValueError("المسامية خارج النطاق")
    if k <= 0: raise ValueError("النفاذية > 0")
    v = (k * g) / p
    days = d / v
    return {"days": days, "years": days / 365.25, "velocity": v}

def mitigate(idx, hdpe=False, treatment=False, monitoring=False):
    m = idx
    if hdpe: m *= 0.40
    if treatment: m *= 0.60
    if monitoring: m *= 0.85
    red = ((idx - m) / idx * 100) if idx > 0 else 0
    return {"mitigated_index": round(m, 1), "reduction_pct": round(red, 1),
            "methods": [x for x, v in [("HDPE Liner", hdpe),
                        ("Cyanide Treatment", treatment),
                        ("Monitoring Wells", monitoring)] if v]}


# === قوالب التقارير (مدمجة داخل app.py) ===
TEMPLATES = {
    "low": {
        "level": "منخفض", "range": "23-99",
        "assessment": "الموقع يُظهر خطورة منخفضة. الطبقات الجيولوجية توفر حماية جيدة للمياه الجوفية.",
        "recs": ["الاستمرار مع المراقبة السنوية.",
                 "فحص سنوي لجودة المياه الجوفية.",
                 "توثيق أي تغيير في المنشآت.",
                 "التزام العمال بمعدات الحماية الشخصية.",
                 "الإبلاغ الفوري عن أي حادث تلوث."]
    },
    "moderate": {
        "level": "متوسط", "range": "100-139",
        "assessment": "الموقع يُظهر خطورة متوسطة. هناك احتمال لتسرب الملوثات دون إجراءات وقائية.",
        "recs": ["إجراء مراقبة ربع سنوية.",
                 "تركيب 2-3 آبار مراقبة.",
                 "تحسين إدارة المخلفات التعدينية.",
                 "استخدام تقنيات معالجة السيانيد.",
                 "إعداد خطة استجابة للطوارئ.",
                 "تدريب العمال على السلامة البيئية."]
    },
    "high": {
        "level": "مرتفع", "range": "140-179",
        "assessment": "الموقع يُظهر خطورة مرتفعة. الطبقات الجيولوجية لا توفر حماية كافية. التدخل العاجل ضروري.",
        "recs": ["تركيب HDPE Liner تحت أحواض المعالجة.",
                 "إنشاء وحدة معالجة السيانيد.",
                 "حفر 4-6 آبار مراقبة.",
                 "مراقبة شهرية لجودة المياه.",
                 "إعداد دراسة أثر بيئي شاملة.",
                 "تقليل استخدام السيانيد.",
                 "إبلاغ المجلس الأعلى للبيئة."]
    },
    "very_high": {
        "level": "مرتفع جداً", "range": "180-230",
        "assessment": "الموقع يُظهر خطورة مرتفعة جداً. خطر داهم على مصادر مياه الشرب. التدخل الفوري إلزامي.",
        "recs": ["إيقاف النشاط التعديني مؤقتاً.",
                 "تركيب HDPE + معالجة سيانيد فورية.",
                 "حفر 8-10 آبار مراقبة.",
                 "مراقبة أسبوعية.",
                 "إخلاء المناطق السكنية القريبة إذا لزم.",
                 "إعداد تقرير طارئ للمجلس الأعلى للبيئة.",
                 "توفير مصادر مياه بديلة.",
                 "خطة إعادة تأهيل شاملة."]
    },
}


def get_tpl_key(idx):
    if idx >= 180: return "very_high"
    if idx >= 140: return "high"
    if idx >= 100: return "moderate"
    return "low"


def gen_report(site, coords, idx, ratings, values, travel=None):
    key = get_tpl_key(idx)
    tpl = TEMPLATES[key]
    today = datetime.date.today()
    ref = "GRAS-" + today.strftime("%Y%m%d") + "-" + key.upper()[:3]
    
    L = []
    L.append("=" * 60)
    L.append("تقرير تقييم هشاشة المياه الجوفية")
    L.append("جامعة الخرطوم - كلية الهندسة")
    L.append("مكتب الاستشارات الهندسية")
    L.append("=" * 60)
    L.append("")
    L.append("الرقم المرجعي: " + ref)
    L.append("التاريخ: " + today.strftime("%Y-%m-%d"))
    L.append("القالب: " + key.upper())
    L.append("")
    L.append("-" * 60)
    L.append("القسم 1: بيانات الموقع")
    L.append("-" * 60)
    L.append("الاسم: " + str(site))
    L.append("الإحداثيات: " + str(coords[0]) + ", " + str(coords[1]))
    L.append("")
    L.append("-" * 60)
    L.append("القسم 2: نتائج DRASTIC")
    L.append("-" * 60)
    L.append("المؤشر: " + str(idx) + " / 230")
    L.append("المستوى: " + tpl["level"] + " (" + tpl["range"] + ")")
    L.append("")
    L.append("D - العمق: " + str(values.get("depth", "N/A")))
    L.append("R - التغذية: " + str(values.get("recharge", "N/A")))
    L.append("A - الخزان: " + str(values.get("aquifer", "N/A")))
    L.append("S - التربة: " + str(values.get("soil", "N/A")))
    L.append("T - الانحدار: " + str(values.get("slope", "N/A")))
    L.append("I - غير المشبعة: " + str(values.get("vadose", "N/A")))
    L.append("C - النفاذية: " + str(values.get("conductivity", "N/A")))
    L.append("")
    if travel:
        L.append("زمن وصول الملوثات: " + str(round(travel, 2)) + " سنة")
        L.append("")
    L.append("-" * 60)
    L.append("القسم 3: التقييم الهيدروجيولوجي")
    L.append("-" * 60)
    L.append(tpl["assessment"])
    L.append("")
    L.append("-" * 60)
    L.append("القسم 4: التوصيات")
    L.append("-" * 60)
    for i, rec in enumerate(tpl["recs"], 1):
        L.append(str(i) + ". " + rec)
    L.append("")
    L.append("-" * 60)
    L.append("القسم 5: الامتثال التشريعي")
    L.append("-" * 60)
    L.append("- المادة (26) من قانون التعدين 2015")
    L.append("- قانون حماية البيئة 2001 (رقم 18)")
    L.append("- لائحة التعدين التقليدي 2016")
    L.append("- معايير WHO (2022)")
    L.append("")
    L.append("-" * 60)
    L.append("القسم 6: المراجع")
    L.append("-" * 60)
    L.append("1. Aller et al. (1987). EPA/600/2-87/035")
    L.append("2. Fetter (2001). Applied Hydrogeology, 4th ed.")
    L.append("3. US EPA (1993). EPA/600/R-93/174")
    L.append("4. WHO (2022). Drinking-water Quality Guidelines")
    L.append("")
    L.append("-" * 60)
    L.append("القسم 7: المراجعة والاعتماد")
    L.append("-" * 60)
    L.append("هذا التقرير مُولَّد آلياً. لا يُعتمد رسمياً إلا بعد")
    L.append("مراجعة وتوقيع مهندس مختص.")
    L.append("")
    L.append("اسم المهندس: _______________________")
    L.append("الرقم الوظيفي: _______________________")
    L.append("التاريخ: ___/___/______")
    L.append("التوقيع: _______________________")
    L.append("")
    L.append("=" * 60)
    L.append("جامعة الخرطوم - 2026")
    L.append("=" * 60)
    return "\n".join(L)


# === الواجهة ===
st.title("⛏️ نظام التقييم البيئي للتعدين")
st.markdown("### جامعة الخرطوم - كلية الهندسة")
st.markdown("#### DRASTIC Sudan v5.0")
st.markdown("---")

if DS_OK:
    preset = get_preset_locations_for_app()
    summary = get_data_summary()
    with st.sidebar:
        st.markdown("### 📊 البيانات")
        st.metric("المواقع", summary["Total Data Points"])
        st.metric("NARIS", summary["NARIS Wells"])
        st.metric("دارفور", summary["Darfur Wells"])
        st.metric("تعدين", summary["Known Mining Sites"])
else:
    preset = {"موقع تجريبي": {"coords": (19.53, 33.32),
              "depth": 15.0, "conductivity": 5.0, "source": "افتراضي"}}


tabs = st.tabs(["📍 التقييم", "📊 الجماعي (A)", "🛡️ الحلول (C)",
                "📄 التقرير", "🗺️ الخريطة"])


# === TAB 1 ===
with tabs[0]:
    st.header("⚙️ اختيار الموقع والمدخلات")
    site = st.selectbox("الموقع:", list(preset.keys()))
    sd = preset[site]
    st.caption("المصدر: " + sd.get("source", "غير محدد"))

    c1, c2 = st.columns(2)
    with c1:
        depth = st.slider("D - العمق (م):", 0.5, 100.0, float(sd["depth"]), 0.5)
        recharge = st.slider("R - التغذية (مم/سنة):", 0.0, 400.0, 150.0, 10.0)
        slope = st.slider("T - الانحدار (%):", 0.0, 30.0, 4.0, 0.5)
        conductivity = st.slider("C - النفاذية (م/يوم):", 0.01, 100.0,
                                  float(sd["conductivity"]), 0.1)
    with c2:
        aquifer = st.selectbox("A - الخزان:",
            ["massive_sandstone", "sand_and_gravel", "karst_limestone",
             "basalt", "massive_shale"])
        soil = st.selectbox("S - التربة:",
            ["sand", "sandy_loam", "loam", "silty_loam",
             "clay_loam", "nonshrinking_clay"])
        vadose = st.selectbox("I - غير المشبعة:",
            ["sand_gravel", "sandstone", "limestone", "silt_clay", "shale"])
        porosity = st.slider("θ - المسامية:", 0.02, 0.55, 0.25, 0.01)

    try:
        D_r = get_d_rating(depth); R_r = get_r_rating(recharge)
        A_r = get_a_rating(aquifer); S_r = get_s_rating(soil)
        T_r = get_t_rating(slope); I_r = get_i_rating(vadose)
        C_r = get_c_rating(conductivity)
        idx = calc_index(D_r, R_r, A_r, S_r, T_r, I_r, C_r)
        risk = classify(idx)

        st.session_state["idx"] = idx
        st.session_state["site"] = site
        st.session_state["coords"] = sd["coords"]
        st.session_state["ratings"] = {"D": D_r, "R": R_r, "A": A_r,
            "S": S_r, "T": T_r, "I": I_r, "C": C_r}
        st.session_state["values"] = {"depth": depth, "recharge": recharge,
            "aquifer": aquifer, "soil": soil, "slope": slope,
            "vadose": vadose, "conductivity": conductivity}

        st.markdown("---")
        st.header("🎯 النتائج")
        x1, x2, x3, x4 = st.columns(4)
        x1.metric("D", D_r); x2.metric("R", R_r)
        x3.metric("A", A_r); x4.metric("S", S_r)
        x5, x6, x7, x8 = st.columns(4)
        x5.metric("T", T_r); x6.metric("I", I_r)
        x7.metric("C", C_r); x8.metric("θ", round(porosity, 2))
        st.markdown("---")
        y1, y2 = st.columns(2)
        y1.metric("📊 المؤشر", str(idx) + " / 230")
        y2.metric("⚠️ المستوى", risk["level"])
        if risk["color"] == "red": st.error(risk["action"])
        elif risk["color"] == "orange": st.warning(risk["action"])
        elif risk["color"] == "yellow": st.info(risk["action"])
        else: st.success(risk["action"])

        travel = calc_travel(depth, porosity, conductivity)
        st.session_state["travel"] = travel["years"]
        st.markdown("---")
        st.subheader("⏱️ زمن وصول الملوثات")
        t1, t2, t3 = st.columns(3)
        t1.metric("سنوات", round(travel["years"], 2))
        t2.metric("أيام", round(travel["days"], 1))
        t3.metric("سرعة التسرب", round(travel["velocity"], 6))
    except ValueError as e:
        st.error("خطأ: " + str(e))


# === TAB 2 ===
with tabs[1]:
    st.header("📊 التقييم الجماعي")
    sample = pd.DataFrame({
        "name": ["موقع 1", "موقع 2"], "lat": [19.53, 18.12],
        "lon": [33.32, 33.99], "depth_m": [15.0, 10.0],
        "recharge_mm": [80.0, 120.0], "slope_pct": [4.0, 8.0],
        "conductivity": [5.0, 10.0],
        "aquifer": ["massive_sandstone", "sand_and_gravel"],
        "soil": ["sand", "sandy_loam"], "vadose": ["sand_gravel", "sandstone"],
    })
    st.download_button("📥 نموذج CSV",
        data=sample.to_csv(index=False).encode("utf-8-sig"),
        file_name="template.csv", mime="text/csv")

    f = st.file_uploader("ارفع ملف:", type=["csv", "xlsx"])
    if f:
        try:
            df = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)
            results = []
            for i, row in df.iterrows():
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
                    results.append({"الموقع": row.get("name", "موقع " + str(i)),
                        "lat": row.get("lat", 0), "lon": row.get("lon", 0),
                        "المؤشر": ix, "المستوى": rk["level"]})
                except Exception as e:
                    st.warning("خطأ سطر " + str(i) + ": " + str(e))
            if results:
                dfr = pd.DataFrame(results)
                st.markdown("---")
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("الإجمالي", len(dfr))
                k2.metric("المتوسط", round(dfr["المؤشر"].mean(), 1))
                k3.metric("الأعلى", dfr["المؤشر"].max())
                k4.metric("خطرة", len(dfr[dfr["المؤشر"] >= 140]))
                st.dataframe(dfr, use_container_width=True)
                st.download_button("📥 النتائج CSV",
                    data=dfr.to_csv(index=False).encode("utf-8-sig"),
                    file_name="results.csv", mime="text/csv")
                try:
                    mb = folium.Map(location=[float(dfr["lat"].mean()),
                        float(dfr["lon"].mean())], zoom_start=6)
                    for _, r in dfr.iterrows():
                        col = ("red" if r["المؤشر"] >= 160 else
                               "orange" if r["المؤشر"] >= 120 else "green")
                        folium.Marker([r["lat"], r["lon"]],
                            popup=str(r["الموقع"]) + ": " + str(r["المؤشر"]),
                            icon=folium.Icon(color=col)).add_to(mb)
                    st_folium(mb, width=None, height=500, key="bulk")
                except Exception:
                    pass
        except Exception as e:
            st.error("خطأ: " + str(e))


# === TAB 3 ===
with tabs[2]:
    st.header("🛡️ محاكي الحلول")
    if "idx" not in st.session_state:
        st.warning("⚠️ اختر موقعاً أولاً من التبويب الأول.")
    else:
        base = st.session_state["idx"]
        st.info("الموقع: " + st.session_state["site"] + " | المؤشر: " + str(base))
        c1, c2 = st.columns(2)
        with c1:
            h = st.checkbox("HDPE Liner (خفض 60%)")
            tr = st.checkbox("معالجة السيانيد (خفض 40%)")
        with c2:
            mo = st.checkbox("آبار مراقبة (خفض 15%)")
        if h or tr or mo:
            r = mitigate(base, h, tr, mo)
            st.markdown("---")
            a, b, c = st.columns(3)
            a.metric("قبل", base); b.metric("بعد", r["mitigated_index"])
            c.metric("التخفيض", str(r["reduction_pct"]) + "%")
            st.progress(min(r["reduction_pct"] / 100, 1.0))
            nr = classify(int(r["mitigated_index"]))
            st.metric("المستوى الجديد", nr["level"])


# === TAB 4 ===
with tabs[3]:
    st.header("📄 توليد التقرير")
    if "idx" not in st.session_state:
        st.warning("⚠️ اختر موقعاً أولاً.")
    else:
        idx = st.session_state["idx"]
        site = st.session_state["site"]
        key = get_tpl_key(idx)
        st.info("الموقع: " + site + " | المؤشر: " + str(idx) + 
                " | القالب: " + key.upper())
        if st.button("📄 توليد التقرير", type="primary"):
            rep = gen_report(
                site=site,
                coords=st.session_state["coords"],
                idx=idx,
                ratings=st.session_state["ratings"],
                values=st.session_state["values"],
                travel=st.session_state.get("travel")
            )
            st.session_state["report"] = rep
            st.success("✅ تم التوليد")
        if "report" in st.session_state:
            st.text_area("التقرير:", st.session_state["report"], height=500)
            st.download_button("📥 تحميل",
                data=st.session_state["report"],
                file_name="report_" + site + ".txt", mime="text/plain")
            st.warning("⚠️ هذا تقرير آلي - يحتاج مراجعة بشرية.")


# === TAB 5 ===
with tabs[4]:
    st.header("🗺️ الخريطة")
    m = folium.Map(location=[15.5, 32.5], zoom_start=6)
    if DS_OK:
        for name, d in NARIS_WELLS.items():
            folium.Marker([d["coords"][1], d["coords"][0]],
                popup=name, icon=folium.Icon(color="blue")).add_to(m)
        for name, d in DARFUR_WELLS.items():
            folium.Marker([d["coords"][1], d["coords"][0]],
                popup=name, icon=folium.Icon(color="green")).add_to(m)
        for name, d in KNOWN_MINING_SITES.items():
            col = "red" if d.get("cyanide_use") else "orange"
            folium.Marker([d["coords"][1], d["coords"][0]],
                popup=name, icon=folium.Icon(color=col)).add_to(m)
        for name, d in KHARTOUM_LOCALITIES.items():
            folium.CircleMarker([d["coords"][1], d["coords"][0]],
                radius=8, color="purple", fill=True, popup=name).add_to(m)
    st_folium(m, width=None, height=600, key="m")


st.markdown("---")
st.caption("© 2026 جامعة الخرطوم - DRASTIC Sudan v5.0")
