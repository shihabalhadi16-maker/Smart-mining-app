"""
DRASTIC Model & Hydrogeological Calculations Module
وحدة حساب نموذج دراستيك والحسابات الهيدروجيولوجية

References:
    - Aller, L., Bennett, T., Lehr, J. H., Petty, R. J., & Hackett, G. (1987).
      DRASTIC: A standardized system for evaluating ground water pollution 
      potential using hydrogeologic settings.
      U.S. Environmental Protection Agency, Washington, D.C., EPA/600/2-87/035.
    - Fetter, C. W. (2001). Applied Hydrogeology (4th ed.). Prentice Hall.
    - US EPA (1993). Ground Water Volume I: Ground Water and Contamination.
      EPA/600/R-93/174, Section 7.3.3.2, pp. 356-358.
    - Rahman, A. (2008). A GIS-based DRASTIC model for assessing groundwater 
      vulnerability in shallow aquifer in Aligarh.
      Environmental Monitoring and Assessment, 140(1-3), 225-238.
"""

from typing import Union, Tuple, Dict, Any, List

# ============================================================
# [1] قاموس المسامية الفعالة الافتراضية
# Reference: Fetter (2001), Table 3.4, p.78
# ============================================================
EFFECTIVE_POROSITY_DEFAULTS: Dict[str, float] = {
    "clay": 0.03,
    "silt": 0.10,
    "silty_sand": 0.18,
    "fine_sand": 0.22,
    "medium_sand": 0.25,
    "coarse_sand": 0.28,
    "gravel": 0.30,
    "sand_and_gravel": 0.28,
    "sandstone": 0.20,
    "limestone": 0.10,
    "fractured_rock": 0.02
}

# ============================================================
# [2] حدود نموذج حساب زمن وصول الملوثات
# Reference: US EPA (1993). EPA/600/R-93/174, Section 7.3.3.2
# ============================================================
DRASTIC_MODEL_LIMITATIONS: Dict[str, Any] = {
    "travel_time": {
        "reference": "US EPA (1993). EPA/600/R-93/174, Section 7.3.3.2, pp. 356-358",
        "assumptions": [
            "Homogeneous porous medium (وسط مسامي متجانس)",
            "Constant seepage velocity (سرعة تسرب ثابتة)",
            "Non-reactive conservative solute (ملوث محافظ غير متفاعل)",
            "No hydrodynamic dispersion (لا يوجد انتشار هيدروديناميكي)",
            "No sorption/retardation (لا يوجد امتزاز أو تأخير)",
            "Steady-state downward flow (تدفق مستقر لأسفل)"
        ],
        "does_not_account_for": [
            "Fractures and preferential pathways (الشقوق والمسارات التفضيلية)",
            "Heterogeneity in K and porosity (عدم التجانس في النفاذية والمسامية)",
            "Chemical reactions and biodegradation (التفاعلات الكيميائية والتحلل)",
            "Dispersion of the contaminant front (انتشار جبهة الملوث)",
            "Transient recharge events (أحداث التغذية العابرة)"
        ],
        "result_interpretation": (
            "النتيجة هي زمن وصول الجبهة الأمامية، وليس الزمن الكامل "
            "لوصول الملوث."
        ),
        "intended_use": "Screening-level assessment only (تقييم أولي فقط)"
    }
}


# ============================================================
# [3] دوال التصنيف الأساسية (EPA/600/2-87/035)
# ============================================================

def get_d_rating(depth_m: float) -> int:
    """
    Depth to Water (D) rating based on EPA/600/2-87/035 
    (Aller et al., 1987, Table 6, p. 19).

    Ranges (converted from feet to meters):
    - 0 to 1.5 m      -> Rating: 10
    - 1.5 to 4.6 m    -> Rating: 9
    - 4.6 to 9.1 m    -> Rating: 7
    - 9.1 to 15.2 m   -> Rating: 5
    - 15.2 to 22.9 m  -> Rating: 3
    - 22.9 to 30.5 m  -> Rating: 2
    - > 30.5 m        -> Rating: 1
    """
    if depth_m < 0:
        raise ValueError(
            "عمق المياه الجوفية لا يمكن أن يكون سالباً. / "
            "Depth to water cannot be negative."
        )
    if depth_m <= 1.5:
        return 10
    elif depth_m <= 4.6:
        return 9
    elif depth_m <= 9.1:
        return 7
    elif depth_m <= 15.2:
        return 5
    elif depth_m <= 22.9:
        return 3
    elif depth_m <= 30.5:
        return 2
    else:
        return 1


