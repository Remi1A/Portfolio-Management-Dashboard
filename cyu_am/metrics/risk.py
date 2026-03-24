"""Métriques de risque — fonctions pures sur séries de rendements."""

import pandas as pd
import numpy as np

from cyu_am.config.settings import RISK_FREE_RATE, VAR_CONFIDENCE


def volatility(returns: pd.Series, periods_per_year: float = 252) -> float:
    """Volatilité annualisée."""
    if len(returns) < 2:
        return 0.0
    return float(returns.std() * np.sqrt(periods_per_year))


def downside_volatility(returns: pd.Series, threshold: float = 0.0,
                        periods_per_year: float = 252) -> float:
    """Volatilité downside (rendements < threshold uniquement)."""
    downside = returns[returns < threshold]
    if len(downside) < 2:
        return 0.0
    return float(downside.std() * np.sqrt(periods_per_year))


def sharpe_ratio(returns: pd.Series, rf: float = None,
                 periods_per_year: float = 252) -> float:
    """Sharpe Ratio = (R_p - R_f) / sigma_p annualisé (annualisation linéaire)."""
    if rf is None:
        rf = RISK_FREE_RATE
    if len(returns) < 2:
        return 0.0
    ann_ret = returns.mean() * periods_per_year
    vol = volatility(returns, periods_per_year)
    if vol == 0:
        return 0.0
    return (ann_ret - rf) / vol


def sortino_ratio(returns: pd.Series, rf: float = None,
                  periods_per_year: float = 252) -> float:
    """Sortino Ratio = (R_p - R_f) / sigma_downside (annualisation linéaire)."""
    if rf is None:
        rf = RISK_FREE_RATE
    if len(returns) < 2:
        return 0.0
    ann_ret = returns.mean() * periods_per_year
    down_vol = downside_volatility(returns, 0.0, periods_per_year)
    if down_vol == 0:
        return 0.0
    return (ann_ret - rf) / down_vol


def omega_ratio(returns: pd.Series, threshold: float = 0.0) -> float:
    """Omega Ratio = sum(gains au-dessus du seuil) / sum(pertes en-dessous)."""
    excess = returns - threshold
    gains = excess[excess > 0].sum()
    losses = -excess[excess < 0].sum()
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def calmar_ratio(returns: pd.Series, nav: pd.Series = None,
                 periods_per_year: float = 252) -> float:
    """Calmar Ratio = CAGR / |Max Drawdown|."""
    from cyu_am.metrics.performance import cagr as calc_cagr
    if nav is None:
        nav = (1 + returns).cumprod()
    c = calc_cagr(nav, periods_per_year)
    mdd = max_drawdown(nav)
    if mdd == 0:
        return 0.0
    return c / abs(mdd)


# ── Drawdown ──

def drawdown_series(nav: pd.Series) -> pd.Series:
    """Série de drawdowns (valeurs négatives ou zéro)."""
    peak = nav.cummax()
    return (nav - peak) / peak


def max_drawdown(nav: pd.Series) -> float:
    """Max Drawdown (valeur négative)."""
    dd = drawdown_series(nav)
    if dd.empty:
        return 0.0
    return float(dd.min())


def max_drawdown_duration(nav: pd.Series) -> int:
    """Durée du plus long drawdown en jours de trading."""
    peak = nav.cummax()
    in_dd = nav < peak

    if not in_dd.any():
        return 0

    groups = (~in_dd).cumsum()
    dd_groups = groups[in_dd]
    if dd_groups.empty:
        return 0
    return int(dd_groups.value_counts().max())


# ── Value at Risk ──

def var_historical(returns: pd.Series, confidence: float = None) -> float:
    """VaR historique (percentile). Retourne une valeur négative."""
    if confidence is None:
        confidence = VAR_CONFIDENCE
    if returns.empty:
        return 0.0
    return float(np.percentile(returns.dropna(), (1 - confidence) * 100))


def var_parametric(returns: pd.Series, confidence: float = None) -> float:
    """VaR paramétrique (gaussien). Retourne une valeur négative."""
    if confidence is None:
        confidence = VAR_CONFIDENCE
    if len(returns) < 2:
        return 0.0
    from scipy.stats import norm
    z = norm.ppf(1 - confidence)
    return float(returns.mean() + z * returns.std())


def cvar(returns: pd.Series, confidence: float = None) -> float:
    """CVaR / Expected Shortfall = moyenne des pertes au-delà du VaR."""
    if confidence is None:
        confidence = VAR_CONFIDENCE
    var = var_historical(returns, confidence)
    tail = returns[returns <= var]
    if tail.empty:
        return var
    return float(tail.mean())


