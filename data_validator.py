"""
Data Import Validator — DRASTIC-Tox v61 (v58.4 + dataset audit)
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
import re
import numpy as np
import pandas as pd
import drastic_core as dc


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

# Valid categorical values: single source of truth = drastic_core
VALID_AQUIFERS = set(dc.AQUIFER)
VALID_SOILS = set(dc.SOIL)
VALID_VADOSE = set(dc.VADOSE)
VALID_MINING_TYPES = {"traditional", "industrial", "mixed"}

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

    _extra_checks(df, mode, errors, warnings, info)
    return _finalize(errors, warnings, info, df, mode)


# ============================================================
# v61 - DATASET AUDIT (things that silently break validation)
# ============================================================
def _m(typ, sev, ar, en, **kw):
    d = {"type": typ, "severity": sev, "message_ar": ar, "message_en": en}
    d.update(kw)
    return d


def location_keys(df):
    """One id per physical location (Dry/Wet rows of the same place share it)."""
    if {"lat", "lon"} <= set(df.columns):
        return [f"{a:.2f},{b:.2f}" for a, b in zip(pd.to_numeric(df["lat"], errors="coerce"),
                                                   pd.to_numeric(df["lon"], errors="coerce"))]
    if "coords" in df.columns:
        out = []
        for c in df["coords"]:
            try:
                out.append(",".join(f"{float(x):.2f}" for x in c))
            except Exception:
                out.append(str(c))
        return out
    if "site_key" in df.columns:
        return [re.sub(r"_(Dry|Wet)$", "", str(k), flags=re.I) for k in df["site_key"]]
    return None


def audit_site_dataset(df, standard=None):
    standard = standard or dc.DEFAULT_STANDARD
    """Returns a list of findings (dicts with severity warning/info) for a mining site table."""
    f = []
    n = len(df)
    num = lambda c: pd.to_numeric(df[c], errors="coerce") if c in df.columns else None
    cn, hg = num("cn_water_mg_l"), num("hg_water_mg_l")
    y = num("actual_contaminated")

    if hg is not None and (hg > 0.1).any():
        f.append(_m("unit_check", "warning",
                    f"Hg > 0.1 mg/L في {int((hg > 0.1).sum())} صف: تحقق من الوحدة (µg/L مقابل mg/L).",
                    f"Hg > 0.1 mg/L in {int((hg > 0.1).sum())} rows: check units (ug/L vs mg/L)."))
    if cn is not None and (cn > 5).any():
        f.append(_m("unit_check", "warning", "CN > 5 mg/L: تحقق من الوحدة.", "CN > 5 mg/L: check units."))

    keys = location_keys(df)
    if keys is not None:
        n_loc = len(set(keys))
        if n_loc < n:
            f.append(_m("pseudo_replication", "warning",
                        f"{n} صفاً لكن {n_loc} موقعاً مستقلاً فقط (صفوف جاف/رطب لنفس المكان تشترك في الخصائص الهيدروجيولوجية). "
                        "استخدم التحقق leave-one-location-out، وعدّ n = عدد المواقع.",
                        f"{n} rows but only {n_loc} independent locations (Dry/Wet rows share hydrogeology). "
                        "Use leave-one-location-out and count n as locations.", n_locations=n_loc))

    if cn is not None and hg is not None and y is not None:
        L = dc.LIMITS_MG_L[standard]
        exceed = ((cn > L["cn"]) if L["cn"] else False) | (hg > L["hg"])
        names = df["site_name"] if "site_name" in df.columns else (df["site_key"] if "site_key" in df.columns else df.index.to_series())
        c1 = [str(names.iloc[i]) for i in range(n) if y.iloc[i] == 0 and bool(exceed.iloc[i])]
        c2 = [str(names.iloc[i]) for i in range(n) if y.iloc[i] == 1 and not bool(exceed.iloc[i])]
        if c1 or c2:
            f.append(_m("label_rule", "warning",
                        f"تصنيف 'ملوث/نظيف' لا يتبع معياراً موحّداً ({standard}): نظيف مع تجاوز ({len(c1)}) "
                        f"{', '.join(c1[:4])} | ملوث بلا تجاوز ({len(c2)}) {', '.join(c2[:4])}. وثّق قاعدة التصنيف.",
                        f"'contaminated/clean' label does not follow one rule ({standard}): clean but exceeding ({len(c1)}) "
                        f"{', '.join(c1[:4])} | contaminated without exceedance ({len(c2)}) {', '.join(c2[:4])}. Document the rule."))
        else:
            f.append(_m("label_rule", "info",
                        "التصنيف يطابق قاعدة تجاوز الحد بالكامل: النموذج قد يكون دائرياً (التركيز يحدد التسمية ويدخل في المؤشر).",
                        "Labels equal the exceedance rule exactly: the model may be circular (concentration defines the label and enters the index)."))

    if y is not None:
        npos, nneg = int((y == 1).sum()), int((y == 0).sum())
        if min(npos, nneg) < 10:
            f.append(_m("events_per_class", "warning",
                        f"الفئة الأقل فيها {min(npos, nneg)} صفاً فقط (يُنصح بـ 10 على الأقل لكل فئة).",
                        f"Minority class has only {min(npos, nneg)} rows (>= 10 per class recommended)."))
        if "state" in df.columns and npos > 0 and df.loc[y == 1, "state"].nunique() == 1:
            st = df.loc[y == 1, "state"].iloc[0]
            f.append(_m("confounding", "warning",
                        f"كل المواقع الملوثة في ولاية واحدة ({st}): الجغرافيا والتلوث متلازمان ولا يمكن فصل أثرهما.",
                        f"All contaminated sites are in one state ({st}): geography and contamination are confounded."))

    for col in ("cn_water_mg_l", "hg_water_mg_l"):
        v = num(col)
        if v is not None and n >= 6:
            vc = v.round(4).value_counts()
            share = vc.iloc[0] / n
            if share >= 0.4:
                f.append(_m("uniform_values", "info",
                            f"'{col}': القيمة {vc.index[0]} تتكرر في {int(vc.iloc[0])} من {n} صفاً ({share:.0%}). "
                            "تحقق أنها قياسات فعلية وليست حدّاً أدنى للكشف أو تقديراً.",
                            f"'{col}': value {vc.index[0]} repeats in {int(vc.iloc[0])} of {n} rows ({share:.0%}). "
                            "Check these are measurements, not detection limits or estimates."))
    if "source" in df.columns and df["source"].astype(str).str.contains("تقديرات|estimate", case=False, regex=True).any():
        f.append(_m("estimated_data", "warning",
                    "بعض المصادر مكتوبة 'تقديرات عامة': لا تُستخدم هذه الصفوف للمعايرة أو التحقق.",
                    "Some sources say 'general estimates': do not use these rows for calibration or validation."))
    if "is_gray_zone" in df.columns and df["is_gray_zone"].astype(bool).any():
        f.append(_m("synthetic", "error",
                    "الملف يحتوي مواقع اصطناعية (Gray Zone): للاختبار البرمجي فقط، ممنوعة في المعايرة والتحقق والنشر.",
                    "File contains synthetic (Gray Zone) sites: software testing only, never for calibration, validation or publication."))
    if "mining_type" in df.columns:
        bad = set(df["mining_type"].dropna().astype(str)) - VALID_MINING_TYPES
        if bad:
            f.append(_m("mining_type", "warning", f"mining_type غير معروف: {sorted(bad)}", f"Unknown mining_type: {sorted(bad)}"))
    return f


def audit_agri_dataset(df, tol=0.25):
    """EC vs sum of cations rule of thumb: sum(cations, meq/L) ~ 10 x EC (dS/m)."""
    f = []
    need = ["ec_ds_m", "na_meq_l", "ca_meq_l", "mg_meq_l"]
    if not all(c in df.columns for c in need):
        return f
    cat = df["na_meq_l"].astype(float) + df["ca_meq_l"].astype(float) + df["mg_meq_l"].astype(float)
    if "k_meq_l" in df.columns:
        cat = cat + df["k_meq_l"].astype(float)
    ratio = (10.0 * df["ec_ds_m"].astype(float)) / cat.replace(0, np.nan)
    bad = df.index[(ratio < 1 - tol) | (ratio > 1 + tol)]
    if len(bad):
        names = df["site_key"] if "site_key" in df.columns else df.index.to_series()
        f.append(_m("ec_balance", "warning",
                    f"{len(bad)} صف لا يتسق فيه EC مع مجموع الكاتيونات (قاعدة 10×EC ≈ Σ الكاتيونات ±{int(tol * 100)}%): "
                    f"{', '.join(str(names.loc[i]) for i in bad[:5])}. راجع القياسات أو الوحدات.",
                    f"{len(bad)} rows where EC is inconsistent with the cation sum (10 x EC ~ sum of cations +/-{int(tol * 100)}%): "
                    f"{', '.join(str(names.loc[i]) for i in bad[:5])}. Check measurements/units."))
    if "no3_mg_l" in df.columns and (df["no3_mg_l"].astype(float) > 500).any():
        f.append(_m("unit_check", "warning", "NO3 > 500 mg/L: تحقق من الوحدة (NO3 مقابل NO3-N).", "NO3 > 500 mg/L: check units (NO3 vs NO3-N)."))
    return f


def _extra_checks(df, mode, errors, warnings, info):
    if mode == "mining":
        if "conductivity" not in df.columns and "conductivity_m_d" in df.columns:
            info.append(_m("alias", "info", "استُخدم العمود conductivity_m_d بدل conductivity.", "Using conductivity_m_d instead of conductivity."))
        findings = audit_site_dataset(df)
    else:
        findings = audit_agri_dataset(df)
    for item in findings:
        {"error": errors, "warning": warnings}.get(item["severity"], info).append(item)
    if mode == "mining" and len(df) < 30:
        warnings.append(_m("pilot_size", "warning",
                           f"عدد الصفوف {len(df)} < 30: الدراسة استكشافية (pilot) ولا تصلح للتحقق الإحصائي.",
                           f"{len(df)} rows < 30: pilot study only, not suitable for statistical validation."))


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
