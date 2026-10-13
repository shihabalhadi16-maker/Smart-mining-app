"""
analysis_tools.py — v61.1
SPSA / Sensitivity / Monte Carlo / Mitigation / Toxicity / HTML Report

يعتمد فقط على drastic_core.py (الموجود في المشروع).
كل دالة مكتوبة بشكل مستقل لتجنب مشاكل الاستيراد.
"""

import datetime
import math
import numpy as np
import pandas as pd

# ============================================================
# استيراد drastic_core مع بديل داخلي إن فشل
# ============================================================
try:
    import drastic_core as dc
    DC_LOADED = True
except ImportError:
    DC_LOADED = False

    class dc:  # noqa
        W_STD = {"D": 5, "R": 4, "A": 3, "S": 2, "T": 1, "I": 5, "C": 3}
        AQUIFER = {
            "massive_shale": 2, "metamorphic_igneous": 3,
            "weathered_metamorphic_igneous": 4, "thin_bedded_sequences": 6,
            "massive_sandstone": 6, "massive_limestone": 6,
            "sand_and_gravel": 8, "basalt": 9, "karst_limestone": 10,
        }
        SOIL = {
            "thin_or_absent": 10, "gravel": 10, "sand": 9, "peat": 8,
            "shrinking_aggregated_clay": 7, "sandy_loam": 6, "loam": 5,
            "silty_loam": 4, "clay_loam": 3, "muck": 2, "nonshrinking_clay": 1,
        }
        VADOSE = {
            "confining_layer": 1, "silt_clay": 3, "shale": 3,
            "metamorphic_igneous": 4, "limestone": 6, "sandstone": 6,
            "sand_gravel_silt_clay": 6, "sand_gravel": 8,
            "basalt": 9, "karst_limestone": 10,
        }
        LIMITS_MG_L = {
            "EU": {"cn": 0.05, "hg": 0.001},
            "WHO": {"cn": None, "hg": 0.006},
        }

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
            M = {
                "low": ["low", "low", "moderate", "moderate"],
                "moderate": ["low", "moderate", "moderate", "high"],
                "high": ["moderate", "moderate", "high", "high"],
                "very_high": ["moderate", "high", "high", "very_high"],
            }
            H = ["compliant", "elevated", "high", "severe"]
            return M[v][H.index(h)]

        @staticmethod
        def rate_D(m):
            if m is None or m < 0:
                raise ValueError("Invalid depth")
            for edge, r in zip([1.5, 4.6, 9.1, 15.2, 22.9, 30.5],
                                [10, 9, 7, 5, 3, 2]):
                if m <= edge:
                    return r
            return 1

        @staticmethod
        def rate_R(mm):
            if mm is None or mm < 0:
                raise ValueError("Invalid recharge")
            for edge, r in zip([50.8, 101.6, 177.8, 254.0], [1, 3, 6, 8]):
                if mm <= edge:
                    return r
            return 9

        @staticmethod
        def rate_T(p):
            if p is None or p < 0:
                raise ValueError("Invalid slope")
            for edge, r in zip([2.0, 6.0, 12.0, 18.0], [10, 9, 5, 3]):
                if p <= edge:
                    return r
            return 1

        @staticmethod
        def rate_C(c):
            if c is None or c < 0:
                raise ValueError("Invalid conductivity")
            for edge, r in zip([4.074, 12.222, 28.518, 40.740, 81.480],
                                [1, 2, 4, 6, 8]):
                if c <= edge:
                    return r
            return 10


# ============================================================
# ثوابت
# ============================================================
STANDARD = "EU"
DRASTIC_MAX = 226
DRASTIC_MIN = 23
DTOX_MAX = 276
DEFAULT_TOX_THRESHOLD = 144.4


# ============================================================
# دوال التقييم — fallback إن لم يوجد drastic_core
# ============================================================
def _get_d_rating(depth_m):
    if depth_m < 0:
        raise ValueError("Depth must be >= 0")
    if depth_m <= 1.5: return 10
    if depth_m <= 4.6: return 9
    if depth_m <= 9.1: return 7
    if depth_m <= 15.2: return 5
    if depth_m <= 22.9: return 3
    if depth_m <= 30.5: return 2
    return 1


