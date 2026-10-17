"""نظام التعدين السوداني — DRASTIC-Tox v62 (جامعة الخرطوم، نسخة تجريبية).
ملف واحد. الدوال المنطقية نقية (لا تستدعي st.*) لتسهيل الاختبار؛ الواجهة في main().
"""
import sys, types, math, html, importlib
import numpy as np
import pandas as pd
import streamlit as st

VERSION = "v66"

# ============================================================
# 1. المعايير — مصدر واحد للحدود (كل المواضع تقرأ منه)
# ============================================================
STANDARDS = {
    "SUDAN": {"cn": 0.05, "hg": 0.004, "name": ("السودان (SSMO)", "Sudan (SSMO)"),
              "note": ("⚠️ Hg = 0.004 mg/L وفق ملخص SSMO (مصدر ثانوي). النص الأصلي للوثيقة لم يُفحص بعد. البدائل في تبويب الإدخال اليدوي",
                       "⚠️ Hg = 0.004 mg/L per SSMO summary (secondary). Primary document not yet checked. Alternatives in manual tab")},
    "EU": {"cn": 0.05, "hg": 0.001, "name": ("الاتحاد الأوروبي (EU)", "European Union (EU)"), "note": ("", "")},
    "WHO": {"cn": 0.07, "hg": 0.006, "name": ("منظمة الصحة العالمية (WHO)", "WHO"),
            "note": ("CN: WHO 2003 — Hg: WHO الطبعة الرابعة (غير العضوي)", "CN: WHO 2003 — Hg: WHO 4th ed. (inorganic)")},
}
DEFAULT_STD = "SUDAN"
# بدائل حد الزئبق السوداني: القيمة غير محسومة حتى التحقق من وثيقة SSMO
SUDAN_HG_ALTERNATIVES = [
    (0.004, ("SSMO وفق ملخص بحث (القيمة الافتراضية)", "SSMO per research summary (default)")),
    (0.0007, ("EMRO 2006 (معيار السودان 2002، ICS 13.060.00)", "EMRO 2006 (Sudan 2002 standard)")),
    (0.001, ("Elwaleed et al. 2024 (يذكر 1 µg/L)", "Elwaleed et al. 2024 (states 1 µg/L)")),
    (0.002, ("القيمة السابقة في البرنامج (بلا مصدر محقق)", "Previous value (no verified source)")),
]

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


def scenario(site, std, cn_red=0.0, hg_red=0.0):
    """سيناريو تقليل المصدر: يخفّض التراكيز فقط ويترك DRASTIC كما هو (خاصية جيولوجية لا تتغير)."""
    cn = _chk(site.get("cn_water_mg_l"), "CN") * (1 - cn_red / 100.0)
    hg = _chk(site.get("hg_water_mg_l"), "Hg") * (1 - hg_red / 100.0)
    idx = index_of(ratings(site))
    t = tox_eval(idx, cn, hg, std)
    return {"cn": round(cn, 6), "hg": round(hg, 6), "tox": t, "action": action_code(idx, t["exceeds"])}


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
            "verif": ("وصفي على البيانات الموثقة (ليس تنبؤياً)", "Descriptive on verified data (NOT predictive)"),
            "predict": ("تنبؤ مستقل (تحقق صارم)", "Independent prediction (strict)"),
            "prev": ("اختبار إضافة التركيز السابق", "Test: does adding prior concentration help?"),
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


def parse_conc(v, rule):
    """يحوّل القيم مثل '<0.001' حسب قاعدة صريحة يختارها المستخدم: 0، أو نصف حد الكشف، أو حد الكشف."""
    if isinstance(v, str):
        t = v.strip().replace(",", ".")
        if t.startswith("<"):
            dl = float(t[1:])
            return {"صفر": 0.0, "نصف حد الكشف": dl / 2, "حد الكشف": dl}[rule]
        return float(t)
    return v


def audit_db(ds):
    """يتحقق من وجود كل الحقول صراحة في البيانات الخام (قبل أي قيمة افتراضية)."""
    need = ("depth_m", "recharge_mm", "slope_pct", "conductivity", "aquifer", "soil", "vadose",
            "cn_water_mg_l", "hg_water_mg_l")
    issues = []
    for st_name, d in ds.STATES_DATABASE.items():
        for k, v in d["sites"].items():
            for f in need:
                if f not in v:
                    issues.append(f"{st_name}/{k}: {f} مفقود")
    return issues


