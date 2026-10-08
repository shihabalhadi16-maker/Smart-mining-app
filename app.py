"""
نظام التعدين السوداني v57.6
=====================================
جامعة الخرطوم - كلية الهندسة

v57.6 يضيف على v57.5:
- تبويب "📐 العتبة المثلى" (Youden's J)
- استيراد find_optimal_threshold من auto_calibration
- رسم منحنى ROC تفاعلي

المراجع: Aller 1987، Konaté 2025، Karan 2018، Landis & Koch 1977، Youden 1950
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
    from auto_calibration import (
        auto_calibrate_weights, apply_calibration, compare_with_defaults,
        interpret_kappa, find_optimal_threshold,
        DEFAULT_WEIGHTS as AUTO_CAL_DEFAULTS,
    )
    AUTOCAL_OK = True
except ImportError:
    AUTOCAL_OK = False

st.set_page_config(page_title="نظام التعدين السوداني v57.6", page_icon="⛏️",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    html, body, [class*="css"] { font-family: 'Segoe UI', 'Tahoma', 'Arial', sans-serif; font-size: 15px; }
    .stButton > button { border-radius: 8px; font-weight: 600; padding: 10px 24px; border: none; }
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, #5c2c16 0%, #c19a6b 100%); color: white; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; flex-wrap: wrap; background-color: #faf8f3; padding: 8px; border-radius: 12px; border: 1px solid #e0d4b8; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 10px 16px; font-size: 0.9em; font-weight: 600; background-color: transparent; color: #5c2c16; }
    .stTabs [aria-selected="true"] { background-color: #5c2c16 !important; color: white !important; }
    div[data-testid="stMetric"] { background: linear-gradient(135deg, #ffffff 0%, #f9f5ec 100%); border: 2px solid #d4af37; border-radius: 12px; padding: 16px 20px; box-shadow: 0 3px 10px rgba(212, 175, 55, 0.12); }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #f5eedc 0%, #faf8f3 100%); border-right: 3px solid #c19a6b; }
    .header-container { background: linear-gradient(135deg, #5c2c16 0%, #c19a6b 100%); padding: 28px 24px; border-radius: 16px; margin-bottom: 24px; color: white; text-align: center; box-shadow: 0 8px 24px rgba(92, 44, 22, 0.35); }
    .header-agri { background: linear-gradient(135deg, #2d5016 0%, #7cb342 100%) !important; }
    .header-title { font-size: 2.1em; font-weight: 700; margin: 0; }
    .header-subtitle { font-size: 1.05em; opacity: 0.95; margin: 6px 0 0 0; }
    .header-badge { display: inline-block; background: rgba(255, 255, 255, 0.2); padding: 4px 12px; border-radius: 20px; font-size: 0.85em; margin-top: 10px; }
    .section-header { display: flex; align-items: center; gap: 10px; margin: 16px 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid #f0e6d2; }
    .section-header h3 { color: #5c2c16; margin: 0; font-size: 1.25em; }
    .info-card { background: #faf8f3; border: 1px solid #e0d4b8; border-radius: 10px; padding: 16px; margin: 10px 0; }
    .upload-zone { background: linear-gradient(135deg, #fff9ec 0%, #f5e6c8 100%); border: 3px dashed #c19a6b; border-radius: 14px; padding: 22px; margin: 12px 0; text-align: center; }
    .upload-zone h4 { color: #5c2c16; margin: 0 0 6px 0; font-size: 1.1em; }
    .upload-zone p { color: #777; margin: 0; font-size: 0.85em; }
    .pilot-banner { background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%); color: white; padding: 12px 16px; border-radius: 10px; margin: 8px 0; font-weight: 600; text-align: center; }
    .quality-box-ok { background:#e8f5e9; border-left:4px solid #4caf50; padding:10px 12px; border-radius:8px; margin:5px 0; }
    .quality-box-warn { background:#fff3e0; border-left:4px solid #ff9800; padding:10px 12px; border-radius:8px; margin:5px 0; }
    .about-box { background: #faf8f3; border: 1px solid #e0d4b8; border-radius: 10px; padding: 16px; margin: 10px 0; font-size: 0.9em; }
    .about-box h4 { color: #5c2c16; margin: 8px 0 4px 0; font-size: 1em; }
    .about-box ul { margin: 4px 0; padding-right: 20px; }
    .about-box li { margin: 2px 0; }
    .mining-badge { display: inline-block; padding: 6px 14px; border-radius: 8px; font-size: 1em; font-weight: 700; margin: 8px 0; }
    .mining-industrial { background: #e3f2fd; color: #1565c0; border: 2px solid #1565c0; }
    .mining-traditional { background: #fff3e0; color: #e65100; border: 2px solid #e65100; }
    .mining-mixed { background: #f3e5f5; color: #6a1b9a; border: 2px solid #6a1b9a; }
    .research-note { background: #e8eaf6; border-left: 4px solid #3f51b5; padding: 10px 14px; border-radius: 8px; margin: 8px 0; font-size: 0.85em; color: #1a237e; }
    .kappa-box { padding: 20px; border-radius: 12px; text-align: center; margin: 12px 0; color: white; }
    .kappa-excellent { background: linear-gradient(135deg, #2e7d32 0%, #66bb6a 100%); }
    .kappa-good { background: linear-gradient(135deg, #388e3c 0%, #81c784 100%); }
    .kappa-moderate { background: linear-gradient(135deg, #f57c00 0%, #ffb74d 100%); }
    .kappa-fair { background: linear-gradient(135deg, #e64a19 0%, #ff8a65 100%); }
    .kappa-poor { background: linear-gradient(135deg, #c62828 0%, #ef5350 100%); }
    .cal-result-card { background: #f5eedc; border: 2px solid #c19a6b; border-radius: 12px; padding: 16px; margin: 8px 0; text-align: center; }
    .cal-result-value { font-size: 2em; font-weight: 700; color: #5c2c16; margin: 4px 0; }
    .cal-result-label { font-size: 0.85em; color: #777; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    @media (max-width: 768px) {
        .header-title { font-size: 1.5em !important; }
        .header-subtitle { font-size: 0.9em !important; }
        .header-container { padding: 18px 14px !important; }
        [data-testid="stHorizontalBlock"] { flex-direction: column !important; }
        [data-testid="stHorizontalBlock"] > div { width: 100% !important; margin-bottom: 8px; }
        .stTabs [data-baseweb="tab"] { padding: 8px 12px; font-size: 0.8em; }
    }
</style>
""", unsafe_allow_html=True)

