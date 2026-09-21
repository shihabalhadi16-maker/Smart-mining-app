import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import Geocoder
import google.generativeai as genai

# ==========================================
# 1. إعدادات الصفحة
# ==========================================
st.set_page_config(
    page_title="نظام التعدين الذكي",
    page_icon="⛏️",
    layout="wide"
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
# 3. الهيدر الرئيسي
# ==========================================
col_logo, col_title = st.columns([1, 5])

with col_logo:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png", width=105)

with col_title:
    st.title("⛏️ نظام التعدين الذكي وتقييم المخاطر البيئية")
    st.caption("جامعة الخرطوم — كلية الهندسة — قسم هندسة التعدين")

st.markdown("---")

# ==========================================
# 4. قائمة المناطق الشاملة في السودان
# ==========================================
preset_locations = {
    "سوق طواحين أبو حمد (نهر النيل)": {"coords": (19.5333, 33.3167), "depth": 15, "dist": 250, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.45},
    "عطبرة - النيل الكبرى (نهر النيل)": {"coords": (17.6833, 33.9833), "depth": 8, "dist": 100, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.80},
    "سوق العبيدية (نهر النيل)": {"coords": (18.1234, 33.9876), "depth": 10, "dist": 300, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.65},
    "مناجم بربر (نهر النيل)": {"coords": (18.0167, 33.9833), "depth": 12, "dist": 180, "soil": "تربة طمية مختلطة (نفاذية متوسطة)", "cyanide": 0.30},
    "قبقبة / وادي العشاري (الشمالية)": {"coords": (21.8000, 34.5000), "depth": 60, "dist": 2500, "soil": "تربة صخرية صلبة (نفاذية منخفضة)", "cyanide": 0.10},
    "وادي حلفا - كرمة (الشمالية)": {"coords": (21.7950, 31.3700), "depth": 25, "dist": 600, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.50},
    "مناجم أرياب (البحر الأحمر)": {"coords": (18.3333, 36.3500), "depth": 45, "dist": 1500, "soil": "تربة صخرية صلبة (نفاذية منخفضة)", "cyanide": 0.05},
    "سوق دلقو (الشمالية)": {"coords": (20.3000, 30.5500), "depth": 35, "dist": 1200, "soil": "تربة صخرية صلبة (نفاذية منخفضة)", "cyanide": 0.15},
    "تلودي / الليري (جبال النوبة)": {"coords": (10.6333, 30.1167), "depth": 18, "dist": 350, "soil": "تربة طمية مختلطة (نفاذية متوسطة)", "cyanide": 0.70},
    "كادوقلي (جنوب كردفان)": {"coords": (11.0167, 29.7167), "depth": 20, "dist": 400, "soil": "تربة طمية مختلطة (نفاذية متوسطة)", "cyanide": 0.20},
    "سوق سنقو (جنوب دارفور)": {"coords": (9.8333, 23.6500), "depth": 22, "dist": 500, "soil": "تربة طمية مختلطة (نفاذية متوسطة)", "cyanide": 0.25},
    "📍 إدخال موقع مخصص / إحداثيات": {"coords": (19.5333, 33.3167), "depth": 15, "dist": 250, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.10}
}

if "selected_preset" not in st.session_state:
    st.session_state.selected_preset = "سوق طواحين أبو حمد (نهر النيل)"

def update_preset_values():
    selected = st.session_state.selected_preset
    data = preset_locations[selected]
    st.session_state.val_lat = float(data["coords"][0])
    st.session_state.val_lon = float(data["coords"][1])
    st.session_state.val_depth = int(data["depth"])
    st.session_state.val_dist = int(data["dist"])
    st.session_state.val_soil = data["soil"]
    st.session_state.val_cyanide = float(data["cyanide"])

if "val_lat" not in st.session_state:
    update_preset_values()

# ==========================================
# 5. القائمة الجانبية
# ==========================================
st.sidebar.header("📍 اختيار موقع التعدين")

selected_preset = st.sidebar.selectbox(
    "اختر منطقة التعدين للوصول السريع:", 
    list(preset_locations.keys()),
    key="selected_preset",
    on_change=update_preset_values
)

if selected_preset == "📍 إدخال موقع مخصص / إحداثيات":
    site_name = st.sidebar.text_input("اسم المنجم الجديد:", value="منجم جديد")
else:
    site_name = selected_preset

lat_input = st.sidebar.number_input("خط العرض (Latitude):", key="val_lat", format="%.4f")
lon_input = st.sidebar.number_input("خط الطول (Longitude):", key="val_lon", format="%.4f")

map_style = st.sidebar.selectbox(
    "نوع نمط الخريطة:",
    ["قمر صناعي (Satellite)", "خريطة شوارع (OpenStreetMap)"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ المعطيات الهيدروجيولوجية")

water_depth = st.sidebar.slider("عمق المياه الجوفية (متر):", min_value=2, max_value=150, key="val_depth")
river_dist = st.sidebar.slider("البعد عن المجرى المائي (متر):", min_value=20, max_value=5000, step=50, key="val_dist")
soil_type = st.sidebar.selectbox(
    "نوع التربة:",
    ["تربة صخرية صلبة (نفاذية منخفضة)", "تربة طمية مختلطة (نفاذية متوسطة)", "تربة رملية هشّة (نفاذية عالية)"],
    key="val_soil"
)
cyanide_conc = st.sidebar.slider("تركيز الملوثات (mg/L):", min_value=0.01, max_value=2.00, step=0.01, key="val_cyanide")

# ==========================================
# 6. الحسابات
# ==========================================
perm = 0.1 if "صخرية" in soil_type else (0.5 if "طمية" in soil_type else 0.95)
risk_score = (1800 / (river_dist + 1)) * (perm * 35) * (30 / water_depth) + (cyanide_conc * 20)
risk_score = min(max(round(risk_score, 1), 5.0), 98.5)
years = round((water_depth * (1.1 - perm)) / 1.3, 1)

# ==========================================
# 7. المؤشرات
# ==========================================
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="مؤشر الخطر البيئي", value=f"{risk_score}%")
with col2:
    status = "✅ آمن" if cyanide_conc <= 0.05 else "⚠️ يتجاوز الحد"
    st.metric(label="تركيز السيانيد", value=f"{cyanide_conc} mg/L", delta=status, delta_color="inverse" if cyanide_conc > 0.05 else "normal")
with col3:
    st.metric(label="زمن الوصول للمياه", value=f"{years} سنة")

st.markdown("---")

# ==========================================
# 8. الذكاء الاصطناعي
# ==========================================
st.subheader("🤖 التحليل البيئي بالذكاء الاصطناعي")

if st.button("✨ توليد تقرير بيئي سريع", type="primary", use_container_width=True):
    if "GEMINI_API_KEY" in st.secrets:
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"قم بتحليل موقع {site_name} بتركيز سيانيد {cyanide_conc} mg/L وخطر {risk_score}%. أعط توصيات موجزة."
            response = model.generate_content(prompt)
            st.info(response.text)
        except Exception as e:
            st.error(f"خطأ: {e}")
    else:
        st.warning("⚠️ يرجى إضافة GEMINI_API_KEY في Secrets.")

st.markdown("---")

# ==========================================
# 9. الخريطة الخفيفة والسريعة جداً
# ==========================================
st.subheader(f"🗺️ الخريطة: {site_name}")

if map_style == "قمر صناعي (Satellite)":
    m = folium.Map(location=[lat_input, lon_input], zoom_start=11, tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri')
else:
    m = folium.Map(location=[lat_input, lon_input], zoom_start=11)

# محرك بحث خفيف واستجابة سريعة عبر خدمة Esri
Geocoder(service="esri", collapsed=True, placeholder="ابحث عن مكان...").add_to(m)

marker_color = "red" if risk_score >= 70 else ("orange" if risk_score >= 40 else "green")

folium.Marker(
    location=[lat_input, lon_input],
    popup=f"{site_name} ({risk_score}%)",
    tooltip=site_name,
    icon=folium.Icon(color=marker_color, icon="info-sign")
).add_to(m)

st_folium(m, width="100%", height=400)