def check_core_consistency(core_mod):
    """يقارن الجداول والدوال في drastic_core.py الحقيقي (إن وُجد) مع جداول التطبيق."""
    probs = []
    for name, mine in (("W_STD", W_STD), ("AQUIFER", AQUIFER), ("SOIL", SOIL), ("VADOSE", VADOSE)):
        if getattr(core_mod, name, None) != mine:
            probs.append(f"{name} مختلف")
    for fn_name, mine in (("rate_D", r_D), ("rate_R", r_R), ("rate_T", r_T), ("rate_C", r_C)):
        f = getattr(core_mod, fn_name, None)
        if f is None:
            probs.append(f"{fn_name} غير موجودة")
            continue
        for x in (0.5, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0):
            if f(x) != mine(x):
                probs.append(f"{fn_name}({x}) مختلف")
                break
    return probs


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
                       format_func=lambda k: sites[k]["name_ar"] + ("" if sites[k].get("verified") else tx(" (تقديري)", " (estimated)")))
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


FORBIDDEN_PREDICTORS = {"cn_water_mg_l", "hg_water_mg_l", "DRASTIC-Tox", "drastic_tox", "tox", "bonus",
                        "hq", "max_HQ", "label", "actual_contaminated"}
PREDICTOR_COLS = ["depth_m", "recharge_mm", "slope_pct", "conductivity", "aquifer", "soil", "vadose"]


def leakage_guard(features):
    """يرفض أي متنبئ يحمل معلومة الهدف (التركيز أو المؤشرات المشتقة منه أو التسمية)."""
    bad = [f for f in features if f in FORBIDDEN_PREDICTORS]
    if bad:
        raise ValueError("تسرب معلوماتي: المتنبئ يحتوي على متغيرات تحمل معلومة الهدف: " + ", ".join(bad))
    missing = [c for c in PREDICTOR_COLS if c not in features]
    if missing:
        raise ValueError("أعمدة المتنبئ الجيولوجي ناقصة: " + ", ".join(missing))
    return True


