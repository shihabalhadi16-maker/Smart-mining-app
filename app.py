"""نظام التعدين السوداني v57.8 — جامعة الخرطوم"""
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
    from auto_calibration import (auto_calibrate_weights, apply_calibration,
        compare_with_defaults, interpret_kappa, find_optimal_threshold)
    AUTOCAL_OK = True
except ImportError:
    AUTOCAL_OK = False

st.set_page_config(page_title="نظام التعدين السوداني v57.8", page_icon="⛏️", layout="wide", initial_sidebar_state="expanded")

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
        with st.spinner("Loading MODFLOW 6..."):
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
    "industrial":  {"alpha": 0.7, "beta": 0.5, "SF": 1.0, "ar": "Industrial Companies"},
    "traditional": {"alpha": 0.3, "beta": 1.0, "SF": 1.1, "ar": "Traditional Miners"},
    "mixed":       {"alpha": 0.5, "beta": 0.9, "SF": 1.3, "ar": "Mixed"},
}
OPTIMAL_THRESHOLDS = {"traditional": 106.5, "industrial": 128.0, "mixed": 117.0}
def get_optimal_threshold(mining_type):
    return OPTIMAL_THRESHOLDS.get(mining_type, 140.0)

AQUIFER_AR = {"massive_shale":"صخر طيني ضخم","metamorphic_igneous":"صخور متحولة/نارية","weathered_metamorphic_igneous":"صخور متحولة/نارية متآكلة","thin_bedded_sequences":"تتابعات رقيقة الطبقات","massive_sandstone":"حجر رملي ضخم","massive_limestone":"حجر جيري ضخم","sand_and_gravel":"رمل وحصى","basalt":"بازلت","karst_limestone":"حجر جيري كارستي"}
SOIL_AR = {"thin_or_absent":"رقيقة أو معدومة","gravel":"حصى","sand":"رمل","peat":"خث","shrinking_aggregated_clay":"طين متقلص متكتل","sandy_loam":"طين رملي","loam":"طين طميي","silty_loam":"طمي غريني","clay_loam":"طين غريني","muck":"طين عضوي","nonshrinking_clay":"طين غير متقلص"}
VADOSE_AR = {"confining_layer":"طبقة كتيمة","silt_clay":"غرين وطين","shale":"صخر طيني","metamorphic_igneous":"صخور متحولة/نارية","limestone":"حجر جيري","sandstone":"حجر رملي","sand_gravel_silt_clay":"رمل وحصى وغرين وطين","sand_gravel":"رمل وحصى","basalt":"بازلت","karst_limestone":"حجر جيري كارستي"}
LEVEL_AR = {"منخفض":"Green Low","متوسط":"Yellow Medium","مرتفع":"Orange High","مرتفع جدا":"Red Very High"}

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
    if idx >= 180: return {"level":"Very High","color":"red","action":"Immediate Treatment"}
    if idx >= 140: return {"level":"High","color":"orange","action":"Urgent Monitoring"}
    if idx >= 100: return {"level":"Medium","color":"yellow","action":"Periodic Monitoring"}
    return {"level":"Low","color":"green","action":"Routine Monitoring"}

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
    if drastic_t >= 180: level, color = "Very High", "red"
    elif drastic_t >= 140: level, color = "High", "orange"
    elif drastic_t >= 100: level, color = "Medium", "yellow"
    else: level, color = "Low", "green"
    increase_pct = (toxicity_bonus / base_drastic * 100) if base_drastic > 0 else 0
    return {"base_drastic":base_drastic,"mining_type":mining_type,"alpha":alpha,"beta":beta,
            "source_factor":source_factor,"cri":round(cri,3),"mri":round(mri,3),
            "cn_score":round(cn_score,2),"hg_score":round(hg_score,2),"base_bonus":round(base_bonus,2),
            "toxicity_bonus":round(toxicity_bonus,2),"drastic_t":round(drastic_t,1),
            "drastic_p":round(drastic_t,1),"modifier":round(1.0 + toxicity_bonus / max(base_drastic, 1), 3),
            "increase_pct":round(increase_pct,1),"level":level,"color":color}

def weighted_toxicity(hgw, hgs, cnw, cns, mining_type="traditional"):
    CN_LIMIT = 0.05; HG_LIMIT = 0.0007
    cn_score = min(30.0, (cnw / CN_LIMIT) * 30.0)
    hg_score = min(30.0, (hgw / HG_LIMIT) * 30.0)
    w = WEIGHTS.get(mining_type, WEIGHTS["traditional"])
    alpha, beta = w["alpha"], w["beta"]
    bonus = min(50.0, alpha * cn_score + beta * hg_score)
    soil_factor = 1.0
    if hgs > 1.0: soil_factor += 0.3
    if cns > 10.0: soil_factor += 0.3
    toxicity_index = bonus * soil_factor
    if toxicity_index <= 5.0: cat, act = "Safe", "No action"
    elif toxicity_index <= 15.0: cat, act = "Under Monitoring", "Periodic"
    elif toxicity_index <= 30.0: cat, act = "Hazardous", "Urgent"
    else: cat, act = "Critical", "Stop Activity"
    return {"index": round(toxicity_index, 2), "cn_score": round(cn_score, 2),
            "hg_score": round(hg_score, 2), "bonus": round(bonus, 2),
            "soil_factor": round(soil_factor, 2),
            "category": cat, "action": act, "mining_type": mining_type}

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

def monte_carlo_analysis(pv, n_iter=1000, variation=0.15):
    np.random.seed(42)
    D=float(pv.get("depth",15.0)); R=float(pv.get("recharge",100.0))
    A_b=get_a_rating(str(pv.get("aquifer","massive_sandstone"))); S_b=get_s_rating(str(pv.get("soil","sand")))
    T=float(pv.get("slope",4.0)); I_b=get_i_rating(str(pv.get("vadose","sand_gravel"))); C=float(pv.get("conductivity",5.0))
    D_s = np.clip(np.random.normal(D, max(0.5, D*variation), n_iter), 0.5, 100.0)
    R_s = np.clip(np.random.lognormal(np.log(max(1,R)) - 0.5*variation**2, variation, n_iter), 0.0, 400.0) if R > 0 else np.zeros(n_iter)
    A_s = np.random.choice([max(1,A_b-1),A_b,min(10,A_b+1)], n_iter, p=[0.15,0.70,0.15])
    S_s = np.random.choice([max(1,S_b-1),S_b,min(10,S_b+1)], n_iter, p=[0.15,0.70,0.15])
    T_s = np.clip(np.random.normal(T, max(0.5,T*variation), n_iter), 0.0, 30.0)
    I_s = np.random.choice([max(1,I_b-1),I_b,min(10,I_b+1)], n_iter, p=[0.15,0.70,0.15])
    C_s = np.clip(np.random.lognormal(np.log(max(0.01,C)) - 0.5*variation**2, variation, n_iter), 0.01, 100.0)
    D_r = np.select([D_s<=1.5,D_s<=4.6,D_s<=9.1,D_s<=15.2,D_s<=22.9,D_s<=30.5],[10,9,7,5,3,2],default=1)
    R_r = np.select([R_s<=50.8,R_s<=101.6,R_s<=177.8,R_s<=254.0],[1,3,6,8],default=9)
    T_r = np.select([T_s<=2.0,T_s<=6.0,T_s<=12.0,T_s<=18.0],[10,9,5,3],default=1)
    C_r = np.select([C_s<=4.074,C_s<=12.222,C_s<=28.518,C_s<=40.740,C_s<=81.480],[1,2,4,6,8],default=10)
    drastic = D_r*5+R_r*4+A_s*3+S_s*2+T_r*1+I_s*5+C_r*3
    results = np.sort(drastic.astype(int))
    def pct(p): return int(np.percentile(results, p))
    return {"mean":round(float(np.mean(results)),1),"std":round(float(np.std(results)),2),"min":int(results[0]),"max":int(results[-1]),"ci_90":(pct(5),pct(95)),"prob_over_140":round(float(np.mean(results>=140)*100),1)}

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
    df = pd.DataFrame({"Year":[round(t/365.25,2) for t in times],"Concentration (mg/L)":concentrations,"Distance (m)":[round(v*t,1) for t in times]})
    return {"results":df,"v_seepage":round(v,6),"D_dispersion":round(D,4),"t_travel_years":round(distance/v/365.25,3)}

