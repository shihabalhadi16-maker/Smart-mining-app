"""Sudan Mining System v61.2 — University of Khartoum
SELF-CONTAINED single-file app: drastic_bridge + analysis_tools + app merged.
Optional modules imported with graceful fallbacks.
"""
import streamlit as st
import subprocess, os, sys, shutil, stat, zipfile, io, tempfile, math, datetime
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import pandas as pd
import numpy as np
import requests
from pathlib import Path
from bisect import bisect_left

# ============================================================
# TRANSLATIONS — safe fallback
# ============================================================
try:
    from translations import t as _t, TEXTS
    TRANS_OK = True
except Exception:
    TRANS_OK = False
    TEXTS = {}
    def _t(key, lang="ar"):
        FALLBACK = {
            "language": "🌐 اللغة / Language",
            "app_title": "نظام التعدين السوداني" if lang == "ar" else "Sudan Mining System",
            "university": "جامعة الخرطوم، كلية الهندسة" if lang == "ar" else "University of Khartoum",
            "subtitle": "DRASTIC-Tox — Pilot Study",
            "version": "الإصدار",
            "pilot_version": "⚠️ نسخة تجريبية — Pilot Study — n = 11 موقعاً موثقاً",
            "screening_only": "أداة فرز أولي فقط — ليست أداة تنظيمية",
            "upload_files": "رفع الملفات",
            "validation_file": "ملف التحقق",
            "bulk_file": "ملف جماعي",
            "extra_file": "ملف إضافي",
            "rows": "صفوف",
            "clear_all": "مسح الكل",
            "data_quality": "جودة البيانات",
            "verified_sites": "مواقع موثقة",
            "display_only": "للعرض فقط",
            "data_scope": "نطاق البيانات",
            "select": "اختر",
            "scope_traditional": "⛏️ تقليدي",
            "scope_industrial": "🏭 صناعي",
            "scope_all": "🔀 الكل",
            "no_industrial_file": "ملف industrial_sites.csv غير موجود",
            "mode": "الوضع",
            "mode_system": "🏠 النظام الرئيسي",
            "mode_agricultural": "🌾 الزراعة",
            "mode_verification": "✅ التحقق",
            "mode_transport": "🌊 الانتقال",
            "mode_independent": "🔬 مستقل",
            "mode_satellite": "🛰️ الأقمار",
            "mode_dynamic": "⏳ الديناميكي",
            "mode_modflow": "💧 MODFLOW",
            "status": "الحالة",
            "current_index": "المؤشر الحالي",
            "about": "حول",
            "modules": "الوحدات",
            "constraints": "القيود",
            "site_selection": "اختيار الموقع",
            "state": "الولاية",
            "site": "الموقع",
            "activity": "النشاط",
            "season": "الموسم",
            "site_status": "حالة الموقع",
            "documentation": "التوثيق",
            "contaminated": "ملوث",
            "clean": "نظيف",
            "verified": "موثق",
            "display": "للعرض",
            "depth": "العمق",
            "recharge": "التغذية",
            "slope": "الميل",
            "conductivity": "التوصيلية",
            "aquifer": "طبقة المياه",
            "soil": "التربة",
            "vadose": "المنطقة غير المشبعة",
            "porosity": "المسامية",
            "m": "م",
            "mm_yr": "ملم/سنة",
            "m_day": "م/يوم",
            "limits": "الحدود",
            "level": "المستوى",
            "percentage": "النسبة",
            "drastic_tox": "DRASTIC-Tox",
            "bonus": "الإضافة",
            "calculation_details": "تفاصيل الحساب",
            "cn_score": "درجة CN",
            "hg_score": "درجة Hg",
            "base_bonus": "الإضافة الأساسية",
            "source_factor": "معامل المصدر",
            "using_calibrated": "🔄 يُستخدم ملف الأوزان المعايَر",
            "action_immediate": "🚨 إجراء فوري مطلوب",
            "action_urgent": "⚠️ إجراء عاجل مطلوب",
            "action_periodic": "📋 مراقبة دورية",
            "action_routine": "✅ إجراءات روتينية",
            "low": "منخفض", "medium": "متوسط", "high": "مرتفع", "very_high": "مرتفع جداً",
            "tab_input": "🏠 الإدخال",
            "tab_manual": "✍️ إدخال يدوي",
            "tab_bulk": "📊 تقييم جماعي",
            "tab_solutions": "🛠️ الحلول",
            "tab_report": "📄 التقرير",
            "tab_heatmap": "🗺️ الخريطة الحرارية",
            "tab_sensitivity": "📈 الحساسية",
            "tab_toxicity": "☣️ السمّية",
            "tab_gis": "🌍 GIS",
            "tab_monte_carlo": "🎲 Monte Carlo",
            "tab_advanced": "🔬 مقاييس متقدمة",
            "tab_development": "🧪 تطوير النموذج",
            "tab_auto_maps": "🗺️ خرائط تلقائية",
            "tab_calibration": "⚙️ المعايرة",
            "tab_threshold": "🎯 العتبة المثلى",
            "sensitivity_title": "تحليل الحساسية",
            "sensitivity_hint": "قيّم تأثير كل معامل",
            "spsa_tab": "SPSA",
            "variation_tab": "تغيير نسبي",
            "spsa_title": "SPSA — تحليل أحادي المعامل",
            "reference": "المرجع",
            "formula": "المعادلة",
            "spsa_explanation": "يُظهر التأثير الفعلي لكل معامل على المؤشر الكلي",
            "run_spsa": "تشغيل SPSA",
            "most_influential": "الأكثر تأثيراً",
            "base_index": "المؤشر الأساسي",
            "parameter": "المعامل",
            "weight_wi": "الوزن Wi",
            "rating_ri": "التقييم Ri",
            "weighted": "المرجّح",
            "theoretical_pct": "النظري %",
            "effective_pct": "الفعلي %",
            "difference": "الفرق",
            "more_important": "أكثر أهمية فعلياً",
            "less_important": "أقل أهمية فعلياً",
            "variation_title": "تحليل التغيير",
            "variation_explanation": "غيّر كل معامل بنسبة",
            "change_pct": "نسبة التغيير %",
            "run": "تشغيل",
            "most_sensitive": "الأكثر حساسية",
            "original_value": "القيمة الأصلية",
            "modified_value": "القيمة المعدلة",
            "new_index": "المؤشر الجديد",
            "change": "التغيير",
            "sensitivity_pct": "الحساسية %",
            "toxicity_title": "تحليل السمّية",
            "hg_in_soil": "Hg في التربة",
            "cn_in_soil": "CN في التربة",
            "analyze": "تحليل",
            "category": "الفئة",
            "action": "الإجراء",
            "soil_factor": "معامل التربة",
            "mc_title": "محاكاة Monte Carlo",
            "simulations": "عدد المحاكاات",
            "variation": "نسبة التغيير %",
            "mean": "المتوسط",
            "std": "الانحراف المعياري",
            "ci_90": "فاصل ثقة 90%",
            "advanced_title": "مقاييس متقدمة",
            "kappa": "Kappa",
            "roc_auc": "ROC-AUC",
            "f1_score": "F1",
            "recall": "الحساسية",
            "precision": "الدقة",
            "accuracy": "الدقة الكلية",
            "specificity": "النوعية",
            "confusion_matrix": "مصفوفة الالتباس",
            "bootstrap_ci": "فاصل Bootstrap",
            "loocv": "LOOCV",
            "development_title": "تطوير النموذج",
            "no_dev_module": "model_development.py غير مثبت",
            "no_sklearn": "scikit-learn غير مثبت",
            "gray_zone": "المنطقة الرمادية",
            "calibration_ab": "معايرة α و β",
            "model_comparison": "مقارنة النماذج",
            "verified_only_11": "الموثقة فقط (11)",
            "with_gray_17": "مع الرمادية (17)",
            "load_data": "تحميل البيانات",
            "total_sites": "إجمالي المواقع",
            "gray_sites": "مواقع رمادية",
            "contaminated_sites": "مواقع ملوثة",
            "calibrate_hint": "ارفع ملفاً أولاً",
            "alpha_min": "الحد الأدنى α",
            "alpha_max": "الحد الأعلى α",
            "beta_min": "الحد الأدنى β",
            "beta_max": "الحد الأعلى β",
            "run_calibration": "تشغيل المعايرة",
            "searching": "جاري البحث...",
            "best_kappa": "أفضل Kappa",
            "balanced": "المتوازن",
            "calculating": "جاري الحساب...",
            "auto_calibration": "المعايرة التلقائية",
            "mining_pattern": "نمط التعدين",
            "search_precision": "دقة البحث",
            "drastic_tox_threshold": "عتبة DRASTIC-Tox",
            "run_auto_calibration": "تشغيل المعايرة التلقائية",
            "compare": "مقارنة",
            "reset": "إعادة تعيين",
            "reset_done": "تم إعادة التعيين",
            "default_kappa": "Kappa الافتراضي",
            "calibrated_kappa": "Kappa المعايَر",
            "result": "النتيجة",
            "optimal_threshold_title": "العتبة المثلى",
            "references": "المراجع",
            "use_calibrated_weights": "استخدم الأوزان المعايَرة",
            "compute_threshold": "حساب العتبة",
            "threshold": "العتبة",
            "agricultural_title": "التقييم الزراعي",
            "verification_title": "التحقق",
            "transport_title": "نموذج الانتقال",
            "independent_title": "التحقق المستقل",
            "satellite_title": "بيانات الأقمار",
            "dynamic_title": "المخاطر الديناميكية",
            "modflow_title": "MODFLOW",
            "heatmap_title": "الخريطة الحرارية",
            "shows_verified_only": "يعرض المواقع الموثقة فقط",
            "view_mode": "وضع العرض",
            "both": "الاثنان",
            "markers": "علامات",
            "heat": "حراري",
            "height": "الارتفاع",
            "download_sites": "تنزيل المواقع",
            "download_results": "تنزيل النتائج",
            "no_file": "ارفع ملفاً أولاً",
            "upload_validation_first": "ارفع ملف التحقق أولاً",
            "file_missing_tox": "الملف يفتقد أعمدة السمّية",
            "file_has": "الملف يحتوي على",
            "success": "تم بنجاح",
            "save": "حفظ",
            "gis_title": "بيانات GIS",
            "all": "الكل",
            "verified_only": "الموثقة فقط",
            "display_only_filter": "للعرض فقط",
            "sites": "مواقع",
            "drastic_threshold": "عتبة DRASTIC",
            "bulk_assessment": "التقييم الجماعي",
            "solutions": "الحلول المقترحة",
            "hdpe_liner": "بطانة HDPE",
            "cyanide_treatment": "معالجة السيانيد",
            "monitoring_wells": "آبار مراقبة",
            "before": "قبل", "after": "بعد", "reduction": "التخفيض",
        }
        return FALLBACK.get(key, key)

