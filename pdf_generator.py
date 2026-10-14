"""
PDF report generator - DRASTIC-Tox v61
University of Khartoum, Faculty of Engineering
Requires: fpdf2   (core Helvetica font => Latin-1 text only; Arabic text is mapped to English)

Changes vs v58.9
  * ranges fixed: DRASTIC 23-226 (not 230); DRASTIC-Tox is EXPERIMENTAL, 23-276 with equal weights
  * the Arabic->English step matched SUBSTRINGS: any text containing "لا" (e.g. inside "السلام")
    was replaced by "No". Now: exact match via the app's own translations, then whole words only
  * two-axis result (vulnerability x hazard) added; limits used are stated (EU Directive 98/83/EC)
  * the "scores above 140 = urgent action" claim is replaced by an honest interpretation note
  * fpdf2 calls use the current API (new_x/new_y) with a fallback for older versions
  * unit warnings supported
"""
import datetime
import re
from io import BytesIO

try:
    import drastic_core as dc
    from drastic_bridge import STANDARD, DRASTIC_MAX
except Exception:
    dc, STANDARD, DRASTIC_MAX = None, "EU", 226


def _has_fpdf():
    try:
        from fpdf import FPDF
        return True, FPDF
    except ImportError:
        return False, None


COLOR_PRIMARY = (92, 44, 22)
COLOR_ACCENT = (193, 154, 107)
COLOR_LOW = (56, 142, 60)
COLOR_MEDIUM = (251, 192, 45)
COLOR_HIGH = (245, 124, 0)
COLOR_VERY_HIGH = (211, 47, 47)
COLOR_LIGHT_BG = (250, 248, 243)

ARABIC_TO_ENGLISH = {
    "منخفض": "Low", "متوسط": "Medium", "مرتفع": "High", "مرتفع جدا": "Very High", "مرتفع جداً": "Very High",
    "روتيني": "Routine monitoring", "مراقبة دورية": "Periodic monitoring", "إجراء عاجل": "Urgent action required",
    "اجراء عاجل": "Urgent action required", "إيقاف النشاط": "Stop activity",
    "تقليدي": "Traditional", "صناعي": "Industrial", "مختلط": "Mixed",
    "سنار": "Sennar", "كسلا": "Kassala", "نهر النيل": "River Nile", "الخرطوم": "Khartoum", "البحر الأحمر": "Red Sea",
    "الشمالية": "Northern", "الجزيرة": "Gezira", "القضارف": "Gedaref", "النيل الأزرق": "Blue Nile",
    "النيل الأبيض": "White Nile", "شمال كردفان": "North Kordofan", "جنوب كردفان": "South Kordofan",
    "غرب كردفان": "West Kordofan", "شمال دارفور": "North Darfur", "جنوب دارفور": "South Darfur",
    "غرب دارفور": "West Darfur", "وسط دارفور": "Central Darfur", "شرق دارفور": "East Darfur",
    "ملوث": "Contaminated", "نظيف": "Clean", "نعم": "Yes", "لا": "No", "غير معروف": "Unknown",
}


def _latin(s):
    return "".join(ch for ch in str(s) if ord(ch) < 256).strip()


_REVERSE = None


def _reverse_map():
    """Arabic text -> English text taken from the app's own translations.py (exact strings)."""
    global _REVERSE
    if _REVERSE is None:
        _REVERSE = {}
        try:
            from translations import TEXTS
            ar, en = TEXTS["ar"], TEXTS["en"]
            for k, a in ar.items():
                e = en.get(k)
                if isinstance(a, str) and isinstance(e, str) and 0 < len(a) < 200:
                    _REVERSE.setdefault(a.strip(), _latin(e))
        except Exception:
            pass
    return _REVERSE


def _to_english(text, default="N/A"):
    """Arabic -> English without substring accidents. Never raises."""
    if text is None:
        return default
    text = str(text).strip()
    if not text:
        return default
    rev = _reverse_map()
    if text in rev and rev[text]:
        return rev[text]
    if text in ARABIC_TO_ENGLISH:
        return ARABIC_TO_ENGLISH[text]
    if not re.search(r"[\u0600-\u06FF]", text):          # already Latin: keep as is
        return _latin(text) or default
    words = [ARABIC_TO_ENGLISH.get(w, w) for w in re.split(r"\s+", text)]   # whole words only
    cleaned = _latin(" ".join(words))
    return cleaned if cleaned else default


