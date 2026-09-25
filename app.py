import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
from geopy.geocoders import Nominatim
import datetime

# ==========================================
# الجزء 1: نموذج DRASTIC (من drastic_model.py)
# ==========================================
MAX_DRASTIC = 226.0
WEIGHTS = {"D": 5, "R": 4, "A": 3, "S": 2, "T": 1, "I": 5, "C": 3}
WHO_CYANIDE_LIMIT = 0.07


def rating_depth(depth_m):
    if depth_m < 1.5: return 10
    if depth_m < 4.6: return 9
    if depth_m < 9.1: return 7
    if depth_m < 15.2: return 5
    if depth_m < 22.9: return 3
    if depth_m < 30.5: return 2
    return 1


def rating_recharge(recharge_mm):
    if recharge_mm < 51: return 1
    if recharge_mm < 102: return 3
    if recharge_mm < 178: return 6
    if recharge_mm < 254: return 8
    return 9


def rating_aquifer(aquifer_type):
    mapping = {
        "massive_shale": 1, "metamorphic": 2, "igneous": 2,
        "weathered_metamorphic": 3, "glacial_till": 4,
        "bedded_sandstone": 6, "limestone": 6,
        "sand_and_gravel": 8, "basalt": 9, "karst_limestone": 10
    }
    return mapping.get(aquifer_type, 6)


def rating_soil(soil_type):
    mapping = {
        "thin_clay": 1, "clay": 3, "silty_clay": 4, "sandy_clay": 5,
        "silt": 6, "sandy_loam": 7, "sand": 9, "gravel": 10, "thin_gravel": 10
    }
    return mapping.get(soil_type, 5)


def rating_topography(slope_percent):
    if slope_percent < 2: return 10
    if slope_percent < 6: return 9
    if slope_percent < 12: return 5
    if slope_percent < 18: return 3
    return 1


def rating_vadose(vadose_type):
    mapping = {
        "confining_clay": 1, "silty_clay": 3, "shale": 2,
        "sandy_silt": 5, "sandstone": 6, "limestone": 6,
        "sand_gravel": 8, "karst": 10
    }
    return mapping.get(vadose_type, 6)


def rating_conductivity(k_m_per_day):
    if k_m_per_day < 0.04: return 1
    if k_m_per_day < 0.4: return 2
    if k_m_per_day < 4: return 4
    if k_m_per_day < 12: return 6
    if k_m_per_day < 28: return 8
    return 10


def calculate_drastic_index(ratings):
    return round(sum(ratings[k] * WEIGHTS[k] for k in WEIGHTS), 1)


def drastic_to_percentage(index):
    return round((index / MAX_DRASTIC) * 100, 1)


def classify_risk(index):
    if index < 100: return ("🟢 منخفض", "low")
    if index < 140: return ("🟡 متوسط", "medium")
    if index < 180: return ("🟠 مرتفع", "high")
    return ("🔴 مرتفع جداً", "very_high")


def travel_time_darcy(depth_m, k_m_per_day, hydraulic_gradient=0.01, porosity=0.25):
    if k_m_per_day <= 0 or porosity <= 0:
        return float('inf')
    v = (k_m_per_day * hydraulic_gradient) / porosity
    days = depth_m / v
    return round(days / 365.25, 2)


def apply_mitigation(ratings, hdpe_liner=False, cyanide_treatment=False,
                     clay_cap=False, drainage=False):
    r = ratings.copy()
    if hdpe_liner:
        r["I"] = max(1, r["I"] - 4)
        r["C"] = max(1, r["C"] - 4)
    if clay_cap:
        r["S"] = max(1, r["S"] - 5)
        r["I"] = max(1, r["I"] - 2)
    if drainage:
        r["T"] = max(1, r["T"] - 3)
    return r


# ==========================================
# الجزء 2: مساعد AI (من ai_helper.py)
# ==========================================
CANDIDATE_MODELS = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]


def _get_api_key():
    try:
        return st.secrets["GEMINI_API_KEY"]
    except (KeyError, FileNotFoundError):
        return None


def generate_report(prompt, session_key, spinner_msg="جاري التوليد..."):
    api_key = _get_api_key()
    if not api_key:
        st.warning("⚠️ لم يتم العثور على GEMINI_API_KEY في Secrets.")
        return False

    try:
        from google import genai
    except ImportError:
        st.error("مكتبة `google-genai` غير مثبتة. أضفها في requirements.txt")
        return False

    client = genai.Client(api_key=api_key)
    errors = []

    with st.spinner(spinner_msg):
        for model_name in CANDIDATE_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name, contents=prompt,
                )
                st.session_state[session_key] = response.text
                st.success(f"✅ تم التوليد باستخدام `{model_name}`")
                return True
            except Exception as e:
                errors.append(f"{model_name}: {str(e)[:120]}")
                continue

    st.error("فشل جميع النماذج. التفاصيل:\n" + "\n".join(errors))
    return False


