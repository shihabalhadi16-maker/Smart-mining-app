"""نظام التعدين السوداني — DRASTIC-Tox v62 (جامعة الخرطوم، نسخة تجريبية).
ملف واحد. الدوال المنطقية نقية (لا تستدعي st.*) لتسهيل الاختبار؛ الواجهة في main().
"""
import sys, types, math, html, importlib
import numpy as np
import pandas as pd
import streamlit as st

VERSION = "v62"

# ============================================================
# 1. المعايير — مصدر واحد للحدود (كل المواضع تقرأ منه)
# ============================================================
STANDARDS = {
    "SUDAN": {"cn": 0.05, "hg": 0.002, "name": ("السودان (SSMO)", "Sudan (SSMO)"),
              "note": ("⚠️ تحقق من وثيقة SSMO — المصدر ثانوي", "⚠️ Verify against SSMO document — secondary source")},
    "EU": {"cn": 0.05, "hg": 0.001, "name": ("الاتحاد الأوروبي (EU)", "European Union (EU)"), "note": ("", "")},
    "WHO": {"cn": None, "hg": 0.006, "name": ("منظمة الصحة العالمية (WHO)", "WHO"),
            "note": ("لا توجد قيمة CN في هذا الإصدار", "No CN value in this version")},
}
DEFAULT_STD = "SUDAN"

# ============================================================
# 2. جداول DRASTIC
# ============================================================
DRASTIC_MIN, DRASTIC_MAX = 23, 226      # أقصى تقييم R = 9 لذلك 226 لا 230
DTOX_MAX = DRASTIC_MAX + 50
PEST_MIN, PEST_MAX = 26, 256
DRASTIC_HIGH = 140                      # فاصل تصنيف اصطلاحي — ليس عتبة مُعايَرة
W_STD = {"D": 5, "R": 4, "A": 3, "S": 2, "T": 1, "I": 5, "C": 3}
W_PEST = {"D": 5, "R": 4, "A": 3, "S": 5, "T": 3, "I": 4, "C": 2}

AQUIFER = {"massive_shale": 2, "metamorphic_igneous": 3, "weathered_metamorphic_igneous": 4,
           "glacial_till": 5, "thin_bedded_sequences": 6, "massive_sandstone": 6,
           "massive_limestone": 6, "sand_and_gravel": 8, "basalt": 9, "karst_limestone": 10}
SOIL = {"thin_or_absent": 10, "gravel": 10, "sand": 9, "peat": 8, "shrinking_aggregated_clay": 7,
        "sandy_loam": 6, "loam": 5, "silty_loam": 4, "clay_loam": 3, "muck": 2, "nonshrinking_clay": 1}
VADOSE = {"confining_layer": 1, "silt_clay": 3, "shale": 3, "metamorphic_igneous": 4, "limestone": 6,
          "sandstone": 6, "bedded_limestone_sandstone": 6, "sand_gravel_silt_clay": 6,
          "sand_gravel": 8, "basalt": 9, "karst_limestone": 10}


def _chk(x, name):
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise ValueError(f"{name} غير صالح: {x}") from None
    if not v >= 0:
        raise ValueError(f"{name} غير صالح: {x}")
    return v


def _band(x, edges, last):
    for edge, val in edges:
        if x <= edge:
            return val
    return last


def r_D(d): return _band(_chk(d, "العمق"), [(1.5, 10), (4.6, 9), (9.1, 7), (15.2, 5), (22.9, 3), (30.5, 2)], 1)
def r_R(r): return _band(_chk(r, "التغذية"), [(50.8, 1), (101.6, 3), (177.8, 6), (254.0, 8)], 9)
def r_T(t): return _band(_chk(t, "الميل"), [(2.0, 10), (6.0, 9), (12.0, 5), (18.0, 3)], 1)
def r_C(c): return _band(_chk(c, "الناقلية"), [(4.074, 1), (12.222, 2), (28.518, 4), (40.740, 6), (81.480, 8)], 10)


def _cat(table, key, name):
    k = str(key)
    if k not in table:
        raise ValueError(f"{name} غير معروف: {k}")
    return table[k]


def ratings(s):
    cond = s.get("conductivity", s.get("conductivity_m_d"))
    return {"D": r_D(s.get("depth_m")), "R": r_R(s.get("recharge_mm")),
            "A": _cat(AQUIFER, s.get("aquifer"), "الخزان الجوفي"),
            "S": _cat(SOIL, s.get("soil"), "التربة"),
            "T": r_T(s.get("slope_pct")),
            "I": _cat(VADOSE, s.get("vadose"), "المنطقة غير المشبعة"),
            "C": r_C(cond)}


def index_of(rt, w=W_STD):
    return sum(w[k] * rt[k] for k in w)


# ============================================================
# 3. السمية: مقياس الخطر والتصنيف من HQ
# ============================================================
def hazard_score(conc, limit):
    """min(30, 30*log10(HQ)/log10(1000)) وصفر إن HQ <= 1. مقياس اصطلاحي من هذا النموذج، ليس من الأدبيات."""
    if limit is None or conc <= 0:
        return 0.0
    hq = conc / limit
    return 0.0 if hq <= 1 else min(30.0, 30.0 * math.log10(hq) / 3.0)


def hq_pair(cn, hg, std):
    L = STANDARDS[std]
    h_cn = cn / L["cn"] if (L["cn"] and cn > 0) else 0.0
    h_hg = hg / L["hg"] if (L["hg"] and hg > 0) else 0.0
    return h_cn, h_hg


def hq_class(hq):
    if hq <= 1: return "compliant"
    if hq <= 10: return "elevated"
    if hq <= 100: return "hq_high"
    return "severe"


