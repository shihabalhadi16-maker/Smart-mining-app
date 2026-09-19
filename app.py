import streamlit as st
import pandas as pd
import pydeck as pdk
import folium
from streamlit_folium import st_folium

# ==========================================
# 1. إعدادات الصفحة والتصميم
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
        background-color: rgba(255, 255, 255, 0.75) !important;
        border-radius: 10px;
        padding: 8px;
        border: 1px solid #d4af37;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. الهيدر الرئيسي مع شعار الجامعة
# ==========================================
col_logo, col_title = st.columns([1, 5])

with col_logo:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png", width=105)

with col_title:
    st.title("⛏️ المنصة الذكية لتقييم المخاطر البيئية للتعدين")
    st.caption("جامعة الخرطوم — كلية الهندسة — قسم هندسة التعدين | نظام خرائط الأقمار الصناعية ثلاثية الأبعاد (3D High-Detail GIS)")

st.markdown("---")

# ==========================================
# 4. قاعدة البيانات وإدارة الجلسة
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
st.sidebar.header("🔍 اختيار وتحديد الموقع")

selected_preset = st.sidebar.selectbox(
    "اختر منطقة التعدين:", 
    list(preset_locations.keys()),
    key="preset_choice",
    on_change=update_preset
)

lat_input = st.sidebar.number_input("خط العرض (Latitude):", key="lat_val", format="%.4f")
lon_input = st.sidebar.number_input("خط الطول (Longitude):", key="lon_val", format="%.4f")

st.sidebar.markdown("---")
st.sidebar.header("🎮 التحكم بخصائص الرؤية 3D")
zoom_level = st.sidebar.slider("مستوى التقريب والتفاصيل (Zoom):", min_value=10, max_value=18, value=14)
pitch_val = st.sidebar.slider("زاوية الإمالة ثلاثية الأبعاد (Pitch):", min_value=0, max_value=85, value=60)
bearing_val = st.sidebar.slider("زاوية التدوير (Bearing):", min_value=0, max_value=360, value=30)

st.sidebar.markdown("---")
st.sidebar.header("📊 المعطيات الجيولوجية والهيدرولوجية")

soil_options = [
    "تربة صخرية صلبة (نفاذية منخفضة)", 
    "تربة طمية مختلطة (نفاذية متوسطة)", 
    "تربة رملية هشّة (نفاذية عالية)"
]

water_depth = st.sidebar.slider("عمق المياه الجوفية (متر):", min_value=2, max_value=150, key="depth_val")
river_dist = st.sidebar.slider("البعد عن أقرب مجرى مائي (متر):", min_value=20, max_value=5000, step=50, key="dist_val")
soil_type = st.sidebar.selectbox("نوع التربة الجيولوجية:", soil_options, key="soil_val")
cyanide_conc = st.sidebar.slider("تركيز المواد الكيميائية (mg/L):", min_value=0.01, max_value=2.00, step=0.01, key="cyanide_val")

# ==========================================
# 6. الخوارزمية وحساب النتائج
# ==========================================
perm = 0.1 if "صخرية" in soil_type else (0.5 if "طمية" in soil_type else 0.95)
risk_score = (1800 / (river_dist + 1)) * (perm * 35) * (30 / water_depth) + (cyanide_conc * 20)
risk_score = min(max(round(risk_score, 1), 5.0), 98.5)

# ==========================================
# 7. عرض المؤشرات والنتائج
# ==========================================
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="مؤشر الخطر التقديري", value=f"{risk_score}%")

with col2:
    status = "✅ ضمن الحدود الآمنة" if cyanide_conc <= 0.05 else "⚠️ يتجاوز معايير WHO"
    st.metric(label="تركيز الملوثات (السيانيد)", value=f"{cyanide_conc} mg/L", delta=status, delta_color="inverse" if cyanide_conc > 0.05 else "normal")

with col3:
    years = round((water_depth * (1.1 - perm)) / 1.3, 1)
    st.metric(label="الزمن المتوقع لتسرب المياه الجوفية", value=f"{years} سنة")

st.markdown("---")

# ==========================================
# 8. عرض الخرائط المدمجة
# ==========================================
st.subheader(f"🌐 المعاينة الجغرافية الفضائية: {selected_preset}")

# إعداد لون المؤشر حسب خطورة الموقع
if risk_score >= 70:
    color_rgb = [235, 40, 40, 230]
    marker_color = "red"
elif risk_score >= 40:
    color_rgb = [245, 160, 20, 230]
    marker_color = "orange"
else:
    color_rgb = [45, 190, 85, 230]
    marker_color = "green"

# تقسيم العرض إلى تبويبين (Tabs)
tab1, tab2 = st.tabs(["🛰️ خريطة 3D التفاعلية المجسمة", "🌍 خريطة الأقمار الصناعية عالية التفاصيل (Esri Satellite)"])

with tab1:
    st.info("💡 **نصيحة:** يمكنك التفاعل مع الخريطة ثلاثية الأبعاد باستخدام الماوس أو اللمس بـ 2 إصبع للإمالة والتدوير.")
    
    df_site = pd.DataFrame([{
        "name": selected_preset,
        "lat": lat_input,
        "lon": lon_input,
        "elevation": risk_score * 15,
        "radius": river_dist
    }])

    # طبقة التجسيم العمودي
    column_layer = pdk.Layer(
        "ColumnLayer",
        data=df_site,
        get_position=["lon", "lat"],
        get_elevation="elevation",
        elevation_scale=2,
        radius=100,
        get_fill_color=color_rgb,
        pickable=True,
        extruded=True,
    )

    # طبقة النطاق الجغرافي
    scatterplot_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_site,
        get_position=["lon", "lat"],
        get_radius=river_dist,
        get_fill_color=[color_rgb[0], color_rgb[1], color_rgb[2], 50],
        get_line_color=color_rgb,
        line_width_min_pixels=3,
        pickable=True,
    )

    view_state = pdk.ViewState(
        latitude=lat_input,
        longitude=lon_input,
        zoom=zoom_level,
        pitch=pitch_val,
        bearing=bearing_val
    )

    r = pdk.Deck(
        layers=[scatterplot_layer, column_layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/satellite-v9",
        tooltip={"html": "<b>الموقع:</b> {name}<br/><b>درجة تجسيم الخطر:</b> {elevation}m"}
    )

    st.pydeck_chart(r)

with tab2:
    # خريطة الأقمار الصناعية عالية التفاصيل والمستقرة من Esri
    m_sat = folium.Map(
        location=[lat_input, lon_input], 
        zoom_start=zoom_level,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery"
    )

    folium.Marker(
        location=[lat_input, lon_input],
        popup=f"<b>{selected_preset}</b><br>نسبة الخطر: {risk_score}%",
        tooltip=selected_preset,
        icon=folium.Icon(color=marker_color, icon="info-sign")
    ).add_to(m_sat)

    folium.Circle(
        location=[lat_input, lon_input],
        radius=river_dist,
        color=marker_color,
        fill=True,
        fill_opacity=0.25,
        popup="حرم الحماية المائية والبيئية"
    ).add_to(m_sat)

    st_folium(m_sat, width="100%", height=500)
