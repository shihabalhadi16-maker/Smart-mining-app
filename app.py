"""DRASTIC Sudan v15.0 - Final Fixed Version"""
import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import datetime

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
    if idx >= 180:
        return {"level": "مرتفع جدا", "color": "red", "action": "معالجة فورية"}
    if idx >= 140:
        return {"level": "مرتفع", "color": "orange", "action": "مراقبة عاجلة"}
    if idx >= 100:
        return {"level": "متوسط", "color": "yellow", "action": "مراقبة دورية"}
    return {"level": "منخفض", "color": "green", "action": "مراقبة روتينية"}

def calc_travel(d, p, k, g=1.0):
    if d <= 0: raise ValueError("Depth > 0")
    if not (0.01 < p < 0.60): raise ValueError("Porosity")
    if k <= 0: raise ValueError("K > 0")
    v = (k * g) / p
    days = d / v
    return {"days": days, "years": days / 365.25, "velocity": v}

def mitigate(idx, hdpe=False, treatment=False, monitoring=False):
    m = idx
    if hdpe: m *= 0.40
    if treatment: m *= 0.60
    if monitoring: m *= 0.85
    red = ((idx - m) / idx * 100) if idx > 0 else 0
    methods = []
    if hdpe: methods.append("HDPE Liner")
    if treatment: methods.append("Cyanide Treatment")
    if monitoring: methods.append("Monitoring Wells")
    return {"mitigated_index": round(m, 1),
            "reduction_pct": round(red, 1),
            "methods": methods}

def calc_accuracy(preds, actuals):
    if len(preds) != len(actuals): raise ValueError("Mismatch")
    if len(preds) == 0: raise ValueError("Empty")
    tp = tn = fp = fn = 0
    for p, a in zip(preds, actuals):
        if p == 1 and a == 1: tp += 1
        elif p == 0 and a == 0: tn += 1
        elif p == 1 and a == 0: fp += 1
        else: fn += 1
    total = tp + tn + fp + fn
    acc = (tp + tn) / total * 100
    prec = (tp / (tp + fp) * 100) if (tp + fp) > 0 else 0
    rec = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0
    spec = (tn / (tn + fp) * 100) if (tn + fp) > 0 else 0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0
    po = (tp + tn) / total
    pe = ((tp + fp) * (tp + fn) + (tn + fn) * (tn + fp)) / (total ** 2)
    kappa = ((po - pe) / (1 - pe)) if (1 - pe) > 0 else 0
    return {"accuracy": round(acc, 2), "precision": round(prec, 2),
            "recall": round(rec, 2), "specificity": round(spec, 2),
            "f1": round(f1, 2), "kappa": round(kappa, 4),
            "tp": tp, "tn": tn, "fp": fp, "fn": fn, "total": total}

def interp_kappa(k):
    if k < 0.20: return "Poor"
    if k < 0.40: return "Fair"
    if k < 0.60: return "Moderate"
    if k < 0.80: return "Good"
    return "Excellent"

def interp_acc(a):
    if a >= 90: return "Excellent"
    if a >= 80: return "Very Good"
    if a >= 70: return "Good"
    if a >= 60: return "Acceptable"
    return "Poor"


