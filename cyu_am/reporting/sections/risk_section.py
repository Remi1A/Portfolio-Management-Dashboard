"""Section PDF — Analyse des risques."""

from reportlab.lib.colors import HexColor
from reportlab.lib.units import cm
from reportlab.platypus import Spacer, Paragraph, Table, TableStyle, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

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


def _fmt(v, fmt_type="pct"):
    if v is None:
        return "N/A"
    if fmt_type == "pct":
        return f"{v * 100:+.2f}%"
    if fmt_type == "ratio":
        return f"{v:.3f}"
    if fmt_type == "days":
        return f"{int(v)}j"
    return str(v)


def build_risk_section(risk_metrics: dict,
                       underwater_chart_path: str = None,
                       distribution_chart_path: str = None,
                       nav_current: float = None) -> list:
    """
    Section risque du rapport PDF.

    Args:
        risk_metrics: dictionnaire complet des métriques de risque
        underwater_chart_path: chemin image PNG du drawdown chart
        distribution_chart_path: chemin image PNG de la distribution
        nav_current: valeur actuelle de la NAV pour les stress tests
    """
    elements = []
    elements.append(_section_title("Analyse des Risques"))

    label_style = ParagraphStyle("L", fontSize=9, fontName="Helvetica",
                                 textColor=TEXT_GRAY, alignment=TA_LEFT)
    value_style = ParagraphStyle("V", fontSize=9, fontName="Helvetica-Bold",
                                 textColor=TEXT_WHITE, alignment=TA_CENTER)
    header_style = ParagraphStyle("H", fontSize=9, fontName="Helvetica-Bold",
                                  textColor=ACCENT, alignment=TA_CENTER)

    # Tableau des métriques
    metrics_display = [
        ("Volatilite annualisee", risk_metrics.get("volatility"), "pct"),
        ("Sharpe Ratio", risk_metrics.get("sharpe"), "ratio"),
        ("Sortino Ratio", risk_metrics.get("sortino"), "ratio"),
        ("Omega Ratio", risk_metrics.get("omega"), "ratio"),
        ("Calmar Ratio", risk_metrics.get("calmar"), "ratio"),
        ("Max Drawdown", risk_metrics.get("max_drawdown"), "pct"),
        ("Duree max drawdown", risk_metrics.get("max_dd_duration"), "days"),
        ("VaR 95% (hist.)", risk_metrics.get("var_95_hist"), "pct"),
        ("VaR 95% (param.)", risk_metrics.get("var_95_param"), "pct"),
        ("CVaR 95%", risk_metrics.get("cvar_95"), "pct"),
        ("Skewness", risk_metrics.get("skewness"), "ratio"),
        ("Kurtosis", risk_metrics.get("kurtosis"), "ratio"),
    ]

    # Ajouter métriques benchmark si disponibles
    if "beta" in risk_metrics:
        metrics_display.extend([
            ("Beta", risk_metrics.get("beta"), "ratio"),
            ("Alpha de Jensen", risk_metrics.get("alpha"), "pct"),
            ("Tracking Error", risk_metrics.get("tracking_error"), "pct"),
            ("Information Ratio", risk_metrics.get("information_ratio"), "ratio"),
            ("Correlation", risk_metrics.get("correlation"), "ratio"),
        ])

    # Diviser en 2 colonnes
    mid = (len(metrics_display) + 1) // 2
    left = metrics_display[:mid]
    right = metrics_display[mid:]

    rows = [[Paragraph("Metrique", header_style), Paragraph("Valeur", header_style),
             Paragraph("Metrique", header_style), Paragraph("Valeur", header_style)]]

    for i in range(max(len(left), len(right))):
        row = []
        if i < len(left):
            row.extend([Paragraph(left[i][0], label_style),
                        Paragraph(_fmt(left[i][1], left[i][2]), value_style)])
        else:
            row.extend([Paragraph("", label_style), Paragraph("", value_style)])
        if i < len(right):
            row.extend([Paragraph(right[i][0], label_style),
                        Paragraph(_fmt(right[i][1], right[i][2]), value_style)])
        else:
            row.extend([Paragraph("", label_style), Paragraph("", value_style)])
        rows.append(row)

    table = Table(rows, colWidths=[5 * cm, 3.5 * cm, 5 * cm, 3.5 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PANEL),
        ("BACKGROUND", (0, 1), (-1, -1), DARK_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, TEXT_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)

    # Graphique underwater
    if underwater_chart_path:
        elements.append(Spacer(1, 0.5 * cm))
        try:
            img = Image(underwater_chart_path, width=16 * cm, height=7 * cm)
            elements.append(img)
        except Exception:
            pass

    # Graphique distribution des rendements
    if distribution_chart_path:
        elements.append(Spacer(1, 0.5 * cm))
        try:
            img = Image(distribution_chart_path, width=16 * cm, height=7 * cm)
            elements.append(img)
        except Exception:
            pass

    # Stress tests
    if nav_current is not None and nav_current > 0:
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(_section_title("Stress Tests"))

        stress_header = [Paragraph("Scenario", header_style),
                         Paragraph("Impact (EUR)", header_style),
                         Paragraph("NAV post-choc", header_style)]
        stress_rows = [stress_header]

        for shock in [-0.05, -0.10, -0.20, -0.30]:
            impact = nav_current * shock
            stress_rows.append([
                Paragraph(f"Choc {shock * 100:+.0f}%", label_style),
                Paragraph(f"{impact:+,.0f} EUR", value_style),
                Paragraph(f"{nav_current + impact:,.0f} EUR", value_style),
            ])

        # VaR en EUR
        var_hist = risk_metrics.get("var_95_hist", 0)
        if var_hist:
            var_eur = nav_current * var_hist
            stress_rows.append([
                Paragraph("VaR 95% (1 jour)", label_style),
                Paragraph(f"{var_eur:+,.0f} EUR", value_style),
                Paragraph(f"{nav_current + var_eur:,.0f} EUR", value_style),
            ])

        stress_table = Table(stress_rows, colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm])
        stress_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PANEL),
            ("BACKGROUND", (0, 1), (-1, -1), DARK_BG),
            ("GRID", (0, 0), (-1, -1), 0.5, TEXT_GRAY),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(stress_table)

    return elements
