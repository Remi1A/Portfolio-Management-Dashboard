"""Section PDF — Page de garde."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER


DARK_BG = HexColor("#0E1117")
ACCENT = HexColor("#00D4AA")
TEXT_WHITE = HexColor("#FAFAFA")
TEXT_GRAY = HexColor("#8892A4")


def build_cover(portfolio_name: str, benchmark_name: str,
                period_label: str, generation_date: str) -> list:
    """Retourne les flowables ReportLab pour la page de garde."""

    elements = []
    elements.append(Spacer(1, 6 * cm))

    # Titre principal
    title_style = ParagraphStyle(
        "CoverTitle", fontSize=32, fontName="Helvetica-Bold",
        textColor=TEXT_WHITE, alignment=TA_CENTER, spaceAfter=20,
    )
    elements.append(Paragraph("CY Tech AM", title_style))

    # Sous-titre
    subtitle_style = ParagraphStyle(
        "CoverSubtitle", fontSize=18, fontName="Helvetica",
        textColor=ACCENT, alignment=TA_CENTER, spaceAfter=40,
    )
    elements.append(Paragraph("Rapport de Gestion Mensuel", subtitle_style))

    elements.append(Spacer(1, 2 * cm))

    # Infos
    info_style = ParagraphStyle(
        "CoverInfo", fontSize=13, fontName="Helvetica",
        textColor=TEXT_WHITE, alignment=TA_CENTER, spaceAfter=12,
    )
    elements.append(Paragraph(f"Portefeuille : {portfolio_name}", info_style))
    elements.append(Paragraph(f"Benchmark : {benchmark_name}", info_style))
    elements.append(Paragraph(f"Periode : {period_label}", info_style))

    elements.append(Spacer(1, 3 * cm))

    date_style = ParagraphStyle(
        "CoverDate", fontSize=10, fontName="Helvetica",
        textColor=TEXT_GRAY, alignment=TA_CENTER,
    )
    elements.append(Paragraph(f"Rapport genere le {generation_date}", date_style))

    return elements