def tox_eval(base, cn, hg, std):
    """المكافأة = min(50, α·CN + β·Hg) مع α=β=1 (فرضية صفرية، ليست معايرة)."""
    L = STANDARDS[std]
    cs = hazard_score(cn, L["cn"])
    hs = hazard_score(hg, L["hg"])
    bonus = min(50.0, cs + hs)
    h_cn, h_hg = hq_pair(cn, hg, std)
    hq = max(h_cn, h_hg)
    return {"base": base, "cn_score": round(cs, 2), "hg_score": round(hs, 2), "bonus": round(bonus, 2),
            "tox": round(base + bonus, 1), "inc_pct": round(bonus / base * 100, 1) if base > 0 else 0.0,
            "hq_cn": round(h_cn, 3), "hq_hg": round(h_hg, 3), "hq": round(hq, 3),
            "hq_class": hq_class(hq), "exceeds": hq > 1}


def action_code(drastic, exceeds):
    if exceeds: return "urgent"
    if drastic >= DRASTIC_HIGH: return "watch"
    return "routine"


def evaluate(site, std):
    rt = ratings(site)
    idx = index_of(rt)
    t = tox_eval(idx, _chk(site.get("cn_water_mg_l"), "CN"), _chk(site.get("hg_water_mg_l"), "Hg"), std)
    return {"idx": idx, "rt": rt, "tox": t, "action": action_code(idx, t["exceeds"]),
            "pct": round((idx - DRASTIC_MIN) / (DRASTIC_MAX - DRASTIC_MIN) * 100, 1)}


# ============================================================
# 4. التحقق الصادق على البيانات الموثقة
# ============================================================
def cohen_kappa(y, p):
    y = np.asarray(y); p = np.asarray(p)
    if len(y) == 0: return float("nan")
    po = float(np.mean(y == p))
    pe = sum(float(np.mean(y == c)) * float(np.mean(p == c)) for c in (0, 1))
    if pe >= 1: return float("nan")       # فئة واحدة فقط: غير معرّف
    return (po - pe) / (1 - pe)


def _fit_threshold(x, y, grid):
    best_k, best_t = -2.0, None
    for t in grid:                         # عند التعادل تُختار أصغر عتبة
        k = cohen_kappa(y, (x >= t).astype(int))
        if not np.isnan(k) and k > best_k:
            best_k, best_t = k, t
    return best_t


def lolo(df, col, default_t):
    """Leave-one-location-out: تُعاير العتبة على المواقع الأخرى فقط ثم تُطبَّق على الموقع المستبعد."""
    x = df[col].values; y = df["y"].values; locs = df["loc"].values
    pred = np.zeros(len(df), dtype=int); thr = []
    for loc in pd.unique(locs):
        te = locs == loc; tr = ~te
        t = None
        if len(set(y[tr])) >= 2:
            t = _fit_threshold(x[tr], y[tr], np.unique(x[tr]))
        if t is None:
            t = default_t
        pred[te] = (x[te] >= t).astype(int)
        thr.append(round(float(t), 4))
    return pred, thr


def boot_kappa(df, pred, B=1000, seed=42):
    """فاصل ثقة bootstrap يعيد أخذ العينات على مستوى الموقع (الصفوف الجاف/الرطب لا تُفصل)."""
    rng = np.random.default_rng(seed)
    locs = pd.unique(df["loc"].values)
    groups = [np.where(df["loc"].values == l)[0] for l in locs]
    y = df["y"].values; ks = []
    for _ in range(B):
        pick = rng.integers(0, len(locs), len(locs))
        idx = np.concatenate([groups[i] for i in pick])
        k = cohen_kappa(y[idx], pred[idx])
        if not np.isnan(k): ks.append(k)
    if not ks: return float("nan"), float("nan")
    return float(np.percentile(ks, 2.5)), float(np.percentile(ks, 97.5))


def calib_frame(ds, std):
    rows = []
    for _, r in ds.get_calibration_dataset().iterrows():
        s = r.to_dict()
        ev = evaluate(s, std)
        rows.append({"site": s["site_name"], "loc": s["location_id"],
                     "y": int(s["actual_contaminated"]), "DRASTIC": ev["idx"], "hq": ev["tox"]["hq"]})
    return pd.DataFrame(rows)


# ============================================================
# 5. القطاع الزراعي
# ============================================================
FAO_SAR_EDGES = [(3, 0.7, 0.2), (6, 1.2, 0.3), (12, 1.9, 0.5), (20, 2.9, 1.3), (40, 5.0, 2.9)]


def ussl_class(ec, sar):
    c = "C1" if ec < 0.25 else "C2" if ec < 0.75 else "C3" if ec < 2.25 else "C4"
    s = "S1" if sar < 10 else "S2" if sar < 18 else "S3" if sar < 26 else "S4"
    return c + "-" + s


def fao29(ec, sar):
    """جدول FAO 29 (Ayers & Westcot, 1985) أُدخل من الذاكرة — يجب التحقق منه قبل الاستشهاد."""
    sal = "none" if ec < 0.7 else "slight_mod" if ec <= 3.0 else "severe"
    inf = "severe"
    for smax, e_none, e_sev in FAO_SAR_EDGES:
        if sar <= smax:
            inf = "none" if ec > e_none else "slight_mod" if ec >= e_sev else "severe"
            break
    return sal, inf


