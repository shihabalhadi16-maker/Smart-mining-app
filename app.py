import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
import google.generativeai as genai
from geopy.geocoders import Nominatim

# ==========================================
# 1. إعدادات الصفحة والتنسيق البصري المؤسسي
# ==========================================
st.set_page_config(
    page_title="نظام النمذجة والتقييم البيئي للتعدين",
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
    st.markdown("<h4 style='color: #c19a6b; margin-top:0;'>نظام التقييم البيئي الذكي ونمذجة مخاطر التعدين (DRASTIC Model)</h4>", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 3. قائمة المناطق المجهزة مسبقاً
# ==========================================
preset_locations = {
    "سوق طواحين أبو حمد (نهر النيل)": {"coords": (19.5333, 33.3167), "depth": 15, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.45},
    "عطبرة - النيل الكبرى (نهر النيل)": {"coords": (17.6833, 33.9833), "depth": 8, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.80},
    "سوق العبيدية (نهر النيل)": {"coords": (18.1234, 33.9876), "depth": 10, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.65},
    "مناجم بربر (نهر النيل)": {"coords": (18.0167, 33.9833), "depth": 12, "soil": "تربة طمية مختلطة (نفاذية متوسطة)", "cyanide": 0.30},
    "قبقبة / وادي العشاري (الشمالية)": {"coords": (21.8000, 34.5000), "depth": 60, "soil": "تربة صخرية صلبة (نفاذية منخفضة)", "cyanide": 0.10},
    "وادي حلفا - كرمة (الشمالية)": {"coords": (21.7950, 31.3700), "depth": 25, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.50},
    "مناجم أرياب (البحر الأحمر)": {"coords": (18.3333, 36.3500), "depth": 45, "soil": "تربة صخرية صلبة (نفاذية منخفضة)", "cyanide": 0.05},
    "سوق دلقو (الشمالية)": {"coords": (20.3000, 30.5500), "depth": 35, "soil": "تربة صخرية صلبة (نفاذية منخفضة)", "cyanide": 0.15},
    "تلودي / الليري (جبال النوبة)": {"coords": (10.6333, 30.1167), "depth": 18, "soil": "تربة طمية مختلطة (نفاذية متوسطة)", "cyanide": 0.70},
    "كادوقلي (جنوب كردفان)": {"coords": (11.0167, 29.7167), "depth": 20, "soil": "تربة طمية مختلطة (نفاذية متوسطة)", "cyanide": 0.20}
}

# إدارة الحالات (Session State)
if "selected_site_name" not in st.session_state:
    st.session_state.selected_site_name = "سوق طواحين أبو حمد (نهر النيل)"

if "lat" not in st.session_state:
    st.session_state.lat = 19.5333
if "lon" not in st.session_state:
    st.session_state.lon = 33.3167

def on_preset_change():
    site = st.session_state.preset_select
    st.session_state.selected_site_name = site
    st.session_state.lat = preset_locations[site]["coords"][0]
    st.session_state.lon = preset_locations[site]["coords"][1]

# ==========================================
# 4. التبويبات الرئيسية
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "📍 التقييم الفردي والتقرير الذكي",
    "📊 التقييم الجماعي والخرائط الحرارية (Bulk Upload)",
    "🛡️ محاكاة الحلول الهندسية"
])

