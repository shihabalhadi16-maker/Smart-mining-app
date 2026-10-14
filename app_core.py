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
import tempfile
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
    from modflow_engine import is_modflow_available, build_and_run_model, estimate_travel_time_modflow
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