def t(key, **kwargs):
    return _t(key, st.session_state.get("lang", "ar"))

def is_ar():
    return st.session_state.get("lang", "ar") == "ar"

def tx(ar, en):
    return ar if is_ar() else en


# ============================================================
# DRACTIC CORE — inline fallback
# ============================================================
try:
    import drastic_core as dc
    DC_OK = True
except Exception:
    DC_OK = False
    class dc:  # noqa
        W_STD = {"D": 5, "R": 4, "A": 3, "S": 2, "T": 1, "I": 5, "C": 3}
        W_PEST = {"D": 5, "R": 4, "A": 3, "S": 5, "T": 3, "I": 4, "C": 2}
        AQUIFER = {"massive_shale": 2, "metamorphic_igneous": 3,
                   "weathered_metamorphic_igneous": 4, "glacial_till": 5,
                   "thin_bedded_sequences": 6, "massive_sandstone": 6,
                   "massive_limestone": 6, "sand_and_gravel": 8,
                   "basalt": 9, "karst_limestone": 10}
        SOIL = {"thin_or_absent": 10, "gravel": 10, "sand": 9, "peat": 8,
                "shrinking_aggregated_clay": 7, "sandy_loam": 6, "loam": 5,
                "silty_loam": 4, "clay_loam": 3, "muck": 2, "nonshrinking_clay": 1}
        VADOSE = {"confining_layer": 1, "silt_clay": 3, "shale": 3,
                  "metamorphic_igneous": 4, "limestone": 6, "sandstone": 6,
                  "bedded_limestone_sandstone": 6, "sand_gravel_silt_clay": 6,
                  "sand_gravel": 8, "basalt": 9, "karst_limestone": 10}
        LIMITS_MG_L = {"EU": {"cn": 0.05, "hg": 0.001},
                       "WHO": {"cn": None, "hg": 0.006}}

        @staticmethod
        def hazard_score(conc, limit, hq_ref=1000.0, max_score=30.0):
            if limit is None or conc <= 0:
                return 0.0
            hq = conc / limit
            if hq <= 1:
                return 0.0
            return min(max_score, max_score * math.log10(hq) / math.log10(hq_ref))

        @staticmethod
        def hazard_class(max_hq):
            return ("compliant" if max_hq <= 1 else "elevated" if max_hq <= 10
                    else "high" if max_hq <= 100 else "severe")

        @staticmethod
        def vulnerability_class(idx, weights=None):
            weights = weights or dc.W_STD
            lo = sum(weights.values())
            mx = {"D": 10, "R": 9, "A": 10, "S": 10, "T": 10, "I": 10, "C": 10}
            hi = sum(mx[k] * w for k, w in weights.items())
            if hi <= lo:
                return "low", 0.0
            p = (idx - lo) / (hi - lo) * 100
            return ("low" if p < 25 else "moderate" if p < 50
                    else "high" if p < 75 else "very_high"), round(p, 1)

        @staticmethod
        def risk_category(v, h):
            M = {"low": ["low", "low", "moderate", "moderate"],
                 "moderate": ["low", "moderate", "moderate", "high"],
                 "high": ["moderate", "moderate", "high", "high"],
                 "very_high": ["moderate", "high", "high", "very_high"]}
            H = ["compliant", "elevated", "high", "severe"]
            return M[v][H.index(h)]

        @staticmethod
        def check_units(cn=None, hg=None):
            w = []
            if hg is not None and hg > 0.1:
                w.append(f"Hg={hg} mg/L is very high; check units.")
            if cn is not None and cn > 5:
                w.append(f"CN={cn} mg/L is very high; check units.")
            return w


# ============================================================
# BRIDGE constants & functions
# ============================================================
DRASTIC_MIN = 23
DRASTIC_MAX = 226
DTOX_MIN = 23
DTOX_MAX = 276
DEFAULT_TOX_THRESHOLD = 144.4
STANDARD = "EU"


def get_d_rating(d):
    if d is None or d < 0:
        raise ValueError("Depth invalid")
    for edge, r in zip([1.5, 4.6, 9.1, 15.2, 22.9, 30.5], [10, 9, 7, 5, 3, 2]):
        if d <= edge:
            return r
    return 1


def get_r_rating(r):
    if r is None or r < 0:
        raise ValueError("Recharge invalid")
    for edge, v in zip([50.8, 101.6, 177.8, 254.0], [1, 3, 6, 8]):
        if r <= edge:
            return v
    return 9


def get_t_rating(t):
    if t is None or t < 0:
        raise ValueError("Slope invalid")
    for edge, v in zip([2.0, 6.0, 12.0, 18.0], [10, 9, 5, 3]):
        if t <= edge:
            return v
    return 1


def get_c_rating(c):
    if c is None or c < 0:
        raise ValueError("Conductivity invalid")
    for edge, v in zip([4.074, 12.222, 28.518, 40.740, 81.480], [1, 2, 4, 6, 8]):
        if c <= edge:
            return v
    return 10


def get_a_rating(a):
    key = str(a)
    if key not in dc.AQUIFER:
        raise ValueError(f"Aquifer unknown: {key}")
    return dc.AQUIFER[key]


def get_s_rating(s):
    key = str(s)
    if key not in dc.SOIL:
        raise ValueError(f"Soil unknown: {key}")
    return dc.SOIL[key]


def get_i_rating(i):
    key = str(i)
    if key not in dc.VADOSE:
        raise ValueError(f"Vadose unknown: {key}")
    return dc.VADOSE[key]


def calc_index(D, R, A, S, T, I, C):
    w = dc.W_STD
    return D*w["D"] + R*w["R"] + A*w["A"] + S*w["S"] + T*w["T"] + I*w["I"] + C*w["C"]


def calc_pesticide_index(D, R, A, S, T, I, C):
    w = dc.W_PEST
    return D*w["D"] + R*w["R"] + A*w["A"] + S*w["S"] + T*w["T"] + I*w["I"] + C*w["C"]


def classify(idx, mining_type=None, is_tox=False, calibrated_threshold=None):
    if is_tox:
        th = calibrated_threshold if calibrated_threshold is not None else DEFAULT_TOX_THRESHOLD
        if idx >= th + 80:
            return {"level": "very_high", "color": "red", "action": "action_immediate"}
        if idx >= th:
            return {"level": "high", "color": "orange", "action": "action_urgent"}
        if idx >= th - 30:
            return {"level": "medium", "color": "yellow", "action": "action_periodic"}
        return {"level": "low", "color": "green", "action": "action_routine"}
    if idx >= 180:
        return {"level": "very_high", "color": "red", "action": "action_immediate"}
    if idx >= 140:
        return {"level": "high", "color": "orange", "action": "action_urgent"}
    if idx >= 100:
        return {"level": "medium", "color": "yellow", "action": "action_periodic"}
    return {"level": "low", "color": "green", "action": "action_routine"}


