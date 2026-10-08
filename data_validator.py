"""
Data Import Validator — DRASTIC-Tox v58.4
Author: Shihab Alhadi + Sarah Akasha
University of Khartoum, Faculty of Engineering

Validates uploaded CSV/Excel files before processing:
    - Required columns presence
    - Data type correctness
    - Value ranges (physical bounds)
    - Missing values detection
    - Outlier detection (IQR method)
    - Consistency checks (duplicates, negative values)

Returns structured report with:
    - is_valid (bool)
    - errors (blocking issues)
    - warnings (non-blocking)
    - info (statistics)
    - score (0-100 data quality)
"""
import numpy as np
import pandas as pd


# ============================================================
# SCHEMA DEFINITIONS
# ============================================================

MINING_REQUIRED = [
    "depth_m", "recharge_mm", "slope_pct", "conductivity",
    "aquifer", "soil", "vadose"
]

MINING_OPTIONAL = [
    "cn_water_mg_l", "hg_water_mg_l", "actual_contaminated",
    "name", "name_ar", "state", "coords", "mining_type",
    "verified", "source", "season", "activity"
]

AGRI_REQUIRED = [
    "ec_ds_m", "na_meq_l", "ca_meq_l", "mg_meq_l"
]

AGRI_OPTIONAL = [
    "k_meq_l", "crop_type", "irrigation_method",
    "name", "name_ar", "state"
]

# Physical bounds: (min, max) — None = no bound
NUMERIC_BOUNDS = {
    "depth_m":               (0.1, 500.0),
    "recharge_mm":           (0.0, 2000.0),
    "slope_pct":             (0.0, 90.0),
    "conductivity":          (0.001, 1000.0),
    "cn_water_mg_l":         (0.0, 100.0),
    "hg_water_mg_l":         (0.0, 50.0),
    "ec_ds_m":               (0.0, 100.0),
    "na_meq_l":              (0.0, 500.0),
    "ca_meq_l":              (0.0, 500.0),
    "mg_meq_l":              (0.0, 500.0),
    "k_meq_l":               (0.0, 500.0),
    "actual_contaminated":   (0, 1),
}

# Valid categorical values (from app.py)
VALID_AQUIFERS = {
    "massive_shale", "metamorphic_igneous", "weathered_metamorphic_igneous",
    "thin_bedded_sequences", "massive_sandstone", "massive_limestone",
    "sand_and_gravel", "basalt", "karst_limestone"
}

VALID_SOILS = {
    "thin_or_absent", "gravel", "sand", "peat", "shrinking_aggregated_clay",
    "sandy_loam", "loam", "silty_loam", "clay_loam", "muck", "nonshrinking_clay"
}

VALID_VADOSE = {
    "confining_layer", "silt_clay", "shale", "metamorphic_igneous",
    "limestone", "sandstone", "sand_gravel_silt_clay", "sand_gravel",
    "basalt", "karst_limestone"
}

CATEGORICAL_SCHEMAS = {
    "aquifer": VALID_AQUIFERS,
    "soil":    VALID_SOILS,
    "vadose":  VALID_VADOSE,
}


# ============================================================
# MAIN VALIDATOR
# ============================================================

