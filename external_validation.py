"""
external_validation.py  v61 - drop-in replacement for v58.3
Requires: drastic_core.py, drastic_bridge.py, auto_calibration.py in the same folder.

Why the old version was replaced
  * "external validation" was a split of the SAME sites; with n=11 the test set had 3-4 rows
  * the threshold (106.5 / 140 / 144.4 ...) was typed in, never fitted inside the training part
  * Dry/Wet rows of the same place were split between train and test (leakage)
  * 5-fold CV on 11 rows gave folds of 2 rows: kappa/AUC per fold are meaningless
  * Brier score was computed on score/230 (not a probability)
  * the "baselines" were fitted on the DRASTIC-Tox score itself (one feature), so they were
    not baselines at all; a concentration-only baseline was missing (the label is probably
    defined by concentrations)
  * rows that failed were silently skipped

What it does now
  * leave-one-LOCATION-out CV: weights (if fitted) and threshold are fitted on the other locations
  * compares: DRASTIC alone, DRASTIC-Tox (equal weights), DRASTIC-Tox (weights fitted in-fold),
    Hg only, CN+Hg only (no hydrogeology), and the plain regulatory exceedance rule
  * 95% CI of kappa by resampling locations; a leaky leave-one-row-out run is shown for contrast
If a concentration-only model matches DRASTIC-Tox, the hydrogeological part adds nothing yet.
"""
import numpy as np
import pandas as pd
import auto_calibration as ac

NAMES = {
    "drastic": "DRASTIC",
    "tox_equal": "DRASTIC-Tox (equal weights)",
    "tox_fit": "DRASTIC-Tox (weights fitted in-fold)",
    "hg_only": "Hg only (no hydrogeology)",
    "cnhg_only": "CN + Hg only (no hydrogeology)",
    "exceed": "Regulatory exceedance rule (no fitting)",
}


def _pr_auc(y, s):
    try:
        from sklearn.metrics import average_precision_score
        return round(float(average_precision_score(y, s)), 3)
    except Exception:
        return None


def external_validation_analysis(
        df, mining_type="traditional", threshold_d=None, threshold_dt=None,
        test_size=None, n_folds=None, random_state=42,
        calc_index_fn=None, calc_drastic_t_fn=None, get_d_rating_fn=None,
        get_r_rating_fn=None, get_a_rating_fn=None, get_s_rating_fn=None,
        get_t_rating_fn=None, get_i_rating_fn=None, get_c_rating_fn=None,
        calibrated_weights=None, sklearn_ok=True, n_boot=2000, n_steps=11):
    """Old keyword arguments are accepted and ignored (thresholds are fitted, not typed)."""
    try:
        d, cn, hg, y = ac.prepare_arrays(df)
    except ValueError as e:
        return {"error": str(e)}
    groups = ac.location_groups(df)
    n, n_loc = len(y), len(np.unique(groups))
    pos_loc = len(np.unique(groups[y == 1]))
    neg_loc = len(np.unique(groups[y == 0]))
    if n_loc < 4 or pos_loc < 2 or neg_loc < 2:
        return {"error": f"Need >= 2 contaminated and >= 2 clean LOCATIONS "
                         f"(found {pos_loc} / {neg_loc} in {n_loc} locations)."}

    grid = ac.score_grid(n_steps, None, None)
    zeros = np.zeros(n)
    cn_mg = df["cn_water_mg_l"].astype(float).values
    hg_mg = df["hg_water_mg_l"].astype(float).values
    cn_lim, hg_lim = ac.CN_LIMIT, ac.HG_LIMIT

    runs = {
        "drastic": ac.grouped_cv(d, cn, hg, y, fixed=(0.0, 0.0), groups=groups),
        "tox_equal": ac.grouped_cv(d, cn, hg, y, fixed=(1.0, 1.0), groups=groups),
        "tox_fit": ac.grouped_cv(d, cn, hg, y, grid=grid, groups=groups),
        "hg_only": ac.grouped_cv(zeros, cn, hg, y, fixed=(0.0, 1.0), groups=groups),
        "cnhg_only": ac.grouped_cv(zeros, cn, hg, y, fixed=(1.0, 1.0), groups=groups),
    }
    hq = np.maximum(cn_mg / cn_lim, hg_mg / hg_lim)
    runs["exceed"] = ((hq > 1).astype(int), hq)

    models = {}
    for key, (pred, sc) in runs.items():
        m = ac.classification_metrics(y, pred, sc)
        lo, hi = ac.bootstrap_group_ci(y, pred, groups, n_boot=n_boot, seed=random_state)
        m.update({"name": NAMES[key], "kappa_ci_95": (lo, hi), "pr_auc": _pr_auc(y, sc)})
        models[key] = m

    naive_pred, naive_sc = ac.grouped_cv(d, cn, hg, y, fixed=(1.0, 1.0), groups=None)
    naive = ac.classification_metrics(y, naive_pred, naive_sc)

    extra = None
    if calibrated_weights and "alpha" in calibrated_weights:
        p, s = ac.grouped_cv(d, cn, hg, y, fixed=(float(calibrated_weights["alpha"]),
                                                  float(calibrated_weights["beta"])), groups=groups)
        extra = ac.classification_metrics(y, p, s)
        extra["note"] = "Profile weights were fitted on these same sites: optimistic."

    warnings = [
        f"{n} rows but only {n_loc} independent locations "
        f"({pos_loc} contaminated, {neg_loc} clean): intervals are very wide.",
        "Dry/Wet rows of one place are never split between training and test.",
    ]
    if pos_loc < 5:
        warnings.append("Fewer than 5 contaminated locations: kappa/AUC are not stable.")
    gap = naive["kappa"] - models["tox_equal"]["kappa"]
    if gap > 0.1:
        warnings.append(f"Leave-one-row-out (leaky) kappa is {gap:+.2f} higher than leave-one-location-out.")
    best_conc = max(models["hg_only"]["kappa"], models["cnhg_only"]["kappa"], models["exceed"]["kappa"])
    if best_conc >= models["tox_equal"]["kappa"]:
        warnings.append("A concentration-only rule is as good as DRASTIC-Tox: the hydrogeological "
                        "part adds no detectable value on this dataset.")

    site_col = "site_name" if "site_name" in df.columns else ("site_key" if "site_key" in df.columns else None)
    table = pd.DataFrame({
        "site": df[site_col].values if site_col else np.arange(n),
        "actual": y, "DRASTIC": d.round(1),
        "Tox_score(equal w)": np.round(runs["tox_equal"][1], 1),
        "Tox_predicted": runs["tox_equal"][0],
        "HQ_max": np.round(hq, 2)})

    return {"n_total": n, "n_contaminated": int(y.sum()), "n_clean": int((y == 0).sum()),
            "n_locations": n_loc, "n_pos_locations": pos_loc, "n_neg_locations": neg_loc,
            "mining_type": mining_type, "scheme": "leave-one-location-out (nested)",
            "models": models, "leaky_row_out_tox_equal": naive, "profile_weights_model": extra,
            "site_table": table, "warnings": warnings}
