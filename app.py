"""
نموذج DRASTIC المعتمد - US EPA (Aller et al., 1987)
المرجع: https://www.epa.gov/sites/default/files/2015-12/documents/drastic-a-gis-based-model.pdf
"""

# القيمة العظمى النظرية للنموذج حسب US EPA = 226
MAX_DRASTIC = 226.0

# أوزان DRASTIC الرسمية
WEIGHTS = {"D": 5, "R": 4, "A": 3, "S": 2, "T": 1, "I": 5, "C": 3}

# حد WHO للسيانيد الحر في مياه الشرب (4th Edition, 2022)
WHO_CYANIDE_LIMIT = 0.07  # mg/L


# =========================================
# دوال التحويل من القيم الفيزيائية إلى Ratings
# =========================================
def rating_depth(depth_m):
    """D: عمق المياه الجوفية بالأمتار"""
    if depth_m < 1.5: return 10
    if depth_m < 4.6: return 9
    if depth_m < 9.1: return 7
    if depth_m < 15.2: return 5
    if depth_m < 22.9: return 3
    if depth_m < 30.5: return 2
    return 1


def rating_recharge(recharge_mm):
    """R: معدل التغذية السنوية (مم/سنة)"""
    if recharge_mm < 51: return 1
    if recharge_mm < 102: return 3
    if recharge_mm < 178: return 6
    if recharge_mm < 254: return 8
    return 9


def rating_aquifer(aquifer_type):
    """A: نوع الخزان الجوفي"""
    mapping = {
        "massive_shale": 1, "metamorphic": 2, "igneous": 2,
        "weathered_metamorphic": 3, "glacial_till": 4,
        "bedded_sandstone": 6, "limestone": 6,
        "sand_and_gravel": 8, "basalt": 9, "karst_limestone": 10
    }
    return mapping.get(aquifer_type, 6)


def rating_soil(soil_type):
    """S: نوع التربة السطحية"""
    mapping = {
        "thin_clay": 1, "clay": 3, "silty_clay": 4, "sandy_clay": 5,
        "silt": 6, "sandy_loam": 7, "sand": 9, "gravel": 10, "thin_gravel": 10
    }
    return mapping.get(soil_type, 5)


def rating_topography(slope_percent):
    """T: الانحدار (%)"""
    if slope_percent < 2: return 10
    if slope_percent < 6: return 9
    if slope_percent < 12: return 5
    if slope_percent < 18: return 3
    return 1


def rating_vadose(vadose_type):
    """I: المنطقة غير المشبعة"""
    mapping = {
        "confining_clay": 1, "silty_clay": 3, "shale": 2,
        "sandy_silt": 5, "sandstone": 6, "limestone": 6,
        "sand_gravel": 8, "karst": 10
    }
    return mapping.get(vadose_type, 6)


def rating_conductivity(k_m_per_day):
    """C: النفاذية الهيدروليكية (متر/يوم)"""
    if k_m_per_day < 0.04: return 1
    if k_m_per_day < 0.4: return 2
    if k_m_per_day < 4: return 4
    if k_m_per_day < 12: return 6
    if k_m_per_day < 28: return 8
    return 10


# =========================================
# الحساب النهائي والتصنيف
# =========================================
def calculate_drastic_index(ratings):
    """ratings: dict بمفاتيح D,R,A,S,T,I,C بقيم 1-10"""
    return round(sum(ratings[k] * WEIGHTS[k] for k in WEIGHTS), 1)


def drastic_to_percentage(index):
    """نسبة الخطر من القيمة العظمى النظرية"""
    return round((index / MAX_DRASTIC) * 100, 1)


def classify_risk(index):
    """تصنيف الخطورة حسب US EPA (مُعدّل)"""
    if index < 100: return ("🟢 منخفض", "low")
    if index < 140: return ("🟡 متوسط", "medium")
    if index < 180: return ("🟠 مرتفع", "high")
    return ("🔴 مرتفع جداً", "very_high")


# =========================================
# زمن وصول التسرب - قانون Darcy
# =========================================
def travel_time_darcy(depth_m, k_m_per_day, hydraulic_gradient=0.01, porosity=0.25):
    """
    t = depth / v ;  v = (K * i) / n_e
    النتيجة: سنة
    """
    if k_m_per_day <= 0 or porosity <= 0:
        return float('inf')
    v = (k_m_per_day * hydraulic_gradient) / porosity  # m/day
    days = depth_m / v
    return round(days / 365.25, 2)


# =========================================
# محاكاة الحلول الهندسية
# =========================================
def apply_mitigation(ratings, hdpe_liner=False, cyanide_treatment=False,
                     clay_cap=False, drainage=False):
    """
    تخفيض Ratings بناءً على أدبيات EPA.
    """
    r = ratings.copy()
    if hdpe_liner:
        r["I"] = max(1, r["I"] - 4)
        r["C"] = max(1, r["C"] - 4)
    if clay_cap:
        r["S"] = max(1, r["S"] - 5)
        r["I"] = max(1, r["I"] - 2)
    if drainage:
        r["T"] = max(1, r["T"] - 3)
    return r