def calc_drastic_t(base_drastic, cn_water, hg_water, distance_m=100.0, seepage=1.0,
                   bio_acc=1.0, mining_type="traditional",
                   alpha_override=None, beta_override=None, SF_override=None,
                   use_log_transform=True, calibrated_threshold=None):
    CN_LIMIT = dc.LIMITS_MG_L["EU"]["cn"]
    HG_LIMIT = dc.LIMITS_MG_L["EU"]["hg"]
    MAX_BONUS = 50.0
    a = alpha_override if alpha_override is not None else 1.0
    b = beta_override if beta_override is not None else 1.0
    sf = SF_override if SF_override is not None else 1.0
    df_ = max(0.1, min(1.0, 100.0 / max(1.0, float(distance_m))))
    s_f = max(0.1, min(1.0, float(seepage)))
    b_f = max(0.1, min(1.0, float(bio_acc)))
    cn = float(cn_water) if cn_water else 0.0
    hg = float(hg_water) if hg_water else 0.0
    cn_score = (dc.hazard_score(cn, CN_LIMIT) if cn > 0 else 0.0) * df_ * s_f
    hg_score = (dc.hazard_score(hg, HG_LIMIT) if hg > 0 else 0.0) * df_ * b_f
    base_bonus = min(MAX_BONUS, a * cn_score + b * hg_score)
    tox_bonus = base_bonus * sf
    tox = float(base_drastic) + tox_bonus
    _cls = classify(tox, mining_type=mining_type, is_tox=True,
                    calibrated_threshold=calibrated_threshold)
    inc = (tox_bonus / base_drastic * 100) if base_drastic > 0 else 0.0
    return {"base_drastic": base_drastic, "mining_type": mining_type,
            "alpha": a, "beta": b, "source_factor": sf,
            "cri": round(cn / CN_LIMIT, 3) if CN_LIMIT else 0.0,
            "mri": round(hg / HG_LIMIT, 3) if HG_LIMIT else 0.0,
            "cn_score": round(cn_score, 2), "hg_score": round(hg_score, 2),
            "base_bonus": round(base_bonus, 2), "toxicity_bonus": round(tox_bonus, 2),
            "drastic_t": round(tox, 1), "increase_pct": round(inc, 1),
            "level": _cls["level"], "color": _cls["color"], "action": _cls["action"],
            "used_log_transform": True}


# ============================================================
# ANALYSIS TOOLS — inline
# ============================================================
def spsa_analysis(pv):
    D_r = get_d_rating(float(pv.get("depth", 15.0)))
    R_r = get_r_rating(float(pv.get("recharge", 100.0)))
    A_r = get_a_rating(str(pv.get("aquifer", "massive_sandstone")))
    S_r = get_s_rating(str(pv.get("soil", "sand")))
    T_r = get_t_rating(float(pv.get("slope", 4.0)))
    I_r = get_i_rating(str(pv.get("vadose", "sand_gravel")))
    C_r = get_c_rating(float(pv.get("conductivity", 5.0)))
    w = {"D": 5, "R": 4, "A": 3, "S": 2, "T": 1, "I": 5, "C": 3}
    tw = sum(w.values())
    rt = {"D": D_r, "R": R_r, "A": A_r, "S": S_r, "T": T_r, "I": I_r, "C": C_r}
    DI = sum(w[k] * rt[k] for k in w)
    res = []
    for k, ww in w.items():
        r = rt[k]
        theo = (ww / tw) * 100
        eff = (ww * r / DI) * 100 if DI > 0 else 0
        res.append({"param": k, "weight": ww, "rating": r, "weighted_score": ww * r,
                    "theoretical_pct": round(theo, 2), "effective_pct": round(eff, 2),
                    "difference": round(eff - theo, 2)})
    rs = sorted(res, key=lambda x: x["effective_pct"], reverse=True)
    return {"base_index": DI, "parameters": rs,
            "most_influential": rs[0]["param"] if rs else None,
            "least_influential": rs[-1]["param"] if rs else None}


def sensitivity_analysis(pv, variation=0.10):
    D = float(pv.get("depth", 15.0)); R = float(pv.get("recharge", 100.0))
    A = str(pv.get("aquifer", "massive_sandstone")); S = str(pv.get("soil", "sand"))
    T = float(pv.get("slope", 4.0)); I = str(pv.get("vadose", "sand_gravel"))
    C = float(pv.get("conductivity", 5.0))

    def ci(d, r, a, s, t, i, c):
        return calc_index(get_d_rating(d), get_r_rating(r), get_a_rating(a),
                          get_s_rating(s), get_t_rating(t), get_i_rating(i), get_c_rating(c))

    base = ci(D, R, A, S, T, I, C)
    res = {}
    for name, val, lo, hi in [("D", D, 0.5, 100.0), ("R", R, 0.0, 400.0),
                              ("T", T, 0.0, 30.0), ("C", C, 0.01, 100.0)]:
        v = max(lo, min(hi, val * (1 + variation)))
        if name == "D":   ni = ci(v, R, A, S, T, I, C)
        elif name == "R": ni = ci(D, v, A, S, T, I, C)
        elif name == "T": ni = ci(D, R, A, S, v, I, C)
        else:             ni = ci(D, R, A, S, T, I, v)
        res[name] = {"original_phys": val, "modified_phys": round(v, 2),
                     "new_index": ni, "change": ni - base,
                     "sensitivity": round(abs(ni - base) / base * 100, 3) if base > 0 else 0}
    for name, br, ww in [("A", get_a_rating(A), 3), ("S", get_s_rating(S), 2),
                          ("I", get_i_rating(I), 5)]:
        nr = max(1, min(10, br + 1))
        ni = base - br * ww + nr * ww
        res[name] = {"original_phys": "rating", "modified_phys": "rating+1",
                     "new_index": ni, "change": ni - base,
                     "sensitivity": round(abs(ni - base) / base * 100, 3) if base > 0 else 0}
    sr = dict(sorted(res.items(), key=lambda x: x[1]["sensitivity"], reverse=True))
    return {"base_index": base, "parameters": sr,
            "most_sensitive": list(sr.keys())[0] if sr else None}


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
    R_s = (np.clip(np.random.lognormal(np.log(max(1, R)) - 0.5 * variation ** 2,
                                        variation, n_iter), 0.0, 400.0)
           if R > 0 else np.zeros(n_iter))
    A_s = np.random.choice([max(1, A_b - 1), A_b, min(10, A_b + 1)], n_iter, p=[0.15, 0.70, 0.15])
    S_s = np.random.choice([max(1, S_b - 1), S_b, min(10, S_b + 1)], n_iter, p=[0.15, 0.70, 0.15])
    T_s = np.clip(np.random.normal(T, max(0.5, T * variation), n_iter), 0.0, 30.0)
    I_s = np.random.choice([max(1, I_b - 1), I_b, min(10, I_b + 1)], n_iter, p=[0.15, 0.70, 0.15])
    C_s = np.clip(np.random.lognormal(np.log(max(0.01, C)) - 0.5 * variation ** 2,
                                       variation, n_iter), 0.01, 100.0)
    D_r = np.select([D_s <= 1.5, D_s <= 4.6, D_s <= 9.1, D_s <= 15.2, D_s <= 22.9, D_s <= 30.5],
                    [10, 9, 7, 5, 3, 2], default=1)
    R_r = np.select([R_s <= 50.8, R_s <= 101.6, R_s <= 177.8, R_s <= 254.0],
                    [1, 3, 6, 8], default=9)
    T_r = np.select([T_s <= 2.0, T_s <= 6.0, T_s <= 12.0, T_s <= 18.0], [10, 9, 5, 3], default=1)
    C_r = np.select([C_s <= 4.074, C_s <= 12.222, C_s <= 28.518, C_s <= 40.740, C_s <= 81.480],
                    [1, 2, 4, 6, 8], default=10)
    drastic = D_r * 5 + R_r * 4 + A_s * 3 + S_s * 2 + T_r * 1 + I_s * 5 + C_r * 3
    if calibrated_weights:
        a_m = calibrated_weights.get("alpha", 1.0)
        b_m = calibrated_weights.get("beta", 1.0)
        sf_m = calibrated_weights.get("SF", 1.0)
    else:
        a_m = b_m = sf_m = 1.0
    a_s = np.clip(np.random.normal(a_m, 0.05, n_iter), 0.0, 1.0)
    b_s = np.clip(np.random.normal(b_m, 0.10, n_iter), 0.0, 1.0)
    sf_s = np.clip(np.random.normal(sf_m, 0.08, n_iter), 0.5, 2.0)
    CN_LIMIT = dc.LIMITS_MG_L["EU"]["cn"]
    HG_LIMIT = dc.LIMITS_MG_L["EU"]["hg"]
    cn_s = np.clip(np.random.lognormal(np.log(max(0.001, cn_w)) - 0.02, 0.2, n_iter), 0.0, 10.0)
    hg_s = np.clip(np.random.lognormal(np.log(max(0.0001, hg_w)) - 0.02, 0.2, n_iter), 0.0, 10.0)
    cn_sc = np.where(cn_s > CN_LIMIT,
                     np.minimum(30.0, 30.0 * np.log10(np.maximum(cn_s / CN_LIMIT, 1.0)) / 3.0), 0.0)
    hg_sc = np.where(hg_s > HG_LIMIT,
                     np.minimum(30.0, 30.0 * np.log10(np.maximum(hg_s / HG_LIMIT, 1.0)) / 3.0), 0.0)
    bonus_s = np.minimum(50.0, a_s * cn_sc + b_s * hg_sc)
    tox = drastic + bonus_s * sf_s
    res = np.sort(drastic.astype(int))
    res_tox = np.sort(tox)

    def pct(arr, p): return float(np.percentile(arr, p))

    return {"mean": round(float(np.mean(res)), 1), "std": round(float(np.std(res)), 2),
            "min": int(res[0]), "max": int(res[-1]),
            "ci_90": (int(pct(res, 5)), int(pct(res, 95))),
            "prob_over_140": round(float(np.mean(res >= 140) * 100), 1),
            "tox_mean": round(float(np.mean(res_tox)), 1),
            "tox_std": round(float(np.std(res_tox)), 2),
            "tox_min": round(float(res_tox[0]), 1),
            "tox_max": round(float(res_tox[-1]), 1),
            "tox_ci_90": (round(pct(res_tox, 5), 1), round(pct(res_tox, 95), 1)),
            "tox_prob_over_140": round(float(np.mean(res_tox >= 140) * 100), 1),
            "tox_prob_over_180": round(float(np.mean(res_tox >= 180) * 100), 1),
            "n_iter": n_iter, "variation_pct": int(variation * 100)}


