import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# ==========================================
# 1. تهيئة وإعدادات الصفحة الرئيسية
# ==========================================
st.set_page_config(
    page_title="نظام التعدين الذكي - جامعة الخرطوم",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. التنسيق البصري (CSS)
# ==========================================
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(rgba(244, 238, 218, 0.88), rgba(193, 154, 107, 0.92)),
                    url('https://images.unsplash.com/photo-1578328819058-b69f3a3b0f6b?q=80&w=1600&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #5c2c16 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #f5eedc !important;
        border-right: 2px solid #c19a6b;
    }
    div[data-testid="stMetric"], div.stSelectbox, div.stNumberInput, div.stSlider, div.stTextInput {
        background-color: rgba(255, 255, 255, 0.70) !important;
        border-radius: 10px;
        padding: 8px;
        border: 1px solid #d4af37;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. الهيدر الرئيسي مع شعار جامعة الخرطوم
# ==========================================
col_logo, col_title = st.columns([1, 5])

with col_logo:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png", width=105)

with col_title:
    st.title("⛏️ نظام التعدين الذكي وتقييم المخاطر البيئية")
    st.caption("جامعة الخرطوم — كلية الهندسة — قسم هندسة التعدين | نظام الذكاء الاصطناعي للتنبؤ بالتسرب الجوفي")

st.markdown("---")

# ==========================================
# 4. القائمة الجانبية والبحث التلقائي بالاسم
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png", width=140)
st.sidebar.header("🔍 إدخال بيانات الموقع والبحث")

# قاعدة بيانات محلية سريعة لأشهر مناطق التعدين بالسودان
preset_locations = {
    "أبو حمد (نهر النيل)": (19.5333, 33.3167),
    "عطبرة (نهر النيل)": (17.6833, 33.9833),
    "بربر (نهر النيل)": (18.0167, 33.9833),
    "القباب (البحر الأحمر)": (21.8000, 35.5000),
    "هيا (البحر الأحمر)": (18.3333, 36.3500),
    "كادوقلي (جنوب كردفان)": (11.0167, 29.7167),
    "إدخال موقع آخـر / بحث تلقائي": None
}

selected_preset = st.sidebar.selectbox("اختر منطقة تعدين معروفة:", list(preset_locations.keys()))

if selected_preset != "إدخال موقع آخـر / بحث تلقائي":
    lat_default, lon_default = preset_locations[selected_preset]
    site_name = selected_preset
else:
    site_name = st.sidebar.text_input("اكتب اسم المدينة / المنطقة للبحث:", "Atbara, Sudan")
    
    # البحث التلقائي باستخدام Geopy
    geolocator = Nominatim(user_agent="mining_app_uofk")
    try:
        location = geolocator.geocode(site_name)
        if location:
            lat_default = location.latitude
            lon_default = location.longitude
            st.sidebar.success(f"📍 تم العثور على الموقع: {location.address[:30]}...")
        else:
            lat_default, lon_default = 18.55, 33.82
            st.sidebar.warning("لم يتم العثور على الموقع، تم استخدام الإحداثيات الافتراضية.")
    except:
        lat_default, lon_default = 18.55, 33.82

lat_input = st.sidebar.number_input("خط العرض (Latitude):", value=float(lat_default), format="%.4f")
lon_input = st.sidebar.number_input("خط الطول (Longitude):", value=float(lon_default), format="%.4f")

map_style = st.sidebar.selectbox(
    "نوع الخريطة:",
    ["قمر صناعي (Satellite)", "خريطة شوارع (OpenStreetMap)"]
)

st.sidebar.markdown("---")
st.sidebar.header("📊 المعطيات الهيدروجيولوجية والهندسية")

water_depth = st.sidebar.slider("عمق المياه الجوفية (متر):", min_value=2, max_value=150, value=20)
river_dist = st.sidebar.slider("البعد عن أقرب مجرى مائي (متر):", min_value=20, max_value=5000, value=350, step=50)
soil_type = st.sidebar.selectbox(
    "نوع التربة والهيكلية الجيولوجية:",
    ["تربة صخرية صلبة (نفاذية منخفضة)", "تربة طمية مختلطة (نفاذية متوسطة)", "تربة رملية هشّة (نفاذية عالية)"]
)
cyanide_conc = st.sidebar.slider("تركيز السيانيد/الزئبق (mg/L):", min_value=0.01, max_value=2.00, value=0.15, step=0.01)

# ==========================================
# 5. الحسابات
# ==========================================
perm = 0.1 if "صخرية" in soil_type else (0.5 if "طمية" in soil_type else 0.95)
risk_score = (1800 / (river_dist + 1)) * (perm * 35) * (30 / water_depth) + (cyanide_conc * 15)
risk_score = min(max(round(risk_score, 1), 5.0), 98.5)

# ==========================================
# 6. عرض النتائج والمؤشرات
# ==========================================
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="درجة الخطر التقديرية (Score)", value=f"{risk_score}%")

with col2:
    status = "✅ مطابق للمواصفات" if cyanide_conc <= 0.05 else "⚠️ يتجاوز حد WHO"
    st.metric(label="تركيز السيانيد", value=f"{cyanide_conc} mg/L", delta=status, delta_color="inverse" if cyanide_conc > 0.05 else "normal")

with col3:
    years = round((water_depth * (1.1 - perm)) / 1.3, 1)
    st.metric(label="زمن وصول التسرب للمياه الجوفية", value=f"{years} سنة")

st.markdown("---")

# ==========================================
# 7. الخريطة التفاعلية
# ==========================================
st.subheader(f"🗺️ الخريطة التفاعلية للموقع: {site_name}")

if map_style == "قمر صناعي (Satellite)":
    m = folium.Map(location=[lat_input, lon_input], zoom_start=11, tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri')
else:
    m = folium.Map(location=[lat_input, lon_input], zoom_start=11)

marker_color = "red" if risk_score >= 70 else ("orange" if risk_score >= 40 else "green")

folium.Marker(
    location=[lat_input, lon_input],
    popup=f"<b>المنجم:</b> {site_name}<br><b>درجة الخطر:</b> {risk_score}%",
    tooltip=site_name,
    icon=folium.Icon(color=marker_color, icon="info-sign")
).add_to(m)

folium.Circle(
    location=[lat_input, lon_input],
    radius=river_dist,
    color=marker_color,
    fill=True,
    fill_opacity=0.2,
    popup="نطاق التأثير المتوقع"
).add_to(m)

st_folium(m, width="100%", height=450)
