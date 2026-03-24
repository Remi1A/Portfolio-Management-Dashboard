"""Métriques de performance — fonctions pures sur séries de rendements / NAV."""

import pandas as pd
import numpy as np


def total_return(nav: pd.Series) -> float:
    """Rendement total : (NAV_final / NAV_initial) - 1"""
    if len(nav) < 2:
        return 0.0
    return nav.iloc[-1] / nav.iloc[0] - 1


def cagr(nav: pd.Series, periods_per_year: float = 252) -> float:
    """Compound Annual Growth Rate."""
    if len(nav) < 2:
        return 0.0
    n = len(nav) / periods_per_year
    if n <= 0:
        return 0.0
    total = nav.iloc[-1] / nav.iloc[0]
    if total <= 0:
        return -1.0
    return total ** (1 / n) - 1


def ytd_return(nav: pd.Series) -> float:
    """Rendement Year-to-Date."""
    if nav.empty:
        return 0.0
    current_year = nav.index[-1].year
    year_start = nav.index[nav.index.year == current_year]
    if year_start.empty:
        return 0.0
    return nav.iloc[-1] / nav.loc[year_start[0]] - 1


def mtd_return(nav: pd.Series) -> float:
    """Rendement Month-to-Date."""
    if nav.empty:
        return 0.0
    last_date = nav.index[-1]
    month_start = nav.index[(nav.index.year == last_date.year) &
                            (nav.index.month == last_date.month)]
    if month_start.empty:
        return 0.0
    return nav.iloc[-1] / nav.loc[month_start[0]] - 1


def daily_returns(nav: pd.Series) -> pd.Series:
    """Rendements quotidiens."""
    return nav.pct_change().dropna()


def monthly_returns(nav: pd.Series) -> pd.Series:
    """Rendements mensuels (dernier jour de chaque mois)."""
    monthly_nav = nav.resample("ME").last()
    return monthly_nav.pct_change().dropna()


def monthly_returns_table(nav: pd.Series) -> pd.DataFrame:
    """
    Heatmap-ready : tableau pivot avec années en lignes, mois en colonnes.
    Valeurs = rendements mensuels en %.
    """
    rets = monthly_returns(nav)
    if rets.empty:
        return pd.DataFrame()
    df = pd.DataFrame({
        "year": rets.index.year,
        "month": rets.index.month,
        "return": rets.values * 100,
    })
    pivot = df.pivot_table(index="year", columns="month", values="return", aggfunc="first")
    pivot.columns = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][:len(pivot.columns)]
    return pivot


def cumulative_returns(returns: pd.Series) -> pd.Series:
    """Rendements cumulés à partir d'une série de rendements."""
    return (1 + returns).cumprod() - 1


def annualized_return(returns: pd.Series, periods_per_year: float = 252) -> float:
    """Rendement annualisé à partir de rendements quotidiens."""
    if returns.empty:
        return 0.0
    total = (1 + returns).prod()
    n_years = len(returns) / periods_per_year
    if n_years <= 0 or total <= 0:
        return 0.0
    return total ** (1 / n_years) - 1


def period_return(nav: pd.Series, period: str) -> float:
    """
    Rendement sur une période standard.
    period: '1M', '3M', '6M', '1Y', 'YTD', 'MAX'
    """
    if nav.empty:
        return 0.0

    end = nav.index[-1]

    if period == "YTD":
        return ytd_return(nav)
    elif period == "MAX":
        return total_return(nav)

    offsets = {"1M": 21, "3M": 63, "6M": 126, "1Y": 252}
    days = offsets.get(period, 0)
    if days == 0:
        return 0.0

    if len(nav) <= days:
        return total_return(nav)

    return nav.iloc[-1] / nav.iloc[-days - 1] - 1


def periods_summary(nav: pd.Series) -> dict[str, float]:
    """Résumé des rendements sur toutes les périodes standard."""
    return {p: period_return(nav, p) for p in ["1M", "3M", "6M", "1Y", "YTD", "MAX"]}
