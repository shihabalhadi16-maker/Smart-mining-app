import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import google.generativeai as genai
# ==========================================
# 1. تهيئة مفتاح الذكاء الاصطناعي
# ==========================================
API_KEY = "ضع_مفتاحك_هنا_بين_التنصيص"  # <--- ضع مفتاح Gemini الخاص بك هنا
# ==========================================
# 2. إعدادات اسم وأيقونة التطبيق المتكاملة
# ==========================================
st.set_page_config(
    page_title="نظام التعدين الذكي",
    page_icon="⛏️",
    layout="wide"
)
# كود تخصيص الأيقونة واسم التطبيق لشاشة الجوال الرئيسية والمتصفح
pwa_meta = """
<meta name="apple-mobile-web-app-title" content="التعدين الذكي">
<meta name="application-name" content="نظام التعدين الذكي">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/2921/2921961.png">
<link rel="icon" type="image/png" href="https://cdn-icons-png.flaticon.com/512/2921/2921961.png">
"""
st.markdown(pwa_meta, unsafe_allow_html=True)
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
    div[data-testid="stMetric"], div.stSelectbox, div.stNumberInput, div.stSlider {
        background-color: rgba(255, 255, 255, 0.65) !important;
        border-radius: 10px;
        padding: 8px;
        border: 1px solid #d4af37;
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)
# ==========================================
# 4. العنوان الرئيسي
# ==========================================
st.title("⛏️ نظام التعدين الذكي وتقييم المخاطر البيئية")
st.caption("جامعة الخرطوم - قسم هندسة التعدين | نظام الذكاء الاصطناعي للتنبؤ بالتسرب الجوفي")
st.markdown("---")
# ==========================================
# 5. القائمة الجانبية (مدخلات البيانات)
# ==========================================
st.sidebar.header("🔍 إدخال بيانات الموقع الميداني")
site_name = st.sidebar.text_input("اسم المنجم / المنطقة:", "منجم نهر النيل - Block A4")
lat_input = st.sidebar.number_input("خط العرض (Latitude):", value=18.5500, format="%.4f")
lon_input = st.sidebar.number_input("خط الطول (Longitude):", value=33.8200, format="%.4f")
st.sidebar.markdown("---")
st.sidebar.header("📊 المعطيات البيئية والجيولوجية")
water_depth = st.sidebar.slider("عمق المياه الجوفية (متر):", min_value=2, max_value=150, value=20)
river_dist = st.sidebar.slider("البعد عن أقرب مجرى مائي (متر):", min_value=20, max_value=5000, value=350, step=50)
soil_type = st.sidebar.selectbox(
    "نوع التربة والهيكلية الجيولوجية:",
    ["تربة صخرية صلبة (نفاذية منخفضة)", "تربة طمية مختلطة (نفاذية متوسطة)", "تربة رملية هشّة (نفاذية عالية)"]
)
cyanide_conc = st.sidebar.slider("تركيز السيانيد/الزئبق (mg/L):", min_value=0.01, max_value=2.00, value=0.15, step=0.01)
# ==========================================
# 6. المعادلة الحسابية للتقييم
# ==========================================
perm = 0.1 if "صخرية" in soil_type else (0.5 if "طمية" in soil_type else 0.95)
risk_score = (1800 / (river_dist + 1)) * (perm * 35) * (30 / water_depth) + (cyanide_conc * 15)
risk_score = min(max(round(risk_score, 1), 5.0), 98.5)

# ==========================================
# 7. عرض النتائج والمؤشرات
# ==========================================
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="درجة الخطر التقديرية (Risk Score)", value=f"{risk_score}%")
with col2:
    status = "✅ مطابق للمواصفات" if cyanide_conc <= 0.05 else "⚠️ يتجاوز حد WHO"
    st.metric(label="تركيز السيانيد الحصري", value=f"{cyanide_conc} mg/L", delta=status, delta_color="inverse" if cyanide_conc > 0.05 else "normal")
with col3:
    years = round((water_depth * (1.1 - perm)) / 1.3, 1)
    st.metric(label="زمن وصول التسرب للمياه الجوفية", value=f"{years} سنة")

st.markdown("---")

# ==========================================
# 8. قسم الذكاء الاصطناعي (توليد التقرير)
# ==========================================
st.subheader("🤖 التقرير والاستشارة البيئية بالذكاء الاصطناعي")

if st.button("توليد التقرير البيئي الشامل ⚡"):
    if API_KEY == "ضع_مفتاحك_هنا_بين_التنصيص" or not API_KEY:
        st.error("⚠️ يرجى وضع مفتاح Gemini API في السطر رقم 9 داخل الكود أولاً.")
    else
        with st.spinner("جاري تحليل المعطيات وتوليد التوصيات الهندسية..."):
            try:
                genai.configure(api_key=API_KEY)
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"""
                أنت خبير بيئي وهندسي متخصص في مجال التعدين بالسودان. قم بتوليد تقرير تقييم مخاطر للموقع التالي:
                - اسم المنجم: {site_name}
                - تركيز السيانيد/الزئبق: {cyanide_conc} mg/L
                - عمق المياه الجوفية: {water_depth} متر
                - البعد عن أقرب مجرى مائي: {river_dist} متر
                - نوع التربة: {soil_type}
                - نسبة الخطر البيئي المحسوبة: {risk_score}%
                
                يرجى تقديم:
                1. تقييم سريع ومباشر لمدى خطورة الوضع على المياه الجوفية.
                2. توصيات هندسية سريعة وميدانية للحد من هذا التسرب وتقليل المخاطر.
                """
                response = model.generate_content(prompt)
                st.success("تم توليد التقرير بنجاح!")
                st.write(response.text)
            except Exception as e:
                st.error(f"حدث خطأ أثناء الاتصال بالذكاء الاصطناعي: {e}")

st.markdown("---")

# ==========================================
# 9. الخريطة التفاعلية
# ==========================================
st.subheader("🗺️ الخريطة التفاعلية لموقع المنجم")
m = folium.Map(location=[lat_input, lon_input], zoom_start=12)
marker_color = "red" if risk_score >= 70 else ("orange" if risk_score >= 40 else "green")

folium.Marker(
    location=[lat_input, lon_input],
    popup=f"<b>المنجم:</b> {site_name}<br><b>درجة الخطر:</b> {risk_score}%",
    tooltip=site_name,
    icon=folium.Icon(color=marker_color, icon="info-sign")
).add_to(m)

st_folium(m, width="100%", height=400)
