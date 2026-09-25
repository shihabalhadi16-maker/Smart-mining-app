import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
import google.generativeai as genai
from geopy.geocoders import Nominatim
import datetime

# ==========================================
# 1. إعدادات الصفحة والتنسيق البصري المؤسسي
# ==========================================
st.set_page_config(
    page_title="نظام النمذجة والتقييم البيئي للتعدين - DRASTIC",
    page_icon="⛏️",
    layout="wide"
)

st.markdown("""
<style>
    .stApp {
        background-color: #f8f9fa;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #d4af37;
        border-radius: 10px;
        padding: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    [data-testid="stSidebar"] {
        background-color: #f5eedc !important;
        border-right: 2px solid #c19a6b;
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

# ==========================================
# 2. الهيدر الرئيسي
# ==========================================
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png", width=90)
with col_title:
    st.markdown("<h2 style='color: #5c2c16; margin-bottom:0;'>جامعة الخرطوم — كلية الهندسة</h2>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #c19a6b; margin-top:0;'>نظام التقييم البيئي الذكي المعتمد (DRASTIC Standard Model)</h4>", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 3. قاعدة البيانات المحلية وإدارة الجلسة
# ==========================================
preset_locations = {
    "سوق طواحين أبو حمد (نهر النيل)": {"coords": (19.5333, 33.3167), "depth": 15.0, "cyanide": 0.45},
    "عطبرة - النيل الكبرى (نهر النيل)": {"coords": (17.6833, 33.9833), "depth": 8.0, "cyanide": 0.80},
    "سوق العبيدية (نهر النيل)": {"coords": (18.1234, 33.9876), "depth": 10.0, "cyanide": 0.65},
    "مناجم بربر (نهر النيل)": {"coords": (18.0167, 33.9833), "depth": 12.0, "cyanide": 0.30},
    "وادي العشاري / قبقبة (الشمالية)": {"coords": (21.8000, 34.5000), "depth": 45.0, "cyanide": 0.10},
    "وادي حلفا - كرمة (الشمالية)": {"coords": (21.7950, 31.3700), "depth": 25.0, "cyanide": 0.50},
    "مناجم أرياب (البحر الأحمر)": {"coords": (18.3333, 36.3500), "depth": 40.0, "cyanide": 0.05},
    "سوق دلقو (الشمالية)": {"coords": (20.3000, 30.5500), "depth": 35.0, "cyanide": 0.15},
    "تلودي / الليري (جبال النوبة)": {"coords": (10.6333, 30.1167), "depth": 18.0, "cyanide": 0.70},
    "كادوقلي (جنوب كردفان)": {"coords": (11.0167, 29.7167), "depth": 20.0, "cyanide": 0.20}
}

if "selected_site_name" not in st.session_state:
    st.session_state.selected_site_name = "سوق طواحين أبو حمد (نهر النيل)"
if "lat" not in st.session_state:
    st.session_state.lat = 19.5333
if "lon" not in st.session_state:
    st.session_state.lon = 33.3167
if "ai_report_text" not in st.session_state:
    st.session_state.ai_report_text = ""

def on_preset_change():
    site = st.session_state.preset_select
    st.session_state.selected_site_name = site
    st.session_state.lat = preset_locations[site]["coords"][0]
    st.session_state.lon = preset_locations[site]["coords"][1]
    st.session_state.ai_report_text = ""

# ==========================================
# 4. التبويبات الرئيسية
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "📍 التقييم الفردي وإصدار التقارير",
    "📊 التقييم الجماعي والخرائط الحرارية (Bulk Upload)",
    "🛡️ محاكاة الحلول الهندسية"
])

# ==========================================
# TAB 1: التقييم الفردي
# ==========================================
with tab1:
    col_input, col_display = st.columns([1, 2])

    with col_input:
        st.markdown("<h4 class='section-header'>🔍 اختيار أو البحث عن موقع</h4>", unsafe_allow_html=True)
        st.selectbox("اختر من المناطق الجاهزة:", list(preset_locations.keys()), key="preset_select", on_change=on_preset_change)
        
        custom_search = st.text_input("أو ابحث باسم أي مدينة/منجم:", placeholder="مثال: Berber")
        if st.button("🔍 بحث وانتقال الخريطة", use_container_width=True):
            query_str = custom_search.strip()
            if query_str != "":
                geolocator = Nominatim(user_agent="uofk_smart_mining_v11")
                try:
                    q = f"{query_str}, Sudan" if "sudan" not in query_str.lower() else query_str
                    loc = geolocator.geocode(q, timeout=8)
                    if loc:
                        st.session_state.lat = loc.latitude
                        st.session_state.lon = loc.longitude
                        st.session_state.selected_site_name = query_str
                        st.session_state.ai_report_text = ""
                        st.success(f"تم العثور على: {loc.address.split(',')[0]}")
                        st.rerun()
                except Exception:
                    st.error("تعذر الوصول لخدمة البحث، يمكنك الاختيار من القائمة الجاهزة.")

        st.markdown("---")
        st.markdown("<h4 class='section-header'>⚙️ مدخلات نموذج DRASTIC (US EPA)</h4>", unsafe_allow_html=True)
        
        lat_val = st.number_input("خط العرض (Latitude):", value=st.session_state.lat, format="%.4f")
        lon_val = st.number_input("خط الطول (Longitude):", value=st.session_state.lon, format="%.4f")
        
        depth = st.slider("1. عمق المياه الجوفية D (متر):", 0.5, 60.0, 15.0, step=0.5)
        if depth < 1.5: r_D = 10
        elif depth < 4.5: r_D = 9
        elif depth < 9.1: r_D = 7
        elif depth < 15.2: r_D = 5
        elif depth < 22.9: r_D = 3
        else: r_D = 1

        recharge = st.selectbox("2. معدل التغذية السنوية R (مم/سنة):", ["منخفض (< 50 مم)", "متوسط (50 - 100 مم)", "عالي (> 100 مم)"])
        r_R = 1 if "منخفض" in recharge else (6 if "متوسط" in recharge else 9)

        aquifer = st.selectbox("3. نوع صخور الخزان الجوفي A:", ["صخور صماء / باسالتي (Basalt)", "حجر رملي (Sandstone)", "حصى ورمل مشبع (Gravel & Sand)"])
        r_A = 3 if "صخور" in aquifer else (6 if "حجر" in aquifer else 8)

        soil = st.selectbox("4. نوع التربة السطحية S:", ["طين عازل (Clay)", "سلت / طمي (Silt)", "تربة رملية هشّة (Sand/Gravel)"])
        r_S = 1 if "طين" in soil else (4 if "سلت" in soil else 9)

        topo = st.slider("5. نسبة انحدار الأرض T (%):", 0, 30, 4)
        if topo < 2: r_T = 10
        elif topo < 6: r_T = 9
        elif topo < 12: r_T = 5
        else: r_T = 1

        vadose = st.selectbox("6. طبيعة المنطقة غير المشبعة I:", ["طبقات طينية متماسكة", "حجر رملي / متشقق", "حصى ورمل نفاذ"])
        r_I = 3 if "طينية" in vadose else (6 if "رملي" in vadose else 8)

        cond = st.selectbox("7. النفاذية الهيدروليكية C:", ["منخفضة جداً", "متوسطة", "عالية جداً"])
        r_C = 1 if "منخفضة" in cond else (4 if "متوسطة" in cond else 8)

        st.markdown("---")
        st.markdown("<h4 class='section-header'>🧪 الملوثات والمسافات الميدانية</h4>", unsafe_allow_html=True)
        river_dist = st.slider("البعد عن أقرب مجرى مائي / وادي (متر):", 50, 5000, 300, step=50)
        cyanide = st.slider("تركيز السيانيد (Cyanide mg/L):", 0.01, 2.00, 0.45, step=0.01)

        # حساب نموذج DRASTIC
        w_D, w_R, w_A, w_S, w_T, w_I, w_C = 5, 4, 3, 2, 1, 5, 3
        drastic_index = (r_D * w_D) + (r_R * w_R) + (r_A * w_A) + (r_S * w_S) + (r_T * w_T) + (r_I * w_I) + (r_C * w_C)
        risk_score = round((drastic_index / 230) * 100, 1)
        perm_factor = 0.95 if "رملية" in soil else (0.50 if "سلت" in soil else 0.10)
        years = round((depth * (1.1 - perm_factor)) / 1.3, 1)

    with col_display:
        st.markdown(f"<h4 class='section-header'>📊 النتائج للموقع: {st.session_state.selected_site_name}</h4>", unsafe_allow_html=True)
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("مؤشر DRASTIC", f"{drastic_index} / 230")
        kpi2.metric("نسبة الخطر البيئي", f"{risk_score}%")
        kpi3.metric("زمن وصول التسرب", f"{years} سنة")
        status = "⚠️ يتجاوز الحد" if cyanide > 0.05 else "✅ ضمن المسموح"
        kpi4.metric("تركيز السيانيد", f"{cyanide} mg/L", delta=status, delta_color="inverse" if cyanide > 0.05 else "normal")

        # الخريطة الفضائية
        st.markdown("##### 🛰️ خريطة الأقمار الصناعية")
        m = folium.Map(
            location=[lat_val, lon_val], 
            zoom_start=13, 
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery"
        )
        folium.TileLayer(
            tiles="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png",
            attr="CartoDB",
            name="أسماء المناطق والطرق",
            overlay=True
        ).add_to(m)

        marker_color = "red" if drastic_index >= 160 else ("orange" if drastic_index >= 120 else "green")
        folium.Marker(
            [lat_val, lon_val],
            popup=f"موقع المنجم: {st.session_state.selected_site_name}<br>مؤشر DRASTIC: {drastic_index}",
            icon=folium.Icon(color=marker_color, icon="warning")
        ).add_to(m)
        
        folium.Circle(
            [lat_val, lon_val],
            radius=river_dist,
            color=marker_color,
            fill=True,
            fill_opacity=0.25
        ).add_to(m)
        
        st_folium(m, width="100%", height=350, key="sat_map")

        # ==========================================
        # الذكاء الاصطناعي (Gemini 3.8 Flash) وتصدير التقرير
        # ==========================================
        st.markdown("---")
        st.markdown("<h4 class='section-header'>⚡ توليد التقرير المعتمد وتصديره (Gemini 3.8 Flash)</h4>", unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns([2, 1])
        
        with col_btn1:
            if st.button("✨ توليد التقرير المعتمد عبر Gemini 3.8 Flash", type="primary", use_container_width=True):
                if "GEMINI_API_KEY" in st.secrets:
                    try:
                        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                        
                        # اعتماد نموذج gemini-3.8-flash المحدث مباشرة
                        model = genai.GenerativeModel(
                            'gemini-3.8-flash',
                            generation_config={"temperature": 0.2, "max_output_tokens": 2048}
                        )

                        prompt = f"""
                        بصفتك خبير استشاري في هيدروجيولوجيا التعدين بجامعة الخرطوم، قم بإعداد تقرير هندسي وتقييمي متكامل وبند بـ بند لموقع: {st.session_state.selected_site_name}.
                        
                        المعطيات الفنية الميدانية:
                        - مؤشر DRASTIC الإجمالي: {drastic_index} من 230 (نسبة الخطر البيئي: {risk_score}%)
                        - عمق المياه الجوفية (D): {depth} متر
                        - معدل التغذية السنوية (R): {recharge}
                        - نوع التربة السطحية (S): {soil}
                        - البعد عن المجرى المائي: {river_dist} متر
                        - تركيز السيانيد/الزئبق الميداني: {cyanide} mg/L (الحد المسموح به من الصحة العالمية WHO هو 0.05 mg/L)
                        - زمن وصول التسرب المتوقع: {years} سنة
                        
                        يرجى كتابة التقرير باللغة العربية بتنسيق منظم يغطي النقاط التالية بشكل كافٍ ومكتمل دون أي اختصار:
                        1. **التقييم الهيدروجيولوجي الشامل ومستوى الخطورة:**
                        2. **تحليل انتشار ملوثات السيانيد وأثرها على المياه الجوفية:**
                        3. **التوصيات والتدابير الهندسية العاجلة الواجب اتخاذها في الموقع:**
                        """
                        
                        with st.spinner("جاري صياغة التقرير الفني المكتمل باستخدام Gemini 3.8 Flash..."):
                            response = model.generate_content(prompt)
                            st.session_state.ai_report_text = response.text
                            st.success("تم توليد التقرير المكتمل بنجاح!")
                            
                    except Exception as e:
                        if "429" in str(e):
                            st.warning("⏳ تجاوزت الحد المسموح للطلبات. يرجى الانتظار بضع ثوانٍ ثم إعادة المحاولة.")
                        else:
                            st.error(f"خطأ في الاتصال بالنموذج: {e}")
                else:
                    st.warning("⚠️ يرجى إضافة مفتاح GEMINI_API_KEY في قسم Secrets على Streamlit Cloud.")

        # عرض التقرير المتولد
        if st.session_state.ai_report_text:
            st.markdown("##### 📄 النص المعتمد للتقرير:")
            st.info(st.session_state.ai_report_text)

        # تجهيز المستند النهائي المحمول للتصدير
        today_date = datetime.date.today().strftime("%Y-%m-%d")
        full_export_document = f"""====================================================================
جامعة الخرطوم — كلية الهندسة — قسم هندسة التعدين
تقرير التقييم البيئي والهيدروجيولوجي المعتمد (DRASTIC Standard Model)
====================================================================
تاريخ التقرير: {today_date}
الموقع المستهدف: {st.session_state.selected_site_name}
الإحداثيات الجغرافية: Latitude {lat_val:.4f}, Longitude {lon_val:.4f}
معيار النمذجة: US EPA DRASTIC Standard Model
محرك التحليل الذكي: Gemini 3.8 Flash Engine
--------------------------------------------------------------------

أولاً: البيانات الحسابية الميدانية ومؤشرات DRASTIC:
----------------------------------------------------
* مؤشر DRASTIC الإجمالي: {drastic_index} / 230
* نسبة الخطر البيئي التراكمية: {risk_score}%
* زمن وصول التسرب للمياه الجوفية: {years} سنة
* تركيز السيانيد الميداني: {cyanide} mg/L (الحد الأقصى المسموح: 0.05 mg/L)
* عمق المياه الجوفية (D): {depth} متر
* نوع التربة السطحية (S): {soil}
* البعد عن المجرى المائي: {river_dist} متر

ثانياً: التقرير الفني المعتمد وتحليل الذكاء الاصطناعي:
----------------------------------------------------
{st.session_state.ai_report_text if st.session_state.ai_report_text else "لم يتم ضغط زر توليد التقرير قبل التصدير."}

====================================================================
صُدر هذا المستند هندسياً عبر منصة النمذجة البيئية — جامعة الخرطوم
====================================================================
"""

        with col_btn2:
            st.download_button(
                label="📥 تصدير التقرير كملف (DOC/TXT)",
                data=full_export_document,
                file_name=f"DRASTIC_Report_{st.session_state.selected_site_name}.txt",
                mime="text/plain",
                use_container_width=True
            )

# ==========================================
# TAB 2: التقييم الجماعي
# ==========================================
with tab2:
    st.markdown("<h4 class='section-header'>📤 رفع ملف البيانات الجماعي (Bulk Upload)</h4>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("اختر ملف Excel أو CSV:", type=["xlsx", "csv"])
    
    if uploaded_file is not None:
        try:
            df_bulk = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            st.success(f"تم تحميل {len(df_bulk)} موقع بنجاح.")
            
            col_tbl, col_heat = st.columns([1, 1])
            with col_tbl:
                st.dataframe(df_bulk, use_container_width=True)
            with col_heat:
                m_heat = folium.Map(
                    location=[df_bulk['Latitude'].mean(), df_bulk['Longitude'].mean()], 
                    zoom_start=6,
                    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                    attr="Esri World Imagery"
                )
                heat_data = [[row['Latitude'], row['Longitude'], row['Cyanide']] for _, row in df_bulk.iterrows() if 'Latitude' in row and 'Longitude' in row]
                HeatMap(heat_data, radius=15).add_to(m_heat)
                st_folium(m_heat, width="100%", height=380, key="bulk_heat_map")
        except Exception as e:
            st.error(f"خطأ في قراءة الملف: {e}")

# ==========================================
# TAB 3: محاكي الحلول الهندسية
# ==========================================
with tab3:
    st.markdown("<h4 class='section-header'>🛡️ محاكاة تأثير الحلول الهندسية الوقائية</h4>", unsafe_allow_html=True)
    col_sc1, col_sc2 = st.columns(2)
    
    with col_sc1:
        st.subheader("الوضع الحالي")
        st.error(f"مؤشر DRASTIC الحالي: {drastic_index} / 230")
        st.warning(f"نسبة الخطر الحالية: {risk_score}%")
        
    with col_sc2:
        st.subheader("الوضع بعد تطبيق الحلول")
        liner = st.checkbox("تركيب بطانة عازلة HDPE Liner")
        treatment = st.checkbox("وحدة معالجة السيانيد الكيميائية")
        
        mitigated_drastic = drastic_index
        if liner: mitigated_drastic *= 0.40  
        if treatment: mitigated_drastic *= 0.60  
            
        mitigated_drastic = round(mitigated_drastic, 1)
        st.success(f"مؤشر DRASTIC المتوقع: {mitigated_drastic} / 230")
        reduction = round(((drastic_index - mitigated_drastic) / drastic_index) * 100, 1) if drastic_index > 0 else 0
        st.metric("نسبة خفض الخطر البيئي", f"{reduction}%")
