"""
نظام التقييم البيئي للتعدين — DRASTIC Sudan
جامعة الخرطوم — كلية الهندسة
الإصدار: 4.0 (A + C + القوالب الثابتة)

الميزات:
    A — التقييم الجماعي (Bulk Upload)
    C — محاكي الحلول الهندسية
    D — تقارير من قوالب ثابتة (معتمدة)

References:
    - Aller et al. (1987). EPA/600/2-87/035
    - Fetter (2001). Applied Hydrogeology, 4th ed.
    - US EPA (1993). EPA/600/R-93/174
    - WHO (2022). Guidelines for Drinking-water Quality
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import datetime

# ============================================================
# الاستيرادات
# ============================================================
try:
    from data_sources import (
        get_preset_locations_for_app,
        get_data_summary,
        KNOWN_MINING_SITES,
        NARIS_WELLS,
        DARFUR_WELLS,
        KHARTOUM_LOCALITIES,
    )
    DATA_SOURCES_AVAILABLE = True
except ImportError:
    DATA_SOURCES_AVAILABLE = False

try:
    from templates import (
        generate_report,
        get_templates_summary,
        get_template_key,
        TEMPLATE_METADATA,
    )
    TEMPLATES_AVAILABLE = True
except ImportError:
    TEMPLATES_AVAILABLE = False


# ============================================================
# إعدادات الصفحة
# ============================================================
st.set_page_config(
    page_title="DRASTIC Sudan — التقييم البيئي للتعدين",
    page_icon="⛏️",
    layout="wide",
)

st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #d4af37;
        border-radius: 10px;
        padding: 12px;
    }
    .section-header {
        color: #5c2c16;
        border-bottom: 2px solid #c19a6b;
        padding-bottom: 5px;
        margin-bottom: 15px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# دوال DRASTIC
# ============================================================

def get_d_rating(depth_m):
    if depth_m < 0: raise ValueError("العمق سالب")
    if depth_m <= 1.5: return 10
    if depth_m <= 4.6: return 9
    if depth_m <= 9.1: return 7
    if depth_m <= 15.2: return 5
    if depth_m <= 22.9: return 3
    if depth_m <= 30.5: return 2
    return 1


def get_r_rating(recharge_mm):
    if recharge_mm < 0: raise ValueError("التغذية سالبة")
    if recharge_mm <= 50.8: return 1
    if recharge_mm <= 101.6: return 3
    if recharge_mm <= 177.8: return 6
    if recharge_mm <= 254.0: return 8
    return 9


def get_a_rating(aquifer_type):
    type_map = {
        "massive_shale": 2, "metamorphic_igneous": 3,
        "thin_bedded_sequences": 6, "massive_sandstone": 6,
        "massive_limestone": 6, "sand_and_gravel": 8,
        "basalt": 9, "karst_limestone": 10,
    }
    return type_map.get(aquifer_type, 6)


def get_s_rating(soil_type):
    type_map = {
        "thin_or_absent": 10, "gravel": 10, "sand": 9, "peat": 8,
        "sandy_loam": 6, "loam": 5, "silty_loam": 4,
        "clay_loam": 3, "muck": 2, "nonshrinking_clay": 1,
    }
    return type_map.get(soil_type, 5)


def get_t_rating(slope_percent):
    if slope_percent < 0: raise ValueError("الانحدار سالب")
    if slope_percent <= 2.0: return 10
    if slope_percent <= 6.0: return 9
    if slope_percent <= 12.0: return 5
    if slope_percent <= 18.0: return 3
    return 1


def get_i_rating(vadose_type):
    type_map = {
        "silt_clay": 1, "shale": 3, "limestone": 6, "sandstone": 6,
        "sand_gravel_silt_clay": 6, "sand_gravel": 8,
        "basalt": 9, "karst_limestone": 10,
    }
    return type_map.get(vadose_type, 6)


def get_c_rating(conductivity_m_day):
    if conductivity_m_day < 0: raise ValueError("النفاذية سالبة")
    if conductivity_m_day <= 4.074: return 1
    if conductivity_m_day <= 12.222: return 2
    if conductivity_m_day <= 28.518: return 4
    if conductivity_m_day <= 40.740: return 6
    if conductivity_m_day <= 81.480: return 8
    return 10


def calculate_drastic_index(D, R, A, S, T, I, C):
    return (D * 5) + (R * 4) + (A * 3) + (S * 2) + (T * 1) + (I * 5) + (C * 3)


def classify_drastic_risk(index):
    if index >= 180:
        return {"level": "مرتفع جداً", "color": "red", "action": "معالجة فورية"}
    if index >= 140:
        return {"level": "مرتفع", "color": "orange", "action": "مراقبة عاجلة"}
    if index >= 100:
        return {"level": "متوسط", "color": "yellow", "action": "مراقبة دورية"}
    return {"level": "منخفض", "color": "green", "action": "مراقبة روتينية"}


def calculate_travel_time(depth_m, porosity, K_m_day, gradient=1.0):
    if depth_m <= 0: raise ValueError("العمق > 0")
    if not (0.01 < porosity < 0.60): raise ValueError("المسامية خارج النطاق")
    if K_m_day <= 0: raise ValueError("النفاذية > 0")
    velocity = (K_m_day * gradient) / porosity
    days = depth_m / velocity
    return {"days": days, "years": days / 365.25, "velocity": velocity}


def apply_engineering_mitigation(drastic_index, hdpe=False, 
                                   treatment=False, monitoring=False):
    """المسار C — محاكي الحلول."""
    mitigated = drastic_index
    if hdpe: mitigated *= 0.40
    if treatment: mitigated *= 0.60
    if monitoring: mitigated *= 0.85
    reduction = ((drastic_index - mitigated) / drastic_index * 100) if drastic_index > 0 else 0
    return {
        "mitigated_index": round(mitigated, 1),
        "reduction_pct": round(reduction, 1),
        "methods": [m for m, v in [
            ("HDPE Liner", hdpe),
            ("Cyanide Treatment", treatment),
            ("Monitoring Wells", monitoring)
        ] if v],
    }


# ============================================================
# الترويسة
# ============================================================
st.title("⛏️ نظام التقييم البيئي للتعدين")
st.markdown("### جامعة الخرطوم — كلية الهندسة")
st.markdown("#### مكتب الاستشارات الهندسية — DRASTIC Sudan v4.0")
st.markdown("---")


# ============================================================
# تحميل المواقع
# ============================================================
if DATA_SOURCES_AVAILABLE:
    preset_locations = get_preset_locations_for_app()
    summary = get_data_summary()
    with st.sidebar:
        st.markdown("### 📊 ملخص البيانات")
        st.metric("إجمالي المواقع", summary["Total Data Points"])
        st.metric("آبار NARIS", summary["NARIS Wells"])
        st.metric("آبار دارفور", summary["Darfur Wells"])
        st.metric("مواقع تعدين", summary["Known Mining Sites"])
        st.markdown("---")
        if TEMPLATES_AVAILABLE:
            st.success("✅ القوالب الثابتة مُحمّلة")
        st.caption("المصادر: NARIS, UNEP, WHO, Elsheikh (2023)")
else:
    preset_locations = {
        "موقع تجريبي": {
            "coords": (19.53, 33.32),
            "depth": 15.0, "conductivity": 5.0,
        },
    }


# ============================================================
# التبويبات — 5 تبويبات
# ============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📍 التقييم الفردي",
    "📊 التقييم الجماعي (A)",
    "🛡️ محاكي الحلول (C)",
    "📄 توليد التقرير (قوالب)",
    "🗺️ الخريطة",
])


# ============================================================
# TAB 1: التقييم الفردي
# ============================================================
with tab1:
    st.header("⚙️ اختيار الموقع والمدخلات")

    col_site, col_info = st.columns([2, 1])
    with col_site:
        selected_site = st.selectbox(
            "🔍 اختر الموقع:",
            options=list(preset_locations.keys()),
        )
        site_data = preset_locations[selected_site]
        st.caption(f"📌 المصدر: {site_data.get('source', 'غير محدد')}")
    with col_info:
        st.metric("الإحداثيات",
                  f"{site_data['coords'][0]:.3f}, {site_data['coords'][1]:.3f}")
        st.metric("العمق المرجعي", f"{site_data['depth']:.1f} م")

    st.markdown("---")

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("🔬 البيانات الهيدروجيولوجية")
        depth = st.slider("1️⃣ العمق D (م):", 0.5, 100.0,
                          float(site_data["depth"]), 0.5)
        recharge = st.slider("2️⃣ التغذية R (مم/سنة):", 0.0, 400.0, 150.0, 10.0)
        slope = st.slider("3️⃣ الانحدار T (%):", 0.0, 30.0, 4.0, 0.5)
        conductivity = st.slider("4️⃣ النفاذية C (م/يوم):", 0.01, 100.0,
                                  float(site_data["conductivity"]), 0.1)
    with col_right:
        st.subheader("🪨 البيانات الجيولوجية")
        aquifer = st.selectbox("5️⃣ الخزان A:",
            ["massive_sandstone", "sand_and_gravel", "karst_limestone",
             "basalt", "massive_shale", "metamorphic_igneous"])
        soil = st.selectbox("6️⃣ التربة S:",
            ["sand", "sandy_loam", "loam", "silty_loam",
             "clay_loam", "nonshrinking_clay"])
        vadose = st.selectbox("7️⃣ المنطقة غير المشبعة I:",
            ["sand_gravel", "sandstone", "limestone", "silt_clay", "shale"])
        porosity = st.slider("المسامية θ:", 0.02, 0.55, 0.25, 0.01)

    try:
        D_r = get_d_rating(depth)
        R_r = get_r_rating(recharge)
        A_r = get_a_rating(aquifer)
        S_r = get_s_rating(soil)
        T_r = get_t_rating(slope)
        I_r = get_i_rating(vadose)
        C_r = get_c_rating(conductivity)
        index = calculate_drastic_index(D_r, R_r, A_r, S_r, T_r, I_r, C_r)
        risk = classify_drastic_risk(index)

        # حفظ في session_state
        st.session_state.update({
            "current_index": index,
            "current_site": selected_site,
            "current_coords": site_data["coords"],
            "current_depth": depth,
            "current_recharge": recharge,
            "current_slope": slope,
            "current_conductivity": conductivity,
            "current_aquifer": aquifer,
            "current_soil": soil,
            "current_vadose": vadose,
            "current_ratings": {"D": D_r, "R": R_r, "A": A_r, "S": S_r,
                                 "T": T_r, "I": I_r, "C": C_r},
            "current_porosity": porosity,
        })

        st.markdown("---")
        st.header("🎯 نتائج التقييم")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("D", D_r); c2.metric("R", R_r)
        c3.metric("A", A_r); c4.metric("S", S_r)
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("T", T_r); c6.metric("I", I_r)
        c7.metric("C", C_r); c8.metric("θ", f"{porosity:.2f}")

        cx, cy = st.columns(2)
        cx.metric("📊 مؤشر DRASTIC", f"{index} / 230")
        cy.metric("⚠️ الخطورة", risk["level"])

        if risk["color"] == "red":
            st.error(f"🔴 {risk['level']} — {risk['action']}")
        elif risk["color"] == "orange":
            st.warning(f"🟠 {risk['level']} — {risk['action']}")
        elif risk["color"] == "yellow":
            st.info(f"🟡 {risk['level']} — {risk['action']}")
        else:
            st.success(f"🟢 {risk['level']} — {risk['action']}")

        st.markdown("---")
        st.subheader("⏱️ زمن وصول الملوثات")
        travel = calculate_travel_time(depth, porosity, conductivity)
        st.session_state["current_travel_years"] = travel["years"]
        tc1, tc2, tc3 = st.columns(3)
        tc1.metric("الزمن (سنوات)", f"{travel['years']:.2f}")
        tc2.metric("الزمن (أيام)", f"{travel['days']:.1f}")
        tc3.metric("سرعة التسرب", f"{travel['velocity']:.6f}")

        st.info("ℹ️ انتقل إلى تبويب 'توليد التقرير' لإنشاء تقرير فني كامل.")
    except ValueError as e:
        st.error(f"❌ خطأ: {e}")


# ============================================================
# TAB 2 (A): التقييم الجماعي
# ============================================================
with tab2:
    st.header("📊 التقييم الجماعي — Bulk Upload")
    st.markdown("""
    **ارفع ملف Excel أو CSV** لحساب DRASTIC لكل موقع دفعة واحدة.
    
    **الأعمدة المطلوبة:** `name`, `lat`, `lon`, `depth_m`, 
    `recharge_mm`, `slope_pct`, `conductivity`, `aquifer`, 
    `soil`, `vadose`.
    """)

    sample_df = pd.DataFrame({
        "name": ["موقع 1", "موقع 2"],
        "lat": [19.53, 18.12], "lon": [33.32, 33.99],
        "depth_m": [15.0, 10.0], "recharge_mm": [80.0, 120.0],
        "slope_pct": [4.0, 8.0], "conductivity": [5.0, 10.0],
        "aquifer": ["massive_sandstone", "sand_and_gravel"],
        "soil": ["sand", "sandy_loam"],
        "vadose": ["sand_gravel", "sandstone"],
    })
    st.download_button(
        "📥 تحميل نموذج CSV",
        data=sample_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="drastic_template.csv",
        mime="text/csv",
    )

    uploaded_file = st.file_uploader(
        "📤 ارفع ملف (CSV / Excel):",
        type=["csv", "xlsx"],
    )

    if uploaded_file is not None:
        try:
            df = (pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv")
                  else pd.read_excel(uploaded_file))

            results = []
            for i, row in df.iterrows():
                try:
                    D_r = get_d_rating(float(row.get("depth_m", 15)))
                    R_r = get_r_rating(float(row.get("recharge_mm", 100)))
                    A_r = get_a_rating(str(row.get("aquifer", "massive_sandstone")))
                    S_r = get_s_rating(str(row.get("soil", "sand")))
                    T_r = get_t_rating(float(row.get("slope_pct", 4)))
                    I_r = get_i_rating(str(row.get("vadose", "sand_gravel")))
                    C_r = get_c_rating(float(row.get("conductivity", 5)))
                    index = calculate_drastic_index(D_r, R_r, A_r, S_r, T_r, I_r, C_r)
                    risk = classify_drastic_risk(index)
                    results.append({
                        "الموقع": row.get("name", f"موقع {i}"),
                        "lat": row.get("lat", 0), "lon": row.get("lon", 0),
                        "المؤشر": index, "المستوى": risk["level"],
                        "التوصية": risk["action"],
                    })
                except Exception as e:
                    st.warning(f"خطأ في السطر {i}: {e}")

            if results:
                df_res = pd.DataFrame(results)
                st.markdown("---")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("إجمالي المواقع", len(df_res))
                c2.metric("متوسط المؤشر", f"{df_res['المؤشر'].mean():.1f}")
                c3.metric("أعلى مؤشر", df_res["المؤشر"].max())
                c4.metric("مواقع خطرة",
                          len(df_res[df_res["المؤشر"] >= 140]))

                st.dataframe(df_res, use_container_width=True)

                st.download_button(
                    "📥 تحميل النتائج CSV",
                    data=df_res.to_csv(index=False).encode("utf-8-sig"),
                    file_name="drastic_results.csv",
                    mime="text/csv",
                )

                # خريطة
                if "lat" in df_res.columns and "lon" in df_res.columns:
                    st.markdown("---")
                    st.subheader("🗺️ خريطة النتائج")
                    m_bulk = folium.Map(
                        location=[df_res["lat"].mean(), df_res["lon"].mean()],
                        zoom_start=6, tiles="OpenStreetMap",
                    )
                    for _, r in df_res.iterrows():
                        color = ("red" if r["المؤشر"] >= 160 else
                                 "orange" if r["المؤشر"] >= 120 else "green")
                        folium.Marker(
                            [r["lat"], r["lon"]],
                            popup=f"<b>{r['الموقع']}</b><br>DRASTIC: {r['المؤشر']}",
                            icon=folium.Icon(color=color),
                        ).add_to(m_bulk)
                    st_folium(m_bulk
