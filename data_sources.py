"""
Data Sources Module — مصادر البيانات المجانية
وحدة البيانات المجانية المتاحة للاستخدام الفوري

الغرض:
    توفير بيانات جاهزة من مصادر مفتوحة (NARIS, UNEP, الدراسات المنشورة)
    لتغذية نموذج DRASTIC بدون الحاجة لزيارات ميدانية فورية.

References:
    - NARIS (2005). Nubian Sandstone Aquifer System Monitoring 
      and Evaluation Rapid Assessment Report. CEDARE.
    - UNEP (2007). Groundwater in Darfur. UNEP Publications.
    - Elsheikh et al. (2023). Groundwater Vulnerability Assessment 
      in Khartoum State. Nature Environment and Pollution Technology, 
      22(4). DOI: 10.46488/NEPT.2023.v22i04.033
    - BGS (2000). Groundwater Literature Archive — Sudan.

⚠️ تنبيه:
    جميع هذه البيانات من مصادر منشورة، وتحتاج تحققاً ميدانياً قبل
    الاستخدام الرسمي. القيم المُقدّرة موسومة بوضوح.
"""

from typing import Dict, Any, List, Tuple

# ============================================================
# [1] مواقع مسبقة من NARIS (الحجر الرملي النوبي)
# المصدر: NARIS (2005). CEDARE
# ============================================================

NARIS_WELLS: Dict[str, Dict[str, Any]] = {
    "El-Kifar": {
        "coords": (29.531, 26.936),  # (lon, lat)
        "depth_m": 50.0,  # تقديري من التقرير
        "initial_water_level_m": 45.0,
        "hydraulic_conductivity_m_day": 5.0,
        "transmissivity_m2_day": 250.0,
        "lithology": "Nubian Sandstone",
        "source": "NARIS (2005), Table 4",
        "verification": "published"
    },
    "El-Heiz": {
        "coords": (27.900, 28.720),
        "depth_m": 40.0,
        "initial_water_level_m": 35.0,
        "hydraulic_conductivity_m_day": 3.0,
        "transmissivity_m2_day": 120.0,
        "lithology": "Nubian Sandstone",
        "source": "NARIS (2005), Table 4",
        "verification": "published"
    },
    "East Oweinat": {
        "coords": (28.500, 22.500),
        "depth_m": 200.0,
        "initial_water_level_m": 180.0,
        "hydraulic_conductivity_m_day": 8.0,
        "transmissivity_m2_day": 1600.0,
        "lithology": "Nubian Sandstone",
        "source": "NARIS (2005), Table 4",
        "verification": "published"
    },
    "Abu Minqar": {
        "coords": (28.500, 27.500),
        "depth_m": 60.0,
        "initial_water_level_m": 55.0,
        "hydraulic_conductivity_m_day": 4.0,
        "transmissivity_m2_day": 240.0,
        "lithology": "Nubian Sandstone",
        "source": "NARIS (2005), Table 4",
        "verification": "published"
    },
}


# ============================================================
# [2] آبار دارفور من UNEP
# المصدر: UNEP (2007). Groundwater in Darfur
# ============================================================

DARFUR_WELLS: Dict[str, Dict[str, Any]] = {
    "Zamzam_1": {
        "coords": (25.30, 13.60),  # تقريبي
        "depth_m": 63.0,
        "location": "جنوب الفاشر",
        "water_level_monitored": True,
        "source": "UNEP (2007)",
        "verification": "published"
    },
    "Zamzam_2": {
        "coords": (25.32, 13.62),
        "depth_m": 60.0,
        "location": "على بعد 2 كم من وادي الكوع",
        "water_level_monitored": True,
        "source": "UNEP (2007)",
        "verification": "published"
    },
    "Um_Dahin": {
        "coords": (22.50, 12.00),
        "depth_m": 45.0,
        "location": "غرب دارفور",
        "water_level_monitored": True,
        "source": "UNEP (2007)",
        "verification": "published"
    },
}


# ============================================================
# [3] محليات الخرطوم (الدراسة المرجعية)
# المصدر: Elsheikh et al. (2023)
# ============================================================

