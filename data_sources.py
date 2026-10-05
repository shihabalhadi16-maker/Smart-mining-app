"""قاعدة بيانات السودان الكاملة - نظام التعدين السوداني v56.2"""
import pandas as pd

# ============================================================
# الولايات السودانية (18 ولاية)
# ============================================================
STATES_DATABASE = {
    # ============ 1. سنار (موثق - 5 مواقع) ============
    "سنار": {
        "description": "ولاية سنار - منطقة تعدين أهلي نشطة",
        "source": "Elmedani et al. (2025)",
        "sites": {
            "Ghaat_Haffer_Dry": {
                "name_ar": "حفير القلعات - موسم جاف",
                "coords": (13.55, 33.60),
                "depth_m": 12.0, "recharge_mm": 20.0, "slope_pct": 3.0,
                "conductivity": 2.5, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.025, "hg_water_mg_l": 0.011,
                "actual_contaminated": 1, "season": "جاف",
                "activity": "تعدين أهلي", "verified": True,
            },
            "Ghaat_Haffer_Wet": {
                "name_ar": "حفير القلعات - موسم رطب",
                "coords": (13.55, 33.60),
                "depth_m": 12.0, "recharge_mm": 20.0, "slope_pct": 3.0,
                "conductivity": 2.5, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.350, "hg_water_mg_l": 0.36,
                "actual_contaminated": 1, "season": "رطب",
                "activity": "تعدين أهلي", "verified": True,
            },
            "Gabis_Haffer_Dry": {
                "name_ar": "حفير جبس - موسم جاف",
                "coords": (13.50, 33.55),
                "depth_m": 15.0, "recharge_mm": 18.0, "slope_pct": 4.0,
                "conductivity": 3.0, "aquifer": "sand_and_gravel",
                "soil": "sandy_loam", "vadose": "sandstone",
                "cn_water_mg_l": 0.022, "hg_water_mg_l": 0.2,
                "actual_contaminated": 1, "season": "جاف",
                "activity": "تعدين أهلي", "verified": True,
            },
            "Gabis_Haffer_Wet": {
                "name_ar": "حفير جبس - موسم رطب",
                "coords": (13.50, 33.55),
                "depth_m": 15.0, "recharge_mm": 18.0, "slope_pct": 4.0,
                "conductivity": 3.0, "aquifer": "sand_and_gravel",
                "soil": "sandy_loam", "vadose": "sandstone",
                "cn_water_mg_l": 0.200, "hg_water_mg_l": 0.53,
                "actual_contaminated": 1, "season": "رطب",
                "activity": "تعدين أهلي", "verified": True,
            },
            "Jebel_Moya": {
                "name_ar": "جبل موية - موقع مرجعي",
                "coords": (13.45, 33.50),
                "depth_m": 25.0, "recharge_mm": 10.0, "slope_pct": 6.0,
                "conductivity": 1.5, "aquifer": "massive_shale",
                "soil": "clay_loam", "vadose": "silt_clay",
                "cn_water_mg_l": 0.001, "hg_water_mg_l": 0.0001,
                "actual_contaminated": 0, "season": "جاف",
                "activity": "مرجعي (نظيف)", "verified": True,
            },
        }
    },

    # ============ 2. كسلا (للعرض - 3 مواقع) ============
    "كسلا": {
        "description": "ولاية كسلا - خزان القاش الجوفي",
        "source": "دراسة القاش (2025)",
        "sites": {
            "Gash_Upstream": {
                "name_ar": "القاش - المنبع",
                "coords": (15.50, 36.45),
                "depth_m": 15.0, "recharge_mm": 96.0, "slope_pct": 2.0,
                "conductivity": 110.0, "aquifer": "sand_and_gravel",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.010, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-",
                "activity": "زراعة", "verified": False,
            },
            "Gash_Kassala_City": {
                "name_ar": "القاش - مدينة كسلا",
                "coords": (15.45, 36.40),
                "depth_m": 20.0, "recharge_mm": 96.0, "slope_pct": 3.0,
                "conductivity": 30.0, "aquifer": "sand_and_gravel",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.020, "hg_water_mg_l": 0.002,
                "actual_contaminated": 1, "season": "-",
                "activity": "زراعة + تعدين", "verified": False,
            },
            "Gash_Downstream": {
                "name_ar": "القاش - المصب",
                "coords": (15.40, 36.35),
                "depth_m": 25.0, "recharge_mm": 96.0, "slope_pct": 2.0,
                "conductivity": 50.0, "aquifer": "sand_and_gravel",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.015, "hg_water_mg_l": 0.0015,
                "actual_contaminated": 0, "season": "-",
                "activity": "زراعة", "verified": False,
            },
        }
    },

    # ============ 3. نهر النيل (موثق - 3 مواقع) ============
    "نهر النيل": {
        "description": "ولاية نهر النيل - الحجر الرملي النوبي",
        "source": "Mohammed et al. (2023)",
        "sites": {
            "Berber": {
                "name_ar": "بربر",
                "coords": (18.02, 33.98),
                "depth_m": 18.0, "recharge_mm": 15.0, "slope_pct": 4.0,
                "conductivity": 5.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-",
                "activity": "زراعة", "verified": True,
            },
            "Abu_Hamad": {
                "name_ar": "أبو حمد",
                "coords": (19.53, 33.32),
                "depth_m": 22.0, "recharge_mm": 12.0, "slope_pct": 3.0,
                "conductivity": 3.5, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.008, "hg_water_mg_l": 0.002,
                "actual_contaminated": 0, "season": "-",
                "activity": "تعدين + زراعة", "verified": True,
            },
            "El_Damer": {
                "name_ar": "الدamer",
                "coords": (17.59, 33.96),
                "depth_m": 20.0, "recharge_mm": 15.0, "slope_pct": 4.0,
                "conductivity": 4.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.006, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-",
                "activity": "زراعة", "verified": True,
            },
        }
    },

    # ============ 4. الخرطوم (موثق - 3 مواقع) ============
    "الخرطوم": {
        "description": "ولاية الخرطوم - الحجر الرملي النوبي",
        "source": "Mohammed et al. (2023)",
        "sites": {
            "Omdurman": {
                "name_ar": "أم درمان",
                "coords": (15.65, 32.48),
                "depth_m": 15.0, "recharge_mm": 15.0, "slope_pct": 3.0,
                "conductivity": 3.3, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-",
                "activity": "حضري", "verified": True,
            },
            "North_Khartoum": {
                "name_ar": "شمال الخرطوم",
                "coords": (15.75, 32.55),
                "depth_m": 20.0, "recharge_mm": 15.0, "slope_pct": 4.0,
                "conductivity": 4.85, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sandstone",
                "cn_water_mg_l": 0.006, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-",
                "activity": "حضري", "verified": True,
            },
            "East_Nile": {
                "name_ar": "شرق النيل",
                "coords": (15.60, 32.65),
                "depth_m": 18.0, "recharge_mm": 15.0, "slope_pct": 3.0,
                "conductivity": 4.0, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.007, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-",
                "activity": "صناعي + حضري", "verified": True,
            },
        }
    },

    # ============ 5-18. ولايات للعرض فقط ============
    "البحر الأحمر": {
        "description": "ولاية البحر الأحمر - تعدين الذهب",
        "source": "تقديرات عامة",
        "sites": {
            "Port_Sudan": {"name_ar": "بورتسودان", "coords": (19.62, 37.22),
                "depth_m": 25.0, "recharge_mm": 30.0, "slope_pct": 5.0,
                "conductivity": 5.0, "aquifer": "sand_and_gravel",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-", "activity": "تعدين + حضري", "verified": False},
            "Jebel_Alba": {"name_ar": "جبل علبة", "coords": (21.50, 36.50),
                "depth_m": 30.0, "recharge_mm": 20.0, "slope_pct": 8.0,
                "conductivity": 3.0, "aquifer": "metamorphic_igneous",
                "soil": "gravel", "vadose": "metamorphic_igneous",
                "cn_water_mg_l": 0.015, "hg_water_mg_l": 0.005,
                "actual_contaminated": 1, "season": "-", "activity": "تعدين أهلي", "verified": False},
            "Halaib": {"name_ar": "حلايب", "coords": (22.22, 36.65),
                "depth_m": 28.0, "recharge_mm": 25.0, "slope_pct": 6.0,
                "conductivity": 2.5, "aquifer": "metamorphic_igneous",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.010, "hg_water_mg_l": 0.003,
                "actual_contaminated": 1, "season": "-", "activity": "تعدين أهلي", "verified": False},
        }
    },
    "الشمالية": {
        "description": "الولاية الشمالية - تعدين الذهب",
        "source": "تقديرات عامة",
        "sites": {
            "Wadi_Halfa": {"name_ar": "وادي حلفا", "coords": (21.80, 31.35),
                "depth_m": 30.0, "recharge_mm": 10.0, "slope_pct": 3.0,
                "conductivity": 2.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sandstone",
                "cn_water_mg_l": 0.010, "hg_water_mg_l": 0.002,
                "actual_contaminated": 1, "season": "-", "activity": "تعدين أهلي", "verified": False},
            "Dongola": {"name_ar": "دنقلا", "coords": (19.17, 30.47),
                "depth_m": 25.0, "recharge_mm": 12.0, "slope_pct": 2.0,
                "conductivity": 3.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.008, "hg_water_mg_l": 0.001,
                "actual_contaminated": 1, "season": "-", "activity": "تعدين + زراعة", "verified": False},
            "Merowe": {"name_ar": "مروي", "coords": (18.47, 31.82),
                "depth_m": 22.0, "recharge_mm": 12.0, "slope_pct": 3.0,
                "conductivity": 4.0, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.006, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-", "activity": "زراعة", "verified": False},
        }
    },
    "الجزيرة": {
        "description": "ولاية الجزيرة - الزراعة والتعدين",
        "source": "تقديرات عامة",
        "sites": {
            "Wad_Madani": {"name_ar": "ود مدني", "coords": (14.40, 33.52),
                "depth_m": 18.0, "recharge_mm": 20.0, "slope_pct": 2.0,
                "conductivity": 5.0, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-", "activity": "زراعة", "verified": False},
            "Al_Hasaheisa": {"name_ar": "الحصاحيصا", "coords": (14.75, 33.30),
                "depth_m": 20.0, "recharge_mm": 18.0, "slope_pct": 2.0,
                "conductivity": 4.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.006, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-", "activity": "زراعة", "verified": False},
        }
    },
    "القضارف": {
        "description": "ولاية القضارف - الزراعة والتعدين",
        "source": "تقديرات عامة",
        "sites": {
            "Gedaref_City": {"name_ar": "القضارف", "coords": (14.03, 35.38),
                "depth_m": 25.0, "recharge_mm": 40.0, "slope_pct": 4.0,
                "conductivity": 3.0, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-", "activity": "زراعة", "verified": False},
            "Gallabat": {"name_ar": "القلابات", "coords": (12.87, 35.90),
                "depth_m": 22.0, "recharge_mm": 50.0, "slope_pct": 5.0,
                "conductivity": 2.5, "aquifer": "metamorphic_igneous",
                "soil": "sand", "vadose": "metamorphic_igneous",
                "cn_water_mg_l": 0.010, "hg_water_mg_l": 0.002,
                "actual_contaminated": 1, "season": "-", "activity": "تعدين أهلي", "verified": False},
        }
    },
    "النيل الأزرق": {
        "description": "ولاية النيل الأزرق - الزراعة",
        "source": "تقديرات عامة",
        "sites": {
            "Damazin": {"name_ar": "الدمازين", "coords": (11.79, 34.36),
                "depth_m": 20.0, "recharge_mm": 60.0, "slope_pct": 6.0,
                "conductivity": 4.0, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-", "activity": "زراعة", "verified": False},
            "Roseires": {"name_ar": "الروصيرص", "coords": (11.85, 34.38),
                "depth_m": 18.0, "recharge_mm": 65.0, "slope_pct": 5.0,
                "conductivity": 3.5, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.006, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-", "activity": "زراعة", "verified": False},
        }
    },
    "النيل الأبيض": {
        "description": "ولاية النيل الأبيض - الزراعة",
        "source": "تقديرات عامة",
        "sites": {
            "Kosti": {"name_ar": "كوستي", "coords": (13.17, 32.67),
                "depth_m": 18.0, "recharge_mm": 20.0, "slope_pct": 2.0,
                "conductivity": 5.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-", "activity": "زراعة", "verified": False},
            "Rabak": {"name_ar": "ربك", "coords": (13.18, 32.74),
                "depth_m": 20.0, "recharge_mm": 18.0, "slope_pct": 2.0,
                "conductivity": 4.0, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.006, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-", "activity": "صناعة + زراعة", "verified": False},
        }
    },
    "شمال كردفان": {
        "description": "ولاية شمال كردفان - تعدين",
        "source": "تقديرات عامة",
        "sites": {
            "El_Obeid": {"name_ar": "الأبيض", "coords": (13.18, 30.22),
                "depth_m": 30.0, "recharge_mm": 15.0, "slope_pct": 3.0,
                "conductivity": 3.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-", "activity": "تعدين + حضري", "verified": False},
            "Sodari": {"name_ar": "سودري", "coords": (13.50, 29.50),
                "depth_m": 35.0, "recharge_mm": 12.0, "slope_pct": 6.0,
                "conductivity": 2.0, "aquifer": "metamorphic_igneous",
                "soil": "gravel", "vadose": "metamorphic_igneous",
                "cn_water_mg_l": 0.012, "hg_water_mg_l": 0.004,
                "actual_contaminated": 1, "season": "-", "activity": "تعدين أهلي", "verified": False},
        }
    },
    "جنوب كردفان": {
        "description": "ولاية جنوب كردفان - تعدين الذهب",
        "source": "تقديرات عامة",
        "sites": {
            "Kadugli": {"name_ar": "كادوقلي", "coords": (11.01, 29.72),
                "depth_m": 25.0, "recharge_mm": 30.0, "slope_pct": 5.0,
                "conductivity": 3.0, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.010, "hg_water_mg_l": 0.004,
                "actual_contaminated": 1, "season": "-", "activity": "تعدين أهلي", "verified": False},
            "Dilling": {"name_ar": "الدلنج", "coords": (12.05, 29.65),
                "depth_m": 28.0, "recharge_mm": 25.0, "slope_pct": 7.0,
                "conductivity": 2.5, "aquifer": "metamorphic_igneous",
                "soil": "sand", "vadose": "metamorphic_igneous",
                "cn_water_mg_l": 0.012, "hg_water_mg_l": 0.005,
                "actual_contaminated": 1, "season": "-", "activity": "تعدين أهلي", "verified": False},
        }
    },
    "غرب كردفان": {
        "description": "ولاية غرب كردفان - رعوي",
        "source": "تقديرات عامة",
        "sites": {
            "Al_Fula": {"name_ar": "الفولة", "coords": (11.72, 28.35),
                "depth_m": 30.0, "recharge_mm": 35.0, "slope_pct": 4.0,
                "conductivity": 2.0, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.008, "hg_water_mg_l": 0.002,
                "actual_contaminated": 0, "season": "-", "activity": "رعوي", "verified": False},
        }
    },
    "شمال دارفور": {
        "description": "ولاية شمال دارفور - تعدين",
        "source": "UNEP Darfur Reports",
        "sites": {
            "El_Fasher": {"name_ar": "الفاشر", "coords": (13.63, 25.35),
                "depth_m": 35.0, "recharge_mm": 25.0, "slope_pct": 5.0,
                "conductivity": 2.0, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.010, "hg_water_mg_l": 0.003,
                "actual_contaminated": 1, "season": "-", "activity": "تعدين أهلي", "verified": False},
            "Kutum": {"name_ar": "كتم", "coords": (14.20, 24.65),
                "depth_m": 40.0, "recharge_mm": 20.0, "slope_pct": 8.0,
                "conductivity": 1.5, "aquifer": "metamorphic_igneous",
                "soil": "gravel", "vadose": "metamorphic_igneous",
                "cn_water_mg_l": 0.015, "hg_water_mg_l": 0.005,
                "actual_contaminated": 1, "season": "-", "activity": "تعدين أهلي", "verified": False},
        }
    },
    "جنوب دارفور": {
        "description": "ولاية جنوب دارفور - تعدين",
        "source": "UNEP Darfur Reports",
        "sites": {
            "Nyala": {"name_ar": "نيالا", "coords": (12.05, 24.88),
                "depth_m": 30.0, "recharge_mm": 30.0, "slope_pct": 5.0,
                "conductivity": 2.5, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.010, "hg_water_mg_l": 0.002,
                "actual_contaminated": 1, "season": "-", "activity": "حضري + تعدين أهلي", "verified": False},
            "Zalingei": {"name_ar": "زالنجي", "coords": (12.90, 23.47),
                "depth_m": 35.0, "recharge_mm": 28.0, "slope_pct": 9.0,
                "conductivity": 2.0, "aquifer": "metamorphic_igneous",
                "soil": "gravel", "vadose": "metamorphic_igneous",
                "cn_water_mg_l": 0.012, "hg_water_mg_l": 0.003,
                "actual_contaminated": 1, "season": "-", "activity": "تعدين أهلي", "verified": False},
        }
    },
    "غرب دارفور": {
        "description": "ولاية غرب دارفور - تعدين",
        "source": "UNEP Darfur Reports",
        "sites": {
            "El_Geneina": {"name_ar": "الجنينة", "coords": (13.45, 22.45),
                "depth_m": 32.0, "recharge_mm": 32.0, "slope_pct": 7.0,
                "conductivity": 2.5, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.010, "hg_water_mg_l": 0.002,
                "actual_contaminated": 1, "season": "-", "activity": "تعدين أهلي", "verified": False},
        }
    },
    "وسط دارفور": {
        "description": "ولاية وسط دارفور - تعدين",
        "source": "UNEP Darfur Reports",
        "sites": {
            "Zalingei_Central": {"name_ar": "وسط دارفور", "coords": (12.50, 23.50),
                "depth_m": 33.0, "recharge_mm": 30.0, "slope_pct": 8.0,
                "conductivity": 2.0, "aquifer": "metamorphic_igneous",
                "soil": "gravel", "vadose": "metamorphic_igneous",
                "cn_water_mg_l": 0.012, "hg_water_mg_l": 0.003,
                "actual_contaminated": 1, "season": "-", "activity": "تعدين أهلي", "verified": False},
        }
    },
    "شرق دارفور": {
        "description": "ولاية شرق دارفور - رعوي + تعدين",
        "source": "UNEP Darfur Reports",
        "sites": {
            "Ed_Daein": {"name_ar": "الضعين", "coords": (11.45, 26.12),
                "depth_m": 35.0, "recharge_mm": 28.0, "slope_pct": 6.0,
                "conductivity": 2.0, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.010, "hg_water_mg_l": 0.002,
                "actual_contaminated": 1, "season": "-", "activity": "رعوي + تعدين أهلي", "verified": False},
        }
    },
}


# ============================================================
# البيانات الزراعية
# ============================================================
AGRICULTURAL_DATA = {
    "الخرطوم": {
        "description": "بيانات حقيقية من شمال الخرطوم",
        "source": "Mohammed et al. (2023)",
        "sites": {
            "North_Khartoum_Well_1": {
                "name_ar": "شمال الخرطوم - بئر 1",
                "coords": (15.75, 32.55),
                "depth_m": 18.0, "recharge_mm": 15.0, "slope_pct": 4.0,
                "conductivity": 4.85, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sandstone",
                "no3_mg_l": 12.0, "na_meq_l": 1.39, "ca_meq_l": 1.40,
                "mg_meq_l": 0.99, "k_meq_l": 0.064, "ec_ds_m": 0.52,
                "fertilizer_use": 0.5, "land_use_factor": 0.6,
                "crop_type": "خضروات", "irrigation_method": "ري سطحي",
            },
            "North_Khartoum_Well_2": {
                "name_ar": "شمال الخرطوم - بئر 2",
                "coords": (15.76, 32.56),
                "depth_m": 20.0, "recharge_mm": 15.0, "slope_pct": 4.0,
                "conductivity": 4.5, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sandstone",
                "no3_mg_l": 18.0, "na_meq_l": 1.96, "ca_meq_l": 1.75,
                "mg_meq_l": 1.48, "k_meq_l": 0.082, "ec_ds_m": 0.68,
                "fertilizer_use": 0.6, "land_use_factor": 0.7,
                "crop_type": "خضروات، فواكه", "irrigation_method": "ري بالتنقيط",
            },
            "North_Khartoum_Well_3": {
                "name_ar": "شمال الخرطوم - بئر 3",
                "coords": (15.74, 32.54),
                "depth_m": 22.0, "recharge_mm": 15.0, "slope_pct": 3.0,
                "conductivity": 5.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sandstone",
                "no3_mg_l": 8.0, "na_meq_l": 1.22, "ca_meq_l": 1.10,
                "mg_meq_l": 0.82, "k_meq_l": 0.051, "ec_ds_m": 0.45,
                "fertilizer_use": 0.4, "land_use_factor": 0.5,
                "crop_type": "ذرة", "irrigation_method": "ري سطحي",
            },
            "North_Khartoum_Well_4": {
                "name_ar": "شمال الخرطوم - بئر 4",
                "coords": (15.77, 32.57),
                "depth_m": 15.0, "recharge_mm": 15.0, "slope_pct": 5.0,
                "conductivity": 4.0, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sandstone",
                "no3_mg_l": 25.0, "na_meq_l": 2.39, "ca_meq_l": 2.10,
                "mg_meq_l": 1.81, "k_meq_l": 0.102, "ec_ds_m": 0.82,
                "fertilizer_use": 0.7, "land_use_factor": 0.8,
                "crop_type": "خضروات", "irrigation_method": "ري بالتنقيط",
            },
            "North_Khartoum_Well_5": {
                "name_ar": "شمال الخرطوم - بئر 5",
                "coords": (15.73, 32.53),
                "depth_m": 20.0, "recharge_mm": 15.0, "slope_pct": 4.0,
                "conductivity": 4.85, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sandstone",
                "no3_mg_l": 15.0, "na_meq_l": 1.65, "ca_meq_l": 1.50,
                "mg_meq_l": 1.23, "k_meq_l": 0.072, "ec_ds_m": 0.60,
                "fertilizer_use": 0.5, "land_use_factor": 0.6,
                "crop_type": "فواكه", "irrigation_method": "ري سطحي",
            },
        }
    },
    "نهر النيل": {
        "description": "ولاية نهر النيل - زراعة على ضفاف النيل",
        "source": "Mohammed et al. (2023)",
        "sites": {
            "Berber_Agri": {
                "name_ar": "بربر - زراعة", "coords": (18.02, 33.98),
                "depth_m": 18.0, "recharge_mm": 15.0, "slope_pct": 4.0,
                "conductivity": 5.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "no3_mg_l": 22.0, "na_meq_l": 1.52, "ca_meq_l": 1.50,
                "mg_meq_l": 0.62, "k_meq_l": 0.026, "ec_ds_m": 0.50,
                "fertilizer_use": 0.5, "land_use_factor": 0.6,
                "crop_type": "فواكه، تمور", "irrigation_method": "ري غمر",
            },
            "Abu_Hamad_Agri": {
                "name_ar": "أبو حمد - زراعة", "coords": (19.53, 33.32),
                "depth_m": 22.0, "recharge_mm": 12.0, "slope_pct": 3.0,
                "conductivity": 3.5, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "no3_mg_l": 18.0, "na_meq_l": 1.30, "ca_meq_l": 1.75,
                "mg_meq_l": 0.82, "k_meq_l": 0.038, "ec_ds_m": 0.40,
                "fertilizer_use": 0.4, "land_use_factor": 0.5,
                "crop_type": "خضروات", "irrigation_method": "ري سطحي",
            },
        }
    },
    "الجزيرة": {
        "description": "أكبر مشروع زراعي في السودان",
        "source": "دراسات زراعية سودانية",
        "sites": {
            "Wad_Madani_Agri": {
                "name_ar": "ود مدني - مشروع الجزيرة", "coords": (14.40, 33.52),
                "depth_m": 18.0, "recharge_mm": 20.0, "slope_pct": 2.0,
                "conductivity": 5.0, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "no3_mg_l": 35.0, "na_meq_l": 5.0, "ca_meq_l": 3.0,
                "mg_meq_l": 1.5, "k_meq_l": 0.3, "ec_ds_m": 0.8,
                "fertilizer_use": 0.7, "land_use_factor": 0.8,
                "crop_type": "قطن، قمح، فول سوداني", "irrigation_method": "ري سطحي",
            },
            "Al_Hasaheisa_Agri": {
                "name_ar": "الحصاحيصا - الجزيرة", "coords": (14.75, 33.30),
                "depth_m": 20.0, "recharge_mm": 18.0, "slope_pct": 2.0,
                "conductivity": 4.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "no3_mg_l": 28.0, "na_meq_l": 4.0, "ca_meq_l": 3.5,
                "mg_meq_l": 2.0, "k_meq_l": 0.4, "ec_ds_m": 0.6,
                "fertilizer_use": 0.6, "land_use_factor": 0.7,
                "crop_type": "ذرة، قمح", "irrigation_method": "ري سطحي",
            },
        }
    },
    "النيل الأبيض": {
        "description": "ولاية النيل الأبيض - زراعة قصب السكر",
        "source": "دراسات زراعية سودانية",
        "sites": {
            "Kenana_Agri": {
                "name_ar": "كنانة - قصب السكر", "coords": (13.10, 32.85),
                "depth_m": 15.0, "recharge_mm": 22.0, "slope_pct": 2.0,
                "conductivity": 5.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "no3_mg_l": 30.0, "na_meq_l": 4.5, "ca_meq_l": 3.0,
                "mg_meq_l": 2.0, "k_meq_l": 0.3, "ec_ds_m": 0.9,
                "fertilizer_use": 0.6, "land_use_factor": 0.7,
                "crop_type": "قصب السكر", "irrigation_method": "ري سطحي",
            },
        }
    },
}


# ============================================================
# ✅ المواقع الرمادية (Gray Zone) — للاختبار فقط
# ============================================================
# ⚠️ تحذير: هذه المواقع **افتراضية** لاختبار المنهجية
# لا تُستخدم في التحليل الرسمي أو التقارير
# القيم مشتقة من النطاقات الفعلية بين المواقع الموثقة

GRAY_ZONE_SITES = {
    "مواقع رمادية (اختبار)": {
        "description": "⚠️ مواقع افتراضية للاختبار — لا تُستخدم في التقارير الرسمية",
        "source": "Synthetic (Testing Only)",
        "is_gray_zone": True,
        "sites": {
            "GZ-01": {
                "name_ar": "رمادي 1",
                "coords": (13.5, 33.5),
                "depth_m": 16.0, "recharge_mm": 16.0, "slope_pct": 3.5,
                "conductivity": 2.8, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.035, "hg_water_mg_l": 0.007,
                "actual_contaminated": 1, "season": "-",
                "activity": "اختباري", "verified": False,
                "is_gray_zone": True,
            },
            "GZ-02": {
                "name_ar": "رمادي 2",
                "coords": (13.6, 33.4),
                "depth_m": 18.0, "recharge_mm": 15.0, "slope_pct": 4.0,
                "conductivity": 3.2, "aquifer": "sand_and_gravel",
                "soil": "sandy_loam", "vadose": "sandstone",
                "cn_water_mg_l": 0.028, "hg_water_mg_l": 0.005,
                "actual_contaminated": 1, "season": "-",
                "activity": "اختباري", "verified": False,
                "is_gray_zone": True,
            },
            "GZ-03": {
                "name_ar": "رمادي 3",
                "coords": (13.7, 33.3),
                "depth_m": 20.0, "recharge_mm": 14.0, "slope_pct": 4.5,
                "conductivity": 3.5, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.042, "hg_water_mg_l": 0.009,
                "actual_contaminated": 0, "season": "-",
                "activity": "اختباري", "verified": False,
                "is_gray_zone": True,
            },
            "GZ-04": {
                "name_ar": "رمادي 4",
                "coords": (13.4, 33.6),
                "depth_m": 15.0, "recharge_mm": 18.0, "slope_pct": 3.0,
                "conductivity": 2.5, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.030, "hg_water_mg_l": 0.006,
                "actual_contaminated": 0, "season": "-",
                "activity": "اختباري", "verified": False,
                "is_gray_zone": True,
            },
            "GZ-05": {
                "name_ar": "رمادي 5",
                "coords": (13.8, 33.2),
                "depth_m": 22.0, "recharge_mm": 13.0, "slope_pct": 5.0,
                "conductivity": 3.8, "aquifer": "sand_and_gravel",
                "soil": "sand", "vadose": "sandstone",
                "cn_water_mg_l": 0.045, "hg_water_mg_l": 0.010,
                "actual_contaminated": 1, "season": "-",
                "activity": "اختباري", "verified": False,
                "is_gray_zone": True,
            },
            "GZ-06": {
                "name_ar": "رمادي 6",
                "coords": (13.45, 33.55),
                "depth_m": 14.0, "recharge_mm": 17.0, "slope_pct": 3.5,
                "conductivity": 2.7, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.038, "hg_water_mg_l": 0.008,
                "actual_contaminated": 0, "season": "-",
                "activity": "اختباري", "verified": False,
                "is_gray_zone": True,
            },
        }
    },
}


# ============================================================
# بيانات مساعدة
# ============================================================
NARIS_WELLS = {
    "NARIS_Well_01": {"coords": (15.55, 32.55), "depth": 20.0},
    "NARIS_Well_02": {"coords": (15.60, 32.60), "depth": 22.0},
    "NARIS_Well_03": {"coords": (15.50, 32.50), "depth": 18.0},
    "NARIS_Well_04": {"coords": (15.65, 32.65), "depth": 25.0},
}
DARFUR_WELLS = {
    "Darfur_Well_01": {"coords": (13.60, 25.30), "depth": 35.0},
    "Darfur_Well_02": {"coords": (13.62, 25.32), "depth": 38.0},
    "Darfur_Well_03": {"coords": (13.55, 25.25), "depth": 32.0},
}
KNOWN_MINING_SITES = {
    "Ghaat_Haffer": {"coords": (13.55, 33.60), "activity": "تعدين أهلي"},
    "Gabis_Haffer": {"coords": (13.50, 33.55), "activity": "تعدين أهلي"},
    "Kadugli": {"coords": (11.01, 29.72), "activity": "تعدين أهلي"},
    "El_Fasher": {"coords": (13.63, 25.35), "activity": "تعدين أهلي"},
    "Nyala": {"coords": (12.05, 24.88), "activity": "تعدين أهلي"},
    "Kutum": {"coords": (14.20, 24.65), "activity": "تعدين أهلي"},
    "Wadi_Halfa": {"coords": (21.80, 31.35), "activity": "تعدين أهلي"},
    "Dongola": {"coords": (19.17, 30.47), "activity": "تعدين أهلي"},
}
KHARTOUM_LOCALITIES = {
    "Omdurman": {"coords": (15.65, 32.48), "wells_sampled": 15},
    "Khartoum": {"coords": (15.50, 32.55), "wells_sampled": 10},
    "Bahri": {"coords": (15.60, 32.60), "wells_sampled": 12},
    "East_Nile": {"coords": (15.60, 32.65), "wells_sampled": 8},
    "Jebel_Aulia": {"coords": (15.30, 32.50), "wells_sampled": 6},
    "Karari": {"coords": (15.70, 32.45), "wells_sampled": 7},
    "Um_Badda": {"coords": (15.65, 32.45), "wells_sampled": 5},
}


# ============================================================
# الدوال
# ============================================================
def get_preset_locations_for_app():
    """إرجاع قاموس المواقع"""
    preset = {}
    for state_name, state_data in STATES_DATABASE.items():
        for site_key, site_data in state_data["sites"].items():
            display_name = f"{state_name} - {site_data['name_ar']}"
            preset[display_name] = {
                "coords": site_data["coords"],
                "depth": site_data["depth_m"],
                "conductivity": site_data["conductivity"],
                "recharge": site_data["recharge_mm"],
                "verified": site_data.get("verified", False),
            }
    return preset


def get_data_summary():
    """ملخص بيانات التعدين"""
    return {
        "total_states": len(STATES_DATABASE),
        "total_sites": sum(len(s["sites"]) for s in STATES_DATABASE.values()),
        "verified_sites": sum(
            1 for state in STATES_DATABASE.values()
            for site in state["sites"].values()
            if site.get("verified", False)
        ),
        "states": list(STATES_DATABASE.keys()),
    }


def get_sites_by_state(state_name):
    if state_name in STATES_DATABASE:
        return STATES_DATABASE[state_name]["sites"]
    return {}


def get_site_data(state_name, site_key):
    if state_name in STATES_DATABASE:
        sites = STATES_DATABASE[state_name]["sites"]
        if site_key in sites:
            site = sites[site_key].copy()
            site["state"] = state_name
            site["source"] = STATES_DATABASE[state_name]["source"]
            return site
    return None


def add_new_site(state_name, site_key, site_data):
    if state_name not in STATES_DATABASE:
        STATES_DATABASE[state_name] = {
            "description": f"ولاية {state_name}",
            "source": site_data.get("source", "إدخال يدوي"),
            "sites": {}
        }
    STATES_DATABASE[state_name]["sites"][site_key] = site_data
    return True


def get_all_sites_as_dataframe():
    """قاعدة بيانات مواقع التعدين — كل المواقع"""
    rows = []
    for state_name, state_data in STATES_DATABASE.items():
        for site_key, site_data in state_data["sites"].items():
            rows.append({
                "site_name": f"{state_name}-{site_data.get('name_ar', site_key)}",
                "state": state_name,
                "site_key": site_key,
                "depth_m": site_data["depth_m"],
                "recharge_mm": site_data["recharge_mm"],
                "slope_pct": site_data.get("slope_pct", 3.0),
                "conductivity": site_data["conductivity"],
                "aquifer": site_data["aquifer"],
                "soil": site_data["soil"],
                "vadose": site_data["vadose"],
                "cn_water_mg_l": site_data["cn_water_mg_l"],
                "hg_water_mg_l": site_data["hg_water_mg_l"],
                "actual_contaminated": site_data["actual_contaminated"],
                "source": state_data["source"],
                "season": site_data["season"],
                "activity": site_data["activity"],
                "verified": site_data.get("verified", False),
                "is_gray_zone": False,
            })
    return pd.DataFrame(rows)


def get_verified_sites_as_dataframe():
    """المواقع الموثقة فقط"""
    df = get_all_sites_as_dataframe()
    return df[df["verified"] == True].reset_index(drop=True)


def get_all_sites_as_dataframe_with_flag():
    """كل المواقع مع علامة verified"""
    return get_all_sites_as_dataframe()


def get_combined_dataset(include_gray=False):
    """
    قاعدة بيانات موحّدة
    - include_gray=False: الموثقة فقط (11)
    - include_gray=True: الموثقة + الرمادية (17)
    """
    rows = []
    for state_name, state_data in STATES_DATABASE.items():
        for site_key, site_data in state_data.get("sites", {}).items():
            if site_data.get("verified", False):
                rows.append({
                    "site_name": f"{state_name}-{site_data.get('name_ar', site_key)}",
                    "state": state_name, "site_key": site_key,
                    "depth_m": site_data["depth_m"],
                    "recharge_mm": site_data["recharge_mm"],
                    "slope_pct": site_data.get("slope_pct", 3.0),
                    "conductivity": site_data["conductivity"],
                    "aquifer": site_data["aquifer"], "soil": site_data["soil"],
                    "vadose": site_data["vadose"],
                    "cn_water_mg_l": site_data["cn_water_mg_l"],
                    "hg_water_mg_l": site_data["hg_water_mg_l"],
                    "actual_contaminated": site_data["actual_contaminated"],
                    "verified": True, "is_gray_zone": False,
                })
    if include_gray:
        for state_name, state_data in GRAY_ZONE_SITES.items():
            for site_key, site_data in state_data.get("sites", {}).items():
                rows.append({
                    "site_name": f"GZ-{site_data.get('name_ar', site_key)}",
                    "state": state_name, "site_key": site_key,
                    "depth_m": site_data["depth_m"],
                    "recharge_mm": site_data["recharge_mm"],
                    "slope_pct": site_data.get("slope_pct", 3.0),
                    "conductivity": site_data["conductivity"],
                    "aquifer": site_data["aquifer"], "soil": site_data["soil"],
                    "vadose": site_data["vadose"],
                    "cn_water_mg_l": site_data["cn_water_mg_l"],
                    "hg_water_mg_l": site_data["hg_water_mg_l"],
                    "actual_contaminated": site_data["actual_contaminated"],
                    "verified": False, "is_gray_zone": True,
                })
    return pd.DataFrame(rows)


def get_states_list():
    return list(STATES_DATABASE.keys())


def get_sites_list(state_name):
    if state_name in STATES_DATABASE:
        return list(STATES_DATABASE[state_name]["sites"].keys())
    return []


# ============================================================
# دوال الزراعة
# ============================================================
def get_agricultural_data_summary():
    return {
        "total_states": len(AGRICULTURAL_DATA),
        "total_sites": sum(len(s["sites"]) for s in AGRICULTURAL_DATA.values()),
    }


def get_agri_states_list():
    return list(AGRICULTURAL_DATA.keys())


def get_agri_sites_list(agri_state):
    if agri_state in AGRICULTURAL_DATA:
        return list(AGRICULTURAL_DATA[agri_state]["sites"].keys())
    return []


def get_agri_site_data(agri_state, agri_site_key):
    if agri_state in AGRICULTURAL_DATA:
        sites = AGRICULTURAL_DATA[agri_state]["sites"]
        if agri_site_key in sites:
            site = sites[agri_site_key].copy()
            site["state"] = agri_state
            site["source"] = AGRICULTURAL_DATA[agri_state]["source"]
            return site
    return None


def add_new_agri_site(agri_state, agri_site_key, agri_site_data):
    if agri_state not in AGRICULTURAL_DATA:
        AGRICULTURAL_DATA[agri_state] = {
            "description": f"ولاية {agri_state}",
            "source": agri_site_data.get("source", "إدخال يدوي"),
            "sites": {}
        }
    AGRICULTURAL_DATA[agri_state]["sites"][agri_site_key] = agri_site_data
    return True


def get_all_agri_sites_as_dataframe():
    rows = []
    for state_name, state_data in AGRICULTURAL_DATA.items():
        for site_key, site_data in state_data["sites"].items():
            rows.append({
                "site_name": f"{state_name}-{site_data.get('name_ar', site_key)}",
                "state": state_name, "site_key": site_key,
                "depth_m": site_data["depth_m"],
                "recharge_mm": site_data["recharge_mm"],
                "slope_pct": site_data.get("slope_pct", 3.0),
                "conductivity": site_data["conductivity"],
                "aquifer": site_data["aquifer"], "soil": site_data["soil"],
                "vadose": site_data["vadose"],
                "no3_mg_l": site_data["no3_mg_l"],
                "na_meq_l": site_data["na_meq_l"],
                "ca_meq_l": site_data["ca_meq_l"],
                "mg_meq_l": site_data["mg_meq_l"],
                "k_meq_l": site_data["k_meq_l"],
                "ec_ds_m": site_data["ec_ds_m"],
                "crop_type": site_data.get("crop_type", "N/A"),
                "irrigation_method": site_data.get("irrigation_method", "N/A"),
                "source": state_data["source"],
            })
    return pd.DataFrame(rows)