def compute_basic_metrics(y_true, y_score, threshold):
    if not SKLEARN_OK: return {"error": "scikit-learn not installed"}
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
    if not SKLEARN_OK: return {"error": "scikit-learn not installed"}
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
    if not SKLEARN_OK: return {"error": "scikit-learn not installed"}
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
h1{{color:#5c2c16;border-bottom:3px solid #c19a6b;padding-bottom:10px;}}h2{{color:#5c2c16;margin-top:30px;}}
table{{width:100%;border-collapse:collapse;margin:15px 0;}}th,td{{padding:10px;border:1px solid #ddd;text-align:right;}}
th{{background-color:#f5eedc;color:#5c2c16;}}.metric{{font-size:1.5em;font-weight:bold;color:#c19a6b;}}
</style></head><body>
<h1>Risk Assessment Report</h1>
<p><b>Date:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<h2>Site Information</h2><table>
<tr><th>Site</th><td>{site_info.get('name','N/A')}</td></tr>
<tr><th>State</th><td>{site_info.get('state','N/A')}</td></tr>
<tr><th>Coordinates</th><td>{site_info.get('coords','N/A')}</td></tr>
<tr><th>Depth (D)</th><td>{site_info.get('depth','N/A')} m</td></tr>
<tr><th>Recharge (R)</th><td>{site_info.get('recharge','N/A')} mm/yr</td></tr>
<tr><th>Slope (T)</th><td>{site_info.get('slope','N/A')} %</td></tr>
<tr><th>Conductivity (C)</th><td>{site_info.get('conductivity','N/A')} m/day</td></tr>
<tr><th>CN</th><td>{site_info.get('cn','N/A')} mg/L</td></tr>
<tr><th>Hg</th><td>{site_info.get('hg','N/A')} mg/L</td></tr>
</table>
<h2>Results</h2><table>
<tr><th>DRASTIC</th><td class="metric">{drastic}/230</td></tr>
<tr><th>DRASTIC-Tox</th><td class="metric">{drastic_t}/280</td></tr>
<tr><th>Level</th><td class="metric">{level}</td></tr>
</table>
<h2>Recommendation</h2><p><b>{recommendation}</b></p>
<p style="text-align:center;color:#666;">PILOT VERSION - DRASTIC-Tox v57.8</p>
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
            if drastic_t >= 180: color, radius, level = "#d32f2f", 20, "Very High"; stats["very_high"] += 1
            elif drastic_t >= 140: color, radius, level = "#f57c00", 16, "High"; stats["high"] += 1
            elif drastic_t >= 100: color, radius, level = "#fbc02d", 12, "Medium"; stats["medium"] += 1
            else: color, radius, level = "#388e3c", 9, "Low"; stats["low"] += 1
            popup_html = f"""<div style="font-family:Arial;font-size:12px;min-width:230px;"><h4 style="color:{color};margin:0 0 8px 0;">{site_data.get('name_ar', site_key)}</h4><hr><b>State:</b> {state_name}<br><b>DRASTIC:</b> {drastic}<br><b>DRASTIC-Tox:</b> <span style="color:{color};font-weight:bold;">{drastic_t}</span><br><b>Level:</b> {level}<br><b>CN:</b> {cn} mg/L<br><b>Hg:</b> {hg} mg/L</div>"""
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
if "calibrated_weights" not in st.session_state: st.session_state["calibrated_weights"] = None
CALIBRATED_WEIGHTS = st.session_state["calibrated_weights"]

st.sidebar.markdown("""<div style="background:linear-gradient(135deg,#5c2c16,#c19a6b);padding:16px;border-radius:12px;color:white;text-align:center;margin-bottom:16px;"><div style="font-size:1.3em;font-weight:700;">Upload Files</div></div>""", unsafe_allow_html=True)

uploaded_val = st.sidebar.file_uploader("Validation:", type=["csv","xlsx"], key="uploader_validation")
uploaded_bulk = st.sidebar.file_uploader("Bulk:", type=["csv","xlsx"], key="uploader_bulk")
uploaded_extra = st.sidebar.file_uploader("Extra:", type=["csv","xlsx"], key="uploader_extra")

if uploaded_val is not None:
    try:
        df_val_side = pd.read_csv(uploaded_val) if uploaded_val.name.endswith(".csv") else pd.read_excel(uploaded_val)
        st.session_state["df_validation"] = df_val_side; st.sidebar.success(f"OK {len(df_val_side)}")
    except Exception as e: st.sidebar.error(f"ERR {str(e)[:80]}")
if uploaded_bulk is not None:
    try:
        df_bulk_side = pd.read_csv(uploaded_bulk) if uploaded_bulk.name.endswith(".csv") else pd.read_excel(uploaded_bulk)
        st.session_state["df_bulk"] = df_bulk_side; st.sidebar.success(f"OK {len(df_bulk_side)}")
    except Exception as e: st.sidebar.error(f"ERR {str(e)[:80]}")
if uploaded_extra is not None:
    try:
        df_extra_side = pd.read_csv(uploaded_extra) if uploaded_extra.name.endswith(".csv") else pd.read_excel(uploaded_extra)
        st.session_state["df_extra"] = df_extra_side; st.sidebar.info(f"OK {len(df_extra_side)}")
    except Exception as e: st.sidebar.error(f"ERR {str(e)[:80]}")

if st.sidebar.button("Clear All", key="clear_all_files_btn"):
    for k in ["df_validation","df_bulk","df_extra","df_combined"]: st.session_state.pop(k, None)
    st.rerun()

st.sidebar.markdown("---")
if DS_OK:
    st.sidebar.markdown("### Data Quality")
    st.sidebar.markdown(f"""<div class="quality-box-ok"><div style="font-size:0.85em;color:#2e7d32;">Verified: {n_sites_verified}</div></div><div class="quality-box-warn"><div style="font-size:0.85em;color:#e65100;">Display Only: {n_sites_total - n_sites_verified}</div></div>""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### Data Scope")
DATA_SCOPE = st.sidebar.radio("Scope:", ["Traditional","Industrial","All"], index=0, key="sidebar_data_scope")
if DATA_SCOPE == "Traditional": SCOPE_KEY = "traditional"
elif DATA_SCOPE == "Industrial": SCOPE_KEY = "industrial"
else: SCOPE_KEY = "all"
if SCOPE_KEY == "industrial" and not INDUSTRIAL_SITES: st.sidebar.warning("No industrial_sites.csv")

_display_weights = None
if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == SCOPE_KEY:
    _display_weights = {"ar": WEIGHTS[SCOPE_KEY]["ar"] + " (Calibrated)","alpha": CALIBRATED_WEIGHTS["alpha"],"beta": CALIBRATED_WEIGHTS["beta"],"SF": CALIBRATED_WEIGHTS["SF"],"kappa": CALIBRATED_WEIGHTS.get("kappa","-")}
else:
    _w = WEIGHTS.get(SCOPE_KEY if SCOPE_KEY != "all" else "traditional", WEIGHTS["traditional"])
    _display_weights = {"ar": _w["ar"],"alpha": _w["alpha"],"beta": _w["beta"],"SF": _w["SF"],"kappa": "-"}

_badge_cls = "mining-industrial" if SCOPE_KEY == "industrial" else "mining-mixed" if SCOPE_KEY == "mixed" else "mining-traditional"
st.sidebar.markdown(f"""<div class="mining-badge {_badge_cls}">{_display_weights['ar']}</div><div style="font-size:0.75em;color:#666;margin-top:4px;">a={_display_weights['alpha']} | b={_display_weights['beta']} | SF={_display_weights['SF']}</div>""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("## Mode")
mode_options = ["System"]
if ADV_OK: mode_options += ["Agricultural","Verification","Transport","Independent","Satellite","Dynamic"]
if MODFLOW_OK: mode_options.append("MODFLOW")
mode = st.sidebar.radio("Select:", mode_options, key="app_mode_radio")
st.sidebar.markdown("---")
st.sidebar.markdown("### Status")
status_icon = "OK" if _modflow_status in ["already_installed","installed"] else "WARN"
st.sidebar.info(f"{status_icon} MODFLOW: {_modflow_status}")
if "ci" in st.session_state: st.sidebar.success(f"Index: {st.session_state['ci']}")

st.markdown(f"""<div class="pilot-banner">PILOT VERSION</div><div class="header-container"><div class="header-title">Sudan Mining System</div><div class="header-subtitle">University of Khartoum - Faculty of Engineering</div><div class="header-subtitle">DRASTIC + DRASTIC-Tox + MODFLOW 6</div><div class="header-badge">v57.8 | {n_states} states, {n_sites_total} sites ({n_sites_verified} verified)</div></div>""", unsafe_allow_html=True)

with st.expander("Upload Area", expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        main_val = st.file_uploader("Validation:", type=["csv","xlsx"], key="main_val_uploader")
        if main_val:
            try:
                st.session_state["df_validation"] = pd.read_csv(main_val) if main_val.name.endswith(".csv") else pd.read_excel(main_val)
                st.success(f"OK {len(st.session_state['df_validation'])}")
            except Exception as e: st.error(f"ERR {str(e)[:60]}")
    with col2:
        main_bulk = st.file_uploader("Bulk:", type=["csv","xlsx"], key="main_bulk_uploader")
        if main_bulk:
            try:
                st.session_state["df_bulk"] = pd.read_csv(main_bulk) if main_bulk.name.endswith(".csv") else pd.read_excel(main_bulk)
                st.success(f"OK {len(st.session_state['df_bulk'])}")
            except Exception as e: st.error(f"ERR {str(e)[:60]}")
    with col3:
        main_extra = st.file_uploader("Extra:", type=["csv","xlsx"], key="main_extra_uploader")
        if main_extra:
            try:
                st.session_state["df_extra"] = pd.read_csv(main_extra) if main_extra.name.endswith(".csv") else pd.read_excel(main_extra)
                st.info(f"OK {len(st.session_state['df_extra'])}")
            except Exception as e: st.error(f"ERR {str(e)[:60]}")
    sample = pd.DataFrame({"site_name":["Site1","Site2"],"depth_m":[12.0,15.0],"recharge_mm":[20.0,18.0],"slope_pct":[3.0,4.0],"conductivity":[2.5,3.0],"aquifer":["massive_sandstone","sand_and_gravel"],"soil":["sand","sandy_loam"],"vadose":["sand_gravel","sandstone"],"cn_water_mg_l":[0.10,0.09],"hg_water_mg_l":[0.008,0.007],"actual_contaminated":[1,1]})
    st.download_button("Download Template", data=sample.to_csv(index=False).encode("utf-8-sig"), file_name="template.csv", mime="text/csv", key="download_template_btn")

st.markdown("---")
if mode == "System":
    tabs = st.tabs(["Input","Manual","Bulk","Solutions","Report","Heatmap","Sensitivity","Toxicity","GIS","Monte Carlo","Advanced","Development","Auto Maps","Calibration","Threshold"])

    with tabs[0]:
        st.markdown('<div class="section-header"><h3>Site Selection</h3></div>', unsafe_allow_html=True)
        if not DS_OK: st.error("data_sources.py not found")
        else:
            c1, c2 = st.columns([1, 2])
            with c1: state = st.selectbox("State:", get_states_list(), key="tab0_state_select")
            with c2:
                state_info = STATES_DATABASE[state]
                st.markdown(f'<div class="info-card" style="margin-top:28px;"><div style="font-size:0.9em;color:#5c2c16;">{state_info["description"]}<br><span style="font-size:0.85em;color:#666;">Source: {state_info["source"]}</span></div></div>', unsafe_allow_html=True)
            site_key = st.selectbox("Site:", get_sites_list(state), key="tab0_site_select")
            site_data = get_site_data(state, site_key)
            mining_type_key = site_data.get("mining_type", SCOPE_KEY if SCOPE_KEY != "all" else "traditional")
            mining_type_label = WEIGHTS.get(mining_type_key, WEIGHTS["traditional"])["ar"]
            badge_class = "mining-industrial" if mining_type_key == "industrial" else "mining-mixed" if mining_type_key == "mixed" else "mining-traditional"
            st.markdown(f'<div class="mining-badge {badge_class}">{mining_type_label}</div>', unsafe_allow_html=True)
            st.session_state["mining_type"] = mining_type_key
            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Activity", site_data.get("activity","N/A")); c2.metric("Season", site_data.get("season","N/A"))
            c3.metric("Status", "Contaminated" if site_data["actual_contaminated"] == 1 else "Clean")
            c4.metric("Verified", "Yes" if site_data.get("verified", False) else "No")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("D - Depth", f"{site_data['depth_m']} m"); st.metric("R - Recharge", f"{site_data['recharge_mm']} mm/yr")
                st.metric("T - Slope", f"{site_data['slope_pct']} %"); st.metric("C - Conductivity", f"{site_data['conductivity']} m/day")
            with c2:
                st.metric("A - Aquifer", site_data['aquifer'])
                st.metric("S - Soil", site_data['soil'])
                st.metric("I - Vadose", site_data['vadose'])
                st.metric("theta - Porosity", "0.25")
            c1, c2 = st.columns(2)
            c1.metric("CN", f"{site_data['cn_water_mg_l']} mg/L"); c2.metric("Hg", f"{site_data['hg_water_mg_l']} mg/L")
            st.caption("Limits: CN = 0.05 mg/L | Hg = 0.0007 mg/L")
            try:
                idx = calc_index(get_d_rating(site_data['depth_m']), get_r_rating(site_data['recharge_mm']), get_a_rating(site_data['aquifer']), get_s_rating(site_data['soil']), get_t_rating(site_data['slope_pct']), get_i_rating(site_data['vadose']), get_c_rating(site_data['conductivity']))
                risk = classify(idx); st.session_state["ci"] = idx
                st.session_state["cv"] = {"depth":site_data['depth_m'],"recharge":site_data['recharge_mm'],"aquifer":site_data['aquifer'],"soil":site_data['soil'],"slope":site_data['slope_pct'],"vadose":site_data['vadose'],"conductivity":site_data['conductivity'],"cn_water_mg_l":site_data['cn_water_mg_l'],"hg_water_mg_l":site_data['hg_water_mg_l']}
                z1, z2, z3 = st.columns(3)
                z1.metric("DRASTIC", f"{idx}/230"); z2.metric("Level", risk["level"]); z3.metric("Pct", f"{round(idx/230*100,1)}%")
                if risk["color"] == "red": st.error(risk['action'])
                elif risk["color"] == "orange": st.warning(risk['action'])
                elif risk["color"] == "yellow": st.info(risk['action'])
                else: st.success(risk['action'])
                if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mining_type_key:
                    dt_result = calc_drastic_t(idx, site_data['cn_water_mg_l'], site_data['hg_water_mg_l'], mining_type=mining_type_key, alpha_override=CALIBRATED_WEIGHTS["alpha"], beta_override=CALIBRATED_WEIGHTS["beta"], SF_override=CALIBRATED_WEIGHTS["SF"])
                    st.caption("Using Calibrated Weights")
                else: dt_result = calc_drastic_t(idx, site_data['cn_water_mg_l'], site_data['hg_water_mg_l'], mining_type=mining_type_key)
                st.markdown("---"); st.markdown(f"#### DRASTIC-Tox - {mining_type_label}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("DRASTIC-Tox", f"{dt_result['drastic_t']}/280", delta=f"+{dt_result['increase_pct']}%")
                m2.metric("Bonus", dt_result['toxicity_bonus']); m3.metric("alpha (CN)", dt_result['alpha']); m4.metric("beta (Hg)", dt_result['beta'])
                with st.expander("Calculation Details"):
                    d1, d2, d3, d4 = st.columns(4)
                    d1.metric("CN Score", dt_result['cn_score']); d2.metric("Hg Score", dt_result['hg_score'])
                    d3.metric("Base Bonus", dt_result['base_bonus']); d4.metric("Source Factor", dt_result['source_factor'])
                st.markdown("---")
                report_html = generate_html_report(site_info={"name":site_data.get("name_ar",site_key),"state":state,"coords":f"{site_data['coords'][0]}, {site_data['coords'][1]}","source":state_info["source"],"verified":site_data.get("verified",False),"depth":site_data['depth_m'],"recharge":site_data['recharge_mm'],"slope":site_data['slope_pct'],"conductivity":site_data['conductivity'],"cn":site_data['cn_water_mg_l'],"hg":site_data['hg_water_mg_l']}, drastic=idx, drastic_t=dt_result["drastic_t"], level=risk["level"], recommendation=risk["action"])
                st.download_button("Download Report (HTML)", data=report_html.encode("utf-8"), file_name=f"report_{site_key}.html", mime="text/html", key="download_report_btn")
            except ValueError as e: st.error(f"Error: {e}")

    with tabs[1]:
        st.markdown('<div class="section-header"><h3>Manual Entry</h3></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            new_state = st.text_input("State:", value="Sennar", key="new_state_input")
            new_site_key = st.text_input("Site Name:", value="New_Site", key="new_site_input")
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
        with c3: new_cont = st.selectbox("Status:", ["Clean (0)","Contaminated (1)"], key="new_cont_select")
        if st.button("Save", type="primary", key="save_manual_site_btn"):
            site_data = {"name_ar":new_site_key,"coords":(new_lat,new_lon),"depth_m":new_depth,"recharge_mm":new_recharge,"slope_pct":new_slope,"conductivity":new_conductivity,"aquifer":new_aquifer,"soil":new_soil,"vadose":new_vadose,"cn_water_mg_l":new_cn,"hg_water_mg_l":new_hg,"actual_contaminated":1 if new_cont == "Contaminated (1)" else 0,"season":"-","activity":"Manual","verified":True}
            add_new_site(new_state, new_site_key, site_data); st.success("Saved"); st.rerun()

    with tabs[2]:
        st.markdown('<div class="section-header"><h3>Bulk Assessment</h3></div>', unsafe_allow_html=True)
        df_bulk = get_loaded_df("df_bulk","df_validation")
        if df_bulk is None: st.warning("No file uploaded")
        else:
            try:
                st.dataframe(df_bulk.head(10), width="stretch")
                _mt_bulk = st.session_state.get("mining_type", "traditional")
                _default_th_dt_bulk = int(get_optimal_threshold(_mt_bulk))
                c1, c2 = st.columns(2)
                with c1: th_d = st.number_input("DRASTIC Threshold:", 50, 200, 100, 10, key="bulk_th_d_input")
                with c2: th_dt = st.number_input("DRASTIC-Tox Threshold:", 50, 280, _default_th_dt_bulk, 5, key="bulk_th_dt_input")
                mt_current = st.session_state.get("mining_type", "traditional")
                has_tox = "cn_water_mg_l" in df_bulk.columns and "hg_water_mg_l" in df_bulk.columns
                results, d_list, dp_list, actual_list = [], [], [], []
                for i, row in df_bulk.iterrows():
                    try:
                        ix = calc_index(get_d_rating(float(row.get("depth_m",15))), get_r_rating(float(row.get("recharge_mm",100))), get_a_rating(str(row.get("aquifer","massive_sandstone"))), get_s_rating(str(row.get("soil","sand"))), get_t_rating(float(row.get("slope_pct",4))), get_i_rating(str(row.get("vadose","sand_gravel"))), get_c_rating(float(row.get("conductivity",5))))
                        d_list.append(ix)
                        if has_tox:
                            cn_w = float(row.get("cn_water_mg_l",0.0)); hg_w = float(row.get("hg_water_mg_l",0.0))
                            if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mt_current:
                                ix_t = calc_drastic_t(ix, cn_w, hg_w, mining_type=mt_current, alpha_override=CALIBRATED_WEIGHTS["alpha"], beta_override=CALIBRATED_WEIGHTS["beta"], SF_override=CALIBRATED_WEIGHTS["SF"])["drastic_t"]
                            else: ix_t = calc_drastic_t(ix, cn_w, hg_w, mining_type=mt_current)["drastic_t"]
                        else: ix_t = ix
                        dp_list.append(ix_t)
                        if "actual_contaminated" in row: actual_list.append(int(row["actual_contaminated"]))
                        results.append({"Site":row.get("name",f"R{i+1}"),"DRASTIC":ix,"DRASTIC-Tox":ix_t,"Status":"HIGH" if ix_t >= th_dt else "LOW"})
                    except Exception: results.append({"Site":f"R{i+1}","DRASTIC":0,"DRASTIC-Tox":0,"Status":"ERR"})
                df_results = pd.DataFrame(results); st.dataframe(df_results, width="stretch")
                if has_tox and actual_list:
                    st.markdown("---")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**DRASTIC**"); md = calculate_confusion_matrix(d_list, actual_list, th_d)
                        st.metric("Kappa", md["kappa"]); st.metric("Recall", f"{md['recall']}%")
                    with c2:
                        st.markdown("**DRASTIC-Tox**"); mp = calculate_confusion_matrix(dp_list, actual_list, th_dt)
                        st.metric("Kappa", mp["kappa"]); st.metric("Recall", f"{mp['recall']}%")
                st.download_button("Download Results", data=df_results.to_csv(index=False).encode("utf-8-sig"), file_name="results.csv", mime="text/csv", key="download_bulk_results_btn")
            except Exception as e: st.error(f"Error: {e}")

    with tabs[3]:
        st.markdown('<div class="section-header"><h3>Solutions</h3></div>', unsafe_allow_html=True)
        if "ci" in st.session_state:
            ci = st.session_state["ci"]; c1, c2 = st.columns(2)
            with c1:
                h = st.checkbox("HDPE Liner", key="chk_hdpe")
                tr = st.checkbox("Cyanide Treatment", key="chk_cyanide")
            with c2:
                mo = st.checkbox("Monitoring Wells", key="chk_monitoring")
            if h or tr or mo:
                r = mitigate(ci, h, tr, mo); c1, c2, c3 = st.columns(3)
                c1.metric("Before", ci); c2.metric("After", r["mitigated_index"]); c3.metric("Reduction", f"{r['reduction_pct']}%")

    with tabs[4]:
        st.markdown('<div class="section-header"><h3>Report</h3></div>', unsafe_allow_html=True)
        if "ci" not in st.session_state: st.warning("Select a site first")
        else:
            cv = st.session_state.get("cv", {}); mt_key = st.session_state.get("mining_type","traditional")
            c1, c2, c3 = st.columns(3)
            c1.metric("DRASTIC", st.session_state["ci"]); c2.metric("CN", f"{cv.get('cn_water_mg_l','N/A')} mg/L"); c3.metric("Hg", f"{cv.get('hg_water_mg_l','N/A')} mg/L")
            st.markdown("---")
            idx = st.session_state["ci"]; cn = cv.get('cn_water_mg_l',0); hg = cv.get('hg_water_mg_l',0)
            if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mt_key:
                dt_res = calc_drastic_t(idx, cn, hg, mining_type=mt_key, alpha_override=CALIBRATED_WEIGHTS["alpha"], beta_override=CALIBRATED_WEIGHTS["beta"], SF_override=CALIBRATED_WEIGHTS["SF"])
            else: dt_res = calc_drastic_t(idx, cn, hg, mining_type=mt_key)
            summary_df = pd.DataFrame({"Metric":["DRASTIC Base","CN_score","Hg_score","Base Bonus","Source Factor","Final Bonus","DRASTIC-Tox","Level"],"Value":[idx,dt_res["cn_score"],dt_res["hg_score"],dt_res["base_bonus"],dt_res["source_factor"],dt_res["toxicity_bonus"],dt_res["drastic_t"],dt_res["level"]]})
            st.dataframe(summary_df, width="stretch", hide_index=True)

    with tabs[5]:
        st.markdown('<div class="section-header"><h3>Heatmap</h3></div>', unsafe_allow_html=True)
        if not DS_OK: st.error("data_sources.py not found")
        else:
            c1, c2 = st.columns(2)
            with c1: map_mode = st.radio("Mode:", ["Both","Markers","Heat"], key="map_mode_radio", horizontal=True)
            with c2: map_height = st.slider("Height:", 400, 900, 600, 50, key="map_height_slider")
            show_heat = map_mode in ["Both","Heat"]; show_markers = map_mode in ["Both","Markers"]
            with st.spinner("Building..."): mapa, stats, df_sites = build_heatmap_verified(show_heat=show_heat, show_markers=show_markers)
            st_folium(mapa, height=map_height, key="map_folium_v578", use_container_width=True)
            st.markdown("---")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Low", stats["low"]); c2.metric("Medium", stats["medium"]); c3.metric("High", stats["high"]); c4.metric("Very High", stats["very_high"]); c5.metric("Total", sum(stats.values()))
            st.dataframe(df_sites, width="stretch")
            st.download_button("Download Sites", data=df_sites.to_csv(index=False).encode("utf-8-sig"), file_name="verified_sites.csv", mime="text/csv", key="download_sites_btn")

    with tabs[6]:
        st.markdown('<div class="section-header"><h3>Sensitivity Analysis</h3></div>', unsafe_allow_html=True)
        if "cv" not in st.session_state: st.warning("Select a site first")
        else:
            var_pct = st.slider("Variation (%):", 5, 30, 10, 5, key="sens_var_pct_slider")
            if st.button("Run", type="primary", key="run_sens_btn"):
                with st.spinner("Calculating..."):
                    sens = sensitivity_analysis(st.session_state["cv"], var_pct/100.0); st.session_state["sens_result"] = sens
            if "sens_result" in st.session_state:
                sens = st.session_state["sens_result"]; st.success(f"Most Sensitive: {sens['most_sensitive']}")
                rows = []
                for param, data in sens["parameters"].items(): rows.append({"Param":param,"Original":data["original_phys"],"Modified":data["modified_phys"],"New Index":data["new_index"],"Change":data["change"],"Sensitivity (%)":data["sensitivity"]})
                st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    with tabs[7]:
        st.markdown('<div class="section-header"><h3>Toxicity Analysis</h3></div>', unsafe_allow_html=True)
        if "cv" not in st.session_state: st.warning("Select a site first")
        else:
            cv = st.session_state["cv"]; hgw = cv.get("hg_water_mg_l",0.011); cnw = cv.get("cn_water_mg_l",0.025)
            c1, c2 = st.columns(2); c1.metric("CN", f"{cnw} mg/L"); c2.metric("Hg", f"{hgw} mg/L")
            c1, c2 = st.columns(2)
            with c1: hgs = st.number_input("Hg in Soil (mg/kg):", 0.0, 100.0, 0.5, 0.1, key="tox_hgs_input")
            with c2: cns = st.number_input("CN in Soil (mg/kg):", 0.0, 100.0, 5.0, 0.5, key="tox_cns_input")
            if st.button("Analyze", type="primary", key="run_tox_btn"):
                mt_tox = st.session_state.get("mining_type", "traditional")
                st.session_state["tox_result"] = weighted_toxicity(hgw, hgs, cnw, cns, mining_type=mt_tox)
            if "tox_result" in st.session_state:
                tox = st.session_state["tox_result"]; st.markdown("---")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Index", tox["index"]); c2.metric("CN Score", tox["cn_score"])
                c3.metric("Hg Score", tox["hg_score"]); c4.metric("Bonus", tox["bonus"])
                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                c1.metric("Category", tox["category"]); c2.metric("Action", tox["action"]); c3.metric("Soil Factor", tox["soil_factor"])

    with tabs[8]:
        st.markdown('<div class="section-header"><h3>GIS</h3></div>', unsafe_allow_html=True)
        if not DS_OK: st.error("data_sources.py not found")
        else:
            filter_mode = st.radio("View:", ["All","Verified","Display Only"], horizontal=True, key="gis_filter_radio")
            try:
                df_all = get_all_sites_as_dataframe_with_flag()
                if filter_mode == "Verified": df_show = df_all[df_all["verified"] == True] if "verified" in df_all.columns else df_all
                elif filter_mode == "Display Only": df_show = df_all[df_all["verified"] == False] if "verified" in df_all.columns else df_all.head(0)
                else: df_show = df_all
                st.caption(f"{len(df_show)} sites"); st.dataframe(df_show, width="stretch")
                st.download_button("Download CSV", data=df_show.to_csv(index=False).encode("utf-8-sig"), file_name="sites_filtered.csv", mime="text/csv", key="download_gis_csv_btn")
            except Exception as e: st.error(f"Error: {e}")

    with tabs[9]:
        st.markdown('<div class="section-header"><h3>Monte Carlo</h3></div>', unsafe_allow_html=True)
        if "ci" in st.session_state:
            n_iter = st.slider("Iterations:", 100, 5000, 1000, 100, key="mc_n_iter_slider")
            var_pct = st.slider("Variation (%):", 5, 30, 15, 5, key="mc_var_pct_slider")
            if st.button("Run", type="primary", key="run_mc_btn"):
                mc = monte_carlo_analysis(st.session_state["cv"], n_iter, var_pct/100.0)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Mean", mc["mean"]); c2.metric("Std", mc["std"]); c3.metric("CI 90%", f"{mc['ci_90'][0]}-{mc['ci_90'][1]}"); c4.metric("P>140", f"{mc['prob_over_140']}%")

    with tabs[10]:
        st.markdown('<div class="section-header"><h3>Advanced Validation</h3></div>', unsafe_allow_html=True)
        if not SKLEARN_OK: st.error("scikit-learn not installed")
        else:
            df_val = st.session_state.get("df_validation")
            if df_val is None: st.warning("Upload validation file")
            else:
                has_tox = "cn_water_mg_l" in df_val.columns and "hg_water_mg_l" in df_val.columns
                if not has_tox: st.error("File missing CN or Hg")
                else:
                    mt_adv = st.session_state.get("mining_type", "traditional")
                    _default_th_dt_adv = int(get_optimal_threshold(mt_adv))
                    c1, c2 = st.columns(2)
                    with c1: th_d_adv = st.number_input("DRASTIC:", 50, 200, 100, 10, key="adv_th_d_input")
                    with c2: th_dt_adv = st.number_input("DRASTIC-Tox:", 50, 280, _default_th_dt_adv, 5, key="adv_th_dt_input")
                    d_list_adv, dp_list_adv, actual_list_adv = [], [], []
                    for i, row in df_val.iterrows():
                        try:
                            ix = calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])), get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])), get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])), get_c_rating(float(row["conductivity"])))
                            d_list_adv.append(ix); cn_w = float(row.get("cn_water_mg_l",0.0)); hg_w = float(row.get("hg_water_mg_l",0.0))
                            if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mt_adv:
                                dp_list_adv.append(calc_drastic_t(ix, cn_w, hg_w, mining_type=mt_adv, alpha_override=CALIBRATED_WEIGHTS["alpha"], beta_override=CALIBRATED_WEIGHTS["beta"], SF_override=CALIBRATED_WEIGHTS["SF"])["drastic_t"])
                            else: dp_list_adv.append(calc_drastic_t(ix, cn_w, hg_w, mining_type=mt_adv)["drastic_t"])
                            actual_list_adv.append(int(row["actual_contaminated"]))
                        except Exception: pass
                    if not d_list_adv: st.error("No valid data")
                    else:
                        if st.button("Run Advanced", type="primary", key="run_adv_btn"):
                            with st.spinner("Calculating..."):
                                m_d = compute_basic_metrics(actual_list_adv, d_list_adv, th_d_adv); b_d = bootstrap_kappa_ci(actual_list_adv, d_list_adv, th_d_adv, n_boot=1000); l_d = loocv_analysis(actual_list_adv, d_list_adv, th_d_adv)
                                m_dt = compute_basic_metrics(actual_list_adv, dp_list_adv, th_dt_adv); b_dt = bootstrap_kappa_ci(actual_list_adv, dp_list_adv, th_dt_adv, n_boot=1000); l_dt = loocv_analysis(actual_list_adv, dp_list_adv, th_dt_adv)
                                st.session_state["adv_results"] = {"m_d":m_d,"b_d":b_d,"l_d":l_d,"m_dt":m_dt,"b_dt":b_dt,"l_dt":l_dt}
                        if "adv_results" in st.session_state:
                            r = st.session_state["adv_results"]; st.markdown("---"); c1, c2 = st.columns(2)
                            with c1:
                                st.markdown("#### DRASTIC")
                                if "error" not in r["m_d"]:
                                    st.metric("Kappa", r["m_d"]["kappa"]); st.metric("ROC-AUC", r["m_d"]["auc"]); st.metric("F1", r["m_d"]["f1"]); st.metric("Recall", f"{r['m_d']['recall']}%")
                                    with st.expander("CM"): st.write(f"TP={r['m_d']['tp']} TN={r['m_d']['tn']} FP={r['m_d']['fp']} FN={r['m_d']['fn']}")
                                    with st.expander("Bootstrap"): st.write(f"CI: [{r['b_d']['ci_low']}, {r['b_d']['ci_high']}]")
                                    with st.expander("LOOCV"): st.write(f"Kappa={r['l_d']['kappa']} Acc={r['l_d']['accuracy']}%")
                            with c2:
                                st.markdown("#### DRASTIC-Tox")
                                if "error" not in r["m_dt"]:
                                    st.metric("Kappa", r["m_dt"]["kappa"]); st.metric("ROC-AUC", r["m_dt"]["auc"]); st.metric("F1", r["m_dt"]["f1"]); st.metric("Recall", f"{r['m_dt']['recall']}%")
                                    with st.expander("CM"): st.write(f"TP={r['m_dt']['tp']} TN={r['m_dt']['tn']} FP={r['m_dt']['fp']} FN={r['m_dt']['fn']}")
                                    with st.expander("Bootstrap"): st.write(f"CI: [{r['b_dt']['ci_low']}, {r['b_dt']['ci_high']}]")
                                    with st.expander("LOOCV"): st.write(f"Kappa={r['l_dt']['kappa']} Acc={r['l_dt']['accuracy']}%")

    with tabs[11]:
        st.markdown('<div class="section-header"><h3>Model Development</h3></div>', unsafe_allow_html=True)
        if not DEV_OK: st.error("model_development.py not found")
        elif not SKLEARN_OK: st.error("scikit-learn not installed")
        else:
            sub_tabs = st.tabs(["Gray Zone","Calibration","Comparison"])
            with sub_tabs[0]:
                st.markdown("#### Gray Zone Sites")
                gray_rows = []
                for state_name, state_data in GRAY_ZONE_SITES.items():
                    for site_key, site_data in state_data.get("sites", {}).items():
                        gray_rows.append({"Site":site_data.get("name_ar",site_key),"D":site_data["depth_m"],"R":site_data["recharge_mm"],"CN":site_data["cn_water_mg_l"],"Hg":site_data["hg_water_mg_l"],"Status":"Cont" if site_data["actual_contaminated"] == 1 else "Clean"})
                st.dataframe(pd.DataFrame(gray_rows), width="stretch", hide_index=True)
                st.markdown("---")
                merge_option = st.radio("Choose:", ["Verified only","Verified + Gray"], key="gray_merge_radio")
                include_gray = "Gray" in merge_option
                if st.button("Load Data", type="primary", key="load_combined_btn"):
                    df_combined = get_combined_dataset(include_gray=include_gray); drastic_vals, dt_vals = [], []
                    for _, row in df_combined.iterrows():
                        try:
                            ix = calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])), get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])), get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])), get_c_rating(float(row["conductivity"])))
                            dt = calc_drastic_t(ix, float(row["cn_water_mg_l"]), float(row["hg_water_mg_l"]), mining_type="traditional")["drastic_t"]
                            drastic_vals.append(ix); dt_vals.append(dt)
                        except Exception: drastic_vals.append(0); dt_vals.append(0)
                    df_combined = df_combined.copy(); df_combined["DRASTIC"] = drastic_vals; df_combined["DRASTIC_Tox"] = dt_vals
                    st.session_state["df_combined"] = df_combined; st.success(f"Loaded {len(df_combined)}"); st.rerun()
                if "df_combined" in st.session_state:
                    df_saved = st.session_state["df_combined"]; st.markdown("---"); st.dataframe(df_saved, width="stretch")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total", len(df_saved)); c2.metric("Verified", safe_sum(df_saved, "verified", 0)); c3.metric("Gray", safe_sum(df_saved, "is_gray_zone", 0)); c4.metric("Contam", safe_sum(df_saved, "actual_contaminated", 0))
            with sub_tabs[1]:
                st.markdown("#### Calibration alpha beta")
                df_cal = get_loaded_df("df_combined", "df_validation")
                if df_cal is None: st.warning("Load data first")
                else:
                    if "DRASTIC" not in df_cal.columns:
                        drastic_vals = []
                        for _, row in df_cal.iterrows():
                            try: drastic_vals.append(calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])), get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])), get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])), get_c_rating(float(row["conductivity"]))))
                            except Exception: drastic_vals.append(0)
                        df_cal = df_cal.copy(); df_cal["DRASTIC"] = drastic_vals; st.session_state["df_combined"] = df_cal
                    c1, c2 = st.columns(2)
                    with c1:
                        a_min = st.slider("alpha min:", 0.0, 1.0, 0.1, 0.1, key="cal_a_min_slider"); a_max = st.slider("alpha max:", 0.0, 1.0, 0.9, 0.1, key="cal_a_max_slider")
                    with c2:
                        b_min = st.slider("beta min:", 0.0, 1.0, 0.1, 0.1, key="cal_b_min_slider"); b_max = st.slider("beta max:", 0.0, 1.0, 0.9, 0.1, key="cal_b_max_slider")
                    if st.button("Run Calibration", type="primary", key="run_cal_btn"):
                        with st.spinner("Searching..."):
                            alpha_range = list(np.arange(a_min, a_max + 0.05, 0.1)); beta_range = list(np.arange(b_min, b_max + 0.05, 0.1))
                            st.session_state["cal_result"] = calibrate_alpha_beta(df_cal, {"DRASTIC":100,"DRASTIC-T":140}, alpha_range=alpha_range, beta_range=beta_range)
                    if "cal_result" in st.session_state:
                        res = st.session_state["cal_result"]
                        if "error" in res: st.error(res["error"])
                        else:
                            c1, c2 = st.columns(2)
                            with c1:
                                st.markdown("#### Best Kappa"); bk = res["best_kappa"]
                                st.metric("alpha", bk["alpha"]); st.metric("beta", bk["beta"]); st.metric("Kappa", bk["kappa"]); st.metric("Recall", f"{bk['recall']}%")
                            with c2:
                                st.markdown("#### Balanced"); bb = res["best_balanced"]
                                st.metric("alpha", bb["alpha"]); st.metric("beta", bb["beta"]); st.metric("Kappa", bb["kappa"]); st.metric("Recall", f"{bb['recall']}%")
            with sub_tabs[2]:
                st.markdown("#### Compare Models")
                df_cmp = get_loaded_df("df_combined", "df_validation")
                if df_cmp is None: st.warning("Load data first")
                else:
                    if st.button("Run Comparison", type="primary", key="run_cmp_btn"):
                        with st.spinner("Calculating..."): st.session_state["cmp_results"] = compare_models(df_cmp, (get_d_rating,get_r_rating,get_a_rating,get_s_rating,get_t_rating,get_i_rating,get_c_rating), calc_index)
                    if "cmp_results" in st.session_state:
                        r = st.session_state["cmp_results"]; summary_rows = []
                        for model_name, metrics in r.items():
                            if "error" not in metrics: summary_rows.append({"Model":model_name,"Kappa":metrics["kappa"],"Recall":metrics["recall"],"Precision":metrics["precision"],"Accuracy":metrics["accuracy"],"ROC-AUC":metrics["auc"]})
                        st.dataframe(pd.DataFrame(summary_rows), width="stretch", hide_index=True)

    with tabs[12]:
        st.markdown('<div class="section-header"><h3>Auto Maps</h3></div>', unsafe_allow_html=True)
        if not MAPS_OK: st.error("auto_maps.py not found")
        else:
            df_source = get_loaded_df("df_combined","df_validation")
            if df_source is None: st.warning("No data loaded")
            else:
                st.write(f"Sites: {len(df_source)}")
                if st.button("Generate Maps", type="primary", key="gen_maps_btn"):
                    with st.spinner("Generating..."):
                        try:
                            df_maps = df_source.copy()
                            if "coords" in df_maps.columns and "lon" not in df_maps.columns:
                                df_maps["lat"] = df_maps["coords"].apply(lambda c: c[0] if isinstance(c, (tuple, list)) and len(c) >= 2 else None)
                                df_maps["lon"] = df_maps["coords"].apply(lambda c: c[1] if isinstance(c, (tuple, list)) and len(c) >= 2 else None)
                            if "lon" not in df_maps.columns: st.error("No coordinates"); st.stop()
                            if "DRASTIC" not in df_maps.columns:
                                dv = []
                                for _, row in df_maps.iterrows():
                                    try: dv.append(calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])), get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])), get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])), get_c_rating(float(row["conductivity"]))))
                                    except Exception: dv.append(0)
                                df_maps["DRASTIC"] = dv
                            if "DRASTIC_Tox" not in df_maps.columns:
                                dtv = []
                                for _, row in df_maps.iterrows():
                                    try:
                                        ix = calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])), get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])), get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])), get_c_rating(float(row["conductivity"])))
                                        dtv.append(calc_drastic_t(ix, float(row.get("cn_water_mg_l",0)), float(row.get("hg_water_mg_l",0)), mining_type="traditional")["drastic_t"])
                                    except Exception: dtv.append(0)
                                df_maps["DRASTIC_Tox"] = dtv
                            rename_map = {}
                            if "cn_water_mg_l" in df_maps.columns: rename_map["cn_water_mg_l"] = "CN"
                            if "hg_water_mg_l" in df_maps.columns: rename_map["hg_water_mg_l"] = "Hg"
                            if rename_map: df_maps = df_maps.rename(columns=rename_map)
                            df_prepared = prepare_df_for_maps(df_maps, (get_d_rating,get_r_rating,get_a_rating,get_s_rating,get_t_rating,get_i_rating,get_c_rating))
                            fig = generate_auto_maps(df_prepared, show_sudan=True)
                            st.session_state["auto_maps_fig"] = fig; st.success(f"Generated: {len(df_prepared)}")
                        except Exception as e: st.error(f"Error: {e}")
                if "auto_maps_fig" in st.session_state:
                    st.plotly_chart(st.session_state["auto_maps_fig"], use_container_width=True, key="auto_maps_chart_v578")
                    html_str = st.session_state["auto_maps_fig"].to_html(include_plotlyjs='cdn')
                    st.download_button("Download Maps", data=html_str.encode("utf-8"), file_name="auto_maps.html", mime="text/html", key="download_maps_html_btn")

    with tabs[13]:
        st.markdown('<div class="section-header"><h3>Automatic Weight Calibration</h3></div>', unsafe_allow_html=True)
        st.markdown("""<div class="research-note"><b>References:</b><br>Konate et al. (2025)<br>Karan et al. (2018)<br>Landis &amp; Koch (1977)</div>""", unsafe_allow_html=True)
        if not AUTOCAL_OK: st.error("auto_calibration.py not found")
        elif not SKLEARN_OK: st.error("scikit-learn not installed")
        else:
            if SCOPE_KEY == "industrial" and INDUSTRIAL_SITES:
                df_cal_auto = pd.DataFrame(INDUSTRIAL_SITES)
            else:
                df_cal_auto = get_loaded_df("df_validation","df_bulk","df_combined")
            if df_cal_auto is None: st.warning("Upload validation file")
            else:
                required_cols = ["depth_m","recharge_mm","slope_pct","conductivity","aquifer","soil","vadose","cn_water_mg_l","hg_water_mg_l","actual_contaminated"]
                missing = [c for c in required_cols if c not in df_cal_auto.columns]
                if missing: st.error(f"Missing columns: {missing}")
                else:
                    st.success(f"File has {len(df_cal_auto)} sites")
                    c1, c2, c3 = st.columns(3)
                    with c1: mt_choice = st.selectbox("Mining Type:", ["traditional","industrial","mixed"], key="cal_mining_type_select")
                    with c2: n_steps = st.slider("Search Steps:", 10, 30, 15, 5, key="cal_n_steps_slider")
                    with c3: threshold = st.number_input("DRASTIC-Tox Threshold:", 50, 280, 140, 10, key="cal_threshold_input")
                    n_combos = n_steps ** 3; st.caption(f"Combinations: {n_combos:,}")
                    st.markdown("---")
                    b1, b2, b3 = st.columns(3)
                    with b1: run_cal = st.button("Run Calibration", type="primary", key="run_auto_cal_btn", use_container_width=True)
                    with b2: run_cmp = st.button("Compare", key="run_compare_btn", use_container_width=True)
                    with b3: reset = st.button("Reset", key="reset_weights_btn", use_container_width=True)
                    if reset:
                        st.session_state["calibrated_weights"] = None; st.session_state.pop("auto_cal_result", None); st.session_state.pop("auto_cal_mining_type", None); st.session_state.pop("comparison_result", None)
                        st.success("Reset done"); st.rerun()
                    if run_cmp:
                        with st.spinner("Calculating..."): comparison = compare_with_defaults(df_cal_auto, mt_choice, threshold=threshold)
                        if "error" in comparison: st.error(f"Error: {comparison['error']}")
                        else: st.session_state["comparison_result"] = comparison
                    if run_cal:
                        with st.spinner(f"Searching {n_combos:,} combos..."): result = auto_calibrate_weights(df_cal_auto, mt_choice, n_steps=n_steps, threshold=threshold)
                        if "error" in result: st.error(f"Error: {result['error']}")
                        else:
                            st.session_state["auto_cal_result"] = result; st.session_state["auto_cal_mining_type"] = mt_choice
                            st.session_state["calibrated_weights"] = apply_calibration(result, mt_choice)
                            st.success(f"Kappa = {result['best_kappa']}"); st.rerun()
                    if "comparison_result" in st.session_state:
                        cmp = st.session_state["comparison_result"]; st.markdown("---")
                        col1, col2, col3 = st.columns(3)
                        with col1: st.metric("Default Kappa", cmp["default_kappa"])
                        with col2: st.metric("Calibrated Kappa", cmp["best_kappa"] or "-", delta=f"{cmp.get('improvement', 0):+.4f}" if cmp.get("best_kappa") else None)
                        with col3: st.metric("Recall", f"{cmp.get('best_recall', 0)}%")
                    if "auto_cal_result" in st.session_state:
                        res = st.session_state["auto_cal_result"]; mt_saved = st.session_state.get("auto_cal_mining_type","traditional"); interp = res.get("kappa_interpretation", {})
                        st.markdown("---"); st.markdown(f"### Result - {WEIGHTS[mt_saved]['ar']}")
                        kappa_class = "kappa-excellent" if interp.get("level") == "ممتاز" else "kappa-good" if interp.get("level") == "جيد" else "kappa-moderate" if interp.get("level") == "متوسط" else "kappa-fair" if interp.get("level") == "مقبول" else "kappa-poor"
                        st.markdown(f'<div class="kappa-box {kappa_class}"><div style="font-size:0.9em;opacity:0.9;">Kappa</div><div style="font-size:3em;font-weight:700;margin:8px 0;">{res["best_kappa"]}</div><div style="font-size:1.3em;font-weight:600;">{interp.get("level", "-")} - {interp.get("en", "-")}</div></div>', unsafe_allow_html=True)
                        st.markdown("#### Optimal Weights"); c1, c2, c3, c4 = st.columns(4)
                        with c1: st.markdown(f'<div class="cal-result-card"><div class="cal-result-label">alpha (CN)</div><div class="cal-result-value">{res["best_alpha"]}</div></div>', unsafe_allow_html=True)
                        with c2: st.markdown(f'<div class="cal-result-card"><div class="cal-result-label">beta (Hg)</div><div class="cal-result-value">{res["best_beta"]}</div></div>', unsafe_allow_html=True)
                        with c3: st.markdown(f'<div class="cal-result-card"><div class="cal-result-label">SF</div><div class="cal-result-value">{res["best_SF"]}</div></div>', unsafe_allow_html=True)
                        with c4: st.markdown(f'<div class="cal-result-card"><div class="cal-result-label">Recall</div><div class="cal-result-value">{res["best_recall"]}%</div></div>', unsafe_allow_html=True)
                        st.markdown("---"); st.markdown("#### Top 10 Combinations")
                        top_results = res.get("all_results", [])[:10]
                        if top_results:
                            df_top = pd.DataFrame(top_results); df_top = df_top.rename(columns={"alpha":"alpha (CN)","beta":"beta (Hg)","SF":"SF","kappa":"Kappa","recall":"Recall %"})
                            df_top.insert(0, "Rank", range(1, len(df_top) + 1)); st.dataframe(df_top, width="stretch", hide_index=True)
                        st.markdown("---"); st.warning("Weights calibrated on current data only.")

    with tabs[14]:
        st.markdown('<div class="section-header"><h3>Optimal Threshold (Youden Index)</h3></div>', unsafe_allow_html=True)
        st.markdown("""<div class="research-note"><b>References:</b><br>Youden (1950) Cancer 3(1):32-35<br>Landis &amp; Koch (1977)<br>Baddeley et al. (2020)</div>""", unsafe_allow_html=True)
        st.info("1) Compute DRASTIC-Tox 2) Plot ROC 3) Find max J = Sensitivity + Specificity - 1 4) Suggest optimal threshold")
        if not AUTOCAL_OK: st.error("auto_calibration.py not found")
        elif not SKLEARN_OK: st.error("scikit-learn not installed")
        else:
            if SCOPE_KEY == "industrial" and INDUSTRIAL_SITES:
                df_opt = pd.DataFrame(INDUSTRIAL_SITES)
            else:
                df_opt = get_loaded_df("df_validation","df_combined")
            if df_opt is None: st.warning("Upload validation file")
            else:
                mt_choice_opt = st.selectbox("Mining Type:", ["traditional","industrial","mixed"], key="opt_mining_type_select")
                use_calibrated = False
                if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mt_choice_opt:
                    use_calibrated = st.checkbox(f"Use calibrated weights (Kappa = {CALIBRATED_WEIGHTS.get('kappa', '-')})", value=True, key="use_calibrated_for_opt_chk")
                if st.button("Compute Optimal Threshold", type="primary", key="run_opt_threshold_btn"):
                    with st.spinner("Calculating..."):
                        try:
                            if use_calibrated and CALIBRATED_WEIGHTS:
                                opt_result = find_optimal_threshold(df_opt, mt_choice_opt, alpha=CALIBRATED_WEIGHTS["alpha"], beta=CALIBRATED_WEIGHTS["beta"], SF=CALIBRATED_WEIGHTS["SF"])
                            else: opt_result = find_optimal_threshold(df_opt, mt_choice_opt)
                            st.session_state["opt_threshold_result"] = opt_result
                        except Exception as e: st.error(f"Error: {e}")
                if "opt_threshold_result" in st.session_state:
                    res = st.session_state["opt_threshold_result"]
                    if "error" in res: st.error(f"Error: {res['error']}")
                    else:
                        st.markdown("---"); st.markdown(f"### Optimal Threshold - {WEIGHTS[res['mining_type']]['ar']}")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1: st.markdown(f'<div class="cal-result-card" style="background:linear-gradient(135deg,#e8f5e9,#c8e6c9);"><div class="cal-result-label">Threshold</div><div class="cal-result-value">{res["optimal_threshold"]}</div><div class="cal-result-label">Youden Index</div></div>', unsafe_allow_html=True)
                        with col2: st.markdown(f'<div class="cal-result-card"><div class="cal-result-label">J</div><div class="cal-result-value">{res["J_max"]}</div></div>', unsafe_allow_html=True)
                        with col3: st.markdown(f'<div class="cal-result-card"><div class="cal-result-label">Sensitivity</div><div class="cal-result-value">{res["sensitivity"]}</div></div>', unsafe_allow_html=True)
                        with col4: st.markdown(f'<div class="cal-result-card"><div class="cal-result-label">Specificity</div><div class="cal-result-value">{res["specificity"]}</div></div>', unsafe_allow_html=True)
                        st.markdown("---"); st.markdown("#### Comparison with Default Threshold (140)")
                        cmp_df = pd.DataFrame({"Metric":["Threshold","Youden J","Sensitivity","Specificity"],"Default (140)":[res["default_threshold"],res["default_J"],res["default_sensitivity"],res["default_specificity"]],"Optimal":[res["optimal_threshold"],res["J_max"],res["sensitivity"],res["specificity"]]})
                        st.dataframe(cmp_df, width="stretch", hide_index=True)
                        improvement = res["J_max"] - res["default_J"]
                        if improvement > 0.2: st.success(f"Excellent improvement: +{improvement:.3f}")
                        elif improvement > 0.05: st.info(f"Good improvement: +{improvement:.3f}")
                        elif improvement > 0: st.warning(f"Minor improvement: +{improvement:.3f}")
                        else: st.error(f"Default better by {abs(improvement):.3f}")
                        st.markdown("---"); st.markdown("#### ROC Curve")
                        try:
                            import plotly.graph_objects as go
                            roc = res["roc_data"]; fprs = [p["fpr"] for p in roc]; tprs = [p["tpr"] for p in roc]
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=[0,1], y=[0,1], mode='lines', line=dict(color='gray', dash='dash'), name='Random'))
                            fig.add_trace(go.Scatter(x=fprs, y=tprs, mode='lines+markers', line=dict(color='#5c2c16', width=2), marker=dict(size=4), name='DRASTIC-Tox ROC'))
                            fig.add_trace(go.Scatter(x=[1-res["specificity"]], y=[res["sensitivity"]], mode='markers', marker=dict(size=18, color='red', symbol='star'), name=f"Threshold ({res['optimal_threshold']})"))
                            fig.update_layout(title=f"ROC - {WEIGHTS[res['mining_type']]['ar']}", xaxis_title="FPR", yaxis_title="TPR", height=500)
                            st.plotly_chart(fig, use_container_width=True, key="roc_chart_v578")
                        except Exception as e: st.warning(f"ROC plot failed: {e}")
                        st.markdown("---"); st.warning(f"n = {res['n_sites']} | Optimal: {res['optimal_threshold']} | Ref: Youden (1950)")
                        if st.button("Apply This Threshold", type="primary", key="apply_opt_threshold_btn"):
                            st.session_state["custom_threshold"] = res["optimal_threshold"]; st.success(f"Applied: {res['optimal_threshold']}")

