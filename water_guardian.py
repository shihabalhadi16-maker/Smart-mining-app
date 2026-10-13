"""
water_guardian.py  v61 - "حارس المياه" irrigation-water tab (was inline in app.py)
Requires: streamlit, pandas, drastic_core.py

Differences from the old inline tab
  * the 0-100 "IWQI" with invented weights is gone (it was not Meireles et al. 2010); results are
    now rule-based and transparent: USSL class (Richards 1954) + FAO 29 hazard classes
    (Ayers & Westcot 1985); the overall result is the WORST hazard, never an average
  * crop suitability uses Maas-Hoffman salt-tolerance parameters (dc.CROPS), not hand-typed limits
  * gum arabic is not in FAO 29: it is not scored (no peer-reviewed table in this project)
  * the sample wells are ILLUSTRATIVE numbers, not measurements
FAO 29 class limits below were typed from memory: verify them against the original tables before publishing.
"""
import streamlit as st
import pandas as pd
import drastic_core as dc

NO3_TO_NO3N = 14.0 / 62.0

WELLS = {   # illustrative only
    "بئر نموذجي 1": {"ec": 0.9, "sar": 4.5, "no3": 8.0, "cl": 3.0, "hco3": 2.5},
    "بئر نموذجي 2": {"ec": 0.5, "sar": 2.5, "no3": 4.0, "cl": 2.0, "hco3": 1.5},
    "بئر نموذجي 3": {"ec": 2.8, "sar": 8.5, "no3": 18.0, "cl": 8.0, "hco3": 4.5},
    "بئر نموذجي 4": {"ec": 4.5, "sar": 12.0, "no3": 25.0, "cl": 15.0, "hco3": 6.0},
}
_RANK = {"none": 0, "slight_moderate": 1, "severe": 2}
_LABEL = {"none": "🟢 لا خطر", "slight_moderate": "🟡 خطر طفيف–متوسط", "severe": "🔴 خطر شديد"}


def _band(x, lo, hi):
    return "none" if x < lo else "slight_moderate" if x <= hi else "severe"


def assess(ec, sar, no3, cl, hco3):
    no3n = no3 * NO3_TO_NO3N
    h = {"الملوحة (FAO)": dc.fao_salinity_hazard(ec),
         "تسرب التربة (SAR+EC)": dc.fao_infiltration_hazard(sar, ec),
         "الكلوريد (ري سطحي)": _band(cl, 4, 10),
         "البيكربونات (رش علوي)": _band(hco3, 1.5, 8.5),
         "النيتروجين NO3-N": _band(no3n, 5, 30)}
    worst = max(h.values(), key=lambda k: _RANK[k])
    return h, worst, no3n


