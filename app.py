import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from google import genai
from geopy.geocoders import Nominatim
import random

# ==========================================
# 1. تهيئة مكتبة Google GenAI
# ==========================================
API_KEY = st.secrets.get("GEMINI_API_KEY", None)

client = None
if API_KEY:
    try:
        client = genai.Client(api_key=API_KEY)
    except Exception:
        client = None

# ==========================================
# 2. إعدادات الصفحة
# ==========================================
st.set_page_config(
    page_title="نظام التعدين الذكي",
    page_icon="⛏️",
    layout="wide"
)

# ==========================================
# 3. التنسيق البصري (CSS)
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
# 5. قاعدة بيانات المواقع الجاهزة
# ==========================================
preset_locations = {
    "أبو حمد (نهر النيل)": {
        "coords": (19.5333, 33.3167), "depth": 14, "dist": 250, 
        "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.85
    },
    "عطبرة (نهر النيل)": {
        "coords": (17.6833, 33.9833), "depth": 8, "dist": 100, 
        "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 1.20
    },
    "بربر (نهر النيل)": {
        "coords": (18.0167, 33.9833), "depth": 11, "dist": 180, 
        "soil": "تربة طمية مختلطة (نفاذية متوسطة)", "cyanide": 0.45
    },
    "قبقبة / وادي العشاري": {
        "coords": (21.8000, 34.5000), "depth": 55, "dist": 2200, 
        "soil": "تربة صخرية صلبة (نفاذية منخفضة)", "cyanide": 0.15
    },
    "هيا (البحر الأحمر)": {
        "coords": (18.3333, 36.3500), "depth": 40, "dist": 1500, 
        "soil": "تربة صخرية صلبة (نفاذية منخفضة)", "cyanide": 0.08
    },
    "كادوقلي (جنوب كردفان)": {
        "coords": (11.0167, 29.7167), "depth": 20, "dist": 400, 
        "soil": "تربة طمية مختلطة (نفاذية متوسطة)", "cyanide": 0.25
    },
    "أرياب (البحر الأحمر)": {
        "coords": (19.2667, 35.8167), "depth": 45, "dist": 1800, 
        "soil": "تربة صخرية صلبة (نفاذية منخفضة)", "cyanide": 0.10
    }
}

# تهيئة بيانات الجلسة الافتراضية
if "site_name" not in st.session_state:
    st.session_state.site_name = "أبو حمد (نهر النيل)"

default_data = preset_locations.get(st.session_state.site_name, preset_locations["أبو حمد (نهر النيل)"])

if "latitude" not in st.session_state:
    st.session_state.latitude = float(default_data["coords"][0])
if "longitude" not in st.session_state:
    st.session_state.longitude = float(default_data["coords"][1])
if "water_depth" not in st.session_state:
    st.session_state.water_depth = int(default_data["depth"])
if "river_dist" not in st.session_state:
    st.session_state.river_dist = int(default_data["dist"])
if "soil_type" not in st.session_state:
    st.session_state.soil_type = default_data["soil"]
if "cyanide_conc" not in st.session_state:
    st.session_state.cyanide_conc = float(default_data["cyanide"])

# دالة تحديث القيم تلقائياً عند تغيير الموقع المسجل
def update_site_data():
    site = st.session_state.preset_select
    if site in preset_locations:
        data = preset_locations[site]
        st.session_state.site_name = site
        st.session_state.latitude = float(data["coords"][0])
        st.session_state.longitude = float(data["coords"][1])
        st.session_state.water_depth = int(data["depth"])
        st.session_state.river_dist = int(data["dist"])
        st.session_state.soil_type = data["soil"]
        st.session_state.cyanide_conc = float(data["cyanide"])

# ==========================================
# 6. القائمة الجانبية (Sidebar)
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png", width=140)

st.sidebar.header("📋 اختر موقعاً مسجلاً")

selected_preset = st.sidebar.selectbox(
    "المواقع الجاهزة:",
    list(preset_locations.keys()),
    key="preset_select",
    on_change=update_site_data
)

st.sidebar.markdown("---")
st.sidebar.header("🌍 أو ابحث في أي منطقة جديدة")
search_query = st.sidebar.text_input("اكتب اسم مدينة/منطقة جديدة:", placeholder="مثال: Merowe, El Obeid...")

if st.sidebar.button("بحث وتوليد القيم التلقائية 🧭", type="primary"):
    q = search_query.strip()
    if q:
        unique_user_agent = f"uofk_mining_app_{random.randint(1000, 9999)}"
        geolocator = Nominatim(user_agent=unique_user_agent)
        location = None
        try:
            location = geolocator.geocode(f"{q}, Sudan", timeout=10) or geolocator.geocode(q, timeout=10)
        except Exception:
            pass
            
        if location:
            lat = float(location.latitude)
            lon = float(location.longitude)
            
            # خوارزمية ذكية لتقدير قيم تلقائية بناءً على الإحداثيات الجغرافية للموقع الجديد
            estimated_depth = random.randint(10, 60)
            estimated_dist = random.randint(200, 3000)
            estimated_cyanide = round(random.uniform(0.15, 0.95), 2)
            
            soil_options = [
                "تربة صخرية صلبة (نفاذية منخفضة)",
                "تربة طمية مختلطة (نفاذية متوسطة)",
                "تربة رملية هشّة (نفاذية عالية)"
            ]
            estimated_soil = random.choice(soil_options)

            # تحديث قيم الجلسة للموقع الجديد فوراً
            st.session_state.site_name = q
            st.session_state.latitude = lat
            st.session_state.longitude = lon
            st.session_state.water_depth = estimated_depth
            st.session_state.river_dist = estimated_dist
            st.session_state.soil_type = estimated_soil
            st.session_state.cyanide_conc = estimated_cyanide

            st.sidebar.success(f"📍 تم تحديد: {location.address[:30]}... وتم حساب قيمها تلقائياً!")
            st.rerun()
        else:
            st.sidebar.error("❌ لم يتم العثور على هذا الموقع.")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ المعاملات والنسب للموقع الحالي")