# MODFLOW Setup
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
        with st.spinner("⏳ تحميل MODFLOW 6..."):
            r = requests.get(MODFLOW_URL, timeout=180, stream=True)
            if r.status_code != 200:
                return f"download_failed_{r.status_code}"
            with zipfile.ZipFile(io.BytesIO(r.content), 'r') as zf:
                mf6_file = None
                for name in zf.namelist():
                    if name.endswith("mf6") and not name.endswith("/"):
                        mf6_file = name
                        break
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

_modflow_status = setup_modflow()
if os.path.exists(MODFLOW_DIR):
    os.environ["PATH"] = MODFLOW_DIR + os.pathsep + os.environ.get("PATH", "")

try:
    from data_sources import (
        STATES_DATABASE, AGRICULTURAL_DATA,
        get_preset_locations_for_app, get_data_summary,
        get_sites_by_state, get_site_data, get_all_sites_as_dataframe,
        add_new_site, get_states_list, get_sites_list,
        get_agricultural_data_summary, get_agri_states_list,
        get_agri_sites_list, get_agri_site_data, add_new_agri_site,
        get_all_agri_sites_as_dataframe, KNOWN_MINING_SITES,
        get_verified_sites_as_dataframe, get_all_sites_as_dataframe_with_flag,
        GRAY_ZONE_SITES, get_combined_dataset)
    DS_OK = True
except ImportError:
    DS_OK = False

try:
    from modflow_engine import (is_modflow_available, build_and_run_model)
    MODFLOW_OK = True
except ImportError:
    MODFLOW_OK = False

try:
    from advanced_modules import (
        calculate_confusion_matrix, model_contaminant_transport,
        fetch_satellite_data, calculate_sar, calculate_na_percent,
        calculate_ec_quality, calculate_agricultural_drastic,
        classify_irrigation_water, independent_validation, calculate_dynamic_risk)
    ADV_OK = True
except ImportError:
    ADV_OK = False

try:
    from model_development import (calibrate_alpha_beta, compare_models, calculate_ahp_weights)
    DEV_OK = True
except ImportError:
    DEV_OK = False

def get_loaded_df(*keys):
    for key in keys:
        df = st.session_state.get(key)
        if df is None: continue
        if hasattr(df, "empty") and not df.empty: return df
    return None

def require_df(*keys):
    df = get_loaded_df(*keys)
    if df is None:
        st.warning("⚠️ لا توجد بيانات محمّلة. ارفع ملفاً أولاً.")
        st.stop()
    return df

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
    except Exception:
        return []

WEIGHTS = {
    "industrial":  {"alpha": 0.7, "beta": 0.5, "SF": 1.0, "ar": "🏭 شركات صناعية (سيانيد)"},
    "traditional": {"alpha": 0.3, "beta": 1.0, "SF": 1.1, "ar": "⛏️ معدنون تقليديون (زئبق)"},
    "mixed":       {"alpha": 0.5, "beta": 0.9, "SF": 1.3, "ar": "🔀 مختلط (سيانيد + زئبق)"},
}

AQUIFER_AR = {"massive_shale": "صخر طيني ضخم", "metamorphic_igneous": "صخور متحولة/نارية",
    "weathered_metamorphic_igneous": "صخور متحولة/نارية متآكلة",
    "thin_bedded_sequences": "تتابعات رقيقة الطبقات", "massive_sandstone": "حجر رملي ضخم",
    "massive_limestone": "حجر جيري ضخم", "sand_and_gravel": "رمل وحصى",
    "basalt": "بازلت", "karst_limestone": "حجر جيري كارستي"}
SOIL_AR = {"thin_or_absent": "رقيقة أو معدومة", "gravel": "حصى", "sand": "رمل", "peat": "خث",
    "shrinking_aggregated_clay": "طين متقلص متكتل", "sandy_loam": "طين رملي",
    "loam": "طين طميي", "silty_loam": "طمي غريني", "clay_loam": "طين غريني",
    "muck": "طين عضوي", "nonshrinking_clay": "طين غير متقلص"}
VADOSE_AR = {"confining_layer": "طبقة كتيمة", "silt_clay": "غرين وطين",
    "shale": "صخر طيني", "metamorphic_igneous": "صخور متحولة/نارية",
    "limestone": "حجر جيري", "sandstone": "حجر رملي",
    "sand_gravel_silt_clay": "رمل وحصى وغرين وطين", "sand_gravel": "رمل وحصى",
    "basalt": "بازلت", "karst_limestone": "حجر جيري كارستي"}
LEVEL_AR = {"منخفض": "🟢 منخفض", "متوسط": "🟡 متوسط", "مرتفع": "🟠 مرتفع", "مرتفع جدا": "🔴 مرتفع جداً"}

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

def get_a_rating(a):
    return {"massive_shale": 2, "metamorphic_igneous": 3, "weathered_metamorphic_igneous": 4,
        "thin_bedded_sequences": 6, "massive_sandstone": 6, "massive_limestone": 6,
        "sand_and_gravel": 8, "basalt": 9, "karst_limestone": 10}.get(a, 6)

def get_s_rating(s):
    return {"thin_or_absent": 10, "gravel": 10, "sand": 9, "peat": 8,
        "shrinking_aggregated_clay": 7, "sandy_loam": 6, "loam": 5, "silty_loam": 4,
        "clay_loam": 3, "muck": 2, "nonshrinking_clay": 1}.get(s, 5)

def get_t_rating(t):
    if t < 0: raise ValueError("Neg")
    if t <= 2.0: return 10
    if t <= 6.0: return 9
    if t <= 12.0: return 5
    if t <= 18.0: return 3
    return 1

def get_i_rating(i):
    return {"confining_layer": 1, "silt_clay": 1, "shale": 3, "metamorphic_igneous": 4,
        "limestone": 6, "sandstone": 6, "sand_gravel_silt_clay": 6, "sand_gravel": 8,
        "basalt": 9, "karst_limestone": 10}.get(i, 6)

def get_c_rating(c):
    if c < 0: raise ValueError("Neg")
    if c <= 4.074: return 1
    if c <= 12.222: return 2
    if c <= 28.518: return 4
    if c <= 40.740: return 6
    if c <= 81.480: return 8
    return 10

def calc_index(D, R, A, S, T, I, C):
    return (D*5) + (R*4) + (A*3) + (S*2) + (T*1) + (I*5) + (C*3)

def classify(idx):
    if idx >= 180: return {"level": "مرتفع جدا", "color": "red", "action": "معالجة فورية"}
    if idx >= 140: return {"level": "مرتفع", "color": "orange", "action": "مراقبة عاجلة"}
    if idx >= 100: return {"level": "متوسط", "color": "yellow", "action": "مراقبة دورية"}
    return {"level": "منخفض", "color": "green", "action": "مراقبة روتينية"}

