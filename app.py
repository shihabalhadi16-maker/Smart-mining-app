"""نظام التعدين السوداني v58.8 — University of Khartoum"""
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

try:
    from weight_manager import (get_all_profiles, get_active_profile, set_active_profile,
        save_calibrated_profile, detect_ceiling_effect, get_profile_summary)
    WM_OK = True
except ImportError:
    WM_OK = False

try:
    from external_validation import external_validation_analysis as _ext_val_fn
    EXT_VAL_OK = True
except ImportError:
    EXT_VAL_OK = False
    _ext_val_fn = None

try:
    from data_validator import validate_dataframe, get_quality_color, get_quality_label_ar
    VALIDATOR_OK = True
except ImportError:
    VALIDATOR_OK = False
    validate_dataframe = None

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
    from gis_raster import (idw_interpolation, kriging_interpolation,
                             export_geotiff, create_raster_plotly,
                             compute_raster_statistics, classify_raster)
    RASTER_OK = True
except ImportError:
    RASTER_OK = False
    idw_interpolation = kriging_interpolation = None
    export_geotiff = create_raster_plotly = None
    compute_raster_statistics = classify_raster = None

try:
    from live_apis import (fetch_nasa_power, fetch_open_meteo_precipitation,
                            fetch_elevation, fetch_elevation_grid,
                            fetch_soilgrids, classify_aquifer_from_soil,
                            classify_soil_from_texture, estimate_recharge_from_rainfall)
    LIVE_API_OK = True
except ImportError:
    LIVE_API_OK = False
    fetch_nasa_power = fetch_open_meteo_precipitation = None
    fetch_elevation = fetch_elevation_grid = None
    fetch_soilgrids = classify_aquifer_from_soil = None
    classify_soil_from_texture = estimate_recharge_from_rainfall = None

def t(key, **kwargs):
    lang = st.session_state.get("lang", "ar")
    return _t(key, lang)

def is_ar():
    return st.session_state.get("lang", "ar") == "ar"

try:
    from sklearn.metrics import cohen_kappa_score, roc_auc_score, confusion_matrix
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False
try:
    from auto_maps import generate_auto_maps, prepare_df_for_maps
    MAPS_OK = True
except ImportError:
    MAPS_OK = False
try:
    from auto_calibration import (auto_calibrate_weights, apply_calibration,
        compare_with_defaults, interpret_kappa, find_optimal_threshold)
    AUTOCAL_OK = True
except ImportError:
    AUTOCAL_OK = False

