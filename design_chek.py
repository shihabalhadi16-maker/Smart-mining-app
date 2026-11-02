"""فحوص تصميم الدراسة للتحقق التنبؤي: استقلال مكاني، ترتيب زمني، توثيق القياس، وحجم العينة.
وحدة نقية (بدون Streamlit). تُستدعى من وضع التنبؤ المستقل في app.py."""
import math
from statistics import NormalDist
import numpy as np
import pandas as pd

DOC_FIELDS = ["lab", "measure_date", "method", "detection_limit"]
MIN_DISTANCE_KM = 5.0


def haversine_km(lat1, lon1, lat2, lon2):
    """المسافة الكروية بالكيلومتر (الدرجات العشرية)."""
    R = 6371.0088
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1; dl = np.radians(np.asarray(lon2) - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def check_spatial_independence(train, test, min_km=MIN_DISTANCE_KM):
    """يعيد (الحالة, قائمة المخالفات). الحالة: 'مثبت' | 'فشل' | 'غير قابل للتحقق'."""
    if not {"lat", "lon"} <= set(train.columns) or not {"lat", "lon"} <= set(test.columns):
        return "غير قابل للتحقق", ["الإحداثيات (lat/lon) غير موجودة"]
    if train[["lat", "lon"]].isna().any().any() or test[["lat", "lon"]].isna().any().any():
        return "غير قابل للتحقق", ["توجد إحداثيات فارغة"]
    viol = []
    for _, t in test.iterrows():
        d = haversine_km(t["lat"], t["lon"], train["lat"].values, train["lon"].values)
        k = int(np.argmin(d))
        if d[k] < min_km:
            viol.append(f"{t.get('location_id', '?')} يبعد {d[k]:.2f} كم عن {train.iloc[k].get('location_id', '?')} (الحد {min_km} كم)")
    return ("فشل" if viol else "مثبت"), viol


def check_temporal_order(train, test):
    """كل قياسات الاختبار يجب أن تكون بعد آخر قياس تدريب. يحتاج عمود measure_date (YYYY-MM-DD)."""
    if "measure_date" not in train.columns or "measure_date" not in test.columns:
        return "غير قابل للتحقق", ["عمود measure_date غير موجود"]
    try:
        tr = pd.to_datetime(train["measure_date"], errors="raise")
        te = pd.to_datetime(test["measure_date"], errors="raise")
    except Exception as e:
        return "فشل", [f"تاريخ غير صالح: {type(e).__name__}"]
    if tr.isna().any() or te.isna().any():
        return "غير قابل للتحقق", ["توجد تواريخ فارغة"]
    last_train = tr.max()
    early = te[te <= last_train]
    if len(early):
        return "فشل", [f"{len(early)} قياس اختبار سابق لآخر قياس تدريب ({last_train.date()})"]
    return "مثبت", []


def check_documentation(df, fields=DOC_FIELDS):
    """يعيد قائمة الصفوف الناقصة للحقول المطلوبة توثيقها."""
    missing_cols = [f for f in fields if f not in df.columns]
    if missing_cols:
        return "فشل", [f"أعمدة توثيق ناقصة: {', '.join(missing_cols)}"]
    bad = []
    for i, r in df.iterrows():
        gaps = [f for f in fields if pd.isna(r[f]) or str(r[f]).strip() == ""]
        if gaps:
            bad.append(f"صف {i + 2} ({r.get('location_id', '?')}): {', '.join(gaps)}")
    return ("فشل" if bad else "مثبت"), bad


def sample_size_auc(auc, prevalence, alpha=0.05, power=0.80, null=0.5):
    """الحجم الإجمالي التقريبي لاختبار AUC ضد الصدفة (طريقة Hanley–McNeil). تقريب، وليس نتيجة دقيقة."""
    z = NormalDist().inv_cdf(1 - alpha / 2) + NormalDist().inv_cdf(power)

    def var(a, n1, n0):
        q1 = a / (2 - a); q2 = 2 * a * a / (1 + a)
        return (a * (1 - a) + (n1 - 1) * (q1 - a * a) + (n0 - 1) * (q2 - a * a)) / (n1 * n0)

    for N in range(10, 5001):
        n1 = max(2, round(N * prevalence)); n0 = N - n1
        if n0 < 2:
            continue
        if (auc - null) / math.sqrt(var(auc, n1, n0)) >= z:
            return {"total": N, "positives": n1, "negatives": n0}
    return None


def design_report(train, test, enforce_docs=True):
    """يجمع الفحوص ويعطي حكماً واحداً مع الأسباب. لا يعدّل البيانات."""
    rows = []
    s1, v1 = check_spatial_independence(train, test)
    rows.append(("الاستقلال المكاني (تدريب/اختبار)", s1, v1))
    s2, v2 = check_temporal_order(train, test)
    rows.append(("الترتيب الزمني", s2, v2))
    if enforce_docs:
        s3, v3 = check_documentation(pd.concat([train, test]))
        rows.append(("توثيق القياس (المختبر، التاريخ، الطريقة، حد الكشف)", s3, v3))
    failed = [r for r in rows if r[1] == "فشل"]
    unverif = [r for r in rows if r[1] == "غير قابل للتحقق"]
    if failed:
        verdict = "مرفوض: يوجد فشل في فحص واحد على الأقل"
    elif unverif:
        verdict = "غير مؤهل للاستنتاج المستقل: بعض الفحوص غير قابلة للتحقق"
    else:
        verdict = "مؤهل للتحليل المستقل وفق الفحوص"
    return {"rows": rows, "verdict": verdict}


def render_sample_size(st, tx):
    """حاسبة حجم العينة كقسم قابل للطي (تُستدعى من وضع التنبؤ)."""
    with st.expander(tx("حاسبة حجم العينة (تقريبية)", "Sample size calculator (approx.)")):
        a_ = st.slider(tx("AUC المتوقع", "Expected AUC"), 0.55, 0.95, 0.70, 0.01, key="ss_auc")
        p_ = st.slider(tx("نسبة الملوث المتوقعة", "Expected prevalence"), 0.05, 0.95, 0.30, 0.05, key="ss_prev")
        res_ss = sample_size_auc(a_, p_)
        if res_ss:
            st.write(f"{tx('الحجم الإجمالي التقريبي', 'Approx. total')}: {res_ss['total']} "
                     f"({tx('ملوثة', 'positive')}: {res_ss['positives']}، {tx('غير ملوثة', 'negative')}: {res_ss['negatives']})")
        st.caption(tx("لاختبار أن AUC أعلى من 0.5 بقوة 80% وألفا 0.05. مقارنة متنبئين مقترنة تحتاج عينة أكبر. العدد يفترض مواقع مستقلة.",
                      "Tests AUC > 0.5 with 80% power, alpha 0.05. Paired comparison needs more. Assumes independent sites."))


def render_design(st, tx, df_ds):
    """يعرض فحوص التصميم ويعيد الحكم. df_ds يحوي عمود split."""
    rep = design_report(df_ds[df_ds["split"] == "train"], df_ds[df_ds["split"] == "test"], enforce_docs=True)
    st.subheader(tx("فحوص التصميم", "Design checks"))
    icons = {"مثبت": "✅", "فشل": "❌", "غير قابل للتحقق": "⚠️"}
    for name, status, detail in rep["rows"]:
        st.write(f"{icons[status]} **{name}**: {status}")
        for d_ in detail[:8]:
            st.caption(d_)
    st.write(f"**{tx('حكم التصميم', 'Design verdict')}:** {rep['verdict']}")
    return rep["verdict"]
