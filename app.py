"""نظام التعدين السوداني v61 — University of Khartoum
DRASTIC / Pesticide DRASTIC + مؤشر DRASTIC-Tox التجريبي (نسخة استكشافية Pilot)

البنية:
  drastic_core.py      المعادلات والتقييمات والحدود (مصدر الحقيقة الوحيد)
  drastic_bridge.py    واجهة التوافق (get_*_rating, calc_index, calc_drastic_t, classify)
  analysis_tools.py    SPSA / الحساسية / Monte Carlo / النقل / التقرير
  advanced_modules.py  مقاييس التحقق، الري، الديناميكي، الأقمار
  auto_calibration.py  المعايرة + leave-one-location-out
  external_validation.py, model_development.py, data_validator.py, gis_raster.py, data_sources.py
  weight_manager.py    ملفات الأوزان   |   water_guardian.py  تبويب مياه الري
"""
import streamlit as st
import subprocess, os, sys, shutil, stat, zipfile, io
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import pandas as pd
import numpy as np
import datetime, requests
from pathlib import Path

from translations import t as _t, TEXTS

import drastic_core as dc
from drastic_bridge import (get_d_rating, get_r_rating, get_a_rating, get_s_rating, get_t_rating,
                            get_i_rating, get_c_rating, calc_index, calc_pesticide_index, classify,
                            calc_drastic_t, DEFAULT_TOX_THRESHOLD, DRASTIC_MAX)
import analysis_tools as at

try:
    from weight_manager import (get_all_profiles, get_active_profile, set_active_profile,
        save_calibrated_profile, detect_ceiling_effect, get_profile_summary, get_stale_profiles)
    WM_OK = True
except ImportError:
    WM_OK = False

try:
    import external_validation as ev
    EXT_VAL_OK = True
except ImportError:
    EXT_VAL_OK = False

try:
    from data_validator import (validate_dataframe, get_quality_color, get_quality_label_ar,
                                audit_site_dataset, audit_agri_dataset)
    VALIDATOR_OK = True
except ImportError:
    VALIDATOR_OK = False

try:
    from pdf_generator import generate_pdf_report
    PDF_OK = True
except ImportError:
    PDF_OK = False
    generate_pdf_report = None

try:
    from excel_exporter import generate_excel_report
    EXCEL_OK = True
except ImportError:
    EXCEL_OK = False
    generate_excel_report = None

try:
    import gis_raster as gr
    RASTER_OK = True
except ImportError:
    RASTER_OK = False

try:
    from live_apis import (fetch_nasa_power, fetch_open_meteo_precipitation, fetch_elevation,
                            fetch_elevation_grid, fetch_soilgrids)
    LIVE_API_OK = True
except ImportError:
    LIVE_API_OK = False

try:
    import auto_calibration as ac
    from auto_calibration import (auto_calibrate_weights, compare_with_defaults, interpret_kappa,
                                  find_optimal_threshold)
    AUTOCAL_OK = True
except ImportError:
    AUTOCAL_OK = False

try:
    from auto_maps import generate_auto_maps, prepare_df_for_maps
    MAPS_OK = True
except ImportError:
    MAPS_OK = False

try:
    import advanced_modules as am
    ADV_OK = True
except ImportError:
    ADV_OK = False

try:
    import model_development as md
    DEV_OK = True
except ImportError:
    DEV_OK = False

try:
    from data_sources import (STATES_DATABASE, AGRICULTURAL_DATA, get_preset_locations_for_app,
        get_data_summary, get_sites_by_state, get_site_data, get_all_sites_as_dataframe, add_new_site,
        get_states_list, get_sites_list, get_agricultural_data_summary, get_agri_states_list,
        get_agri_sites_list, get_agri_site_data, get_all_agri_sites_as_dataframe, KNOWN_MINING_SITES,
        get_verified_sites_as_dataframe, get_all_sites_as_dataframe_with_flag, GRAY_ZONE_SITES,
        get_combined_dataset, get_calibration_dataset, get_data_caveats)
    DS_OK = True
except ImportError:
    DS_OK = False

try:
    from modflow_engine import is_modflow_available, build_and_run_model
    MODFLOW_OK = True
except ImportError:
    MODFLOW_OK = False

try:
    import water_guardian as wg
    WG_OK = True
except ImportError:
    WG_OK = False


def t(key, **kwargs):
    return _t(key, st.session_state.get("lang", "ar"))


def is_ar():
    return st.session_state.get("lang", "ar") == "ar"


def tx(ar, en):
    """نص جديد بلغتين (للعناصر غير الموجودة في translations.py)."""
    return ar if is_ar() else en


