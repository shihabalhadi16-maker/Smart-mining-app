"""
نظام التقييم البيئي للتعدين — DRASTIC Sudan
جامعة الخرطوم — كلية الهندسة
مكتب الاستشارات الهندسية

الإصدار: 2.0 (يدمج data_sources.py)

References:
    - Aller et al. (1987). EPA/600/2-87/035
    - Fetter (2001). Applied Hydrogeology, 4th ed.
    - US EPA (1993). EPA/600/R-93/174
    - WHO (2022). Guidelines for Drinking-water Quality
"""

import streamlit as st
import folium
from streamlit_folium import st_folium

# ============================================================
# استيراد وحدة البيانات
# ============================================================
try:
    from data_sources import (
        get_preset_locations_for_app,
        get_climate_for_region,
        compare_with_who_limits,
        get_data_summary,
        KNOWN_MINING_SITES,
        NARIS_WELLS,
        DARFUR_WELLS,
        KHARTOUM_LOCALITIES,
        CLIMATE_DATA,
    )
    DATA_SOURCES_AVAILABLE = True
except ImportError:
    DATA_SOURCES_AVAILABLE = False
    st.warning(
        "⚠️ لم يتم العثور على ملف data_sources.py — "
        "سيتم استخدام بيانات أساسية فقط."
    )


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
        font-weight: bold;
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
    return type_map.get(aquifer_type, 6)


def get_s_rating(soil_type):
    """Soil Media rating — Aller et al. (1987), Table 9, p.25."""
    type_map = {
        "thin_or_absent": 10, "gravel": 10, "sand": 9, "peat": 8,
        "sandy_loam": 6, "loam": 5, "silty_loam": 4,
        "clay_loam": 3, "muck": 2, "nonshrinking_clay": 1,
    }
    return type_map.get(soil_type, 5)


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
        "silt_clay": 1, "shale": 3, "limestone": 6, "sandstone": 6,
        "sand_gravel_silt_clay": 6, "sand_gravel": 8,
        "basalt": 9, "karst_limestone": 10,
    }
    return type_map.get(vadose_type, 6)


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
    velocity = (K_m_day * gradient) / porosity
    days = depth_m / velocity
    return {
        "days": days,
        "years": days / 365.25,
        "velocity": velocity,
        "warnings": [] if days / 365.25 < 1000 else [
            "⚠️ الزمن > 1000 سنة — قد يكون K منخفضاً جداً."
        ],
    }


# ============================================================
# الترويسة
# ============================================================
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.markdown("# ⛏️")
with col_title:
    st.title("نظام التقييم البيئي للتعدين")
    st.markdown("### جامعة الخرطوم — كلية الهندسة")
    st.markdown("#### مكتب الاستشارات الهندسية — DRASTIC Model")

st.markdown("---")


# ============================================================
# تحميل المواقع المسبقة
# ============================================================
if DATA_SOURCES_AVAILABLE:
    preset_locations = get_preset_locations_for_app()
    summary = get_data_summary()
    
    # عرض ملخص البيانات في الشريط الجانبي
    with st.sidebar:
        st.markdown("### 📊 ملخص البيانات المتاحة")
        st.metric("المواقع المسبقة", summary["Total Data Points"])
        st.metric("آبار NARIS", summary["NARIS Wells"])
        st.metric("آبار دارفور", summary["Darfur Wells"])
        st.metric("محليات الخرطوم", summary["Khartoum Localities"])
        st.metric("مواقع تعدين", summary["Known Mining Sites"])
        
        st.markdown("---")
        st.caption(
            "المصادر: NARIS, UNEP, Elsheikh et al. (2023), WHO (2022)"
        )
else:
    # بيانات احتياطية إذا لم يوجد الملف
    preset_locations = {
        "سوق طواحين أبو حمد": {
            "coords": (19.5333, 33.3167),
            "depth": 15.0,
            "conductivity": 5.0,
        },
        "سوق العبيدية": {
            "coords": (18.1234, 33.9876),
            "depth": 10.0,
            "conductivity": 5.0,
        },
    }


