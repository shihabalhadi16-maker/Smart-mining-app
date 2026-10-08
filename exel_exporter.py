"""
Excel Multi-sheet Exporter — DRASTIC-Tox v58.6
Author: Shihab Alhadi + Sarah Akasha
University of Khartoum, Faculty of Engineering

Generates comprehensive Excel reports with 5 sheets:
    1. Summary — Site info + main indices
    2. DRASTIC Breakdown — Per-parameter analysis
    3. SPSA — Single Parameter Sensitivity Analysis
    4. Monte Carlo — Uncertainty simulation
    5. Metadata — Report generation info

Requires: openpyxl (already in requirements)
"""
import datetime
from io import BytesIO


def _has_openpyxl():
    try:
        from openpyxl import Workbook
        return True, Workbook
    except ImportError:
        return False, None


COLOR_PRIMARY = "5C2C16"
COLOR_ACCENT = "C19A6B"
COLOR_LIGHT_BG = "FAF8F3"
COLOR_LOW = "388E3C"
COLOR_MEDIUM = "FBC02D"
COLOR_HIGH = "F57C00"
COLOR_VERY_HIGH = "D32F2F"
COLOR_WHITE = "FFFFFF"


def _style_header(cell, bg_color=COLOR_PRIMARY, font_color=COLOR_WHITE, size=12):
    from openpyxl.styles import Font, PatternFill, Alignment
    cell.font = Font(bold=True, color=font_color, size=size)
    cell.fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type="solid")
    cell.alignment = Alignment(horizontal="center", vertical="center")


def _style_title(cell, size=14):
    from openpyxl.styles import Font, Alignment
    cell.font = Font(bold=True, color=COLOR_PRIMARY, size=size)
    cell.alignment = Alignment(horizontal="left", vertical="center")


def _style_label(cell, bold=True):
    from openpyxl.styles import Font, PatternFill, Alignment
    cell.font = Font(bold=bold, color=COLOR_PRIMARY, size=10)
    cell.fill = PatternFill(start_color=COLOR_LIGHT_BG, end_color=COLOR_LIGHT_BG, fill_type="solid")
    cell.alignment = Alignment(horizontal="left", vertical="center")


def _style_value(cell, bold=False):
    from openpyxl.styles import Font, Alignment
    cell.font = Font(bold=bold, size=10)
    cell.alignment = Alignment(horizontal="left", vertical="center")


def _get_level_color_hex(level_str):
    level = (level_str or "").lower()
    if "very_high" in level or "مرتفع جدا" in level or "مرتفع جداً" in level or "critical" in level:
        return COLOR_VERY_HIGH
    if "high" in level or "مرتفع" in level:
        return COLOR_HIGH
    if "medium" in level or "متوسط" in level:
        return COLOR_MEDIUM
    return COLOR_LOW


