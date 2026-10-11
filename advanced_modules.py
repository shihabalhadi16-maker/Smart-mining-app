"""
advanced_modules.py  v61 - drop-in replacement for v60 (same public names used by app.py)
Requires: drastic_core.py in the same folder.

Public functions kept: calculate_confusion_matrix, model_contaminant_transport,
fetch_satellite_data, calculate_sar, calculate_na_percent, calculate_ec_quality,
calculate_agricultural_drastic, classify_irrigation_water, independent_validation,
calculate_dynamic_risk.
Removed (superseded by drastic_core): CRI/MRI indices, multiplicative DRASTIC-P.
"""
import math
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import drastic_core as dc

HQ_REF = 1000.0
DRASTIC_MAX = 226
NO3_LIMIT = 50.0     # mg/L as NO3 (WHO / EU)


def _score_hq(hq, max_score=30.0):
    """Log hazard score from a hazard quotient; 0 if compliant."""
    if hq <= 1:
        return 0.0
    return min(max_score, max_score * math.log10(hq) / math.log10(HQ_REF))


def _level(idx):
    if idx >= 180: return "مرتفع جدا", "red"
    if idx >= 140: return "مرتفع", "orange"
    if idx >= 100: return "متوسط", "yellow"
    return "منخفض", "green"


# ===================================================== 1. validation metrics
def calculate_confusion_matrix(predicted, actual, threshold=140):
    predicted = np.array(predicted, dtype=float)
    actual = np.array(actual, dtype=int)
    pc = (predicted >= threshold).astype(int)
    tp = int(np.sum((pc == 1) & (actual == 1))); tn = int(np.sum((pc == 0) & (actual == 0)))
    fp = int(np.sum((pc == 1) & (actual == 0))); fn = int(np.sum((pc == 0) & (actual == 1)))
    n = tp + tn + fp + fn
    acc = (tp + tn) / n if n else 0
    prec = tp / (tp + fp) if tp + fp else 0
    rec = tp / (tp + fn) if tp + fn else 0
    spec = tn / (tn + fp) if tn + fp else 0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
    npv = tn / (tn + fn) if tn + fn else 0
    pe = ((tp + fp) * (tp + fn) + (tn + fn) * (tn + fp)) / (n ** 2) if n else 0
    kappa = (acc - pe) / (1 - pe) if (1 - pe) > 0 else 0
    den = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = (tp * tn - fp * fn) / den if den > 0 else 0
    return {"confusion_matrix": {"TP": tp, "TN": tn, "FP": fp, "FN": fn, "Total": n},
            "accuracy": round(acc * 100, 2), "precision": round(prec * 100, 2),
            "recall": round(rec * 100, 2), "specificity": round(spec * 100, 2),
            "f1_score": round(f1 * 100, 2), "npv": round(npv * 100, 2),
            "balanced_accuracy": round((rec + spec) / 2 * 100, 2),
            "kappa": round(kappa, 4), "mcc": round(mcc, 4),
            "youden_j": round(rec - (fp / (fp + tn) if fp + tn else 0), 4),
            "threshold": threshold}


# ===================================================== 2. dynamic (scenario only)
def project_drastic_change(base, years=10, mining=0.05, climate=-0.02, pop=0.03):
    """ILLUSTRATIVE scenario multipliers - no empirical calibration."""
    proj = []
    for y in range(years + 1):
        v = base if y == 0 else min(DRASTIC_MAX, base * (1 + mining * y) * (1 + climate * y)
                                    * (1 + pop * y * 0.5))
        proj.append({"السنة": y, "المؤشر": round(v, 1),
                     "الزيادة_المئوية": round((v - base) / base * 100, 1) if base > 0 else 0})
    return {"base_index": base, "years": years, "projections": proj,
            "final_index": proj[-1]["المؤشر"]}


def calculate_dynamic_risk(base, years, mining, climate, pop, cri0=0, mri0=0):
    """cri0 / mri0 are hazard quotients (conc / limit). Additive log hazard bonus."""
    dp = project_drastic_change(base, years, mining, climate, pop)
    rows = []
    for p in dp["projections"]:
        y = p["السنة"]
        cri = cri0 * (1 + mining * y * 2)
        mri = mri0 * (1 + mining * y * 1.5)
        total = p["المؤشر"] + min(50.0, _score_hq(cri) + _score_hq(mri))
        lvl, col = _level(total)
        rows.append({"السنة": y, "DRASTIC": p["المؤشر"], "CRI": round(cri, 2),
                     "MRI": round(mri, 2), "DRASTIC-Modified": round(total, 1),
                     "المستوى": lvl, "اللون": col})
    return {"drastic_projection": dp, "combined": pd.DataFrame(rows),
            "final_modified": rows[-1]["DRASTIC-Modified"], "final_level": rows[-1]["المستوى"],
            "note": "Scenario illustration only - multipliers are assumptions."}


