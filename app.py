"""
Module: calculations.py
Description: Hydrogeological computations for the DRASTIC and Modified DRASTIC models,
             including travel time estimations, uncertainty bounds, and regulatory compliance checks.
Reference: US EPA (1993). EPA/600/R-93/174, Section 7.3.3.2, pp. 356-358.
"""

from typing import Dict, Any, List, Union


# ============================================================
# [القسم الجديد 1] دوال مساعدة لحدود الحساب والثوابت العلمية
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
        "result_interpretation": "النتيجة هي زمن وصول الجبهة الأمامية، وليس الزمن الكامل لوصول الملوث.",
        "intended_use": "Screening-level assessment only (تقييم أولي فقط)"
    }
}


def assess_confidence_level(
    has_measured_K: bool,
    has_measured_porosity: bool,
    has_tracer_data: bool,
    has_borehole_logs: bool
) -> Dict[str, str]:
    """
    تقييم مستوى الثقة في نتائج الحساب بناءً على جودة البيانات الميدانية المتاحة.
    
    Evaluates the confidence level of calculation results based on available field data quality.
    
    Confidence assessment based on data quality tiers adapted from 
    US EPA (1993) and Fetter (2001).

    :param has_measured_K: هل تم قياس النفاذية الهيدروليكية ميدانياً؟
    :param has_measured_porosity: هل تم قياس المسامية الفعالة ميدانياً؟
    :param has_tracer_data: هل تتوفر بيانات تتبع الملوثات الميدانية؟
    :param has_borehole_logs: هل تتوفر سجلات الآبار والجسات الجيوفيزيائية؟
    :return: قاموس يحتوي على مستوى الثقة، اللون، والرسالة باللغتين العربية والإنجليزية.
    """
    data_points_sum = sum([
        bool(has_measured_K),
        bool(has_measured_porosity),
        bool(has_tracer_data),
        bool(has_borehole_logs)
    ])

    if data_points_sum >= 4:
        return {
            "level": "High",
            "color": "green",
            "message": "النتيجة موثوقة للمراجعة الرسمية",
            "message_en": "Result is reliable for official review"
        }
    elif data_points_sum >= 2:
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


def calculate_travel_time_range(
    depth_m: float,
    porosity_min: float,
    porosity_max: float,
    K_min_m_day: float,
    K_max_m_day: float,
    gradient: float = 1.0
) -> Dict[str, Any]:
    """
    حساب نطاق زمن عبور الملوث للتعامل مع عدم اليقين في خصائص الطبقة غير المشبعة.
    
    Calculates the range of contaminant travel time to address parameter uncertainty 
    in unsaturated zone properties.

    Range calculation reflects uncertainty in hydraulic conductivity 
    and effective porosity. Based on US EPA (1993) guidance on 
    parameter uncertainty in travel time estimates.

    :param depth_m: العمق إلى مستوى الماء الجوفي (متر)
    :param porosity_min: الحد الأدنى للمسامية الفعالة (كسر عشري)
    :param porosity_max: الحد الأقصى للمسامية الفعالة (كسر عشري)
    :param K_min_m_day: الحد الأدنى للنفاذية الهيدروليكية (متر/يوم)
    :param K_max_m_day: الحد الأقصى للنفاذية الهيدروليكية (متر/يوم)
    :param gradient: الهيدروليكي / التدرج المائي (Default = 1.0 للتدفق الرأسي)
    :return: قاموس يتضمن أزمنة العبور (بالسنوات) للسناريوهات المختلفة وتوصيف النطاق.
    """
    # Seepage Velocity v_s = (K * i) / n_e
    # Travel Time t (days) = depth / v_s = (depth * n_e) / (K * i)
    # Convert to years: t (years) = t (days) / 365.25

    # Min time (Worst case): maximum velocity -> K_max and porosity_min
    v_max = (K_max_m_day * gradient) / porosity_min if porosity_min > 0 and K_max_m_day > 0 else 1e-9
    t_min_days = depth_m / v_max if v_max > 0 else 0
    t_min_years = round(t_min_days / 365.25, 2)

    # Max time (Best case): minimum velocity -> K_min and porosity_max
    v_min = (K_min_m_day * gradient) / porosity_max if porosity_max > 0 and K_min_m_day > 0 else 1e-9
    t_max_days = depth_m / v_min if v_min > 0 else 0
    t_max_years = round(t_max_days / 365.25, 2)

    # Best estimate: mean values
    porosity_avg = (porosity_min + porosity_max) / 2.0
    K_avg = (K_min_m_day + K_max_m_day) / 2.0
    v_avg = (K_avg * gradient) / porosity_avg if porosity_avg > 0 and K_avg > 0 else 1e-9
    t_best_days = depth_m / v_avg if v_avg > 0 else 0
    t_best_years = round(t_best_days / 365.25, 2)

    return {
        "travel_time_min_years": t_min_years,
        "travel_time_max_years": t_max_years,
        "travel_time_best_years": t_best_years,
        "range_description": f"{t_min_years} - {t_max_years} سنة (تقديري)",
        "notes": "النطاق يعكس عدم اليقين في K والمسامية"
    }


