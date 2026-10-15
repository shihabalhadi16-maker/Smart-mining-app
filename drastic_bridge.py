"""
drastic_bridge.py - keeps app.py's existing function names/signatures,
but delegates all calculations to drastic_core.py.

In app.py: delete the old definitions of
  get_d_rating ... get_c_rating, calc_index, classify, calc_drastic_t
and put instead:
  from drastic_bridge import (get_d_rating, get_r_rating, get_a_rating, get_s_rating,
      get_t_rating, get_i_rating, get_c_rating, calc_index, classify, calc_drastic_t,
      calc_pesticide_index, DEFAULT_TOX_THRESHOLD, DRASTIC_MAX)
"""
import drastic_core as dc

STANDARD = dc.DEFAULT_STANDARD   # "SD" (Sudanese, default) | "EU" | "WHO" (WHO has no cyanide limit)
HQ_REF = 1000.0             # hazard quotient mapped to score 30 (assumption)
DRASTIC_MAX = 226           # was 230 - correct maximum (Aller 1987)
DEFAULT_TOX_THRESHOLD = 140.0   # old 144.4 was fitted on the OLD scoring: retired

# ---- ratings (unknown categories / negative values now raise ValueError)
get_d_rating = dc.rate_D
get_r_rating = dc.rate_R
get_t_rating = dc.rate_T
get_c_rating = dc.rate_C
def get_a_rating(a): return dc._cat(dc.AQUIFER, a, "A")
def get_s_rating(s): return dc._cat(dc.SOIL, s, "S")
def get_i_rating(i): return dc._cat(dc.VADOSE, i, "I")


def calc_index(D, R, A, S, T, I, C):
    w = dc.W_STD
    return D * w["D"] + R * w["R"] + A * w["A"] + S * w["S"] + T * w["T"] + I * w["I"] + C * w["C"]


def calc_pesticide_index(D, R, A, S, T, I, C):
    """Pesticide DRASTIC (agricultural), range 26-256. Same ratings as calc_index."""
    w = dc.W_PEST
    return D * w["D"] + R * w["R"] + A * w["A"] + S * w["S"] + T * w["T"] + I * w["I"] + C * w["C"]


def classify(idx, mining_type=None, is_tox=False, calibrated_threshold=None):
    """Same return shape as before. For Tox, an explicit calibrated threshold wins;
    otherwise the same 100/140/180 bands are used."""
    if is_tox and calibrated_threshold is not None:
        th = calibrated_threshold
        if idx >= th + 80: return {"level": "very_high", "color": "red", "action": "action_immediate"}
        if idx >= th:      return {"level": "high", "color": "orange", "action": "action_urgent"}
        if idx >= th - 30: return {"level": "medium", "color": "yellow", "action": "action_periodic"}
        return {"level": "low", "color": "green", "action": "action_routine"}
    if idx >= 180: return {"level": "very_high", "color": "red", "action": "action_immediate"}
    if idx >= 140: return {"level": "high", "color": "orange", "action": "action_urgent"}
    if idx >= 100: return {"level": "medium", "color": "yellow", "action": "action_periodic"}
    return {"level": "low", "color": "green", "action": "action_routine"}


def calc_drastic_t(base_drastic, cn_water, hg_water, distance_m=100.0, seepage=1.0,
                   bio_acc=1.0, mining_type="traditional", alpha_override=None,
                   beta_override=None, SF_override=None, use_log_transform=None,
                   calibrated_threshold=None):
    """Drop-in replacement. alpha->weight of CN score, beta->weight of Hg score,
    SF multiplies the bonus (default 1.0: mining-type factors are no longer assumed).
    distance_m / seepage / bio_acc / use_log_transform are ignored (kept for compatibility)."""
    w_cn = 1.0 if alpha_override is None else alpha_override
    w_hg = 1.0 if beta_override is None else beta_override
    sf = 1.0 if SF_override is None else SF_override
    L = dc.LIMITS_MG_L[STANDARD]
    s_cn = dc.hazard_score(cn_water, L["cn"], HQ_REF) if L["cn"] else 0.0
    s_hg = dc.hazard_score(hg_water, L["hg"], HQ_REF)
    base_bonus = min(50.0, w_cn * s_cn + w_hg * s_hg)
    bonus = base_bonus * sf
    dt = base_drastic + bonus
    cls = classify(dt, is_tox=True, calibrated_threshold=calibrated_threshold)
    return {"base_drastic": base_drastic, "mining_type": mining_type,
            "alpha": w_cn, "beta": w_hg, "source_factor": sf,
            "cri": round(cn_water / L["cn"], 3) if L["cn"] else 0.0,
            "mri": round(hg_water / L["hg"], 3),
            "cn_score": round(s_cn, 2), "hg_score": round(s_hg, 2),
            "base_bonus": round(base_bonus, 2), "toxicity_bonus": round(bonus, 2),
            "drastic_t": round(dt, 1), "drastic_p": round(dt, 1),
            "modifier": round(1.0 + bonus / max(base_drastic, 1), 3),
            "increase_pct": round(bonus / base_drastic * 100, 1) if base_drastic > 0 else 0,
            "level": cls["level"], "color": cls["color"], "used_log_transform": True,
            "unit_warnings": dc.check_units(cn_water, hg_water)}


if __name__ == "__main__":
    r = calc_drastic_t(calc_index(9, 6, 8, 6, 10, 8, 6), 0.35, 0.36)
    assert r["hg_score"] < 30 and r["drastic_t"] > 173
    assert calc_drastic_t(100, 0.01, 0.0005)["toxicity_bonus"] == 0
    try:
        get_i_rating("bad"); raise SystemExit("no error")
    except ValueError:
        pass
    print("bridge OK", r["drastic_t"], r["cn_score"], r["hg_score"])
