"""Page Risques — métriques de risque, corrélation, VaR, stress tests, concentration, secteurs, géographie."""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

from cyu_am.config.benchmarks import list_benchmarks, get_benchmark_ticker, DEFAULT_BENCHMARK
from cyu_am.config.tickers import UNIVERSE, get_sector, get_country, get_region
from cyu_am.data.database import get_portfolios
from cyu_am.data.cached import reconstruct_nav, get_current_positions
from cyu_am.data.market_data import fetch_prices, fetch_multiple
from cyu_am.metrics.performance import daily_returns
from cyu_am.metrics.risk import risk_summary, drawdown_series
from cyu_am.ui.components import portfolio_selector, section_header, empty_state, load_css
from cyu_am.ui.charts import correlation_matrix, underwater_chart, returns_distribution, allocation_pie
from cyu_am.utils.formatters import fmt_pct, fmt_ratio, fmt_days


@st.cache_data(ttl=86400, show_spinner=False)
def _fetch_ticker_info(ticker: str) -> dict:
    """Recupere sector, country, industry depuis yfinance (cache 24h)."""
    try:
        info = yf.Ticker(ticker).info
        return {
            "sector": info.get("sector", "N/A"),
            "country": info.get("country", "N/A"),
            "industry": info.get("industry", "N/A"),
        }
    except Exception:
        return {"sector": "N/A", "country": "N/A", "industry": "N/A"}


def _enrich_positions(positions: pd.DataFrame) -> pd.DataFrame:
    """Ajoute sector, country, region a chaque position."""
    sectors, countries, regions = [], [], []
    for _, row in positions.iterrows():
        ticker = row["ticker"]
        if ticker in UNIVERSE:
            sectors.append(get_sector(ticker))
            countries.append(get_country(ticker))
            regions.append(get_region(ticker))
        else:
            info = _fetch_ticker_info(ticker)
            sectors.append(info["sector"])
            countries.append(info["country"])
            regions.append("N/A")
    positions = positions.copy()
    positions["sector"] = sectors
    positions["country"] = countries
    positions["region"] = regions
    return positions


def _hhi(weights: pd.Series) -> float:
    """Herfindahl-Hirschman Index (0-10000). >2500 = highly concentrated."""
    shares = weights / weights.sum() * 100
    return float((shares ** 2).sum())