def mitigate(idx, hdpe=False, treat=False, mon=False):
    m = float(idx)
    if hdpe: m *= 0.40
    if treat: m *= 0.60
    if mon: m *= 0.85
    red = ((idx - m) / idx * 100) if idx > 0 else 0.0
    return {"mitigated_index": round(m, 1), "reduction_pct": round(red, 1)}

def calc_drastic_t(base_drastic, cn_water, hg_water, distance_m=100.0, seepage=1.0,
                    bio_acc=1.0, mining_type="traditional",
                    alpha_override=None, beta_override=None, SF_override=None):
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
    if drastic_t >= 180: level, color = "مرتفع جدا", "red"
    elif drastic_t >= 140: level, color = "مرتفع", "orange"
    elif drastic_t >= 100: level, color = "متوسط", "yellow"
    else: level, color = "منخفض", "green"
    increase_pct = (toxicity_bonus / base_drastic * 100) if base_drastic > 0 else 0
    return {"base_drastic": base_drastic, "mining_type": mining_type,
            "alpha": alpha, "beta": beta, "source_factor": source_factor,
            "cri": round(cri, 3), "mri": round(mri, 3),
            "cn_score": round(cn_score, 2), "hg_score": round(hg_score, 2),
            "base_bonus": round(base_bonus, 2), "toxicity_bonus": round(toxicity_bonus, 2),
            "drastic_t": round(drastic_t, 1), "drastic_p": round(drastic_t, 1),
            "modifier": round(1.0 + toxicity_bonus / max(base_drastic, 1), 3),
            "increase_pct": round(increase_pct, 1), "level": level, "color": color}

def sensitivity_analysis(pv, variation=0.10):
    D = float(pv.get("depth", 15.0)); R = float(pv.get("recharge", 100.0))
    A = str(pv.get("aquifer", "massive_sandstone")); S = str(pv.get("soil", "sand"))
    T = float(pv.get("slope", 4.0)); I = str(pv.get("vadose", "sand_gravel"))
    C = float(pv.get("conductivity", 5.0))
    def ci(d, r, a, s, t, i, c):
        return calc_index(get_d_rating(d), get_r_rating(r), get_a_rating(a),
                          get_s_rating(s), get_t_rating(t), get_i_rating(i), get_c_rating(c))
    base = ci(D, R, A, S, T, I, C); res = {}
    for name, val, lo, hi in [("D", D, 0.5, 100.0), ("R", R, 0.0, 400.0),
                              ("T", T, 0.0, 30.0), ("C", C, 0.01, 100.0)]:
        v = max(lo, min(hi, val * (1 + variation)))
        if name == "D": ni = ci(v, R, A, S, T, I, C)
        elif name == "R": ni = ci(D, v, A, S, T, I, C)
        elif name == "T": ni = ci(D, R, A, S, v, I, C)
        else: ni = ci(D, R, A, S, T, I, v)
        res[name] = {"original_phys": val, "modified_phys": round(v, 2),
                     "new_index": ni, "change": ni - base,
                     "sensitivity": round(abs(ni - base) / base * 100, 3)}
    for name, br, w in [("A", get_a_rating(A), 3), ("S", get_s_rating(S), 2), ("I", get_i_rating(I), 5)]:
        nr = max(1, min(10, br + 1))
        ni = base - br * w + nr * w
        res[name] = {"original_phys": "rating", "modified_phys": "rating+1",
                     "new_index": ni, "change": ni - base,
                     "sensitivity": round(abs(ni - base) / base * 100, 3)}
    sr = dict(sorted(res.items(), key=lambda x: x[1]["sensitivity"], reverse=True))
    return {"base_index": base, "parameters": sr,
            "most_sensitive": list(sr.keys())[0] if sr else None}

def monte_carlo_analysis(pv, n_iter=1000, variation=0.15):
    np.random.seed(42)
    D = float(pv.get("depth", 15.0)); R = float(pv.get("recharge", 100.0))
    A_b = get_a_rating(str(pv.get("aquifer", "massive_sandstone")))
    S_b = get_s_rating(str(pv.get("soil", "sand")))
    T = float(pv.get("slope", 4.0)); I_b = get_i_rating(str(pv.get("vadose", "sand_gravel")))
    C = float(pv.get("conductivity", 5.0))
    D_s = np.clip(np.random.normal(D, max(0.5, D * variation), n_iter), 0.5, 100.0)
    R_s = np.clip(np.random.lognormal(np.log(max(1, R)) - 0.5 * variation**2, variation, n_iter), 0.0, 400.0) if R > 0 else np.zeros(n_iter)
    A_s = np.random.choice([max(1, A_b-1), A_b, min(10, A_b+1)], n_iter, p=[0.15, 0.70, 0.15])
    S_s = np.random.choice([max(1, S_b-1), S_b, min(10, S_b+1)], n_iter, p=[0.15, 0.70, 0.15])
    T_s = np.clip(np.random.normal(T, max(0.5, T * variation), n_iter), 0.0, 30.0)
    I_s = np.random.choice([max(1, I_b-1), I_b, min(10, I_b+1)], n_iter, p=[0.15, 0.70, 0.15])
    C_s = np.clip(np.random.lognormal(np.log(max(0.01, C)) - 0.5 * variation**2, variation, n_iter), 0.01, 100.0)
    D_r = np.select([D_s <= 1.5, D_s <= 4.6, D_s <= 9.1, D_s <= 15.2, D_s <= 22.9, D_s <= 30.5], [10, 9, 7, 5, 3, 2], default=1)
    R_r = np.select([R_s <= 50.8, R_s <= 101.6, R_s <= 177.8, R_s <= 254.0], [1, 3, 6, 8], default=9)
    T_r = np.select([T_s <= 2.0, T_s <= 6.0, T_s <= 12.0, T_s <= 18.0], [10, 9, 5, 3], default=1)
    C_r = np.select([C_s <= 4.074, C_s <= 12.222, C_s <= 28.518, C_s <= 40.740, C_s <= 81.480], [1, 2, 4, 6, 8], default=10)
    drastic = D_r*5 + R_r*4 + A_s*3 + S_s*2 + T_r*1 + I_s*5 + C_r*3
    results = np.sort(drastic.astype(int))
    def pct(p): return int(np.percentile(results, p))
    return {"mean": round(float(np.mean(results)), 1), "std": round(float(np.std(results)), 2),
            "min": int(results[0]), "max": int(results[-1]),
            "ci_90": (pct(5), pct(95)),
            "prob_over_140": round(float(np.mean(results >= 140) * 100), 1)}

