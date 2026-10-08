"""
PDF Report Generator — DRASTIC-Tox v58.5
Author: Shihab Alhadi + Sarah Akasha
University of Khartoum, Faculty of Engineering

Generates professional PDF reports for individual sites.
Requires: fpdf2 (pip install fpdf2)
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
# COLOR PALETTE (RGB)
# ============================================================
COLOR_PRIMARY = (92, 44, 22)        # Brown #5c2c16
COLOR_ACCENT = (193, 154, 107)      # Tan #c19a6b
COLOR_LOW = (56, 142, 60)            # Green
COLOR_MEDIUM = (251, 192, 45)        # Yellow
COLOR_HIGH = (245, 124, 0)           # Orange
COLOR_VERY_HIGH = (211, 47, 47)      # Red
COLOR_LIGHT_BG = (250, 248, 243)     # Cream


def _get_level_color(level):
    """Return RGB tuple based on risk level."""
    level = (level or "").lower()
    if "very_high" in level or "مرتفع جداً" in level:
        return COLOR_VERY_HIGH
    if "high" in level or "مرتفع" in level:
        return COLOR_HIGH
    if "medium" in level or "متوسط" in level:
        return COLOR_MEDIUM
    return COLOR_LOW


def _sanitize_arabic(text):
    """Sanitize Arabic text for PDF (remove unsupported chars)."""
    if not text:
        return ""
    # Remove problematic unicode chars for basic PDF
    # Note: Full Arabic support requires a Unicode font
    return str(text).strip()


def generate_pdf_report(site_info, drastic, drastic_t, level, recommendation,
                          cn_score=None, hg_score=None, base_bonus=None,
                          source_factor=None, toxicity_bonus=None,
                          cn_value=None, hg_value=None):
    """
    Generate a professional PDF report.

    Parameters
    ----------
    site_info : dict with keys: name, state, coords, depth, recharge, slope, conductivity, cn, hg
    drastic : float — DRASTIC index (23-230)
    drastic_t : float — DRASTIC-Tox index (23-280)
    level : str — risk level
    recommendation : str — action text
    cn_score, hg_score, base_bonus, source_factor, toxicity_bonus : float (optional)
    cn_value, hg_value : float (optional)

    Returns
    -------
    bytes : PDF file content (BytesIO)
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
    pdf.cell(90, 6, "Version: v58.5", ln=True, align="R")

    pdf.ln(4)
    pdf.set_draw_color(*COLOR_ACCENT)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # ============================================================
    # SITE INFO
    # ============================================================
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 8, "1. Site Information", ln=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)

    site_name = site_info.get("name", "N/A")
    state = site_info.get("state", "N/A")
    coords = site_info.get("coords", "N/A")

    # Site table
    pdf.set_fill_color(*COLOR_LIGHT_BG)
    rows = [
        ("Site Name", str(site_name)),
        ("State", str(state)),
        ("Coordinates", str(coords)),
        ("Depth (m)", str(site_info.get("depth", "N/A"))),
        ("Recharge (mm/yr)", str(site_info.get("recharge", "N/A"))),
        ("Slope (%)", str(site_info.get("slope", "N/A"))),
        ("Conductivity (m/day)", str(site_info.get("conductivity", "N/A"))),
    ]
    for label, val in rows:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(60, 7, label, border=1, fill=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(120, 7, val, border=1, ln=True)

    pdf.ln(6)

    # ============================================================
    # DRASTIC INDEX
    # ============================================================
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 8, "2. DRASTIC Index (Classical)", ln=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)

    pdf.set_fill_color(240, 240, 240)
    pdf.cell(60, 8, "DRASTIC Value", border=1, fill=True)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(60, 8, f"{drastic} / 230", border=1, ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_fill_color(*COLOR_LIGHT_BG)
    pdf.cell(60, 8, "Percentage", border=1, fill=True)
    pdf.cell(60, 8, f"{round(drastic / 230 * 100, 1)}%", border=1, ln=True)

    pdf.ln(6)

    # ============================================================
    # DRASTIC-TOX INDEX
    # ============================================================
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 8, "3. DRASTIC-Tox Index (Modified)", ln=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)

    pdf.set_fill_color(240, 240, 240)
    pdf.cell(60, 8, "DRASTIC-Tox Value", border=1, fill=True)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(60, 8, f"{drastic_t} / 280", border=1, ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_fill_color(*COLOR_LIGHT_BG)
    increase = round(drastic_t - drastic, 1)
    pdf.cell(60, 8, "Increase over DRASTIC", border=1, fill=True)
    pdf.cell(60, 8, f"+{increase}", border=1, ln=True)

    # Bonus components (if provided)
    if cn_score is not None or hg_score is not None:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Toxicity Bonus Components", ln=True)
        pdf.set_font("Helvetica", "", 10)

        components = []
        if cn_value is not None:
            components.append(("CN concentration (mg/L)", str(cn_value)))
        if hg_value is not None:
            components.append(("Hg concentration (mg/L)", str(hg_value)))
        if cn_score is not None:
            components.append(("CN Score", str(cn_score)))
        if hg_score is not None:
            components.append(("Hg Score", str(hg_score)))
        if base_bonus is not None:
            components.append(("Base Bonus", str(base_bonus)))
        if source_factor is not None:
            components.append(("Source Factor (SF)", str(source_factor)))
        if toxicity_bonus is not None:
            components.append(("Final Toxicity Bonus", str(toxicity_bonus)))

        for label, val in components:
            pdf.set_fill_color(*COLOR_LIGHT_BG)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(80, 6, label, border=1, fill=True)
            pdf.cell(60, 6, val, border=1, ln=True)

    pdf.ln(6)

    # ============================================================
    # RISK ASSESSMENT (colored box)
    # ============================================================
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 8, "4. Risk Assessment", ln=True)

    # Colored level box
    level_color = _get_level_color(level)
    pdf.set_fill_color(*level_color)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 14, f"  Risk Level: {_sanitize_arabic(level)}  ", ln=True, fill=True, align="C")

    pdf.ln(4)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Recommended Action:", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, _sanitize_arabic(recommendation))

    pdf.ln(8)

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
    pdf.cell(0, 5, "DRASTIC-Tox v58.5 - Pilot Version", ln=True, align="C")

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