def validate_dataframe(df, mode="mining"):
    """
    Validate an uploaded DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Uploaded data
    mode : str
        'mining' or 'agricultural'

    Returns
    -------
    dict with keys:
        - is_valid (bool)
        - errors (list of dicts)
        - warnings (list of dicts)
        - info (list of dicts)
        - score (int 0-100)
        - summary (str)
    """
    if df is None or not hasattr(df, "empty"):
        return _empty_result("Invalid DataFrame object")

    if df.empty:
        return _empty_result("File is empty — no rows found")

    required = MINING_REQUIRED if mode == "mining" else AGRI_REQUIRED
    optional = MINING_OPTIONAL if mode == "mining" else AGRI_OPTIONAL

    errors = []
    warnings = []
    info = []

    # ==========================================================
    # 1. COLUMN PRESENCE
    # ==========================================================
    present_cols = set(df.columns)
    missing_required = [c for c in required if c not in present_cols]

    if missing_required:
        errors.append({
            "type": "missing_columns",
            "severity": "error",
            "message_ar": f"أعمدة مطلوبة مفقودة: {', '.join(missing_required)}",
            "message_en": f"Missing required columns: {', '.join(missing_required)}",
            "details": missing_required,
        })

    missing_optional = [c for c in optional if c not in present_cols]
    if missing_optional:
        info.append({
            "type": "missing_optional",
            "severity": "info",
            "message_ar": f"أعمدة اختيارية غير موجودة ({len(missing_optional)}): {', '.join(missing_optional[:5])}"
                          + (f" +{len(missing_optional)-5} أخرى" if len(missing_optional) > 5 else ""),
            "message_en": f"Optional columns absent ({len(missing_optional)}): {', '.join(missing_optional[:5])}"
                          + (f" +{len(missing_optional)-5} more" if len(missing_optional) > 5 else ""),
        })

    # Stop early if required columns missing
    if missing_required:
        return _finalize(errors, warnings, info, df, mode, early=True)

    # ==========================================================
    # 2. ROW COUNT
    # ==========================================================
    n_rows = len(df)
    if n_rows < 3:
        warnings.append({
            "type": "small_sample",
            "severity": "warning",
            "message_ar": f"حجم العينة صغير جداً ({n_rows} صفوف). النتائج قد لا تكون موثوقة.",
            "message_en": f"Very small sample ({n_rows} rows). Results may not be reliable.",
        })
    elif n_rows < 10:
        warnings.append({
            "type": "small_sample",
            "severity": "warning",
            "message_ar": f"حجم العينة صغير ({n_rows} صفوف). فسّر النتائج بحذر.",
            "message_en": f"Small sample ({n_rows} rows). Interpret with caution.",
        })
    else:
        info.append({
            "type": "row_count",
            "severity": "info",
            "message_ar": f"عدد المواقع: {n_rows}",
            "message_en": f"Number of sites: {n_rows}",
        })

    # ==========================================================
    # 3. NUMERIC VALIDATION
    # ==========================================================
    for col, (lo, hi) in NUMERIC_BOUNDS.items():
        if col not in df.columns:
            continue
        try:
            series = pd.to_numeric(df[col], errors="coerce")
        except Exception:
            continue

        # Check non-numeric values
        n_nonnumeric = series.isna().sum() - df[col].isna().sum()
        if n_nonnumeric > 0:
            errors.append({
                "type": "non_numeric",
                "severity": "error",
                "message_ar": f"العمود '{col}' يحتوي على {n_nonnumeric} قيمة غير رقمية",
                "message_en": f"Column '{col}' contains {n_nonnumeric} non-numeric values",
            })

        # Check missing
        n_missing = series.isna().sum()
        if n_missing > 0:
            pct = round(n_missing / n_rows * 100, 1)
            severity = "error" if pct > 30 else "warning"
            (errors if severity == "error" else warnings).append({
                "type": "missing_values",
                "severity": severity,
                "message_ar": f"'{col}': {n_missing} قيمة مفقودة ({pct}%)",
                "message_en": f"'{col}': {n_missing} missing values ({pct}%)",
            })

        # Check bounds
        valid_series = series.dropna()
        if len(valid_series) > 0:
            out_low = (valid_series < lo).sum()
            out_high = (valid_series > hi).sum()
            if out_low > 0 or out_high > 0:
                warnings.append({
                    "type": "out_of_bounds",
                    "severity": "warning",
                    "message_ar": f"'{col}': {out_low + out_high} قيمة خارج النطاق [{lo}, {hi}]",
                    "message_en": f"'{col}': {out_low + out_high} values outside [{lo}, {hi}]",
                })

            # IQR outliers (for informational purposes)
            if len(valid_series) >= 5:
                q1, q3 = valid_series.quantile([0.25, 0.75])
                iqr = q3 - q1
                if iqr > 0:
                    lo_iqr = q1 - 3 * iqr
                    hi_iqr = q3 + 3 * iqr
                    n_outliers = ((valid_series < lo_iqr) | (valid_series > hi_iqr)).sum()
                    if n_outliers > 0:
                        info.append({
                            "type": "iqr_outliers",
                            "severity": "info",
                            "message_ar": f"'{col}': {n_outliers} قيمة شاذة إحصائياً (IQR × 3)",
                            "message_en": f"'{col}': {n_outliers} statistical outliers (IQR × 3)",
                        })

    # ==========================================================
    # 4. CATEGORICAL VALIDATION
    # ==========================================================
    for col, valid_set in CATEGORICAL_SCHEMAS.items():
        if col not in df.columns:
            continue
        unique_vals = df[col].dropna().astype(str).str.strip().unique()
        invalid = [v for v in unique_vals if v not in valid_set]
        if invalid:
            warnings.append({
                "type": "invalid_category",
                "severity": "warning",
                "message_ar": f"'{col}': {len(invalid)} قيمة غير معروفة — {', '.join(invalid[:3])}"
                              + (f" +{len(invalid)-3}" if len(invalid) > 3 else ""),
                "message_en": f"'{col}': {len(invalid)} unknown values — {', '.join(invalid[:3])}"
                              + (f" +{len(invalid)-3}" if len(invalid) > 3 else ""),
                "details": invalid,
            })

    # ==========================================================
    # 5. CONSISTENCY CHECKS
    # ==========================================================
    # Duplicate rows
    n_dups = df.duplicated().sum()
    if n_dups > 0:
        warnings.append({
            "type": "duplicates",
            "severity": "warning",
            "message_ar": f"{n_dups} صف مكرر",
            "message_en": f"{n_dups} duplicate rows",
        })

    # Negative values in columns that shouldn't be negative
    non_negative_cols = ["depth_m", "recharge_mm", "slope_pct", "conductivity",
                          "cn_water_mg_l", "hg_water_mg_l"]
    for col in non_negative_cols:
        if col not in df.columns:
            continue
        try:
            series = pd.to_numeric(df[col], errors="coerce")
            neg = (series < 0).sum()
            if neg > 0:
                errors.append({
                    "type": "negative_values",
                    "severity": "error",
                    "message_ar": f"'{col}': {neg} قيمة سالبة (غير مسموح)",
                    "message_en": f"'{col}': {neg} negative values (not allowed)",
                })
        except Exception:
            pass

    # Toxicity consistency (mining only)
    if mode == "mining" and "actual_contaminated" in df.columns:
        try:
            actual = pd.to_numeric(df["actual_contaminated"], errors="coerce")
            non_binary = ~actual.isin([0, 1, 0.0, 1.0])
            non_binary = non_binary & actual.notna()
            if non_binary.sum() > 0:
                warnings.append({
                    "type": "non_binary_target",
                    "severity": "warning",
                    "message_ar": f"'actual_contaminated': {non_binary.sum()} قيمة ليست 0 أو 1",
                    "message_en": f"'actual_contaminated': {non_binary.sum()} values not 0 or 1",
                })

            # Class balance
            valid_actual = actual.dropna()
            if len(valid_actual) > 0:
                n_cont = int((valid_actual == 1).sum())
                n_clean = int((valid_actual == 0).sum())
                if n_cont == 0:
                    warnings.append({
                        "type": "no_positive_class",
                        "severity": "warning",
                        "message_ar": "لا توجد مواقع ملوثة — لا يمكن حساب Kappa أو ROC",
                        "message_en": "No contaminated sites — cannot compute Kappa or ROC",
                    })
                elif n_clean == 0:
                    warnings.append({
                        "type": "no_negative_class",
                        "severity": "warning",
                        "message_ar": "لا توجد مواقع نظيفة — لا يمكن حساب Kappa أو ROC",
                        "message_en": "No clean sites — cannot compute Kappa or ROC",
                    })
                else:
                    ratio = n_cont / (n_cont + n_clean)
                    if ratio < 0.2 or ratio > 0.8:
                        warnings.append({
                            "type": "imbalanced_classes",
                            "severity": "warning",
                            "message_ar": f"عدم توازن الفئات: {n_cont} ملوث / {n_clean} نظيف",
                            "message_en": f"Imbalanced classes: {n_cont} contaminated / {n_clean} clean",
                        })
                    else:
                        info.append({
                            "type": "class_balance",
                            "severity": "info",
                            "message_ar": f"توزيع متوازن: {n_cont} ملوث / {n_clean} نظيف",
                            "message_en": f"Balanced distribution: {n_cont} contaminated / {n_clean} clean",
                        })
        except Exception:
            pass

    return _finalize(errors, warnings, info, df, mode)


