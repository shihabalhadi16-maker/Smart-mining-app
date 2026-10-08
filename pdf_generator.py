"""
PDF Report Generator — DRASTIC-Tox v58.5.1
Author: Shihab Alhadi + Sarah Akasha
University of Khartoum, Faculty of Engineering

Generates professional English PDF reports.
Handles Arabic text safely by mapping to English equivalents.
Requires: fpdf2
"""
import datetime
from io import BytesIO


def _has_fpdf():
    try:
        from fpdf import FPDF
        return True, FPDF
    except ImportError:
        return False, None


# ============================================================
# COLOR PALETTE
# ============================================================
COLOR_PRIMARY = (92, 44, 22)
COLOR_ACCENT = (193, 154, 107)
COLOR_LOW = (56, 142, 60)
COLOR_MEDIUM = (251, 192, 45)
COLOR_HIGH = (245, 124, 0)
COLOR_VERY_HIGH = (211, 47, 47)
COLOR_LIGHT_BG = (250, 248, 243)


# ============================================================
# ARABIC → ENGLISH MAPPING (CRITICAL FIX)
# ============================================================
ARABIC_TO_ENGLISH = {
    # Risk levels
    "منخفض": "Low",
    "متوسط": "Medium",
    "مرتفع": "High",
    "مرتفع جدا": "Very High",
    "مرتفع جداً": "Very High",
    "خطر داهم": "Critical",
    # Actions
    "روتيني": "Routine monitoring",
    "مراقبة دورية": "Periodic monitoring",
    "إجراء عاجل": "Urgent action required",
    "اجراء عاجل": "Urgent action required",
    "إجراء فوري - خطر داهم": "Immediate action - Critical risk",
    "اجراء فوري - خطر داهم": "Immediate action - Critical risk",
    "إيقاف النشاط": "Stop activity",
    "ايقاف النشاط": "Stop activity",
    # Categories
    "آمن": "Safe",
    "امن": "Safe",
    "تحت المراقبة": "Under monitoring",
    "خطير": "Hazardous",
    "حرج": "Critical",
    # Mining types
    "تقليدي": "Traditional",
    "صناعي": "Industrial",
    "مختلط": "Mixed",
    # States
    "سنار": "Sennar",
    "كسلا": "Kassala",
    "نهر النيل": "River Nile",
    "الخرطوم": "Khartoum",
    "شمال الخرطوم": "North Khartoum",
    "البحر الأحمر": "Red Sea",
    "نهر النيل - بربر": "Berber",
    "نهر النيل - أبو حمد": "Abu Hamad",
    # Generic
    "لا": "No",
    "نعم": "Yes",
    "غير معروف": "Unknown",
    "ملوث": "Contaminated",
    "نظيف": "Clean",
}


def _to_english(text, default="N/A"):
    """Convert Arabic text to English safely. Never crashes."""
    if text is None:
        return default
    text = str(text).strip()
    if not text:
        return default

    # Direct map lookup
    if text in ARABIC_TO_ENGLISH:
        return ARABIC_TO_ENGLISH[text]

    # Try partial match
    for ar, en in ARABIC_TO_ENGLISH.items():
        if ar in text:
            return en

    # Strip non-Latin-1 characters safely
    result = []
    for ch in text:
        try:
            ch.encode('latin-1')
            result.append(ch)
        except UnicodeEncodeError:
            continue
    cleaned = ''.join(result).strip()
    return cleaned if cleaned else default


def _safe_str(value, default="N/A"):
    """Convert any value to a safe Latin-1 string for PDF."""
    if value is None:
        return default
    try:
        s = str(value)
        # Try direct encoding first
        s.encode('latin-1')
        return s
    except UnicodeEncodeError:
        # Fall back to translation mapping
        return _to_english(value, default)