def generate_travel_time_disclaimer() -> str:
    """
    توليد نص إخلاء المسؤولية الموحد الخاص بحدود وأحكام حساب زمن عبور الملوثات.
    
    Generates a standardized legal/technical disclaimer regarding contaminant 
    travel time calculation limits and boundaries.

    Reference: US EPA/600/R-93/174, Section 7.3.3.2, pp. 356-358.

    :return: نص إخلاء المسؤولية منسق بالعربية.
    """
    return (
        "⚠️ حدود حساب زمن وصول الملوثات:\n\n"
        "1. هذا تقدير أولي (Screening-level) وفقاً لـ US EPA (1993).\n"
        "2. يفترض وسطاً متجانساً، سرعة ثابتة، ملوثاً غير متفاعل.\n"
        "3. لا يأخذ في الحسبان: الانتشار، الامتزاز، الشقوق، عدم التجانس.\n"
        "4. دقة الحساب تعتمد على دقة K و porosity المُدخلة.\n"
        "5. النتيجة هي زمن وصول الجبهة الأمامية، وليس الزمن الكامل.\n"
        "6. للقرارات النهائية: معايرة ميدانية إلزامية (Tracer Tests).\n\n"
        "المرجع: US EPA/600/R-93/174, Section 7.3.3.2, pp. 356-358."
    )


# ============================================================
# [القسم الرئيسي / المحدث] حسابات نموذج DRASTIC وزمن العبور
# ============================================================

def calculate_drastic_index(
    D: float, R: float, A: float, S: float, T: float, I: float, C: float,
    weights: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    حساب مؤشر DRASTIC القياسي أو المعدل بناءً على الأوزان المحددة.
    
    Calculates the DRASTIC Index using parameters ratings and weights.
    """
    if weights is None:
        # Default DRASTIC Weights
        weights = {'D': 5, 'R': 4, 'A': 3, 'S': 2, 'T': 1, 'I': 5, 'C': 3}

    drastic_index = (
        (D * weights.get('D', 5)) +
        (R * weights.get('R', 4)) +
        (A * weights.get('A', 3)) +
        (S * weights.get('S', 2)) +
        (T * weights.get('T', 1)) +
        (I * weights.get('I', 5)) +
        (C * weights.get('C', 3))
    )

    # Risk categorization
    if drastic_index < 100:
        vulnerability = "Low"
        color = "blue"
    elif 100 <= drastic_index < 140:
        vulnerability = "Moderate"
        color = "yellow"
    elif 140 <= drastic_index < 180:
        vulnerability = "High"
        color = "orange"
    else:
        vulnerability = "Very High"
        color = "red"

    return {
        "drastic_index": round(drastic_index, 2),
        "vulnerability_category": vulnerability,
        "color": color
    }


def calculate_travel_time(
    depth_m: float,
    porosity: float,
    K_m_day: float,
    gradient: float = 1.0
) -> Dict[str, Any]:
    """
    حساب زمن عبور الملوث الرأسي عبر نطاق التهوية (Unsaturated Zone)
    مع إدراج الحدود النظرية والتحذيرات القانونية/الفنية المصاحبة.
    
    Calculates vertical contaminant travel time through the vadose zone,
    incorporating model theoretical limitations and standard disclaimers.

    Reference: US EPA/600/R-93/174, Section 7.3.3.2, pp. 356-358.

    :param depth_m: العمق حتى المياه الجوفية (متر)
    :param porosity: المسامية الفعالة (كسر عشري)
    :param K_m_day: النفاذية الهيدروليكية (متر/يوم)
    :param gradient: الهيدروليكي / التدرج (افتراضي = 1.0)
    :return: قاموس يحوي الزمن بالساعات والأيام والسنوات بالإضافة للمحددات وإخلاء المسؤولية.
    """
    if K_m_day <= 0 or porosity <= 0:
        seepage_velocity = 0.0
        travel_time_days = float('inf')
        travel_time_years = float('inf')
    else:
        # Seepage velocity (m/day) = (K * i) / n_e
        seepage_velocity = (K_m_day * gradient) / porosity
        travel_time_days = depth_m / seepage_velocity if seepage_velocity > 0 else float('inf')
        travel_time_years = travel_time_days / 365.25

    return {
        "seepage_velocity_m_day": round(seepage_velocity, 4),
        "travel_time_days": round(travel_time_days, 2) if travel_time_days != float('inf') else None,
        "travel_time_years": round(travel_time_years, 2) if travel_time_years != float('inf') else None,
        "model_limitations": DRASTIC_MODEL_LIMITATIONS["travel_time"],
        "disclaimer": generate_travel_time_disclaimer()
    }
