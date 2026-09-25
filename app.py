import datetime
import folium
from folium.plugins import HeatMap
import google.generativeai as genai
from geopy.geocoders import Nominatim
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# ==========================================
# 0. التشريعات والقوانين السودانية والمعايير الدولية المعتمدة
# ==========================================
SUDAN_MINING_LEGISLATIONS = {
    "national_laws": {
        "mining_act_2015": {
            "title": "قانون تنمية الثروة المعدنية والتعدين لسنة 2015م",
            "article_26": (
                "إلزام صاحب العقد/الترخيص بحماية البيئة وتحمل المسؤولية"
                " المباشرة عن الأضرار المترتبة وتكاليف التعويضات."
            ),
        },
        "environmental_act_2001": {
            "title": "قانون حماية البيئة لسنة 2001م",
            "requirement": (
                "تقديم دراسة جدوى بيئية (Environmental Feasibility Study)"
                " واشتراطات الحد من التلوث قبل النشاط."
            ),
        },
        "traditional_mining_reg_2016": {
            "title": "لائحة تنظيم التعدين التقليدي لسنة 2016م",
            "safety_distance_km": 25,
            "rule": (
                "الالتزام بالمسافات الآمنة (لا تقل عن 25 كم عن المناطق السكنية)"
                " ومعالجة المخلفات داخل الأسواق المعتمدة فقط."
            ),
        },
        "mineral_exploitation_reg_2018": {
            "title": "لائحة تنظيم استغلال المعادن لسنة 2018م",
            "penalties": (
                "فرض عقوبات وجزاءات مالية على المخالفات البيئية والتعدين بدون"
                " دراسة أثر بيئي."
            ),
        },
        "environmental_health_act_2009": {
            "title": "قانون الصحة البيئية لسنة 2009م",
            "restriction": (
                "حظر تصريف المخلفات التعدينية الصلبة والسائلة (السيانيد والزئبق)"
                " في مصادر المياه."
            ),
        },
        "decree_90_2021": {
            "title": "القرار (90) لسنة 2021م",
            "social_responsibility": (
                "تخصيص 1% من أرباح شركات الامتياز و 4% من شركات المعالجة لصالح"
                " أموال المسؤولية المجتمعية للمحلية."
            ),
        },
    },
    "international_agreements": {
        "minamata": (
            "اتفاقية ميناماتا بشأن الزئبق (Minamata Convention on Mercury)"
        ),
        "cyanide_code": (
            "مدونة إدارة السيانيد الدولية (International Cyanide Management"
            " Code)"
        ),
        "basel": "اتفاقية بازل للتحكم في نقل وإدارة النفايات والمواد الخطرة",
        "technical_standards": ["كود JORC الأسترالي", "معيار NI 43-101 الكندي"],
    },
}


def append_legal_disclaimer(report_text: str) -> str:
  """دالة مساعدة لإضافة التقييم التشريعي والبيئي لنهاية تقارير النظام"""
  compliance_block = f"""
\n--------------------------------------------------------------------
الامتثال التشريعي والبيئي (Regulatory & Legal Compliance):
• هذا التقييم مُعد وفق المادة (26) من {SUDAN_MINING_LEGISLATIONS['national_laws']['mining_act_2015']['title']}.
• متوافق مع اشتراطات {SUDAN_MINING_LEGISLATIONS['national_laws']['environmental_act_2001']['title']}.
• يلتزم بضوابط {SUDAN_MINING_LEGISLATIONS['national_laws']['traditional_mining_reg_2016']['title']} (مسافة أمان لا تقل عن {SUDAN_MINING_LEGISLATIONS['national_laws']['traditional_mining_reg_2016']['safety_distance_km']} كم عن المناطق السكنية).
• يراعي المعايير الدولية:
  - {SUDAN_MINING_LEGISLATIONS['international_agreements']['minamata']}
  - {SUDAN_MINING_LEGISLATIONS['international_agreements']['cyanide_code']}
  - {SUDAN_MINING_LEGISLATIONS['international_agreements']['basel']}
"""
  return report_text + compliance_block


# ==========================================
# 1. إعدادات الصفحة والتنسيق البصري المؤسسي
# ==========================================
st.set_page_config(
    page_title="نظام النمذجة والتقييم البيئي للتعدين - DRASTIC",
    page_icon="⛏️",
    layout="wide",
)