elif mode == "Agricultural" and ADV_OK:
    st.markdown("""<div class="header-container header-agri"><div class="header-title">Agricultural Sector</div><div class="header-subtitle">DRASTIC-Agri + SAR + Na% + EC</div></div>""", unsafe_allow_html=True)
    if DS_OK:
        try:
            agri_summary = get_agricultural_data_summary(); st.info(f"{agri_summary['total_states']} states, {agri_summary['total_sites']} sites")
            c1, c2 = st.columns([1, 2])
            with c1: agri_state = st.selectbox("State:", get_agri_states_list(), key="agri_state_select")
            with c2: st.markdown(f'<div class="info-card" style="margin-top:28px;">{AGRICULTURAL_DATA[agri_state]["description"]}</div>', unsafe_allow_html=True)
            agri_site_key = st.selectbox("Site:", get_agri_sites_list(agri_state), key="agri_site_select")
            agri_data = get_agri_site_data(agri_state, agri_site_key)
            st.markdown("---"); c1, c2, c3 = st.columns(3)
            c1.metric("Crop", agri_data.get("crop_type","N/A")); c2.metric("Irrigation", agri_data.get("irrigation_method","N/A")); c3.metric("EC", f"{agri_data['ec_ds_m']} dS/m")
            sar = calculate_sar(agri_data['na_meq_l'], agri_data['ca_meq_l'], agri_data['mg_meq_l'])
            na_pct = calculate_na_percent(agri_data['na_meq_l'], agri_data['ca_meq_l'], agri_data['mg_meq_l'], agri_data['k_meq_l'])
            ec_res = calculate_ec_quality(agri_data['ec_ds_m']); overall = classify_irrigation_water(sar, na_pct, ec_res)
            st.markdown("---"); c1, c2, c3 = st.columns(3)
            c1.metric("SAR", sar.get("sar","N/A")); c2.metric("Na%", f"{na_pct.get('na_percent','N/A')}%"); c3.metric("EC", ec_res.get("ec","N/A"))
            st.markdown("---"); c1, c2, c3 = st.columns(3)
            c1.metric("Class", overall.get("class","N/A")); c2.metric("Level", overall.get("level","N/A")); c3.metric("Action", overall.get("action","N/A"))
        except Exception as e: st.error(f"Error: {e}")