# ===================================================== 3. transport (Ogata-Banks)
def model_contaminant_transport(initial_conc, k_value, porosity, gradient, distance,
                                source_duration_years, decay_coefficient=0.001,
                                dispersivity=10.0):
    """1-D continuous source, Ogata-Banks (1961) with BOTH terms.
    C/C0 = 0.5*[erfc((x-vt)/(2 sqrt(Dt))) + exp(vx/D) erfc((x+vt)/(2 sqrt(Dt)))]
    Decay applied as exp(-lambda*t) (approximation)."""
    if not (0 < porosity < 1): raise ValueError("Porosity must be between 0 and 1")
    if k_value <= 0: raise ValueError("K must be > 0")
    v = k_value * gradient / porosity
    if v <= 0: return {"error": "Velocity must be > 0"}
    D = max(dispersivity * v, 1e-9)
    rows = []
    for yr in range(1, int(source_duration_years) + 1):
        t = yr * 365.25
        s = 2 * math.sqrt(D * t)
        term1 = math.erfc((distance - v * t) / s)
        term2 = math.exp(v * distance / D) * math.erfc((distance + v * t) / s) \
            if v * distance / D < 600 else 0.0
        ratio = max(0.0, min(1.0, 0.5 * (term1 + term2))) * math.exp(-decay_coefficient * yr)
        rows.append({"السنة": yr, "التركيز (mg/L)": round(initial_conc * ratio, 6),
                     "المسافة المقطوعة (m)": round(v * t, 1),
                     "النسبة من التركيز الأولي %": round(ratio * 100, 2)})
    return {"velocity_m_day": round(v, 6), "velocity_m_year": round(v * 365.25, 3),
            "results": pd.DataFrame(rows)}


# ===================================================== 4. satellite / reanalysis
def fetch_satellite_data(lat, lon, years=3):
    """ERA5 REANALYSIS via Open-Meteo (not satellite imagery). Network code: untested offline."""
    import requests
    bad = lambda msg: {"rainfall_mm": None, "temperature_c": None, "aridity": "خطأ",
                       "ndvi_estimated": None, "source": msg}
    try:
        la, lo = float(lat), float(lon)
    except (ValueError, TypeError):
        return bad("Invalid latitude/longitude")
    if not (-90 <= la <= 90 and -180 <= lo <= 180):
        return bad("Coordinates out of range")
    try:
        end = datetime.now() - timedelta(days=7)
        start = end - timedelta(days=int(365.25 * years))
        r = requests.get("https://archive-api.open-meteo.com/v1/archive", timeout=60, params={
            "latitude": la, "longitude": lo, "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"), "timezone": "Africa/Khartoum",
            "daily": ["precipitation_sum", "temperature_2m_mean", "et0_fao_evapotranspiration"]})
        if r.status_code != 200:
            return bad(f"HTTP {r.status_code}")
        d = r.json().get("daily", {})
        clean = lambda k: [x for x in d.get(k, []) if x is not None]
        rain, temp, et0 = clean("precipitation_sum"), clean("temperature_2m_mean"), clean("et0_fao_evapotranspiration")
        yrs = max(len(rain) / 365.25, 1e-9)
        p_ann = round(sum(rain) / yrs, 1) if rain else None
        pet_ann = sum(et0) / (len(et0) / 365.25) if et0 else None
        ai = round(p_ann / pet_ann, 3) if (p_ann is not None and pet_ann) else None
        if ai is None: arid = "غير محدد"
        elif ai < 0.05: arid = "شديد الجفاف"
        elif ai < 0.2: arid = "جاف"
        elif ai < 0.5: arid = "شبه جاف"
        elif ai < 0.65: arid = "شبه رطب جاف"
        else: arid = "رطب"
        return {"rainfall_mm": p_ann, "temperature_c": round(sum(temp) / len(temp), 1) if temp else None,
                "aridity": arid, "aridity_index": ai, "ndvi_estimated": None,
                "source": "ERA5 reanalysis via Open-Meteo (UNEP aridity index = P/PET)",
                "n_days": len(rain)}
    except Exception as e:
        return bad(f"خطأ: {str(e)[:60]}")