def _get_level_color(level_en):
    """Return RGB tuple based on English risk level."""
    level = (level_en or "").lower()
    if "critical" in level or "very high" in level:
        return COLOR_VERY_HIGH
    if "high" in level:
        return COLOR_HIGH
    if "medium" in level:
        return COLOR_MEDIUM
    return COLOR_LOW


def _level_english(level_input):
    """Convert any level input to canonical English."""
    if not level_input:
        return "Unknown"
    s = str(level_input).strip()
    # If already English
    if s.lower() in ["low", "medium", "high", "very high", "critical"]:
        return s.title()
    # Map Arabic
    mapped = _to_english(s, "Unknown")
    # Normalize
    low = mapped.lower()
    if "very high" in low: return "Very High"
    if "critical" in low: return "Critical"
    if "high" in low: return "High"
    if "medium" in low: return "Medium"
    if "low" in low: return "Low"
    return mapped


# ============================================================
# MAIN PDF GENERATOR
# ============================================================

def generate_pdf_report(site_info, drastic, drastic_t, level, recommendation,
                          cn_score=None, hg_score=None, base_bonus=None,
                          source_factor=None, toxicity_bonus=None,
                          cn_value=None, hg_value=None):
    """
    Generate a professional PDF report (English).

    All inputs are sanitized automatically. Arabic text is mapped to English.
    """
    ok, FPDF = _has_fpdf()
    if not ok:
        return None

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ============================================================
    # HEADER
    # ============================================================
    pdf.set_fill_color(*COLOR_PRIMARY)
    pdf.rect(0, 0, 210, 40, style="F")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_xy(10, 12)
    pdf.cell(190, 10, "DRASTIC-Tox Report", ln=True, align="C")

    pdf.set_font("Helvetica", "I", 11)
    pdf.set_xy(10, 24)
    pdf.cell(190, 8, "Groundwater Contamination Risk Assessment", ln=True, align="C")

    # ============================================================
    # META
    # ============================================================
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(10, 50)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(90, 6, f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=False)
    pdf.cell(90, 6, "Version: v58.5.1", ln=True, align="R")

    pdf.ln(4)
    pdf.set_draw_color(*COLOR_ACCENT)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # ============================================================
    # 1. SITE INFORMATION
    # ============================================================
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 8, "1. Site Information", ln=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)

    site_name = _safe_str(site_info.get("name", "N/A"), "Unknown Site")
    state = _safe_str(site_info.get("state", "N/A"), "N/A")
    coords = _safe_str(site_info.get("coords", "N/A"), "N/A")

    rows = [
        ("Site Name", site_name),
        ("State / Region", state),
        ("Coordinates", coords),
        ("Depth (m)", _safe_str(site_info.get("depth", "N/A"))),
        ("Recharge (mm/yr)", _safe_str(site_info.get("recharge", "N/A"))),
        ("Slope (%)", _safe_str(site_info.get("slope", "N/A"))),
        ("Conductivity (m/day)", _safe_str(site_info.get("conductivity", "N/A"))),
    ]
    for label, val in rows:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(*COLOR_LIGHT_BG)
        pdf.cell(70, 7, label, border=1, fill=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_fill_color(255, 255, 255)
        pdf.cell(110, 7, val, border=1, ln=True)

    pdf.ln(6)

    # ============================================================
    # 2. DRASTIC INDEX
    # ============================================================
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 8, "2. DRASTIC Index (Classical)", ln=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)

    pdf.set_fill_color(240, 240, 240)
    pdf.cell(70, 8, "DRASTIC Value", border=1, fill=True)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(60, 8, f"{drastic} / 230", border=1, ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_fill_color(*COLOR_LIGHT_BG)
    pdf.cell(70, 8, "Percentage of Maximum", border=1, fill=True)
    pdf.cell(60, 8, f"{round(drastic / 230 * 100, 1)}%", border=1, ln=True)

    pdf.ln(6)

    # ============================================================
    # 3. DRASTIC-TOX INDEX
    # ============================================================
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 8, "3. DRASTIC-Tox Index (Modified)", ln=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)

    pdf.set_fill_color(240, 240, 240)
    pdf.cell(70, 8, "DRASTIC-Tox Value", border=1, fill=True)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(60, 8, f"{drastic_t} / 280", border=1, ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_fill_color(*COLOR_LIGHT_BG)
    increase = round(drastic_t - drastic, 1)
    pdf.cell(70, 8, "Increase over DRASTIC", border=1, fill=True)
    pdf.cell(60, 8, f"+{increase}", border=1, ln=True)

    # Bonus components
    if cn_score is not None or hg_score is not None:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*COLOR_PRIMARY)
        pdf.cell(0, 7, "Toxicity Bonus Components", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 10)

        components = []
        if cn_value is not None:
            components.append(("CN concentration (mg/L)", _safe_str(cn_value)))
        if hg_value is not None:
            components.append(("Hg concentration (mg/L)", _safe_str(hg_value)))
        if cn_score is not None:
            components.append(("CN Score (max 30)", _safe_str(cn_score)))
        if hg_score is not None:
            components.append(("Hg Score (max 30)", _safe_str(hg_score)))
        if base_bonus is not None:
            components.append(("Base Bonus", _safe_str(base_bonus)))
        if source_factor is not None:
            components.append(("Source Factor (SF)", _safe_str(source_factor)))
        if toxicity_bonus is not None:
            components.append(("Final Toxicity Bonus", _safe_str(toxicity_bonus)))

        for label, val in components:
            pdf.set_fill_color(*COLOR_LIGHT_BG)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(90, 6, label, border=1, fill=True)
            pdf.set_fill_color(255, 255, 255)
            pdf.cell(70, 6, val, border=1, ln=True)

    pdf.ln(6)

    # ============================================================
    # 4. RISK ASSESSMENT
    # ============================================================
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 8, "4. Risk Assessment", ln=True)

    # Translate level to English
    level_en = _level_english(level)
    level_color = _get_level_color(level_en)

    # Colored level box
    pdf.set_fill_color(*level_color)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 14, f"  Risk Level: {level_en}  ", ln=True, fill=True, align="C")

    pdf.ln(4)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Recommended Action:", ln=True)
    pdf.set_font("Helvetica", "", 11)

    # Translate recommendation to English
    rec_en = _to_english(recommendation, "Consult with hydrogeologist")
    pdf.multi_cell(0, 6, rec_en)

    pdf.ln(8)

    # ============================================================
    # 5. INTERPRETATION NOTES
    # ============================================================
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 7, "5. Interpretation", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 5,
        "DRASTIC-Tox integrates cyanide (CN) and mercury (Hg) toxicity into the "
        "classical DRASTIC model. The Final Bonus reflects site-specific weighting "
        "based on mining pattern (traditional, industrial, or mixed). "
        "Scores above 140 indicate high contamination risk requiring urgent action.")

    pdf.ln(6)

    # ============================================================
    # FOOTER
    # ============================================================
    pdf.set_draw_color(*COLOR_ACCENT)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "Authors: Shihab Alhadi Saeed Dangal & Sarah Akasha Al-Tayeb Ali", ln=True, align="C")
    pdf.cell(0, 5, "University of Khartoum - Faculty of Engineering", ln=True, align="C")
    pdf.cell(0, 5, "DRASTIC-Tox v58.5.1 - Pilot Version", ln=True, align="C")

    pdf.ln(4)
    pdf.set_text_color(150, 50, 50)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 5,
        "DISCLAIMER: This is a screening tool for preliminary risk assessment. "
        "It does not replace laboratory analysis or field investigation. "
        "Results must be verified by qualified hydrogeologists.")

    # Return as bytes
    output = BytesIO()
    pdf_bytes = pdf.output(dest="S")
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode("latin-1")
    output.write(pdf_bytes)
    output.seek(0)
    return output.getvalue()