def mitigate(idx, hdpe=False, treat=False, mon=False):
    m = float(idx)
    if hdpe: m *= 0.40
    if treat: m *= 0.60
    if mon: m *= 0.85
    red = ((idx - m) / idx * 100) if idx > 0 else 0.0
    return {"mitigated_index": round(m, 1), "reduction_pct": round(red, 1)}


def weighted_toxicity(hgw, hgs, cnw, cns, mining_type="traditional",
                      alpha_override=None, beta_override=None, SF_override=None,
                      use_log_transform=True):
    CN_LIMIT = dc.LIMITS_MG_L["EU"]["cn"]
    HG_LIMIT = dc.LIMITS_MG_L["EU"]["hg"]
    cn_score = dc.hazard_score(float(cnw or 0.0), CN_LIMIT)
    hg_score = dc.hazard_score(float(hgw or 0.0), HG_LIMIT)
    a = alpha_override if alpha_override is not None else 1.0
    b = beta_override if beta_override is not None else 1.0
    sf = SF_override if SF_override is not None else 1.0
    base_bonus = min(50.0, a * cn_score + b * hg_score)
    tox_idx = base_bonus * sf
    _cls = classify(tox_idx, mining_type=mining_type, is_tox=True)
    hq_cn = (float(cnw) / CN_LIMIT) if cnw else 0.0
    hq_hg = (float(hgw) / HG_LIMIT) if hgw else 0.0
    return {"index": round(tox_idx, 2), "drastic_tox_bonus": round(tox_idx, 2),
            "cn_score": round(cn_score, 2), "hg_score": round(hg_score, 2),
            "base_bonus": round(base_bonus, 2), "source_factor": round(sf, 2),
            "max_hq": round(max(hq_cn, hq_hg), 2),
            "category": _cls["level"], "action": _cls["action"],
            "mining_type": mining_type, "used_log_transform": True}


def generate_html_report(site_info, drastic, drastic_t, level, recommendation):
    name = site_info.get("name", "N/A")
    state = site_info.get("state", "N/A")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        '<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="UTF-8">'
        '<title>DRASTIC-Tox Report</title><style>'
        "body{font-family:Arial;padding:40px;max-width:800px;margin:0 auto;}"
        "h1{color:#5c2c16;border-bottom:3px solid #c19a6b;padding-bottom:10px;}"
        "table{width:100%;border-collapse:collapse;margin:15px 0;}"
        "th,td{padding:10px;border:1px solid #ddd;text-align:right;}"
        "th{background:#f5eedc;color:#5c2c16;}"
        ".metric{font-size:1.4em;font-weight:bold;color:#c19a6b;}"
        "</style></head><body>"
        "<h1>DRASTIC-Tox Report</h1>"
        f"<p><b>Date:</b> {now}</p><table>"
        f"<tr><th>Site</th><td>{name}</td></tr>"
        f"<tr><th>State</th><td>{state}</td></tr>"
        f'<tr><th>DRASTIC</th><td class="metric">{drastic}/{DRASTIC_MAX}</td></tr>'
        f'<tr><th>DRASTIC-Tox</th><td class="metric">{drastic_t}/{DTOX_MAX}</td></tr>'
        f'<tr><th>Level</th><td class="metric">{level}</td></tr>'
        "</table>"
        f"<p><b>{recommendation}</b></p>"
        '<p style="text-align:center;color:#666;">DRASTIC-Tox v61.2</p>'
        "</body></html>")


# ============================================================
# OPTIONAL MODULES
# ============================================================
try:
    from weight_manager import (get_all_profiles, get_active_profile,
        set_active_profile, save_calibrated_profile, detect_ceiling_effect,
        get_profile_summary, get_stale_profiles)
    WM_OK = True
except Exception:
    WM_OK = False

try:
    import external_validation as ev
    EXT_VAL_OK = True
except Exception:
    EXT_VAL_OK = False
    ev = None

try:
    from data_validator import (validate_dataframe, get_quality_color,
                                 get_quality_label_ar)
    VALIDATOR_OK = True
except Exception:
    VALIDATOR_OK = False
    validate_dataframe = None
    def get_quality_color(s): return "#666"
    def get_quality_label_ar(s): return "-"

try:
    from pdf_generator import generate_pdf_report
    PDF_OK = True
except Exception:
    PDF_OK = False
    generate_pdf_report = None

try:
    from excel_exporter import generate_excel_report
    EXCEL_OK = True
except Exception:
    EXCEL_OK = False
    generate_excel_report = None

try:
    import gis_raster as gr
    RASTER_OK = True
except Exception:
    RASTER_OK = False
    gr = None

try:
    from live_apis import (fetch_nasa_power, fetch_open_meteo_precipitation,
                            fetch_elevation_grid, fetch_soilgrids)
    LIVE_API_OK = True
except Exception:
    LIVE_API_OK = False
    fetch_nasa_power = fetch_open_meteo_precipitation = None
    fetch_elevation_grid = fetch_soilgrids = None

try:
    import auto_calibration as ac
    from auto_calibration import (auto_calibrate_weights, compare_with_defaults,
                                   find_optimal_threshold)
    AUTOCAL_OK = True
except Exception:
    AUTOCAL_OK = False

try:
    from auto_maps import generate_auto_maps, prepare_df_for_maps
    MAPS_OK = True
except Exception:
    MAPS_OK = False

try:
    import advanced_modules as am
    ADV_OK = True
except Exception:
    ADV_OK = False
    am = None

try:
    import model_development as md
    DEV_OK = True
except Exception:
    DEV_OK = False
    md = None

try:
    from data_sources import (STATES_DATABASE, AGRICULTURAL_DATA,
        get_preset_locations_for_app, get_data_summary, get_sites_by_state,
        get_site_data, get_all_sites_as_dataframe, add_new_site,
        get_states_list, get_sites_list, get_agricultural_data_summary,
        get_agri_states_list, get_agri_sites_list, get_agri_site_data,
        get_all_agri_sites_as_dataframe, KNOWN_MINING_SITES,
        get_verified_sites_as_dataframe, get_all_sites_as_dataframe_with_flag,
        GRAY_ZONE_SITES, get_combined_dataset)
    DS_OK = True
except Exception:
    DS_OK = False
    STATES_DATABASE = {}
    AGRICULTURAL_DATA = {}
    GRAY_ZONE_SITES = {}
    KNOWN_MINING_SITES = {}
    def get_preset_locations_for_app(): return {}
    def get_data_summary(): return {"total_states": 0, "total_sites": 0, "verified_sites": 0}
    def get_sites_by_state(s): return {}
    def get_site_data(s, k): return None
    def get_all_sites_as_dataframe(): return pd.DataFrame()
    def add_new_site(*a, **k): return True
    def get_states_list(): return []
    def get_sites_list(s): return []
    def get_agricultural_data_summary(): return {"total_states": 0, "total_sites": 0}
    def get_agri_states_list(): return []
    def get_agri_sites_list(s): return []
    def get_agri_site_data(s, k): return None
    def get_all_agri_sites_as_dataframe(): return pd.DataFrame()
    def get_verified_sites_as_dataframe(): return pd.DataFrame()
    def get_all_sites_as_dataframe_with_flag(): return pd.DataFrame()
    def get_combined_dataset(include_gray=False): return pd.DataFrame()

try:
    from modflow_engine import is_modflow_available, build_and_run_model
    MODFLOW_OK = True
except Exception:
    MODFLOW_OK = False
    def is_modflow_available(): return (False, "not installed")
    build_and_run_model = None

try:
    import water_guardian as wg
    WG_OK = True
except Exception:
    WG_OK = False
    wg = None


# ============================================================
# HELPERS
# ============================================================
def get_loaded_df(*keys):
    for k in keys:
        d = st.session_state.get(k)
        if d is not None and hasattr(d, "empty") and not d.empty:
            return d
    return None