# ===================================================== 5. irrigation water
def calculate_sar(na, ca, mg):
    try:
        na, ca, mg = float(na), float(ca), float(mg)
        if ca + mg <= 0:
            return {"sar": None, "level": "غير محدد", "color": "gray", "action": "بيانات ناقصة"}
        s = dc.sar(na, ca, mg)
        cls = dc.ussl_sodium(s)
        lvl, col, act = {"S1": ("منخفض", "green", "آمن للري"), "S2": ("متوسط", "yellow", "مراقبة دورية"),
                         "S3": ("مرتفع", "orange", "يحتاج معالجة"),
                         "S4": ("مرتفع جدا", "red", "غير مناسب للري")}[cls]
        return {"sar": round(s, 2), "class": cls, "level": lvl, "color": col, "action": act}
    except Exception:
        return {"sar": None, "level": "خطأ", "color": "gray", "action": "بيانات غير صحيحة"}


def calculate_na_percent(na, ca, mg, k=0):
    """Wilcox (1955): Na% = (Na + K) / (Ca + Mg + Na + K) x 100  (fixes v60: K was omitted)."""
    try:
        na, ca, mg, k = float(na), float(ca), float(mg), float(k)
        if na + ca + mg + k <= 0:
            return {"na_percent": None, "level": "غير محدد", "color": "gray", "action": "بيانات ناقصة"}
        p = dc.na_percent(na, k, ca, mg)
        lvl, col, act = (("ممتاز", "green", "آمن تماماً") if p < 20 else
                         ("جيد", "green", "آمن") if p < 40 else
                         ("مقبول", "yellow", "مراقبة") if p < 60 else
                         ("مشكوك", "orange", "يحتاج معالجة") if p < 80 else
                         ("غير مناسب", "red", "غير صالح للري"))
        return {"na_percent": round(p, 2), "level": lvl, "color": col, "action": act}
    except Exception:
        return {"na_percent": None, "level": "خطأ", "color": "gray", "action": "بيانات غير صحيحة"}


def calculate_ec_quality(ec):
    try:
        ec = float(ec)
        cls = dc.ussl_salinity(ec)
        lvl, col, act = {"C1": ("C1 - ممتاز", "green", "آمن للري"), "C2": ("C2 - جيد", "green", "آمن"),
                         "C3": ("C3 - مقبول", "yellow", "مراقبة"),
                         "C4": ("C4 - مشكوك/عالي", "orange", "يحتاج معالجة ومحاصيل متحملة")}[cls]
        return {"ec": ec, "class": cls, "level": lvl, "color": col, "action": act}
    except Exception:
        return {"ec": None, "level": "خطأ", "color": "gray", "action": "بيانات غير صحيحة"}


def classify_irrigation_water(sar_result, na_result, ec_result):
    """Real USSL class (from EC and SAR) + FAO 29 hazards. v60 used a colour-score
    that printed class labels unrelated to the actual EC/SAR."""
    ec, s = ec_result.get("ec"), sar_result.get("sar")
    if ec is None or s is None:
        return {"class": "N/A", "level": "غير محدد", "color": "gray", "action": "بيانات ناقصة"}
    c, sd = dc.ussl_salinity(ec), dc.ussl_sodium(s)
    sal, inf = dc.fao_salinity_hazard(ec), dc.fao_infiltration_hazard(s, ec)
    worst = max(int(c[1]), int(sd[1]))
    lvl, col, act = {1: ("ممتاز", "green", "آمن لجميع المحاصيل"),
                     2: ("جيد", "green", "آمن لمعظم المحاصيل"),
                     3: ("مقبول", "yellow", "آمن لمحاصيل متحملة للملوحة"),
                     4: ("مشكوك", "orange", "يحتاج معالجة/غسيل وتصريف")}[worst]
    if "severe" in (sal, inf) and worst < 4:
        lvl, col, act = "مشكوك", "orange", "خطر شديد حسب FAO 29 (ملوحة أو تسرب)"
    return {"class": f"{c}-{sd}", "level": lvl, "color": col, "action": act,
            "fao_salinity_hazard": sal, "fao_infiltration_hazard": inf,
            "na_class": na_result.get("level")}


