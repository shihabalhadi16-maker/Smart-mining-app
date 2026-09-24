import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
import google.generativeai as genai
from geopy.geocoders import Nominatim

# ==========================================
# 1. إعدادات الصفحة والمعايير البصرية (Corporate Standards)
# ==========================================
st.set_page_config(
    page_title="نظام النمذجة الهيدروجيولوجية والتقييم البيئي للتعدين",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Enterprise CSS
st.markdown("""
<style>
    :root {
        --primary-color: #5C2C16;
        --secondary-color: #C19A6B;
        --bg-color: #F8F9FA;
        --card-bg: #FFFFFF;
    }
    .stApp {
        background-color: var(--bg-color);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: var(--card-bg) !important;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetric"] label {
        color: #666666 !important;
        font-size: 0.9rem !important;
        font-weight: 600;
    }
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #F4EEDA !important;
        border-right: 1px solid #D4AF37;
    }
    /* Section Headers */
    .section-header {
        color: #5C2C16;
        border-bottom: 2px solid #C19A6B;
        padding-bottom: 8px;
        margin-bottom: 20px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. الهيدر المؤسسي وشعار الجامعة
# ==========================================
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png", width=90)
with col_title:
    st.markdown("<h2 style='color: #5C2C16; margin-bottom:0;'>جامعة الخرطوم — كلية الهندسة</h2>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #C19A6B; margin-top:0;'>نظام النمذجة الجيومكانية والتقييم البيئي لموقع التعدين (DRASTIC Model)</h4>", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 3. محرك نموذج DRASTIC العلمي
# ==========================================
def calculate_drastic_index(depth, recharge, soil_type, slope, cyanide_conc):
    # D: Depth to Water rating (1-10)
    d_rating = 10 if depth < 5 else (9 if depth < 15 else (7 if depth < 30 else (3 if depth < 50 else 1)))
    
    # R: Recharge rating
    r_rating = 8 if recharge == "عالية (أمطار/سيول)" else (5 if recharge == "متوسطة" else 2)
    
    # S: Soil Media rating
    s_rating = 10 if "رملية" in soil_type else (6 if "طمية" in soil_type else 2)
    
    # T: Topography (Slope) rating
    t_rating = 10 if slope < 2 else (9 if slope < 6 else (5 if slope < 12 else 1))
    
    # Standard Weights (EPA DRASTIC Model)
    Dw, Rw, Sw, Tw = 5, 4, 2, 1
    
    # Base DRASTIC Index
    drastic_score = (d_rating * Dw) + (r_rating * Rw) + (s_rating * Sw) + (t_rating * Tw)
    
    # Vulnerability Classification
    if drastic_score >= 85:
        category = "عالية جداً (Very High Vulnerability)"
        color = "#D32F2F"
    elif drastic_score >= 65:
        category = "عالية (High Vulnerability)"
        color = "#F57C00"
    elif drastic_score >= 45:
        category = "متوسطة (Moderate Vulnerability)"
        color = "#FBC02D"
    else:
        category = "منخفضة (Low Vulnerability)"
        color = "#388E3C"
        
    return drastic_score, category, color

# ==========================================
# 4. تبويبات النظام (Main Navigation Tabs)
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "📍 تقييم موقع فردي (Single Site Assessment)",
    "📊 التقييم الجماعي والخرائط الحرارية (Bulk Upload & Heatmaps)",
    "🛡️ محاكي السيناريوهات والحلول الهندسية (Engineering Mitigation)"
])

# ==========================================
# TAB 1: تقييم موقع فردي
# ==========================================
with tab1:
    col_input, col_map = st.columns([1, 2])
    
    with col_input:
        st.markdown("<h4 class='section-header'>⚙️ المدخلات الجيولوجية والهيدرولوجية</h4>", unsafe_allow_html=True)
        
        search_query = st.text_input("🔍 البحث بالاسم عن موقع/منجم:", value="أبوحمد, السودان")
        if st.button("انتقال للموقع"):
            geolocator = Nominatim(user_agent="smart_mining_app")
            try:
                loc = geolocator.geocode(search_query)
                if loc:
                    st.session_state['lat'] = loc.latitude
                    st.session_state['lon'] = loc.longitude
                    st.success("تم تحديد الموقع بنجاح.")
                else:
                    st.error("لم يتم العثور على الموقع.")
            except Exception:
                st.error("تعذر الاتصال بخدمة الخرائط.")
                
        lat = st.number_input("خط العرض (Latitude):", value=st.session_state.get('lat', 19.5333), format="%.4f")
        lon = st.number_input("خط الطول (Longitude):", value=st.session_state.get('lon', 33.3167), format="%.4f")
        
        depth = st.slider("عمق المياه الجوفية (متر):", 1, 100, 15)
        soil = st.selectbox("نوع التربة السطحية:", ["تربة رملية هشّة (نفاذية عالية)", "تربة طمية مختلطة (نفاذية متوسطة)", "تربة صخرية صلبة (نفاذية منخفضة)"])
        recharge = st.selectbox("معدل التغذية المائية (Recharge):", ["منخفضة (مناطق جافة)", "متوسطة", "عالية (أمطار/سيول)"])
        slope = st.slider("انحدار السطح (Topography Slope %):", 0, 20, 2)
        cyanide = st.slider("تركيز الملوث الملاحظ (Cyanide mg/L):", 0.00, 2.00, 0.45, step=0.01)

        score, category, color = calculate_drastic_index(depth, recharge, soil, slope, cyanide)

    with col_map:
        st.markdown("<h4 class='section-header'>📌 المخرجات واللوحة الجيومكانية</h4>", unsafe_allow_html=True)
        
        # Dashboard Cards
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric("مؤشر DRASTIC", f"{score} pts")
        with kpi2:
            st.metric("درجة هشاشة الخزان الجوفي", category)
        with kpi3:
            st.metric("تركيز السيانيد", f"{cyanide} mg/L", delta="يتجاوز المعايير" if cyanide > 0.05 else "ضمن المعايير الآمنة", delta_color="inverse" if cyanide > 0.05 else "normal")
            
        # Folium Map
        m = folium.Map(location=[lat, lon], zoom_start=11, tiles="OpenStreetMap")
        
        folium.Marker(
            [lat, lon],
            popup=f"موقع المنجم<br>DRASTIC: {score}<br>الوضع: {category}",
            tooltip="موقع المنجم الخاضع للفحص",
            icon=folium.Icon(color="red" if score >= 65 else "orange" if score >= 45 else "green", icon="warning")
        ).add_to(m)
        
        # Buffer Zone Safety Boundary (500m)
        folium.Circle(
            [lat, lon],
            radius=1000,
            color=color,
            fill=True,
            fill_opacity=0.25,
            popup="حرم الأمان البيئي المقترح (1000 متر)"
        ).add_to(m)
        
        st_folium(m, width="100%", height=420)

# ==========================================
# TAB 2: التقييم الجماعي والخرائط الحرارية
# ==========================================
with tab2:
    st.markdown("<h4 class='section-header'>📤 رفع وتقييم بيانات الولايات (Bulk Analysis & Spatial Heatmap)</h4>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("قم برفع ملف Excel أو CSV يحتوي على أحداثيات ومواصفات المناجم:", type=["xlsx", "csv"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_bulk = pd.read_csv(uploaded_file)
            else:
                df_bulk = pd.read_excel(uploaded_file)
                
            st.success(f"تم تحميل {len(df_bulk)} موقع بنجاح.")
            
            # Display Data Frame Summary
            col_tbl, col_heat = st.columns([1, 1])
            with col_tbl:
                st.dataframe(df_bulk.head(10), use_container_width=True)
                
            with col_heat:
                # Generate Heatmap
                map_center = [df_bulk['Latitude'].mean(), df_bulk['Longitude'].mean()]
                m_heat = folium.Map(location=map_center, zoom_start=6)
                
                heat_data = [[row['Latitude'], row['Longitude'], row['Cyanide']] for index, row in df_bulk.iterrows()]
                HeatMap(heat_data, radius=15).add_to(m_heat)
                
                st_folium(m_heat, width="100%", height=350)
        except Exception as e:
            st.error(f"حدث خطأ أثناء قراءة الملف: {e}")

# ==========================================
# TAB 3: محاكي الحلول الهندسية
# ==========================================
with tab3:
    st.markdown("<h4 class='section-header'>🛡️ محاكاة الحلول والتدابير الهندسية الوقائية (Mitigation Scenarios)</h4>", unsafe_allow_html=True)
    
    st.info("تسمح هذه الأداة بتقدير مدى انخفاض نسبة خطر التسرب عند تطبيق تقنيات عزل حديثة في أحواض التعدين.")
    
    col_sc1, col_sc2 = st.columns(2)
    
    with col_sc1:
        st.subheader("الوضع الحالي (بدون عزل)")
        curr_score = score
        st.error(f"مؤشر الخطر الحقيقي: {curr_score} pts ({category})")
        
    with col_sc2:
        st.subheader("الوضع بعد تطبيق الحل الهندسي")
        liner = st.checkbox("تركيب بطانة عازلة مزدوجة High-Density Polyethylene (HDPE Liner)")
        treatment = st.checkbox("تطبيق وحدة المعالجة بالكيميائيات (INCO SO2/Air Cyanide Destruction)")
        
        mitigated_score = curr_score
        if liner:
            mitigated_score *= 0.35  # تخفيض الخطر بنسبة 65%
        if treatment:
            mitigated_score *= 0.50  # تخفيض الخطر بنسبة 50%
            
        mitigated_score = round(mitigated_score, 1)
        st.success(f"مؤشر الخطر المتوقع بعد التدابير: {mitigated_score} pts")
        
        reduction = round(((curr_score - mitigated_score) / curr_score) * 100, 1) if curr_score > 0 else 0
        st.metric("نسبة خفض المخاطر البيئية", f"{reduction}%")
