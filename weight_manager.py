"""
weight_manager.py — إدارة الأوزان الاحترافية
نظام Profiles مع حفظ دائم على القرص
"""
import json
from pathlib import Path
from datetime import datetime

WEIGHTS_DIR = Path(__file__).parent / "weights"
PROFILES_DIR = WEIGHTS_DIR / "profiles"
CONFIG_FILE = WEIGHTS_DIR / "weights_config.json"


# ============================================================
# Default weight profiles (from literature)
# ============================================================
DEFAULT_PROFILES = {
    "traditional_literature": {
        "name_ar": "⛏️ تقليدي — من الأدبيات",
        "name_en": "⛏️ Traditional — Literature",
        "mining_type": "traditional",
        "source": "Konaté et al. (2025), Karan et al. (2018)",
        "source_type": "literature",
        "alpha": 0.3, "beta": 1.0, "SF": 1.1,
        "kappa": None, "n_sites": None, "date_created": "2025-01-01",
        "verified": True,
        "description_ar": "أوزان مبنية على دراسات منشورة للتعدين الأهلي",
        "description_en": "Weights based on published artisanal mining studies",
    },
    "traditional_calibrated": {
        "name_ar": "⛏️ تقليدي — مُعاير من البيانات",
        "name_en": "⛏️ Traditional — Calibrated",
        "mining_type": "traditional",
        "source": "Grid Search on local data",
        "source_type": "calibrated",
        "alpha": 0.1, "beta": 0.743, "SF": 1.45,
        "kappa": 0.783, "n_sites": 7, "date_created": "2026-10-08",
        "verified": True,
        "description_ar": "أوزان مُعايرة على 7 مواقع تقليدية موثّقة",
        "description_en": "Weights calibrated on 7 verified traditional sites",
    },
    "industrial_literature": {
        "name_ar": "🏭 صناعي — من الأدبيات",
        "name_en": "🏭 Industrial — Literature",
        "mining_type": "industrial",
        "source": "Karan et al. (2018), Kaur et al. (2019)",
        "source_type": "literature",
        "alpha": 0.7, "beta": 0.5, "SF": 1.0,
        "kappa": None, "n_sites": None, "date_created": "2025-01-01",
        "verified": True,
        "description_ar": "أوزان للشركات الصناعية (CIL/CIP) — السيانيد رئيسي",
        "description_en": "Industrial (CIL/CIP) weights — cyanide dominant",
    },
    "industrial_calibrated": {
        "name_ar": "🏭 صناعي — مُعاير من البيانات",
        "name_en": "🏭 Industrial — Calibrated",
        "mining_type": "industrial",
        "source": "Grid Search on local data",
        "source_type": "calibrated",
        "alpha": 0.1, "beta": 0.743, "SF": 1.45,
        "kappa": 0.783, "n_sites": 10, "date_created": "2026-10-08",
        "verified": True,
        "warning_ar": "⚠️ تحذير: تأثرت المعايرة بـ Ceiling Effect في CN",
        "warning_en": "⚠️ Warning: Calibration affected by CN ceiling effect",
        "description_ar": "أوزان مُعايرة على 10 مواقع صناعية",
        "description_en": "Weights calibrated on 10 industrial sites",
    },
    "mixed_literature": {
        "name_ar": "🔀 مختلط — من الأدبيات",
        "name_en": "🔀 Mixed — Literature",
        "mining_type": "mixed",
        "source": "Weighted average (literature)",
        "source_type": "literature",
        "alpha": 0.5, "beta": 0.9, "SF": 1.3,
        "kappa": None, "n_sites": None, "date_created": "2025-01-01",
        "verified": True,
        "description_ar": "أوزان مختلطة (متوسط التقليدي والصناعي)",
        "description_en": "Mixed weights (average of traditional and industrial)",
    },
}


def _ensure_dirs():
    """إنشاء المجلدات إذا لم تكن موجودة."""
    WEIGHTS_DIR.mkdir(exist_ok=True)
    PROFILES_DIR.mkdir(exist_ok=True)


def _load_config():
    """تحميل الإعدادات الرئيسية."""
    _ensure_dirs()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # إنشاء ملف افتراضي
    config = {
        "active_profile": None,
        "profiles": {},
        "last_updated": datetime.now().isoformat(),
    }
    _save_config(config)
    return config