def ag_metrics(w):
    na, ca, mg, k = (float(w[x]) for x in ("na_meq_l", "ca_meq_l", "mg_meq_l", "k_meq_l"))
    if ca + mg <= 0:
        raise ValueError("Ca+Mg صفر: لا يمكن حساب SAR")
    sar = na / math.sqrt((ca + mg) / 2.0)                    # SAR بالمكافئ/لتر
    na_pct = (na + k) / (ca + mg + na + k) * 100              # Wilcox: (Na+K)/المجموع
    ec = float(w["ec_ds_m"])
    sal, inf = fao29(ec, sar)
    return {"sar": round(sar, 2), "na_pct": round(na_pct, 1), "ec": ec,
            "ussl": ussl_class(ec, sar), "fao_sal": sal, "fao_inf": inf,
            "pest": index_of(ratings(w), W_PEST), "no3": w.get("no3_mg_l")}


# ============================================================
# 6. نقل الملوثات (توجيهي فقط)
# ============================================================
def transport(site, theta=0.25):
    """v = K·i/θ. θ=0.25 افتراض ثابت (لم يُقَس)، والميل الطبوغرافي بديل لتدرج منسوب الماء."""
    K = float(site["conductivity"]); i = float(site["slope_pct"]) / 100.0
    v = K * i / theta
    times = {d: (round(d / v / 365.0, 2) if v > 0 else None) for d in (100, 500, 1000)}
    return {"v_m_d": round(v, 4), "v_m_yr": round(v * 365, 1), "years": times}


# ============================================================
# 7. تحليلات الحساسية والمحاكاة (على نفس الدالة الأساسية)
# ============================================================
PHYS = {"D": "depth_m", "R": "recharge_mm", "T": "slope_pct", "C": "conductivity"}


def sensitivity(site, std, var=0.10):
    base = evaluate(site, std)["idx"]
    out = {}
    for k, f in PHYS.items():
        s2 = dict(site); s2[f] = float(site[f]) * (1 + var)
        new = evaluate(s2, std)["idx"]
        out[k] = {"new": new, "chg": new - base,
                  "sens_pct": round(abs(new - base) / base * 100, 2) if base else 0.0}
    rt = ratings(site)
    for k in ("A", "S", "I"):                      # رتبة +1 (بسقف 10)
        r2 = min(10, rt[k] + 1)
        new = base + (r2 - rt[k]) * W_STD[k]
        out[k] = {"new": new, "chg": new - base,
                  "sens_pct": round(abs(new - base) / base * 100, 2) if base else 0.0}
    return base, dict(sorted(out.items(), key=lambda x: -x[1]["sens_pct"]))


def monte_carlo(site, std, n=1000, var=0.15, seed=42):
    """ضوضاء طبيعية على المعاملات الفيزيائية فقط؛ A/S/I ثابتة في هذه المحاكاة."""
    rng = np.random.default_rng(seed)
    dr, tt = [], []
    for _ in range(n):
        s = dict(site)
        s["depth_m"] = max(0.5, float(site["depth_m"]) * (1 + rng.normal(0, var)))
        s["recharge_mm"] = max(0.0, float(site["recharge_mm"]) * (1 + rng.normal(0, var)))
        s["slope_pct"] = max(0.0, float(site["slope_pct"]) * (1 + rng.normal(0, var)))
        s["conductivity"] = max(0.01, float(site["conductivity"]) * (1 + rng.normal(0, var)))
        ev = evaluate(s, std)
        dr.append(ev["idx"]); tt.append(ev["tox"]["tox"])
    dr = np.array(dr, float); tt = np.array(tt, float)
    return {"d_mean": round(dr.mean(), 1), "d_std": round(dr.std(), 2),
            "d_ci": (round(np.percentile(dr, 5), 1), round(np.percentile(dr, 95), 1)),
            "t_mean": round(tt.mean(), 1), "t_std": round(tt.std(), 2),
            "t_ci": (round(np.percentile(tt, 5), 1), round(np.percentile(tt, 95), 1)),
            "p_high": round(float(np.mean(dr >= DRASTIC_HIGH) * 100), 1), "n": n}


def mitigate(idx, hdpe=False, treat=False, mon=False):
    """معاملات توضيحية بلا مصدر (تُعرض كذلك في الواجهة)."""
    m = float(idx)
    if hdpe: m *= 0.40
    if treat: m *= 0.60
    if mon: m *= 0.85
    red = (idx - m) / idx * 100 if idx > 0 else 0.0
    return {"after": round(m, 1), "reduction_pct": round(red, 1)}


def html_report(site_name, state, ev, std):
    t = ev["tox"]
    rows = [("الموقع", site_name), ("الولاية", state), ("المعيار", std),
            ("DRASTIC", f"{ev['idx']}/{DRASTIC_MAX}"), ("DRASTIC-Tox", f"{t['tox']}/{DTOX_MAX}"),
            ("أقصى HQ", t["hq"]), ("التوصية", ACTION_AR[ev["action"]])]
    body = "".join(f"<tr><th>{html.escape(str(a))}</th><td>{html.escape(str(b))}</td></tr>" for a, b in rows)
    return ('<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="UTF-8">'
            '<title>DRASTIC-Tox</title></head><body style="font-family:Arial;max-width:800px;margin:auto">'
            f'<h1>DRASTIC-Tox {VERSION}</h1><table border="1" cellpadding="6">{body}</table>'
            '<p>أداة فرز أولي — نسخة تجريبية — لا تُغني عن الفحص المخبري. '
            'DRASTIC يقيس الهشاشة لا التلوث الفعلي.</p></body></html>')


ACTION_AR = {"urgent": "إجراء عاجل: تجاوز الحد المعياري", "watch": "هشاشة عالية: أولوية للرصد",
             "routine": "مراقبة روتينية"}

