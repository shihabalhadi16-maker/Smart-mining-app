import streamlit as st
import folium
from streamlit_folium import st_folium
import google.generativeai as genai

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="المساعد الجيولوجي والرقابي الذكي", layout="wide")

st.title("🛡️ المساعد الجيولوجي والرقابي الذكي")
st.write("منصة تقييم المخاطر البيئية لمواقع التعدين بالسودان")

# --- 2. جلب مفتاح Gemini من الـ Secrets تلقائياً ---
api_key = st.secrets.get("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    st.error("⚠️ لم يتم العثور على GEMINI_API_KEY في قسم Secrets. يرجى التأكد من إضافته في إعدادات التطبيق.")

# --- 3. القائمة الجانبية (مدخلات البيانات) ---
st.sidebar.header("📋 مدخلات موقع التعدين")
site_name = st.sidebar.text_input("اسم المنجم / الموقع", "أبو حمد - موقع 1")
water_depth = st.sidebar.slider("عمق المياه الجوفية (متر)", 2, 150, 25)
river_dist = st.sidebar.slider("المسافة عن أقرب مجرى مائي (متر)", 10, 5000, 350)
cyanide_conc = st.sidebar.number_input("تركيز السيانيد (mg/L)", 0.0, 5.0, 0.25, step=0.05)
soil_type = st.sidebar.selectbox("نوع التربة", ["تربة رملية (نفاذية عالية)", "تربة صخرية (نفاذية متوسطة)", "تربة طينية (نفاذية منخفضة)"])

# --- 4. قسم الذكاء الاصطناعي (توليد التقرير) ---
st.subheader("🤖 التحليل البيئي بالذكاء الاصطناعي")

if st.button("✨ توليد تقرير وتحليل بيئي بالذكاء الاصطناعي"):
    if not api_key:
        st.error("يرجى التأكد من إضافة المفتاح في قسم Secrets أولاً.")
    else:
        with st.spinner("جاري تحليل البيانات الجيولوجية والبيئية بواسطة Gemini..."):
            prompt = f"""
            بصفتك خبيراً بيئياً وجيوتقنياً في مجال التعدين بالسودان، قم بتوليد تقرير هندسي وتقييم مخاطر للموقع التالي:
            - اسم المنجم/المنطقة: {site_name}
            - عمق المياه الجوفية: {water_depth} متر
            - المسافة عن المجرى المائي: {river_dist} متر
            - تركيز السيانيد: {cyanide_conc} mg/L
            - نوع التربة: {soil_type}
            
            يرجى تقديم:
            1. تقييم مدى خطورة التسرب الجوفي.
            2. التوصيات الهندسية الفورية للسلامة.
            3. حلول المعالجة المقترحة لحماية المياه الجوفية والمجرى المائي.
            """
            
            try:
                response = model.generate_content(prompt)
                st.success("تم توليد التقرير بنجاح! 📊")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"حدث خطأ أثناء الاتصال بالذكاء الاصطناعي: {e}")

st.divider()

# --- 5. عرض الخريطة الميدانية ---
st.subheader("🌐 الخريطة الجغرافية الميدانية")
# إحداثيات افتراضية لمدينة أبو حمد
m = folium.Map(location=[19.5333, 33.3167], zoom_start=12)
folium.Marker(
    [19.5333, 33.3167], 
    popup=f"موقع: {site_name}", 
    tooltip=site_name,
    icon=folium.Icon(color="red", icon="info-sign")
).add_to(m)

st_folium(m, width="100%", height=400)
