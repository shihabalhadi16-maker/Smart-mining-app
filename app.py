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