elif mode == "Verification" and ADV_OK:
    st.markdown('<div class="section-header"><h3>Field Verification</h3></div>', unsafe_allow_html=True)
    if DS_OK:
        c1, c2 = st.columns([3, 1])
        with c2:
            if st.button("Load Verified", type="primary", key="load_verified_sites_btn"):
                try:
                    df_ver = get_verified_sites_as_dataframe(); st.session_state["df_validation"] = df_ver; st.success(f"Loaded {len(df_ver)}"); st.rerun()
                except Exception as e: st.error(f"Error: {e}")
        with c1: st.info(f"{n_sites_verified} verified sites")
    df_val = st.session_state.get("df_validation")
    if df_val is None: st.warning("No file uploaded")
    else:
        try:
            st.dataframe(df_val.head(10), width="stretch")
            has_tox = "cn_water_mg_l" in df_val.columns and "hg_water_mg_l" in df_val.columns
            if not has_tox: st.error("File missing CN or Hg")
            else:
                c1, c2 = st.columns(2)
                with c1: th_d = st.number_input("DRASTIC:", 50, 200, 100, 10, key="verify_th_d_input")
                with c2: th_dt = st.number_input("DRASTIC-Tox:", 50, 280, 140, 10, key="verify_th_dt_input")
                mt_v = st.session_state.get("mining_type", "traditional")
                d_list, dp_list, actual_list = [], [], []
                for i, row in df_val.iterrows():
                    try:
                        ix = calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])), get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])), get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])), get_c_rating(float(row["conductivity"])))
                        d_list.append(ix); cn_w = float(row.get("cn_water_mg_l",0.0)); hg_w = float(row.get("hg_water_mg_l",0.0))
                        if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mt_v:
                            dp_list.append(calc_drastic_t(ix, cn_w, hg_w, mining_type=mt_v, alpha_override=CALIBRATED_WEIGHTS["alpha"], beta_override=CALIBRATED_WEIGHTS["beta"], SF_override=CALIBRATED_WEIGHTS["SF"])["drastic_t"])
                        else: dp_list.append(calc_drastic_t(ix, cn_w, hg_w, mining_type=mt_v)["drastic_t"])
                        actual_list.append(int(row["actual_contaminated"]))
                    except Exception: pass
                st.markdown("---"); c1, c2 = st.columns(2)
                with c1:
                    st.markdown("#### DRASTIC"); md = calculate_confusion_matrix(d_list, actual_list, th_d)
                    st.metric("Kappa", md["kappa"]); st.metric("Recall", f"{md['recall']}%"); st.metric("Accuracy", f"{md.get('accuracy', 'N/A')}%")
                with c2:
                    st.markdown("#### DRASTIC-Tox"); mp = calculate_confusion_matrix(dp_list, actual_list, th_dt)
                    st.metric("Kappa", mp["kappa"]); st.metric("Recall", f"{mp['recall']}%"); st.metric("Accuracy", f"{mp.get('accuracy', 'N/A')}%")
        except Exception as e: st.error(f"Error: {e}")

