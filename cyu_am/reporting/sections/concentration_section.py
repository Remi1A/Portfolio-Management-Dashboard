"""Section PDF — Analyse de concentration sectorielle et geographique."""

import pandas as pd
from reportlab.lib.colors import HexColor
from reportlab.lib.units import cm
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

PANEL = HexColor("#1E2130")
DARK_BG = HexColor("#0E1117")
ACCENT = HexColor("#00D4AA")
TEXT_WHITE = HexColor("#FAFAFA")
TEXT_GRAY = HexColor("#8892A4")


def _section_title(text: str) -> Paragraph:
    style = ParagraphStyle(
        "SectionTitle", fontSize=16, fontName="Helvetica-Bold",
        textColor=ACCENT, spaceAfter=12, spaceBefore=20,
    )
    return Paragraph(text, style)


def _subtitle(text: str) -> Paragraph:
    style = ParagraphStyle(
        "SubTitle", fontSize=12, fontName="Helvetica-Bold",
        textColor=TEXT_WHITE, spaceAfter=8,
    )
    return Paragraph(text, style)


def _hhi(weights: pd.Series) -> float:
    shares = weights / weights.sum() * 100
    return float((shares ** 2).sum())


def _hhi_label(hhi_val: float) -> str:
    if hhi_val > 2500:
        return "Eleve"
    elif hhi_val > 1500:
        return "Modere"
    return "Diversifie"


def _build_concentration_table(data: dict[str, float], total_value: dict[str, float],
                               counts: dict[str, int],
                               col1_name: str) -> Table:
    """Build a concentration table with name, weight, value, count."""
    header_style = ParagraphStyle("H", fontSize=8, fontName="Helvetica-Bold",
                                  textColor=ACCENT, alignment=TA_CENTER)
    cell_style = ParagraphStyle("C", fontSize=8, fontName="Helvetica",
                                textColor=TEXT_WHITE, alignment=TA_CENTER)
    cell_right = ParagraphStyle("CR", fontSize=8, fontName="Helvetica",
                                textColor=TEXT_WHITE, alignment=TA_RIGHT)

    rows = [[Paragraph(col1_name, header_style),
             Paragraph("Poids (%)", header_style),
             Paragraph("Valeur (EUR)", header_style),
             Paragraph("Nb actifs", header_style)]]

    for name in sorted(data, key=data.get, reverse=True):
        rows.append([
            Paragraph(name, cell_style),
            Paragraph(f"{data[name]:.1f}%", cell_right),
            Paragraph(f"{total_value.get(name, 0):,.0f}", cell_right),
            Paragraph(str(counts.get(name, 0)), cell_style),
        ])

    table = Table(rows, colWidths=[5 * cm, 3.5 * cm, 4.5 * cm, 3 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PANEL),
        ("BACKGROUND", (0, 1), (-1, -1), DARK_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, TEXT_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def build_concentration_section(sector_data: dict = None,
                                country_data: dict = None,
                                region_data: dict = None,
                                sector_chart_path: str = None,
                                country_chart_path: str = None) -> list:
    """
    Section concentration sectorielle et geographique du rapport PDF.

    Args:
        sector_data: {"weights": {name: pct}, "values": {name: eur}, "counts": {name: n}}
        country_data: same structure
        region_data: same structure
        sector_chart_path: chemin image PNG du pie chart sectoriel
        country_chart_path: chemin image PNG du pie chart geographique
    """
    elements = []
    elements.append(_section_title("Analyse de Concentration"))

    info_style = ParagraphStyle("Info", fontSize=9, fontName="Helvetica",
                                textColor=TEXT_GRAY, alignment=TA_LEFT)
    metric_style = ParagraphStyle("Metric", fontSize=10, fontName="Helvetica-Bold",
                                  textColor=TEXT_WHITE, alignment=TA_CENTER)

    # ── Sectoriel ──
    if sector_data:
        elements.append(_subtitle("Concentration sectorielle"))

        # Pie chart
        if sector_chart_path:
            try:
                img = Image(sector_chart_path, width=10 * cm, height=7 * cm)
                elements.append(img)
                elements.append(Spacer(1, 0.3 * cm))
            except Exception:
                pass

        # Table
        table = _build_concentration_table(
            sector_data["weights"], sector_data["values"],
            sector_data["counts"], "Secteur",
        )
        elements.append(table)

        # HHI
        hhi_val = _hhi(pd.Series(sector_data["weights"]))
        elements.append(Spacer(1, 0.3 * cm))
        hhi_row = Table(
            [[Paragraph(f"HHI sectoriel : {hhi_val:,.0f} ({_hhi_label(hhi_val)})", metric_style)]],
            colWidths=[16 * cm],
        )
        hhi_row.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PANEL),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(hhi_row)
        elements.append(Spacer(1, 0.5 * cm))

    # ── Geographique ──
    if country_data:
        elements.append(_subtitle("Concentration geographique"))

        # Pie chart
        if country_chart_path:
            try:
                img = Image(country_chart_path, width=10 * cm, height=7 * cm)
                elements.append(img)
                elements.append(Spacer(1, 0.3 * cm))
            except Exception:
                pass

        # Table par pays
        table = _build_concentration_table(
            country_data["weights"], country_data["values"],
            country_data["counts"], "Pays",
        )
        elements.append(table)

        # HHI pays
        hhi_country = _hhi(pd.Series(country_data["weights"]))
        elements.append(Spacer(1, 0.3 * cm))

        # Region HHI si disponible
        hhi_text = f"HHI par pays : {hhi_country:,.0f} ({_hhi_label(hhi_country)})"
        if region_data:
            hhi_region = _hhi(pd.Series(region_data["weights"]))
            hhi_text += f"  |  HHI par region : {hhi_region:,.0f} ({_hhi_label(hhi_region)})"

        hhi_row = Table(
            [[Paragraph(hhi_text, metric_style)]],
            colWidths=[16 * cm],
        )
        hhi_row.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PANEL),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(hhi_row)

    if not sector_data and not country_data:
        elements.append(Paragraph("Donnees de concentration non disponibles.", info_style))

    return elements