# ===================================================== 6. agricultural (experimental)
def calculate_agricultural_drastic(base_drastic, no3_mg_l, fertilizer_use=0.5,
                                   land_use_factor=0.5, depth_m=15, alpha_agri=0.50, max_cap=300):
    """EXPERIMENTAL additive nitrate bonus: base + log score of NO3/50 (0 if compliant).
    fertilizer_use, land_use_factor, depth_m, alpha_agri, max_cap are ignored (kept for
    compatibility; the old factors had no source). Prefer Pesticide DRASTIC for the
    agricultural vulnerability and use NO3 only as VALIDATION data - using it as an input
    and then validating against it is circular."""
    try:
        hq = float(no3_mg_l) / NO3_LIMIT
    except (ValueError, TypeError):
        hq = 0.0
    bonus = _score_hq(hq)
    total = base_drastic + bonus
    lvl, col = _level(total)
    return {"base_drastic": base_drastic, "nri": round(hq, 3), "drastic_agri": round(total, 1),
            "modifier": round(total / base_drastic, 3) if base_drastic > 0 else 1.0,
            "increase_pct": round(bonus / base_drastic * 100, 1) if base_drastic > 0 else 0,
            "level": lvl, "color": col, "nri_details": {"no3_ratio": round(hq, 3), "no3_limit": NO3_LIMIT},
            "alpha_agri": 1.0, "max_cap": None,
            "warning": "Do not validate against nitrate if nitrate is an input."}


# ===================================================== 7. independent validation
def _youden_threshold(score, y):
    s = np.sort(np.unique(score))
    cands = np.concatenate(([s[0] - 1], (s[:-1] + s[1:]) / 2, [s[-1] + 1]))
    best_j, best = -2, []
    for th in cands:
        p = score >= th
        j = (p[y == 1].mean() if (y == 1).any() else 0) - (p[y == 0].mean() if (y == 0).any() else 0)
        if j > best_j + 1e-12: best_j, best = j, [th]
        elif abs(j - best_j) <= 1e-12: best.append(th)
    return float(np.median(best)), best_j


def independent_validation(df, drastic_col, actual_col, alpha_range=(0.0, 1.0, 0.1),
                           beta_range=(0.0, 1.0, 0.1), test_size=0.3, random_state=42):
    """Stratified hold-out. Weights (alpha->CN, beta->Hg) AND threshold are fitted on
    training sites only; same ADDITIVE log model as drastic_core (v60 used a different,
    multiplicative formula capped at 230). With n~11 the test set is 3-4 sites:
    treat as a demonstration, not as evidence."""
    n = len(df)
    y_all = df[actual_col].astype(int).values
    if n < 6 or len(set(y_all)) < 2:
        return {"error": "Need >= 6 samples with both classes"}
    L = dc.LIMITS_MG_L["EU"]
    cn = np.array([dc.hazard_score(float(v), L["cn"], HQ_REF) for v in df.get("cn_water_mg_l", [0.0] * n)])
    hg = np.array([dc.hazard_score(float(v), L["hg"], HQ_REF) for v in df.get("hg_water_mg_l", [0.0] * n)])
    base = df[drastic_col].astype(float).values
    rng = np.random.default_rng(random_state)
    test = []
    for c in (0, 1):
        idx = np.where(y_all == c)[0]; rng.shuffle(idx)
        k = min(max(1, int(round(len(idx) * test_size))), max(len(idx) - 1, 0))
        test += list(idx[:k])
    test = np.array(sorted(test)); train = np.array([i for i in range(n) if i not in set(test)])
    alphas = np.arange(alpha_range[0], alpha_range[1] + 1e-9, alpha_range[2])
    betas = np.arange(beta_range[0], beta_range[1] + 1e-9, beta_range[2])
    best = None
    for a in alphas:
        for b in betas:
            sc = base[train] + np.minimum(50.0, a * cn[train] + b * hg[train])
            th, j = _youden_threshold(sc, y_all[train])
            key = (round(j, 6), -abs(a - 1) - abs(b - 1))      # ties -> nearest equal weights
            if best is None or key > best[0]:
                best = (key, a, b, th)
    _, a, b, th = best
    m_tr = calculate_confusion_matrix(base[train] + np.minimum(50.0, a * cn[train] + b * hg[train]), y_all[train], th)
    m_te = calculate_confusion_matrix(base[test] + np.minimum(50.0, a * cn[test] + b * hg[test]), y_all[test], th)
    return {"best_alpha": round(float(a), 2), "best_beta": round(float(b), 2), "threshold": round(th, 1),
            "train_kappa": m_tr["kappa"], "test_kappa": m_te["kappa"],
            "test_accuracy": m_te["accuracy"], "test_recall": m_te["recall"], "test_metrics": m_te,
            "n_train": len(train), "n_test": len(test),
            "alpha_range": alpha_range[:2], "beta_range": beta_range[:2]}
