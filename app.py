import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

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
# 2. إعدادات معاينة الرابط عند المشاركة (Meta Tags)
# ==========================================
st.markdown("""
    <head>
        <meta property="og:title" content="منصة التعدين الذكي وتقييم المخاطر البيئية">
        <meta property="og:description" content="نظام ذكاء اصطناعي للتنبؤ بمخاطر تسرب التلوث في مناجم السودان - جامعة الخرطوم">
        <meta property="og:image" content="https://images.unsplash.com/photo-1578328819058-b69f3a3b0f6b?q=80&w=1200">
    </head>
""", unsafe_allow_html=True)

# ==========================================
# 3. التنسيق البصري (CSS) - اللون الرملي وتصميم التعدين
# ==========================================
st.markdown("""
<style>
    /* خلفية التطبيق متدرجة باللون الرملي مع خلفية تعدين */
    .stApp {
        background: linear-gradient(rgba(244, 238, 218, 0.88), rgba(193, 154, 107, 0.92)),
                    url('https://images.unsplash.com/photo-1578328819058-b69f3a3b0f6b?q=80&w=1600&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    /* نصوص العناوين باللون البني الصحراوي */
    h1, h2, h3, h4, h5, h6 {
        color: #5c2c16 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* القائمة الجانبية باللون البيج الرملي */
    [data-testid="stSidebar"] {
        background-color: #f5eedc !important;
        border-right: 2px solid #c19a6b;
    }

    /* إبراز المربعات والبطاقات بلمسة شفافة ودبابيس ذهبية */
    div[data-testid="stMetric"], div.stSelectbox, div.stNumberInput, div.stSlider, div.stTextInput {
        background-color: rgba(255, 255, 255, 0.70) !important;
        border-radius: 10px;
        padding: 8px;
        border: 1px solid #d4af37;
    }
    
    /* إخفاء القوائم الافتراضية لإعطاء طابع احترافي */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. الهيدر الرئيسي مع شعار جامعة الخرطوم
# ==========================================
col_logo, col_title = st.columns([1, 5])

with col_logo:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png", width=105)

with col_title:
    st.title("⛏️ نظام التعدين الذكي وتقييم المخاطر البيئية")
    st.caption("جامعة الخرطوم — كلية الهندسة — قسم هندسة التعدين | نظام الذكاء الاصطناعي للتنبؤ بالتسرب الجوفي")

st.markdown("---")

# ==========================================
# 5. القائمة الجانبية (Sidebar)
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png", width=140)
st.sidebar.header("🔍 إدخال بيانات الموقع والبحث")

site_name = st.sidebar.text_input("اسم المنجم / المنطقة:", "منجم نهر النيل - Block A4")
lat_input = st.sidebar.number_input("خط العرض (Latitude):", value=18.55, format="%.4f")
lon_input = st.sidebar.number_input("خط الطول (Longitude):", value=33.82, format="%.4f")

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
# 6. الحسابات والخوارزمية
# ==========================================
perm = 0.1 if "صخرية" in soil_type else (0.5 if "طمية" in soil_type else 0.95)
risk_score = (1800 / (river_dist + 1)) * (perm * 35) * (30 / water_depth) + (cyanide_conc * 15)
risk_score = min(max(round(risk_score, 1), 5.0), 98.5)

# ==========================================
# 7. عرض النتائج والمؤشرات
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
# 8. الخريطة التفاعلية
# ==========================================
st.subheader("🗺️ الخريطة التفاعلية للموقع المحدد")

if map_style == "قمر صناعي (Satellite)":
    m = folium.Map(location=[lat_input, lon_input], zoom_start=12, tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri')
else:
    m = folium.Map(location=[lat_input, lon_input], zoom_start=12)

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
