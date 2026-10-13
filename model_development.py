"""
model_development.py  v61 - drop-in replacement for v56.2
Requires: drastic_core.py, drastic_bridge.py, auto_calibration.py in the same folder.

Public names kept: calibrate_alpha_beta, calculate_ahp_weights, compare_models, evaluate_model.

Why the old version was replaced
  * calibrate_alpha_beta searched alpha/beta on the same rows it reported, at a typed threshold,
    with the old linear (saturating) scores
  * calculate_ahp_weights used a pairwise matrix with no source, never checked consistency
    (CR < 0.10 is required) and then rescaled/clipped the result to 1..5, which destroys AHP
  * compare_models used a different typed threshold for each model (100 / 140 / 100) on the
    training rows, so the comparison was not fair; "DRASTIC-Lu" used cyanide concentration as
    a "land-use factor" (the contaminant itself, i.e. circular)
Now every model is evaluated with the same leave-one-LOCATION-out scheme, threshold fitted
in-fold, on raw indices (no hidden rescaling).
"""
import numpy as np
import pandas as pd
import drastic_core as dc
import auto_calibration as ac
from drastic_bridge import (get_d_rating, get_r_rating, get_a_rating, get_s_rating,
                            get_t_rating, get_i_rating, get_c_rating)

RI_SAATY = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
CRITERIA = ["D", "R", "A", "S", "T", "I", "C"]

# ILLUSTRATIVE matrix (the one used before). It is NOT expert-derived: replace it with the
# consensus matrix of at least 3-5 hydrogeologists before calling the result "AHP".
DEFAULT_COMPARISON = np.array([
    [1,   2,   3,   4,   7,   2,   3],
    [1/2, 1,   2,   3,   5,   1,   2],
    [1/3, 1/2, 1,   2,   4,   1,   1],
    [1/4, 1/3, 1/2, 1,   3,   1/2, 1/2],
    [1/7, 1/5, 1/4, 1/3, 1,   1/5, 1/4],
    [1/2, 1,   1,   2,   5,   1,   2],
    [1/3, 1/2, 1,   2,   4,   1/2, 1],
])


# ------------------------------------------------------------------ 1. alpha/beta
def calibrate_alpha_beta(df, thresholds_dict=None, alpha_range=None, beta_range=None):
    """Keeps the old return shape (best_kappa / best_balanced / results) but the kappa shown is
    the nested leave-one-location-out estimate. thresholds_dict is ignored (fitted in-fold)."""
    try:
        d, cn, hg, y = _arrays_from_df(df)
    except ValueError as e:
        return {"error": str(e)}
    groups = ac.location_groups(df)
    A = list(alpha_range) if alpha_range is not None else [round(x, 2) for x in np.arange(0, 1.01, 0.1)]
    B = list(beta_range) if beta_range is not None else [round(x, 2) for x in np.arange(0, 1.01, 0.1)]
    rows = []
    for a in A:
        for b in B:
            pred, sc = ac.grouped_cv(d, cn, hg, y, fixed=(float(a), float(b)), groups=groups)
            m = ac.classification_metrics(y, pred, sc)
            rows.append({"alpha": round(float(a), 2), "beta": round(float(b), 2), "kappa": m["kappa"],
                         "accuracy": m["accuracy"], "recall": m["recall"]})
    res = pd.DataFrame(rows)
    if res.empty:
        return {"error": "No valid results"}
    res["score"] = res["kappa"] * 0.5 + res["recall"] / 100 * 0.5
    # ties -> closest to equal weights (no preference for extreme values)
    res["dist"] = (res["alpha"] - 1).abs() + (res["beta"] - 1).abs()
    best = res.sort_values(["kappa", "dist"], ascending=[False, True]).iloc[0]
    bal = res.sort_values(["score", "dist"], ascending=[False, True]).iloc[0]
    pack = lambda r: {"alpha": float(r["alpha"]), "beta": float(r["beta"]), "kappa": float(r["kappa"]),
                      "accuracy": float(r["accuracy"]), "recall": float(r["recall"])}
    return {"best_kappa": pack(best), "best_balanced": pack(bal), "results": res.drop(columns=["dist"]),
            "note": "Each (alpha,beta) is scored out-of-location with a threshold fitted in-fold; "
                    "picking the maximum of this table is still optimistic (selection bias)."}


