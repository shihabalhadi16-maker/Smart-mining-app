import streamlit as st
import pandas as pd
import pydeck as pdk
import folium
from streamlit_folium import st_folium

# ==========================================
# 1. إعدادات الصفحة
# ==========================================
st.set_page_config(
    page_title="نظام التعدين الذكي 3D - جامعة الخرطوم",
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
# 3. الهيدر الرئيسي
# ==========================================
col_logo, col_title = st.columns([1, 5])

with col_logo:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png", width=105)

with col_title:
    st.title("⛏️ خريطة التعدين الواقعية ثلاثية الأبعاد (Real 3D Terrain)")
    st.caption("جامعة الخرطوم — كلية الهندسة — قسم هندسة التعدين | التجسيم الميداني للتضاريس والمخاطر البيئية")

st.markdown("---")

# ==========================================
# 4. قاعدة البيانات
# ==========================================
preset_locations = {
    "أبو حمد (نهر النيل)": {
        "coords": (19.5333, 33.3167), "depth": 15, "dist": 250, 
        "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.45
    },
    "عطبرة (نهر النيل)": {
        "coords": (17.6833, 33.9833), "depth": 8, "dist": 100, 
        "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.80
    },
    "بربر (نهر النيل)": {
        "coords": (18.0167, 33.9833), "depth": 12, "dist": 180, 
        "soil": "تربة طمية مختلطة (نفاذية متوسطة)", "cyanide": 0.30
    },
    "قبقبة / وادي العشاري": {
        "coords": (21.8000, 34.5000), "depth": 60, "dist": 2500, 
        "soil": "تربة صخرية صلبة (نفاذية منخفضة)", "cyanide": 0.10
    },
    "هيا (البحر الأحمر)": {
        "coords": (18.3333, 36.3500), "depth": 45, "dist": 1500, 
        "soil": "تربة صخرية صلبة (نفاذية منخفضة)", "cyanide": 0.05
    },
    "كادوقلي (جنوب كردفان)": {
        "coords": (11.0167, 29.7167), "depth": 20, "dist": 400, 
        "soil": "تربة طمية مختلطة (نفاذية متوسطة)", "cyanide": 0.20
    }
}

if "preset_choice" not in st.session_state:
    st.session_state.preset_choice = "عطبرة (نهر النيل)"

default_data = preset_locations[st.session_state.preset_choice]

if "lat_val" not in st.session_state:
    st.session_state.lat_val = float(default_data["coords"][0])
if "lon_val" not in st.session_state:
    st.session_state.lon_val = float(default_data["coords"][1])
if "depth_val" not in st.session_state:
    st.session_state.depth_val = int(default_data["depth"])
if "dist_val" not in st.session_state:
    st.session_state.dist_val = int(default_data["dist"])
if "soil_val" not in st.session_state:
    st.session_state.soil_val = default_data["soil"]
if "cyanide_val" not in st.session_state:
    st.session_state.cyanide_val = float(default_data["cyanide"])

def update_preset():
    choice = st.session_state.preset_choice
    data = preset_locations[choice]
    st.session_state.lat_val = float(data["coords"][0])
    st.session_state.lon_val = float(data["coords"][1])
    st.session_state.depth_val = int(data["depth"])
    st.session_state.dist_val = int(data["dist"])
    st.session_state.soil_val = data["soil"]
    st.session_state.cyanide_val = float(data["cyanide"])

# ==========================================
# 5. القائمة الجانبية (Sidebar)
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png", width=140)
st.sidebar.header("🔍 إدخال بيانات الموقع")

selected_preset = st.sidebar.selectbox(
    "اختر منطقة التعدين:", 
    list(preset_locations.keys()),
    key="preset_choice",
    on_change=update_preset
)

lat_input = st.sidebar.number_input("خط العرض (Latitude):", key="lat_val", format="%.4f")
lon_input = st.sidebar.number_input("خط الطول (Longitude):", key="lon_val", format="%.4f")

pitch_val = st.sidebar.slider("زاوية إمالة الخريطة 3D (Pitch):", min_value=0, max_value=85, value=65)
bearing_val = st.sidebar.slider("زاوية دوران الاتجاه (Bearing):", min_value=0, max_value=360, value=30)

st.sidebar.markdown("---")
st.sidebar.header("📊 المعطيات الجيولوجية")

soil_options = [
    "تربة صخرية صلبة (نفاذية منخفضة)", 
    "تربة طمية مختلطة (نفاذية متوسطة)", 
    "تربة رملية هشّة (نفاذية عالية)"
]

water_depth = st.sidebar.slider("عمق المياه الجوفية (متر):", min_value=2, max_value=150, key="depth_val")
river_dist = st.sidebar.slider("البعد عن أقرب مجرى مائي (متر):", min_value=20, max_value=5000, step=50, key="dist_val")
soil_type = st.sidebar.selectbox("نوع التربة:", soil_options, key="soil_val")
cyanide_conc = st.sidebar.slider("تركيز المواد الكيميائية (mg/L):", min_value=0.01, max_value=2.00, step=0.01, key="cyanide_val")

# ==========================================
# 6. الحسابات والنتائج
# ==========================================
perm = 0.1 if "صخرية" in soil_type else (0.5 if "طمية" in soil_type else 0.95)
risk_score = (1800 / (river_dist + 1)) * (perm * 35) * (30 / water_depth) + (cyanide_conc * 20)
risk_score = min(max(round(risk_score, 1), 5.0), 98.5)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="درجة الخطر التقديرية", value=f"{risk_score}%")
with col2:
    status = "✅ آمن" if cyanide_conc <= 0.05 else "⚠️ غير مطابق"
    st.metric(label="تركيز السيانيد", value=f"{cyanide_conc} mg/L", delta=status)
