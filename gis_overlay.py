"""التراكب المرجّح لـDRASTIC على شبكة (منهجية ArcGIS: Reclassify + Weighted Overlay).
وحدة نقية بـnumpy. لا تستورد app.py؛ دوال التقييم تُمرَّر كمعاملات لضمان أنها نفسها المستخدمة في الحساب النقطي.
تجريبية: تعمل على طبقات تُرفع إليها، ولا تُعد دليلاً مكانياً بذاتها."""
import numpy as np

W_STD = {"D": 5, "R": 4, "A": 3, "S": 2, "T": 1, "I": 5, "C": 3}
DRASTIC_HIGH = 140


def reclassify(layer, fn):
    """يحوّل قيم طبقة (مصفوفة) إلى تقييمات بالدالة fn. NaN يبقى NaN (لا تعبئة صامتة)."""
    arr = np.asarray(layer, dtype=float)
    out = np.full(arr.shape, np.nan)
    it = np.nditer(arr, flags=["multi_index"])
    for v in it:
        if not np.isnan(v.item()):
            out[it.multi_index] = fn(float(v.item()))
    return out


def reclassify_categorical(layer, table):
    """للطبقات الفئوية (خزان، تربة، منطقة غير مشبعة). قيمة غير معروفة ترفع خطأ."""
    arr = np.asarray(layer, dtype=object)
    out = np.full(arr.shape, np.nan)
    for idx, v in np.ndenumerate(arr):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            continue
        if str(v) not in table:
            raise ValueError(f"فئة غير معروفة: {v}")
        out[idx] = table[str(v)]
    return out


def weighted_overlay(ratings, weights=W_STD):
    """ratings: قاموس {'D': مصفوفة تقييم، ...}. يعيد مصفوفة DRASTIC.
    أي خلية فيها NaN في أي طبقة تبقى NaN."""
    keys = list(weights)
    missing = [k for k in keys if k not in ratings]
    if missing:
        raise ValueError(f"طبقات ناقصة: {missing}")
    shapes = {np.asarray(ratings[k]).shape for k in keys}
    if len(shapes) != 1:
        raise ValueError(f"أبعاد الطبقات غير متطابقة: {shapes}")
    total = np.zeros(next(iter(shapes)))
    for k in keys:
        total = total + weights[k] * np.asarray(ratings[k], dtype=float)
    return total


def classify(index):
    """تصنيف واحد مُعلن: 140 فاصل اصطلاحي (وليس معايَراً). NaN يبقى NaN."""
    idx = np.asarray(index, dtype=float)
    out = np.where(np.isnan(idx), np.nan, np.where(idx >= DRASTIC_HIGH, 1.0, 0.0))
    return out


def top_cells(index, k=5):
    """أعلى k خلية هشاشة (تتجاهل NaN). تعيد قائمة (صف، عمود، قيمة)."""
    idx = np.asarray(index, dtype=float)
    flat = [(float(v), i) for i, v in np.ndenumerate(idx) if not np.isnan(v)]
    flat.sort(key=lambda t: -t[0])
    return [(int(i[0]), int(i[1]), round(v, 2)) for v, i in flat[:k]]


OVERLAY_COLS = ["row", "col", "depth_m", "recharge_mm", "slope_pct", "conductivity", "aquifer", "soil", "vadose"]


def build_grid(df):
    """يحوّل جدول (صف، عمود، القيم) إلى مصفوفات. الخلايا غير المذكورة تبقى NaN."""
    import pandas as pd
    nr = int(df["row"].max()) + 1; nc = int(df["col"].max()) + 1
    arrays = {c: np.full((nr, nc), np.nan) for c in ["depth_m", "recharge_mm", "slope_pct", "conductivity"]}
    cat = {c: np.full((nr, nc), None, dtype=object) for c in ["aquifer", "soil", "vadose"]}
    for r in df.to_dict("records"):
        i, j = int(r["row"]), int(r["col"])
        for c in arrays:
            v = r.get(c)
            arrays[c][i, j] = float(v) if v is not None and str(v) != "nan" else np.nan
        for c in cat:
            v = r.get(c)
            cat[c][i, j] = None if v is None or str(v) == "nan" else str(v)
    return arrays, cat


