import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap, Geocoder
from streamlit_folium import st_folium
import google.generativeai as genai
import io

# ==========================================
# 1. تهيئة وإعدادات الصفحة الرئيسية
# ==========================================
st.set_page_config(
    page_title="المنصة الذكية لتقييم المخاطر البيئية للتعدين (DRASTIC)",
    page_icon="⛏️",
    layout="wide"
)

# ==========================================
# 2. التنسيق البصري وواجهة المستخدم (CSS)
# ==========================================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(rgba(244, 238, 218, 0.90), rgba(193, 154, 107, 0.93)),
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
    background-color: rgba(255, 255, 255, 0.85) !important;
    border-radius: 10px;
    padding: 10px;
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
    st.title("⛏️ المنصة المتقدمة لتقييم حساسية المياه الجوفية للتلوث (DRASTIC Model)")
    st.caption("جامعة الخرطوم — كلية الهندسة — قسم هندسة التعدين | نظام نمذجة التلوث الجوفي والتحليل السيناريو")

st.markdown("---")

# ==========================================
# 4. خوارزمية DRASTIC المعتمدة عالمياً (تعديل 1)
# ==========================================
def calculate_drastic(depth, recharge, aquifer, soil, topography, vadose, hydraulic_cond, liner=False):
    """
    نموذج DRASTIC مع حزمة الأوزان القياسية (US EPA):
    Index = D_r*D_w + R_r*R_w + A_r*A_w + S_r*S_w + T_r*T_w + I_r*I_w + C_r*C_w
    """
    # الأوزان المعتمدة (Weights)
    Dw, Rw, Aw, Sw, Tw, Iw, Cw = 5, 4, 3, 2, 1, 5, 3

    # 1. Depth to Water Rating (D)
    if depth < 5: Dr = 10
    elif depth < 15: Dr = 9
    elif depth < 30: Dr = 7
    elif depth < 50: Dr = 5
    else: Dr = 2

    # 2. Recharge Rating (R)
    Rr = 8 if recharge > 200 else (5 if recharge > 100 else 2)

    # 3. Aquifer Media Rating (A)
    Ar = 8 if "حصى" in aquifer or "كاست" in aquifer else (6 if "حجر رملي" in aquifer else 4)

    # 4. Soil Media Rating (S)
    if "رملية" in soil: Sr = 9
    elif "طمية" in soil: Sr = 5
    else: Sr = 2 # صخرية أو طينية

    # 5. Topography Rating (T)
    Tr = 10 if topography < 2 else (7 if topography < 5 else 3)

    # 6. Impact of Vadose Zone (I)
    Ir = 9 if "رمل" in vadose or "هشة" in vadose else (5 if "مختلطة" in vadose else 2)
    if liner: Ir = max(1, Ir - 6) # تطبيق البطانة العازلة ينقص التأثير بشكل حاد

    # 7. Hydraulic Conductivity (C)
    Cr = 10 if hydraulic_cond > 40 else (6 if hydraulic_cond > 10 else 2)

    # حساب المؤشر النهائي
    drastic_index = (Dr * Dw) + (Rr * Rw) + (Ar * Aw) + (Sr * Sw) + (Tr * Tw) + (Ir * Iw) + (Cr * Cw)
    
    # تحويل المؤشر لنسبة مئوية (المجال النظري بين 23 و 226)
    risk_percentage = min(max(round(((drastic_index - 23) / (226 - 23)) * 100, 1), 5.0), 99.0)
    return drastic_index, risk_percentage

# ==========================================
# 5. إدارة الجلسة والمواقع المسبقة
# ==========================================
preset_locations = {
    "أبو حمد (نهر النيل)": {"coords": (19.5333, 33.3167), "depth": 15, "dist": 250, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.45},
    "عطبرة (نهر النيل)": {"coords": (17.6833, 33.9833), "depth": 8, "dist": 100, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.80},
    "بربر (نهر النيل)": {"coords": (18.0167, 33.9833), "depth": 12, "dist": 180, "soil": "تربة طمية مختلطة (نفاذية متوسطة)", "cyanide": 0.30},
    "قبقبة / وادي العشاري": {"coords": (21.8000, 34.5000), "depth": 60, "dist": 2500, "soil": "تربة صخرية صلبة (نفاذية منخفضة)", "cyanide": 0.10},
    "📍 إدخال موقع مخصص": {"coords": (19.5333, 33.3167), "depth": 15, "dist": 250, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.10}
}

if "selected_preset" not in st.session_state:
    st.session_state.selected_preset = "أبو حمد (نهر النيل)"

def update_preset():
    sel = st.session_state.selected_preset
    d = preset_locations[sel]
    st.session_state.v_lat = float(d["coords"][0])
    st.session_state.v_lon = float(d["coords"][1])
    st.session_state.v_depth = int(d["depth"])
    st.session_state.v_dist = int(d["dist"])
    st.session_state.v_soil = d["soil"]
    st.session_state.v_cyanide = float(d["cyanide"])

if "v_lat" not in st.session_state:
    update_preset()