# ============================================================
# 8. الترجمة والتسميات (تُقرأ من الجلسة، لا تُستخدم في الدوال المنطقية)
# ============================================================
LBL = {
    "compliant": ("مطابق", "Compliant"), "elevated": ("مرتفع قليلاً", "Slightly elevated"),
    "hq_high": ("مرتفع", "High"), "severe": ("شديد", "Severe"),
    "urgent": ("⚠️ إجراء عاجل: تجاوز الحد المعياري", "⚠️ Urgent: standard exceeded"),
    "watch": ("هشاشة عالية: أولوية للرصد", "High vulnerability: prioritize monitoring"),
    "routine": ("مراقبة روتينية", "Routine monitoring"),
    "hi": ("هشاشة عالية", "High vulnerability"), "lo": ("هشاشة منخفضة", "Low vulnerability"),
    "none": ("لا يوجد", "None"), "slight_mod": ("خفيف إلى متوسط", "Slight to moderate"),
    "severe_ag": ("شديد", "Severe"),
}
MODE_LBL = {"system": ("النظام الأساسي", "Core system"), "agri": ("القطاع الزراعي", "Agriculture"),
            "verif": ("التحقق على البيانات الموثقة", "Validation (verified data)"),
            "transport": ("نقل الملوثات (توجيهي)", "Transport (indicative)")}
OPTIONAL_MODULES = ["weight_manager", "external_validation", "data_validator", "pdf_generator",
                    "excel_exporter", "gis_raster", "live_apis", "auto_calibration", "auto_maps",
                    "advanced_modules", "model_development", "modflow_engine", "water_guardian"]


def ar():
    return st.session_state.get("lang", "ar") == "ar"


def tx(a, e):
    return a if ar() else e


def lb(code):
    return tx(*LBL.get(code, (str(code), str(code))))


# ============================================================
# 9. تحميل قاعدة البيانات (مع تركيب بديل لـ drastic_core إن لم يوجد ملف)
# ============================================================
def install_core_shim():
    try:
        import drastic_core  # noqa: F401
        return "ملف"
    except ImportError:
        pass
    if "drastic_core" in sys.modules:
        return "وحدة مركّبة"
    m = types.ModuleType("drastic_core")
    m.W_STD, m.AQUIFER, m.SOIL, m.VADOSE = W_STD, AQUIFER, SOIL, VADOSE
    m.rate_D, m.rate_R, m.rate_T, m.rate_C = r_D, r_R, r_T, r_C
    m._cat = _cat
    m.LIMITS_MG_L = {k: {"cn": v["cn"], "hg": v["hg"]} for k, v in STANDARDS.items()}
    sys.modules["drastic_core"] = m
    return "مركّبة من هذا الملف"


def load_db():
    try:
        core = install_core_shim()
        import data_sources as ds
        return ds, None, core
    except Exception as e:
        return None, f"{type(e).__name__}: {e}", None


def probe_optional():
    out = {}
    for name in OPTIONAL_MODULES:
        try:
            importlib.import_module(name)
            out[name] = None
        except Exception as e:
            out[name] = f"{type(e).__name__}: {str(e)[:70]}"
    return out


def list_site(ds, state, key):
    s = ds.get_site_data(state, key)
    if s is None:
        raise KeyError(f"موقع غير موجود: {state}/{key}")
    s["name"] = s.get("name_ar", key)
    return s


# ============================================================
# 10. الواجهة
# ============================================================
CSS = """<style>
.pilot{background:#f57c00;color:#fff;padding:10px;border-radius:8px;font-weight:600;text-align:center;}
.badge{display:inline-block;padding:4px 12px;border-radius:8px;background:#fff3e0;color:#e65100;border:2px solid #e65100;font-weight:700;}
</style>"""


def units_warn(cn, hg):
    if hg is not None and hg > 0.1: st.warning(tx(f"Hg={hg} mg/L مرتفع جداً — تحقق من الوحدات", f"Hg={hg} mg/L very high — check units"))
    if cn is not None and cn > 5: st.warning(tx(f"CN={cn} mg/L مرتفع جداً — تحقق من الوحدات", f"CN={cn} mg/L very high — check units"))


def render_eval(ev):
    t = ev["tox"]
    c1, c2, c3 = st.columns(3)
    c1.metric("DRASTIC", f"{ev['idx']}/{DRASTIC_MAX}")
    c2.metric(tx("مستوى الهشاشة", "Vulnerability"), lb("hi" if ev["idx"] >= DRASTIC_HIGH else "lo"))
    c3.metric(tx("نسبة النطاق", "Range %"), f"{ev['pct']}%")
    c1, c2, c3 = st.columns(3)
    c1.metric("DRASTIC-Tox", t["tox"], delta=(f"+{t['inc_pct']}%" if t["inc_pct"] > 0 else None))
    c2.metric(tx("المكافأة", "Bonus"), t["bonus"])
    c3.metric(tx("أقصى HQ", "Max HQ"), t["hq"])
    st.write(f"**{tx('تصنيف السمية (من HQ)', 'Toxicity class (from HQ)')}:** {lb(t['hq_class'])}")
    {"urgent": st.error, "watch": st.warning, "routine": st.success}[ev["action"]](lb(ev["action"]))


def cur_site():
    return st.session_state.get("manual_site") if st.session_state.get("src") == "manual" \
        else st.session_state.get("list_site")


