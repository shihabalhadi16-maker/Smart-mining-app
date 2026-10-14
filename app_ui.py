
# ================================================================= دوال مساعدة للتبويبات

MT_LABEL = {"industrial": ("🏭 صناعي", "🏭 Industrial"), "traditional": ("⛏️ تقليدي", "⛏️ Traditional"),
            "mixed": ("🔀 مختلط", "🔀 Mixed")}


def mt_label(mt):
    ar, en = MT_LABEL.get(mt, MT_LABEL["traditional"])
    return ar if is_ar() else en

_LAB_AR = {"low": "منخفض", "moderate": "متوسط", "medium": "متوسط", "high": "مرتفع", "very_high": "مرتفع جداً",
           "compliant": "مطابق للحد", "elevated": "أعلى من الحد قليلاً", "severe": "شديد"}


def lab(x):
    return _LAB_AR.get(x, x) if is_ar() else str(x).replace("_", " ").title()


def two_axis(idx, cn, hg):
    """محور الهشاشة (DRASTIC) + محور الخطر (تركيز/حد) + مصفوفة المخاطر. لا يخلط التركيز بالهشاشة."""
    L = dc.LIMITS_MG_L[at.STANDARD]
    hq = max(cn / L["cn"] if L["cn"] else 0.0, hg / L["hg"])
    v, vp = dc.vulnerability_class(idx)
    h = dc.hazard_class(hq)
    return {"vuln": v, "vuln_pct": vp, "hazard": h, "max_hq": round(hq, 1), "risk": dc.risk_category(v, h)}


def show_two_axis(idx, cn, hg):
    ta = two_axis(idx, cn, hg)
    k1, k2, k3 = st.columns(3)
    k1.metric(tx("الهشاشة (DRASTIC)", "Vulnerability (DRASTIC)"), f"{lab(ta['vuln'])} ({ta['vuln_pct']}%)")
    k2.metric(tx("الخطر (التركيز ÷ الحد)", "Hazard (conc ÷ limit)"), f"{lab(ta['hazard'])} (HQ={ta['max_hq']})")
    k3.metric(tx("فئة المخاطر المركّبة", "Combined risk"), lab(ta["risk"]))
    st.caption(tx(f"الحدود: EU Directive 98/83/EC ({at.STANDARD}) — السيانيد 0.05 و الزئبق 0.001 mg/L. الفئات اصطلاحية وليست من Aller 1987.",
                  f"Limits: EU Directive 98/83/EC ({at.STANDARD}) — CN 0.05, Hg 0.001 mg/L. Classes are conventions, not from Aller 1987."))
    return ta


