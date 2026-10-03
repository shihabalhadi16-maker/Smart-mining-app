"""قاعدة بيانات السودان الكاملة - نظام التعدين السوداني v54.0
=====================================
يحتوي على:
1. 18 ولاية سودانية (STATES_DATABASE)
2. بيانات زراعية لـ 4 ولايات (AGRICULTURAL_DATA)
3. آبار NARIS و دارفور
4. مواقع التعدين المعروفة
5. محليات الخرطوم
"""

# ============================================================
# ============ قاعدة بيانات الولايات السودانية (18 ولاية) ============
# ============================================================
STATES_DATABASE = {
    # ============ 1. سنار ============
    "سنار": {
        "description": "ولاية سنار - منطقة تعدين أهلي نشطة",
        "source": "Elmedani et al. (2025)",
        "sites": {
            "Ghaat_Haffer_Dry": {
                "name_ar": "حفير القلعاط - موسم جاف",
                "coords": (13.55, 33.60),
                "depth_m": 12.0, "recharge_mm": 20.0, "slope_pct": 3.0,
                "conductivity": 2.5, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.025, "hg_water_mg_l": 0.011,
                "actual_contaminated": 1, "season": "جاف",
                "activity": "تعدين أهلي"
            },
            "Ghaat_Haffer_Wet": {
                "name_ar": "حفير القلعاط - موسم رطب",
                "coords": (13.55, 33.60),
                "depth_m": 12.0, "recharge_mm": 20.0, "slope_pct": 3.0,
                "conductivity": 2.5, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.350, "hg_water_mg_l": 0.360,
                "actual_contaminated": 1, "season": "رطب",
                "activity": "تعدين أهلي"
            },
            "Gabis_Haffer_Dry": {
                "name_ar": "حفير جبس - موسم جاف",
                "coords": (13.50, 33.55),
                "depth_m": 15.0, "recharge_mm": 18.0, "slope_pct": 4.0,
                "conductivity": 3.0, "aquifer": "sand_and_gravel",
                "soil": "sandy_loam", "vadose": "sandstone",
                "cn_water_mg_l": 0.022, "hg_water_mg_l": 0.200,
                "actual_contaminated": 1, "season": "جاف",
                "activity": "تعدين أهلي"
            },
            "Gabis_Haffer_Wet": {
                "name_ar": "حفير جبس - موسم رطب",
                "coords": (13.50, 33.55),
                "depth_m": 15.0, "recharge_mm": 18.0, "slope_pct": 4.0,
                "conductivity": 3.0, "aquifer": "sand_and_gravel",
                "soil": "sandy_loam", "vadose": "sandstone",
                "cn_water_mg_l": 0.200, "hg_water_mg_l": 0.530,
                "actual_contaminated": 1, "season": "رطب",
                "activity": "تعدين أهلي"
            },
            "Jebel_Moya": {
                "name_ar": "جبل موية - موقع مرجعي",
                "coords": (13.45, 33.50),
                "depth_m": 25.0, "recharge_mm": 10.0, "slope_pct": 6.0,
                "conductivity": 1.5, "aquifer": "massive_shale",
                "soil": "clay_loam", "vadose": "silt_clay",
                "cn_water_mg_l": 0.001, "hg_water_mg_l": 0.0001,
                "actual_contaminated": 0, "season": "جاف",
                "activity": "مرجعي (نظيف)"
            }
        }
    },
    # ============ 2. كسلا ============
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
                "activity": "زراعة"
            },
            "Gash_Kassala_City": {
                "name_ar": "القاش - مدينة كسلا",
                "coords": (15.45, 36.40),
                "depth_m": 20.0, "recharge_mm": 96.0, "slope_pct": 3.0,
                "conductivity": 30.0, "aquifer": "sand_and_gravel",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.020, "hg_water_mg_l": 0.002,
                "actual_contaminated": 1, "season": "-",
                "activity": "تعدين + زراعة"
            },
            "Gash_Downstream": {
                "name_ar": "القاش - المصب",
                "coords": (15.40, 36.35),
                "depth_m": 25.0, "recharge_mm": 96.0, "slope_pct": 4.0,
                "conductivity": 50.0, "aquifer": "sand_and_gravel",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.015, "hg_water_mg_l": 0.0015,
                "actual_contaminated": 0, "season": "-",
                "activity": "زراعة"
            }
        }
    },
    # ============ 3. نهر النيل ============
    "نهر النيل": {
        "description": "ولاية نهر النيل - الحجر الرملي النوبي",
        "source": "Mohammed et al. (2023)",
        "sites": {
            "Berber": {
                "name_ar": "بربر",
                "coords": (18.02, 33.98),
                "depth_m": 18.0, "recharge_mm": 15.0, "slope_pct": 2.0,
                "conductivity": 5.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-",
                "activity": "زراعة"
            },
            "Abu_Hamad": {
                "name_ar": "أبو حمد",
                "coords": (19.53, 33.32),
                "depth_m": 22.0, "recharge_mm": 12.0, "slope_pct": 3.0,
                "conductivity": 3.5, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.008, "hg_water_mg_l": 0.002,
                "actual_contaminated": 0, "season": "-",
                "activity": "زراعة + تعدين"
            },
            "El_Damer": {
                "name_ar": "الدامر",
                "coords": (17.59, 33.96),
                "depth_m": 20.0, "recharge_mm": 15.0, "slope_pct": 3.0,
                "conductivity": 4.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.006, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-",
                "activity": "زراعة"
            }
        }
    },
    # ============ 4. الخرطوم ============
    "الخرطوم": {
        "description": "ولاية الخرطوم - الحجر الرملي النوبي",
        "source": "Mohammed et al. (2023)",
        "sites": {
            "Omdurman": {
                "name_ar": "أم درمان",
                "coords": (15.65, 32.48),
                "depth_m": 15.0, "recharge_mm": 15.0, "slope_pct": 4.0,
                "conductivity": 3.3, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-",
                "activity": "حضري"
            },
            "North_Khartoum": {
                "name_ar": "شمال الخرطوم",
                "coords": (15.75, 32.55),
                "depth_m": 20.0, "recharge_mm": 15.0, "slope_pct": 3.0,
                "conductivity": 4.85, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sandstone",
                "cn_water_mg_l": 0.006, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-",
                "activity": "حضري"
            },
            "East_Nile": {
                "name_ar": "شرق النيل",
                "coords": (15.60, 32.65),
                "depth_m": 18.0, "recharge_mm": 15.0, "slope_pct": 3.5,
                "conductivity": 4.0, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.007, "hg_water_mg_l": 0.0015,
                "actual_contaminated": 0, "season": "-",
                "activity": "حضري + صناعي"
            }
        }
    },
    # ============ 5. البحر الأحمر ============
    "البحر الأحمر": {
        "description": "ولاية البحر الأحمر - تعدين الذهب",
        "source": "تقديرات عامة",
        "sites": {
            "Port_Sudan": {
                "name_ar": "بورتسودان",
                "coords": (19.62, 37.22),
                "depth_m": 25.0, "recharge_mm": 30.0, "slope_pct": 3.0,
                "conductivity": 5.0, "aquifer": "sand_and_gravel",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-",
                "activity": "حضري + تعدين"
            },
            "Jebel_Alba": {
                "name_ar": "جبل علبة",
                "coords": (21.50, 36.50),
                "depth_m": 30.0, "recharge_mm": 20.0, "slope_pct": 8.0,
                "conductivity": 3.0, "aquifer": "metamorphic_igneous",
                "soil": "gravel", "vadose": "metamorphic_igneous",
                "cn_water_mg_l": 0.015, "hg_water_mg_l": 0.005,
                "actual_contaminated": 1, "season": "-",
                "activity": "تعدين أهلي"
            },
            "Halaib": {
                "name_ar": "حلايب",
                "coords": (22.22, 36.65),
                "depth_m": 28.0, "recharge_mm": 25.0, "slope_pct": 5.0,
                "conductivity": 2.5, "aquifer": "metamorphic_igneous",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.010, "hg_water_mg_l": 0.003,
                "actual_contaminated": 1, "season": "-",
                "activity": "تعدين أهلي"
            }
        }
    },
    # ============ 6. الشمالية ============
    "الشمالية": {
        "description": "الولاية الشمالية - تعدين الذهب",
        "source": "تقديرات عامة",
        "sites": {
            "Wadi_Halfa": {
                "name_ar": "وادي حلفا",
                "coords": (21.80, 31.35),
                "depth_m": 30.0, "recharge_mm": 10.0, "slope_pct": 2.0,
                "conductivity": 2.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sandstone",
                "cn_water_mg_l": 0.010, "hg_water_mg_l": 0.005,
                "actual_contaminated": 1, "season": "-",
                "activity": "تعدين أهلي"
            },
            "Dongola": {
                "name_ar": "دنقلا",
                "coords": (19.17, 30.47),
                "depth_m": 25.0, "recharge_mm": 12.0, "slope_pct": 2.0,
                "conductivity": 3.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.008, "hg_water_mg_l": 0.003,
                "actual_contaminated": 1, "season": "-",
                "activity": "زراعة + تعدين"
            },
            "Merowe": {
                "name_ar": "مروي",
                "coords": (18.47, 31.82),
                "depth_m": 22.0, "recharge_mm": 12.0, "slope_pct": 3.0,
                "conductivity": 4.0, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.006, "hg_water_mg_l": 0.002,
                "actual_contaminated": 0, "season": "-",
                "activity": "زراعة"
            }
        }
    },
    # ============ 7. الجزيرة ============
    "الجزيرة": {
        "description": "ولاية الجزيرة - الزراعة والتعدين",
        "source": "تقديرات عامة",
        "sites": {
            "Wad_Madani": {
                "name_ar": "ود مدني",
                "coords": (14.40, 33.52),
                "depth_m": 18.0, "recharge_mm": 20.0, "slope_pct": 3.0,
                "conductivity": 5.0, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-",
                "activity": "زراعة"
            },
            "Al_Hasaheisa": {
                "name_ar": "الحصاحيصا",
                "coords": (14.75, 33.30),
                "depth_m": 20.0, "recharge_mm": 18.0, "slope_pct": 4.0,
                "conductivity": 4.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.006, "hg_water_mg_l": 0.002,
                "actual_contaminated": 0, "season": "-",
                "activity": "زراعة"
            }
        }
    },
    # ============ 8. القضارف ============
    "القضارف": {
        "description": "ولاية القضارف - الزراعة والتعدين",
        "source": "تقديرات عامة",
        "sites": {
            "Gedaref_City": {
                "name_ar": "القضارف",
                "coords": (14.03, 35.38),
                "depth_m": 25.0, "recharge_mm": 40.0, "slope_pct": 4.0,
                "conductivity": 3.0, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-",
                "activity": "زراعة"
            },
            "Gallabat": {
                "name_ar": "القلابات",
                "coords": (12.87, 35.90),
                "depth_m": 22.0, "recharge_mm": 50.0, "slope_pct": 5.0,
                "conductivity": 2.5, "aquifer": "metamorphic_igneous",
                "soil": "sand", "vadose": "metamorphic_igneous",
                "cn_water_mg_l": 0.010, "hg_water_mg_l": 0.005,
                "actual_contaminated": 1, "season": "-",
                "activity": "تعدين أهلي"
            }
        }
    },
    # ============ 9. النيل الأزرق ============
    "النيل الأزرق": {
        "description": "ولاية النيل الأزرق - الزراعة",
        "source": "تقديرات عامة",
        "sites": {
            "Damazin": {
                "name_ar": "الدمازين",
                "coords": (11.79, 34.36),
                "depth_m": 20.0, "recharge_mm": 60.0, "slope_pct": 3.0,
                "conductivity": 4.0, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-",
                "activity": "زراعة"
            },
            "Roseires": {
                "name_ar": "الروصيرص",
                "coords": (11.85, 34.38),
                "depth_m": 18.0, "recharge_mm": 65.0, "slope_pct": 4.0,
                "conductivity": 3.5, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.006, "hg_water_mg_l": 0.002,
                "actual_contaminated": 0, "season": "-",
                "activity": "زراعة"
            }
        }
    },
    # ============ 10. النيل الأبيض ============
    "النيل الأبيض": {
        "description": "ولاية النيل الأبيض - الزراعة",
        "source": "تقديرات عامة",
        "sites": {
            "Kosti": {
                "name_ar": "كوستي",
                "coords": (13.17, 32.67),
                "depth_m": 18.0, "recharge_mm": 20.0, "slope_pct": 2.0,
                "conductivity": 5.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-",
                "activity": "زراعة"
            },
            "Rabak": {
                "name_ar": "ربك",
                "coords": (13.18, 32.74),
                "depth_m": 20.0, "recharge_mm": 18.0, "slope_pct": 3.0,
                "conductivity": 4.0, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.006, "hg_water_mg_l": 0.002,
                "actual_contaminated": 0, "season": "-",
                "activity": "زراعة + صناعة"
            }
        }
    },
    # ============ 11. شمال كردفان ============
    "شمال كردفان": {
        "description": "ولاية شمال كردفان - تعدين",
        "source": "تقديرات عامة",
        "sites": {
            "El_Obeid": {
                "name_ar": "الأبيض",
                "coords": (13.18, 30.22),
                "depth_m": 30.0, "recharge_mm": 15.0, "slope_pct": 4.0,
                "conductivity": 3.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.005, "hg_water_mg_l": 0.001,
                "actual_contaminated": 0, "season": "-",
                "activity": "حضري + تعدين"
            },
            "Sodari": {
                "name_ar": "سودري",
                "coords": (13.50, 29.50),
                "depth_m": 35.0, "recharge_mm": 12.0, "slope_pct": 5.0,
                "conductivity": 2.0, "aquifer": "metamorphic_igneous",
                "soil": "gravel", "vadose": "metamorphic_igneous",
                "cn_water_mg_l": 0.015, "hg_water_mg_l": 0.008,
                "actual_contaminated": 1, "season": "-",
                "activity": "تعدين أهلي"
            }
        }
    },
    # ============ 12. جنوب كردفان ============
    "جنوب كردفان": {
        "description": "ولاية جنوب كردفان - تعدين الذهب",
        "source": "تقديرات عامة",
        "sites": {
            "Kadugli": {
                "name_ar": "كادوقلي",
                "coords": (11.01, 29.72),
                "depth_m": 25.0, "recharge_mm": 30.0, "slope_pct": 5.0,
                "conductivity": 3.0, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.010, "hg_water_mg_l": 0.005,
                "actual_contaminated": 1, "season": "-",
                "activity": "تعدين أهلي"
            },
            "Dilling": {
                "name_ar": "الدلنج",
                "coords": (12.05, 29.65),
                "depth_m": 28.0, "recharge_mm": 25.0, "slope_pct": 4.0,
                "conductivity": 2.5, "aquifer": "metamorphic_igneous",
                "soil": "sand", "vadose": "metamorphic_igneous",
                "cn_water_mg_l": 0.012, "hg_water_mg_l": 0.006,
                "actual_contaminated": 1, "season": "-",
                "activity": "تعدين أهلي"
            }
        }
    },
    # ============ 13. غرب كردفان ============
    "غرب كردفان": {
        "description": "ولاية غرب كردفان - رعوي",
        "source": "تقديرات عامة",
        "sites": {
            "Al_Fula": {
                "name_ar": "الفولة",
                "coords": (11.72, 28.35),
                "depth_m": 30.0, "recharge_mm": 35.0, "slope_pct": 3.0,
                "conductivity": 2.0, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.008, "hg_water_mg_l": 0.003,
                "actual_contaminated": 0, "season": "-",
                "activity": "رعوي"
            }
        }
    },
    # ============ 14. شمال دارفور ============
    "شمال دارفور": {
        "description": "ولاية شمال دارفور - تعدين",
        "source": "UNEP Darfur Reports",
        "sites": {
            "El_Fasher": {
                "name_ar": "الفاشر",
                "coords": (13.63, 25.35),
                "depth_m": 35.0, "recharge_mm": 25.0, "slope_pct": 4.0,
                "conductivity": 2.0, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.010, "hg_water_mg_l": 0.005,
                "actual_contaminated": 1, "season": "-",
                "activity": "تعدين أهلي"
            },
            "Kutum": {
                "name_ar": "كتم",
                "coords": (14.20, 24.65),
                "depth_m": 40.0, "recharge_mm": 20.0, "slope_pct": 5.0,
                "conductivity": 1.5, "aquifer": "metamorphic_igneous",
                "soil": "gravel", "vadose": "metamorphic_igneous",
                "cn_water_mg_l": 0.015, "hg_water_mg_l": 0.008,
                "actual_contaminated": 1, "season": "-",
                "activity": "تعدين أهلي"
            }
        }
    },
    # ============ 15. جنوب دارفور ============
    "جنوب دارفور": {
        "description": "ولاية جنوب دارفور - تعدين",
        "source": "UNEP Darfur Reports",
        "sites": {
            "Nyala": {
                "name_ar": "نيالا",
                "coords": (12.05, 24.88),
                "depth_m": 30.0, "recharge_mm": 30.0, "slope_pct": 4.0,
                "conductivity": 2.5, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.010, "hg_water_mg_l": 0.005,
                "actual_contaminated": 1, "season": "-",
                "activity": "تعدين أهلي + حضري"
            },
            "Zalingei": {
                "name_ar": "زالنجي",
                "coords": (12.90, 23.47),
                "depth_m": 35.0, "recharge_mm": 28.0, "slope_pct": 5.0,
                "conductivity": 2.0, "aquifer": "metamorphic_igneous",
                "soil": "gravel", "vadose": "metamorphic_igneous",
                "cn_water_mg_l": 0.012, "hg_water_mg_l": 0.006,
                "actual_contaminated": 1, "season": "-",
                "activity": "تعدين أهلي"
            }
        }
    },
    # ============ 16. غرب دارفور ============
    "غرب دارفور": {
        "description": "ولاية غرب دارفور - تعدين",
        "source": "UNEP Darfur Reports",
        "sites": {
            "El_Geneina": {
                "name_ar": "الجنينة",
                "coords": (13.45, 22.45),
                "depth_m": 32.0, "recharge_mm": 32.0, "slope_pct": 4.0,
                "conductivity": 2.5, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.010, "hg_water_mg_l": 0.005,
                "actual_contaminated": 1, "season": "-",
                "activity": "تعدين أهلي"
            }
        }
    },
    # ============ 17. وسط دارفور ============
    "وسط دارفور": {
        "description": "ولاية وسط دارفور - تعدين",
        "source": "UNEP Darfur Reports",
        "sites": {
            "Zalingei_Central": {
                "name_ar": "وسط دارفور",
                "coords": (12.50, 23.50),
                "depth_m": 33.0, "recharge_mm": 30.0, "slope_pct": 5.0,
                "conductivity": 2.0, "aquifer": "metamorphic_igneous",
                "soil": "gravel", "vadose": "metamorphic_igneous",
                "cn_water_mg_l": 0.012, "hg_water_mg_l": 0.006,
                "actual_contaminated": 1, "season": "-",
                "activity": "تعدين أهلي"
            }
        }
    },
    # ============ 18. شرق دارفور ============
    "شرق دارفور": {
        "description": "ولاية شرق دارفور - رعوي + تعدين",
        "source": "UNEP Darfur Reports",
        "sites": {
            "Ed_Daein": {
                "name_ar": "الضعين",
                "coords": (11.45, 26.12),
                "depth_m": 35.0, "recharge_mm": 28.0, "slope_pct": 4.0,
                "conductivity": 2.0, "aquifer": "weathered_metamorphic_igneous",
                "soil": "sand", "vadose": "sand_gravel",
                "cn_water_mg_l": 0.010, "hg_water_mg_l": 0.005,
                "actual_contaminated": 1, "season": "-",
                "activity": "تعدين أهلي + رعوي"
            }
        }
    }
}