def _safe_str(value, default="N/A"):
    if value is None:
        return default
    s = str(value)
    try:
        s.encode("latin-1")
        return s
    except UnicodeEncodeError:
        return _to_english(value, default)


def _level_color(level_en):
    low = (level_en or "").lower()
    if "critical" in low or "very high" in low:
        return COLOR_VERY_HIGH
    if "high" in low:
        return COLOR_HIGH
    if "medium" in low or "moderate" in low:
        return COLOR_MEDIUM
    return COLOR_LOW


def _level_english(level_input):
    if not level_input:
        return "Unknown"
    s = str(level_input).strip()
    if s.lower() in ("low", "medium", "high", "very high", "very_high", "critical"):
        return s.replace("_", " ").title()
    mapped = _to_english(s, "Unknown")
    low = mapped.lower()
    for key, out in (("very high", "Very High"), ("critical", "Critical"), ("high", "High"), ("medium", "Medium"), ("low", "Low")):
        if key in low:
            return out
    return mapped


# ---- fpdf2 compatibility helpers (new API first, legacy fallback) ----
def _cell(pdf, w, h, txt="", border=0, fill=False, align="", newline=False):
    try:
        pdf.cell(w, h, txt, border=border, fill=fill, align=align,
                 new_x="LMARGIN" if newline else "RIGHT", new_y="NEXT" if newline else "TOP")
    except TypeError:
        pdf.cell(w, h, txt, border=border, fill=fill, align=align, ln=1 if newline else 0)


def _multi(pdf, w, h, txt):
    try:
        pdf.multi_cell(w, h, txt, new_x="LMARGIN", new_y="NEXT")
    except TypeError:
        pdf.multi_cell(w, h, txt)


def _heading(pdf, text):
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*COLOR_PRIMARY)
    _cell(pdf, 0, 8, text, newline=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)