def render_view(st, tx, fns, evaluate_site, std):
    """واجهة وضع الهشاشة بالتراكب. fns: r_D, r_R, r_T, r_C, AQUIFER, SOIL, VADOSE من التطبيق نفسه."""
    import io, pandas as pd
    st.warning(tx("وضع تجريبي: يحسب هشاشة كل خلية بمنهجية التراكب المرجّح. لا يُعد خريطة معتمدة، ولا يثبت التنبؤ بالتلوث. الجداول من الذاكرة وتحتاج مطابقة.",
                  "Experimental: computes per-cell vulnerability by weighted overlay. Not an approved map and does not prove contamination prediction."))
    tpl = pd.DataFrame(columns=OVERLAY_COLS + ["lat", "lon"])
    st.download_button(tx("📥 قالب الشبكة (CSV)", "📥 Grid template (CSV)"), tpl.to_csv(index=False).encode("utf-8-sig"),
                       file_name="overlay_grid_template.csv", mime="text/csv")
    up = st.file_uploader("CSV / Excel (grid)", type=["csv", "xlsx"], key="ov_up")
    if up is None:
        st.caption(tx("كل صف = خلية: row وcol (من 0)، والقيم الخام، وlat وlon اختياريان.", "Each row = one cell: row and col (0-based), raw values, optional lat/lon."))
        return
    df = pd.read_csv(up) if up.name.endswith(".csv") else pd.read_excel(up)
    missing = [c for c in OVERLAY_COLS if c not in df.columns]
    if missing:
        st.error(f"{tx('أعمدة ناقصة', 'Missing columns')}: {missing}")
        return
    arrays, cat = build_grid(df)
    rat = {"D": reclassify(arrays["depth_m"], fns["r_D"]), "R": reclassify(arrays["recharge_mm"], fns["r_R"]),
           "T": reclassify(arrays["slope_pct"], fns["r_T"]), "C": reclassify(arrays["conductivity"], fns["r_C"]),
           "A": reclassify_categorical(cat["aquifer"], fns["AQUIFER"]), "S": reclassify_categorical(cat["soil"], fns["SOIL"]),
           "I": reclassify_categorical(cat["vadose"], fns["VADOSE"])}
    grid = weighted_overlay(rat)
    cls = classify(grid)
    n_ok = int(np.sum(~np.isnan(grid))); n_all = grid.size
    st.write(f"{tx('خلايا محسوبة', 'cells computed')}: {n_ok} / {n_all} | "
             f"{tx('>= 140 (أولوية)', '>= 140 (priority)')}: {int(np.nansum(cls))}")
    if n_ok < n_all:
        st.warning(tx(f"{n_all - n_ok} خلية ناقصة القيم، وتُترك فارغة ولا تُعبأ.", f"{n_all - n_ok} cells have missing values and are left empty."))
    top = top_cells(grid, k=10)
    rows = []
    for i, j, v in top:
        rr = df[(df["row"] == i) & (df["col"] == j)]
        lat = rr["lat"].iloc[0] if ("lat" in df.columns and len(rr)) else ""
        lon = rr["lon"].iloc[0] if ("lon" in df.columns and len(rr)) else ""
        rows.append({"row": i, "col": j, "DRASTIC": v, "lat": lat, "lon": lon})
    st.subheader(tx("أعلى 10 خلايا هشاشة (أولوية للنزول الميداني)", "Top 10 cells (field priority)"))
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.subheader(tx("تحقق: حساب الخلية نفسها بحساب البرنامج النقطي", "Check: same cell via point calculator"))
    if top:
        i, j, v = top[0]
        r = df[(df["row"] == i) & (df["col"] == j)].iloc[0].to_dict()
        site = {"depth_m": r["depth_m"], "recharge_mm": r["recharge_mm"], "slope_pct": r["slope_pct"],
                "conductivity": r["conductivity"], "aquifer": r["aquifer"], "soil": r["soil"], "vadose": r["vadose"],
                "cn_water_mg_l": r.get("cn_water_mg_l", 0.0) if "cn_water_mg_l" in r else 0.0,
                "hg_water_mg_l": r.get("hg_water_mg_l", 0.0) if "hg_water_mg_l" in r else 0.0}
        try:
            pt = evaluate_site(site, std)["idx"]
            st.write(f"{tx('الخلية', 'cell')} ({i}, {j}): {tx('الشبكة', 'grid')} = {v} | {tx('البرنامج النقطي', 'point calc')} = {pt} | "
                     f"{'✅' if abs(pt - v) < 1e-9 else '❌'}")
        except ValueError as e:
            st.caption(f"{tx('الحساب النقطي يحتاج CN وHg للخلية', 'Point calc needs CN and Hg for the cell')}: {e}")
    out = pd.DataFrame(grid)
    st.download_button(tx("📥 تنزيل خريطة الهشاشة (CSV: صفوف × أعمدة)", "📥 Download vulnerability grid (CSV)"),
                       out.to_csv(index=False, header=False).encode("utf-8-sig"), file_name="drastic_grid.csv", mime="text/csv")