elif mode == "Transport" and ADV_OK:
    st.markdown('<div class="section-header"><h3>Contaminant Transport (Ogata-Banks)</h3></div>', unsafe_allow_html=True)
    if "cv" not in st.session_state: st.warning("Open System mode first")
    else:
        cv = st.session_state["cv"]; c1, c2 = st.columns(2)
        with c1:
            init_conc = st.number_input("Initial Concentration:", 0.001, 10.0, 0.10, 0.001, format="%.4f", key="trans_init_conc")
            distance = st.number_input("Distance (m):", 10.0, 5000.0, 500.0, 50.0, key="trans_distance")
        with c2:
            gradient = st.number_input("Gradient:", 0.0001, 0.5, 0.01, 0.0001, format="%.4f", key="trans_gradient")
            years = st.slider("Years:", 1, 30, 10, 1, key="trans_years")
        porosity = st.slider("Porosity:", 0.02, 0.55, 0.25, 0.01, key="trans_porosity")
        k_val = st.number_input("K (m/day):", 0.01, 500.0, float(cv.get("conductivity", 3.5)), 0.1, key="trans_k_val")
        dispersivity = st.number_input("Dispersivity:", 0.1, 100.0, 10.0, 0.5, key="trans_disper")
        if st.button("Run", type="primary", key="run_transport_btn"):
            st.session_state["transport_result"] = model_contaminant_transport_fixed(init_conc, k_val, porosity, gradient, distance, years, dispersivity)
        if "transport_result" in st.session_state:
            tr = st.session_state["transport_result"]
            if "error" in tr: st.error(f"Error: {tr['error']}")
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Seepage Velocity", f"{tr['v_seepage']:.6f} m/d"); c2.metric("Dispersion", f"{tr['D_dispersion']} m2/d"); c3.metric("Travel Time", f"{tr['t_travel_years']} yr")
                st.dataframe(tr["results"], width="stretch"); st.line_chart(tr["results"].set_index("Year")["Concentration (mg/L)"])

