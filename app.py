import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import folium
from streamlit_folium import st_folium
from google import genai

# ==========================================
# 1. إعدادات الصفحة والتصميم
# ==========================================
st.set_page_config(
    page_title="نظام التعدين الذكي - دعم القرار بالذكاء الاصطناعي",
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
        background-color: #f4f6f9;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #0e3047 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 2px solid #d97736;
    }
    .ai-box {
        background-color: #ffffff;
        border-right: 5px solid #d97736;
        padding: 15px;
        border-radius: 8px;
        margin-top: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. الهيدر الرئيسي
# ==========================================
st.title("⛏️ المنصة الذكية لدعم القرار وتقييم مخاطر التعدين")
st.caption("جامعة الخرطوم — كلية الهندسة — قسم هندسة التعدين | مدعوم بنماذج الذكاء الاصطناعي")

st.markdown("---")

# ==========================================
# 4. المعاملات الجيولوجية والدالة
# ==========================================
SOIL_PROPERTIES = {
    "تربة صخرية نارية صلبة": {"K": 0.001, "n": 0.05},
    "تربة طمية رسوبية": {"K": 0.15, "n": 0.25},
    "تربة رملية حصوية": {"K": 5.0, "n": 0.35}
}

preset_locations = {
    "سوق طواحين أبو حمد (نهر النيل)": {
        "coords": (19.5333, 33.3167), "depth": 14.0, "dist": 300, 
        "soil": "تربة رملية حصوية", "cyanide": 0.85
    },
    "عطبرة - النيل الكبرى": {
        "coords": (17.6833, 33.9833), "depth": 8.5, "dist": 120, 
        "soil": "تربة رملية حصوية", "cyanide": 1.20
    },
    "مناجم أرياب (البحر الأحمر)": {
        "coords": (18.3333, 36.3500), "depth": 40.0, "dist": 1800, 
        "soil": "تربة صخرية نارية صلبة", "cyanide": 0.08
    }
}

if "preset_choice" not in st.session_state:
    st.session_state.preset_choice = "سوق طواحين أبو حمد (نهر النيل)"

default_data = preset_locations[st.session_state.preset_choice]

# ==========================================
# 5. القائمة الجانبية ومفتاح الذكاء الاصطناعي
# ==========================================
st.sidebar.header("📍 موقع التعدين")

selected_preset = st.sidebar.selectbox(
    "اختر الموقع الميداني:", 
    list(preset_locations.keys()),
    key="preset_choice"
)

lat_input = default_data["coords"][0]
lon_input = default_data["coords"][1]

st.sidebar.markdown("---")
st.sidebar.header("⚙️ المعاملات الفيزيائية")

soil_type = st.sidebar.selectbox("نوع التربة الجيولوجية:", list(SOIL_PROPERTIES.keys()))
water_depth = st.sidebar.slider("عمق المياه الجوفية (متر):", min_value=1.0, max_value=120.0, value=default_data["depth"])
river_dist = st.sidebar.slider("البعد عن المسطح المائي (متر):", min_value=10, max_value=5000, value=default_data["dist"])
cyanide_conc = st.sidebar.slider("تركيز الملوثات (mg/L):", min_value=0.01, max_value=3.00, value=default_data["cyanide"])

st.sidebar.markdown("---")
# 🔥 هذا هو الخيار الذي سيظهر لك في الجانب:
st.sidebar.header("🤖 إعدادات الذكاء الاصطناعي")
api_key_input = st.sidebar.text_input("مفتاح Gemini API Key:", type="password", help="ضع مفتاح API المنسوخ هنا")

# ==========================================
# 6. الحسابات الجيولوجية
# ==========================================
K_val = SOIL_PROPERTIES[soil_type]["K"]
n_val = SOIL_PROPERTIES[soil_type]["n"]

v_seepage_m_day = (K_val * 0.01) / n_val
vertical_years = round((water_depth / (v_seepage_m_day + 1e-6)) / 365.25, 2)

raw_risk = ((cyanide_conc / 0.05) * 25) + (((1000 - min(1000, river_dist)) / 1000) * 40)
risk_score = float(np.clip(round(raw_risk, 1), 2.0, 99.0))

# ==========================================
# 7. المؤشرات والنتائج
# ==========================================
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="مؤشر الخطر البيئي", value=f"{risk_score}%")
with col2:
    st.metric(label="تركيز السيانيد", value=f"{cyanide_conc} mg/L")
with col3:
    st.metric(label="زمن وصول التسرب للمياه", value=f"{vertical_years} سنة")

st.markdown("---")

# ==========================================
# 8. قسم العقل الاصطناعي (AI Assistant)
# ==========================================
st.subheader("🤖 المساعد الجيولوجي والرقابي الذكي")

generate_report = st.button("✨ توليد تقرير وتحليل بيئي بالذكاء الاصطناعي", use_container_width=True)

if generate_report:
    if not api_key_input:
        st.error("⚠️ يرجى إدخال مفتاح Gemini API Key في القائمة الجانبية أولاً.")
    else:
        with st.spinner("جاري تحليل البيانات عبر الذكاء الاصطناعي..."):
            try:
                client = genai.Client(api_key=api_key_input)
                prompt = f"قم بتحليل موقع تعدين في السودان ({selected_preset}) بتركيز سيانيد {cyanide_conc} mg/L ونسبة خطر {risk_score}%. اعط توصيات بيئية هامة."
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                
                st.markdown(f"""
                <div class="ai-box">
                    <h4>📋 التقرير البيئي الصادر عن الذكاء الاصطناعي:</h4>
                    <br>
                    {response.text}
                </div>
                """, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"حدث خطأ أثناء الاتصال: {e}")

st.markdown("---")

# ==========================================
# 9. عرض الخريطة
# ==========================================
st.subheader("🌐 الخريطة الجغرافية الميدانية")
m = folium.Map(location=[lat_input, lon_input], zoom_start=12)
folium.Marker([lat_input, lon_input], popup=selected_preset).add_to(m)
st_folium(m, width="100%", height=400)