def get_r_rating(recharge_mm: float) -> int:
    """
    Net Recharge (R) rating based on EPA/600/2-87/035 
    (Aller et al., 1987, Table 7, p. 21).

    Ranges (converted from inches/year to mm/year):
    - 0 to 50.8 mm      -> Rating: 1
    - 50.8 to 101.6 mm  -> Rating: 3
    - 101.6 to 177.8 mm -> Rating: 6
    - 177.8 to 254.0 mm -> Rating: 8
    - > 254.0 mm        -> Rating: 9
    """
    if recharge_mm < 0:
        raise ValueError(
            "معدل التغذية السنوية لا يمكن أن يكون سالباً. / "
            "Recharge cannot be negative."
        )
    if recharge_mm <= 50.8:
        return 1
    elif recharge_mm <= 101.6:
        return 3
    elif recharge_mm <= 177.8:
        return 6
    elif recharge_mm <= 254.0:
        return 8
    else:
        return 9


def get_a_rating(
    aquifer_type: str, use_range: bool = False
) -> Union[int, Tuple[int, int]]:
    """
    Aquifer Media (A) rating based on EPA/600/2-87/035 
    (Aller et al., 1987, Table 8, p. 23).

    Values (min, typical, max):
    - massive_shale: (1, 2, 3)
    - metamorphic_igneous: (2, 3, 5)
    - weathered_metamorphic_igneous: (3, 4, 5)
    - thin_bedded_sequences: (5, 6, 9)
    - massive_sandstone: (4, 6, 9)
    - massive_limestone: (4, 6, 9)
    - sand_and_gravel: (4, 8, 9)
    - basalt: (2, 9, 10)
    - karst_limestone: (9, 10, 10)
    """
    type_map: Dict[str, Tuple[int, int, int]] = {
        "massive_shale": (1, 2, 3),
        "metamorphic_igneous": (2, 3, 5),
        "weathered_metamorphic_igneous": (3, 4, 5),
        "thin_bedded_sequences": (5, 6, 9),
        "massive_sandstone": (4, 6, 9),
        "massive_limestone": (4, 6, 9),
        "sand_and_gravel": (4, 8, 9),
        "basalt": (2, 9, 10),
        "karst_limestone": (9, 10, 10)
    }
    key = aquifer_type.strip().lower()
    if key not in type_map:
        raise ValueError(
            f"نوع الخزان الجوفي غير صالح '{aquifer_type}'. "
            f"الخيارات المتاحة: {list(type_map.keys())}"
        )
    min_val, typical_val, max_val = type_map[key]
    if use_range:
        return (min_val, max_val)
    return typical_val


def get_s_rating(
    soil_type: str, use_range: bool = False
) -> Union[int, Tuple[int, int]]:
    """
    Soil Media (S) rating based on EPA/600/2-87/035 
    (Aller et al., 1987, Table 9, p. 25).

    Values (min, typical, max):
    - thin_or_absent: (10, 10, 10)
    - gravel: (10, 10, 10)
    - sand: (9, 9, 9)
    - peat: (8, 8, 8)
    - aggregated_clay: (7, 7, 7)
    - sandy_loam: (6, 6, 6)
    - loam: (5, 5, 5)
    - silty_loam: (4, 4, 4)
    - clay_loam: (3, 3, 3)
    - muck: (2, 2, 2)
    - nonshrinking_clay: (1, 1, 1)
    """
    type_map: Dict[str, Tuple[int, int, int]] = {
        "thin_or_absent": (10, 10, 10),
        "gravel": (10, 10, 10),
        "sand": (9, 9, 9),
        "peat": (8, 8, 8),
        "aggregated_clay": (7, 7, 7),
        "sandy_loam": (6, 6, 6),
        "loam": (5, 5, 5),
        "silty_loam": (4, 4, 4),
        "clay_loam": (3, 3, 3),
        "muck": (2, 2, 2),
        "nonshrinking_clay": (1, 1, 1)
    }
    key = soil_type.strip().lower()
    if key not in type_map:
        raise ValueError(
            f"نوع التربة غير صالح '{soil_type}'. "
            f"الخيارات المتاحة: {list(type_map.keys())}"
        )
    min_val, typical_val, max_val = type_map[key]
    if use_range:
        return (min_val, max_val)
    return typical_val