st.set_page_config(page_title="Sudan Mining System v58.8", page_icon="⛏️", layout="wide", initial_sidebar_state="expanded")

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
.upload-zone{background:linear-gradient(135deg,#fff9ec,#f5e6c8);border:3px dashed #c19a6b;border-radius:14px;padding:22px;margin:12px 0;text-align:center;}
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
.cal-result-card{background:#f5eedc;border:2px solid #c19a6b;border-radius:12px;padding:16px;margin:8px 0;text-align:center;}
.cal-result-value{font-size:2em;font-weight:700;color:#5c2c16;margin:4px 0;}
.cal-result-label{font-size:.85em;color:#777;}
#MainMenu{visibility:hidden;} footer{visibility:hidden;}
@media(max-width:768px){.header-title{font-size:1.5em!important;}.header-container{padding:18px 14px!important;}[data-testid="stHorizontalBlock"]{flex-direction:column!important;}[data-testid="stHorizontalBlock"]>div{width:100%!important;}}
</style>""", unsafe_allow_html=True)

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
            if r.status_code != 200: return f"download_failed_{r.status_code}"
            with zipfile.ZipFile(io.BytesIO(r.content), 'r') as zf:
                mf6_file = None
                for name in zf.namelist():
                    if name.endswith("mf6") and not name.endswith("/"): mf6_file = name; break
                if not mf6_file: return "mf6_not_in_zip"
                zf.extract(mf6_file, MODFLOW_DIR)
                ex = os.path.join(MODFLOW_DIR, mf6_file)
                if ex != mf6_path: shutil.move(ex, mf6_path)
        os.chmod(mf6_path, os.stat(mf6_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        os.environ["PATH"] = MODFLOW_DIR + os.pathsep + os.environ.get("PATH", "")
        return "installed" if shutil.which("mf6") else "installed_but_not_in_path"
    except Exception as e: return f"error: {str(e)[:100]}"

_modflow_status = setup_modflow()
if os.path.exists(MODFLOW_DIR): os.environ["PATH"] = MODFLOW_DIR + os.pathsep + os.environ.get("PATH", "")

try:
    from data_sources import (STATES_DATABASE, AGRICULTURAL_DATA, get_preset_locations_for_app,
        get_data_summary, get_sites_by_state, get_site_data, get_all_sites_as_dataframe,
        add_new_site, get_states_list, get_sites_list, get_agricultural_data_summary,
        get_agri_states_list, get_agri_sites_list, get_agri_site_data, add_new_agri_site,
        get_all_agri_sites_as_dataframe, KNOWN_MINING_SITES, get_verified_sites_as_dataframe,
        get_all_sites_as_dataframe_with_flag, GRAY_ZONE_SITES, get_combined_dataset)
    DS_OK = True
except ImportError: DS_OK = False

try:
    from modflow_engine import (is_modflow_available, build_and_run_model)
    MODFLOW_OK = True
except ImportError: MODFLOW_OK = False

try:
    from advanced_modules import (calculate_confusion_matrix, model_contaminant_transport,
        fetch_satellite_data, calculate_sar, calculate_na_percent, calculate_ec_quality,
        calculate_agricultural_drastic, classify_irrigation_water, independent_validation,
        calculate_dynamic_risk)
    ADV_OK = True
except ImportError: ADV_OK = False

try:
    from model_development import (calibrate_alpha_beta, compare_models, calculate_ahp_weights)
    DEV_OK = True
except ImportError: DEV_OK = False

def get_loaded_df(*keys):
    for key in keys:
        df = st.session_state.get(key)
        if df is None: continue
        if hasattr(df, "empty") and not df.empty: return df
    return None

def safe_sum(df, column, default=0):
    if df is None or column not in df.columns: return default
    try: return int(df[column].sum())
    except Exception: return default

def safe_len(df, default=0):
    if df is None: return default
    try: return len(df)
    except Exception: return default

@st.cache_data(show_spinner=False)
def load_industrial_sites_csv():
    csv_path = Path(__file__).parent / "industrial_sites.csv"
    if not csv_path.exists(): return []
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
        if "verified" in df.columns:
            df["verified"] = df["verified"].astype(str).str.lower() == "true"
        return df.to_dict(orient="records")
    except Exception: return []

WEIGHTS = {
    "industrial":  {"alpha": 0.7, "beta": 0.5, "SF": 1.0, "ar": "🏭 Industrial", "en": "🏭 Industrial"},
    "traditional": {"alpha": 0.3, "beta": 1.0, "SF": 1.1, "ar": "⛏️ Traditional", "en": "⛏️ Traditional"},
    "mixed":       {"alpha": 0.5, "beta": 0.9, "SF": 1.3, "ar": "🔀 Mixed", "en": "🔀 Mixed"},
}
OPTIMAL_THRESHOLDS = {"traditional": 106.5, "industrial": 128.0, "mixed": 117.0}
def get_optimal_threshold(mining_type):
    return OPTIMAL_THRESHOLDS.get(mining_type, 140.0)

AQUIFER_AR = {"massive_shale":"صخر طيني ضخم","metamorphic_igneous":"صخور متحولة/نارية","weathered_metamorphic_igneous":"صخور متحولة/نارية متآكلة","thin_bedded_sequences":"تتابعات رقيقة الطبقات","massive_sandstone":"حجر رملي ضخم","massive_limestone":"حجر جيري ضخم","sand_and_gravel":"رمل وحصى","basalt":"بازلت","karst_limestone":"حجر جيري كارستي"}
AQUIFER_EN = {"massive_shale":"Massive Shale","metamorphic_igneous":"Metamorphic/Igneous","weathered_metamorphic_igneous":"Weathered Metamorphic","thin_bedded_sequences":"Thin Bedded","massive_sandstone":"Massive Sandstone","massive_limestone":"Massive Limestone","sand_and_gravel":"Sand & Gravel","basalt":"Basalt","karst_limestone":"Karst Limestone"}
SOIL_AR = {"thin_or_absent":"رقيقة أو معدومة","gravel":"حصى","sand":"رمل","peat":"خث","shrinking_aggregated_clay":"طين متقلص متكتل","sandy_loam":"طين رملي","loam":"طين طميي","silty_loam":"طمي غريني","clay_loam":"طين غريني","muck":"طين عضوي","nonshrinking_clay":"طين غير متقلص"}
SOIL_EN = {"thin_or_absent":"Thin or Absent","gravel":"Gravel","sand":"Sand","peat":"Peat","shrinking_aggregated_clay":"Shrinking Clay","sandy_loam":"Sandy Loam","loam":"Loam","silty_loam":"Silty Loam","clay_loam":"Clay Loam","muck":"Muck","nonshrinking_clay":"Non-shrinking Clay"}
VADOSE_AR = {"confining_layer":"طبقة كتيمة","silt_clay":"غرين وطين","shale":"صخر طيني","metamorphic_igneous":"صخور متحولة/نارية","limestone":"حجر جيري","sandstone":"حجر رملي","sand_gravel_silt_clay":"رمل وحصى وغرين وطين","sand_gravel":"رمل وحصى","basalt":"بازلت","karst_limestone":"حجر جيري كارستي"}
VADOSE_EN = {"confining_layer":"Confining Layer","silt_clay":"Silt & Clay","shale":"Shale","metamorphic_igneous":"Metamorphic/Igneous","limestone":"Limestone","sandstone":"Sandstone","sand_gravel_silt_clay":"Sand/Gravel/Silt/Clay","sand_gravel":"Sand & Gravel","basalt":"Basalt","karst_limestone":"Karst Limestone"}

def AQ(a): return AQUIFER_AR.get(a, a) if is_ar() else AQUIFER_EN.get(a, a)
def SL(s): return SOIL_AR.get(s, s) if is_ar() else SOIL_EN.get(s, s)
def VD(v): return VADOSE_AR.get(v, v) if is_ar() else VADOSE_EN.get(v, v)

def get_d_rating(d):
    if d < 0: raise ValueError("Neg")
    if d <= 1.5: return 10
    if d <= 4.6: return 9
    if d <= 9.1: return 7
    if d <= 15.2: return 5
    if d <= 22.9: return 3
    if d <= 30.5: return 2
    return 1

def get_r_rating(r):
    if r < 0: raise ValueError("Neg")
    if r <= 50.8: return 1
    if r <= 101.6: return 3
    if r <= 177.8: return 6
    if r <= 254.0: return 8
    return 9

def get_a_rating(a): return {"massive_shale":2,"metamorphic_igneous":3,"weathered_metamorphic_igneous":4,"thin_bedded_sequences":6,"massive_sandstone":6,"massive_limestone":6,"sand_and_gravel":8,"basalt":9,"karst_limestone":10}.get(a,6)
def get_s_rating(s): return {"thin_or_absent":10,"gravel":10,"sand":9,"peat":8,"shrinking_aggregated_clay":7,"sandy_loam":6,"loam":5,"silty_loam":4,"clay_loam":3,"muck":2,"nonshrinking_clay":1}.get(s,5)

def get_t_rating(t):
    if t < 0: raise ValueError("Neg")
    if t <= 2.0: return 10
    if t <= 6.0: return 9
    if t <= 12.0: return 5
    if t <= 18.0: return 3
    return 1

def get_i_rating(i): return {"confining_layer":1,"silt_clay":1,"shale":3,"metamorphic_igneous":4,"limestone":6,"sandstone":6,"sand_gravel_silt_clay":6,"sand_gravel":8,"basalt":9,"karst_limestone":10}.get(i,6)

def get_c_rating(c):
    if c < 0: raise ValueError("Neg")
    if c <= 4.074: return 1
    if c <= 12.222: return 2
    if c <= 28.518: return 4
    if c <= 40.740: return 6
    if c <= 81.480: return 8
    return 10

def calc_index(D, R, A, S, T, I, C): return (D*5)+(R*4)+(A*3)+(S*2)+(T*1)+(I*5)+(C*3)

def classify(idx):
    if idx >= 180: return {"level": "very_high", "color": "red", "action": "action_immediate"}
    if idx >= 140: return {"level": "high", "color": "orange", "action": "action_urgent"}
    if idx >= 100: return {"level": "medium", "color": "yellow", "action": "action_periodic"}
    return {"level": "low", "color": "green", "action": "action_routine"}

def mitigate(idx, hdpe=False, treat=False, mon=False):
    m = float(idx)
    if hdpe: m *= 0.40
    if treat: m *= 0.60
    if mon: m *= 0.85
    red = ((idx - m) / idx * 100) if idx > 0 else 0.0
    return {"mitigated_index": round(m, 1), "reduction_pct": round(red, 1)}

def calc_drastic_t(base_drastic, cn_water, hg_water, distance_m=100.0, seepage=1.0, bio_acc=1.0,
                    mining_type="traditional", alpha_override=None, beta_override=None, SF_override=None):
    CN_LIMIT = 0.05; HG_LIMIT = 0.0007
    MAX_CN_SCORE = 30.0; MAX_HG_SCORE = 30.0; MAX_TOXICITY_BONUS = 50.0
    if alpha_override is not None:
        alpha = alpha_override
        beta = beta_override if beta_override is not None else 0.5
        source_factor = SF_override if SF_override is not None else 1.0
    else:
        w = WEIGHTS.get(mining_type, WEIGHTS["traditional"])
        alpha, beta, source_factor = w["alpha"], w["beta"], w["SF"]
    d_factor = max(0.1, min(1.0, 100.0 / max(1, distance_m)))
    s_factor = max(0.1, min(1.0, seepage))
    cn_ratio = cn_water / CN_LIMIT if CN_LIMIT > 0 else 0
    cri = cn_ratio * d_factor * s_factor
    cn_score = min(MAX_CN_SCORE, cri * 30.0)
    hg_ratio = hg_water / HG_LIMIT if HG_LIMIT > 0 else 0
    mri = hg_ratio * bio_acc
    hg_score = min(MAX_HG_SCORE, mri * 30.0)
    base_bonus = min(MAX_TOXICITY_BONUS, alpha * cn_score + beta * hg_score)
    toxicity_bonus = base_bonus * source_factor
    drastic_t = base_drastic + toxicity_bonus
    if drastic_t >= 180: level, color = "very_high", "red"
    elif drastic_t >= 140: level, color = "high", "orange"
    elif drastic_t >= 100: level, color = "medium", "yellow"
    else: level, color = "low", "green"
    increase_pct = (toxicity_bonus / base_drastic * 100) if base_drastic > 0 else 0
    return {"base_drastic":base_drastic,"mining_type":mining_type,"alpha":alpha,"beta":beta,
            "source_factor":source_factor,"cri":round(cri,3),"mri":round(mri,3),
            "cn_score":round(cn_score,2),"hg_score":round(hg_score,2),"base_bonus":round(base_bonus,2),
            "toxicity_bonus":round(toxicity_bonus,2),"drastic_t":round(drastic_t,1),
            "drastic_p":round(drastic_t,1),"modifier":round(1.0 + toxicity_bonus / max(base_drastic, 1), 3),
            "increase_pct":round(increase_pct,1),"level":level,"color":color}

def weighted_toxicity(hgw, hgs, cnw, cns, mining_type="traditional",
                      alpha_override=None, beta_override=None, SF_override=None):
    CN_LIMIT = 0.05; HG_LIMIT = 0.0007
    cn_score = min(30.0, (cnw / CN_LIMIT) * 30.0)
    hg_score = min(30.0, (hgw / HG_LIMIT) * 30.0)
    if alpha_override is not None:
        alpha = alpha_override
        beta = beta_override if beta_override is not None else 0.5
        SF = SF_override if SF_override is not None else 1.0
    else:
        w = WEIGHTS.get(mining_type, WEIGHTS["traditional"])
        alpha, beta, SF = w["alpha"], w["beta"], w["SF"]
    base_bonus = min(50.0, alpha * cn_score + beta * hg_score)
    soil_factor = 1.0
    if hgs > 1.0: soil_factor += 0.3
    if cns > 10.0: soil_factor += 0.3
    drastic_tox_bonus = base_bonus * SF
    toxicity_index = drastic_tox_bonus * soil_factor
    if toxicity_index <= 5.0: cat, act = "safe", "no_action"
    elif toxicity_index <= 15.0: cat, act = "under_monitoring", "periodic"
    elif toxicity_index <= 30.0: cat, act = "hazardous", "urgent"
    else: cat, act = "critical", "stop_activity"
    return {"index": round(toxicity_index, 2),
            "drastic_tox_bonus": round(drastic_tox_bonus, 2),
            "cn_score": round(cn_score, 2), "hg_score": round(hg_score, 2),
            "base_bonus": round(base_bonus, 2),
            "source_factor": round(SF, 2), "soil_factor": round(soil_factor, 2),
            "category": cat, "action": act, "mining_type": mining_type}

def spsa_analysis(pv):
    D_r = get_d_rating(float(pv.get("depth", 15.0)))
    R_r = get_r_rating(float(pv.get("recharge", 100.0)))
    A_r = get_a_rating(str(pv.get("aquifer", "massive_sandstone")))
    S_r = get_s_rating(str(pv.get("soil", "sand")))
    T_r = get_t_rating(float(pv.get("slope", 4.0)))
    I_r = get_i_rating(str(pv.get("vadose", "sand_gravel")))
    C_r = get_c_rating(float(pv.get("conductivity", 5.0)))
    D_w, R_w, A_w, S_w, T_w, I_w, C_w = 5, 4, 3, 2, 1, 5, 3
    total_weight = 23
    DI = (D_r*D_w) + (R_r*R_w) + (A_r*A_w) + (S_r*S_w) + (T_r*T_w) + (I_r*I_w) + (C_r*C_w)
    params = [("D",D_w,D_r),("R",R_w,R_r),("A",A_w,A_r),("S",S_w,S_r),
              ("T",T_w,T_r),("I",I_w,I_r),("C",C_w,C_r)]
    results = []
    for name, w, r in params:
        theo = (w / total_weight) * 100
        eff = (w * r / DI) * 100 if DI > 0 else 0
        results.append({"param":name,"weight":w,"rating":r,"weighted_score":w*r,
            "theoretical_pct":round(theo,2),"effective_pct":round(eff,2),
            "difference":round(eff-theo,2)})
    results_sorted = sorted(results, key=lambda x: x["effective_pct"], reverse=True)
    return {"base_index": DI, "parameters": results_sorted,
            "most_influential": results_sorted[0]["param"] if results_sorted else None,
            "least_influential": results_sorted[-1]["param"] if results_sorted else None}

def sensitivity_analysis(pv, variation=0.10):
    D=float(pv.get("depth",15.0)); R=float(pv.get("recharge",100.0))
    A=str(pv.get("aquifer","massive_sandstone")); S=str(pv.get("soil","sand"))
    T=float(pv.get("slope",4.0)); I=str(pv.get("vadose","sand_gravel")); C=float(pv.get("conductivity",5.0))
    def ci(d,r,a,s,t,i,c): return calc_index(get_d_rating(d),get_r_rating(r),get_a_rating(a),get_s_rating(s),get_t_rating(t),get_i_rating(i),get_c_rating(c))
    base = ci(D,R,A,S,T,I,C); res = {}
    for name,val,lo,hi in [("D",D,0.5,100.0),("R",R,0.0,400.0),("T",T,0.0,30.0),("C",C,0.01,100.0)]:
        v = max(lo,min(hi,val*(1+variation)))
        if name=="D": ni = ci(v,R,A,S,T,I,C)
        elif name=="R": ni = ci(D,v,A,S,T,I,C)
        elif name=="T": ni = ci(D,R,A,S,v,I,C)
        else: ni = ci(D,R,A,S,T,I,v)
        res[name] = {"original_phys":val,"modified_phys":round(v,2),"new_index":ni,"change":ni-base,"sensitivity":round(abs(ni-base)/base*100,3)}
    for name,br,w in [("A",get_a_rating(A),3),("S",get_s_rating(S),2),("I",get_i_rating(I),5)]:
        nr = max(1,min(10,br+1)); ni = base-br*w+nr*w
        res[name] = {"original_phys":"rating","modified_phys":"rating+1","new_index":ni,"change":ni-base,"sensitivity":round(abs(ni-base)/base*100,3)}
    sr = dict(sorted(res.items(), key=lambda x: x[1]["sensitivity"], reverse=True))
    return {"base_index":base,"parameters":sr,"most_sensitive":list(sr.keys())[0] if sr else None}

def monte_carlo_analysis(pv, n_iter=1000, variation=0.15, mining_type="traditional",
                          calibrated_weights=None):
    np.random.seed(42)
    D = float(pv.get("depth", 15.0)); R = float(pv.get("recharge", 100.0))
    T = float(pv.get("slope", 4.0)); C = float(pv.get("conductivity", 5.0))
    A_b = get_a_rating(str(pv.get("aquifer", "massive_sandstone")))
    S_b = get_s_rating(str(pv.get("soil", "sand")))
    I_b = get_i_rating(str(pv.get("vadose", "sand_gravel")))
    cn_w = float(pv.get("cn_water_mg_l", 0.025))
    hg_w = float(pv.get("hg_water_mg_l", 0.011))
    D_s = np.clip(np.random.normal(D, max(0.5, D * variation), n_iter), 0.5, 100.0)
    R_s = np.clip(np.random.lognormal(np.log(max(1, R)) - 0.5 * variation ** 2, variation, n_iter), 0.0, 400.0) if R > 0 else np.zeros(n_iter)
    A_s = np.random.choice([max(1, A_b - 1), A_b, min(10, A_b + 1)], n_iter, p=[0.15, 0.70, 0.15])
    S_s = np.random.choice([max(1, S_b - 1), S_b, min(10, S_b + 1)], n_iter, p=[0.15, 0.70, 0.15])
    T_s = np.clip(np.random.normal(T, max(0.5, T * variation), n_iter), 0.0, 30.0)
    I_s = np.random.choice([max(1, I_b - 1), I_b, min(10, I_b + 1)], n_iter, p=[0.15, 0.70, 0.15])
    C_s = np.clip(np.random.lognormal(np.log(max(0.01, C)) - 0.5 * variation ** 2, variation, n_iter), 0.01, 100.0)
    D_r = np.select([D_s <= 1.5, D_s <= 4.6, D_s <= 9.1, D_s <= 15.2, D_s <= 22.9, D_s <= 30.5], [10, 9, 7, 5, 3, 2], default=1)
    R_r = np.select([R_s <= 50.8, R_s <= 101.6, R_s <= 177.8, R_s <= 254.0], [1, 3, 6, 8], default=9)
    T_r = np.select([T_s <= 2.0, T_s <= 6.0, T_s <= 12.0, T_s <= 18.0], [10, 9, 5, 3], default=1)
    C_r = np.select([C_s <= 4.074, C_s <= 12.222, C_s <= 28.518, C_s <= 40.740, C_s <= 81.480], [1, 2, 4, 6, 8], default=10)
    drastic = D_r * 5 + R_r * 4 + A_s * 3 + S_s * 2 + T_r * 1 + I_s * 5 + C_r * 3
    if calibrated_weights:
        alpha_mean = calibrated_weights.get("alpha", 0.3)
        beta_mean = calibrated_weights.get("beta", 1.0)
        SF_mean = calibrated_weights.get("SF", 1.1)
    else:
        w = WEIGHTS.get(mining_type, WEIGHTS["traditional"])
        alpha_mean, beta_mean, SF_mean = w["alpha"], w["beta"], w["SF"]
    alpha_s = np.clip(np.random.normal(alpha_mean, 0.05, n_iter), 0.0, 1.0)
    beta_s = np.clip(np.random.normal(beta_mean, 0.10, n_iter), 0.0, 1.0)
    SF_s = np.clip(np.random.normal(SF_mean, 0.08, n_iter), 0.5, 2.0)
    CN_LIMIT = 0.05; HG_LIMIT = 0.0007
    cn_s = np.clip(np.random.lognormal(np.log(max(0.001, cn_w)) - 0.5 * 0.2 ** 2, 0.2, n_iter), 0.0, 10.0)
    hg_s = np.clip(np.random.lognormal(np.log(max(0.0001, hg_w)) - 0.5 * 0.2 ** 2, 0.2, n_iter), 0.0, 10.0)
    cn_score_s = np.minimum(30.0, (cn_s / CN_LIMIT) * 30.0)
    hg_score_s = np.minimum(30.0, (hg_s / HG_LIMIT) * 30.0)
    base_bonus_s = np.minimum(50.0, alpha_s * cn_score_s + beta_s * hg_score_s)
    toxicity_bonus_s = base_bonus_s * SF_s
    drastic_tox = drastic + toxicity_bonus_s
    results = np.sort(drastic.astype(int))
    results_tox = np.sort(drastic_tox)
    def pct(arr, p): return float(np.percentile(arr, p))
    return {
        "mean": round(float(np.mean(results)), 1), "std": round(float(np.std(results)), 2),
        "min": int(results[0]), "max": int(results[-1]),
        "ci_90": (int(pct(results, 5)), int(pct(results, 95))),
        "prob_over_140": round(float(np.mean(results >= 140) * 100), 1),
        "tox_mean": round(float(np.mean(results_tox)), 1),
        "tox_std": round(float(np.std(results_tox)), 2),
        "tox_min": round(float(results_tox[0]), 1), "tox_max": round(float(results_tox[-1]), 1),
        "tox_ci_90": (round(pct(results_tox, 5), 1), round(pct(results_tox, 95), 1)),
        "tox_prob_over_140": round(float(np.mean(results_tox >= 140) * 100), 1),
        "tox_prob_over_180": round(float(np.mean(results_tox >= 180) * 100), 1),
        "n_iter": n_iter,
        "variation_pct": int(variation * 100),
    }

def model_contaminant_transport_fixed(C0, K, porosity, gradient, distance, years, dispersivity=10.0):
    try:
        from scipy import special as sp; has_scipy = True
    except ImportError: has_scipy = False
    v = (K*gradient)/porosity
    if v <= 0: return {"error": "Velocity is zero or negative"}
    D = dispersivity*v
    if D <= 0: return {"error": "Dispersion coefficient is zero"}
    total_days = int(years*365.25)
    times = np.linspace(1, total_days, min(200, max(10, total_days)))
    concentrations = []
    for t in times:
        if t <= 0: C = 0.0
        else:
            arg = (distance - v*t) / (2.0*np.sqrt(D*t))
            if has_scipy: erfc_val = float(sp.erfc(arg))
            else:
                z = abs(arg); tt = 1.0/(1.0+0.5*z)
                erf_approx = 1 - tt*np.exp(-z*z-1.26551223+tt*(1.00002368+tt*(0.37409196+tt*(0.09678418+tt*(-0.18628806+tt*(0.27886807+tt*(-1.13520398+tt*(1.48851587+tt*(-0.82215223+tt*0.17087277)))))))))
                erfc_val = 1-erf_approx if arg >= 0 else 1+erf_approx
            C = (C0/2.0)*erfc_val; C = max(0.0, min(C0, C))
        concentrations.append(round(C, 6))
    df = pd.DataFrame({"Year":[round(t/365.25,2) for t in times],"Concentration":concentrations,"Distance":[round(v*t,1) for t in times]})
    return {"results":df,"v_seepage":round(v,6),"D_dispersion":round(D,4),"t_travel_years":round(distance/v/365.25,3)}

def compute_basic_metrics(y_true, y_score, threshold):
    if not SKLEARN_OK: return {"error": "scikit-learn"}
    try:
        y_true = np.array(y_true); y_score = np.array(y_score)
        y_pred = (y_score >= threshold).astype(int)
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
        kappa = float(cohen_kappa_score(y_true, y_pred)) if len(np.unique(y_true)) > 1 else 0.0
        recall = float(tp/(tp+fn)) if (tp+fn) > 0 else 0.0
        precision = float(tp/(tp+fp)) if (tp+fp) > 0 else 0.0
        accuracy = float((tp+tn)/(tp+tn+fp+fn))
        f1 = 2*(precision*recall)/(precision+recall) if (precision+recall) > 0 else 0.0
        try: auc = float(roc_auc_score(y_true, y_score))
        except Exception: auc = 0.5
        return {"kappa":round(kappa,3),"recall":round(recall*100,1),"precision":round(precision*100,1),"accuracy":round(accuracy*100,1),"f1":round(f1,3),"auc":round(auc,3),"tp":int(tp),"tn":int(tn),"fp":int(fp),"fn":int(fn)}
    except Exception as e: return {"error": str(e)}

def bootstrap_kappa_ci(y_true, y_score, threshold, n_boot=1000, seed=42):
    if not SKLEARN_OK: return {"error": "scikit-learn"}
    try:
        y_true = np.array(y_true); y_score = np.array(y_score); np.random.seed(seed); kappas = []
        for _ in range(n_boot):
            idx = np.random.choice(len(y_true), len(y_true), replace=True)
            yt = y_true[idx]; ys = y_score[idx]
            if len(np.unique(yt)) < 2: continue
            yp = (ys >= threshold).astype(int)
            try: kappas.append(cohen_kappa_score(yt, yp))
            except Exception: continue
        if not kappas: return {"mean":0,"std":0,"ci_low":0,"ci_high":0}
        kappas = np.array(kappas)
        return {"mean":round(float(np.mean(kappas)),3),"std":round(float(np.std(kappas)),3),"ci_low":round(float(np.percentile(kappas,2.5)),3),"ci_high":round(float(np.percentile(kappas,97.5)),3)}
    except Exception as e: return {"error": str(e)}

def loocv_analysis(y_true, y_score, threshold):
    if not SKLEARN_OK: return {"error": "scikit-learn"}
    try:
        y_true = np.array(y_true); y_score = np.array(y_score); n = len(y_true)
        all_actual = []; all_pred = []
        for i in range(n): all_actual.append(y_true[i]); all_pred.append(int(y_score[i] >= threshold))
        all_actual = np.array(all_actual); all_pred = np.array(all_pred)
        kappa = float(cohen_kappa_score(all_actual, all_pred)) if len(np.unique(all_actual)) > 1 else 0.0
        accuracy = float(np.mean(all_actual == all_pred)*100)
        tp = int(np.sum((all_actual == 1) & (all_pred == 1))); fn = int(np.sum((all_actual == 1) & (all_pred == 0)))
        recall = (tp/(tp+fn)*100) if (tp+fn) > 0 else 0.0
        return {"kappa":round(kappa,3),"accuracy":round(accuracy,1),"recall":round(recall,1),"n_correct":int(np.sum(all_actual == all_pred)),"n_total":n}
    except Exception as e: return {"error": str(e)}

def generate_html_report(site_info, drastic, drastic_t, level, recommendation):
    return f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="UTF-8"><title>Report</title>
<style>body{{font-family:Arial;padding:40px;max-width:800px;margin:0 auto;}}
h1{{color:#5c2c16;border-bottom:3px solid #c19a6b;padding-bottom:10px;}}
table{{width:100%;border-collapse:collapse;margin:15px 0;}}th,td{{padding:10px;border:1px solid #ddd;text-align:right;}}
th{{background-color:#f5eedc;color:#5c2c16;}}.metric{{font-size:1.5em;font-weight:bold;color:#c19a6b;}}
</style></head><body>
<h1>DRASTIC-Tox Report</h1>
<p><b>Date:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<table>
<tr><th>Site</th><td>{site_info.get('name','N/A')}</td></tr>
<tr><th>State</th><td>{site_info.get('state','N/A')}</td></tr>
<tr><th>DRASTIC</th><td class="metric">{drastic}/230</td></tr>
<tr><th>DRASTIC-Tox</th><td class="metric">{drastic_t}/280</td></tr>
<tr><th>Level</th><td class="metric">{level}</td></tr>
</table>
<p><b>{recommendation}</b></p>
<p style="text-align:center;color:#666;">DRASTIC-Tox v58.8</p>
</body></html>"""

def build_heatmap_verified(show_heat=True, show_markers=True):
    m = folium.Map(location=[15.5, 32.5], zoom_start=6, tiles='OpenStreetMap')
    heat_data = []; stats = {"low":0,"medium":0,"high":0,"very_high":0}; sites_info = []
    for state_name, state_data in STATES_DATABASE.items():
        for site_key, site_data in state_data.get("sites", {}).items():
            if not site_data.get("verified", False): continue
            coords = site_data.get("coords", None)
            if not coords or len(coords) < 2: continue
            lat, lon = coords[0], coords[1]
            try:
                drastic = calc_index(get_d_rating(site_data.get("depth_m",15)), get_r_rating(site_data.get("recharge_mm",100)), get_a_rating(site_data.get("aquifer","massive_sandstone")), get_s_rating(site_data.get("soil","sand")), get_t_rating(site_data.get("slope_pct",4)), get_i_rating(site_data.get("vadose","sand_gravel")), get_c_rating(site_data.get("conductivity",5)))
                cn = site_data.get("cn_water_mg_l",0.0); hg = site_data.get("hg_water_mg_l",0.0)
                mt = site_data.get("mining_type","traditional")
                if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mt:
                    w = CALIBRATED_WEIGHTS
                    drastic_t = calc_drastic_t(drastic, cn, hg, mining_type=mt, alpha_override=w["alpha"], beta_override=w["beta"], SF_override=w["SF"])["drastic_t"]
                else: drastic_t = calc_drastic_t(drastic, cn, hg, mining_type=mt)["drastic_t"]
            except Exception: continue
            if drastic_t >= 180: color, radius, level = "#d32f2f", 20, "very_high"; stats["very_high"] += 1
            elif drastic_t >= 140: color, radius, level = "#f57c00", 16, "high"; stats["high"] += 1
            elif drastic_t >= 100: color, radius, level = "#fbc02d", 12, "medium"; stats["medium"] += 1
            else: color, radius, level = "#388e3c", 9, "low"; stats["low"] += 1
            popup_html = f"""<div style="font-family:Arial;font-size:12px;"><h4 style="color:{color};">{site_data.get('name_ar', site_key)}</h4><b>DRASTIC:</b> {drastic}<br><b>DRASTIC-Tox:</b> <span style="color:{color};font-weight:bold;">{drastic_t}</span><br><b>CN:</b> {cn} mg/L<br><b>Hg:</b> {hg} mg/L</div>"""
            if show_markers:
                folium.CircleMarker(location=[lat,lon], radius=radius, popup=folium.Popup(popup_html, max_width=280), tooltip=f"{site_data.get('name_ar', site_key)} - {drastic_t}", color=color, fill=True, fillColor=color, fillOpacity=0.75, weight=2).add_to(m)
            heat_data.append([lat, lon, min(1.0, drastic_t/230.0)])
            sites_info.append({"state":state_name,"site":site_data.get("name_ar",site_key),"lat":lat,"lon":lon,"DRASTIC":drastic,"DRASTIC-Tox":drastic_t,"CN":cn,"Hg":hg,"Level":level})
    if show_heat and heat_data:
        HeatMap(heat_data, min_opacity=0.3, max_zoom=10, radius=30, blur=20, gradient={0.0:'#388e3c',0.4:'#fbc02d',0.7:'#f57c00',1.0:'#d32f2f'}).add_to(m)
    return m, stats, pd.DataFrame(sites_info)

VALID_AQUIFERS = ["massive_shale","metamorphic_igneous","weathered_metamorphic_igneous","thin_bedded_sequences","massive_sandstone","massive_limestone","sand_and_gravel","basalt","karst_limestone"]
VALID_SOILS = ["thin_or_absent","gravel","sand","peat","shrinking_aggregated_clay","sandy_loam","loam","silty_loam","clay_loam","muck","nonshrinking_clay"]
VALID_VADOSE = ["confining_layer","silt_clay","shale","metamorphic_igneous","limestone","sandstone","sand_gravel_silt_clay","sand_gravel","basalt","karst_limestone"]

if DS_OK:
    preset = get_preset_locations_for_app(); summary = get_data_summary(); n_states = summary.get('total_states', 0)
    try:
        _df_all = get_all_sites_as_dataframe_with_flag()
        n_sites_total = safe_len(_df_all, summary.get('total_sites', 0))
        n_sites_verified = safe_sum(_df_all, "verified", 0)
    except Exception: n_sites_total = summary.get('total_sites', 0); n_sites_verified = 0
    agri_summary = get_agricultural_data_summary(); n_agri_states = agri_summary.get('total_states', 0)
    try:
        _df_agri = get_all_agri_sites_as_dataframe()
        n_agri_sites = safe_len(_df_agri, agri_summary.get('total_sites', 0))
    except Exception: n_agri_sites = agri_summary.get('total_sites', 0)
else: preset = {}; n_states = n_sites_total = n_sites_verified = n_agri_states = n_agri_sites = 0

INDUSTRIAL_SITES = load_industrial_sites_csv()
if "lang" not in st.session_state: st.session_state["lang"] = "ar"

_lang_opts = {"🇸🇦 العربية": "ar", "🇬🇧 English": "en"}
_cur = "🇸🇦 العربية" if st.session_state["lang"] == "ar" else "🇬🇧 English"
_sel = st.sidebar.selectbox(t("language"), list(_lang_opts.keys()), index=list(_lang_opts.keys()).index(_cur), key="lang_switcher")
st.session_state["lang"] = _lang_opts[_sel]

st.sidebar.markdown(f"""<div style="background:linear-gradient(135deg,#5c2c16,#c19a6b);padding:16px;border-radius:12px;color:white;text-align:center;margin-bottom:16px;"><div style="font-size:1.3em;font-weight:700;">{t("upload_files")}</div></div>""", unsafe_allow_html=True)

uploaded_val = st.sidebar.file_uploader(t("validation_file") + ":", type=["csv","xlsx"], key="uploader_validation")
uploaded_bulk = st.sidebar.file_uploader(t("bulk_file") + ":", type=["csv","xlsx"], key="uploader_bulk")
uploaded_extra = st.sidebar.file_uploader(t("extra_file") + ":", type=["csv","xlsx"], key="uploader_extra")

if uploaded_val is not None:
    try:
        df_val_side = pd.read_csv(uploaded_val) if uploaded_val.name.endswith(".csv") else pd.read_excel(uploaded_val)
        st.session_state["df_validation"] = df_val_side; st.sidebar.success(f"{len(df_val_side)} {t('rows')}")
    except Exception as e: st.sidebar.error(f"{str(e)[:80]}")
if uploaded_bulk is not None:
    try:
        df_bulk_side = pd.read_csv(uploaded_bulk) if uploaded_bulk.name.endswith(".csv") else pd.read_excel(uploaded_bulk)
        st.session_state["df_bulk"] = df_bulk_side; st.sidebar.success(f"{len(df_bulk_side)} {t('rows')}")
    except Exception as e: st.sidebar.error(f"{str(e)[:80]}")
if uploaded_extra is not None:
    try:
        df_extra_side = pd.read_csv(uploaded_extra) if uploaded_extra.name.endswith(".csv") else pd.read_excel(uploaded_extra)
        st.session_state["df_extra"] = df_extra_side; st.sidebar.info(f"{len(df_extra_side)} {t('rows')}")
    except Exception as e: st.sidebar.error(f"{str(e)[:80]}")

if st.sidebar.button(t("clear_all"), key="clear_all_files_btn"):
    for k in ["df_validation","df_bulk","df_extra","df_combined"]: st.session_state.pop(k, None)
    st.rerun()

st.sidebar.markdown("---")
if DS_OK:
    st.sidebar.markdown(f"### {t('data_quality')}")
    st.sidebar.markdown(f"""<div class="quality-box-ok"><div style="font-size:0.85em;color:#2e7d32;">{t('verified_sites')}: {n_sites_verified}</div></div><div class="quality-box-warn"><div style="font-size:0.85em;color:#e65100;">{t('display_only')}: {n_sites_total - n_sites_verified}</div></div>""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown(f"### {t('data_scope')}")
DATA_SCOPE = st.sidebar.radio(t("select"),
    [t("scope_traditional"), t("scope_industrial"), t("scope_all")],
    index=0, key="sidebar_data_scope", label_visibility="collapsed")
if DATA_SCOPE == t("scope_traditional"): SCOPE_KEY = "traditional"
elif DATA_SCOPE == t("scope_industrial"): SCOPE_KEY = "industrial"
else: SCOPE_KEY = "all"
if SCOPE_KEY == "industrial" and not INDUSTRIAL_SITES: st.sidebar.warning(t("no_industrial_file"))

CALIBRATED_WEIGHTS = None
if WM_OK:
    _active_prof = get_active_profile(SCOPE_KEY if SCOPE_KEY != "all" else "traditional")
    if _active_prof:
        CALIBRATED_WEIGHTS = {
            "mining_type": _active_prof["mining_type"],
            "alpha": _active_prof["alpha"], "beta": _active_prof["beta"], "SF": _active_prof["SF"],
            "kappa": _active_prof.get("kappa", "—"),
            "source_type": _active_prof.get("source_type", ""),
            "ar": _active_prof.get("name_ar", ""),
        }

_display_weights = None
if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == SCOPE_KEY:
    _display_weights = {"name": CALIBRATED_WEIGHTS["ar"], "cal": True,
        "alpha": CALIBRATED_WEIGHTS["alpha"], "beta": CALIBRATED_WEIGHTS["beta"], "SF": CALIBRATED_WEIGHTS["SF"]}
else:
    _w = WEIGHTS.get(SCOPE_KEY if SCOPE_KEY != "all" else "traditional", WEIGHTS["traditional"])
    _display_weights = {"name": _w["ar"] if is_ar() else _w["en"], "cal": False,
        "alpha": _w["alpha"], "beta": _w["beta"], "SF": _w["SF"]}

_badge_cls = "mining-industrial" if SCOPE_KEY == "industrial" else "mining-mixed" if SCOPE_KEY == "mixed" else "mining-traditional"
st.sidebar.markdown(f"""<div class="mining-badge {_badge_cls}">{_display_weights['name']}</div><div style="font-size:0.75em;color:#666;margin-top:4px;">α={_display_weights['alpha']} | β={_display_weights['beta']} | SF={_display_weights['SF']}</div>""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown(f"## {t('mode')}")
mode_options = [t("mode_system")]
if ADV_OK:
    mode_options += [t("mode_agricultural"), t("mode_verification"), t("mode_transport"),
                     t("mode_independent"), t("mode_satellite"), t("mode_dynamic")]
if MODFLOW_OK:
    mode_options.append(t("mode_modflow"))
mode = st.sidebar.radio(t("select"), mode_options, key="app_mode_radio", label_visibility="collapsed")

MODE_MAP = {
    t("mode_system"): "system", t("mode_agricultural"): "agricultural",
    t("mode_verification"): "verification", t("mode_transport"): "transport",
    t("mode_independent"): "independent", t("mode_satellite"): "satellite",
    t("mode_dynamic"): "dynamic", t("mode_modflow"): "modflow",
}
MODE_KEY = MODE_MAP.get(mode, "system")

st.sidebar.markdown("---")
st.sidebar.markdown(f"### {t('status')}")
_si = "OK" if _modflow_status in ["already_installed","installed"] else "WARN"
st.sidebar.info(f"{_si} MODFLOW: {_modflow_status}")
if "ci" in st.session_state: st.sidebar.success(f"{t('current_index')}: {st.session_state['ci']}")

st.sidebar.markdown("---")
with st.sidebar.expander(t("about"), expanded=False):
    st.markdown(f"""<div class="about-box">
<h4>{t('app_title')} v58.8</h4>
<h4>{t('modules')}:</h4>
<p style="font-size:0.8em;">
weight_manager: {'OK' if WM_OK else 'NO'}<br>
auto_calibration: {'OK' if AUTOCAL_OK else 'NO'}<br>
auto_maps: {'OK' if MAPS_OK else 'NO'}<br>
modflow: {'OK' if MODFLOW_OK else 'NO'}<br>
advanced: {'OK' if ADV_OK else 'NO'}<br>
model_development: {'OK' if DEV_OK else 'NO'}<br>
external_validation: {'OK' if EXT_VAL_OK else 'NO'}<br>
data_validator: {'OK' if VALIDATOR_OK else 'NO'}<br>
pdf_generator: {'OK' if PDF_OK else 'NO'}<br>
excel_exporter: {'OK' if EXCEL_OK else 'NO'}<br>
gis_raster: {'OK' if RASTER_OK else 'NO'}<br>
live_apis: {'OK' if LIVE_API_OK else 'NO'}
</p>
<h4>{t('constraints')}:</h4>
<ul style="font-size:0.85em;">
<li>PILOT VERSION</li>
<li>n = 7-10 sites</li>
<li>{t('screening_only')}</li>
</ul>
</div>""", unsafe_allow_html=True)

st.markdown(f"""<div class="pilot-banner">{t("pilot_version")}</div><div class="header-container"><div class="header-title">{t("app_title")}</div><div class="header-subtitle">{t("university")}</div><div class="header-subtitle">{t("subtitle")}</div><div class="header-badge">{t("version")} 58.8 | {n_states} | {n_sites_total} {t("sites")} ({n_sites_verified} {t("verified_sites")})</div></div>""", unsafe_allow_html=True)

with st.expander(f"📤 {t('upload_files')}", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        mv = st.file_uploader(t("validation_file") + ":", type=["csv","xlsx"], key="main_val_uploader")
        if mv:
            try:
                df_loaded = pd.read_csv(mv) if mv.name.endswith(".csv") else pd.read_excel(mv)
                st.session_state["df_validation"] = df_loaded
                st.success(f"{len(df_loaded)} {t('rows')}")
            except Exception as e: st.error(f"{str(e)[:60]}")
    with c2:
        mb = st.file_uploader(t("bulk_file") + ":", type=["csv","xlsx"], key="main_bulk_uploader")
        if mb:
            try:
                df_loaded = pd.read_csv(mb) if mb.name.endswith(".csv") else pd.read_excel(mb)
                st.session_state["df_bulk"] = df_loaded
                st.success(f"{len(df_loaded)} {t('rows')}")
            except Exception as e: st.error(f"{str(e)[:60]}")
    with c3:
        me = st.file_uploader(t("extra_file") + ":", type=["csv","xlsx"], key="main_extra_uploader")
        if me:
            try:
                df_loaded = pd.read_csv(me) if me.name.endswith(".csv") else pd.read_excel(me)
                st.session_state["df_extra"] = df_loaded
                st.info(f"{len(df_loaded)} {t('rows')}")
            except Exception as e: st.error(f"{str(e)[:60]}")

    if VALIDATOR_OK:
        df_to_validate = None
        for key in ["df_validation", "df_bulk", "df_extra"]:
            if key in st.session_state and st.session_state[key] is not None:
                if hasattr(st.session_state[key], "empty") and not st.session_state[key].empty:
                    df_to_validate = st.session_state[key]
                    break

        if df_to_validate is not None:
            st.markdown("---")
            st.markdown("#### 🔍 " + ("فحص جودة البيانات" if is_ar() else "Data Quality Check"))

            if st.button("🔍 " + ("فحص الملف" if is_ar() else "Validate File"),
                         type="secondary", key="run_validator_btn"):
                with st.spinner("Analyzing data..."):
                    st.session_state["validation_report"] = validate_dataframe(df_to_validate, mode="mining")

            if "validation_report" in st.session_state:
                report = st.session_state["validation_report"]
                score = report["score"]
                color = get_quality_color(score)
                label = get_quality_label_ar(score)

                st.markdown(f"""
                <div style="background:linear-gradient(135deg,{color}22,{color}11);
                            border:2px solid {color};border-radius:12px;padding:20px;
                            margin:12px 0;text-align:center;">
                    <div style="font-size:0.9em;color:#666;">
                        {"جودة البيانات" if is_ar() else "Data Quality"}
                    </div>
                    <div style="font-size:3em;font-weight:700;color:{color};margin:8px 0;">
                        {score}/100
                    </div>
                    <div style="font-size:1.2em;font-weight:600;color:{color};">
                        {label}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Rows", report["n_rows"])
                c2.metric("Cols", report["n_cols"])
                c3.metric("❌ Errors", len(report["errors"]))
                c4.metric("⚠️ Warnings", len(report["warnings"]))

                if report["errors"]:
                    st.markdown("---")
                    st.markdown("#### ❌ " + ("أخطاء حرجة" if is_ar() else "Critical Errors"))
                    for err in report["errors"]:
                        msg = err["message_ar"] if is_ar() else err["message_en"]
                        st.error(f"• {msg}")

                if report["warnings"]:
                    st.markdown("---")
                    st.markdown("#### ⚠️ " + ("تحذيرات" if is_ar() else "Warnings"))
                    for w in report["warnings"]:
                        msg = w["message_ar"] if is_ar() else w["message_en"]
                        st.warning(f"• {msg}")

                if report["info"]:
                    with st.expander("ℹ️ " + ("ملاحظات" if is_ar() else "Info")):
                        for i in report["info"]:
                            msg = i["message_ar"] if is_ar() else i["message_en"]
                            st.info(f"• {msg}")

                st.markdown("---")
                if report["is_valid"]:
                    st.success("✅ " + ("البيانات جاهزة للتحليل" if is_ar() else "Data is ready for analysis"))
                else:
                    st.error("❌ " + ("يجب إصلاح الأخطاء قبل المتابعة" if is_ar() else "Fix errors before proceeding"))

    sample = pd.DataFrame({"site_name":["Site1","Site2"],"depth_m":[12.0,15.0],"recharge_mm":[20.0,18.0],"slope_pct":[3.0,4.0],"conductivity":[2.5,3.0],"aquifer":["massive_sandstone","sand_and_gravel"],"soil":["sand","sandy_loam"],"vadose":["sand_gravel","sandstone"],"cn_water_mg_l":[0.10,0.09],"hg_water_mg_l":[0.008,0.007],"actual_contaminated":[1,1]})
    st.download_button("📥 Template / القالب", data=sample.to_csv(index=False).encode("utf-8-sig"), file_name="template.csv", mime="text/csv", key="download_template_btn")

st.markdown("---")

if MODE_KEY == "system":
    tabs = st.tabs([
        t("tab_input"), t("tab_manual"), t("tab_bulk"),
        t("tab_solutions"), t("tab_report"), t("tab_heatmap"),
        t("tab_sensitivity"), t("tab_toxicity"), t("tab_gis"),
        t("tab_monte_carlo"), t("tab_advanced"), t("tab_development"),
        t("tab_auto_maps"), t("tab_calibration"), t("tab_threshold"),
        "⚙️ Profiles", "🔬 External Validation", "🗺️ GIS Raster", "🌐 Live Data"
    ])

    with tabs[0]:
        st.markdown(f'<div class="section-header"><h3>{t("site_selection")}</h3></div>', unsafe_allow_html=True)
        if not DS_OK: st.error("data_sources.py")
        else:
            c1, c2 = st.columns([1, 2])
            with c1: state = st.selectbox(t("state"), get_states_list(), key="tab0_state_select")
            with c2:
                state_info = STATES_DATABASE[state]
                st.markdown(f'<div class="info-card" style="margin-top:28px;"><div style="font-size:0.9em;color:#5c2c16;">{state_info["description"]}</div></div>', unsafe_allow_html=True)
            site_key = st.selectbox(t("site"), get_sites_list(state), key="tab0_site_select")
            site_data = get_site_data(state, site_key)
            mt_key = site_data.get("mining_type", SCOPE_KEY if SCOPE_KEY != "all" else "traditional")
            mt_label = WEIGHTS.get(mt_key, WEIGHTS["traditional"])["ar"] if is_ar() else WEIGHTS.get(mt_key, WEIGHTS["traditional"])["en"]
            badge_class = "mining-industrial" if mt_key == "industrial" else "mining-mixed" if mt_key == "mixed" else "mining-traditional"
            st.markdown(f'<div class="mining-badge {badge_class}">{mt_label}</div>', unsafe_allow_html=True)
            st.session_state["mining_type"] = mt_key
            st.session_state["current_site_key"] = site_key
            st.session_state["current_site_data"] = site_data
            st.session_state["current_state"] = state
            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(t("activity"), site_data.get("activity","N/A"))
            c2.metric(t("season"), site_data.get("season","N/A"))
            c3.metric(t("site_status"), t("contaminated") if site_data["actual_contaminated"] == 1 else t("clean"))
            c4.metric(t("documentation"), t("verified") if site_data.get("verified", False) else t("display"))
            c1, c2 = st.columns(2)
            with c1:
                st.metric("D - " + t("depth"), f"{site_data['depth_m']} {t('m')}")
                st.metric("R - " + t("recharge"), f"{site_data['recharge_mm']} {t('mm_yr')}")
                st.metric("T - " + t("slope"), f"{site_data['slope_pct']} %")
                st.metric("C - " + t("conductivity"), f"{site_data['conductivity']} {t('m_day')}")
            with c2:
                st.metric("A - " + t("aquifer"), AQ(site_data['aquifer']))
                st.metric("S - " + t("soil"), SL(site_data['soil']))
                st.metric("I - " + t("vadose"), VD(site_data['vadose']))
                st.metric("theta - " + t("porosity"), "0.25")
            c1, c2 = st.columns(2)
            c1.metric("CN", f"{site_data['cn_water_mg_l']} mg/L")
            c2.metric("Hg", f"{site_data['hg_water_mg_l']} mg/L")
            st.caption(f"{t('limits')}: CN = 0.05 mg/L | Hg = 0.0007 mg/L")
            try:
                idx = calc_index(get_d_rating(site_data['depth_m']), get_r_rating(site_data['recharge_mm']),
                    get_a_rating(site_data['aquifer']), get_s_rating(site_data['soil']),
                    get_t_rating(site_data['slope_pct']), get_i_rating(site_data['vadose']),
                    get_c_rating(site_data['conductivity']))
                risk = classify(idx)
                st.session_state["ci"] = idx
                st.session_state["cv"] = {"depth":site_data['depth_m'],"recharge":site_data['recharge_mm'],
                    "aquifer":site_data['aquifer'],"soil":site_data['soil'],"slope":site_data['slope_pct'],
                    "vadose":site_data['vadose'],"conductivity":site_data['conductivity'],
                    "cn_water_mg_l":site_data['cn_water_mg_l'],"hg_water_mg_l":site_data['hg_water_mg_l']}
                st.session_state["current_risk"] = risk
                z1, z2, z3 = st.columns(3)
                z1.metric("DRASTIC", f"{idx}/230")
                z2.metric(t("level"), t(risk["level"]))
                z3.metric(t("percentage"), f"{round(idx/230*100,1)}%")
                if risk["color"] == "red": st.error(t(risk["action"]))
                elif risk["color"] == "orange": st.warning(t(risk["action"]))
                elif risk["color"] == "yellow": st.info(t(risk["action"]))
                else: st.success(t(risk["action"]))
                if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mt_key:
                    dt_result = calc_drastic_t(idx, site_data['cn_water_mg_l'], site_data['hg_water_mg_l'],
                        mining_type=mt_key, alpha_override=CALIBRATED_WEIGHTS["alpha"],
                        beta_override=CALIBRATED_WEIGHTS["beta"], SF_override=CALIBRATED_WEIGHTS["SF"])
                    st.caption(t("using_calibrated"))
                else:
                    dt_result = calc_drastic_t(idx, site_data['cn_water_mg_l'], site_data['hg_water_mg_l'], mining_type=mt_key)
                st.markdown("---")
                st.markdown(f"#### {t('drastic_tox')} - {mt_label}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric(t("drastic_tox"), f"{dt_result['drastic_t']}/280", delta=f"+{dt_result['increase_pct']}%")
                m2.metric(t("bonus"), dt_result['toxicity_bonus'])
                m3.metric("alpha (CN)", dt_result['alpha'])
                m4.metric("beta (Hg)", dt_result['beta'])
                with st.expander(t("calculation_details")):
                    d1, d2, d3, d4 = st.columns(4)
                    d1.metric(t("cn_score"), dt_result['cn_score'])
                    d2.metric(t("hg_score"), dt_result['hg_score'])
                    d3.metric(t("base_bonus"), dt_result['base_bonus'])
                    d4.metric(t("source_factor"), dt_result['source_factor'])
                st.markdown("---")
                report_html = generate_html_report(
                    site_info={"name":site_data.get("name_ar",site_key),"state":state,
                        "coords":f"{site_data['coords'][0]}, {site_data['coords'][1]}",
                        "depth":site_data['depth_m'],"recharge":site_data['recharge_mm'],
                        "slope":site_data['slope_pct'],"conductivity":site_data['conductivity'],
                        "cn":site_data['cn_water_mg_l'],"hg":site_data['hg_water_mg_l']},
                    drastic=idx, drastic_t=dt_result["drastic_t"],
                    level=t(risk["level"]), recommendation=t(risk["action"]))
                st.download_button("📄 " + t("tab_report") + " (HTML)",
                    data=report_html.encode("utf-8"),
                    file_name=f"report_{site_key}.html",
                    mime="text/html", key="download_report_btn")
            except ValueError as e: st.error(str(e))

    with tabs[1]:
        st.markdown(f'<div class="section-header"><h3>{t("tab_manual")}</h3></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            new_state = st.text_input(t("state"), value="Sennar", key="new_state_input")
            new_site_key = st.text_input(t("site"), value="New_Site", key="new_site_input")
            new_lat = st.number_input("Lat:", value=13.55, key="new_lat_input")
            new_lon = st.number_input("Lon:", value=33.60, key="new_lon_input")
            new_depth = st.number_input("D:", 0.5, 100.0, 15.0, key="new_depth_input")
            new_recharge = st.number_input("R:", 0.0, 400.0, 20.0, key="new_recharge_input")
        with c2:
            new_slope = st.number_input("T:", 0.0, 30.0, 3.0, key="new_slope_input")
            new_conductivity = st.number_input("C:", 0.01, 200.0, 3.0, key="new_conductivity_input")
            new_aquifer = st.selectbox("A:", VALID_AQUIFERS, key="new_aquifer_select")
            new_soil = st.selectbox("S:", VALID_SOILS, key="new_soil_select")
            new_vadose = st.selectbox("I:", VALID_VADOSE, key="new_vadose_select")
        c1, c2, c3 = st.columns(3)
        with c1: new_cn = st.number_input("CN:", 0.0, 10.0, 0.010, key="new_cn_input")
        with c2: new_hg = st.number_input("Hg:", 0.0, 10.0, 0.001, key="new_hg_input")
        with c3: new_cont = st.selectbox(t("site_status"), [t("clean") + " (0)", t("contaminated") + " (1)"], key="new_cont_select")
        if st.button("💾 " + t("save"), type="primary", key="save_manual_site_btn"):
            site_data = {"name_ar":new_site_key,"coords":(new_lat,new_lon),"depth_m":new_depth,
                "recharge_mm":new_recharge,"slope_pct":new_slope,"conductivity":new_conductivity,
                "aquifer":new_aquifer,"soil":new_soil,"vadose":new_vadose,
                "cn_water_mg_l":new_cn,"hg_water_mg_l":new_hg,
                "actual_contaminated":1 if "1" in new_cont else 0,
                "season":"-","activity":"Manual","verified":True}
            add_new_site(new_state, new_site_key, site_data)
            st.success(t("success")); st.rerun()

    with tabs[2]:
        st.markdown(f'<div class="section-header"><h3>{t("bulk_assessment")}</h3></div>', unsafe_allow_html=True)
        df_bulk = get_loaded_df("df_bulk","df_validation")
        if df_bulk is None: st.warning(t("no_file"))
        else:
            try:
                st.dataframe(df_bulk.head(10), width="stretch")
                _mt = st.session_state.get("mining_type", "traditional")
                _def_th = int(get_optimal_threshold(_mt))
                c1, c2 = st.columns(2)
                with c1: th_d = st.number_input(t("drastic_threshold"), 50, 200, 100, 10, key="bulk_th_d_input")
                with c2: th_dt = st.number_input(t("drastic_tox_threshold"), 50, 280, _def_th, 5, key="bulk_th_dt_input")
                has_tox = "cn_water_mg_l" in df_bulk.columns and "hg_water_mg_l" in df_bulk.columns
                results, d_l, dp_l, act_l = [], [], [], []
                for i, row in df_bulk.iterrows():
                    try:
                        ix = calc_index(get_d_rating(float(row.get("depth_m",15))),
                            get_r_rating(float(row.get("recharge_mm",100))),
                            get_a_rating(str(row.get("aquifer","massive_sandstone"))),
                            get_s_rating(str(row.get("soil","sand"))),
                            get_t_rating(float(row.get("slope_pct",4))),
                            get_i_rating(str(row.get("vadose","sand_gravel"))),
                            get_c_rating(float(row.get("conductivity",5))))
                        d_l.append(ix)
                        if has_tox:
                            cw = float(row.get("cn_water_mg_l",0.0)); hw = float(row.get("hg_water_mg_l",0.0))
                            if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == _mt:
                                ixt = calc_drastic_t(ix, cw, hw, mining_type=_mt,
                                    alpha_override=CALIBRATED_WEIGHTS["alpha"],
                                    beta_override=CALIBRATED_WEIGHTS["beta"],
                                    SF_override=CALIBRATED_WEIGHTS["SF"])["drastic_t"]
                            else: ixt = calc_drastic_t(ix, cw, hw, mining_type=_mt)["drastic_t"]
                        else: ixt = ix
                        dp_l.append(ixt)
                        if "actual_contaminated" in row: act_l.append(int(row["actual_contaminated"]))
                        results.append({"Site":row.get("name",f"R{i+1}"),"DRASTIC":ix,"DRASTIC-Tox":ixt,"Status":"HIGH" if ixt >= th_dt else "LOW"})
                    except Exception: results.append({"Site":f"R{i+1}","DRASTIC":0,"DRASTIC-Tox":0,"Status":"ERR"})
                df_results = pd.DataFrame(results)
                st.dataframe(df_results, width="stretch")
                if has_tox and act_l:
                    st.markdown("---")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**DRASTIC**")
                        md = calculate_confusion_matrix(d_l, act_l, th_d)
                        st.metric(t("kappa"), md["kappa"]); st.metric(t("recall"), f"{md['recall']}%")
                    with c2:
                        st.markdown("**DRASTIC-Tox**")
                        mp = calculate_confusion_matrix(dp_l, act_l, th_dt)
                        st.metric(t("kappa"), mp["kappa"]); st.metric(t("recall"), f"{mp['recall']}%")
                st.download_button(t("download_results"),
                    data=df_results.to_csv(index=False).encode("utf-8-sig"),
                    file_name="results.csv", mime="text/csv", key="download_bulk_results_btn")
            except Exception as e: st.error(str(e))

    with tabs[3]:
        st.markdown(f'<div class="section-header"><h3>{t("solutions")}</h3></div>', unsafe_allow_html=True)
        if "ci" in st.session_state:
            ci = st.session_state["ci"]
            c1, c2 = st.columns(2)
            with c1:
                h = st.checkbox(t("hdpe_liner"), key="chk_hdpe")
                tr = st.checkbox(t("cyanide_treatment"), key="chk_cyanide")
            with c2:
                mo = st.checkbox(t("monitoring_wells"), key="chk_monitoring")
            if h or tr or mo:
                r = mitigate(ci, h, tr, mo)
                c1, c2, c3 = st.columns(3)
                c1.metric(t("before"), ci); c2.metric(t("after"), r["mitigated_index"])
                c3.metric(t("reduction"), f"{r['reduction_pct']}%")

    with tabs[4]:
        st.markdown(f'<div class="section-header"><h3>{t("tab_report")}</h3></div>', unsafe_allow_html=True)
        if "ci" not in st.session_state: st.warning(t("site_selection"))
        else:
            cv = st.session_state.get("cv", {})
            mt_key = st.session_state.get("mining_type","traditional")
            site_key_current = st.session_state.get("current_site_key", "site")
            current_risk = st.session_state.get("current_risk", None)
            c1, c2, c3 = st.columns(3)
            c1.metric("DRASTIC", st.session_state["ci"])
            c2.metric("CN", f"{cv.get('cn_water_mg_l','N/A')} mg/L")
            c3.metric("Hg", f"{cv.get('hg_water_mg_l','N/A')} mg/L")
            st.markdown("---")
            idx = st.session_state["ci"]
            cn = cv.get('cn_water_mg_l',0); hg = cv.get('hg_water_mg_l',0)
            if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mt_key:
                dt_res = calc_drastic_t(idx, cn, hg, mining_type=mt_key,
                    alpha_override=CALIBRATED_WEIGHTS["alpha"],
                    beta_override=CALIBRATED_WEIGHTS["beta"],
                    SF_override=CALIBRATED_WEIGHTS["SF"])
            else: dt_res = calc_drastic_t(idx, cn, hg, mining_type=mt_key)
            sdf = pd.DataFrame({
                "Metric":["DRASTIC","CN_score","Hg_score","Base Bonus","Source Factor","Final Bonus","DRASTIC-Tox","Level"],
                "Value":[idx,dt_res["cn_score"],dt_res["hg_score"],dt_res["base_bonus"],
                    dt_res["source_factor"],dt_res["toxicity_bonus"],dt_res["drastic_t"],t(dt_res["level"])]})
            st.dataframe(sdf, width="stretch", hide_index=True)
            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                if PDF_OK:
                    try:
                        pdf_bytes = generate_pdf_report(
                            site_info={
                                "name": site_key_current,
                                "state": mt_key,
                                "coords": "Sudan",
                                "depth": cv.get("depth", "N/A"),
                                "recharge": cv.get("recharge", "N/A"),
                                "slope": cv.get("slope", "N/A"),
                                "conductivity": cv.get("conductivity", "N/A"),
                                "cn": cn, "hg": hg,
                            },
                            drastic=idx,
                            drastic_t=dt_res["drastic_t"],
                            level=t(dt_res["level"]),
                            recommendation=t(current_risk["action"]) if current_risk else "—",
                            cn_score=dt_res["cn_score"],
                            hg_score=dt_res["hg_score"],
                            base_bonus=dt_res["base_bonus"],
                            source_factor=dt_res["source_factor"],
                            toxicity_bonus=dt_res["toxicity_bonus"],
                            cn_value=cn,
                            hg_value=hg,
                        )
                        if pdf_bytes:
                            st.download_button("📄 تحميل PDF",
                                data=pdf_bytes,
                                file_name=f"report_{site_key_current}.pdf",
                                mime="application/pdf",
                                key="download_pdf_btn")
                        else:
                            st.info("تثبيت fpdf2 مطلوب لتوليد PDF")
                    except Exception as e:
                        st.warning(f"تعذر توليد PDF: {str(e)[:80]}")
                else:
                    st.info("📄 PDF: يتطلب تثبيت fpdf2 و pdf_generator.py")
            with c2:
                if EXCEL_OK:
                    try:
                        spsa_data = st.session_state.get("spsa_result", None)
                        mc_data = st.session_state.get("mc_result", None)
                        excel_bytes = generate_excel_report(
                            site_info={
                                "name": site_key_current,
                                "state": mt_key,
                                "coords": "Sudan",
                                "depth": cv.get("depth", "N/A"),
                                "recharge": cv.get("recharge", "N/A"),
                                "slope": cv.get("slope", "N/A"),
                                "conductivity": cv.get("conductivity", "N/A"),
                                "cn": cn, "hg": hg,
                                "aquifer": cv.get("aquifer", "—"),
                                "soil": cv.get("soil", "—"),
                                "vadose": cv.get("vadose", "—"),
                                "D_rating": get_d_rating(cv.get("depth", 15)),
                                "R_rating": get_r_rating(cv.get("recharge", 100)),
                                "A_rating": get_a_rating(cv.get("aquifer", "massive_sandstone")),
                                "S_rating": get_s_rating(cv.get("soil", "sand")),
                                "T_rating": get_t_rating(cv.get("slope", 4)),
                                "I_rating": get_i_rating(cv.get("vadose", "sand_gravel")),
                                "C_rating": get_c_rating(cv.get("conductivity", 5)),
                            },
                            drastic_result=dt_res,
                            risk_info=current_risk if current_risk else classify(idx),
                            mining_type=mt_key,
                            spsa_result=spsa_data,
                            mc_result=mc_data,
                        )
                        if excel_bytes:
                            st.download_button("📊 تحميل Excel",
                                data=excel_bytes,
                                file_name=f"report_{site_key_current}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="download_excel_btn")
                        else:
                            st.info("openpyxl مطلوب لتوليد Excel")
                    except Exception as e:
                        st.warning(f"تعذر توليد Excel: {str(e)[:80]}")
                else:
                    st.info("📊 Excel: يتطلب excel_exporter.py")
            st.caption("PDF و Excel يحتويان على ملخص كامل + التوصيات")

    with tabs[5]:
        st.markdown(f'<div class="section-header"><h3>{t("heatmap_title")}</h3></div>', unsafe_allow_html=True)
        st.info(t("shows_verified_only") + f" ({n_sites_verified})")
        if not DS_OK: st.error("data_sources.py")
        else:
            c1, c2 = st.columns(2)
            with c1: mm = st.radio(t("view_mode"), [t("both"), t("markers"), t("heat")], key="map_mode_radio", horizontal=True)
            with c2: mh = st.slider(t("height"), 400, 900, 600, 50, key="map_height_slider")
            sh = mm in [t("both"), t("heat")]
            sm = mm in [t("both"), t("markers")]
            with st.spinner(t("calculating")):
                mapa, stats, df_sites = build_heatmap_verified(show_heat=sh, show_markers=sm)
            st_folium(mapa, height=mh, key="map_folium_v588", use_container_width=True)
            st.markdown("---")
            st.markdown(f"#### {t('statistics')}")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric(t("low"), stats["low"]); c2.metric(t("medium"), stats["medium"])
            c3.metric(t("high"), stats["high"]); c4.metric(t("very_high"), stats["very_high"])
            c5.metric(t("total"), sum(stats.values()))
            st.markdown("---")
            st.dataframe(df_sites, width="stretch")
            st.download_button(t("download_sites"),
                data=df_sites.to_csv(index=False).encode("utf-8-sig"),
                file_name="verified_sites.csv", mime="text/csv", key="download_sites_btn")

    with tabs[6]:
        st.markdown(f'<div class="section-header"><h3>{t("sensitivity_title")}</h3></div>', unsafe_allow_html=True)
        st.info(t("sensitivity_hint"))
        if "cv" not in st.session_state: st.warning(t("site_selection"))
        else:
            sub_sens = st.tabs([t("spsa_tab"), t("variation_tab")])

            with sub_sens[0]:
                st.markdown(f"#### {t('spsa_title')}")
                st.markdown(f'<div class="research-note"><b>{t("reference")}:</b> Napolitano &amp; Fabbri (1996)<br><b>{t("formula")}:</b> Si = (Wi × Ri / DI) × 100</div>', unsafe_allow_html=True)
                st.info(t("spsa_explanation"))

                if st.button("🚀 " + t("run_spsa"), type="primary", key="run_spsa_btn"):
                    with st.spinner(t("calculating")):
                        st.session_state["spsa_result"] = spsa_analysis(st.session_state["cv"])

                if "spsa_result" in st.session_state:
                    spsa = st.session_state["spsa_result"]
                    st.success(f"🏆 {t('most_influential')}: **{spsa['most_influential']}** | {t('base_index')}: **{spsa['base_index']}**")
                    st.markdown("---")
                    rows = []
                    for p in spsa["parameters"]:
                        rows.append({
                            t("parameter"): p["param"], t("weight_wi"): p["weight"],
                            t("rating_ri"): p["rating"], t("weighted"): p["weighted_score"],
                            t("theoretical_pct"): f"{p['theoretical_pct']}%",
                            t("effective_pct"): f"{p['effective_pct']}%",
                            t("difference"): f"{p['difference']:+.2f}%",
                        })
                    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
                    st.markdown("---")
                    st.markdown(f"#### {t('interpretation')}")
                    for p in spsa["parameters"][:3]:
                        if p["difference"] > 0:
                            st.info(f"**{p['param']}**: {t('more_important')} (+{p['difference']:.2f}%)")
                        elif p["difference"] < 0:
                            st.warning(f"**{p['param']}**: {t('less_important')} ({p['difference']:.2f}%)")
                    try:
                        import plotly.graph_objects as go
                        fig = go.Figure()
                        params = [p["param"] for p in spsa["parameters"]]
                        theo = [p["theoretical_pct"] for p in spsa["parameters"]]
                        eff = [p["effective_pct"] for p in spsa["parameters"]]
                        fig.add_trace(go.Bar(name=t("theoretical_pct"), x=params, y=theo, marker_color='#c19a6b'))
                        fig.add_trace(go.Bar(name=t("effective_pct"), x=params, y=eff, marker_color='#5c2c16'))
                        fig.update_layout(barmode='group', height=400, xaxis_title=t("parameter"), yaxis_title="%")
                        st.plotly_chart(fig, use_container_width=True, key="spsa_chart")
                    except Exception:
                        pass

            with sub_sens[1]:
                st.markdown(f"#### {t('variation_title')}")
                st.info(t("variation_explanation"))
                vp = st.slider(t("change_pct"), 5, 30, 10, 5, key="sens_var_pct_slider")
                if st.button("🚀 " + t("run"), type="primary", key="run_sens_btn"):
                    with st.spinner(t("calculating")):
                        st.session_state["sens_result"] = sensitivity_analysis(st.session_state["cv"], vp/100.0)
                if "sens_result" in st.session_state:
                    sens = st.session_state["sens_result"]
                    st.success(f"{t('most_sensitive')}: {sens['most_sensitive']}")
                    rows = []
                    for p, d in sens["parameters"].items():
                        rows.append({t("parameter"):p,t("original_value"):d["original_phys"],
                            t("modified_value"):d["modified_phys"],t("new_index"):d["new_index"],
                            t("change"):d["change"],t("sensitivity_pct"):d["sensitivity"]})
                    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    with tabs[7]:
        st.markdown(f'<div class="section-header"><h3>{t("toxicity_title")}</h3></div>', unsafe_allow_html=True)
        if "cv" not in st.session_state: st.warning(t("site_selection"))
        else:
            cv = st.session_state["cv"]
            hgw = cv.get("hg_water_mg_l",0.011); cnw = cv.get("cn_water_mg_l",0.025)
            c1, c2 = st.columns(2)
            c1.metric("CN", f"{cnw} mg/L"); c2.metric("Hg", f"{hgw} mg/L")
            st.markdown(f"#### {t('additional_inputs')}")
            c1, c2 = st.columns(2)
            with c1: hgs = st.number_input(t("hg_in_soil"), 0.0, 100.0, 0.5, 0.1, key="tox_hgs_input")
            with c2: cns = st.number_input(t("cn_in_soil"), 0.0, 100.0, 5.0, 0.5, key="tox_cns_input")
            if st.button(t("analyze"), type="primary", key="run_tox_btn"):
                mt_tox = st.session_state.get("mining_type", "traditional")
                if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mt_tox:
                    st.session_state["tox_result"] = weighted_toxicity(hgw, hgs, cnw, cns, mining_type=mt_tox,
                        alpha_override=CALIBRATED_WEIGHTS["alpha"],
                        beta_override=CALIBRATED_WEIGHTS["beta"],
                        SF_override=CALIBRATED_WEIGHTS["SF"])
                else:
                    st.session_state["tox_result"] = weighted_toxicity(hgw, hgs, cnw, cns, mining_type=mt_tox)
            if "tox_result" in st.session_state:
                tox = st.session_state["tox_result"]
                st.markdown("---")
                st.markdown(f"#### {t('toxicity_metrics')}")
                c1, c2, c3 = st.columns(3)
                c1.metric(t("cn_score"), tox["cn_score"])
                c2.metric(t("hg_score"), tox["hg_score"])
                c3.metric(t("base_bonus"), tox["base_bonus"])
                c1, c2 = st.columns(2)
                c1.metric(t("source_factor") + " (SF)", tox["source_factor"])
                c2.metric(t("soil_factor"), tox["soil_factor"])
                st.markdown("---")
                st.markdown(f"#### {t('two_metrics_explained')}")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"""<div class="cal-result-card" style="background:linear-gradient(135deg,#e3f2fd,#bbdefb);">
                        <div class="cal-result-label">{t('drastic_tox_bonus')}</div>
                        <div class="cal-result-value">{tox['drastic_tox_bonus']}</div>
                        <div style="font-size:0.8em;color:#0d47a1;margin-top:8px;">
                            {t('used_in_report')} (Base × SF)
                        </div>
                    </div>""", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""<div class="cal-result-card" style="background:linear-gradient(135deg,#fff3e0,#ffe0b2);">
                        <div class="cal-result-label">{t('toxicity_index')}</div>
                        <div class="cal-result-value">{tox['index']}</div>
                        <div style="font-size:0.8em;color:#e65100;margin-top:8px;">
                            Bonus × Soil Factor
                        </div>
                    </div>""", unsafe_allow_html=True)
                st.markdown("---")
                c1, c2 = st.columns(2)
                c1.metric(t("category"), t(tox["category"]))
                c2.metric(t("action"), t(tox["action"]))

    with tabs[8]:
        st.markdown(f'<div class="section-header"><h3>{t("gis_title")}</h3></div>', unsafe_allow_html=True)
        if not DS_OK: st.error("data_sources.py")
        else:
            fm = st.radio(t("view_mode"), [t("all"), t("verified_only"), t("display_only_filter")],
                horizontal=True, key="gis_filter_radio")
            try:
                df_all = get_all_sites_as_dataframe_with_flag()
                if fm == t("verified_only"): df_show = df_all[df_all["verified"] == True] if "verified" in df_all.columns else df_all
                elif fm == t("display_only_filter"): df_show = df_all[df_all["verified"] == False] if "verified" in df_all.columns else df_all.head(0)
                else: df_show = df_all
                st.caption(f"{len(df_show)} {t('sites')}")
                st.dataframe(df_show, width="stretch")
                st.download_button("📥 CSV",
                    data=df_show.to_csv(index=False).encode("utf-8-sig"),
                    file_name="sites_filtered.csv", mime="text/csv", key="download_gis_csv_btn")
            except Exception as e: st.error(str(e))

    with tabs[9]:
        st.markdown(f'<div class="section-header"><h3>{t("mc_title")}</h3></div>', unsafe_allow_html=True)
        if "ci" not in st.session_state:
            st.warning(t("site_selection"))
        else:
            ni = st.slider(t("simulations"), 100, 5000, 1000, 100, key="mc_n_iter_slider")
            vp = st.slider(t("variation"), 5, 30, 15, 5, key="mc_var_pct_slider")
            if st.button(t("run"), type="primary", key="run_mc_btn"):
                mt_mc = st.session_state.get("mining_type", "traditional")
                cal_w = CALIBRATED_WEIGHTS if (CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mt_mc) else None
                st.session_state["mc_result"] = monte_carlo_analysis(
                    st.session_state["cv"], ni, vp/100.0,
                    mining_type=mt_mc, calibrated_weights=cal_w)
            if "mc_result" in st.session_state:
                mc = st.session_state["mc_result"]
                st.markdown("---")
                st.markdown(f"#### DRASTIC")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(t("mean"), mc["mean"]); c2.metric(t("std"), mc["std"])
                c3.metric(t("ci_90"), f"{mc['ci_90'][0]}-{mc['ci_90'][1]}")
                c4.metric("P>140", f"{mc['prob_over_140']}%")
                st.markdown("---")
                st.markdown(f"#### DRASTIC-Tox (مع Bonus)")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(t("mean"), mc["tox_mean"]); c2.metric(t("std"), mc["tox_std"])
                c3.metric(t("ci_90"), f"{mc['tox_ci_90'][0]}-{mc['tox_ci_90'][1]}")
                c4.metric("P>140", f"{mc['tox_prob_over_140']}%")
                c1, c2 = st.columns(2)
                c1.metric("P>180", f"{mc['tox_prob_over_180']}%")
                c2.metric("Range", f"{mc['tox_min']}-{mc['tox_max']}")

    with tabs[10]:
        st.markdown(f'<div class="section-header"><h3>{t("advanced_title")}</h3></div>', unsafe_allow_html=True)
        st.info(t("advanced_hint"))
        if not SKLEARN_OK: st.error(t("no_sklearn"))
        else:
            df_val = st.session_state.get("df_validation")
            if df_val is None: st.warning(t("upload_validation_first"))
            else:
                has_tox = "cn_water_mg_l" in df_val.columns and "hg_water_mg_l" in df_val.columns
                if not has_tox: st.error(t("file_missing_tox"))
                else:
                    mt = st.session_state.get("mining_type", "traditional")
                    _def = int(get_optimal_threshold(mt))
                    c1, c2 = st.columns(2)
                    with c1: th_d = st.number_input("DRASTIC:", 50, 200, 100, 10, key="adv_th_d_input")
                    with c2: th_dt = st.number_input("DRASTIC-Tox:", 50, 280, _def, 5, key="adv_th_dt_input")
                    d_l, dp_l, act_l = [], [], []
                    for i, row in df_val.iterrows():
                        try:
                            ix = calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])),
                                get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])),
                                get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])),
                                get_c_rating(float(row["conductivity"])))
                            d_l.append(ix)
                            cw = float(row.get("cn_water_mg_l",0.0)); hw = float(row.get("hg_water_mg_l",0.0))
                            if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mt:
                                dp_l.append(calc_drastic_t(ix, cw, hw, mining_type=mt,
                                    alpha_override=CALIBRATED_WEIGHTS["alpha"],
                                    beta_override=CALIBRATED_WEIGHTS["beta"],
                                    SF_override=CALIBRATED_WEIGHTS["SF"])["drastic_t"])
                            else: dp_l.append(calc_drastic_t(ix, cw, hw, mining_type=mt)["drastic_t"])
                            act_l.append(int(row["actual_contaminated"]))
                        except Exception: pass
                    if not d_l: st.error(t("no_file"))
                    else:
                        if st.button("🚀 " + t("run"), type="primary", key="run_adv_btn"):
                            with st.spinner(t("calculating")):
                                m_d = compute_basic_metrics(act_l, d_l, th_d)
                                b_d = bootstrap_kappa_ci(act_l, d_l, th_d, n_boot=1000)
                                l_d = loocv_analysis(act_l, d_l, th_d)
                                m_dt = compute_basic_metrics(act_l, dp_l, th_dt)
                                b_dt = bootstrap_kappa_ci(act_l, dp_l, th_dt, n_boot=1000)
                                l_dt = loocv_analysis(act_l, dp_l, th_dt)
                                st.session_state["adv_results"] = {"m_d":m_d,"b_d":b_d,"l_d":l_d,"m_dt":m_dt,"b_dt":b_dt,"l_dt":l_dt}
                        if "adv_results" in st.session_state:
                            r = st.session_state["adv_results"]
                            st.markdown("---")
                            c1, c2 = st.columns(2)
                            with c1:
                                st.markdown(f"#### DRASTIC")
                                if "error" not in r["m_d"]:
                                    st.metric(t("kappa"), r["m_d"]["kappa"])
                                    st.metric(t("roc_auc"), r["m_d"]["auc"])
                                    st.metric(t("f1_score"), r["m_d"]["f1"])
                                    st.metric(t("recall"), f"{r['m_d']['recall']}%")
                                    with st.expander(t("confusion_matrix")):
                                        st.write(f"TP={r['m_d']['tp']} TN={r['m_d']['tn']} FP={r['m_d']['fp']} FN={r['m_d']['fn']}")
                                    with st.expander(t("bootstrap_ci")):
                                        st.write(f"[{r['b_d']['ci_low']}, {r['b_d']['ci_high']}]")
                                    with st.expander(t("loocv")):
                                        st.write(f"Kappa={r['l_d']['kappa']} Acc={r['l_d']['accuracy']}%")
                            with c2:
                                st.markdown(f"#### DRASTIC-Tox")
                                if "error" not in r["m_dt"]:
                                    st.metric(t("kappa"), r["m_dt"]["kappa"])
                                    st.metric(t("roc_auc"), r["m_dt"]["auc"])
                                    st.metric(t("f1_score"), r["m_dt"]["f1"])
                                    st.metric(t("recall"), f"{r['m_dt']['recall']}%")
                                    with st.expander(t("confusion_matrix")):
                                        st.write(f"TP={r['m_dt']['tp']} TN={r['m_dt']['tn']} FP={r['m_dt']['fp']} FN={r['m_dt']['fn']}")
                                    with st.expander(t("bootstrap_ci")):
                                        st.write(f"[{r['b_dt']['ci_low']}, {r['b_dt']['ci_high']}]")
                                    with st.expander(t("loocv")):
                                        st.write(f"Kappa={r['l_dt']['kappa']} Acc={r['l_dt']['accuracy']}%")

    with tabs[11]:
        st.markdown(f'<div class="section-header"><h3>{t("development_title")}</h3></div>', unsafe_allow_html=True)
        if not DEV_OK: st.error(t("no_dev_module"))
        elif not SKLEARN_OK: st.error(t("no_sklearn"))
        else:
            sub = st.tabs([t("gray_zone"), t("calibration_ab"), t("model_comparison")])
            with sub[0]:
                st.markdown(f"#### {t('gray_zone')}")
                st.warning(t("gray_warning"))
                gray_rows = []
                for sname, sdata in GRAY_ZONE_SITES.items():
                    for sk, sd in sdata.get("sites", {}).items():
                        gray_rows.append({"Site":sd.get("name_ar",sk),"D":sd["depth_m"],"R":sd["recharge_mm"],
                            "CN":sd["cn_water_mg_l"],"Hg":sd["hg_water_mg_l"],
                            "Status":t("contaminated") if sd["actual_contaminated"] == 1 else t("clean")})
                st.dataframe(pd.DataFrame(gray_rows), width="stretch", hide_index=True)
                st.markdown("---")
                mo = st.radio(t("select"), [t("verified_only_11"), t("with_gray_17")], key="gray_merge_radio")
                inc_gray = "17" in mo
                if st.button("🔄 " + t("load_data"), type="primary", key="load_combined_btn"):
                    df_c = get_combined_dataset(include_gray=inc_gray)
                    dv, dtv = [], []
                    for _, row in df_c.iterrows():
                        try:
                            ix = calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])),
                                get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])),
                                get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])),
                                get_c_rating(float(row["conductivity"])))
                            dt = calc_drastic_t(ix, float(row["cn_water_mg_l"]), float(row["hg_water_mg_l"]),
                                mining_type="traditional")["drastic_t"]
                            dv.append(ix); dtv.append(dt)
                        except Exception: dv.append(0); dtv.append(0)
                    df_c = df_c.copy(); df_c["DRASTIC"] = dv; df_c["DRASTIC_Tox"] = dtv
                    st.session_state["df_combined"] = df_c
                    st.success(f"{len(df_c)} {t('sites')}"); st.rerun()
                if "df_combined" in st.session_state:
                    df_s = st.session_state["df_combined"]
                    st.markdown("---"); st.dataframe(df_s, width="stretch")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(t("total_sites"), len(df_s))
                    c2.metric(t("verified_sites"), safe_sum(df_s, "verified", 0))
                    c3.metric(t("gray_sites"), safe_sum(df_s, "is_gray_zone", 0))
                    c4.metric(t("contaminated_sites"), safe_sum(df_s, "actual_contaminated", 0))
            with sub[1]:
                st.markdown(f"#### {t('calibration_ab')}")
                df_c = get_loaded_df("df_combined", "df_validation")
                if df_c is None: st.warning(t("calibrate_hint"))
                else:
                    if "DRASTIC" not in df_c.columns:
                        dv = []
                        for _, row in df_c.iterrows():
                            try: dv.append(calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])),
                                get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])),
                                get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])),
                                get_c_rating(float(row["conductivity"]))))
                            except Exception: dv.append(0)
                        df_c = df_c.copy(); df_c["DRASTIC"] = dv; st.session_state["df_combined"] = df_c
                    c1, c2 = st.columns(2)
                    with c1:
                        amin = st.slider(t("alpha_min"), 0.0, 1.0, 0.1, 0.1, key="cal_a_min_slider")
                        amax = st.slider(t("alpha_max"), 0.0, 1.0, 0.9, 0.1, key="cal_a_max_slider")
                    with c2:
                        bmin = st.slider(t("beta_min"), 0.0, 1.0, 0.1, 0.1, key="cal_b_min_slider")
                        bmax = st.slider(t("beta_max"), 0.0, 1.0, 0.9, 0.1, key="cal_b_max_slider")
                    if st.button("🚀 " + t("run_calibration"), type="primary", key="run_cal_btn"):
                        with st.spinner(t("searching")):
                            ar = list(np.arange(amin, amax + 0.05, 0.1))
                            br = list(np.arange(bmin, bmax + 0.05, 0.1))
                            st.session_state["cal_result"] = calibrate_alpha_beta(df_c, {"DRASTIC":100,"DRASTIC-T":140}, alpha_range=ar, beta_range=br)
                    if "cal_result" in st.session_state:
                        res = st.session_state["cal_result"]
                        if "error" in res: st.error(res["error"])
                        else:
                            st.markdown("---")
                            c1, c2 = st.columns(2)
                            with c1:
                                st.markdown(f"#### {t('best_kappa')}")
                                bk = res["best_kappa"]
                                st.metric("alpha", bk["alpha"]); st.metric("beta", bk["beta"])
                                st.metric(t("kappa"), bk["kappa"]); st.metric(t("recall"), f"{bk['recall']}%")
                            with c2:
                                st.markdown(f"#### {t('balanced')}")
                                bb = res["best_balanced"]
                                st.metric("alpha", bb["alpha"]); st.metric("beta", bb["beta"])
                                st.metric(t("kappa"), bb["kappa"]); st.metric(t("recall"), f"{bb['recall']}%")
            with sub[2]:
                st.markdown(f"#### {t('model_comparison')}")
                df_c = get_loaded_df("df_combined", "df_validation")
                if df_c is None: st.warning(t("calibrate_hint"))
                else:
                    if st.button("🚀 " + t("run"), type="primary", key="run_cmp_btn"):
                        with st.spinner(t("calculating")):
                            st.session_state["cmp_results"] = compare_models(df_c,
                                (get_d_rating,get_r_rating,get_a_rating,get_s_rating,get_t_rating,get_i_rating,get_c_rating),
                                calc_index)
                    if "cmp_results" in st.session_state:
                        r = st.session_state["cmp_results"]
                        rows = []
                        for mn, mt in r.items():
                            if "error" not in mt:
                                rows.append({"Model":mn,t("kappa"):mt["kappa"],t("recall"):mt["recall"],
                                    t("precision"):mt["precision"],t("accuracy"):mt["accuracy"],"ROC-AUC":mt["auc"]})
                        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    with tabs[12]:
        st.markdown(f'<div class="section-header"><h3>{t("tab_auto_maps")}</h3></div>', unsafe_allow_html=True)
        if not MAPS_OK: st.error("auto_maps.py")
        else:
            df_s = get_loaded_df("df_combined","df_validation")
            if df_s is None: st.warning(t("no_file"))
            else:
                st.write(f"{len(df_s)} {t('sites')}")
                if st.button("🎨 " + t("run"), type="primary", key="gen_maps_btn"):
                    with st.spinner(t("calculating")):
                        try:
                            df_m = df_s.copy()
                            if "coords" in df_m.columns and "lon" not in df_m.columns:
                                df_m["lat"] = df_m["coords"].apply(lambda c: c[0] if isinstance(c,(tuple,list)) and len(c)>=2 else None)
                                df_m["lon"] = df_m["coords"].apply(lambda c: c[1] if isinstance(c,(tuple,list)) and len(c)>=2 else None)
                            if "lon" not in df_m.columns: st.error("No coordinates"); st.stop()
                            if "DRASTIC" not in df_m.columns:
                                dv = []
                                for _, row in df_m.iterrows():
                                    try: dv.append(calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])),
                                        get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])),
                                        get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])),
                                        get_c_rating(float(row["conductivity"]))))
                                    except Exception: dv.append(0)
                                df_m["DRASTIC"] = dv
                            if "DRASTIC_Tox" not in df_m.columns:
                                dtv = []
                                for _, row in df_m.iterrows():
                                    try:
                                        ix = calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])),
                                            get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])),
                                            get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])),
                                            get_c_rating(float(row["conductivity"])))
                                        dtv.append(calc_drastic_t(ix, float(row.get("cn_water_mg_l",0)),
                                            float(row.get("hg_water_mg_l",0)), mining_type="traditional")["drastic_t"])
                                    except Exception: dtv.append(0)
                                df_m["DRASTIC_Tox"] = dtv
                            rm = {}
                            if "cn_water_mg_l" in df_m.columns: rm["cn_water_mg_l"] = "CN"
                            if "hg_water_mg_l" in df_m.columns: rm["hg_water_mg_l"] = "Hg"
                            if rm: df_m = df_m.rename(columns=rm)
                            df_p = prepare_df_for_maps(df_m, (get_d_rating,get_r_rating,get_a_rating,get_s_rating,get_t_rating,get_i_rating,get_c_rating))
                            fig = generate_auto_maps(df_p, show_sudan=True)
                            st.session_state["auto_maps_fig"] = fig
                            st.success(f"{len(df_p)} {t('sites')}")
                        except Exception as e: st.error(str(e))
                if "auto_maps_fig" in st.session_state:
                    st.plotly_chart(st.session_state["auto_maps_fig"], use_container_width=True, key="auto_maps_chart_v588")
                    html = st.session_state["auto_maps_fig"].to_html(include_plotlyjs='cdn')
                    st.download_button("📥 HTML", data=html.encode("utf-8"),
                        file_name="auto_maps.html", mime="text/html", key="download_maps_html_btn")

    with tabs[13]:
        st.markdown(f'<div class="section-header"><h3>{t("auto_calibration")}</h3></div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="research-note"><b>{t('references')}:</b><br>• Konate et al. (2025)<br>• Karan et al. (2018)<br>• Landis &amp; Koch (1977)</div>""", unsafe_allow_html=True)
        if not AUTOCAL_OK: st.error("auto_calibration.py")
        elif not SKLEARN_OK: st.error(t("no_sklearn"))
        else:
            if SCOPE_KEY == "industrial" and INDUSTRIAL_SITES:
                df_c = pd.DataFrame(INDUSTRIAL_SITES)
            else:
                df_c = get_loaded_df("df_validation","df_bulk","df_combined")
            if df_c is None: st.warning(t("upload_validation_first"))
            else:
                req = ["depth_m","recharge_mm","slope_pct","conductivity","aquifer","soil","vadose","cn_water_mg_l","hg_water_mg_l","actual_contaminated"]
                miss = [x for x in req if x not in df_c.columns]
                if miss: st.error(f"Missing: {miss}")
                else:
                    st.success(f"{t('file_has')} {len(df_c)} {t('sites')}")
                    if WM_OK:
                        ceiling = detect_ceiling_effect(df_c, SCOPE_KEY if SCOPE_KEY != "all" else "traditional")
                        if ceiling:
                            st.warning("Ceiling Effect detected in CN scores — calibrated alpha may be unreliable.")
                    st.markdown("---")
                    st.markdown(f"#### {t('calibration_settings')}")
                    c1, c2, c3 = st.columns(3)
                    with c1: mc = st.selectbox(t("mining_pattern"), ["traditional","industrial","mixed"], key="cal_mining_type_select")
                    with c2: ns = st.slider(t("search_precision"), 10, 30, 15, 5, key="cal_n_steps_slider")
                    with c3: th = st.number_input(t("drastic_tox_threshold"), 50, 280, 140, 10, key="cal_threshold_input")
                    st.caption(f"{t('combinations')}: {ns**3:,}")
                    st.markdown("---")
                    b1, b2, b3 = st.columns(3)
                    with b1: rc = st.button("🚀 " + t("run_auto_calibration"), type="primary", key="run_auto_cal_btn", use_container_width=True)
                    with b2: rcm = st.button("📊 " + t("compare"), key="run_compare_btn", use_container_width=True)
                    with b3: rst = st.button("🔄 " + t("reset"), key="reset_weights_btn", use_container_width=True)
                    if rst:
                        for k in ["auto_cal_result","auto_cal_mining_type","comparison_result"]: st.session_state.pop(k, None)
                        st.success(t("reset_done")); st.rerun()
                    if rcm:
                        with st.spinner(t("calculating")): cmp = compare_with_defaults(df_c, mc, threshold=th)
                        if "error" in cmp: st.error(cmp["error"])
                        else: st.session_state["comparison_result"] = cmp
                    if rc:
                        with st.spinner(f"{t('searching')} {ns**3:,}..."):
                            result = auto_calibrate_weights(df_c, mc, n_steps=ns, threshold=th)
                        if "error" in result: st.error(result["error"])
                        else:
                            st.session_state["auto_cal_result"] = result
                            st.session_state["auto_cal_mining_type"] = mc
                            if WM_OK:
                                pk = save_calibrated_profile(mc, result, len(df_c))
                                st.success(f"{t('kappa')} = {result['best_kappa']} — Saved: {pk}")
                            else:
                                st.success(f"{t('kappa')} = {result['best_kappa']}")
                            st.rerun()
                    if "comparison_result" in st.session_state:
                        cmp = st.session_state["comparison_result"]
                        st.markdown("---")
                        c1, c2, c3 = st.columns(3)
                        with c1: st.metric(t("default_kappa"), cmp["default_kappa"])
                        with c2: st.metric(t("calibrated_kappa"), cmp["best_kappa"] or "-",
                            delta=f"{cmp.get('improvement',0):+.4f}" if cmp.get("best_kappa") else None)
                        with c3: st.metric(t("recall"), f"{cmp.get('best_recall',0)}%")
                    if "auto_cal_result" in st.session_state:
                        res = st.session_state["auto_cal_result"]
                        ms = st.session_state.get("auto_cal_mining_type","traditional")
                        interp = res.get("kappa_interpretation", {})
                        st.markdown("---")
                        lbl = WEIGHTS[ms]["ar"] if is_ar() else WEIGHTS[ms]["en"]
                        st.markdown(f"### {t('result')} - {lbl}")
                        kc = "kappa-excellent" if interp.get("level") == "ممتاز" else "kappa-good" if interp.get("level") == "جيد" else "kappa-moderate" if interp.get("level") == "متوسط" else "kappa-fair" if interp.get("level") == "مقبول" else "kappa-poor"
                        st.markdown(f'<div class="kappa-box {kc}"><div style="font-size:0.9em;opacity:0.9;">{t("kappa")}</div><div style="font-size:3em;font-weight:700;margin:8px 0;">{res["best_kappa"]}</div><div style="font-size:1.3em;font-weight:600;">{interp.get("level","-")} - {interp.get("en","-")}</div></div>', unsafe_allow_html=True)
                        st.markdown(f"#### {t('optimal_weights')}")
                        c1, c2, c3, c4 = st.columns(4)
                        with c1: st.markdown(f'<div class="cal-result-card"><div class="cal-result-label">alpha (CN)</div><div class="cal-result-value">{res["best_alpha"]}</div></div>', unsafe_allow_html=True)
                        with c2: st.markdown(f'<div class="cal-result-card"><div class="cal-result-label">beta (Hg)</div><div class="cal-result-value">{res["best_beta"]}</div></div>', unsafe_allow_html=True)
                        with c3: st.markdown(f'<div class="cal-result-card"><div class="cal-result-label">SF</div><div class="cal-result-value">{res["best_SF"]}</div></div>', unsafe_allow_html=True)
                        with c4: st.markdown(f'<div class="cal-result-card"><div class="cal-result-label">{t("recall_pct")}</div><div class="cal-result-value">{res["best_recall"]}%</div></div>', unsafe_allow_html=True)
                        st.markdown("---")
                        st.markdown(f"#### {t('top_10')}")
                        tr_ = res.get("all_results", [])[:10]
                        if tr_:
                            dt = pd.DataFrame(tr_).rename(columns={"alpha":"alpha (CN)","beta":"beta (Hg)","SF":"SF","kappa":t("kappa"),"recall":t("recall")})
                            dt.insert(0, t("rank"), range(1, len(dt)+1))
                            st.dataframe(dt, width="stretch", hide_index=True)
                        st.markdown("---")
                        st.warning(t("calibration_warning"))

    with tabs[14]:
        st.markdown(f'<div class="section-header"><h3>{t("optimal_threshold_title")}</h3></div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="research-note"><b>{t('references')}:</b><br>• Youden (1950)<br>• Landis &amp; Koch (1977)</div>""", unsafe_allow_html=True)
        st.info(t("threshold_hint"))
        if not AUTOCAL_OK: st.error("auto_calibration.py")
        elif not SKLEARN_OK: st.error(t("no_sklearn"))
        else:
            if SCOPE_KEY == "industrial" and INDUSTRIAL_SITES:
                df_o = pd.DataFrame(INDUSTRIAL_SITES)
            else:
                df_o = get_loaded_df("df_validation","df_combined")
            if df_o is None: st.warning(t("upload_validation_first"))
            else:
                mto = st.selectbox(t("mining_pattern"), ["traditional","industrial","mixed"], key="opt_mining_type_select")
                uc = False
                if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mto:
                    uc = st.checkbox(f"{t('use_calibrated_weights')} (Kappa = {CALIBRATED_WEIGHTS.get('kappa','-')})", value=True, key="use_calibrated_for_opt_chk")
                if st.button("🚀 " + t("compute_threshold"), type="primary", key="run_opt_threshold_btn"):
                    with st.spinner(t("calculating")):
                        try:
                            if uc and CALIBRATED_WEIGHTS:
                                optr = find_optimal_threshold(df_o, mto, alpha=CALIBRATED_WEIGHTS["alpha"],
                                    beta=CALIBRATED_WEIGHTS["beta"], SF=CALIBRATED_WEIGHTS["SF"])
                            else: optr = find_optimal_threshold(df_o, mto)
                            st.session_state["opt_threshold_result"] = optr
                        except Exception as e: st.error(str(e))
                if "opt_threshold_result" in st.session_state:
                    res = st.session_state["opt_threshold_result"]
                    if "error" in res: st.error(res["error"])
                    else:
                        lbl = WEIGHTS[res["mining_type"]]["ar"] if is_ar() else WEIGHTS[res["mining_type"]]["en"]
                        st.markdown("---")
                        st.markdown(f"### {t('optimal_threshold_title')} - {lbl}")
                        c1, c2, c3, c4 = st.columns(4)
                        with c1: st.markdown(f'<div class="cal-result-card" style="background:linear-gradient(135deg,#e8f5e9,#c8e6c9);"><div class="cal-result-label">{t("threshold")}</div><div class="cal-result-value">{res["optimal_threshold"]}</div><div class="cal-result-label">{t("youden_index")}</div></div>', unsafe_allow_html=True)
                        with c2: st.markdown(f'<div class="cal-result-card"><div class="cal-result-label">J</div><div class="cal-result-value">{res["J_max"]}</div></div>', unsafe_allow_html=True)
                        with c3: st.markdown(f'<div class="cal-result-card"><div class="cal-result-label">{t("sensitivity")}</div><div class="cal-result-value">{res["sensitivity"]}</div></div>', unsafe_allow_html=True)
                        with c4: st.markdown(f'<div class="cal-result-card"><div class="cal-result-label">{t("specificity")}</div><div class="cal-result-value">{res["specificity"]}</div></div>', unsafe_allow_html=True)
                        st.markdown("---")
                        st.markdown(f"#### {t('comparison_default')}")
                        cmp_df = pd.DataFrame({
                            "Metric":[t("threshold"),"Youden J",t("sensitivity"),t("specificity")],
                            "Default (140)":[res["default_threshold"],res["default_J"],res["default_sensitivity"],res["default_specificity"]],
                            "Optimal":[res["optimal_threshold"],res["J_max"],res["sensitivity"],res["specificity"]]})
                        st.dataframe(cmp_df, width="stretch", hide_index=True)
                        imp = res["J_max"] - res["default_J"]
                        if imp > 0.2: st.success(f"{t('excellent_improvement')}: +{imp:.3f}")
                        elif imp > 0.05: st.info(f"{t('good_improvement')}: +{imp:.3f}")
                        elif imp > 0: st.warning(f"{t('minor_improvement')}: +{imp:.3f}")
                        else: st.error(f"{t('default_better')}: {abs(imp):.3f}")
                        st.markdown("---")
                        st.markdown(f"#### {t('roc_curve')}")
                        try:
                            import plotly.graph_objects as go
                            roc = res["roc_data"]
                            fprs = [p["fpr"] for p in roc]; tprs = [p["tpr"] for p in roc]
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=[0,1], y=[0,1], mode='lines', line=dict(color='gray', dash='dash'), name=t("random")))
                            fig.add_trace(go.Scatter(x=fprs, y=tprs, mode='lines+markers', line=dict(color='#5c2c16', width=2), marker=dict(size=4), name='DRASTIC-Tox'))
                            fig.add_trace(go.Scatter(x=[1-res["specificity"]], y=[res["sensitivity"]], mode='markers', marker=dict(size=18, color='red', symbol='star'), name=f"{t('threshold_label')} ({res['optimal_threshold']})"))
                            fig.update_layout(xaxis_title="FPR", yaxis_title="TPR", height=500)
                            st.plotly_chart(fig, use_container_width=True, key="roc_chart_v588")
                        except Exception as e: st.warning(str(e))
                        st.markdown("---")
                        st.warning(f"n = {res['n_sites']} | {t('threshold_label')}: {res['optimal_threshold']}")
                        if st.button("✅ " + t("apply_threshold"), type="primary", key="apply_opt_threshold_btn"):
                            st.session_state["custom_threshold"] = res["optimal_threshold"]
                            st.success(f"{t('applied_threshold')}: {res['optimal_threshold']}")

    with tabs[15]:
        st.markdown('<div class="section-header"><h3>⚙️ Weight Profiles Manager</h3></div>', unsafe_allow_html=True)
        if not WM_OK:
            st.error("weight_manager.py not installed")
        else:
            st.info("Select weight profile. Changes are saved permanently.")
            mining_filter = st.radio("Mining Type:",
                ["traditional", "industrial", "mixed"],
                format_func=lambda x: {"traditional":"⛏️ Traditional","industrial":"🏭 Industrial","mixed":"🔀 Mixed"}[x],
                key="profile_filter", horizontal=True)
            profiles = get_all_profiles()
            active = get_active_profile(mining_filter)
            filtered = {k:v for k,v in profiles.items() if v.get("mining_type") == mining_filter}
            st.markdown("---")
            st.markdown(f"#### Available Profiles: {len(filtered)}")
            for key, prof in filtered.items():
                is_active = (active and prof["alpha"] == active.get("alpha")
                              and prof["beta"] == active.get("beta")
                              and prof["SF"] == active.get("SF"))
                col1, col2 = st.columns([3, 1])
                with col1:
                    border_color = "#4caf50" if is_active else "#e0d4b8"
                    bg_color = "#f1f8e9" if is_active else "#faf8f3"
                    src_badge = "Literature" if prof.get("source_type") == "literature" else "Calibrated"
                    warning_html = f'<div style="background:#fff3e0;border-left:3px solid #ff9800;padding:6px 10px;margin-top:8px;font-size:0.8em;color:#e65100;">{prof.get("warning_ar","")}</div>' if prof.get('warning_ar') else ""
                    active_html = '<div style="background:#e8f5e9;padding:4px 8px;border-radius:4px;display:inline-block;margin-top:6px;font-size:0.8em;color:#2e7d32;font-weight:bold;">ACTIVE</div>' if is_active else ""
                    kappa_html = f'<p style="font-size:0.85em;color:#e65100;margin:6px 0;"><b>Kappa:</b> {prof["kappa"]} | <b>n:</b> {prof["n_sites"]}</p>' if prof.get('kappa') else ""
                    st.markdown(f"""
                    <div style="background:{bg_color};border:2px solid {border_color};border-radius:10px;padding:16px;margin:8px 0;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <h4 style="color:#5c2c16;margin:0;">{prof.get('name_ar', key)}</h4>
                            <span style="font-size:0.75em;background:#e8eaf6;color:#3f51b5;padding:2px 8px;border-radius:4px;">{src_badge}</span>
                        </div>
                        <p style="font-size:0.85em;color:#666;margin:6px 0;"><b>Source:</b> {prof.get('source','N/A')}</p>
                        <div style="display:flex;gap:20px;margin-top:8px;font-size:1.05em;">
                            <span><b>alpha</b> = <b>{prof['alpha']}</b></span>
                            <span><b>beta</b> = <b>{prof['beta']}</b></span>
                            <span><b>SF</b> = <b>{prof['SF']}</b></span>
                        </div>
                        <p style="font-size:0.8em;color:#666;margin:6px 0;">{prof.get('description_ar','')}</p>
                        {kappa_html}
                        {warning_html}
                        {active_html}
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if not is_active:
                        if st.button("Activate", key=f"act_{key}", use_container_width=True):
                            set_active_profile(key)
                            st.success("Activated")
                            st.rerun()
                    else:
                        st.success("Active")
            st.markdown("---")
            st.markdown("#### Active Profile (JSON)")
            if active: st.json(active)

    with tabs[16]:
        st.markdown(f'<div class="section-header"><h3>🔬 External Validation</h3></div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="research-note">
        <b>Purpose:</b> Proper external validation using train/test split + K-Fold CV.<br>
        <b>References:</b> Efron (1979) · Kohavi (1995) · Landis &amp; Koch (1977)
        </div>""", unsafe_allow_html=True)

        if not EXT_VAL_OK:
            st.error("external_validation.py not installed")
            st.info("Create a file named `external_validation.py` in the same folder as `app.py`")
        elif not SKLEARN_OK:
            st.error("scikit-learn required")
        else:
            df_ext = get_loaded_df("df_validation", "df_combined", "df_bulk")
            if df_ext is None:
                st.warning("Upload validation file first (Tab 11 → Load Data)")
            else:
                req_cols = ["depth_m","recharge_mm","slope_pct","conductivity",
                            "aquifer","soil","vadose","cn_water_mg_l","hg_water_mg_l",
                            "actual_contaminated"]
                miss = [c for c in req_cols if c not in df_ext.columns]
                if miss:
                    st.error(f"Missing columns: {miss}")
                else:
                    st.success(f"Data loaded: {len(df_ext)} sites")
                    st.markdown("---")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        mt_ext = st.selectbox("Mining Type",
                            ["traditional","industrial","mixed"], key="ext_mining_type")
                    with c2:
                        test_pct = st.slider("Test Size (%)", 20, 50, 30, 5, key="ext_test_size")
                    with c3:
                        n_folds = st.slider("K-Folds", 3, 10, 5, 1, key="ext_k_folds")

                    c1, c2 = st.columns(2)
                    with c1:
                        th_d_ext = st.number_input("DRASTIC threshold", 50, 200, 100, 5, key="ext_th_d")
                    with c2:
                        th_dt_ext = st.number_input("DRASTIC-Tox threshold", 50, 280,
                            int(get_optimal_threshold(mt_ext)), 5, key="ext_th_dt")

                    if st.button("🚀 Run External Validation", type="primary", key="run_ext_val_btn"):
                        with st.spinner("Running train/test split + K-Fold CV..."):
                            cal_w = CALIBRATED_WEIGHTS if (CALIBRATED_WEIGHTS and
                                CALIBRATED_WEIGHTS.get("mining_type") == mt_ext) else None
                            st.session_state["ext_val_result"] = _ext_val_fn(
                                df_ext, mining_type=mt_ext,
                                threshold_d=th_d_ext, threshold_dt=th_dt_ext,
                                test_size=test_pct/100.0, n_folds=n_folds,
                                calc_index_fn=calc_index,
                                calc_drastic_t_fn=calc_drastic_t,
                                get_d_rating_fn=get_d_rating, get_r_rating_fn=get_r_rating,
                                get_a_rating_fn=get_a_rating, get_s_rating_fn=get_s_rating,
                                get_t_rating_fn=get_t_rating, get_i_rating_fn=get_i_rating,
                                get_c_rating_fn=get_c_rating,
                                calibrated_weights=cal_w,
                                sklearn_ok=SKLEARN_OK)

                    if "ext_val_result" in st.session_state:
                        r = st.session_state["ext_val_result"]
                        if "error" in r:
                            st.error(r["error"])
                        else:
                            st.markdown("---")
                            st.markdown("#### Dataset Summary")
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Total Sites", r["n_total"])
                            c2.metric("Contaminated", r["n_contaminated"])
                            c3.metric("Clean", r["n_clean"])

                            if "n_train" in r:
                                st.markdown("---")
                                st.markdown(f"#### Train/Test Split ({100-r['test_size_pct']}/{r['test_size_pct']})")
                                c1, c2 = st.columns(2)
                                c1.metric("Training Set", r["n_train"])
                                c2.metric("Test Set", r["n_test"])
                                st.markdown("##### Held-out Test Set Performance")
                                c1, c2 = st.columns(2)
                                with c1:
                                    st.markdown("**DRASTIC**")
                                    st.metric("Kappa", r.get("test_kappa_drastic", "N/A"))
                                    st.metric("ROC-AUC", r.get("test_auc_drastic", "N/A"))
                                with c2:
                                    st.markdown("**DRASTIC-Tox**")
                                    kd = None
                                    if r.get("test_kappa_drastic") is not None and r.get("test_kappa_drastic_tox") is not None:
                                        kd = r["test_kappa_drastic_tox"] - r["test_kappa_drastic"]
                                    st.metric("Kappa", r.get("test_kappa_drastic_tox", "N/A"),
                                              delta=f"{kd:+.3f}" if kd is not None else None)
                                    st.metric("ROC-AUC", r.get("test_auc_drastic_tox", "N/A"))

                            if "cv_n_folds" in r and r["cv_n_folds"] > 0:
                                st.markdown("---")
                                st.markdown(f"#### Stratified {r['cv_n_folds']}-Fold Cross-Validation")
                                c1, c2 = st.columns(2)
                                with c1:
                                    st.markdown("**DRASTIC**")
                                    st.metric("Kappa (mean ± std)",
                                              f"{r['cv_kappa_drastic_mean']} ± {r['cv_kappa_drastic_std']}")
                                    st.metric("ROC-AUC (mean)", r['cv_auc_drastic_mean'])
                                with c2:
                                    st.markdown("**DRASTIC-Tox**")
                                    st.metric("Kappa (mean ± std)",
                                              f"{r['cv_kappa_drastic_tox_mean']} ± {r['cv_kappa_drastic_tox_std']}")
                                    st.metric("ROC-AUC (mean)", r['cv_auc_drastic_tox_mean'])
                                with st.expander("📊 Fold-by-fold Kappa"):
                                    fold_df = pd.DataFrame({
                                        "Fold": list(range(1, len(r["fold_kappas_drastic"]) + 1)),
                                        "DRASTIC Kappa": r["fold_kappas_drastic"],
                                        "DRASTIC-Tox Kappa": r["fold_kappas_drastic_tox"],
                                    })
                                    st.dataframe(fold_df, width="stretch", hide_index=True)

                            if "baseline_logreg_kappa" in r:
                                st.markdown("---")
                                st.markdown("#### Baseline ML Models")
                                st.caption("Trained on DRASTIC-Tox as sole feature (fair comparison)")
                                baseline_df = pd.DataFrame({
                                    "Model": ["DRASTIC-Tox (fixed threshold)",
                                              "Logistic Regression", "Random Forest"],
                                    "Kappa": [r.get("test_kappa_drastic_tox", "N/A"),
                                              r["baseline_logreg_kappa"],
                                              r["baseline_rf_kappa"]],
                                    "ROC-AUC": [r.get("test_auc_drastic_tox", "N/A"),
                                                r["baseline_logreg_auc"],
                                                r["baseline_rf_auc"]],
                                })
                                st.dataframe(baseline_df, width="stretch", hide_index=True)

                            if "pr_auc_drastic" in r:
                                st.markdown("---")
                                st.markdown("#### Enhanced Metrics (Test Set)")
                                enhanced_df = pd.DataFrame({
                                    "Metric": ["PR-AUC", "Brier Score"],
                                    "DRASTIC": [r["pr_auc_drastic"], r["brier_drastic"]],
                                    "DRASTIC-Tox": [r["pr_auc_drastic_tox"], r["brier_drastic_tox"]],
                                })
                                st.dataframe(enhanced_df, width="stretch", hide_index=True)
                                st.caption("PR-AUC: higher is better · Brier: lower is better")

                            st.markdown("---")
                            export_df = pd.DataFrame([r])
                            st.download_button("📥 Download Results (CSV)",
                                data=export_df.to_csv(index=False).encode("utf-8-sig"),
                                file_name="external_validation.csv",
                                mime="text/csv", key="download_ext_val_btn")

                            st.warning("⚠️ With n=11 sites, test set is small (3-4 sites). "
                                       "Interpret with caution and report CI.")

    with tabs[17]:
        st.markdown(f'<div class="section-header"><h3>🗺️ GIS Raster Interpolation</h3></div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="research-note">
        <b>Purpose:</b> Convert point risk data into continuous raster surfaces.<br>
        <b>Methods:</b> IDW (always available) · Kriging (requires pykrige) · GeoTIFF (requires rasterio)
        </div>""", unsafe_allow_html=True)

        if not RASTER_OK:
            st.error("gis_raster.py not installed")
            st.info("Create a file named `gis_raster.py` in the same folder as `app.py`")
        else:
            df_raster = get_loaded_df("df_combined", "df_validation", "df_bulk")

            if df_raster is None or ("coords" not in df_raster.columns and "lat" not in df_raster.columns):
                if DS_OK:
                    try:
                        rows = []
                        for _st_name, _st_data in STATES_DATABASE.items():
                            for _sk, _sd in _st_data.get("sites", {}).items():
                                _c = _sd.get("coords")
                                if not _c or len(_c) < 2:
                                    continue
                                rows.append({
                                    "site_name": _sd.get("name_ar", _sk),
                                    "site_key": _sk,
                                    "state": _st_name,
                                    "lat": float(_c[0]),
                                    "lon": float(_c[1]),
                                    "depth_m": _sd.get("depth_m"),
                                    "recharge_mm": _sd.get("recharge_mm"),
                                    "slope_pct": _sd.get("slope_pct"),
                                    "conductivity": _sd.get("conductivity"),
                                    "aquifer": _sd.get("aquifer"),
                                    "soil": _sd.get("soil"),
                                    "vadose": _sd.get("vadose"),
                                    "cn_water_mg_l": _sd.get("cn_water_mg_l"),
                                    "hg_water_mg_l": _sd.get("hg_water_mg_l"),
                                    "actual_contaminated": _sd.get("actual_contaminated"),
                                    "mining_type": _sd.get("mining_type", "traditional"),
                                    "verified": _sd.get("verified", False),
                                })
                        df_raster = pd.DataFrame(rows) if rows else None
                    except Exception as _e:
                        st.error(f"Failed to load built-in sites: {_e}")
                        df_raster = None

            if df_raster is not None and not df_raster.empty:
                if "coords" in df_raster.columns and ("lat" not in df_raster.columns or "lon" not in df_raster.columns):
                    df_raster = df_raster.copy()
                    def _extract_coord(c, idx):
                        if isinstance(c, (tuple, list)) and len(c) >= 2:
                            return c[idx]
                        if isinstance(c, str):
                            try:
                                import ast
                                parsed = ast.literal_eval(c)
                                if isinstance(parsed, (tuple, list)) and len(parsed) >= 2:
                                    return parsed[idx]
                            except Exception:
                                pass
                        return None
                    df_raster["lat"] = df_raster["coords"].apply(lambda c: _extract_coord(c, 0))
                    df_raster["lon"] = df_raster["coords"].apply(lambda c: _extract_coord(c, 1))

            if df_raster is None or df_raster.empty:
                st.warning("No data available. Upload a file or load verified sites.")
            else:
                if "lat" not in df_raster.columns or "lon" not in df_raster.columns:
                    st.error("Coordinates (lat/lon) not found in data")
                elif df_raster["lat"].isna().all() or df_raster["lon"].isna().all():
                    st.error("Coordinates are all empty/null")
                else:
                    st.success(f"Data loaded: {len(df_raster)} sites")

                    st.markdown("---")
                    c1, c2, c3 = st.columns(3)

                    with c1:
                        param_choices = {
                            "DRASTIC-Tox": "DRASTIC_Tox",
                            "DRASTIC": "DRASTIC",
                            "CN (mg/L)": "cn_water_mg_l",
                            "Hg (mg/L)": "hg_water_mg_l",
                            "Depth (m)": "depth_m",
                            "Recharge (mm/yr)": "recharge_mm",
                            "Conductivity (m/day)": "conductivity",
                        }
                        param_label = st.selectbox("Parameter", list(param_choices.keys()),
                            key="raster_param_select")
                        param_col = param_choices[param_label]

                    with c2:
                        method = st.selectbox("Interpolation Method",
                            ["IDW", "Kriging"], key="raster_method_select")

                    with c3:
                        resolution = st.slider("Grid Resolution", 30, 200, 80, 10,
                            key="raster_resolution_slider")

                    if method == "IDW":
                        c1, c2 = st.columns(2)
                        with c1:
                            power = st.slider("IDW Power", 1.0, 5.0, 2.0, 0.5,
                                key="raster_idw_power_slider")
                        with c2:
                            st.caption("Higher power → more localized influence")
                        variogram = "linear"
                    else:
                        power = 2.0
                        c1, c2 = st.columns(2)
                        with c1:
                            variogram = st.selectbox("Variogram Model",
                                ["linear", "power", "gaussian", "spherical", "exponential"],
                                key="raster_variogram_select")
                        with c2:
                            st.caption("Requires pykrige")

                    points = []
                    for _, row in df_raster.iterrows():
                        try:
                            lat = float(row["lat"])
                            lon = float(row["lon"])

                            if param_col == "DRASTIC_Tox":
                                if "DRASTIC_Tox" not in df_raster.columns:
                                    ix = calc_index(
                                        get_d_rating(float(row["depth_m"])),
                                        get_r_rating(float(row["recharge_mm"])),
                                        get_a_rating(str(row["aquifer"])),
                                        get_s_rating(str(row["soil"])),
                                        get_t_rating(float(row["slope_pct"])),
                                        get_i_rating(str(row["vadose"])),
                                        get_c_rating(float(row["conductivity"])))
                                    val = calc_drastic_t(
                                        ix,
                                        float(row.get("cn_water_mg_l", 0.0)),
                                        float(row.get("hg_water_mg_l", 0.0)),
                                        mining_type=st.session_state.get("mining_type", "traditional"))["drastic_t"]
                                else:
                                    val = float(row["DRASTIC_Tox"])
                            elif param_col == "DRASTIC":
                                if "DRASTIC" not in df_raster.columns:
                                    val = calc_index(
                                        get_d_rating(float(row["depth_m"])),
                                        get_r_rating(float(row["recharge_mm"])),
                                        get_a_rating(str(row["aquifer"])),
                                        get_s_rating(str(row["soil"])),
                                        get_t_rating(float(row["slope_pct"])),
                                        get_i_rating(str(row["vadose"])),
                                        get_c_rating(float(row["conductivity"])))
                                else:
                                    val = float(row["DRASTIC"])
                            else:
                                val = float(row[param_col])

                            points.append((lat, lon, val))
                        except Exception:
                            continue

                    if len(points) < 3:
                        st.warning(f"Need at least 3 valid points, got {len(points)}")
                    else:
                        st.caption(f"Valid points: {len(points)}")

                        if st.button("🎨 Generate Raster", type="primary", key="gen_raster_btn"):
                            with st.spinner(f"Interpolating via {method}..."):
                                if method == "Kriging":
                                    result = kriging_interpolation(points, resolution=resolution,
                                        variogram_model=variogram)
                                    if "error" in result:
                                        st.warning(f"Kriging failed, using IDW instead: {result['error']}")
                                        result = idw_interpolation(points, resolution=resolution, power=power)
                                else:
                                    result = idw_interpolation(points, resolution=resolution, power=power)
                                st.session_state["raster_result"] = result

                        if "raster_result" in st.session_state:
                            result = st.session_state["raster_result"]
                            if "error" in result:
                                st.error(result["error"])
                            else:
                                st.markdown("---")
                                st.markdown(f"#### {param_label} — {result['method']} Raster")

                                stats = compute_raster_statistics(result)
                                c1, c2, c3, c4 = st.columns(4)
                                c1.metric("Min", round(stats["min"], 1))
                                c2.metric("Mean", round(stats["mean"], 1))
                                c3.metric("Max", round(stats["max"], 1))
                                c4.metric("Std Dev", round(stats["std"], 2))

                                c1, c2, c3, c4 = st.columns(4)
                                c1.metric("Median", round(stats["median"], 1))
                                c2.metric("P25", round(stats["p25"], 1))
                                c3.metric("P75", round(stats["p75"], 1))
                                c4.metric("Coverage (km²)", stats["coverage_km2"])

                                st.markdown("---")
                                st.markdown("#### Risk Classification")
                                classes = classify_raster(result,
                                    thresholds=[100, 140, 180] if "DRASTIC" in param_col else None)
                                c1, c2, c3, c4 = st.columns(4)
                                c1.metric("🟢 Low", f"{classes['low']['percent']}%",
                                    help=f"{classes['low']['count']} cells")
                                c2.metric("🟡 Medium", f"{classes['medium']['percent']}%",
                                    help=f"{classes['medium']['count']} cells")
                                c3.metric("🟠 High", f"{classes['high']['percent']}%",
                                    help=f"{classes['high']['count']} cells")
                                c4.metric("🔴 Very High", f"{classes['very_high']['percent']}%",
                                    help=f"{classes['very_high']['count']} cells")

                                st.markdown("---")
                                st.markdown("#### Interactive Raster Map")
                                colorscale = "RdYlGn_r" if "DRASTIC" in param_col else "Viridis"
                                fig = create_raster_plotly(result,
                                    title=f"{param_label} — {result['method']}",
                                    colorscale=colorscale)
                                if fig:
                                    st.plotly_chart(fig, use_container_width=True,
                                        key="raster_plotly_chart")
                                else:
                                    st.warning("Plotly not available")

                                st.markdown("---")
                                c1, c2 = st.columns(2)

                                with c1:
                                    try:
                                        geotiff_bytes = None
                                        import tempfile
                                        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
                                            tmp_path = tmp.name

                                        gt_result = export_geotiff(result, tmp_path)
                                        if gt_result["success"]:
                                            with open(tmp_path, "rb") as f:
                                                geotiff_bytes = f.read()
                                            try:
                                                os.unlink(tmp_path)
                                            except Exception:
                                                pass

                                            st.download_button(
                                                "🗺️ تحميل GeoTIFF",
                                                data=geotiff_bytes,
                                                file_name=f"raster_{param_col}.tif",
                                                mime="image/tiff",
                                                key="download_geotiff_btn")
                                        else:
                                            st.info(f"GeoTIFF: {gt_result['message']}")
                                    except Exception as e:
                                        st.info(f"GeoTIFF: {str(e)[:80]}")

                                with c2:
                                    if fig:
                                        html = fig.to_html(include_plotlyjs='cdn')
                                        st.download_button(
                                            "📥 تحميل HTML",
                                            data=html.encode("utf-8"),
                                            file_name=f"raster_{param_col}.html",
                                            mime="text/html",
                                            key="download_raster_html_btn")

    with tabs[18]:
        st.markdown(f'<div class="section-header"><h3>🌐 Live API Data</h3></div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="research-note">
        <b>Purpose:</b> Fetch real-time and historical environmental data from public APIs.<br>
        <b>Sources:</b> NASA POWER · Open-Meteo · Open-Elevation · ISRIC SoilGrids<br>
        <b>All APIs are free and require NO keys.</b>
        </div>""", unsafe_allow_html=True)

        if not LIVE_API_OK:
            st.error("live_apis.py not installed")
            st.info("Create a file named `live_apis.py` in the same folder as `app.py`")
        else:
            c1, c2 = st.columns(2)
            with c1:
                use_current = st.checkbox("Use current site coordinates",
                    value=True, key="live_use_current_chk")
            with c2:
                st.caption("Or enter coordinates manually below")

            if use_current and "current_site_data" in st.session_state:
                _sd = st.session_state["current_site_data"]
                _coords = _sd.get("coords", (15.5, 32.5))
                live_lat = float(_coords[0])
                live_lon = float(_coords[1])
                st.success(f"Using: **{_sd.get('name_ar', 'Current Site')}** ({live_lat:.4f}, {live_lon:.4f})")
            else:
                c1, c2 = st.columns(2)
                with c1:
                    live_lat = st.number_input("Latitude", -90.0, 90.0, 15.6, 0.01,
                        format="%.4f", key="live_lat_input")
                with c2:
                    live_lon = st.number_input("Longitude", -180.0, 180.0, 32.5, 0.01,
                        format="%.4f", key="live_lon_input")

            st.markdown("---")

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button("☁️ NASA POWER", type="primary", key="fetch_nasa_btn"):
                    with st.spinner("Fetching climate data..."):
                        st.session_state["live_nasa"] = fetch_nasa_power(live_lat, live_lon, years=3)
            with c2:
                if st.button("🌧️ Open-Meteo", type="primary", key="fetch_meteo_btn"):
                    with st.spinner("Fetching precipitation..."):
                        st.session_state["live_meteo"] = fetch_open_meteo_precipitation(live_lat, live_lon, years=5)
            with c3:
                if st.button("⛰️ Elevation", type="primary", key="fetch_elev_btn"):
                    with st.spinner("Fetching elevation grid..."):
                        st.session_state["live_elev"] = fetch_elevation_grid(live_lat, live_lon, radius_km=5)
            with c4:
                if st.button("🪨 Soil", type="primary", key="fetch_soil_btn"):
                    with st.spinner("Fetching soil properties..."):
                        st.session_state["live_soil"] = fetch_soilgrids(live_lat, live_lon)

            st.markdown("---")

            if "live_nasa" in st.session_state:
                r = st.session_state["live_nasa"]
                if "error" in r:
                    st.error(f"NASA POWER: {r['error']}")
                else:
                    st.markdown("#### ☁️ NASA POWER — Climate Data")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Annual Rainfall", f"{r.get('rainfall_mm_annual', 'N/A')} mm")
                    c2.metric("Temperature", f"{r.get('temperature_c', 'N/A')} °C")
                    c3.metric("Humidity", f"{r.get('humidity_pct', 'N/A')} %")
                    c4.metric("Wind Speed", f"{r.get('wind_speed_ms', 'N/A')} m/s")
                    c1, c2 = st.columns(2)
                    c1.metric("Temp Max", f"{r.get('temperature_max_c', 'N/A')} °C")
                    c2.metric("Temp Min", f"{r.get('temperature_min_c', 'N/A')} °C")
                    st.caption(f"Source: {r.get('source')} | Averaged over {r.get('n_years')} years")

            if "live_meteo" in st.session_state:
                r = st.session_state["live_meteo"]
                if "error" in r:
                    st.error(f"Open-Meteo: {r['error']}")
                else:
                    st.markdown("#### 🌧️ Open-Meteo — Historical Precipitation")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Annual Rainfall", f"{r.get('annual_rainfall_mm', 'N/A')} mm")
                    c2.metric("Dry Months", f"{r.get('n_dry_months', 'N/A')} / 12")
                    c3.metric("Mean Temp", f"{r.get('temperature_mean_c', 'N/A')} °C")
                    if "monthly_avg_mm" in r:
                        with st.expander("📊 Monthly Breakdown"):
                            month_names = ["Jan","Feb","Mar","Apr","May","Jun",
                                           "Jul","Aug","Sep","Oct","Nov","Dec"]
                            monthly_df = pd.DataFrame({
                                "Month": month_names,
                                "Avg (mm)": [r["monthly_avg_mm"].get(str(i), 0) for i in range(1, 13)]
                            })
                            st.dataframe(monthly_df, width="stretch", hide_index=True)
                    st.caption(f"Source: {r.get('source')} | Averaged over {r.get('n_years')} years")

            if "live_elev" in st.session_state:
                r = st.session_state["live_elev"]
                if "error" in r:
                    st.error(f"Elevation: {r['error']}")
                else:
                    st.markdown("#### ⛰️ Open-Elevation — Terrain")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Elevation", f"{r.get('elevation_m', 'N/A')} m")
                    c2.metric("Estimated Slope", f"{r.get('slope_pct', 'N/A')} %")
                    c3.metric("Relief (5km radius)", f"{r.get('elevation_range_m', 'N/A')} m")
                    st.caption(f"Source: {r.get('source')}")

            if "live_soil" in st.session_state:
                r = st.session_state["live_soil"]
                if "error" in r:
                    st.error(f"SoilGrids: {r['error']}")
                else:
                    st.markdown("#### 🪨 ISRIC SoilGrids — Soil Properties")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Sand", f"{r.get('sand_pct', 'N/A')} %")
                    c2.metric("Clay", f"{r.get('clay_pct', 'N/A')} %")
                    c3.metric("Silt", f"{r.get('silt_pct', 'N/A')} %")
                    c1, c2 = st.columns(2)
                    c1.metric("Organic Carbon", f"{r.get('soc_g_kg', 'N/A')} g/kg")
                    c2.metric("Bulk Density", f"{r.get('bulk_density_kg_m3', 'N/A')} kg/m³")
                    st.caption(f"Source: {r.get('source')}")

            has_data = ("live_nasa" in st.session_state and "error" not in st.session_state.get("live_nasa", {})) or \
                       ("live_meteo" in st.session_state and "error" not in st.session_state.get("live_meteo", {}))

            if has_data:
                st.markdown("---")
                st.markdown("#### 🔄 Auto-fill DRASTIC Parameters")
                st.caption("Uses fetched data to suggest recharge, slope, aquifer, and soil values.")

                if st.button("🎯 Generate Suggested Values", type="primary", key="autofill_btn"):
                    suggestions = {}

                    rain = None
                    if "live_meteo" in st.session_state and "annual_rainfall_mm" in st.session_state["live_meteo"]:
                        rain = st.session_state["live_meteo"]["annual_rainfall_mm"]
                    elif "live_nasa" in st.session_state and "rainfall_mm_annual" in st.session_state["live_nasa"]:
                        rain = st.session_state["live_nasa"]["rainfall_mm_annual"]

                    slope = None
                    if "live_elev" in st.session_state and "slope_pct" in st.session_state["live_elev"]:
                        slope = st.session_state["live_elev"]["slope_pct"]

                    soil_type = "sandy_loam"
                    if "live_soil" in st.session_state:
                        soil_r = st.session_state["live_soil"]
                        soil_type = classify_soil_from_texture(
                            soil_r.get("sand_pct"),
                            soil_r.get("clay_pct"),
                            soil_r.get("silt_pct"))
                        suggestions["aquifer"] = classify_aquifer_from_soil(
                            soil_r.get("sand_pct"),
                            soil_r.get("clay_pct"))

                    suggestions["soil"] = soil_type

                    if rain and slope is not None:
                        suggestions["recharge_mm"] = estimate_recharge_from_rainfall(rain, soil_type, slope)
                    elif rain:
                        suggestions["recharge_mm"] = estimate_recharge_from_rainfall(rain, soil_type, 5.0)

                    if slope is not None:
                        suggestions["slope_pct"] = slope

                    st.session_state["live_suggestions"] = suggestions

                if "live_suggestions" in st.session_state:
                    s = st.session_state["live_suggestions"]
                    st.markdown("##### Suggested DRASTIC Parameters")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("R — Recharge", f"{s.get('recharge_mm', '—')} mm/yr")
                    c2.metric("T — Slope", f"{s.get('slope_pct', '—')} %")
                    c3.metric("A — Aquifer", str(s.get("aquifer", "—"))[:20])
                    c4.metric("S — Soil", str(s.get("soil", "—"))[:20])

                    st.info("💡 Copy these values to the **Manual Entry** tab to create a new site with real data.")