def weighted_toxicity(hgw, hgs, cnw, cns):
    w = (hgw/0.006*0.40) + (hgs/1.0*0.20) + (cnw/0.07*0.30) + (cns/10.0*0.10)
    if w <= 1.0: cat, act = "آمن", "لا يتطلب تدخل"
    elif w <= 3.0: cat, act = "تحت المراقبة", "مراقبة دورية"
    elif w <= 10.0: cat, act = "خطر", "تدخل عاجل"
    else: cat, act = "خطر داهم", "إيقاف النشاط"
    return {"index": round(w, 2), "category": cat, "action": act}

def model_contaminant_transport_fixed(C0, K, porosity, gradient, distance, years, dispersivity=10.0):
    try:
        from scipy import special as sp
        has_scipy = True
    except ImportError:
        has_scipy = False
    v = (K * gradient) / porosity
    if v <= 0: return {"error": "Velocity is zero or negative"}
    D = dispersivity * v
    if D <= 0: return {"error": "Dispersion coefficient is zero"}
    total_days = int(years * 365.25)
    times = np.linspace(1, total_days, min(200, max(10, total_days)))
    concentrations = []
    for t in times:
        if t <= 0: C = 0.0
        else:
            arg = (distance - v * t) / (2.0 * np.sqrt(D * t))
            if has_scipy:
                erfc_val = float(sp.erfc(arg))
            else:
                z = abs(arg); tt = 1.0 / (1.0 + 0.5 * z)
                erf_approx = 1 - tt * np.exp(-z*z - 1.26551223 + tt * (1.00002368 + tt * (0.37409196 + tt * (0.09678418 + tt * (-0.18628806 + tt * (0.27886807 + tt * (-1.13520398 + tt * (1.48851587 + tt * (-0.82215223 + tt * 0.17087277)))))))))
                erfc_val = 1 - erf_approx if arg >= 0 else 1 + erf_approx
            C = (C0 / 2.0) * erfc_val
            C = max(0.0, min(C0, C))
        concentrations.append(round(C, 6))
    df = pd.DataFrame({"السنة": [round(t / 365.25, 2) for t in times],
        "التركيز (mg/L)": concentrations, "المسافة (m)": [round(v * t, 1) for t in times]})
    return {"results": df, "v_seepage": round(v, 6), "D_dispersion": round(D, 4),
            "t_travel_years": round(distance / v / 365.25, 3)}

