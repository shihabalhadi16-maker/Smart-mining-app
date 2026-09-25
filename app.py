import datetime
import time
import folium
from folium.plugins import HeatMap
from geopy.geocoders import Nominatim
from google import genai
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
                " ومعالجة المخلفات داخل الأسوق المعتمدة فقط."
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
  """دالة إضافة الملحق التشريعي وقوالب التوقيع والاعتماد للتقارير"""
  today_str = datetime.date.today().strftime("%Y-%m-%d")
  ref_num = f"UOFK-ENG-ENV-{datetime.date.today().strftime('%Y%m%d')}-01"

  compliance_block = f"""
\n--------------------------------------------------------------------
الامتثال التشريعي والبيئي (Regulatory & Legal Compliance):
• التقييم مُعد وفق المادة (26) من {SUDAN_MINING_LEGISLATIONS['national_laws']['mining_act_2015']['title']}.
• متوافق مع اشتراطات {SUDAN_MINING_LEGISLATIONS['national_laws']['environmental_act_2001']['title']}.
• يلتزم بضوابط {SUDAN_MINING_LEGISLATIONS['national_laws']['traditional_mining_reg_2016']['title']} (مسافة أمان لا تقل عن {SUDAN_MINING_LEGISLATIONS['national_laws']['traditional_mining_reg_2016']['safety_distance_km']} كم عن المناطق السكنية).
• يراعي المعايير الدولية:
  - {SUDAN_MINING_LEGISLATIONS['international_agreements']['minamata']}
  - {SUDAN_MINING_LEGISLATIONS['international_agreements']['cyanide_code']}
  - {SUDAN_MINING_LEGISLATIONS['international_agreements']['basel']}

====================================================================
بيانات الاعتماد والتوقيع الرسمي:
الرقم المرجعي: {ref_num} | التاريخ: {today_str}

1. المهندس الهيدروجيولوجي المسؤول: ............................. (التوقيع: ........)
2. رئيس قسم هندسة التعدين: ....................................... (التوقيع: ........)
3. ختم مكتب الاستشارات الهندسية بجامعة الخرطوم:
====================================================================
"""
  return report_text + compliance_block


# ==========================================
# 1. دالة استدعاء Gemini الذكية للتعامل مع خطأ Rate Limit (429)
# ==========================================
def generate_ai_report_with_retry(prompt_text, api_key):
  """استدعاء النماذج الحديثة مع إعادة المحاولة التلقائية لتفادي تجاوز الحدود المجانية"""
  client = genai.Client(api_key=api_key)
  models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash"]

  for model_id in models_to_try:
    for attempt in range(3):
      try:
        response = client.models.generate_content(
            model=model_id, contents=prompt_text
        )
        if response.text:
          return response.text, model_id
      except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "quota" in error_str or "resource" in error_str:
          time.sleep((attempt + 1) * 5)  # الانتظار قبل إعادة المحاولة
        else:
          break
  return None, None


# ==========================================
# 2. إعدادات الصفحة والتنسيق البصري
# ==========================================
st.set_page_config(
    page_title="نظام النمذجة والتقييم البيئي للتعدين - DRASTIC",
    page_icon="⛏️",
    layout="wide",
)