st.set_page_config(page_title="Sudan Mining System v61", page_icon="⛏️", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""<style>
html,body,[class*="css"]{font-family:'Segoe UI','Tahoma',Arial;font-size:15px;}
.stButton>button{border-radius:8px;font-weight:600;padding:10px 24px;border:none;}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,#5c2c16,#c19a6b);color:white;}
.stTabs [data-baseweb="tab-list"]{gap:4px;flex-wrap:wrap;background:#faf8f3;padding:8px;border-radius:12px;border:1px solid #e0d4b8;}
.stTabs [data-baseweb="tab"]{border-radius:8px;padding:10px 16px;font-size:.9em;font-weight:600;background:transparent;color:#5c2c16;}
.stTabs [aria-selected="true"]{background:#5c2c16!important;color:white!important;}
div[data-testid="stMetric"]{background:linear-gradient(135deg,#fff,#f9f5ec);border:2px solid #d4af37;border-radius:12px;padding:16px 20px;box-shadow:0 3px 10px rgba(212,175,55,.12);}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#f5eedc,#faf8f3);border-right:3px solid #c19a6b;}
.header-container{background:linear-gradient(135deg,#5c2c16,#c19a6b);padding:28px 24px;border-radius:16px;margin-bottom:24px;color:white;text-align:center;}
.header-agri{background:linear-gradient(135deg,#2d5016,#7cb342)!important;}
.header-title{font-size:2.1em;font-weight:700;margin:0;}
.header-subtitle{font-size:1.05em;opacity:.95;margin:6px 0 0;}
.header-badge{display:inline-block;background:rgba(255,255,255,.2);padding:4px 12px;border-radius:20px;font-size:.85em;margin-top:10px;}
.section-header{display:flex;align-items:center;gap:10px;margin:16px 0 12px;padding-bottom:8px;border-bottom:2px solid #f0e6d2;}
.section-header h3{color:#5c2c16;margin:0;font-size:1.25em;}
.info-card{background:#faf8f3;border:1px solid #e0d4b8;border-radius:10px;padding:16px;margin:10px 0;}
.pilot-banner{background:linear-gradient(135deg,#ff9800,#f57c00);color:white;padding:12px 16px;border-radius:10px;margin:8px 0;font-weight:600;text-align:center;}
.quality-box-ok{background:#e8f5e9;border-left:4px solid #4caf50;padding:10px 12px;border-radius:8px;margin:5px 0;}
.quality-box-warn{background:#fff3e0;border-left:4px solid #ff9800;padding:10px 12px;border-radius:8px;margin:5px 0;}
.about-box{background:#faf8f3;border:1px solid #e0d4b8;border-radius:10px;padding:16px;margin:10px 0;font-size:.9em;}
.mining-badge{display:inline-block;padding:6px 14px;border-radius:8px;font-size:1em;font-weight:700;margin:8px 0;}
.mining-industrial{background:#e3f2fd;color:#1565c0;border:2px solid #1565c0;}
.mining-traditional{background:#fff3e0;color:#e65100;border:2px solid #e65100;}
.mining-mixed{background:#f3e5f5;color:#6a1b9a;border:2px solid #6a1b9a;}
.research-note{background:#e8eaf6;border-left:4px solid #3f51b5;padding:10px 14px;border-radius:8px;margin:8px 0;font-size:.85em;color:#1a237e;}
.kappa-box{padding:20px;border-radius:12px;text-align:center;margin:12px 0;color:white;}
.kappa-excellent{background:linear-gradient(135deg,#2e7d32,#66bb6a);}
.kappa-good{background:linear-gradient(135deg,#388e3c,#81c784);}
.kappa-moderate{background:linear-gradient(135deg,#f57c00,#ffb74d);}
.kappa-fair{background:linear-gradient(135deg,#e64a19,#ff8a65);}
.kappa-poor{background:linear-gradient(135deg,#c62828,#ef5350);}
#MainMenu{visibility:hidden;} footer{visibility:hidden;}
@media(max-width:768px){.header-title{font-size:1.5em!important;}.header-container{padding:18px 14px!important;}[data-testid="stHorizontalBlock"]{flex-direction:column!important;}[data-testid="stHorizontalBlock"]>div{width:100%!important;}}
</style>""", unsafe_allow_html=True)

# ---------------------------------------------------------------- MODFLOW (تحميل عند الطلب فقط)
MODFLOW_URL = "https://github.com/MODFLOW-ORG/modflow6/releases/download/6.4.4/mf6.4.4_linux.zip"
MODFLOW_DIR = "/tmp/modflow6"


@st.cache_resource(show_spinner=False)
def setup_modflow():
    try:
        Path(MODFLOW_DIR).mkdir(parents=True, exist_ok=True)
        mf6_path = os.path.join(MODFLOW_DIR, "mf6")
        if os.path.exists(mf6_path) and os.access(mf6_path, os.X_OK):
            os.environ["PATH"] = MODFLOW_DIR + os.pathsep + os.environ.get("PATH", "")
            return "already_installed"
        with st.spinner("MODFLOW 6..."):
            r = requests.get(MODFLOW_URL, timeout=180, stream=True)
            if r.status_code != 200:
                return f"download_failed_{r.status_code}"
            with zipfile.ZipFile(io.BytesIO(r.content), "r") as zf:
                mf6_file = next((n for n in zf.namelist() if n.endswith("mf6") and not n.endswith("/")), None)
                if not mf6_file:
                    return "mf6_not_in_zip"
                zf.extract(mf6_file, MODFLOW_DIR)
                ex = os.path.join(MODFLOW_DIR, mf6_file)
                if ex != mf6_path:
                    shutil.move(ex, mf6_path)
        os.chmod(mf6_path, os.stat(mf6_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        os.environ["PATH"] = MODFLOW_DIR + os.pathsep + os.environ.get("PATH", "")
        return "installed" if shutil.which("mf6") else "installed_but_not_in_path"
    except Exception as e:
        return f"error: {str(e)[:100]}"


if os.path.exists(MODFLOW_DIR):
    os.environ["PATH"] = MODFLOW_DIR + os.pathsep + os.environ.get("PATH", "")

# ---------------------------------------------------------------- مساعدات عامة
def get_loaded_df(*keys):
    for key in keys:
        df = st.session_state.get(key)
        if df is not None and hasattr(df, "empty") and not df.empty:
            return df
    return None


def safe_sum(df, column, default=0):
    if df is None or column not in df.columns:
        return default
    try:
        return int(df[column].sum())
    except Exception:
        return default


def safe_len(df, default=0):
    try:
        return len(df) if df is not None else default
    except Exception:
        return default


@st.cache_data(show_spinner=False)
def load_industrial_sites_csv():
    csv_path = Path(__file__).parent / "industrial_sites.csv"
    if not csv_path.exists():
        return []
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
        if "verified" in df.columns:
            df["verified"] = df["verified"].astype(str).str.lower() == "true"
        return df.to_dict(orient="records")
    except Exception:
        return []


MINING_LABELS = {"industrial": "🏭 Industrial", "traditional": "⛏️ Traditional", "mixed": "🔀 Mixed"}

AQUIFER_AR = {"massive_shale": "صخر طيني ضخم", "metamorphic_igneous": "صخور متحولة/نارية",
              "weathered_metamorphic_igneous": "صخور متحولة/نارية متآكلة", "glacial_till": "ركام جليدي",
              "thin_bedded_sequences": "تتابعات رقيقة الطبقات", "massive_sandstone": "حجر رملي ضخم",
              "massive_limestone": "حجر جيري ضخم", "sand_and_gravel": "رمل وحصى", "basalt": "بازلت",
              "karst_limestone": "حجر جيري كارستي"}
AQUIFER_EN = {"massive_shale": "Massive Shale", "metamorphic_igneous": "Metamorphic/Igneous",
              "weathered_metamorphic_igneous": "Weathered Metamorphic", "glacial_till": "Glacial Till",
              "thin_bedded_sequences": "Thin Bedded", "massive_sandstone": "Massive Sandstone",
              "massive_limestone": "Massive Limestone", "sand_and_gravel": "Sand & Gravel", "basalt": "Basalt",
              "karst_limestone": "Karst Limestone"}
SOIL_AR = {"thin_or_absent": "رقيقة أو معدومة", "gravel": "حصى", "sand": "رمل", "peat": "خث",
           "shrinking_aggregated_clay": "طين متقلص متكتل", "sandy_loam": "طين رملي", "loam": "طين طميي",
           "silty_loam": "طمي غريني", "clay_loam": "طين غريني", "muck": "طين عضوي", "nonshrinking_clay": "طين غير متقلص"}
SOIL_EN = {"thin_or_absent": "Thin or Absent", "gravel": "Gravel", "sand": "Sand", "peat": "Peat",
           "shrinking_aggregated_clay": "Shrinking Clay", "sandy_loam": "Sandy Loam", "loam": "Loam",
           "silty_loam": "Silty Loam", "clay_loam": "Clay Loam", "muck": "Muck", "nonshrinking_clay": "Non-shrinking Clay"}
VADOSE_AR = {"confining_layer": "طبقة كتيمة", "silt_clay": "غرين وطين", "shale": "صخر طيني",
             "metamorphic_igneous": "صخور متحولة/نارية", "limestone": "حجر جيري", "sandstone": "حجر رملي",
             "bedded_limestone_sandstone": "حجر جيري/رملي متطبق", "sand_gravel_silt_clay": "رمل وحصى وغرين وطين",
             "sand_gravel": "رمل وحصى", "basalt": "بازلت", "karst_limestone": "حجر جيري كارستي"}
VADOSE_EN = {"confining_layer": "Confining Layer", "silt_clay": "Silt & Clay", "shale": "Shale",
             "metamorphic_igneous": "Metamorphic/Igneous", "limestone": "Limestone", "sandstone": "Sandstone",
             "bedded_limestone_sandstone": "Bedded Limestone/Sandstone", "sand_gravel_silt_clay": "Sand/Gravel/Silt/Clay",
             "sand_gravel": "Sand & Gravel", "basalt": "Basalt", "karst_limestone": "Karst Limestone"}


def AQ(a): return AQUIFER_AR.get(a, a) if is_ar() else AQUIFER_EN.get(a, a)
def SL(s): return SOIL_AR.get(s, s) if is_ar() else SOIL_EN.get(s, s)
def VD(v): return VADOSE_AR.get(v, v) if is_ar() else VADOSE_EN.get(v, v)


VALID_AQUIFERS = list(dc.AQUIFER)
VALID_SOILS = list(dc.SOIL)
VALID_VADOSE = list(dc.VADOSE)

if "lang" not in st.session_state:
    st.session_state["lang"] = "ar"

# الأوزان المعايَرة تُطبَّق فقط إذا كان الملف النشط معايَراً فعلاً (وليس الافتراضي)
CALIBRATED_WEIGHTS = None


def tox_kw(mining_type):
    """وسائط الأوزان لـ calc_drastic_t: فارغة (أوزان متساوية) ما لم يوجد ملف معايَر نشط لنفس النمط."""
    if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mining_type:
        return dict(alpha_override=CALIBRATED_WEIGHTS["alpha"], beta_override=CALIBRATED_WEIGHTS["beta"],
                    SF_override=CALIBRATED_WEIGHTS["SF"])
    return {}


def row_drastic(row):
    """DRASTIC لصف (قاموس أو Series). يرفع ValueError عند خطأ بدل إرجاع 0."""
    return calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])),
                      get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])),
                      get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])),
                      get_c_rating(float(row["conductivity"])))


def row_pesticide(row):
    return calc_pesticide_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])),
                                get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])),
                                get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])),
                                get_c_rating(float(row["conductivity"])))


def row_tox(row, mining_type="traditional"):
    ix = row_drastic(row)
    r = calc_drastic_t(ix, float(row.get("cn_water_mg_l", 0.0)), float(row.get("hg_water_mg_l", 0.0)),
                       mining_type=mining_type, **tox_kw(mining_type))
    return ix, r


def add_indices(df, mining_type="traditional"):
    """يضيف DRASTIC و DRASTIC_Tox إلى جدول ويُرجع (df, أخطاء)."""
    d_vals, t_vals, errs = [], [], []
    for i, (_, row) in enumerate(df.iterrows()):
        try:
            ix, r = row_tox(row, mining_type)
            d_vals.append(ix)
            t_vals.append(r["drastic_t"])
        except Exception as e:
            d_vals.append(np.nan)
            t_vals.append(np.nan)
            errs.append(f"{i + 1}: {str(e)[:80]}")
    out = df.copy()
    out["DRASTIC"], out["DRASTIC_Tox"] = d_vals, t_vals
    return out, errs


def generate_html_report(*a, **k):
    return at.generate_html_report(*a, **k)


def build_heatmap_verified(show_heat=True, show_markers=True):
    m = folium.Map(location=[15.5, 32.5], zoom_start=6, tiles="OpenStreetMap")
    heat_data, stats, sites_info = [], {"low": 0, "medium": 0, "high": 0, "very_high": 0}, []
    colors = {"very_high": ("#d32f2f", 20), "high": ("#f57c00", 16), "medium": ("#fbc02d", 12), "low": ("#388e3c", 9)}
    for state_name, state_data in STATES_DATABASE.items():
        for site_key, sd in state_data.get("sites", {}).items():
            if not sd.get("verified", False):
                continue
            coords = sd.get("coords")
            if not coords or len(coords) < 2:
                continue
            try:
                mt = sd.get("mining_type", "traditional")
                ix, r = row_tox({"depth_m": sd["depth_m"], "recharge_mm": sd["recharge_mm"], "slope_pct": sd["slope_pct"],
                                 "conductivity": sd["conductivity"], "aquifer": sd["aquifer"], "soil": sd["soil"],
                                 "vadose": sd["vadose"], "cn_water_mg_l": sd.get("cn_water_mg_l", 0.0),
                                 "hg_water_mg_l": sd.get("hg_water_mg_l", 0.0)}, mt)
                dtox = r["drastic_t"]
            except Exception:
                continue
            level = classify(dtox, is_tox=True)["level"]
            color, radius = colors[level]
            stats[level] += 1
            popup = (f'<div style="font-family:Arial;font-size:12px;"><h4 style="color:{color};">{sd.get("name_ar", site_key)}</h4>'
                     f'<b>DRASTIC:</b> {ix}<br><b>DRASTIC-Tox:</b> <span style="color:{color};font-weight:bold;">{dtox}</span><br>'
                     f'<b>CN:</b> {sd.get("cn_water_mg_l")} mg/L<br><b>Hg:</b> {sd.get("hg_water_mg_l")} mg/L</div>')
            if show_markers:
                folium.CircleMarker(location=[coords[0], coords[1]], radius=radius, popup=folium.Popup(popup, max_width=280),
                                    tooltip=f"{sd.get('name_ar', site_key)} - {dtox}", color=color, fill=True,
                                    fillColor=color, fillOpacity=0.75, weight=2).add_to(m)
            heat_data.append([coords[0], coords[1], min(1.0, dtox / (DRASTIC_MAX + 50.0))])
            sites_info.append({"state": state_name, "site": sd.get("name_ar", site_key), "lat": coords[0], "lon": coords[1],
                               "DRASTIC": ix, "DRASTIC-Tox": dtox, "CN": sd.get("cn_water_mg_l"),
                               "Hg": sd.get("hg_water_mg_l"), "Level": level})
    if show_heat and heat_data:
        HeatMap(heat_data, min_opacity=0.3, max_zoom=10, radius=30, blur=20,
                gradient={0.0: "#388e3c", 0.4: "#fbc02d", 0.7: "#f57c00", 1.0: "#d32f2f"}).add_to(m)
    return m, stats, pd.DataFrame(sites_info)


if DS_OK:
    preset = get_preset_locations_for_app()
    summary = get_data_summary()
    n_states = summary.get("total_states", 0)
    n_sites_total = summary.get("total_sites", 0)
    n_sites_verified = summary.get("verified_sites", 0)
    n_locations_verified = summary.get("verified_locations", n_sites_verified)
    agri_summary = get_agricultural_data_summary()
    n_agri_states = agri_summary.get("total_states", 0)
    n_agri_sites = agri_summary.get("total_sites", 0)
else:
    preset = {}
    n_states = n_sites_total = n_sites_verified = n_locations_verified = n_agri_states = n_agri_sites = 0

INDUSTRIAL_SITES = load_industrial_sites_csv()

# ================================================================= الشريط الجانبي
_lang_opts = {"🇸🇦 العربية": "ar", "🇬🇧 English": "en"}
_cur = "🇸🇦 العربية" if st.session_state["lang"] == "ar" else "🇬🇧 English"
_sel = st.sidebar.selectbox(t("language"), list(_lang_opts.keys()), index=list(_lang_opts.keys()).index(_cur), key="lang_switcher")
st.session_state["lang"] = _lang_opts[_sel]

st.sidebar.markdown(f"""<div style="background:linear-gradient(135deg,#5c2c16,#c19a6b);padding:16px;border-radius:12px;color:white;text-align:center;margin-bottom:16px;"><div style="font-size:1.3em;font-weight:700;">{t("upload_files")}</div></div>""", unsafe_allow_html=True)


def _read_upload(f):
    return pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)


for _label, _key, _state, _info in ((t("validation_file"), "uploader_validation", "df_validation", False),
                                    (t("bulk_file"), "uploader_bulk", "df_bulk", False),
                                    (t("extra_file"), "uploader_extra", "df_extra", True)):
    _up = st.sidebar.file_uploader(_label + ":", type=["csv", "xlsx"], key=_key)
    if _up is not None:
        try:
            _df = _read_upload(_up)
            st.session_state[_state] = _df
            (st.sidebar.info if _info else st.sidebar.success)(f"{len(_df)} {t('rows')}")
        except Exception as e:
            st.sidebar.error(f"{str(e)[:80]}")

if st.sidebar.button(t("clear_all"), key="clear_all_files_btn"):
    for k in ["df_validation", "df_bulk", "df_extra", "df_combined", "validation_report"]:
        st.session_state.pop(k, None)
    st.rerun()

st.sidebar.markdown("---")
if DS_OK:
    st.sidebar.markdown(f"### {t('data_quality')}")
    st.sidebar.markdown(f"""<div class="quality-box-ok"><div style="font-size:0.85em;color:#2e7d32;">{t('verified_sites')}: {n_sites_verified}
    ({tx('مواقع مستقلة', 'independent locations')}: {n_locations_verified})</div></div>
    <div class="quality-box-warn"><div style="font-size:0.85em;color:#e65100;">{t('display_only')}: {n_sites_total - n_sites_verified}</div></div>""", unsafe_allow_html=True)
    with st.sidebar.expander(tx("⚠️ ملاحظات على جودة البيانات", "⚠️ Data quality notes"), expanded=False):
        try:
            for _f in get_data_caveats():
                (st.warning if _f["severity"] in ("warning", "error") else st.info)(_f["message_ar"] if is_ar() else _f["message_en"])
        except Exception as e:
            st.caption(str(e)[:80])

st.sidebar.markdown("---")
st.sidebar.markdown(f"### {t('data_scope')}")
DATA_SCOPE = st.sidebar.radio(t("select"), [t("scope_traditional"), t("scope_industrial"), t("scope_all")],
                              index=0, key="sidebar_data_scope", label_visibility="collapsed")
SCOPE_KEY = "traditional" if DATA_SCOPE == t("scope_traditional") else "industrial" if DATA_SCOPE == t("scope_industrial") else "all"
if SCOPE_KEY == "industrial" and not INDUSTRIAL_SITES:
    st.sidebar.warning(t("no_industrial_file"))

# الأوزان: ملف معايَر نشط فقط يُعدّ "معايَراً"
if WM_OK:
    _active_prof = get_active_profile(SCOPE_KEY if SCOPE_KEY != "all" else "traditional")
    if _active_prof and _active_prof.get("source_type") == "calibrated":
        CALIBRATED_WEIGHTS = {"mining_type": _active_prof["mining_type"], "alpha": _active_prof["alpha"],
                              "beta": _active_prof["beta"], "SF": _active_prof["SF"],
                              "kappa": _active_prof.get("kappa", "—"), "source_type": "calibrated",
                              "ar": _active_prof.get("name_ar", "")}
    elif _active_prof:
        _display_default = _active_prof
_a, _b, _sf, _name, _cal = 1.0, 1.0, 1.0, tx("افتراضي (أوزان متساوية)", "Default (equal weights)"), False
if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == (SCOPE_KEY if SCOPE_KEY != "all" else "traditional"):
    _a, _b, _sf, _name, _cal = CALIBRATED_WEIGHTS["alpha"], CALIBRATED_WEIGHTS["beta"], CALIBRATED_WEIGHTS["SF"], CALIBRATED_WEIGHTS["ar"], True
_badge_cls = "mining-industrial" if SCOPE_KEY == "industrial" else "mining-traditional"
st.sidebar.markdown(f"""<div class="mining-badge {_badge_cls}">{_name}</div><div style="font-size:0.75em;color:#666;margin-top:4px;">
α(CN)={_a} | β(Hg)={_b} | SF={_sf} {'' if _cal else '— ' + tx('فرضية صفرية', 'null assumption')}</div>""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown(f"## {t('mode')}")
mode_options = [t("mode_system")]
if ADV_OK:
    mode_options += [t("mode_agricultural"), t("mode_verification"), t("mode_transport"),
                     t("mode_independent"), t("mode_satellite"), t("mode_dynamic")]
if MODFLOW_OK:
    mode_options.append(t("mode_modflow"))
mode = st.sidebar.radio(t("select"), mode_options, key="app_mode_radio", label_visibility="collapsed")
MODE_MAP = {t("mode_system"): "system", t("mode_agricultural"): "agricultural", t("mode_verification"): "verification",
            t("mode_transport"): "transport", t("mode_independent"): "independent", t("mode_satellite"): "satellite",
            t("mode_dynamic"): "dynamic", t("mode_modflow"): "modflow"}
MODE_KEY = MODE_MAP.get(mode, "system")

st.sidebar.markdown("---")
st.sidebar.markdown(f"### {t('status')}")
st.sidebar.info(f"MODFLOW: {tx('يُحمَّل عند اختيار وضعه', 'loaded on demand')}")
if "ci" in st.session_state:
    st.sidebar.success(f"{t('current_index')}: {st.session_state['ci']}")

st.sidebar.markdown("---")
with st.sidebar.expander(t("about"), expanded=False):
    _mods = {"weight_manager": WM_OK, "auto_calibration": AUTOCAL_OK, "auto_maps": MAPS_OK, "modflow": MODFLOW_OK,
             "advanced": ADV_OK, "model_development": DEV_OK, "external_validation": EXT_VAL_OK,
             "data_validator": VALIDATOR_OK, "pdf_generator": PDF_OK, "excel_exporter": EXCEL_OK,
             "gis_raster": RASTER_OK, "live_apis": LIVE_API_OK, "water_guardian": WG_OK}
    st.markdown(f"""<div class="about-box"><h4>{t('app_title')} v61</h4><h4>{t('modules')}:</h4><p style="font-size:0.8em;">
{'<br>'.join(f'{k}: {"OK" if v else "NO"}' for k, v in _mods.items())}</p><h4>{t('constraints')}:</h4>
<ul style="font-size:0.85em;"><li>PILOT VERSION</li><li>n = {n_sites_verified} {tx('صفاً', 'rows')} / {n_locations_verified} {tx('مواقع مستقلة', 'independent locations')}</li>
<li>{t('screening_only')}</li></ul></div>""", unsafe_allow_html=True)

# ================================================================= الترويسة ورفع الملفات
st.markdown(f"""<div class="pilot-banner">{t("pilot_version")}</div><div class="header-container"><div class="header-title">{t("app_title")}</div>
<div class="header-subtitle">{t("university")}</div><div class="header-subtitle">{t("subtitle")}</div>
<div class="header-badge">{t("version")} 61 | {n_states} | {n_sites_total} {t("sites")} ({n_sites_verified} {t("verified_sites")})</div></div>""", unsafe_allow_html=True)

with st.expander(f"📤 {t('upload_files')}", expanded=False):
    c1, c2, c3 = st.columns(3)
    for _col, _lab, _k, _st in ((c1, t("validation_file"), "main_val_uploader", "df_validation"),
                                (c2, t("bulk_file"), "main_bulk_uploader", "df_bulk"),
                                (c3, t("extra_file"), "main_extra_uploader", "df_extra")):
        with _col:
            _f = st.file_uploader(_lab + ":", type=["csv", "xlsx"], key=_k)
            if _f:
                try:
                    st.session_state[_st] = _read_upload(_f)
                    st.success(f"{len(st.session_state[_st])} {t('rows')}")
                except Exception as e:
                    st.error(f"{str(e)[:60]}")

    if VALIDATOR_OK:
        df_to_validate = get_loaded_df("df_validation", "df_bulk", "df_extra")
        if df_to_validate is not None:
            st.markdown("---")
            st.markdown("#### 🔍 " + tx("فحص جودة البيانات", "Data Quality Check"))
            if st.button("🔍 " + tx("فحص الملف", "Validate File"), type="secondary", key="run_validator_btn"):
                with st.spinner("Analyzing data..."):
                    st.session_state["validation_report"] = validate_dataframe(df_to_validate, mode="mining")
            if "validation_report" in st.session_state:
                report = st.session_state["validation_report"]
                score = report["score"]
                color = get_quality_color(score)
                st.markdown(f"""<div style="background:linear-gradient(135deg,{color}22,{color}11);border:2px solid {color};border-radius:12px;padding:20px;margin:12px 0;text-align:center;">
                <div style="font-size:0.9em;color:#666;">{tx("جودة البيانات", "Data Quality")}</div>
                <div style="font-size:3em;font-weight:700;color:{color};margin:8px 0;">{score}/100</div>
                <div style="font-size:1.2em;font-weight:600;color:{color};">{get_quality_label_ar(score)}</div></div>""", unsafe_allow_html=True)
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Rows", report["n_rows"]); k2.metric("Cols", report["n_cols"])
                k3.metric("❌ Errors", len(report["errors"])); k4.metric("⚠️ Warnings", len(report["warnings"]))
                for _title, _items, _fn in (("❌ " + tx("أخطاء حرجة", "Critical Errors"), report["errors"], st.error),
                                            ("⚠️ " + tx("تحذيرات", "Warnings"), report["warnings"], st.warning)):
                    if _items:
                        st.markdown("---"); st.markdown(f"#### {_title}")
                        for it in _items:
                            _fn("• " + (it["message_ar"] if is_ar() else it["message_en"]))
                if report["info"]:
                    with st.expander("ℹ️ " + tx("ملاحظات", "Info")):
                        for it in report["info"]:
                            st.info("• " + (it["message_ar"] if is_ar() else it["message_en"]))
                (st.success if report["is_valid"] else st.error)(
                    "✅ " + tx("البيانات صالحة تقنياً (راجع التحذيرات العلمية أعلاه)", "Technically valid (read the scientific warnings above)")
                    if report["is_valid"] else "❌ " + tx("يجب إصلاح الأخطاء قبل المتابعة", "Fix errors before proceeding"))

    sample = pd.DataFrame({"site_name": ["Site1", "Site2"], "site_key": ["Site1", "Site2"], "lat": [13.5, 15.6], "lon": [33.6, 32.5],
                           "depth_m": [12.0, 15.0], "recharge_mm": [20.0, 18.0], "slope_pct": [3.0, 4.0], "conductivity": [2.5, 3.0],
                           "aquifer": ["massive_sandstone", "sand_and_gravel"], "soil": ["sand", "sandy_loam"],
                           "vadose": ["sand_gravel", "sandstone"], "cn_water_mg_l": [0.10, 0.009], "hg_water_mg_l": [0.008, 0.0007],
                           "actual_contaminated": [1, 0]})
    st.download_button("📥 Template / القالب", data=sample.to_csv(index=False).encode("utf-8-sig"),
                       file_name="template.csv", mime="text/csv", key="download_template_btn")
    st.caption(tx("أضف lat/lon (أو site_key) كي تُعامل صفوف الموقع الواحد (جاف/رطب) كموقع مستقل واحد في التحقق.",
                  "Add lat/lon (or site_key) so repeated rows of one place count as one location in validation."))

st.markdown("---")

# ================================================================= دوال مساعدة للتبويبات

MT_LABEL = {"industrial": ("🏭 صناعي", "🏭 Industrial"), "traditional": ("⛏️ تقليدي", "⛏️ Traditional"),
            "mixed": ("🔀 مختلط", "🔀 Mixed")}


def mt_label(mt):
    ar, en = MT_LABEL.get(mt, MT_LABEL["traditional"])
    return ar if is_ar() else en

_LAB_AR = {"low": "منخفض", "moderate": "متوسط", "medium": "متوسط", "high": "مرتفع", "very_high": "مرتفع جداً",
           "compliant": "مطابق للحد", "elevated": "أعلى من الحد قليلاً", "severe": "شديد"}


def lab(x):
    return _LAB_AR.get(x, x) if is_ar() else str(x).replace("_", " ").title()


def two_axis(idx, cn, hg):
    """محور الهشاشة (DRASTIC) + محور الخطر (تركيز/حد) + مصفوفة المخاطر. لا يخلط التركيز بالهشاشة."""
    L = dc.LIMITS_MG_L[at.STANDARD]
    hq = max(cn / L["cn"] if L["cn"] else 0.0, hg / L["hg"])
    v, vp = dc.vulnerability_class(idx)
    h = dc.hazard_class(hq)
    return {"vuln": v, "vuln_pct": vp, "hazard": h, "max_hq": round(hq, 1), "risk": dc.risk_category(v, h)}


def show_two_axis(idx, cn, hg):
    ta = two_axis(idx, cn, hg)
    k1, k2, k3 = st.columns(3)
    k1.metric(tx("الهشاشة (DRASTIC)", "Vulnerability (DRASTIC)"), f"{lab(ta['vuln'])} ({ta['vuln_pct']}%)")
    k2.metric(tx("الخطر (التركيز ÷ الحد)", "Hazard (conc ÷ limit)"), f"{lab(ta['hazard'])} (HQ={ta['max_hq']})")
    k3.metric(tx("فئة المخاطر المركّبة", "Combined risk"), lab(ta["risk"]))
    st.caption(tx(f"الحدود: EU Directive 98/83/EC ({at.STANDARD}) — السيانيد 0.05 و الزئبق 0.001 mg/L. الفئات اصطلاحية وليست من Aller 1987.",
                  f"Limits: EU Directive 98/83/EC ({at.STANDARD}) — CN 0.05, Hg 0.001 mg/L. Classes are conventions, not from Aller 1987."))
    return ta


if MODE_KEY == "system":
    tabs = st.tabs([
        t("tab_input"), t("tab_manual"), t("tab_bulk"), t("tab_solutions"), t("tab_report"), t("tab_heatmap"),
        t("tab_sensitivity"), t("tab_toxicity"), t("tab_gis"), t("tab_monte_carlo"), t("tab_advanced"),
        t("tab_development"), t("tab_auto_maps"), t("tab_calibration"), t("tab_threshold"),
        "⚙️ Profiles", "🔬 External Validation", "🗺️ GIS Raster", "🌐 Live Data", "💧 حارس المياه"])

    # ------------------------------------------------------------- 0: اختيار موقع
    with tabs[0]:
        st.markdown(f'<div class="section-header"><h3>{t("site_selection")}</h3></div>', unsafe_allow_html=True)
        if not DS_OK:
            st.error("data_sources.py")
        else:
            c1, c2 = st.columns([1, 2])
            with c1:
                state = st.selectbox(t("state"), get_states_list(), key="tab0_state_select")
            with c2:
                st.markdown(f'<div class="info-card" style="margin-top:28px;"><div style="font-size:0.9em;color:#5c2c16;">{STATES_DATABASE[state]["description"]}</div></div>', unsafe_allow_html=True)
            site_key = st.selectbox(t("site"), get_sites_list(state), key="tab0_site_select")
            site_data = get_site_data(state, site_key)
            is_est = "تقديرات" in str(site_data.get("source", ""))
            mt_key = site_data.get("mining_type", SCOPE_KEY if SCOPE_KEY != "all" else "traditional")
            if mt_key not in ("industrial", "traditional", "mixed"):
                mt_key = "traditional"
            badge_class = {"industrial": "mining-industrial", "mixed": "mining-mixed"}.get(mt_key, "mining-traditional")
            st.markdown(f'<div class="mining-badge {badge_class}">{mt_label(mt_key)}</div>', unsafe_allow_html=True)
            st.session_state.update({"mining_type": mt_key, "current_site_key": site_key,
                                     "current_site_data": site_data, "current_state": state})
            if is_est or not site_data.get("verified", False):
                st.warning(tx("⚠️ بيانات تقديرية/غير موثَّقة: للعرض فقط، لا تُستخدم في المعايرة أو التحقق.",
                              "⚠️ Estimated / unverified data: display only, not used for calibration or validation."))
            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(t("activity"), site_data.get("activity", "N/A"))
            c2.metric(t("season"), site_data.get("season", "N/A"))
            c3.metric(t("site_status"), t("contaminated") if site_data["actual_contaminated"] == 1 else t("clean"))
            c4.metric(t("documentation"), t("verified") if site_data.get("verified", False) else t("display"))
            c1, c2 = st.columns(2)
            with c1:
                st.metric("D - " + t("depth"), f"{site_data['depth_m']} {t('m')}")
                st.metric("R - " + t("recharge"), f"{site_data['recharge_mm']} {t('mm_yr')}")
                st.metric("T - " + t("slope"), f"{site_data['slope_pct']} %")
                st.metric("C - " + t("conductivity"), f"{site_data['conductivity']} {t('m_day')}")
            with c2:
                st.metric("A - " + t("aquifer"), AQ(site_data["aquifer"]))
                st.metric("S - " + t("soil"), SL(site_data["soil"]))
                st.metric("I - " + t("vadose"), VD(site_data["vadose"]))
                st.metric("theta - " + t("porosity"), "0.25")
            c1, c2 = st.columns(2)
            c1.metric("CN", f"{site_data['cn_water_mg_l']} mg/L")
            c2.metric("Hg", f"{site_data['hg_water_mg_l']} mg/L")
            _L = dc.LIMITS_MG_L[at.STANDARD]
            st.caption(f"{t('limits')}: CN = {_L['cn']} mg/L | Hg = {_L['hg']} mg/L ({at.STANDARD})")
            for _w in dc.check_units(site_data["cn_water_mg_l"], site_data["hg_water_mg_l"]):
                st.warning(_w)
            try:
                idx = row_drastic(site_data)
                risk = classify(idx)
                st.session_state["ci"] = idx
                st.session_state["cv"] = {"depth": site_data["depth_m"], "recharge": site_data["recharge_mm"],
                                          "aquifer": site_data["aquifer"], "soil": site_data["soil"],
                                          "slope": site_data["slope_pct"], "vadose": site_data["vadose"],
                                          "conductivity": site_data["conductivity"],
                                          "cn_water_mg_l": site_data["cn_water_mg_l"], "hg_water_mg_l": site_data["hg_water_mg_l"]}
                st.session_state["current_risk"] = risk
                z1, z2, z3 = st.columns(3)
                z1.metric("DRASTIC", f"{idx}/{DRASTIC_MAX}")
                z2.metric(t("level"), t(risk["level"]))
                z3.metric(t("percentage"), f"{round((idx - 23) / (DRASTIC_MAX - 23) * 100, 1)}%")
                {"red": st.error, "orange": st.warning, "yellow": st.info}.get(risk["color"], st.success)(t(risk["action"]))
                st.markdown("---")
                st.markdown(f"#### {tx('تقييم من محورين (مُوصى به)', 'Two-axis assessment (recommended)')}")
                show_two_axis(idx, site_data["cn_water_mg_l"], site_data["hg_water_mg_l"])
                dt_result = calc_drastic_t(idx, site_data["cn_water_mg_l"], site_data["hg_water_mg_l"],
                                           mining_type=mt_key, **tox_kw(mt_key))
                if tox_kw(mt_key):
                    st.caption(t("using_calibrated"))
                st.markdown("---")
                st.markdown(f"#### {t('drastic_tox')} — {tx('تجريبي', 'experimental')}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric(t("drastic_tox"), f"{dt_result['drastic_t']}", delta=f"+{dt_result['increase_pct']}%")
                m2.metric(t("bonus"), dt_result["toxicity_bonus"])
                m3.metric("α (CN)", dt_result["alpha"])
                m4.metric("β (Hg)", dt_result["beta"])
                st.caption(tx("المدى النظري 23–276 بأوزان متساوية. الإضافة صيغة مقترحة غير مُتحقَّق منها خارجياً.",
                              "Theoretical range 23–276 with equal weights. The bonus is a proposed, externally unvalidated formulation."))
                with st.expander(t("calculation_details")):
                    d1, d2, d3, d4 = st.columns(4)
                    d1.metric(t("cn_score"), dt_result["cn_score"]); d2.metric(t("hg_score"), dt_result["hg_score"])
                    d3.metric(t("base_bonus"), dt_result["base_bonus"]); d4.metric(t("source_factor"), dt_result["source_factor"])
                st.markdown("---")
                st.download_button("📄 " + t("tab_report") + " (HTML)", key="download_report_btn", mime="text/html",
                                   file_name=f"report_{site_key}.html",
                                   data=generate_html_report(
                                       site_info={"name": site_data.get("name_ar", site_key), "state": state},
                                       drastic=idx, drastic_t=dt_result["drastic_t"], level=t(risk["level"]),
                                       recommendation=t(risk["action"])).encode("utf-8"))
            except ValueError as e:
                st.error(str(e))

    # ------------------------------------------------------------- 1: إدخال يدوي
    with tabs[1]:
        st.markdown(f'<div class="section-header"><h3>{t("tab_manual")}</h3></div>', unsafe_allow_html=True)
        st.info(tx("المواقع اليدوية تُحفظ في ذاكرة الخادم فقط (تظهر لكل المستخدمين وتُمحى عند إعادة التشغيل) وتُوسَم غير موثَّقة.",
                   "Manual sites live in server memory only (visible to all users, wiped on restart) and are flagged unverified."))
        c1, c2 = st.columns(2)
        with c1:
            new_state = st.text_input(t("state"), value="Sennar", key="new_state_input")
            new_site_key = st.text_input(t("site"), value="New_Site", key="new_site_input")
            new_lat = st.number_input("Lat:", value=13.55, key="new_lat_input")
            new_lon = st.number_input("Lon:", value=33.60, key="new_lon_input")
            new_depth = st.number_input("D (m):", 0.5, 100.0, 15.0, key="new_depth_input")
            new_recharge = st.number_input("R (mm/yr):", 0.0, 400.0, 20.0, key="new_recharge_input")
        with c2:
            new_slope = st.number_input("T (%):", 0.0, 30.0, 3.0, key="new_slope_input")
            new_conductivity = st.number_input("C (m/d):", 0.01, 200.0, 3.0, key="new_conductivity_input")
            new_aquifer = st.selectbox("A:", VALID_AQUIFERS, key="new_aquifer_select")
            new_soil = st.selectbox("S:", VALID_SOILS, key="new_soil_select")
            new_vadose = st.selectbox("I:", VALID_VADOSE, key="new_vadose_select")
        c1, c2, c3 = st.columns(3)
        with c1: new_cn = st.number_input("CN (mg/L):", 0.0, 10.0, 0.010, format="%.4f", key="new_cn_input")
        with c2: new_hg = st.number_input("Hg (mg/L):", 0.0, 10.0, 0.001, format="%.5f", key="new_hg_input")
        with c3: new_cont = st.selectbox(t("site_status"), [t("clean") + " (0)", t("contaminated") + " (1)"], key="new_cont_select")
        if st.button("💾 " + t("save"), type="primary", key="save_manual_site_btn"):
            try:
                if not DS_OK:
                    raise ValueError("data_sources.py")
                add_new_site(new_state, new_site_key, {
                    "name_ar": new_site_key, "coords": (new_lat, new_lon), "depth_m": new_depth, "recharge_mm": new_recharge,
                    "slope_pct": new_slope, "conductivity": new_conductivity, "aquifer": new_aquifer, "soil": new_soil,
                    "vadose": new_vadose, "cn_water_mg_l": new_cn, "hg_water_mg_l": new_hg,
                    "actual_contaminated": 1 if "1" in new_cont else 0, "season": "-", "activity": "Manual"})
                st.success(t("success")); st.rerun()
            except ValueError as e:
                st.error(str(e))

    # ------------------------------------------------------------- 2: تقييم جماعي
    with tabs[2]:
        st.markdown(f'<div class="section-header"><h3>{t("bulk_assessment")}</h3></div>', unsafe_allow_html=True)
        df_bulk = get_loaded_df("df_bulk", "df_validation")
        if df_bulk is None:
            st.warning(t("no_file"))
        else:
            try:
                st.dataframe(df_bulk.head(10), use_container_width=True)
                _mt = st.session_state.get("mining_type", "traditional")
                c1, c2 = st.columns(2)
                with c1: th_d = st.number_input(t("drastic_threshold"), 50, 200, 140, 5, key="bulk_th_d_input")
                with c2: th_dt = st.number_input(t("drastic_tox_threshold"), 50, 280, int(DEFAULT_TOX_THRESHOLD), 5, key="bulk_th_dt_input")
                has_tox = "cn_water_mg_l" in df_bulk.columns and "hg_water_mg_l" in df_bulk.columns
                scored, errs = add_indices(df_bulk, _mt)
                name_col = "name" if "name" in scored.columns else ("site_name" if "site_name" in scored.columns else None)
                df_results = pd.DataFrame({
                    "Site": scored[name_col] if name_col else [f"R{i + 1}" for i in range(len(scored))],
                    "DRASTIC": scored["DRASTIC"], "DRASTIC-Tox": scored["DRASTIC_Tox"],
                    "Status": np.where(scored["DRASTIC_Tox"].isna(), "ERR", np.where(scored["DRASTIC_Tox"] >= th_dt, "HIGH", "LOW"))})
                st.dataframe(df_results, use_container_width=True)
                for e in errs[:10]:
                    st.error(tx("خطأ في الصف ", "Row error ") + e)
                ok = scored.dropna(subset=["DRASTIC", "DRASTIC_Tox"])
                if has_tox and "actual_contaminated" in ok.columns and ok["actual_contaminated"].nunique() == 2 and ADV_OK:
                    st.markdown("---")
                    st.caption(tx("مقاييس وصفية على نفس البيانات وبعتبة مُدخلة (غير مُستقلة). للتقدير الصادق استخدم تبويب External Validation.",
                                  "Descriptive metrics on the same data at a typed threshold (not independent). For honest estimates use the External Validation tab."))
                    c1, c2 = st.columns(2)
                    for col, name, vals, th in ((c1, "DRASTIC", ok["DRASTIC"], th_d), (c2, "DRASTIC-Tox", ok["DRASTIC_Tox"], th_dt)):
                        with col:
                            st.markdown(f"**{name}**")
                            m = am.calculate_confusion_matrix(vals.tolist(), ok["actual_contaminated"].astype(int).tolist(), th)
                            st.metric(t("kappa"), m["kappa"]); st.metric(t("recall"), f"{m['recall']}%")
                st.download_button(t("download_results"), data=df_results.to_csv(index=False).encode("utf-8-sig"),
                                   file_name="results.csv", mime="text/csv", key="download_bulk_results_btn")
            except Exception as e:
                st.error(str(e))

    # ------------------------------------------------------------- 3: الحلول
    with tabs[3]:
        st.markdown(f'<div class="section-header"><h3>{t("solutions")}</h3></div>', unsafe_allow_html=True)
        st.warning(tx("⚠️ معاملات التخفيض (HDPE ×0.40، معالجة ×0.60، مراقبة ×0.85) افتراضات توضيحية بلا مصدر.",
                      "⚠️ Reduction factors (HDPE ×0.40, treatment ×0.60, monitoring ×0.85) are illustrative assumptions without a source."))
        if "ci" in st.session_state:
            ci = st.session_state["ci"]
            c1, c2 = st.columns(2)
            with c1:
                h = st.checkbox(t("hdpe_liner"), key="chk_hdpe")
                tr = st.checkbox(t("cyanide_treatment"), key="chk_cyanide")
            with c2:
                mo = st.checkbox(t("monitoring_wells"), key="chk_monitoring")
            if h or tr or mo:
                r = at.mitigate(ci, h, tr, mo)
                c1, c2, c3 = st.columns(3)
                c1.metric(t("before"), ci); c2.metric(t("after"), r["mitigated_index"]); c3.metric(t("reduction"), f"{r['reduction_pct']}%")
        else:
            st.info(t("site_selection"))

    # ------------------------------------------------------------- 4: التقارير
    with tabs[4]:
        st.markdown(f'<div class="section-header"><h3>{t("tab_report")}</h3></div>', unsafe_allow_html=True)
        if "ci" not in st.session_state:
            st.warning(t("site_selection"))
        else:
            cv = st.session_state.get("cv", {})
            mt_key = st.session_state.get("mining_type", "traditional")
            site_key_current = st.session_state.get("current_site_key", "site")
            current_risk = st.session_state.get("current_risk")
            idx = st.session_state["ci"]
            cn, hg = cv.get("cn_water_mg_l", 0), cv.get("hg_water_mg_l", 0)
            c1, c2, c3 = st.columns(3)
            c1.metric("DRASTIC", f"{idx}/{DRASTIC_MAX}"); c2.metric("CN", f"{cn} mg/L"); c3.metric("Hg", f"{hg} mg/L")
            st.markdown("---")
            dt_res = calc_drastic_t(idx, cn, hg, mining_type=mt_key, **tox_kw(mt_key))
            st.dataframe(pd.DataFrame({
                "Metric": ["DRASTIC", "CN_score", "Hg_score", "Base Bonus", "Source Factor", "Final Bonus", "DRASTIC-Tox (experimental)", "Level"],
                "Value": [idx, dt_res["cn_score"], dt_res["hg_score"], dt_res["base_bonus"], dt_res["source_factor"],
                          dt_res["toxicity_bonus"], dt_res["drastic_t"], t(dt_res["level"])]}),
                use_container_width=True, hide_index=True)
            show_two_axis(idx, cn, hg)
            st.markdown("---")
            _site_info = {"name": site_key_current, "state": mt_key, "coords": "Sudan", "depth": cv.get("depth", "N/A"),
                          "recharge": cv.get("recharge", "N/A"), "slope": cv.get("slope", "N/A"),
                          "conductivity": cv.get("conductivity", "N/A"), "cn": cn, "hg": hg}
            c1, c2 = st.columns(2)
            with c1:
                if PDF_OK:
                    try:
                        pdf_bytes = generate_pdf_report(
                            site_info=_site_info, drastic=idx, drastic_t=dt_res["drastic_t"], level=t(dt_res["level"]),
                            recommendation=t(current_risk["action"]) if current_risk else "—",
                            cn_score=dt_res["cn_score"], hg_score=dt_res["hg_score"], base_bonus=dt_res["base_bonus"],
                            source_factor=dt_res["source_factor"], toxicity_bonus=dt_res["toxicity_bonus"], cn_value=cn, hg_value=hg)
                        if pdf_bytes:
                            st.download_button("📄 تحميل PDF", data=pdf_bytes, file_name=f"report_{site_key_current}.pdf",
                                               mime="application/pdf", key="download_pdf_btn")
                        else:
                            st.info("تثبيت fpdf2 مطلوب")
                    except Exception as e:
                        st.warning(f"تعذر PDF: {str(e)[:80]}")
                else:
                    st.info("📄 PDF: يتطلب fpdf2")
            with c2:
                if EXCEL_OK:
                    try:
                        excel_bytes = generate_excel_report(
                            site_info={**_site_info, "aquifer": cv.get("aquifer", "—"), "soil": cv.get("soil", "—"),
                                       "vadose": cv.get("vadose", "—"),
                                       "D_rating": get_d_rating(cv.get("depth", 15)), "R_rating": get_r_rating(cv.get("recharge", 100)),
                                       "A_rating": get_a_rating(cv.get("aquifer", "massive_sandstone")),
                                       "S_rating": get_s_rating(cv.get("soil", "sand")), "T_rating": get_t_rating(cv.get("slope", 4)),
                                       "I_rating": get_i_rating(cv.get("vadose", "sand_gravel")),
                                       "C_rating": get_c_rating(cv.get("conductivity", 5))},
                            drastic_result=dt_res, risk_info=current_risk if current_risk else classify(idx),
                            mining_type=mt_key, spsa_result=st.session_state.get("spsa_result"),
                            mc_result=st.session_state.get("mc_result"))
                        if excel_bytes:
                            st.download_button("📊 تحميل Excel", data=excel_bytes, file_name=f"report_{site_key_current}.xlsx",
                                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                               key="download_excel_btn")
                        else:
                            st.info("openpyxl مطلوب")
                    except Exception as e:
                        st.warning(f"تعذر Excel: {str(e)[:80]}")
                else:
                    st.info("📊 Excel: يتطلب excel_exporter.py")

    # ------------------------------------------------------------- 5: الخريطة الحرارية
    with tabs[5]:
        st.markdown(f'<div class="section-header"><h3>{t("heatmap_title")}</h3></div>', unsafe_allow_html=True)
        st.info(t("shows_verified_only") + f" ({n_sites_verified})")
        st.caption(tx("الطبقة الحرارية للعرض البصري فقط (كثافة النقاط مُوزَّنة بالمؤشر) وليست نموذج استيفاء. للاستيفاء استخدم تبويب GIS Raster.",
                      "The heat layer is a visual aid (point density weighted by the index), not an interpolation model. Use the GIS Raster tab for interpolation."))
        if not DS_OK:
            st.error("data_sources.py")
        else:
            c1, c2 = st.columns(2)
            with c1: mm = st.radio(t("view_mode"), [t("both"), t("markers"), t("heat")], key="map_mode_radio", horizontal=True)
            with c2: mh = st.slider(t("height"), 400, 900, 600, 50, key="map_height_slider")
            with st.spinner(t("calculating")):
                mapa, stats, df_sites = build_heatmap_verified(show_heat=mm in [t("both"), t("heat")],
                                                               show_markers=mm in [t("both"), t("markers")])
            st_folium(mapa, height=mh, key="map_folium_v61", use_container_width=True)
            st.markdown("---")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric(t("low"), stats["low"]); c2.metric(t("medium"), stats["medium"])
            c3.metric(t("high"), stats["high"]); c4.metric(t("very_high"), stats["very_high"]); c5.metric(t("total"), sum(stats.values()))
            st.dataframe(df_sites, use_container_width=True)
            st.download_button(t("download_sites"), data=df_sites.to_csv(index=False).encode("utf-8-sig"),
                               file_name="verified_sites.csv", mime="text/csv", key="download_sites_btn")

    # ------------------------------------------------------------- 6: الحساسية
    with tabs[6]:
        st.markdown(f'<div class="section-header"><h3>{t("sensitivity_title")}</h3></div>', unsafe_allow_html=True)
        st.info(t("sensitivity_hint"))
        if "cv" not in st.session_state:
            st.warning(t("site_selection"))
        else:
            sub_sens = st.tabs([t("spsa_tab"), t("variation_tab")])
            with sub_sens[0]:
                st.markdown(f"#### {t('spsa_title')}")
                st.markdown(f'<div class="research-note"><b>{t("reference")}:</b> Napolitano &amp; Fabbri (1996)<br><b>{t("formula")}:</b> Si = (Wi × Ri / DI) × 100</div>', unsafe_allow_html=True)
                st.info(t("spsa_explanation"))
                if st.button("🚀 " + t("run_spsa"), type="primary", key="run_spsa_btn"):
                    with st.spinner(t("calculating")):
                        st.session_state["spsa_result"] = at.spsa_analysis(st.session_state["cv"])
                if "spsa_result" in st.session_state:
                    spsa = st.session_state["spsa_result"]
                    st.success(f"🏆 {t('most_influential')}: **{spsa['most_influential']}** | {t('base_index')}: **{spsa['base_index']}**")
                    st.dataframe(pd.DataFrame([{t("parameter"): p["param"], t("weight_wi"): p["weight"], t("rating_ri"): p["rating"],
                                                t("weighted"): p["weighted_score"], t("theoretical_pct"): f"{p['theoretical_pct']}%",
                                                t("effective_pct"): f"{p['effective_pct']}%", t("difference"): f"{p['difference']:+.2f}%"}
                                               for p in spsa["parameters"]]), use_container_width=True, hide_index=True)
                    st.caption(tx("الفرق السالب لا يعني أن المعامل «غير مؤثر»، بل أن وزنه الفعلي أقل من النظري عند هذا الموقع.",
                                  "A negative difference does not mean the parameter is unimportant: its effective weight is below the theoretical one at this site."))
                    try:
                        import plotly.graph_objects as go
                        fig = go.Figure()
                        _p = [p["param"] for p in spsa["parameters"]]
                        fig.add_trace(go.Bar(name=t("theoretical_pct"), x=_p, y=[p["theoretical_pct"] for p in spsa["parameters"]], marker_color="#c19a6b"))
                        fig.add_trace(go.Bar(name=t("effective_pct"), x=_p, y=[p["effective_pct"] for p in spsa["parameters"]], marker_color="#5c2c16"))
                        fig.update_layout(barmode="group", height=400, xaxis_title=t("parameter"), yaxis_title="%")
                        st.plotly_chart(fig, use_container_width=True, key="spsa_chart")
                    except Exception:
                        pass
            with sub_sens[1]:
                st.markdown(f"#### {t('variation_title')}")
                st.info(t("variation_explanation"))
                vp = st.slider(t("change_pct"), 5, 30, 10, 5, key="sens_var_pct_slider")
                if st.button("🚀 " + t("run"), type="primary", key="run_sens_btn"):
                    with st.spinner(t("calculating")):
                        st.session_state["sens_result"] = at.sensitivity_analysis(st.session_state["cv"], vp / 100.0)
                if "sens_result" in st.session_state:
                    sens = st.session_state["sens_result"]
                    st.success(f"{t('most_sensitive')}: {sens['most_sensitive']}")
                    st.dataframe(pd.DataFrame([{t("parameter"): p, t("original_value"): d["original_phys"], t("modified_value"): d["modified_phys"],
                                                t("new_index"): d["new_index"], t("change"): d["change"], t("sensitivity_pct"): d["sensitivity"]}
                                               for p, d in sens["parameters"].items()]), use_container_width=True, hide_index=True)

    # ------------------------------------------------------------- 7: السمّية
    with tabs[7]:
        st.markdown(f'<div class="section-header"><h3>{t("toxicity_title")}</h3></div>', unsafe_allow_html=True)
        if "cv" not in st.session_state:
            st.warning(t("site_selection"))
        else:
            cv = st.session_state["cv"]
            hgw, cnw = cv.get("hg_water_mg_l", 0.011), cv.get("cn_water_mg_l", 0.025)
            c1, c2 = st.columns(2)
            c1.metric("CN", f"{cnw} mg/L"); c2.metric("Hg", f"{hgw} mg/L")
            st.caption(tx("حدّ التربة غير مُدرج: لا يوجد في المشروع حدّ تربة بمصدر موثَّق (كان العامل القديم 1.0–1.5 افتراضياً).",
                          "No soil term: the project has no sourced soil limit (the old 1.0–1.5 soil factor was an assumption)."))
            if st.button(t("analyze"), type="primary", key="run_tox_btn"):
                _mt = st.session_state.get("mining_type", "traditional")
                st.session_state["tox_result"] = at.weighted_toxicity(hgw, 0.0, cnw, 0.0, mining_type=_mt, **tox_kw(_mt))
            if "tox_result" in st.session_state:
                tox = st.session_state["tox_result"]
                c1, c2, c3 = st.columns(3)
                c1.metric(t("cn_score"), tox["cn_score"]); c2.metric(t("hg_score"), tox["hg_score"]); c3.metric(t("base_bonus"), tox["base_bonus"])
                c1, c2, c3 = st.columns(3)
                c1.metric(t("source_factor") + " (SF)", tox["source_factor"]); c2.metric("HQ max", tox["max_hq"]); c3.metric(t("category"), t(tox["category"]))
                st.metric(t("action"), t(tox["action"]))
                if "ci" in st.session_state:
                    st.markdown("---")
                    show_two_axis(st.session_state["ci"], cnw, hgw)

    # ------------------------------------------------------------- 8: جدول GIS
    with tabs[8]:
        st.markdown(f'<div class="section-header"><h3>{t("gis_title")}</h3></div>', unsafe_allow_html=True)
        if not DS_OK:
            st.error("data_sources.py")
        else:
            fm = st.radio(t("view_mode"), [t("all"), t("verified_only"), t("display_only_filter")], horizontal=True, key="gis_filter_radio")
            try:
                df_all = get_all_sites_as_dataframe()
                df_show = (df_all[df_all["verified"] == True] if fm == t("verified_only")
                           else df_all[df_all["verified"] == False] if fm == t("display_only_filter") else df_all)
                st.caption(f"{len(df_show)} {t('sites')}")
                st.dataframe(df_show, use_container_width=True)
                st.download_button("📥 CSV", data=df_show.to_csv(index=False).encode("utf-8-sig"), file_name="sites_filtered.csv",
                                   mime="text/csv", key="download_gis_csv_btn")
            except Exception as e:
                st.error(str(e))

    # ------------------------------------------------------------- 9: Monte Carlo
    with tabs[9]:
        st.markdown(f'<div class="section-header"><h3>{t("mc_title")}</h3></div>', unsafe_allow_html=True)
        if "ci" not in st.session_state:
            st.warning(t("site_selection"))
        else:
            ni = st.slider(t("simulations"), 100, 5000, 1000, 100, key="mc_n_iter_slider")
            vp = st.slider(t("variation"), 5, 30, 15, 5, key="mc_var_pct_slider")
            if st.button(t("run"), type="primary", key="run_mc_btn"):
                _mt = st.session_state.get("mining_type", "traditional")
                _cw = CALIBRATED_WEIGHTS if (CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == _mt) else None
                st.session_state["mc_result"] = at.monte_carlo_analysis(st.session_state["cv"], ni, vp / 100.0, mining_type=_mt, calibrated_weights=_cw)
            if "mc_result" in st.session_state:
                mc = st.session_state["mc_result"]
                st.caption(tx("النتيجة تعكس عدم اليقين المفترض في المدخلات (توزيعات اختارها المستخدم) وليس عدم اليقين الميداني.",
                              "The result reflects the ASSUMED input uncertainty (user-chosen distributions), not field uncertainty."))
                st.markdown("#### DRASTIC")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(t("mean"), mc["mean"]); c2.metric(t("std"), mc["std"])
                c3.metric(t("ci_90"), f"{mc['ci_90'][0]}-{mc['ci_90'][1]}"); c4.metric("P>140", f"{mc['prob_over_140']}%")
                st.markdown("#### DRASTIC-Tox")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(t("mean"), mc["tox_mean"]); c2.metric(t("std"), mc["tox_std"])
                c3.metric(t("ci_90"), f"{mc['tox_ci_90'][0]}-{mc['tox_ci_90'][1]}"); c4.metric("P>140", f"{mc['tox_prob_over_140']}%")

    # ------------------------------------------------------------- 10: مقاييس وصفية
    with tabs[10]:
        st.markdown(f'<div class="section-header"><h3>{t("advanced_title")}</h3></div>', unsafe_allow_html=True)
        st.warning(tx("هذه مقاييس وصفية على نفس البيانات وبعتبة مُدخلة: متفائلة. الأرقام الصادقة (leave-one-location-out وفواصل الثقة) في تبويب External Validation.",
                      "These are descriptive metrics on the same data at a typed threshold: optimistic. Honest numbers (leave-one-location-out with CIs) are in the External Validation tab."))
        df_val = st.session_state.get("df_validation")
        if not ADV_OK:
            st.error("advanced_modules.py")
        elif df_val is None:
            st.warning(t("upload_validation_first"))
        elif not ("cn_water_mg_l" in df_val.columns and "hg_water_mg_l" in df_val.columns):
            st.error(t("file_missing_tox"))
        else:
            mt = st.session_state.get("mining_type", "traditional")
            c1, c2 = st.columns(2)
            with c1: th_d = st.number_input("DRASTIC:", 50, 200, 140, 5, key="adv_th_d_input")
            with c2: th_dt = st.number_input("DRASTIC-Tox:", 50, 280, int(DEFAULT_TOX_THRESHOLD), 5, key="adv_th_dt_input")
            scored, errs = add_indices(df_val, mt)
            ok = scored.dropna(subset=["DRASTIC", "DRASTIC_Tox"])
            for e in errs[:10]:
                st.error(tx("خطأ في الصف ", "Row error ") + e)
            if len(ok) == 0 or "actual_contaminated" not in ok.columns or ok["actual_contaminated"].nunique() < 2:
                st.error(t("no_file"))
            elif st.button("🚀 " + t("run"), type="primary", key="run_adv_btn"):
                y = ok["actual_contaminated"].astype(int).tolist()
                st.session_state["adv_results"] = {"d": am.calculate_confusion_matrix(ok["DRASTIC"].tolist(), y, th_d),
                                                   "dt": am.calculate_confusion_matrix(ok["DRASTIC_Tox"].tolist(), y, th_dt)}
            if "adv_results" in st.session_state:
                r = st.session_state["adv_results"]
                c1, c2 = st.columns(2)
                for col, key, name in ((c1, "d", "DRASTIC"), (c2, "dt", "DRASTIC-Tox")):
                    with col:
                        st.markdown(f"#### {name}")
                        m = r[key]
                        st.metric(t("kappa"), m["kappa"]); st.metric("MCC", m["mcc"]); st.metric(t("f1_score"), m["f1_score"])
                        st.metric(t("recall"), f"{m['recall']}%"); st.metric(tx("النوعية", "Specificity"), f"{m['specificity']}%")
                        with st.expander(t("confusion_matrix")):
                            cm = m["confusion_matrix"]
                            st.write(f"TP={cm['TP']} TN={cm['TN']} FP={cm['FP']} FN={cm['FN']}")

    # ------------------------------------------------------------- 11: تطوير النموذج
    with tabs[11]:
        st.markdown(f'<div class="section-header"><h3>{t("development_title")}</h3></div>', unsafe_allow_html=True)
        if not DEV_OK:
            st.error(t("no_dev_module"))
        else:
            sub = st.tabs([t("gray_zone"), t("calibration_ab"), t("model_comparison")])
            with sub[0]:
                st.markdown(f"#### {t('gray_zone')}")
                st.error(tx("⚠️ مواقع اصطناعية (Synthetic) لاختبار البرنامج فقط. أُزيلت من المعايرة والتحقق: تسميات «ملوث/نظيف» فيها مُختلَقة وتتناقض مع تراكيزها.",
                            "⚠️ Synthetic sites for SOFTWARE TESTING only. Removed from calibration and validation: their contaminated/clean labels are invented and contradict their concentrations."))
                if DS_OK:
                    gray_rows = [{"Site": sd.get("name_ar", sk), "D": sd["depth_m"], "R": sd["recharge_mm"], "CN": sd["cn_water_mg_l"],
                                  "Hg": sd["hg_water_mg_l"], "Status": t("contaminated") if sd["actual_contaminated"] == 1 else t("clean")}
                                 for sdata in GRAY_ZONE_SITES.values() for sk, sd in sdata.get("sites", {}).items()]
                    st.dataframe(pd.DataFrame(gray_rows), use_container_width=True, hide_index=True)
                    st.markdown("---")
                    st.caption(tx("مجموعة المعايرة الوحيدة: المواقع الموثَّقة، غير التقديرية، غير الاصطناعية.",
                                  "The ONLY calibration set: verified, non-estimate, non-synthetic sites."))
                    if st.button("🔄 " + t("load_data"), type="primary", key="load_combined_btn"):
                        df_c, _errs = add_indices(get_calibration_dataset(), "traditional")
                        st.session_state["df_combined"] = df_c
                        st.rerun()
                if "df_combined" in st.session_state:
                    df_s = st.session_state["df_combined"]
                    st.dataframe(df_s, use_container_width=True)
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(t("total_sites"), len(df_s))
                    c2.metric(tx("مواقع مستقلة", "Independent locations"), df_s["location_id"].nunique() if "location_id" in df_s.columns else len(df_s))
                    c3.metric(t("verified_sites"), safe_sum(df_s, "verified", 0))
                    c4.metric(t("contaminated_sites"), safe_sum(df_s, "actual_contaminated", 0))
            with sub[1]:
                st.markdown(f"#### {t('calibration_ab')}")
                df_c = get_loaded_df("df_combined", "df_validation")
                if df_c is None:
                    st.warning(t("calibrate_hint"))
                else:
                    c1, c2 = st.columns(2)
                    with c1:
                        amin = st.slider(t("alpha_min"), 0.0, 1.0, 0.1, 0.1, key="cal_a_min_slider")
                        amax = st.slider(t("alpha_max"), 0.0, 1.0, 1.0, 0.1, key="cal_a_max_slider")
                    with c2:
                        bmin = st.slider(t("beta_min"), 0.0, 1.0, 0.1, 0.1, key="cal_b_min_slider")
                        bmax = st.slider(t("beta_max"), 0.0, 1.0, 1.0, 0.1, key="cal_b_max_slider")
                    if st.button("🚀 " + t("run_calibration"), type="primary", key="run_cal_btn"):
                        with st.spinner(t("searching")):
                            st.session_state["cal_result"] = md.calibrate_alpha_beta(
                                df_c, {}, alpha_range=[round(float(v), 2) for v in np.arange(amin, amax + 0.05, 0.1)],
                                beta_range=[round(float(v), 2) for v in np.arange(bmin, bmax + 0.05, 0.1)])
                    if "cal_result" in st.session_state:
                        res = st.session_state["cal_result"]
                        if "error" in res:
                            st.error(res["error"])
                        else:
                            c1, c2 = st.columns(2)
                            for col, key, title in ((c1, "best_kappa", t("best_kappa")), (c2, "best_balanced", t("balanced"))):
                                with col:
                                    st.markdown(f"#### {title}")
                                    b = res[key]
                                    st.metric("alpha", b["alpha"]); st.metric("beta", b["beta"])
                                    st.metric(t("kappa"), b["kappa"]); st.metric(t("recall"), f"{b['recall']}%")
                            if res.get("note"):
                                st.caption(res["note"])
            with sub[2]:
                st.markdown(f"#### {t('model_comparison')}")
                df_c = get_loaded_df("df_combined", "df_validation")
                if df_c is None:
                    st.warning(t("calibrate_hint"))
                else:
                    if st.button("🚀 " + t("run"), type="primary", key="run_cmp_btn"):
                        with st.spinner(t("calculating")):
                            st.session_state["cmp_results"] = md.compare_models(
                                df_c, (get_d_rating, get_r_rating, get_a_rating, get_s_rating, get_t_rating, get_i_rating, get_c_rating), calc_index)
                    if "cmp_results" in st.session_state:
                        rows = [{"Model": mn, t("kappa"): m["kappa"], t("recall"): m["recall"], t("precision"): m["precision"],
                                 t("accuracy"): m["accuracy"], "ROC-AUC": m["auc"]}
                                for mn, m in st.session_state["cmp_results"].items() if isinstance(m, dict) and "kappa" in m]
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                        st.caption(tx("كل نموذج يُقيَّم خارج الموقع (leave-one-location-out) بعتبة تُحسب داخل الطيّة. نموذج «CN + Hg فقط» خط أساس: إن تفوّق على DRASTIC فالتسمية مرتبطة بالتراكيز لا بالهشاشة.",
                                      "Each model is scored out-of-location (leave-one-location-out) with a threshold fitted in-fold. The 'CN + Hg only' model is a baseline: if it beats DRASTIC, the label follows concentrations, not vulnerability."))

    # ------------------------------------------------------------- 12: خرائط تلقائية
    with tabs[12]:
        st.markdown(f'<div class="section-header"><h3>{t("tab_auto_maps")}</h3></div>', unsafe_allow_html=True)
        if not MAPS_OK:
            st.error("auto_maps.py")
        else:
            df_s = get_loaded_df("df_combined", "df_validation")
            if df_s is None:
                st.warning(t("no_file"))
            else:
                if st.button("🎨 " + t("run"), type="primary", key="gen_maps_btn"):
                    with st.spinner(t("calculating")):
                        try:
                            df_m, _errs = add_indices(df_s, "traditional")
                            df_m = df_m.dropna(subset=["DRASTIC", "DRASTIC_Tox"])
                            if "coords" in df_m.columns and "lon" not in df_m.columns:
                                df_m["lat"] = df_m["coords"].apply(lambda c: c[0] if isinstance(c, (tuple, list)) and len(c) >= 2 else None)
                                df_m["lon"] = df_m["coords"].apply(lambda c: c[1] if isinstance(c, (tuple, list)) and len(c) >= 2 else None)
                            df_m = df_m.rename(columns={"cn_water_mg_l": "CN", "hg_water_mg_l": "Hg"})
                            df_p = prepare_df_for_maps(df_m, (get_d_rating, get_r_rating, get_a_rating, get_s_rating, get_t_rating, get_i_rating, get_c_rating))
                            st.session_state["auto_maps_fig"] = generate_auto_maps(df_p, show_sudan=True)
                        except Exception as e:
                            st.error(str(e))
                if "auto_maps_fig" in st.session_state:
                    st.plotly_chart(st.session_state["auto_maps_fig"], use_container_width=True, key="auto_maps_chart_v61")
                    st.download_button("📥 HTML", data=st.session_state["auto_maps_fig"].to_html(include_plotlyjs="cdn").encode("utf-8"),
                                       file_name="auto_maps.html", mime="text/html", key="download_maps_html_btn")

    # ------------------------------------------------------------- 13: المعايرة التلقائية
    with tabs[13]:
        st.markdown(f'<div class="section-header"><h3>{t("auto_calibration")}</h3></div>', unsafe_allow_html=True)
        if not AUTOCAL_OK:
            st.error("auto_calibration.py")
        else:
            if SCOPE_KEY == "industrial" and INDUSTRIAL_SITES:
                df_c = pd.DataFrame(INDUSTRIAL_SITES)
            else:
                df_c = get_loaded_df("df_validation", "df_bulk", "df_combined")
                if df_c is None and DS_OK:
                    df_c = get_calibration_dataset()
                    st.info(tx("لم يُرفع ملف: تُستخدم مجموعة المعايرة الموثَّقة من قاعدة البيانات.",
                               "No file uploaded: using the verified calibration set from the database."))
            req = ["depth_m", "recharge_mm", "slope_pct", "conductivity", "aquifer", "soil", "vadose",
                   "cn_water_mg_l", "hg_water_mg_l", "actual_contaminated"]
            miss = [x for x in req if df_c is None or x not in df_c.columns]
            if df_c is None:
                st.warning(t("upload_validation_first"))
            elif miss:
                st.error(f"Missing: {miss}")
            else:
                st.success(f"{t('file_has')} {len(df_c)} {t('sites')}")
                st.warning(tx("⚠️ مع عدد مواقع صغير تُعتبر الأوزان المعايَرة استكشافية. الرقم المعروض هو تقدير leave-one-location-out وليس kappa التدريب.",
                              "⚠️ With few sites calibrated weights are exploratory. The number shown is a leave-one-location-out estimate, not the training kappa."))
                if WM_OK and detect_ceiling_effect(df_c, SCOPE_KEY if SCOPE_KEY != "all" else "traditional"):
                    st.warning("Ceiling Effect detected — calibrated weights may be unreliable.")
                c1, c2 = st.columns(2)
                with c1: mc = st.selectbox(t("mining_pattern"), ["traditional", "industrial", "mixed"], key="cal_mining_type_select")
                with c2: ns = st.slider(t("search_precision"), 10, 30, 15, 5, key="cal_n_steps_slider")
                b1, b2, b3 = st.columns(3)
                with b1: rc = st.button("🚀 " + t("run_auto_calibration"), type="primary", key="run_auto_cal_btn", use_container_width=True)
                with b2: rcm = st.button("📊 " + t("compare"), key="run_compare_btn", use_container_width=True)
                with b3: rst = st.button("🔄 " + t("reset"), key="reset_weights_btn", use_container_width=True)
                if rst:
                    for k in ["auto_cal_result", "auto_cal_mining_type", "comparison_result"]:
                        st.session_state.pop(k, None)
                    st.success(t("reset_done")); st.rerun()
                if rcm:
                    with st.spinner(t("calculating")):
                        cmp = compare_with_defaults(df_c, mc)
                    st.error(cmp["error"]) if "error" in cmp else st.session_state.__setitem__("comparison_result", cmp)
                if rc:
                    with st.spinner(f"{t('searching')} {ns ** 2:,}..."):
                        result = auto_calibrate_weights(df_c, mc, n_steps=ns)
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.session_state["auto_cal_result"] = result
                        st.session_state["auto_cal_mining_type"] = mc
                        if WM_OK:
                            pk = save_calibrated_profile(mc, result, len(df_c))
                            st.success(f"{t('kappa')} (LOLO) = {result['best_kappa']} — {tx('حُفظ (غير مُفعَّل)', 'Saved (not activated)')}: {pk}")
                if "comparison_result" in st.session_state:
                    cmp = st.session_state["comparison_result"]
                    c1, c2, c3 = st.columns(3)
                    c1.metric(t("default_kappa"), cmp["default_kappa"])
                    c2.metric(t("calibrated_kappa"), cmp["best_kappa"] if cmp.get("best_kappa") is not None else "-",
                              delta=f"{cmp.get('improvement', 0):+.4f}" if cmp.get("best_kappa") is not None else None)
                    c3.metric(t("recall"), f"{cmp.get('best_recall', 0)}%")
                    st.caption(tx("المقارنة بنفس الطريقة لكلا النموذجين (leave-one-location-out، عتبة داخل الطيّة).",
                                  "Both models are evaluated the same way (leave-one-location-out, in-fold threshold)."))
                if "auto_cal_result" in st.session_state:
                    res = st.session_state["auto_cal_result"]
                    interp = res.get("kappa_interpretation", {})
                    st.markdown(f"### {t('result')} - {mt_label(st.session_state.get('auto_cal_mining_type', 'traditional'))}")
                    kc = {"ممتاز": "kappa-excellent", "جيد": "kappa-good", "متوسط": "kappa-moderate", "مقبول": "kappa-fair"}.get(interp.get("level"), "kappa-poor")
                    st.markdown(f'<div class="kappa-box {kc}"><div style="font-size:0.9em;opacity:0.9;">{t("kappa")} (leave-one-location-out)</div>'
                                f'<div style="font-size:3em;font-weight:700;margin:8px 0;">{res["best_kappa"]}</div>'
                                f'<div style="font-size:1.3em;font-weight:600;">{interp.get("level", "-")} - {interp.get("en", "-")}</div></div>', unsafe_allow_html=True)
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("α (CN)", res["best_alpha"]); c2.metric("β (Hg)", res["best_beta"])
                    c3.metric(tx("العتبة المُقدَّرة", "Fitted threshold"), res.get("threshold"))
                    c4.metric(tx("مواقع مستقلة", "Locations"), res.get("n_locations", "-"))
                    c1, c2 = st.columns(2)
                    c1.metric(tx("kappa على بيانات التدريب (متفائل)", "Training kappa (optimistic)"), res.get("resubstitution_kappa"))
                    c2.metric(tx("kappa بتقسيم الصفوف (متسرّب)", "Row-wise kappa (leaky)"), (res.get("cv_naive_leaky") or {}).get("kappa"))
                    for w in res.get("warnings", []):
                        st.warning(w)
                    st.info(tx("لتفعيل الأوزان المحفوظة اذهب إلى تبويب Profiles.", "To activate the saved weights go to the Profiles tab."))

    # ------------------------------------------------------------- 14: العتبة المثلى
    with tabs[14]:
        st.markdown(f'<div class="section-header"><h3>{t("optimal_threshold_title")}</h3></div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="research-note"><b>{t('references')}:</b><br>• Youden (1950)<br>• Landis &amp; Koch (1977)</div>""", unsafe_allow_html=True)
        if not AUTOCAL_OK:
            st.error("auto_calibration.py")
        else:
            if SCOPE_KEY == "industrial" and INDUSTRIAL_SITES:
                df_o = pd.DataFrame(INDUSTRIAL_SITES)
            else:
                df_o = get_loaded_df("df_validation", "df_combined")
                if df_o is None and DS_OK:
                    df_o = get_calibration_dataset()
            if df_o is None:
                st.warning(t("upload_validation_first"))
            else:
                mto = st.selectbox(t("mining_pattern"), ["traditional", "industrial", "mixed"], key="opt_mining_type_select")
                uc = False
                if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mto:
                    uc = st.checkbox(f"{t('use_calibrated_weights')}", value=True, key="use_calibrated_for_opt_chk")
                if st.button("🚀 " + t("compute_threshold"), type="primary", key="run_opt_threshold_btn"):
                    with st.spinner(t("calculating")):
                        try:
                            st.session_state["opt_threshold_result"] = (
                                find_optimal_threshold(df_o, mto, alpha=CALIBRATED_WEIGHTS["alpha"], beta=CALIBRATED_WEIGHTS["beta"], SF=CALIBRATED_WEIGHTS["SF"])
                                if uc and CALIBRATED_WEIGHTS else find_optimal_threshold(df_o, mto))
                        except Exception as e:
                            st.error(str(e))
                if "opt_threshold_result" in st.session_state:
                    res = st.session_state["opt_threshold_result"]
                    if "error" in res:
                        st.error(res["error"])
                    else:
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric(t("threshold"), res["optimal_threshold"]); c2.metric("Youden J", res["J_max"])
                        c3.metric(t("sensitivity"), res["sensitivity"]); c4.metric(t("specificity"), res["specificity"])
                        st.metric(tx("فاصل ثقة 95% للعتبة (bootstrap)", "Threshold 95% CI (bootstrap)"), str(res.get("threshold_ci_95")))
                        st.caption(res.get("note", ""))

    # ------------------------------------------------------------- 15: ملفات الأوزان
    with tabs[15]:
        st.markdown('<div class="section-header"><h3>⚙️ Weight Profiles Manager</h3></div>', unsafe_allow_html=True)
        if not WM_OK:
            st.error("weight_manager.py not installed")
        else:
            mining_filter = st.radio("Mining Type:", ["traditional", "industrial", "mixed"], format_func=mt_label,
                                     key="profile_filter", horizontal=True)
            profiles = get_all_profiles()
            active = get_active_profile(mining_filter)
            filtered = {k: v for k, v in profiles.items() if v.get("mining_type") == mining_filter}
            stale = get_stale_profiles()
            if stale:
                st.warning(tx(f"تُجوهلت {len(stale)} ملفات محفوظة بصيغة قديمة: {', '.join(stale)}. أعد المعايرة.",
                              f"{len(stale)} profile(s) saved with an older formula were ignored: {', '.join(stale)}. Recalibrate."))
            st.markdown(f"#### Available Profiles: {len(filtered)}")
            st.caption(tx("الملف الافتراضي أوزان متساوية (فرضية صفرية)، وليس نتيجة أدبيات أو بيانات.",
                          "The default profile is equal weights (a null assumption), not a literature or data result."))
            for key, prof in filtered.items():
                is_active = active is not None and prof["alpha"] == active.get("alpha") and prof["beta"] == active.get("beta") and prof["SF"] == active.get("SF")
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"""<div style="background:{'#f1f8e9' if is_active else '#faf8f3'};border:2px solid {'#4caf50' if is_active else '#e0d4b8'};border-radius:10px;padding:16px;margin:8px 0;">
                    <h4 style="color:#5c2c16;margin:0;">{prof.get('name_ar', key)}</h4>
                    <p><b>alpha</b>={prof['alpha']} | <b>beta</b>={prof['beta']} | <b>SF</b>={prof['SF']} | kappa={prof.get('kappa')} | n={prof.get('n_sites')}</p></div>""", unsafe_allow_html=True)
                    for w in prof.get("warnings", []):
                        st.caption("⚠️ " + w)
                with col2:
                    if not is_active:
                        if st.button("Activate", key=f"act_{key}", use_container_width=True):
                            set_active_profile(key); st.success("Activated"); st.rerun()
                    else:
                        st.success("Active")

    # ------------------------------------------------------------- 16: التحقق الخارجي
    with tabs[16]:
        st.markdown('<div class="section-header"><h3>🔬 External / Nested Validation</h3></div>', unsafe_allow_html=True)
        if not EXT_VAL_OK:
            st.error("external_validation.py not installed")
        else:
            df_ext = get_loaded_df("df_validation", "df_combined", "df_bulk")
            if df_ext is None and DS_OK:
                df_ext = get_calibration_dataset()
                st.info(tx("لم يُرفع ملف: تُستخدم مجموعة المعايرة الموثَّقة.", "No file uploaded: using the verified calibration set."))
            req_cols = ["depth_m", "recharge_mm", "slope_pct", "conductivity", "aquifer", "soil", "vadose",
                        "cn_water_mg_l", "hg_water_mg_l", "actual_contaminated"]
            miss = [c for c in req_cols if df_ext is None or c not in df_ext.columns]
            if df_ext is None:
                st.warning("Upload validation file first")
            elif miss:
                st.error(f"Missing: {miss}")
            else:
                st.success(f"Data loaded: {len(df_ext)} sites")
                st.markdown(tx("**المنهج:** leave-one-location-out متداخل — الأوزان والعتبة تُقدَّر على بقية المواقع فقط، وصفوف جاف/رطب لموقع واحد لا تُفصل أبداً.",
                               "**Method:** nested leave-one-location-out — weights and threshold are fitted on the other locations only; Dry/Wet rows of one place are never split."))
                mt_ext = st.selectbox("Mining Type", ["traditional", "industrial", "mixed"], key="ext_mining_type")
                if st.button("🚀 Run Validation", type="primary", key="run_ext_val_btn"):
                    with st.spinner("Running..."):
                        cal_w = CALIBRATED_WEIGHTS if (CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mt_ext) else None
                        st.session_state["ext_val_result"] = ev.external_validation_analysis(
                            df_ext, mining_type=mt_ext, calc_index_fn=calc_index, calc_drastic_t_fn=calc_drastic_t,
                            get_d_rating_fn=get_d_rating, get_r_rating_fn=get_r_rating, get_a_rating_fn=get_a_rating,
                            get_s_rating_fn=get_s_rating, get_t_rating_fn=get_t_rating, get_i_rating_fn=get_i_rating,
                            get_c_rating_fn=get_c_rating, calibrated_weights=cal_w, sklearn_ok=True)
                if "ext_val_result" in st.session_state:
                    r = st.session_state["ext_val_result"]
                    if "error" in r:
                        st.error(r["error"])
                    else:
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Rows", r["n_total"]); c2.metric(tx("مواقع مستقلة", "Locations"), r.get("n_locations"))
                        c3.metric(tx("مواقع ملوثة", "Contaminated loc."), r.get("n_pos_locations")); c4.metric(tx("مواقع نظيفة", "Clean loc."), r.get("n_neg_locations"))
                        st.caption(f"{tx('المنهج', 'Scheme')}: {r.get('scheme')}")
                        for w in r.get("warnings", []):
                            st.warning(w)
                        rows = [{"Model": m.get("name", k), "Kappa": m.get("kappa"), "Kappa 95% CI": str(m.get("kappa_ci_95")),
                                 "ROC-AUC": m.get("auc"), "PR-AUC": m.get("pr_auc"), "Recall %": m.get("recall"),
                                 "Specificity %": m.get("specificity"), "Accuracy %": m.get("accuracy")}
                                for k, m in r["models"].items() if isinstance(m, dict) and "kappa" in m]
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                        st.info(tx("قارن DRASTIC بنماذج «التركيز فقط». إن كانت الأخيرة أفضل أو مساوية فإضافة الهيدروجيولوجيا لا تُحسّن التنبؤ بالتسمية الحالية (التسمية مرتبطة بالتراكيز).",
                                   "Compare DRASTIC with the concentration-only models. If those are as good or better, hydrogeology adds nothing to predicting the current labels (the labels follow concentrations)."))
                        if r.get("leaky_row_out_tox_equal"):
                            lk = r["leaky_row_out_tox_equal"]
                            st.caption(f"{tx('للمقارنة: تقسيم الصفوف المتسرّب (لا تستخدمه)', 'For comparison: leaky row-wise split (do not use)')}: kappa={lk.get('kappa')}, AUC={lk.get('auc')}")
                        if r.get("profile_weights_model"):
                            st.caption(f"{tx('الملف المعايَر النشط', 'Active calibrated profile')}: {r['profile_weights_model']}")
                        if r.get("site_table") is not None:
                            with st.expander(tx("جدول التنبؤ لكل موقع", "Per-site predictions")):
                                st.dataframe(r["site_table"], use_container_width=True)
                                st.download_button("📥 CSV", data=r["site_table"].to_csv(index=False).encode("utf-8-sig"),
                                                   file_name="validation_sites.csv", mime="text/csv", key="download_valsites_btn")

    # ------------------------------------------------------------- 17: GIS Raster
    with tabs[17]:
        st.markdown('<div class="section-header"><h3>🗺️ GIS Raster Interpolation</h3></div>', unsafe_allow_html=True)
        if not RASTER_OK:
            st.error("gis_raster.py not installed")
        else:
            st.warning(tx("⚠️ الاستيفاء بين عدد قليل من المواقع تقدير بصري. الخلايا الأبعد من المسافة المحددة عن أقرب عيّنة تُخفى. خرائط DRASTIC الحقيقية تستوفي المعاملات (العمق، التغذية…) من طبقات خام لا قيم المؤشر.",
                          "⚠️ Interpolating between a few sites is a visual estimate. Cells farther than the chosen distance from any sample are hidden. Real DRASTIC maps interpolate the parameters (depth, recharge…) from raw layers, not the index values."))
            df_raster = get_loaded_df("df_combined", "df_validation", "df_bulk")
            if df_raster is None and DS_OK:
                inc_est = st.checkbox(tx("تضمين المواقع التقديرية (للعرض فقط)", "Include estimated sites (display only)"), value=False, key="raster_incl_est")
                df_raster = get_all_sites_as_dataframe() if inc_est else get_calibration_dataset()
            if df_raster is not None and not df_raster.empty:
                df_raster = df_raster.copy()
                if "lat" not in df_raster.columns and "coords" in df_raster.columns:
                    df_raster["lat"] = df_raster["coords"].apply(lambda c: c[0] if isinstance(c, (tuple, list)) and len(c) >= 2 else None)
                    df_raster["lon"] = df_raster["coords"].apply(lambda c: c[1] if isinstance(c, (tuple, list)) and len(c) >= 2 else None)
                if "lat" in df_raster.columns and "lon" in df_raster.columns and not df_raster["lat"].isna().all():
                    st.success(f"Data loaded: {len(df_raster)} sites")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        param_choices = {"DRASTIC-Tox": "DRASTIC_Tox", "DRASTIC": "DRASTIC", "CN (mg/L)": "cn_water_mg_l", "Hg (mg/L)": "hg_water_mg_l",
                                         "Depth (m)": "depth_m", "Recharge (mm/yr)": "recharge_mm", "Conductivity (m/day)": "conductivity"}
                        param_label = st.selectbox("Parameter", list(param_choices.keys()), key="raster_param_select")
                        param_col = param_choices[param_label]
                    with c2: method = st.selectbox("Interpolation", ["IDW", "Kriging"], key="raster_method_select")
                    with c3: resolution = st.slider("Resolution", 30, 200, 80, 10, key="raster_resolution_slider")
                    c1, c2 = st.columns(2)
                    with c1:
                        power = st.slider("IDW Power", 1.0, 5.0, 2.0, 0.5, key="raster_idw_power_slider") if method == "IDW" else 2.0
                        variogram = "linear" if method == "IDW" else st.selectbox("Variogram", ["linear", "power", "gaussian", "spherical", "exponential"], key="raster_variogram_select")
                    with c2:
                        max_km = st.slider(tx("أقصى مسافة عن أقرب عيّنة (كم)", "Max distance from nearest sample (km)"), 25, 500, 150, 25, key="raster_maxdist_slider")
                    _mt_r = st.session_state.get("mining_type", "traditional")
                    scored_r, _errs = add_indices(df_raster, _mt_r) if param_col in ("DRASTIC", "DRASTIC_Tox") and "DRASTIC" not in df_raster.columns else (df_raster, [])
                    if param_col not in scored_r.columns:
                        st.error(f"Column not available: {param_col}")
                        points = []
                    else:
                        sub = scored_r.dropna(subset=["lat", "lon", param_col])
                        points = [(float(a), float(b), float(v)) for a, b, v in zip(sub["lat"], sub["lon"], sub[param_col])]
                    if len(points) >= 3:
                        st.caption(f"Valid points: {len(points)}")
                        if st.button("🎨 Generate Raster", type="primary", key="gen_raster_btn"):
                            with st.spinner(f"Interpolating via {method}..."):
                                result = gr.kriging_interpolation(points, resolution=resolution, variogram_model=variogram, max_distance_km=max_km) if method == "Kriging" else {"error": "idw"}
                                if "error" in result:
                                    if method == "Kriging":
                                        st.info(result["error"])
                                    result = gr.idw_interpolation(points, resolution=resolution, power=power, max_distance_km=max_km)
                                st.session_state["raster_result"] = result
                                st.session_state["raster_points"] = points
                        if "raster_result" in st.session_state:
                            result = st.session_state["raster_result"]
                            if "error" in result:
                                st.error(result["error"])
                            else:
                                for w in result.get("warnings", []):
                                    st.warning(w)
                                stats = gr.compute_raster_statistics(result)
                                c1, c2, c3, c4 = st.columns(4)
                                c1.metric("Min", round(stats["min"], 1)); c2.metric("Mean", round(stats["mean"], 1))
                                c3.metric("Max", round(stats["max"], 1)); c4.metric("Std Dev", round(stats["std"], 2))
                                c1, c2 = st.columns(2)
                                c1.metric(tx("نسبة الخلايا ذات البيانات", "Cells with data"), f"{round(stats.get('valid_cell_fraction', 0) * 100, 1)}%")
                                c2.metric(tx("المساحة المغطاة (كم²)", "Covered area (km²)"), f"{stats['coverage_km2']:,}")
                                fig = gr.create_raster_plotly(result, title=f"{param_label} — {result['method']}", colorscale="RdYlGn_r", points=st.session_state.get("raster_points"))
                                if fig:
                                    st.plotly_chart(fig, use_container_width=True, key="raster_plotly_chart")
                                if param_col in ("DRASTIC", "DRASTIC_Tox"):
                                    st.dataframe(pd.DataFrame(gr.classify_raster(result)).T, use_container_width=True)
                                try:
                                    _tmp = os.path.join(tempfile.gettempdir(), "raster_out.tif")
                                    _ex = gr.export_geotiff(result, _tmp)
                                    if _ex.get("success"):
                                        with open(_tmp, "rb") as fh:
                                            st.download_button("📥 GeoTIFF", data=fh.read(), file_name="raster.tif", mime="image/tiff", key="download_tif_btn")
                                    else:
                                        st.caption(_ex.get("message", ""))
                                except Exception as e:
                                    st.caption(str(e)[:80])

    # ------------------------------------------------------------- 18: بيانات حيّة
    with tabs[18]:
        st.markdown('<div class="section-header"><h3>🌐 Live API Data</h3></div>', unsafe_allow_html=True)
        if not LIVE_API_OK:
            st.error("live_apis.py not installed")
        else:
            use_current = st.checkbox("Use current site coordinates", value=True, key="live_use_current_chk")
            if use_current and "current_site_data" in st.session_state:
                _sd = st.session_state["current_site_data"]
                live_lat, live_lon = float(_sd.get("coords", (15.5, 32.5))[0]), float(_sd.get("coords", (15.5, 32.5))[1])
                st.success(f"Using: **{_sd.get('name_ar', 'Current Site')}** ({live_lat:.4f}, {live_lon:.4f})")
            else:
                c1, c2 = st.columns(2)
                with c1: live_lat = st.number_input("Latitude", -90.0, 90.0, 15.6, 0.01, format="%.4f", key="live_lat_input")
                with c2: live_lon = st.number_input("Longitude", -180.0, 180.0, 32.5, 0.01, format="%.4f", key="live_lon_input")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button("☁️ NASA POWER", type="primary", key="fetch_nasa_btn"):
                    with st.spinner("Fetching..."): st.session_state["live_nasa"] = fetch_nasa_power(live_lat, live_lon, years=3)
            with c2:
                if st.button("🌧️ Open-Meteo", type="primary", key="fetch_meteo_btn"):
                    with st.spinner("Fetching..."): st.session_state["live_meteo"] = fetch_open_meteo_precipitation(live_lat, live_lon, years=5)
            with c3:
                if st.button("⛰️ Elevation", type="primary", key="fetch_elev_btn"):
                    with st.spinner("Fetching..."): st.session_state["live_elev"] = fetch_elevation_grid(live_lat, live_lon, radius_km=5)
            with c4:
                if st.button("🪨 Soil", type="primary", key="fetch_soil_btn"):
                    with st.spinner("Fetching..."): st.session_state["live_soil"] = fetch_soilgrids(live_lat, live_lon)
            for _key, _title, _fields in (
                    ("live_nasa", "☁️ NASA POWER", (("Rainfall", "rainfall_mm_annual", "mm"), ("Temp", "temperature_c", "°C"), ("Humidity", "humidity_pct", "%"), ("Wind", "wind_speed_ms", "m/s"))),
                    ("live_meteo", "🌧️ Open-Meteo", (("Annual Rainfall", "annual_rainfall_mm", "mm"), ("Dry Months", "n_dry_months", "/ 12"), ("Mean Temp", "temperature_mean_c", "°C"))),
                    ("live_elev", "⛰️ Elevation", (("Elevation", "elevation_m", "m"), ("Slope", "slope_pct", "%"), ("Relief", "elevation_range_m", "m"))),
                    ("live_soil", "🪨 SoilGrids", (("Sand", "sand_pct", "%"), ("Clay", "clay_pct", "%"), ("Silt", "silt_pct", "%")))):
                if _key in st.session_state:
                    _r = st.session_state[_key]
                    if "error" in _r:
                        st.error(f"{_title}: {_r['error']}")
                    else:
                        st.markdown(f"#### {_title}")
                        for _col, (_lbl, _f, _u) in zip(st.columns(len(_fields)), _fields):
                            _col.metric(_lbl, f"{_r.get(_f, 'N/A')} {_u}")

    # ------------------------------------------------------------- 19: حارس المياه
    with tabs[19]:
        if WG_OK:
            wg.render()
        else:
            st.error("water_guardian.py not installed")

elif MODE_KEY == "agricultural" and ADV_OK:
    st.markdown(f"""<div class=
