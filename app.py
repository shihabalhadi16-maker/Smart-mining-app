import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import google.generativeai as genai
from geopy.geocoders import Nominatim
import random
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# 1. تهيئة النظام وإعدادات الصفحة
# ==========================================
st.set_page_config(
    page_title="منصة التعدين الذكي - جامعة الخرطوم",
    page_icon="⛏️",
    layout="wide"
)

API_KEY = st.secrets.get("GEMINI_API_KEY", None)

if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-3.6-flash')
    except Exception:
        model = None
else:
    model = None

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
# 3. الهيدر الرئيسي
# ==========================================
col_logo, col_title = st.columns([1, 5])

with col_logo:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png", width=105)

with col_title:
    st.title("⛏️ المنصة المتقدمة لتقييم أخطار التعدين وهيدروجيولوجيا المياه الجوفية")
    st.caption("جامعة الخرطوم — كلية الهندسة — قسم هندسة التعدين | الموديل الهندسي الذكي المتكامل")

st.markdown("---")

# ==========================================
# 4. محرك حساب نموذج DRASTIC القياسي
# ==========================================
def calculate_drastic(depth_m, river_dist_m, soil_type, cyanide_mg):
    # D: Depth to Water (1-10)
    if depth_m < 5: d_rating = 10
    elif depth_m < 15: d_rating = 9
    elif depth_m < 30: d_rating = 7
    elif depth_m < 50: d_rating = 5
    else: d_rating = 3
    
    # R: Recharge / Proximity to Surface Water (1-10)
    if river_dist_m < 100: r_rating = 10
    elif river_dist_m < 500: r_rating = 8
    elif river_dist_m < 1500: r_rating = 5
    else: r_rating = 2
    
    # S: Soil Media (1-10)
    if "رملية" in soil_type: s_rating = 9
    elif "طمية" in soil_type: s_rating = 5
    else: s_rating = 2
    
    # C: Contaminant Impact Factor (Cyanide)
    c_rating = min(10, int(cyanide_mg * 8) + 1)
    
    # DRASTIC Index Calculation (Weighted Sum)
    index = (d_rating * 5) + (r_rating * 4) + (s_rating * 2) + (c_rating * 5)
    
    # Normalization to % (Max Score ~ 160)
    risk_percentage = round(min(98.5, max(5.0, (index / 160.0) * 100)), 1)
    travel_years = round((depth_m * (11 - s_rating)) / 15.0, 1)
    
    return risk_percentage, max(0.1, travel_years)

# ==========================================
# 5. إدارة حالة الجلسة والإدخال
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

if "latitude" not in st.session_state: st.session_state.latitude = 19.5333
if "longitude" not in st.session_state: st.session_state.longitude = 33.3167
if "site_name" not in st.session_state: st.session_state.site_name = "أبو حمد (نهر النيل)"

st.sidebar.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png", width=140)

# ==========================================
# 6. القائمة الجانبية وإدخال البيانات
# ==========================================
st.sidebar.header("🔍 البحث وتحديد الموقع")
search_query = st.sidebar.text_input("بحث عالمي عن موقع/منجم:", placeholder="مثال: Ariab, الخرطوم...")

if st.sidebar.button("بحث عن الموقع 🧭", type="primary"):
    if search_query.strip():
        geolocator = Nominatim(user_agent=f"uofk_mining_{random.randint(1000,9999)}")
        loc = None
        try: loc = geolocator.geocode(f"{search_query}, Sudan", timeout=10)
        except: pass
        if not loc:
            try: loc = geolocator.geocode(search_query, timeout=10)
            except: pass
        if loc:
            st.session_state.latitude, st.session_state.longitude = float(loc.latitude), float(loc.longitude)
            st.session_state.site_name = search_query
            st.rerun()

selected_preset = st.sidebar.selectbox("مناطق سودانية مسجلة:", ["-- اختر موقعاً --"] + list(preset_locations.keys()))
if selected_preset != "-- اختر موقعاً --":
    coords = preset_locations[selected_preset]
    if st.session_state.latitude != coords[0] or st.session_state.longitude != coords[1]:
        st.session_state.latitude, st.session_state.longitude = coords[0], coords[1]
        st.session_state.site_name = selected_preset
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("📊 المعطيات الهيدروجيولوجية")
water_depth = st.sidebar.slider("عمق المياه الجوفية (متر):", 2, 150, 15)
river_dist = st.sidebar.slider("البعد عن أقرب مجرى مائي (متر):", 20, 5000, 250, 50)
soil_type = st.sidebar.selectbox("نوع التربة الجيولوجية:", ["تربة صخرية صلبة (نفاذية منخفضة)", "تربة طمية مختلطة (نفاذية متوسطة)", "تربة رملية هشّة (نفاذية عالية)"])
cyanide_conc = st.sidebar.slider("تركيز السيانيد/الزئبق (mg/L):", 0.01, 2.00, 0.45, 0.01)

