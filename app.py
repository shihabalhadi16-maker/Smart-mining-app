import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import google.generativeai as genai
from geopy.geocoders import Nominatim
import random

# ==========================================
# 1. تهيئة مفتاح الذكاء الاصطناعي
# ==========================================
API_KEY = "ضع_مفتاحك_هنا_بين_التنصيص"  # <--- ضع مفتاح Gemini الخاص بك هنا

if API_KEY and API_KEY != "AQ.Ab8RN6IV5s_KbsKQSFRchYhhyaRaBBzIgSM9cg2NfW0V7i5oGA ":
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        model = None
else:
    model = None

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
# 5. إدارة حالة الجلسة والإحداثيات الأولية
# ==========================================
preset_locations = {
    "أبو حمد (نهر النيل)": (19.5333, 33.3167),
    "عطبرة (نهر النيل)": (17.6833, 33.9833),
    "بربر (نهر النيل)": (18.0167, 33.9833),
    "قبقبة / وادي العشاري": (21.8000, 34.5000),
    "هيا (البحر الأحمر)": (18.3333, 36.3500),
    "كادوقلي (جنوب كردفان)": (11.0167, 29.7167),
    "أرياب (البحر الأحمر)": (19.2667, 35.8167)
}

if "latitude" not in st.session_state:
    st.session_state.latitude = 19.5333
if "longitude" not in st.session_state:
    st.session_state.longitude = 33.3167
if "site_name" not in st.session_state:
    st.session_state.site_name = "أبو حمد (نهر النيل)"

# ==========================================
# 6. القائمة الجانبية ووظائف البحث العالمية
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png", width=140)

st.sidebar.header("🌍 البحث في أي منطقة في العالم")
search_query = st.sidebar.text_input("اكتب اسم مدينة/منطقة/منجم:", placeholder="مثال: Ariab, الخرطوم, Cairo...")

if st.sidebar.button("بحث عالمي 🧭", type="primary"):
    q = search_query.strip()
    if q:
        # إنشاء اسم معرف عشوائي لتفادي حظر السيرفرات
        unique_user_agent = f"uofk_mining_app_{random.randint(1000, 9999)}"
        geolocator = Nominatim(user_agent=unique_user_agent)
        
        location = None
        try:
            # المحاولة الأولى: البحث بإضافة اسم "Sudan" لزيادة دقة البحث المحلي
            location = geolocator.geocode(f"{q}, Sudan", timeout=12)
        except Exception:
            pass
            
        if not location:
            try:
                # المحاولة الثانية: البحث المباشر في قاعدة البيانات العالمية
                location = geolocator.geocode(q, timeout=12)
            except Exception:
                pass
                
        if location:
            st.session_state.latitude = float(location.latitude)
            st.session_state.longitude = float(location.longitude)
            st.session_state.site_name = q
            st.sidebar.success(f"📍 تم العثور على: {location.address[:40]}...")
            st.rerun()
        else:
            st.sidebar.error("❌ لم يتم العثور على هذا الموقع. جرب كتابة الاسم بالإنجليزية أو اختياره من القائمة.")

st.sidebar.markdown("---")
st.sidebar.header("📋 أو اختر من المواقع السودانية الجاهزة")

selected_preset = st.sidebar.selectbox(
    "مناطق تعدين مسجلة:",
    ["-- اختر موقعاً --"] + list(preset_locations.keys())
)

if selected_preset != "-- اختر موقعاً --":
    coords = preset_locations[selected_preset]
    if st.session_state.latitude != coords[0] or st.session_state.longitude != coords[1]:
        st.session_state.latitude = coords[0]
        st.session_state.longitude = coords[1]
        st.session_state.site_name = selected_preset
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("📍 الإحداثيات الحالية")

lat_input = st.sidebar.number_input("خط العرض (Lat):", value=st.session_state.latitude, format="%.4f")
lon_input = st.sidebar.number_input("خط الطول (Lon):", value=st.session_state.longitude, format="%.4f")

st.session_state.latitude = lat_input
st.session_state.longitude = lon_input

map_style = st.sidebar.selectbox(
    "نوع الخريطة:",
    ["خريطة شوارع (OpenStreetMap)", "قمر صناعي (Satellite)"]
)

st.sidebar.markdown("---")
st.sidebar.header("📊 المعطيات الهيدروجيولوجية والهندسية")

water_depth = st.sidebar.slider("عمق المياه الجوفية (متر):", min_value=2, max_value=150, value=15)
river_dist = st.sidebar.slider("البعد عن أقرب مجرى مائي (متر):", min_value=20, max_value=5000, value=250, step=50)
soil_type = st.sidebar.selectbox(
    "نوع التربة والهيكلية الجيولوجية:",
    ["تربة صخرية صلبة (نفاذية منخفضة)", "تربة طمية مختلطة (نفاذية متوسطة)", "تربة رملية هشّة (نفاذية عالية)"]
)
cyanide_conc = st.sidebar.slider("تركيز السيانيد/الزئبق (mg/L):", min_value=0.01, max_value=2.00, value=0.45, step=0.01)

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
    if model is None:
        st.warning("يرجى إضافة مفتاح API_KEY الصحيح في السطر 9 لتفعيل خدمة الذكاء الاصطناعي.")
    else:
        with st.spinner("جاري تحليل المعطيات وتوليد التقرير الهندسي..."):
            prompt = f"""
            أنت خبير هندسة تعدين وسلامة بيئية. قم بتوليد تقرير تقييم مخاطر مختصر لمنطقة التعدين التالية:
            - اسم الموقع: {st.session_state.site_name}
            - الإحداثيات: {st.session_state.latitude}, {st.session_state.longitude}
            - عمق المياه الجوفية: {water_depth} متر
            - البعد عن أقرب مجرى مائي: {river_dist} متر
            - نوع التربة: {soil_type}
            - تركيز السيانيد/الزئبق: {cyanide_conc} mg/L
            - درجة الخطر التقديرية: {risk_score}%
            
            قدم التوصيات الهندسية والإجراءات التصحيحية المباشرة للحفاظ على البيئة والمياه الجوفية.
            """
            try:
                response = model.generate_content(prompt)
                st.success("تم توليد التقرير بنجاح:")
                st.write(response.text)
            except Exception as e:
                st.error(f"حدث خطأ أثناء الاتصال بالذكاء الاصطناعي: {e}")

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
