"""Métriques sur fenêtre glissante (rolling)."""

import pandas as pd
import numpy as np

from cyu_am.config.settings import ROLLING_WINDOWS, RISK_FREE_RATE


def rolling_volatility(returns: pd.Series, window: int = 90,
                       periods_per_year: float = 252) -> pd.Series:
    return returns.rolling(window).std() * np.sqrt(periods_per_year)


def rolling_sharpe(returns: pd.Series, window: int = 90, rf: float = None,
                   periods_per_year: float = 252) -> pd.Series:
    if rf is None:
        rf = RISK_FREE_RATE
    rf_daily = (1 + rf) ** (1 / periods_per_year) - 1
    excess = returns - rf_daily
    roll_mean = excess.rolling(window).mean() * periods_per_year
    roll_std = returns.rolling(window).std() * np.sqrt(periods_per_year)
    return roll_mean / roll_std.replace(0, np.nan)


def rolling_beta(portfolio_returns: pd.Series, benchmark_returns: pd.Series,
                 window: int = 90) -> pd.Series:
    aligned = pd.concat([portfolio_returns.rename("port"),
                         benchmark_returns.rename("bench")], axis=1).dropna()
    cov = aligned["port"].rolling(window).cov(aligned["bench"])
    var = aligned["bench"].rolling(window).var()
    return cov / var.replace(0, np.nan)


def rolling_max_drawdown(nav: pd.Series, window: int = 252) -> pd.Series:
    def _mdd(x):
        peak = x.cummax()
        dd = (x - peak) / peak
        return dd.min()
    return nav.rolling(window).apply(_mdd, raw=False)


def rolling_correlation(portfolio_returns: pd.Series, benchmark_returns: pd.Series,
                        window: int = 90) -> pd.Series:
    aligned = pd.concat([portfolio_returns.rename("port"),
                         benchmark_returns.rename("bench")], axis=1).dropna()
    return aligned["port"].rolling(window).corr(aligned["bench"])


def all_rolling_metrics(returns: pd.Series, nav: pd.Series,
                        benchmark_returns: pd.Series = None) -> dict[str, pd.DataFrame]:
    """
    Calcule toutes les métriques rolling pour chaque fenêtre standard.
    Retourne {metric_name: DataFrame avec une colonne par fenêtre}.
    """
    result = {}

    for label, w in ROLLING_WINDOWS.items():
        vol = rolling_volatility(returns, w)
        sharpe = rolling_sharpe(returns, w)
        mdd = rolling_max_drawdown(nav, w)

        for metric, series in [("volatility", vol), ("sharpe", sharpe), ("max_drawdown", mdd)]:
            if metric not in result:
                result[metric] = pd.DataFrame(index=returns.index)
            result[metric][label] = series

        if benchmark_returns is not None:
            b = rolling_beta(returns, benchmark_returns, w)
            corr = rolling_correlation(returns, benchmark_returns, w)
            for metric, series in [("beta", b), ("correlation", corr)]:
                if metric not in result:
                    result[metric] = pd.DataFrame(index=returns.index)
                result[metric][label] = series

    return result