# ==========================================
# 7. معالجة حسابات DRASTIC والسيناريو الإشعاعي
# ==========================================
base_risk, base_years = calculate_drastic(water_depth, river_dist, soil_type, cyanide_conc)

st.subheader("📊 مؤشرات الحسابات الهيدروجيولوجية (نموذج DRASTIC)")

c1, c2, c3 = st.columns(3)
c1.metric("درجة الخطر الحالية (DRASTIC)", f"{base_risk}%")
status = "✅ مطابق" if cyanide_conc <= 0.05 else "⚠️ يتجاوز WHO"
c2.metric("تركيز السيانيد", f"{cyanide_conc} mg/L", delta=status, delta_color="inverse" if cyanide_conc > 0.05 else "normal")
c3.metric("زمن الوصول للمياه الجوفية", f"{base_years} سنة")

st.markdown("---")

# ==========================================
# 8. شاشة تحليل السيناريوهات (Before & After)
# ==========================================
st.subheader("🔄 تحليل السيناريوهات والحلول الهندسية المقترحة (Scenario Analysis)")

with st.expander("🛠️ اضغط هنا لتجربة الحلول الهندسية ورؤية تحسن نسبة الخطر", expanded=False):
    col_sc1, col_sc2 = st.columns(2)
    with col_sc1:
        st.markdown("**الإجراءات الهندسية الوقائية:**")
        use_liner = st.checkbox("تركيب بطانة عازلة HDPE عالية الكثافة (تمنع النفاذية)")
        increase_dist = st.slider("زيادة المسافة عن المجرى المائي عبر تغيير موقع الأحواض (متر):", 0, 2000, 500, 100)
    
    with col_sc2:
        mod_soil = "تربة صخرية صلبة (نفاذية منخفضة)" if use_liner else soil_type
        mod_dist = river_dist + increase_dist
        opt_risk, opt_years = calculate_drastic(water_depth, mod_dist, mod_soil, cyanide_conc)
        
        st.markdown("**مقارنة الأداء بعد التطوير:**")
        st.metric("درجة الخطر بعد الحلول الهندسية", f"{opt_risk}%", delta=f"{opt_risk - base_risk:.1f}%", delta_color="normal")
        st.metric("زمن وصول التلوث الجديد", f"{opt_years} سنة", delta=f"+{opt_years - base_years:.1f} سنة")

st.markdown("---")

# ==========================================
# 9. رفـع الملفات المتعددة (CSV / Excel Upload)
# ==========================================
st.subheader("📁 تحليل دفعة مواقع تعدين (Batch Processing)")
uploaded_file = st.file_uploader("قم برفع ملف Excel أو CSV يحتوي على معطيات عدة مناجم:", type=["csv", "xlsx"])

uploaded_data = None
if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            uploaded_data = pd.read_csv(uploaded_file)
        else:
            uploaded_data = pd.read_excel(uploaded_file)
        
        st.success(f"تم تحميل الملف بنجاح! عدد المواقع: {len(uploaded_data)}")
        
        # حساب الحقول إذا كانت الأعمدة متوفرة
        if all(col in uploaded_data.columns for col in ['lat', 'lon', 'depth', 'dist', 'soil', 'cyanide']):
            results = []
            for _, row in uploaded_data.iterrows():
                r, y = calculate_drastic(row['depth'], row['dist'], str(row['soil']), row['cyanide'])
                results.append((r, y))
            uploaded_data['DRASTIC_Risk_%'] = [r[0] for r in results]
            uploaded_data['Travel_Years'] = [r[1] for r in results]
            
            st.dataframe(uploaded_data)
        else:
            st.warning("يرجى التأكد من احتواء الملف على الأعمدة المطلوبة: lat, lon, depth, dist, soil, cyanide")
    except Exception as e:
        st.error(f"خطأ في قراءة الملف: {e}")

st.markdown("---")

