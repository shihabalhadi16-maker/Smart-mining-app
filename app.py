import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
import google.generativeai as genai
from geopy.geocoders import Nominatim
import math

# ==========================================
# 1. إعدادات الصفحة والتنسيق البصري المؤسسي
# ==========================================
st.set_page_config(
    page_title="نظام النمذجة والتقييم البيئي للتعدين - المعتمد",
    page_icon="⛏️",
    layout="wide"
)

st.markdown("""
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
    .report-box {
        background-color: #ffffff;
        border-right: 4px solid #5c2c16;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# دالة تحويل UTM إلى Lat/Lon رياضياً بدون مكتبات خارجية
def utm_to_latlon(easting, northing, zone=36, northern_hemisphere=True):
    a = 6378137.0
    f = 1 / 298.257223563
    k0 = 0.9996
    e = math.sqrt(2 * f - f ** 2)
    e1sq = e ** 2 / (1 - e ** 2)
    
    x = easting - 500000.0
    y = northing if northern_hemisphere else northing - 10000000.0
    
    long0 = (zone - 1) * 6 - 180 + 3
    
    M = y / k0
    mu = M / (a * (1 - (e**2)/4 - 3*(e**4)/64 - 5*(e**6)/256))
    
    phi1 = mu + (3*e1sq/2 - 27*(e1sq**3)/32)*math.sin(2*mu) + (21*(e1sq**2)/16 - 55*(e1sq**4)/32)*math.sin(4*mu)
    
    N1 = a / math.sqrt(1 - (e * math.sin(phi1))**2)
    T1 = math.tan(phi1)**2
    C1 = e1sq * math.cos(phi1)**2
    R1 = a * (1 - e**2) / ((1 - (e * math.sin(phi1))**2)**1.5)
    D = x / (N1 * k0)
    
    lat = phi1 - (N1 * math.tan(phi1) / R1) * (D**2/2 - (5 + 3*T1 + 10*C1 - 4*C1**2 - 9*e1sq)*(D**4)/24 + (61 + 90*T1 + 298*C1 + 45*(T1**2) - 252*e1sq - 3*(C1**2))*(D**6)/720)
    lat = math.degrees(lat)
    
    lon = (D - (1 + 2*T1 + C1)*(D**3)/6 + (5 - 2*C1 + 28*T1 - 3*(C1**2) + 8*e1sq + 24*(T1**2))*(D**5)/120) / math.cos(phi1)
    lon = long0 + math.degrees(lon)
    
    return lat, lon

# ==========================================
# 2. الهيدر الرئيسي
# ==========================================
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/8/82/University_of_Khartoum_logo.png/220px-University_of_Khartoum_logo.png", width=90)
with col_title:
    st.markdown("<h2 style='color: #5c2c16; margin-bottom:0;'>جامعة الخرطوم — كلية الهندسة وقسم هندسة التعدين</h2>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #c19a6b; margin-top:0;'>نظام التقييم البيئي الذكي ونمذجة مخاطر التعدين (DRASTIC Model / USEPA Standards)</h4>", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 3. قاعدة البيانات المحلية للمناطق الشهيرة
# ==========================================
preset_locations = {
    "سوق طواحين أبو حمد (نهر النيل)": {"coords": (19.5333, 33.3167), "depth": 15, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.45, "mercury": 0.08},
    "عطبرة - النيل الكبرى (نهر النيل)": {"coords": (17.6833, 33.9833), "depth": 8, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.80, "mercury": 0.12},
    "سوق العبيدية (نهر النيل)": {"coords": (18.1234, 33.9876), "depth": 10, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.65, "mercury": 0.09},
    "مناجم بربر (نهر النيل)": {"coords": (18.0167, 33.9833), "depth": 12, "soil": "تربة طمية مختلطة (نفاذية متوسطة)", "cyanide": 0.30, "mercury": 0.04},
    "وادي العشاري / قبقبة (الشمالية)": {"coords": (21.8000, 34.5000), "depth": 60, "soil": "تربة صخرية صلبة (نفاذية منخفضة)", "cyanide": 0.10, "mercury": 0.02},
    "وادي حلفا - كرمة (الشمالية)": {"coords": (21.7950, 31.3700), "depth": 25, "soil": "تربة رملية هشّة (نفاذية عالية)", "cyanide": 0.50, "mercury": 0.06},
    "مناجم أرياب (البحر الأحمر)": {"coords": (18.3333, 36.3500), "depth": 45, "soil": "تربة صخرية صلبة (نفاذية منخفضة)", "cyanide": 0.05, "mercury": 0.01},
    "سوق دلقو (الشمالية)": {"coords": (20.3000, 30.5500), "depth": 35, "soil": "تربة صخرية صلبة (نفاذية منخفضة)", "cyanide": 0.15, "mercury": 0.03},
    "تلودي / الليري (جبال النوبة)": {"coords": (10.6333, 30.1167), "depth": 18, "soil": "تربة طمية مختلطة (نفاذية متوسطة)", "cyanide": 0.70, "mercury": 0.15},
    "كادوقلي (جنوب كردفان)": {"coords": (11.0167, 29.7167), "depth": 20, "soil": "تربة طمية مختلطة (نفاذية متوسطة)", "cyanide": 0.20, "mercury": 0.05}
}

if "selected_site_name" not in st.session_state:
    st.session_state.selected_site_name = "سوق طواحين أبو حمد (نهر النيل)"

if "lat" not in st.session_state:
    st.session_state.lat = 19.5333
if "lon" not in st.session_state:
    st.session_state.lon = 33.3167

def on_preset_change():
    site = st.session_state.preset_select
    st.session_state.selected_site_name = site
    st.session_state.lat = preset_locations[site]["coords"][0]
    st.session_state.lon = preset_locations[site]["coords"][1]

# ==========================================
# 4. التبويبات الرئيسية
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "📍 التقييم الفردي والتقرير الذكي",
    "📊 التقييم الجماعي والخرائط الحرارية (Bulk Upload)",
    "🛡️ محاكاة الحلول الهندسية"
])

# ==========================================
# TAB 1: التقييم الفردي
# ==========================================
with tab1:
    col_input, col_display = st.columns([1, 2])

    with col_input:
        st.markdown("<h4 class='section-header'>🔍 اختيار أو البحث عن موقع</h4>", unsafe_allow_html=True)
        
        coord_mode = st.radio("نظام الإدخال الإحداثي:", ["جغرافي (Lat/Lon) والبحث", "متري ميداني (UTM Zone 36N/37N)"], horizontal=True)
        
        if coord_mode == "جغرافي (Lat/Lon) والبحث":
            st.selectbox("اختر من المناطق الجاهزة:", list(preset_locations.keys()), key="preset_select", on_change=on_preset_change)
            
            custom_search = st.text_input("أو ابحث باسم أي مدينة/منجم:", placeholder="مثال: Port Sudan أو العبيدية")
            if st.button("🔍 بحث وانتقال الخريطة", use_container_width=True):
                query_str = custom_search.strip()
                if query_str != "":
                    found_in_preset = False
                    for name, data in preset_locations.items():
                        if query_str.lower() in name.lower():
                            st.session_state.lat = data["coords"][0]
                            st.session_state.lon = data["coords"][1]
                            st.session_state.selected_site_name = name
                            found_in_preset = True
                            st.success(f"تم العثور على: {name}")
                            st.rerun()
                            break
                    
                    if not found_in_preset:
                        geolocator = Nominatim(user_agent="uofk_smart_mining_v9")
                        try:
                            q = f"{query_str}, Sudan" if "sudan" not in query_str.lower() else query_str
                            loc = geolocator.geocode(q, timeout=8)
                            if loc:
                                st.session_state.lat = loc.latitude
                                st.session_state.lon = loc.longitude
                                st.session_state.selected_site_name = query_str
                                st.success(f"تم العثور على: {loc.address.split(',')[0]}")
                                st.rerun()
                            else:
                                st.warning("لم يتم العثور على الموقع، اختر موقعك من القائمة أعلاه.")
                        except Exception:
                            st.error("تنبيه: تعذر الوصول لخدمة البحث الخارجية حالياً.")

            lat_val = st.number_input("خط العرض (Latitude):", value=st.session_state.lat, format="%.5f")
            lon_val = st.number_input("خط الطول (Longitude):", value=st.session_state.lon, format="%.5f")
        else:
            utm_easting = st.number_input("Easting (X - متر):", value=533200.0)
            utm_northing = st.number_input("Northing (Y - متر):", value=2159800.0)
            utm_zone = st.selectbox("النطاق (UTM Zone):", [36, 37], index=0)
            try:
                lat_val, lon_val = utm_to_latlon(utm_easting, utm_northing, zone=utm_zone)
                st.info(f"تم التحويل الميداني: Lat {lat_val:.5f}, Lon {lon_val:.5f}")
            except Exception:
                lat_val, lon_val = st.session_state.lat, st.session_state.lon

        st.markdown("---")
        st.markdown("<h4 class='section-header'>⚙️ المعطيات الجيولوجية والملوثات</h4>", unsafe_allow_html=True)
        
        depth = st.slider("عمق المياه الجوفية (متر):", 2, 100, 15)
        river_dist = st.slider("البعد عن أقرب مجرى مائي / نيل (متر):", 50, 5000, 300, step=50)
        soil = st.selectbox("نوع التربة السطحية:", ["تربة رملية هشّة (نفاذية عالية)", "تربة طمية مختلطة (نفاذية متوسطة)", "تربة صخرية صلبة (نفاذية منخفضة)"])
        
        st.markdown("**تركيزات الملوثات التعدينية:**")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            cyanide = st.number_input("تركيز السيانيد (mg/L):", min_value=0.01, max_value=5.00, value=0.45, step=0.05)
        with col_m2:
            mercury = st.number_input("تركيز الزئبق (mg/L):", min_value=0.000, max_value=1.000, value=0.080, step=0.005)

        perm = 0.95 if "رملية" in soil else (0.50 if "طمية" in soil else 0.10)
        soil_rating = 9 if "رملية" in soil else (6 if "طمية" in soil else 2)
        d_rating = 10 if depth < 5 else (8 if depth < 15 else (5 if depth < 30 else 2))
        dist_rating = 10 if river_dist < 200 else (6 if river_dist < 1000 else 2)
        
        drastic_score = (d_rating * 5) + (soil_rating * 3) + (dist_rating * 4) + (cyanide * 10) + (mercury * 20)
        risk_score = round(min(max((drastic_score / 130.0) * 100, 5.0), 98.5), 1)
        years = round((depth * (1.1 - perm)) / 1.3, 1)

    with col_display:
        st.markdown(f"<h4 class='section-header'>📊 النتائج والتقييم للموقع: {st.session_state.selected_site_name}</h4>", unsafe_allow_html=True)
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            st.metric("مؤشر الخطر (DRASTIC)", f"{risk_score}%")
        with kpi2:
            st.metric("زمن وصول الملوثات", f"{years} سنة")
        with kpi3:
            c_status = "⚠️ يتجاوز" if cyanide > 0.05 else "✅ ضمن الحد"
            st.metric("السيانيد (CN)", f"{cyanide} mg/L", delta=c_status, delta_color="inverse" if cyanide > 0.05 else "normal")
        with kpi4:
            m_status = "⚠️ يتجاوز" if mercury > 0.006 else "✅ ضمن الحد"
            st.metric("الزئبق (Hg)", f"{mercury} mg/L", delta=m_status, delta_color="inverse" if mercury > 0.006 else "normal")

        st.markdown("##### 🛰️ خريطة الأقمار الصناعية ونطاق التأثير")
        
        m = folium.Map(
            location=[lat_val, lon_val], 
            zoom_start=13, 
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery"
        )
        
        folium.TileLayer(
            tiles="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png",
            attr="CartoDB",
            name="أسماء المناطق والطرق",
            overlay=True
        ).add_to(m)

        marker_color = "red" if risk_score >= 70 else ("orange" if risk_score >= 40 else "green")
        
        folium.Marker(
            [lat_val, lon_val],
            popup=f"موقع المنجم: {st.session_state.selected_site_name}<br>مؤشر الخطر: {risk_score}%",
            tooltip=st.session_state.selected_site_name,
            icon=folium.Icon(color=marker_color, icon="warning")
        ).add_to(m)
        
        folium.Circle(
            [lat_val, lon_val],
            radius=river_dist,
            color=marker_color,
            fill=True,
            fill_opacity=0.25,
            popup="نطاق التأثير الهيدروجيولوجي المتوقع"
        ).add_to(m)
        
        st_folium(m, width="100%", height=380, key="sat_map")

        st.markdown("---")
        st.markdown("<h4 class='section-header'>⚡ التقرير البيئي الاستشاري المعتمد</h4>", unsafe_allow_html=True)
        
        if st.button("✨ توليد تقرير فني فوري", type="primary", use_container_width=True):
            ai_generated = False
            generated_text = ""

            if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"] != "":
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    try:
                        model = genai.GenerativeModel('gemini-3.6-flash')
                    except Exception:
                        model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    prompt = f"""
                    أنت استشاري بيئي بهيئة الأبحاث الجيولوجية وجامعة الخرطوم. صغ تقريراً فنياً لموقع {st.session_state.selected_site_name}:
                    المعطيات: عمق المياه {depth}m، تربة {soil}، البعد عن المجرى المائي {river_dist}m، السيانيد {cyanide}mg/L، الزئبق {mercury}mg/L، مؤشر DRASTIC للخطورة {risk_score}%.
                    
                    صغ التقرير في 3 نقاط مركزة:
                    1. **التقييم الجيوهيدرولوجي والمخاطر:**
                    2. **الأثر البيئي والصحي المباشر:**
                    3. **التوصيات الهندسية الميدانية العاجلة:**
                    """
                    response = model.generate_content(prompt)
                    generated_text = response.text
                    ai_generated = True
                except Exception:
                    ai_generated = False

            if not ai_generated:
                c_eval = "يتجاوز المعايير العالمية بشكل حاد (حد USEPA هو 0.05 mg/L)" if cyanide > 0.05 else "ضمن الحدود المسموح بها"
                m_eval = "شديد الخطورة ويشكل تهديداً سمياً سمكياً وجوفياً" if mercury > 0.006 else "ضمن الحدود المقبولة"
                
                generated_text = f"""
                ### 📄 تقرير التقييم الفني الميداني (الهيئة العامة للأبحاث الجيولوجية - جامعة الخرطوم)
                **الموقع المستهدف:** {st.session_state.selected_site_name} | **درجة الخطر الجيوهيدرولوجي:** {risk_score}%

                1. **التقييم الجيوهيدرولوجي والمخاطر:**
                   - بناءً على معيار DRASTIC، يقع الموقع ضمن نطاق خطر ({'مرتفع جداً' if risk_score > 60 else 'متوسط'}).
                   - نظرية التسرب في تربة ({soil}) بعمق مائي ({depth} متر) تشير إلى زمن وصول قدره ({years} سنة) للمياه الجوفية.

                2. **الأثر البيئي والصحي المباشر:**
                   - **تركيز السيانيد:** {cyanide} mg/L — {c_eval}.
                   - **تركيز الزئبق:** {mercury} mg/L — {m_eval}.
                   - القرب من المجرى المائي ({river_dist} متر) يتطلب حظر الصرف السطحي المباشر منعاً لانتقال التلوث.

                3. **التوصيات الهندسية الميدانية العاجلة:**
                   - الإلزام الفوري بتركيب بطانات عازلة من نوع (HDPE Liner 2mm) لجميع أحواض المعالجة والتطفيح.
                   - حفر آبار مراقبة اختبارية (Monitoring Wells) على مسافات متدرجة للتدفق الجوفي.
                   - إلزام الشركات والمجتمعات بتركيب وحدات تدمير السيانيد واستبدال الزئبق بطرق الاستخلاص الحديثة.
                """

            st.markdown(f"<div class='report-box'>{generated_text}</div>", unsafe_allow_html=True)
            
            st.download_button(
                label="📥 تصدير التقرير الفني (DOC/TXT)",
                data=generated_text,
                file_name=f"Mining_Environmental_Report_{st.session_state.selected_site_name}.txt",
                mime="text/plain"
            )

# ==========================================
# TAB 2: التقييم الجماعي
# ==========================================
with tab2:
    st.markdown("<h4 class='section-header'>📤 رفع ملف البيانات الجماعي (Bulk Upload)</h4>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("اختر ملف Excel أو CSV:", type=["xlsx", "csv"])
    
    if uploaded_file is not None:
        try:
            df_bulk = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            st.success(f"تم تحميل {len(df_bulk)} موقع بنجاح من الملف.")
            col_tbl, col_heat = st.columns([1, 1])
            with col_tbl:
                st.dataframe(df_bulk, use_container_width=True)
            with col_heat:
                map_center = [df_bulk['Latitude'].mean(), df_bulk['Longitude'].mean()]
                m_heat = folium.Map(location=map_center, zoom_start=6, tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri")
                heat_data = [[row['Latitude'], row['Longitude'], row['Cyanide']] for index, row in df_bulk.iterrows() if 'Latitude' in row and 'Longitude' in row and 'Cyanide' in row]
                HeatMap(heat_data, radius=15).add_to(m_heat)
                st_folium(m_heat, width="100%", height=380, key="bulk_heat_map")
        except Exception as e:
            st.error(f"خطأ في قراءة الملف: {e}")

# ==========================================
# TAB 3: محاكاة الحلول الهندسية
# ==========================================
with tab3:
    st.markdown("<h4 class='section-header'>🛡️ محاكاة تأثير الحلول الهندسية الوقائية</h4>", unsafe_allow_html=True)
    col_sc1, col_sc2 = st.columns(2)
    with col_sc1:
        st.subheader("الوضع الحالي (بدون عزل)")
        st.error(f"مؤشر الخطر الحالي: {risk_score}%")
        st.warning(f"زمن وصول الملوثات: {years} سنة")
    with col_sc2:
        st.subheader("الوضع المتوقع بعد التدابير الهندسية")
        liner = st.checkbox("تركيب بطانة عازلة مزدوجة عالية الكثافة (HDPE Liner)")
        treatment = st.checkbox("تطبيق وحدة معالجة السيانيد بالكيميائيات (Cyanide Destruction Unit)")
        mercury_stop = st.checkbox("إلغاء حرق الزئبق المكشوف واستبداله بتقنية الخضخضة العازلة")
        
        mitigated_score = risk_score
        if liner: mitigated_score *= 0.35  
        if treatment: mitigated_score *= 0.50  
        if mercury_stop: mitigated_score *= 0.70

        mitigated_score = round(mitigated_score, 1)
        st.success(f"مؤشر الخطر المتوقع: {mitigated_score}%")
        reduction = round(((risk_score - mitigated_score) / risk_score) * 100, 1) if risk_score > 0 else 0
        st.metric("نسبة انخفاض الخطر البيئي الإجمالية", f"{reduction}%")
