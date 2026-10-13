"""
drastic_bridge.py — واجهة توافق بين app.py و drastic_core.py
يوفر: get_*_rating, calc_index, calc_pesticide_index, classify,
       calc_drastic_t, DEFAULT_TOX_THRESHOLD, DRASTIC_MAX
"""
import math
import drastic_core as dc

DRASTIC_MIN = 23
DRASTIC_MAX = 226
DTOX_MIN = 23
DTOX_MAX = 276
DEFAULT_TOX_THRESHOLD = 144.4

# ---------------------------------------------------------------- ratings
def get_d_rating(depth_m):       return dc.rate_D(float(depth_m))
def get_r_rating(recharge_mm):   return dc.rate_R(float(recharge_mm))
def get_t_rating(slope_pct):     return dc.rate_T(float(slope_pct))
def get_c_rating(conductivity):  return dc.rate_C(float(conductivity))

def get_a_rating(aquifer):
    key = str(aquifer)
    if key not in dc.AQUIFER:
        raise ValueError(f"Aquifer unknown: {key}. Valid: {sorted(dc.AQUIFER)}")
    return dc.AQUIFER[key]

def get_s_rating(soil):
    key = str(soil)
    if key not in dc.SOIL:
        raise ValueError(f"Soil unknown: {key}. Valid: {sorted(dc.SOIL)}")
    return dc.SOIL[key]

def get_i_rating(vadose):
    key = str(vadose)
    if key not in dc.VADOSE:
        raise ValueError(f"Vadose unknown: {key}. Valid: {sorted(dc.VADOSE)}")
    return dc.VADOSE[key]

# ---------------------------------------------------------------- indices
def calc_index(D, R, A, S, T, I, C):
    w = dc.W_STD
    return (D * w["D"]) + (R * w["R"]) + (A * w["A"]) + (S * w["S"]) + \
           (T * w["T"]) + (I * w["I"]) + (C * w["C"])

def calc_pesticide_index(D, R, A, S, T, I, C):
    w = dc.W_PEST
    return (D * w["D"]) + (R * w["R"]) + (A * w["A"]) + (S * w["S"]) + \
           (T * w["T"]) + (I * w["I"]) + (C * w["C"])

# ---------------------------------------------------------------- classify
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

# ---------------------------------------------------------------- DRASTIC-Tox
def calc_drastic_t(base_drastic, cn_water, hg_water, distance_m=100.0, seepage=1.0,
                   bio_acc=1.0, mining_type="traditional",
                   alpha_override=None, beta_override=None, SF_override=None,
                   use_log_transform=True, calibrated_threshold=None):
    """DRASTIC-Tox = base + min(50, alpha·CN + beta·Hg) · SF
    CN/Hg use log10 hazard score (saturates at HQ=1000)."""
    CN_LIMIT = dc.LIMITS_MG_L["EU"]["cn"]      # 0.05 mg/L
    HG_LIMIT = dc.LIMITS_MG_L["EU"]["hg"]      # 0.001 mg/L
    MAX_BONUS = 50.0

    alpha = alpha_override if alpha_override is not None else 1.0
    beta = beta_override if beta_override is not None else 1.0
    SF = SF_override if SF_override is not None else 1.0

    d_factor = max(0.1, min(1.0, 100.0 / max(1.0, float(distance_m))))
    s_factor = max(0.1, min(1.0, float(seepage)))
    b_factor = max(0.1, min(1.0, float(bio_acc)))

    cn = float(cn_water) if cn_water else 0.0
    hg = float(hg_water) if hg_water else 0.0

    cn_score = (dc.hazard_score(cn, CN_LIMIT) if cn > 0 else 0.0) * d_factor * s_factor
    hg_score = (dc.hazard_score(hg, HG_LIMIT) if hg > 0 else 0.0) * d_factor * b_factor

    base_bonus = min(MAX_BONUS, alpha * cn_score + beta * hg_score)
    toxicity_bonus = base_bonus * SF
    drastic_t = float(base_drastic) + toxicity_bonus

    _cls = classify(drastic_t, mining_type=mining_type, is_tox=True,
                    calibrated_threshold=calibrated_threshold)
    inc = (toxicity_bonus / base_drastic * 100) if base_drastic > 0 else 0.0

    return {
        "base_drastic": base_drastic,
        "mining_type": mining_type,
        "alpha": alpha, "beta": beta, "source_factor": SF,
        "cri": round(cn / CN_LIMIT, 3) if CN_LIMIT else 0.0,
        "mri": round(hg / HG_LIMIT, 3) if HG_LIMIT else 0.0,
        "cn_score": round(cn_score, 2),
        "hg_score": round(hg_score, 2),
        "base_bonus": round(base_bonus, 2),
        "toxicity_bonus": round(toxicity_bonus, 2),
        "drastic_t": round(drastic_t, 1),
        "increase_pct": round(inc, 1),
        "level": _cls["level"], "color": _cls["color"], "action": _cls["action"],
        "used_log_transform": bool(use_log_transform),
    }