# ============================================================
# HELPERS
# ============================================================

def _finalize(errors, warnings, info, df, mode, early=False):
    """Compute final score and summary."""
    if early:
        score = 0
    else:
        score = 100
        score -= len(errors) * 20
        score -= len(warnings) * 5
        score = max(0, min(100, score))

    is_valid = len(errors) == 0

    summary = _build_summary(is_valid, score, errors, warnings, info, len(df), mode)

    return {
        "is_valid": is_valid,
        "score": score,
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "n_rows": len(df),
        "n_cols": len(df.columns) if hasattr(df, "columns") else 0,
        "mode": mode,
        "summary": summary,
    }


def _empty_result(msg):
    return {
        "is_valid": False,
        "score": 0,
        "errors": [{"type": "empty", "severity": "error",
                    "message_ar": msg, "message_en": msg}],
        "warnings": [],
        "info": [],
        "n_rows": 0,
        "n_cols": 0,
        "mode": "unknown",
        "summary": msg,
    }


def _build_summary(is_valid, score, errors, warnings, info, n_rows, mode):
    """Build a readable text summary."""
    if is_valid:
        grade = "ممتاز" if score >= 90 else "جيد جداً" if score >= 75 else "جيد" if score >= 60 else "مقبول"
        status_ar = f"✅ البيانات صالحة — الجودة: {grade} ({score}/100)"
    else:
        status_ar = f"❌ البيانات غير صالحة — {len(errors)} خطأ حرج"

    lines = [
        status_ar,
        f"عدد الصفوف: {n_rows} | الوضع: {mode}",
        f"الأخطاء: {len(errors)} | التحذيرات: {len(warnings)} | ملاحظات: {len(info)}",
    ]
    return "\n".join(lines)


def get_quality_color(score):
    """Return a hex color for the score."""
    if score >= 90: return "#2e7d32"   # green
    if score >= 75: return "#66bb6a"   # light green
    if score >= 60: return "#fbc02d"   # yellow
    if score >= 40: return "#f57c00"   # orange
    return "#d32f2f"                    # red


def get_quality_label_ar(score):
    """Return Arabic quality label."""
    if score >= 90: return "ممتاز"
    if score >= 75: return "جيد جداً"
    if score >= 60: return "جيد"
    if score >= 40: return "مقبول"
    return "ضعيف"