def _arrays_from_df(df):
    """Accept either a raw site table or one that already has a DRASTIC column."""
    return ac.prepare_arrays(df)


# ------------------------------------------------------------------ 2. AHP
def calculate_ahp_weights(comparison=None):
    """Saaty AHP with consistency check. Returns raw weights (sum 1) and, for compatibility,
    D..C keys = weights x 7 (so a uniform vector would be 1.0 each) - no clipping."""
    M = np.array(DEFAULT_COMPARISON if comparison is None else comparison, dtype=float)
    n = M.shape[0]
    eigvals, eigvecs = np.linalg.eig(M)
    k = int(np.argmax(eigvals.real))
    w = np.abs(eigvecs[:, k].real)
    w = w / w.sum()
    lam = float(eigvals[k].real)
    ci = (lam - n) / (n - 1) if n > 1 else 0.0
    cr = ci / RI_SAATY.get(n, 1.49) if RI_SAATY.get(n, 1.49) > 0 else 0.0
    out = {c: float(round(w[i] * n, 3)) for i, c in enumerate(CRITERIA[:n])}
    out.update({"raw_weights": w.tolist(), "lambda_max": round(lam, 4), "CI": round(ci, 4),
                "CR": round(cr, 4), "consistent": bool(cr < 0.10),
                "source": "illustrative default matrix" if comparison is None else "user matrix"})
    return out


def ahp_index(ratings_df, ahp):
    return sum(ratings_df[c].values * ahp[c] for c in CRITERIA)


# ------------------------------------------------------------------ 3. compare models
def _rating_table(df):
    return pd.DataFrame({
        "D": [get_d_rating(float(v)) for v in df["depth_m"]],
        "R": [get_r_rating(float(v)) for v in df["recharge_mm"]],
        "A": [get_a_rating(str(v)) for v in df["aquifer"]],
        "S": [get_s_rating(str(v)) for v in df["soil"]],
        "T": [get_t_rating(float(v)) for v in df["slope_pct"]],
        "I": [get_i_rating(str(v)) for v in df["vadose"]],
        "C": [get_c_rating(float(v)) for v in df["conductivity"]]})


def compare_models(df, get_rating_funcs=None, calc_index_func=None):
    """Returns {model: metrics}. Same evaluation for all (leave-one-location-out, fitted threshold).
    Extra args are accepted for backward compatibility and ignored."""
    try:
        d, cn, hg, y = ac.prepare_arrays(df)
    except ValueError as e:
        return {"_error": {"error": str(e)}}
    groups = ac.location_groups(df)
    R = _rating_table(df)
    zeros = np.zeros(len(y))
    pest = sum(R[k].values * w for k, w in dc.W_PEST.items())
    ahp = calculate_ahp_weights()
    ahp_val = ahp_index(R, ahp)

    def run(base, fixed):
        pred, sc = ac.grouped_cv(base, cn, hg, y, fixed=fixed, groups=groups)
        return ac.classification_metrics(y, pred, sc)

    out = {
        "DRASTIC": run(d, (0.0, 0.0)),
        "Pesticide DRASTIC": run(pest, (0.0, 0.0)),
        "AHP-DRASTIC (illustrative matrix)": run(ahp_val, (0.0, 0.0)),
        "DRASTIC-Tox (equal weights)": run(d, (1.0, 1.0)),
        "Pesticide DRASTIC-Tox": run(pest, (1.0, 1.0)),
        "CN + Hg only (no hydrogeology)": run(zeros, (1.0, 1.0)),
    }
    out["AHP-DRASTIC (illustrative matrix)"]["weights"] = {k: ahp[k] for k in CRITERIA}
    out["AHP-DRASTIC (illustrative matrix)"]["CR"] = ahp["CR"]
    out["AHP-DRASTIC (illustrative matrix)"]["consistent"] = ahp["consistent"]
    return out


def evaluate_model(y_true, y_score, threshold):
    """In-sample evaluation at a GIVEN threshold (kept for compatibility; optimistic)."""
    y = np.asarray(y_true).astype(int)
    s = np.asarray(y_score, dtype=float)
    m = ac.classification_metrics(y, (s >= threshold).astype(int), s)
    m["threshold"] = threshold
    return m