KHARTOUM_LOCALITIES: Dict[str, Dict[str, Any]] = {
    "Shargelnile": {
        "coords": (32.60, 15.60),
        "wells_sampled": 75,
        "total_coliform_positive_pct": 34.4,
        "source": "Elsheikh et al. (2023)",
    },
    "Omdurman": {
        "coords": (32.50, 15.60),
        "wells_sampled": 28,
        "source": "Elsheikh et al. (2023)",
    },
    "Ombada": {
        "coords": (32.40, 15.60),
        "wells_sampled": 31,
        "source": "Elsheikh et al. (2023)",
    },
    "Khartoum": {
        "coords": (32.50, 15.50),
        "wells_sampled": 20,
        "source": "Elsheikh et al. (2023)",
    },
    "Bahry": {
        "coords": (32.60, 15.60),
        "wells_sampled": 31,
        "source": "Elsheikh et al. (2023)",
    },
    "Karary": {
        "coords": (32.40, 15.70),
        "wells_sampled": 56,
        "source": "Elsheikh et al. (2023)",
    },
    "Jabalawlya": {
        "coords": (32.50, 15.40),
        "wells_sampled": 39,
        "source": "Elsheikh et al. (2023)",
    },
}


# ============================================================
# [4] بيانات مناخية (الأمطار والتغذية)
# المصدر: دراسات منشورة + تقديرات
# ============================================================

CLIMATE_DATA: Dict[str, Dict[str, float]] = {
    "دارفور": {
        "rainfall_mm_year": 300.0,
        "recharge_mm_year": 15.0,
        "source": "UNEP (2007) + published estimates",
    },
    "الخرطوم": {
        "rainfall_mm_year": 150.0,
        "recharge_mm_year": 10.0,
        "source": "Published studies",
    },
    "نهر النيل": {
        "rainfall_mm_year": 100.0,
        "recharge_mm_year": 8.0,
        "source": "Published studies",
    },
    "الشمالية": {
        "rainfall_mm_year": 50.0,
        "recharge_mm_year": 5.0,
        "source": "Published studies",
    },
    "البحر الأحمر": {
        "rainfall_mm_year": 100.0,
        "recharge_mm_year": 10.0,
        "source": "Published studies",
    },
    "كسلا": {
        "rainfall_mm_year": 250.0,
        "recharge_mm_year": 12.0,
        "source": "Published studies",
    },
    "الجزيرة": {
        "rainfall_mm_year": 200.0,
        "recharge_mm_year": 10.0,
        "source": "Published studies",
    },
}


# ============================================================
# [5] معادلة النفاذية من MODFLOW
# المصدر: MODFLOW Study, Khartoum
# ============================================================

def estimate_conductivity_from_resistivity(
    aquifer_resistivity_ohm_m: float
) -> float:
    """
    تقدير النفاذية الهيدروليكية من مقاومة الخزان الجوفي.
    
    المعادلة من: MODFLOW Study, Khartoum.
        K = 386.4 * R_aq^(-0.93283)
    
    حيث:
        K: النفاذية (m/day)
        R_aq: مقاومة الخزان (ohm·m)
    
    Args:
        aquifer_resistivity_ohm_m: مقاومة الخزان الكهربائية
    
    Returns:
        float: النفاذية الهيدروليكية بـ m/day
    """
    if aquifer_resistivity_ohm_m <= 0:
        raise ValueError("المقاومة يجب أن تكون > 0")
    
    K = 386.4 * (aquifer_resistivity_ohm_m ** -0.93283)
    return round(K, 4)


# ============================================================
# [6] طبقات جيولوجية نموذجية (الخرطوم)
# المصدر: MODFLOW Study
# ============================================================

KHARTOUM_STRATIGRAPHY = [
    {
        "layer": "Clay",
        "depth_from_m": 22.7,
        "depth_to_m": 32.1,
        "drastic_I_rating": 1,  # Silt/Clay
        "drastic_A_contribution": None,  # ليس خزاناً
    },
    {
        "layer": "Saturated Sand",
        "depth_from_m": 31.0,
        "depth_to_m": 32.0,
        "drastic_I_rating": 8,  # Sand and Gravel
        "drastic_A_contribution": 8,
    },
    {
        "layer": "Saturated Sandstone",
        "depth_from_m": 32.0,
        "depth_to_m": 232.0,
        "drastic_I_rating": 6,  # Sandstone
        "drastic_A_contribution": 6,
    },
]