def tab_input(ds, std):
    states = list(ds.STATES_DATABASE)
    c1, c2 = st.columns([1, 2])
    state = c1.selectbox(tx("الولاية", "State"), states, key="s_state")
    sites = ds.get_sites_by_state(state)
    key = c2.selectbox(tx("الموقع", "Site"), list(sites), key="s_site",
                       format_func=lambda k: sites[k]["name_ar"])
    if "تقديرات" in str(ds.STATES_DATABASE[state].get("source", "")):
        st.warning(tx("موقع تقديري (تقديرات عامة) — لا يدخل المعايرة ولا التحقق",
                      "Estimated site — excluded from calibration and validation"))
    site = list_site(ds, state, key)
    st.session_state["list_site"] = site
    if "تعدين" in str(site.get("activity", "")):
        st.markdown(f"<span class='badge'>⛏️ {tx('تقليدي', 'Artisanal')}</span>", unsafe_allow_html=True)
    st.caption(f"{tx('النشاط', 'Activity')}: {site.get('activity', '-')} | "
               f"{tx('الموسم', 'Season')}: {site.get('season', '-')} | "
               f"{tx('التوثيق', 'Documentation')}: "
               f"{tx('موثق', 'verified') if site.get('verified') else tx('للعرض فقط', 'display only')}")
    units_warn(site["cn_water_mg_l"], site["hg_water_mg_l"])
    c1, c2 = st.columns(2)
    c1.metric("CN", f"{site['cn_water_mg_l']} mg/L")
    c2.metric("Hg", f"{site['hg_water_mg_l']} mg/L")
    render_eval(evaluate(site, std))


