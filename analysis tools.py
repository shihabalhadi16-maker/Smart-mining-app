"""
analysis_tools.py — SPSA / الحساسية / Monte Carlo / التخفيف / التقرير
يعتمد على drastic_core.py + drastic_bridge.py
"""
import datetime
import numpy as np
import pandas as pd
import drastic_core as dc
from drastic_bridge import (
    get_d_rating, get_r_rating, get_a_rating, get_s_rating,
    get_t_rating, get_i_rating, get_c_rating,
    calc_index, calc_drastic_t, classify, DEFAULT_TOX_THRESHOLD, DRASTIC_MAX)

STANDARD = "EU"


def spsa_analysis(pv):
    D_r = get_d_rating(float(pv.get("depth", 15.0)))
    R_r = get_r_rating(float(pv.get("recharge", 100.0)))
    A_r = get_a_rating(str(pv.get("aquifer", "massive_sandstone")))
    S_r = get_s_rating(str(pv.get("soil", "sand")))
    T_r = get_t_rating(float(pv.get("slope", 4.0)))
    I_r = get_i_rating(str(pv.get("vadose", "sand_gravel")))
    C_r = get_c_rating(float(pv.get("conductivity", 5.0)))
    weights = {"D": 5, "R": 4, "A": 3, "S": 2, "T": 1, "I": 5, "C": 3}
    total_weight = sum(weights.values())
    ratings_ = {"D": D_r, "R": R_r, "A": A_r, "S": S_r, "T": T_r, "I": I_r, "C": C_r}
    DI = sum(weights[k] * ratings_[k] for k in weights)
    results = []
    for k, w in weights.items():
        r = ratings_[k]
        theo = (w / total_weight) * 100
        eff = (w * r / DI) * 100 if DI > 0 else 0
        results.append({"param": k, "weight": w, "rating": r,
                        "weighted_score": w * r,
                        "theoretical_pct": round(theo, 2),
                        "effective_pct": round(eff, 2),
                        "difference": round(eff - theo, 2)})
    results_sorted = sorted(results, key=lambda x: x["effective_pct"], reverse=True)
    return {"base_index": DI, "parameters": results_sorted,
            "most_influential": results_sorted[0]["param"] if results_sorted else None,
            "least_influential": results_sorted[-1]["param"] if results_sorted else None}


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
    for name, br, w in [("A", get_a_rating(A), 3), ("S", get_s_rating(S), 2), ("I", get_i_rating(I), 5)]:
        nr = max(1, min(10, br + 1))
        ni = base - br * w + nr * w
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
    R_s = np.clip(np.random.lognormal(np.log(max(1, R)) - 0.5 * variation ** 2,
                                       variation, n_iter), 0.0, 400.0) if R > 0 else np.zeros(n_iter)
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
    cn_s = np.clip(np.random.lognormal(np.log(max(0.001, cn_w)) - 0.5 * 0.2 ** 2, 0.2, n_iter), 0.0, 10.0)
    hg_s = np.clip(np.random.lognormal(np.log(max(0.0001, hg_w)) - 0.5 * 0.2 ** 2, 0.2, n_iter), 0.0, 10.0)
    cn_sc = np.where(cn_s > CN_LIMIT,
                     np.minimum(30.0, 30.0 * np.log10(np.maximum(cn_s / CN_LIMIT, 1.0)) / 3.0), 0.0)
    hg_sc = np.where(hg_s > HG_LIMIT,
                     np.minimum(30.0, 30.0 * np.log10(np.maximum(hg_s / HG_LIMIT, 1.0)) / 3.0), 0.0)
    bonus_s = np.minimum(50.0, a_s * cn_sc + b_s * hg_sc)
    tox = drastic + bonus_s * sf_s

    res = np.sort(drastic.astype(int))
    res_tox = np.sort(tox)

    def pct(arr, p):
        return float(np.percentile(arr, p))

    return {
        "mean": round(float(np.mean(res)), 1), "std": round(float(np.std(res)), 2),
        "min": int(res[0]), "max": int(res[-1]),
        "ci_90": (int(pct(res, 5)), int(pct(res, 95))),
        "prob_over_140": round(float(np.mean(res >= 140) * 100), 1),
        "tox_mean": round(float(np.mean(res_tox)), 1),
        "tox_std": round(float(np.std(res_tox)), 2),
        "tox_min": round(float(res_tox[0]), 1), "tox_max": round(float(res_tox[-1]), 1),
        "tox_ci_90": (round(pct(res_tox, 5), 1), round(pct(res_tox, 95), 1)),
        "tox_prob_over_140": round(float(np.mean(res_tox >= 140) * 100), 1),
        "tox_prob_over_180": round(float(np.mean(res_tox >= 180) * 100), 1),
        "n_iter": n_iter, "variation_pct": int(variation * 100),
    }


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
    return {
        "index": round(tox_idx, 2), "drastic_tox_bonus": round(tox_idx, 2),
        "cn_score": round(cn_score, 2), "hg_score": round(hg_score, 2),
        "base_bonus": round(base_bonus, 2), "source_factor": round(sf, 2),
        "max_hq": round(max(hq_cn, hq_hg), 2),
        "category": _cls["level"], "action": _cls["action"],
        "mining_type": mining_type, "used_log_transform": True,
    }


def generate_html_report(site_info, drastic, drastic_t, level, recommendation):
    name = site_info.get("name", "N/A")
    state = site_info.get("state", "N/A")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    html = (
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
        f"<p><b>Date:</b> {now}</p>"
        "<table>"
        f"<tr><th>Site</th><td>{name}</td></tr>"
        f"<tr><th>State</th><td>{state}</td></tr>"
        f'<tr><th>DRASTIC</th><td class="metric">{drastic}/{DRASTIC_MAX}</td></tr>'
        f'<tr><th>DRASTIC-Tox</th><td class="metric">{drastic_t}/276</td></tr>'
        f'<tr><th>Level</th><td class="metric">{level}</td></tr>'
        "</table>"
        f"<p><b>{recommendation}</b></p>"
        '<p style="text-align:center;color:#666;">DRASTIC-Tox v61</p>'
        "</body></html>"
    )
    return html
