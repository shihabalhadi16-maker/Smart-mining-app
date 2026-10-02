"""قاعدة بيانات المواقع السودانية - نظام التعدين السوداني v49.0
تتضمن:
- 4 ولايات: سنار، كسلا، نهر النيل، الخرطوم
- بيانات ميدانية حقيقية من دراسات محكمة
- قيم CN و Hg من دراسة Elmedani et al. (2025)
- قيم K من دراسات أم درمان والقاش
"""

# ============================================================
# ============ قاعدة بيانات الولايات السودانية ============
# ============================================================
STATES_DATABASE = {
    "سنار": {
        "description": "ولاية سنار - منطقة تعدين أهلي نشطة",
        "source": "Elmedani et al. (2025)",
        "sites": {
            "Ghaat_Haffer_Dry": {
                "name_ar": "حفير القلعاط - موسم جاف",
                "coords": (13.55, 33.60),
                "depth_m": 12.0,
                "recharge_mm": 20.0,
                "slope_pct": 3.0,
                "conductivity": 2.5,
                "aquifer": "massive_sandstone",
                "soil": "sand",
                "vadose": "sand_gravel",
                "cn_water_mg_l": 0.025,
                "hg_water_mg_l": 0.011,
                "actual_contaminated": 1,
                "season": "جاف",
                "activity": "تعدين أهلي"
            },
            "Ghaat_Haffer_Wet": {
                "name_ar": "حفير القلعاط - موسم رطب",
                "coords": (13.55, 33.60),
                "depth_m": 12.0,
                "recharge_mm": 20.0,
                "slope_pct": 3.0,
                "conductivity": 2.5,
                "aquifer": "massive_sandstone",
                "soil": "sand",
                "vadose": "sand_gravel",
                "cn_water_mg_l": 0.350,
                "hg_water_mg_l": 0.360,
                "actual_contaminated": 1,
                "season": "رطب",
                "activity": "تعدين أهلي"
            },
            "Gabis_Haffer_Dry": {
                "name_ar": "حفير جبس - موسم جاف",
                "coords": (13.50, 33.55),
                "depth_m": 15.0,
                "recharge_mm": 18.0,
                "slope_pct": 4.0,
                "conductivity": 3.0,
                "aquifer": "sand_and_gravel",
                "soil": "sandy_loam",
                "vadose": "sandstone",
                "cn_water_mg_l": 0.022,
                "hg_water_mg_l": 0.200,
                "actual_contaminated": 1,
                "season": "جاف",
                "activity": "تعدين أهلي"
            },
            "Gabis_Haffer_Wet": {
                "name_ar": "حفير جبس - موسم رطب",
                "coords": (13.50, 33.55),
                "depth_m": 15.0,
                "recharge_mm": 18.0,
                "slope_pct": 4.0,
                "conductivity": 3.0,
                "aquifer": "sand_and_gravel",
                "soil": "sandy_loam",
                "vadose": "sandstone",
                "cn_water_mg_l": 0.200,
                "hg_water_mg_l": 0.530,
                "actual_contaminated": 1,
                "season": "رطب",
                "activity": "تعدين أهلي"
            },
            "Jebel_Moya": {
                "name_ar": "جبل موية - موقع مرجعي",
                "coords": (13.45, 33.50),
                "depth_m": 25.0,
                "recharge_mm": 10.0,
                "slope_pct": 6.0,
                "conductivity": 1.5,
                "aquifer": "massive_shale",
                "soil": "clay_loam",
                "vadose": "silt_clay",
                "cn_water_mg_l": 0.001,
                "hg_water_mg_l": 0.0001,
                "actual_contaminated": 0,
                "season": "جاف",
                "activity": "مرجعي (نظيف)"
            }
        }
    },
    "كسلا": {
        "description": "ولاية كسلا - خزان القاش الجوفي",
        "source": "دراسة القاش (2025)",
        "sites": {
            "Gash_Upstream": {
                "name_ar": "القاش - المنبع",
                "coords": (15.50, 36.45),
                "depth_m": 15.0,
                "recharge_mm": 96.0,
                "slope_pct": 2.0,
                "conductivity": 110.0,
                "aquifer": "sand_and_gravel",
                "soil": "sand",
                "vadose": "sand_gravel",
                "cn_water_mg_l": 0.010,
                "hg_water_mg_l": 0.001,
                "actual_contaminated": 0,
                "season": "-",
                "activity": "زراعة"
            },
            "Gash_Kassala_City": {
                "name_ar": "القاش - مدينة كسلا",
                "coords": (15.45, 36.40),
                "depth_m": 20.0,
                "recharge_mm": 96.0,
                "slope_pct": 3.0,
                "conductivity": 30.0,
                "aquifer": "sand_and_gravel",
                "soil": "sandy_loam",
                "vadose": "sand_gravel",
                "cn_water_mg_l": 0.020,
                "hg_water_mg_l": 0.002,
                "actual_contaminated": 1,
                "season": "-",
                "activity": "تعدين + زراعة"
            },
            "Gash_Downstream": {
                "name_ar": "القاش - المصب",
                "coords": (15.40, 36.35),
                "depth_m": 25.0,
                "recharge_mm": 96.0,
                "slope_pct": 4.0,
                "conductivity": 50.0,
                "aquifer": "sand_and_gravel",
                "soil": "sandy_loam",
                "vadose": "sand_gravel",
                "cn_water_mg_l": 0.015,
                "hg_water_mg_l": 0.0015,
                "actual_contaminated": 0,
                "season": "-",
                "activity": "زراعة"
            }
        }
    },
    "نهر النيل": {
        "description": "ولاية نهر النيل - الحجر الرملي النوبي",
        "source": "Mohammed et al. (2023)",
        "sites": {
            "Berber": {
                "name_ar": "بربر",
                "coords": (18.02, 33.98),
                "depth_m": 18.0,
                "recharge_mm": 15.0,
                "slope_pct": 2.0,
                "conductivity": 5.0,
                "aquifer": "massive_sandstone",
                "soil": "sand",
                "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005,
                "hg_water_mg_l": 0.001,
                "actual_contaminated": 0,
                "season": "-",
                "activity": "زراعة"
            },
            "Abu_Hamad": {
                "name_ar": "أبو حمد",
                "coords": (19.53, 33.32),
                "depth_m": 22.0,
                "recharge_mm": 12.0,
                "slope_pct": 3.0,
                "conductivity": 3.5,
                "aquifer": "massive_sandstone",
                "soil": "sandy_loam",
                "vadose": "sand_gravel",
                "cn_water_mg_l": 0.008,
                "hg_water_mg_l": 0.002,
                "actual_contaminated": 0,
                "season": "-",
                "activity": "زراعة + تعدين"
            },
            "El_Damer": {
                "name_ar": "الدامر",
                "coords": (17.59, 33.96),
                "depth_m": 20.0,
                "recharge_mm": 15.0,
                "slope_pct": 3.0,
                "conductivity": 4.0,
                "aquifer": "massive_sandstone",
                "soil": "sand",
                "vadose": "sand_gravel",
                "cn_water_mg_l": 0.006,
                "hg_water_mg_l": 0.001,
                "actual_contaminated": 0,
                "season": "-",
                "activity": "زراعة"
            }
        }
    },
    "الخرطوم": {
        "description": "ولاية الخرطوم - الحجر الرملي النوبي",
        "source": "Mohammed et al. (2023)",
        "sites": {
            "Omdurman": {
                "name_ar": "أم درمان",
                "coords": (15.65, 32.48),
                "depth_m": 15.0,
                "recharge_mm": 15.0,
                "slope_pct": 4.0,
                "conductivity": 3.3,
                "aquifer": "massive_sandstone",
                "soil": "sand",
                "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005,
                "hg_water_mg_l": 0.001,
                "actual_contaminated": 0,
                "season": "-",
                "activity": "حضري"
            },
            "North_Khartoum": {
                "name_ar": "شمال الخرطوم",
                "coords": (15.75, 32.55),
                "depth_m": 20.0,
                "recharge_mm": 15.0,
                "slope_pct": 3.0,
                "conductivity": 4.85,
                "aquifer": "massive_sandstone",
                "soil": "sand",
                "vadose": "sandstone",
                "cn_water_mg_l": 0.006,
                "hg_water_mg_l": 0.001,
                "actual_contaminated": 0,
                "season": "-",
                "activity": "حضري"
            },
            "East_Nile": {
                "name_ar": "شرق النيل",
                "coords": (15.60, 32.65),
                "depth_m": 18.0,
                "recharge_mm": 15.0,
                "slope_pct": 3.5,
                "conductivity": 4.0,
                "aquifer": "massive_sandstone",
                "soil": "sandy_loam",
                "vadose": "sand_gravel",
                "cn_water_mg_l": 0.007,
                "hg_water_mg_l": 0.0015,
                "actual_contaminated": 0,
                "season": "-",
                "activity": "حضري + صناعي"
            }
        }
    }
}


