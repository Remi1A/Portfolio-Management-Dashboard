"""Cached wrappers for expensive portfolio engine functions.

Uses @st.cache_data to avoid recomputing NAV and positions on every
Streamlit re-render.  Import these instead of the raw functions in pages.
"""

import streamlit as st
import pandas as pd

from cyu_am.data.portfolio_engine import (
    reconstruct_nav as _reconstruct_nav,
    get_current_positions as _get_current_positions,
    get_current_cash as _get_current_cash,
    get_nav_with_benchmark as _get_nav_with_benchmark,
)

CACHE_TTL = 300  # 5 minutes


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def reconstruct_nav(portfolio_id: int, start: str = None,
                    end: str = None) -> pd.DataFrame:
    return _reconstruct_nav(portfolio_id, start, end)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_current_positions(portfolio_id: int) -> pd.DataFrame:
    return _get_current_positions(portfolio_id)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_current_cash(portfolio_id: int) -> float:
    return _get_current_cash(portfolio_id)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_nav_with_benchmark(portfolio_id: int, benchmark_ticker: str,
                           start: str = None, end: str = None,
                           base: float = 100.0) -> pd.DataFrame:
    return _get_nav_with_benchmark(portfolio_id, benchmark_ticker, start, end, base)


def clear_portfolio_cache():
    """Call after adding/modifying transactions to force fresh data."""
    reconstruct_nav.clear()
    get_current_positions.clear()
    get_current_cash.clear()
    get_nav_with_benchmark.clear()
