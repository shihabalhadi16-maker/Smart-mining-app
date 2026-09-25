"""
نظام التقييم البيئي للتعدين — DRASTIC Sudan
جامعة الخرطوم — كلية الهندسة
مكتب الاستشارات الهندسية

نسخة موحدة (ملف واحد) — جاهزة للتشغيل على Streamlit Cloud

References:
    - Aller et al. (1987). EPA/600/2-87/035
    - Fetter (2001). Applied Hydrogeology, 4th ed.
    - US EPA (1993). EPA/600/R-93/174
"""

import streamlit as st

# ============================================================
# إعدادات الصفحة
# ============================================================
st.set_page_config(
    page_title="DRASTIC Sudan — التقييم البيئي للتعدين",
    page_icon="⛏️",
    layout="wide",
)

# ============================================================
# التنسيق البصري
# ============================================================
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
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# دوال DRASTIC — EPA/600/2-87/035
# ============================================================

def get_d_rating(depth_m):
    """Depth to Water rating — Aller et al. (1987), Table 6, p.19."""
    if depth_m < 0:
        raise ValueError("عمق المياه لا يمكن أن يكون سالباً")
    if depth_m <= 1.5: return 10
    if depth_m <= 4.6: return 9
    if depth_m <= 9.1: return 7
    if depth_m <= 15.2: return 5
    if depth_m <= 22.9: return 3
    if depth_m <= 30.5: return 2
    return 1


def get_r_rating(recharge_mm):
    """Net Recharge rating — Aller et al. (1987), Table 7, p.21."""
    if recharge_mm < 0:
        raise ValueError("التغذية لا يمكن أن تكون سالبة")
    if recharge_mm <= 50.8: return 1
    if recharge_mm <= 101.6: return 3
    if recharge_mm <= 177.8: return 6
    if recharge_mm <= 254.0: return 8
    return 9


def get_a_rating(aquifer_type):
    """Aquifer Media rating — Aller et al. (1987), Table 8, p.23."""
    type_map = {
        "massive_shale": 2,
        "metamorphic_igneous": 3,
        "thin_bedded_sequences": 6,
        "massive_sandstone": 6,
        "massive_limestone": 6,
        "sand_and_gravel": 8,
        "basalt": 9,
        "karst_limestone": 10,
    }
    if aquifer_type not in type_map:
        raise ValueError(f"نوع الخزان غير صالح: {aquifer_type}")
    return type_map[aquifer_type]


def get_s_rating(soil_type):
    """Soil Media rating — Aller et al. (1987), Table 9, p.25."""
    type_map = {
        "thin_or_absent": 10,
        "gravel": 10,
        "sand": 9,
        "peat": 8,
        "sandy_loam": 6,
        "loam": 5,
        "silty_loam": 4,
        "clay_loam": 3,
        "nonshrinking_clay": 1,
    }
    if soil_type not in type_map:
        raise ValueError(f"نوع التربة غير صالح: {soil_type}")
    return type_map[soil_type]


def get_t_rating(slope_percent):
    """Topography rating — Aller et al. (1987), Table 10, p.27."""
    if slope_percent < 0:
        raise ValueError("الانحدار لا يمكن أن يكون سالباً")
    if slope_percent <= 2.0: return 10
    if slope_percent <= 6.0: return 9
    if slope_percent <= 12.0: return 5
    if slope_percent <= 18.0: return 3
    return 1


def get_i_rating(vadose_type):
    """Vadose Zone rating — Aller et al. (1987), Table 11, p.29."""
    type_map = {
        "silt_clay": 1,
        "shale": 3,
        "limestone": 6,
        "sandstone": 6,
        "sand_gravel_silt_clay": 6,
        "sand_gravel": 8,
        "basalt": 9,
        "karst_limestone": 10,
    }
    if vadose_type not in type_map:
        raise ValueError(f"نوع المنطقة غير المشبعة غير صالح: {vadose_type}")
    return type_map[vadose_type]


def get_c_rating(conductivity_m_day):
    """Hydraulic Conductivity rating — Aller et al. (1987), Table 12, p.31."""
    if conductivity_m_day < 0:
        raise ValueError("النفاذية لا يمكن أن تكون سالبة")
    if conductivity_m_day <= 4.074: return 1
    if conductivity_m_day <= 12.222: return 2
    if conductivity_m_day <= 28.518: return 4
    if conductivity_m_day <= 40.740: return 6
    if conductivity_m_day <= 81.480: return 8
    return 10