elif MODE_KEY == "agricultural" and ADV_OK:
    st.markdown(f"""<div class="header-container header-agri"><div class="header-title">{t("agricultural_title")}</div><div class="header-subtitle">DRASTIC-Agri + SAR + Na% + EC</div></div>""", unsafe_allow_html=True)
    if DS_OK:
        try:
            ag_s = get_agricultural_data_summary()
            st.info(f"{ag_s['total_states']} / {ag_s['total_sites']}")
            c1, c2 = st.columns([1, 2])
            with c1: ags = st.selectbox(t("state"), get_agri_states_list(), key="agri_state_select")
            with c2: st.markdown(f'<div class="info-card" style="margin-top:28px;">{AGRICULTURAL_DATA[ags]["description"]}</div>', unsafe_allow_html=True)
            agk = st.selectbox(t("site"), get_agri_sites_list(ags), key="agri_site_select")
            agd = get_agri_site_data(ags, agk)
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Crop", agd.get("crop_type","N/A"))
            c2.metric("Irrigation", agd.get("irrigation_method","N/A"))
            c3.metric("EC", f"{agd['ec_ds_m']} dS/m")
            sar = calculate_sar(agd['na_meq_l'], agd['ca_meq_l'], agd['mg_meq_l'])
            nap = calculate_na_percent(agd['na_meq_l'], agd['ca_meq_l'], agd['mg_meq_l'], agd['k_meq_l'])
            ecr = calculate_ec_quality(agd['ec_ds_m'])
            ov = classify_irrigation_water(sar, nap, ecr)
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("SAR", sar.get("sar","N/A"))
            c2.metric("Na%", f"{nap.get('na_percent','N/A')}%")
            c3.metric("EC", ecr.get("ec","N/A"))
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Class", ov.get("class","N/A"))
            c2.metric(t("level"), ov.get("level","N/A"))
            c3.metric(t("action"), ov.get("action","N/A"))
        except Exception as e: st.error(str(e))

