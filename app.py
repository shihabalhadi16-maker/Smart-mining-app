import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Smart Mining System", page_icon="⛏️", layout="wide")

st.title("⛏️ منصة التعدين الذكي وتقييم المخاطر البيئية")
st.markdown("نظام ذكي متكامل لتقييم أمان مواقع التعدين وجدواها الاقتصادية باستخدام الذكاء الاصطناعي - جامعة الخرطوم")

mining_data = [
    {"ID": "ST-01", "الموقع": "حوض الكرتة الرئيسي", "الولاية": "نهر النيل", "lat": 18.55, "lon": 33.82, "عمق المياه (م)": 12, "الخطر %": 96.8, "الحالة": "حرج جداً"},
    {"ID": "ST-02", "الموقع": "منجم أهلي حديث", "الولاية": "نهر النيل", "lat": 18.42, "lon": 33.95, "عمق المياه (م)": 28, "الخطر %": 78.5, "الحالة": "مرتفع"},
    {"ID": "ST-03", "الموقع": "معالجة بعيدة عن المياه", "الولاية": "الشمالية", "lat": 18.60, "lon": 33.65, "عمق المياه (م)": 85, "الخطر %": 22.1, "الحالة": "آمن"},
    {"ID": "ST-04", "الموقع": "حوض معالجة بالسيانيد", "الولاية": "البحر الأحمر", "lat": 18.35, "lon": 33.72, "عمق المياه (م)": 18, "الخطر %": 84.3, "الحالة": "حرج"},
    {"ID": "ST-05", "الموقع": "منطقة استكشاف جديدة", "الولاية": "نهر النيل", "lat": 18.70, "lon": 33.90, "عمق المياه (م)": 95, "الخطر %": 15.0, "الحالة": "آمن"}
]

df = pd.DataFrame(mining_data)

col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("📍 الخريطة الجغرافية للمواقع والمخاطر")
    m = folium.Map(location=[18.55, 33.82], zoom_start=8)
    for idx, row in df.iterrows():
        color = "red" if row["الخطر %"] > 70 else "green"
        folium.Marker(
            [row["lat"], row["lon"]],
            popup=f"<b>{row['الموقع']}</b><br>مستوى الخطر: {row['الخطر %']}%",
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(m)
    st_folium(m, width="100%", height=400)

with col2:
    st.subheader("📊 حاسبة التنبؤ السريع بالخطر")
    water_depth = st.slider("عمق المياه الجوفية (متر)", 5, 150, 20)
    distance_river = st.slider("المسافة من مجرى النيل (متر)", 10, 2000, 200)
    
    risk_score = max(5.0, min(99.9, round((100 - water_depth * 0.5) + (50 - distance_river * 0.05), 1)))
    st.metric(label="نسبة الخطر المتوقعة", value=f"{risk_score}%")
    
    if risk_score > 70:
        st.error("⚠️ موقع حرج جداً - يتطلب بطانات عازلة سميكة ومعالجة فورية.")
    else:
        st.success("✅ موقع آمن ضمن المعايير البيئية.")

st.subheader("📋 لوحة تحكم البيانات الشاملة")
st.dataframe(df, use_container_width=True)
