"""
وحدات متقدمة - نظام التعدين السوداني v60.0
=====================================
يحتوي على:
1. Validation Metrics (Confusion Matrix, Kappa, MCC)
2. DRASTIC-P (Cyanide + Mercury)
3. Dynamic Assessment
4. Transport Modeling
5. Independent Validation (70/30 Split)
6. Satellite Data (ERA5)
7. Agricultural Module

الإصلاحات في v60.0:
- إضافة max_cap مرن للوحدات (230 أو 300)
- تحسين التوثيق
- إصلاح اختيار نوع الاستخدام (drinking/irrigation/industrial)
- إضافة validation للإحداثيات في satellite data
- تحسين الأخطاء
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from itertools import product


# ============================================================
# ============ 1. Validation Metrics ============
# ============================================================
def calculate_confusion_matrix(predicted, actual, threshold=140):
    """
    حساب مصفوفة الالتباس والمقاييس الإحصائية

    Parameters
    ----------
    predicted : array-like — القيم المتوقعة
    actual : array-like — القيم الفعلية (0 أو 1)
    threshold : float — العتبة للتصنيف

    Returns
    -------
    dict — المقاييس الإحصائية
    """
    predicted = np.array(predicted)
    actual = np.array(actual)
    pred_class = (predicted >= threshold).astype(int)

    tp = int(np.sum((pred_class == 1) & (actual == 1)))
    tn = int(np.sum((pred_class == 0) & (actual == 0)))
    fp = int(np.sum((pred_class == 1) & (actual == 0)))
    fn = int(np.sum((pred_class == 0) & (actual == 1)))
    total = tp + tn + fp + fn

    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0
    npv = tn / (tn + fn) if (tn + fn) > 0 else 0
    po = accuracy
    pe = ((tp + fp) * (tp + fn) + (tn + fn) * (tn + fp)) / (total ** 2) if total > 0 else 0
    kappa = ((po - pe) / (1 - pe)) if (1 - pe) > 0 else 0
    mcc_num = (tp * tn) - (fp * fn)
    mcc_den = np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = mcc_num / mcc_den if mcc_den > 0 else 0
    tpr = recall
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
    youden = tpr - fpr
    balanced_acc = (recall + specificity) / 2

    return {
        "confusion_matrix": {"TP": tp, "TN": tn, "FP": fp, "FN": fn, "Total": total},
        "accuracy": round(accuracy * 100, 2),
        "precision": round(precision * 100, 2),
        "recall": round(recall * 100, 2),
        "specificity": round(specificity * 100, 2),
        "f1_score": round(f1 * 100, 2),
        "npv": round(npv * 100, 2),
        "balanced_accuracy": round(balanced_acc * 100, 2),
        "kappa": round(kappa, 4),
        "mcc": round(mcc, 4),
        "youden_j": round(youden, 4),
        "threshold": threshold}


def analyze_validation_by_level(predicted, actual):
    """تحليل الدقة حسب المستوى"""
    predicted = np.array(predicted)
    actual = np.array(actual)
    levels = []
    for idx in predicted:
        if idx < 100: levels.append("منخفض")
        elif idx < 140: levels.append("متوسط")
        elif idx < 180: levels.append("مرتفع")
        else: levels.append("مرتفع جدا")
    df = pd.DataFrame({"predicted_index": predicted, "actual": actual, "level": levels})
    results = []
    for level in ["منخفض", "متوسط", "مرتفع", "مرتفع جدا"]:
        sub = df[df["level"] == level]
        if len(sub) > 0:
            if level in ["مرتفع", "مرتفع جدا"]:
                correct = (sub["actual"] == 1).sum()
            elif level == "منخفض":
                correct = (sub["actual"] == 0).sum()
            else:
                correct = 0
            results.append({"المستوى": level, "العدد": len(sub),
                "التصنيفات الصحيحة": int(correct),
                "نسبة الدقة": round(correct / len(sub) * 100, 1)})
    return pd.DataFrame(results)


def generate_validation_report(metrics):
    """تقرير التحقق الكامل"""
    L = ["=" * 60, "تقرير التحقق الإحصائي", "=" * 60, ""]
    cm = metrics["confusion_matrix"]
    L.append(f"TP: {cm['TP']} | TN: {cm['TN']} | FP: {cm['FP']} | FN: {cm['FN']}")
    L.append("")
    L.append(f"Accuracy:    {metrics['accuracy']} %")
    L.append(f"Precision:   {metrics['precision']} %")
    L.append(f"Recall:      {metrics['recall']} %")
    L.append(f"Specificity: {metrics['specificity']} %")
    L.append(f"F1:          {metrics['f1_score']} %")
    L.append(f"Kappa:       {metrics['kappa']}")
    L.append(f"MCC:         {metrics['mcc']}")
    L.append(f"Balanced Accuracy: {metrics['balanced_accuracy']} %")
    L.append("")
    L.append("تفسير Kappa (Landis & Koch):")
    k = metrics["kappa"]
    if k >= 0.8: interp = "توافق ممتاز"
    elif k >= 0.6: interp = "توافق جيد"
    elif k >= 0.4: interp = "توافق متوسط"
    else: interp = "توافق ضعيف"
    L.append(f"  {interp}")
    return "\n".join(L)


# ============================================================
# ============ 2. DRASTIC-P ============
# ============================================================
def calculate_cyanide_risk_index(cn_w, cn_s, dist, seepage):
    """
    CRI - مؤشر السيانيد

    يحسب خطر السيانيد من:
    - تركيز السيانيد في الماء (cn_w)
    - تركيز السيانيد في التربة (cn_s)
    - المسافة من المصدر
    - معامل التسرب
    """
    CN_W, CN_S = 0.05, 10.0  # WHO water limit, soil screening value
    w_r = cn_w / CN_W
    s_r = cn_s / CN_S
    d_f = max(0.1, min(1.0, 100.0 / max(1, dist)))
    s_f = max(0.1, min(1.0, seepage))
    cri = (w_r * 0.5 + s_r * 0.3) * d_f * s_f
    if cri <= 0.5: level, color = "منخفض", "green"
    elif cri <= 2.0: level, color = "متوسط", "yellow"
    elif cri <= 5.0: level, color = "مرتفع", "orange"
    else: level, color = "مرتفع جدا", "red"
    return {"cri": round(cri, 3), "water_ratio": round(w_r, 2),
            "soil_ratio": round(s_r, 2), "level": level, "color": color}


def calculate_mercury_risk_index(hg_w, hg_s, bio, use="drinking"):
    """
    MRI - مؤشر الزئبق

    use : drinking / irrigation / industrial
    """
    limits = {"drinking": {"water": 0.0007, "soil": 1.0},
              "irrigation": {"water": 0.0007, "soil": 1.0},
              "industrial": {"water": 0.005, "soil": 5.0}}  # ✅ تم التصحيح من 0.05 → 0.005
    lim = limits.get(use, limits["drinking"])
    w_r = hg_w / lim["water"]
    s_r = hg_s / lim["soil"]
    mri = (w_r * 0.6 + s_r * 0.4) * bio
    if mri <= 0.5: level, color = "منخفض", "green"
    elif mri <= 2.0: level, color = "متوسط", "yellow"
    elif mri <= 5.0: level, color = "مرتفع", "orange"
    else: level, color = "مرتفع جدا", "red"
    return {"mri": round(mri, 3), "water_ratio": round(w_r, 2),
            "soil_ratio": round(s_r, 2), "level": level, "color": color}


def calculate_modified_drastic(base, cri=0, mri=0, amd=0,
                                alpha=0.50, beta=0.50, gamma=0.10,
                                max_cap=230):
    """
    DRASTIC-P = DRASTIC × (1 + α×CRI + β×MRI + γ×AMD)

    Parameters
    ----------
    max_cap : float — الحد الأقصى (230 للـ DRASTIC الكلاسيكي، 300 للـ DRASTIC-Tox)
    """
    modifier = 1.0 + (alpha * cri) + (beta * mri) + (gamma * amd)
    modified = min(max_cap, base * modifier)
    inc = ((modified - base) / base * 100) if base > 0 else 0
    if modified >= 180: level, color = "مرتفع جدا", "red"
    elif modified >= 140: level, color = "مرتفع", "orange"
    elif modified >= 100: level, color = "متوسط", "yellow"
    else: level, color = "منخفض", "green"
    return {"base_drastic": base, "modified_drastic": round(modified, 1),
            "modifier_factor": round(modifier, 3),
            "increase_pct": round(inc, 1), "cri": cri, "mri": mri,
            "amd_risk": amd, "level": level, "color": color,
            "alpha": alpha, "beta": beta, "max_cap": max_cap}


# ============================================================
# ============ 3. Dynamic Assessment ============
# ============================================================
def project_drastic_change(base, years=10, mining=0.05, climate=-0.02, pop=0.03):
    """توقع تغير DRASTIC مع الزمن"""
    proj = []
    for year in range(years + 1):
        if year == 0:
            proj.append({"السنة": 0, "المؤشر": round(base, 1), "الزيادة_المئوية": 0})
            continue
        mf = 1 + (mining * year)
        cf = 1 + (climate * year)
        pf = 1 + (pop * year * 0.5)
        ni = min(230, base * mf * cf * pf)
        inc = ((ni - base) / base * 100) if base > 0 else 0
        proj.append({"السنة": year, "المؤشر": round(ni, 1),
                      "الزيادة_المئوية": round(inc, 1)})
    return {"base_index": base, "years": years, "projections": proj,
            "final_index": proj[-1]["المؤشر"]}


def estimate_mitigation_impact(base, years=10, mit_year=3):
    """تقدير تأثير الحلول"""
    rows = []
    for year in range(years + 1):
        mf = 1 + (0.05 * year)
        cf = 1 + (-0.02 * year)
        no_mit = min(230, base * mf * cf)
        if year >= mit_year:
            eff = max(0.3, 1 - 0.15 * min(year - mit_year + 1, 5))
        else:
            eff = 1.0
        with_mit = min(230, base * mf * cf * eff)
        diff = no_mit - with_mit
        rows.append({"السنة": year, "بدون تخفيف": round(no_mit, 1),
            "مع تخفيف": round(with_mit, 1), "الفرق": round(diff, 1),
            "التخفيض %": round(diff / no_mit * 100, 1) if no_mit > 0 else 0})
    return pd.DataFrame(rows)


def calculate_dynamic_risk(base, years, mining, climate, pop, cri0=0, mri0=0):
    """التقييم الديناميكي الشامل"""
    dp = project_drastic_change(base, years, mining, climate, pop)
    combined = []
    for proj in dp["projections"]:
        year = proj["السنة"]
        cri = cri0 * (1 + mining * year * 2)
        mri = mri0 * (1 + mining * year * 1.5)
        mod = calculate_modified_drastic(proj["المؤشر"], cri, mri,
                                          min(1.0, 0.1 * year))
        combined.append({"السنة": year, "DRASTIC": proj["المؤشر"],
            "CRI": round(cri, 2), "MRI": round(mri, 2),
            "DRASTIC-Modified": mod["modified_drastic"],
            "المستوى": mod["level"], "اللون": mod["color"]})
    return {"drastic_projection": dp, "combined": pd.DataFrame(combined),
            "final_modified": combined[-1]["DRASTIC-Modified"],
            "final_level": combined[-1]["المستوى"]}


# ============================================================
# ============ 4. Transport Modeling ============
# ============================================================
def model_contaminant_transport(initial_conc, k_value, porosity, gradient,
                                  distance, source_duration_years,
                                  decay_coefficient=0.001):
    """نمذجة انتقال الملوثات المبسطة"""
    if porosity <= 0 or porosity >= 1:
        raise ValueError("Porosity must be between 0 and 1")
    if k_value <= 0:
        raise ValueError("K must be > 0")

    v = (k_value * gradient) / porosity
    if v <= 0:
        return {"error": "Velocity must be > 0"}

    try:
        from scipy.special import erfc
        has_scipy = True
    except ImportError:
        has_scipy = False

    results = []
    for year in range(1, source_duration_years + 1):
        time_days = year * 365.25
        dispersivity = 10.0
        D = v * dispersivity
        if D <= 0:
            D = 0.001
        distance_traveled = v * time_days

        if has_scipy and distance > 0:
            arg = distance / (2 * np.sqrt(D * time_days))
            factor = float(erfc(arg))
        else:
            if distance > 0:
                factor = max(0.0, 1.0 - distance / max(distance_traveled, 1))
            else:
                factor = 1.0

        decay = np.exp(-decay_coefficient * time_days / 365.25)
        conc = initial_conc * factor * decay
        results.append({
            "السنة": year,
            "التركيز (mg/L)": round(conc, 6),
            "المسافة المقطوعة (m)": round(distance_traveled, 1),
            "النسبة من الحد": round(conc / initial_conc * 100, 2) if initial_conc > 0 else 0
        })
    return {
        "velocity_m_day": round(v, 6),
        "velocity_m_year": round(v * 365.25, 3),
        "results": pd.DataFrame(results)
    }


def calculate_travel_time_to_well(depth, porosity, k_value, gradient,
                                    well_distance):
    """حساب زمن وصول الملوث إلى البئر"""
    v = (k_value * gradient) / porosity
    if v <= 0:
        return None
    days = well_distance / v
    years = days / 365.25
    return {
        "velocity_m_day": round(v, 6),
        "travel_days": round(days, 1),
        "travel_years": round(years, 2)
    }


# ============================================================
# ============ 5. Independent Validation ============
# ============================================================
def independent_validation(df, drastic_col, actual_col,
                            alpha_range=(0.2, 1.0, 0.1),
                            beta_range=(0.2, 1.0, 0.1),
                            test_size=0.3, random_state=42):
    """التحقق المستقل (70/30 Split) + تحسين α و β"""
    np.random.seed(random_state)
    n = len(df)
    if n < 5:
        return {"error": "Need at least 5 samples for validation"}

    indices = np.random.permutation(n)
    test_n = max(1, int(n * test_size))
    test_idx = indices[:test_n]
    train_idx = indices[test_n:]

    df_train = df.iloc[train_idx].copy()
    df_test = df.iloc[test_idx].copy()

    best_kappa = -1
    best_alpha = 0.5
    best_beta = 0.5

    alphas = np.arange(alpha_range[0], alpha_range[1] + alpha_range[2], alpha_range[2])
    betas = np.arange(beta_range[0], beta_range[1] + beta_range[2], beta_range[2])

    for alpha, beta in product(alphas, betas):
        preds = []
        for _, row in df_train.iterrows():
            base = float(row[drastic_col])
            cn = float(row.get("cn_water_mg_l", 0.0))
            hg = float(row.get("hg_water_mg_l", 0.0))
            cri = (cn / 0.05) * 0.5
            mri = (hg / 0.0007) * 0.6
            modifier = 1.0 + (alpha * cri) + (beta * mri)
            preds.append(min(230, base * modifier))

        actuals = df_train[actual_col].values
        metrics = calculate_confusion_matrix(preds, actuals, threshold=140)
        if metrics["kappa"] > best_kappa:
            best_kappa = metrics["kappa"]
            best_alpha = alpha
            best_beta = beta

    test_preds = []
    for _, row in df_test.iterrows():
        base = float(row[drastic_col])
        cn = float(row.get("cn_water_mg_l", 0.0))
        hg = float(row.get("hg_water_mg_l", 0.0))
        cri = (cn / 0.05) * 0.5
        mri = (hg / 0.0007) * 0.6
        modifier = 1.0 + (best_alpha * cri) + (best_beta * mri)
        test_preds.append(min(230, base * modifier))

    test_actuals = df_test[actual_col].values
    test_metrics = calculate_confusion_matrix(test_preds, test_actuals, threshold=140)

    return {
        "best_alpha": round(best_alpha, 2),
        "best_beta": round(best_beta, 2),
        "train_kappa": round(best_kappa, 4),
        "test_kappa": test_metrics["kappa"],
        "test_accuracy": test_metrics["accuracy"],
        "test_recall": test_metrics["recall"],
        "test_metrics": test_metrics,
        "n_train": len(df_train),
        "n_test": len(df_test),
        "alpha_range": (alpha_range[0], alpha_range[1]),
        "beta_range": (beta_range[0], beta_range[1])
    }


def generate_independent_validation_report(result):
    """تقرير التحقق المستقل"""
    L = ["=" * 60, "تقرير التحقق المستقل", "=" * 60, ""]
    L.append(f"عدد مواقع التدريب: {result['n_train']}")
    L.append(f"عدد مواقع الاختبار: {result['n_test']}")
    L.append("")
    L.append(f"أفضل α: {result['best_alpha']}")
    L.append(f"أفضل β: {result['best_beta']}")
    L.append("")
    L.append(f"Kappa (تدريب): {result['train_kappa']}")
    L.append(f"Kappa (اختبار): {result['test_kappa']}")
    L.append(f"Accuracy (اختبار): {result['test_accuracy']} %")
    L.append(f"Recall (اختبار): {result['test_recall']} %")
    L.append("")
    k_test = result['test_kappa']
    if k_test >= 0.8: interp = "✅ ممتاز - النموذج قابل للتعميم"
    elif k_test >= 0.6: interp = "✅ جيد - النموذج قابل للاعتماد"
    elif k_test >= 0.4: interp = "⚠️ متوسط - يحتاج تحسين"
    else: interp = "❌ ضعيف - يحتاج إعادة معايرة"
    L.append(f"التقييم: {interp}")
    L.append("=" * 60)
    return "\n".join(L)


# ============================================================
# ============ 6. Satellite Data ============
# ============================================================
def fetch_satellite_data(lat, lon, years=3):
    """
    جلب بيانات الأقمار الصناعية من Open-Meteo (ERA5)

    ✅ إصلاح v60.0: التحقق من صحة الإحداثيات
    """
    import requests

    # ✅ التحقق من الإحداثيات
    try:
        lat_f = float(lat)
        lon_f = float(lon)
        if not (-90 <= lat_f <= 90):
            return {"rainfall_mm": None, "temperature_c": None,
                    "aridity": "خطأ إحداثيات", "ndvi_estimated": None,
                    "source": "Latitude must be -90 to 90"}
        if not (-180 <= lon_f <= 180):
            return {"rainfall_mm": None, "temperature_c": None,
                    "aridity": "خطأ إحداثيات", "ndvi_estimated": None,
                    "source": "Longitude must be -180 to 180"}
    except (ValueError, TypeError):
        return {"rainfall_mm": None, "temperature_c": None,
                "aridity": "خطأ إحداثيات", "ndvi_estimated": None,
                "source": "Invalid latitude/longitude"}

    try:
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=365 * years)).strftime('%Y-%m-%d')

        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat_f,
            "longitude": lon_f,
            "start_date": start,
            "end_date": end,
            "daily": ["precipitation_sum", "temperature_2m_mean"],
            "timezone": "Africa/Khartoum"
        }

        r = requests.get(url, params=params, timeout=60)
        if r.status_code != 200:
            return {"rainfall_mm": None, "temperature_c": None,
                    "aridity": "غير محدد", "ndvi_estimated": None,
                    "source": f"HTTP {r.status_code}"}

        data = r.json()
        daily = data.get("daily", {})
        rain_data = daily.get("precipitation_sum", [])
        temp_data = daily.get("temperature_2m_mean", [])

        rv = [x for x in rain_data if x is not None]
        tv = [x for x in temp_data if x is not None]

        rain = round(sum(rv) / years, 1) if rv else None
        temp = round(sum(tv) / len(tv), 1) if tv else None

        aridity = "غير محدد"
        if rain is not None:
            if rain < 100: aridity = "صحراوي"
            elif rain < 250: aridity = "شبه جاف"
            elif rain < 500: aridity = "شبه رطب"
            else: aridity = "رطب"

        ndvi = None
        if rain is not None:
            ndvi = round(min(0.7, max(0.05, rain / 1000.0)), 3)

        return {"rainfall_mm": rain, "temperature_c": temp,
                "aridity": aridity, "ndvi_estimated": ndvi,
                "source": "ERA5 (ECMWF) via Open-Meteo",
                "n_years": years, "n_days": len(rv)}
    except requests.exceptions.Timeout:
        return {"rainfall_mm": None, "temperature_c": None,
                "aridity": "انتهت المهلة", "ndvi_estimated": None,
                "source": "Timeout (60s)"}
    except requests.exceptions.ConnectionError:
        return {"rainfall_mm": None, "temperature_c": None,
                "aridity": "خطأ اتصال", "ndvi_estimated": None,
                "source": "Connection Error"}
    except Exception as e:
        return {"rainfall_mm": None, "temperature_c": None,
                "aridity": "غير محدد", "ndvi_estimated": None,
                "source": f"خطأ: {str(e)[:50]}"}


# ============================================================
# ============ 7. Agricultural Module ============
# ============================================================
def calculate_sar(na, ca, mg):
    """
    حساب نسبة امتصاص الصوديوم (SAR)

    USSL 1954:
    S1: 0-10 | S2: 10-18 | S3: 18-26 | S4: >26
    """
    try:
        na = float(na); ca = float(ca); mg = float(mg)
        if ca + mg <= 0:
            return {"sar": None, "level": "غير محدد", "color": "gray",
                    "action": "بيانات ناقصة"}
        sar = na / np.sqrt((ca + mg) / 2)
        if sar < 10:
            level, color, action = "منخفض", "green", "آمن للري"
        elif sar < 18:
            level, color, action = "متوسط", "yellow", "مراقبة دورية"
        elif sar < 26:
            level, color, action = "مرتفع", "orange", "يحتاج معالجة"
        else:
            level, color, action = "مرتفع جدا", "red", "غير مناسب للري"
        return {"sar": round(sar, 2), "level": level, "color": color, "action": action}
    except Exception:
        return {"sar": None, "level": "خطأ", "color": "gray",
                "action": "بيانات غير صحيحة"}


def calculate_na_percent(na, ca, mg, k=0):
    """حساب نسبة الصوديوم (Na%)"""
    try:
        na = float(na); ca = float(ca); mg = float(mg); k = float(k)
        total = na + ca + mg + k
        if total <= 0:
            return {"na_percent": None, "level": "غير محدد", "color": "gray",
                    "action": "بيانات ناقصة"}
        nap = (na / total) * 100
        if nap < 20:
            level, color, action = "ممتاز", "green", "آمن تماماً"
        elif nap < 40:
            level, color, action = "جيد", "green", "آمن"
        elif nap < 60:
            level, color, action = "مقبول", "yellow", "مراقبة"
        elif nap < 80:
            level, color, action = "مشكوك", "orange", "يحتاج معالجة"
        else:
            level, color, action = "غير مناسب", "red", "غير صالح للري"
        return {"na_percent": round(nap, 2), "level": level, "color": color,
                "action": action}
    except Exception:
        return {"na_percent": None, "level": "خطأ", "color": "gray",
                "action": "بيانات غير صحيحة"}


def calculate_ec_quality(ec):
    """
    تصنيف جودة المياه حسب التوصيلية الكهربائية (EC)

    ✅ USSL 1954 — محدث بدقة:
    C1: < 0.25 | C2: 0.25-0.75 | C3: 0.75-2.25 | C4: 2.25-4.0 | C4+: >4.0
    """
    try:
        ec = float(ec)
        if ec < 0.25:
            level, color, action = "C1 - ممتاز", "green", "آمن للري"
        elif ec < 0.75:
            level, color, action = "C2 - جيد", "green", "آمن"
        elif ec < 2.25:
            level, color, action = "C3 - مقبول", "yellow", "مراقبة"
        elif ec < 4.0:
            level, color, action = "C4 - مشكوك", "orange", "يحتاج معالجة"
        else:
            level, color, action = "C4+ - غير مناسب", "red", "غير صالح للري"
        return {"ec": ec, "level": level, "color": color, "action": action}
    except Exception:
        return {"ec": None, "level": "خطأ", "color": "gray",
                "action": "بيانات غير صحيحة"}


def calculate_nitrate_risk_index(no3_mg_l, fertilizer_use=0.5,
                                   land_use_factor=0.5, depth_m=15):
    """حساب مؤشر مخاطر النترات (NRI)"""
    try:
        no3 = float(no3_mg_l)
        LIMIT = 50.0  # WHO 2022
        ratio = no3 / LIMIT if LIMIT > 0 else 0
        nri = ratio * fertilizer_use * land_use_factor
        depth_factor = max(0.1, min(1.0, 15.0 / max(1, depth_m)))
        nri *= depth_factor
        nri = round(nri, 3)

        if nri <= 0.3: level, color, action = "منخفض", "green", "مراقبة سنوية"
        elif nri <= 1.0: level, color, action = "متوسط", "yellow", "مراقبة دورية"
        elif nri <= 2.0: level, color, action = "مرتفع", "orange", "تدخل عاجل"
        else: level, color, action = "مرتفع جدا", "red", "إيقاف التسميد"

        return {"nri": nri, "no3_ratio": round(ratio, 2),
                "fertilizer_factor": fertilizer_use,
                "land_use_factor": land_use_factor,
                "depth_factor": round(depth_factor, 3),
                "level": level, "color": color, "action": action,
                "no3_limit": LIMIT}
    except Exception as e:
        return {"nri": None, "level": "خطأ", "color": "gray",
                "action": f"خطأ: {str(e)[:40]}"}


def calculate_agricultural_drastic(base_drastic, no3_mg_l,
                                     fertilizer_use=0.5,
                                     land_use_factor=0.5,
                                     depth_m=15,
                                     alpha_agri=0.50,
                                     max_cap=300):
    """
    DRASTIC-Agri = DRASTIC × (1 + α × NRI)

    ✅ إصلاح v60.0: max_cap = 300 (متوافق مع DRASTIC-Tox)
    """
    nri_result = calculate_nitrate_risk_index(
        no3_mg_l, fertilizer_use, land_use_factor, depth_m)
    nri = nri_result.get("nri", 0)
    if nri is None:
        nri = 0

    modifier = 1.0 + (alpha_agri * nri)
    drastic_agri = min(max_cap, base_drastic * modifier)

    if drastic_agri >= 180: level, color = "مرتفع جدا", "red"
    elif drastic_agri >= 140: level, color = "مرتفع", "orange"
    elif drastic_agri >= 100: level, color = "متوسط", "yellow"
    else: level, color = "منخفض", "green"

    return {
        "base_drastic": base_drastic,
        "nri": nri_result.get("nri"),
        "drastic_agri": round(drastic_agri, 1),
        "modifier": round(modifier, 3),
        "increase_pct": round(((drastic_agri - base_drastic) / base_drastic * 100)
                              if base_drastic > 0 else 0, 1),
        "level": level, "color": color,
        "nri_details": nri_result,
        "alpha_agri": alpha_agri,
        "max_cap": max_cap
    }


def classify_irrigation_water(sar_result, na_result, ec_result):
    """تصنيف شامل لجودة مياه الري"""
    score = 0
    if sar_result.get("color") == "green": score += 3
    elif sar_result.get("color") == "yellow": score += 2
    elif sar_result.get("color") == "orange": score += 1

    if na_result.get("color") == "green": score += 3
    elif na_result.get("color") == "yellow": score += 2
    elif na_result.get("color") == "orange": score += 1

    if ec_result.get("color") == "green": score += 3
    elif ec_result.get("color") == "yellow": score += 2
    elif ec_result.get("color") == "orange": score += 1

    if score >= 8:
        return {"class": "C1-S1", "level": "ممتاز", "color": "green",
                "action": "آمن لجميع المحاصيل"}
    elif score >= 6:
        return {"class": "C2-S1", "level": "جيد", "color": "green",
                "action": "آمن لمعظم المحاصيل"}
    elif score >= 4:
        return {"class": "C3-S2", "level": "مقبول", "color": "yellow",
                "action": "آمن لمحاصيل متحملة"}
    elif score >= 2:
        return {"class": "C4-S3", "level": "مشكوك", "color": "orange",
                "action": "يحتاج معالجة"}
    else:
        return {"class": "C4-S4", "level": "غير مناسب", "color": "red",
                "action": "غير صالح للري"}
