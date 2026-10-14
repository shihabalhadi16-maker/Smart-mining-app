"""
analysis_tools.py  v61 - analysis helpers that used to live inside app.py
Requires: drastic_core.py, drastic_bridge.py

Everything here uses the SAME scoring as the rest of the project (drastic_core):
  * standard DRASTIC ratings/weights, unknown categories raise errors
  * hazard score = log scale of concentration / limit (0 if compliant), EU limits by default
Moved out of app.py: spsa_analysis, sensitivity_analysis, monte_carlo_analysis, weighted_toxicity,
transport_timeseries (was model_contaminant_transport_fixed), mitigate, generate_html_report.
"""
import datetime
import math
import numpy as np
import pandas as pd
import drastic_core as dc
from drastic_bridge import (get_d_rating, get_r_rating, get_a_rating, get_s_rating, get_t_rating,
                            get_i_rating, get_c_rating, calc_index, classify, DRASTIC_MAX, HQ_REF, STANDARD)

W = dc.W_STD
TOTAL_W = sum(W.values())          # 23


def _ratings(pv):
    return {"D": get_d_rating(float(pv.get("depth", 15.0))), "R": get_r_rating(float(pv.get("recharge", 100.0))),
            "A": get_a_rating(str(pv.get("aquifer", "massive_sandstone"))), "S": get_s_rating(str(pv.get("soil", "sand"))),
            "T": get_t_rating(float(pv.get("slope", 4.0))), "I": get_i_rating(str(pv.get("vadose", "sand_gravel"))),
            "C": get_c_rating(float(pv.get("conductivity", 5.0)))}


# ----------------------------------------------------------------- SPSA (Napolitano & Fabbri 1996)
def spsa_analysis(pv):
    r = _ratings(pv)
    di = sum(r[k] * W[k] for k in W)
    rows = []
    for k in W:
        theo = W[k] / TOTAL_W * 100
        eff = W[k] * r[k] / di * 100 if di > 0 else 0.0
        rows.append({"param": k, "weight": W[k], "rating": r[k], "weighted_score": W[k] * r[k],
                     "theoretical_pct": round(theo, 2), "effective_pct": round(eff, 2),
                     "difference": round(eff - theo, 2)})
    rows.sort(key=lambda x: x["effective_pct"], reverse=True)
    return {"base_index": di, "parameters": rows, "most_influential": rows[0]["param"],
            "least_influential": rows[-1]["param"]}


# ----------------------------------------------------------------- one-at-a-time sensitivity
def sensitivity_analysis(pv, variation=0.10):
    D, R = float(pv.get("depth", 15.0)), float(pv.get("recharge", 100.0))
    T, C = float(pv.get("slope", 4.0)), float(pv.get("conductivity", 5.0))
    base_r = _ratings(pv)
    base = sum(base_r[k] * W[k] for k in W)

    def idx(**ov):
        r = dict(base_r)
        r.update(ov)
        return sum(r[k] * W[k] for k in W)

    res = {}
    for name, val, lo, hi, fn in (("D", D, 0.5, 100.0, get_d_rating), ("R", R, 0.0, 400.0, get_r_rating),
                                  ("T", T, 0.0, 30.0, get_t_rating), ("C", C, 0.01, 100.0, get_c_rating)):
        v = max(lo, min(hi, val * (1 + variation)))
        ni = idx(**{name: fn(v)})
        res[name] = {"original_phys": val, "modified_phys": round(v, 2), "new_index": ni, "change": ni - base,
                     "sensitivity": round(abs(ni - base) / base * 100, 3)}
    for name in ("A", "S", "I"):
        ni = idx(**{name: min(10, base_r[name] + 1)})
        res[name] = {"original_phys": "rating", "modified_phys": "rating+1", "new_index": ni, "change": ni - base,
                     "sensitivity": round(abs(ni - base) / base * 100, 3)}
    res = dict(sorted(res.items(), key=lambda x: x[1]["sensitivity"], reverse=True))
    return {"base_index": base, "parameters": res, "most_sensitive": next(iter(res))}


# ----------------------------------------------------------------- Monte Carlo
def _bin_vec(x, edges, ratings):
    return np.asarray(ratings)[np.searchsorted(edges, x, side="left")]


def _hazard_vec(conc, limit, max_score=30.0):
    hq = np.maximum(conc / limit, 1.0)
    return np.where(conc / limit <= 1.0, 0.0, np.minimum(max_score, max_score * np.log10(hq) / math.log10(HQ_REF)))


