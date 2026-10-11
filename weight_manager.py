"""
weight_manager.py  v61 - drop-in replacement (same public API as before)
Requires: drastic_core.py in the same folder.

Changes
  * the hard-coded "literature" and "calibrated" profiles are gone: they had no
    verified source, and the "calibrated" ones were identical for two different datasets
  * default profile = equal weights (alpha = beta = SF = 1): a null assumption, not a finding
  * saved profiles carry scoring_version; profiles made with older formulas are ignored
  * config is written atomically (no half-written JSON)
  * calibrated profiles are saved but NOT auto-activated and are marked verified = False
  * detect_ceiling_effect uses the new scoring and checks BOTH CN and Hg
NOTE: the config file lives on the server disk and is shared by all users; on
Streamlit Community Cloud it is also wiped when the app restarts.
"""
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime
import drastic_core as dc

SCORING_VERSION = "v61"
WEIGHTS_DIR = Path(__file__).parent / "weights"
PROFILES_DIR = WEIGHTS_DIR / "profiles"
CONFIG_FILE = WEIGHTS_DIR / "weights_config.json"

_ICON = {"traditional": "⛏️", "industrial": "🏭", "mixed": "🔀"}


def _default_profile(mt):
    return {
        "name_ar": f"{_ICON[mt]} {mt} — افتراضي (أوزان متساوية)",
        "name_en": f"{_ICON[mt]} {mt} — Default (equal weights)",
        "mining_type": mt,
        "source": "Null assumption (equal weights); not derived from data or literature",
        "source_type": "default",
        "alpha": 1.0, "beta": 1.0, "SF": 1.0,
        "kappa": None, "n_sites": None, "date_created": "2026-10-11",
        "verified": False, "scoring_version": SCORING_VERSION,
        "description_ar": "فرضية صفرية: وزن متساوٍ لـ CN وHg. تحتاج تحليل حساسية.",
        "description_en": "Null assumption: equal CN and Hg weights. Needs sensitivity analysis.",
    }


DEFAULT_PROFILES = {f"{mt}_default": _default_profile(mt) for mt in _ICON}


def _ensure_dirs():
    WEIGHTS_DIR.mkdir(exist_ok=True)
    PROFILES_DIR.mkdir(exist_ok=True)


def _save_config(config):
    _ensure_dirs()
    config["last_updated"] = datetime.now().isoformat()
    fd, tmp = tempfile.mkstemp(dir=str(WEIGHTS_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CONFIG_FILE)               # atomic on the same filesystem
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _load_config():
    _ensure_dirs()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    config = {"active_profile": None, "profiles": {}}
    _save_config(config)
    return config


def get_stale_profiles():
    """Saved profiles made with a different scoring version (ignored)."""
    saved = _load_config().get("profiles", {})
    return [k for k, v in saved.items() if v.get("scoring_version") != SCORING_VERSION]


def get_all_profiles():
    profiles = {**DEFAULT_PROFILES}
    for k, v in _load_config().get("profiles", {}).items():
        if v.get("scoring_version") == SCORING_VERSION:
            profiles[k] = v
    return profiles


def get_active_profile(mining_type=None):
    config = _load_config()
    profiles = get_all_profiles()
    active = config.get("active_profile")
    if active in profiles:
        p = profiles[active]
        if mining_type is None or p.get("mining_type") == mining_type:
            return p
    return profiles.get(f"{mining_type}_default", profiles["traditional_default"])


def set_active_profile(profile_key):
    if profile_key not in get_all_profiles():
        return False
    config = _load_config()
    config["active_profile"] = profile_key
    _save_config(config)
    return True


def save_calibrated_profile(mining_type, result, n_sites):
    """Saves (does NOT activate) a calibrated profile. result = auto_calibrate_weights output."""
    key = f"{mining_type}_calibrated"
    icon = _ICON.get(mining_type, "")
    profile = {
        "name_ar": f"{icon} {mining_type} — مُعاير",
        "name_en": f"{icon} {mining_type} — Calibrated",
        "mining_type": mining_type,
        "source": "Grid search + nested leave-one-out (auto_calibration v61)",
        "source_type": "calibrated",
        "alpha": result["best_alpha"], "beta": result["best_beta"],
        "SF": result.get("best_SF", 1.0),
        "kappa": result["best_kappa"],                       # nested LOO estimate
        "resubstitution_kappa": result.get("resubstitution_kappa"),
        "recall": result.get("best_recall", 0),
        "threshold": result.get("threshold"),
        "n_sites": n_sites,
        "warnings": result.get("warnings", []),
        "date_created": datetime.now().isoformat(),
        "verified": False, "scoring_version": SCORING_VERSION,
        "description_ar": f"أوزان مُعايرة على {n_sites} موقع ({mining_type}) - غير مُتحقَّق منها خارجياً",
        "description_en": f"Weights calibrated on {n_sites} {mining_type} sites - not externally validated",
    }
    config = _load_config()
    config.setdefault("profiles", {})[key] = profile
    _save_config(config)
    return key


def ceiling_report(df, frac=0.95):
    """Share of contaminated sites whose CN / Hg score is at the cap (>= frac x 30)."""
    if df is None or "actual_contaminated" not in df.columns:
        return {"cn": None, "hg": None, "any": False}
    c = df[df["actual_contaminated"] == 1]
    if len(c) == 0:
        return {"cn": None, "hg": None, "any": False}
    out = {}
    for name, col, lim in (("cn", "cn_water_mg_l", dc.LIMITS_MG_L["EU"]["cn"]),
                           ("hg", "hg_water_mg_l", dc.LIMITS_MG_L["EU"]["hg"])):
        if col not in c.columns:
            out[name] = None
            continue
        s = c[col].apply(lambda x: dc.hazard_score(float(x), lim) if x > 0 else 0.0)
        out[name] = round(float((s >= frac * 30.0).mean()), 2)
    out["any"] = any(v is not None and v >= 0.8 for v in (out["cn"], out["hg"]))
    return out


def detect_ceiling_effect(df, mining_type):
    return ceiling_report(df)["any"]


def get_profile_summary():
    p = get_active_profile()
    return {"name": p["name_ar"], "alpha": p["alpha"], "beta": p["beta"], "SF": p["SF"],
            "source": p["source"], "kappa": p.get("kappa"),
            "warning": p.get("warning_ar")}
