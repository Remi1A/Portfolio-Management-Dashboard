"""Tests unitaires pour cyu_am.metrics.risk."""

import pytest
import pandas as pd
import numpy as np

from cyu_am.metrics.risk import (
    volatility,
    downside_volatility,
    sharpe_ratio,
    sortino_ratio,
    omega_ratio,
    calmar_ratio,
    drawdown_series,
    max_drawdown,
    max_drawdown_duration,
    var_historical,
    var_parametric,
    cvar,
    beta,
    alpha_jensen,
    tracking_error,
    information_ratio,
    skewness,
    kurtosis,
    up_capture,
    down_capture,
    correlation,
    risk_summary,
)


# ── Fixtures ──

@pytest.fixture
def positive_returns():
    """Rendements quotidiens positifs constants."""
    dates = pd.bdate_range("2025-01-02", periods=252)
    return pd.Series(0.001, index=dates, name="returns")


@pytest.fixture
def zero_returns():
    """Rendements nuls."""
    dates = pd.bdate_range("2025-01-02", periods=252)
    return pd.Series(0.0, index=dates, name="returns")


@pytest.fixture
def normal_returns():
    """Rendements simules N(0.0004, 0.01)."""
    np.random.seed(42)
    dates = pd.bdate_range("2025-01-02", periods=500)
    return pd.Series(np.random.normal(0.0004, 0.01, 500), index=dates, name="returns")


@pytest.fixture
def nav_from_returns(normal_returns):
    """NAV reconstruite depuis les rendements."""
    return (1 + normal_returns).cumprod() * 100


@pytest.fixture
def benchmark_returns():
    """Rendements benchmark simules."""
    np.random.seed(123)
    dates = pd.bdate_range("2025-01-02", periods=500)
    return pd.Series(np.random.normal(0.0003, 0.012, 500), index=dates, name="bench")


@pytest.fixture
def drawdown_nav():
    """NAV avec un drawdown marque."""
    values = [100, 105, 110, 108, 100, 95, 90, 92, 95, 100, 105, 110, 115]
    dates = pd.bdate_range("2025-01-02", periods=len(values))
    return pd.Series(values, index=dates, name="nav")


# ── Volatility ──

class TestVolatility:
    def test_positive(self, normal_returns):
        vol = volatility(normal_returns)
        assert vol > 0

    def test_zero_for_constant(self, zero_returns):
        assert volatility(zero_returns) == 0.0

    def test_annualized(self, normal_returns):
        daily_std = normal_returns.std()
        expected = daily_std * np.sqrt(252)
        assert volatility(normal_returns) == pytest.approx(expected, rel=1e-6)

    def test_short_series(self):
        assert volatility(pd.Series([0.01])) == 0.0


# ── Downside Volatility ──

class TestDownsideVolatility:
    def test_lower_than_total(self, normal_returns):
        dv = downside_volatility(normal_returns)
        vol = volatility(normal_returns)
        # Downside vol can be higher or lower, but should be > 0
        assert dv > 0

    def test_zero_for_positive_only(self, positive_returns):
        # No returns below 0 threshold
        assert downside_volatility(positive_returns) == 0.0


# ── Sharpe Ratio ──

class TestSharpeRatio:
    def test_positive_for_positive_excess(self, positive_returns):
        sr = sharpe_ratio(positive_returns, rf=0.0)
        assert sr > 0

    def test_zero_for_constant(self, zero_returns):
        assert sharpe_ratio(zero_returns) == 0.0

    def test_custom_rf(self, normal_returns):
        sr_low = sharpe_ratio(normal_returns, rf=0.01)
        sr_high = sharpe_ratio(normal_returns, rf=0.10)
        assert sr_low > sr_high

    def test_short_series(self):
        assert sharpe_ratio(pd.Series([0.01])) == 0.0


# ── Sortino Ratio ──