def render():
    st.markdown("""<div style="background:linear-gradient(135deg,#184e77,#34a0a4);color:white;padding:20px;
    border-radius:10px;text-align:center;margin-bottom:20px;"><h2 style="margin:0;">💧 حارس المياه</h2>
    <p style="margin:5px 0;opacity:0.95;">تقييم مياه الري | USSL + FAO 29</p></div>""", unsafe_allow_html=True)
    st.warning("⚠️ أداة فحص أولي منفصلة عن نموذج DRASTIC-Tox. الأرقام الجاهزة للآبار نموذجية وليست قياسات.")

    for k, v in {"wg_ec": 0.9, "wg_sar": 4.5, "wg_no3": 8.0, "wg_cl": 3.0, "wg_hco3": 2.5}.items():
        st.session_state.setdefault(k, v)

    t1, t2, t3 = st.tabs(["💧 تقييم عينة", "🌾 المحاصيل", "📚 المراجع والتنبيهات"])

    with t1:
        c1, c2 = st.columns([1, 2])
        with c1:
            sel = st.selectbox("قيم نموذجية (اختياري):", ["— إدخال يدوي —"] + list(WELLS), key="wg_well_sel")
            if sel != "— إدخال يدوي —" and st.session_state.get("wg_last_sel") != sel:
                for k, v in WELLS[sel].items():
                    st.session_state[f"wg_{k}"] = v
                st.session_state["wg_last_sel"] = sel
                st.rerun()
            ec = st.slider("EC (dS/m)", 0.1, 8.0, float(st.session_state["wg_ec"]), 0.1, key="wg_ec_s")
            sar = st.slider("SAR", 0.0, 30.0, float(st.session_state["wg_sar"]), 0.1, key="wg_sar_s")
            no3 = st.slider("NO₃ (mg/L)", 0.0, 100.0, float(st.session_state["wg_no3"]), 0.5, key="wg_no3_s")
            cl = st.slider("Cl (meq/L)", 0.0, 30.0, float(st.session_state["wg_cl"]), 0.5, key="wg_cl_s")
            hco3 = st.slider("HCO₃ (meq/L)", 0.0, 12.0, float(st.session_state["wg_hco3"]), 0.1, key="wg_hco3_s")
        with c2:
            haz, worst, no3n = assess(ec, sar, no3, cl, hco3)
            c, s = dc.ussl_salinity(ec), dc.ussl_sodium(sar)
            k1, k2, k3 = st.columns(3)
            k1.metric("تصنيف USSL", f"{c}-{s}")
            k2.metric("أسوأ خطر", _LABEL[worst])
            k3.metric("NO₃ مقابل حد الشرب (50)", f"{no3 / 50:.2f}×")
            st.dataframe(pd.DataFrame([{"المعيار": k, "التصنيف": _LABEL[v]} for k, v in haz.items()]),
                         use_container_width=True, hide_index=True)
            st.caption(f"NO₃-N = {no3n:.1f} mg/L (تحويل من NO₃). النتيجة العامة = أسوأ خطر وليست متوسطاً.")
            rows = [{"المحصول": name, "الغلة النسبية المتوقعة %": dc.relative_yield(name, ec)} for name in dc.CROPS]
            st.markdown("#### 🌾 الغلة النسبية المتوقعة (Maas-Hoffman، ECe ≈ 1.5×ECw)")
            st.dataframe(pd.DataFrame(rows).sort_values("الغلة النسبية المتوقعة %", ascending=False),
                         use_container_width=True, hide_index=True)

    with t2:
        crop = st.selectbox("المحصول", list(dc.CROPS), key="wg_crop_sel")
        a, b = dc.CROPS[crop]
        st.info(f"عتبة ECe = **{a} dS/m** | ميل الانخفاض = **{b}%** لكل dS/m. (تحقق من FAO 29 جدول 4)")
        ecw = st.slider("EC مياه الري ECw (dS/m)", 0.1, 10.0, 1.0, 0.1, key="wg_c_ec")
        lf = st.slider("عامل التحويل ECe/ECw", 1.0, 2.0, 1.5, 0.1, key="wg_c_lf")
        y = dc.relative_yield(crop, ecw, lf)
        st.metric("الغلة النسبية المتوقعة", f"{y}%")
        st.progress(min(1.0, y / 100))
        xs = [i / 10 for i in range(1, 101)]
        st.line_chart(pd.DataFrame({"ECw": xs, "الغلة %": [dc.relative_yield(crop, x, lf) for x in xs]}).set_index("ECw"))
        st.caption("الصمغ العربي غير مدرج في FAO 29، فلا يُقيَّم هنا حتى توجد مرجعية محكّمة.")

    with t3:
        st.markdown("""
### المراجع
- **USSL (Richards 1954)** — USDA Handbook 60: تصنيف الملوحة C1–C4 والصوديوم S1–S4.
- **FAO 29 (Ayers & Westcot 1985)** — فئات الخطر للملوحة والتسرب والكلوريد والبيكربونات والنيتروجين.
- **Maas & Hoffman (1977)** — تحمل المحاصيل للملوحة (ECe، الميل).
- **WHO** — حد النترات في مياه الشرب 50 mg/L (NO₃).

### تنبيهات
- حدود فئات FAO 29 كُتبت من الذاكرة: راجع الجداول الأصلية قبل النشر.
- تصنيف USSL لـ S1–S4 هنا مبسّط (لا يعتمد على EC كما في مخطط USSL الكامل).
- لا يغني عن التحليل المخبري ولا عن استشارة مهندس زراعي.
""")