elif MODE_KEY == "verification" and ADV_OK:
    st.markdown(f'<div class="section-header"><h3>{t("verification_title")}</h3></div>', unsafe_allow_html=True)
    if DS_OK:
        c1, c2 = st.columns([3, 1])
        with c2:
            if st.button("📥 " + t("load_data"), type="primary", key="load_verified_sites_btn"):
                try:
                    df_v = get_verified_sites_as_dataframe()
                    st.session_state["df_validation"] = df_v
                    st.success(f"{len(df_v)} {t('sites')}"); st.rerun()
                except Exception as e: st.error(str(e))
        with c1: st.info(f"{n_sites_verified} {t('verified_sites')}")
    df_val = st.session_state.get("df_validation")
    if df_val is None: st.warning(t("no_file"))
    else:
        try:
            st.dataframe(df_val.head(10), width="stretch")
            has_tox = "cn_water_mg_l" in df_val.columns and "hg_water_mg_l" in df_val.columns
            if not has_tox: st.error(t("file_missing_tox"))
            else:
                c1, c2 = st.columns(2)
                with c1: th_d = st.number_input("DRASTIC:", 50, 200, 100, 10, key="verify_th_d_input")
                with c2: th_dt = st.number_input("DRASTIC-Tox:", 50, 280, 140, 10, key="verify_th_dt_input")
                mt = st.session_state.get("mining_type", "traditional")
                d_l, dp_l, act_l = [], [], []
                for i, row in df_val.iterrows():
                    try:
                        ix = calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])),
                            get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])),
                            get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])),
                            get_c_rating(float(row["conductivity"])))
                        d_l.append(ix)
                        cw = float(row.get("cn_water_mg_l",0.0)); hw = float(row.get("hg_water_mg_l",0.0))
                        if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mt:
                            dp_l.append(calc_drastic_t(ix, cw, hw, mining_type=mt,
                                alpha_override=CALIBRATED_WEIGHTS["alpha"],
                                beta_override=CALIBRATED_WEIGHTS["beta"],
                                SF_override=CALIBRATED_WEIGHTS["SF"])["drastic_t"])
                        else: dp_l.append(calc_drastic_t(ix, cw, hw, mining_type=mt)["drastic_t"])
                        act_l.append(int(row["actual_contaminated"]))
                    except Exception: pass
                st.markdown("---")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("#### DRASTIC")
                    md = calculate_confusion_matrix(d_l, act_l, th_d)
                    st.metric(t("kappa"), md["kappa"])
                    st.metric(t("recall"), f"{md['recall']}%")
                    st.metric(t("accuracy"), f"{md.get('accuracy','N/A')}%")
                with c2:
                    st.markdown("#### DRASTIC-Tox")
                    mp = calculate_confusion_matrix(dp_l, act_l, th_dt)
                    st.metric(t("kappa"), mp["kappa"])
                    st.metric(t("recall"), f"{mp['recall']}%")
                    st.metric(t("accuracy"), f"{mp.get('accuracy','N/A')}%")
        except Exception as e: st.error(str(e))