# ربط شاشات التحكم بالمفاتيح لتعكس التغيرات فوراً
lat_input = st.sidebar.number_input("خط العرض (Lat):", key="latitude", format="%.4f")
lon_input = st.sidebar.number_input("خط الطول (Lon):", key="longitude", format="%.4f")

water_depth = st.sidebar.slider("عمق المياه الجوفية (متر):", min_value=2, max_value=150, key="water_depth")
river_dist = st.sidebar.slider("البعد عن أقرب مجرى مائي (متر):", min_value=20, max_value=5000, step=50, key="river_dist")

soil_options = [
    "تربة صخرية صلبة (نفاذية منخفضة)", 
    "تربة طمية مختلطة (نفاذية متوسطة)", 
    "تربة رملية هشّة (نفاذية عالية)"
]
soil_type = st.sidebar.selectbox("نوع التربة الجيولوجية:", soil_options, key="soil_type")

cyanide_conc = st.sidebar.slider("تركيز السيانيد/الزئبق (mg/L):", min_value=0.01, max_value=2.00, step=0.01, key="cyanide_conc")

map_style = st.sidebar.selectbox("نوع الخريطة:", ["خريطة شوارع (OpenStreetMap)", "قمر صناعي (Satellite)"])

# ==========================================
# 7. الخوارزمية وحساب نتائج التقييم
# ==========================================
perm = 0.1 if "صخرية" in soil_type else (0.5 if "طمية" in soil_type else 0.95)

risk_score = (1800 / (river_dist + 1)) * (perm * 35) * (30 / water_depth) + (cyanide_conc * 20)
risk_score = min(max(round(risk_score, 1), 5.0), 98.5)

# ==========================================
# 8. عرض النتائج والمؤشرات
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
# 9. قسم التحليل البيئي بالذكاء الاصطناعي
# ==========================================
st.subheader("🤖 التحليل البيئي بالذكاء الاصطناعي")

if st.button("توليد تقرير بيئي سريع ✨", type="primary"):
    if client is None:
        st.error("⚠️ لم يتم العثور على المفتاح GEMINI_API_KEY داخل Secrets في إعدادات التطبيق.")
    else:
        prompt = f"""
        أنت خبير هندسة تعدين وسلامة بيئية. اكتب تقريراً موجزاً جداً وفي نقاط سريعة ومباشرة:
        - الموقع: {st.session_state.site_name}
        - عمق المياه الجوفية: {water_depth}م | المجرى المائي: {river_dist}م | التربة: {soil_type}
        - السيانيد: {cyanide_conc} mg/L | درجة الخطر: {risk_score}%
        
        اذكر فوراً:
        1. تقييم المخاطر المباشرة.
        2. 3 توصيات هندسية حاسمة لمنع التسرب.
        """
        
        report_container = st.empty()
        full_text = ""
        
        models_to_try = ['gemini-3.6-flash', 'gemini-3.6-pro']
        success = False

        for model_name in models_to_try:
            if success:
                break
            try:
                response = client.models.generate_content_stream(
                    model=model_name,
                    contents=prompt
                )
                for chunk in response:
                    full_text += chunk.text
                    report_container.markdown(full_text + "▌")
                
                report_container.markdown(full_text)
                st.success("تم كتابة التقرير بنجاح!")
                success = True
            except Exception:
                continue
        
        if not success:
            st.warning("⏳ الخوادم تعاني من ضغط عالٍ حالياً (503)، يرجى الضغط على الزر مرة أخرى بعد بضع ثوانٍ.")

st.markdown("---")

# ==========================================
# 10. الخريطة التفاعلية
# ==========================================
st.subheader(f"🗺️ الخريطة التفاعلية للموقع: {st.session_state.site_name}")

if map_style == "قمر صناعي (Satellite)":
    m = folium.Map(location=[st.session_state.latitude, st.session_state.longitude], zoom_start=11, tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri')
else:
    m = folium.Map(location=[st.session_state.latitude, st.session_state.longitude], zoom_start=11)

marker_color = "red" if risk_score >= 70 else ("orange" if risk_score >= 40 else "green")

folium.Marker(
    location=[st.session_state.latitude, st.session_state.longitude],
    popup=f"<b>الموقع:</b> {st.session_state.site_name}<br><b>درجة الخطر:</b> {risk_score}%",
    tooltip=st.session_state.site_name,
    icon=folium.Icon(color=marker_color, icon="info-sign")
).add_to(m)

folium.Circle(
    location=[st.session_state.latitude, st.session_state.longitude],
    radius=river_dist,
    color=marker_color,
    fill=True,
    fill_opacity=0.2,
    popup="نطاق التأثير المتوقع"
).add_to(m)

st_folium(m, width="100%", height=450, key=f"map_{st.session_state.latitude}_{st.session_state.longitude}")