# ==========================================
# 6. القائمة الجانبية للتفاعل (Sidebar)
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png", width=120)
st.sidebar.header("🕹️ مدخلات وتقييم الموقع")

selected_preset = st.sidebar.selectbox("اختيار موقع معتمد:", list(preset_locations.keys()), key="selected_preset", on_change=update_preset)
site_name = st.sidebar.text_input("اسم المنجم/الموقع:", value=selected_preset if selected_preset != "📍 إدخال موقع مخصص" else "منجم جديد")

lat_input = st.sidebar.number_input("خط العرض (Lat):", key="v_lat", format="%.4f")
lon_input = st.sidebar.number_input("خط الطول (Lon):", key="v_lon", format="%.4f")

st.sidebar.markdown("---")
st.sidebar.header("🧬 معايير نموذج DRASTIC")
water_depth = st.sidebar.slider("عمق المياه الجوفية (متر) - D:", 1, 120, key="v_depth")
river_dist = st.sidebar.slider("البعد عن أقرب مجرى مائي (متر):", 20, 5000, key="v_dist")
soil_type = st.sidebar.selectbox("نوع التربة - S:", ["تربة رملية هشّة (نفاذية عالية)", "تربة طمية مختلطة (نفاذية متوسطة)", "تربة صخرية صلبة (نفاذية منخفضة)"], key="v_soil")
cyanide_conc = st.sidebar.slider("تركيز السيانيد/الملوثات (mg/L):", 0.01, 2.00, key="v_cyanide")

# ==========================================
# 7. حساب نموذج DRASTIC وسيناريو المقارنة (تعديل 1 & 5)
# ==========================================
# حساب الوضع الحالي
drastic_idx_current, risk_current = calculate_drastic(
    depth=water_depth, recharge=50, aquifer="حجر رملي",
    soil=soil_type, topography=2, vadose=soil_type, hydraulic_cond=15, liner=False
)

# قسم مقارنة السيناريوهات (تعديل 5)
st.subheader("💡 مقارنة السيناريوهات والحلول الهندسية (Scenario Analysis)")
col_sc1, col_sc2 = st.columns(2)

with col_sc1:
    st.markdown("#### 🔴 الوضع الحالي (دون معالجة)")
    st.metric("مؤشر DRASTIC الحالي", f"{drastic_idx_current} pt")
    st.metric("نسبة الخطر البيئي", f"{risk_current}%", delta="وضع حرج" if risk_current > 60 else "متوسط", delta_color="inverse")

with col_sc2:
    st.markdown("#### 🟢 السيناريو المعدل (إجراءات هندسية)")
    apply_liner = st.checkbox("تطبيق بطانة HDPE عالية الكثافة عازلة للتربة", value=True)
    add_distance = st.slider("زيادة مسافة الأمان عن المجرى المائي (متر إضافي):", 0, 2000, step=100, value=500)
    
    # حساب سيناريو التحسين
    drastic_idx_opt, risk_opt = calculate_drastic(
        depth=water_depth, recharge=20, aquifer="حجر رملي",
        soil=soil_type, topography=2, vadose=soil_type, hydraulic_cond=5, liner=apply_liner
    )
    
    diff = round(risk_current - risk_opt, 1)
    st.metric("مؤشر DRASTIC بعد التحسين", f"{drastic_idx_opt} pt")
    st.metric("نسبة الخطر الجديدة", f"{risk_opt}%", delta=f"انخفاض الخطر بـ -{diff}%", delta_color="normal")

st.markdown("---")

# ==========================================
# 8. رفع وتحليل الملفات الجماعية CSV/Excel (تعديل 2)
# ==========================================
st.subheader("📂 التقييم الجماعي للمواقع (Bulk CSV/Excel Upload)")
uploaded_file = st.file_uploader("قم برفع ملف إكسل أو CSV يحتوي إحداثيات المناجم لحسابها دفعة واحدة:", type=["csv", "xlsx"])

bulk_df = None
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            bulk_df = pd.read_csv(uploaded_file)
        else:
            bulk_df = pd.read_excel(uploaded_file)
            
        st.success(f"تم تحميل الملف بنجاح! عدد المواقع المكتشفة: {len(bulk_df)}")
        
        # حساب التقييم لكل موقع في الملف
        if 'Latitude' in bulk_df.columns and 'Longitude' in bulk_df.columns:
            results = []
            for _, row in bulk_df.iterrows():
                d = row.get('Depth', 15)
                s = row.get('Soil', 'رملية')
                _, idx_risk = calculate_drastic(d, 50, "حجر رملي", s, 2, s, 15)
                results.append(idx_risk)
            
            bulk_df['DRASTIC_Risk_%'] = results
            st.dataframe(bulk_df.head(10), use_container_width=True)
            
            # زر تحميل النتائج المجتمعة
            output_buffer = io.BytesIO()
            bulk_df.to_excel(output_buffer, index=False)
            st.download_button(
                label="📥 تحميل التقرير الشامل لجميع المناجم (Excel)",
                data=output_buffer.getvalue(),
                file_name="Mining_Risks_Report.xlsx",
                mime="application/vnd.ms-excel"
            )
        else:
            st.warning("⚠️ يرجى التأكد من احتواء الملف على أعمدة باسم 'Latitude' و 'Longitude'.")
    except Exception as e:
        st.error(f"حدث خطأ أثناء قراءة الملف: {e}")

