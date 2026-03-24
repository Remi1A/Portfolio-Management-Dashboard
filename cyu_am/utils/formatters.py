"""Formatage des valeurs pour l'affichage."""


def fmt_pct(value: float, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:+.{decimals}f}%"


def fmt_pct_no_sign(value: float, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.{decimals}f}%"


def fmt_eur(value: float, decimals: int = 0) -> str:
    if value is None:
        return "N/A"
    if decimals == 0:
        return f"{value:,.0f} EUR".replace(",", " ")
    return f"{value:,.{decimals}f} EUR".replace(",", " ")


def fmt_number(value: float, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}".replace(",", " ")


def fmt_ratio(value: float, decimals: int = 3) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}"


def fmt_days(value: int) -> str:
    if value is None:
        return "N/A"
    return f"{value}j"


def delta_color(value: float) -> str:
    """Retourne 'positive', 'negative' ou 'neutral' pour st.metric."""
    if value > 0:
        return "normal"
    elif value < 0:
        return "inverse"
    return "off"