# ── Beta / Alpha ──

def beta(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Beta = Cov(R_p, R_m) / Var(R_m)."""
    aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 2:
        return 1.0
    cov_matrix = aligned.cov()
    var_bench = cov_matrix.iloc[1, 1]
    if var_bench == 0:
        return 1.0
    return float(cov_matrix.iloc[0, 1] / var_bench)


def alpha_jensen(portfolio_returns: pd.Series, benchmark_returns: pd.Series,
                 rf: float = None, periods_per_year: float = 252) -> float:
    """Alpha de Jensen = R_p - [R_f + beta * (R_m - R_f)]."""
    if rf is None:
        rf = RISK_FREE_RATE
    b = beta(portfolio_returns, benchmark_returns)
    ann_port = portfolio_returns.mean() * periods_per_year
    ann_bench = benchmark_returns.mean() * periods_per_year
    return ann_port - (rf + b * (ann_bench - rf))


# ── Tracking ──

def tracking_error(portfolio_returns: pd.Series, benchmark_returns: pd.Series,
                   periods_per_year: float = 252) -> float:
    """Tracking Error = std(R_p - R_b) annualisé."""
    excess = (portfolio_returns - benchmark_returns).dropna()
    if len(excess) < 2:
        return 0.0
    return float(excess.std() * np.sqrt(periods_per_year))


def information_ratio(portfolio_returns: pd.Series, benchmark_returns: pd.Series,
                      periods_per_year: float = 252) -> float:
    """Information Ratio = excès de rendement annualisé / Tracking Error."""
    excess = (portfolio_returns - benchmark_returns).dropna()
    if len(excess) < 2:
        return 0.0
    te = tracking_error(portfolio_returns, benchmark_returns, periods_per_year)
    if te == 0:
        return 0.0
    ann_excess = excess.mean() * periods_per_year
    return float(ann_excess / te)


# ── Distribution ──

def skewness(returns: pd.Series) -> float:
    """Asymétrie de la distribution."""
    if len(returns) < 3:
        return 0.0
    return float(returns.skew())


def kurtosis(returns: pd.Series) -> float:
    """Kurtosis (excès) de la distribution."""
    if len(returns) < 4:
        return 0.0
    return float(returns.kurtosis())


# ── Capture Ratios ──

def up_capture(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Up Capture Ratio (mois où le benchmark est positif)."""
    aligned = pd.concat(
        [portfolio_returns.rename("port"), benchmark_returns.rename("bench")], axis=1
    ).dropna()
    if aligned.empty:
        return 0.0
    up_months = aligned[aligned["bench"] > 0]
    if up_months.empty:
        return 0.0
    return float(up_months["port"].mean() / up_months["bench"].mean() * 100)


def down_capture(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Down Capture Ratio (mois où le benchmark est négatif)."""
    aligned = pd.concat(
        [portfolio_returns.rename("port"), benchmark_returns.rename("bench")], axis=1
    ).dropna()
    if aligned.empty:
        return 0.0
    down_months = aligned[aligned["bench"] < 0]
    if down_months.empty:
        return 0.0
    return float(down_months["port"].mean() / down_months["bench"].mean() * 100)


# ── Corrélation ──

def correlation(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Corrélation entre portefeuille et benchmark."""
    aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 2:
        return 0.0
    return float(aligned.corr().iloc[0, 1])


# ── Résumé complet ──

def risk_summary(returns: pd.Series, nav: pd.Series,
                 benchmark_returns: pd.Series = None) -> dict:
    """Dictionnaire complet de toutes les métriques de risque."""
    summary = {
        "volatility": volatility(returns),
        "sharpe": sharpe_ratio(returns),
        "sortino": sortino_ratio(returns),
        "omega": omega_ratio(returns),
        "calmar": calmar_ratio(returns, nav),
        "max_drawdown": max_drawdown(nav),
        "max_dd_duration": max_drawdown_duration(nav),
        "var_95_hist": var_historical(returns),
        "var_95_param": var_parametric(returns),
        "cvar_95": cvar(returns),
        "skewness": skewness(returns),
        "kurtosis": kurtosis(returns),
    }

    if benchmark_returns is not None:
        summary.update({
            "beta": beta(returns, benchmark_returns),
            "alpha": alpha_jensen(returns, benchmark_returns),
            "tracking_error": tracking_error(returns, benchmark_returns),
            "information_ratio": information_ratio(returns, benchmark_returns),
            "correlation": correlation(returns, benchmark_returns),
            "up_capture": up_capture(returns, benchmark_returns),
            "down_capture": down_capture(returns, benchmark_returns),
        })

    return summary