def compute_basic_metrics(y_true, y_score, threshold):
    if not SKLEARN_OK: return {"error": "scikit-learn غير مثبت"}
    try:
        y_true = np.array(y_true); y_score = np.array(y_score)
        y_pred = (y_score >= threshold).astype(int)
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
        kappa = float(cohen_kappa_score(y_true, y_pred)) if len(np.unique(y_true)) > 1 else 0.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        accuracy = float((tp + tn) / (tp + tn + fp + fn))
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        try: auc = float(roc_auc_score(y_true, y_score))
        except Exception: auc = 0.5
        return {"kappa": round(kappa, 3), "recall": round(recall * 100, 1),
                "precision": round(precision * 100, 1), "accuracy": round(accuracy * 100, 1),
                "f1": round(f1, 3), "auc": round(auc, 3),
                "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn)}
    except Exception as e: return {"error": str(e)}

def bootstrap_kappa_ci(y_true, y_score, threshold, n_boot=1000, seed=42):
    if not SKLEARN_OK: return {"error": "scikit-learn غير مثبت"}
    try:
        y_true = np.array(y_true); y_score = np.array(y_score)
        np.random.seed(seed); kappas = []
        for _ in range(n_boot):
            idx = np.random.choice(len(y_true), len(y_true), replace=True)
            yt = y_true[idx]; ys = y_score[idx]
            if len(np.unique(yt)) < 2: continue
            yp = (ys >= threshold).astype(int)
            try: kappas.append(cohen_kappa_score(yt, yp))
            except Exception: continue
        if not kappas: return {"mean": 0, "std": 0, "ci_low": 0, "ci_high": 0}
        kappas = np.array(kappas)
        return {"mean": round(float(np.mean(kappas)), 3), "std": round(float(np.std(kappas)), 3),
                "ci_low": round(float(np.percentile(kappas, 2.5)), 3),
                "ci_high": round(float(np.percentile(kappas, 97.5)), 3)}
    except Exception as e: return {"error": str(e)}

def loocv_analysis(y_true, y_score, threshold):
    if not SKLEARN_OK: return {"error": "scikit-learn غير مثبت"}
    try:
        y_true = np.array(y_true); y_score = np.array(y_score)
        n = len(y_true); all_actual = []; all_pred = []
        for i in range(n):
            all_actual.append(y_true[i]); all_pred.append(int(y_score[i] >= threshold))
        all_actual = np.array(all_actual); all_pred = np.array(all_pred)
        kappa = float(cohen_kappa_score(all_actual, all_pred)) if len(np.unique(all_actual)) > 1 else 0.0
        accuracy = float(np.mean(all_actual == all_pred) * 100)
        tp = int(np.sum((all_actual == 1) & (all_pred == 1)))
        fn = int(np.sum((all_actual == 1) & (all_pred == 0)))
        recall = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0.0
        return {"kappa": round(kappa, 3), "accuracy": round(accuracy, 1), "recall": round(recall, 1),
                "n_correct": int(np.sum(all_actual == all_pred)), "n_total": n}
    except Exception as e: return {"error": str(e)}

def generate_html_report(site_info, drastic, drastic_t, level, recommendation):
    return f"""<!DOCTYPE html>
<html dir="rtl" lang="ar"><head><meta charset="UTF-8"><title>تقرير — {site_info.get('name', 'N/A')}</title>
<style>body {{ font-family: 'Segoe UI', Tahoma, Arial; padding: 40px; max-width: 800px; margin: 0 auto; }}
h1 {{ color: #5c2c16; border-bottom: 3px solid #c19a6b; padding-bottom: 10px; }}
h2 {{ color: #5c2c16; margin-top: 30px; }}
table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
th, td {{ padding: 10px; border: 1px solid #ddd; text-align: right; }}
th {{ background-color: #f5eedc; color: #5c2c16; }}
.metric {{ font-size: 1.5em; font-weight: bold; color: #c19a6b; }}
.footer {{ margin-top: 40px; text-align: center; color: #666; font-size: 0.9em; }}
.disclaimer {{ background: #fff3e0; padding: 15px; border-right: 4px solid #ff9800; margin: 20px 0; }}</style>
</head><body>
<h1>⛏️ تقرير تقييم المخاطر</h1>
<p><b>التاريخ:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<h2>📍 معلومات الموقع</h2>
<table>
<tr><th>الموقع</th><td>{site_info.get('name', 'N/A')}</td></tr>
<tr><th>الولاية</th><td>{site_info.get('state', 'N/A')}</td></tr>
<tr><th>الإحداثيات</th><td>{site_info.get('coords', 'N/A')}</td></tr>
<tr><th>المصدر</th><td>{site_info.get('source', 'N/A')}</td></tr>
<tr><th>التوثيق</th><td>{'✅ موثق' if site_info.get('verified', False) else 'ℹ️ للعرض'}</td></tr>
<tr><th>نمط التعدين</th><td>{site_info.get('mining_type_ar', 'N/A')}</td></tr>
</table>
<h2>📊 المعايير</h2>
<table>
<tr><th>العمق (D)</th><td>{site_info.get('depth', 'N/A')} م</td></tr>
<tr><th>التغذية (R)</th><td>{site_info.get('recharge', 'N/A')} مم/سنة</td></tr>
<tr><th>الميل (T)</th><td>{site_info.get('slope', 'N/A')} %</td></tr>
<tr><th>التوصيلية (C)</th><td>{site_info.get('conductivity', 'N/A')} م/يوم</td></tr>
<tr><th>CN</th><td>{site_info.get('cn', 'N/A')} mg/L</td></tr>
<tr><th>Hg</th><td>{site_info.get('hg', 'N/A')} mg/L</td></tr>
</table>
<h2>🎯 النتائج</h2>
<table>
<tr><th>DRASTIC</th><td class="metric">{drastic}/230</td></tr>
<tr><th>DRASTIC-Tox</th><td class="metric">{drastic_t}/280</td></tr>
<tr><th>المستوى</th><td class="metric">{level}</td></tr>
</table>
<h2>💡 التوصية</h2>
<div class="disclaimer"><b>{recommendation}</b></div>
<div class="footer">
<p>⚠️ <b>PILOT VERSION</b> — أداة فرز أولي، لا تُغني عن الفحص المخبري</p>
<p>نظام التعدين السوداني v57.6 — جامعة الخرطوم</p>
</div></body></html>"""

def build_heatmap_verified(show_heat=True, show_markers=True):
    m = folium.Map(location=[15.5, 32.5], zoom_start=6, tiles='OpenStreetMap')
    heat_data = []; stats = {"low": 0, "medium": 0, "high": 0, "very_high": 0}; sites_info = []
    for state_name, state_data in STATES_DATABASE.items():
        for site_key, site_data in state_data.get("sites", {}).items():
            if not site_data.get("verified", False): continue
            coords = site_data.get("coords", None)
            if not coords or len(coords) < 2: continue
            lat, lon = coords[0], coords[1]
            try:
                drastic = calc_index(
                    get_d_rating(site_data.get("depth_m", 15)),
                    get_r_rating(site_data.get("recharge_mm", 100)),
                    get_a_rating(site_data.get("aquifer", "massive_sandstone")),
                    get_s_rating(site_data.get("soil", "sand")),
                    get_t_rating(site_data.get("slope_pct", 4)),
                    get_i_rating(site_data.get("vadose", "sand_gravel")),
                    get_c_rating(site_data.get("conductivity", 5)))
                cn = site_data.get("cn_water_mg_l", 0.0); hg = site_data.get("hg_water_mg_l", 0.0)
                mt = site_data.get("mining_type", "traditional")
                if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mt:
                    w = CALIBRATED_WEIGHTS
                    drastic_t = calc_drastic_t(drastic, cn, hg, mining_type=mt,
                        alpha_override=w["alpha"], beta_override=w["beta"],
                        SF_override=w["SF"])["drastic_t"]
                else:
                    drastic_t = calc_drastic_t(drastic, cn, hg, mining_type=mt)["drastic_t"]
            except Exception: continue
            if drastic_t >= 180: color, radius, level = "#d32f2f", 20, "مرتفع جداً"; stats["very_high"] += 1
            elif drastic_t >= 140: color, radius, level = "#f57c00", 16, "مرتفع"; stats["high"] += 1
            elif drastic_t >= 100: color, radius, level = "#fbc02d", 12, "متوسط"; stats["medium"] += 1
            else: color, radius, level = "#388e3c", 9, "منخفض"; stats["low"] += 1
            popup_html = f"""<div style="font-family:Arial;font-size:12px;min-width:230px;">
<h4 style="color:{color};margin:0 0 8px 0;">{site_data.get('name_ar', site_key)}</h4>
<hr style="margin:5px 0;"><b>الولاية:</b> {state_name}<br>
<b>المصدر:</b> {state_data.get('source', 'N/A')}<br>
<hr style="margin:5px 0;"><b>DRASTIC:</b> {drastic}<br>
<b>DRASTIC-Tox:</b> <span style="color:{color};font-weight:bold;">{drastic_t}</span><br>
<b>المستوى:</b> {level}<br>
<hr style="margin:5px 0;"><b>CN:</b> {cn} mg/L<br><b>Hg:</b> {hg} mg/L</div>"""
            if show_markers:
                folium.CircleMarker(location=[lat, lon], radius=radius,
                    popup=folium.Popup(popup_html, max_width=280),
                    tooltip=f"{site_data.get('name_ar', site_key)} — {drastic_t}",
                    color=color, fill=True, fillColor=color, fillOpacity=0.75, weight=2).add_to(m)
            heat_data.append([lat, lon, min(1.0, drastic_t / 230.0)])
            sites_info.append({"state": state_name, "site": site_data.get("name_ar", site_key),
                "lat": lat, "lon": lon, "DRASTIC": drastic, "DRASTIC-Tox": drastic_t,
                "CN": cn, "Hg": hg, "المستوى": level})
    if show_heat and heat_data:
        HeatMap(heat_data, min_opacity=0.3, max_zoom=10, radius=30, blur=20,
                gradient={0.0: '#388e3c', 0.4: '#fbc02d', 0.7: '#f57c00', 1.0: '#d32f2f'}).add_to(m)
    legend_html = """<div style="position:fixed;bottom:50px;left:50px;width:230px;
background-color:white;border:2px solid grey;z-index:9999;font-size:13px;padding:12px;
border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.2);">
<b style="font-size:14px;">🗺️ مفتاح الخريطة</b>
<div style="font-size:11px;color:#666;margin:4px 0;">المواقع الموثقة فقط</div>
<hr style="margin:6px 0;">
<span style="color:#388e3c;font-size:16px;">●</span> منخفض (&lt; 100)<br>
<span style="color:#fbc02d;font-size:16px;">●</span> متوسط (100-140)<br>
<span style="color:#f57c00;font-size:16px;">●</span> مرتفع (140-180)<br>
<span style="color:#d32f2f;font-size:16px;">●</span> مرتفع جداً (≥ 180)</div>"""
    m.get_root().html.add_child(folium.Element(legend_html))
    return m, stats, pd.DataFrame(sites_info)

VALID_AQUIFERS = ["massive_shale", "metamorphic_igneous", "weathered_metamorphic_igneous",
    "thin_bedded_sequences", "massive_sandstone", "massive_limestone",
    "sand_and_gravel", "basalt", "karst_limestone"]
VALID_SOILS = ["thin_or_absent", "gravel", "sand", "peat", "shrinking_aggregated_clay",
    "sandy_loam", "loam", "silty_loam", "clay_loam", "muck", "nonshrinking_clay"]
VALID_VADOSE = ["confining_layer", "silt_clay", "shale", "metamorphic_igneous",
    "limestone", "sandstone", "sand_gravel_silt_clay", "sand_gravel", "basalt", "karst_limestone"]

if DS_OK:
    preset = get_preset_locations_for_app()
    summary = get_data_summary()
    n_states = summary.get('total_states', 0)
    try:
        _df_all = get_all_sites_as_dataframe_with_flag()
        n_sites_total = safe_len(_df_all, summary.get('total_sites', 0))
        n_sites_verified = safe_sum(_df_all, "verified", 0)
    except Exception:
        n_sites_total = summary.get('total_sites', 0); n_sites_verified = 0
    agri_summary = get_agricultural_data_summary()
    n_agri_states = agri_summary.get('total_states', 0)
    try:
        _df_agri = get_all_agri_sites_as_dataframe()
        n_agri_sites = safe_len(_df_agri, agri_summary.get('total_sites', 0))
    except Exception:
        n_agri_sites = agri_summary.get('total_sites', 0)
else:
    preset = {}; n_states = n_sites_total = n_sites_verified = n_agri_states = n_agri_sites = 0

INDUSTRIAL_SITES = load_industrial_sites_csv()

if "calibrated_weights" not in st.session_state:
    st.session_state["calibrated_weights"] = None
CALIBRATED_WEIGHTS = st.session_state["calibrated_weights"]

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown("""
<div style="background: linear-gradient(135deg, #5c2c16 0%, #c19a6b 100%);
padding: 16px; border-radius: 12px; color: white; text-align: center; margin-bottom: 16px;">
<div style="font-size: 1.3em; font-weight: 700;">📤 منطقة رفع الملفات</div>
<div style="font-size: 0.8em; opacity: 0.9;">ارفع ملفاتك من هنا</div>
</div>
""", unsafe_allow_html=True)

uploaded_val = st.sidebar.file_uploader("🔵 ملف التحقق:", type=["csv", "xlsx"], key="uploader_validation")
uploaded_bulk = st.sidebar.file_uploader("🟢 ملف التقييم الجماعي:", type=["csv", "xlsx"], key="uploader_bulk")
uploaded_extra = st.sidebar.file_uploader("🟡 ملف إضافي:", type=["csv", "xlsx"], key="uploader_extra")

if uploaded_val is not None:
    try:
        df_val_side = pd.read_csv(uploaded_val) if uploaded_val.name.endswith(".csv") else pd.read_excel(uploaded_val)
        st.session_state["df_validation"] = df_val_side
        st.sidebar.success(f"✅ {len(df_val_side)} صف")
    except Exception as e: st.sidebar.error(f"❌ {str(e)[:80]}")

if uploaded_bulk is not None:
    try:
        df_bulk_side = pd.read_csv(uploaded_bulk) if uploaded_bulk.name.endswith(".csv") else pd.read_excel(uploaded_bulk)
        st.session_state["df_bulk"] = df_bulk_side
        st.sidebar.success(f"✅ {len(df_bulk_side)} صف")
    except Exception as e: st.sidebar.error(f"❌ {str(e)[:80]}")

if uploaded_extra is not None:
    try:
        df_extra_side = pd.read_csv(uploaded_extra) if uploaded_extra.name.endswith(".csv") else pd.read_excel(uploaded_extra)
        st.session_state["df_extra"] = df_extra_side
        st.sidebar.info(f"ℹ️ {len(df_extra_side)} صف")
    except Exception as e: st.sidebar.error(f"❌ {str(e)[:80]}")

if st.sidebar.button("🗑️ مسح جميع الملفات"):
    for k in ["df_validation", "df_bulk", "df_extra", "df_combined"]:
        st.session_state.pop(k, None)
    st.rerun()

st.sidebar.markdown("---")

if DS_OK:
    st.sidebar.markdown("### 📊 جودة البيانات")
    st.sidebar.markdown(f"""
<div class="quality-box-ok"><div style="font-size:0.85em;color:#2e7d32;">✅ <b>موثق:</b> {n_sites_verified} موقع</div></div>
<div class="quality-box-warn"><div style="font-size:0.85em;color:#e65100;">ℹ️ <b>للعرض فقط:</b> {n_sites_total - n_sites_verified} موقع</div></div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 نطاق البيانات")
DATA_SCOPE = st.sidebar.radio("اختر:",
    ["⛏️ تقليدي (موثّق)", "🏭 صناعي (تجريبي)", "🔀 الكل"],
    index=0, key="data_scope")

if DATA_SCOPE.startswith("⛏️"): SCOPE_KEY = "traditional"
elif DATA_SCOPE.startswith("🏭"): SCOPE_KEY = "industrial"
else: SCOPE_KEY = "all"

if SCOPE_KEY == "industrial" and not INDUSTRIAL_SITES:
    st.sidebar.warning("⚠️ لم يُعثر على `industrial_sites.csv`")

_display_weights = None
if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == SCOPE_KEY:
    _display_weights = {"ar": WEIGHTS[SCOPE_KEY]["ar"] + " (مُعايرة)",
        "alpha": CALIBRATED_WEIGHTS["alpha"], "beta": CALIBRATED_WEIGHTS["beta"],
        "SF": CALIBRATED_WEIGHTS["SF"], "kappa": CALIBRATED_WEIGHTS.get("kappa", "—")}
else:
    _w = WEIGHTS.get(SCOPE_KEY if SCOPE_KEY != "all" else "traditional", WEIGHTS["traditional"])
    _display_weights = {"ar": _w["ar"], "alpha": _w["alpha"], "beta": _w["beta"],
        "SF": _w["SF"], "kappa": "—"}

_badge_cls = "mining-industrial" if SCOPE_KEY == "industrial" else \
             "mining-mixed" if SCOPE_KEY == "mixed" else "mining-traditional"

st.sidebar.markdown(f"""
<div class="mining-badge {_badge_cls}">
{_display_weights['ar']}
</div>
<div style="font-size:0.75em;color:#666;margin-top:4px;">
α={_display_weights['alpha']} | β={_display_weights['beta']} | SF={_display_weights['SF']}
{'<br><b>Kappa: ' + str(_display_weights['kappa']) + '</b>' if _display_weights['kappa'] != '—' else ''}
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("## 🎛️ وضع التشغيل")
mode_options = ["🏠 النظام الأساسي"]
if ADV_OK:
    mode_options += ["🌾 القطاع الزراعي", "✅ التحقق الفعلي", "🚀 نقل الملوثات"]
    mode_options += ["🔬 التحقق المستقل", "🛰️ الأقمار الصناعية", "⏳ الديناميكي"]
if MODFLOW_OK:
    mode_options.append("🌊 MODFLOW")

mode = st.sidebar.radio("اختر:", mode_options, key="app_mode")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔧 الحالة")
status_icon = "✅" if _modflow_status in ["already_installed", "installed"] else "⚠️"
st.sidebar.info(f"{status_icon} MODFLOW: {_modflow_status}")

if "ci" in st.session_state:
    st.sidebar.success(f"✅ مؤشر: {st.session_state['ci']}")

st.sidebar.markdown("---")
with st.sidebar.expander("ℹ️ **حول الأداة**", expanded=False):
    st.markdown(f"""
<div class="about-box">
<h4>⛏️ نظام التعدين السوداني v57.6</h4>
<p style="font-size:0.85em;">أداة تقييم مخاطر المياه الجوفية.</p>
<h4>📚 المراجع العلمية:</h4>
<ul style="font-size:0.8em;">
<li>Aller et al. (1987) — DRASTIC الأصلي</li>
<li>Konaté et al. (2025) — All Earth</li>
<li>Karan et al. (2018) — Land Degradation &amp; Development</li>
<li>Landis &amp; Koch (1977) — Kappa</li>
<li>Youden (1950) — العتبة المثلى</li>
</ul>
<h4>⚠️ قيود:</h4>
<ul style="font-size:0.85em;">
<li>PILOT VERSION</li>
<li>n = 11 موقع موثق</li>
<li>لا يُغني عن الفحص المخبري</li>
</ul>
<h4>🏛️ الجهة:</h4>
<p style="font-size:0.85em;">جامعة الخرطوم — كلية الهندسة<br>الإصدار 57.6</p>
<h4>🧩 الوحدات:</h4>
<p style="font-size:0.8em;">
auto_calibration: {'✅' if AUTOCAL_OK else '❌'}<br>
auto_maps: {'✅' if MAPS_OK else '❌'}<br>
modflow: {'✅' if MODFLOW_OK else '❌'}<br>
advanced: {'✅' if ADV_OK else '❌'}<br>
model_development: {'✅' if DEV_OK else '❌'}
</p>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="pilot-banner">⚠️ PILOT VERSION — أداة فرز أولي، لا تُغني عن الفحص المخبري</div>
<div class="header-container">
<div class="header-title">⛏️ نظام التعدين السوداني</div>
<div class="header-subtitle">جامعة الخرطوم - كلية الهندسة</div>
<div class="header-subtitle">DRASTIC + DRASTIC-Tox + MODFLOW 6</div>
<div class="header-badge">الإصدار 57.6 | التعدين: {n_states} ولاية، {n_sites_total} موقع ({n_sites_verified} موثق) | الزراعة: {n_agri_states} ولاية، {n_agri_sites} موقع</div>
</div>
""", unsafe_allow_html=True)

with st.expander("📤 **منطقة رفع الملفات الرئيسية**", expanded=False):
    st.markdown('<div class="upload-zone"><h4>📂 ارفع ملفات البيانات</h4><p>CSV أو Excel</p></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        main_val = st.file_uploader("🔵 ملف التحقق:", type=["csv", "xlsx"], key="main_val")
        if main_val:
            try:
                st.session_state["df_validation"] = pd.read_csv(main_val) if main_val.name.endswith(".csv") else pd.read_excel(main_val)
                st.success(f"✅ {len(st.session_state['df_validation'])} صف")
            except Exception as e: st.error(f"❌ {str(e)[:60]}")
    with col2:
        main_bulk = st.file_uploader("🟢 ملف التقييم:", type=["csv", "xlsx"], key="main_bulk")
        if main_bulk:
            try:
                st.session_state["df_bulk"] = pd.read_csv(main_bulk) if main_bulk.name.endswith(".csv") else pd.read_excel(main_bulk)
                st.success(f"✅ {len(st.session_state['df_bulk'])} صف")
            except Exception as e: st.error(f"❌ {str(e)[:60]}")
    with col3:
        main_extra = st.file_uploader("🟡 ملف إضافي:", type=["csv", "xlsx"], key="main_extra")
        if main_extra:
            try:
                st.session_state["df_extra"] = pd.read_csv(main_extra) if main_extra.name.endswith(".csv") else pd.read_excel(main_extra)
                st.info(f"ℹ️ {len(st.session_state['df_extra'])} صف")
            except Exception as e: st.error(f"❌ {str(e)[:60]}")
    st.markdown("---")
    sample = pd.DataFrame({"site_name": ["موقع 1", "موقع 2"], "depth_m": [12.0, 15.0],
        "recharge_mm": [20.0, 18.0], "slope_pct": [3.0, 4.0], "conductivity": [2.5, 3.0],
        "aquifer": ["massive_sandstone", "sand_and_gravel"], "soil": ["sand", "sandy_loam"],
        "vadose": ["sand_gravel", "sandstone"], "cn_water_mg_l": [0.10, 0.09],
        "hg_water_mg_l": [0.008, 0.007], "actual_contaminated": [1, 1]})
    st.download_button("📥 تحميل القالب", data=sample.to_csv(index=False).encode("utf-8-sig"),
        file_name="template.csv", mime="text/csv", use_container_width=True)

st.markdown("---")

# ============================================================
# MODE 1: النظام الأساسي
# ============================================================
if mode == "🏠 النظام الأساسي":
    tabs = st.tabs(["📍 المدخلات", "➕ إدخال يدوي", "📊 التقييم الجماعي",
                    "🛡️ الحلول", "📄 التقرير", "🗺️ الخريطة الحرارية",
                    "📈 الحساسية", "☠️ السمية", "🌍 GIS",
                    "🎲 Monte Carlo", "🔬 التحقق المتقدم", "🚀 تطوير النموذج",
                    "🗺️ الخرائط التلقائية", "🎯 معايرة الأوزان", "📐 العتبة المثلى"])

    with tabs[0]:
        st.markdown('<div class="section-header"><h3>📍 اختيار الموقع</h3></div>', unsafe_allow_html=True)
        if not DS_OK:
            st.error("❌ `data_sources.py` غير متوفر")
        else:
            active_label = WEIGHTS[SCOPE_KEY if SCOPE_KEY != "all" else "traditional"]["ar"]
            st.info(f"🎯 **نمط التعدين النشط:** {active_label}")

            c1, c2 = st.columns([1, 2])
            with c1:
                state = st.selectbox("**الولاية:**", get_states_list(), key="state_selector")
            with c2:
                state_info = STATES_DATABASE[state]
                st.markdown(f'<div class="info-card" style="margin-top:28px;"><div style="font-size:0.9em;color:#5c2c16;">ℹ️ {state_info["description"]}<br><span style="font-size:0.85em;color:#666;">المصدر: {state_info["source"]}</span></div></div>', unsafe_allow_html=True)

            site_key = st.selectbox("**الموقع:**", get_sites_list(state), key="site_selector")
            site_data = get_site_data(state, site_key)

            mining_type_key = site_data.get("mining_type", SCOPE_KEY if SCOPE_KEY != "all" else "traditional")
            mining_type_label = WEIGHTS.get(mining_type_key, WEIGHTS["traditional"])["ar"]
            badge_class = "mining-industrial" if mining_type_key == "industrial" else \
                          "mining-mixed" if mining_type_key == "mixed" else "mining-traditional"
            st.markdown(f'<div class="mining-badge {badge_class}">{mining_type_label}</div>', unsafe_allow_html=True)
            st.session_state["mining_type"] = mining_type_key
            st.markdown("---")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("النشاط", site_data.get("activity", "N/A"))
            c2.metric("الموسم", site_data.get("season", "N/A"))
            c3.metric("الحالة", "🔴 ملوث" if site_data["actual_contaminated"] == 1 else "🟢 نظيف")
            c4.metric("التوثيق", "✅ موثق" if site_data.get("verified", False) else "ℹ️ للعرض")

            c1, c2 = st.columns(2)
            with c1:
                st.metric("D - عمق", f"{site_data['depth_m']} م")
                st.metric("R - تغذية", f"{site_data['recharge_mm']} مم/سنة")
                st.metric("T - ميل", f"{site_data['slope_pct']} %")
                st.metric("C - توصيلية", f"{site_data['conductivity']} م/يوم")
            with c2:
                st.metric("A - الوسط", AQUIFER_AR.get(site_data['aquifer'], site_data['aquifer']))
                st.metric("S - التربة", SOIL_AR.get(site_data['soil'], site_data['soil']))
                st.metric("I - التهوية", VADOSE_AR.get(site_data['vadose'], site_data['vadose']))
                st.metric("θ - المسامية", "0.25")

            c1, c2 = st.columns(2)
            c1.metric("CN", f"{site_data['cn_water_mg_l']} mg/L")
            c2.metric("Hg", f"{site_data['hg_water_mg_l']} mg/L")
            st.caption("**الحدود:** CN = 0.05 mg/L | Hg = 0.0007 mg/L")

            try:
                idx = calc_index(get_d_rating(site_data['depth_m']), get_r_rating(site_data['recharge_mm']),
                                 get_a_rating(site_data['aquifer']), get_s_rating(site_data['soil']),
                                 get_t_rating(site_data['slope_pct']), get_i_rating(site_data['vadose']),
                                 get_c_rating(site_data['conductivity']))
                risk = classify(idx)
                st.session_state["ci"] = idx
                st.session_state["cv"] = {"depth": site_data['depth_m'], "recharge": site_data['recharge_mm'],
                    "aquifer": site_data['aquifer'], "soil": site_data['soil'], "slope": site_data['slope_pct'],
                    "vadose": site_data['vadose'], "conductivity": site_data['conductivity'],
                    "cn_water_mg_l": site_data['cn_water_mg_l'], "hg_water_mg_l": site_data['hg_water_mg_l']}

                z1, z2, z3 = st.columns(3)
                z1.metric("DRASTIC", f"{idx}/230")
                z2.metric("المستوى", LEVEL_AR.get(risk["level"], risk["level"]))
                z3.metric("النسبة", f"{round(idx/230*100, 1)}%")

                if risk["color"] == "red": st.error(f"🔴 {risk['action']}")
                elif risk["color"] == "orange": st.warning(f"🟠 {risk['action']}")
                elif risk["color"] == "yellow": st.info(f"🟡 {risk['action']}")
                else: st.success(f"🟢 {risk['action']}")

                if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mining_type_key:
                    dt_result = calc_drastic_t(idx, site_data['cn_water_mg_l'], site_data['hg_water_mg_l'],
                        mining_type=mining_type_key, alpha_override=CALIBRATED_WEIGHTS["alpha"],
                        beta_override=CALIBRATED_WEIGHTS["beta"], SF_override=CALIBRATED_WEIGHTS["SF"])
                    st.caption("✅ يتم استخدام الأوزان **المُعايرة**")
                else:
                    dt_result = calc_drastic_t(idx, site_data['cn_water_mg_l'],
                                               site_data['hg_water_mg_l'], mining_type=mining_type_key)

                st.markdown("---")
                st.markdown(f"#### 🧪 DRASTIC-Tox — {mining_type_label}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("DRASTIC-Tox", f"{dt_result['drastic_t']}/280", delta=f"+{dt_result['increase_pct']}%")
                m2.metric("Bonus", dt_result['toxicity_bonus'])
                m3.metric("α (CN)", dt_result['alpha'])
                m4.metric("β (Hg)", dt_result['beta'])

                with st.expander("🔬 تفاصيل الحساب الكامل"):
                    d1, d2, d3, d4 = st.columns(4)
                    d1.metric("CN Score", dt_result['cn_score'])
                    d2.metric("Hg Score", dt_result['hg_score'])
                    d3.metric("Base Bonus", dt_result['base_bonus'])
                    d4.metric("Source Factor", dt_result['source_factor'])
                    st.markdown(f"""
**المعادلة:**