def _save_config(config):
    """حفظ الإعدادات."""
    _ensure_dirs()
    config["last_updated"] = datetime.now().isoformat()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_all_profiles():
    """إرجاع كل البروفايلات (الافتراضية + المحفوظة)."""
    config = _load_config()
    profiles = {**DEFAULT_PROFILES}
    # إضافة أي بروفايلات محفوظة من قبل المستخدم
    profiles.update(config.get("profiles", {}))
    return profiles


def get_active_profile(mining_type=None):
    """
    إرجاع البروفايل النشط.
    إذا كان mining_type محدداً، يُرجّع البروفايل النشط لذلك النوع.
    """
    config = _load_config()
    active = config.get("active_profile")
    profiles = get_all_profiles()
    
    if active and active in profiles:
        profile = profiles[active]
        if mining_type is None or profile.get("mining_type") == mining_type:
            return profile
    
    # الافتراضي: literature profile
    if mining_type:
        key = f"{mining_type}_literature"
        return profiles.get(key, profiles.get("traditional_literature"))
    
    return profiles.get("traditional_literature")


def set_active_profile(profile_key):
    """تعيين البروفايل النشط."""
    profiles = get_all_profiles()
    if profile_key not in profiles:
        return False
    config = _load_config()
    config["active_profile"] = profile_key
    _save_config(config)
    return True


def save_calibrated_profile(mining_type, result, n_sites):
    """
    حفظ بروفايل مُعاير من البيانات.
    يُستدعى من تبويب المعايرة.
    """
    profile_key = f"{mining_type}_calibrated"
    profile = {
        "name_ar": f"{'⛏️' if mining_type=='traditional' else '🏭' if mining_type=='industrial' else '🔀'} {mining_type} — مُعاير",
        "name_en": f"{'⛏️' if mining_type=='traditional' else '🏭' if mining_type=='industrial' else '🔀'} {mining_type} — Calibrated",
        "mining_type": mining_type,
        "source": "Grid Search on local data",
        "source_type": "calibrated",
        "alpha": result["best_alpha"],
        "beta": result["best_beta"],
        "SF": result["best_SF"],
        "kappa": result["best_kappa"],
        "recall": result.get("best_recall", 0),
        "n_sites": n_sites,
        "date_created": datetime.now().isoformat(),
        "verified": True,
        "description_ar": f"أوزان مُعايرة على {n_sites} موقع {mining_type}",
        "description_en": f"Weights calibrated on {n_sites} {mining_type} sites",
    }
    config = _load_config()
    if "profiles" not in config:
        config["profiles"] = {}
    config["profiles"][profile_key] = profile
    config["active_profile"] = profile_key
    _save_config(config)
    return profile_key


def detect_ceiling_effect(df, mining_type):
    """
    كشف Ceiling Effect في CN Score.
    إذا كانت كل المواقع الملوثة في السقف (30) → تحذير.
    """
    import pandas as pd
    if df is None or "cn_water_mg_l" not in df.columns:
        return False
    if "actual_contaminated" not in df.columns:
        return False
    
    contaminated = df[df["actual_contaminated"] == 1]
    if len(contaminated) == 0:
        return False
    
    CN_LIMIT = 0.05
    # حساب CN Score لكل موقع ملوّث
    cn_scores = contaminated["cn_water_mg_l"].apply(
        lambda x: min(30.0, (x / CN_LIMIT) * 30.0) if x > 0 else 0
    )
    
    # إذا كان 80% أو أكثر في السقف (≥ 29.5) → Ceiling Effect
    at_ceiling = (cn_scores >= 29.5).sum()
    ratio = at_ceiling / len(cn_scores)
    return ratio >= 0.8


def get_profile_summary():
    """إرجاع ملخص للبروفايل النشط."""
    profile = get_active_profile()
    if not profile:
        return "لا يوجد بروفايل نشط"
    return {
        "name": profile["name_ar"],
        "alpha": profile["alpha"],
        "beta": profile["beta"],
        "SF": profile["SF"],
        "source": profile["source"],
        "kappa": profile.get("kappa"),
        "warning": profile.get("warning_ar"),
}