def calculate_drastic_index(D, R, A, S, T, I, C):
    """DRASTIC Index — Aller et al. (1987, p.16). Range: 23-230."""
    return (D * 5) + (R * 4) + (A * 3) + (S * 2) + (T * 1) + (I * 5) + (C * 3)


def classify_drastic_risk(index):
    """تصنيف الخطورة — Rahman (2008)."""
    if index >= 180:
        return {"level": "مرتفع جداً", "color": "red", "action": "معالجة فورية"}
    if index >= 140:
        return {"level": "مرتفع", "color": "orange", "action": "مراقبة عاجلة"}
    if index >= 100:
        return {"level": "متوسط", "color": "yellow", "action": "مراقبة دورية"}
    return {"level": "منخفض", "color": "green", "action": "مراقبة روتينية"}


def calculate_travel_time(depth_m, porosity, K_m_day, gradient=1.0):
    """زمن وصول الملوثات — Fetter (2001), pp.132-136."""
    if depth_m <= 0:
        raise ValueError("العمق يجب أن يكون أكبر من صفر")
    if not (0.01 < porosity < 0.60):
        raise ValueError("المسامية خارج النطاق الجيولوجي (0.01-0.60)")
    if K_m_day <= 0:
        raise ValueError("النفاذية يجب أن تكون أكبر من صفر")
    if gradient <= 0:
        raise ValueError("الميل الهيدروليكي يجب أن يكون أكبر من صفر")

    velocity = (K_m_day * gradient) / porosity
    days = depth_m / velocity
    years = days / 365.25

    warnings = []
    if years > 1000:
        warnings.append(
            "⚠️ الزمن > 1000 سنة — قد يكون K منخفضاً جداً. تحقق من القيمة."
        )

    return {
        "days": days,
        "years": years,
        "velocity": velocity,
        "warnings": warnings,
    }


# ============================================================
# الترويسة
# ============================================================
st.title("⛏️ نظام التقييم البيئي للتعدين")
st.markdown("### جامعة الخرطوم — كلية الهندسة")
st.markdown("#### مكتب الاستشارات الهندسية — DRASTIC Model")
st.markdown("---")

# ============================================================
# التبويبات
# ============================================================
tab1, tab2 = st.tabs(["📍 التقييم الفردي", "📚 المنهجية والمراجع"])


