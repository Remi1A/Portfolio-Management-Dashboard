"""Page Overview — KPIs, NAV chart, allocation."""

import streamlit as st
import pandas as pd

from cyu_am.config.benchmarks import list_benchmarks, get_benchmark_ticker, DEFAULT_BENCHMARK
from cyu_am.data.database import get_portfolios
from cyu_am.data.cached import (
    reconstruct_nav, get_current_positions, get_current_cash, get_nav_with_benchmark,
)
from cyu_am.metrics.performance import (
    total_return, cagr, ytd_return, mtd_return, daily_returns, periods_summary,
)
from cyu_am.metrics.risk import (
    sharpe_ratio, sortino_ratio, max_drawdown, volatility,
)
from cyu_am.ui.components import kpi_card, section_header, portfolio_selector, empty_state, load_css
from cyu_am.ui.charts import nav_chart, allocation_pie, performance_bar
from cyu_am.utils.formatters import fmt_pct, fmt_eur, fmt_ratio


def render():
    load_css()
    st.title("Overview")

    # Sidebar
    portfolios = get_portfolios()
    pid = portfolio_selector(portfolios)
    if pid is None:
        empty_state("Creez un portefeuille dans l'onglet Transactions.")
        return

    benchmark_name = st.sidebar.selectbox("Benchmark", list_benchmarks(),
                                          index=list_benchmarks().index(DEFAULT_BENCHMARK))
    benchmark_ticker = get_benchmark_ticker(benchmark_name)

    # NAV
    with st.spinner("Calcul de la NAV..."):
        nav_df = reconstruct_nav(pid)

    if nav_df.empty:
        empty_state("Ajoutez des transactions pour voir la performance.")
        return

    nav = nav_df["nav"]
    rets = nav_df["daily_return"].dropna()

    # ── KPI Row 1 ──
    cash = get_current_cash(pid)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        val = nav.iloc[-1]
        prev = nav.iloc[-2] if len(nav) > 1 else val
        delta = (val - prev) / prev
        kpi_card("Valeur totale", fmt_eur(val), fmt_pct(delta), delta >= 0)
    with col2:
        kpi_card("Cash disponible", fmt_eur(cash), "", cash >= 0)
    with col3:
        tr = total_return(nav)
        kpi_card("Performance totale", fmt_pct(tr), "Depuis inception", tr >= 0)
    with col4:
        ytd = ytd_return(nav)
        kpi_card("YTD", fmt_pct(ytd), str(nav.index[-1].year), ytd >= 0)
    with col5:
        mtd = mtd_return(nav)
        kpi_card("MTD", fmt_pct(mtd), nav.index[-1].strftime("%b %Y"), mtd >= 0)

    st.markdown("")

    # ── KPI Row 2 ──
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        sr = sharpe_ratio(rets)
        kpi_card("Sharpe Ratio", fmt_ratio(sr), "Annualise", sr >= 0)
    with col6:
        so = sortino_ratio(rets)
        kpi_card("Sortino Ratio", fmt_ratio(so), "Annualise", so >= 0)
    with col7:
        mdd = max_drawdown(nav)
        kpi_card("Max Drawdown", fmt_pct(mdd), "", False)
    with col8:
        vol = volatility(rets)
        kpi_card("Volatilite ann.", fmt_pct(vol, 1), "", True)

    st.markdown("")

    # ── NAV Chart ──
    section_header("Valeur Liquidative vs Benchmark")
    nav_bench = get_nav_with_benchmark(pid, benchmark_ticker)
    if not nav_bench.empty:
        fig = nav_chart(
            nav_bench["nav_portfolio"],
            nav_bench["nav_benchmark"],
            benchmark_name,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        fig = nav_chart(nav / nav.iloc[0] * 100)
        st.plotly_chart(fig, use_container_width=True)

    # ── Allocation ──
    positions = get_current_positions(pid)
    if not positions.empty:
        col_alloc1, col_alloc2 = st.columns(2)

        with col_alloc1:
            section_header("Allocation par classe d'actif")
            class_alloc = positions.groupby("asset_class")["market_value_eur"].sum()
            labels_class = class_alloc.index.tolist()
            values_class = class_alloc.values.tolist()
            if cash > 0:
                labels_class.append("Cash")
                values_class.append(cash)
            fig_class = allocation_pie(labels_class, values_class, "Par classe d'actif")
            st.plotly_chart(fig_class, use_container_width=True)

        with col_alloc2:
            section_header("Allocation par actif")
            labels_asset = positions["ticker"].tolist()
            values_asset = positions["market_value_eur"].tolist()
            if cash > 0:
                labels_asset.append("Cash")
                values_asset.append(cash)
            fig_asset = allocation_pie(labels_asset, values_asset, "Par actif")
            st.plotly_chart(fig_asset, use_container_width=True)

        # ── Top / Bottom performers ──
        section_header("Performance par actif")
        sorted_pos = positions.sort_values("pnl_pct", ascending=True)
        fig_perf = performance_bar(
            sorted_pos["ticker"].tolist(),
            sorted_pos["pnl_pct"].tolist(),
        )
        st.plotly_chart(fig_perf, use_container_width=True)