# ============================================================
# ============ البيانات الزراعية ============
# ============================================================
AGRICULTURAL_DATA = {
    "الجزيرة": {
        "description": "ولاية الجزيرة - أكبر مشروع زراعي في السودان",
        "source": "دراسات زراعية سودانية",
        "sites": {
            "Wad_Madani_Agri": {
                "name_ar": "ود مدني - مشروع الجزيرة",
                "coords": (14.40, 33.52),
                "depth_m": 18.0, "recharge_mm": 20.0, "slope_pct": 3.0,
                "conductivity": 5.0, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "no3_mg_l": 35.0, "na_meq_l": 5.0, "ca_meq_l": 3.0,
                "mg_meq_l": 1.5, "k_meq_l": 0.3, "ec_ds_m": 0.8,
                "fertilizer_use": 0.7, "land_use_factor": 0.8,
                "crop_type": "قطن، قمح، فول سوداني",
                "irrigation_method": "ري سطحي"
            },
            "Al_Hasaheisa_Agri": {
                "name_ar": "الحصاحيصا - الجزيرة",
                "coords": (14.75, 33.30),
                "depth_m": 20.0, "recharge_mm": 18.0, "slope_pct": 4.0,
                "conductivity": 4.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "no3_mg_l": 28.0, "na_meq_l": 4.0, "ca_meq_l": 3.5,
                "mg_meq_l": 2.0, "k_meq_l": 0.4, "ec_ds_m": 0.6,
                "fertilizer_use": 0.6, "land_use_factor": 0.7,
                "crop_type": "قمح، ذرة",
                "irrigation_method": "ري سطحي"
            }
        }
    },
    "النيل الأبيض": {
        "description": "ولاية النيل الأبيض - زراعة قصب السكر",
        "source": "دراسات زراعية سودانية",
        "sites": {
            "Kenana_Agri": {
                "name_ar": "كنانة - قصب السكر",
                "coords": (13.10, 32.85),
                "depth_m": 15.0, "recharge_mm": 22.0, "slope_pct": 2.0,
                "conductivity": 6.0, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "no3_mg_l": 45.0, "na_meq_l": 6.0, "ca_meq_l": 3.5,
                "mg_meq_l": 2.5, "k_meq_l": 0.5, "ec_ds_m": 1.2,
                "fertilizer_use": 0.8, "land_use_factor": 0.9,
                "crop_type": "قصب السكر",
                "irrigation_method": "ري بالرش"
            },
            "Kosti_Agri": {
                "name_ar": "كوستي - زراعة",
                "coords": (13.17, 32.67),
                "depth_m": 18.0, "recharge_mm": 20.0, "slope_pct": 2.5,
                "conductivity": 5.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "no3_mg_l": 30.0, "na_meq_l": 4.5, "ca_meq_l": 3.0,
                "mg_meq_l": 2.0, "k_meq_l": 0.3, "ec_ds_m": 0.9,
                "fertilizer_use": 0.6, "land_use_factor": 0.7,
                "crop_type": "ذرة، فول",
                "irrigation_method": "ري سطحي"
            }
        }
    },
    "نهر النيل": {
        "description": "ولاية نهر النيل - زراعة على ضفاف النيل",
        "source": "دراسات زراعية سودانية",
        "sites": {
            "Berber_Agri": {
                "name_ar": "بربر - زراعة",
                "coords": (18.02, 33.98),
                "depth_m": 18.0, "recharge_mm": 15.0, "slope_pct": 2.0,
                "conductivity": 5.0, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "no3_mg_l": 22.0, "na_meq_l": 3.5, "ca_meq_l": 3.0,
                "mg_meq_l": 1.5, "k_meq_l": 0.2, "ec_ds_m": 0.5,
                "fertilizer_use": 0.5, "land_use_factor": 0.6,
                "crop_type": "تمور، فواكه",
                "irrigation_method": "ري غمر"
            },
            "Abu_Hamad_Agri": {
                "name_ar": "أبو حمد - زراعة",
                "coords": (19.53, 33.32),
                "depth_m": 22.0, "recharge_mm": 12.0, "slope_pct": 3.0,
                "conductivity": 3.5, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "no3_mg_l": 18.0, "na_meq_l": 3.0, "ca_meq_l": 3.5,
                "mg_meq_l": 2.0, "k_meq_l": 0.3, "ec_ds_m": 0.4,
                "fertilizer_use": 0.4, "land_use_factor": 0.5,
                "crop_type": "تمور، خضروات",
                "irrigation_method": "ري غمر"
            }
        }
    },
    "الخرطوم": {
        "description": "ولاية الخرطوم - زراعة حضرية",
        "source": "دراسات زراعية سودانية",
        "sites": {
            "Omdurman_Agri": {
                "name_ar": "أم درمان - زراعة حضرية",
                "coords": (15.65, 32.48),
                "depth_m": 15.0, "recharge_mm": 15.0, "slope_pct": 4.0,
                "conductivity": 3.3, "aquifer": "massive_sandstone",
                "soil": "sand", "vadose": "sand_gravel",
                "no3_mg_l": 55.0, "na_meq_l": 8.0, "ca_meq_l": 4.0,
                "mg_meq_l": 3.0, "k_meq_l": 0.8, "ec_ds_m": 1.5,
                "fertilizer_use": 0.9, "land_use_factor": 0.9,
                "crop_type": "خضروات",
                "irrigation_method": "ري بالتنقيط"
            },
            "Bahri_Agri": {
                "name_ar": "بحري - زراعة",
                "coords": (15.60, 32.60),
                "depth_m": 18.0, "recharge_mm": 15.0, "slope_pct": 3.0,
                "conductivity": 4.0, "aquifer": "massive_sandstone",
                "soil": "sandy_loam", "vadose": "sand_gravel",
                "no3_mg_l": 48.0, "na_meq_l": 7.0, "ca_meq_l": 3.5,
                "mg_meq_l": 2.5, "k_meq_l": 0.6, "ec_ds_m": 1.3,
                "fertilizer_use": 0.8, "land_use_factor": 0.85,
                "crop_type": "خضروات، فواكه",
                "irrigation_method": "ري سطحي"
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
    "Ghaat_Haffer": {"coords": (13.55, 33.60), "activity": "تعدين أهلي",
                     "cyanide_use": True, "mercury_use": True},
    "Gabis_Haffer": {"coords": (13.50, 33.55), "activity": "تعدين أهلي",
                     "cyanide_use": True, "mercury_use": True},
    "Jebel_Moya": {"coords": (13.45, 33.50), "activity": "تعدين أهلي",
                   "cyanide_use": True, "mercury_use": True},
    "Jebel_Alba": {"coords": (21.50, 36.50), "activity": "تعدين أهلي",
                   "cyanide_use": True, "mercury_use": True},
    "Sodari": {"coords": (13.50, 29.50), "activity": "تعدين أهلي",
               "cyanide_use": True, "mercury_use": True},
    "Kadugli": {"coords": (11.01, 29.72), "activity": "تعدين أهلي",
                "cyanide_use": True, "mercury_use": True},
    "El_Fasher": {"coords": (13.63, 25.35), "activity": "تعدين أهلي",
                  "cyanide_use": True, "mercury_use": True},
    "Nyala": {"coords": (12.05, 24.88), "activity": "تعدين أهلي",
              "cyanide_use": True, "mercury_use": True},
    "Kutum": {"coords": (14.20, 24.65), "activity": "تعدين أهلي",
              "cyanide_use": True, "mercury_use": True},
    "Wadi_Halfa": {"coords": (21.80, 31.35), "activity": "تعدين أهلي",
                   "cyanide_use": True, "mercury_use": True},
    "Dongola": {"coords": (19.17, 30.47), "activity": "تعدين أهلي",
                "cyanide_use": True, "mercury_use": True},
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
# ============ دوال مساعدة - التعدين ============
# ============================================================
def get_preset_locations_for_app():
    """إرجاع قاموس المواقع بصيغة متوافقة مع التطبيق"""
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
    """ملخص بيانات التعدين"""
    return {
        "total_states": len(STATES_DATABASE),
        "total_sites": sum(len(s["sites"]) for s in STATES_DATABASE.values()),
        "states": list(STATES_DATABASE.keys()),
        "sources": list(set(s["source"] for s in STATES_DATABASE.values()))
    }


def get_sites_by_state(state_name):
    """مواقع ولاية معينة"""
    if state_name in STATES_DATABASE:
        return STATES_DATABASE[state_name]["sites"]
    return {}


def get_site_data(state_name, site_key):
    """بيانات موقع محدد"""
    if state_name in STATES_DATABASE:
        sites = STATES_DATABASE[state_name]["sites"]
        if site_key in sites:
            site = sites[site_key].copy()
            site["state"] = state_name
            site["source"] = STATES_DATABASE[state_name]["source"]
            return site
    return None


def add_new_site(state_name, site_key, site_data):
    """إضافة موقع جديد للتعدين"""
    if state_name not in STATES_DATABASE:
        STATES_DATABASE[state_name] = {
            "description": f"ولاية {state_name}",
            "source": site_data.get("source", "إدخال يدوي"),
            "sites": {}
        }
    STATES_DATABASE[state_name]["sites"][site_key] = site_data
    return True


def get_all_sites_as_dataframe():
    """كل مواقع التعدين كـ DataFrame"""
    import pandas as pd
    rows = []
    for state_name, state_data in STATES_DATABASE.items():
        for site_key, site_data in state_data["sites"].items():
            rows.append({
                "site_name": f"{state_name}-{site_data['name_ar']}",
                "state": state_name, "site_key": site_key,
                "depth_m": site_data["depth_m"],
                "recharge_mm": site_data["recharge_mm"],
                "slope_pct": site_data["slope_pct"],
                "conductivity": site_data["conductivity"],
                "aquifer": site_data["aquifer"],
                "soil": site_data["soil"], "vadose": site_data["vadose"],
                "cn_water_mg_l": site_data["cn_water_mg_l"],
                "hg_water_mg_l": site_data["hg_water_mg_l"],
                "actual_contaminated": site_data["actual_contaminated"],
                "source": state_data["source"],
                "season": site_data["season"],
                "activity": site_data["activity"]
            })
    return pd.DataFrame(rows)


def get_states_list():
    """قائمة الولايات"""
    return list(STATES_DATABASE.keys())


def get_sites_list(state_name):
    """قائمة المواقع في ولاية"""
    if state_name in STATES_DATABASE:
        return list(STATES_DATABASE[state_name]["sites"].keys())
    return []


# ============================================================
# ============ دوال مساعدة - الزراعة ============
# ============================================================
def get_agricultural_data_summary():
    """ملخص البيانات الزراعية"""
    return {
        "total_states": len(AGRICULTURAL_DATA),
        "total_sites": sum(len(s["sites"]) for s in AGRICULTURAL_DATA.values()),
        "states": list(AGRICULTURAL_DATA.keys())
    }


def get_agri_states_list():
    """قائمة الولايات الزراعية"""
    return list(AGRICULTURAL_DATA.keys())


def get_agri_sites_list(state_name):
    """قائمة المواقع الزراعية في ولاية"""
    if state_name in AGRICULTURAL_DATA:
        return list(AGRICULTURAL_DATA[state_name]["sites"].keys())
    return []


def get_agri_site_data(state_name, site_key):
    """بيانات موقع زراعي"""
    if state_name in AGRICULTURAL_DATA:
        sites = AGRICULTURAL_DATA[state_name]["sites"]
        if site_key in sites:
            site = sites[site_key].copy()
            site["state"] = state_name
            site["source"] = AGRICULTURAL_DATA[state_name]["source"]
            return site
    return None


def add_new_agri_site(state_name, site_key, site_data):
    """إضافة موقع زراعي جديد"""
    if state_name not in AGRICULTURAL_DATA:
        AGRICULTURAL_DATA[state_name] = {
            "description": f"ولاية {state_name} - زراعة",
            "source": site_data.get("source", "إدخال يدوي"),
            "sites": {}
        }
    AGRICULTURAL_DATA[state_name]["sites"][site_key] = site_data
    return True


def get_all_agri_sites_as_dataframe():
    """كل المواقع الزراعية كـ DataFrame"""
    import pandas as pd
    rows = []
    for state_name, state_data in AGRICULTURAL_DATA.items():
        for site_key, site_data in state_data["sites"].items():
            rows.append({
                "site_name": f"{state_name}-{site_data['name_ar']}",
                "state": state_name, "site_key": site_key,
                "depth_m": site_data["depth_m"],
                "recharge_mm": site_data["recharge_mm"],
                "slope_pct": site_data["slope_pct"],
                "conductivity": site_data["conductivity"],
                "aquifer": site_data["aquifer"],
                "soil": site_data["soil"], "vadose": site_data["vadose"],
                "no3_mg_l": site_data["no3_mg_l"],
                "na_meq_l": site_data["na_meq_l"],
                "ca_meq_l": site_data["ca_meq_l"],
                "mg_meq_l": site_data["mg_meq_l"],
                "k_meq_l": site_data["k_meq_l"],
                "ec_ds_m": site_data["ec_ds_m"],
                "fertilizer_use": site_data["fertilizer_use"],
                "land_use_factor": site_data["land_use_factor"],
                "crop_type": site_data["crop_type"],
                "irrigation_method": site_data["irrigation_method"]
            })
    return pd.DataFrame(rows)
