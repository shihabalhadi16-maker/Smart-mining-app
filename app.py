"""DRASTIC Sudan v19.0 - Modular Architecture"""
import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import datetime

import drastic
import satellite as sat
import reports

st.set_page_config(page_title="DRASTIC Sudan", page_icon="", layout="wide")

try:
    from data_sources import (
        get_preset_locations_for_app, get_data_summary,
        KNOWN_MINING_SITES, NARIS_WELLS, DARFUR_WELLS, KHARTOUM_LOCALITIES,
    )
    DS_OK = True
except ImportError:
    DS_OK = False


# ============================================================
# الترويسة
# ============================================================
st.title("نظام التقييم البيئي للتعدين")
st.markdown("### جامعة الخرطوم - كلية الهندسة")
st.markdown("#### DRASTIC Sudan v19.0")
st.markdown("---")

if DS_OK:
    preset = get_preset_locations_for_app()
    summary = get_data_summary()
else:
    preset = {"موقع تجريبي": {"coords": (19.53, 33.32),
              "depth": 15.0, "conductivity": 5.0, "source": "افتراضي"}}
    summary = {"Total Data Points": 1}


# ============================================================
# التبويبات
# ============================================================
t1, t2, t3, t4, t5, t6 = st.tabs([
    "المدخلات والنتائج", "الجماعي", "الحلول",
    "التقرير", "الخريطة", "الدقة"
])


# ============================================================
# TAB 1: المدخلات والنتائج
# ============================================================
with t1:
    st.header("اختيار الموقع والمدخلات")
    site = st.selectbox("اختر الموقع:", list(preset.keys()))
    sd = preset[site]
    st.caption("المصدر: " + sd.get("source", "غير محدد"))

    st.markdown("---")
    st.subheader("بيانات الأقمار الصناعية (ERA5)")
    st.caption("المصدر: ERA5 (ECMWF) عبر Open-Meteo - معترف بها دوليا")

    if st.button("جلب البيانات من Open-Meteo", key="fetch_sat"):
        with st.spinner("جاري جلب البيانات..."):
            sat_data = sat.fetch_satellite_data(
                sd["coords"][0], sd["coords"][1], years=3)
            st.session_state["sat_data"] = sat_data

    if "sat_data" in st.session_state:
        s = st.session_state["sat_data"]
        if s.get("rainfall_mm") is None:
            st.warning("تعذر جلب البيانات. تحقق من الاتصال.")
        else:
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("الأمطار (مم/سنة)", s["rainfall_mm"])
            sc2.metric("الحرارة (C)", s["temperature_c"])
            sc3.metric("NDVI مقدر", s["ndvi_estimated"])
            sc4.metric("المناخ", s["aridity"])
            st.caption("المصدر: " + s["source"] + " | الفترة: " + s["period"])
            rec_est = sat.estimate_recharge(s["rainfall_mm"])
            st.info("التغذية المقدرة: " + str(rec_est) + " مم/سنة (مرجع مساعد)")

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
        D_r = drastic.get_d_rating(depth)
        R_r = drastic.get_r_rating(recharge)
        A_r = drastic.get_a_rating(aquifer)
        S_r = drastic.get_s_rating(soil)
        T_r = drastic.get_t_rating(slope)
        I_r = drastic.get_i_rating(vadose)
        C_r = drastic.get_c_rating(conductivity)
        idx = drastic.calc_index(D_r, R_r, A_r, S_r, T_r, I_r, C_r)
        risk = drastic.classify(idx)
        travel = drastic.calc_travel_time(depth, porosity, conductivity)

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
        if risk["color"] == "red":
            st.error(risk["action"])
        elif risk["color"] == "orange":
            st.warning(risk["action"])
        elif risk["color"] == "yellow":
            st.info(risk["action"])
        else:
            st.success(risk["action"])
        st.markdown("---")
        st.subheader("زمن وصول الملوثات")
        w1, w2, w3 = st.columns(3)
        w1.metric("سنوات", travel["years"])
        w2.metric("أيام", travel["days"])
        w3.metric("السرعة", travel["velocity"])
    except ValueError as e:
        st.error("خطأ: " + str(e))


# ============================================================
# TAB 2: التقييم الجماعي
# ============================================================
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
                D = drastic.get_d_rating(float(row.get("depth_m", 15)))
                R = drastic.get_r_rating(float(row.get("recharge_mm", 100)))
                A = drastic.get_a_rating(str(row.get("aquifer", "massive_sandstone")))
                S = drastic.get_s_rating(str(row.get("soil", "sand")))
                T = drastic.get_t_rating(float(row.get("slope_pct", 4)))
                I = drastic.get_i_rating(str(row.get("vadose", "sand_gravel")))
                C = drastic.get_c_rating(float(row.get("conductivity", 5)))
                ix = drastic.calc_index(D, R, A, S, T, I, C)
                rk = drastic.classify(ix)
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


# ============================================================
# TAB 3: محاكي الحلول
# ============================================================
with t3:
    st.header("محاكي الحلول")
    if "ci" in st.session_state:
        cur_idx = st.session_state["ci"]
        cur_site = st.session_state["cs"]
        st.info("الموقع: " + cur_site + " | المؤشر: " + str(cur_idx))
        st.caption("HDPE = 60 | المعالجة = 40 | الآبار = 15")
        c1, c2 = st.columns(2)
        with c1:
            h = st.checkbox("HDPE Liner", key="mit_h")
            tr = st.checkbox("Cyanide Treatment", key="mit_t")
        with c2:
            mo = st.checkbox("Monitoring Wells", key="mit_m")
        if h or tr or mo:
            r = drastic.mitigate(cur_idx, h, tr, mo)
            a, b, c = st.columns(3)
            a.metric("قبل", cur_idx)
            b.metric("بعد", r["mitigated_index"])
            c.metric("التخفيض", str(r["reduction_pct"]) + " %")
            st.progress(min(r["reduction_pct"] / 100, 1.0))
            nr = drastic.classify(int(r["mitigated_index"]))
            st.metric("المستوى الجديد", nr["level"])
    else:
        st.warning("افتح تبويب المدخلات أولا")


# ============================================================
# TAB 4: التقرير
# ============================================================
with t4:
    st.header("توليد التقرير")
    if "ci" in st.session_state:
        cur_idx = st.session_state["ci"]
        cur_site = st.session_state["cs"]
        key = reports.get_template_key(cur_idx)
        st.info("الموقع: " + cur_site + " | المؤشر: " + str(cur_idx) +
                " | القالب: " + key.upper())
        if st.button("توليد", type="primary", key="gen"):
            rep = reports.generate_report(
                cur_site, st.session_state["cc"], cur_idx,
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
                    data=reports.generate_html(
                        st.session_state["rep"], cur_site).encode("utf-8"),
                    file_name="rep_" + safe + ".html",
                    mime="text/html; charset=utf-8",
                    use_container_width=True)
            st.warning("يحتاج مراجعة بشرية")
    else:
        st.warning("افتح تبويب المدخلات أولا")


# ============================================================
# TAB 5: الخريطة
# ============================================================
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


# ============================================================
# TAB 6: الدقة الإحصائية
# ============================================================
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


st.markdown("---")
st.caption("2026 University of Khartoum - DRASTIC Sudan v19.0 Modular")