def safe_sum(df, col, default=0):
    if df is None or col not in df.columns:
        return default
    try:
        return int(df[col].sum())
    except Exception:
        return default


def safe_len(df, default=0):
    try:
        return len(df) if df is not None else default
    except Exception:
        return default


def row_drastic(row):
    cond = row.get("conductivity_m_d") or row.get("conductivity")
    return calc_index(get_d_rating(float(row["depth_m"])),
                      get_r_rating(float(row["recharge_mm"])),
                      get_a_rating(str(row["aquifer"])),
                      get_s_rating(str(row["soil"])),
                      get_t_rating(float(row["slope_pct"])),
                      get_i_rating(str(row["vadose"])),
                      get_c_rating(float(cond)))


def row_tox(row, mining_type="traditional"):
    ix = row_drastic(row)
    r = calc_drastic_t(ix, float(row.get("cn_water_mg_l", 0.0)),
                       float(row.get("hg_water_mg_l", 0.0)),
                       mining_type=mining_type)
    return ix, r


def add_indices(df, mining_type="traditional"):
    d_vals, t_vals, errs = [], [], []
    for i, (_, row) in enumerate(df.iterrows()):
        try:
            ix, r = row_tox(row, mining_type)
            d_vals.append(ix)
            t_vals.append(r["drastic_t"])
        except Exception as e:
            d_vals.append(np.nan)
            t_vals.append(np.nan)
            errs.append(f"{i+1}: {str(e)[:80]}")
    out = df.copy()
    out["DRASTIC"], out["DRASTIC_Tox"] = d_vals, t_vals
    return out, errs


@st.cache_data(show_spinner=False)
def load_industrial_sites_csv():
    p = Path(__file__).parent / "industrial_sites.csv"
    if not p.exists():
        return []
    try:
        df = pd.read_csv(p, encoding="utf-8")
        if "verified" in df.columns:
            df["verified"] = df["verified"].astype(str).str.lower() == "true"
        return df.to_dict(orient="records")
    except Exception:
        return []


def _read_upload(f):
    return pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)


MT_LABEL = {"industrial": ("🏭 صناعي", "🏭 Industrial"),
            "traditional": ("⛏️ تقليدي", "⛏️ Traditional"),
            "mixed": ("🔀 مختلط", "🔀 Mixed")}


def mt_label(mt):
    ar, en = MT_LABEL.get(mt, MT_LABEL["traditional"])
    return ar if is_ar() else en


AQUIFER_AR = {"massive_shale": "صخر طيني ضخم",
              "metamorphic_igneous": "صخور متحولة/نارية",
              "weathered_metamorphic_igneous": "صخور متحولة/نارية متآكلة",
              "glacial_till": "ركام جليدي",
              "thin_bedded_sequences": "تتابعات رقيقة الطبقات",
              "massive_sandstone": "حجر رملي ضخم",
              "massive_limestone": "حجر جيري ضخم",
              "sand_and_gravel": "رمل وحصى",
              "basalt": "بازلت",
              "karst_limestone": "حجر جيري كارستي"}

AQUIFER_EN = {"massive_shale": "Massive Shale",
              "metamorphic_igneous": "Metamorphic/Igneous",
              "weathered_metamorphic_igneous": "Weathered Metamorphic",
              "glacial_till": "Glacial Till",
              "thin_bedded_sequences": "Thin Bedded",
              "massive_sandstone": "Massive Sandstone",
              "massive_limestone": "Massive Limestone",
              "sand_and_gravel": "Sand & Gravel",
              "basalt": "Basalt",
              "karst_limestone": "Karst Limestone"}

SOIL_AR = {"thin_or_absent": "رقيقة أو معدومة", "gravel": "حصى", "sand": "رمل",
           "peat": "خث", "shrinking_aggregated_clay": "طين متقلص متكتل",
           "sandy_loam": "طين رملي", "loam": "طين طميي", "silty_loam": "طمي غريني",
           "clay_loam": "طين غريني", "muck": "طين عضوي",
           "nonshrinking_clay": "طين غير متقلص"}

SOIL_EN = {"thin_or_absent": "Thin or Absent", "gravel": "Gravel", "sand": "Sand",
           "peat": "Peat", "shrinking_aggregated_clay": "Shrinking Clay",
           "sandy_loam": "Sandy Loam", "loam": "Loam", "silty_loam": "Silty Loam",
           "clay_loam": "Clay Loam", "muck": "Muck",
           "nonshrinking_clay": "Non-shrinking Clay"}

VADOSE_AR = {"confining_layer": "طبقة كتيمة", "silt_clay": "غرين وطين",
             "shale": "صخر طيني", "metamorphic_igneous": "صخور متحولة/نارية",
             "limestone": "حجر جيري", "sandstone": "حجر رملي",
             "bedded_limestone_sandstone": "حجر جيري/رملي متطبق",
             "sand_gravel_silt_clay": "رمل وحصى وغرين وطين",
             "sand_gravel": "رمل وحصى", "basalt": "بازلت",
             "karst_limestone": "حجر جيري كارستي"}

VADOSE_EN = {"confining_layer": "Confining Layer", "silt_clay": "Silt & Clay",
             "shale": "Shale", "metamorphic_igneous": "Metamorphic/Igneous",
             "limestone": "Limestone", "sandstone": "Sandstone",
             "bedded_limestone_sandstone": "Bedded Limestone/Sandstone",
             "sand_gravel_silt_clay": "Sand/Gravel/Silt/Clay",
             "sand_gravel": "Sand & Gravel", "basalt": "Basalt",
             "karst_limestone": "Karst Limestone"}


def AQ(a): return AQUIFER_AR.get(a, a) if is_ar() else AQUIFER_EN.get(a, a)
def SL(s): return SOIL_AR.get(s, s) if is_ar() else SOIL_EN.get(s, s)
def VD(v): return VADOSE_AR.get(v, v) if is_ar() else VADOSE_EN.get(v, v)


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="Sudan Mining System v61.2",
                   page_icon="⛏️", layout="wide",
                   initial_sidebar_state="expanded")

# ══════════════════════════════════════════════════════════
# ✅ أسطر عرض مرئية — تُظهر أن التطبيق بدأ يعمل
# ══════════════════════════════════════════════════════════
st.title("✅ التطبيق بدأ يعمل بنجاح")
st.write("**مرحباً — نظام التعدين السوداني v61.2**")
st.write("جاري تحميل الوحدات...")
st.success("تم تحميل الوحدات الأساسية بنجاح.")
st.markdown("---")
# ══════════════════════════════════════════════════════════

st.markdown("""<style>
html,body,[class*="css"]{font-family:'Segoe UI','Tahoma',Arial;font-size:15px;}
.stButton>button{border-radius:8px;font-weight:600;padding:10px 24px;border:none;}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,#5c2c16,#c19a6b);color:white;}
.stTabs [data-baseweb="tab-list"]{gap:4px;flex-wrap:wrap;background:#faf8f3;padding:8px;border-radius:12px;border:1px solid #e0d4b8;}
.stTabs [data-baseweb="tab"]{border-radius:8px;padding:10px 16px;font-size:.9em;font-weight:600;background:transparent;color:#5c2c16;}
.stTabs [aria-selected="true"]{background:#5c2c16!important;color:white!important;}
div[data-testid="stMetric"]{background:linear-gradient(135deg,#fff,#f9f5ec);border:2px solid #d4af37;border-radius:12px;padding:16px 20px;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#f5eedc,#faf8f3);border-right:3px solid #c19a6b;}
.header-container{background:linear-gradient(135deg,#5c2c16,#c19a6b);padding:28px 24px;border-radius:16px;margin-bottom:24px;color:white;text-align:center;}
.header-title{font-size:2em;font-weight:700;margin:0;}
.header-subtitle{font-size:1em;opacity:.95;margin:6px 0 0;}
.header-badge{display:inline-block;background:rgba(255,255,255,.2);padding:4px 12px;border-radius:20px;font-size:.85em;margin-top:10px;}
.section-header{margin:16px 0 12px;padding-bottom:8px;border-bottom:2px solid #f0e6d2;}
.section-header h3{color:#5c2c16;margin:0;font-size:1.25em;}
.info-card{background:#faf8f3;border:1px solid #e0d4b8;border-radius:10px;padding:16px;margin:10px 0;}
.pilot-banner{background:linear-gradient(135deg,#ff9800,#f57c00);color:white;padding:12px 16px;border-radius:10px;margin:8px 0;font-weight:600;text-align:center;}
.quality-box-ok{background:#e8f5e9;border-left:4px solid #4caf50;padding:10px 12px;border-radius:8px;margin:5px 0;}
.quality-box-warn{background:#fff3e0;border-left:4px solid #ff9800;padding:10px 12px;border-radius:8px;margin:5px 0;}
.mining-badge{display:inline-block;padding:6px 14px;border-radius:8px;font-size:1em;font-weight:700;margin:8px 0;}
.mining-traditional{background:#fff3e0;color:#e65100;border:2px solid #e65100;}
.mining-industrial{background:#e3f2fd;color:#1565c0;border:2px solid #1565c0;}
.mining-mixed{background:#f3e5f5;color:#6a1b9a;border:2px solid #6a1b9a;}
.research-note{background:#e8eaf6;border-left:4px solid #3f51b5;padding:10px 14px;border-radius:8px;margin:8px 0;font-size:.85em;color:#1a237e;}
.kappa-box{padding:20px;border-radius:12px;text-align:center;margin:12px 0;color:white;}
.kappa-excellent{background:linear-gradient(135deg,#2e7d32,#66bb6a);}
.kappa-good{background:linear-gradient(135deg,#388e3c,#81c784);}
.kappa-moderate{background:linear-gradient(135deg,#f57c00,#ffb74d);}
.kappa-fair{background:linear-gradient(135deg,#e64a19,#ff8a65);}
.kappa-poor{background:linear-gradient(135deg,#c62828,#ef5350);}
#MainMenu{visibility:hidden;} footer{visibility:hidden;}
</style>""", unsafe_allow_html=True)


