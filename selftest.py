"""الاختبارات الذاتية لـDRASTIC-Tox. تُشغَّل من الشريط الجانبي أو بالأمر: python app.py --selftest"""
import sys, math
import numpy as np
import pandas as pd


def run(ds, A):
    # يستخدم دوال التطبيق عبر الوحدة A (تُنسخ أسماؤها إلى هذا النطاق)
    globals().update({k: getattr(A, k) for k in dir(A) if not k.startswith("__")})
    res = []

    def chk(name, cond, detail=""):
        res.append((name, bool(cond), str(detail)))

    base = {"depth_m": 15, "recharge_mm": 20, "slope_pct": 3, "conductivity": 3, "aquifer": "massive_shale",
            "soil": "thin_or_absent", "vadose": "confining_layer", "cn_water_mg_l": 0.025, "hg_water_mg_l": 0.011}
    ev = evaluate(base, "SUDAN")
    chk("A: DRASTIC = 72", ev["idx"] == 72, ev["idx"])
    chk("A: hazard(Hg=0.011, limit=0.004) = 4.39", round(hazard_score(0.011, 0.004), 2) == 4.39)
    chk("A: DRASTIC-Tox = 76.4 (SUDAN Hg=0.004)", ev["tox"]["tox"] == 76.4, ev["tox"]["tox"])
    chk("A: الزيادة 6.1%", ev["tox"]["inc_pct"] == 6.1, ev["tox"]["inc_pct"])
    chk("A: EU = 82.4", evaluate(base, "EU")["tox"]["tox"] == 82.4, evaluate(base, "EU")["tox"]["tox"])
    chk("حدود DRASTIC 23..226", index_of({k: 1 for k in W_STD}) == 23 and
        index_of({"D": 10, "R": 9, "A": 10, "S": 10, "T": 10, "I": 10, "C": 10}) == 226)
    chk("حدود Pesticide 26..256", index_of({k: 1 for k in W_PEST}, W_PEST) == 26 and
        index_of({"D": 10, "R": 9, "A": 10, "S": 10, "T": 10, "I": 10, "C": 10}, W_PEST) == 256)
    chk("WHO: CN = 0.07 يعطي HQ=1", tox_eval(0, 0.07, 0, "WHO")["hq"] == 1.0)
    chk("تصنيف HQ: 1 مطابق، 5.5 مرتفع قليلاً، 11 مرتفع", hq_class(1) == "compliant" and
        hq_class(5.5) == "elevated" and hq_class(11) == "hq_high")
    chk("الميل: 2.0 → 10 و 2.1 → 9", r_T(2.0) == 10 and r_T(2.1) == 9)
    chk("خطأ صريح عند NaN", _raises(lambda: evaluate({**base, "cn_water_mg_l": float("nan")}, "SUDAN")))
    chk("خطأ صريح عند فئة غير معروفة", _raises(lambda: evaluate({**base, "soil": "xyz"}, "SUDAN")))
    chk("parse '<0.001' بقاعدة نصف الحد = 0.0005", parse_conc("<0.001", "نصف حد الكشف") == 0.0005)
    chk("تسرب: التركيز في المتنبئ يُرفض", _raises_msg(lambda: leakage_guard(PREDICTOR_COLS + ["cn_water_mg_l"]), "تسرب"))
    chk("تسرب: DRASTIC-Tox في المتنبئ يُرفض", _raises_msg(lambda: leakage_guard(PREDICTOR_COLS + ["DRASTIC-Tox"]), "تسرب"))
    chk("المتنبئ الجيولوجي وحده مقبول", leakage_guard(PREDICTOR_COLS) is True)
    chk("AUC: فصل تام = 1.0", auc_rank([0, 0, 1, 1], [1, 2, 3, 4]) == 1.0)
    chk("AUC: عكس الفصل = 0.0", auc_rank([0, 0, 1, 1], [4, 3, 2, 1]) == 0.0)
    chk("AUC: كل القيم متعادلة = 0.5", auc_rank([0, 1, 0, 1], [5, 5, 5, 5]) == 0.5)
    _xs = np.linspace(-2, 2, 200); _ys = (_xs + np.random.default_rng(3).normal(0, 0.5, 200) > 0).astype(float)
    _b0, _b1 = fit_logistic(_xs, _ys)
    chk("معايرة: الميل موجب عندما يرتبط المتنبئ بالهدف", _b1 > 0, round(_b1, 3))
    chk("معايرة: Brier = 0.25 للاحتمال 0.5 مع نسبة 50%", abs(brier(np.full(4, 0.5), [0, 1, 0, 1]) - 0.25) < 1e-12)
    chk("معايرة: الاحتمالات بين 0 و1", bool(np.all((_sigmoid(_b0 + _b1 * _xs) > 0) & (_sigmoid(_b0 + _b1 * _xs) < 1))))
    _r2 = np.random.default_rng(9); _X = _r2.normal(size=(300, 2))
    _yy = (_X[:, 0] * 2 - _X[:, 1] * 0.5 + _r2.normal(0, 0.5, 300) > 0).astype(float)
    _c = fit_logistic_multi(_X, _yy)
    chk("نموذج مزدوج: المعاملان يُستعادان بالإشارة الصحيحة", _c[1] > 0 and _c[2] < 0, [round(v, 2) for v in _c])
    if ds is not None:
        try:
            _f = build_map_frame(ds, "SUDAN")
            _need = ["lon", "lat", "D_rating", "R_rating", "A_rating", "S_rating", "T_rating", "I_rating",
                     "C_rating", "CN", "Hg", "DRASTIC", "DRASTIC_Tox"]
            chk("خرائط: الجدول يحوي كل الأعمدة المطلوبة لكل المواقع", all(c in _f.columns for c in _need) and len(_f) == 40, len(_f))
        except Exception as e:
            chk("خرائط: بناء الجدول", False, f"{type(e).__name__}: {e}")
    _ra = {"lats": [0.0, 1.0], "lons": [0.0, 1.0], "raster": [[1.0, 1.0], [1.0, 1.0]]}
    _m, _ok, _all = mask_far_cells(_ra, [(0.0, 0.0, 5.0)], max_km=50)
    chk("خرائط: الخلايا البعيدة عن المواقع تُفرغ", _ok < _all and np.isnan(_m["raster"][1][1]) and _m["raster"][0][0] == 1.0, (_ok, _all))
    import tempfile, os as _os
    _tmp = _os.path.join(tempfile.gettempdir(), "coords_selftest.csv")
    pd.DataFrame([
        {"state": "سنار", "site_key": "A", "lat": "13.5", "lon": "33.6", "source": "Google Maps", "read_date": "2026-10-18"},
        {"state": "سنار", "site_key": "B", "lat": "45.0", "lon": "33.6", "source": "x", "read_date": ""},
        {"state": "سنار", "site_key": "C", "lat": "", "lon": "", "source": "", "read_date": ""},
        {"state": "سنار", "site_key": "D", "lat": "abc", "lon": "33", "source": "", "read_date": ""},
    ]).to_csv(_tmp, index=False, encoding="utf-8-sig")
    _ov, _er = load_coord_overrides(_tmp)
    chk("إحداثيات: الصف الصالح يُقبل", ("سنار", "A") in _ov and _ov[("سنار", "A")]["lat"] == 13.5)
    chk("إحداثيات: خارج السودان يُرفض مع رسالة", ("سنار", "B") not in _ov and any("خارج نطاق" in e for e in _er), _er)
    chk("إحداثيات: الصف الفارغ يُتجاهل", ("سنار", "C") not in _ov)
    chk("إحداثيات: القيمة غير الرقمية تُرفض مع رسالة", ("سنار", "D") not in _ov and any("ليست أرقاماً" in e for e in _er))
    _exp = build_map_frame(ds, "SUDAN") if ds is not None else None
    if _exp is not None:
        chk("تصدير: الأعمدة المطلوبة لـArcGIS موجودة", all(c in _exp.columns for c in ["lat", "lon", "D_rating", "C_rating", "DRASTIC", "DRASTIC_Tox", "CN", "Hg"]))
    try:
        import design_checks as _dct
        _tr = pd.DataFrame({"location_id": ["a"], "lat": [13.0], "lon": [33.0], "measure_date": ["2024-01-10"], "lab": ["L"], "method": ["M"], "detection_limit": [0.1]})
        _te = pd.DataFrame({"location_id": ["b"], "lat": [13.01], "lon": [33.0], "measure_date": ["2023-03-01"], "lab": ["L"], "method": ["M"], "detection_limit": [0.1]})
        chk("تصميم: موقعان على 1.1 كم يُرفضان بالاستقلال المكاني", _dct.check_spatial_independence(_tr, _te)[0] == "فشل")
        chk("تصميم: اختبار سابق للتدريب زمنياً يُرفض", _dct.check_temporal_order(_tr, _te)[0] == "فشل")
        chk("تصميم: 111.2 كم لكل درجة عرض", abs(float(_dct.haversine_km(0, 0, 1, 0)) - 111.19) < 0.05)
        chk("تصميم: حجم العينة للـAUC 0.70 بنسبة 50% بين 40 و80", 40 <= _dct.sample_size_auc(0.70, 0.5)["total"] <= 80)
        chk("تصميم: توثيق ناقص يُرفض", _dct.check_documentation(pd.DataFrame({"lab": [""], "measure_date": ["x"], "method": ["m"], "detection_limit": [1]}))[0] == "فشل")
    except Exception as e:
        chk("تصميم: وحدة الفحوص", False, f"{type(e).__name__}: {e}")
    chk("إضافة: التركيز الحالي في الملف يُرفض", _raises_msg(lambda: prev_guard(PREDICTOR_COLS + PREV_COLS + ["cn_water_mg_l"]), "تركيزاً حالياً"))
    chk("إضافة: الملف الصحيح مقبول", prev_guard(PREDICTOR_COLS + PREV_COLS) is True)
    _rng = np.random.default_rng(7); _n = 80
    _d = pd.DataFrame({"location_id": [f"S{i}" for i in range(_n)], "split": ["test"] * _n,
                       "label": _rng.integers(0, 2, _n), "DRASTIC": _rng.uniform(40, 200, _n),
                       "cn_prev": 0.01, "hg_prev": 0.001})
    _r = prev_contrast(_d, "SUDAN")
    chk("إضافة: بيانات بلا إشارة لا تُقبل", not (_r["diff_ci"][0] > 0), _r["diff_ci"])
    if ds is not None:
        try:
            cal = calib_frame(ds, "SUDAN")
            p4 = (cal["hq"].values > 1).astype(int)
            chk("ج: قاعدة التجاوز kappa = 1.0", abs(cohen_kappa(cal["y"].values, p4) - 1.0) < 1e-9)
            g = ds.get_site_data("كسلا", "Gash_Upstream")
            eb = evaluate(g, "SUDAN")
            chk("ب: Gash_Upstream = 159 و 159.0 و مكافأة 0", eb["idx"] == 159 and eb["tox"]["tox"] == 159.0 and eb["tox"]["bonus"] == 0)
            chk("مراجعة البيانات الخام: كل الحقول موجودة", not audit_db(ds), audit_db(ds)[:3])
        except Exception as e:
            chk("اختبارات البيانات", False, f"{type(e).__name__}: {e}")
    return res


def _raises_msg(fn, word):
    try:
        fn()
    except ValueError as e:
        return word in str(e)
    return False


def _raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