elif MODE_KEY == "transport" and ADV_OK:
    st.markdown(f'<div class="section-header"><h3>{t("transport_title")}</h3></div>', unsafe_allow_html=True)
    if "cv" not in st.session_state: st.warning(t("mode_system"))
    else:
        cv = st.session_state["cv"]
        c1, c2 = st.columns(2)
        with c1:
            ic = st.number_input("C0:", 0.001, 10.0, 0.10, 0.001, format="%.4f", key="trans_init_conc")
            ds = st.number_input("Distance (m):", 10.0, 5000.0, 500.0, 50.0, key="trans_distance")
        with c2:
            gr = st.number_input("Gradient:", 0.0001, 0.5, 0.01, 0.0001, format="%.4f", key="trans_gradient")
            yr = st.slider("Years:", 1, 30, 10, 1, key="trans_years")
        po = st.slider("Porosity:", 0.02, 0.55, 0.25, 0.01, key="trans_porosity")
        kv = st.number_input("K (m/d):", 0.01, 500.0, float(cv.get("conductivity", 3.5)), 0.1, key="trans_k_val")
        di = st.number_input("Dispersivity:", 0.1, 100.0, 10.0, 0.5, key="trans_disper")
        if st.button("🚀 " + t("run"), type="primary", key="run_transport_btn"):
            st.session_state["transport_result"] = model_contaminant_transport_fixed(ic, kv, po, gr, ds, yr, di)
        if "transport_result" in st.session_state:
            tr = st.session_state["transport_result"]
            if "error" in tr: st.error(tr["error"])
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Velocity", f"{tr['v_seepage']:.6f} m/d")
                c2.metric("Dispersion", f"{tr['D_dispersion']} m2/d")
                c3.metric("Travel Time", f"{tr['t_travel_years']} yr")
                st.dataframe(tr["results"], width="stretch")
                st.line_chart(tr["results"].set_index("Year")["Concentration"])