def auc_rank(y, score):
    """AUC بطريقة Mann-Whitney مع معالجة التعادل. 0.5 = الصدفة."""
    y = np.asarray(y); score = np.asarray(score, float)
    pos = score[y == 1]; neg = score[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    ranks = pd.Series(np.concatenate([pos, neg])).rank().values
    r_pos = ranks[:len(pos)].sum()
    return float((r_pos - len(pos) * (len(pos) + 1) / 2.0) / (len(pos) * len(neg)))


def boot_auc(df, score, B=1000, seed=42):
    """فاصل ثقة bootstrap على مستوى الموقع."""
    rng = np.random.default_rng(seed)
    locs = pd.unique(df["location_id"].values)
    groups = [np.where(df["location_id"].values == l)[0] for l in locs]
    y = df["label"].values; out = []
    for _ in range(B):
        pick = rng.integers(0, len(locs), len(locs))
        idx = np.concatenate([groups[i] for i in pick])
        a = auc_rank(y[idx], score[idx])
        if not np.isnan(a): out.append(a)
    if not out: return float("nan"), float("nan")
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


PREREG_RULE = ("قاعدة القبول (تُعلن قبل النظر إلى النتائج): يُقبل التنبؤ الجيولوجي إذا كان الحد الأدنى "
               "لفاصل AUC أعلى من 0.5، وكانت AUC لـDRASTIC أعلى من المنافس. وإلا يُرفض.")


def predictive_eval(df, drastic_scores):
    """تقييم على مجموعة الاختبار وحدها. drastic_scores مُحسوب من PREDICTOR_COLS فقط."""
    test = df[df["split"] == "test"].reset_index(drop=True)
    res = {"n_test_rows": len(test), "n_test_locations": int(test["location_id"].nunique()),
           "n_pos": int(test["label"].sum()), "warnings": []}
    if res["n_test_locations"] < 30:
        res["warnings"].append(f"مواقع الاختبار {res['n_test_locations']} فقط (أقل من 30): الفاصل واسع جداً")
    if res["n_pos"] < 10:
        res["warnings"].append(f"عدد المواقع الملوثة في الاختبار {res['n_pos']} فقط (أقل من 10)")
    d = np.asarray(drastic_scores, float)[df["split"].values == "test"]
    res["auc_drastic"] = auc_rank(test["label"].values, d)
    res["ci_drastic"] = boot_auc(test.assign(_s=d), d)
    if "dist_to_mine_m" in test.columns:
        comp = -test["dist_to_mine_m"].astype(float).values        # الأقرب للتعدين = خطر أعلى
        res["auc_comp"] = auc_rank(test["label"].values, comp)
        res["ci_comp"] = boot_auc(test, comp)
    else:
        res["auc_comp"] = None
    lo = res["ci_drastic"][0]
    if np.isnan(lo):
        verdict = "غير قابل للحكم"
    elif lo > 0.5 and (res["auc_comp"] is None or res["auc_drastic"] > res["auc_comp"]):
        verdict = "قُبل التنبؤ الجيولوجي وفق القاعدة المعلنة"
    else:
        verdict = "رُفض التنبؤ الجيولوجي وفق القاعدة المعلنة"
    res["verdict"] = verdict
    return res


PREV_COLS = ["cn_prev", "hg_prev"]
CURRENT_CONC_COLS = ["cn_water_mg_l", "hg_water_mg_l"]


def prev_guard(columns):
    """هذا الوضع يستخدم التركيز السابق فقط. التركيز الحالي ممنوع لأنه قد يكون هو الهدف نفسه."""
    cur = [c for c in columns if c in CURRENT_CONC_COLS]
    if cur:
        raise ValueError("الملف يحوي تركيزاً حالياً (" + ", ".join(cur) + "): احذفه. هذا الوضع يستخدم cn_prev وhg_prev فقط")
    missing = [c for c in PREDICTOR_COLS + PREV_COLS if c not in columns]
    if missing:
        raise ValueError("أعمدة ناقصة: " + ", ".join(missing))
    return True


def boot_diff(df, fn_a, fn_b, B=1000, seed=42):
    """فرق مقترن (A − B) بفاصل ثقة bootstrap على مستوى الموقع. fn(indices) -> AUC."""
    rng = np.random.default_rng(seed)
    locs = pd.unique(df["location_id"].values)
    groups = [np.where(df["location_id"].values == l)[0] for l in locs]
    out = []
    for _ in range(B):
        pick = rng.integers(0, len(locs), len(locs))
        idx = np.concatenate([groups[i] for i in pick])
        a, b = fn_a(idx), fn_b(idx)
        if not (np.isnan(a) or np.isnan(b)):
            out.append(a - b)
    if not out:
        return float("nan"), float("nan")
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


PREREG_PREV = ("قاعدة القبول (تُعلن قبل النظر إلى النتائج): تُقبل إضافة الجيولوجيا إذا كان الحد الأدنى "
               "لفاصل الفرق AUC(DRASTIC + التركيز السابق) − AUC(التركيز السابق وحده) أعلى من الصفر.")


def prev_contrast(df, std):
    """ثلاثة متنبئات على مجموعة الاختبار: DRASTIC، و DRASTIC + تركيز سابق، والتركيز السابق وحده.
    لا يوجد أي تعلّم أو ضبط: الدرجات مُعرّفة مسبقاً، لذلك لا يحدث تسرب من التسمية."""
    test = df[df["split"] == "test"].reset_index(drop=True)
    L = STANDARDS[std]
    dr = test["DRASTIC"].values.astype(float)
    cn = test["cn_prev"].values.astype(float); hg = test["hg_prev"].values.astype(float)
    bonus = np.array([min(50.0, hazard_score(c, L["cn"]) + hazard_score(h, L["hg"])) for c, h in zip(cn, hg)])
    hq = np.array([max(hq_pair(c, h, std)) for c, h in zip(cn, hg)])
    score_a = dr
    score_b = dr + bonus
    score_c = hq
    y = test["label"].values
    res = {"n_locations": int(test["location_id"].nunique()), "n_pos": int(test["label"].sum()), "warnings": []}
    if res["n_locations"] < 30:
        res["warnings"].append(f"مواقع الاختبار {res['n_locations']} فقط (أقل من 30): الفاصل واسع جداً")
    if res["n_pos"] < 10:
        res["warnings"].append(f"عدد الحالات الملوثة {res['n_pos']} فقط (أقل من 10)")
    res["auc_drastic"] = auc_rank(y, score_a)
    res["auc_drastic_prev"] = auc_rank(y, score_b)
    res["auc_prev_only"] = auc_rank(y, score_c)
    res["diff_ci"] = boot_diff(test, lambda i: auc_rank(y[i], score_b[i]),
                               lambda i: auc_rank(y[i], score_c[i]))
    lo = res["diff_ci"][0]
    if np.isnan(lo):
        res["verdict"] = "غير قابل للحكم"
    elif lo > 0:
        res["verdict"] = "الجيولوجيا تضيف معلومة فوق التركيز السابق وفق القاعدة المعلنة"
    else:
        res["verdict"] = "لم تثبت الجيولوجيا إضافة فوق التركيز السابق وفق القاعدة المعلنة"
    return res


def tox_with_limits(base, cn, hg, cn_lim, hg_lim):
    """نفس منطق tox_eval لكن بحدود صريحة (لمقارنة البدائل)."""
    cs = hazard_score(cn, cn_lim); hs = hazard_score(hg, hg_lim)
    bonus = min(50.0, cs + hs)
    hq = max((cn / cn_lim) if (cn_lim and cn > 0) else 0.0, (hg / hg_lim) if hg > 0 else 0.0)
    return {"tox": round(base + bonus, 1), "bonus": round(bonus, 2), "hq": round(hq, 3)}


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
    for hg_lim, label in SUDAN_HG_ALTERNATIVES:
        r2 = tox_with_limits(ev["idx"], cn, hg, STANDARDS["SUDAN"]["cn"], hg_lim)
        rows.append({tx("المعيار", "Standard"): "Hg: " + tx(*label),
                     "DRASTIC-Tox": r2["tox"], tx("المكافأة", "Bonus"): r2["bonus"], "max HQ": r2["hq"]})
    st.caption(tx("حد الزئبق السوداني 0.004 وفق ملخص SSMO، ويبقى غير مُتحقَّق منه من الوثيقة الأصلية. الصفوف الأخرى بدائل للمقارنة فقط.",
                  "Sudan Hg limit 0.004 per SSMO summary, not yet verified against the primary document. Other rows are for comparison only."))
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
    rule = st.selectbox(tx("قاعدة القيم تحت حد الكشف (<)", "Rule for values below detection limit (<)"),
                        ["نصف حد الكشف", "حد الكشف", "صفر"], key="dl_rule")
    st.caption(tx("القاعدة افتراض يجب ذكره في العرض. الافتراضي نصف حد الكشف.",
                  "This rule is an assumption and must be stated in the presentation. Default: half DL."))
    for col in ("cn_water_mg_l", "hg_water_mg_l"):
        if col in df.columns:
            df[col] = df[col].map(lambda v: parse_conc(v, rule))
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


def tab_solutions(site, std):
    if site is None:
        st.info(tx("اختر موقعاً أولاً", "Select a site first"))
        return
    st.info(tx("السيناريوهات تخفّض تركيز المصدر فقط. DRASTIC لا يتغير لأنه خاصية جيولوجية للموقع.",
               "Scenarios reduce source concentration only. DRASTIC does not change: it is a site property."))
    st.warning(tx("⚠️ نسب التخفيض مدخلات افتراضية من المستخدم، وليست قيماً مُقاسة أو موثقة.",
                  "⚠️ Reduction percentages are user assumptions, not measured or documented values."))
    c1, c2 = st.columns(2)
    cn_red = c1.slider(tx("تخفيض CN %", "CN reduction %"), 0, 100, 0, 5, key="sc_cn")
    hg_red = c2.slider(tx("تخفيض Hg %", "Hg reduction %"), 0, 100, 0, 5, key="sc_hg")
    base = scenario(site, std)
    sc = scenario(site, std, cn_red, hg_red)
    rows = [{tx("المؤشر", "Metric"): tx("أقصى HQ", "Max HQ"), tx("الحالي", "Current"): base["tox"]["hq"],
             tx("السيناريو", "Scenario"): sc["tox"]["hq"]},
            {tx("المؤشر", "Metric"): tx("تصنيف السمية", "Toxicity class"),
             tx("الحالي", "Current"): lb(base["tox"]["hq_class"]),
             tx("السيناريو", "Scenario"): lb(sc["tox"]["hq_class"])},
            {tx("المؤشر", "Metric"): "DRASTIC-Tox", tx("الحالي", "Current"): base["tox"]["tox"],
             tx("السيناريو", "Scenario"): sc["tox"]["tox"]}]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    {"urgent": st.error, "watch": st.warning, "routine": st.success}[sc["action"]](lb(sc["action"]))


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
    st.caption(tx("التقييم فئوي: الصفر يعني أن التغيير لم يعبر حداً فاصلاً، وليس أن المتغير لا يهم.",
                  "Ratings are categorical: zero means the change did not cross a class boundary, not that the variable is irrelevant."))
    st.subheader("SPSA")
    tot = sum(W_STD.values())
    rt = ratings(site)
    DI = index_of(rt)
    st.dataframe(pd.DataFrame([{"param": k, "Wi": w, "Ri": rt[k],
                                "theor. %": round(w / tot * 100, 2),
                                "effect. %": round(w * rt[k] / DI * 100, 2)} for k, w in W_STD.items()]),
                 hide_index=True, use_container_width=True)
    st.subheader("Monte Carlo")
    st.caption(tx("يمثل هذا عدم اليقين في المدخلات الفيزيائية فقط، وليس عدم اليقين في القياسات المخبرية. A/S/I ثابتة. المتوسط قد يختلف عن القيمة الأساسية بسبب التقييم الفئوي.",
                  "This represents uncertainty in physical inputs only, not laboratory measurement uncertainty. A/S/I are fixed. The mean may differ from the base value due to categorical ratings."))
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
    st.caption(tx("خط الأساس الحاسم: DRASTIC وحده. kappa قرب الصفر = توافق بقدر الصدفة فقط، ولا يكفي لاستنتاج أي شيء مع 9 مواقع.",
                  "Key baseline: DRASTIC alone. Kappa near zero = agreement no better than chance; with 9 sites this cannot support any conclusion."))
    with st.expander(tx("الصفوف المستخدمة", "Rows used")):
        st.dataframe(cal, hide_index=True, use_container_width=True)


def view_predictive(std):
    st.warning(tx("وضع صارم: DRASTIC وحده متنبئ مسموح. لا يُسمح بالتركيز ولا بـDRASTIC-Tox كمتنبئ. "
                  "الحكم يتم على مجموعة الاختبار المستقلة فقط.",
                  "Strict mode: DRASTIC alone is the only allowed predictor. No concentrations or DRASTIC-Tox. "
                  "Verdict is based only on the independent test set."))
    st.info(PREREG_RULE)
    cols = ["location_id", "split", "label"] + PREDICTOR_COLS + ["dist_to_mine_m"]
    sample = pd.DataFrame(columns=cols)
    st.download_button(tx("📥 قالب البيانات المستقلة", "📥 Independent data template"),
                       sample.to_csv(index=False).encode("utf-8-sig"), file_name="independent_template.csv",
                       mime="text/csv")
    up = st.file_uploader("CSV / Excel", type=["csv", "xlsx"], key="pred_up")
    if up is None:
        st.caption(tx("الأعمدة المطلوبة: location_id، split (train/test)، label (0/1)، والمتنبئات الجيولوجية السبعة. "
                      "dist_to_mine_m اختياري وهو المنافس.",
                      "Required: location_id, split (train/test), label (0/1), and the 7 geological predictors. "
                      "dist_to_mine_m is optional and is the competitor."))
        return
    df = pd.read_csv(up) if up.name.endswith(".csv") else pd.read_excel(up)
    try:
        leakage_guard(PREDICTOR_COLS)
        miss = [c for c in ["location_id", "split", "label"] + PREDICTOR_COLS if c not in df.columns]
        if miss:
            st.error(f"{tx('أعمدة ناقصة', 'Missing columns')}: {miss}")
            return
        df["split"] = df["split"].astype(str).str.strip().str.lower()
        df["label"] = df["label"].astype(int)
        if not set(df["label"].unique()) <= {0, 1}:
            st.error(tx("العمود label يجب أن يكون 0 أو 1", "label must be 0 or 1"))
            return
        scores, errs = [], []
        for i, row in df.iterrows():
            try:
                scores.append(index_of(ratings(row.to_dict())))
            except Exception as e:
                errs.append(f"row {i + 1}: {type(e).__name__}: {e}")
                scores.append(np.nan)
        if errs:
            st.error(f"{len(errs)} {tx('صف فشل', 'rows failed')}")
            for e in errs[:10]:
                st.caption(e)
            return
        r = predictive_eval(df, scores)
        for w in r["warnings"]:
            st.warning(w)
        c1, c2, c3 = st.columns(3)
        c1.metric(tx("مواقع الاختبار", "Test locations"), r["n_test_locations"])
        c2.metric(tx("ملوثة في الاختبار", "Positive in test"), r["n_pos"])
        c3.metric("AUC DRASTIC", round(r["auc_drastic"], 3))
        lo, hi = r["ci_drastic"]
        st.write(f"95% CI (location bootstrap): [{lo:.3f}, {hi:.3f}]")
        if r["auc_comp"] is not None:
            st.write(f"AUC {tx('المنافس: القرب من التعدين', 'competitor: distance to mining')} = {round(r['auc_comp'], 3)}")
        st.write(f"**{tx('الحكم', 'Verdict')}:** {r['verdict']}")
    except Exception as e:
        st.error(f"{type(e).__name__}: {e}")


def view_prev(std):
    st.warning(tx("هذا الوضع يقارن ثلاثة متنبئات على مجموعة اختبار مستقلة. التركيز السابق يأتي من حملة منفصلة، "
                  "والهدف تجاوز في حملة لاحقة. التركيز الحالي ممنوع.",
                  "Compares three predictors on an independent test set. Prior concentration is from a separate campaign; "
                  "the target is an exceedance in a later campaign. Current concentration is not allowed."))
    st.info(PREREG_PREV)
    cols = ["location_id", "split", "label"] + PREDICTOR_COLS + PREV_COLS
    st.download_button(tx("📥 قالب اختبار إضافة التركيز السابق", "📥 Prior-concentration test template"),
                       pd.DataFrame(columns=cols).to_csv(index=False).encode("utf-8-sig"),
                       file_name="prev_concentration_template.csv", mime="text/csv")
    confirmed = st.checkbox(tx("أؤكد أن التسمية (label) مأخوذة من حملة لاحقة لم تُستخدم في أي متنبئ",
                               "I confirm the label comes from a later campaign not used in any predictor"),
                            key="prev_confirm")
    up = st.file_uploader("CSV / Excel", type=["csv", "xlsx"], key="prev_up")
    if up is None:
        return
    if not confirmed:
        st.error(tx("يجب تأكيد استقلال التسمية قبل التحليل", "You must confirm label independence first"))
        return
    df = pd.read_csv(up) if up.name.endswith(".csv") else pd.read_excel(up)
    try:
        prev_guard(list(df.columns))
        df["split"] = df["split"].astype(str).str.strip().str.lower()
        df["label"] = df["label"].astype(int)
        if not set(df["label"].unique()) <= {0, 1}:
            st.error("label must be 0 or 1")
            return
        dr, errs = [], []
        for i, row in df.iterrows():
            try:
                dr.append(index_of(ratings(row.to_dict())))
            except Exception as e:
                errs.append(f"row {i + 1}: {type(e).__name__}: {e}")
                dr.append(np.nan)
        if errs:
            st.error(f"{len(errs)} {tx('صف فشل', 'rows failed')}")
            for e in errs[:10]:
                st.caption(e)
            return
        df["DRASTIC"] = dr
        r = prev_contrast(df, std)
        for w in r["warnings"]:
            st.warning(w)
        st.write(f"{tx('مواقع الاختبار', 'Test locations')}: {r['n_locations']} | {tx('ملوثة', 'Positive')}: {r['n_pos']}")
        st.dataframe(pd.DataFrame([
            {tx("المتنبئ", "Predictor"): tx("DRASTIC وحده", "DRASTIC alone"), "AUC": round(r["auc_drastic"], 3)},
            {tx("المتنبئ", "Predictor"): tx("DRASTIC + تركيز سابق", "DRASTIC + prior conc."), "AUC": round(r["auc_drastic_prev"], 3)},
            {tx("المتنبئ", "Predictor"): tx("التركيز السابق وحده", "Prior conc. only"), "AUC": round(r["auc_prev_only"], 3)},
        ]), hide_index=True, use_container_width=True)
        lo, hi = r["diff_ci"]
        st.write(f"{tx('فرق AUC (الجمع − التركيز وحده)', 'AUC difference (combined − conc. only)')}: "
                 f"[{lo:.3f}, {hi:.3f}] 95% (location bootstrap)")
        st.write(f"**{tx('الحكم', 'Verdict')}:** {r['verdict']}")
    except Exception as e:
        st.error(f"{type(e).__name__}: {e}")


def view_agri(ds, std):
    states = list(ds.AGRICULTURAL_DATA)
    c1, c2 = st.columns(2)
    state = c1.selectbox(tx("الولاية", "State"), states, key="ag_state")
    sites = ds.AGRICULTURAL_DATA[state]["sites"]
    key = c2.selectbox(tx("البئر", "Well"), list(sites), key="ag_site")
    w = dict(sites[key])
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


def run_self_tests(ds=None):
    res = []

    def chk(name, cond, detail=""):
        res.append((name, bool(cond), str(detail)))

    base = {"depth_m": 15, "recharge_mm": 20, "slope_pct": 3, "conductivity": 3, "aquifer": "massive_shale",
            "soil": "thin_or_absent", "vadose": "confining_layer", "cn_water_mg_l": 0.025, "hg_water_mg_l": 0.011}
    ev = evaluate(base, "SUDAN")
    chk("A: DRASTIC = 72", ev["idx"] == 72, ev["idx"])
    chk("A: hazard(Hg=0.011, limit=0.004) = 4.39", round(hazard_score(0.011, 0.004), 2) == 4.39)
    chk("A: DRASTIC-Tox = 76.4 (SUDAN Hg=0.004)", ev["tox"]["tox"] == 76.4, ev["tox"]["tox"])
    chk("A: الزيادة 6.1%", ev["tox"]["inc_pct"] == 6.1, ev["tox"]["inc_pct"])
    chk("A: EU = 82.4", evaluate(base, "EU")["tox"]["tox"] == 82.4, evaluate(base, "EU")["tox"]["tox"])
    chk("حدود DRASTIC 23..226", index_of({k: 1 for k in W_STD}) == 23 and
        index_of({"D": 10, "R": 9, "A": 10, "S": 10, "T": 10, "I": 10, "C": 10}) == 226)
    chk("حدود Pesticide 26..256", index_of({k: 1 for k in W_PEST}, W_PEST) == 26 and
        index_of({"D": 10, "R": 9, "A": 10, "S": 10, "T": 10, "I": 10, "C": 10}, W_PEST) == 256)
    chk("WHO: CN = 0.07 يعطي HQ=1", tox_eval(0, 0.07, 0, "WHO")["hq"] == 1.0)
    chk("تصنيف HQ: 1 مطابق، 5.5 مرتفع قليلاً، 11 مرتفع", hq_class(1) == "compliant" and
        hq_class(5.5) == "elevated" and hq_class(11) == "hq_high")
    chk("الميل: 2.0 → 10 و 2.1 → 9", r_T(2.0) == 10 and r_T(2.1) == 9)
    chk("خطأ صريح عند NaN", _raises(lambda: evaluate({**base, "cn_water_mg_l": float("nan")}, "SUDAN")))
    chk("خطأ صريح عند فئة غير معروفة", _raises(lambda: evaluate({**base, "soil": "xyz"}, "SUDAN")))
    chk("parse '<0.001' بقاعدة نصف الحد = 0.0005", parse_conc("<0.001", "نصف حد الكشف") == 0.0005)
    chk("تسرب: التركيز في المتنبئ يُرفض", _raises_msg(lambda: leakage_guard(PREDICTOR_COLS + ["cn_water_mg_l"]), "تسرب"))
    chk("تسرب: DRASTIC-Tox في المتنبئ يُرفض", _raises_msg(lambda: leakage_guard(PREDICTOR_COLS + ["DRASTIC-Tox"]), "تسرب"))
    chk("المتنبئ الجيولوجي وحده مقبول", leakage_guard(PREDICTOR_COLS) is True)
    chk("AUC: فصل تام = 1.0", auc_rank([0, 0, 1, 1], [1, 2, 3, 4]) == 1.0)
    chk("AUC: عكس الفصل = 0.0", auc_rank([0, 0, 1, 1], [4, 3, 2, 1]) == 0.0)
    chk("AUC: كل القيم متعادلة = 0.5", auc_rank([0, 1, 0, 1], [5, 5, 5, 5]) == 0.5)
    chk("إضافة: التركيز الحالي في الملف يُرفض", _raises_msg(lambda: prev_guard(PREDICTOR_COLS + PREV_COLS + ["cn_water_mg_l"]), "تركيزاً حالياً"))
    chk("إضافة: الملف الصحيح مقبول", prev_guard(PREDICTOR_COLS + PREV_COLS) is True)
    _rng = np.random.default_rng(7); _n = 80
    _d = pd.DataFrame({"location_id": [f"S{i}" for i in range(_n)], "split": ["test"] * _n,
                       "label": _rng.integers(0, 2, _n), "DRASTIC": _rng.uniform(40, 200, _n),
                       "cn_prev": 0.01, "hg_prev": 0.001})
    _r = prev_contrast(_d, "SUDAN")
    chk("إضافة: بيانات بلا إشارة لا تُقبل", not (_r["diff_ci"][0] > 0), _r["diff_ci"])
    if ds is not None:
        try:
            cal = calib_frame(ds, "SUDAN")
            p4 = (cal["hq"].values > 1).astype(int)
            chk("ج: قاعدة التجاوز kappa = 1.0", abs(cohen_kappa(cal["y"].values, p4) - 1.0) < 1e-9)
            g = ds.get_site_data("كسلا", "Gash_Upstream")
            eb = evaluate(g, "SUDAN")
            chk("ب: Gash_Upstream = 159 و 159.0 و مكافأة 0", eb["idx"] == 159 and eb["tox"]["tox"] == 159.0 and eb["tox"]["bonus"] == 0)
            chk("مراجعة البيانات الخام: كل الحقول موجودة", not audit_db(ds), audit_db(ds)[:3])
        except Exception as e:
            chk("اختبارات البيانات", False, f"{type(e).__name__}: {e}")
    return res


def _raises_msg(fn, word):
    try:
        fn()
    except ValueError as e:
        return word in str(e)
    return False


def _raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


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
        st.caption(tx("الوحدات الاختيارية غير مستخدمة في v63 بعد.", "Optional modules are not used in v63 yet."))
        if ds is not None:
            issues = audit_db(ds)
            st.caption(tx("مراجعة البيانات: ✅ كل الحقول موجودة" if not issues else f"❌ {len(issues)} حقل مفقود",
                          "Data audit: ✅ all fields present" if not issues else f"❌ {len(issues)} missing fields"))
            for it in issues[:5]:
                st.caption(it)
        if core == "ملف":
            try:
                import drastic_core as _dc
                mism = check_core_consistency(_dc)
                st.caption("✅ drastic_core مطابق للجداول" if not mism else "❌ drastic_core: " + "، ".join(mism))
            except Exception as e:
                st.caption(f"❌ drastic_core: {type(e).__name__}: {e}")
        if st.button(tx("تشغيل الاختبارات الذاتية", "Run self-tests"), key="selftest_btn"):
            st.session_state["selftest"] = run_self_tests(ds)
        for name, ok, detail in st.session_state.get("selftest", []):
            st.caption(("✅ " if ok else "❌ ") + name + ("" if ok else f" — {detail}"))
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
            with t[4]: tab_solutions(site, STD)
            with t[5]: tab_report(site, STD, ev)
            with t[6]: tab_analysis(site, STD)
        elif mode == "agri":
            view_agri(ds, STD)
        elif mode == "verif":
            tab_verification(ds, STD)
        elif mode == "predict":
            view_predictive(STD)
        elif mode == "prev":
            view_prev(STD)
        else:
            st.radio(tx("مصدر الموقع", "Site source"), ["list", "manual"], horizontal=True,
                     format_func=lambda s: tx("موقع من القائمة", "Site from list") if s == "list"
                     else tx("إدخال يدوي", "Manual input"), key="src")
            view_transport(cur_site())
    except Exception as e:
        st.error(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _ds, _err, _ = load_db()
        _all = run_self_tests(_ds)
        for _n, _ok, _d in _all:
            print("PASS" if _ok else "FAIL", _n, _d if not _ok else "")
        print(f"{sum(o for _, o, _ in _all)}/{len(_all)} passed")
        sys.exit(0 if all(o for _, o, _ in _all) else 1)
    main()