def get_t_rating(slope_percent: float) -> int:
    """
    Topography/Slope (T) rating based on EPA/600/2-87/035 
    (Aller et al., 1987, Table 10, p. 27).

    Ranges:
    - 0 to 2%   -> Rating: 10
    - 2 to 6%   -> Rating: 9
    - 6 to 12%  -> Rating: 5
    - 12 to 18% -> Rating: 3
    - > 18%     -> Rating: 1
    """
    if slope_percent < 0:
        raise ValueError(
            "نسبة الانحدار لا يمكن أن تكون سالبة. / "
            "Slope percent cannot be negative."
        )
    if slope_percent <= 2.0:
        return 10
    elif slope_percent <= 6.0:
        return 9
    elif slope_percent <= 12.0:
        return 5
    elif slope_percent <= 18.0:
        return 3
    else:
        return 1


def get_i_rating(vadose_type: str) -> int:
    """
    Impact of Vadose Zone (I) rating based on EPA/600/2-87/035 
    (Aller et al., 1987, Table 11, p. 29).
    """
    type_map: Dict[str, int] = {
        "silt_clay": 1,
        "shale": 3,
        "limestone": 6,
        "sandstone": 6,
        "bedded_sequences": 6,
        "metamorphic_igneous": 4,
        "sand_gravel_silt_clay": 6,
        "sand_gravel": 8,
        "basalt": 9,
        "karst_limestone": 10
    }
    key = vadose_type.strip().lower()
    if key not in type_map:
        raise ValueError(
            f"نوع المنطقة غير المشبعة غير صالح '{vadose_type}'. "
            f"الخيارات المتاحة: {list(type_map.keys())}"
        )
    return type_map[key]


def get_c_rating(conductivity_m_day: float) -> int:
    """
    Hydraulic Conductivity (C) rating based on EPA/600/2-87/035 
    (Aller et al., 1987, Table 12, p. 31).

    Conversion factor: 1 gpd/ft^2 = 0.04074 m/day
    """
    if conductivity_m_day < 0:
        raise ValueError(
            "النفاذية الهيدروليكية لا يمكن أن تكون سالبة. / "
            "Hydraulic conductivity cannot be negative."
        )
    if conductivity_m_day <= 4.074:
        return 1
    elif conductivity_m_day <= 12.222:
        return 2
    elif conductivity_m_day <= 28.518:
        return 4
    elif conductivity_m_day <= 40.740:
        return 6
    elif conductivity_m_day <= 81.480:
        return 8
    else:
        return 10


# ============================================================
# [4] حساب مؤشر دراستيك الإجمالي
# ============================================================

def calculate_drastic_index(
    D: int, R: int, A: int, S: int, T: int, I: int, C: int
) -> int:
    """
    DRASTIC Index based on Aller et al. (1987, p. 16).

    Formula:
        DI = Dr·Dw + Rr·Rw + Ar·Aw + Sr·Sw + Tr·Tw + Ir·Iw + Cr·Cw

    Weights: Dw=5, Rw=4, Aw=3, Sw=2, Tw=1, Iw=5, Cw=3
    Range: 23 (min) to 230 (max)
    """
    ratings = [D, R, A, S, T, I, C]
    if any(not isinstance(r, int) or r < 1 or r > 10 for r in ratings):
        raise ValueError(
            "جميع تقييمات دراستيك الفردية يجب أن تكون أعداداً صحيحة "
            "بين 1 و 10."
        )
    Dw, Rw, Aw, Sw, Tw, Iw, Cw = 5, 4, 3, 2, 1, 5, 3
    return (D * Dw) + (R * Rw) + (A * Aw) + (S * Sw) + (T * Tw) + (I * Iw) + (C * Cw)


# ============================================================
# [5] تصنيف مستوى الخطورة (مبني على Rahman 2008)
# ============================================================