elif MODE_KEY == "independent" and ADV_OK:
    st.markdown(f'<div class="section-header"><h3>{t("independent_title")}</h3></div>', unsafe_allow_html=True)
    df_val = st.session_state.get("df_validation")
    if df_val is None: st.warning(t("upload_validation_first"))
    else:
        try:
            req = ["depth_m","recharge_mm","slope_pct","conductivity","aquifer","soil","vadose","actual_contaminated"]
            miss = [c for c in req if c not in df_val.columns]
            if miss: st.error(f"Missing: {miss}")
            else:
                if st.button("🚀 " + t("run"), type="primary", key="run_ind_val_btn"):
                    with st.spinner(t("calculating")):
                        try:
                            df_i = df_val.copy()
                            if "DRASTIC" not in df_i.columns:
                                dv = []
                                for _, row in df_i.iterrows():
                                    try: dv.append(calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])),
                                        get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])),
                                        get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])),
                                        get_c_rating(float(row["conductivity"]))))
                                    except Exception: dv.append(0)
                                df_i["DRASTIC"] = dv
                            if "DRASTIC_Tox" not in df_i.columns and "cn_water_mg_l" in df_i.columns and "hg_water_mg_l" in df_i.columns:
                                dtv = []; mti = st.session_state.get("mining_type", "traditional")
                                for _, row in df_i.iterrows():
                                    try:
                                        ix = calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])),
                                            get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])),
                                            get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])),
                                            get_c_rating(float(row["conductivity"])))
                                        dtv.append(calc_drastic_t(ix, float(row.get("cn_water_mg_l",0)),
                                            float(row.get("hg_water_mg_l",0)), mining_type=mti)["drastic_t"])
                                    except Exception: dtv.append(0)
                                df_i["DRASTIC_Tox"] = dtv
                            st.session_state["ind_val_result"] = independent_validation(df_i, "DRASTIC", "actual_contaminated", test_size=0.3)
                        except Exception as e: st.error(str(e))
                if "ind_val_result" in st.session_state:
                    r = st.session_state["ind_val_result"]
                    if "error" in r: st.error(r["error"])
                    else:
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("alpha", r.get("best_alpha","N/A"))
                        c2.metric("beta", r.get("best_beta","N/A"))
                        c3.metric(f"{t('kappa')} (Train)", r.get("train_kappa","N/A"))
                        c4.metric(f"{t('kappa')} (Test)", r.get("test_kappa","N/A"))
        except Exception as e: st.error(str(e))

