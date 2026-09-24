import math
import random
from datetime import datetime
import folium
from folium.plugins import HeatMap
import google.generativeai as genai
from geopy.geocoders import Nominatim
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# ==========================================
# 1. إعدادات الصفحة والتنسيق البصري الموحد
# ==========================================
st.set_page_config(
    page_title="Cyanide & Mining Risk Assessment System",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# التهيئة المباشرة لمفتاح Gemini API
API_KEY = st.secrets.get("GEMINI_API_KEY", None)
if API_KEY:
  genai.configure(api_key=API_KEY)

# تطبيق ثيم التصميم الأخضر العصري (Eco-Modern Theme)
st.markdown(
    """
<style>
    /* خلفية التطبيق العامة */
    .stApp {
        background: linear-gradient(180deg, #eaf4ed 0%, #f4f9f5 300px, #f8faf7 100%);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: #1e3a29;
    }
    
    /* الهيدر الرئيسي */
    .header-card {
        background-color: #ffffff;
        border-radius: 20px;
        padding: 18px 26px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
    }
    .header-title {
        font-size: 24px;
        font-weight: 800;
        color: #1b4332;
        margin: 0;
    }
    .header-subtitle {
        font-size: 14px;
        color: #2d6a4f;
        font-weight: 600;
        margin-top: 4px;
    }
    .status-badge {
        background-color: #d8f3dc;
        color: #1b4332;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        display: inline-block;
    }

    /* بطاقات القياس والمؤشرات */
    div[data-testid="stMetric"] {
        background: #ffffff !important;
        border: 1px solid #e8f0e9 !important;
        border-radius: 18px !important;
        padding: 16px 20px !important;
        box-shadow: 0 4px 12px rgba(45, 106, 79, 0.04) !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #52796f !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
    }
    div[data-testid="stMetricValue"] {
        color: #1b4332 !important;
        font-size: 1.8rem !important;
        font-weight: 800 !important;
    }

    /* كروت التنبيهات */
    .alert-card-warning {
        background-color: #fff8f0;
        border-right: 5px solid #f39c12;
        border-radius: 14px;
        padding: 14px 18px;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    .alert-card-success {
        background-color: #f4fbf7;
        border-right: 5px solid #2ea44f;
        border-radius: 14px;
        padding: 14px 18px;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }

    /* الشريط الجانبي */
    [data-testid="stSidebar"] {
        background-color: #1b4332 !important;
    }
    [data-testid="stSidebar"] * {
        color: #e8f0e9 !important;
    }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] select {
        color: #1b4332 !important;
        border-radius: 10px !important;
    }
    
    /* الأزرار الخضراء العصرية */
    .stButton>button {
        width: 100%;
        border-radius: 12px !important;
        font-weight: 700 !important;
        background: #2d6a4f !important;
        color: #ffffff !important;
        border: none !important;
        padding: 10px 18px !important;
        box-shadow: 0 4px 12px rgba(45, 106, 79, 0.2) !important;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background: #1b4332 !important;
        transform: translateY(-1px);
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)


# ==========================================
# 2. الدوال الحسابية المساعدة (UTM Conversion)
# ==========================================
def utm_to_latlon(easting, northing, zone=36, northern_hemisphere=True):
  a = 6378137.0
  f = 1 / 298.257223563
  k0 = 0.9996
  e = math.sqrt(2 * f - f**2)
  e1sq = e**2 / (1 - e**2)

  x = easting - 500000.0
  y = northing if northern_hemisphere else northing - 10000000.0

  long0 = (zone - 1) * 6 - 180 + 3

  M = y / k0
  mu = M / (a * (1 - (e**2) / 4 - 3 * (e**4) / 64 - 5 * (e**6) / 256))

  phi1 = (
      mu
      + (3 * e1sq / 2 - 27 * (e1sq**3) / 32) * math.sin(2 * mu)
      + (21 * (e1sq**2) / 16 - 55 * (e1sq**4) / 32) * math.sin(4 * mu)
  )

  N1 = a / math.sqrt(1 - (e * math.sin(phi1)) ** 2)
  T1 = math.tan(phi1) ** 2
  C1 = e1sq * math.cos(phi1) ** 2
  R1 = a * (1 - e**2) / ((1 - (e * math.sin(phi1)) ** 2) ** 1.5)
  D = x / (N1 * k0)

  lat = phi1 - (N1 * math.tan(phi1) / R1) * (
      D**2 / 2
      - (5 + 3 * T1 + 10 * C1 - 4 * C1**2 - 9 * e1sq) * (D**4) / 24
      + (61 + 90 * T1 + 298 * C1 + 45 * (T1**2) - 252 * e1sq - 3 * (C1**2))
      * (D**6)
      / 720
  )
  lat = math.degrees(lat)

  lon = (
      D
      - (1 + 2 * T1 + C1) * (D**3) / 6
      + (5 - 2 * C1 + 28 * T1 - 3 * (C1**2) + 8 * e1sq + 24 * (T1**2))
      * (D**5)
      / 120
  ) / math.cos(phi1)
  lon = long0 + math.degrees(lon)

  return lat, lon


# ==========================================
# 3. إدارة المواقع وقواعد البيانات المضمنة
# ==========================================
preset_locations = {
    "سوق طواحين أبو حمد (نهر النيل)": {
        "coords": (19.5333, 33.3167),
        "depth": 15,
        "soil": "تربة رملية هشّة (نفاذية عالية)",
        "cyanide": 0.45,
        "mercury": 0.08,
        "ph": 7.4,
    },
    "عطبرة - النيل الكبرى (نهر النيل)": {
        "coords": (17.6833, 33.9833),
        "depth": 8,
        "soil": "تربة رملية هشّة (نفاذية عالية)",
        "cyanide": 0.80,
        "mercury": 0.12,
        "ph": 7.2,
    },
    "سوق العبيدية (نهر النيل)": {
        "coords": (18.1234, 33.9876),
        "depth": 10,
        "soil": "تربة رملية هشّة (نفاذية عالية)",
        "cyanide": 0.65,
        "mercury": 0.09,
        "ph": 7.6,
    },
    "مناجم بربر (نهر النيل)": {
        "coords": (18.0167, 33.9833),
        "depth": 12,
        "soil": "تربة طمية مختلطة (نفاذية متوسطة)",
        "cyanide": 0.30,
        "mercury": 0.04,
        "ph": 7.8,
    },
    "وادي العشاري / قبقبة (الشمالية)": {
        "coords": (21.8000, 34.5000),
        "depth": 60,
        "soil": "تربة صخرية صلبة (نفاذية منخفضة)",
        "cyanide": 0.10,
        "mercury": 0.02,
        "ph": 8.0,
    },
    "وادي حلفا - كرمة (الشمالية)": {
        "coords": (21.7950, 31.3700),
        "depth": 25,
        "soil": "تربة رملية هشّة (نفاذية عالية)",
        "cyanide": 0.50,
        "mercury": 0.06,
        "ph": 7.5,
    },
    "مناجم أرياب (البحر الأحمر)": {
        "coords": (18.3333, 36.3500),
        "depth": 45,
        "soil": "تربة صخرية صلبة (نفاذية منخفضة)",
        "cyanide": 0.05,
        "mercury": 0.01,
        "ph": 8.1,
    },
    "سوق دلقو (الشمالية)": {
        "coords": (20.3000, 30.5500),
        "depth": 35,
        "soil": "تربة صخرية صلبة (نفاذية منخفضة)",
        "cyanide": 0.15,
        "mercury": 0.03,
        "ph": 7.9,
    },
    "تلودي / الليري (جبال النوبة)": {
        "coords": (10.6333, 30.1167),
        "depth": 18,
        "soil": "تربة طمية مختلطة (نفاذية متوسطة)",
        "cyanide": 0.70,
        "mercury": 0.15,
        "ph": 6.8,
    },
    "كادوقلي (جنوب كردفان)": {
        "coords": (11.0167, 29.7167),
        "depth": 20,
        "soil": "تربة طمية مختلطة (نفاذية متوسطة)",
        "cyanide": 0.20,
        "mercury": 0.05,
        "ph": 7.1,
    },
}

if "selected_site_name" not in st.session_state:
  st.session_state.selected_site_name = "سوق طواحين أبو حمد (نهر النيل)"
if "lat" not in st.session_state:
  st.session_state.lat = 19.5333
if "lon" not in st.session_state:
  st.session_state.lon = 33.3167


def on_preset_change():
  site = st.session_state.preset_select
  if site in preset_locations:
    st.session_state.selected_site_name = site
    st.session_state.lat = preset_locations[site]["coords"][0]
    st.session_state.lon = preset_locations[site]["coords"][1]


# ==========================================
# 4. الشريط الجانبي (Sidebar Setup)
# ==========================================
st.sidebar.image(
    "https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png",
    width=110,
)
st.sidebar.markdown("### ⛏️ جامعة الخرطوم\n**قسم هندسة التعدين**")

st.sidebar.markdown("---")
st.sidebar.header("🌍 البحث والتحويل الإحداثي")

coord_mode = st.sidebar.radio(
    "نظام التحديد:",
    ["اسم المنطقة / Lat-Lon", "إحداثيات متريّة (UTM Zone 36N/37N)"],
)

if coord_mode == "اسم المنطقة / Lat-Lon":
  st.sidebar.selectbox(
      "مواقع مسجلة جاهزة:",
      list(preset_locations.keys()),
      key="preset_select",
      on_change=on_preset_change,
  )
  custom_search = st.sidebar.text_input(
      "أو ابحث عن موقع:", placeholder="مثال: Port Sudan أو العبيدية"
  )
  if st.sidebar.button("بحث 🧭"):
    q = custom_search.strip()
    if q:
      geolocator = Nominatim(
          user_agent=f"uofk_mining_app_{random.randint(1000, 9999)}"
      )
      try:
        loc = geolocator.geocode(
            f"{q}, Sudan", timeout=8
        ) or geolocator.geocode(q, timeout=8)
        if loc:
          st.session_state.lat = loc.latitude
          st.session_state.lon = loc.longitude
          st.session_state.selected_site_name = q
          st.sidebar.success(f"📍 {loc.address[:30]}...")
          st.rerun()
        else:
          st.sidebar.error("❌ لم يتم العثور على الموقع")
      except Exception:
        st.sidebar.error("تعذر الاتصال بخدمة الخرائط")
else:
  utm_easting = st.sidebar.number_input("Easting (X - متر):", value=533200.0)
  utm_northing = st.sidebar.number_input("Northing (Y - متر):", value=2159800.0)
  utm_zone = st.sidebar.selectbox("النطاق (UTM Zone):", [36, 37], index=0)
  if st.sidebar.button("تحويل الإحداثيات 🔄"):
    try:
      lat_v, lon_v = utm_to_latlon(utm_easting, utm_northing, zone=utm_zone)
      st.session_state.lat = lat_v
      st.session_state.lon = lon_v
      st.session_state.selected_site_name = (
          f"UTM ({utm_easting}, {utm_northing})"
      )
      st.rerun()
    except Exception as e:
      st.sidebar.error(f"خطأ في التحويل: {e}")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ المعطيات الميدانية")
depth = st.sidebar.slider("عمق المياه الجوفية (متر):", 2, 120, 15)
river_dist = st.sidebar.slider(
    "البعد عن أقرب مجرى مائي (متر):", 50, 5000, 300, step=50
)
soil = st.sidebar.selectbox(
    "نوع التربة السطحية:",
    [
        "تربة رملية هشّة (نفاذية عالية)",
        "تربة طمية مختلطة (نفاذية متوسطة)",
        "تربة صخرية صلبة (نفاذية منخفضة)",
    ],
)

col_sb1, col_sb2 = st.sidebar.columns(2)
with col_sb1:
  cyanide = st.number_input(
      "السيانيد (mg/L):",
      min_value=0.01,
      max_value=5.00,
      value=0.45,
      step=0.05,
  )
with col_sb2:
  mercury = st.number_input(
      "الزئبق (mg/L):",
      min_value=0.000,
      max_value=1.000,
      value=0.080,
      step=0.005,
  )

ph_level = st.sidebar.slider("مستوى الحموضة (pH Level):", 1.0, 14.0, 7.4, 0.1)

# الحسابات الهيدروجيولوجية (DRASTIC Model)
perm = 0.95 if "رملية" in soil else (0.50 if "طمية" in soil else 0.10)
soil_rating = 9 if "رملية" in soil else (6 if "طمية" in soil else 2)
d_rating = 10 if depth < 5 else (8 if depth < 15 else (5 if depth < 30 else 2))
dist_rating = 10 if river_dist < 200 else (6 if river_dist < 1000 else 2)

drastic_score = (
    (d_rating * 5)
    + (soil_rating * 3)
    + (dist_rating * 4)
    + (cyanide * 10)
    + (mercury * 20)
)
risk_score = round(min(max((drastic_score / 130.0) * 100, 5.0), 98.5), 1)
years = round((depth * (1.1 - perm)) / 1.3, 1)

risk_status = "LOW" if risk_score < 40 else ("MEDIUM" if risk_score < 70 else "HIGH")
badge_color = (
    "#d8f3dc"
    if risk_status == "LOW"
    else ("#ffe8d6" if risk_status == "MEDIUM" else "#ffccd5")
)
badge_text_color = (
    "#1b4332"
    if risk_status == "LOW"
    else ("#a71e1c" if risk_status == "HIGH" else "#9c6644")
)
current_time = datetime.now().strftime("%b %d, %Y • %I:%M %p")

# ==========================================
# 5. الهيدر العريض العلوي (Top Header)
# ==========================================
st.markdown(
    f"""
<div class="header-card">
    <div>
        <div class="header-title">🌿 Cyanide & Environmental Risk Assessment</div>
        <div class="header-subtitle">جامعة الخرطوم — كلية الهندسة وقسم هندسة التعدين</div>
        <div style="font-size: 12px; color: #52796f; margin-top: 4px;">الموقع: <b>{st.session_state.selected_site_name}</b> | {current_time}</div>
    </div>
    <div>
        <span class="status-badge" style="background-color: {badge_color}; color: {badge_text_color};">
            ● Overall Risk • {risk_status} ({risk_score}%)
        </span>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 6. التبويبات الرئيسية (Tabs)
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "📊 لوحة المراقبة والتقرير الذكي (Dashboard & AI)",
    "📤 التقييم الجماعي والخرائط الحرارية (Bulk Upload)",
    "🛡️ محاكاة الحلول الهندسية (Mitigation Simulation)",
])

