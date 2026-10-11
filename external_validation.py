"""
External Validation Module — DRASTIC-Tox v61
Author: Shihab Alhadi + Sarah Akasha
University of Khartoum, Faculty of Engineering

Provides:
    - external_validation_analysis(): train/test split + K-Fold CV
    - baseline_ml_models(): LogReg + Random Forest baselines
    - enhanced_metrics(): PR-AUC + Brier score

v61 Changes:
  * threshold_dt default fixed: 106.5 → 144.4 (aligns with weight_manager v61)
  * Normalisation divisors corrected:
      DRASTIC      max = 226  (was 230)
      DRASTIC-Tox  max = 276  (was 280; = 226 + max_toxicity_bonus)
  * Docstring clarifies that Brier/PR-AUC use min-max normalisation
    because DRASTIC is NOT a probability.
"""
import numpy as np
import pandas as pd

# ============================================================
# Canonical ranges (v61: aligned with drastic_core.py)
# ============================================================
DRASTIC_MIN    = 23.0    # index_range(W_STD)[0]
DRASTIC_MAX    = 226.0   # index_range(W_STD)[1]
DTOX_MIN       = 23.0
DTOX_MAX       = 276.0   # 226 + MAX_TOXICITY_BONUS (50)
DEFAULT_THRESH_DT = 144.4


def _norm_drastic(x):
    """Map DRASTIC [23, 226] -> [0, 1]."""
    return (np.asarray(x, dtype=float) - DRASTIC_MIN) / (DRASTIC_MAX - DRASTIC_MIN)

def _norm_dtox(x):
    """Map DRASTIC-Tox [23, 276] -> [0, 1]."""
    return (np.asarray(x, dtype=float) - DTOX_MIN) / (DTOX_MAX - DTOX_MIN)