# ============================================================
# TAB 1: التقييم الفردي
# ============================================================
with tab1:
    st.header("⚙️ مدخلات نموذج DRASTIC")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("البيانات الهيدروجيولوجية")

        depth = st.slider(
            "1️⃣ عمق المياه الجوفية D (متر):",
            min_value=0.5, max_value=60.0, value=15.0, step=0.5
        )

        recharge = st.slider(
            "2️⃣ التغذية السنوية R (مم/سنة):",
            min_value=0.0, max_value=400.0, value=80.0, step=10.0
        )

        slope = st.slider(
            "3️⃣ الانحدار T (%):",
            min_value=0.0, max_value=30.0, value=4.0, step=0.5
        )

        conductivity = st.slider(
            "4️⃣ النفاذية C (م/يوم):",
            min_value=0.01, max_value=100.0, value=5.0, step=0.1
        )

    with col_right:
        st.subheader("البيانات الجيولوجية")

        aquifer = st.selectbox(
            "5️⃣ نوع الخزان الجوفي A:",
            options=[
                "massive_sandstone",
                "sand_and_gravel",
                "karst_limestone",
                "basalt",
                "massive_shale",
                "metamorphic_igneous",
            ],
            format_func=lambda x: {
                "massive_sandstone": "حجر رملي ضخم",
                "sand_and_gravel": "رمل وحصى",
                "karst_limestone": "حجر جيري كارستي",
                "basalt": "بازلت",
                "massive_shale": "طفل ضخم",
                "metamorphic_igneous": "صخور متحولة/نارية",
            }.get(x, x),
        )

        soil = st.selectbox(
            "6️⃣ نوع التربة S:",
            options=[
                "sand",
                "sandy_loam",
                "loam",
                "silty_loam",
                "clay_loam",
                "nonshrinking_clay",
            ],
            format_func=lambda x: {
                "sand": "رمل",
                "sandy_loam": "طمي رملي",
                "loam": "طمي",
                "silty_loam": "طمي غريني",
                "clay_loam": "طمي طيني",
                "nonshrinking_clay": "طين غير متقلص",
            }.get(x, x),
        )

        vadose = st.selectbox(
            "7️⃣ المنطقة غير المشبعة I:",
            options=[
                "sand_gravel",
                "sandstone",
                "limestone",
                "silt_clay",
                "shale",
            ],
            format_func=lambda x: {
                "sand_gravel": "رمل وحصى",
                "sandstone": "حجر رملي",
                "limestone": "حجر جيري",
                "silt_clay": "غرين وطين",
                "shale": "طفل",
            }.get(x, x),
        )

        porosity = st.slider(
            "المسامية الفعالة θ (كسر):",
            min_value=0.02, max_value=0.55, value=0.25, step=0.01
        )

    # ============================================================
    # الحسابات
    # ============================================================
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

        st.markdown("---")
        st.header("🎯 نتائج التقييم")

        # التقييمات الفردية
        st.subheader("التقييمات الفردية للمعاملات السبعة")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("D — العمق", D_r)
        c2.metric("R — التغذية", R_r)
        c3.metric("A — الخزان", A_r)
        c4.metric("S — التربة", S_r)

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("T — الانحدار", T_r)
        c6.metric("I — غير المشبعة", I_r)
        c7.metric("C — النفاذية", C_r)
        c8.metric("θ — المسامية", f"{porosity:.2f}")

        # المؤشر الإجمالي
        st.markdown("---")
        st.subheader("المؤشر الإجمالي ومستوى الخطورة")
        col_x, col_y, col_z = st.columns(3)
        col_x.metric("📊 مؤشر DRASTIC", f"{index} / 230")
        col_y.metric("⚠️ مستوى الخطورة", risk["level"])
        col_z.metric("🎨 التصنيف", risk["color"].upper())

        # عرض التحذير
        if risk["color"] == "red":
            st.error(f"🔴 مستوى {risk['level']} — التوصية: {risk['action']}")
        elif risk["color"] == "orange":
            st.warning(f"🟠 مستوى {risk['level']} — التوصية: {risk['action']}")
        elif risk["color"] == "yellow":
            st.info(f"🟡 مستوى {risk['level']} — التوصية: {risk['action']}")
        else:
            st.success(f"🟢 مستوى {risk['level']} — التوصية: {risk['action']}")

        # ============================================================
        # زمن وصول الملوثات
        # ============================================================
        st.markdown("---")
        st.header("⏱️ زمن وصول الملوثات (تقديري)")

        try:
            travel = calculate_travel_time(
                depth_m=depth,
                porosity=porosity,
                K_m_day=conductivity,
                gradient=1.0,
            )

            tc1, tc2, tc3 = st.columns(3)
            tc1.metric("الزمن (سنوات)", f"{travel['years']:.2f}")
            tc2.metric("الزمن (أيام)", f"{travel['days']:.1f}")
            tc3.metric("سرعة التسرب (م/يوم)", f"{travel['velocity']:.6f}")

            for w in travel["warnings"]:
                st.warning(w)

            with st.expander("⚠️ حدود النموذج والافتراضات"):
                st.markdown("""
                **المرجع:** US EPA (1993). EPA/600/R-93/174, Section 7.3.3.2

                **الافتراضات:**
                1. وسط مسامي متجانس
                2. سرعة تسرب ثابتة
                3. ملوث محافظ غير متفاعل
                4. لا يوجد انتشار هيدروديناميكي
                5. لا يوجد امتزاز أو تأخير
                6. تدفق مستقر لأسفل

                **لا يأخذ في الحسبان:**
                - الشقوق والمسارات التفضيلية
                - عدم التجانس في K والمسامية
                - التفاعلات الكيميائية والتحلل
                - انتشار جبهة الملوث
                - أحداث التغذية العابرة

                **تفسير النتيجة:** الزمن هو زمن وصول الجبهة الأمامية،
                وليس الزمن الكامل لوصول الملوث.

                **الاستخدام:** تقييم أولي (Screening-level) فقط.

                ⚠️ للقرارات النهائية: معايرة ميدانية إلزامية (Tracer Tests).
                """)

        except ValueError as e:
            st.error(f"❌ خطأ في حساب زمن الوصول: {e}")

    except ValueError as e:
        st.error(f"❌ خطأ في المدخلات: {e}")
    except Exception as e:
        st.error(f"❌ خطأ غير متوقع: {e}")