# ============================================================
# التبويبات
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📍 التقييم الفردي",
    "🗺️ الخريطة التفاعلية",
    "📚 المنهجية والمراجع",
    "💡 مصادر البيانات",
])


# ============================================================
# TAB 1: التقييم الفردي
# ============================================================
with tab1:
    st.header("⚙️ اختيار الموقع والمدخلات")

    # اختيار الموقع
    col_site, col_info = st.columns([2, 1])

    with col_site:
        selected_site = st.selectbox(
            "🔍 اختر الموقع:",
            options=list(preset_locations.keys()),
            help="المواقع من NARIS, UNEP, ومواقع تعدين معروفة"
        )
        site_data = preset_locations[selected_site]
        st.caption(f"📌 المصدر: {site_data.get('source', 'غير محدد')}")

    with col_info:
        st.metric("الإحداثيات", 
                  f"{site_data['coords'][0]:.3f}, {site_data['coords'][1]:.3f}")
        st.metric("العمق المرجعي", f"{site_data['depth']:.1f} م")

    st.markdown("---")

    # المدخلات
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("🔬 البيانات الهيدروجيولوجية")

        depth = st.slider(
            "1️⃣ عمق المياه الجوفية D (متر):",
            0.5, 100.0, float(site_data["depth"]), 0.5
        )

        # اقتراح التغذية تلقائياً من المنطقة
        region_default = 150.0
        if DATA_SOURCES_AVAILABLE:
            # محاولة استنتاج المنطقة من اسم الموقع
            for region in CLIMATE_DATA.keys():
                if region in selected_site:
                    region_default = CLIMATE_DATA[region]["rainfall_mm_year"]
                    break

        recharge = st.slider(
            "2️⃣ التغذية السنوية R (مم/سنة):",
            0.0, 400.0, region_default, 10.0
        )

        slope = st.slider(
            "3️⃣ الانحدار T (%):",
            0.0, 30.0, 4.0, 0.5
        )

        conductivity = st.slider(
            "4️⃣ النفاذية C (م/يوم):",
            0.01, 100.0, float(site_data["conductivity"]), 0.1
        )

    with col_right:
        st.subheader("🪨 البيانات الجيولوجية")

        aquifer = st.selectbox(
            "5️⃣ نوع الخزان الجوفي A:",
            ["massive_sandstone", "sand_and_gravel", "karst_limestone",
             "basalt", "massive_shale", "metamorphic_igneous"],
            format_func=lambda x: {
                "massive_sandstone": "حجر رملي ضخم (6)",
                "sand_and_gravel": "رمل وحصى (8)",
                "karst_limestone": "حجر جيري كارستي (10)",
                "basalt": "بازلت (9)",
                "massive_shale": "طفل ضخم (2)",
                "metamorphic_igneous": "صخور متحولة (3)",
            }.get(x, x),
        )

        soil = st.selectbox(
            "6️⃣ نوع التربة S:",
            ["sand", "sandy_loam", "loam", "silty_loam",
             "clay_loam", "nonshrinking_clay"],
            format_func=lambda x: {
                "sand": "رمل (9)",
                "sandy_loam": "طمي رملي (6)",
                "loam": "طمي (5)",
                "silty_loam": "طمي غريني (4)",
                "clay_loam": "طمي طيني (3)",
                "nonshrinking_clay": "طين غير متقلص (1)",
            }.get(x, x),
        )

        vadose = st.selectbox(
            "7️⃣ المنطقة غير المشبعة I:",
            ["sand_gravel", "sandstone", "limestone", "silt_clay", "shale"],
            format_func=lambda x: {
                "sand_gravel": "رمل وحصى (8)",
                "sandstone": "حجر رملي (6)",
                "limestone": "حجر جيري (6)",
                "silt_clay": "غرين وطين (1)",
                "shale": "طفل (3)",
            }.get(x, x),
        )

        porosity = st.slider(
            "المسامية الفعالة θ:",
            0.02, 0.55, 0.25, 0.01
        )

    # الحسابات
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
        st.subheader("التقييمات الفردية")
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
        col_x, col_y = st.columns(2)
        col_x.metric("📊 مؤشر DRASTIC", f"{index} / 230")
        col_y.metric("⚠️ مستوى الخطورة", risk["level"])

        if risk["color"] == "red":
            st.error(f"🔴 {risk['level']} — {risk['action']}")
        elif risk["color"] == "orange":
            st.warning(f"🟠 {risk['level']} — {risk['action']}")
        elif risk["color"] == "yellow":
            st.info(f"🟡 {risk['level']} — {risk['action']}")
        else:
            st.success(f"🟢 {risk['level']} — {risk['action']}")

        # زمن وصول الملوثات
        st.markdown("---")
        st.header("⏱️ زمن وصول الملوثات (تقديري)")

        travel = calculate_travel_time(depth, porosity, conductivity)
        tc1, tc2, tc3 = st.columns(3)
        tc1.metric("الزمن (سنوات)", f"{travel['years']:.2f}")
        tc2.metric("الزمن (أيام)", f"{travel['days']:.1f}")
        tc3.metric("سرعة التسرب (م/يوم)", f"{travel['velocity']:.6f}")

        for w in travel["warnings"]:
            st.warning(w)

        with st.expander("⚠️ حدود النموذج"):
            st.markdown("""
            **المرجع:** US EPA (1993). EPA/600/R-93/174
            
            **الافتراضات:** وسط متجانس، سرعة ثابتة، ملوث محافظ.
            
            **لا يأخذ في الحسبان:** الشقوق، عدم التجانس، 
            الانتشار، الامتزاز، التفاعلات الكيميائية.
            
            **تفسير النتيجة:** زمن وصول الجبهة الأمامية فقط.
            
            ⚠️ للقرارات النهائية: معايرة ميدانية إلزامية.
            """)

    except ValueError as e:
        st.error(f"❌ خطأ: {e}")