def monte_carlo_analysis(pv, n_iter=1000, variation=0.15, mining_type="traditional", calibrated_weights=None, seed=42):
    """DRASTIC and DRASTIC-Tox distributions. Same additive log model as the rest of the project.
    Weights alpha/beta are drawn around their central values (equal weights unless a calibrated
    profile is given). The result reflects the ASSUMED input uncertainty, not field uncertainty."""
    rng = np.random.default_rng(seed)
    D, R = float(pv.get("depth", 15.0)), float(pv.get("recharge", 100.0))
    T, C = float(pv.get("slope", 4.0)), float(pv.get("conductivity", 5.0))
    A_b, S_b, I_b = (get_a_rating(str(pv.get("aquifer", "massive_sandstone"))), get_s_rating(str(pv.get("soil", "sand"))),
                     get_i_rating(str(pv.get("vadose", "sand_gravel"))))
    cn_w, hg_w = float(pv.get("cn_water_mg_l", 0.025)), float(pv.get("hg_water_mg_l", 0.011))

    D_s = np.clip(rng.normal(D, max(0.5, D * variation), n_iter), 0.5, 100.0)
    R_s = np.clip(rng.lognormal(np.log(max(1, R)) - 0.5 * variation ** 2, variation, n_iter), 0.0, 400.0) if R > 0 else np.zeros(n_iter)
    T_s = np.clip(rng.normal(T, max(0.5, T * variation), n_iter), 0.0, 30.0)
    C_s = np.clip(rng.lognormal(np.log(max(0.01, C)) - 0.5 * variation ** 2, variation, n_iter), 0.01, 100.0)
    pick = lambda b: rng.choice([max(1, b - 1), b, min(10, b + 1)], n_iter, p=[0.15, 0.70, 0.15])
    A_s, S_s, I_s = pick(A_b), pick(S_b), pick(I_b)

    D_r = _bin_vec(D_s, [1.5, 4.6, 9.1, 15.2, 22.9, 30.5], [10, 9, 7, 5, 3, 2, 1])
    R_r = _bin_vec(R_s, [50.8, 101.6, 177.8, 254.0], [1, 3, 6, 8, 9])
    T_r = _bin_vec(T_s, [2, 6, 12, 18], [10, 9, 5, 3, 1])
    C_r = _bin_vec(C_s, [4.074, 12.222, 28.518, 40.74, 81.48], [1, 2, 4, 6, 8, 10])
    drastic = D_r * W["D"] + R_r * W["R"] + A_s * W["A"] + S_s * W["S"] + T_r * W["T"] + I_s * W["I"] + C_r * W["C"]

    cw = calibrated_weights or {}
    a_m, b_m, sf_m = cw.get("alpha", 1.0), cw.get("beta", 1.0), cw.get("SF", 1.0)
    a_s, b_s = np.clip(rng.normal(a_m, 0.1, n_iter), 0, 1.5), np.clip(rng.normal(b_m, 0.1, n_iter), 0, 1.5)
    sf_s = np.clip(rng.normal(sf_m, 0.05, n_iter), 0.5, 1.5)
    L = dc.LIMITS_MG_L[STANDARD]
    cn_s = np.clip(rng.lognormal(np.log(max(0.001, cn_w)) - 0.5 * 0.2 ** 2, 0.2, n_iter), 0.0, 100.0)
    hg_s = np.clip(rng.lognormal(np.log(max(0.0001, hg_w)) - 0.5 * 0.2 ** 2, 0.2, n_iter), 0.0, 100.0)
    s_cn = _hazard_vec(cn_s, L["cn"]) if L["cn"] else np.zeros(n_iter)
    bonus = np.minimum(50.0, a_s * s_cn + b_s * _hazard_vec(hg_s, L["hg"])) * sf_s
    tox = drastic + bonus
    r, rt = np.sort(drastic.astype(float)), np.sort(tox)
    pc = lambda arr, p: float(np.percentile(arr, p))
    return {"mean": round(float(r.mean()), 1), "std": round(float(r.std()), 2), "min": int(r[0]), "max": int(r[-1]),
            "ci_90": (int(pc(r, 5)), int(pc(r, 95))), "prob_over_140": round(float((r >= 140).mean() * 100), 1),
            "tox_mean": round(float(rt.mean()), 1), "tox_std": round(float(rt.std()), 2),
            "tox_min": round(float(rt[0]), 1), "tox_max": round(float(rt[-1]), 1),
            "tox_ci_90": (round(pc(rt, 5), 1), round(pc(rt, 95), 1)),
            "tox_prob_over_140": round(float((rt >= 140).mean() * 100), 1),
            "tox_prob_over_180": round(float((rt >= 180).mean() * 100), 1),
            "n_iter": n_iter, "variation_pct": int(variation * 100)}


# ----------------------------------------------------------------- water toxicity tab
_LEVEL = {"compliant": ("low", "action_routine"), "elevated": ("medium", "action_periodic"),
          "high": ("high", "action_urgent"), "severe": ("very_high", "action_immediate")}


