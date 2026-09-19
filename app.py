import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import folium
from streamlit_folium import st_folium

# ==========================================
# 1. إعدادات الصفحة والتصميم
# ==========================================
st.set_page_config(
    page_title="نظام التعدين الذكي - نموذج هيدرولوجي دقيق",
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
        background-color: rgba(255, 255, 255, 0.80) !important;
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
    st.title("⛏️ النموذج الهيدروليكي الدقيق لتقييم مخاطر التعدين")
    st.caption("جامعة الخرطوم — كلية الهندسة — قسم هندسة التعدين | حسابات مائية بناءً على قانون دارسي (Darcy's Law)")

st.markdown("---")

# ==========================================
# 4. قاعدة البيانات والمعاملات الجيولوجية الدقيقة
# ==========================================
# K: Hydraulic Conductivity (m/day), n: Effective Porosity
SOIL_PROPERTIES = {
    "تربة صخرية نارية صلبة (أنفيلتريشن ضعيف)": {"K": 0.001, "n": 0.05, "desc": "نفاذية ضئيلة جداً"},
    "تربة طمية رسوبية (مختلطة)": {"K": 0.15, "n": 0.25, "desc": "نفاذية متوسطة"},
    "تربة رملية حصوية (عالية النفاذية)": {"K": 5.0, "n": 0.35, "desc": "نفاذية عالية وسريعة"}
}

preset_locations = {
    "سوق طواحين أبو حمد (نهر النيل)": {
        "coords": (19.5333, 33.3167), "depth": 14.0, "dist": 300, 
        "soil": "تربة رملية حصوية (عالية النفاذية)", "cyanide": 0.85
    },
    "عطبرة - النيل الكبرى": {
        "coords": (17.6833, 33.9833), "depth": 8.5, "dist": 120, 
        "soil": "تربة رملية حصوية (عالية النفاذية)", "cyanide": 1.20
    },
    "بربر - منطقة العبيدية": {
        "coords": (18.0167, 33.9833), "depth": 11.0, "dist": 250, 
        "soil": "تربة طمية رسوبية (مختلطة)", "cyanide": 0.45
    },
    "وادي العشاري / قبقبة": {
        "coords": (21.8000, 34.5000), "depth": 55.0, "dist": 2200, 
        "soil": "تربة صخرية نارية صلبة (أنفيلتريشن ضعيف)", "cyanide": 0.15
    },
    "مناجم أرياب (البحر الأحمر)": {
        "coords": (18.3333, 36.3500), "depth": 40.0, "dist": 1800, 
        "soil": "تربة صخرية نارية صلبة (أنفيلتريشن ضعيف)", "cyanide": 0.08
    }
}

if "preset_choice" not in st.session_state:
    st.session_state.preset_choice = "سوق طواحين أبو حمد (نهر النيل)"

default_data = preset_locations[st.session_state.preset_choice]

if "lat_val" not in st.session_state:
    st.session_state.lat_val = float(default_data["coords"][0])
if "lon_val" not in st.session_state:
    st.session_state.lon_val = float(default_data["coords"][1])
if "depth_val" not in st.session_state:
    st.session_state.depth_val = float(default_data["depth"])
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
    st.session_state.depth_val = float(data["depth"])
    st.session_state.dist_val = int(data["dist"])
    st.session_state.soil_val = data["soil"]
    st.session_state.cyanide_val = float(data["cyanide"])

# ==========================================
# 5. القائمة الجانبية (إدخال المتغيرات الفيزيائية)
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png", width=130)
st.sidebar.header("📍 اختيار موقع التعدين")

selected_preset = st.sidebar.selectbox(
    "الموقع الميداني المحدد:", 
    list(preset_locations.keys()),
    key="preset_choice",
    on_change=update_preset
)

lat_input = st.sidebar.number_input("خط العرض (Lat):", key="lat_val", format="%.4f")
lon_input = st.sidebar.number_input("خط الطول (Lon):", key="lon_val", format="%.4f")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ المعاملات الهيدروجيولوجية")

soil_type = st.sidebar.selectbox("نوع الطبقة الجيولوجية للتربة:", list(SOIL_PROPERTIES.keys()), key="soil_val")
water_depth = st.sidebar.slider("عمق المياه الجوفية (متر):", min_value=1.0, max_value=120.0, step=0.5, key="depth_val")
river_dist = st.sidebar.slider("البعد عن المسطح المائي/النيل (متر):", min_value=10, max_value=5000, step=25, key="dist_val")
cyanide_conc = st.sidebar.slider("تركيز الملوثات الكيميائية (mg/L):", min_value=0.01, max_value=3.00, step=0.02, key="cyanide_val")
grad_i = st.sidebar.slider("الانحدار الهيدروليكي (Hydraulic Gradient i):", min_value=0.001, max_value=0.050, value=0.010, step=0.001)

st.sidebar.markdown("---")
st.sidebar.header("🎮 الرؤية الفضائية 3D")
zoom_level = st.sidebar.slider("مستوى التقريب (Zoom):", min_value=10, max_value=18, value=14)
pitch_val = st.sidebar.slider("الإمالة (Pitch):", min_value=0, max_value=85, value=60)

# ==========================================
# 6. الحسابات الفيزياء والهيدرولوجية الدقيقة
# ==========================================
# استخراج K و n للتربة المختارة
K_val = SOIL_PROPERTIES[soil_type]["K"] # m/day
n_val = SOIL_PROPERTIES[soil_type]["n"] # porosity

# حساب سرعة تسرب التسرب بالتوافق مع قانون دارسي Darcy's Seepage Velocity v = (K * i) / n
v_seepage_m_day = (K_val * grad_i) / n_val # m/day

# الزمن اللازم لوصول الملوث للماء الجوفي عمودياً (بالأيام ثم بالسنوات)
vertical_days = water_depth / (v_seepage_m_day + 1e-6)
vertical_years = round(vertical_days / 365.25, 2)

# حساب مؤشر الخطورة الدقيق (Risk Index) بناءً على النفاذية والتركيز والمسافة
# المعيار العالمي المسموح لـ WHO هو 0.05 mg/L
concentration_factor = cyanide_conc / 0.05
distance_factor = max(0.1, (1000 - river_dist) / 1000) if river_dist < 1000 else 0.05
depth_factor = max(0.1, (50 - water_depth) / 50) if water_depth < 50 else 0.05

raw_risk = (concentration_factor * 25) + (distance_factor * 40) + (depth_factor * 35) + (K_val * 5)
risk_score = float(np.clip(round(raw_risk, 1), 2.0, 99.0))

# ==========================================
# 7. عرض المؤشرات والتحليلات الأكاديمية
# ==========================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="مؤشر الخطر المائي البيئي", value=f"{risk_score}%")

with col2:
    status = "✅ مطابق لـ WHO" if cyanide_conc <= 0.05 else "⚠️ يتجاوز الحد المسموح"
    st.metric(label="تركيز السيانيد الحسابي", value=f"{cyanide_conc} mg/L", delta=status, delta_color="inverse" if cyanide_conc > 0.05 else "normal")

with col3:
    st.metric(label="زمن وصول التسرب للمياه", value=f"{vertical_years} سنة")

with col4:
    st.metric(label="سرعة التدفق الجوفي (Darcy)", value=f"{round(v_seepage_m_day*1000, 2)} mm/day")

st.markdown("---")

# ==========================================
# 8. عرض الخرائط التفاعلية
# ==========================================
st.subheader(f"🌐 المحاكاة الجغرافية الفضائية: {selected_preset}")

if risk_score >= 70:
    color_rgb = [235, 40, 40, 230]
    marker_color = "red"
elif risk_score >= 40:
    color_rgb = [245, 160, 20, 230]
    marker_color = "orange"
else:
    color_rgb = [45, 190, 85, 230]
    marker_color = "green"

tab1, tab2 = st.tabs(["🛰️ الخريطة ثلاثية الأبعاد (3D Darcy Plume)", "🌍 الأقمار الصناعية عالي الدقة (Esri Imagery)"])

with tab1:
    df_site = pd.DataFrame([{
        "name": selected_preset,
        "lat": lat_input,
        "lon": lon_input,
        "elevation": risk_score * 12,
        "radius": river_dist
    }])

    column_layer = pdk.Layer(
        "ColumnLayer",
        data=df_site,
        get_position=["lon", "lat"],
        get_elevation="elevation",
        elevation_scale=2,
        radius=80,
        get_fill_color=color_rgb,
        pickable=True,
        extruded=True,
    )

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
        bearing=30
    )

    r = pdk.Deck(
        layers=[scatterplot_layer, column_layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/satellite-v9",
        tooltip={"html": "<b>الموقع:</b> {name}<br/><b>ارتفاع العمود يمثل شدة الخطر:</b> {elevation}m"}
    )

    st.pydeck_chart(r)

with tab2:
    m_sat = folium.Map(
        location=[lat_input, lon_input], 
        zoom_start=zoom_level,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery"
    )

    folium.Marker(
        location=[lat_input, lon_input],
        popup=f"<b>{selected_preset}</b><br>نسبة الخطر: {risk_score}%<br>سرعة التسرب: {round(v_seepage_m_day, 4)} m/day",
        tooltip=selected_preset,
        icon=folium.Icon(color=marker_color, icon="info-sign")
    ).add_to(m_sat)

    folium.Circle(
        location=[lat_input, lon_input],
        radius=river_dist,
        color=marker_color,
        fill=True,
        fill_opacity=0.25,
        popup="نطاق التأثير المباشر للمسطحات المائية"
    ).add_to(m_sat)

    st_folium(m_sat, width="100%", height=500)
