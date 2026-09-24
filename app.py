import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import google.generativeai as genai
import os

# ==========================================
# 1. إعدادات الصفحة
# ==========================================
st.set_page_config(
    page_title="نظام التعدين الذكي",
    page_icon="⛏️",
    layout="wide"
)

# ==========================================
# 2. التنسيق والتبسيط البصري (CSS)
# ==========================================
st.markdown("""
<style>
.stApp {
    background-color: #fdfbf7;
}
.stMetric {
    background-color: #ffffff !important;
    border-radius: 10px;
    padding: 12px;
    border: 1px solid #e0e0e0;
    box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
}
.stButton>button {
    width: 100%;
    border-radius: 8px;
    font-weight: bold;
    background-color: #d97706;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. الهيدر الرئيسي
# ==========================================
st.title("⛏️ نظام التعدين الذكي وتقييم المخاطر")
st.caption("جامعة الخرطوم | قسم هندسة التعدين")

# ==========================================
# 4. إدارة البيانات والمدخلات
# ==========================================
preset_locations = {
    "أبو حمد (نهر النيل)": {"coords": (19.5333, 33.3167), "depth": 15, "dist": 250, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.45},
    "عطبرة (نهر النيل)": {"coords": (17.6833, 33.9833), "depth": 8, "dist": 100, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.80},
    "بربر (نهر النيل)": {"coords": (18.0167, 33.9833), "depth": 12, "dist": 180, "soil": "تربة طمية مختلطة (نفاذية متوسطة)", "cyanide": 0.30},
    "قبقبة / وادي العشاري": {"coords": (21.8000, 34.5000), "depth": 60, "dist": 2500, "soil": "تربة صخرية صلبة (نفاذية منخفضة)", "cyanide": 0.10},
    "كادوقلي (جنوب كردفان)": {"coords": (11.0167, 29.7167), "depth": 20, "dist": 400, "soil": "تربة طمية مختلطة (نفاذية متوسطة)", "cyanide": 0.20}
}

# الشريط الجانبي مبسط
st.sidebar.header("📍 اختيار الموقع")
selected_preset = st.sidebar.selectbox("اختر المنجم/المنطقة:", list(preset_locations.keys()))
site_data = preset_locations[selected_preset]

# تعديل المدخلات لو أراد المستخدم
st.sidebar.markdown("---")
st.sidebar.header("⚙️ تعديل المعطيات")
water_depth = st.sidebar.slider("عمق المياه الجوفية (متر):", 2, 150, int(site_data["depth"]))
river_dist = st.sidebar.slider("البعد عن أقرب وادي/مجرى (متر):", 20, 5000, int(site_data["dist"]), step=50)
cyanide_conc = st.sidebar.slider("تركيز السيانيد (mg/L):", 0.01, 2.00, float(site_data["cyanide"]), step=0.01)

# ==========================================
# 5. الحسابات الفورية
# ==========================================
perm = 0.95 if "رملية" in site_data["soil"] else (0.5 if "طمية" in site_data["soil"] else 0.1)
risk_score = min(max(round((1800 / (river_dist + 1)) * (perm * 35) * (30 / water_depth) + (cyanide_conc * 20), 1), 5.0), 98.5)
years = round((water_depth * (1.1 - perm)) / 1.3, 1)

# ==========================================
# 6. تقسيم الواجهة إلى تبويبات (Tabs)
# ==========================================
tab1, tab2, tab3 = st.tabs(["📍 الخريطة والبيانات", "📊 التقييم الهندي", "🤖 التقرير الذكي السريع"])

with tab1:
    col_map1, col_map2 = st.columns([1, 2])
    with col_map1:
        st.subheader("بيانات موقع المنجم")
        st.write(f"**المنطقة:** {selected_preset}")
        st.write(f"**نوع التربة:** {site_data['soil']}")
        st.write(f"**عمق المياه:** {water_depth} متر")
        st.write(f"**المسافة للوادي:** {river_dist} متر")
    
    with col_map2:
        m = folium.Map(location=site_data["coords"], zoom_start=11)
        marker_color = "red" if risk_score >= 70 else ("orange" if risk_score >= 40 else "green")
        folium.Marker(location=site_data["coords"], popup=selected_preset, icon=folium.Icon(color=marker_color)).add_to(m)
        st_folium(m, width="100%", height=300)

with tab2:
    st.subheader("مؤشرات الخطر البيئي")
    c1, c2, c3 = st.columns(3)
    c1.metric("درجة الخطر التقديرية", f"{risk_score}%")
    c2.metric("تركيز السيانيد", f"{cyanide_conc} mg/L")
    c3.metric("زمن التسرب المتوقع", f"{years} سنة")

with tab3:
    st.subheader("توليد تقرير هندسي سريع (AI)")
    st.info("يستخدم هذا الخيار أسرع موديل ذكاء اصطناعي لاستخراج التوصيات في ثوانٍ.")
    
    if st.button("⚡ استخراج التقرير الآن"):
        api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", None)
        
        if not api_key:
            st.error("⚠️ يرجى إضافة مفتاح GEMINI_API_KEY في إعدادات Secrets المنصة.")
        else:
            with st.spinner("جاري استخراج التقرير في ثوانٍ..."):
                try:
                    genai.configure(api_key=api_key)
                    # استخدام أسرع نموذج متاح لتجنب البطء
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    prompt = f"""
                    أنت خبير هندسي بيئي في التعدين بالسودان. اكتب تقريراً مختصراً ومركزاً في 4 نقاط فقط للموقع التالي:
                    - الموقع: {selected_preset}
                    - نسبة الخطر: {risk_score}%
                    - تركيز السيانيد: {cyanide_conc} mg/L
                    - زمن الوصول للمياه: {years} سنة
                    
                    المطلوب:
                    1. تقييم خطورة الحالة موجز.
                    2. الإجراء الهندسي الفوري المطلوبة للحماية.
                    3. طريقة تحييد خطر السيانيد k.
                    """
                    
                    response = model.generate_content(prompt)
                    st.success("تم توليد التقرير بنجاح!")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"حدث خطأ أثناء التواصل مع الخدمة: {e}")