elif mode == "Independent" and ADV_OK:
    st.markdown('<div class="section-header"><h3>Independent Validation (70/30)</h3></div>', unsafe_allow_html=True)
    df_val = st.session_state.get("df_validation")
    if df_val is None: st.warning("Upload validation file")
    else:
        try:
            required = ["depth_m","recharge_mm","slope_pct","conductivity","aquifer","soil","vadose","actual_contaminated"]
            missing = [c for c in required if c not in df_val.columns]
            if missing: st.error(f"Missing columns: {missing}")
            else:
                if st.button("Run", type="primary", key="run_ind_val_btn"):
                    with st.spinner("Validating..."):
                        try:
                            df_ind = df_val.copy()
                            if "DRASTIC" not in df_ind.columns:
                                drastic_vals = []
                                for _, row in df_ind.iterrows():
                                    try: drastic_vals.append(calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])), get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])), get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])), get_c_rating(float(row["conductivity"]))))
                                    except Exception: drastic_vals.append(0)
                                df_ind["DRASTIC"] = drastic_vals
                            if "DRASTIC_Tox" not in df_ind.columns and "cn_water_mg_l" in df_ind.columns and "hg_water_mg_l" in df_ind.columns:
                                dt_vals = []; mt_ind = st.session_state.get("mining_type", "traditional")
                                for _, row in df_ind.iterrows():
                                    try:
                                        ix = calc_index(get_d_rating(float(row["depth_m"])), get_r_rating(float(row["recharge_mm"])), get_a_rating(str(row["aquifer"])), get_s_rating(str(row["soil"])), get_t_rating(float(row["slope_pct"])), get_i_rating(str(row["vadose"])), get_c_rating(float(row["conductivity"])))
                                        dt_vals.append(calc_drastic_t(ix, float(row.get("cn_water_mg_l",0)), float(row.get("hg_water_mg_l",0)), mining_type=mt_ind)["drastic_t"])
                                    except Exception: dt_vals.append(0)
                                df_ind["DRASTIC_Tox"] = dt_vals
                            st.session_state["ind_val_result"] = independent_validation(df_ind, "DRASTIC", "actual_contaminated", test_size=0.3)
                        except Exception as e: st.error(f"Error: {e}")
                if "ind_val_result" in st.session_state:
                    r = st.session_state["ind_val_result"]
                    if "error" in r: st.error(r["error"])
                    else:
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Best alpha", r.get("best_alpha","N/A")); c2.metric("Best beta", r.get("best_beta","N/A")); c3.metric("Train Kappa", r.get("train_kappa","N/A")); c4.metric("Test Kappa", r.get("test_kappa","N/A"))
        except Exception as e: st.error(f"Error: {e}")