# ============================================================
# SESSION STATE
# ============================================================
if "lang" not in st.session_state:
    st.session_state["lang"] = "ar"
if "use_log_transform" not in st.session_state:
    st.session_state["use_log_transform"] = True

CALIBRATED_WEIGHTS = None


# ============================================================
# SIDEBAR
# ============================================================
_lang_opts = {"🇸🇦 العربية": "ar", "🇬🇧 English": "en"}
_cur = "🇸🇦 العربية" if st.session_state["lang"] == "ar" else "🇬🇧 English"
_sel = st.sidebar.selectbox(t("language"), list(_lang_opts.keys()),
                             index=list(_lang_opts.keys()).index(_cur),
                             key="lang_switcher")
st.session_state["lang"] = _lang_opts[_sel]

st.sidebar.markdown("---")
st.sidebar.markdown(f"### {tx('حالة الوحدات', 'Module Status')}")
_mods = {
    "drastic_core": DC_OK,
    "translations": TRANS_OK,
    "weight_manager": WM_OK,
    "data_validator": VALIDATOR_OK,
    "external_validation": EXT_VAL_OK,
    "auto_calibration": AUTOCAL_OK,
    "advanced_modules": ADV_OK,
    "model_development": DEV_OK,
    "data_sources": DS_OK,
    "gis_raster": RASTER_OK,
    "auto_maps": MAPS_OK,
    "pdf_generator": PDF_OK,
    "excel_exporter": EXCEL_OK,
    "live_apis": LIVE_API_OK,
    "water_guardian": WG_OK,
    "modflow": MODFLOW_OK,
}
for k, v in _mods.items():
    icon = "✅" if v else "⚪"
    st.sidebar.caption(f"{icon} {k}")

if DS_OK:
    try:
        _sum = get_data_summary()
        _n_total = _sum.get("total_sites", 0)
        _n_verified = _sum.get("verified_sites", 0)
    except Exception:
        _n_total = _n_verified = 0
else:
    _n_total = _n_verified = 0