# ==========================================
# الجزء 3: التطبيق الرئيسي (من app.py)
# ==========================================
st.set_page_config(
    page_title="نظام DRASTIC لتقييم التعدين",
    page_icon="⛏️", layout="wide"
)

st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #d4af37;
        border-radius: 10px;
        padding: 12px;
    }
    .section-header {
        color: #5c2c16;
        border-bottom: 2px solid #c19a6b;
        padding-bottom: 5px;
        margin-bottom: 15px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image(
        "https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png",
        width=90
    )
with col_title:
    st.markdown("<h2 style='color: #5c2c16; margin-bottom:0;'>جامعة الخرطوم — كلية الهندسة</h2>",
                unsafe_allow_html=True)
    st.markdown(
        f"<h4 style='color: #c19a6b; margin-top:0;'>نظام التقييم البيئي (DRASTIC — US EPA | MAX={int(MAX_DRASTIC)})</h4>",
        unsafe_allow_html=True
    )

st.markdown("---")

preset_locations = {
    "سوق طواحين أبو حمد (نهر النيل)": {"coords": (19.5333, 33.3167), "depth": 15.0, "cyanide": 0.45, "recharge_mm": 60, "slope": 4, "k_m_day": 2.0},
    "عطبرة - النيل الكبرى": {"coords": (17.6833, 33.9833), "depth": 8.0, "cyanide": 0.80, "recharge_mm": 80, "slope": 3, "k_m_day": 5.0},
    "سوق العبيدية": {"coords": (18.1234, 33.9876), "depth": 10.0, "cyanide": 0.65, "recharge_mm": 70, "slope": 5, "k_m_day": 3.5},
    "مناجم بربر": {"coords": (18.0167, 33.9833), "depth": 12.0, "cyanide": 0.30, "recharge_mm": 55, "slope": 6, "k_m_day": 2.5},
    "وادي العشاري / قبقبة": {"coords": (21.8000, 34.5000), "depth": 45.0, "cyanide": 0.10, "recharge_mm": 20, "slope": 8, "k_m_day": 0.5},
    "مناجم أرياب (البحر الأحمر)": {"coords": (18.3333, 36.3500), "depth": 40.0, "cyanide": 0.05, "recharge_mm": 30, "slope": 10, "k_m_day": 0.3},
    "تلودي / الليري": {"coords": (10.6333, 30.1167), "depth": 18.0, "cyanide": 0.70, "recharge_mm": 90, "slope": 7, "k_m_day": 4.0},
    "كادوقلي": {"coords": (11.0167, 29.7167), "depth": 20.0, "cyanide": 0.20, "recharge_mm": 75, "slope": 5, "k_m_day": 2.0}
}

defaults = {
    "selected_site_name": "سوق طواحين أبو حمد (نهر النيل)",
    "lat": 19.5333, "lon": 33.3167,
    "depth": 15.0, "cyanide": 0.45,
    "recharge_mm": 60, "slope": 4, "k_m_day": 2.0,
    "ai_report_text": "", "bulk_ai_report": "",
    "flash_message": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.flash_message:
    st.success(st.session_state.flash_message)
    st.session_state.flash_message = None


def on_preset_change():
    site = st.session_state.preset_select
    data = preset_locations[site]
    st.session_state.selected_site_name = site
    st.session_state.lat = data["coords"][0]
    st.session_state.lon = data["coords"][1]
    st.session_state.depth = data["depth"]
    st.session_state.cyanide = data["cyanide"]
    st.session_state.recharge_mm = data["recharge_mm"]
    st.session_state.slope = data["slope"]
    st.session_state.k_m_day = data["k_m_day"]
    st.session_state.ai_report_text = ""


tab1, tab2, tab3 = st.tabs([
    "📍 التقييم الفردي",
    "📊 التقييم الجماعي (Bulk)",
    "🛡️ محاكاة الحلول الهندسية"
])

# ---------- TAB 1 ----------
with tab1:
    col_input, col_display = st.columns([1, 2])

    with col_input:
        st.markdown("<h4 class='section-header'>🔍 اختيار الموقع</h4>", unsafe_allow_html=True)
        st.selectbox("مناطق جاهزة:", list(preset_locations.keys()),
                     key="preset_select", on_change=on_preset_change)

        custom_search = st.text_input("أو ابحث باسم مدينة/منجم:", placeholder="Berber")
        if st.button("🔍 بحث", use_container_width=True):
            query_str = custom_search.strip()
            if query_str:
                with st.spinner("جاري البحث..."):
                    try:
                        geolocator = Nominatim(user_agent="uofk_drastic_v2")
                        q = f"{query_str}, Sudan" if "sudan" not in query_str.lower() else query_str
                        loc = geolocator.geocode(q, timeout=10)
                        if loc:
                            st.session_state.lat = loc.latitude
                            st.session_state.lon = loc.longitude
                            st.session_state.selected_site_name = query_str
                            st.session_state.ai_report_text = ""
                            st.session_state.flash_message = f"✅ تم العثور على: {loc.address.split(',')[0]}"
                            st.rerun()
                        else:
                            st.warning("لم يتم العثور على الموقع.")
                    except Exception as e:
                        st.error(f"خطأ في البحث: {e}")

        st.markdown("---")
        st.markdown("<h4 class='section-header'>⚙️ مدخلات DRASTIC</h4>", unsafe_allow_html=True)

        lat_val = st.number_input("خط العرض:", value=st.session_state.lat,
                                  min_value=-90.0, max_value=90.0, format="%.4f")
        lon_val = st.number_input("خط الطول:", value=st.session_state.lon,
                                  min_value=-180.0, max_value=180.0, format="%.4f")

        depth = st.slider("1. عمق المياه D (متر):", 0.5, 60.0,
                          value=float(st.session_state.depth), step=0.5)
        r_D = rating_depth(depth)

        recharge = st.slider("2. التغذية السنوية R (مم/سنة):", 0, 300,
                             value=int(st.session_state.recharge_mm), step=5)
        r_R = rating_recharge(recharge)

        aquifer_map = {
            "صخور صماء / بازلت": "basalt",
            "حجر رملي": "bedded_sandstone",
            "حصى ورمل مشبع": "sand_and_gravel",
            "حجر جيري كارستي": "karst_limestone"
        }
        aquifer_label = st.selectbox("3. نوع الخزان A:", list(aquifer_map.keys()))
        r_A = rating_aquifer(aquifer_map[aquifer_label])

        soil_map = {
            "طين عازل": "clay", "سلت / طمي": "silt",
            "رملية": "sand", "حصى": "gravel"
        }
        soil_label = st.selectbox("4. التربة السطحية S:", list(soil_map.keys()))
        r_S = rating_soil(soil_map[soil_label])

        topo = st.slider("5. الانحدار T (%):", 0, 30, value=int(st.session_state.slope))
        r_T = rating_topography(topo)

        vadose_map = {
            "طبقات طينية": "confining_clay", "حجر رملي / متشقق": "sandstone",
            "حصى ورمل نفاذ": "sand_gravel", "كارست": "karst"
        }
        vadose_label = st.selectbox("6. المنطقة غير المشبعة I:", list(vadose_map.keys()))
        r_I = rating_vadose(vadose_map[vadose_label])

        k_value = st.slider("7. النفاذية C (متر/يوم):", 0.01, 30.0,
                            value=float(st.session_state.k_m_day), step=0.1)
        r_C = rating_conductivity(k_value)

        st.markdown("---")
        st.markdown("<h4 class='section-header'>🧪 الملوثات</h4>", unsafe_allow_html=True)
        river_dist = st.slider("البعد عن مجرى مائي (م):", 50, 5000, 300, step=50)
        cyanide = st.slider(f"تركيز السيانيد (mg/L) — حد WHO = {WHO_CYANIDE_LIMIT}",
                            0.0, 2.00, value=float(st.session_state.cyanide), step=0.01)

        ratings = {"D": r_D, "R": r_R, "A": r_A, "S": r_S,
                   "T": r_T, "I": r_I, "C": r_C}
        drastic_index = calculate_drastic_index(ratings)
        risk_score = drastic_to_percentage(drastic_index)
        risk_label, risk_level = classify_risk(drastic_index)
        years = travel_time_darcy(depth, k_value)

    with col_display:
        st.markdown(f"<h4 class='section-header'>📊 النتائج: {st.session_state.selected_site_name}</h4>",
                    unsafe_allow_html=True)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("DRASTIC", f"{drastic_index} / {int(MAX_DRASTIC)}")
        k2.metric("نسبة الخطر", f"{risk_score}%", delta=risk_label)
        k3.metric("زمن وصول التسرب", f"{years} سنة" if years != float('inf') else "—")
        cyan_delta = "⚠️ يتجاوز" if cyanide > WHO_CYANIDE_LIMIT else "✅ آمن"
        k4.metric("السيانيد", f"{cyanide:.2f} mg/L", delta=cyan_delta,
                  delta_color="inverse" if cyanide > WHO_CYANIDE_LIMIT else "normal")

        with st.expander("🔬 تفاصيل Ratings"):
            ratings_df = pd.DataFrame([
                {"المعامل": k, "Rating": ratings[k], "الوزن": WEIGHTS[k],
                 "المساهمة": ratings[k] * WEIGHTS[k]}
                for k in ratings
            ])
            st.dataframe(ratings_df, use_container_width=True, hide_index=True)

        m = folium.Map(
            location=[lat_val, lon_val], zoom_start=13,
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri"
        )
        color_map = {"low": "green", "medium": "orange",
                     "high": "red", "very_high": "darkred"}
        marker_color = color_map[risk_level]
        folium.Marker([lat_val, lon_val],
                      popup=f"{st.session_state.selected_site_name}<br>DRASTIC: {drastic_index}",
                      icon=folium.Icon(color=marker_color, icon="warning")).add_to(m)
        folium.Circle([lat_val, lon_val], radius=river_dist,
                      color=marker_color, fill=True, fill_opacity=0.2).add_to(m)
        st_folium(m, width="100%", height=350, key="sat_map")

        st.markdown("---")
        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            if st.button("✨ توليد التقرير", type="primary", use_container_width=True):
                prompt = f"""بصفتك خبيراً استشارياً في هيدروجيولوجيا التعدين بجامعة الخرطوم، أعدّ تقريراً هندسياً متكاملاً للموقع: {st.session_state.selected_site_name}.
المعطيات:
- مؤشر DRASTIC: {drastic_index}/{int(MAX_DRASTIC)} (نسبة الخطر: {risk_score}%)
- التصنيف: {risk_label}
- Ratings: {ratings}
- عمق المياه: {depth} م | التغذية: {recharge} مم/سنة | الانحدار: {topo}%
- النفاذية: {k_value} م/يوم | السيانيد: {cyanide} mg/L (حد WHO = {WHO_CYANIDE_LIMIT})
- زمن وصول التسرب (Darcy): {years} سنة

اكتب التقرير بالعربية مع:
1. التقييم الهيدروجيولوجي الشامل
2. تحليل انتشار السيانيد وأثره
3. توصيات هندسية عاجلة
"""
                generate_report(prompt, "ai_report_text")

        if st.session_state.ai_report_text:
            st.markdown("##### 📄 التقرير:")
            st.info(st.session_state.ai_report_text)

        today = datetime.date.today().isoformat()
        export_doc = f"""جامعة الخرطوم — تقرير DRASTIC
================================================
التاريخ: {today}
الموقع: {st.session_state.selected_site_name}
الإحداثيات: {lat_val:.4f}, {lon_val:.4f}
DRASTIC: {drastic_index}/{int(MAX_DRASTIC)}
Risk: {risk_score}% ({risk_label})
Travel Time: {years} سنة
Cyanide: {cyanide} mg/L (WHO: {WHO_CYANIDE_LIMIT})
Ratings: {ratings}
================================================
{st.session_state.ai_report_text}"""

        with col_btn2:
            st.download_button("📥 تصدير التقرير", data=export_doc,
                               file_name=f"DRASTIC_{st.session_state.selected_site_name}.txt",
                               mime="text/plain", use_container_width=True)

# ---------- TAB 2 ----------
with tab2:
    st.markdown("<h4 class='section-header'>📤 التقييم الجماعي (Bulk)</h4>", unsafe_allow_html=True)
    st.caption("الأعمدة المطلوبة: Site, Latitude, Longitude, Cyanide + Ratings (D,R,A,S,T,I,C)")

    uploaded_file = st.file_uploader("ارفع Excel/CSV:", type=["xlsx", "csv"])

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') \
                else pd.read_excel(uploaded_file)

            lat_col = next((c for c in df.columns if c.lower() in ['latitude','lat','خط_العرض']), None)
            lon_col = next((c for c in df.columns if c.lower() in ['longitude','lon','long','خط_الطول']), None)
            cy_col = next((c for c in df.columns if c.lower() in ['cyanide','cn','السيانيد']), None)
            name_col = next((c for c in df.columns if c.lower() in ['site','name','location','اسم_الموقع']), None)

            rating_cols = {}
            for key in ['D','R','A','S','T','I','C']:
                col = next((c for c in df.columns if c.upper() == key), None)
                if col: rating_cols[key] = col

            if not (lat_col and lon_col and len(rating_cols) == 7):
                st.error("⚠️ يجب وجود: Latitude, Longitude + كل Ratings (D,R,A,S,T,I,C)")
            else:
                def calc_row(row):
                    r = {k: float(row[v]) for k, v in rating_cols.items()}
                    idx = calculate_drastic_index(r)
                    return pd.Series({"DRASTIC": idx,
                                      "Risk_%": drastic_to_percentage(idx),
                                      "Risk_Level": classify_risk(idx)[0]})
                df = pd.concat([df, df.apply(calc_row, axis=1)], axis=1)

                m1, m2, m3 = st.columns(3)
                m1.metric("عدد المواقع", len(df))
                m2.metric("مواقع شديدة الخطورة", len(df[df["DRASTIC"] >= 180]))
                m3.metric("متوسط DRASTIC", round(df["DRASTIC"].mean(), 1))

                col_tbl, col_heat = st.columns([1, 1])
                with col_tbl:
                    st.dataframe(df, use_container_width=True, height=400)
                    st.download_button("📥 تنزيل CSV",
                                       df.to_csv(index=False).encode('utf-8-sig'),
                                       "Evaluated_Sites.csv", "text/csv")

                with col_heat:
                    m_heat = folium.Map(
                        location=[df[lat_col].mean(), df[lon_col].mean()], zoom_start=6,
                        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                        attr="Esri"
                    )
                    weight_col = cy_col if cy_col else "DRASTIC"
                    heat_data = [[r[lat_col], r[lon_col], float(r[weight_col])]
                                 for _, r in df.iterrows()]
                    HeatMap(heat_data, radius=18).add_to(m_heat)
                    for _, r in df.iterrows():
                        _, lvl = classify_risk(r["DRASTIC"])
                        c = {"low":"green","medium":"orange","high":"red","very_high":"darkred"}[lvl]
                        title = r[name_col] if name_col else "موقع"
                        folium.CircleMarker([r[lat_col], r[lon_col]], radius=6,
                                            popup=f"{title}<br>DRASTIC: {r['DRASTIC']}",
                                            color=c, fill=True).add_to(m_heat)
                    st_folium(m_heat, width="100%", height=400, key="bulk_map")

                st.markdown("---")
                if st.button("✨ توليد التقرير الجماعي", type="primary", use_container_width=True):
                    summary = f"""- عدد المواقع: {len(df)}
- متوسط DRASTIC: {round(df['DRASTIC'].mean(),1)}
- أعلى مؤشر: {df['DRASTIC'].max()}
- مواقع ≥180: {len(df[df['DRASTIC'] >= 180])}"""
                    prompt = f"بصفتك المستشار البيئي لجامعة الخرطوم، اكتب تقريراً تنفيذياً موجزاً:\n{summary}\nالمطلوب: ملخص تنفيذي + أولويات + خطة استجابة."
                    generate_report(prompt, "bulk_ai_report")

                if st.session_state.bulk_ai_report:
                    st.info(st.session_state.bulk_ai_report)
                    st.download_button("📥 تصدير التقرير", st.session_state.bulk_ai_report,
                                       "Bulk_Report.txt", "text/plain")
        except Exception as e:
            st.error(f"خطأ في الملف: {e}")

# ---------- TAB 3 ----------
with tab3:
    st.markdown("<h4 class='section-header'>🛡️ محاكاة الحلول الهندسية</h4>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("الوضع الحالي")
        st.metric("DRASTIC", f"{drastic_index}/{int(MAX_DRASTIC)}")
        st.metric("نسبة الخطر", f"{risk_score}%")
        st.info(f"Ratings: {ratings}")

    with c2:
        st.subheader("بعد التطبيق")
        liner = st.checkbox("بطانة HDPE")
        clay_cap = st.checkbox("غطاء طيني")
        drainage = st.checkbox("نظام صرف")
        treatment = st.checkbox("معالجة السيانيد")

        mitigated = apply_mitigation(ratings, hdpe_liner=liner,
                                     cyanide_treatment=treatment,
                                     clay_cap=clay_cap, drainage=drainage)
        new_idx = calculate_drastic_index(mitigated)
        new_risk = drastic_to_percentage(new_idx)
        new_label, _ = classify_risk(new_idx)
        reduction = round(((drastic_index - new_idx) / drastic_index) * 100, 1) \
            if drastic_index > 0 else 0

        st.metric("DRASTIC الجديد", f"{new_idx}/{int(MAX_DRASTIC)}",
                  delta=f"-{round(drastic_index - new_idx, 1)}")
        st.metric("نسبة الخطر الجديدة", f"{new_risk}%", delta=new_label)
        st.metric("نسبة خفض الخطر", f"{reduction}%")
        st.info(f"Ratings بعد التطبيق: {mitigated}")
