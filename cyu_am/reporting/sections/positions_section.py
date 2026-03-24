"""Section PDF — Composition du portefeuille et transactions."""

from reportlab.lib.colors import HexColor
from reportlab.lib.units import cm
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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


def build_positions_section(positions: pd.DataFrame,
                            transactions: pd.DataFrame = None,
                            allocation_chart_path: str = None) -> list:
    """
    Section positions du rapport PDF.

    Args:
        positions: DataFrame des positions actuelles
        transactions: DataFrame des transactions de la période (optionnel)
    """
    elements = []
    elements.append(_section_title("Composition du Portefeuille"))

    if positions.empty:
        elements.append(Paragraph("Aucune position ouverte.",
                                  ParagraphStyle("Empty", fontSize=10,
                                                 textColor=TEXT_GRAY)))
        return elements

    header_style = ParagraphStyle("H", fontSize=8, fontName="Helvetica-Bold",
                                  textColor=ACCENT, alignment=TA_CENTER)
    cell_style = ParagraphStyle("C", fontSize=8, fontName="Helvetica",
                                textColor=TEXT_WHITE, alignment=TA_CENTER)
    cell_right = ParagraphStyle("CR", fontSize=8, fontName="Helvetica",
                                textColor=TEXT_WHITE, alignment=TA_RIGHT)

    # Tableau des positions
    headers = ["Ticker", "Classe", "Qte", "Prix moy.", "Prix act.",
               "Valeur EUR", "P&L EUR", "P&L %", "Poids %"]
    header_row = [Paragraph(h, header_style) for h in headers]

    data_rows = [header_row]
    for _, pos in positions.iterrows():
        pnl_color = POSITIVE if pos.get("pnl_eur", 0) >= 0 else NEGATIVE
        pnl_style = ParagraphStyle("PNL", fontSize=8, fontName="Helvetica-Bold",
                                   textColor=pnl_color, alignment=TA_RIGHT)
        data_rows.append([
            Paragraph(str(pos.get("ticker", "")), cell_style),
            Paragraph(str(pos.get("asset_class", "")), cell_style),
            Paragraph(f"{pos.get('quantity', 0):.1f}", cell_right),
            Paragraph(f"{pos.get('avg_cost', 0):.2f}", cell_right),
            Paragraph(f"{pos.get('current_price', 0):.2f}", cell_right),
            Paragraph(f"{pos.get('market_value_eur', 0):,.0f}", cell_right),
            Paragraph(f"{pos.get('pnl_eur', 0):+,.0f}", pnl_style),
            Paragraph(f"{pos.get('pnl_pct', 0):+.1f}%", pnl_style),
            Paragraph(f"{pos.get('weight', 0):.1f}%", cell_right),
        ])

    col_widths = [2 * cm, 1.8 * cm, 1.3 * cm, 1.8 * cm, 1.8 * cm,
                  2.2 * cm, 2 * cm, 1.8 * cm, 1.6 * cm]
    table = Table(data_rows, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PANEL),
        ("BACKGROUND", (0, 1), (-1, -1), DARK_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, TEXT_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(table)

    # Graphique allocation
    if allocation_chart_path:
        elements.append(Spacer(1, 0.5 * cm))
        try:
            img = Image(allocation_chart_path, width=10 * cm, height=8 * cm)
            elements.append(img)
        except Exception:
            pass

    # Transactions de la période
    if transactions is not None and not transactions.empty:
        elements.append(Spacer(1, 1 * cm))
        elements.append(_section_title("Transactions de la periode"))

        tx_headers = ["Date", "Ticker", "Action", "Qte", "Prix", "Devise", "Frais"]
        tx_header_row = [Paragraph(h, header_style) for h in tx_headers]
        tx_rows = [tx_header_row]

        for _, tx in transactions.iterrows():
            action_color = POSITIVE if tx.get("action") == "BUY" else NEGATIVE
            action_style = ParagraphStyle("A", fontSize=8, fontName="Helvetica-Bold",
                                          textColor=action_color, alignment=TA_CENTER)
            tx_rows.append([
                Paragraph(str(tx.get("date", ""))[:10], cell_style),
                Paragraph(str(tx.get("ticker", "")), cell_style),
                Paragraph(str(tx.get("action", "")), action_style),
                Paragraph(f"{tx.get('quantity', 0):.1f}", cell_right),
                Paragraph(f"{tx.get('price', 0):.2f}", cell_right),
                Paragraph(str(tx.get("asset_currency", "EUR")), cell_style),
                Paragraph(f"{tx.get('fees', 0):.1f}", cell_right),
            ])

        tx_widths = [2.5 * cm, 2.5 * cm, 2 * cm, 2 * cm, 2.5 * cm, 2 * cm, 2 * cm]
        tx_table = Table(tx_rows, colWidths=tx_widths)
        tx_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PANEL),
            ("BACKGROUND", (0, 1), (-1, -1), DARK_BG),
            ("GRID", (0, 0), (-1, -1), 0.5, TEXT_GRAY),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(tx_table)

    return elements
