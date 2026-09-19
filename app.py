import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import base64

# 1. تهيئة الصفحة وضبط الإعدادات الأساسية
st.set_page_config(
    page_title="نظام التعدين الذكي - جامعة الخرطوم",
    page_icon="⛏️",
    layout="wide"
)

# 2. إضافة التغيير الشامل للون التطبيق واللفية والخلفية عبر CSS
# الألوان: بيج رملي (f4eeda)، بني ذهبي (d4af37)، رملي غامق (c19a6b)، بني محروق (8b4513)
st.markdown("""
<style>
    /* تغيير خلفية التطبيق بالكامل */
    .stApp {
        background: linear-gradient(135deg, rgba(244, 238, 218, 0.98), rgba(193, 154, 107, 0.95)),
                    url('https://images.unsplash.com/photo-1542171120-0beea7f5edc0?q=80&w=2000&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    /* ضبط لون النص الرئيسي */
    p, span, .css-qrb3un {
        color: #5c4033 !important; /* لون بني داكن */
    }

    /* تغيير لون شريط التمرير والسلايدر */
    .stSlider > div > div > div > div > span {
        background-color: #d4af37 !important; /* بني ذهبي */
    }
    
    /* ضبط نمط العناوين */
    h1, h2, h3, h4, h5, h6 {
        color: #8b4513 !important; /* بني محروق */
        font-family: 'Droid Arabic Naskh', sans-serif;
    }

    /* تغيير لون خلفية القائمة الجانبية (Sidebar) */
    .css-1d391kg {
        background-color: #f4eeda !important; /* بيج رملي */
        border-right: 2px solid #c19a6b;
    }

    /* تغيير نمط الصناديق والمربعات */
    div.stSelectbox > div, div.stNumberInput > div, div.stSlider > div, .stMetric {
        background-color: rgba(255, 255, 255, 0.5) !important;
        border-radius: 8px;
        padding: 5px;
        color: #5c4033;
    }

    /* تخصيص مؤشر الأداء الميتريكس */
    [data-testid="stMetricValue"] {
        color: #8b4513 !important;
    }
</style>
""", unsafe_allow_safe_allow_html=True)

# 3. العنوان الرئيسي
st.title("⛏️ نظام التعدين الذكي وتقييم المخاطر البيئية")
st.caption("جامعة الخرطوم - قسم هندسة التعدين | نظام الذكاء الاصطناعي للتنبؤ بالتسرب الجوفي")
st.markdown("---")

# 4. القائمة الجانبية (Sidebar)
st.sidebar.header("🔍 إدخال بيانات الموقع والبحث")

# أ) خاصية البحث وتحديد المواقع
site_name = st.sidebar.text_input("اسم المنجم / المنطقة:", "منجم نهر النيل - Block A4")
lat_input = st.sidebar.number_input("خط العرض (Latitude):", value=18.55, format="%.4f")
lon_input = st.sidebar.number_input("خط الطول (Longitude):", value=33.82, format="%.4f")

# ب) اختيار نوع الخريطة
map_style = st.sidebar.selectbox(
    "نوع الخريطة:",
    ["قمر صناعي (Satellite)", "خريطة شوارع (OpenStreetMap)", "خريطة تضاريس (Terrain)"]
)

st.sidebar.markdown("---")
st.sidebar.header("📊 المعطيات الهيدروجيولوجية والهندسية")

# ج) مدخلات النموذج
water_depth = st.sidebar.slider("عمق المياه الجوفية (متر):", min_value=2, max_value=150, value=20)
river_dist = st.sidebar.slider("البعد عن أقرب مجرى مائي (متر):", min_value=20, max_value=5000, value=350, step=50)
soil_type = st.sidebar.selectbox(
    "نوع التربة والهيكلية الجيولوجية:",
    ["تربة صخرية صلبة (نفاذية منخفضة)", "تربة طمية مختلطة (نفاذية متوسطة)", "تربة رملية هشّة (نفاذية عالية)"]
)
cyanide_conc = st.sidebar.slider("تركيز السيانيد/الزئبق (mg/L):", min_value=0.01, max_value=2.00, value=0.15, step=0.01)

# 5. الحسابات
# معامل النفاذية
perm = 0.1 if "صخرية" in soil_type else (0.5 if "طمية" in soil_type else 0.95)

# حساب نسبة الخطر بذكاء
risk_score = (1800 / (river_dist + 1)) * (perm * 35) * (30 / water_depth) + (cyanide_conc * 15)
risk_score = min(max(round(risk_score, 1), 5.0), 98.5)

# 6. عرض النتائج الرئيسية في واجهة الصفحة
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

# 7. الخريطة التفاعلية
st.subheader("🗺️ الخريطة التفاعلية للموقع المحدد والمنطقة المحيطة")

# تحديد طبقة الخريطة
if map_style == "قمر صناعي (Satellite)":
    # إضافة خريطة القمر الصناعي بشكل صحيح
    m = folium.Map(location=[lat_input, lon_input], zoom_start=12, tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri')
elif map_style == "خريطة تضاريس (Terrain)":
    m = folium.Map(location=[lat_input, lon_input], zoom_start=12, tiles='Stamen Terrain', attr='Stamen')
else:
    m = folium.Map(location=[lat_input, lon_input], zoom_start=12)

# لون المؤشر بناءً على درجة الخطر
marker_color = "red" if risk_score >= 70 else ("orange" if risk_score >= 40 else "green")

# إضافة مؤشر المنجم
folium.Marker(
    location=[lat_input, lon_input],
    popup=f"<b>المنجم:</b> {site_name}<br><b>درجة الخطر:</b> {risk_score}%",
    tooltip=site_name,
    icon=folium.Icon(color=marker_color, icon="info-sign")
).add_to(m)

# رسم دائرة نطاق التأثير الجيولوجي
folium.Circle(
    location=[lat_input, lon_input],
    radius=river_dist,
    color=marker_color,
    fill=True,
    fill_opacity=0.2,
    popup="نطاق التأثير المتوقع"
).add_to(m)

# عرض الخريطة داخل التطبيق
st_folium(m, width="100%", height=450)