def _get_r_rating(recharge_mm):
    if recharge_mm < 0:
        raise ValueError("Recharge must be >= 0")
    if recharge_mm <= 50.8: return 1
    if recharge_mm <= 101.6: return 3
    if recharge_mm <= 177.8: return 6
    if recharge_mm <= 254.0: return 8
    return 9


def _get_t_rating(slope_pct):
    if slope_pct < 0:
        raise ValueError("Slope must be >= 0")
    if slope_pct <= 2.0: return 10
    if slope_pct <= 6.0: return 9
    if slope_pct <= 12.0: return 5
    if slope_pct <= 18.0: return 3
    return 1


def _get_c_rating(conductivity):
    if conductivity < 0:
        raise ValueError("Conductivity must be >= 0")
    if conductivity <= 4.074: return 1
    if conductivity <= 12.222: return 2
    if conductivity <= 28.518: return 4
    if conductivity <= 40.740: return 6
    if conductivity <= 81.480: return 8
    return 10


def _get_a_rating(aquifer):
    key = str(aquifer)
    if key not in dc.AQUIFER:
        raise ValueError(f"Aquifer not recognized: {key}")
    return dc.AQUIFER[key]


def _get_s_rating(soil):
    key = str(soil)
    if key not in dc.SOIL:
        raise ValueError(f"Soil not recognized: {key}")
    return dc.SOIL[key]


def _get_i_rating(vadose):
    key = str(vadose)
    if key not in dc.VADOSE:
        raise ValueError(f"Vadose not recognized: {key}")
    return dc.VADOSE[key]


def calc_index(D, R, A, S, T, I, C):
    w = dc.W_STD
    return (D * w["D"]) + (R * w["R"]) + (A * w["A"]) + (S * w["S"]) + \
           (T * w["T"]) + (I * w["I"]) + (C * w["C"])


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


def calc_drastic_t(base_drastic, cn_water, hg_water,
                   distance_m=100.0, seepage=1.0, bio_acc=1.0,
                   mining_type="traditional",
                   alpha_override=None, beta_override=None, SF_override=None,
                   use_log_transform=True, calibrated_threshold=None):
    CN_LIMIT = dc.LIMITS_MG_L["EU"]["cn"]
    HG_LIMIT = dc.LIMITS_MG_L["EU"]["hg"]
    MAX_BONUS = 50.0

    alpha = alpha_override if alpha_override is not None else 1.0
    beta = beta_override if beta_override is not None else 1.0
    sf = SF_override if SF_override is not None else 1.0

    df_ = max(0.1, min(1.0, 100.0 / max(1.0, float(distance_m))))
    sf_ = max(0.1, min(1.0, float(seepage)))
    bf_ = max(0.1, min(1.0, float(bio_acc)))

    cn = float(cn_water) if cn_water else 0.0
    hg = float(hg_water) if hg_water else 0.0

    cn_score = (dc.hazard_score(cn, CN_LIMIT) if cn > 0 else 0.0) * df_ * sf_
    hg_score = (dc.hazard_score(hg, HG_LIMIT) if hg > 0 else 0.0) * df_ * bf_

    base_bonus = min(MAX_BONUS, alpha * cn_score + beta * hg_score)
    tox_bonus = base_bonus * sf
    tox = float(base_drastic) + tox_bonus

    _cls = classify(tox, mining_type=mining_type, is_tox=True,
                    calibrated_threshold=calibrated_threshold)
    inc = (tox_bonus / base_drastic * 100) if base_drastic > 0 else 0.0

    return {
        "base_drastic": base_drastic,
        "mining_type": mining_type,
        "alpha": alpha, "beta": beta, "source_factor": sf,
        "cri": round(cn / CN_LIMIT, 3) if CN_LIMIT else 0.0,
        "mri": round(hg / HG_LIMIT, 3) if HG_LIMIT else 0.0,
        "cn_score": round(cn_score, 2),
        "hg_score": round(hg_score, 2),
        "base_bonus": round(base_bonus, 2),
        "toxicity_bonus": round(tox_bonus, 2),
        "drastic_t": round(tox, 1),
        "increase_pct": round(inc, 1),
        "level": _cls["level"],
        "color": _cls["color"],
        "action": _cls["action"],
        "used_log_transform": True,
    }