# ============================================================
# ============ آبار NARIS ============
# ============================================================
NARIS_WELLS = {
    "NARIS_Well_01": {"coords": (15.55, 32.55), "depth": 25.0},
    "NARIS_Well_02": {"coords": (15.60, 32.60), "depth": 30.0},
    "NARIS_Well_03": {"coords": (15.50, 32.50), "depth": 20.0},
    "NARIS_Well_04": {"coords": (15.65, 32.65), "depth": 35.0},
}


# ============================================================
# ============ آبار دارفور ============
# ============================================================
DARFUR_WELLS = {
    "Darfur_Well_01": {"coords": (13.60, 25.30), "depth": 40.0},
    "Darfur_Well_02": {"coords": (13.62, 25.32), "depth": 45.0},
    "Darfur_Well_03": {"coords": (13.55, 25.25), "depth": 35.0},
}


# ============================================================
# ============ مواقع التعدين المعروفة ============
# ============================================================
KNOWN_MINING_SITES = {
    "Ghaat_Haffer": {
        "coords": (13.55, 33.60),
        "activity": "تعدين أهلي",
        "cyanide_use": True,
        "mercury_use": True
    },
    "Gabis_Haffer": {
        "coords": (13.50, 33.55),
        "activity": "تعدين أهلي",
        "cyanide_use": True,
        "mercury_use": True
    },
    "Jebel_Moya": {
        "coords": (13.45, 33.50),
        "activity": "تعدين أهلي",
        "cyanide_use": True,
        "mercury_use": True
    },
    "Kassala_Mining": {
        "coords": (15.45, 36.40),
        "activity": "تعدين صغير",
        "cyanide_use": True,
        "mercury_use": False
    },
    "Berber_Mining": {
        "coords": (18.02, 33.98),
        "activity": "تعدين صغير",
        "cyanide_use": False,
        "mercury_use": True
    },
    "Abu_Hamad_Mining": {
        "coords": (19.53, 33.32),
        "activity": "تعدين صغير",
        "cyanide_use": False,
        "mercury_use": True
    },
    "North_Khartoum_Mining": {
        "coords": (15.75, 32.55),
        "activity": "تعدين صغير",
        "cyanide_use": True,
        "mercury_use": False
    }
}


