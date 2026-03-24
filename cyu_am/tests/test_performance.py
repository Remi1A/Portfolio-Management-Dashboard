"""Tests unitaires pour cyu_am.metrics.performance."""

import pytest
import pandas as pd
import numpy as np

from cyu_am.metrics.performance import (
    total_return,
    cagr,
    ytd_return,
    mtd_return,
    daily_returns,
    monthly_returns,
    monthly_returns_table,
    cumulative_returns,
    annualized_return,
    period_return,
    periods_summary,
)


# ── Fixtures ──

@pytest.fixture
def flat_nav():
    """NAV constante a 100."""
    dates = pd.bdate_range("2025-01-02", periods=252)
    return pd.Series(100.0, index=dates, name="nav")


@pytest.fixture
def growing_nav():
    """NAV qui double lineairement sur 252 jours (100 -> 200)."""
    dates = pd.bdate_range("2025-01-02", periods=252)
    values = np.linspace(100, 200, 252)
    return pd.Series(values, index=dates, name="nav")


@pytest.fixture
def known_nav():
    """NAV avec valeurs connues pour calculs exacts."""
    dates = pd.bdate_range("2024-01-02", periods=504)  # ~2 ans
    # Rendement quotidien constant de 0.04% => ~10.5% annualise
    daily_ret = 0.0004
    values = 100 * (1 + daily_ret) ** np.arange(504)
    return pd.Series(values, index=dates, name="nav")


@pytest.fixture
def short_nav():
    """NAV tres courte (1 seul point)."""
    return pd.Series([100.0], index=[pd.Timestamp("2025-06-01")], name="nav")


@pytest.fixture
def empty_nav():
    return pd.Series(dtype=float, name="nav")


# ── total_return ──

class TestTotalReturn:
    def test_basic(self, growing_nav):
        assert total_return(growing_nav) == pytest.approx(1.0, abs=0.01)

    def test_flat(self, flat_nav):
        assert total_return(flat_nav) == pytest.approx(0.0)

    def test_short_series(self, short_nav):
        assert total_return(short_nav) == 0.0

    def test_negative_return(self):
        nav = pd.Series([200.0, 100.0], index=pd.bdate_range("2025-01-02", periods=2))
        assert total_return(nav) == pytest.approx(-0.5)


# ── cagr ──

class TestCagr:
    def test_one_year_doubling(self):
        dates = pd.bdate_range("2025-01-02", periods=252)
        nav = pd.Series([100.0] + [200.0] * 251, index=dates)
        nav.iloc[0] = 100.0
        nav = pd.Series(np.linspace(100, 200, 252), index=dates)
        result = cagr(nav, periods_per_year=252)
        # Over 1 year (252 days), 100->200 => CAGR = 100%
        assert result == pytest.approx(1.0, abs=0.01)

    def test_flat(self, flat_nav):
        assert cagr(flat_nav) == pytest.approx(0.0)

    def test_short(self, short_nav):
        assert cagr(short_nav) == 0.0

    def test_positive(self, known_nav):
        result = cagr(known_nav)
        assert result > 0


# ── ytd_return ──

class TestYtdReturn:
    def test_basic(self, growing_nav):
        result = ytd_return(growing_nav)
        assert result > 0

    def test_empty(self, empty_nav):
        assert ytd_return(empty_nav) == 0.0


# ── mtd_return ──

class TestMtdReturn:
    def test_basic(self, growing_nav):
        result = mtd_return(growing_nav)
        assert isinstance(result, float)

    def test_empty(self, empty_nav):
        assert mtd_return(empty_nav) == 0.0


# ── daily_returns ──

class TestDailyReturns:
    def test_length(self, growing_nav):
        rets = daily_returns(growing_nav)
        assert len(rets) == len(growing_nav) - 1

    def test_no_nans(self, growing_nav):
        rets = daily_returns(growing_nav)
        assert not rets.isna().any()

    def test_flat_returns_zero(self, flat_nav):
        rets = daily_returns(flat_nav)
        assert (rets == 0.0).all()


# ── monthly_returns ──

class TestMonthlyReturns:
    def test_returns_series(self, known_nav):
        mr = monthly_returns(known_nav)
        assert isinstance(mr, pd.Series)
        assert len(mr) > 0

    def test_positive_for_growing(self, growing_nav):
        mr = monthly_returns(growing_nav)
        assert (mr > 0).all()


# ── monthly_returns_table ──

class TestMonthlyReturnsTable:
    def test_pivot_shape(self, known_nav):
        mt = monthly_returns_table(known_nav)
        assert isinstance(mt, pd.DataFrame)
        assert mt.shape[0] > 0  # au moins 1 annee
        assert mt.shape[1] <= 12  # max 12 mois

    def test_empty_input(self):
        nav = pd.Series([100.0], index=[pd.Timestamp("2025-01-01")])
        mt = monthly_returns_table(nav)
        # Trop court pour avoir des rendements mensuels
        assert mt.empty


# ── cumulative_returns ──

class TestCumulativeReturns:
    def test_starts_near_zero(self, growing_nav):
        rets = daily_returns(growing_nav)
        cum = cumulative_returns(rets)
        assert cum.iloc[0] == pytest.approx(rets.iloc[0], abs=1e-6)

    def test_ends_at_total_return(self, growing_nav):
        rets = daily_returns(growing_nav)
        cum = cumulative_returns(rets)
        expected = total_return(growing_nav)
        assert cum.iloc[-1] == pytest.approx(expected, abs=0.01)


# ── annualized_return ──

class TestAnnualizedReturn:
    def test_positive(self, known_nav):
        rets = daily_returns(known_nav)
        ar = annualized_return(rets)
        assert ar > 0

    def test_empty(self):
        assert annualized_return(pd.Series(dtype=float)) == 0.0

    def test_consistency_with_cagr(self, known_nav):
        rets = daily_returns(known_nav)
        ar = annualized_return(rets)
        c = cagr(known_nav)
        # Should be close (not exact due to different formulas)
        assert ar == pytest.approx(c, abs=0.02)


# ── period_return ──

class TestPeriodReturn:
    def test_max_equals_total(self, growing_nav):
        assert period_return(growing_nav, "MAX") == pytest.approx(total_return(growing_nav))

    def test_ytd_matches(self, growing_nav):
        assert period_return(growing_nav, "YTD") == pytest.approx(ytd_return(growing_nav))

    def test_empty(self, empty_nav):
        assert period_return(empty_nav, "1M") == 0.0

    def test_unknown_period(self, growing_nav):
        assert period_return(growing_nav, "INVALID") == 0.0


# ── periods_summary ──

class TestPeriodsSummary:
    def test_all_keys(self, growing_nav):
        summary = periods_summary(growing_nav)
        expected_keys = {"1M", "3M", "6M", "1Y", "YTD", "MAX"}
        assert set(summary.keys()) == expected_keys

    def test_all_floats(self, growing_nav):
        summary = periods_summary(growing_nav)
        for v in summary.values():
            assert isinstance(v, float)