# ============================================================
# SPSA
# ============================================================
def spsa_analysis(pv):
    D_r = _get_d_rating(float(pv.get("depth", 15.0)))
    R_r = _get_r_rating(float(pv.get("recharge", 100.0)))
    A_r = _get_a_rating(str(pv.get("aquifer", "massive_sandstone")))
    S_r = _get_s_rating(str(pv.get("soil", "sand")))
    T_r = _get_t_rating(float(pv.get("slope", 4.0)))
    I_r = _get_i_rating(str(pv.get("vadose", "sand_gravel")))
    C_r = _get_c_rating(float(pv.get("conductivity", 5.0)))

    weights = {"D": 5, "R": 4, "A": 3, "S": 2, "T": 1, "I": 5, "C": 3}
    total_weight = sum(weights.values())
    ratings_ = {"D": D_r, "R": R_r, "A": A_r, "S": S_r, "T": T_r, "I": I_r, "C": C_r}
    DI = sum(weights[k] * ratings_[k] for k in weights)

    results = []
    for k, w in weights.items():
        r = ratings_[k]
        theo = (w / total_weight) * 100
        eff = (w * r / DI) * 100 if DI > 0 else 0
        results.append({
            "param": k, "weight": w, "rating": r,
            "weighted_score": w * r,
            "theoretical_pct": round(theo, 2),
            "effective_pct": round(eff, 2),
            "difference": round(eff - theo, 2),
        })

    results_sorted = sorted(results, key=lambda x: x["effective_pct"], reverse=True)
    return {
        "base_index": DI,
        "parameters": results_sorted,
        "most_influential": results_sorted[0]["param"] if results_sorted else None,
        "least_influential": results_sorted[-1]["param"] if results_sorted else None,
    }


# ============================================================
# Sensitivity
# ============================================================
def sensitivity_analysis(pv, variation=0.10):
    D = float(pv.get("depth", 15.0))
    R = float(pv.get("recharge", 100.0))
    A = str(pv.get("aquifer", "massive_sandstone"))
    S = str(pv.get("soil", "sand"))
    T = float(pv.get("slope", 4.0))
    I = str(pv.get("vadose", "sand_gravel"))
    C = float(pv.get("conductivity", 5.0))

    def ci(d, r, a, s, t, i, c):
        return calc_index(_get_d_rating(d), _get_r_rating(r), _get_a_rating(a),
                          _get_s_rating(s), _get_t_rating(t), _get_i_rating(i),
                          _get_c_rating(c))

    base = ci(D, R, A, S, T, I, C)
    res = {}

    for name, val, lo, hi in [("D", D, 0.5, 100.0), ("R", R, 0.0, 400.0),
                              ("T", T, 0.0, 30.0), ("C", C, 0.01, 100.0)]:
        v = max(lo, min(hi, val * (1 + variation)))
        if name == "D":
            ni = ci(v, R, A, S, T, I, C)
        elif name == "R":
            ni = ci(D, v, A, S, T, I, C)
        elif name == "T":
            ni = ci(D, R, A, S, v, I, C)
        else:
            ni = ci(D, R, A, S, T, I, v)
        res[name] = {
            "original_phys": val,
            "modified_phys": round(v, 2),
            "new_index": ni,
            "change": ni - base,
            "sensitivity": round(abs(ni - base) / base * 100, 3) if base > 0 else 0,
        }

    for name, br, w in [("A", _get_a_rating(A), 3),
                        ("S", _get_s_rating(S), 2),
                        ("I", _get_i_rating(I), 5)]:
        nr = max(1, min(10, br + 1))
        ni = base - br * w + nr * w
        res[name] = {
            "original_phys": "rating",
            "modified_phys": "rating+1",
            "new_index": ni,
            "change": ni - base,
            "sensitivity": round(abs(ni - base) / base * 100, 3) if base > 0 else 0,
        }

    sr = dict(sorted(res.items(), key=lambda x: x[1]["sensitivity"], reverse=True))
    return {
        "base_index": base,
        "parameters": sr,
        "most_sensitive": list(sr.keys())[0] if sr else None,
    }