def classify_drastic_risk(index: int) -> Dict[str, str]:
    """
    Classifies groundwater pollution risk based on DRASTIC Index.

    Reference:
        Thresholds are ADAPTED from Rahman (2008) vulnerability classification.
        GRAS must calibrate locally before official use.
    """
    if not isinstance(index, int):
        raise ValueError("المؤشر يجب أن يكون عدداً صحيحاً. / Index must be an integer.")

    if index >= 180:
        return {
            "level": "Very High",
            "color": "red",
            "action": "Immediate remediation"
        }
    elif index >= 140:
        return {
            "level": "High",
            "color": "orange",
            "action": "Urgent monitoring"
        }
    elif index >= 100:
        return {
            "level": "Moderate",
            "color": "yellow",
            "action": "Regular monitoring"
        }
    else:
        return {
            "level": "Low",
            "color": "green",
            "action": "Routine surveillance"
        }


# ============================================================
# [6] حساب زمن وصول الملوثات (معادلة Darcy)
# ============================================================

def calculate_travel_time(
    depth_m: float,
    porosity: float,
    K_m_day: float,
    gradient: float = 1.0,
    zone: str = "unsaturated"
) -> Dict[str, Any]:
    """
    Advective contaminant travel time using Darcy's seepage velocity.

    Reference: Fetter (2001), Applied Hydrogeology 4th ed., pp. 132-136.

    Formula:
        seepage_velocity = (K_m_day * gradient) / porosity
        travel_time_days = depth_m / seepage_velocity
        travel_time_years = travel_time_days / 365.25

    Limitations: See DRASTIC_MODEL_LIMITATIONS["travel_time"].
    """
    warnings: List[str] = []

    if depth_m <= 0:
        raise ValueError(
            "العمق/المسافة يجب أن تكون أكبر من الصفر. / "
            "depth_m must be greater than zero."
        )
    if not (0.01 < porosity < 0.60):
        raise ValueError(
            "المسامية خارج النطاق الجيولوجي / "
            "Porosity outside geological range (0.01-0.60)."
        )
    if K_m_day <= 0 or K_m_day > 1000:
        raise ValueError(
            "النفاذية الهيدروليكية يجب أن تكون أكبر من 0 وأقل من أو "
            "تساوي 1000 متر/يوم."
        )
    if gradient <= 0:
        raise ValueError(
            "الميل الهيدروليكي يجب أن يكون أكبر من الصفر. / "
            "Gradient must be greater than zero."
        )

    zone_clean = zone.strip().lower()
    if zone_clean not in ["unsaturated", "saturated"]:
        raise ValueError(
            "النطاق يجب أن يكون 'unsaturated' أو 'saturated'."
        )

    if zone_clean == "unsaturated" and gradient != 1.0:
        warnings.append(
            "⚠️ In unsaturated zone, i should equal 1.0 (gravity drainage)."
        )
    if zone_clean == "saturated" and gradient > 0.1:
        warnings.append(
            "⚠️ Gradient is high for saturated zone (typical: 0.001-0.05)."
        )
    if zone_clean == "unsaturated" and K_m_day > 10:
        warnings.append(
            "⚠️ K is high for unsaturated zone (typical: 0.001-1.0 m/day)."
        )

    seepage_velocity = (K_m_day * gradient) / porosity
    travel_time_days = depth_m / seepage_velocity
    travel_time_years = travel_time_days / 365.25

    if travel_time_years > 1000:
        warnings.append(
            f"⚠️ Travel time = {travel_time_years:.0f} years. Extremely "
            "low permeability medium (clay). Verify K value."
        )

    return {
        "travel_time_days": float(travel_time_days),
        "travel_time_years": float(travel_time_years),
        "seepage_velocity_m_day": float(seepage_velocity),
        "warnings": warnings,
        "model_limitations": DRASTIC_MODEL_LIMITATIONS["travel_time"],
        "disclaimer": generate_travel_time_disclaimer()
    }


# ============================================================
# [7] تقييم مستوى الثقة في النتائج
# ============================================================

