"""Optimisation de portefeuille — Markowitz, Monte Carlo, frontière efficiente."""

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from cyu_am.config.settings import RISK_FREE_RATE


def portfolio_stats(weights: np.ndarray, mean_returns: np.ndarray,
                    cov_matrix: np.ndarray, periods_per_year: float = 252
                    ) -> tuple[float, float, float]:
    """Retourne (rendement annualisé, volatilité annualisée, Sharpe)."""
    ret = np.dot(weights, mean_returns) * periods_per_year
    vol = np.sqrt(np.dot(weights, np.dot(cov_matrix * periods_per_year, weights)))
    sharpe = (ret - RISK_FREE_RATE) / vol if vol > 0 else 0.0
    return float(ret), float(vol), float(sharpe)


def min_variance_portfolio(mean_returns: np.ndarray, cov_matrix: np.ndarray,
                           allow_short: bool = False) -> dict:
    """Portefeuille de variance minimale."""
    n = len(mean_returns)
    bounds = ((-1, 1) if allow_short else (0, 1),) * n
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
    x0 = np.ones(n) / n

    result = minimize(
        lambda w: np.sqrt(np.dot(w, np.dot(cov_matrix * 252, w))),
        x0, method="SLSQP", bounds=bounds, constraints=constraints,
    )
    weights = result.x
    ret, vol, sharpe = portfolio_stats(weights, mean_returns, cov_matrix)
    return {"weights": weights, "return": ret, "volatility": vol, "sharpe": sharpe}


def max_sharpe_portfolio(mean_returns: np.ndarray, cov_matrix: np.ndarray,
                         allow_short: bool = False) -> dict:
    """Portefeuille de Sharpe maximal (tangent portfolio)."""
    n = len(mean_returns)
    bounds = ((-1, 1) if allow_short else (0, 1),) * n
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
    x0 = np.ones(n) / n

    def neg_sharpe(w):
        _, _, sr = portfolio_stats(w, mean_returns, cov_matrix)
        return -sr

    result = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints)
    weights = result.x
    ret, vol, sharpe = portfolio_stats(weights, mean_returns, cov_matrix)
    return {"weights": weights, "return": ret, "volatility": vol, "sharpe": sharpe}


def efficient_frontier(mean_returns: np.ndarray, cov_matrix: np.ndarray,
                       n_points: int = 50, allow_short: bool = False) -> pd.DataFrame:
    """
    Calcule la frontière efficiente.
    Retourne DataFrame avec colonnes [return, volatility, sharpe, w_0, w_1, ...].
    """
    n = len(mean_returns)
    bounds = ((-1, 1) if allow_short else (0, 1),) * n

    # Trouver les bornes de rendement
    min_var = min_variance_portfolio(mean_returns, cov_matrix, allow_short)
    max_ret_idx = np.argmax(mean_returns)
    max_ret = mean_returns[max_ret_idx] * 252

    target_returns = np.linspace(min_var["return"], max_ret * 0.95, n_points)

    results = []
    for target in target_returns:
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},
            {"type": "eq", "fun": lambda w, t=target: np.dot(w, mean_returns) * 252 - t},
        ]
        x0 = np.ones(n) / n
        res = minimize(
            lambda w: np.sqrt(np.dot(w, np.dot(cov_matrix * 252, w))),
            x0, method="SLSQP", bounds=bounds, constraints=constraints,
        )
        if res.success:
            ret, vol, sharpe = portfolio_stats(res.x, mean_returns, cov_matrix)
            row = {"return": ret, "volatility": vol, "sharpe": sharpe}
            for i, w in enumerate(res.x):
                row[f"w_{i}"] = w
            results.append(row)

    return pd.DataFrame(results)


def monte_carlo_simulation(mean_returns: np.ndarray, cov_matrix: np.ndarray,
                           n_portfolios: int = 5000) -> pd.DataFrame:
    """
    Simulation Monte Carlo de portefeuilles aléatoires.
    Retourne DataFrame [return, volatility, sharpe, w_0, w_1, ...].
    """
    n = len(mean_returns)
    records = []

    for _ in range(n_portfolios):
        weights = np.random.dirichlet(np.ones(n))
        ret, vol, sharpe = portfolio_stats(weights, mean_returns, cov_matrix)
        row = {"return": ret, "volatility": vol, "sharpe": sharpe}
        for i, w in enumerate(weights):
            row[f"w_{i}"] = w
        records.append(row)

    return pd.DataFrame(records)


def prepare_optimization_inputs(returns_df: pd.DataFrame
                                ) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Prépare les inputs pour l'optimisation à partir d'un DataFrame de rendements.

    Args:
        returns_df: DataFrame avec une colonne par actif, rendements quotidiens.

    Returns:
        (mean_returns, cov_matrix, tickers)
    """
    clean = returns_df.dropna()
    tickers = clean.columns.tolist()
    mean_returns = clean.mean().values
    cov_matrix = clean.cov().values
    return mean_returns, cov_matrix, tickers