# ==========================================
# TAB 1: التقييم الفردي + الذكاء الاصطناعي
# ==========================================
with tab1:
    col_input, col_display = st.columns([1, 2])

    with col_input:
        st.markdown("<h4 class='section-header'>🔍 اختيار أو البحث عن موقع</h4>", unsafe_allow_html=True)
        
        # اختيار جاهز
        st.selectbox("اختر من المناطق الجاهزة:", list(preset_locations.keys()), key="preset_select", on_change=on_preset_change)
        
        # بحث بالاسم
        custom_search = st.text_input("أو ابحث باسم أي مدينة/منجم:", placeholder="مثال: Port Sudan أو الكباشي")
        if st.button("🔍 بحث وانتقال الخريطة", use_container_width=True):
            if custom_search.strip() != "":
                geolocator = Nominatim(user_agent="smart_mining_app_sudan")
                try:
                    query = f"{custom_search}, Sudan" if "sudan" not in custom_search.lower() else custom_search
                    loc = geolocator.geocode(query, timeout=10)
                    if loc:
                        st.session_state.lat = loc.latitude
                        st.session_state.lon = loc.longitude
                        st.session_state.selected_site_name = custom_search
                        st.success(f"تم العثور على: {loc.address.split(',')[0]}")
                    else:
                        st.error("لم يتم العثور على الموقع، حاول كتابة الاسم بالإنجليزية أو التدقيق في الإملاء.")
                except Exception:
                    st.error("تعذر الاتصال بخدمة البحث عن المواقع.")

        st.markdown("---")
        st.markdown("<h4 class='section-header'>⚙️ المعطيات الجيولوجية والملوثات</h4>", unsafe_allow_html=True)
        
        lat_val = st.number_input("خط العرض (Latitude):", value=st.session_state.lat, format="%.4f")
        lon_val = st.number_input("خط الطول (Longitude):", value=st.session_state.lon, format="%.4f")
        
        depth = st.slider("عمق المياه الجوفية (متر):", 2, 100, 15)
        river_dist = st.slider("البعد عن أقرب مجرى مائي / نيل (متر):", 50, 5000, 300, step=50)
        soil = st.selectbox("نوع التربة السطحية:", ["تربة رملية هشّة (نفاذية عالية)", "تربة طمية مختلطة (نفاذية متوسطة)", "تربة صخرية صلبة (نفاذية منخفضة)"])
        cyanide = st.slider("تركيز السيانيد (Cyanide mg/L):", 0.01, 2.00, 0.45, step=0.01)

        # حسابات نموذج المخاطر و DRASTIC
        perm = 0.95 if "رملية" in soil else (0.50 if "طمية" in soil else 0.10)
        
        # مؤشر الخطر البيئي
        risk_score = (1800 / (river_dist + 1)) * (perm * 35) * (30 / depth) + (cyanide * 20)
        risk_score = min(max(round(risk_score, 1), 5.0), 98.5)
        
        # زمن الوصول للمياه الجوفية (بالسنوات)
        years = round((depth * (1.1 - perm)) / 1.3, 1)

    with col_display:
        st.markdown(f"<h4 class='section-header'>📊 النتائج والتقييم للموقع: {st.session_state.selected_site_name}</h4>", unsafe_allow_html=True)
        
        # عرض المؤشرات الثلاثة الرئيسية
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric("مؤشر الخطر البيئي", f"{risk_score}%")
        with kpi2:
            st.metric("زمن وصول التسرب للمياه", f"{years} سنة")
        with kpi3:
            status = "⚠️ يتجاوز الحد الآمن" if cyanide > 0.05 else "✅ ضمن الحد المسموح"
            st.metric("تركيز السيانيد", f"{cyanide} mg/L", delta=status, delta_color="inverse" if cyanide > 0.05 else "normal")

        # الخريطة التفاعلية
        st.markdown("##### 🗺️ الخريطة التفاعلية ونطاق التأثير")
        m = folium.Map(location=[lat_val, lon_val], zoom_start=11, tiles="OpenStreetMap")
        
        marker_color = "red" if risk_score >= 70 else ("orange" if risk_score >= 40 else "green")
        
        folium.Marker(
            [lat_val, lon_val],
            popup=f"موقع المنجم: {st.session_state.selected_site_name}<br>مؤشر الخطر: {risk_score}%",
            tooltip=st.session_state.selected_site_name,
            icon=folium.Icon(color=marker_color, icon="warning")
        ).add_to(m)
        
        # دائرة نطاق الأمان البيئي
        folium.Circle(
            [lat_val, lon_val],
            radius=river_dist,
            color=marker_color,
            fill=True,
            fill_opacity=0.2,
            popup="نطاق التأثير الهيدروجيولوجي المتوقع"
        ).add_to(m)
        
        st_folium(m, width="100%", height=380)

        # قسم الذكاء الاصطناعي لتوليد التقرير
        st.markdown("---")
        st.markdown("<h4 class='section-header'>🤖 التقرير البيئي بالذكاء الاصطناعي (Gemini)</h4>", unsafe_allow_html=True)
        
        if st.button("✨ توليد تقرير فني شامل بالذكاء الاصطناعي", type="primary", use_container_width=True):
            if "GEMINI_API_KEY" in st.secrets:
                try:
                    with st.spinner("جاري كتابة وتحليل التقرير البيئي بواسطة الذكاء الاصطناعي..."):
                        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        prompt = f"""
                        أنت خبير بيئي وهيدروجيولوجي متخصص في التعدين بجامعة الخرطوم.
                        قم بكتابة تقرير تقييم أثر بيئي مفصل لموقع: {st.session_state.selected_site_name}
                        المعطيات:
                        - الإحداثيات: ({lat_val}, {lon_val})
                        - عمق المياه الجوفية: {depth} متر
                        - نوع التربة: {soil}
                        - البعد عن المجرى المائي: {river_dist} متر
                        - تركيز السيانيد: {cyanide} ملجم/لتر (الحد الآمن العالمي هو 0.05)
                        - مؤشر الخطر المحسوب: {risk_score}%
                        - الزمن المتوقع لوصول الملوثات للمياه: {years} سنة

                        يرجى صياغة التقرير في المحاور التالية:
                        1. تقييم مدى الخطورة على المياه الجوفية والسطحية.
                        2. الأثر الصحي على المجتمعات المحيطة.
                        3. التوصيات والتدابير الهندسية الواجب اتخاذها فوراً.
                        """
                        response = model.generate_content(prompt)
                        st.info(response.text)
                except Exception as e:
                    st.error(f"حدث خطأ أثناء الاتصال بالذكاء الاصطناعي: {e}")
            else:
                st.warning("⚠️ يرجى إضافة مفتاح GEMINI_API_KEY في صفحة Secrets على Streamlit Cloud ليتمكن النظام من كتابة التقرير.")