# ============================================================
# TAB 2: المنهجية والمراجع
# ============================================================
with tab2:
    st.header("📚 المنهجية العلمية والمراجع")

    st.markdown("""
    ### 1. نموذج DRASTIC
    
    **المرجع الأصلي:**
    Aller, L., Bennett, T., Lehr, J. H., Petty, R. J., & Hackett, G. (1987).
    *DRASTIC: A Standardized System for Evaluating Ground Water Pollution 
    Potential Using Hydrogeologic Settings*. EPA/600/2-87/035.
    U.S. Environmental Protection Agency, Washington, D.C.
    
    **المعادلة:**
    ```
    DI = Dr·Dw + Rr·Rw + Ar·Aw + Sr·Sw + Tr·Tw + Ir·Iw + Cr·Cw
    ```
    
    **الأوزان الرسمية:**
    - Dw = 5 (عمق المياه الجوفية)
    - Rw = 4 (التغذية السنوية)
    - Aw = 3 (نوع الخزان الجوفي)
    - Sw = 2 (نوع التربة)
    - Tw = 1 (الانحدار)
    - Iw = 5 (المنطقة غير المشبعة)
    - Cw = 3 (النفاذية الهيدروليكية)
    
    **المدى:** 23 (أدنى) إلى 230 (أقصى)
    
    ---
    
    ### 2. حساب زمن وصول الملوثات
    
    **المرجع:**
    Fetter, C. W. (2001). *Applied Hydrogeology* (4th ed.), pp. 132-136.
    Prentice Hall.
    
    **المعادلة (Darcy's Seepage Velocity):**
    ```
    t = (θ · L) / (K · i)
    ```
    
    حيث:
    - t = زمن العبور
    - θ = المسامية الفعالة
    - L = المسافة/العمق
    - K = النفاذية الهيدروليكية
    - i = الميل الهيدروليكي
    
    **الحدود:** انظر US EPA (1993). EPA/600/R-93/174, Section 7.3.3.2.
    
    ---
    
    ### 3. المراجع الدولية
    
    - **WHO (2022).** *Guidelines for Drinking-water Quality*, 4th ed.
    - **US EPA (2020).** *Ground Water Rule*.
    - **Minamata Convention on Mercury (2017).**
    - **International Cyanide Management Code (ICMC).**
    - **ISO 14001:2015.** Environmental Management Systems.
    
    ---
    
    ### 4. التشريعات السودانية
    
    - قانون تنمية الثروة المعدنية والتعدين 2015
    - قانون حماية البيئة 2001 (رقم 18)
    - لائحة تنظيم التعدين التقليدي 2016
    - قانون الصحة البيئية 2009
    - القرار (90) لسنة 2021
    
    ⚠️ **ملاحظة:** يجب التحقق من النصوص القانونية من الجريدة 
    الرسمية السودانية قبل الاستخدام الرسمي.
    
    ---
    
    ### 5. تحذير علمي
    
    هذا النظام أداة مساعدة للقرار، وليس بديلاً عن:
    - الدراسات الميدانية التفصيلية.
    - المراجعة البشرية المتخصصة.
    - المعايرة المحلية (Calibration).
    
    **للاستخدام الرسمي:** يجب معايرة النموذج ببيانات ميدانية 
    سودانية والتحقق من النتائج مع هيئة الأبحاث الجيولوجية (GRAS).
    """)

    st.success("✅ تم توثيق جميع المراجع العلمية")


# ============================================================
# التذييل
# ============================================================
st.markdown("---")
st.caption(
    "© 2026 جامعة الخرطوم — مكتب الاستشارات الهندسية | "
    "نظام DRASTIC Sudan v1.0 | "
    "مبني على Aller et al. (1987) و Fetter (2001)"
)