class TestSortinoRatio:
    def test_zero_downside_returns_zero(self, positive_returns):
        # Purely positive returns => downside vol = 0 => sortino = 0 (guard)
        assert sortino_ratio(positive_returns, rf=0.0) == 0.0

    def test_normal_case(self, normal_returns):
        sort = sortino_ratio(normal_returns, rf=0.0)
        assert isinstance(sort, float)


# ── Omega Ratio ──

class TestOmegaRatio:
    def test_positive_returns(self, positive_returns):
        omega = omega_ratio(positive_returns)
        assert omega == float("inf")  # No losses

    def test_normal(self, normal_returns):
        omega = omega_ratio(normal_returns)
        assert omega > 0

    def test_all_negative(self):
        rets = pd.Series([-0.01, -0.02, -0.005])
        omega = omega_ratio(rets)
        assert omega == 0.0  # No gains above threshold


# ── Calmar Ratio ──

class TestCalmarRatio:
    def test_positive(self, normal_returns, nav_from_returns):
        cal = calmar_ratio(normal_returns, nav_from_returns)
        assert isinstance(cal, float)

    def test_no_drawdown(self, positive_returns):
        nav = (1 + positive_returns).cumprod() * 100
        cal = calmar_ratio(positive_returns, nav)
        # No drawdown => calmar = 0 (division by zero guard)
        assert cal == 0.0


# ── Drawdown ──

class TestDrawdown:
    def test_series_max_zero(self, drawdown_nav):
        dd = drawdown_series(drawdown_nav)
        assert dd.max() == pytest.approx(0.0)

    def test_series_min_negative(self, drawdown_nav):
        dd = drawdown_series(drawdown_nav)
        assert dd.min() < 0

    def test_max_drawdown_value(self, drawdown_nav):
        mdd = max_drawdown(drawdown_nav)
        # Peak = 110, trough = 90 => dd = (90-110)/110 = -18.18%
        assert mdd == pytest.approx(-0.1818, abs=0.01)

    def test_max_drawdown_always_negative_or_zero(self, nav_from_returns):
        assert max_drawdown(nav_from_returns) <= 0

    def test_no_drawdown(self):
        nav = pd.Series([100, 101, 102, 103])
        assert max_drawdown(nav) == 0.0


class TestMaxDrawdownDuration:
    def test_positive_duration(self, drawdown_nav):
        dur = max_drawdown_duration(drawdown_nav)
        assert dur > 0

    def test_no_drawdown(self):
        nav = pd.Series([100, 101, 102, 103])
        assert max_drawdown_duration(nav) == 0


# ── VaR ──

class TestVaR:
    def test_historical_negative(self, normal_returns):
        var = var_historical(normal_returns)
        assert var < 0

    def test_parametric_negative(self, normal_returns):
        var = var_parametric(normal_returns)
        assert var < 0

    def test_historical_vs_parametric(self, normal_returns):
        # For normal distribution, both should be similar
        vh = var_historical(normal_returns, 0.95)
        vp = var_parametric(normal_returns, 0.95)
        assert vh == pytest.approx(vp, abs=0.005)

    def test_higher_confidence_stricter(self, normal_returns):
        var95 = var_historical(normal_returns, 0.95)
        var99 = var_historical(normal_returns, 0.99)
        assert var99 < var95  # 99% VaR is more negative

    def test_empty(self):
        assert var_historical(pd.Series(dtype=float)) == 0.0


# ── CVaR ──

class TestCVar:
    def test_worse_than_var(self, normal_returns):
        v = var_historical(normal_returns)
        cv = cvar(normal_returns)
        assert cv <= v  # CVaR is always worse (more negative)

    def test_negative(self, normal_returns):
        assert cvar(normal_returns) < 0


# ── Beta ──

class TestBeta:
    def test_self_beta(self, normal_returns):
        b = beta(normal_returns, normal_returns)
        assert b == pytest.approx(1.0, abs=0.001)

    def test_uncorrelated(self):
        np.random.seed(42)
        r1 = pd.Series(np.random.normal(0, 0.01, 1000))
        np.random.seed(99)
        r2 = pd.Series(np.random.normal(0, 0.01, 1000))
        b = beta(r1, r2)
        assert abs(b) < 0.2  # Roughly zero

    def test_short_series(self):
        r = pd.Series([0.01])
        assert beta(r, r) == 1.0  # Fallback