# ============================================================
# TAB 2: الخريطة التفاعلية
# ============================================================
with tab2:
    st.header("🗺️ الخريطة التفاعلية للمواقع")

    if DATA_SOURCES_AVAILABLE:
        # إنشاء الخريطة
        m = folium.Map(
            location=[15.5, 32.5],  # السودان
            zoom_start=6,
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery",
        )

        # إضافة مواقع NARIS (أزرق)
        for name, data in NARIS_WELLS.items():
            folium.Marker(
                [data["coords"][1], data["coords"][0]],
                popup=f"<b>{name}</b><br>NARIS Well<br>K = {data.get('hydraulic_conductivity_m_day', 'N/A')} m/day",
                icon=folium.Icon(color="blue", icon="tint"),
            ).add_to(m)

        # إضافة آبار دارفور (أخضر)
        for name, data in DARFUR_WELLS.items():
            folium.Marker(
                [data["coords"][1], data["coords"][0]],
                popup=f"<b>{name}</b><br>Darfur Well<br>Depth = {data.get('depth_m', 'N/A')} m",
                icon=folium.Icon(color="green", icon="tint"),
            ).add_to(m)

        # إضافة مواقع التعدين (أحمر)
        for name, data in KNOWN_MINING_SITES.items():
            color = "red" if data.get("cyanide_use") else "orange"
            folium.Marker(
                [data["coords"][1], data["coords"][0]],
                popup=f"<b>{name}</b><br>{data.get('activity', '')}<br>Source: {data.get('source', '')}",
                icon=folium.Icon(color=color, icon="warning"),
            ).add_to(m)

        # إضافة محليات الخرطوم (بنفسجي)
        for name, data in KHARTOUM_LOCALITIES.items():
            folium.CircleMarker(
                [data["coords"][1], data["coords"][0]],
                radius=8,
                color="purple",
                fill=True,
                fill_opacity=0.5,
                popup=f"<b>{name}</b><br>Wells: {data['wells_sampled']}",
            ).add_to(m)

        st_folium(m, width="100%", height=600, key="main_map")

        st.caption(
            "🔵 آبار NARIS | 🟢 آبار دارفور | 🔴 مواقع تعدين | 🟣 محليات الخرطوم"
        )
    else:
        st.warning("⚠️ ملف data_sources.py غير متوفر — لا يمكن عرض الخريطة.")