def _render_sector_geo_analysis(positions: pd.DataFrame):
    """Affiche l'analyse de concentration sectorielle et geographique."""
    enriched = _enrich_positions(positions)
    # Exclure forex de l'analyse
    enriched = enriched[enriched["sector"] != "FX"]
    if enriched.empty:
        return

    # ── Concentration sectorielle ──
    section_header("Analyse sectorielle")
    sector_weights = enriched.groupby("sector")["market_value_eur"].sum()
    sector_pct = (sector_weights / sector_weights.sum() * 100).sort_values(ascending=False)

    col_s1, col_s2 = st.columns([1, 1])
    with col_s1:
        fig_sector = allocation_pie(
            labels=sector_pct.index.tolist(),
            values=sector_pct.values.tolist(),
            title="Repartition sectorielle",
        )
        st.plotly_chart(fig_sector, use_container_width=True)
    with col_s2:
        sector_table = pd.DataFrame({
            "Secteur": sector_pct.index,
            "Poids (%)": [f"{v:.1f}%" for v in sector_pct.values],
            "Valeur (EUR)": [f"{sector_weights[s]:,.0f}".replace(",", " ") for s in sector_pct.index],
            "Nb actifs": [int((enriched["sector"] == s).sum()) for s in sector_pct.index],
        })
        st.dataframe(sector_table, use_container_width=True, hide_index=True)

        hhi_sector = _hhi(sector_pct)
        if hhi_sector > 2500:
            level = "Eleve"
        elif hhi_sector > 1500:
            level = "Modere"
        else:
            level = "Diversifie"
        st.metric("HHI sectoriel", f"{hhi_sector:,.0f}", help=f"Concentration: {level} (>2500=eleve, <1500=diversifie)")

    # ── Concentration géographique ──
    section_header("Analyse geographique")
    geo_enriched = enriched[enriched["country"] != "N/A"]
    if geo_enriched.empty:
        st.info("Pas de donnees geographiques disponibles.")
        return

    # Par pays
    country_weights = geo_enriched.groupby("country")["market_value_eur"].sum()
    country_pct = (country_weights / country_weights.sum() * 100).sort_values(ascending=False)

    # Par region
    region_weights = geo_enriched.groupby("region")["market_value_eur"].sum()
    region_pct = (region_weights / region_weights.sum() * 100).sort_values(ascending=False)

    col_g1, col_g2 = st.columns([1, 1])
    with col_g1:
        fig_country = allocation_pie(
            labels=country_pct.index.tolist(),
            values=country_pct.values.tolist(),
            title="Repartition par pays",
        )
        st.plotly_chart(fig_country, use_container_width=True)
    with col_g2:
        fig_region = allocation_pie(
            labels=region_pct.index.tolist(),
            values=region_pct.values.tolist(),
            title="Repartition par region",
        )
        st.plotly_chart(fig_region, use_container_width=True)

    # Tableau détaillé par pays
    country_table = pd.DataFrame({
        "Pays": country_pct.index,
        "Poids (%)": [f"{v:.1f}%" for v in country_pct.values],
        "Valeur (EUR)": [f"{country_weights[c]:,.0f}".replace(",", " ") for c in country_pct.index],
        "Nb actifs": [int((geo_enriched["country"] == c).sum()) for c in country_pct.index],
    })
    st.dataframe(country_table, use_container_width=True, hide_index=True)

    col_hhi1, col_hhi2 = st.columns(2)
    with col_hhi1:
        hhi_country = _hhi(country_pct)
        level_c = "Eleve" if hhi_country > 2500 else ("Modere" if hhi_country > 1500 else "Diversifie")
        st.metric("HHI par pays", f"{hhi_country:,.0f}", help=f"Concentration: {level_c}")
    with col_hhi2:
        hhi_region = _hhi(region_pct)
        level_r = "Eleve" if hhi_region > 2500 else ("Modere" if hhi_region > 1500 else "Diversifie")
        st.metric("HHI par region", f"{hhi_region:,.0f}", help=f"Concentration: {level_r}")


