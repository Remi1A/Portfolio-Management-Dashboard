"""Tests unitaires pour cyu_am.metrics.optimization."""

import pytest
import pandas as pd
import numpy as np

from cyu_am.metrics.optimization import (
    portfolio_stats,
    min_variance_portfolio,
    max_sharpe_portfolio,
    efficient_frontier,
    monte_carlo_simulation,
    prepare_optimization_inputs,
)


@pytest.fixture
def two_assets():
    """Deux actifs avec rendements et covariance connus."""
    mean_returns = np.array([0.0004, 0.0006])
    cov_matrix = np.array([
        [0.0001, 0.00002],
        [0.00002, 0.00015],
    ])
    return mean_returns, cov_matrix


@pytest.fixture
def three_assets():
    """Trois actifs pour tests plus complets."""
    np.random.seed(42)
    n = 500
    r1 = np.random.normal(0.0004, 0.01, n)
    r2 = np.random.normal(0.0005, 0.012, n)
    r3 = np.random.normal(0.0003, 0.008, n)
    df = pd.DataFrame({"A": r1, "B": r2, "C": r3})
    mean_returns = df.mean().values
    cov_matrix = df.cov().values
    return mean_returns, cov_matrix


@pytest.fixture
def returns_df():
    np.random.seed(42)
    dates = pd.bdate_range("2024-01-02", periods=300)
    return pd.DataFrame({
        "AAPL": np.random.normal(0.0004, 0.015, 300),
        "MSFT": np.random.normal(0.0005, 0.012, 300),
        "BNP.PA": np.random.normal(0.0003, 0.018, 300),
    }, index=dates)


# ── portfolio_stats ──

class TestPortfolioStats:
    def test_equal_weights(self, two_assets):
        mean_ret, cov = two_assets
        weights = np.array([0.5, 0.5])
        ret, vol, sharpe = portfolio_stats(weights, mean_ret, cov)
        assert ret > 0
        assert vol > 0
        assert isinstance(sharpe, float)

    def test_single_asset(self, two_assets):
        mean_ret, cov = two_assets
        weights = np.array([1.0, 0.0])
        ret, vol, _ = portfolio_stats(weights, mean_ret, cov)
        expected_ret = mean_ret[0] * 252
        assert ret == pytest.approx(expected_ret, rel=1e-6)


# ── min_variance_portfolio ──

class TestMinVariance:
    def test_weights_sum_to_one(self, three_assets):
        mean_ret, cov = three_assets
        result = min_variance_portfolio(mean_ret, cov)
        assert np.sum(result["weights"]) == pytest.approx(1.0, abs=1e-6)

    def test_no_negative_weights(self, three_assets):
        mean_ret, cov = three_assets
        result = min_variance_portfolio(mean_ret, cov, allow_short=False)
        assert (result["weights"] >= -1e-8).all()

    def test_has_all_keys(self, two_assets):
        mean_ret, cov = two_assets
        result = min_variance_portfolio(mean_ret, cov)
        assert "weights" in result
        assert "return" in result
        assert "volatility" in result
        assert "sharpe" in result

    def test_lower_vol_than_equal_weights(self, three_assets):
        mean_ret, cov = three_assets
        min_var = min_variance_portfolio(mean_ret, cov)
        eq_weights = np.ones(3) / 3
        _, eq_vol, _ = portfolio_stats(eq_weights, mean_ret, cov)
        assert min_var["volatility"] <= eq_vol + 1e-6


# ── max_sharpe_portfolio ──

class TestMaxSharpe:
    def test_weights_sum_to_one(self, three_assets):
        mean_ret, cov = three_assets
        result = max_sharpe_portfolio(mean_ret, cov)
        assert np.sum(result["weights"]) == pytest.approx(1.0, abs=1e-6)

    def test_higher_sharpe_than_min_var(self, three_assets):
        mean_ret, cov = three_assets
        max_sr = max_sharpe_portfolio(mean_ret, cov)
        min_var = min_variance_portfolio(mean_ret, cov)
        assert max_sr["sharpe"] >= min_var["sharpe"] - 1e-4

    def test_short_selling(self, three_assets):
        mean_ret, cov = three_assets
        result = max_sharpe_portfolio(mean_ret, cov, allow_short=True)
        assert np.sum(result["weights"]) == pytest.approx(1.0, abs=1e-6)


# ── efficient_frontier ──

class TestEfficientFrontier:
    def test_returns_dataframe(self, three_assets):
        mean_ret, cov = three_assets
        ef = efficient_frontier(mean_ret, cov, n_points=10)
        assert isinstance(ef, pd.DataFrame)
        assert len(ef) > 0

    def test_columns(self, three_assets):
        mean_ret, cov = three_assets
        ef = efficient_frontier(mean_ret, cov, n_points=10)
        assert "return" in ef.columns
        assert "volatility" in ef.columns
        assert "sharpe" in ef.columns

    def test_increasing_return(self, three_assets):
        mean_ret, cov = three_assets
        ef = efficient_frontier(mean_ret, cov, n_points=20)
        if len(ef) > 2:
            # Returns should generally increase along the frontier
            assert ef["return"].iloc[-1] > ef["return"].iloc[0]


# ── monte_carlo_simulation ──

class TestMonteCarlo:
    def test_correct_number(self, two_assets):
        mean_ret, cov = two_assets
        mc = monte_carlo_simulation(mean_ret, cov, n_portfolios=100)
        assert len(mc) == 100

    def test_columns(self, two_assets):
        mean_ret, cov = two_assets
        mc = monte_carlo_simulation(mean_ret, cov, n_portfolios=10)
        assert "return" in mc.columns
        assert "volatility" in mc.columns
        assert "sharpe" in mc.columns
        assert "w_0" in mc.columns
        assert "w_1" in mc.columns

    def test_weights_sum_to_one(self, two_assets):
        mean_ret, cov = two_assets
        mc = monte_carlo_simulation(mean_ret, cov, n_portfolios=50)
        weight_cols = [c for c in mc.columns if c.startswith("w_")]
        sums = mc[weight_cols].sum(axis=1)
        np.testing.assert_allclose(sums, 1.0, atol=1e-6)


# ── prepare_optimization_inputs ──

class TestPrepareInputs:
    def test_shapes(self, returns_df):
        mean_ret, cov, tickers = prepare_optimization_inputs(returns_df)
        assert len(mean_ret) == 3
        assert cov.shape == (3, 3)
        assert tickers == ["AAPL", "MSFT", "BNP.PA"]

    def test_symmetric_cov(self, returns_df):
        _, cov, _ = prepare_optimization_inputs(returns_df)
        np.testing.assert_allclose(cov, cov.T)
