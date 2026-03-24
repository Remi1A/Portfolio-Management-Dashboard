"""Section PDF — Resume executif avec KPIs et benchmarks."""

from reportlab.lib.colors import HexColor
from reportlab.lib.units import cm
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER

DARK_BG = HexColor("#0E1117")
PANEL = HexColor("#1E2130")
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


def _fmt_pct(v: float) -> str:
    return f"{v * 100:+.2f}%" if v is not None else "N/A"


def _fmt_ratio(v: float) -> str:
    return f"{v:.3f}" if v is not None else "N/A"


def build_executive_summary(performance: dict, risk: dict,
                            benchmark_comparison: dict = None,
                            nav_chart_path: str = None) -> list:
    """
    Construit le resume executif.

    Args:
        performance: dict avec keys total_return, cagr, ytd, mtd, nav_final
        risk: dict avec keys volatility, sharpe, sortino, max_drawdown, var_95, beta, alpha
        benchmark_comparison: dict {period: {portfolio: pct, benchmark: pct}}
    """
    elements = []
    elements.append(_section_title("Resume Executif"))

    # KPIs principaux
    cell_style = ParagraphStyle("Cell", fontSize=9, fontName="Helvetica",
                                textColor=TEXT_WHITE, alignment=TA_CENTER)
    header_style = ParagraphStyle("Header", fontSize=9, fontName="Helvetica-Bold",
                                  textColor=ACCENT, alignment=TA_CENTER)

    kpi_data = [
        [Paragraph("NAV", header_style),
         Paragraph("Perf. Totale", header_style),
         Paragraph("CAGR", header_style),
         Paragraph("YTD", header_style),
         Paragraph("MTD", header_style)],
        [Paragraph(f"{performance.get('nav_final', 0):,.0f} EUR", cell_style),
         Paragraph(_fmt_pct(performance.get("total_return")), cell_style),
         Paragraph(_fmt_pct(performance.get("cagr")), cell_style),
         Paragraph(_fmt_pct(performance.get("ytd")), cell_style),
         Paragraph(_fmt_pct(performance.get("mtd")), cell_style)],
    ]
    kpi_table = Table(kpi_data, colWidths=[3.4 * cm] * 5)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PANEL),
        ("BACKGROUND", (0, 1), (-1, 1), DARK_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, TEXT_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Métriques de risque
    risk_data = [
        [Paragraph("Volatilite", header_style),
         Paragraph("Sharpe", header_style),
         Paragraph("Sortino", header_style),
         Paragraph("Max DD", header_style),
         Paragraph("VaR 95%", header_style)],
        [Paragraph(_fmt_pct(risk.get("volatility")), cell_style),
         Paragraph(_fmt_ratio(risk.get("sharpe")), cell_style),
         Paragraph(_fmt_ratio(risk.get("sortino")), cell_style),
         Paragraph(_fmt_pct(risk.get("max_drawdown")), cell_style),
         Paragraph(_fmt_pct(risk.get("var_95")), cell_style)],
    ]
    risk_table = Table(risk_data, colWidths=[3.4 * cm] * 5)
    risk_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PANEL),
        ("BACKGROUND", (0, 1), (-1, 1), DARK_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, TEXT_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(risk_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Graphique NAV
    if nav_chart_path:
        try:
            img = Image(nav_chart_path, width=16 * cm, height=8 * cm)
            elements.append(img)
            elements.append(Spacer(1, 0.5 * cm))
        except Exception:
            pass

    # Benchmark comparison
    if benchmark_comparison:
        elements.append(_section_title("Comparaison vs Benchmark"))
        bench_header = [Paragraph("Periode", header_style),
                        Paragraph("Portefeuille", header_style),
                        Paragraph("Benchmark", header_style),
                        Paragraph("Exces", header_style)]
        bench_rows = [bench_header]
        for period, vals in benchmark_comparison.items():
            port_val = vals.get("portfolio", 0)
            bench_val = vals.get("benchmark", 0)
            excess = port_val - bench_val
            bench_rows.append([
                Paragraph(period, cell_style),
                Paragraph(_fmt_pct(port_val), cell_style),
                Paragraph(_fmt_pct(bench_val), cell_style),
                Paragraph(_fmt_pct(excess), cell_style),
            ])
        bench_table = Table(bench_rows, colWidths=[4.25 * cm] * 4)
        bench_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PANEL),
            ("BACKGROUND", (0, 1), (-1, -1), DARK_BG),
            ("GRID", (0, 0), (-1, -1), 0.5, TEXT_GRAY),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(bench_table)

    return elements