def tab_manual(ds, std):
    st.info(tx("النتيجة تظهر فوراً عند تغيير أي قيمة — لا يوجد زر حفظ. البيانات تبقى في جلسة المتصفح.",
               "Results update instantly. No save button. Data stays in this browser session."))
    c1, c2 = st.columns(2)
    with c1:
        d = st.number_input("D — " + tx("العمق (م)", "Depth (m)"), 0.5, 100.0, 15.0, key="m_d")
        r = st.number_input("R — " + tx("التغذية (مم/سنة)", "Recharge (mm/yr)"), 0.0, 400.0, 20.0, key="m_r")
        tt = st.number_input("T — " + tx("الميل (%)", "Slope (%)"), 0.0, 30.0, 3.0, key="m_t")
        c = st.number_input("C — " + tx("الناقلية (م/يوم)", "Conductivity (m/d)"), 0.01, 200.0, 3.0, key="m_c")
    with c2:
        a = st.selectbox("A — " + tx("الخزان", "Aquifer"), list(AQUIFER),
                         index=list(AQUIFER).index("massive_shale"), key="m_a")
        s_ = st.selectbox("S — " + tx("التربة", "Soil"), list(SOIL),
                          index=list(SOIL).index("thin_or_absent"), key="m_s")
        i_ = st.selectbox("I — " + tx("غير مشبعة", "Vadose"), list(VADOSE),
                          index=list(VADOSE).index("confining_layer"), key="m_i")
    c1, c2 = st.columns(2)
    cn = c1.number_input("CN (mg/L)", 0.0, 10.0, 0.025, format="%.5f", key="m_cn")
    hg = c2.number_input("Hg (mg/L)", 0.0, 10.0, 0.011, format="%.5f", key="m_hg")
    site = {"name": tx("إدخال يدوي", "Manual"), "depth_m": d, "recharge_mm": r, "slope_pct": tt,
            "conductivity": c, "aquifer": a, "soil": s_, "vadose": i_,
            "cn_water_mg_l": cn, "hg_water_mg_l": hg}
    ev = evaluate(site, std)
    sug = 1 if ev["tox"]["exceeds"] else 0
    opts = [tx("اقتراح تلقائي من المعيار", "Auto (from standard)"), tx("ملوث", "Contaminated"),
            tx("نظيف", "Clean")]
    choice = st.radio(tx("الحالة الفعلية (للتحقق)", "Actual status (for validation)"), opts,
                      horizontal=True, key="m_lab")
    actual = sug if choice == opts[0] else (1 if choice == opts[1] else 0)
    st.caption(tx("التسمية المقترحة: ", "Suggested label: ") + (tx("ملوث", "Contaminated") if sug else tx("نظيف", "Clean")))
    if actual != sug:
        st.warning(tx("تحذير: الحالة المختارة تخالف المعيار المحسوب. تأكد من مصدر القياس.",
                      "Warning: chosen status contradicts the computed standard. Check the measurement source."))
    site["actual_contaminated"] = actual
    st.session_state["manual_site"] = site
    units_warn(cn, hg)
    render_eval(ev)
    rows = []
    for k in STANDARDS:
        e2 = evaluate(site, k)
        rows.append({tx("المعيار", "Standard"): tx(*STANDARDS[k]["name"]),
                     "DRASTIC-Tox": e2["tox"]["tox"], tx("المكافأة", "Bonus"): e2["tox"]["bonus"],
                     "max HQ": e2["tox"]["hq"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def tab_bulk(std):
    up = st.file_uploader("CSV / Excel", type=["csv", "xlsx"], key="bulk_up")
    need = ["depth_m", "recharge_mm", "slope_pct", "aquifer", "soil", "vadose", "cn_water_mg_l", "hg_water_mg_l"]
    if up is None:
        sample = pd.DataFrame({"site_name": ["S1"], "depth_m": [15.0], "recharge_mm": [20.0],
                               "slope_pct": [3.0], "conductivity": [3.0], "aquifer": ["massive_sandstone"],
                               "soil": ["sand"], "vadose": ["sand_gravel"],
                               "cn_water_mg_l": [0.025], "hg_water_mg_l": [0.011]})
        st.download_button("📥 Template", sample.to_csv(index=False).encode("utf-8-sig"),
                           file_name="template.csv", mime="text/csv")
        return
    df = pd.read_csv(up) if up.name.endswith(".csv") else pd.read_excel(up)
    miss = [c for c in need if c not in df.columns]
    if "conductivity" not in df.columns and "conductivity_m_d" not in df.columns:
        miss.append("conductivity")
    if miss:
        st.error(f"{tx('أعمدة ناقصة', 'Missing columns')}: {miss}")
        return
    out, errs = [], []
    for i, row in df.iterrows():
        s = row.to_dict()
        name = s.get("site_name", s.get("name", f"R{i + 1}"))
        try:
            ev = evaluate(s, std)
            out.append({"site": name, "DRASTIC": ev["idx"], "DRASTIC_Tox": ev["tox"]["tox"],
                        "max_HQ": ev["tox"]["hq"], "action": ACTION_AR[ev["action"]]})
        except Exception as e:
            errs.append(f"row {i + 1}: {type(e).__name__}: {e}")
            out.append({"site": name, "DRASTIC": None, "DRASTIC_Tox": None, "max_HQ": None, "action": "ERROR"})
    res = pd.DataFrame(out)
    st.dataframe(res, use_container_width=True, hide_index=True)
    if errs:
        st.error(f"{len(errs)} {tx('صف فشل', 'rows failed')}")
        for e in errs[:10]:
            st.caption(e)
    st.download_button("📥 " + tx("تنزيل النتائج", "Download"), res.to_csv(index=False).encode("utf-8-sig"),
                       file_name="results.csv", mime="text/csv")


def tab_toxicity(site, std):
    if site is None:
        st.info(tx("اختر موقعاً أولاً", "Select a site first"))
        return
    ev = evaluate(site, std)
    t = ev["tox"]
    L = STANDARDS[std]
    st.markdown(f"**{tx('المعيار', 'Standard')}:** {tx(*L['name'])} — CN limit: {L['cn']} | Hg limit: {L['hg']}")
    rows = [{tx("المكوّن", "Component"): "CN", tx("التركيز", "Conc."): site["cn_water_mg_l"],
             "HQ": t["hq_cn"], tx("الدرجة", "Score"): t["cn_score"]},
            {tx("المكوّن", "Component"): "Hg", tx("التركيز", "Conc."): site["hg_water_mg_l"],
             "HQ": t["hq_hg"], tx("الدرجة", "Score"): t["hg_score"]}]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.write(f"**{tx('أقصى HQ', 'Max HQ')}:** {t['hq']} → {lb(t['hq_class'])}")
    st.caption(tx("المكافأة = min(50, درجة CN + درجة Hg) بفرضية α=β=1 — ليست معايرة. "
                  "مقياس الخطر min(30, 30·log10(HQ)/3) اصطلاحي من هذا النموذج.",
                  "Bonus = min(50, CN score + Hg score) with α=β=1 (null hypothesis, not calibrated). "
                  "The hazard scale is a model convention, not from literature."))


def tab_solutions(ev):
    st.warning(tx("⚠️ معاملات التخفيض افتراضات توضيحية بلا مصدر.",
                  "⚠️ Reduction factors are illustrative assumptions without a source."))
    if ev is None:
        st.info(tx("اختر موقعاً أولاً", "Select a site first"))
        return
    c1, c2, c3 = st.columns(3)
    hdpe = c1.checkbox(tx("بطانة HDPE", "HDPE liner"), key="chk_hdpe")
    treat = c2.checkbox(tx("معالجة السيانيد", "Cyanide treatment"), key="chk_treat")
    mon = c3.checkbox(tx("آبار مراقبة", "Monitoring wells"), key="chk_mon")
    r = mitigate(ev["idx"], hdpe, treat, mon)
    c1, c2 = st.columns(2)
    c1.metric(tx("قبل", "Before"), ev["idx"])
    c2.metric(tx("بعد", "After"), r["after"], delta=f"-{r['reduction_pct']}%" if r["reduction_pct"] > 0 else None)


def tab_report(site, std, ev):
    if site is None or ev is None:
        st.info(tx("اختر موقعاً أولاً", "Select a site first"))
        return
    t = ev["tox"]
    st.dataframe(pd.DataFrame({
        "Metric": ["DRASTIC", "CN score", "Hg score", "Base bonus", "DRASTIC-Tox", "Max HQ", "Recommendation"],
        "Value": [ev["idx"], t["cn_score"], t["hg_score"], t["bonus"], t["tox"], t["hq"],
                  ACTION_AR[ev["action"]]]}), hide_index=True, use_container_width=True)
    doc = html_report(site.get("name", "-"), site.get("state", "-"), ev, std)
    st.download_button("📄 HTML", doc.encode("utf-8"), file_name="report.html", mime="text/html")


def tab_analysis(site, std):
    if site is None:
        st.info(tx("اختر موقعاً أولاً", "Select a site first"))
        return
    st.subheader(tx("حساسية أحادية البُعد (±10%)", "One-at-a-time sensitivity (±10%)"))
    base, sens = sensitivity(site, std)
    st.dataframe(pd.DataFrame([{tx("المعامل", "Parameter"): k, "new index": v["new"],
                                 "change": v["chg"], "sensitivity %": v["sens_pct"]}
                                for k, v in sens.items()]), hide_index=True, use_container_width=True)
    st.subheader("SPSA")
    tot = sum(W_STD.values())
    rt = ratings(site)
    DI = index_of(rt)
    st.dataframe(pd.DataFrame([{"param": k, "Wi": w, "Ri": rt[k],
                                "theor. %": round(w / tot * 100, 2),
                                "effect. %": round(w * rt[k] / DI * 100, 2)} for k, w in W_STD.items()]),
                 hide_index=True, use_container_width=True)
    st.subheader("Monte Carlo")
    n = st.slider(tx("عدد المحاكاة", "Simulations"), 100, 3000, 1000, 100, key="mc_n")
    v = st.slider(tx("الاختلاف %", "Variation %"), 5, 30, 15, 5, key="mc_v")
    if st.button(tx("تشغيل Monte Carlo", "Run Monte Carlo"), key="mc_run"):
        st.session_state["mc"] = monte_carlo(site, std, n, v / 100.0)
    if "mc" in st.session_state:
        m = st.session_state["mc"]
        c1, c2, c3 = st.columns(3)
        c1.metric("DRASTIC mean ± sd", f"{m['d_mean']} ± {m['d_std']}")
        c2.metric("DRASTIC 90% CI", f"{m['d_ci'][0]}–{m['d_ci'][1]}")
        c3.metric(f"P(DRASTIC ≥ {DRASTIC_HIGH})", f"{m['p_high']}%")
        st.caption(tx(f"DRASTIC-Tox 90% CI: {m['t_ci'][0]}–{m['t_ci'][1]}", f"DRASTIC-Tox 90% CI: {m['t_ci'][0]}–{m['t_ci'][1]}"))


def tab_verification(ds, std):
    st.warning(tx("تنبيه صريح: 11 صفاً موثقاً لكنها تمثل 9 مواقع مستقلة فقط (الجاف والرطب لموقع واحد). "
                  "التسميات بُنيت على نفس الحدود المعيارية، لذا قاعدة التجاوز ليست تحققاً مستقلاً. "
                  "التراكيز المختبرة مشتقة من نفس الجدول.",
                  "Honest caveat: 11 verified rows = 9 independent locations (dry/wet share a location). "
                  "Labels were built from the same standard limits, so the exceedance rule is not an independent test."))
    cal = calib_frame(ds, std)
    if cal.empty:
        st.info(tx("لا توجد صفوف معايرة موثقة", "No verified calibration rows"))
        return
    y = cal["y"].values
    st.write(f"{tx('صفوف', 'rows')}: {len(cal)} | {tx('مواقع مستقلة', 'independent locations')}: "
             f"{cal['loc'].nunique()} | {tx('ملوثة', 'contaminated')}: {int(y.sum())}")
    res = []
    def add(name, pred, thr):
        k = cohen_kappa(y, pred); lo, hi = boot_kappa(cal, pred)
        res.append({tx("الطريقة", "Method"): name, "kappa": round(k, 3) if not np.isnan(k) else "n/a",
                    "95% CI (location boot.)": f"[{lo:.2f}, {hi:.2f}]" if not np.isnan(lo) else "n/a",
                    tx("الدقة", "Accuracy"): round(float(np.mean(y == pred)), 3),
                    tx("العتبات (كل موقع مستبعد)", "Thresholds (per held-out loc.)"): thr})
    p1 = (cal["DRASTIC"].values >= DRASTIC_HIGH).astype(int)
    add(tx("DRASTIC وحده (عتبة 140 ثابتة)", "DRASTIC alone (fixed 140)"), p1, "140")
    p2, t2 = lolo(cal, "DRASTIC", DRASTIC_HIGH)
    add(tx("DRASTIC وحده (معايرة LOLO)", "DRASTIC alone (LOLO-calibrated)"), p2, str(t2))
    p3, t3 = lolo(cal, "hq", 1.000001)
    add(tx("التراكيز فقط (معايرة LOLO على أقصى HQ)", "Concentrations only (LOLO on max HQ)"), p3, str(t3))
    p4 = (cal["hq"].values > 1).astype(int)
    add(tx("قاعدة التجاوز (HQ > 1، بلا معايرة)", "Exceedance rule (HQ > 1, no fitting)"), p4, "1")
    st.dataframe(pd.DataFrame(res), hide_index=True, use_container_width=True)
    st.caption(tx("خط الأساس الحاسم: DRASTIC وحده. نتائج kappa فوق 0.3 تعني توافقاً ضعيفاً جداً مع البيانات الحالية.",
                  "Key baseline: DRASTIC alone. Kappa values near zero mean no agreement beyond chance."))
    with st.expander(tx("الصفوف المستخدمة", "Rows used")):
        st.dataframe(cal, hide_index=True, use_container_width=True)


def view_agri(ds, std):
    states = list(ds.AGRICULTURAL_DATA)
    c1, c2 = st.columns(2)
    state = c1.selectbox(tx("الولاية", "State"), states, key="ag_state")
    sites = ds.AGRICULTURAL_DATA[state]["sites"]
    key = c2.selectbox(tx("البئر", "Well"), list(sites), key="ag_site")
    w = dict(sites[key])
    w.setdefault("slope_pct", 3.0)
    w.setdefault("conductivity", w.get("conductivity"))
    m = ag_metrics(w)
    c1, c2, c3 = st.columns(3)
    c1.metric("SAR", m["sar"])
    c2.metric("Na% (Wilcox)", f"{m['na_pct']}%")
    c3.metric("EC (dS/m)", m["ec"])
    st.write(f"**USSL:** {m['ussl']}")
    st.write(f"**FAO 29 — {tx('الملوحة', 'Salinity')}:** {lb(m['fao_sal'])} | "
             f"**{tx('النفاذية', 'Infiltration')}:** {lb(m['fao_inf'])}")
    st.write(f"**Pesticide DRASTIC:** {m['pest']} / {PEST_MAX} (min {PEST_MIN}) — "
             f"{tx('الوزن: 5،4،3،5،3،4،2', 'weights 5,4,3,5,3,4,2')}")
    st.write(f"NO3: {m['no3']} mg/L — {tx('بلا حد مرجعي في هذا الإصدار', 'no reference limit in this version')}")
    st.caption(tx("جداول USSL وFAO 29 أُدخلت من الذاكرة ويجب التحقق منها قبل الاستشهاد. "
                  "Pesticide DRASTIC لا يملك فئات مُعايرة هنا، لذا يُعرض الرقم الخام فقط.",
                  "USSL and FAO 29 tables were entered from memory; verify before citing. "
                  "Pesticide DRASTIC has no calibrated classes here, so only the raw index is shown."))


def view_transport(site):
    if site is None:
        st.info(tx("اختر موقعاً أولاً", "Select a site first"))
        return
    t = transport(site)
    st.write(f"v = {t['v_m_d']} m/d ≈ {t['v_m_yr']} m/yr")
    st.dataframe(pd.DataFrame([{tx("المسافة (م)", "Distance (m)"): d, tx("السنوات", "Years"): y or "∞"}
                                for d, y in t["years"].items()]), hide_index=True)
    st.warning(tx("توجيهي فقط: θ=0.25 افتراض (لم يُقَس)، والميل بديل لتدرج منسوب الماء، "
                  "ولا يشمل الانتشار أو الامتزاز أو التحلل. ليس نموذجاً لانتقال الملوثات.",
                  "Indicative only: θ=0.25 is an assumption (not measured); slope is a proxy for the water-table "
                  "gradient; no dispersion, sorption or decay. Not a contaminant transport model."))


def main():
    st.set_page_config(page_title=f"Sudan Mining System {VERSION}", page_icon="⛏️", layout="wide")
    st.session_state.setdefault("lang", "ar")
    st.session_state.setdefault("std", DEFAULT_STD)
    st.session_state.setdefault("mode", "system")
    st.markdown(CSS, unsafe_allow_html=True)
    ds, ds_err, core = load_db()
    with st.sidebar:
        st.selectbox("🌐 Language / اللغة", ["ar", "en"], key="lang",
                     format_func=lambda x: "العربية" if x == "ar" else "English")
        st.selectbox(tx("المعيار المرجعي", "Reference standard"), list(STANDARDS), key="std",
                     format_func=lambda k: tx(*STANDARDS[k]["name"]))
        note = tx(*STANDARDS[st.session_state["std"]]["note"])
        if note:
            st.caption(note)
        mode = st.radio(tx("الوضع", "Mode"), list(MODE_LBL), key="mode",
                        format_func=lambda m: tx(*MODE_LBL[m]))
        st.markdown("---")
        st.markdown(f"**{tx('الوحدات', 'Modules')}**")
        st.caption(f"{'✅' if ds else '❌'} data_sources" + ("" if ds else f" — {ds_err}"))
        st.caption(f"✅ drastic_core ({core})" if core else "❌ drastic_core")
        for name, err in probe_optional().items():
            st.caption(f"⚪ {name} — {err}" if err else f"✅ {name}")
        st.caption(tx("الوحدات الاختيارية غير مستخدمة في v62 بعد.", "Optional modules are not used in v62 yet."))
    STD = st.session_state["std"]
    st.title(tx("نظام التعدين السوداني — DRASTIC-Tox", "Sudan Mining System — DRASTIC-Tox"))
    st.markdown(f"<div class='pilot'>⚠️ {tx('نسخة تجريبية — أداة فرز أولي، لا تُغني عن الفحص المخبري', 'Pilot — screening tool, not a substitute for lab analysis')}</div>",
                unsafe_allow_html=True)
    if ds is None:
        st.error(f"{tx('فشل تحميل قاعدة البيانات', 'Database failed to load')}: {ds_err}")
        return
    rows = ds.get_all_sites_as_dataframe()
    ver = rows[rows["verified"] == True]
    st.caption(f"{tx('مواقع', 'sites')}: {len(rows)} | {tx('صفوف موثقة', 'verified rows')}: {len(ver)} | "
               f"{tx('مواقع مستقلة', 'independent locations')}: {ver['location_id'].nunique()} | "
               f"{tx('تقديرية', 'estimated')}: {int(rows['is_estimate'].sum())}")
    try:
        if mode == "system":
            st.radio(tx("مصدر التحليل", "Analysis source"), ["list", "manual"], horizontal=True,
                     format_func=lambda s: tx("موقع من القائمة", "Site from list") if s == "list"
                     else tx("إدخال يدوي", "Manual input"), key="src")
            names = [tx("المدخلات", "Input"), tx("إدخال يدوي", "Manual"), tx("التقييم الجماعي", "Bulk"),
                     tx("السمية", "Toxicity"), tx("الحلول", "Solutions"), tx("التقرير", "Report"),
                     tx("التحليل", "Analysis")]
            t = st.tabs(names)
            with t[0]: tab_input(ds, STD)
            with t[1]: tab_manual(ds, STD)
            with t[2]: tab_bulk(STD)
            site = cur_site()
            ev = evaluate(site, STD) if site else None
            with t[3]: tab_toxicity(site, STD)
            with t[4]: tab_solutions(ev)
            with t[5]: tab_report(site, STD, ev)
            with t[6]: tab_analysis(site, STD)
        elif mode == "agri":
            view_agri(ds, STD)
        elif mode == "verif":
            tab_verification(ds, STD)
        else:
            st.radio(tx("مصدر الموقع", "Site source"), ["list", "manual"], horizontal=True,
                     format_func=lambda s: tx("موقع من القائمة", "Site from list") if s == "list"
                     else tx("إدخال يدوي", "Manual input"), key="src")
            view_transport(cur_site())
    except Exception as e:
        st.error(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