# ============================================================
# [7] حدود السيانيد والزئبق (للمقارنة)
# المصدر: WHO (2022), Minamata Convention
# ============================================================

WATER_QUALITY_LIMITS: Dict[str, Dict[str, float]] = {
    "cyanide_free_mg_L": {
        "WHO_limit": 0.07,
        "source": "WHO (2022), 4th ed.",
    },
    "cyanide_total_mg_L": {
        "WHO_limit": 0.07,
        "source": "WHO (2022), 4th ed.",
    },
    "mercury_inorganic_mg_L": {
        "WHO_limit": 0.006,
        "source": "WHO (2022), 4th ed.",
    },
    "mercury_total_mg_L": {
        "WHO_limit": 0.001,
        "source": "WHO (2022), 4th ed.",
    },
    "lead_mg_L": {
        "WHO_limit": 0.01,
        "source": "WHO (2022), 4th ed.",
    },
    "arsenic_mg_L": {
        "WHO_limit": 0.01,
        "source": "WHO (2022), 4th ed.",
    },
    "cadmium_mg_L": {
        "WHO_limit": 0.003,
        "source": "WHO (2022), 4th ed.",
    },
}


# ============================================================
# [8] مواقع تعدين معروفة (من الدراسات المنشورة)
# المصدر: دراسات سودانية متعددة
# ============================================================

KNOWN_MINING_SITES: Dict[str, Dict[str, Any]] = {
    "العبيدية — نهر النيل": {
        "coords": (33.98, 18.12),
        "activity": "طواحين + معالجة كرتة",
        "cyanide_use": True,
        "mercury_use": True,
        "nearby_water": "نهر النيل + أودية",
        "source": "دراسات منشورة 2019-2023",
        "verification": "published"
    },
    "أبو حمد — نهر النيل": {
        "coords": (33.32, 19.53),
        "activity": "طواحين + تعدين تقليدي",
        "cyanide_use": True,
        "mercury_use": True,
        "nearby_water": "نهر النيل",
        "source": "دراسات منشورة",
        "verification": "published"
    },
    "بربر — نهر النيل": {
        "coords": (33.98, 18.02),
        "activity": "تعدين تقليدي",
        "cyanide_use": False,
        "mercury_use": True,
        "nearby_water": "نهر النيل",
        "source": "تقارير محلية",
        "verification": "needs_verification"
    },
    "أرياب — البحر الأحمر": {
        "coords": (36.35, 18.33),
        "activity": "تعدين صناعي",
        "cyanide_use": True,
        "mercury_use": False,
        "nearby_water": "أودية موسمية",
        "source": "تقارير الشركة",
        "verification": "published"
    },
    "وادي العشاري — الشمالية": {
        "coords": (34.50, 21.80),
        "activity": "تعدين تقليدي",
        "cyanide_use": False,
        "mercury_use": True,
        "nearby_water": "وادي العشاري",
        "source": "تقارير محلية",
        "verification": "needs_verification"
    },
    "تلودي — جنوب كردفان": {
        "coords": (30.12, 10.63),
        "activity": "تعدين تقليدي",
        "cyanide_use": False,
        "mercury_use": True,
        "nearby_water": "أودية موسمية",
        "source": "تقارير محلية",
        "verification": "needs_verification"
    },
    "كادوقلي — جنوب كردفان": {
        "coords": (29.72, 11.02),
        "activity": "طواحين",
        "cyanide_use": True,
        "mercury_use": True,
        "nearby_water": "أودية موسمية",
        "source": "تقارير محلية",
        "verification": "needs_verification"
    },
}


# ============================================================
# [9] دوال مساعدة للاستخدام في البرنامج
# ============================================================