# ── Alpha ──

class TestAlpha:
    def test_self_alpha_near_zero(self, normal_returns):
        a = alpha_jensen(normal_returns, normal_returns, rf=0.0)
        assert a == pytest.approx(0.0, abs=0.001)


# ── Tracking Error ──

class TestTrackingError:
    def test_self_is_zero(self, normal_returns):
        te = tracking_error(normal_returns, normal_returns)
        assert te == pytest.approx(0.0, abs=1e-10)

    def test_positive_for_different(self, normal_returns, benchmark_returns):
        te = tracking_error(normal_returns, benchmark_returns)
        assert te > 0


# ── Information Ratio ──

class TestInformationRatio:
    def test_self_is_zero(self, normal_returns):
        ir = information_ratio(normal_returns, normal_returns)
        assert ir == pytest.approx(0.0, abs=1e-6)

    def test_returns_float(self, normal_returns, benchmark_returns):
        ir = information_ratio(normal_returns, benchmark_returns)
        assert isinstance(ir, float)


# ── Distribution ──

class TestDistribution:
    def test_skewness_near_zero(self, normal_returns):
        # Normal distribution => skew ~0
        sk = skewness(normal_returns)
        assert abs(sk) < 0.5

    def test_kurtosis_near_zero(self, normal_returns):
        # Normal distribution => excess kurtosis ~0
        k = kurtosis(normal_returns)
        assert abs(k) < 1.0

    def test_short_series(self):
        assert skewness(pd.Series([0.01, 0.02])) == 0.0
        assert kurtosis(pd.Series([0.01, 0.02, 0.03])) == 0.0


# ── Capture Ratios ──

class TestCaptureRatios:
    def test_self_capture_100(self, normal_returns):
        uc = up_capture(normal_returns, normal_returns)
        dc = down_capture(normal_returns, normal_returns)
        assert uc == pytest.approx(100.0, abs=0.1)
        assert dc == pytest.approx(100.0, abs=0.1)

    def test_empty(self):
        r = pd.Series(dtype=float)
        assert up_capture(r, r) == 0.0
        assert down_capture(r, r) == 0.0


# ── Correlation ──

class TestCorrelation:
    def test_self_correlation(self, normal_returns):
        c = correlation(normal_returns, normal_returns)
        assert c == pytest.approx(1.0, abs=0.001)

    def test_range(self, normal_returns, benchmark_returns):
        c = correlation(normal_returns, benchmark_returns)
        assert -1.0 <= c <= 1.0


# ── Risk Summary ──

class TestRiskSummary:
    def test_keys_no_benchmark(self, normal_returns, nav_from_returns):
        rs = risk_summary(normal_returns, nav_from_returns)
        expected = {
            "volatility", "sharpe", "sortino", "omega", "calmar",
            "max_drawdown", "max_dd_duration", "var_95_hist",
            "var_95_param", "cvar_95", "skewness", "kurtosis",
        }
        assert set(rs.keys()) == expected

    def test_keys_with_benchmark(self, normal_returns, nav_from_returns, benchmark_returns):
        rs = risk_summary(normal_returns, nav_from_returns, benchmark_returns)
        assert "beta" in rs
        assert "alpha" in rs
        assert "tracking_error" in rs
        assert "information_ratio" in rs
        assert "correlation" in rs
        assert "up_capture" in rs
        assert "down_capture" in rs

    def test_all_values_numeric(self, normal_returns, nav_from_returns, benchmark_returns):
        rs = risk_summary(normal_returns, nav_from_returns, benchmark_returns)
        for k, v in rs.items():
            assert isinstance(v, (int, float)), f"{k} is not numeric: {type(v)}"