def assess_confidence_level(
    has_measured_K: bool,
    has_measured_porosity: bool,
    has_tracer_data: bool,
    has_borehole_logs: bool
) -> Dict[str, str]:
    """
    Assess confidence level based on data quality tiers.

    Reference:
        Adapted from US EPA (1993) and Fetter (2001) guidance on
        parameter uncertainty in hydrogeological assessments.
    """
    score = sum([
        bool(has_measured_K),
        bool(has_measured_porosity),
        bool(has_tracer_data),
        bool(has_borehole_logs)
    ])

    if score >= 4:
        return {
            "level": "High",
            "color": "green",
            "message": "النتيجة موثوقة للمراجعة الرسمية",
            "message_en": "Result is reliable for official review"
        }
    elif score >= 2:
        return {
            "level": "Medium",
            "color": "yellow",
            "message": "النتيجة تقديرية، تحتاج تحققاً ميدانياً",
            "message_en": "Result is estimated, requires field verification"
        }
    else:
        return {
            "level": "Low",
            "color": "red",
            "message": "النتيجة استدلالية فقط، لا تُعتمد رسمياً",
            "message_en": "Result is indicative only, not for official use"
        }


# ============================================================
# [8] حساب نطاق زمن وصول الملوثات (Range)
# ============================================================

def calculate_travel_time_range(
    depth_m: float,
    porosity_min: float,
    porosity_max: float,
    K_min_m_day: float,
    K_max_m_day: float,
    gradient: float = 1.0
) -> Dict[str, Any]:
    """
    Range calculation reflects uncertainty in hydraulic conductivity
    and effective porosity.

    Reference:
        US EPA (1993) guidance on parameter uncertainty in travel 
        time estimates (EPA/600/R-93/174).
    """
    if not (0.01 < porosity_min < porosity_max < 0.60):
        raise ValueError(
            "المسامية يجب أن تكون بين 0.01 و 0.60 مع porosity_min < porosity_max."
        )
    if K_min_m_day <= 0 or K_max_m_day <= K_min_m_day:
        raise ValueError(
            "K_min يجب أن يكون > 0 و K_max > K_min."
        )
    if depth_m <= 0:
        raise ValueError("العمق يجب أن يكون > 0.")
    if gradient <= 0:
        raise ValueError("الميل الهيدروليكي يجب أن يكون > 0.")

    # أسوأ حالة: K_max + porosity_min (أسرع وصول)
    v_min = (K_max_m_day * gradient) / porosity_min
    t_min_days = depth_m / v_min

    # أفضل حالة: K_min + porosity_max (أبطأ وصول)
    v_max = (K_min_m_day * gradient) / porosity_max
    t_max_days = depth_m / v_max

    # تقدير مركزي
    K_avg = (K_min_m_day + K_max_m_day) / 2.0
    por_avg = (porosity_min + porosity_max) / 2.0
    v_best = (K_avg * gradient) / por_avg
    t_best_days = depth_m / v_best

    return {
        "travel_time_min_years": round(t_min_days / 365.25, 3),
        "travel_time_max_years": round(t_max_days / 365.25, 3),
        "travel_time_best_years": round(t_best_days / 365.25, 3),
        "range_description": (
            f"{round(t_min_days / 365.25, 1)} - "
            f"{round(t_max_days / 365.25, 1)} سنة (تقديري)"
        ),
        "notes": (
            "النطاق يعكس عدم اليقين في K والمسامية. "
            "Reference: US EPA (1993), EPA/600/R-93/174."
        )
    }


# ============================================================
# [9] إخلاء المسؤولية لزمن وصول الملوثات
# ============================================================

def generate_travel_time_disclaimer() -> str:
    """
    Returns formatted Arabic disclaimer for travel time calculations.
    """
    return (
        "⚠️ حدود حساب زمن وصول الملوثات:\n\n"
        "1. هذا تقدير أولي (Screening-level) وفقاً لـ US EPA (1993).\n"
        "2. يفترض وسطاً متجانساً، سرعة ثابتة، ملوثاً غير متفاعل.\n"
        "3. لا يأخذ في الحسبان: الانتشار، الامتزاز، الشقوق، عدم التجانس.\n"
        "4. دقة الحساب تعتمد على دقة K والمسامية المُدخلة.\n"
        "5. النتيجة هي زمن وصول الجبهة الأمامية، وليس الزمن الكامل.\n"
        "6. للقرارات النهائية: معايرة ميدانية إلزامية (Tracer Tests).\n\n"
        "المرجع: US EPA/600/R-93/174, Section 7.3.3.2, pp. 356-358."
    )
