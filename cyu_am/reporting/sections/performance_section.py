"""Section PDF — Performance (NAV, rendements mensuels)."""

from reportlab.lib.colors import HexColor
from reportlab.lib.units import cm
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
import pandas as pd

PANEL = HexColor("#1E2130")
DARK_BG = HexColor("#0E1117")
ACCENT = HexColor("#00D4AA")
TEXT_WHITE = HexColor("#FAFAFA")
TEXT_GRAY = HexColor("#8892A4")
POSITIVE = HexColor("#26A69A")
NEGATIVE = HexColor("#EF5350")


def _section_title(text: str) -> Paragraph:
    style = ParagraphStyle(
        "SectionTitle", fontSize=16, fontName="Helvetica-Bold",
        textColor=ACCENT, spaceAfter=12, spaceBefore=20,
    )
    return Paragraph(text, style)


def build_performance_section(monthly_table: pd.DataFrame,
                              nav_chart_path: str = None) -> list:
    """
    Section performance du rapport PDF.

    Args:
        monthly_table: DataFrame pivot (years x months) des rendements mensuels en %
        nav_chart_path: chemin vers l'image PNG du graphique NAV (optionnel)
    """
    elements = []
    elements.append(_section_title("Performance"))

    # Graphique NAV
    if nav_chart_path:
        try:
            img = Image(nav_chart_path, width=16 * cm, height=8 * cm)
            elements.append(img)
            elements.append(Spacer(1, 0.5 * cm))
        except Exception:
            pass

    # Heatmap mensuelle en tableau
    if monthly_table is not None and not monthly_table.empty:
        elements.append(Paragraph(
            "Rendements mensuels (%)",
            ParagraphStyle("SubTitle", fontSize=12, fontName="Helvetica-Bold",
                           textColor=TEXT_WHITE, spaceAfter=8),
        ))

        header_style = ParagraphStyle("H", fontSize=7, fontName="Helvetica-Bold",
                                      textColor=ACCENT, alignment=TA_CENTER)
        cell_style = ParagraphStyle("C", fontSize=7, fontName="Helvetica",
                                    textColor=TEXT_WHITE, alignment=TA_CENTER)

        months = monthly_table.columns.tolist()
        header_row = [Paragraph("Annee", header_style)] + \
                     [Paragraph(m, header_style) for m in months]

        data_rows = [header_row]
        cell_colors = []

        for i, (year, row) in enumerate(monthly_table.iterrows()):
            cells = [Paragraph(str(year), cell_style)]
            for j, val in enumerate(row):
                if pd.notna(val):
                    cells.append(Paragraph(f"{val:.1f}", cell_style))
                    color = POSITIVE if val >= 0 else NEGATIVE
                    cell_colors.append((j + 1, i + 1, color))
                else:
                    cells.append(Paragraph("-", cell_style))
            data_rows.append(cells)

        n_cols = len(months) + 1
        col_width = 17 * cm / n_cols
        table = Table(data_rows, colWidths=[col_width] * n_cols)

        style_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), PANEL),
            ("GRID", (0, 0), (-1, -1), 0.5, TEXT_GRAY),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        # Colorer les cellules selon performance
        for col, row, color in cell_colors:
            style_commands.append(("BACKGROUND", (col, row), (col, row), color))

        table.setStyle(TableStyle(style_commands))
        elements.append(table)

    return elements