TEMPLATES = {
    "low": {"level": "منخفض", "range": "23-99",
        "assessment": "الموقع يظهر خطورة منخفضة. الطبقات الجيولوجية توفر حماية جيدة.",
        "recs": ["الاستمرار مع المراقبة السنوية.",
                 "فحص سنوي لجودة المياه.",
                 "توثيق أي تغيير.",
                 "التزام العمال بمعدات الحماية.",
                 "الإبلاغ عن أي حادث."]},
    "moderate": {"level": "متوسط", "range": "100-139",
        "assessment": "الموقع يظهر خطورة متوسطة. احتمال لتسرب الملوثات.",
        "recs": ["مراقبة ربع سنوية.",
                 "تركيب 2-3 آبار مراقبة.",
                 "تحسين إدارة المخلفات.",
                 "استخدام تقنيات معالجة السيانيد.",
                 "خطة طوارئ.",
                 "تدريب العمال."]},
    "high": {"level": "مرتفع", "range": "140-179",
        "assessment": "خطورة مرتفعة. الطبقات لا توفر حماية كافية. التدخل العاجل ضروري.",
        "recs": ["تركيب HDPE Liner.",
                 "وحدة معالجة السيانيد.",
                 "حفر 4-6 آبار مراقبة.",
                 "مراقبة شهرية.",
                 "دراسة EIA.",
                 "تقليل السيانيد.",
                 "إبلاغ المجلس الأعلى للبيئة."]},
    "very_high": {"level": "مرتفع جدا", "range": "180-230",
        "assessment": "خطورة مرتفعة جدا. خطر داهم. التدخل الفوري إلزامي.",
        "recs": ["إيقاف النشاط مؤقتا.",
                 "HDPE ومعالجة سيانيد.",
                 "حفر 8-10 آبار مراقبة.",
                 "مراقبة أسبوعية.",
                 "إخلاء المناطق إذا لزم.",
                 "تقرير طارئ.",
                 "مصادر مياه بديلة.",
                 "خطة إعادة تأهيل."]},
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
    L.append("=" * 60)
    L.append("")
    L.append("الرقم المرجعي: " + ref)
    L.append("التاريخ: " + today.strftime("%Y-%m-%d"))
    L.append("القالب: " + key.upper())
    L.append("")
    L.append("القسم 1: بيانات الموقع")
    L.append("الاسم: " + str(site))
    L.append("الإحداثيات: " + str(coords[0]) + ", " + str(coords[1]))
    L.append("")
    L.append("القسم 2: نتائج DRASTIC")
    L.append("المؤشر: " + str(idx) + " / 230")
    L.append("المستوى: " + tpl["level"] + " (" + tpl["range"] + ")")
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
    L.append("القسم 3: التقييم الهيدروجيولوجي")
    L.append(tpl["assessment"])
    L.append("")
    L.append("القسم 4: التوصيات")
    for i, rec in enumerate(tpl["recs"], 1):
        L.append(str(i) + ". " + rec)
    L.append("")
    L.append("القسم 5: الامتثال التشريعي")
    L.append("- المادة 26 من قانون التعدين 2015")
    L.append("- قانون حماية البيئة 2001 رقم 18")
    L.append("- لائحة التعدين التقليدي 2016")
    L.append("- معايير WHO 2022")
    L.append("")
    L.append("القسم 6: المراجع")
    L.append("1. Aller et al. 1987 EPA/600/2-87/035")
    L.append("2. Fetter 2001 Applied Hydrogeology")
    L.append("3. US EPA 1993 EPA/600/R-93/174")
    L.append("4. WHO 2022 Drinking-water Quality")
    L.append("")
    L.append("القسم 7: المراجعة والاعتماد")
    L.append("هذا التقرير مولد آليا. لا يعتمد رسميا إلا بعد")
    L.append("مراجعة وتوقيع مهندس مختص.")
    L.append("")
    L.append("اسم المهندس: _______________________")
    L.append("التوقيع: _______________________")
    L.append("")
    L.append("=" * 60)
    L.append("2026 جامعة الخرطوم")
    L.append("=" * 60)
    return "\n".join(L)

def gen_html(rep, site):
    h = ("<!DOCTYPE html><html dir='rtl' lang='ar'><head>"
         "<meta charset='UTF-8'><title>" + site + "</title>"
         "<style>body{font-family:Arial;direction:rtl;text-align:right;"
         "padding:30px;max-width:900px;margin:auto;background:#f8f9fa;"
         "line-height:1.9;}pre{white-space:pre-wrap;background:#fff;"
         "padding:25px;border-radius:8px;border:1px solid #ddd;}"
         "</style></head><body><pre>" + rep + "</pre></body></html>")
    return h


st.title("نظام التقييم البيئي للتعدين")
st.markdown("### جامعة الخرطوم - كلية الهندسة")
st.markdown("#### DRASTIC Sudan v15.0")
st.markdown("---")

if DS_OK:
    preset = get_preset_locations_for_app()
    summary = get_data_summary()
else:
    preset = {"موقع تجريبي": {"coords": (19.53, 33.32),
              "depth": 15.0, "conductivity": 5.0, "source": "افتراضي"}}
    summary = {"Total Data Points": 1}


# ===== الشريط الجانبي =====
with st.sidebar:
    st.markdown("### اختيار الموقع")
    site = st.selectbox("الموقع:", list(preset.keys()), key="site_v150")
    sd = preset[site]
    st.caption("المصدر: " + sd.get("source", "غير محدد"))
    st.markdown("---")
    st.markdown("### المدخلات")
    
    # بدون key — يُعيد Streamlit قراءة القيم الافتراضية لكل موقع
    depth = st.slider("D - العمق (م):", 0.5, 100.0, float(sd["depth"]), 0.5)
    recharge = st.slider("R - التغذية:", 0.0, 400.0, 150.0, 10.0)
    slope = st.slider("T - الانحدار:", 0.0, 30.0, 4.0, 0.5)
    conductivity = st.slider("C - النفاذية:", 0.01, 100.0, float(sd["conductivity"]), 0.1)
    aquifer = st.selectbox("A - الخزان:",
        ["massive_sandstone", "sand_and_gravel", "karst_limestone",
         "basalt", "massive_shale"])
    soil = st.selectbox("S - التربة:",
        ["sand", "sandy_loam", "loam", "silty_loam",
         "clay_loam", "nonshrinking_clay"])
    vadose = st.selectbox("I - غير المشبعة:",
        ["sand_gravel", "sandstone", "limestone", "silt_clay", "shale"])
    porosity = st.slider("المسامية:", 0.02, 0.55, 0.25, 0.01)
    
    st.markdown("---")
    st.markdown("### ملخص البيانات")
    st.metric("المواقع", summary["Total Data Points"])


# ===== الحساب =====
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
    calc_error = None
except ValueError as e:
    idx = 0
    risk = {"level": "خطأ", "color": "red", "action": str(e)}
    travel = {"years": 0, "days": 0, "velocity": 0}
    D_r = R_r = A_r = S_r = T_r = I_r = C_r = 0
    calc_error = str(e)


# ===== عرض سريع =====
c1, c2, c3 = st.columns(3)
c1.metric("الموقع الحالي", site)
c2.metric("مؤشر DRASTIC", str(idx) + " / 230")
c3.metric("المستوى", risk["level"])
st.markdown("---")

if calc_error:
    st.error("خطأ: " + calc_error)


# ===== التبويبات =====
t1, t2, t3, t4, t5, t6 = st.tabs(["النتائج", "الجماعي", "الحلول", "التقرير", "الخريطة", "الدقة"])


with t1:
    st.header("نتائج التقييم للموقع: " + site)
    x1, x2, x3, x4 = st.columns(4)
    x1.metric("D", D_r)
    x2.metric("R", R_r)
    x3.metric("A", A_r)
    x4.metric("S", S_r)
    y1, y2, y3, y4 = st.columns(4)
    y1.metric("T", T_r)
    y2.metric("I", I_r)
    y3.metric("C", C_r)
    y4.metric("المسامية", round(porosity, 2))
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
    w1.metric("سنوات", round(travel["years"], 2))
    w2.metric("أيام", round(travel["days"], 1))
    w3.metric("السرعة", round(travel["velocity"], 6))


with t2:
    st.header("التقييم الجماعي")
    sample = pd.DataFrame({"name": ["A", "B"], "lat": [19.53, 18.12], "lon": [33.32, 33.99],
        "depth_m": [15.0, 10.0], "recharge_mm": [80.0, 120.0], "slope_pct": [4.0, 8.0],
        "conductivity": [5.0, 10.0], "aquifer": ["massive_sandstone", "sand_and_gravel"],
        "soil": ["sand", "sandy_loam"], "vadose": ["sand_gravel", "sandstone"]})
    st.download_button("تحميل نموذج", data=sample.to_csv(index=False).encode("utf-8-sig"),
        file_name="template.csv", mime="text/csv")
    f = st.file_uploader("ارفع ملف:", type=["csv", "xlsx"], key="up_v150")
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
            st.download_button("تحميل النتائج", data=dfr.to_csv(index=False).encode("utf-8-sig"),
                file_name="results.csv", mime="text/csv")
        except Exception as e:
            st.error("خطأ: " + str(e))


with t3:
    st.header("محاكي الحلول الهندسية")
    st.info("الموقع: " + site + " | المؤشر الحالي: " + str(idx))
    st.caption("HDPE = خفض 60 | المعالجة = خفض 40 | الآبار = خفض 15")
    c1, c2 = st.columns(2)
    with c1:
        h = st.checkbox("HDPE Liner", key="mit_hdpe_v150")
        tr = st.checkbox("Cyanide Treatment", key="mit_treat_v150")
    with c2:
        mo = st.checkbox("Monitoring Wells", key="mit_monitor_v150")
    if h or tr or mo:
        r = mitigate(idx, h, tr, mo)
        st.markdown("---")
        a, b, c = st.columns(3)
        a.metric("قبل", idx)
        b.metric("بعد", r["mitigated_index"])
        c.metric("التخفيض", str(r["reduction_pct"]) + " percent")
        st.progress(min(r["reduction_pct"] / 100, 1.0))
        nr = classify(int(r["mitigated_index"]))
        st.metric("المستوى الجديد", nr["level"])
        if nr["color"] == "green": st.success(nr["action"])
        elif nr["color"] == "yellow": st.info(nr["action"])
        elif nr["color"] == "orange": st.warning(nr["action"])
        else: st.error(nr["action"])


with t4:
    st.header("توليد التقرير")
    key = get_tpl_key(idx)
    st.info("الموقع: " + site + " | المؤشر: " + str(idx) + " | القالب: " + key.upper())
    if st.button("توليد التقرير", type="primary", key="gen_btn_v150"):
        ratings_dict = {"D": D_r, "R": R_r, "A": A_r, "S": S_r, "T": T_r, "I": I_r, "C": C_r}
        values_dict = {"depth": depth, "recharge": recharge, "aquifer": aquifer,
                       "soil": soil, "slope": slope, "vadose": vadose,
                       "conductivity": conductivity}
        rep = gen_report(site, sd["coords"], idx, ratings_dict, values_dict, travel["years"])
        st.session_state["rep_v150"] = rep
        st.success("تم التوليد")
    if "rep_v150" in st.session_state:
        st.text_area("التقرير:", st.session_state["rep_v150"], height=400)
        st.markdown("---")
        safe = site.replace(" ", "_")
        cc1, cc2 = st.columns(2)
        with cc1:
            st.download_button("تحميل TXT",
                data=("\ufeff" + st.session_state["rep_v150"]).encode("utf-8"),
                file_name="rep_" + safe + ".txt",
                mime="text/plain; charset=utf-8",
                use_container_width=True,
                key="dl_txt_v150")
        with cc2:
            st.download_button("تحميل HTML",
                data=gen_html(st.session_state["rep_v150"], site).encode("utf-8"),
                file_name="rep_" + safe + ".html",
                mime="text/html; charset=utf-8",
                use_container_width=True,
                key="dl_html_v150")
        st.warning("يحتاج مراجعة بشرية قبل الاعتماد.")


with t5:
    st.header("الخريطة التفاعلية")
    m = folium.Map(location=[15.5, 32.5], zoom_start=6)
    if DS_OK:
        for n, d in NARIS_WELLS.items():
            folium.Marker([d["coords"][1], d["coords"][0]], popup=n, icon=folium.Icon(color="blue")).add_to(m)
        for n, d in DARFUR_WELLS.items():
            folium.Marker([d["coords"][1], d["coords"][0]], popup=n, icon=folium.Icon(color="green")).add_to(m)
        for n, d in KNOWN_MINING_SITES.items():
            col = "red" if d.get("cyanide_use") else "orange"
            folium.Marker([d["coords"][1], d["coords"][0]], popup=n, icon=folium.Icon(color=col)).add_to(m)
        for n, d in KHARTOUM_LOCALITIES.items():
            folium.CircleMarker([d["coords"][1], d["coords"][0]], radius=8, color="purple", fill=True, popup=n).add_to(m)
    st_folium(m, width=None, height=600, key="map_v150")


with t6:
    st.header("تحليل الدقة الإحصائية")
    sample = pd.DataFrame({"name": ["A", "B", "C", "D"], "drastic_index": [150, 80, 130, 165],
        "actual_status": [1, 0, 0, 1]})
    st.download_button("تحميل نموذج", data=sample.to_csv(index=False).encode("utf-8-sig"),
        file_name="accuracy_template.csv", mime="text/csv")
    f2 = st.file_uploader("ارفع:", type=["csv", "xlsx"], key="acc_up_v150")
    if f2:
        try:
            df = pd.read_csv(f2) if f2.name.endswith(".csv") else pd.read_excel(f2)
            if "drastic_index" in df.columns and "actual_status" in df.columns:
                preds = [1 if float(v) >= 140 else 0 for v in df["drastic_index"]]
                actuals = [int(v) for v in df["actual_status"]]
                m = calc_accuracy(preds, actuals)
                a1, a2, a3, a4 = st.columns(4)
                a1.metric("Accuracy", str(m["accuracy"]) + " percent")
                a2.metric("Recall", str(m["recall"]) + " percent")
                a3.metric("Precision", str(m["precision"]) + " percent")
                a4.metric("F1", str(m["f1"]) + " percent")
                b1, b2, b3, b4 = st.columns(4)
                b1.metric("Kappa", m["kappa"])
                b2.metric("Interpretation", interp_kappa(m["kappa"]))
                b3.metric("Specificity", str(m["specificity"]) + " percent")
                b4.metric("Total", m["total"])
                cm_df = pd.DataFrame({"Contaminated": [m["tp"], m["fn"]],
                    "Clean": [m["fp"], m["tn"]]},
                    index=["Predicted Contaminated", "Predicted Clean"])
                st.dataframe(cm_df)
                st.info("Accuracy: " + interp_acc(m["accuracy"]))
                st.info("Kappa: " + interp_kappa(m["kappa"]))
                report = "Accuracy Report\n" + "=" * 40 + "\n"
                report += "Total: " + str(m["total"]) + "\n"
                report += "Accuracy: " + str(m["accuracy"]) + " percent\n"
                report += "Kappa: " + str(m["kappa"]) + "\n"
                st.text_area("Report:", report, height=200)
                st.download_button("تحميل التقرير", data=report.encode("utf-8-sig"),
                    file_name="accuracy_report.txt", mime="text/plain")
            else:
                st.error("Need columns: drastic_index and actual_status")
        except Exception as e:
            st.error("خطأ: " + str(e))


st.markdown("---")
st.caption("2026 University of Khartoum - DRASTIC Sudan v15.0")