if MODE_KEY == "system":
    tabs = st.tabs([
        t("tab_input"), t("tab_manual"), t("tab_bulk"), t("tab_solutions"), t("tab_report"), t("tab_heatmap"),
        t("tab_sensitivity"), t("tab_toxicity"), t("tab_gis"), t("tab_monte_carlo"), t("tab_advanced"),
        t("tab_development"), t("tab_auto_maps"), t("tab_calibration"), t("tab_threshold"),
        "⚙️ Profiles", "🔬 External Validation", "🗺️ GIS Raster", "🌐 Live Data", "💧 حارس المياه"])

    # ------------------------------------------------------------- 0: اختيار موقع
    with tabs[0]:
        st.markdown(f'<div class="section-header"><h3>{t("site_selection")}</h3></div>', unsafe_allow_html=True)
        if not DS_OK:
            st.error("data_sources.py")
        else:
            c1, c2 = st.columns([1, 2])
            with c1:
                state = st.selectbox(t("state"), get_states_list(), key="tab0_state_select")
            with c2:
                st.markdown(f'<div class="info-card" style="margin-top:28px;"><div style="font-size:0.9em;color:#5c2c16;">{STATES_DATABASE[state]["description"]}</div></div>', unsafe_allow_html=True)
            site_key = st.selectbox(t("site"), get_sites_list(state), key="tab0_site_select")
            site_data = get_site_data(state, site_key)
            is_est = "تقديرات" in str(site_data.get("source", ""))
            mt_key = site_data.get("mining_type", SCOPE_KEY if SCOPE_KEY != "all" else "traditional")
            if mt_key not in ("industrial", "traditional", "mixed"):
                mt_key = "traditional"
            badge_class = {"industrial": "mining-industrial", "mixed": "mining-mixed"}.get(mt_key, "mining-traditional")
            st.markdown(f'<div class="mining-badge {badge_class}">{mt_label(mt_key)}</div>', unsafe_allow_html=True)
            st.session_state.update({"mining_type": mt_key, "current_site_key": site_key,
                                     "current_site_data": site_data, "current_state": state})
            if is_est or not site_data.get("verified", False):
                st.warning(tx("⚠️ بيانات تقديرية/غير موثَّقة: للعرض فقط، لا تُستخدم في المعايرة أو التحقق.",
                              "⚠️ Estimated / unverified data: display only, not used for calibration or validation."))
            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(t("activity"), site_data.get("activity", "N/A"))
            c2.metric(t("season"), site_data.get("season", "N/A"))
            c3.metric(t("site_status"), t("contaminated") if site_data["actual_contaminated"] == 1 else t("clean"))
            c4.metric(t("documentation"), t("verified") if site_data.get("verified", False) else t("display"))
            c1, c2 = st.columns(2)
            with c1:
                st.metric("D - " + t("depth"), f"{site_data['depth_m']} {t('m')}")
                st.metric("R - " + t("recharge"), f"{site_data['recharge_mm']} {t('mm_yr')}")
                st.metric("T - " + t("slope"), f"{site_data['slope_pct']} %")
                st.metric("C - " + t("conductivity"), f"{site_data['conductivity']} {t('m_day')}")
            with c2:
                st.metric("A - " + t("aquifer"), AQ(site_data["aquifer"]))
                st.metric("S - " + t("soil"), SL(site_data["soil"]))
                st.metric("I - " + t("vadose"), VD(site_data["vadose"]))
                st.metric("theta - " + t("porosity"), "0.25")
            c1, c2 = st.columns(2)
            c1.metric("CN", f"{site_data['cn_water_mg_l']} mg/L")
            c2.metric("Hg", f"{site_data['hg_water_mg_l']} mg/L")
            _L = dc.LIMITS_MG_L[at.STANDARD]
            st.caption(f"{t('limits')}: CN = {_L['cn']} mg/L | Hg = {_L['hg']} mg/L ({at.STANDARD})")
            for _w in dc.check_units(site_data["cn_water_mg_l"], site_data["hg_water_mg_l"]):
                st.warning(_w)
            try:
                idx = row_drastic(site_data)
                risk = classify(idx)
                st.session_state["ci"] = idx
                st.session_state["cv"] = {"depth": site_data["depth_m"], "recharge": site_data["recharge_mm"],
                                          "aquifer": site_data["aquifer"], "soil": site_data["soil"],
                                          "slope": site_data["slope_pct"], "vadose": site_data["vadose"],
                                          "conductivity": site_data["conductivity"],
                                          "cn_water_mg_l": site_data["cn_water_mg_l"], "hg_water_mg_l": site_data["hg_water_mg_l"]}
                st.session_state["current_risk"] = risk
                z1, z2, z3 = st.columns(3)
                z1.metric("DRASTIC", f"{idx}/{DRASTIC_MAX}")
                z2.metric(t("level"), t(risk["level"]))
                z3.metric(t("percentage"), f"{round((idx - 23) / (DRASTIC_MAX - 23) * 100, 1)}%")
                {"red": st.error, "orange": st.warning, "yellow": st.info}.get(risk["color"], st.success)(t(risk["action"]))
                st.markdown("---")
                st.markdown(f"#### {tx('تقييم من محورين (مُوصى به)', 'Two-axis assessment (recommended)')}")
                show_two_axis(idx, site_data["cn_water_mg_l"], site_data["hg_water_mg_l"])
                dt_result = calc_drastic_t(idx, site_data["cn_water_mg_l"], site_data["hg_water_mg_l"],
                                           mining_type=mt_key, **tox_kw(mt_key))
                if tox_kw(mt_key):
                    st.caption(t("using_calibrated"))
                st.markdown("---")
                st.markdown(f"#### {t('drastic_tox')} — {tx('تجريبي', 'experimental')}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric(t("drastic_tox"), f"{dt_result['drastic_t']}", delta=f"+{dt_result['increase_pct']}%")
                m2.metric(t("bonus"), dt_result["toxicity_bonus"])
                m3.metric("α (CN)", dt_result["alpha"])
                m4.metric("β (Hg)", dt_result["beta"])
                st.caption(tx("المدى النظري 23–276 بأوزان متساوية. الإضافة صيغة مقترحة غير مُتحقَّق منها خارجياً.",
                              "Theoretical range 23–276 with equal weights. The bonus is a proposed, externally unvalidated formulation."))
                with st.expander(t("calculation_details")):
                    d1, d2, d3, d4 = st.columns(4)
                    d1.metric(t("cn_score"), dt_result["cn_score"]); d2.metric(t("hg_score"), dt_result["hg_score"])
                    d3.metric(t("base_bonus"), dt_result["base_bonus"]); d4.metric(t("source_factor"), dt_result["source_factor"])
                st.markdown("---")
                st.download_button("📄 " + t("tab_report") + " (HTML)", key="download_report_btn", mime="text/html",
                                   file_name=f"report_{site_key}.html",
                                   data=generate_html_report(
                                       site_info={"name": site_data.get("name_ar", site_key), "state": state},
                                       drastic=idx, drastic_t=dt_result["drastic_t"], level=t(risk["level"]),
                                       recommendation=t(risk["action"])).encode("utf-8"))
            except ValueError as e:
                st.error(str(e))

    # ------------------------------------------------------------- 1: إدخال يدوي
    with tabs[1]:
        st.markdown(f'<div class="section-header"><h3>{t("tab_manual")}</h3></div>', unsafe_allow_html=True)
        st.info(tx("المواقع اليدوية تُحفظ في ذاكرة الخادم فقط (تظهر لكل المستخدمين وتُمحى عند إعادة التشغيل) وتُوسَم غير موثَّقة.",
                   "Manual sites live in server memory only (visible to all users, wiped on restart) and are flagged unverified."))
        c1, c2 = st.columns(2)
        with c1:
            new_state = st.text_input(t("state"), value="Sennar", key="new_state_input")
            new_site_key = st.text_input(t("site"), value="New_Site", key="new_site_input")
            new_lat = st.number_input("Lat:", value=13.55, key="new_lat_input")
            new_lon = st.number_input("Lon:", value=33.60, key="new_lon_input")
            new_depth = st.number_input("D (m):", 0.5, 100.0, 15.0, key="new_depth_input")
            new_recharge = st.number_input("R (mm/yr):", 0.0, 400.0, 20.0, key="new_recharge_input")
        with c2:
            new_slope = st.number_input("T (%):", 0.0, 30.0, 3.0, key="new_slope_input")
            new_conductivity = st.number_input("C (m/d):", 0.01, 200.0, 3.0, key="new_conductivity_input")
            new_aquifer = st.selectbox("A:", VALID_AQUIFERS, key="new_aquifer_select")
            new_soil = st.selectbox("S:", VALID_SOILS, key="new_soil_select")
            new_vadose = st.selectbox("I:", VALID_VADOSE, key="new_vadose_select")
        c1, c2, c3 = st.columns(3)
        with c1: new_cn = st.number_input("CN (mg/L):", 0.0, 10.0, 0.010, format="%.4f", key="new_cn_input")
        with c2: new_hg = st.number_input("Hg (mg/L):", 0.0, 10.0, 0.001, format="%.5f", key="new_hg_input")
        with c3: new_cont = st.selectbox(t("site_status"), [t("clean") + " (0)", t("contaminated") + " (1)"], key="new_cont_select")
        if st.button("💾 " + t("save"), type="primary", key="save_manual_site_btn"):
            try:
                if not DS_OK:
                    raise ValueError("data_sources.py")
                add_new_site(new_state, new_site_key, {
                    "name_ar": new_site_key, "coords": (new_lat, new_lon), "depth_m": new_depth, "recharge_mm": new_recharge,
                    "slope_pct": new_slope, "conductivity": new_conductivity, "aquifer": new_aquifer, "soil": new_soil,
                    "vadose": new_vadose, "cn_water_mg_l": new_cn, "hg_water_mg_l": new_hg,
                    "actual_contaminated": 1 if "1" in new_cont else 0, "season": "-", "activity": "Manual"})
                st.success(t("success")); st.rerun()
            except ValueError as e:
                st.error(str(e))

    # ------------------------------------------------------------- 2: تقييم جماعي
    with tabs[2]:
        st.markdown(f'<div class="section-header"><h3>{t("bulk_assessment")}</h3></div>', unsafe_allow_html=True)
        df_bulk = get_loaded_df("df_bulk", "df_validation")
        if df_bulk is None:
            st.warning(t("no_file"))
        else:
            try:
                st.dataframe(df_bulk.head(10), use_container_width=True)
                _mt = st.session_state.get("mining_type", "traditional")
                c1, c2 = st.columns(2)
                with c1: th_d = st.number_input(t("drastic_threshold"), 50, 200, 140, 5, key="bulk_th_d_input")
                with c2: th_dt = st.number_input(t("drastic_tox_threshold"), 50, 280, int(DEFAULT_TOX_THRESHOLD), 5, key="bulk_th_dt_input")
                has_tox = "cn_water_mg_l" in df_bulk.columns and "hg_water_mg_l" in df_bulk.columns
                scored, errs = add_indices(df_bulk, _mt)
                name_col = "name" if "name" in scored.columns else ("site_name" if "site_name" in scored.columns else None)
                df_results = pd.DataFrame({
                    "Site": scored[name_col] if name_col else [f"R{i + 1}" for i in range(len(scored))],
                    "DRASTIC": scored["DRASTIC"], "DRASTIC-Tox": scored["DRASTIC_Tox"],
                    "Status": np.where(scored["DRASTIC_Tox"].isna(), "ERR", np.where(scored["DRASTIC_Tox"] >= th_dt, "HIGH", "LOW"))})
                st.dataframe(df_results, use_container_width=True)
                for e in errs[:10]:
                    st.error(tx("خطأ في الصف ", "Row error ") + e)
                ok = scored.dropna(subset=["DRASTIC", "DRASTIC_Tox"])
                if has_tox and "actual_contaminated" in ok.columns and ok["actual_contaminated"].nunique() == 2 and ADV_OK:
                    st.markdown("---")
                    st.caption(tx("مقاييس وصفية على نفس البيانات وبعتبة مُدخلة (غير مُستقلة). للتقدير الصادق استخدم تبويب External Validation.",
                                  "Descriptive metrics on the same data at a typed threshold (not independent). For honest estimates use the External Validation tab."))
                    c1, c2 = st.columns(2)
                    for col, name, vals, th in ((c1, "DRASTIC", ok["DRASTIC"], th_d), (c2, "DRASTIC-Tox", ok["DRASTIC_Tox"], th_dt)):
                        with col:
                            st.markdown(f"**{name}**")
                            m = am.calculate_confusion_matrix(vals.tolist(), ok["actual_contaminated"].astype(int).tolist(), th)
                            st.metric(t("kappa"), m["kappa"]); st.metric(t("recall"), f"{m['recall']}%")
                st.download_button(t("download_results"), data=df_results.to_csv(index=False).encode("utf-8-sig"),
                                   file_name="results.csv", mime="text/csv", key="download_bulk_results_btn")
            except Exception as e:
                st.error(str(e))

    # ------------------------------------------------------------- 3: الحلول
    with tabs[3]:
        st.markdown(f'<div class="section-header"><h3>{t("solutions")}</h3></div>', unsafe_allow_html=True)
        st.warning(tx("⚠️ معاملات التخفيض (HDPE ×0.40، معالجة ×0.60، مراقبة ×0.85) افتراضات توضيحية بلا مصدر.",
                      "⚠️ Reduction factors (HDPE ×0.40, treatment ×0.60, monitoring ×0.85) are illustrative assumptions without a source."))
        if "ci" in st.session_state:
            ci = st.session_state["ci"]
            c1, c2 = st.columns(2)
            with c1:
                h = st.checkbox(t("hdpe_liner"), key="chk_hdpe")
                tr = st.checkbox(t("cyanide_treatment"), key="chk_cyanide")
            with c2:
                mo = st.checkbox(t("monitoring_wells"), key="chk_monitoring")
            if h or tr or mo:
                r = at.mitigate(ci, h, tr, mo)
                c1, c2, c3 = st.columns(3)
                c1.metric(t("before"), ci); c2.metric(t("after"), r["mitigated_index"]); c3.metric(t("reduction"), f"{r['reduction_pct']}%")
        else:
            st.info(t("site_selection"))

    # ------------------------------------------------------------- 4: التقارير
    with tabs[4]:
        st.markdown(f'<div class="section-header"><h3>{t("tab_report")}</h3></div>', unsafe_allow_html=True)
        if "ci" not in st.session_state:
            st.warning(t("site_selection"))
        else:
            cv = st.session_state.get("cv", {})
            mt_key = st.session_state.get("mining_type", "traditional")
            site_key_current = st.session_state.get("current_site_key", "site")
            current_risk = st.session_state.get("current_risk")
            idx = st.session_state["ci"]
            cn, hg = cv.get("cn_water_mg_l", 0), cv.get("hg_water_mg_l", 0)
            c1, c2, c3 = st.columns(3)
            c1.metric("DRASTIC", f"{idx}/{DRASTIC_MAX}"); c2.metric("CN", f"{cn} mg/L"); c3.metric("Hg", f"{hg} mg/L")
            st.markdown("---")
            dt_res = calc_drastic_t(idx, cn, hg, mining_type=mt_key, **tox_kw(mt_key))
            st.dataframe(pd.DataFrame({
                "Metric": ["DRASTIC", "CN_score", "Hg_score", "Base Bonus", "Source Factor", "Final Bonus", "DRASTIC-Tox (experimental)", "Level"],
                "Value": [idx, dt_res["cn_score"], dt_res["hg_score"], dt_res["base_bonus"], dt_res["source_factor"],
                          dt_res["toxicity_bonus"], dt_res["drastic_t"], t(dt_res["level"])]}),
                use_container_width=True, hide_index=True)
            show_two_axis(idx, cn, hg)
            st.markdown("---")
            _site_info = {"name": site_key_current, "state": mt_key, "coords": "Sudan", "depth": cv.get("depth", "N/A"),
                          "recharge": cv.get("recharge", "N/A"), "slope": cv.get("slope", "N/A"),
                          "conductivity": cv.get("conductivity", "N/A"), "cn": cn, "hg": hg}
            c1, c2 = st.columns(2)
            with c1:
                if PDF_OK:
                    try:
                        pdf_bytes = generate_pdf_report(
                            site_info=_site_info, drastic=idx, drastic_t=dt_res["drastic_t"], level=t(dt_res["level"]),
                            recommendation=t(current_risk["action"]) if current_risk else "—",
                            cn_score=dt_res["cn_score"], hg_score=dt_res["hg_score"], base_bonus=dt_res["base_bonus"],
                            source_factor=dt_res["source_factor"], toxicity_bonus=dt_res["toxicity_bonus"], cn_value=cn, hg_value=hg)
                        if pdf_bytes:
                            st.download_button("📄 تحميل PDF", data=pdf_bytes, file_name=f"report_{site_key_current}.pdf",
                                               mime="application/pdf", key="download_pdf_btn")
                        else:
                            st.info("تثبيت fpdf2 مطلوب")
                    except Exception as e:
                        st.warning(f"تعذر PDF: {str(e)[:80]}")
                else:
                    st.info("📄 PDF: يتطلب fpdf2")
            with c2:
                if EXCEL_OK:
                    try:
                        excel_bytes = generate_excel_report(
                            site_info={**_site_info, "aquifer": cv.get("aquifer", "—"), "soil": cv.get("soil", "—"),
                                       "vadose": cv.get("vadose", "—"),
                                       "D_rating": get_d_rating(cv.get("depth", 15)), "R_rating": get_r_rating(cv.get("recharge", 100)),
                                       "A_rating": get_a_rating(cv.get("aquifer", "massive_sandstone")),
                                       "S_rating": get_s_rating(cv.get("soil", "sand")), "T_rating": get_t_rating(cv.get("slope", 4)),
                                       "I_rating": get_i_rating(cv.get("vadose", "sand_gravel")),
                                       "C_rating": get_c_rating(cv.get("conductivity", 5))},
                            drastic_result=dt_res, risk_info=current_risk if current_risk else classify(idx),
                            mining_type=mt_key, spsa_result=st.session_state.get("spsa_result"),
                            mc_result=st.session_state.get("mc_result"))
                        if excel_bytes:
                            st.download_button("📊 تحميل Excel", data=excel_bytes, file_name=f"report_{site_key_current}.xlsx",
                                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                               key="download_excel_btn")
                        else:
                            st.info("openpyxl مطلوب")
                    except Exception as e:
                        st.warning(f"تعذر Excel: {str(e)[:80]}")
                else:
                    st.info("📊 Excel: يتطلب excel_exporter.py")

    # ------------------------------------------------------------- 5: الخريطة الحرارية
    with tabs[5]:
        st.markdown(f'<div class="section-header"><h3>{t("heatmap_title")}</h3></div>', unsafe_allow_html=True)
        st.info(t("shows_verified_only") + f" ({n_sites_verified})")
        st.caption(tx("الطبقة الحرارية للعرض البصري فقط (كثافة النقاط مُوزَّنة بالمؤشر) وليست نموذج استيفاء. للاستيفاء استخدم تبويب GIS Raster.",
                      "The heat layer is a visual aid (point density weighted by the index), not an interpolation model. Use the GIS Raster tab for interpolation."))
        if not DS_OK:
            st.error("data_sources.py")
        else:
            c1, c2 = st.columns(2)
            with c1: mm = st.radio(t("view_mode"), [t("both"), t("markers"), t("heat")], key="map_mode_radio", horizontal=True)
            with c2: mh = st.slider(t("height"), 400, 900, 600, 50, key="map_height_slider")
            with st.spinner(t("calculating")):
                mapa, stats, df_sites = build_heatmap_verified(show_heat=mm in [t("both"), t("heat")],
                                                               show_markers=mm in [t("both"), t("markers")])
            st_folium(mapa, height=mh, key="map_folium_v61", use_container_width=True)
            st.markdown("---")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric(t("low"), stats["low"]); c2.metric(t("medium"), stats["medium"])
            c3.metric(t("high"), stats["high"]); c4.metric(t("very_high"), stats["very_high"]); c5.metric(t("total"), sum(stats.values()))
            st.dataframe(df_sites, use_container_width=True)
            st.download_button(t("download_sites"), data=df_sites.to_csv(index=False).encode("utf-8-sig"),
                               file_name="verified_sites.csv", mime="text/csv", key="download_sites_btn")

    # ------------------------------------------------------------- 6: الحساسية
    with tabs[6]:
        st.markdown(f'<div class="section-header"><h3>{t("sensitivity_title")}</h3></div>', unsafe_allow_html=True)
        st.info(t("sensitivity_hint"))
        if "cv" not in st.session_state:
            st.warning(t("site_selection"))
        else:
            sub_sens = st.tabs([t("spsa_tab"), t("variation_tab")])
            with sub_sens[0]:
                st.markdown(f"#### {t('spsa_title')}")
                st.markdown(f'<div class="research-note"><b>{t("reference")}:</b> Napolitano &amp; Fabbri (1996)<br><b>{t("formula")}:</b> Si = (Wi × Ri / DI) × 100</div>', unsafe_allow_html=True)
                st.info(t("spsa_explanation"))
                if st.button("🚀 " + t("run_spsa"), type="primary", key="run_spsa_btn"):
                    with st.spinner(t("calculating")):
                        st.session_state["spsa_result"] = at.spsa_analysis(st.session_state["cv"])
                if "spsa_result" in st.session_state:
                    spsa = st.session_state["spsa_result"]
                    st.success(f"🏆 {t('most_influential')}: **{spsa['most_influential']}** | {t('base_index')}: **{spsa['base_index']}**")
                    st.dataframe(pd.DataFrame([{t("parameter"): p["param"], t("weight_wi"): p["weight"], t("rating_ri"): p["rating"],
                                                t("weighted"): p["weighted_score"], t("theoretical_pct"): f"{p['theoretical_pct']}%",
                                                t("effective_pct"): f"{p['effective_pct']}%", t("difference"): f"{p['difference']:+.2f}%"}
                                               for p in spsa["parameters"]]), use_container_width=True, hide_index=True)
                    st.caption(tx("الفرق السالب لا يعني أن المعامل «غير مؤثر»، بل أن وزنه الفعلي أقل من النظري عند هذا الموقع.",
                                  "A negative difference does not mean the parameter is unimportant: its effective weight is below the theoretical one at this site."))
                    try:
                        import plotly.graph_objects as go
                        fig = go.Figure()
                        _p = [p["param"] for p in spsa["parameters"]]
                        fig.add_trace(go.Bar(name=t("theoretical_pct"), x=_p, y=[p["theoretical_pct"] for p in spsa["parameters"]], marker_color="#c19a6b"))
                        fig.add_trace(go.Bar(name=t("effective_pct"), x=_p, y=[p["effective_pct"] for p in spsa["parameters"]], marker_color="#5c2c16"))
                        fig.update_layout(barmode="group", height=400, xaxis_title=t("parameter"), yaxis_title="%")
                        st.plotly_chart(fig, use_container_width=True, key="spsa_chart")
                    except Exception:
                        pass
            with sub_sens[1]:
                st.markdown(f"#### {t('variation_title')}")
                st.info(t("variation_explanation"))
                vp = st.slider(t("change_pct"), 5, 30, 10, 5, key="sens_var_pct_slider")
                if st.button("🚀 " + t("run"), type="primary", key="run_sens_btn"):
                    with st.spinner(t("calculating")):
                        st.session_state["sens_result"] = at.sensitivity_analysis(st.session_state["cv"], vp / 100.0)
                if "sens_result" in st.session_state:
                    sens = st.session_state["sens_result"]
                    st.success(f"{t('most_sensitive')}: {sens['most_sensitive']}")
                    st.dataframe(pd.DataFrame([{t("parameter"): p, t("original_value"): d["original_phys"], t("modified_value"): d["modified_phys"],
                                                t("new_index"): d["new_index"], t("change"): d["change"], t("sensitivity_pct"): d["sensitivity"]}
                                               for p, d in sens["parameters"].items()]), use_container_width=True, hide_index=True)

    # ------------------------------------------------------------- 7: السمّية
    with tabs[7]:
        st.markdown(f'<div class="section-header"><h3>{t("toxicity_title")}</h3></div>', unsafe_allow_html=True)
        if "cv" not in st.session_state:
            st.warning(t("site_selection"))
        else:
            cv = st.session_state["cv"]
            hgw, cnw = cv.get("hg_water_mg_l", 0.011), cv.get("cn_water_mg_l", 0.025)
            c1, c2 = st.columns(2)
            c1.metric("CN", f"{cnw} mg/L"); c2.metric("Hg", f"{hgw} mg/L")
            st.caption(tx("حدّ التربة غير مُدرج: لا يوجد في المشروع حدّ تربة بمصدر موثَّق (كان العامل القديم 1.0–1.5 افتراضياً).",
                          "No soil term: the project has no sourced soil limit (the old 1.0–1.5 soil factor was an assumption)."))
            if st.button(t("analyze"), type="primary", key="run_tox_btn"):
                _mt = st.session_state.get("mining_type", "traditional")
                st.session_state["tox_result"] = at.weighted_toxicity(hgw, 0.0, cnw, 0.0, mining_type=_mt, **tox_kw(_mt))
            if "tox_result" in st.session_state:
                tox = st.session_state["tox_result"]
                c1, c2, c3 = st.columns(3)
                c1.metric(t("cn_score"), tox["cn_score"]); c2.metric(t("hg_score"), tox["hg_score"]); c3.metric(t("base_bonus"), tox["base_bonus"])
                c1, c2, c3 = st.columns(3)
                c1.metric(t("source_factor") + " (SF)", tox["source_factor"]); c2.metric("HQ max", tox["max_hq"]); c3.metric(t("category"), t(tox["category"]))
                st.metric(t("action"), t(tox["action"]))
                if "ci" in st.session_state:
                    st.markdown("---")
                    show_two_axis(st.session_state["ci"], cnw, hgw)

    # ------------------------------------------------------------- 8: جدول GIS
    with tabs[8]:
        st.markdown(f'<div class="section-header"><h3>{t("gis_title")}</h3></div>', unsafe_allow_html=True)
        if not DS_OK:
            st.error("data_sources.py")
        else:
            fm = st.radio(t("view_mode"), [t("all"), t("verified_only"), t("display_only_filter")], horizontal=True, key="gis_filter_radio")
            try:
                df_all = get_all_sites_as_dataframe()
                df_show = (df_all[df_all["verified"] == True] if fm == t("verified_only")
                           else df_all[df_all["verified"] == False] if fm == t("display_only_filter") else df_all)
                st.caption(f"{len(df_show)} {t('sites')}")
                st.dataframe(df_show, use_container_width=True)
                st.download_button("📥 CSV", data=df_show.to_csv(index=False).encode("utf-8-sig"), file_name="sites_filtered.csv",
                                   mime="text/csv", key="download_gis_csv_btn")
            except Exception as e:
                st.error(str(e))

    # ------------------------------------------------------------- 9: Monte Carlo
    with tabs[9]:
        st.markdown(f'<div class="section-header"><h3>{t("mc_title")}</h3></div>', unsafe_allow_html=True)
        if "ci" not in st.session_state:
            st.warning(t("site_selection"))
        else:
            ni = st.slider(t("simulations"), 100, 5000, 1000, 100, key="mc_n_iter_slider")
            vp = st.slider(t("variation"), 5, 30, 15, 5, key="mc_var_pct_slider")
            if st.button(t("run"), type="primary", key="run_mc_btn"):
                _mt = st.session_state.get("mining_type", "traditional")
                _cw = CALIBRATED_WEIGHTS if (CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == _mt) else None
                st.session_state["mc_result"] = at.monte_carlo_analysis(st.session_state["cv"], ni, vp / 100.0, mining_type=_mt, calibrated_weights=_cw)
            if "mc_result" in st.session_state:
                mc = st.session_state["mc_result"]
                st.caption(tx("النتيجة تعكس عدم اليقين المفترض في المدخلات (توزيعات اختارها المستخدم) وليس عدم اليقين الميداني.",
                              "The result reflects the ASSUMED input uncertainty (user-chosen distributions), not field uncertainty."))
                st.markdown("#### DRASTIC")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(t("mean"), mc["mean"]); c2.metric(t("std"), mc["std"])
                c3.metric(t("ci_90"), f"{mc['ci_90'][0]}-{mc['ci_90'][1]}"); c4.metric("P>140", f"{mc['prob_over_140']}%")
                st.markdown("#### DRASTIC-Tox")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(t("mean"), mc["tox_mean"]); c2.metric(t("std"), mc["tox_std"])
                c3.metric(t("ci_90"), f"{mc['tox_ci_90'][0]}-{mc['tox_ci_90'][1]}"); c4.metric("P>140", f"{mc['tox_prob_over_140']}%")

    # ------------------------------------------------------------- 10: مقاييس وصفية
    with tabs[10]:
        st.markdown(f'<div class="section-header"><h3>{t("advanced_title")}</h3></div>', unsafe_allow_html=True)
        st.warning(tx("هذه مقاييس وصفية على نفس البيانات وبعتبة مُدخلة: متفائلة. الأرقام الصادقة (leave-one-location-out وفواصل الثقة) في تبويب External Validation.",
                      "These are descriptive metrics on the same data at a typed threshold: optimistic. Honest numbers (leave-one-location-out with CIs) are in the External Validation tab."))
        df_val = st.session_state.get("df_validation")
        if not ADV_OK:
            st.error("advanced_modules.py")
        elif df_val is None:
            st.warning(t("upload_validation_first"))
        elif not ("cn_water_mg_l" in df_val.columns and "hg_water_mg_l" in df_val.columns):
            st.error(t("file_missing_tox"))
        else:
            mt = st.session_state.get("mining_type", "traditional")
            c1, c2 = st.columns(2)
            with c1: th_d = st.number_input("DRASTIC:", 50, 200, 140, 5, key="adv_th_d_input")
            with c2: th_dt = st.number_input("DRASTIC-Tox:", 50, 280, int(DEFAULT_TOX_THRESHOLD), 5, key="adv_th_dt_input")
            scored, errs = add_indices(df_val, mt)
            ok = scored.dropna(subset=["DRASTIC", "DRASTIC_Tox"])
            for e in errs[:10]:
                st.error(tx("خطأ في الصف ", "Row error ") + e)
            if len(ok) == 0 or "actual_contaminated" not in ok.columns or ok["actual_contaminated"].nunique() < 2:
                st.error(t("no_file"))
            elif st.button("🚀 " + t("run"), type="primary", key="run_adv_btn"):
                y = ok["actual_contaminated"].astype(int).tolist()
                st.session_state["adv_results"] = {"d": am.calculate_confusion_matrix(ok["DRASTIC"].tolist(), y, th_d),
                                                   "dt": am.calculate_confusion_matrix(ok["DRASTIC_Tox"].tolist(), y, th_dt)}
            if "adv_results" in st.session_state:
                r = st.session_state["adv_results"]
                c1, c2 = st.columns(2)
                for col, key, name in ((c1, "d", "DRASTIC"), (c2, "dt", "DRASTIC-Tox")):
                    with col:
                        st.markdown(f"#### {name}")
                        m = r[key]
                        st.metric(t("kappa"), m["kappa"]); st.metric("MCC", m["mcc"]); st.metric(t("f1_score"), m["f1_score"])
                        st.metric(t("recall"), f"{m['recall']}%"); st.metric(tx("النوعية", "Specificity"), f"{m['specificity']}%")
                        with st.expander(t("confusion_matrix")):
                            cm = m["confusion_matrix"]
                            st.write(f"TP={cm['TP']} TN={cm['TN']} FP={cm['FP']} FN={cm['FN']}")

    # ------------------------------------------------------------- 11: تطوير النموذج
    with tabs[11]:
        st.markdown(f'<div class="section-header"><h3>{t("development_title")}</h3></div>', unsafe_allow_html=True)
        if not DEV_OK:
            st.error(t("no_dev_module"))
        else:
            sub = st.tabs([t("gray_zone"), t("calibration_ab"), t("model_comparison")])
            with sub[0]:
                st.markdown(f"#### {t('gray_zone')}")
                st.error(tx("⚠️ مواقع اصطناعية (Synthetic) لاختبار البرنامج فقط. أُزيلت من المعايرة والتحقق: تسميات «ملوث/نظيف» فيها مُختلَقة وتتناقض مع تراكيزها.",
                            "⚠️ Synthetic sites for SOFTWARE TESTING only. Removed from calibration and validation: their contaminated/clean labels are invented and contradict their concentrations."))
                if DS_OK:
                    gray_rows = [{"Site": sd.get("name_ar", sk), "D": sd["depth_m"], "R": sd["recharge_mm"], "CN": sd["cn_water_mg_l"],
                                  "Hg": sd["hg_water_mg_l"], "Status": t("contaminated") if sd["actual_contaminated"] == 1 else t("clean")}
                                 for sdata in GRAY_ZONE_SITES.values() for sk, sd in sdata.get("sites", {}).items()]
                    st.dataframe(pd.DataFrame(gray_rows), use_container_width=True, hide_index=True)
                    st.markdown("---")
                    st.caption(tx("مجموعة المعايرة الوحيدة: المواقع الموثَّقة، غير التقديرية، غير الاصطناعية.",
                                  "The ONLY calibration set: verified, non-estimate, non-synthetic sites."))
                    if st.button("🔄 " + t("load_data"), type="primary", key="load_combined_btn"):
                        df_c, _errs = add_indices(get_calibration_dataset(), "traditional")
                        st.session_state["df_combined"] = df_c
                        st.rerun()
                if "df_combined" in st.session_state:
                    df_s = st.session_state["df_combined"]
                    st.dataframe(df_s, use_container_width=True)
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(t("total_sites"), len(df_s))
                    c2.metric(tx("مواقع مستقلة", "Independent locations"), df_s["location_id"].nunique() if "location_id" in df_s.columns else len(df_s))
                    c3.metric(t("verified_sites"), safe_sum(df_s, "verified", 0))
                    c4.metric(t("contaminated_sites"), safe_sum(df_s, "actual_contaminated", 0))
            with sub[1]:
                st.markdown(f"#### {t('calibration_ab')}")
                df_c = get_loaded_df("df_combined", "df_validation")
                if df_c is None:
                    st.warning(t("calibrate_hint"))
                else:
                    c1, c2 = st.columns(2)
                    with c1:
                        amin = st.slider(t("alpha_min"), 0.0, 1.0, 0.1, 0.1, key="cal_a_min_slider")
                        amax = st.slider(t("alpha_max"), 0.0, 1.0, 1.0, 0.1, key="cal_a_max_slider")
                    with c2:
                        bmin = st.slider(t("beta_min"), 0.0, 1.0, 0.1, 0.1, key="cal_b_min_slider")
                        bmax = st.slider(t("beta_max"), 0.0, 1.0, 1.0, 0.1, key="cal_b_max_slider")
                    if st.button("🚀 " + t("run_calibration"), type="primary", key="run_cal_btn"):
                        with st.spinner(t("searching")):
                            st.session_state["cal_result"] = md.calibrate_alpha_beta(
                                df_c, {}, alpha_range=[round(float(v), 2) for v in np.arange(amin, amax + 0.05, 0.1)],
                                beta_range=[round(float(v), 2) for v in np.arange(bmin, bmax + 0.05, 0.1)])
                    if "cal_result" in st.session_state:
                        res = st.session_state["cal_result"]
                        if "error" in res:
                            st.error(res["error"])
                        else:
                            c1, c2 = st.columns(2)
                            for col, key, title in ((c1, "best_kappa", t("best_kappa")), (c2, "best_balanced", t("balanced"))):
                                with col:
                                    st.markdown(f"#### {title}")
                                    b = res[key]
                                    st.metric("alpha", b["alpha"]); st.metric("beta", b["beta"])
                                    st.metric(t("kappa"), b["kappa"]); st.metric(t("recall"), f"{b['recall']}%")
                            if res.get("note"):
                                st.caption(res["note"])
            with sub[2]:
                st.markdown(f"#### {t('model_comparison')}")
                df_c = get_loaded_df("df_combined", "df_validation")
                if df_c is None:
                    st.warning(t("calibrate_hint"))
                else:
                    if st.button("🚀 " + t("run"), type="primary", key="run_cmp_btn"):
                        with st.spinner(t("calculating")):
                            st.session_state["cmp_results"] = md.compare_models(
                                df_c, (get_d_rating, get_r_rating, get_a_rating, get_s_rating, get_t_rating, get_i_rating, get_c_rating), calc_index)
                    if "cmp_results" in st.session_state:
                        rows = [{"Model": mn, t("kappa"): m["kappa"], t("recall"): m["recall"], t("precision"): m["precision"],
                                 t("accuracy"): m["accuracy"], "ROC-AUC": m["auc"]}
                                for mn, m in st.session_state["cmp_results"].items() if isinstance(m, dict) and "kappa" in m]
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                        st.caption(tx("كل نموذج يُقيَّم خارج الموقع (leave-one-location-out) بعتبة تُحسب داخل الطيّة. نموذج «CN + Hg فقط» خط أساس: إن تفوّق على DRASTIC فالتسمية مرتبطة بالتراكيز لا بالهشاشة.",
                                      "Each model is scored out-of-location (leave-one-location-out) with a threshold fitted in-fold. The 'CN + Hg only' model is a baseline: if it beats DRASTIC, the label follows concentrations, not vulnerability."))

    # ------------------------------------------------------------- 12: خرائط تلقائية
    with tabs[12]:
        st.markdown(f'<div class="section-header"><h3>{t("tab_auto_maps")}</h3></div>', unsafe_allow_html=True)
        if not MAPS_OK:
            st.error("auto_maps.py")
        else:
            df_s = get_loaded_df("df_combined", "df_validation")
            if df_s is None:
                st.warning(t("no_file"))
            else:
                if st.button("🎨 " + t("run"), type="primary", key="gen_maps_btn"):
                    with st.spinner(t("calculating")):
                        try:
                            df_m, _errs = add_indices(df_s, "traditional")
                            df_m = df_m.dropna(subset=["DRASTIC", "DRASTIC_Tox"])
                            if "coords" in df_m.columns and "lon" not in df_m.columns:
                                df_m["lat"] = df_m["coords"].apply(lambda c: c[0] if isinstance(c, (tuple, list)) and len(c) >= 2 else None)
                                df_m["lon"] = df_m["coords"].apply(lambda c: c[1] if isinstance(c, (tuple, list)) and len(c) >= 2 else None)
                            df_m = df_m.rename(columns={"cn_water_mg_l": "CN", "hg_water_mg_l": "Hg"})
                            df_p = prepare_df_for_maps(df_m, (get_d_rating, get_r_rating, get_a_rating, get_s_rating, get_t_rating, get_i_rating, get_c_rating))
                            st.session_state["auto_maps_fig"] = generate_auto_maps(df_p, show_sudan=True)
                        except Exception as e:
                            st.error(str(e))
                if "auto_maps_fig" in st.session_state:
                    st.plotly_chart(st.session_state["auto_maps_fig"], use_container_width=True, key="auto_maps_chart_v61")
                    st.download_button("📥 HTML", data=st.session_state["auto_maps_fig"].to_html(include_plotlyjs="cdn").encode("utf-8"),
                                       file_name="auto_maps.html", mime="text/html", key="download_maps_html_btn")

    # ------------------------------------------------------------- 13: المعايرة التلقائية
    with tabs[13]:
        st.markdown(f'<div class="section-header"><h3>{t("auto_calibration")}</h3></div>', unsafe_allow_html=True)
        if not AUTOCAL_OK:
            st.error("auto_calibration.py")
        else:
            if SCOPE_KEY == "industrial" and INDUSTRIAL_SITES:
                df_c = pd.DataFrame(INDUSTRIAL_SITES)
            else:
                df_c = get_loaded_df("df_validation", "df_bulk", "df_combined")
                if df_c is None and DS_OK:
                    df_c = get_calibration_dataset()
                    st.info(tx("لم يُرفع ملف: تُستخدم مجموعة المعايرة الموثَّقة من قاعدة البيانات.",
                               "No file uploaded: using the verified calibration set from the database."))
            req = ["depth_m", "recharge_mm", "slope_pct", "conductivity", "aquifer", "soil", "vadose",
                   "cn_water_mg_l", "hg_water_mg_l", "actual_contaminated"]
            miss = [x for x in req if df_c is None or x not in df_c.columns]
            if df_c is None:
                st.warning(t("upload_validation_first"))
            elif miss:
                st.error(f"Missing: {miss}")
            else:
                st.success(f"{t('file_has')} {len(df_c)} {t('sites')}")
                st.warning(tx("⚠️ مع عدد مواقع صغير تُعتبر الأوزان المعايَرة استكشافية. الرقم المعروض هو تقدير leave-one-location-out وليس kappa التدريب.",
                              "⚠️ With few sites calibrated weights are exploratory. The number shown is a leave-one-location-out estimate, not the training kappa."))
                if WM_OK and detect_ceiling_effect(df_c, SCOPE_KEY if SCOPE_KEY != "all" else "traditional"):
                    st.warning("Ceiling Effect detected — calibrated weights may be unreliable.")
                c1, c2 = st.columns(2)
                with c1: mc = st.selectbox(t("mining_pattern"), ["traditional", "industrial", "mixed"], key="cal_mining_type_select")
                with c2: ns = st.slider(t("search_precision"), 10, 30, 15, 5, key="cal_n_steps_slider")
                b1, b2, b3 = st.columns(3)
                with b1: rc = st.button("🚀 " + t("run_auto_calibration"), type="primary", key="run_auto_cal_btn", use_container_width=True)
                with b2: rcm = st.button("📊 " + t("compare"), key="run_compare_btn", use_container_width=True)
                with b3: rst = st.button("🔄 " + t("reset"), key="reset_weights_btn", use_container_width=True)
                if rst:
                    for k in ["auto_cal_result", "auto_cal_mining_type", "comparison_result"]:
                        st.session_state.pop(k, None)
                    st.success(t("reset_done")); st.rerun()
                if rcm:
                    with st.spinner(t("calculating")):
                        cmp = compare_with_defaults(df_c, mc)
                    st.error(cmp["error"]) if "error" in cmp else st.session_state.__setitem__("comparison_result", cmp)
                if rc:
                    with st.spinner(f"{t('searching')} {ns ** 2:,}..."):
                        result = auto_calibrate_weights(df_c, mc, n_steps=ns)
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.session_state["auto_cal_result"] = result
                        st.session_state["auto_cal_mining_type"] = mc
                        if WM_OK:
                            pk = save_calibrated_profile(mc, result, len(df_c))
                            st.success(f"{t('kappa')} (LOLO) = {result['best_kappa']} — {tx('حُفظ (غير مُفعَّل)', 'Saved (not activated)')}: {pk}")
                if "comparison_result" in st.session_state:
                    cmp = st.session_state["comparison_result"]
                    c1, c2, c3 = st.columns(3)
                    c1.metric(t("default_kappa"), cmp["default_kappa"])
                    c2.metric(t("calibrated_kappa"), cmp["best_kappa"] if cmp.get("best_kappa") is not None else "-",
                              delta=f"{cmp.get('improvement', 0):+.4f}" if cmp.get("best_kappa") is not None else None)
                    c3.metric(t("recall"), f"{cmp.get('best_recall', 0)}%")
                    st.caption(tx("المقارنة بنفس الطريقة لكلا النموذجين (leave-one-location-out، عتبة داخل الطيّة).",
                                  "Both models are evaluated the same way (leave-one-location-out, in-fold threshold)."))
                if "auto_cal_result" in st.session_state:
                    res = st.session_state["auto_cal_result"]
                    interp = res.get("kappa_interpretation", {})
                    st.markdown(f"### {t('result')} - {mt_label(st.session_state.get('auto_cal_mining_type', 'traditional'))}")
                    kc = {"ممتاز": "kappa-excellent", "جيد": "kappa-good", "متوسط": "kappa-moderate", "مقبول": "kappa-fair"}.get(interp.get("level"), "kappa-poor")
                    st.markdown(f'<div class="kappa-box {kc}"><div style="font-size:0.9em;opacity:0.9;">{t("kappa")} (leave-one-location-out)</div>'
                                f'<div style="font-size:3em;font-weight:700;margin:8px 0;">{res["best_kappa"]}</div>'
                                f'<div style="font-size:1.3em;font-weight:600;">{interp.get("level", "-")} - {interp.get("en", "-")}</div></div>', unsafe_allow_html=True)
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("α (CN)", res["best_alpha"]); c2.metric("β (Hg)", res["best_beta"])
                    c3.metric(tx("العتبة المُقدَّرة", "Fitted threshold"), res.get("threshold"))
                    c4.metric(tx("مواقع مستقلة", "Locations"), res.get("n_locations", "-"))
                    c1, c2 = st.columns(2)
                    c1.metric(tx("kappa على بيانات التدريب (متفائل)", "Training kappa (optimistic)"), res.get("resubstitution_kappa"))
                    c2.metric(tx("kappa بتقسيم الصفوف (متسرّب)", "Row-wise kappa (leaky)"), (res.get("cv_naive_leaky") or {}).get("kappa"))
                    for w in res.get("warnings", []):
                        st.warning(w)
                    st.info(tx("لتفعيل الأوزان المحفوظة اذهب إلى تبويب Profiles.", "To activate the saved weights go to the Profiles tab."))

    # ------------------------------------------------------------- 14: العتبة المثلى
    with tabs[14]:
        st.markdown(f'<div class="section-header"><h3>{t("optimal_threshold_title")}</h3></div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="research-note"><b>{t('references')}:</b><br>• Youden (1950)<br>• Landis &amp; Koch (1977)</div>""", unsafe_allow_html=True)
        if not AUTOCAL_OK:
            st.error("auto_calibration.py")
        else:
            if SCOPE_KEY == "industrial" and INDUSTRIAL_SITES:
                df_o = pd.DataFrame(INDUSTRIAL_SITES)
            else:
                df_o = get_loaded_df("df_validation", "df_combined")
                if df_o is None and DS_OK:
                    df_o = get_calibration_dataset()
            if df_o is None:
                st.warning(t("upload_validation_first"))
            else:
                mto = st.selectbox(t("mining_pattern"), ["traditional", "industrial", "mixed"], key="opt_mining_type_select")
                uc = False
                if CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mto:
                    uc = st.checkbox(f"{t('use_calibrated_weights')}", value=True, key="use_calibrated_for_opt_chk")
                if st.button("🚀 " + t("compute_threshold"), type="primary", key="run_opt_threshold_btn"):
                    with st.spinner(t("calculating")):
                        try:
                            st.session_state["opt_threshold_result"] = (
                                find_optimal_threshold(df_o, mto, alpha=CALIBRATED_WEIGHTS["alpha"], beta=CALIBRATED_WEIGHTS["beta"], SF=CALIBRATED_WEIGHTS["SF"])
                                if uc and CALIBRATED_WEIGHTS else find_optimal_threshold(df_o, mto))
                        except Exception as e:
                            st.error(str(e))
                if "opt_threshold_result" in st.session_state:
                    res = st.session_state["opt_threshold_result"]
                    if "error" in res:
                        st.error(res["error"])
                    else:
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric(t("threshold"), res["optimal_threshold"]); c2.metric("Youden J", res["J_max"])
                        c3.metric(t("sensitivity"), res["sensitivity"]); c4.metric(t("specificity"), res["specificity"])
                        st.metric(tx("فاصل ثقة 95% للعتبة (bootstrap)", "Threshold 95% CI (bootstrap)"), str(res.get("threshold_ci_95")))
                        st.caption(res.get("note", ""))

    # ------------------------------------------------------------- 15: ملفات الأوزان
    with tabs[15]:
        st.markdown('<div class="section-header"><h3>⚙️ Weight Profiles Manager</h3></div>', unsafe_allow_html=True)
        if not WM_OK:
            st.error("weight_manager.py not installed")
        else:
            mining_filter = st.radio("Mining Type:", ["traditional", "industrial", "mixed"], format_func=mt_label,
                                     key="profile_filter", horizontal=True)
            profiles = get_all_profiles()
            active = get_active_profile(mining_filter)
            filtered = {k: v for k, v in profiles.items() if v.get("mining_type") == mining_filter}
            stale = get_stale_profiles()
            if stale:
                st.warning(tx(f"تُجوهلت {len(stale)} ملفات محفوظة بصيغة قديمة: {', '.join(stale)}. أعد المعايرة.",
                              f"{len(stale)} profile(s) saved with an older formula were ignored: {', '.join(stale)}. Recalibrate."))
            st.markdown(f"#### Available Profiles: {len(filtered)}")
            st.caption(tx("الملف الافتراضي أوزان متساوية (فرضية صفرية)، وليس نتيجة أدبيات أو بيانات.",
                          "The default profile is equal weights (a null assumption), not a literature or data result."))
            for key, prof in filtered.items():
                is_active = active is not None and prof["alpha"] == active.get("alpha") and prof["beta"] == active.get("beta") and prof["SF"] == active.get("SF")
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"""<div style="background:{'#f1f8e9' if is_active else '#faf8f3'};border:2px solid {'#4caf50' if is_active else '#e0d4b8'};border-radius:10px;padding:16px;margin:8px 0;">
                    <h4 style="color:#5c2c16;margin:0;">{prof.get('name_ar', key)}</h4>
                    <p><b>alpha</b>={prof['alpha']} | <b>beta</b>={prof['beta']} | <b>SF</b>={prof['SF']} | kappa={prof.get('kappa')} | n={prof.get('n_sites')}</p></div>""", unsafe_allow_html=True)
                    for w in prof.get("warnings", []):
                        st.caption("⚠️ " + w)
                with col2:
                    if not is_active:
                        if st.button("Activate", key=f"act_{key}", use_container_width=True):
                            set_active_profile(key); st.success("Activated"); st.rerun()
                    else:
                        st.success("Active")

    # ------------------------------------------------------------- 16: التحقق الخارجي
    with tabs[16]:
        st.markdown('<div class="section-header"><h3>🔬 External / Nested Validation</h3></div>', unsafe_allow_html=True)
        if not EXT_VAL_OK:
            st.error("external_validation.py not installed")
        else:
            df_ext = get_loaded_df("df_validation", "df_combined", "df_bulk")
            if df_ext is None and DS_OK:
                df_ext = get_calibration_dataset()
                st.info(tx("لم يُرفع ملف: تُستخدم مجموعة المعايرة الموثَّقة.", "No file uploaded: using the verified calibration set."))
            req_cols = ["depth_m", "recharge_mm", "slope_pct", "conductivity", "aquifer", "soil", "vadose",
                        "cn_water_mg_l", "hg_water_mg_l", "actual_contaminated"]
            miss = [c for c in req_cols if df_ext is None or c not in df_ext.columns]
            if df_ext is None:
                st.warning("Upload validation file first")
            elif miss:
                st.error(f"Missing: {miss}")
            else:
                st.success(f"Data loaded: {len(df_ext)} sites")
                st.markdown(tx("**المنهج:** leave-one-location-out متداخل — الأوزان والعتبة تُقدَّر على بقية المواقع فقط، وصفوف جاف/رطب لموقع واحد لا تُفصل أبداً.",
                               "**Method:** nested leave-one-location-out — weights and threshold are fitted on the other locations only; Dry/Wet rows of one place are never split."))
                mt_ext = st.selectbox("Mining Type", ["traditional", "industrial", "mixed"], key="ext_mining_type")
                if st.button("🚀 Run Validation", type="primary", key="run_ext_val_btn"):
                    with st.spinner("Running..."):
                        cal_w = CALIBRATED_WEIGHTS if (CALIBRATED_WEIGHTS and CALIBRATED_WEIGHTS.get("mining_type") == mt_ext) else None
                        st.session_state["ext_val_result"] = ev.external_validation_analysis(
                            df_ext, mining_type=mt_ext, calc_index_fn=calc_index, calc_drastic_t_fn=calc_drastic_t,
                            get_d_rating_fn=get_d_rating, get_r_rating_fn=get_r_rating, get_a_rating_fn=get_a_rating,
                            get_s_rating_fn=get_s_rating, get_t_rating_fn=get_t_rating, get_i_rating_fn=get_i_rating,
                            get_c_rating_fn=get_c_rating, calibrated_weights=cal_w, sklearn_ok=True)
                if "ext_val_result" in st.session_state:
                    r = st.session_state["ext_val_result"]
                    if "error" in r:
                        st.error(r["error"])
                    else:
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Rows", r["n_total"]); c2.metric(tx("مواقع مستقلة", "Locations"), r.get("n_locations"))
                        c3.metric(tx("مواقع ملوثة", "Contaminated loc."), r.get("n_pos_locations")); c4.metric(tx("مواقع نظيفة", "Clean loc."), r.get("n_neg_locations"))
                        st.caption(f"{tx('المنهج', 'Scheme')}: {r.get('scheme')}")
                        for w in r.get("warnings", []):
                            st.warning(w)
                        rows = [{"Model": m.get("name", k), "Kappa": m.get("kappa"), "Kappa 95% CI": str(m.get("kappa_ci_95")),
                                 "ROC-AUC": m.get("auc"), "PR-AUC": m.get("pr_auc"), "Recall %": m.get("recall"),
                                 "Specificity %": m.get("specificity"), "Accuracy %": m.get("accuracy")}
                                for k, m in r["models"].items() if isinstance(m, dict) and "kappa" in m]
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                        st.info(tx("قارن DRASTIC بنماذج «التركيز فقط». إن كانت الأخيرة أفضل أو مساوية فإضافة الهيدروجيولوجيا لا تُحسّن التنبؤ بالتسمية الحالية (التسمية مرتبطة بالتراكيز).",
                                   "Compare DRASTIC with the concentration-only models. If those are as good or better, hydrogeology adds nothing to predicting the current labels (the labels follow concentrations)."))
                        if r.get("leaky_row_out_tox_equal"):
                            lk = r["leaky_row_out_tox_equal"]
                            st.caption(f"{tx('للمقارنة: تقسيم الصفوف المتسرّب (لا تستخدمه)', 'For comparison: leaky row-wise split (do not use)')}: kappa={lk.get('kappa')}, AUC={lk.get('auc')}")
                        if r.get("profile_weights_model"):
                            st.caption(f"{tx('الملف المعايَر النشط', 'Active calibrated profile')}: {r['profile_weights_model']}")
                        if r.get("site_table") is not None:
                            with st.expander(tx("جدول التنبؤ لكل موقع", "Per-site predictions")):
                                st.dataframe(r["site_table"], use_container_width=True)
                                st.download_button("📥 CSV", data=r["site_table"].to_csv(index=False).encode("utf-8-sig"),
                                                   file_name="validation_sites.csv", mime="text/csv", key="download_valsites_btn")

    # ------------------------------------------------------------- 17: GIS Raster
    with tabs[17]:
        st.markdown('<div class="section-header"><h3>🗺️ GIS Raster Interpolation</h3></div>', unsafe_allow_html=True)
        if not RASTER_OK:
            st.error("gis_raster.py not installed")
        else:
            st.warning(tx("⚠️ الاستيفاء بين عدد قليل من المواقع تقدير بصري. الخلايا الأبعد من المسافة المحددة عن أقرب عيّنة تُخفى. خرائط DRASTIC الحقيقية تستوفي المعاملات (العمق، التغذية…) من طبقات خام لا قيم المؤشر.",
                          "⚠️ Interpolating between a few sites is a visual estimate. Cells farther than the chosen distance from any sample are hidden. Real DRASTIC maps interpolate the parameters (depth, recharge…) from raw layers, not the index values."))
            df_raster = get_loaded_df("df_combined", "df_validation", "df_bulk")
            if df_raster is None and DS_OK:
                inc_est = st.checkbox(tx("تضمين المواقع التقديرية (للعرض فقط)", "Include estimated sites (display only)"), value=False, key="raster_incl_est")
                df_raster = get_all_sites_as_dataframe() if inc_est else get_calibration_dataset()
            if df_raster is not None and not df_raster.empty:
                df_raster = df_raster.copy()
                if "lat" not in df_raster.columns and "coords" in df_raster.columns:
                    df_raster["lat"] = df_raster["coords"].apply(lambda c: c[0] if isinstance(c, (tuple, list)) and len(c) >= 2 else None)
                    df_raster["lon"] = df_raster["coords"].apply(lambda c: c[1] if isinstance(c, (tuple, list)) and len(c) >= 2 else None)
                if "lat" in df_raster.columns and "lon" in df_raster.columns and not df_raster["lat"].isna().all():
                    st.success(f"Data loaded: {len(df_raster)} sites")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        param_choices = {"DRASTIC-Tox": "DRASTIC_Tox", "DRASTIC": "DRASTIC", "CN (mg/L)": "cn_water_mg_l", "Hg (mg/L)": "hg_water_mg_l",
                                         "Depth (m)": "depth_m", "Recharge (mm/yr)": "recharge_mm", "Conductivity (m/day)": "conductivity"}
                        param_label = st.selectbox("Parameter", list(param_choices.keys()), key="raster_param_select")
                        param_col = param_choices[param_label]
                    with c2: method = st.selectbox("Interpolation", ["IDW", "Kriging"], key="raster_method_select")
                    with c3: resolution = st.slider("Resolution", 30, 200, 80, 10, key="raster_resolution_slider")
                    c1, c2 = st.columns(2)
                    with c1:
                        power = st.slider("IDW Power", 1.0, 5.0, 2.0, 0.5, key="raster_idw_power_slider") if method == "IDW" else 2.0
                        variogram = "linear" if method == "IDW" else st.selectbox("Variogram", ["linear", "power", "gaussian", "spherical", "exponential"], key="raster_variogram_select")
                    with c2:
                        max_km = st.slider(tx("أقصى مسافة عن أقرب عيّنة (كم)", "Max distance from nearest sample (km)"), 25, 500, 150, 25, key="raster_maxdist_slider")
                    _mt_r = st.session_state.get("mining_type", "traditional")
                    scored_r, _errs = add_indices(df_raster, _mt_r) if param_col in ("DRASTIC", "DRASTIC_Tox") and "DRASTIC" not in df_raster.columns else (df_raster, [])
                    if param_col not in scored_r.columns:
                        st.error(f"Column not available: {param_col}")
                        points = []
                    else:
                        sub = scored_r.dropna(subset=["lat", "lon", param_col])
                        points = [(float(a), float(b), float(v)) for a, b, v in zip(sub["lat"], sub["lon"], sub[param_col])]
                    if len(points) >= 3:
                        st.caption(f"Valid points: {len(points)}")
                        if st.button("🎨 Generate Raster", type="primary", key="gen_raster_btn"):
                            with st.spinner(f"Interpolating via {method}..."):
                                result = gr.kriging_interpolation(points, resolution=resolution, variogram_model=variogram, max_distance_km=max_km) if method == "Kriging" else {"error": "idw"}
                                if "error" in result:
                                    if method == "Kriging":
                                        st.info(result["error"])
                                    result = gr.idw_interpolation(points, resolution=resolution, power=power, max_distance_km=max_km)
                                st.session_state["raster_result"] = result
                                st.session_state["raster_points"] = points
                        if "raster_result" in st.session_state:
                            result = st.session_state["raster_result"]
                            if "error" in result:
                                st.error(result["error"])
                            else:
                                for w in result.get("warnings", []):
                                    st.warning(w)
                                stats = gr.compute_raster_statistics(result)
                                c1, c2, c3, c4 = st.columns(4)
                                c1.metric("Min", round(stats["min"], 1)); c2.metric("Mean", round(stats["mean"], 1))
                                c3.metric("Max", round(stats["max"], 1)); c4.metric("Std Dev", round(stats["std"], 2))
                                c1, c2 = st.columns(2)
                                c1.metric(tx("نسبة الخلايا ذات البيانات", "Cells with data"), f"{round(stats.get('valid_cell_fraction', 0) * 100, 1)}%")
                                c2.metric(tx("المساحة المغطاة (كم²)", "Covered area (km²)"), f"{stats['coverage_km2']:,}")
                                fig = gr.create_raster_plotly(result, title=f"{param_label} — {result['method']}", colorscale="RdYlGn_r", points=st.session_state.get("raster_points"))
                                if fig:
                                    st.plotly_chart(fig, use_container_width=True, key="raster_plotly_chart")
                                if param_col in ("DRASTIC", "DRASTIC_Tox"):
                                    st.dataframe(pd.DataFrame(gr.classify_raster(result)).T, use_container_width=True)
                                try:
                                    _tmp = os.path.join(tempfile.gettempdir(), "raster_out.tif")
                                    _ex = gr.export_geotiff(result, _tmp)
                                    if _ex.get("success"):
                                        with open(_tmp, "rb") as fh:
                                            st.download_button("📥 GeoTIFF", data=fh.read(), file_name="raster.tif", mime="image/tiff", key="download_tif_btn")
                                    else:
                                        st.caption(_ex.get("message", ""))
                                except Exception as e:
                                    st.caption(str(e)[:80])

    # ------------------------------------------------------------- 18: بيانات حيّة
    with tabs[18]:
        st.markdown('<div class="section-header"><h3>🌐 Live API Data</h3></div>', unsafe_allow_html=True)
        if not LIVE_API_OK:
            st.error("live_apis.py not installed")
        else:
            use_current = st.checkbox("Use current site coordinates", value=True, key="live_use_current_chk")
            if use_current and "current_site_data" in st.session_state:
                _sd = st.session_state["current_site_data"]
                live_lat, live_lon = float(_sd.get("coords", (15.5, 32.5))[0]), float(_sd.get("coords", (15.5, 32.5))[1])
                st.success(f"Using: **{_sd.get('name_ar', 'Current Site')}** ({live_lat:.4f}, {live_lon:.4f})")
            else:
                c1, c2 = st.columns(2)
                with c1: live_lat = st.number_input("Latitude", -90.0, 90.0, 15.6, 0.01, format="%.4f", key="live_lat_input")
                with c2: live_lon = st.number_input("Longitude", -180.0, 180.0, 32.5, 0.01, format="%.4f", key="live_lon_input")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button("☁️ NASA POWER", type="primary", key="fetch_nasa_btn"):
                    with st.spinner("Fetching..."): st.session_state["live_nasa"] = fetch_nasa_power(live_lat, live_lon, years=3)
            with c2:
                if st.button("🌧️ Open-Meteo", type="primary", key="fetch_meteo_btn"):
                    with st.spinner("Fetching..."): st.session_state["live_meteo"] = fetch_open_meteo_precipitation(live_lat, live_lon, years=5)
            with c3:
                if st.button("⛰️ Elevation", type="primary", key="fetch_elev_btn"):
                    with st.spinner("Fetching..."): st.session_state["live_elev"] = fetch_elevation_grid(live_lat, live_lon, radius_km=5)
            with c4:
                if st.button("🪨 Soil", type="primary", key="fetch_soil_btn"):
                    with st.spinner("Fetching..."): st.session_state["live_soil"] = fetch_soilgrids(live_lat, live_lon)
            for _key, _title, _fields in (
                    ("live_nasa", "☁️ NASA POWER", (("Rainfall", "rainfall_mm_annual", "mm"), ("Temp", "temperature_c", "°C"), ("Humidity", "humidity_pct", "%"), ("Wind", "wind_speed_ms", "m/s"))),
                    ("live_meteo", "🌧️ Open-Meteo", (("Annual Rainfall", "annual_rainfall_mm", "mm"), ("Dry Months", "n_dry_months", "/ 12"), ("Mean Temp", "temperature_mean_c", "°C"))),
                    ("live_elev", "⛰️ Elevation", (("Elevation", "elevation_m", "m"), ("Slope", "slope_pct", "%"), ("Relief", "elevation_range_m", "m"))),
                    ("live_soil", "🪨 SoilGrids", (("Sand", "sand_pct", "%"), ("Clay", "clay_pct", "%"), ("Silt", "silt_pct", "%")))):
                if _key in st.session_state:
                    _r = st.session_state[_key]
                    if "error" in _r:
                        st.error(f"{_title}: {_r['error']}")
                    else:
                        st.markdown(f"#### {_title}")
                        for _col, (_lbl, _f, _u) in zip(st.columns(len(_fields)), _fields):
                            _col.metric(_lbl, f"{_r.get(_f, 'N/A')} {_u}")

    # ------------------------------------------------------------- 19: حارس المياه
    with tabs[19]:
        if WG_OK:
            wg.render()
        else:
            st.error("water_guardian.py not installed")

elif MODE_KEY == "agricultural" and ADV_OK:
    st.markdown(f"""<div class="header-container header-agri"><div class="header-title">{t("agricultural_title")}</div><div class="header-subtitle">Pesticide DRASTIC (Aller 1987) + USSL / FAO 29</div></div>""", unsafe_allow_html=True)
    if DS_OK:
        try:
            ag_s = get_agricultural_data_summary()
            st.info(f"{ag_s['total_states']} / {ag_s['total_sites']}")
            c1, c2 = st.columns([1, 2])
            with c1: ags = st.selectbox(t("state"), get_agri_states_list(), key="agri_state_select")
            with c2: st.markdown(f'<div class="info-card" style="margin-top:28px;">{AGRICULTURAL_DATA[ags]["description"]}</div>', unsafe_allow_html=True)
            agk = st.selectbox(t("site"), get_agri_sites_list(ags), key="agri_site_select")
            agd = get_agri_site_data(ags, agk)
            c1, c2, c3 = st.columns(3)
            c1.metric("Crop", agd.get("crop_type", "N/A")); c2.metric("Irrigation", agd.get("irrigation_method", "N/A")); c3.metric("EC", f"{agd['ec_ds_m']} dS/m")
            sar = am.calculate_sar(agd["na_meq_l"], agd["ca_meq_l"], agd["mg_meq_l"])
            nap = am.calculate_na_percent(agd["na_meq_l"], agd["ca_meq_l"], agd["mg_meq_l"], agd["k_meq_l"])
            ecr = am.calculate_ec_quality(agd["ec_ds_m"])
            ov = am.classify_irrigation_water(sar, nap, ecr)
            c1, c2, c3 = st.columns(3)
            c1.metric("SAR", sar.get("sar", "N/A")); c2.metric("Na%", f"{nap.get('na_percent', 'N/A')}%"); c3.metric("USSL", ov.get("class", "N/A"))
            st.info(f"{ov.get('level')} — {ov.get('action')} | FAO 29: salinity={ov.get('fao_salinity_hazard')}, infiltration={ov.get('fao_infiltration_hazard')}")
            st.markdown("---")
            st.markdown(f"#### {tx('هشاشة المياه الجوفية: Pesticide DRASTIC (المعيار الزراعي)', 'Groundwater vulnerability: Pesticide DRASTIC (agricultural standard)')}")
            _pi = row_pesticide(agd)
            _lo, _hi = dc.index_range(dc.W_PEST)
            vcls, vpct = dc.vulnerability_class(_pi, dc.W_PEST)
            k1, k2 = st.columns(2)
            k1.metric("Pesticide DRASTIC", f"{_pi} ({_lo}–{_hi})"); k2.metric(tx("فئة الهشاشة", "Vulnerability class"), f"{lab(vcls)} ({vpct}%)")
            no3_hq = agd["no3_mg_l"] / am.NO3_LIMIT
            st.metric("NO₃ (mg/L)", f"{agd['no3_mg_l']}  (HQ={round(no3_hq, 2)})")
            st.caption(tx("النترات تُستخدم هنا للعرض فقط. للتحقق من Pesticide DRASTIC قارنه بالنترات في آبار مستقلة ولا تُدخلها في المؤشر.",
                          "Nitrate is shown for context only. To validate Pesticide DRASTIC compare it with nitrate in independent wells; do not put nitrate into the index."))
            if VALIDATOR_OK:
                with st.expander(tx("فحص اتساق البيانات (EC مقابل الأيونات)", "Data consistency (EC vs ions)")):
                    for f in audit_agri_dataset(get_all_agri_sites_as_dataframe()):
                        (st.warning if f["severity"] in ("warning", "error") else st.info)(f["message_ar"] if is_ar() else f["message_en"])
        except Exception as e:
            st.error(str(e))

elif MODE_KEY == "verification" and ADV_OK:
    st.markdown(f'<div class="section-header"><h3>{t("verification_title")}</h3></div>', unsafe_allow_html=True)
    st.warning(tx("وصفي فقط (نفس البيانات، عتبة مُدخلة). التقدير الصادق في تبويب External Validation.", "Descriptive only (same data, typed threshold). Honest estimates: External Validation tab."))
    if DS_OK:
        c1, c2 = st.columns([3, 1])
        with c2:
            if st.button("📥 " + t("load_data"), type="primary", key="load_verified_sites_btn"):
                st.session_state["df_validation"] = get_calibration_dataset(); st.rerun()
        with c1: st.info(f"{n_sites_verified} {t('verified_sites')} / {n_locations_verified} {tx('مواقع مستقلة', 'locations')}")
    df_val = st.session_state.get("df_validation")
    if df_val is None:
        st.warning(t("no_file"))
    elif not ("cn_water_mg_l" in df_val.columns and "hg_water_mg_l" in df_val.columns):
        st.error(t("file_missing_tox"))
    else:
        try:
            st.dataframe(df_val.head(10), use_container_width=True)
            c1, c2 = st.columns(2)
            with c1: th_d = st.number_input("DRASTIC:", 50, 200, 140, 5, key="verify_th_d_input")
            with c2: th_dt = st.number_input("DRASTIC-Tox:", 50, 280, int(DEFAULT_TOX_THRESHOLD), 5, key="verify_th_dt_input")
            scored, errs = add_indices(df_val, st.session_state.get("mining_type", "traditional"))
            ok = scored.dropna(subset=["DRASTIC", "DRASTIC_Tox"])
            for e in errs[:10]: st.error(tx("خطأ في الصف ", "Row error ") + e)
            if "actual_contaminated" in ok.columns and ok["actual_contaminated"].nunique() == 2:
                y = ok["actual_contaminated"].astype(int).tolist()
                c1, c2 = st.columns(2)
                for col, name, vals, th in ((c1, "DRASTIC", ok["DRASTIC"], th_d), (c2, "DRASTIC-Tox", ok["DRASTIC_Tox"], th_dt)):
                    with col:
                        st.markdown(f"#### {name}"); m = am.calculate_confusion_matrix(vals.tolist(), y, th)
                        st.metric(t("kappa"), m["kappa"]); st.metric(t("recall"), f"{m['recall']}%")
        except Exception as e:
            st.error(str(e))

elif MODE_KEY == "transport" and ADV_OK:
    st.markdown(f'<div class="section-header"><h3>{t("transport_title")}</h3></div>', unsafe_allow_html=True)
    if "cv" not in st.session_state:
        st.warning(t("mode_system"))
    else:
        cv = st.session_state["cv"]
        c1, c2 = st.columns(2)
        with c1:
            ic = st.number_input("C0:", 0.001, 10.0, 0.10, 0.001, format="%.4f", key="trans_init_conc")
            ds_m = st.number_input("Distance (m):", 10.0, 5000.0, 500.0, 50.0, key="trans_distance")
        with c2:
            gr_i = st.number_input("Gradient:", 0.0001, 0.5, 0.01, 0.0001, format="%.4f", key="trans_gradient")
            yr = st.slider("Years:", 1, 30, 10, 1, key="trans_years")
        po = st.slider("Porosity:", 0.02, 0.55, 0.25, 0.01, key="trans_porosity")
        kv = st.number_input("K (m/d):", 0.01, 500.0, float(cv.get("conductivity", 3.5)), 0.1, key="trans_k_val")
        di = st.number_input("Dispersivity:", 0.1, 100.0, 10.0, 0.5, key="trans_disper")
        if st.button("🚀 " + t("run"), type="primary", key="run_transport_btn"):
            st.session_state["transport_result"] = at.transport_timeseries(ic, kv, po, gr_i, ds_m, yr, di)
        if "transport_result" in st.session_state:
            tr = st.session_state["transport_result"]
            if "error" in tr: st.error(tr["error"])
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Velocity", f"{tr['v_seepage']:.6f} m/d"); c2.metric("Dispersion", f"{tr['D_dispersion']} m2/d"); c3.metric("Travel Time", f"{tr['t_travel_years']} yr")
                st.caption("Ogata–Banks (1961), 1-D, continuous source, no decay/sorption.")
                st.dataframe(tr["results"], use_container_width=True)
                st.line_chart(tr["results"].set_index("Year")["Concentration"])

elif MODE_KEY == "independent" and ADV_OK:
    st.markdown(f'<div class="section-header"><h3>{t("independent_title")}</h3></div>', unsafe_allow_html=True)
    df_val = st.session_state.get("df_validation")
    if df_val is None:
        st.warning(t("upload_validation_first"))
    else:
        try:
            st.warning(tx("تقسيم طبقي واحد على عدد مواقع صغير: عرض توضيحي لا دليل. استخدم External Validation.", "A single stratified split on few sites: a demonstration, not evidence. Use External Validation."))
            if st.button("🚀 " + t("run"), type="primary", key="run_ind_val_btn"):
                with st.spinner(t("calculating")):
                    df_i, errs = add_indices(df_val, st.session_state.get("mining_type", "traditional"))
                    df_i = df_i.dropna(subset=["DRASTIC"])
                    st.session_state["ind_val_result"] = am.independent_validation(df_i, "DRASTIC", "actual_contaminated", test_size=0.3)
            if "ind_val_result" in st.session_state:
                r = st.session_state["ind_val_result"]
                if "error" in r: st.error(r["error"])
                else:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("alpha", r.get("best_alpha")); c2.metric("beta", r.get("best_beta"))
                    c3.metric(f"{t('kappa')} (Train)", r.get("train_kappa")); c4.metric(f"{t('kappa')} (Test)", r.get("test_kappa"))
                    st.caption(f"n_train={r.get('n_train')} / n_test={r.get('n_test')} — threshold {r.get('threshold')}")
        except Exception as e:
            st.error(str(e))

elif MODE_KEY == "satellite" and ADV_OK:
    st.markdown(f'<div class="section-header"><h3>{t("satellite_title")}</h3></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: lt = st.number_input("Latitude:", -90.0, 90.0, 13.55, 0.01, format="%.4f", key="sat_lat_input")
    with c2: ln = st.number_input("Longitude:", -180.0, 180.0, 33.60, 0.01, format="%.4f", key="sat_lon_input")
    yr = st.slider("Years:", 1, 10, 3, 1, key="sat_years_slider")
    if st.button("🛰️ " + t("run"), type="primary", key="fetch_sat_btn"):
        with st.spinner(t("calculating")):
            try: st.session_state["sat_result"] = am.fetch_satellite_data(lt, ln, yr)
            except Exception as e: st.error(str(e))
    if "sat_result" in st.session_state:
        s = st.session_state["sat_result"]
        if s.get("rainfall_mm") is not None:
            c1, c2, c3 = st.columns(3)
            c1.metric("Rainfall", f"{s['rainfall_mm']} mm/yr"); c2.metric("Temp", f"{s['temperature_c']} C")
            c3.metric("Climate (UNEP P/PET)", f"{s['aridity']} ({s.get('aridity_index')})")
            st.caption(s["source"])
        else:
            st.error(s.get("source", ""))

elif MODE_KEY == "dynamic" and ADV_OK:
    st.markdown(f'<div class="section-header"><h3>{t("dynamic_title")}</h3></div>', unsafe_allow_html=True)
    st.warning(tx("سيناريو توضيحي: معاملات التغير افتراضات بلا معايرة ميدانية.", "Illustrative scenario: change multipliers are assumptions with no field calibration."))
    if "ci" not in st.session_state:
        st.warning(t("mode_system"))
    else:
        c1, c2 = st.columns(2)
        with c1:
            yr = st.slider("Years:", 1, 50, 10, 1, key="dyn_years_slider"); mn = st.slider("Mining:", 0.0, 0.20, 0.05, 0.01, key="dyn_mining_slider")
        with c2:
            cl = st.slider("Climate:", -0.10, 0.05, -0.02, 0.005, key="dyn_climate_slider"); pp = st.slider("Pop:", 0.0, 0.10, 0.03, 0.01, key="dyn_pop_slider")
        cr0 = st.slider("HQ (CN):", 0.0, 10.0, 1.0, 0.1, key="dyn_cri_slider"); mr0 = st.slider("HQ (Hg):", 0.0, 10.0, 0.5, 0.1, key="dyn_mri_slider")
        if st.button("⏳ " + t("run"), type="primary", key="run_dyn_btn"):
            try: st.session_state["dyn"] = am.calculate_dynamic_risk(st.session_state["ci"], yr, mn, cl, pp, cr0, mr0)
            except Exception as e: st.error(str(e))
        if "dyn" in st.session_state and isinstance(st.session_state["dyn"], dict) and "combined" in st.session_state["dyn"]:
            st.dataframe(st.session_state["dyn"]["combined"], use_container_width=True)

elif MODE_KEY == "modflow" and MODFLOW_OK:
    st.markdown(f'<div class="section-header"><h3>{t("modflow_title")}</h3></div>', unsafe_allow_html=True)
    st.warning(tx("نموذج عام غير معاير: صندوق منتظم، K وتغذية ثابتان، حدود ثابتة الضغط. للتوضيح فقط، لا يمثل موقعاً حقيقياً.",
                  "Generic uncalibrated model: regular box, uniform K and recharge, constant-head sides. Illustration only, not a real site."))
    if not shutil.which("mf6"):
        if st.button("⬇️ Install MODFLOW 6", key="install_mf6_btn"):
            with st.spinner("MODFLOW 6..."):
                st.info(setup_modflow())
            st.rerun()
    mok, mmsg = is_modflow_available()
    if not mok:
        st.error(mmsg)
    else:
        st.success(mmsg)
        _cv = st.session_state.get("cv", {})
        _k0 = min(500.0, max(0.01, float(_cv.get("conductivity", 3.5))))
        _r0 = min(500.0, max(0.0, float(_cv.get("recharge", 15.0))))
        if _cv:
            st.caption(tx("القيم الافتراضية لـ K والتغذية مأخوذة من الموقع المختار.", "Default K and recharge come from the selected site."))
        c1, c2 = st.columns(2)
        with c1:
            nl = st.number_input("Layers:", 1, 5, 1, key="mf_nlay_input"); nr = st.number_input("Rows:", 5, 50, 20, key="mf_nrow_input")
            nc = st.number_input("Cols:", 5, 50, 20, key="mf_ncol_input"); dr = st.number_input("Delr (m):", 50.0, 5000.0, 500.0, 50.0, key="mf_delr_input")
        with c2:
            dcc = st.number_input("Delc (m):", 50.0, 5000.0, 500.0, 50.0, key="mf_delc_input"); tp = st.number_input("Top (m):", 100.0, 2000.0, 350.0, 10.0, key="mf_top_input")
            bt = st.number_input("Bottom (m):", 0.0, 1000.0, 250.0, 10.0, key="mf_botm_input"); kv = st.number_input("K (m/d):", 0.01, 500.0, _k0, 0.1, key="mf_k_input")
            rc = st.number_input("Recharge (mm/yr):", 0.0, 500.0, _r0, 1.0, key="mf_rech_input")
        if st.button("🚀 " + t("run"), type="primary", key="run_mf_btn"):
            ws = os.path.join(tempfile.gettempdir(), f"mf_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
            with st.spinner("MODFLOW 6..."):
                st.session_state["mf_res"] = build_and_run_model(workspace=ws, nlay=int(nl), nrow=int(nr), ncol=int(nc), delr=float(dr),
                                                                 delc=float(dcc), top=float(tp), botm=float(bt), k_value=float(kv), recharge_mm=float(rc))
        res = st.session_state.get("mf_res")
        if res is not None:
            if not res.get("success"):
                st.error(res.get("error", "MODFLOW failed"))
                if res.get("hint"):
                    st.info(res["hint"])
                if res.get("lst_content"):
                    with st.expander("mfsim.lst"):
                        st.code(res["lst_content"])
            else:
                for w in res.get("warnings", []):
                    st.warning(w)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Min", f"{res['head_min']:.2f} m"); c2.metric("Max", f"{res['head_max']:.2f} m")
                c3.metric("Mean", f"{res['head_mean']:.2f} m")
                c4.metric(tx("انحراف الميزان", "Budget discrepancy"), "-" if res.get("percent_discrepancy") is None else f"{res['percent_discrepancy']}%")
                try:
                    import plotly.express as px
                    st.plotly_chart(px.imshow(res["heads"], color_continuous_scale="Blues", origin="upper", labels=dict(color="head (m)")),
                                    use_container_width=True, key="mf_heads_chart")
                except Exception:
                    pass
                _tt = estimate_travel_time_modflow(res["heads"], float(kv), 0.25, float(dr), float(dcc))
                if _tt:
                    st.caption(f"{tx('تدرج متوسط', 'Mean gradient')}: {_tt['mean_gradient']} | v = {_tt['velocity_m_year']} m/yr (n=0.25)")

st.markdown("---")
st.markdown(f"""<div style="text-align:center;color:#666;padding:10px;"><b>{t("app_title")} v61</b> - PILOT VERSION<br><span style="font-size:0.85em;">{t("screening_only")}</span></div>""", unsafe_allow_html=True)