def external_validation_analysis(
    df,
    mining_type="traditional",
    threshold_d=100,
    threshold_dt=DEFAULT_THRESH_DT,       # ← v61: was 106.5
    test_size=0.30,
    n_folds=5,
    random_state=42,
    calc_index_fn=None,
    calc_drastic_t_fn=None,
    get_d_rating_fn=None,
    get_r_rating_fn=None,
    get_a_rating_fn=None,
    get_s_rating_fn=None,
    get_t_rating_fn=None,
    get_i_rating_fn=None,
    get_c_rating_fn=None,
    calibrated_weights=None,
    sklearn_ok=True,
):
    """
    External Validation via train/test split + Stratified K-Fold CV.

    Notes
    -----
    - With n ~ 11 the test set is 3-4 sites: treat as demonstration only.
    - PR-AUC / Brier use min-max normalisation because DRASTIC is not a
      probability. Numbers are indicative, not calibrated probabilities.
    """
    if not sklearn_ok:
        return {"error": "scikit-learn required"}

    try:
        from sklearn.model_selection import (train_test_split, StratifiedKFold)
        from sklearn.linear_model import LogisticRegression
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import (cohen_kappa_score, roc_auc_score,
                                     average_precision_score, brier_score_loss)
    except ImportError as e:
        return {"error": f"Missing sklearn module: {e}"}

    required_fns = [calc_index_fn, calc_drastic_t_fn, get_d_rating_fn,
                    get_r_rating_fn, get_a_rating_fn, get_s_rating_fn,
                    get_t_rating_fn, get_i_rating_fn, get_c_rating_fn]
    if any(f is None for f in required_fns):
        return {"error": "All rating/index functions must be provided"}

    # ---------------- Prepare arrays ----------------
    drastic_arr, dtox_arr, actual_arr = [], [], []

    for _, row in df.iterrows():
        try:
            ix = calc_index_fn(
                get_d_rating_fn(float(row["depth_m"])),
                get_r_rating_fn(float(row["recharge_mm"])),
                get_a_rating_fn(str(row["aquifer"])),
                get_s_rating_fn(str(row["soil"])),
                get_t_rating_fn(float(row["slope_pct"])),
                get_i_rating_fn(str(row["vadose"])),
                get_c_rating_fn(float(row.get("conductivity_m_d")
                                       or row.get("conductivity"))),
            )
            cn = float(row.get("cn_water_mg_l", 0.0))
            hg = float(row.get("hg_water_mg_l", 0.0))

            if calibrated_weights and calibrated_weights.get("mining_type") == mining_type:
                dtox = calc_drastic_t_fn(
                    ix, cn, hg, mining_type=mining_type,
                    alpha_override=calibrated_weights["alpha"],
                    beta_override=calibrated_weights["beta"],
                    SF_override=calibrated_weights["SF"],
                )["drastic_t"]
            else:
                dtox = calc_drastic_t_fn(ix, cn, hg, mining_type=mining_type)["drastic_t"]

            drastic_arr.append(ix)
            dtox_arr.append(dtox)
            actual_arr.append(int(row["actual_contaminated"]))
        except Exception:
            continue

    X_d  = np.array(drastic_arr).reshape(-1, 1)
    X_dt = np.array(dtox_arr).reshape(-1, 1)
    y = np.array(actual_arr)
    n = len(y)

    if n < 8:
        return {"error": f"Need at least 8 sites, got {n}"}
    if len(np.unique(y)) < 2:
        return {"error": "Need both classes (contaminated & clean)"}

    results = {
        "n_total": n,
        "n_contaminated": int(y.sum()),
        "n_clean": int((y == 0).sum()),
        "mining_type": mining_type,
        "threshold_d": threshold_d,
        "threshold_dt": threshold_dt,
        "scoring_version": "v61",
        "drastic_range": [DRASTIC_MIN, DRASTIC_MAX],
        "dtox_range": [DTOX_MIN, DTOX_MAX],
    }

    # =========================================================
    # 1. TRAIN / TEST SPLIT (stratified)
    # =========================================================
    try:
        idx_train, idx_test = train_test_split(
            np.arange(n), test_size=test_size,
            random_state=random_state, stratify=y,
        )
        results["test_size_pct"] = int(test_size * 100)
        results["n_train"] = len(idx_train)
        results["n_test"]  = len(idx_test)

        y_test = y[idx_test]
        y_pred_d  = (X_d[idx_test, 0]  >= threshold_d).astype(int)
        y_pred_dt = (X_dt[idx_test, 0] >= threshold_dt).astype(int)

        results["test_kappa_drastic"] = round(
            float(cohen_kappa_score(y_test, y_pred_d)), 3
        ) if len(np.unique(y_test)) > 1 else 0.0

        results["test_kappa_drastic_tox"] = round(
            float(cohen_kappa_score(y_test, y_pred_dt)), 3
        ) if len(np.unique(y_test)) > 1 else 0.0

        try:
            results["test_auc_drastic"] = round(
                float(roc_auc_score(y_test, X_d[idx_test, 0])), 3
            )
            results["test_auc_drastic_tox"] = round(
                float(roc_auc_score(y_test, X_dt[idx_test, 0])), 3
            )
        except Exception:
            results["test_auc_drastic"] = None
            results["test_auc_drastic_tox"] = None

        results["train_indices"] = idx_train.tolist()
        results["test_indices"]  = idx_test.tolist()
    except Exception as e:
        results["split_error"] = str(e)

    # =========================================================
    # 2. STRATIFIED K-FOLD CROSS-VALIDATION
    # =========================================================
    try:
        skf = StratifiedKFold(
            n_splits=min(n_folds, n),
            shuffle=True,
            random_state=random_state,
        )
        fold_kappas_d, fold_kappas_dt = [], []
        fold_aucs_d,   fold_aucs_dt   = [], []

        for _, test_idx in skf.split(X_d, y):
            yt = y[test_idx]
            if len(np.unique(yt)) < 2:
                continue
            yp_d  = (X_d[test_idx, 0]  >= threshold_d).astype(int)
            yp_dt = (X_dt[test_idx, 0] >= threshold_dt).astype(int)
            try:
                fold_kappas_d.append(cohen_kappa_score(yt, yp_d))
                fold_kappas_dt.append(cohen_kappa_score(yt, yp_dt))
                fold_aucs_d.append(roc_auc_score(yt, X_d[test_idx, 0]))
                fold_aucs_dt.append(roc_auc_score(yt, X_dt[test_idx, 0]))
            except Exception:
                continue

        results["cv_n_folds"] = len(fold_kappas_d)
        if fold_kappas_d:
            results["cv_kappa_drastic_mean"]      = round(float(np.mean(fold_kappas_d)), 3)
            results["cv_kappa_drastic_std"]       = round(float(np.std(fold_kappas_d)), 3)
            results["cv_kappa_drastic_tox_mean"]  = round(float(np.mean(fold_kappas_dt)), 3)
            results["cv_kappa_drastic_tox_std"]   = round(float(np.std(fold_kappas_dt)), 3)
            results["cv_auc_drastic_mean"]        = round(float(np.mean(fold_aucs_d)), 3)
            results["cv_auc_drastic_tox_mean"]    = round(float(np.mean(fold_aucs_dt)), 3)
            results["fold_kappas_drastic"]        = [round(float(k), 3) for k in fold_kappas_d]
            results["fold_kappas_drastic_tox"]    = [round(float(k), 3) for k in fold_kappas_dt]
    except Exception as e:
        results["cv_error"] = str(e)

    # =========================================================
    # 3. BASELINE ML MODELS
    # =========================================================
    try:
        X_features = np.column_stack([X_dt.flatten()])
        idx_train, idx_test = train_test_split(
            np.arange(n), test_size=test_size,
            random_state=random_state, stratify=y,
        )

        lr = LogisticRegression(random_state=random_state, max_iter=1000)
        lr.fit(X_features[idx_train], y[idx_train])
        y_pred_lr = lr.predict(X_features[idx_test])
        y_prob_lr = lr.predict_proba(X_features[idx_test])[:, 1]

        results["baseline_logreg_kappa"] = round(
            float(cohen_kappa_score(y[idx_test], y_pred_lr)), 3
        )
        results["baseline_logreg_auc"] = round(
            float(roc_auc_score(y[idx_test], y_prob_lr)), 3
        )

        rf = RandomForestClassifier(
            n_estimators=100, random_state=random_state,
            max_depth=3, min_samples_leaf=2,
        )
        rf.fit(X_features[idx_train], y[idx_train])
        y_pred_rf = rf.predict(X_features[idx_test])
        y_prob_rf = rf.predict_proba(X_features[idx_test])[:, 1]

        results["baseline_rf_kappa"] = round(
            float(cohen_kappa_score(y[idx_test], y_pred_rf)), 3
        )
        results["baseline_rf_auc"] = round(
            float(roc_auc_score(y[idx_test], y_prob_rf)), 3
        )
    except Exception as e:
        results["baseline_error"] = str(e)

    # =========================================================
    # 4. ENHANCED METRICS  (v61: correct normalisation)
    # =========================================================
    try:
        idx_train, idx_test = train_test_split(
            np.arange(n), test_size=test_size,
            random_state=random_state, stratify=y,
        )
        y_test = y[idx_test]

        # min-max normalisation to [0, 1]  (DRASTIC is NOT a probability)
        score_d_norm  = _norm_drastic(X_d[idx_test, 0])
        score_dt_norm = _norm_dtox(X_dt[idx_test, 0])

        results["pr_auc_drastic"] = round(
            float(average_precision_score(y_test, score_d_norm)), 3
        )
        results["pr_auc_drastic_tox"] = round(
            float(average_precision_score(y_test, score_dt_norm)), 3
        )
        results["brier_drastic"] = round(
            float(brier_score_loss(y_test, score_d_norm)), 3
        )
        results["brier_drastic_tox"] = round(
            float(brier_score_loss(y_test, score_dt_norm)), 3
        )
        results["normalisation_note"] = (
            "Brier/PR-AUC use min-max normalisation: "
            f"DRASTIC [{DRASTIC_MIN:.0f}, {DRASTIC_MAX:.0f}], "
            f"DRASTIC-Tox [{DTOX_MIN:.0f}, {DTOX_MAX:.0f}]. "
            "These are indicative, not calibrated probabilities."
        )
    except Exception as e:
        results["enhanced_metrics_error"] = str(e)

    return results 
