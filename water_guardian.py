"""
حارس المياه — Water Guardian
============================
منصة ذكية لتقييم جودة مياه الري في السودان
وفق معايير USSL + FAO الدولية

الفريق: شهاب الهادي + سارة عكاشة
الجامعة: جامعة الخرطوم، كلية الهندسة
المسابقة: IGAD + AfDB
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import datetime


# ==========================================
# 1. تصنيفات USSL (1954)
# ==========================================

def wg_classify_ec(ec):
    """تصنيف الملوحة — USSL Handbook 60"""
    if ec < 0.25: return ("C1 - منخفضة", "excellent", 10)
    if ec < 0.75: return ("C2 - متوسطة", "good", 8)
    if ec < 2.25: return ("C3 - مرتفعة", "fair", 6)
    if ec < 4.00: return ("C4 - مرتفعة جداً", "poor", 4)
    return ("C4+ - غير صالحة", "unsuitable", 1)


def wg_classify_sar(sar):
    """تصنيف SAR — USSL Handbook 60"""
    if sar < 10: return ("S1 - منخفضة", "low", 10)
    if sar < 18: return ("S2 - متوسطة", "medium", 8)
    if sar < 26: return ("S3 - مرتفعة", "high", 5)
    return ("S4 - مرتفعة جداً", "very_high", 3)


def wg_classify_nitrate(no3):
    """تصنيف النترات — WHO 2022"""
    if no3 < 5: return ("آمنة", "safe", 10)
    if no3 < 15: return ("مقبولة", "acceptable", 7)
    if no3 < 30: return ("مرتفعة", "high", 4)
    return ("خطيرة", "critical", 1)


def wg_classify_chloride(cl):
    """تصنيف الكلوريد — FAO 29"""
    if cl < 4: return ("آمنة", "safe", 10)
    if cl < 10: return ("متوسطة", "medium", 7)
    if cl < 20: return ("مرتفعة", "high", 4)
    return ("خطيرة", "critical", 1)


def wg_classify_bicarbonate(hco3):
    """تصنيف البيكربونات — FAO 29"""
    if hco3 < 1.5: return ("آمنة", "safe", 10)
    if hco3 < 4: return ("مقبولة", "acceptable", 7)
    if hco3 < 8: return ("مرتفعة", "high", 4)
    return ("خطيرة", "critical", 1)


def wg_calculate_iwqi(ec, sar, no3, cl, hco3):
    """IWQI 0-100 — Meireles et al. (2010)"""
    weights = {"EC": 0.35, "SAR": 0.25, "NO3": 0.20, "Cl": 0.12, "HCO3": 0.08}
    scores = {
        "EC": wg_classify_ec(ec)[2],
        "SAR": wg_classify_sar(sar)[2],
        "NO3": wg_classify_nitrate(no3)[2],
        "Cl": wg_classify_chloride(cl)[2],
        "HCO3": wg_classify_bicarbonate(hco3)[2],
    }
    iwqi = sum(scores[k] * weights[k] for k in weights) * 10
    return round(iwqi, 1), scores


def wg_classify_iwqi(iwqi):
    if iwqi >= 80: return ("🟢 ممتازة — صالحة لكل المحاصيل", "excellent", "green")
    if iwqi >= 65: return ("🟢 جيدة — صالحة لمعظم المحاصيل", "good", "lightgreen")
    if iwqi >= 50: return ("🟡 مقبولة — صالحة للمحاصيل المتحملة", "fair", "orange")
    if iwqi >= 35: return ("🟠 ضعيفة — تحتاج معالجة", "poor", "red")
    return ("🔴 غير صالحة للري", "unsuitable", "darkred")


# ==========================================
# 2. المحاصيل (عادية + استراتيجية)
# ==========================================

WG_CROP_SUITABILITY = {
    "excellent": ["قمح", "ذرة", "برسيم", "خضروات ورقية", "طماطم", "بصل", "بطاطس",
                  "🌾 قصب السكر", "🥜 الفول السوداني", "🌳 الصمغ العربي"],
    "good":      ["قمح", "ذرة", "برسيم", "بصل", "بطاطس", "فول", "عدس",
                  "🌾 قصب السكر", "🌳 الصمغ العربي"],
    "fair":      ["ذرة", "برسيم", "شعير", "قطن", "فول", "سمسم", "🌳 الصمغ العربي"],
    "poor":      ["شعير", "قطن", "نخيل", "زيتون", "أعلاف متحملة", "🌳 الصمغ العربي"],
    "unsuitable": ["لا يُنصح بالزراعة — يحتاج معالجة أو مصدر بديل"],
}

WG_CROP_REQUIREMENTS = {
    "قصب السكر": {
        "icon": "🌾",
        "scientific": "Saccharum officinarum",
        "fao_sensitivity": "Semi-tolerant (MS)",
        "EC_max": 1.7, "SAR_max": 8, "Cl_max": 10,
        "regions_sudan": "النيل الأزرق، سنار، النيل الأبيض، كسلا",
        "economic_importance": "عالية — مشاريع كنانة، عسلاية، النيل الأبيض",
    },
    "الفول السوداني": {
        "icon": "🥜",
        "scientific": "Arachis hypogaea",
        "fao_sensitivity": "Sensitive (S)",
        "EC_max": 1.5, "SAR_max": 3, "Cl_max": 4,
        "regions_sudan": "شمال كردفان، جنوب كردفان، دارفور، النيل الأزرق",
        "economic_importance": "عالية — محصول تصديري + زيت نباتي",
    },
    "الصمغ العربي": {
        "icon": "🌳",
        "scientific": "Acacia senegal / Acacia seyal",
        "fao_sensitivity": "Tolerant (T)",
        "EC_max": 6.0, "SAR_max": 12, "Cl_max": 20,
        "regions_sudan": "كردفان، دارفور، سنار، النيل الأزرق",
        "economic_importance": "حيوية — السودان ينتج 80% من الإنتاج العالمي",
    },
}


def wg_classify_sugarcane(ec, sar, cl, hco3):
    """تقييم خاص لقصب السكر — FAO 29"""
    score, notes = 10, []
    if ec > 3.0: score -= 5; notes.append("ملوحة عالية جداً — خسارة إنتاج > 50%")
    elif ec > 1.7: score -= 3; notes.append("ملوحة مرتفعة — خسارة إنتاج متوقعة")
    elif ec > 1.0: score -= 1; notes.append("ملوحة طفيفة — مراقبة مطلوبة")
    if sar > 15: score -= 3; notes.append("SAR مرتفع جداً — مشاكل صوديوم")
    elif sar > 8: score -= 1.5; notes.append("SAR مرتفع — يحتاج تصريف جيد")
    if cl > 20: score -= 3; notes.append("كلوريد مرتفع — سمية أوراق محتملة")
    elif cl > 10: score -= 1.5; notes.append("كلوريد مرتفع نسبياً")
    if hco3 > 8: score -= 1.5; notes.append("بيكربونات مرتفعة")
    score = max(1, score)
    if score >= 8: return ("🟢 مناسب جداً", "excellent", score, notes)
    if score >= 6: return ("🟢 مناسب", "good", score, notes)
    if score >= 4: return ("🟡 مقبول مع إدارة", "fair", score, notes)
    return ("🔴 غير مناسب", "unsuitable", score, notes)


def wg_classify_peanut(ec, sar, cl, hco3):
    """تقييم خاص للفول السوداني — FAO 29"""
    score, notes = 10, []
    if ec > 2.5: score -= 5; notes.append("ملوحة عالية جداً — محصول سيفشل")
    elif ec > 1.5: score -= 3; notes.append("ملوحة مرتفعة — خسارة إنتاج")
    elif ec > 0.8: score -= 1; notes.append("ملوحة طفيفة — مقبولة")
    if sar > 8: score -= 3; notes.append("SAR مرتفع — تدهور التربة")
    elif sar > 3: score -= 1.5; notes.append("SAR مرتفع نسبياً")
    if cl > 10: score -= 3; notes.append("كلوريد مرتفع — خطر على النمو")
    elif cl > 4: score -= 1.5; notes.append("كلوريد مرتفع نسبياً")
    if hco3 > 6: score -= 1; notes.append("بيكربونات مرتفعة")
    score = max(1, score)
    if score >= 8: return ("🟢 مناسب جداً", "excellent", score, notes)
    if score >= 6: return ("🟢 مناسب", "good", score, notes)
    if score >= 4: return ("🟡 مقبول مع إدارة", "fair", score, notes)
    return ("🔴 غير مناسب", "unsuitable", score, notes)


def wg_classify_gum_arabic(ec, sar, cl, hco3):
    """تقييم خاص للصمغ العربي — Acacia senegal"""
    score, notes = 10, []
    if ec > 10: score -= 4; notes.append("ملوحة عالية جداً — ضعف النمو")
    elif ec > 6: score -= 2; notes.append("ملوحة مرتفعة — نمو متوسط")
    elif ec > 3: score -= 0.5; notes.append("ملوحة طفيفة — لا تأثير يُذكر")
    if sar > 20: score -= 2; notes.append("SAR مرتفع — تأثير محدود")
    elif sar > 12: score -= 1; notes.append("SAR مرتفع نسبياً")
    if cl > 30: score -= 2; notes.append("كلوريد مرتفع جداً")
    elif cl > 20: score -= 1; notes.append("كلوريد مرتفع نسبياً")
    if hco3 > 8: score -= 0.5; notes.append("بيكربونات مرتفعة")
    score = max(1, score)
    if score >= 8: return ("🟢 مناسب جداً", "excellent", score, notes)
    if score >= 6: return ("🟢 مناسب", "good", score, notes)
    if score >= 4: return ("🟡 مقبول", "fair", score, notes)
    return ("🔴 غير مناسب", "unsuitable", score, notes)


# ==========================================
# 3. آبار نموذجية
# ==========================================
WG_PRESET_WELLS = {
    "بئر الجزيرة — مشروع الجزيرة": {
        "coords": (14.4000, 33.5000),
        "ec": 0.9, "sar": 4.5, "no3": 8.0, "cl": 3.0, "hco3": 2.5
    },
    "بئر سنار — الضفة الشرقية": {
        "coords": (13.5500, 33.6000),
        "ec": 0.5, "sar": 2.5, "no3": 4.0, "cl": 2.0, "hco3": 1.5
    },
    "بئر النيل الأبيض — الكوة": {
        "coords": (13.5500, 32.5000),
        "ec": 2.8, "sar": 8.5, "no3": 18.0, "cl": 8.0, "hco3": 4.5
    },
    "بئر شمال كردفان — بارا": {
        "coords": (13.7000, 30.3667),
        "ec": 4.5, "sar": 12.0, "no3": 25.0, "cl": 15.0, "hco3": 6.0
    },
    "بئر كسلا — دلتا القاش": {
        "coords": (15.4500, 36.4000),
        "ec": 1.8, "sar": 6.0, "no3": 12.0, "cl": 5.0, "hco3": 3.0
    },
    "بئر نهر النيل — شندي": {
        "coords": (16.6833, 33.4333),
        "ec": 0.6, "sar": 3.0, "no3": 5.0, "cl": 2.5, "hco3": 2.0
    },
    "بئر البحر الأحمر — طوكر": {
        "coords": (18.4333, 37.7333),
        "ec": 5.5, "sar": 14.0, "no3": 35.0, "cl": 22.0, "hco3": 7.5
    },
}


# ==========================================
# 4. Gemini AI
# ==========================================
WG_GEMINI_MODELS = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"]


@st.cache_data(ttl=3600)
def wg_geocode(query: str):
    try:
        geo = Nominatim(user_agent="water_guardian_v3")
        q = f"{query}, Sudan" if "sudan" not in query.lower() else query
        loc = geo.geocode(q, timeout=10)
        if loc:
            return loc.latitude, loc.longitude, loc.address.split(',')[0]
    except Exception:
        pass
    return None, None, None


def wg_generate_ai(prompt, session_key):
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except (KeyError, FileNotFoundError):
        st.warning("⚠️ أضف GEMINI_API_KEY في Secrets")
        return False

    try:
        from google import genai
    except ImportError:
        st.error("مكتبة `google-genai` غير مثبتة")
        return False

    client = genai.Client(api_key=api_key)
    errors = []
    with st.spinner("🌾 جاري التوليد..."):
        for model_name in WG_GEMINI_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name, contents=prompt
                )
                st.session_state[session_key] = response.text
                st.success("✅ تم التوليد")
                return True
            except Exception as e:
                errors.append(f"{model_name}: {str(e)[:80]}")
                continue

    st.error("فشل التوليد:\n" + "\n".join(errors))
    return False


# ==========================================
# 5. الدالة الرئيسية
# ==========================================

def render_water_guardian():
    """عرض واجهة حارس المياه الكاملة"""

    # Header
    st.markdown("""
    <div style="background:linear-gradient(135deg,#184e77,#34a0a4);color:white;
    padding:20px;border-radius:10px;text-align:center;margin-bottom:20px;">
        <h1 style="margin:0;">💧 حارس المياه</h1>
        <h4 style="margin:5px 0;opacity:0.95;">
            منصة ذكية لتقييم جودة مياه الري | USSL + FAO
        </h4>
        <p style="margin:8px 0 0;font-size:13px;opacity:0.8;">
            التحدي الوطني لريادة الأعمال — IGAD + AfDB
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Session State
    wg_defaults = {
        "wg_well": "بئر الجزيرة — مشروع الجزيرة",
        "wg_ec": 0.9, "wg_sar": 4.5, "wg_no3": 8.0, "wg_cl": 3.0, "wg_hco3": 2.5,
        "wg_ai": "",
    }
    for k, v in wg_defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Tabs
    wg_tab1, wg_tab2, wg_tab3, wg_tab4 = st.tabs([
        "💧 تقييم بئر", "📊 تقييم جماعي", "🌾 المحاصيل الاستراتيجية", "📚 المراجع"
    ])

    # ==========================
    # TAB 1: تقييم فردي
    # ==========================
    with wg_tab1:
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("### 🔍 اختيار البئر")
            selected = st.selectbox(
                "آبار نموذجية:", list(WG_PRESET_WELLS.keys()),
                key="wg_well_sel"
            )

            # تحديث عند التغيير
            if selected != st.session_state.wg_well:
                d = WG_PRESET_WELLS[selected]
                st.session_state.wg_well = selected
                st.session_state.wg_ec = d["ec"]
                st.session_state.wg_sar = d["sar"]
                st.session_state.wg_no3 = d["no3"]
                st.session_state.wg_cl = d["cl"]
                st.session_state.wg_hco3 = d["hco3"]
                st.rerun()

            st.markdown("### 🧪 بيانات جودة المياه")
            ec = st.slider("1. الملوحة EC (dS/m):", 0.1, 8.0,
                           float(st.session_state.wg_ec), 0.1, key="wg_ec_s")
            sar = st.slider("2. الصوديوم SAR:", 0.0, 30.0,
                            float(st.session_state.wg_sar), 0.1, key="wg_sar_s")
            no3 = st.slider("3. النترات NO₃ (mg/L):", 0.0, 50.0,
                            float(st.session_state.wg_no3), 0.5, key="wg_no3_s")
            cl = st.slider("4. الكلوريد Cl (meq/L):", 0.0, 30.0,
                           float(st.session_state.wg_cl), 0.5, key="wg_cl_s")
            hco3 = st.slider("5. البيكربونات HCO₃ (meq/L):", 0.0, 12.0,
                             float(st.session_state.wg_hco3), 0.1, key="wg_hco3_s")

            # حفظ القيم
            st.session_state.wg_ec = ec
            st.session_state.wg_sar = sar
            st.session_state.wg_no3 = no3
            st.session_state.wg_cl = cl
            st.session_state.wg_hco3 = hco3

        with col2:
            iwqi, scores = wg_calculate_iwqi(ec, sar, no3, cl, hco3)
            label, level, color = wg_classify_iwqi(iwqi)
            crops = WG_CROP_SUITABILITY[level]

            st.markdown(f"### 📊 النتائج: {st.session_state.wg_well}")
            k1, k2, k3 = st.columns(3)
            k1.metric("IWQI", f"{iwqi} / 100")
            k2.metric("التصنيف", label)
            k3.metric("المحاصيل المناسبة", len(crops) if level != "unsuitable" else 0)

            st.markdown("### 🌾 المحاصيل المناسبة")
            if level == "unsuitable":
                st.error("❌ المياه غير صالحة للري حالياً")
            else:
                cols = st.columns(min(len(crops), 4))
                for i, crop in enumerate(crops):
                    cols[i % len(cols)].success(f"✅ {crop}")

            with st.expander("🔬 تفاصيل المعايير (USSL + FAO)"):
                df_details = pd.DataFrame([
                    {"المعيار": "الملوحة (EC)", "القيمة": f"{ec} dS/m",
                     "التصنيف": wg_classify_ec(ec)[0], "الدرجة": f"{scores['EC']}/10"},
                    {"المعيار": "الصوديوم (SAR)", "القيمة": f"{sar}",
                     "التصنيف": wg_classify_sar(sar)[0], "الدرجة": f"{scores['SAR']}/10"},
                    {"المعيار": "النترات (NO₃)", "القيمة": f"{no3} mg/L",
                     "التصنيف": wg_classify_nitrate(no3)[0], "الدرجة": f"{scores['NO3']}/10"},
                    {"المعيار": "الكلوريد (Cl)", "القيمة": f"{cl} meq/L",
                     "التصنيف": wg_classify_chloride(cl)[0], "الدرجة": f"{scores['Cl']}/10"},
                    {"المعيار": "البيكربونات (HCO₃)", "القيمة": f"{hco3} meq/L",
                     "التصنيف": wg_classify_bicarbonate(hco3)[0], "الدرجة": f"{scores['HCO3']}/10"},
                ])
                st.dataframe(df_details, use_container_width=True, hide_index=True)

            # التقرير
            st.markdown("---")
            c1, c2 = st.columns([2, 1])
            with c1:
                if st.button("🌾 توليد توصيات للمزارع", type="primary",
                             use_container_width=True, key="wg_gen_ai_btn"):
                    prompt = f"""أنت مستشار زراعي في السودان. اكتب تقريراً مبسطاً بالعربية:

الموقع: {st.session_state.wg_well}
IWQI: {iwqi}/100 — {label}
EC: {ec} dS/m — {wg_classify_ec(ec)[0]}
SAR: {sar} — {wg_classify_sar(sar)[0]}
النترات: {no3} mg/L
الكلوريد: {cl} meq/L
البيكربونات: {hco3} meq/L

اكتب 4-5 فقرات بلغة سهلة تتضمن:
1. حالة المياه
2. هل صالحة للري؟
3. المحاصيل المناسبة
4. نصائح عملية"""
                    wg_generate_ai(prompt, "wg_ai")

            if st.session_state.wg_ai:
                st.info(st.session_state.wg_ai)

            today = datetime.date.today().isoformat()
            export = f"""================================================
حارس المياه — تقرير جودة مياه الري (USSL + FAO)
================================================
التاريخ: {today}
البئر: {st.session_state.wg_well}
------------------------------------------------
IWQI: {iwqi}/100 — {label}
EC: {ec} dS/m → {wg_classify_ec(ec)[0]}
SAR: {sar} → {wg_classify_sar(sar)[0]}
NO₃: {no3} mg/L
Cl: {cl} meq/L
HCO₃: {hco3} meq/L
------------------------------------------------
المحاصيل المناسبة: {", ".join(crops)}
------------------------------------------------
{st.session_state.wg_ai}
================================================"""

            with c2:
                st.download_button("📥 تصدير", data=export,
                                   file_name=f"Irrigation_{st.session_state.wg_well}.txt",
                                   mime="text/plain", use_container_width=True,
                                   key="wg_export_btn")

    # ==========================
    # TAB 2: تقييم جماعي
    # ==========================
    with wg_tab2:
        st.markdown("### 📤 تقييم مجموعة آبار")
        st.caption("الأعمدة المطلوبة: Well_Name, Latitude, Longitude, EC, SAR, Nitrate, Chloride, Bicarbonate")

        uploaded = st.file_uploader("ارفع Excel أو CSV:", type=["xlsx", "csv"], key="wg_bulk_up")

        if uploaded:
            try:
                df = pd.read_csv(uploaded) if uploaded.name.endswith('.csv') else pd.read_excel(uploaded)

                lat_c = next((c for c in df.columns if c.lower() in ['latitude', 'lat']), None)
                lon_c = next((c for c in df.columns if c.lower() in ['longitude', 'lon']), None)
                name_c = next((c for c in df.columns if c.lower() in ['well', 'name', 'site']), None)
                ec_c = next((c for c in df.columns if c.upper() == 'EC'), None)
                sar_c = next((c for c in df.columns if c.upper() == 'SAR'), None)
                n_c = next((c for c in df.columns if c.upper() in ['NITRATE', 'NO3']), None)
                cl_c = next((c for c in df.columns if c.upper() in ['CHLORIDE', 'CL']), None)
                bic_c = next((c for c in df.columns if c.upper() in ['BICARBONATE', 'HCO3']), None)

                if not all([lat_c, lon_c, ec_c, sar_c, n_c, cl_c, bic_c]):
                    st.error("⚠️ تأكد من وجود كل الأعمدة المطلوبة.")
                else:
                    def calc_row(row):
                        iwqi, _ = wg_calculate_iwqi(
                            float(row[ec_c]), float(row[sar_c]), float(row[n_c]),
                            float(row[cl_c]), float(row[bic_c])
                        )
                        label, level, _ = wg_classify_iwqi(iwqi)
                        return pd.Series({"IWQI": iwqi, "التصنيف": label, "المستوى": level})

                    df = pd.concat([df, df.apply(calc_row, axis=1)], axis=1)

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("عدد الآبار", len(df))
                    m2.metric("صالحة", len(df[df["IWQI"] >= 65]))
                    m3.metric("تحتاج معالجة", len(df[(df["IWQI"] >= 35) & (df["IWQI"] < 65)]))
                    m4.metric("غير صالحة", len(df[df["IWQI"] < 35]))

                    st.dataframe(df, use_container_width=True, height=400)
                    st.download_button("📥 تنزيل CSV",
                                       df.to_csv(index=False).encode('utf-8-sig'),
                                       "Irrigation_Assessment.csv", "text/csv",
                                       key="wg_bulk_dl")

                    st.markdown("---")
                    mh = folium.Map(location=[df[lat_c].mean(), df[lon_c].mean()], zoom_start=6)
                    for _, r in df.iterrows():
                        c = {"excellent": "green", "good": "lightgreen", "fair": "orange",
                             "poor": "red", "unsuitable": "darkred"}.get(r["المستوى"], "gray")
                        title = r[name_c] if name_c else "بئر"
                        folium.CircleMarker(
                            [r[lat_c], r[lon_c]], radius=7,
                            popup=f"{title}<br>IWQI: {r['IWQI']}",
                            color=c, fill=True, fill_opacity=0.8
                        ).add_to(mh)
                    st_folium(mh, width="100%", height=400, key="wg_bulk_map")
            except Exception as e:
                st.error(f"خطأ: {e}")

    # ==========================
    # TAB 3: المحاصيل الاستراتيجية
    # ==========================
    with wg_tab3:
        st.markdown("### 🌾 المحاصيل الاستراتيجية السودانية")
        st.caption("قصب السكر، الفول السوداني، الصمغ العربي — تقييم خاص")

        col1, col2 = st.columns([1, 2])

        with col1:
            selected_crop = st.selectbox(
                "المحصول:", list(WG_CROP_REQUIREMENTS.keys()),
                format_func=lambda x: f"{WG_CROP_REQUIREMENTS[x]['icon']} {x}",
                key="wg_crop_sel"
            )

            st.markdown("### 🧪 بيانات المياه")
            c_ec = st.slider("EC (dS/m):", 0.1, 10.0, 1.0, 0.1, key="wg_c_ec")
            c_sar = st.slider("SAR:", 0.0, 25.0, 5.0, 0.5, key="wg_c_sar")
            c_cl = st.slider("Cl (meq/L):", 0.0, 40.0, 5.0, 0.5, key="wg_c_cl")
            c_hco3 = st.slider("HCO₃ (meq/L):", 0.0, 15.0, 3.0, 0.5, key="wg_c_hco3")

            req = WG_CROP_REQUIREMENTS[selected_crop]
            st.info(f"""
**{req['scientific']}**
- FAO: **{req['fao_sensitivity']}**
- EC الأقصى: **{req['EC_max']} dS/m**
- SAR الأقصى: **{req['SAR_max']}**
- Cl الأقصى: **{req['Cl_max']} meq/L**
- مناطق: {req['regions_sudan']}
""")

        with col2:
            if selected_crop == "قصب السكر":
                level, lvl_en, score, notes = wg_classify_sugarcane(c_ec, c_sar, c_cl, c_hco3)
            elif selected_crop == "الفول السوداني":
                level, lvl_en, score, notes = wg_classify_peanut(c_ec, c_sar, c_cl, c_hco3)
            else:
                level, lvl_en, score, notes = wg_classify_gum_arabic(c_ec, c_sar, c_cl, c_hco3)

            st.markdown(f"### {req['icon']} تقييم: {selected_crop}")
            k1, k2 = st.columns(2)
            k1.metric("التصنيف", level)
            k2.metric("الدرجة", f"{score}/10")
            st.progress(score / 10)

            if notes:
                st.markdown("##### ⚠️ ملاحظات")
                for note in notes:
                    st.warning(note)
            else:
                st.success("✅ المياه مناسبة تماماً")

            report = f"""================================================
تقرير — {selected_crop}
================================================
EC: {c_ec} dS/m | SAR: {c_sar} | Cl: {c_cl} | HCO₃: {c_hco3}
------------------------------------------------
التصنيف: {level}
الدرجة: {score}/10
------------------------------------------------
{chr(10).join('• ' + n for n in notes) if notes else 'لا توجد مشاكل'}
================================================"""

            st.download_button("📥 تصدير", report,
                               f"crop_{selected_crop}.txt", "text/plain",
                               use_container_width=True, key="wg_crop_dl")

    # ==========================
    # TAB 4: المراجع
    # ==========================
    with wg_tab4:
        st.markdown("""
### 📚 المراجع والمعايير

#### 1. US Salinity Laboratory (1954)
- *Diagnosis and Improvement of Saline and Alkali Soils*
- USDA Handbook 60

#### 2. FAO Irrigation and Drainage Paper 29
- Ayers & Westcot (1985)

#### 3. WHO (2022)
- Guidelines for Drinking-water Quality

#### 4. Meireles et al. (2010)
- IWQI methodology

### 🧪 الأوزان
| المؤشر | الوحدة | الوزن |
|--------|--------|-------|
| EC | dS/m | 35% |
| SAR | — | 25% |
| NO₃ | mg/L | 20% |
| Cl | meq/L | 12% |
| HCO₃ | meq/L | 8% |

### 🌾 المحاصيل الاستراتيجية
| المحصول | التصنيف | FAO | EC الأقصى |
|---------|---------|-----|-----------|
| قصب السكر | Saccharum officinarum | Semi-tolerant | 1.7 |
| الفول السوداني | Arachis hypogaea | Sensitive | 1.5 |
| الصمغ العربي | Acacia senegal | Tolerant | 6.0 |
""")
