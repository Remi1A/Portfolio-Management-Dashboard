"""Tests unitaires pour cyu_am.metrics.rolling."""

import pytest
import pandas as pd
import numpy as np

from cyu_am.metrics.rolling import (
    rolling_volatility,
    rolling_sharpe,
    rolling_beta,
    rolling_max_drawdown,
    rolling_correlation,
    all_rolling_metrics,
)


@pytest.fixture
def returns():
    np.random.seed(42)
    dates = pd.bdate_range("2024-01-02", periods=300)
    return pd.Series(np.random.normal(0.0004, 0.01, 300), index=dates, name="port")


@pytest.fixture
def bench_returns():
    np.random.seed(123)
    dates = pd.bdate_range("2024-01-02", periods=300)
    return pd.Series(np.random.normal(0.0003, 0.012, 300), index=dates, name="bench")


@pytest.fixture
def nav(returns):
    return (1 + returns).cumprod() * 100


# ── Rolling Volatility ──

class TestRollingVolatility:
    def test_output_length(self, returns):
        rv = rolling_volatility(returns, window=30)
        assert len(rv) == len(returns)

    def test_first_values_nan(self, returns):
        rv = rolling_volatility(returns, window=30)
        assert rv.iloc[:29].isna().all()

    def test_positive_values(self, returns):
        rv = rolling_volatility(returns, window=30).dropna()
        assert (rv > 0).all()


# ── Rolling Sharpe ──

class TestRollingSharpe:
    def test_output_length(self, returns):
        rs = rolling_sharpe(returns, window=30)
        assert len(rs) == len(returns)

    def test_returns_series(self, returns):
        rs = rolling_sharpe(returns, window=30)
        assert isinstance(rs, pd.Series)


# ── Rolling Beta ──

class TestRollingBeta:
    def test_self_beta_is_one(self, returns):
        rb = rolling_beta(returns, returns, window=30).dropna()
        # Beta of a series with itself should be 1.0
        assert rb.iloc[-1] == pytest.approx(1.0, abs=0.001)

    def test_output_type(self, returns, bench_returns):
        rb = rolling_beta(returns, bench_returns, window=30)
        assert isinstance(rb, pd.Series)


# ── Rolling Max Drawdown ──

class TestRollingMaxDrawdown:
    def test_always_negative_or_zero(self, nav):
        rmdd = rolling_max_drawdown(nav, window=90).dropna()
        assert (rmdd <= 0).all()

    def test_output_length(self, nav):
        rmdd = rolling_max_drawdown(nav, window=90)
        assert len(rmdd) == len(nav)


# ── Rolling Correlation ──

class TestRollingCorrelation:
    def test_self_correlation_is_one(self, returns):
        rc = rolling_correlation(returns, returns, window=30).dropna()
        assert rc.iloc[-1] == pytest.approx(1.0, abs=0.001)

    def test_range(self, returns, bench_returns):
        rc = rolling_correlation(returns, bench_returns, window=30).dropna()
        assert (rc >= -1.0).all() and (rc <= 1.0).all()


# ── All Rolling Metrics ──

class TestAllRollingMetrics:
    def test_keys_no_benchmark(self, returns, nav):
        result = all_rolling_metrics(returns, nav)
        assert "volatility" in result
        assert "sharpe" in result
        assert "max_drawdown" in result

    def test_keys_with_benchmark(self, returns, nav, bench_returns):
        result = all_rolling_metrics(returns, nav, bench_returns)
        assert "beta" in result
        assert "correlation" in result

    def test_dataframe_values(self, returns, nav):
        result = all_rolling_metrics(returns, nav)
        for name, df in result.items():
            assert isinstance(df, pd.DataFrame)
            assert len(df) > 0