st.markdown("---")

# ==========================================
# 9. التقرير بالذكاء الاصطناعي وتصدير PDF/Text (تعديل 4)
# ==========================================
st.subheader("🤖 التقرير الفني الذكي والتصدير (Gemini 3.6)")

ai_report_text = ""
if st.button("✨ توليد التقرير البيئي الشامل", type="primary", use_container_width=True):
    if "GEMINI_API_KEY" in st.secrets:
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel('gemini-3.6-flash')
            
            prompt = f"""
            بصفتك مستشاراً هيدروجيولوجياً وبيئياً في جامعة الخرطوم، أعد تقريراً هندسياً رفيضاً مستنداً على نموذج DRASTIC:
            - اسم الموقع: {site_name} | الإحداثيات: ({lat_input}, {lon_input})
            - مؤشر DRASTIC الحالي: {drastic_idx_current} ({risk_current}%)
            - مؤشر DRASTIC بعد الحلول الهندسية: {drastic_idx_opt} ({risk_opt}%)
            - تركيز السيانيد: {cyanide_conc} mg/L | عمق المياه: {water_depth}م
            
            قدم التقرير ملخصاً في:
            1. **تقييم حساسية المياه الجوفية للتلوث بناءً على DRASTIC**.
            2. **مقارنة الأثر قبل وبعد التعديل الهندسي**.
            3. **توصيات نهائية سريعة**.
            """
            
            response = model.generate_content(prompt)
            ai_report_text = response.text
            st.markdown(ai_report_text)
            
            # تصدير التقرير النصي جاهز للطباعة (تعديل 4)
            full_pdf_content = f"""
            ==================================================
            جامعة الخرطوم - كلية الهندسة - قسم هندسة التعدين
            تقرير تقييم المخاطر البيئية والتسرب الجوفي (DRASTIC)
            ==================================================
            الموقع: {site_name}
            الإحداثيات: {lat_input}, {lon_input}
            نسبة الخطر الحالي: {risk_current}%
            نسبة الخطر بعد معالجة البطانة: {risk_opt}%
            --------------------------------------------------
            التحليل الفني والذكاء الاصطناعي:
            {ai_report_text}
            """
            
            st.download_button(
                label="📄 تصدير التقرير الفني للطباعة (TXT/PDF Ready)",
                data=full_pdf_content,
                file_name=f"DRASTIC_Report_{site_name}.txt",
                mime="text/plain"
            )
            
        except Exception as e:
            st.error(f"خطأ أثناء استدعاء نموذج الذكاء الاصطناعي: {e}")
    else:
        st.warning("⚠️ يرجى إضافة GEMINI_API_KEY في إعدادات Secrets.")

st.markdown("---")

# ==========================================
# 10. الخريطة الحرارية المتقدمة GIS Heatmap (تعديل 3)
# ==========================================
st.subheader(f"🗺️ التحليل المكاني GIS والخرائط الحرارية (Heatmaps & Buffers): {site_name}")

# إنشاء الخريطة الأساسية
m = folium.Map(location=[lat_input, lon_input], zoom_start=11, tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri')

# إدراج شريط البحث الجغرافي
Geocoder(collapsed=False, placeholder="🔍 ابحث عن أي موقع...").add_to(m)

# 1. إضافة الخريطة الحرارية GIS Heatmap (تعديل 3)
heat_data = [[lat_input, lon_input, risk_current / 100.0]]
if bulk_df is not None and 'Latitude' in bulk_df.columns and 'Longitude' in bulk_df.columns:
    for _, r in bulk_df.iterrows():
        heat_data.append([r['Latitude'], r['Longitude'], r.get('DRASTIC_Risk_%', 50) / 100.0])

HeatMap(heat_data, radius=25, blur=15, min_opacity=0.4).add_to(m)

# 2. نطاقات التأثير وسريان المياه الجوفية Groundwater Flow Direction Buffer (تعديل 3)
marker_color = "red" if risk_current >= 70 else ("orange" if risk_current >= 40 else "green")

folium.Marker(
    location=[lat_input, lon_input],
    popup=f"<b>الموقع:</b> {site_name}<br><b>مؤشر DRASTIC:</b> {risk_current}%",
    tooltip=site_name,
    icon=folium.Icon(color=marker_color, icon="info-sign")
).add_to(m)

# دائرة نطاق الخطر المباشر
folium.Circle(
    location=[lat_input, lon_input],
    radius=river_dist + add_distance,
    color=marker_color,
    fill=True,
    fill_opacity=0.15,
    popup="نطاق الأمان الانتطاقي المطور"
).add_to(m)

# إسقاط الخريطة على Streamlit
st_folium(m, width="100%", height=500)