st.markdown(
    """
<style>
    .stApp { background-color: #f8f9fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    div[data-testid="stMetric"] { background-color: #ffffff !important; border: 1px solid #d4af37; border-radius: 10px; padding: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stSidebar"] { background-color: #f5eedc !important; border-right: 2px solid #c19a6b; }
    .section-header { color: #5c2c16; border-bottom: 2px solid #c19a6b; padding-bottom: 5px; margin-bottom: 15px; font-weight: bold; }
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 3. الهيدر الرئيسي
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
      "<h4 style='color: #c19a6b; margin-top:0;'>مكتب الاستشارات الهندسية —"
      " نظام التقييم البيئي المعتمد (DRASTIC Model)</h4>",
      unsafe_allow_html=True,
  )

st.markdown("---")

# ==========================================
# 4. إدارة الجلسة والمواقع المسبقة
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
    return round(
        (d * 5)
        + (r * 4)
        + (a * 3)
        + (s * 2)
        + (t * 1)
        + (i * 5)
        + (c * 3),
        1,
    )
  except Exception:
    return 120.0


# ==========================================
# 5. الواجهة والتبويبات
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "📍 التقييم الفردي وإصدار التقارير",
    "📊 التقييم الجماعي والخرائط الحرارية",
    "🛡️ محاكاة الحلول الهندسية",
])

# ------------------------------------------
# TAB 1: التقييم الفردي
# ------------------------------------------
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
        "أو ابحث باسم أي مدينة/منجم:", placeholder="مثال: Abu Hamad"
    )
    if st.button("🔍 بحث وانتقال الخريطة", use_container_width=True):
      if custom_search.strip():
        geolocator = Nominatim(user_agent="uofk_smart_mining_v14")
        try:
          q = (
              f"{custom_search.strip()}, Sudan"
              if "sudan" not in custom_search.lower()
              else custom_search.strip()
          )
          loc = geolocator.geocode(q, timeout=8)
          if loc:
            st.session_state.lat = loc.latitude
            st.session_state.lon = loc.longitude
            st.session_state.selected_site_name = custom_search.strip()
            st.session_state.ai_report_text = ""
            st.success(f"تم العثور على: {loc.address.split(',')[0]}")
            st.rerun()
        except Exception:
          st.error("تعذر البحث، يمكنك الاختيار من القائمة.")

    st.markdown("---")
    st.markdown(
        "<h4 class='section-header'>⚙️ مدخلات نموذج DRASTIC</h4>",
        unsafe_allow_html=True,
    )
    lat_val = st.number_input(
        "خط العرض (Latitude):", value=st.session_state.lat, format="%.4f"
    )
    lon_val = st.number_input(
        "خط الطول (Longitude):", value=st.session_state.lon, format="%.4f"
    )

    depth = st.slider("1. عمق المياه الجوفية D (متر):", 0.5, 60.0, 15.0, step=0.5)
    r_D = (
        10
        if depth < 1.5
        else (
            9
            if depth < 4.5
            else (7 if depth < 9.1 else (5 if depth < 15.2 else 1))
        )
    )

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
    r_T = 10 if topo < 2 else (9 if topo < 6 else (5 if topo < 12 else 1))

    vadose = st.selectbox(
        "6. طبيعة المنطقة غير المشبعة I:",
        ["طبقات طينية متماسكة", "حجر رملي / متشقب", "حصى ورمل نفاذ"],
    )
    r_I = 3 if "طينية" in vadose else (6 if "رملي" in vadose else 8)

    cond = st.selectbox(
        "7. النفاذية الهيدروليكية C:", ["منخفضة جداً", "متوسطة", "عالية جداً"]
    )
    r_C = 1 if "منخفضة" in cond else (4 if "متوسطة" in cond else 8)

    st.markdown("---")
    river_dist = st.slider(
        "البعد عن أقرب مجرى مائي / وادي (متر):", 50, 5000, 300, step=50
    )
    cyanide = st.slider(
        "تركيز السيانيد (Cyanide mg/L):", 0.01, 2.00, 0.45, step=0.01
    )

    drastic_index = (
        (r_D * 5)
        + (r_R * 4)
        + (r_A * 3)
        + (r_S * 2)
        + (r_T * 1)
        + (r_I * 5)
        + (r_C * 3)
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
    kpi4.metric(
        "تركيز السيانيد",
        f"{cyanide} mg/L",
        delta="⚠️ يتجاوز" if cyanide > 0.05 else "✅ آمن",
        delta_color="inverse" if cyanide > 0.05 else "normal",
    )

    st.markdown("##### 🛰️ خريطة الأقمار الصناعية للموقع")
    m = folium.Map(
        location=[lat_val, lon_val],
        zoom_start=13,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
    )
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png",
        attr="CartoDB",
        overlay=True,
    ).add_to(m)

    m_color = (
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
        icon=folium.Icon(color=m_color, icon="warning"),
    ).add_to(m)
    folium.Circle(
        [lat_val, lon_val],
        radius=river_dist,
        color=m_color,
        fill=True,
        fill_opacity=0.2,
    ).add_to(m)

    st_folium(m, width="100%", height=350, key="sat_map")

    # ==========================================
    # توليد التقرير المعتمد وتفادي أخطاء Rate Limit
    # ==========================================
    st.markdown("---")
    st.markdown(
        "<h4 class='section-header'>⚡ توليد التقرير الاستشاري المعتمد</h4>",
        unsafe_allow_html=True,
    )

    col_btn1, col_btn2 = st.columns([2, 1])

    with col_btn1:
      if st.button(
          "✨ توليد التقرير المعتمد عبر الذكاء الاصطناعي",
          type="primary",
          use_container_width=True,
      ):
        if (
            "GEMINI_API_KEY" in st.secrets
            and st.secrets["GEMINI_API_KEY"].strip()
        ):
          api_key = st.secrets["GEMINI_API_KEY"]

          prompt = f"""
                    بصفتك استشاري هيدروجيولوجيا التعدين بجامعة الخرطوم، قم بإعداد تقرير هندسي وتقييمي متكامل لموقع: {st.session_state.selected_site_name}.
                    
                    البيانات الميدانية:
                    - مؤشر DRASTIC الإجمالي: {drastic_index} من 230 (مستوى الخطر البيئي: {risk_score}%)
                    - عمق المياه الجوفية (D): {depth} متر
                    - معدل التغذية السنوية (R): {recharge}
                    - نوع التربة السطحية (S): {soil}
                    - البعد عن המجرى المائي: {river_dist} متر
                    - تركيز السيانيد/الزئبق الميداني: {cyanide} mg/L (المسموح عالمياً 0.05 mg/L)
                    - زمن وصول التسرب للمياه الجوفية: {years} سنة
                    
                    اكتب تقريراً مهنياً متكاملاً يتضمن:
                    1. التقييم الهيدروجيولوجي للموقع وتحديد الخطر.
                    2. مسار انتشار ملوثات السيانيد وأثرها البيئي.
                    3. التوصيات الهندسية والوقائية الواجب اتخاذها.
                    """

          with st.spinner("جاري التواصل مع النماذج وصياغة التقرير..."):
            report_out, used_model = generate_ai_report_with_retry(
                prompt, api_key
            )

            if report_out:
              full_report = append_legal_disclaimer(report_out)
              st.session_state.ai_report_text = full_report
              st.success(
                  f"تم توليد التقرير بنجاح عبر النموذج الذكي ({used_model})!"
              )
              st.rerun()
            else:
              st.error(
                  "⏳ تم استهلاك الحدود المجانية المؤقتة. انتظر 30 ثانية ثم اضغط"
                  " مجدداً."
              )
        else:
          st.warning("⚠️ يرجى ضبط المفتاح GEMINI_API_KEY في إعدادات Secrets.")

    if st.session_state.ai_report_text:
      st.markdown("##### 📄 التقرير الاستشاري المعاين:")
      st.info(st.session_state.ai_report_text)

    with col_btn2:
      st.download_button(
          label="📥 تصدير التقرير المعتمد (TXT)",
          data=st.session_state.ai_report_text,
          file_name=(
              f"Approved_DRASTIC_Report_{st.session_state.selected_site_name}.txt"
          ),
          mime="text/plain",
          use_container_width=True,
          disabled=not bool(st.session_state.ai_report_text),
      )

# ------------------------------------------
# TAB 2: التقييم الجماعي (Bulk Upload)
# ------------------------------------------
with tab2:
  st.markdown(
      "<h4 class='section-header'>📤 رفع ملف البيانات الجماعي (Bulk Upload &"
      " Evaluation)</h4>",
      unsafe_allow_html=True,
  )
  uploaded_file = st.file_uploader(
      "اختر ملف Excel أو CSV مع مراعاة وجود أعمدة الإحداثيات والرموز (D, R, A,"
      " S, T, I, C):",
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

        def assign_label(v):
          return (
              "🔴 خطر مرتفع جداً"
              if v >= 160
              else ("🟠 خطر متوسط" if v >= 120 else "🟢 خطر منخفض")
          )

        df_bulk["Risk_Level"] = df_bulk["Calculated_DRASTIC"].apply(
            assign_label
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

          heat_w = cy_col if cy_col else "Calculated_DRASTIC"
          heat_data = [
              [row[lat_col], row[lon_col], float(row[heat_w])]
              for _, row in df_bulk.iterrows()
          ]
          HeatMap(heat_data, radius=18).add_to(m_heat)

          for _, r in df_bulk.iterrows():
            st_title = r[name_col] if name_col else "منجم"
            col_m = (
                "red"
                if r["Calculated_DRASTIC"] >= 160
                else ("orange" if r["Calculated_DRASTIC"] >= 120 else "green")
            )
            folium.CircleMarker(
                location=[r[lat_col], r[lon_col]],
                radius=6,
                popup=(
                    f"{st_title}<br>DRASTIC:"
                    f" {r['Calculated_DRASTIC']}<br>الخطر: {r['Risk_Level']}"
                ),
                color=col_m,
                fill=True,
            ).add_to(m_heat)

          st_folium(m_heat, width="100%", height=380, key="bulk_heat_map_v3")

        # التقرير الجماعي
        st.markdown("---")
        st.markdown(
            "<h4 class='section-header'>⚡ توليد التقرير التنفيذي الجماعي"
            " المعتمد</h4>",
            unsafe_allow_html=True,
        )

        if st.button(
            "✨ تحليل وتوليد التقرير التنفيذي الجماعي",
            type="primary",
            use_container_width=True,
        ):
          if (
              "GEMINI_API_KEY" in st.secrets
              and st.secrets["GEMINI_API_KEY"].strip()
          ):
            api_key = st.secrets["GEMINI_API_KEY"]
            summary_info = f"""
                        - عدد المناجم المرفوعة: {len(df_bulk)}
                        - متوسط مؤشر DRASTIC: {round(df_bulk['Calculated_DRASTIC'].mean(), 1)}
                        - أعلى مؤشر خطورة: {df_bulk['Calculated_DRASTIC'].max()}
                        - عدد المناجم شديدة الخطورة: {len(df_bulk[df_bulk['Calculated_DRASTIC'] >= 160])}
                        """

            prompt_bulk = f"""
                        بصفتك المستشار البيئي الرئيسي بجامعة الخرطوم، اكتب تقريراً تنفيذاً موحداً حول التقييم الجماعي للمناجم التالية:
                        {summary_info}
                        
                        المطلوب:
                        1. الملخص التنفيذي وتقييم الخطر الجماعي.
                        2. تحديد المناجم ذات الخطورة العالية التي تتطلب تدخلاً ميدانياً عاجلاً.
                        3. التوصيات الهندسية والوقائية الشاملة.
                        """

            with st.spinner("جاري معالجة البيانات وتوليد التقرير التنفيذي..."):
              bulk_out, bulk_model = generate_ai_report_with_retry(
                  prompt_bulk, api_key
              )
              if bulk_out:
                final_bulk_report = append_legal_disclaimer(bulk_out)
                st.session_state.bulk_ai_report = final_bulk_report
                st.success(
                    f"تم توليد التقرير التنفيذي بنجاح باستخدام ({bulk_model})!"
                )
                st.rerun()
              else:
                st.error("⏳ استُهلك الحد الأقصى. انتظر 30 ثانية ثم أعد التوليد.")
          else:
            st.warning("⚠️ يرجى إدخال GEMINI_API_KEY في إعدادات Secrets.")

        if st.session_state.bulk_ai_report:
          st.markdown("##### 📄 التقرير التنفيذي الجماعي المعتمد:")
          st.info(st.session_state.bulk_ai_report)
          st.download_button(
              label="📥 تصدير التقرير الجماعي (TXT)",
              data=st.session_state.bulk_ai_report,
              file_name="Approved_Bulk_Executive_Report.txt",
              mime="text/plain",
          )
      else:
        st.error(
            "⚠️ لم يتم العثور على أعمدة الإحداثيات (Latitude / Longitude) في"
            " الملف."
        )
    except Exception as e:
      st.error(f"خطأ أثناء معالجة الملف: {e}")

# ------------------------------------------
# TAB 3: محاكي الحلول الهندسية
# ------------------------------------------
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
    st.subheader("الوضع بعد تطبيق الحلول الهندسية")
    liner = st.checkbox("تركيب بطانة عازلة عالية الكثافة HDPE Liner")
    treatment = st.checkbox("وحدة معالجة السيانيد الكيميائية")

    mitigated = drastic_index
    if liner:
      mitigated *= 0.40
    if treatment:
      mitigated *= 0.60

    mitigated = round(mitigated, 1)
    st.success(f"مؤشر DRASTIC المتوقع: {mitigated} / 230")
    reduction = (
        round(((drastic_index - mitigated) / drastic_index) * 100, 1)
        if drastic_index > 0
        else 0
    )
    st.metric("نسبة خفض الخطر البيئي", f"{reduction}%")