def get_preset_locations_for_app() -> Dict[str, Dict[str, Any]]:
    """
    إرجاع قائمة المواقع المسبقة الجاهزة للاستخدام في Streamlit.
    
    Returns:
        Dict: قاموس يطابق بنية preset_locations في app.py
    """
    preset = {}
    
    # مواقع NARIS
    for name, data in NARIS_WELLS.items():
        preset[f"{name} (NARIS)"] = {
            "coords": (data["coords"][1], data["coords"][0]),  # (lat, lon)
            "depth": data.get("initial_water_level_m", 30.0),
            "conductivity": data.get("hydraulic_conductivity_m_day", 5.0),
            "source": data["source"],
        }
    
    # مواقع دارفور
    for name, data in DARFUR_WELLS.items():
        preset[f"{name} (Darfur)"] = {
            "coords": (data["coords"][1], data["coords"][0]),
            "depth": data.get("depth_m", 50.0),
            "conductivity": 2.0,
            "source": data["source"],
        }
    
    # مواقع تعدين معروفة
    for name, data in KNOWN_MINING_SITES.items():
        preset[name] = {
            "coords": (data["coords"][1], data["coords"][0]),
            "depth": 20.0,  # تقديري
            "conductivity": 5.0,
            "source": data["source"],
        }
    
    return preset


def get_climate_for_region(region_name: str) -> Dict[str, float]:
    """
    إرجاع بيانات المناخ لمنطقة محددة.
    
    Args:
        region_name: اسم المنطقة (بالعربية كما في CLIMATE_DATA)
    
    Returns:
        Dict: {"rainfall_mm_year": ..., "recharge_mm_year": ...}
    """
    if region_name not in CLIMATE_DATA:
        # إرجاع قيم افتراضية للسودان
        return {
            "rainfall_mm_year": 150.0,
            "recharge_mm_year": 10.0,
            "source": "Default Sudan values",
        }
    return CLIMATE_DATA[region_name]


def compare_with_who_limits(measured_value: float, 
                             parameter: str) -> Dict[str, Any]:
    """
    مقارنة قيمة مقاسة بحدود WHO.
    
    Args:
        measured_value: القيمة المقاسة (mg/L)
        parameter: اسم المعامل (مثل "cyanide_free_mg_L")
    
    Returns:
        Dict: يحتوي على القيمة، الحد، والحالة
    """
    if parameter not in WATER_QUALITY_LIMITS:
        raise ValueError(f"معامل غير معروف: {parameter}")
    
    limit = WATER_QUALITY_LIMITS[parameter]["WHO_limit"]
    compliant = measured_value <= limit
    excess = measured_value - limit if not compliant else 0
    
    return {
        "measured": measured_value,
        "who_limit": limit,
        "compliant": compliant,
        "excess_mg_L": round(excess, 4),
        "status": "✅ مطابق" if compliant else "❌ تجاوز",
        "source": WATER_QUALITY_LIMITS[parameter]["source"],
    }


def get_data_summary() -> Dict[str, int]:
    """
    ملخص البيانات المتاحة من هذا الملف.
    
    Returns:
        Dict: عدد العناصر في كل فئة
    """
    return {
        "NARIS Wells": len(NARIS_WELLS),
        "Darfur Wells": len(DARFUR_WELLS),
        "Khartoum Localities": len(KHARTOUM_LOCALITIES),
        "Climate Regions": len(CLIMATE_DATA),
        "Known Mining Sites": len(KNOWN_MINING_SITES),
        "Water Quality Parameters": len(WATER_QUALITY_LIMITS),
        "Total Data Points": (
            len(NARIS_WELLS) + len(DARFUR_WELLS) + 
            len(KHARTOUM_LOCALITIES) + len(CLIMATE_DATA) + 
            len(KNOWN_MINING_SITES)
        ),
    }


# ============================================================
# [10] عند التشغيل المباشر
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Data Sources Module — Summary")
    print("=" * 60)
    
    summary = get_data_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("Sample: NARIS Well Data")
    print("=" * 60)
    for name, data in list(NARIS_WELLS.items())[:2]:
        print(f"\n{name}:")
        for k, v in data.items():
            print(f"  {k}: {v}")
    
    print("\n" + "=" * 60)
    print("Sample: WHO Cyanide Limit Check")
    print("=" * 60)
    result = compare_with_who_limits(0.45, "cyanide_free_mg_L")
    for k, v in result.items():
        print(f"  {k}: {v}")