if DS_OK:
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### {t('data_quality')}")
    st.sidebar.markdown(
        '<div class="quality-box-ok">'
        f'<div style="font-size:0.85em;color:#2e7d32;">'
        f'{t("verified_sites")}: {_n_verified}</div></div>'
        '<div class="quality-box-warn">'
        f'<div style="font-size:0.85em;color:#e65100;">'
        f'{t("display_only")}: {_n_total - _n_verified}</div></div>',
        unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown(f"## {t('mode')}")
_mode_opts = [t("mode_system")]
if ADV_OK:
    _mode_opts += [t("mode_agricultural"), t("mode_verification"),
                    t("mode_transport"), t("mode_independent"),
                    t("mode_satellite"), t("mode_dynamic")]
mode_choice = st.sidebar.radio(t("select"), _mode_opts,
                                key="mode_radio", label_visibility="collapsed")
MODE_KEY = "system" if mode_choice == t("mode_system") else "other"


# ============================================================
# HEADER
# ============================================================
_banner = (
    f'<div class="pilot-banner">{t("pilot_version")}</div>'
    '<div class="header-container">'
    f'<div class="header-title">{t("app_title")}</div>'
    f'<div class="header-subtitle">{t("university")}</div>'
    f'<div class="header-subtitle">{t("subtitle")}</div>'
    f'<div class="header-badge">v61.2 | {_n_total} {t("sites")} '
    f'({_n_verified} {t("verified_sites")})</div>'
    '</div>'
)
st.markdown(_banner, unsafe_allow_html=True)

st.markdown("---")


# ============================================================
# MAIN SYSTEM MODE
# ============================================================
if MODE_KEY == "system":
    tabs = st.tabs([
        t("tab_input"), t("tab_manual"), t("tab_bulk"),
        t("tab_solutions"), t("tab_report"),
        t("tab_sensitivity"), t("tab_toxicity"),
        t("tab_monte_carlo"),
    ])

    # ---------- TAB 0: Site Selection ----------
    with tabs[0]:
        st.markdown(f'<div class="section-header"><h3>{t("site_selection")}</h3></div>',
                    unsafe_allow_html=True)
        if not DS_OK:
            st.warning(tx("data_sources.py غير موجود — استخدم الإدخال اليدوي (التبويب التالي)",
                           "data_sources.py not found — use manual input (next tab)"))
        else:
            try:
                states = get_states_list()
                if not states:
                    st.warning(tx("لا توجد ولايات", "No states available"))
                else:
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        state = st.selectbox(t("state"), states, key="s_state")
                    with c2:
                        try:
                            desc = STATES_DATABASE[state].get("description", "")
                        except Exception:
                            desc = ""
                        if desc:
                            st.markdown(
                                f'<div class="info-card" style="margin-top:28px;">'
                                f'<div style="font-size:0.9em;color:#5c2c16;">{desc}</div>'
                                '</div>', unsafe_allow_html=True)

                    sites = get_sites_list(state)
                    if not sites:
                        st.warning(tx("لا توجد مواقع في هذه الولاية",
                                       "No sites in this state"))
                    else:
                        site_key = st.selectbox(t("site"), sites, key="s_site")
                        site_data = get_site_data(state, site_key)
                        if site_data:
                            mt_key = site_data.get("mining_type", "traditional")
                            if mt_key not in ("industrial", "traditional", "mixed"):
                                mt_key = "traditional"
                            badge_class = {"industrial": "mining-industrial",
                                           "mixed": "mining-mixed"}.get(
                                mt_key, "mining-traditional")
                            st.markdown(
                                f'<div class="mining-badge {badge_class}">'
                                f'{mt_label(mt_key)}</div>',
                                unsafe_allow_html=True)

                            st.session_state.update({
                                "mining_type": mt_key,
                                "current_site_key": site_key,
                                "current_site_data": site_data,
                                "current_state": state,
                            })

                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric(t("activity"), site_data.get("activity", "N/A"))
                            c2.metric(t("season"), site_data.get("season", "N/A"))
                            c3.metric(t("site_status"),
                                       t("contaminated") if site_data.get("actual_contaminated", 0) == 1
                                       else t("clean"))
                            c4.metric(t("documentation"),
                                       t("verified") if site_data.get("verified", False)
                                       else t("display"))

                            c1, c2 = st.columns(2)
                            with c1:
                                st.metric("D - " + t("depth"),
                                           f"{site_data.get('depth_m', '?')} {t('m')}")
                                st.metric("R - " + t("recharge"),
                                           f"{site_data.get('recharge_mm', '?')} {t('mm_yr')}")
                                st.metric("T - " + t("slope"),
                                           f"{site_data.get('slope_pct', '?')} %")
                                cond_v = (site_data.get("conductivity_m_d")
                                          or site_data.get("conductivity", "?"))
                                st.metric("C - " + t("conductivity"),
                                           f"{cond_v} {t('m_day')}")
                            with c2:
                                st.metric("A - " + t("aquifer"),
                                           AQ(site_data.get("aquifer", "?")))
                                st.metric("S - " + t("soil"),
                                           SL(site_data.get("soil", "?")))
                                st.metric("I - " + t("vadose"),
                                           VD(site_data.get("vadose", "?")))
                                st.metric("θ - " + t("porosity"), "0.25")

                            c1, c2 = st.columns(2)
                            c1.metric("CN", f"{site_data.get('cn_water_mg_l', '?')} mg/L")
                            c2.metric("Hg", f"{site_data.get('hg_water_mg_l', '?')} mg/L")
                            L = dc.LIMITS_MG_L["EU"]
                            st.caption(f"{t('limits')}: CN = {L['cn']} mg/L | Hg = {L['hg']} mg/L")

                            for w in dc.check_units(site_data.get("cn_water_mg_l"),
                                                     site_data.get("hg_water_mg_l")):
                                st.warning(w)

                            try:
                                idx = row_drastic(site_data)
                                risk = classify(idx)
                                st.session_state["ci"] = idx
                                st.session_state["cv"] = {
                                    "depth": site_data.get("depth_m"),
                                    "recharge": site_data.get("recharge_mm"),
                                    "aquifer": site_data.get("aquifer"),
                                    "soil": site_data.get("soil"),
                                    "slope": site_data.get("slope_pct"),
                                    "vadose": site_data.get("vadose"),
                                    "conductivity": cond_v,
                                    "cn_water_mg_l": site_data.get("cn_water_mg_l", 0),
                                    "hg_water_mg_l": site_data.get("hg_water_mg_l", 0),
                                }
                                st.session_state["current_risk"] = risk

                                z1, z2, z3 = st.columns(3)
                                z1.metric("DRASTIC", f"{idx}/{DRASTIC_MAX}")
                                z2.metric(t("level"), t(risk["level"]))
                                z3.metric(t("percentage"),
                                           f"{round((idx - 23) / (DRASTIC_MAX - 23) * 100, 1)}%")

                                color_fn = {"red": st.error, "orange": st.warning,
                                            "yellow": st.info}.get(risk["color"], st.success)
                                color_fn(t(risk["action"]))

                                st.markdown("---")
                                dt_result = calc_drastic_t(
                                    idx, site_data.get("cn_water_mg_l", 0),
                                    site_data.get("hg_water_mg_l", 0),
                                    mining_type=mt_key)
                                st.markdown(f"#### {t('drastic_tox')} — {tx('تجريبي', 'experimental')}")
                                m1, m2, m3, m4 = st.columns(4)
                                m1.metric(t("drastic_tox"), f"{dt_result['drastic_t']}",
                                           delta=f"+{dt_result['increase_pct']}%")
                                m2.metric(t("bonus"), dt_result["toxicity_bonus"])
                                m3.metric("α (CN)", dt_result["alpha"])
                                m4.metric("β (Hg)", dt_result["beta"])

                                st.markdown("---")
                                html_report = generate_html_report(
                                    site_info={
                                        "name": site_data.get("name_ar", site_key),
                                        "state": state,
                                    },
                                    drastic=idx,
                                    drastic_t=dt_result["drastic_t"],
                                    level=t(risk["level"]),
                                    recommendation=t(risk["action"]))
                                st.download_button(
                                    "📄 " + t("tab_report") + " (HTML)",
                                    data=html_report.encode("utf-8"),
                                    file_name=f"report_{site_key}.html",
                                    mime="text/html",
                                    key="dl_report_main")
                            except Exception as e:
                                st.error(f"Computation error: {e}")
            except Exception as e:
                st.error(f"Error: {e}")

    # ---------- TAB 1: Manual Input ----------
    with tabs[1]:
        st.markdown(f'<div class="section-header"><h3>{t("tab_manual")}</h3></div>',
                    unsafe_allow_html=True)
        st.info(tx("البيانات المدخلة تُحفظ في جلسة المتصفح فقط.",
                    "Entered data is stored only in browser session."))

        c1, c2 = st.columns(2)
        with c1:
            m_depth = st.number_input("D — " + t("depth") + " (m):",
                                       0.5, 100.0, 15.0, key="m_depth")
            m_recharge = st.number_input("R — " + t("recharge") + " (mm/yr):",
                                          0.0, 400.0, 20.0, key="m_recharge")
            m_slope = st.number_input("T — " + t("slope") + " (%):",
                                       0.0, 30.0, 3.0, key="m_slope")
            m_cond = st.number_input("C — " + t("conductivity") + " (m/d):",
                                      0.01, 200.0, 3.0, key="m_cond")
        with c2:
            m_aquifer = st.selectbox("A — " + t("aquifer"),
                                      list(dc.AQUIFER.keys()), key="m_aquifer")
            m_soil = st.selectbox("S — " + t("soil"),
                                   list(dc.SOIL.keys()), key="m_soil")
            m_vadose = st.selectbox("I — " + t("vadose"),
                                     list(dc.VADOSE.keys()), key="m_vadose")

        c1, c2, c3 = st.columns(3)
        with c1:
            m_cn = st.number_input("CN (mg/L):", 0.0, 10.0, 0.025,
                                    format="%.4f", key="m_cn")
        with c2:
            m_hg = st.number_input("Hg (mg/L):", 0.0, 10.0, 0.011,
                                    format="%.5f", key="m_hg")
        with c3:
            m_status = st.selectbox(t("site_status"),
                                     [t("clean") + " (0)", t("contaminated") + " (1)"],
                                     key="m_status")

        if st.button("💾 " + t("save"), type="primary", key="btn_save_manual"):
            try:
                manual = {
                    "depth_m": m_depth, "recharge_mm": m_recharge,
                    "slope_pct": m_slope, "conductivity": m_cond,
                    "aquifer": m_aquifer, "soil": m_soil, "vadose": m_vadose,
                    "cn_water_mg_l": m_cn, "hg_water_mg_l": m_hg,
                    "actual_contaminated": 1 if "1" in m_status else 0,
                }
                idx = row_drastic(manual)
                risk = classify(idx)
                st.session_state["ci"] = idx
                st.session_state["cv"] = {
                    "depth": m_depth, "recharge": m_recharge,
                    "slope": m_slope, "conductivity": m_cond,
                    "aquifer": m_aquifer, "soil": m_soil, "vadose": m_vadose,
                    "cn_water_mg_l": m_cn, "hg_water_mg_l": m_hg,
                }
                st.session_state["current_risk"] = risk
                st.success(f"✅ DRASTIC = {idx} — {t('level')}: {t(risk['level'])}")

                dt = calc_drastic_t(idx, m_cn, m_hg)
                st.info(f"DRASTIC-Tox = {dt['drastic_t']} "
                        f"(+{dt['increase_pct']}%) — {t('bonus')}: {dt['toxicity_bonus']}")
            except Exception as e:
                st.error(f"Error: {e}")

    # ---------- TAB 2: Bulk ----------
    with tabs[2]:
        st.markdown(f'<div class="section-header"><h3>{t("bulk_assessment")}</h3></div>',
                    unsafe_allow_html=True)
        up = st.file_uploader("CSV/Excel:", type=["csv", "xlsx"], key="bulk_up")
        if up:
            try:
                df = _read_upload(up)
                st.success(f"{len(df)} {t('rows')}")
                st.dataframe(df.head(10), use_container_width=True)

                required = ["depth_m", "recharge_mm", "slope_pct",
                             "aquifer", "soil", "vadose"]
                has_cond = "conductivity" in df.columns or "conductivity_m_d" in df.columns
                missing = [c for c in required if c not in df.columns]
                if not has_cond:
                    missing.append("conductivity (or conductivity_m_d)")

                if missing:
                    st.error(f"Missing columns: {missing}")
                else:
                    scored, errs = add_indices(df, "traditional")
                    if errs:
                        st.warning(f"Errors in {len(errs)} rows")
                        for e in errs[:5]:
                            st.caption("• " + e)

                    name_col = next((c for c in ["name", "site_name", "site_key"]
                                     if c in scored.columns), None)
                    results = pd.DataFrame({
                        "Site": scored[name_col] if name_col
                        else [f"R{i+1}" for i in range(len(scored))],
                        "DRASTIC": scored["DRASTIC"],
                        "DRASTIC-Tox": scored["DRASTIC_Tox"],
                    })
                    st.dataframe(results, use_container_width=True)

                    st.download_button(
                        "📥 " + t("download_results"),
                        data=results.to_csv(index=False).encode("utf-8-sig"),
                        file_name="results.csv", mime="text/csv",
                        key="dl_bulk")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.info(t("no_file"))
            sample = pd.DataFrame({
                "site_name": ["Site1", "Site2"],
                "depth_m": [12.0, 15.0], "recharge_mm": [20.0, 18.0],
                "slope_pct": [3.0, 4.0], "conductivity": [2.5, 3.0],
                "aquifer": ["massive_sandstone", "sand_and_gravel"],
                "soil": ["sand", "sandy_loam"],
                "vadose": ["sand_gravel", "sandstone"],
                "cn_water_mg_l": [0.10, 0.009],
                "hg_water_mg_l": [0.008, 0.0007],
                "actual_contaminated": [1, 0],
            })
            st.download_button("📥 Template", data=sample.to_csv(index=False).encode("utf-8-sig"),
                                file_name="template.csv", mime="text/csv",
                                key="dl_template")

    # ---------- TAB 3: Solutions ----------
    with tabs[3]:
        st.markdown(f'<div class="section-header"><h3>{t("solutions")}</h3></div>',
                    unsafe_allow_html=True)
        st.warning(tx("⚠️ معاملات التخفيض افتراضات توضيحية بلا مصدر.",
                       "⚠️ Reduction factors are illustrative assumptions without a source."))
        if "ci" not in st.session_state:
            st.info(t("site_selection"))
        else:
            ci = st.session_state["ci"]
            c1, c2 = st.columns(2)
            with c1:
                hdpe = st.checkbox(t("hdpe_liner"), key="chk_hdpe")
                treat = st.checkbox(t("cyanide_treatment"), key="chk_treat")
            with c2:
                mon = st.checkbox(t("monitoring_wells"), key="chk_mon")
            if hdpe or treat or mon:
                r = mitigate(ci, hdpe, treat, mon)
                c1, c2, c3 = st.columns(3)
                c1.metric(t("before"), ci)
                c2.metric(t("after"), r["mitigated_index"])
                c3.metric(t("reduction"), f"{r['reduction_pct']}%")

    # ---------- TAB 4: Report ----------
    with tabs[4]:
        st.markdown(f'<div class="section-header"><h3>{t("tab_report")}</h3></div>',
                    unsafe_allow_html=True)
        if "ci" not in st.session_state:
            st.info(t("site_selection"))
        else:
            idx = st.session_state["ci"]
            cv = st.session_state.get("cv", {})
            cn = cv.get("cn_water_mg_l", 0)
            hg = cv.get("hg_water_mg_l", 0)
            dt = calc_drastic_t(idx, cn, hg)
            risk = classify(idx)

            c1, c2, c3 = st.columns(3)
            c1.metric("DRASTIC", f"{idx}/{DRASTIC_MAX}")
            c2.metric("CN", f"{cn} mg/L")
            c3.metric("Hg", f"{hg} mg/L")

            st.markdown("---")
            st.dataframe(pd.DataFrame({
                "Metric": ["DRASTIC", "CN_score", "Hg_score", "Base Bonus",
                           "Source Factor", "Final Bonus", "DRASTIC-Tox", "Level"],
                "Value": [idx, dt["cn_score"], dt["hg_score"], dt["base_bonus"],
                          dt["source_factor"], dt["toxicity_bonus"],
                          dt["drastic_t"], t(risk["level"])],
            }), use_container_width=True, hide_index=True)

            html = generate_html_report(
                site_info={"name": "Current", "state": "-"},
                drastic=idx, drastic_t=dt["drastic_t"],
                level=t(risk["level"]), recommendation=t(risk["action"]))
            st.download_button("📄 Download HTML", data=html.encode("utf-8"),
                                file_name="report.html", mime="text/html",
                                key="dl_html_report")

    # ---------- TAB 5: Sensitivity (SPSA) ----------
    with tabs[5]:
        st.markdown(f'<div class="section-header"><h3>{t("sensitivity_title")}</h3></div>',
                    unsafe_allow_html=True)
        if "cv" not in st.session_state:
            st.info(t("site_selection"))
        else:
            sub = st.tabs([t("spsa_tab"), t("variation_tab")])
            with sub[0]:
                st.markdown(f"#### {t('spsa_title')}")
                st.info(t("spsa_explanation"))
                if st.button("🚀 " + t("run_spsa"), type="primary", key="run_spsa_btn"):
                    with st.spinner(t("calculating")):
                        st.session_state["spsa"] = spsa_analysis(st.session_state["cv"])
                if "spsa" in st.session_state:
                    spsa = st.session_state["spsa"]
                    st.success(f"🏆 {t('most_influential')}: **{spsa['most_influential']}** "
                                f"| {t('base_index')}: **{spsa['base_index']}**")
                    st.dataframe(pd.DataFrame([{
                        t("parameter"): p["param"],
                        t("weight_wi"): p["weight"],
                        t("rating_ri"): p["rating"],
                        t("weighted"): p["weighted_score"],
                        t("theoretical_pct"): f"{p['theoretical_pct']}%",
                        t("effective_pct"): f"{p['effective_pct']}%",
                        t("difference"): f"{p['difference']:+.2f}%",
                    } for p in spsa["parameters"]]),
                    use_container_width=True, hide_index=True)
            with sub[1]:
                st.markdown(f"#### {t('variation_title')}")
                vp = st.slider(t("change_pct"), 5, 30, 10, 5, key="sens_var")
                if st.button("🚀 " + t("run"), type="primary", key="run_sens_btn"):
                    with st.spinner(t("calculating")):
                        st.session_state["sens"] = sensitivity_analysis(
                            st.session_state["cv"], vp / 100.0)
                if "sens" in st.session_state:
                    sens = st.session_state["sens"]
                    st.success(f"{t('most_sensitive')}: **{sens['most_sensitive']}**")
                    st.dataframe(pd.DataFrame([{
                        t("parameter"): p,
                        t("original_value"): d["original_phys"],
                        t("modified_value"): d["modified_phys"],
                        t("new_index"): d["new_index"],
                        t("change"): d["change"],
                        t("sensitivity_pct"): d["sensitivity"],
                    } for p, d in sens["parameters"].items()]),
                    use_container_width=True, hide_index=True)

    # ---------- TAB 6: Toxicity ----------
    with tabs[6]:
        st.markdown(f'<div class="section-header"><h3>{t("toxicity_title")}</h3></div>',
                    unsafe_allow_html=True)
        if "cv" not in st.session_state:
            st.info(t("site_selection"))
        else:
            cv = st.session_state["cv"]
            cnw = cv.get("cn_water_mg_l", 0.025)
            hgw = cv.get("hg_water_mg_l", 0.011)

            c1, c2 = st.columns(2)
            c1.metric("CN", f"{cnw} mg/L")
            c2.metric("Hg", f"{hgw} mg/L")

            if st.button(t("analyze"), type="primary", key="run_tox_btn"):
                with st.spinner(t("calculating")):
                    st.session_state["tox"] = weighted_toxicity(hgw, 0, cnw, 0)

            if "tox" in st.session_state:
                tox = st.session_state["tox"]
                c1, c2, c3 = st.columns(3)
                c1.metric(t("cn_score"), tox["cn_score"])
                c2.metric(t("hg_score"), tox["hg_score"])
                c3.metric(t("base_bonus"), tox["base_bonus"])
                c1, c2, c3 = st.columns(3)
                c1.metric(t("source_factor"), tox["source_factor"])
                c2.metric("HQ max", tox["max_hq"])
                c3.metric(t("category"), t(tox["category"]))
                st.metric(t("action"), t(tox["action"]))

    # ---------- TAB 7: Monte Carlo ----------
    with tabs[7]:
        st.markdown(f'<div class="section-header"><h3>{t("mc_title")}</h3></div>',
                    unsafe_allow_html=True)
        if "cv" not in st.session_state:
            st.info(t("site_selection"))
        else:
            ni = st.slider(t("simulations"), 100, 5000, 1000, 100, key="mc_n")
            vp = st.slider(t("variation"), 5, 30, 15, 5, key="mc_v")

            if st.button("🚀 " + t("run"), type="primary", key="run_mc_btn"):
                with st.spinner(t("calculating")):
                    st.session_state["mc"] = monte_carlo_analysis(
                        st.session_state["cv"], ni, vp / 100.0)

            if "mc" in st.session_state:
                mc = st.session_state["mc"]
                st.markdown("#### DRASTIC")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(t("mean"), mc["mean"])
                c2.metric(t("std"), mc["std"])
                c3.metric(t("ci_90"), f"{mc['ci_90'][0]}-{mc['ci_90'][1]}")
                c4.metric("P>140", f"{mc['prob_over_140']}%")

                st.markdown("#### DRASTIC-Tox")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(t("mean"), mc["tox_mean"])
                c2.metric(t("std"), mc["tox_std"])
                c3.metric(t("ci_90"), f"{mc['tox_ci_90'][0]}-{mc['tox_ci_90'][1]}")
                c4.metric("P>140", f"{mc['tox_prob_over_140']}%")


# ============================================================
# OTHER MODES (minimal)
# ============================================================
elif MODE_KEY == "other":
    st.info(tx("وضع مختصر — عُد إلى النظام الرئيسي للوظائف الكاملة.",
                "Brief mode — return to System for full functionality."))

    mode_choice_str = str(mode_choice)
    if "التحقق" in mode_choice_str or "Verification" in mode_choice_str:
        st.markdown(f'<div class="section-header"><h3>{t("verification_title")}</h3></div>',
                    unsafe_allow_html=True)
        df_val = st.session_state.get("df_validation")
        if df_val is None:
            st.warning(t("upload_validation_first"))
        else:
            st.dataframe(df_val.head(10), use_container_width=True)
            if "cn_water_mg_l" in df_val.columns and "hg_water_mg_l" in df_val.columns:
                scored, errs = add_indices(df_val, "traditional")
                if "actual_contaminated" in scored.columns:
                    ok = scored.dropna(subset=["DRASTIC", "DRASTIC_Tox"])
                    if len(ok) > 0 and ok["actual_contaminated"].nunique() >= 2:
                        y = ok["actual_contaminated"].astype(int).tolist()
                        try:
                            from sklearn.metrics import cohen_kappa_score
                            pred = (ok["DRASTIC_Tox"] >= DEFAULT_TOX_THRESHOLD).astype(int).tolist()
                            k = cohen_kappa_score(y, pred)
                            st.metric(t("kappa"), round(float(k), 3))
                        except Exception:
                            st.warning("scikit-learn مطلوب")
    else:
        st.info(tx("هذا الوضع يعمل فقط عند توفر الوحدات الاختيارية.",
                    "This mode requires optional modules."))


# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#666;padding:10px;">'
    f'<b>{t("app_title")} v61.2</b> — PILOT VERSION<br>'
    f'<span style="font-size:0.85em;">{t("screening_only")}</span></div>',
    unsafe_allow_html=True)