# ==========================================
# TAB 1: Dashboard & AI Report
# ==========================================
with tab1:
  # بطاقات المؤشرات المباشرة
  k1, k2, k3, k4 = st.columns(4)
  with k1:
    st.metric(
        "🧪 Cyanide Concentration",
        f"{cyanide} mg/L",
        delta="Safe Limit: 0.20 mg/L",
        delta_color="normal" if cyanide <= 0.20 else "inverse",
    )
  with k2:
    st.metric(
        "💧 pH Level",
        f"{ph_level}",
        delta="Optimal: 6.5 - 8.5",
        delta_color="normal" if 6.5 <= ph_level <= 8.5 else "inverse",
    )
  with k3:
    st.metric(
        "⚗️ Mercury (Hg)",
        f"{mercury} mg/L",
        delta="Safe Limit: 0.006 mg/L",
        delta_color="normal" if mercury <= 0.006 else "inverse",
    )
  with k4:
    st.metric(
        "⏳ زمن الوصول للجوف", f"{years} سنة", delta=f"العمق: {depth}m"
    )

  st.markdown("<br>", unsafe_allow_html=True)

  # خريطة الأقمار الصناعية
  st.markdown("### 🗺️ Water Contamination & Impact Map")
  m = folium.Map(
      location=[st.session_state.lat, st.session_state.lon],
      zoom_start=12,
      tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      attr="Esri World Imagery",
  )
  folium.TileLayer(
      tiles="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png",
      attr="CartoDB",
      name="أسماء المناطق والطرق",
      overlay=True,
  ).add_to(m)

  marker_color = (
      "green" if risk_score < 40 else ("orange" if risk_score < 70 else "red")
  )

  folium.Marker(
      [st.session_state.lat, st.session_state.lon],
      popup=(
          f"<b>الموقع:</b> {st.session_state.selected_site_name}<br><b>درجة"
          f" الخطر:</b> {risk_score}%"
      ),
      tooltip=st.session_state.selected_site_name,
      icon=folium.Icon(color=marker_color, icon="leaf", prefix="fa"),
  ).add_to(m)

  folium.Circle(
      [st.session_state.lat, st.session_state.lon],
      radius=river_dist,
      color="#2d6a4f" if risk_score < 40 else "#e67e22",
      fill=True,
      fill_opacity=0.20,
  ).add_to(m)

  st_folium(m, width="100%", height=380, key="main_map")

  st.markdown("<br>", unsafe_allow_html=True)

  # تنبيهات السلامة والتقرير
  st.markdown("### 🚨 Safety Alerts & Advisory Report")

  if cyanide > 0.20 or mercury > 0.006:
    st.markdown(
        """
        <div class="alert-card-warning">
            <div class="alert-title">⚠️ Warning: Contaminant Limits Exceeded</div>
            <div class="alert-desc">مستويات السيانيد أو الزئبق تتجاوز الحدود الآمنة المعتمدة. يُوصى بفحص أغطية وأحواض المعالجة بشكل عاجل.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
  else:
    st.markdown(
        """
        <div class="alert-card-success">
            <div class="alert-title">✅ All Parameters Within Safe Limits</div>
            <div class="alert-desc">جميع المؤشرات تقيم ضمن الحدود المسموح بها بيئياً للظروف الميدانية الحالية.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

  if st.button(
      "📄 توليد تقرير استشاري فني فوري (AI Report)", type="primary"
  ):
    report_container = st.empty()

    prompt = f"""
        أنت استشاري بيئي بهيئة الأبحاث الجيولوجية وجامعة الخرطوم. صغ تقريراً فنياً لموقع {st.session_state.selected_site_name}:
        المعطيات الميدانية:
        - عمق المياه: {depth} متر
        - نوع التربة: {soil}
        - البعد عن المجرى المائي: {river_dist} متر
        - تركيز السيانيد: {cyanide} mg/L (الحد المسموح 0.20)
        - تركيز الزئبق: {mercury} mg/L (الحد المسموح 0.006)
        - مستوى الحموضة pH: {ph_level}
        - مؤشر DRASTIC للخطورة: {risk_score}%
        
        قم بكتابة التقرير في 3 محاور محددة:
        1. **التقييم الجيوهيدرولوجي والمخاطر.**
        2. **الأثر البيئي والصحي المباشر.**
        3. **التوصيات الهندسية الميدانية العاجلة.**
        """

    ai_generated = False
    if API_KEY:
      for model_name in [
          "gemini-1.5-flash",
          "gemini-1.5-pro",
          "gemini-2.0-flash",
      ]:
        if ai_generated:
          break
        try:
          model = genai.GenerativeModel(model_name)
          response = model.generate_content(prompt, stream=True)
          full_text = ""
          for chunk in response:
            full_text += chunk.text
            report_container.markdown(f"{full_text}▌")
          report_container.markdown(f"{full_text}")
          ai_generated = True
        except Exception:
          continue

    if not ai_generated:
      c_eval = (
          "يتجاوز المعايير العالمية بشكل حاد (حد USEPA هو 0.20 mg/L)"
          if cyanide > 0.20
          else "ضمن الحدود المسموح بها"
      )
      m_eval = (
          "شديد الخطورة ويشكل تهديداً بيئياً وجوفياً"
          if mercury > 0.006
          else "ضمن الحدود المقبولة"
      )

      fallback_text = f"""
### 📄 تقرير التقييم الفني الميداني (جامعة الخرطوم - قسم التعدين)
**الموقع:** {st.session_state.selected_site_name} | **درجة الخطر:** {risk_score}%

---

#### 1. **التقييم الجيوهيدرولوجي والمخاطر:**
- تقييم نموذج DRASTIC يشير إلى خطر بدرجة **({risk_status})**.
- زمن الوصول المتوقع للملوثات إلى المياه الجوفية بعمق **{depth} متر** هو **{years} سنة**.

#### 2. **الأثر البيئي والصحي المباشر:**
- **السيانيد:** `{cyanide} mg/L` — {c_eval}.
- **الزئبق:** `{mercury} mg/L` — {m_eval}.
- **مستوى الحموضة (pH):** `{ph_level}`.
- قرب الموقع (**{river_dist} متر**) من المجاري المائية يتطلب احتياطات عزل إضافية.

#### 3. **التوصيات الهندسية الميدانية العاجلة:**
- الإلزام الفوري بتركيب بطانات عازلة من نوع **(HDPE Liner)** بتركيب عالي الكثافة.
- حفر آبار مراقبة اختبارية لمتابعة حركة المياه الجوفية وتدفق الملوثات.
"""
      report_container.markdown(fallback_text)

# ==========================================
# TAB 2: Bulk Upload & HeatMap
# ==========================================
with tab2:
  st.markdown("### 📤 رفع البيانات الجماعية والخرائط الحرارية")
  uploaded_file = st.file_uploader(
      "اختر ملف CSV أو Excel يحتوي على الإحداثيات والملوثات:",
      type=["xlsx", "csv"],
  )

  if uploaded_file is not None:
    try:
      df_bulk = (
          pd.read_csv(uploaded_file)
          if uploaded_file.name.endswith(".csv")
          else pd.read_excel(uploaded_file)
      )
      st.success(f"تم تحميل {len(df_bulk)} موقع بنجاح.")

      c_tbl, c_heat = st.columns([1, 1])
      with c_tbl:
        st.dataframe(df_bulk, use_container_width=True)
      with c_heat:
        if "Latitude" in df_bulk.columns and "Longitude" in df_bulk.columns:
          map_center = [
              df_bulk["Latitude"].mean(),
              df_bulk["Longitude"].mean(),
          ]
          m_heat = folium.Map(
              location=map_center,
              zoom_start=6,
              tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
              attr="Esri",
          )

          heat_val = (
              "Cyanide"
              if "Cyanide" in df_bulk.columns
              else df_bulk.columns[2]
          )
          heat_data = [
              [row["Latitude"], row["Longitude"], row[heat_val]]
              for index, row in df_bulk.iterrows()
          ]
          HeatMap(heat_data, radius=15).add_to(m_heat)
          st_folium(m_heat, width="100%", height=380, key="bulk_heat_map")
        else:
          st.error(
              "الملف يحتاج إلى ألوح تحوي أعمدة 'Latitude' و 'Longitude'"
          )
    except Exception as e:
      st.error(f"حدث خطأ أثناء قراءة الملف: {e}")

# ==========================================
# TAB 3: Mitigation Simulation
# ==========================================
with tab3:
  st.markdown("### 🛡️ محاكاة تأثير التدابير الهندسية والوقائية")
  col_sc1, col_sc2 = st.columns(2)

  with col_sc1:
    st.subheader("الوضع الحالي (بدون تدابير)")
    st.error(f"مؤشر الخطر الحقيقي: {risk_score}%")
    st.warning(f"زمن وصول الملوث للجوف: {years} سنة")

  with col_sc2:
    st.subheader("الوضع المتوقع بعد التطبيق")
    liner = st.checkbox(
        "تركيب بطانة عازلة مزدوجة عالية الكثافة (HDPE Liner)"
    )
    treatment = st.checkbox(
        "تطبيق وحدة معالجة وتفكيك السيانيد بالكيميائيات (Cyanide Destruction)"
    )
    mercury_stop = st.checkbox(
        "استبدال الزئبق بتقنيات إعادة التدوير والخضخضة العازلة"
    )

    mitigated_score = risk_score
    if liner:
      mitigated_score *= 0.35
    if treatment:
      mitigated_score *= 0.50
    if mercury_stop:
      mitigated_score *= 0.70

    mitigated_score = round(mitigated_score, 1)
    st.success(f"مؤشر الخطر المحاكى: {mitigated_score}%")

    reduction = (
        round(((risk_score - mitigated_score) / risk_score) * 100, 1)
        if risk_score > 0
        else 0
    )
    st.metric("نسبة الانخفاض الإجمالية في مخاطر التلوث", f"{reduction}%")