# ============================================================
# Monte Carlo
# ============================================================
def monte_carlo_analysis(pv, n_iter=1000, variation=0.15,
                          mining_type="traditional", calibrated_weights=None):
    np.random.seed(42)

    D = float(pv.get("depth", 15.0))
    R = float(pv.get("recharge", 100.0))
    T = float(pv.get("slope", 4.0))
    C = float(pv.get("conductivity", 5.0))
    A_b = _get_a_rating(str(pv.get("aquifer", "massive_sandstone")))
    S_b = _get_s_rating(str(pv.get("soil", "sand")))
    I_b = _get_i_rating(str(pv.get("vadose", "sand_gravel")))
    cn_w = float(pv.get("cn_water_mg_l", 0.025))
    hg_w = float(pv.get("hg_water_mg_l", 0.011))

    D_s = np.clip(np.random.normal(D, max(0.5, D * variation), n_iter), 0.5, 100.0)
    if R > 0:
        R_s = np.clip(np.random.lognormal(np.log(max(1, R)) - 0.5 * variation ** 2,
                                           variation, n_iter), 0.0, 400.0)
    else:
        R_s = np.zeros(n_iter)
    A_s = np.random.choice([max(1, A_b - 1), A_b, min(10, A_b + 1)], n_iter,
                            p=[0.15, 0.70, 0.15])
    S_s = np.random.choice([max(1, S_b - 1), S_b, min(10, S_b + 1)], n_iter,
                            p=[0.15, 0.70, 0.15])
    T_s = np.clip(np.random.normal(T, max(0.5, T * variation), n_iter), 0.0, 30.0)
    I_s = np.random.choice([max(1, I_b - 1), I_b, min(10, I_b + 1)], n_iter,
                            p=[0.15, 0.70, 0.15])
    C_s = np.clip(np.random.lognormal(np.log(max(0.01, C)) - 0.5 * variation ** 2,
                                       variation, n_iter), 0.01, 100.0)

    D_r = np.select(
        [D_s <= 1.5, D_s <= 4.6, D_s <= 9.1, D_s <= 15.2, D_s <= 22.9, D_s <= 30.5],
        [10, 9, 7, 5, 3, 2], default=1)
    R_r = np.select(
        [R_s <= 50.8, R_s <= 101.6, R_s <= 177.8, R_s <= 254.0],
        [1, 3, 6, 8], default=9)
    T_r = np.select(
        [T_s <= 2.0, T_s <= 6.0, T_s <= 12.0, T_s <= 18.0],
        [10, 9, 5, 3], default=1)
    C_r = np.select(
        [C_s <= 4.074, C_s <= 12.222, C_s <= 28.518, C_s <= 40.740, C_s <= 81.480],
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

    cn_s = np.clip(np.random.lognormal(np.log(max(0.001, cn_w)) - 0.5 * 0.04,
                                        0.2, n_iter), 0.0, 10.0)
    hg_s = np.clip(np.random.lognormal(np.log(max(0.0001, hg_w)) - 0.5 * 0.04,
                                        0.2, n_iter), 0.0, 10.0)

    cn_sc = np.where(cn_s > CN_LIMIT,
                     np.minimum(30.0, 30.0 * np.log10(np.maximum(cn_s / CN_LIMIT, 1.0)) / 3.0),
                     0.0)
    hg_sc = np.where(hg_s > HG_LIMIT,
                     np.minimum(30.0, 30.0 * np.log10(np.maximum(hg_s / HG_LIMIT, 1.0)) / 3.0),
                     0.0)

    bonus_s = np.minimum(50.0, a_s * cn_sc + b_s * hg_sc)
    tox = drastic + bonus_s * sf_s

    res = np.sort(drastic.astype(int))
    res_tox = np.sort(tox)

    def pct(arr, p):
        return float(np.percentile(arr, p))

    return {
        "mean": round(float(np.mean(res)), 1),
        "std": round(float(np.std(res)), 2),
        "min": int(res[0]),
        "max": int(res[-1]),
        "ci_90": (int(pct(res, 5)), int(pct(res, 95))),
        "prob_over_140": round(float(np.mean(res >= 140) * 100), 1),
        "tox_mean": round(float(np.mean(res_tox)), 1),
        "tox_std": round(float(np.std(res_tox)), 2),
        "tox_min": round(float(res_tox[0]), 1),
        "tox_max": round(float(res_tox[-1]), 1),
        "tox_ci_90": (round(pct(res_tox, 5), 1), round(pct(res_tox, 95), 1)),
        "tox_prob_over_140": round(float(np.mean(res_tox >= 140) * 100), 1),
        "tox_prob_over_180": round(float(np.mean(res_tox >= 180) * 100), 1),
        "n_iter": n_iter,
        "variation_pct": int(variation * 100),
    }


# ============================================================
# Mitigation
# ============================================================
def mitigate(idx, hdpe=False, treat=False, mon=False):
    m = float(idx)
    if hdpe:
        m *= 0.40
    if treat:
        m *= 0.60
    if mon:
        m *= 0.85
    red = ((idx - m) / idx * 100) if idx > 0 else 0.0
    return {"mitigated_index": round(m, 1), "reduction_pct": round(red, 1)}


# ============================================================
# Weighted toxicity
# ============================================================
def weighted_toxicity(hgw, hgs, cnw, cns, mining_type="traditional",
                      alpha_override=None, beta_override=None,
                      SF_override=None, use_log_transform=True):
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

    return {
        "index": round(tox_idx, 2),
        "drastic_tox_bonus": round(tox_idx, 2),
        "cn_score": round(cn_score, 2),
        "hg_score": round(hg_score, 2),
        "base_bonus": round(base_bonus, 2),
        "source_factor": round(sf, 2),
        "max_hq": round(max(hq_cn, hq_hg), 2),
        "category": _cls["level"],
        "action": _cls["action"],
        "mining_type": mining_type,
        "used_log_transform": True,
    }


# ============================================================
# HTML report
# ============================================================
def generate_html_report(site_info, drastic, drastic_t, level, recommendation):
    name = site_info.get("name", "N/A")
    state = site_info.get("state", "N/A")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    head = (
        '<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="UTF-8">'
        '<title>DRASTIC-Tox Report</title><style>'
        "body{font-family:Arial;padding:40px;max-width:800px;margin:0 auto;}"
        "h1{color:#5c2c16;border-bottom:3px solid #c19a6b;padding-bottom:10px;}"
        "table{width:100%;border-collapse:collapse;margin:15px 0;}"
        "th,td{padding:10px;border:1px solid #ddd;text-align:right;}"
        "th{background:#f5eedc;color:#5c2c16;}"
        ".metric{font-size:1.4em;font-weight:bold;color:#c19a6b;}"
        "</style></head><body>"
    )

    body = (
        "<h1>DRASTIC-Tox Report</h1>"
        f"<p><b>Date:</b> {now}</p>"
        "<table>"
        f"<tr><th>Site</th><td>{name}</td></tr>"
        f"<tr><th>State</th><td>{state}</td></tr>"
        f'<tr><th>DRASTIC</th><td class="metric">{drastic}/{DRASTIC_MAX}</td></tr>'
        f'<tr><th>DRASTIC-Tox</th><td class="metric">{drastic_t}/{DTOX_MAX}</td></tr>'
        f'<tr><th>Level</th><td class="metric">{level}</td></tr>'
        "</table>"
        f"<p><b>{recommendation}</b></p>"
        '<p style="text-align:center;color:#666;">DRASTIC-Tox v61.1</p>'
        "</body></html>"
    )

    return head + body


# ============================================================
# Self-test
# ============================================================
def _selftest():
    pv = {"depth": 15.0, "recharge": 100.0, "slope": 4.0, "conductivity": 5.0,
          "aquifer": "massive_sandstone", "soil": "sand", "vadose": "sand_gravel",
          "cn_water_mg_l": 0.025, "hg_water_mg_l": 0.011}

    sp = spsa_analysis(pv)
    assert "base_index" in sp
    assert sp["base_index"] > 0

    se = sensitivity_analysis(pv)
    assert "parameters" in se

    mc = monte_carlo_analysis(pv, n_iter=100)
    assert "mean" in mc

    m = mitigate(150.0, hdpe=True, treat=True)
    assert m["mitigated_index"] < 150.0

    wt = weighted_toxicity(0.011, 0.0, 0.025, 0.0)
    assert wt["index"] >= 0

    html = generate_html_report(
        {"name": "Test", "state": "Sennar"}, 100.0, 130.0, "high", "urgent")
    assert "DRASTIC-Tox" in html

    print("analysis_tools.py v61.1 — all self-tests passed")


if __name__ == "__main__":
    _selftest() 