with col3:
    years = round((water_depth * (1.1 - perm)) / 1.3, 1)
    st.metric(label="زمن وصول التسرب", value=f"{years} سنة")

st.markdown("---")

# ==========================================
# 7. بناء الخريطة ثلاثية الأبعاد الفعلية (True 3D Map)
# ==========================================
st.subheader(f"🗺️ الخريطة التضاريسية ثلاثية الأبعاد: {selected_preset}")
st.info("👆 **طريقة التحكم:** استخدم زر الماوس الأيمن أو السحب باللمس بإصبعين على الشاشة لتعديل زاوية الرؤية ثلاثية الأبعاد، التدوير، والتكبير.")

# تحديد الألوان حسب نسبة الخطر
if risk_score >= 70:
    color_rgb = [230, 40, 40, 220]
elif risk_score >= 40:
    color_rgb = [240, 150, 20, 220]
else:
    color_rgb = [40, 180, 80, 220]

df_site = pd.DataFrame([{
    "name": selected_preset,
    "lat": lat_input,
    "lon": lon_input,
    "elevation": risk_score * 25,
    "radius": river_dist
}])

# طبقة مجسم الموقع الهندسي (3D Extruded Column)
column_layer = pdk.Layer(
    "ColumnLayer",
    data=df_site,
    get_position=["lon", "lat"],
    get_elevation="elevation",
    elevation_scale=4,
    radius=180,
    get_fill_color=color_rgb,
    pickable=True,
    extruded=True,
)

# طبقة الحرم المائي والنطاق التأثيري ثلاثي الأبعاد
scatterplot_layer = pdk.Layer(
    "ScatterplotLayer",
    data=df_site,
    get_position=["lon", "lat"],
    get_radius=river_dist,
    get_fill_color=[color_rgb[0], color_rgb[1], color_rgb[2], 60],
    get_line_color=color_rgb,
    line_width_min_pixels=2,
    pickable=True,
)

# إعدادات الكاميرا والتجسيم الثلاثي الأبعاد
view_state = pdk.ViewState(
    latitude=lat_input,
    longitude=lon_input,
    zoom=12,
    pitch=pitch_val,      # التحكم بإمالة الكاميرا للـ 3D
    bearing=bearing_val   # التحكم بتدوير الاتجاه
)

# عرض الخريطة ثلاثية الأبعاد
r = pdk.Deck(
    layers=[scatterplot_layer, column_layer],
    initial_view_state=view_state,
    map_style="pdk.map_styles.SATELLITE",
    tooltip={"html": "<b>الموقع:</b> {name}<br/><b>مستوى مجسم الخطر:</b> {elevation}m"}
)

st.pydeck_chart(r)