# ==========================================
# TAB 2: التقييم الجماعي والخرائط الحرارية
# ==========================================
with tab2:
    st.markdown("<h4 class='section-header'>📤 رفع ملف البيانات الجماعي (Bulk Upload)</h4>", unsafe_allow_html=True)
    st.caption("يمكنك رفع ملف Excel أو CSV يحتوي على أسماء وأحداثيات عدة مناجم لعرضها دفعة واحدة على الخريطة الحرارية.")
    
    uploaded_file = st.file_uploader("اختر ملف Excel أو CSV:", type=["xlsx", "csv"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_bulk = pd.read_csv(uploaded_file)
            else:
                df_bulk = pd.read_excel(uploaded_file)
                
            st.success(f"تم تحميل {len(df_bulk)} موقع بنجاح من الملف.")
            
            col_tbl, col_heat = st.columns([1, 1])
            with col_tbl:
                st.markdown("##### جدول المواقع المرفوعة")
                st.dataframe(df_bulk, use_container_width=True)
                
            with col_heat:
                st.markdown("##### الخريطة الحرارية لتركيزات الملوثات (Heatmap)")
                map_center = [df_bulk['Latitude'].mean(), df_bulk['Longitude'].mean()]
                m_heat = folium.Map(location=map_center, zoom_start=6)
                
                heat_data = [[row['Latitude'], row['Longitude'], row['Cyanide']] for index, row in df_bulk.iterrows() if 'Latitude' in row and 'Longitude' in row and 'Cyanide' in row]
                HeatMap(heat_data, radius=15).add_to(m_heat)
                
                st_folium(m_heat, width="100%", height=380)
        except Exception as e:
            st.error(f"تأكد من اختيار الملف الصحيح وتطابق أسماء الأعمدة: {e}")

# ==========================================
# TAB 3: محاكي الحلول الهندسية
# ==========================================
with tab3:
    st.markdown("<h4 class='section-header'>🛡️ محاكاة تأثير الحلول الهندسية الوقائية</h4>", unsafe_allow_html=True)
    st.info("قياس نسبة الانخفاض في الخطر البيئي عند استخدام تقنيات العزل والمعالجة الحديثة.")
    
    col_sc1, col_sc2 = st.columns(2)
    
    with col_sc1:
        st.subheader("الوضع الحالي (بدون عزل)")
        st.error(f"مؤشر الخطر الحالي: {risk_score}%")
        st.warning(f"زمن وصول الملوثات: {years} سنة")
        
    with col_sc2:
        st.subheader("الوضع المتوقع بعد التدابير الهندسية")
        liner = st.checkbox("تركيب بطانة عازلة مزدوجة عالية الكثافة (HDPE Liner)")
        treatment = st.checkbox("تطبيق وحدة معالجة السيانيد بالكيميائيات (Cyanide Destruction Unit)")
        
        mitigated_score = risk_score
        if liner:
            mitigated_score *= 0.35  # خفض الخطر 65%
        if treatment:
            mitigated_score *= 0.50  # خفض الخطر 50%
            
        mitigated_score = round(mitigated_score, 1)
        st.success(f"مؤشر الخطر المتوقع: {mitigated_score}%")
        
        reduction = round(((risk_score - mitigated_score) / risk_score) * 100, 1) if risk_score > 0 else 0
        st.metric("نسبة انخفاض الخطر البيئي الإجمالية", f"{reduction}%")