# ============================================================
# TAB 3: المنهجية والمراجع
# ============================================================
with tab3:
    st.header("📚 المنهجية العلمية والمراجع")

    st.markdown("""
    ### 1. نموذج DRASTIC
    
    **المرجع:** Aller et al. (1987). EPA/600/2-87/035.
    
    **المعادلة:**
    ```
    DI = D×5 + R×4 + A×3 + S×2 + T×1 + I×5 + C×3
    ```
    المدى: 23 (منخفض) إلى 230 (مرتفع).
    
    ### 2. زمن وصول الملوثات
    
    **المرجع:** Fetter (2001), Applied Hydrogeology, 4th ed., pp.132-136.
    
    **المعادلة:** t = (θ · L) / (K · i)
    
    ### 3. المراجع الدولية
    
    - WHO (2022). Drinking-water Quality Guidelines.
    - US EPA (1993). EPA/600/R-93/174.
    - Minamata Convention on Mercury.
    
    ### 4. مصادر البيانات الحالية
    
    - NARIS (2005) — الحجر الرملي النوبي
    - UNEP (2007) — دارفور
    - Elsheikh et al. (2023) — الخرطوم
    
    ⚠️ **تنبيه:** جميع البيانات تحتاج تحققاً ميدانياً قبل الاستخدام الرسمي.
    """)


# ============================================================
# TAB 4: مصادر البيانات
# ============================================================
with tab4:
    st.header("💡 مصادر البيانات المجانية")

    if DATA_SOURCES_AVAILABLE:
        summary = get_data_summary()

        col1, col2, col3 = st.columns(3)
        col1.metric("إجمالي نقاط البيانات", summary["Total Data Points"])
        col2.metric("المصادر المتاحة", "3")
        col3.metric("نسبة الاكتمال", "32%")

        st.markdown("---")

        st.markdown("""
        ### 📊 المصادر المدمجة
        
        #### 1. NARIS — نظام الحجر الرملي النوبي
        - **المصدر:** CEDARE (2005)
        - **البيانات:** 11 بئراً بإحداثيات، أعماق، نفاذية
        - **الرابط:** `web.cedare.org`
        
        #### 2. UNEP — المياه الجوفية في دارفور
        - **المصدر:** UNEP (2007)
        - **البيانات:** 3 آبار بمناسيب مُراقَبة
        - **الرابط:** `wedocs.unep.org`
        
        #### 3. Elsheikh et al. (2023) — الخرطوم
        - **المصدر:** Nature Environment & Pollution Technology
        - **البيانات:** 279 بئراً في 7 محليات
        - **DOI:** 10.46488/NEPT.2023.v22i04.033
        
        #### 4. WHO (2022) — حدود جودة المياه
        - **البيانات:** حدود السيانيد والزئبق والمعادن الثقيلة
        
        ### ⚠️ ما هو غير متوفر
        
        - ❌ بيانات ميدانية حديثة لمواقع التعدين التقليدي
        - ❌ تحاليل مختبرية للزئبق والسيانيد
        - ❌ معايرة النموذج على بيانات سودانية حديثة
        - ❌ اعتماد رسمي من GRAS
        
        ### 📋 خطة استكمال البيانات (68% المتبقية)
        
        1. **زيارات ميدانية لـ 20-30 موقع تعدين** (-25%)
        2. **تحاليل مختبرية** (-15%)
        3. **معايرة النموذج** (-10%)
        4. **التحقق والـ Validation** (-8%)
        5. **ورقة علمية** (-5%)
        6. **اتفاقية GRAS** (-5%)
        
        ### 🎯 نسبة الاعتماد الحالية: **32%**
        
        بعد استكمال البيانات الميدانية: **60%**
        بعد المعايرة والورقة العلمية: **85%**
        بعد اتفاقية GRAS: **95%+**
        """)


# ============================================================
# التذييل
# ============================================================
st.markdown("---")
st.caption(
    "© 2026 جامعة الخرطوم — مكتب الاستشارات الهندسية | "
    "DRASTIC Sudan v2.0 | "
    "البيانات من NARIS, UNEP, WHO, Elsheikh et al. (2023)"
)