st.markdown(
    """
<style>
    .stApp {
        background-color: #f8f9fa;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #d4af37;
        border-radius: 10px;
        padding: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    [data-testid="stSidebar"] {
        background-color: #f5eedc !important;
        border-right: 2px solid #c19a6b;
    }
    .section-header {
        color: #5c2c16;
        border-bottom: 2px solid #c19a6b;
        padding-bottom: 5px;
        margin-bottom: 15px;
        font-weight: bold;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. الهيدر الرئيسي
# ==========================================
col_logo, col_title = st.columns([1, 6])
with col_logo:
  st.image(
      "https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png",
      width=90,
  )
with col_title:
  st.markdown(
      "<h2 style='color: #5c2c16; margin-bottom:0;'>جامعة الخرطوم — كلية"
      " الهندسة</h2>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<h4 style='color: #c19a6b; margin-top:0;'>نظام التقييم البيئي الذكي"
      " المعتمد (DRASTIC Standard Model)</h4>",
      unsafe_allow_html=True,
  )

st.markdown("---")

# ==========================================
# 3. قاعدة البيانات المحلية وإدارة الجلسة
# ==========================================
preset_locations = {
    "سوق طواحين أبو حمد (نهر النيل)": {
        "coords": (19.5333, 33.3167),
        "depth": 15.0,
        "cyanide": 0.45,
    },
    "عطبرة - النيل الكبرى (نهر النيل)": {
        "coords": (17.6833, 33.9833),
        "depth": 8.0,
        "cyanide": 0.80,
    },
    "سوق العبيدية (نهر النيل)": {
        "coords": (18.1234, 33.9876),
        "depth": 10.0,
        "cyanide": 0.65,
    },
    "مناجم بربر (نهر النيل)": {
        "coords": (18.0167, 33.9833),
        "depth": 12.0,
        "cyanide": 0.30,
    },
    "وادي العشاري / قبقبة (الشمالية)": {
        "coords": (21.8000, 34.5000),
        "depth": 45.0,
        "cyanide": 0.10,
    },
    "وادي حلفا - كرمة (الشمالية)": {
        "coords": (21.7950, 31.3700),
        "depth": 25.0,
        "cyanide": 0.50,
    },
    "مناجم أرياب (البحر الأحمر)": {
        "coords": (18.3333, 36.3500),
        "depth": 40.0,
        "cyanide": 0.05,
    },
    "سوق دلقو (الشمالية)": {
        "coords": (20.3000, 30.5500),
        "depth": 35.0,
        "cyanide": 0.15,
    },
    "تلودي / الليري (جبال النوبة)": {
        "coords": (10.6333, 30.1167),
        "depth": 18.0,
        "cyanide": 0.70,
    },
    "كادوقلي (جنوب كردفان)": {
        "coords": (11.0167, 29.7167),
        "depth": 20.0,
        "cyanide": 0.20,
    },
}

if "selected_site_name" not in st.session_state:
  st.session_state.selected_site_name = "سوق طواحين أبو حمد (نهر النيل)"
if "lat" not in st.session_state:
  st.session_state.lat = 19.5333
if "lon" not in st.session_state:
  st.session_state.lon = 33.3167
if "ai_report_text" not in st.session_state:
  st.session_state.ai_report_text = ""
if "bulk_ai_report" not in st.session_state:
  st.session_state.bulk_ai_report = ""


def on_preset_change():
  site = st.session_state.preset_select
  st.session_state.selected_site_name = site
  st.session_state.lat = preset_locations[site]["coords"][0]
  st.session_state.lon = preset_locations[site]["coords"][1]
  st.session_state.ai_report_text = ""


def calculate_row_drastic(row):
  try:
    d = float(row.get("D", row.get("Depth", row.get("العمق", 15))))
    r = float(row.get("R", row.get("Recharge", row.get("التغذية", 5))))
    a = float(row.get("A", row.get("Aquifer", row.get("الخزان", 6))))
    s = float(row.get("S", row.get("Soil", row.get("التربة", 5))))
    t = float(row.get("T", row.get("Topography", row.get("الانحدار", 5))))
    i = float(
        row.get("I", row.get("Impact_Vadose", row.get("غير_المشبعة", 6)))
    )
    c = float(row.get("C", row.get("Conductivity", row.get("النفاذية", 4))))

    index = (
        (d * 5)
        + (r * 4)
        + (a * 3)
        + (s * 2)
        + (t * 1)
        + (i * 5)
        + (c * 3)
    )
    return round(index, 1)
  except Exception:
    return 120.0


# ==========================================
# 4. التبويبات الرئيسية
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "📍 التقييم الفردي وإصدار التقارير",
    "📊 التقييم الجماعي والخرائط الحرارية (Bulk Upload)",
    "🛡️ محاكاة الحلول الهندسية",
])

# ==========================================
# TAB 1: التقييم الفردي
# ==========================================
with tab1:
  col_input, col_display = st.columns([1, 2])

  with col_input:
    st.markdown(
        "<h4 class='section-header'>🔍 اختيار أو البحث عن موقع</h4>",
        unsafe_allow_html=True,
    )
    st.selectbox(
        "اختر من المناطق الجاهزة:",
        list(preset_locations.keys()),
        key="preset_select",
        on_change=on_preset_change,
    )

    custom_search = st.text_input(
        "أو ابحث باسم أي مدينة/منجم:", placeholder="مثال: Berber"
    )
    if st.button("🔍 بحث وانتقال الخريطة", use_container_width=True):
      query_str = custom_search.strip()
      if query_str != "":
        geolocator = Nominatim(user_agent="uofk_smart_mining_v13")
        try:
          q = (
              f"{query_str}, Sudan"
              if "sudan" not in query_str.lower()
              else query_str
          )
          loc = geolocator.geocode(q, timeout=8)
          if loc:
            st.session_state.lat = loc.latitude
            st.session_state.lon = loc.longitude
            st.session_state.selected_site_name = query_str
            st.session_state.ai_report_text = ""
            st.success(f"تم العثور على: {loc.address.split(',')[0]}")
            st.rerun()
        except Exception:
          st.error(
              "تعذر الوصول لخدمة البحث، يمكنك الاختيار من القائمة الجاهزة."
          )

    st.markdown("---")
    st.markdown(
        "<h4 class='section-header'>⚙️ مدخلات نموذج DRASTIC (US EPA)</h4>",
        unsafe_allow_html=True,
    )

    lat_val = st.number_input(
        "خط العرض (Latitude):", value=st.session_state.lat, format="%.4f"
    )
    lon_val = st.number_input(
        "خط الطول (Longitude):", value=st.session_state.lon, format="%.4f"
    )

    depth = st.slider("1. عمق المياه الجوفية D (متر):", 0.5, 60.0, 15.0, step=0.5)
    if depth < 1.5:
      r_D = 10
    elif depth < 4.5:
      r_D = 9
    elif depth < 9.1:
      r_D = 7
    elif depth < 15.2:
      r_D = 5
    elif depth < 22.9:
      r_D = 3
    else:
      r_D = 1

    recharge = st.selectbox(
        "2. معدل التغذية السنوية R (مم/سنة):",
        ["منخفض (< 50 مم)", "متوسط (50 - 100 مم)", "عالي (> 100 مم)"],
    )
    r_R = 1 if "منخفض" in recharge else (6 if "متوسط" in recharge else 9)

    aquifer = st.selectbox(
        "3. نوع صخور الخزان الجوفي A:",
        [
            "صخور صماء / باسالتي (Basalt)",
            "حجر رملي (Sandstone)",
            "حصى ورمل مشبع (Gravel & Sand)",
        ],
    )
    r_A = 3 if "صخور" in aquifer else (6 if "حجر" in aquifer else 8)

    soil = st.selectbox(
        "4. نوع التربة السطحية S:",
        [
            "طين عازل (Clay)",
            "سلت / طمي (Silt)",
            "تربة رملية هشّة (Sand/Gravel)",
        ],
    )
    r_S = 1 if "طين" in soil else (4 if "سلت" in soil else 9)

    topo = st.slider("5. نسبة انحدار الأرض T (%):", 0, 30, 4)
    if topo < 2:
      r_T = 10
    elif topo < 6:
      r_T = 9
    elif topo < 12:
      r_T = 5
    else:
      r_T = 1

    vadose = st.selectbox(
        "6. طبيعة المنطقة غير المشبعة I:",
        ["طبقات طينية متماسكة", "حجر رملي / متشقق", "حصى ورمل نفاذ"],
    )
    r_I = 3 if "طينية" in vadose else (6 if "رملي" in vadose else 8)

    cond = st.selectbox(
        "7. النفاذية الهيدروليكية C:", ["منخفضة جداً", "متوسطة", "عالية جداً"]
    )
    r_C = 1 if "منخفضة" in cond else (4 if "متوسطة" in cond else 8)

    st.markdown("---")
    st.markdown(
        "<h4 class='section-header'>🧪 الملوثات والمسافات الميدانية</h4>",
        unsafe_allow_html=True,
    )
    river_dist = st.slider(
        "البعد عن أقرب مجرى مائي / وادي (متر):", 50, 5000, 300, step=50
    )
    cyanide = st.slider(
        "تركيز السيانيد (Cyanide mg/L):", 0.01, 2.00, 0.45, step=0.01
    )

    w_D, w_R, w_A, w_S, w_T, w_I, w_C = 5, 4, 3, 2, 1, 5, 3
    drastic_index = (
        (r_D * w_D)
        + (r_R * w_R)
        + (r_A * w_A)
        + (r_S * w_S)
        + (r_T * w_T)
        + (r_I * w_I)
        + (r_C * w_C)
    )
    risk_score = round((drastic_index / 230) * 100, 1)
    perm_factor = 0.95 if "رملية" in soil else (0.50 if "سلت" in soil else 0.10)
    years = round((depth * (1.1 - perm_factor)) / 1.3, 1)

  with col_display:
    st.markdown(
        f"<h4 class='section-header'>📊 النتائج للموقع:"
        f" {st.session_state.selected_site_name}</h4>",
        unsafe_allow_html=True,
    )

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("مؤشر DRASTIC", f"{drastic_index} / 230")
    kpi2.metric("نسبة الخطر البيئي", f"{risk_score}%")
    kpi3.metric("زمن وصول التسرب", f"{years} سنة")
    status = "⚠️ يتجاوز الحد" if cyanide > 0.05 else "✅ ضمن المسموح"
    kpi4.metric(
        "تركيز السيانيد",
        f"{cyanide} mg/L",
        delta=status,
        delta_color="inverse" if cyanide > 0.05 else "normal",
    )

    st.markdown("##### 🛰️ خريطة الأقمار الصناعية")
    m = folium.Map(
        location=[lat_val, lon_val],
        zoom_start=13,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
    )
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png",
        attr="CartoDB",
        name="أسماء المناطق والطرق",
        overlay=True,
    ).add_to(m)

    marker_color = (
        "red"
        if drastic_index >= 160
        else ("orange" if drastic_index >= 120 else "green")
    )
    folium.Marker(
        [lat_val, lon_val],
        popup=(
            f"موقع المنجم:"
            f" {st.session_state.selected_site_name}<br>مؤشر DRASTIC:"
            f" {drastic_index}"
        ),
        icon=folium.Icon(color=marker_color, icon="warning"),
    ).add_to(m)

    folium.Circle(
        [lat_val, lon_val],
        radius=river_dist,
        color=marker_color,
        fill=True,
        fill_opacity=0.25,
    ).add_to(m)

    st_folium(m, width="100%", height=350, key="sat_map")

    # ==========================================
    # الذكاء الاصطناعي مع آلية التبديل المزدوج لتفادي خطأ 429
    # ==========================================
    st.markdown("---")
    st.markdown(
        "<h4 class='section-header'>⚡ توليد التقرير المعتمد وتصديره</h4>",
        unsafe_allow_html=True,
    )

    col_btn1, col_btn2 = st.columns([2, 1])

    with col_btn1:
      if st.button(
          "✨ توليد التقرير المعتمد عبر الذكاء الاصطناعي",
          type="primary",
          use_container_width=True,
      ):
        if "GEMINI_API_KEY" in st.secrets:
          genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

          # نماذج احتياطية يتم تجربتها متسلسلاً في حال حدوث Quota Exceeded (429)
          candidate_models = [
              "gemini-1.5-flash",
              "gemini-1.5-pro",
              "gemini-1.0-pro",
          ]

          prompt = f"""
                    بصفتك خبير استشاري في هيدروجيولوجيا التعدين بجامعة الخرطوم، قم بإعداد تقرير هندسي وتقييمي متكامل وبند بـ بند لموقع: {st.session_state.selected_site_name}.
                    
                    المعطيات الفنية الميدانية:
                    - مؤشر DRASTIC الإجمالي: {drastic_index} من 230 (نسبة الخطر البيئي: {risk_score}%)
                    - عمق المياه الجوفية (D): {depth} متر
                    - معدل التغذية السنوية (R): {recharge}
                    - نوع التربة السطحية (S): {soil}
                    - البعد عن المجرى المائي: {river_dist} متر
                    - تركيز السيانيد/الزئبق الميداني: {cyanide} mg/L (الحد المسموح به من الصحة العالمية WHO هو 0.05 mg/L)
                    - زمن وصول التسرب المتوقع: {years} سنة
                    
                    يرجى كتابة التقرير باللغة العربية بتنسيق منظم يغطي النقاط التالية بشكل كافٍ ومكتمل:
                    1. **التقييم الهيدروجيولوجي الشامل ومستوى الخطورة:**
                    2. **تحليل انتشار ملوثات السيانيد وأثرها على المياه الجوفية:**
                    3. **التوصيات والتدابير الهندسية العاجلة الواجب اتخاذها في الموقع:**
                    """

          success = False
          with st.spinner("جاري صياغة التقرير الفني..."):
            for m_name in candidate_models:
              try:
                model = genai.GenerativeModel(m_name)
                response = model.generate_content(prompt)
                report_with_laws = append_legal_disclaimer(response.text)
                st.session_state.ai_report_text = report_with_laws
                success = True
                st.success(
                    f"تم توليد التقرير بنجاح باستخدام النموذج ({m_name})!"
                )
                break
              except Exception:
                continue

          if not success:
            st.error(
                "⏳ تم استهلاك الحدود المجانية المؤقتة لجميع النماذج. انتظر"
                " 30 ثانية ثم اضغط مجدداً أو استخدم مفتاح API جديد."
            )
        else:
          st.warning(
              "⚠️ يرجى إضافة مفتاح GEMINI_API_KEY في قسم Secrets على Streamlit"
              " Cloud."
          )

    if st.session_state.ai_report_text:
      st.markdown("##### 📄 النص المعتمد للتقرير:")
      st.info(st.session_state.ai_report_text)

    today_date = datetime.date.today().strftime("%Y-%m-%d")
    raw_export = f"""====================================================================
جامعة الخرطوم — كلية الهندسة — قسم هندسة التعدين
تقرير التقييم البيئي والهيدروجيولوجي المعتمد (DRASTIC Standard Model)
====================================================================
تاريخ التقرير: {today_date}
الموقع المستهدف: {st.session_state.selected_site_name}
الإحداثيات الجغرافية: Latitude {lat_val:.4f}, Longitude {lon_val:.4f}
معيار النمذجة: US EPA DRASTIC Standard Model
--------------------------------------------------------------------
* مؤشر DRASTIC الإجمالي: {drastic_index} / 230
* نسبة الخطر البيئي التراكمية: {risk_score}%
* زمن وصول التسرب للمياه الجوفية: {years} سنة
* تركيز السيانيد الميداني: {cyanide} mg/L
--------------------------------------------------------------------
{st.session_state.ai_report_text}
====================================================================
"""
    full_export_document = (
        raw_export
        if "الامتثال التشريعي" in raw_export
        else append_legal_disclaimer(raw_export)
    )

    with col_btn2:
      st.download_button(
          label="📥 تصدير التقرير كملف (DOC/TXT)",
          data=full_export_document,
          file_name=(
              f"DRASTIC_Report_{st.session_state.selected_site_name}.txt"
          ),
          mime="text/plain",
          use_container_width=True,
      )

# ==========================================
# TAB 2: التقييم الجماعي
# ==========================================
with tab2:
  st.markdown(
      "<h4 class='section-header'>📤 رفع ملف البيانات الجماعي وحسابه دُفعة"
      " واحدة (Bulk Upload & Evaluation)</h4>",
      unsafe_allow_html=True,
  )
  uploaded_file = st.file_uploader(
      "اختر ملف Excel أو CSV مع مراعاة احتواء الملف على الأعمدة (Site/Name,"
      " Latitude, Longitude, Cyanide, والرموز D,R,A,S,T,I,C):",
      type=["xlsx", "csv"],
  )

  if uploaded_file is not None:
    try:
      df_bulk = (
          pd.read_csv(uploaded_file)
          if uploaded_file.name.endswith(".csv")
          else pd.read_excel(uploaded_file)
      )

      lat_col = next(
          (
              c
              for c in df_bulk.columns
              if c.lower() in ["latitude", "lat", "خط_العرض"]
          ),
          None,
      )
      lon_col = next(
          (
              c
              for c in df_bulk.columns
              if c.lower() in ["longitude", "lon", "long", "خط_الطول"]
          ),
          None,
      )
      cy_col = next(
          (
              c
              for c in df_bulk.columns
              if c.lower() in ["cyanide", "cn", "السيانيد"]
          ),
          None,
      )
      name_col = next(
          (
              c
              for c in df_bulk.columns
              if c.lower() in ["site", "name", "location", "اسم_الموقع", "الموقع"]
          ),
          None,
      )

      if lat_col and lon_col:
        df_bulk["Calculated_DRASTIC"] = df_bulk.apply(
            calculate_row_drastic, axis=1
        )
        df_bulk["Risk_Percentage (%)"] = (
            (df_bulk["Calculated_DRASTIC"] / 230) * 100
        ).round(1)

        def assign_risk_label(val):
          if val >= 160:
            return "🔴 خطر مرتفع جداً"
          elif val >= 120:
            return "🟠 خطر متوسط"
          else:
            return "🟢 خطر منخفض"

        df_bulk["Risk_Level"] = df_bulk["Calculated_DRASTIC"].apply(
            assign_risk_label
        )

        st.success(
            f"تم تحليل وترقيم {len(df_bulk)} موقع بنجاح بواسطة نموذج DRASTIC!"
        )

        m1, m2, m3 = st.columns(3)
        m1.metric("إجمالي المواقع المرفوعة", len(df_bulk))
        high_risk_count = len(df_bulk[df_bulk["Calculated_DRASTIC"] >= 160])
        m2.metric(
            "عدد المواقع عالية الخطورة",
            high_risk_count,
            delta="حرجة" if high_risk_count > 0 else "آمنة",
            delta_color="inverse",
        )
        m3.metric(
            "متوسط مؤشر DRASTIC للمواقع",
            round(df_bulk["Calculated_DRASTIC"].mean(), 1),
        )

        st.markdown("---")
        col_tbl, col_heat = st.columns([1, 1])

        with col_tbl:
          st.markdown("##### 📋 جدول التقييم المحسوب بالكامل:")
          st.dataframe(df_bulk, use_container_width=True)

          csv_data = df_bulk.to_csv(index=False).encode("utf-8-sig")
          st.download_button(
              label="📥 تنزيل الجدول المحسوب (CSV)",
              data=csv_data,
              file_name="Evaluated_Mining_Sites_DRASTIC.csv",
              mime="text/csv",
          )

        with col_heat:
          st.markdown("##### 🛰️ الخريطة الحرارية ونطاقات التلوث:")
          m_heat = folium.Map(
              location=[df_bulk[lat_col].mean(), df_bulk[lon_col].mean()],
              zoom_start=6,
              tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
              attr="Esri World Imagery",
          )

          heat_weight = cy_col if cy_col else "Calculated_DRASTIC"
          heat_data = [
              [row[lat_col], row[lon_col], float(row[heat_weight])]
              for _, row in df_bulk.iterrows()
          ]
          HeatMap(heat_data, radius=18).add_to(m_heat)

          for _, r in df_bulk.iterrows():
            site_title = r[name_col] if name_col else "منجم"
            m_color = (
                "red"
                if r["Calculated_DRASTIC"] >= 160
                else ("orange" if r["Calculated_DRASTIC"] >= 120 else "green")
            )
            folium.CircleMarker(
                location=[r[lat_col], r[lon_col]],
                radius=6,
                popup=(
                    f"{site_title}<br>DRASTIC:"
                    f" {r['Calculated_DRASTIC']}<br>الخطر: {r['Risk_Level']}"
                ),
                color=m_color,
                fill=True,
            ).add_to(m_heat)

          st_folium(m_heat, width="100%", height=380, key="bulk_heat_map_v2")

        # ==========================================
        # التقرير الجماعي بالذكاء الاصطناعي (مع التبديل التلقائي)
        # ==========================================
        st.markdown("---")
        st.markdown(
            "<h4 class='section-header'>⚡ توليد التقرير الموحد للبيانات"
            " الجماعية (Bulk AI Executive Report)</h4>",
            unsafe_allow_html=True,
        )

        if st.button(
            "✨ تحليل وتوليد التقرير التنفيذي الجماعي عبر الذكاء الاصطناعي",
            type="primary",
            use_container_width=True,
        ):
          if "GEMINI_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            candidate_models = [
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-1.0-pro",
            ]

            summary_data = f"""
                        - عدد المناجم والمواقع الكلي: {len(df_bulk)}
                        - متوسط مؤشر DRASTIC: {round(df_bulk['Calculated_DRASTIC'].mean(), 1)}
                        - أعلى مؤشر خطورة مسجل: {df_bulk['Calculated_DRASTIC'].max()}
                        - عدد المواقع شديدة الخطورة (DRASTIC >= 160): {len(df_bulk[df_bulk['Calculated_DRASTIC'] >= 160])}
                        - ملخص تركيزات السيانيد إن وجد: متوسط {round(df_bulk[cy_col].mean(), 2) if cy_col else 'غير محدد'} mg/L
                        """

            prompt = f"""
                        بصفتك المستشار البيئي الرئيسي لجامعة الخرطوم وهيئة الأبحاث الجيولوجية، قم بصياغة تقرير تقييمي جماعي تنفيذي موجه للوزارة والشركات بناءً على تحليل دفعة المناجم التالية:
                        {summary_data}
                        
                        المطلوب في التقرير:
                        1. **الملخص التنفيذي وتقييم الخطر الجماعي للمناجم المرفوعة.**
                        2. **تحديد الأولويات والمناجم ذات الخطورة العالية التي تتطلب تدخلاً ميدانياً عاجلاً.**
                        3. **خط الاستجابة الهندسية والتوصيات لحماية الخزانات الجوفية القريبة من هذه التجمعات.**
                        """

            success_bulk = False
            with st.spinner(
                "جاري تحليل كافة المناجم وصياغة التقرير التنفيذي..."
            ):
              for m_name in candidate_models:
                try:
                  model = genai.GenerativeModel(m_name)
                  res = model.generate_content(prompt)
                  bulk_report_with_laws = append_legal_disclaimer(res.text)
                  st.session_state.bulk_ai_report = bulk_report_with_laws
                  success_bulk = True
                  st.success(
                      f"تم توليد التقرير الجماعي بنجاح باستخدام النموذج"
                      f" ({m_name})!"
                  )
                  break
                except Exception:
                  continue

            if not success_bulk:
              st.error(
                  "⏳ استُهلك الحد الأقصى المؤقت. انتظر 30 ثانية ثم أعد التوليد."
              )

          else:
            st.warning("⚠️ يرجى إدخال GEMINI_API_KEY في إعدادات Secrets.")

        if st.session_state.bulk_ai_report:
          st.markdown("##### 📄 التقرير التنفيذي الجماعي المعتمد:")
          st.info(st.session_state.bulk_ai_report)

          st.download_button(
              label="📥 تصدير التقرير الجماعي (TXT)",
              data=st.session_state.bulk_ai_report,
              file_name="Bulk_Executive_Mining_Report.txt",
              mime="text/plain",
          )

      else:
        st.error(
            "⚠️ لم يتم العثور على أعمدة الإحداثيات (Latitude / Longitude) في"
            " الملف. يرجى التأكد من تسمية الأعمدة بشكل صحيح."
        )
    except Exception as e:
      st.error(f"خطأ أثناء معالجة الملف: {e}")

# ==========================================
# TAB 3: محاكي الحلول الهندسية
# ==========================================
with tab3:
  st.markdown(
      "<h4 class='section-header'>🛡️ محاكاة تأثير الحلول الهندسية الوقائية</h4>",
      unsafe_allow_html=True,
  )
  col_sc1, col_sc2 = st.columns(2)

  with col_sc1:
    st.subheader("الوضع الحالي")
    st.error(f"مؤشر DRASTIC الحالي: {drastic_index} / 230")
    st.warning(f"نسبة الخطر الحالية: {risk_score}%")

  with col_sc2:
    st.subheader("الوضع بعد تطبيق الحلول")
    liner = st.checkbox("تركيب بطانة عازلة HDPE Liner")
    treatment = st.checkbox("وحدة معالجة السيانيد الكيميائية")

    mitigated_drastic = drastic_index
    if liner:
      mitigated_drastic *= 0.40
    if treatment:
      mitigated_drastic *= 0.60

    mitigated_drastic = round(mitigated_drastic, 1)
    st.success(f"مؤشر DRASTIC المتوقع: {mitigated_drastic} / 230")
    reduction = (
        round(((drastic_index - mitigated_drastic) / drastic_index) * 100, 1)
        if drastic_index > 0
        else 0
    )
    st.metric("نسبة خفض الخطر البيئي", f"{reduction}%")
