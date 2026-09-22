# ==========================================
# 9. قسم التحليل البيئي بالذكاء الاصطناعي (مع دعم gemini-3.6-flash وإعادة المحاولة)
# ==========================================
st.subheader("🤖 التحليل البيئي بالذكاء الاصطناعي")

if st.button("توليد تقرير بيئي سريع ✨", type="primary"):
    if client is None:
        st.error("⚠️ لم يتم العثور على المفتاح GEMINI_API_KEY داخل Secrets في إعدادات التطبيق.")
    else:
        prompt = f"""
        أنت خبير هندسة تعدين وسلامة بيئية. اكتب تقريراً موجزاً جداً وفي نقاط سريعة ومباشرة:
        - الموقع: {st.session_state.site_name}
        - عمق المياه الجوفية: {water_depth}م | المجرى المائي: {river_dist}م | التربة: {soil_type}
        - السيانيد: {cyanide_conc} mg/L | درجة الخطر: {risk_score}%
        
        اذكر فوراً:
        1. تقييم المخاطر المباشرة.
        2. 3 توصيات هندسية حاسمة لمنع التسرب.
        """
        
        report_container = st.empty()
        full_text = ""
        
        # الاعتماد الأساسي على نموذج 3.6 ومحاولته
        models_to_try = ['gemini-3.6-flash', 'gemini-3.6-pro']
        success = False

        for model_name in models_to_try:
            if success:
                break
            try:
                response = client.models.generate_content_stream(
                    model=model_name,
                    contents=prompt
                )
                for chunk in response:
                    full_text += chunk.text
                    report_container.markdown(full_text + "▌")
                
                report_container.markdown(full_text)
                st.success("تم كتابة التقرير بنجاح!")
                success = True
            except Exception as e:
                # في حال وجود ضغط مؤقت 503 يتم الانتقال للمحاولة التالية
                continue
        
        if not success:
            st.warning("⏳ الخوادم تعاني من ضغط عالٍ حالياً (503)، يرجى الضغط على الزر مرة أخرى بعد بضع ثوانٍ.")