# ============================================================
# ============ محليات الخرطوم ============
# ============================================================
KHARTOUM_LOCALITIES = {
    "Omdurman": {"coords": (15.65, 32.48), "wells_sampled": 15},
    "Khartoum": {"coords": (15.50, 32.55), "wells_sampled": 20},
    "Bahri": {"coords": (15.60, 32.60), "wells_sampled": 12},
    "East_Nile": {"coords": (15.60, 32.65), "wells_sampled": 10},
    "Jebel_Aulia": {"coords": (15.30, 32.50), "wells_sampled": 8},
    "Karari": {"coords": (15.70, 32.45), "wells_sampled": 6},
    "Um_Badda": {"coords": (15.65, 32.45), "wells_sampled": 5},
}


# ============================================================
# ============ دوال مساعدة ============
# ============================================================
def get_preset_locations_for_app():
    """
    إرجاع قاموس المواقع بصيغة متوافقة مع التطبيق القديم
    (لضمان عدم تعطل الأجزاء الموجودة)
    """
    preset = {}
    for state_name, state_data in STATES_DATABASE.items():
        for site_key, site_data in state_data["sites"].items():
            display_name = f"{state_name} - {site_data['name_ar']}"
            preset[display_name] = {
                "coords": site_data["coords"],
                "depth": site_data["depth_m"],
                "conductivity": site_data["conductivity"],
                "recharge": site_data["recharge_mm"],
                "aquifer": site_data["aquifer"],
                "soil": site_data["soil"],
                "slope": site_data["slope_pct"],
                "vadose": site_data["vadose"],
                "source": state_data["source"],
                "cn_water_mg_l": site_data["cn_water_mg_l"],
                "hg_water_mg_l": site_data["hg_water_mg_l"],
                "actual_contaminated": site_data["actual_contaminated"],
                "season": site_data["season"],
                "activity": site_data["activity"]
            }
    return preset


def get_data_summary():
    """ملخص البيانات المتوفرة"""
    summary = {
        "total_states": len(STATES_DATABASE),
        "total_sites": sum(len(s["sites"]) for s in STATES_DATABASE.values()),
        "states": list(STATES_DATABASE.keys()),
        "sources": list(set(s["source"] for s in STATES_DATABASE.values()))
    }
    return summary


def get_sites_by_state(state_name):
    """إرجاع مواقع ولاية معينة"""
    if state_name in STATES_DATABASE:
        return STATES_DATABASE[state_name]["sites"]
    return {}


def get_site_data(state_name, site_key):
    """إرجاع بيانات موقع محدد"""
    if state_name in STATES_DATABASE:
        sites = STATES_DATABASE[state_name]["sites"]
        if site_key in sites:
            site = sites[site_key].copy()
            site["state"] = state_name
            site["source"] = STATES_DATABASE[state_name]["source"]
            return site
    return None


def get_all_sites_as_dataframe():
    """إرجاع كل المواقع كـ DataFrame جاهز للتحقق الفعلي"""
    import pandas as pd
    rows = []
    for state_name, state_data in STATES_DATABASE.items():
        for site_key, site_data in state_data["sites"].items():
            rows.append({
                "site_name": f"{state_name}-{site_data['name_ar']}",
                "state": state_name,
                "site_key": site_key,
                "depth_m": site_data["depth_m"],
                "recharge_mm": site_data["recharge_mm"],
                "slope_pct": site_data["slope_pct"],
                "conductivity": site_data["conductivity"],
                "aquifer": site_data["aquifer"],
                "soil": site_data["soil"],
                "vadose": site_data["vadose"],
                "cn_water_mg_l": site_data["cn_water_mg_l"],
                "hg_water_mg_l": site_data["hg_water_mg_l"],
                "actual_contaminated": site_data["actual_contaminated"],
                "source": state_data["source"],
                "season": site_data["season"],
                "activity": site_data["activity"]
            })
    return pd.DataFrame(rows)