# ==========================================
# 10. الذكاء الاصطناعي وتوليد تقارير PDF
# ==========================================
st.subheader("🤖 الاستشارة الذكية وتصدير التقرير الفني")

ai_report_text = ""

if st.button("توليد التقرير الهندسي بالذكاء الاصطناعي ✨", type="primary"):
    if model is None:
        st.error("⚠️ يرجى ضبط GEMINI_API_KEY في إعدادات التطبيق (Secrets).")
    else:
        prompt = f"""
        بصفتك خبير استشاري في هيدروجيولوجيا التعدين بجميعة الخرطوم، اكتب تقريراً فنياً باللغة العربية:
        - الموقع: {st.session_state.site_name} (خط عرض: {st.session_state.latitude}, خط طول: {st.session_state.longitude})
        - تقييم DRASTIC للمخاطر: {base_risk}%
        - المعطيات: عمق المياه {water_depth}م، المسافة عن النيل {river_dist}م، التربة {soil_type}، السيانيد {cyanide_conc} mg/L
        
        يرجى تقديم:
        1. تقييم تفصيلي للمخاطر.
        2. التوصيات الهندسية الحاكمة للحماية والمراقبة.
        """
        with st.spinner("جاري صياغة التقرير الهندسي..."):
            try:
                res = model.generate_content(prompt)
                ai_report_text = res.text
                st.info(ai_report_text)
            except Exception as e:
                st.error(f"خطأ في الاتصال بالذكاء الاصطناعي: {e}")

# خدمة تصدير PDF
def generate_pdf(site, risk, depth, dist, soil, cyanide, years, text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, alignment=1)
    normal_style = styles['Normal']
    
    story.append(Paragraph("<b>University of Khartoum - Mining Engineering Dept</b>", title_style))
    story.append(Paragraph("<b>Smart Mining Hydrogeology & Risk Assessment Report</b>", title_style))
    story.append(Spacer(1, 15))
    
    data = [
        ["Site Name", str(site)],
        ["DRASTIC Risk Score", f"{risk}%"],
        ["Water Table Depth", f"{depth} m"],
        ["Distance to Waterway", f"{dist} m"],
        ["Soil Formation", str(soil)],
        ["Cyanide Conc.", f"{cyanide} mg/L"],
        ["Estimated Migration Time", f"{years} Years"]
    ]
    
    t = Table(data, colWidths=[200, 250])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5c2c16')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold')
    ]))
    story.append(t)
    story.append(Spacer(1, 15))
    
    if text:
        story.append(Paragraph("<b>AI Technical Assessment Summary:</b>", styles['Heading2']))
        story.append(Paragraph(text.replace("\n", "<br/>"), normal_style))
        
    doc.build(story)
    buffer.seek(0)
    return buffer

pdf_file = generate_pdf(
    st.session_state.site_name, base_risk, water_depth, 
    river_dist, soil_type, cyanide_conc, base_years, ai_report_text
)

st.download_button(
    label="📄 تحميل التقرير الفني المعتمد (PDF)",
    data=pdf_file,
    file_name=f"Mining_Risk_Report_{st.session_state.site_name}.pdf",
    mime="application/pdf"
)

st.markdown("---")

# ==========================================
# 11. الخريطة التفاعلية الاحترافية مع Heatmap
# ==========================================
st.subheader(f"🗺️ الخريطة الهيدروجيولوجية وخريطة التلوث الحرارية (GIS Heatmap)")

m = folium.Map(location=[st.session_state.latitude, st.session_state.longitude], zoom_start=11)

# إضافة نقاط التلوث الحراري (Heatmap)
heat_data = [[st.session_state.latitude, st.session_state.longitude, base_risk / 100.0]]

if uploaded_data is not None and 'lat' in uploaded_data.columns and 'lon' in uploaded_data.columns:
    for _, row in uploaded_data.iterrows():
        heat_data.append([row['lat'], row['lon'], 0.8])

HeatMap(heat_data, radius=25, blur=15).add_to(m)

# علامة الموقع الحالي
marker_color = "red" if base_risk >= 70 else ("orange" if base_risk >= 40 else "green")
folium.Marker(
    location=[st.session_state.latitude, st.session_state.longitude],
    popup=f"<b>الموقع:</b> {st.session_state.site_name}<br><b>الخطر:</b> {base_risk}%",
    icon=folium.Icon(color=marker_color, icon="info-sign")
).add_to(m)

st_folium(m, width="100%", height=500, key=f"map_{st.session_state.latitude}_{st.session_state.longitude}")