def render():
    load_css()
    st.title("Analyse des risques")

    portfolios = get_portfolios()
    pid = portfolio_selector(portfolios)
    if pid is None:
        empty_state("Creez un portefeuille dans l'onglet Transactions.")
        return

    benchmark_name = st.sidebar.selectbox("Benchmark", list_benchmarks(),
                                          index=list_benchmarks().index(DEFAULT_BENCHMARK),
                                          key="risk_bench")
    benchmark_ticker = get_benchmark_ticker(benchmark_name)

    with st.spinner("Calcul..."):
        nav_df = reconstruct_nav(pid)

    if nav_df.empty:
        empty_state("Ajoutez des transactions.")
        return

    nav = nav_df["nav"]
    rets = nav_df["daily_return"].dropna()

    # Benchmark
    bench_prices = fetch_prices(benchmark_ticker, start=nav.index[0].strftime("%Y-%m-%d"))
    bench_rets = None
    if not bench_prices.empty:
        br = bench_prices["close"].pct_change().dropna()
        common = rets.index.intersection(br.index)
        bench_rets = br.reindex(common)
        rets_for_bench = rets.reindex(common)
    else:
        rets_for_bench = rets

    # ── Tableau des métriques ──
    section_header("Metriques de risque")
    rs = risk_summary(rets, nav, bench_rets)

    # Formater pour affichage
    display = {
        "Volatilite annualisee": fmt_pct(rs["volatility"], 1),
        "Sharpe Ratio": fmt_ratio(rs["sharpe"]),
        "Sortino Ratio": fmt_ratio(rs["sortino"]),
        "Omega Ratio": fmt_ratio(rs["omega"]),
        "Calmar Ratio": fmt_ratio(rs["calmar"]),
        "Max Drawdown": fmt_pct(rs["max_drawdown"]),
        "Duree max drawdown": fmt_days(rs["max_dd_duration"]),
        "VaR 95% (historique)": fmt_pct(rs["var_95_hist"]),
        "VaR 95% (parametrique)": fmt_pct(rs["var_95_param"]),
        "CVaR 95%": fmt_pct(rs["cvar_95"]),
        "Skewness": fmt_ratio(rs["skewness"]),
        "Kurtosis": fmt_ratio(rs["kurtosis"]),
    }

    if bench_rets is not None:
        display.update({
            f"Beta vs {benchmark_name}": fmt_ratio(rs.get("beta", 0)),
            f"Alpha vs {benchmark_name}": fmt_pct(rs.get("alpha", 0)),
            "Tracking Error": fmt_pct(rs.get("tracking_error", 0), 1),
            "Information Ratio": fmt_ratio(rs.get("information_ratio", 0)),
            f"Correlation vs {benchmark_name}": fmt_ratio(rs.get("correlation", 0)),
            "Up Capture (%)": fmt_ratio(rs.get("up_capture", 0), 1),
            "Down Capture (%)": fmt_ratio(rs.get("down_capture", 0), 1),
        })

    col1, col2 = st.columns(2)
    items = list(display.items())
    mid = len(items) // 2
    with col1:
        df1 = pd.DataFrame(items[:mid], columns=["Metrique", "Valeur"])
        st.dataframe(df1, use_container_width=True, hide_index=True)
    with col2:
        df2 = pd.DataFrame(items[mid:], columns=["Metrique", "Valeur"])
        st.dataframe(df2, use_container_width=True, hide_index=True)

    # ── Matrice de corrélation ──
    positions = get_current_positions(pid)
    if not positions.empty and len(positions) > 1:
        section_header("Matrice de correlation entre actifs")
        tickers = positions["ticker"].tolist()
        all_prices = fetch_multiple(tickers, start=nav.index[0].strftime("%Y-%m-%d"))
        returns_dict = {}
        for t in tickers:
            p = all_prices.get(t, pd.DataFrame())
            if not p.empty:
                returns_dict[t] = p["close"].pct_change().dropna()

        if len(returns_dict) > 1:
            corr_df = pd.DataFrame(returns_dict).corr()
            fig_corr = correlation_matrix(corr_df)
            st.plotly_chart(fig_corr, use_container_width=True)

    # ── VaR Visualization ──
    section_header("Value at Risk")
    col_var1, col_var2 = st.columns(2)
    with col_var1:
        st.metric("VaR 95% historique (1 jour)", fmt_pct(rs["var_95_hist"]))
        st.metric("VaR 95% parametrique (1 jour)", fmt_pct(rs["var_95_param"]))
    with col_var2:
        st.metric("CVaR / Expected Shortfall", fmt_pct(rs["cvar_95"]))
        current_value = nav.iloc[-1]
        var_eur = current_value * rs["var_95_hist"]
        st.metric("VaR en EUR (1 jour)", f"{var_eur:,.0f} EUR".replace(",", " "))

    # ── Stress tests ──
    section_header("Stress tests")
    shocks = [-0.05, -0.10, -0.20, -0.30]
    stress_data = []
    for shock in shocks:
        impact = current_value * shock
        stress_data.append({
            "Scenario": f"Choc {shock*100:+.0f}%",
            "Impact (EUR)": f"{impact:,.0f} EUR".replace(",", " "),
            "NAV post-choc": f"{current_value + impact:,.0f} EUR".replace(",", " "),
        })
    st.dataframe(pd.DataFrame(stress_data), use_container_width=True, hide_index=True)

    # ── Analyse sectorielle & géographique ──
    if not positions.empty:
        _render_sector_geo_analysis(positions)