def weighted_toxicity(hgw, hgs, cnw, cns, mining_type="traditional", alpha_override=None, beta_override=None,
                      SF_override=None, use_log_transform=None):
    """Water-based hazard bonus. hgs/cns (soil) are accepted but NOT used: there is no sourced soil limit
    in the project (the old soil factor multiplied the result by an arbitrary 1.0-1.5)."""
    L = dc.LIMITS_MG_L[STANDARD]
    a = 1.0 if alpha_override is None else alpha_override
    b = 1.0 if beta_override is None else beta_override
    sf = 1.0 if SF_override is None else SF_override
    s_cn = dc.hazard_score(cnw, L["cn"], HQ_REF) if L["cn"] else 0.0
    s_hg = dc.hazard_score(hgw, L["hg"], HQ_REF)
    base = min(50.0, a * s_cn + b * s_hg)
    hq = max(cnw / L["cn"] if L["cn"] else 0.0, hgw / L["hg"])
    cat, act = _LEVEL[dc.hazard_class(hq)]
    return {"index": round(base * sf, 2), "drastic_tox_bonus": round(base * sf, 2), "cn_score": round(s_cn, 2),
            "hg_score": round(s_hg, 2), "base_bonus": round(base, 2), "source_factor": round(sf, 2),
            "soil_factor": 1.0, "max_hq": round(hq, 2), "category": cat, "action": act,
            "mining_type": mining_type, "used_log_transform": True}


# ----------------------------------------------------------------- mitigation (ILLUSTRATIVE)
def mitigate(idx, hdpe=False, treat=False, mon=False):
    """Multipliers are assumptions (no source): use only to illustrate relative effects."""
    m = float(idx)
    if hdpe: m *= 0.40
    if treat: m *= 0.60
    if mon: m *= 0.85
    red = ((idx - m) / idx * 100) if idx > 0 else 0.0
    return {"mitigated_index": round(m, 1), "reduction_pct": round(red, 1), "illustrative": True}


# ----------------------------------------------------------------- transport (Ogata-Banks, both terms)
def transport_timeseries(C0, K, porosity, gradient, distance, years, dispersivity=10.0):
    v = (K * gradient) / porosity
    if v <= 0:
        return {"error": "Velocity is zero or negative"}
    D = max(dispersivity * v, 1e-9)
    total_days = int(years * 365.25)
    times = np.linspace(1, total_days, min(200, max(10, total_days)))
    out = []
    for t in times:
        s = 2.0 * math.sqrt(D * t)
        t1 = math.erfc((distance - v * t) / s)
        t2 = math.exp(v * distance / D) * math.erfc((distance + v * t) / s) if v * distance / D < 600 else 0.0
        out.append(max(0.0, min(C0, 0.5 * C0 * (t1 + t2))))
    df = pd.DataFrame({"Year": [round(t / 365.25, 2) for t in times], "Concentration": [round(c, 6) for c in out],
                       "Distance": [round(v * t, 1) for t in times]})
    return {"results": df, "v_seepage": round(v, 6), "D_dispersion": round(D, 4),
            "t_travel_years": round(distance / v / 365.25, 3)}


# ----------------------------------------------------------------- descriptive metrics
def descriptive_metrics(y_true, y_score, threshold):
    """In-sample metrics at a GIVEN threshold (descriptive only)."""
    import advanced_modules as am
    return am.calculate_confusion_matrix(y_score, y_true, threshold)


# ----------------------------------------------------------------- HTML report
def generate_html_report(site_info, drastic, drastic_t, level, recommendation):
    return f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="UTF-8"><title>Report</title>
<style>body{{font-family:Arial;padding:40px;max-width:800px;margin:0 auto;}}
h1{{color:#5c2c16;border-bottom:3px solid #c19a6b;padding-bottom:10px;}}
table{{width:100%;border-collapse:collapse;margin:15px 0;}}th,td{{padding:10px;border:1px solid #ddd;text-align:right;}}
th{{background-color:#f5eedc;color:#5c2c16;}}.metric{{font-size:1.5em;font-weight:bold;color:#c19a6b;}}
.warn{{background:#fff3e0;border-right:4px solid #ff9800;padding:10px;margin-top:20px;font-size:.9em;}}
</style></head><body>
<h1>DRASTIC / DRASTIC-Tox Report</h1>
<p><b>Date:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<table>
<tr><th>Site</th><td>{site_info.get('name','N/A')}</td></tr>
<tr><th>State</th><td>{site_info.get('state','N/A')}</td></tr>
<tr><th>DRASTIC (Aller 1987, range 23-{DRASTIC_MAX})</th><td class="metric">{drastic}/{DRASTIC_MAX}</td></tr>
<tr><th>DRASTIC-Tox (experimental)</th><td class="metric">{drastic_t}</td></tr>
<tr><th>Level</th><td class="metric">{level}</td></tr>
</table>
<p><b>{recommendation}</b></p>
<div class="warn">Screening-level result from a pilot tool. Limits: EU Directive 98/83/EC ({STANDARD}).
The DRASTIC-Tox bonus is an unvalidated formulation; not for regulatory or health decisions.</div>
</body></html>"""
