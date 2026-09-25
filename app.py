"""
نظام التقييم البيئي للتعدين — DRASTIC Sudan
جامعة الخرطوم — كلية الهندسة
"""
import streamlit as st

st.set_page_config(
    page_title="DRASTIC Sudan — تقييم التعدين البيئي",
    page_icon="⛏️",
    layout="wide",
)

st.title("⛏️ نظام التقييم البيئي للتعدين")
st.markdown("### جامعة الخرطوم — كلية الهندسة")
st.markdown("### مكتب الاستشارات الهندسية")
st.markdown("---")

# اختبار وحدة الحسابات
try:
    from calculations import (
        get_d_rating,
        get_r_rating,
        get_a_rating,
        get_s_rating,
        get_t_rating,
        get_i_rating,
        get_c_rating,
        calculate_drastic_index,
        classify_drastic_risk,
        calculate_travel_time,
        EFFECTIVE_POROSITY_DEFAULTS,
    )
    
    st.success("✅ وحدة الحسابات `calculations.py` تعمل بنجاح")
    
    st.header("📊 اختبار سريع لنموذج DRASTIC")
    
    col1, col2 = st.columns(2)
    
    with col1:
        depth = st.slider(
            "1. عمق المياه الجوفية D (متر):", 
            0.5, 60.0, 15.0, step=0.5
        )
        recharge = st.slider(
            "2. التغذية السنوية R (مم/سنة):", 
            0.0, 400.0, 80.0, step=10.0
        )
        slope = st.slider(
            "3. الانحدار T (%):", 
            0.0, 30.0, 4.0, step=0.5
        )
        conductivity = st.slider(
            "4. النفاذية C (م/يوم):", 
            0.01, 100.0, 5.0, step=0.1
        )
    
    with col2:
        aquifer = st.selectbox(
            "5. نوع الخزان الجوفي A:",
            ["massive_sandstone", "sand_and_gravel", "karst_limestone", 
             "basalt", "massive_shale"],
        )
        soil = st.selectbox(
            "6. نوع التربة S:",
            ["sand", "sandy_loam", "loam", "silty_loam", 
             "clay_loam", "nonshrinking_clay"],
        )
        vadose = st.selectbox(
            "7. المنطقة غير المشبعة I:",
            ["sand_gravel", "sandstone", "limestone", 
             "silt_clay", "shale"],
        )
    
    # الحساب
    D_r = get_d_rating(depth)
    R_r = get_r_rating(recharge)
    A_r = get_a_rating(aquifer)
    S_r = get_s_rating(soil)
    T_r = get_t_rating(slope)
    I_r = get_i_rating(vadose)
    C_r = get_c_rating(conductivity)
    
    index = calculate_drastic_index(D_r, R_r, A_r, S_r, T_r, I_r, C_r)
    risk = classify_drastic_risk(index)
    
    st.markdown("---")
    st.header("🎯 النتائج")
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("تقييم D", D_r)
    col_b.metric("تقييم R", R_r)
    col_c.metric("تقييم A", A_r)
    
    col_d, col_e, col_f, col_g = st.columns(4)
    col_d.metric("تقييم S", S_r)
    col_e.metric("تقييم T", T_r)
    col_f.metric("تقييم I", I_r)
    col_g.metric("تقييم C", C_r)
    
    st.markdown("---")
    col_x, col_y = st.columns(2)
    col_x.metric("📊 مؤشر DRASTIC الإجمالي", f"{index} / 230")
    col_y.metric("⚠️ مستوى الخطورة", risk["level"])
    
    if risk["color"] == "red":
        st.error(f"🔴 {risk['level']} — {risk['action']}")
    elif risk["color"] == "orange":
        st.warning(f"🟠 {risk['level']} — {risk['action']}")
    elif risk["color"] == "yellow":
        st.info(f"🟡 {risk['level']} — {risk['action']}")
    else:
        st.success(f"🟢 {risk['level']} — {risk['action']}")
    
    # حساب زمن وصول الملوثات
    st.markdown("---")
    st.header("⏱️ زمن وصول الملوثات (تقديري)")
    
    porosity = EFFECTIVE_POROSITY_DEFAULTS.get(
        "sand_and_gravel" if "sand" in aquifer else "sandstone", 
        0.20
    )
    K_value = conductivity
    
    try:
        travel = calculate_travel_time(
            depth_m=depth,
            porosity=porosity,
            K_m_day=K_value,
            gradient=1.0,
            zone="unsaturated"
        )
        st.metric(
            "الزمن المتوقع", 
            f"{travel['travel_time_years']:.1f} سنة"
        )
        
        if travel["warnings"]:
            for w in travel["warnings"]:
                st.warning(w)
        
        with st.expander("⚠️ حدود النموذج والافتراضات"):
            st.markdown(travel["disclaimer"])
    except ValueError as e:
        st.error(f"خطأ في الحساب: {e}")

except ImportError as e:
    st.error(f"❌ خطأ في الاستيراد: {e}")
    st.info(
        "تأكد من وجود ملف `calculations.py` في نفس المستودع، "
        "وأنه يحتوي على الدوال المطلوبة."
    )
except Exception as e:
    st.error(f"❌ خطأ غير متوقع: {e}")
    st.exception(e)

st.markdown("---")
st.caption("© 2026 جامعة الخرطوم — مكتب الاستشارات الهندسية")