elif MODE_KEY == "satellite" and ADV_OK:
    st.markdown(f'<div class="section-header"><h3>{t("satellite_title")}</h3></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: lt = st.number_input("Latitude:", -90.0, 90.0, 13.55, 0.01, format="%.4f", key="sat_lat_input")
    with c2: ln = st.number_input("Longitude:", -180.0, 180.0, 33.60, 0.01, format="%.4f", key="sat_lon_input")
    yr = st.slider("Years:", 1, 10, 3, 1, key="sat_years_slider")
    if st.button("🛰️ " + t("run"), type="primary", key="fetch_sat_btn"):
        with st.spinner(t("calculating")):
            try: st.session_state["sat_result"] = fetch_satellite_data(lt, ln, yr)
            except Exception as e: st.error(str(e))
    if "sat_result" in st.session_state:
        s = st.session_state["sat_result"]
        if s.get("rainfall_mm") is not None:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Rainfall", f"{s['rainfall_mm']} mm")
            c2.metric("Temp", f"{s['temperature_c']} C")
            c3.metric("Climate", s["aridity"])
            c4.metric("NDVI", s["ndvi_estimated"])
            st.caption(s['source'])
        else: st.error(s.get('source',''))

elif MODE_KEY == "dynamic" and ADV_OK:
    st.markdown(f'<div class="section-header"><h3>{t("dynamic_title")}</h3></div>', unsafe_allow_html=True)
    if "ci" not in st.session_state: st.warning(t("mode_system"))
    else:
        c1, c2 = st.columns(2)
        with c1:
            yr = st.slider("Years:", 1, 50, 10, 1, key="dyn_years_slider")
            mn = st.slider("Mining:", 0.0, 0.20, 0.05, 0.01, key="dyn_mining_slider")
        with c2:
            cl = st.slider("Climate:", -0.10, 0.05, -0.02, 0.005, key="dyn_climate_slider")
            pp = st.slider("Pop:", 0.0, 0.10, 0.03, 0.01, key="dyn_pop_slider")
        cr0 = st.slider("CRI:", 0.0, 10.0, 1.0, 0.1, key="dyn_cri_slider")
        mr0 = st.slider("MRI:", 0.0, 10.0, 0.5, 0.1, key="dyn_mri_slider")
        if st.button("⏳ " + t("run"), type="primary", key="run_dyn_btn"):
            try: st.session_state["dyn"] = calculate_dynamic_risk(st.session_state["ci"], yr, mn, cl, pp, cr0, mr0)
            except Exception as e: st.error(str(e))
        if "dyn" in st.session_state:
            res = st.session_state["dyn"]
            if isinstance(res, dict) and "combined" in res:
                st.dataframe(res["combined"], width="stretch")

elif MODE_KEY == "modflow" and MODFLOW_OK:
    st.markdown(f'<div class="section-header"><h3>{t("modflow_title")}</h3></div>', unsafe_allow_html=True)
    mok, mmsg = is_modflow_available()
    if not mok: st.error(mmsg)
    else:
        st.success(mmsg)
        c1, c2 = st.columns(2)
        with c1:
            nl = st.number_input("Layers:", 1, 5, 1, key="mf_nlay_input")
            nr = st.number_input("Rows:", 5, 50, 20, key="mf_nrow_input")
            nc = st.number_input("Cols:", 5, 50, 20, key="mf_ncol_input")
            dr = st.number_input("Delr:", 50.0, 5000.0, 500.0, 50.0, key="mf_delr_input")
        with c2:
            dc = st.number_input("Delc:", 50.0, 5000.0, 500.0, 50.0, key="mf_delc_input")
            tp = st.number_input("Top:", 100.0, 2000.0, 350.0, 10.0, key="mf_top_input")
            bt = st.number_input("Bottom:", 0.0, 1000.0, 250.0, 10.0, key="mf_botm_input")
            kv = st.number_input("K:", 0.01, 500.0, 3.5, 0.1, key="mf_k_input")
            rc = st.number_input("Recharge:", 0.0, 500.0, 15.0, 1.0, key="mf_rech_input")
        if st.button("🚀 " + t("run"), type="primary", key="run_mf_btn"):
            try:
                ws = f"/tmp/mf_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                st.session_state["mf_res"] = build_and_run_model(workspace=ws, nlay=int(nl), nrow=int(nr),
                    ncol=int(nc), delr=float(dr), delc=float(dc), top=float(tp), botm=float(bt),
                    k_value=float(kv), recharge_mm=float(rc))
            except Exception as e: st.error(str(e))
        if "mf_res" in st.session_state:
            res = st.session_state["mf_res"]
            if res.get("success"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Min", f"{res['head_min']:.2f} m")
                c2.metric("Max", f"{res['head_max']:.2f} m")
                c3.metric("Mean", f"{res['head_mean']:.2f} m")

st.markdown("---")
st.markdown(f"""<div style="text-align:center;color:#666;padding:10px;"><b>{t("app_title")} v58.8</b> - PILOT VERSION<br><span style="font-size:0.85em;">{t("screening_only")}</span></div>""", unsafe_allow_html=True)