def generate_excel_report(
    site_info,
    drastic_result,
    risk_info,
    mining_type,
    spsa_result=None,
    mc_result=None,
):
    """
    Generate Excel report with 5 sheets. Returns bytes.

    Parameters
    ----------
    site_info : dict with name, state, coords, depth, recharge, slope,
                conductivity, cn, hg, aquifer, soil, vadose
    drastic_result : dict from calc_drastic_t (base_drastic, cn_score,
                    hg_score, base_bonus, source_factor, toxicity_bonus,
                    drastic_t, increase_pct)
    risk_info : dict from classify (level, action)
    mining_type : str
    spsa_result : dict (optional)
    mc_result : dict (optional)
    """
    ok, Workbook = _has_openpyxl()
    if not ok:
        return None

    from openpyxl.styles import Font, PatternFill, Alignment

    wb = Workbook()

    # ==========================================================
    # SHEET 1: SUMMARY
    # ==========================================================
    ws = wb.active
    ws.title = "Summary"

    ws["A1"] = "DRASTIC-Tox Report — Site Summary"
    _style_title(ws["A1"], size=16)
    ws.merge_cells("A1:D1")
    ws.row_dimensions[1].height = 30

    ws["A2"] = f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ws["A2"].font = Font(italic=True, size=9, color="666666")
    ws.merge_cells("A2:D2")

    row = 4
    ws.cell(row=row, column=1, value="SITE INFORMATION")
    _style_header(ws.cell(row=row, column=1))
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    row += 1

    site_rows = [
        ("Site Name", site_info.get("name", "N/A")),
        ("State", site_info.get("state", "N/A")),
        ("Coordinates", site_info.get("coords", "N/A")),
        ("Mining Type", mining_type),
        ("Depth (m)", site_info.get("depth", "N/A")),
        ("Recharge (mm/yr)", site_info.get("recharge", "N/A")),
        ("Slope (%)", site_info.get("slope", "N/A")),
        ("Conductivity (m/day)", site_info.get("conductivity", "N/A")),
        ("Aquifer", site_info.get("aquifer", "N/A")),
        ("Soil", site_info.get("soil", "N/A")),
        ("Vadose", site_info.get("vadose", "N/A")),
    ]
    for label, val in site_rows:
        ws.cell(row=row, column=1, value=label)
        _style_label(ws.cell(row=row, column=1))
        ws.cell(row=row, column=2, value=str(val))
        _style_value(ws.cell(row=row, column=2))
        row += 1

    row += 1
    ws.cell(row=row, column=1, value="INDICES")
    _style_header(ws.cell(row=row, column=1))
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    row += 1

    idx_rows = [
        ("DRASTIC Index", f"{drastic_result.get('base_drastic', 'N/A')} / 230"),
        ("CN Score", drastic_result.get("cn_score", "N/A")),
        ("Hg Score", drastic_result.get("hg_score", "N/A")),
        ("Base Bonus", drastic_result.get("base_bonus", "N/A")),
        ("Source Factor (SF)", drastic_result.get("source_factor", "N/A")),
        ("Final Bonus", drastic_result.get("toxicity_bonus", "N/A")),
        ("DRASTIC-Tox Index", f"{drastic_result.get('drastic_t', 'N/A')} / 280"),
        ("Increase", f"+{drastic_result.get('increase_pct', 0)}%"),
    ]
    for label, val in idx_rows:
        ws.cell(row=row, column=1, value=label)
        _style_label(ws.cell(row=row, column=1))
        ws.cell(row=row, column=2, value=str(val))
        _style_value(ws.cell(row=row, column=2), bold=True)
        row += 1

    row += 1
    ws.cell(row=row, column=1, value="RISK ASSESSMENT")
    _style_header(ws.cell(row=row, column=1))
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    row += 1

    level_str = str(risk_info.get("level", "N/A"))
    color_hex = _get_level_color_hex(level_str)

    ws.cell(row=row, column=1, value="Risk Level")
    _style_label(ws.cell(row=row, column=1))
    cell = ws.cell(row=row, column=2, value=level_str)
    cell.font = Font(bold=True, color=COLOR_WHITE, size=12)
    cell.fill = PatternFill(start_color=color_hex, end_color=color_hex, fill_type="solid")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    row += 1

    ws.cell(row=row, column=1, value="Recommended Action")
    _style_label(ws.cell(row=row, column=1))
    ws.cell(row=row, column=2, value=str(risk_info.get("action", "N/A")))
    _style_value(ws.cell(row=row, column=2))

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 40
    ws.column_dimensions["C"].width = 15
    ws.column_dimensions["D"].width = 15

    # ==========================================================
    # SHEET 2: DRASTIC BREAKDOWN
    # ==========================================================
    ws2 = wb.create_sheet("DRASTIC Breakdown")
    ws2["A1"] = "DRASTIC Parameter Breakdown"
    _style_title(ws2["A1"], size=16)
    ws2.merge_cells("A1:E1")
    ws2.row_dimensions[1].height = 30

    headers = ["Parameter", "Weight (Wi)", "Rating (Ri)", "Wi × Ri", "Contribution %"]
    for col, h in enumerate(headers, 1):
        cell = ws2.cell(row=3, column=col, value=h)
        _style_header(cell, bg_color=COLOR_ACCENT, font_color=COLOR_PRIMARY, size=11)

    params = [
        ("D — Depth to Water", 5, site_info.get("D_rating", "—")),
        ("R — Net Recharge", 4, site_info.get("R_rating", "—")),
        ("A — Aquifer Media", 3, site_info.get("A_rating", "—")),
        ("S — Soil Media", 2, site_info.get("S_rating", "—")),
        ("T — Topography", 1, site_info.get("T_rating", "—")),
        ("I — Impact of Vadose", 5, site_info.get("I_rating", "—")),
        ("C — Hydraulic Conductivity", 3, site_info.get("C_rating", "—")),
    ]

    total_weighted = 0
    for _, w, r in params:
        if isinstance(r, (int, float)):
            total_weighted += w * r

    row = 4
    for name, w, r in params:
        ws2.cell(row=row, column=1, value=name)
        _style_value(ws2.cell(row=row, column=1))
        ws2.cell(row=row, column=2, value=w)
        _style_value(ws2.cell(row=row, column=2))
        ws2.cell(row=row, column=3, value=r)
        _style_value(ws2.cell(row=row, column=3))
        if isinstance(r, (int, float)):
            ws2.cell(row=row, column=4, value=w * r)
            _style_value(ws2.cell(row=row, column=4))
            contrib = round((w * r / total_weighted) * 100, 2) if total_weighted > 0 else 0
            ws2.cell(row=row, column=5, value=f"{contrib}%")
            _style_value(ws2.cell(row=row, column=5))
        else:
            ws2.cell(row=row, column=4, value="—")
            ws2.cell(row=row, column=5, value="—")
        row += 1

    row += 1
    ws2.cell(row=row, column=1, value="TOTAL DRASTIC")
    _style_header(ws2.cell(row=row, column=1))
    ws2.cell(row=row, column=2, value=sum(w for _, w, _ in params))
    _style_header(ws2.cell(row=row, column=2), bg_color=COLOR_ACCENT, font_color=COLOR_PRIMARY)
    ws2.cell(row=row, column=3, value="—")
    _style_header(ws2.cell(row=row, column=3), bg_color=COLOR_ACCENT, font_color=COLOR_PRIMARY)
    ws2.cell(row=row, column=4, value=total_weighted)
    _style_header(ws2.cell(row=row, column=4), bg_color=COLOR_ACCENT, font_color=COLOR_PRIMARY)
    ws2.cell(row=row, column=5, value="100%")
    _style_header(ws2.cell(row=row, column=5), bg_color=COLOR_ACCENT, font_color=COLOR_PRIMARY)

    ws2.column_dimensions["A"].width = 30
    ws2.column_dimensions["B"].width = 15
    ws2.column_dimensions["C"].width = 15
    ws2.column_dimensions["D"].width = 15
    ws2.column_dimensions["E"].width = 18

    # ==========================================================
    # SHEET 3: SPSA
    # ==========================================================
    if spsa_result and "parameters" in spsa_result:
        ws3 = wb.create_sheet("SPSA")
        ws3["A1"] = "Single Parameter Sensitivity Analysis (SPSA)"
        _style_title(ws3["A1"], size=16)
        ws3.merge_cells("A1:G1")
        ws3.row_dimensions[1].height = 30

        ws3["A2"] = "Reference: Napolitano & Fabbri (1996)"
        ws3["A2"].font = Font(italic=True, size=9, color="666666")
        ws3.merge_cells("A2:G2")

        headers3 = ["Parameter", "Wi", "Ri", "Wi × Ri", "Theoretical %", "Effective %", "Difference %"]
        for col, h in enumerate(headers3, 1):
            cell = ws3.cell(row=4, column=col, value=h)
            _style_header(cell, bg_color=COLOR_ACCENT, font_color=COLOR_PRIMARY, size=11)

        row = 5
        for p in spsa_result["parameters"]:
            ws3.cell(row=row, column=1, value=p["param"])
            _style_value(ws3.cell(row=row, column=1))
            ws3.cell(row=row, column=2, value=p["weight"])
            _style_value(ws3.cell(row=row, column=2))
            ws3.cell(row=row, column=3, value=p["rating"])
            _style_value(ws3.cell(row=row, column=3))
            ws3.cell(row=row, column=4, value=p["weighted_score"])
            _style_value(ws3.cell(row=row, column=4))
            ws3.cell(row=row, column=5, value=f"{p['theoretical_pct']}%")
            _style_value(ws3.cell(row=row, column=5))
            ws3.cell(row=row, column=6, value=f"{p['effective_pct']}%")
            _style_value(ws3.cell(row=row, column=6))
            diff_cell = ws3.cell(row=row, column=7, value=f"{p['difference']:+.2f}%")
            if p["difference"] > 0:
                diff_cell.font = Font(bold=True, color="2E7D32")
            elif p["difference"] < 0:
                diff_cell.font = Font(bold=True, color="C62828")
            row += 1

        row += 1
        ws3.cell(row=row, column=1, value="Most Influential:")
        _style_label(ws3.cell(row=row, column=1))
        ws3.cell(row=row, column=2, value=spsa_result.get("most_influential", "—"))
        row += 1
        ws3.cell(row=row, column=1, value="Base Index (DI):")
        _style_label(ws3.cell(row=row, column=1))
        ws3.cell(row=row, column=2, value=spsa_result.get("base_index", "—"))

        for col, w in [("A", 15), ("B", 10), ("C", 10), ("D", 12), ("E", 16), ("F", 14), ("G", 14)]:
            ws3.column_dimensions[col].width = w

    # ==========================================================
    # SHEET 4: MONTE CARLO
    # ==========================================================
    if mc_result:
        ws4 = wb.create_sheet("Monte Carlo")
        ws4["A1"] = "Monte Carlo Uncertainty Analysis"
        _style_title(ws4["A1"], size=16)
        ws4.merge_cells("A1:C1")
        ws4.row_dimensions[1].height = 30

        ws4["A2"] = f"Iterations: {mc_result.get('n_iter', 'N/A')}  |  Variation: {mc_result.get('variation_pct', 'N/A')}%"
        ws4["A2"].font = Font(italic=True, size=9, color="666666")
        ws4.merge_cells("A2:C2")

        ws4.cell(row=4, column=1, value="DRASTIC")
        _style_header(ws4.cell(row=4, column=1))
        ws4.merge_cells("A4:C4")

        mc_rows = [
            ("Mean", mc_result.get("mean", "—")),
            ("Std Dev", mc_result.get("std", "—")),
            ("Minimum", mc_result.get("min", "—")),
            ("Maximum", mc_result.get("max", "—")),
            ("CI 90%", f"{mc_result.get('ci_90', ('—', '—'))[0]} - {mc_result.get('ci_90', ('—', '—'))[1]}"),
            ("P(index > 140)", f"{mc_result.get('prob_over_140', '—')}%"),
        ]
        row = 5
        for label, val in mc_rows:
            ws4.cell(row=row, column=1, value=label)
            _style_label(ws4.cell(row=row, column=1))
            ws4.cell(row=row, column=2, value=str(val))
            _style_value(ws4.cell(row=row, column=2))
            row += 1

        if "tox_mean" in mc_result:
            row += 1
            ws4.cell(row=row, column=1, value="DRASTIC-Tox")
            _style_header(ws4.cell(row=row, column=1))
            ws4.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
            row += 1

            mc_tox_rows = [
                ("Mean", mc_result.get("tox_mean", "—")),
                ("Std Dev", mc_result.get("tox_std", "—")),
                ("Minimum", mc_result.get("tox_min", "—")),
                ("Maximum", mc_result.get("tox_max", "—")),
                ("CI 90%", f"{mc_result.get('tox_ci_90', ('—', '—'))[0]} - {mc_result.get('tox_ci_90', ('—', '—'))[1]}"),
                ("P(index > 140)", f"{mc_result.get('tox_prob_over_140', '—')}%"),
                ("P(index > 180)", f"{mc_result.get('tox_prob_over_180', '—')}%"),
            ]
            for label, val in mc_tox_rows:
                ws4.cell(row=row, column=1, value=label)
                _style_label(ws4.cell(row=row, column=1))
                ws4.cell(row=row, column=2, value=str(val))
                _style_value(ws4.cell(row=row, column=2))
                row += 1

        ws4.column_dimensions["A"].width = 22
        ws4.column_dimensions["B"].width = 25
        ws4.column_dimensions["C"].width = 15

    # ==========================================================
    # SHEET 5: METADATA
    # ==========================================================
    ws5 = wb.create_sheet("Metadata")
    ws5["A1"] = "Report Metadata"
    _style_title(ws5["A1"], size=16)
    ws5.merge_cells("A1:B1")
    ws5.row_dimensions[1].height = 30

    meta_rows = [
        ("Application", "DRASTIC-Tox"),
        ("Version", "v58.6"),
        ("Report Date", datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ("Authors", "Shihab Alhadi Saeed Dangal & Sarah Akasha Al-Tayeb Ali"),
        ("Institution", "University of Khartoum — Faculty of Engineering"),
        ("Contact", "Shihabalhadi16@gmail.com"),
        ("Location", "Singa, Al-Salam — Sennar State, Sudan"),
        ("Status", "Pilot Version"),
        ("", ""),
        ("References", "Aller et al. (1987) — DRASTIC"),
        ("", "Napolitano & Fabbri (1996) — SPSA"),
        ("", "Konaté et al. (2025) — Modified DRASTIC"),
        ("", "WHO (2022) — Guidelines for Drinking-water Quality"),
        ("", ""),
        ("Disclaimer", "Screening tool only. Does not replace laboratory analysis."),
    ]
    row = 3
    for label, val in meta_rows:
        if label:
            ws5.cell(row=row, column=1, value=label)
            _style_label(ws5.cell(row=row, column=1))
        ws5.cell(row=row, column=2, value=str(val))
        _style_value(ws5.cell(row=row, column=2))
        row += 1

    ws5.column_dimensions["A"].width = 20
    ws5.column_dimensions["B"].width = 60

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()