elif mode == "Satellite" and ADV_OK:
    st.markdown('<div class="section-header"><h3>Satellite Data (ERA5)</h3></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: lat = st.number_input("Latitude:", -90.0, 90.0, 13.55, 0.01, format="%.4f", key="sat_lat_input")
    with c2: lon = st.number_input("Longitude:", -180.0, 180.0, 33.60, 0.01, format="%.4f", key="sat_lon_input")
    years = st.slider("Years:", 1, 10, 3, 1, key="sat_years_slider")
    if st.button("Fetch Data", type="primary", key="fetch_sat_btn"):
        with st.spinner("Fetching..."):
            try: st.session_state["sat_result"] = fetch_satellite_data(lat, lon, years)
            except Exception as e: st.error(f"Error: {e}")
    if "sat_result" in st.session_state:
        s = st.session_state["sat_result"]
        if s.get("rainfall_mm") is not None:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Rainfall", f"{s['rainfall_mm']} mm"); c2.metric("Temp", f"{s['temperature_c']} C"); c3.metric("Climate", s["aridity"]); c4.metric("NDVI", s["ndvi_estimated"])
            st.caption(f"Source: {s['source']}")
        else: st.error(f"Failed: {s.get('source', '')}")

elif mode == "Dynamic" and ADV_OK:
    st.markdown('<div class="section-header"><h3>Dynamic Assessment</h3></div>', unsafe_allow_html=True)
    if "ci" not in st.session_state: st.warning("Open System mode first")
    else:
        c1, c2 = st.columns(2)
        with c1:
            years = st.slider("Years:", 1, 50, 10, 1, key="dyn_years_slider"); mining = st.slider("Mining Expansion:", 0.0, 0.20, 0.05, 0.01, key="dyn_mining_slider")
        with c2:
            climate = st.slider("Climate:", -0.10, 0.05, -0.02, 0.005, key="dyn_climate_slider"); pop = st.slider("Population:", 0.0, 0.10, 0.03, 0.01, key="dyn_pop_slider")
        cri0 = st.slider("CRI Now:", 0.0, 10.0, 1.0, 0.1, key="dyn_cri_slider"); mri0 = st.slider("MRI Now:", 0.0, 10.0, 0.5, 0.1, key="dyn_mri_slider")
        if st.button("Run", type="primary", key="run_dyn_btn"):
            try: st.session_state["dyn"] = calculate_dynamic_risk(st.session_state["ci"], years, mining, climate, pop, cri0, mri0)
            except Exception as e: st.error(f"Error: {e}")
        if "dyn" in st.session_state:
            res = st.session_state["dyn"]
            if isinstance(res, dict) and "combined" in res: st.dataframe(res["combined"], width="stretch")

elif mode == "MODFLOW" and MODFLOW_OK:
    st.markdown('<div class="section-header"><h3>MODFLOW 6</h3></div>', unsafe_allow_html=True)
    mf_ok, mf_msg = is_modflow_available()
    if not mf_ok: st.error(f"Error: {mf_msg}")
    else:
        st.success(f"OK: {mf_msg}")
        c1, c2 = st.columns(2)
        with c1:
            nlay = st.number_input("Layers:", 1, 5, 1, key="mf_nlay_input"); nrow = st.number_input("Rows:", 5, 50, 20, key="mf_nrow_input"); ncol = st.number_input("Cols:", 5, 50, 20, key="mf_ncol_input"); delr = st.number_input("Delr:", 50.0, 5000.0, 500.0, 50.0, key="mf_delr_input")
        with c2:
            delc = st.number_input("Delc:", 50.0, 5000.0, 500.0, 50.0, key="mf_delc_input"); top = st.number_input("Top:", 100.0, 2000.0, 350.0, 10.0, key="mf_top_input"); botm = st.number_input("Bottom:", 0.0, 1000.0, 250.0, 10.0, key="mf_botm_input"); k_val = st.number_input("K:", 0.01, 500.0, 3.5, 0.1, key="mf_k_input"); rech = st.number_input("Recharge:", 0.0, 500.0, 15.0, 1.0, key="mf_rech_input")
        if st.button("Run", type="primary", key="run_mf_btn"):
            try:
                ws = f"/tmp/mf_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                st.session_state["mf_res"] = build_and_run_model(workspace=ws, nlay=int(nlay), nrow=int(nrow), ncol=int(ncol), delr=float(delr), delc=float(delc), top=float(top), botm=float(botm), k_value=float(k_val), recharge_mm=float(rech))
            except Exception as e: st.error(f"Error: {e}")
        if "mf_res" in st.session_state:
            res = st.session_state["mf_res"]
            if res.get("success"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Min", f"{res['head_min']:.2f} m"); c2.metric("Max", f"{res['head_max']:.2f} m"); c3.metric("Mean", f"{res['head_mean']:.2f} m")

st.markdown("---")
st.markdown("""<div style="text-align:center;color:#666;padding:10px;"><b>Sudan Mining System v57.8</b> - PILOT VERSION<br><span style="font-size:0.85em;">Screening tool only - not a substitute for lab testing</span></div>""", unsafe_allow_html=True)