def _row(pdf, label, val, w1=70, w2=110):
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(*COLOR_LIGHT_BG)
    _cell(pdf, w1, 7, label, border=1, fill=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_fill_color(255, 255, 255)
    _cell(pdf, w2, 7, _safe_str(val), border=1, newline=True)


def _two_axis(site_info, drastic):
    if dc is None:
        return None
    try:
        cn, hg = float(site_info.get("cn")), float(site_info.get("hg"))
        L = dc.LIMITS_MG_L[STANDARD]
        hq = max(cn / L["cn"] if L["cn"] else 0.0, hg / L["hg"])
        v, vp = dc.vulnerability_class(float(drastic))
        h = dc.hazard_class(hq)
        return {"vuln": v, "vuln_pct": vp, "hazard": h, "hq": round(hq, 1), "risk": dc.risk_category(v, h), "limits": L}
    except Exception:
        return None


def generate_pdf_report(site_info, drastic, drastic_t, level, recommendation, cn_score=None, hg_score=None,
                        base_bonus=None, source_factor=None, toxicity_bonus=None, cn_value=None, hg_value=None,
                        warnings=None):
    """Generate the PDF (bytes), or None if fpdf2 is missing. Inputs are sanitised automatically."""
    ok, FPDF = _has_fpdf()
    if not ok:
        return None
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_fill_color(*COLOR_PRIMARY)
    pdf.rect(0, 0, 210, 40, style="F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_xy(10, 12)
    _cell(pdf, 190, 10, "DRASTIC-Tox Report", align="C", newline=True)
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_xy(10, 24)
    _cell(pdf, 190, 8, "Groundwater Vulnerability & Contamination Hazard Screening", align="C", newline=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(10, 50)
    pdf.set_font("Helvetica", "", 10)
    _cell(pdf, 90, 6, f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    _cell(pdf, 90, 6, "Version: v61", align="R", newline=True)
    pdf.ln(4)
    pdf.set_draw_color(*COLOR_ACCENT)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    _heading(pdf, "1. Site Information")
    _row(pdf, "Site Name", _safe_str(site_info.get("name"), "Unknown Site"))
    _row(pdf, "State / Region", site_info.get("state", "N/A"))
    if site_info.get("mining_type"):
        _row(pdf, "Mining Type", _to_english(site_info.get("mining_type")))
    for label, key in (("Coordinates", "coords"), ("Depth (m)", "depth"), ("Recharge (mm/yr)", "recharge"),
                       ("Slope (%)", "slope"), ("Conductivity (m/day)", "conductivity")):
        _row(pdf, label, site_info.get(key, "N/A"))
    pdf.ln(6)

    _heading(pdf, f"2. Vulnerability: DRASTIC Index (range 23-{DRASTIC_MAX})")
    pct = round((float(drastic) - 23) / (DRASTIC_MAX - 23) * 100, 1)
    _row(pdf, "DRASTIC Value", f"{drastic} / {DRASTIC_MAX}", 70, 60)
    _row(pdf, "Position within range", f"{pct}%", 70, 60)
    pdf.ln(6)

    ta = _two_axis(site_info, drastic)
    if ta:
        _heading(pdf, "3. Two-axis Assessment (recommended)")
        _row(pdf, "Vulnerability class", f"{ta['vuln'].replace('_', ' ').title()} ({ta['vuln_pct']}% of range)")
        _row(pdf, "Hazard class", f"{ta['hazard'].title()} (max conc/limit = {ta['hq']})")
        _row(pdf, "Combined risk", ta["risk"].replace("_", " ").title())
        _row(pdf, "Limits used", f"{STANDARD}: CN {ta['limits']['cn']}, Hg {ta['limits']['hg']} mg/L")
        pdf.ln(6)

    _heading(pdf, "4. DRASTIC-Tox (EXPERIMENTAL, range 23-276 with equal weights)")
    _row(pdf, "DRASTIC-Tox Value", f"{drastic_t}", 70, 60)
    _row(pdf, "Increase over DRASTIC", f"+{round(float(drastic_t) - float(drastic), 1)}", 70, 60)
    comps = [("CN concentration (mg/L)", cn_value), ("Hg concentration (mg/L)", hg_value), ("CN Score (max 30)", cn_score),
             ("Hg Score (max 30)", hg_score), ("Base Bonus", base_bonus), ("Source Factor (SF)", source_factor),
             ("Final Toxicity Bonus", toxicity_bonus)]
    comps = [(a, b) for a, b in comps if b is not None]
    if comps:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*COLOR_PRIMARY)
        _cell(pdf, 0, 7, "Toxicity Bonus Components", newline=True)
        pdf.set_text_color(0, 0, 0)
        for a, b in comps:
            _row(pdf, a, b, 90, 70)
    pdf.ln(6)

    _heading(pdf, "5. Risk Level (index bands)")
    level_en = _level_english(level)
    pdf.set_fill_color(*_level_color(level_en))
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    _cell(pdf, 0, 14, f"Risk Level: {level_en}", fill=True, align="C", newline=True)
    pdf.ln(4)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 11)
    _cell(pdf, 0, 7, "Recommended Action:", newline=True)
    pdf.set_font("Helvetica", "", 11)
    _multi(pdf, 0, 6, _to_english(recommendation, "Consult a hydrogeologist"))
    pdf.ln(4)

    if warnings:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(150, 50, 50)
        _cell(pdf, 0, 6, "Data warnings:", newline=True)
        pdf.set_font("Helvetica", "", 9)
        for w in warnings:
            _multi(pdf, 0, 5, "- " + _to_english(w, ""))
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*COLOR_PRIMARY)
    _cell(pdf, 0, 7, "6. Interpretation", newline=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)
    _multi(pdf, 0, 5,
           "DRASTIC (Aller et al., 1987) measures INTRINSIC vulnerability, not actual contamination. The hazard axis compares "
           "measured cyanide and mercury with drinking-water limits. DRASTIC-Tox adds a log-scaled hazard score to DRASTIC; it is an "
           "experimental formulation without external validation, and its weights and class bands are conventions, not standards. "
           "Use it to prioritise sites for sampling, not to declare a site safe or contaminated.")
    pdf.ln(6)

    pdf.set_draw_color(*COLOR_ACCENT)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    _cell(pdf, 0, 5, "University of Khartoum - Faculty of Engineering", align="C", newline=True)
    _cell(pdf, 0, 5, "DRASTIC-Tox v61 - Pilot Version", align="C", newline=True)
    pdf.ln(4)
    pdf.set_text_color(150, 50, 50)
    _multi(pdf, 0, 5, "DISCLAIMER: screening tool for preliminary assessment. It does not replace laboratory analysis or "
                      "field investigation; results must be verified by qualified hydrogeologists.")

    try:
        out = pdf.output()                      # fpdf2: bytearray
    except TypeError:
        out = pdf.output(dest="S")
    if isinstance(out, str):
        out = out.encode("latin-1")
    return bytes(out)
