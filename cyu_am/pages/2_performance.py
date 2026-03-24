"""Page Performance — rendements, heatmap, underwater, rolling."""

import streamlit as st
import pandas as pd

from cyu_am.config.benchmarks import list_benchmarks, get_benchmark_ticker, DEFAULT_BENCHMARK
from cyu_am.data.database import get_portfolios
from cyu_am.data.cached import reconstruct_nav
from cyu_am.data.market_data import fetch_prices
from cyu_am.metrics.performance import (
    daily_returns, monthly_returns_table, cumulative_returns, periods_summary,
)
from cyu_am.metrics.rolling import rolling_volatility, rolling_sharpe
from cyu_am.ui.components import portfolio_selector, section_header, empty_state, load_css
from cyu_am.ui.charts import (
    monthly_heatmap, underwater_chart, cumulative_returns_chart,
    returns_distribution, rolling_chart,
)
from cyu_am.utils.formatters import fmt_pct


def render():
    load_css()
    st.title("Analyse de performance")

    portfolios = get_portfolios()
    pid = portfolio_selector(portfolios)
    if pid is None:
        empty_state("Creez un portefeuille dans l'onglet Transactions.")
        return

    benchmark_name = st.sidebar.selectbox("Benchmark", list_benchmarks(),
                                          index=list_benchmarks().index(DEFAULT_BENCHMARK),
                                          key="perf_bench")
    benchmark_ticker = get_benchmark_ticker(benchmark_name)

    with st.spinner("Calcul..."):
        nav_df = reconstruct_nav(pid)

    if nav_df.empty:
        empty_state("Ajoutez des transactions.")
        return

    nav = nav_df["nav"]
    rets = nav_df["daily_return"].dropna()

    # Benchmark returns
    bench_prices = fetch_prices(benchmark_ticker,
                                start=nav.index[0].strftime("%Y-%m-%d"))
    bench_rets = bench_prices["close"].pct_change().dropna() if not bench_prices.empty else pd.Series()
    common = rets.index.intersection(bench_rets.index)
    bench_rets_aligned = bench_rets.reindex(common)
    rets_aligned = rets.reindex(common)

    # ── Tableau comparatif ──
    section_header("Rendements par periode")
    port_summary = periods_summary(nav)

    if not bench_prices.empty:
        bench_nav = bench_prices["close"]
        bench_summary = periods_summary(bench_nav)
        comparison = pd.DataFrame({
            "Portefeuille": {k: fmt_pct(v) for k, v in port_summary.items()},
            benchmark_name: {k: fmt_pct(v) for k, v in bench_summary.items()},
            "Exces": {k: fmt_pct(port_summary[k] - bench_summary[k])
                      for k in port_summary},
        })
        st.dataframe(comparison, use_container_width=True)
    else:
        st.dataframe(
            pd.DataFrame({"Portefeuille": {k: fmt_pct(v) for k, v in port_summary.items()}}),
            use_container_width=True,
        )

    # ── Rendements cumulés ──
    section_header("Rendements cumules")
    cum_port = cumulative_returns(rets_aligned) if not rets_aligned.empty else cumulative_returns(rets)
    cum_bench = cumulative_returns(bench_rets_aligned) if not bench_rets_aligned.empty else None
    fig_cum = cumulative_returns_chart(cum_port, cum_bench, benchmark_name)
    st.plotly_chart(fig_cum, use_container_width=True)

    col1, col2 = st.columns(2)

    # ── Heatmap mensuelle ──
    with col1:
        section_header("Rendements mensuels")
        mt = monthly_returns_table(nav)
        if not mt.empty:
            fig_heat = monthly_heatmap(mt)
            st.plotly_chart(fig_heat, use_container_width=True)

    # ── Distribution ──
    with col2:
        section_header("Distribution des rendements")
        fig_dist = returns_distribution(rets)
        st.plotly_chart(fig_dist, use_container_width=True)

    # ── Underwater ──
    section_header("Underwater Chart")
    fig_uw = underwater_chart(nav)
    st.plotly_chart(fig_uw, use_container_width=True)

    # ── Rolling ──
    section_header("Metriques glissantes")
    tab_vol, tab_sharpe = st.tabs(["Volatilite rolling", "Sharpe rolling"])

    with tab_vol:
        df_vol = pd.DataFrame({
            "30j": rolling_volatility(rets, 30),
            "90j": rolling_volatility(rets, 90),
        }).dropna(how="all")
        if not df_vol.empty:
            fig_rvol = rolling_chart(df_vol, "Volatilite annualisee (rolling)", "Volatilite")
            st.plotly_chart(fig_rvol, use_container_width=True)

    with tab_sharpe:
        df_sharpe = pd.DataFrame({
            "30j": rolling_sharpe(rets, 30),
            "90j": rolling_sharpe(rets, 90),
        }).dropna(how="all")
        if not df_sharpe.empty:
            fig_rsh = rolling_chart(df_sharpe, "Sharpe Ratio (rolling)", "Sharpe")
            st.plotly_chart(fig_rsh, use_container_width=True)
