"""Page Optimisation — Markowitz, frontière efficiente, Monte Carlo."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from cyu_am.config.settings import COLORS
from cyu_am.config.tickers import UNIVERSE
from cyu_am.data.database import get_portfolios
from cyu_am.data.cached import get_current_positions
from cyu_am.data.market_data import fetch_prices, fetch_multiple
from cyu_am.metrics.optimization import (
    prepare_optimization_inputs,
    min_variance_portfolio,
    max_sharpe_portfolio,
    efficient_frontier,
    monte_carlo_simulation,
)
from cyu_am.ui.components import portfolio_selector, section_header, empty_state, load_css
from cyu_am.utils.formatters import fmt_pct, fmt_ratio


def render():
    load_css()
    st.title("Optimisation de portefeuille")

    portfolios = get_portfolios()
    pid = portfolio_selector(portfolios)
    if pid is None:
        empty_state("Creez un portefeuille dans l'onglet Transactions.")
        return

    positions = get_current_positions(pid)
    if positions.empty or len(positions) < 2:
        empty_state("Il faut au moins 2 positions pour l'optimisation.")
        return

    tickers = positions["ticker"].tolist()

    # Paramètres sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Optimisation")
    n_simulations = st.sidebar.slider("Simulations Monte Carlo", 500, 10000, 3000, 500)
    allow_short = st.sidebar.checkbox("Autoriser les ventes a decouvert", value=False)
    lookback = st.sidebar.selectbox("Historique", ["1A", "2A", "3A"], index=1)
    lookback_days = {"1A": 365, "2A": 730, "3A": 1095}
    start_date = (pd.Timestamp.now() - pd.Timedelta(days=lookback_days[lookback])).strftime("%Y-%m-%d")

    # Charger les rendements (batch fetch)
    with st.spinner("Chargement des donnees de marche..."):
        all_prices = fetch_multiple(tickers, start=start_date)
        returns_dict = {}
        for t in tickers:
            prices = all_prices.get(t, pd.DataFrame())
            if not prices.empty and len(prices) > 20:
                returns_dict[t] = prices["close"].pct_change().dropna()

    if len(returns_dict) < 2:
        empty_state("Pas assez de donnees de prix pour l'optimisation.")
        return

    returns_df = pd.DataFrame(returns_dict).dropna()
    valid_tickers = returns_df.columns.tolist()

    if len(returns_df) < 30:
        empty_state("Pas assez de jours de donnees (min 30).")
        return

    mean_returns, cov_matrix, _ = prepare_optimization_inputs(returns_df)

    # ── Calculs ──
    with st.spinner("Optimisation en cours..."):
        min_var = min_variance_portfolio(mean_returns, cov_matrix, allow_short)
        max_sr = max_sharpe_portfolio(mean_returns, cov_matrix, allow_short)
        ef = efficient_frontier(mean_returns, cov_matrix, n_points=50, allow_short=allow_short)
        mc = monte_carlo_simulation(mean_returns, cov_matrix, n_simulations)

    # ── Allocation actuelle ──
    current_weights = positions.set_index("ticker")["weight"].reindex(valid_tickers).fillna(0).values / 100
    from cyu_am.metrics.optimization import portfolio_stats
    cur_ret, cur_vol, cur_sharpe = portfolio_stats(current_weights, mean_returns, cov_matrix)

    # ── Graphique frontière efficiente ──
    section_header("Frontiere efficiente de Markowitz")

    fig = go.Figure()

    # Monte Carlo scatter
    fig.add_trace(go.Scatter(
        x=mc["volatility"] * 100, y=mc["return"] * 100,
        mode="markers",
        marker=dict(
            size=3, color=mc["sharpe"],
            colorscale="Viridis", colorbar=dict(title="Sharpe"),
            opacity=0.5,
        ),
        name="Monte Carlo",
        hovertemplate="Vol: %{x:.1f}%<br>Ret: %{y:.1f}%<extra></extra>",
    ))

    # Frontière efficiente
    if not ef.empty:
        fig.add_trace(go.Scatter(
            x=ef["volatility"] * 100, y=ef["return"] * 100,
            mode="lines",
            line=dict(color=COLORS["accent"], width=3),
            name="Frontiere efficiente",
        ))

    # Min variance
    fig.add_trace(go.Scatter(
        x=[min_var["volatility"] * 100], y=[min_var["return"] * 100],
        mode="markers",
        marker=dict(size=15, color="#FF9F43", symbol="diamond"),
        name=f"Min Variance (Sharpe: {min_var['sharpe']:.2f})",
    ))

    # Max Sharpe
    fig.add_trace(go.Scatter(
        x=[max_sr["volatility"] * 100], y=[max_sr["return"] * 100],
        mode="markers",
        marker=dict(size=15, color=COLORS["positive"], symbol="star"),
        name=f"Max Sharpe ({max_sr['sharpe']:.2f})",
    ))

    # Portefeuille actuel
    fig.add_trace(go.Scatter(
        x=[cur_vol * 100], y=[cur_ret * 100],
        mode="markers",
        marker=dict(size=15, color=COLORS["negative"], symbol="x"),
        name=f"Actuel (Sharpe: {cur_sharpe:.2f})",
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["bg"],
        xaxis_title="Volatilite annualisee (%)",
        yaxis_title="Rendement annualise (%)",
        height=550,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Comparaison des allocations ──
    section_header("Comparaison des allocations")

    alloc_df = pd.DataFrame({
        "Actif": valid_tickers,
        "Nom": [UNIVERSE.get(t, {}).get("name", t) for t in valid_tickers],
        "Actuel (%)": current_weights * 100,
        "Min Variance (%)": min_var["weights"] * 100,
        "Max Sharpe (%)": max_sr["weights"] * 100,
    })
    # Filtrer les poids < 0.1% pour la lisibilité
    alloc_df = alloc_df[
        (alloc_df["Actuel (%)"].abs() > 0.1) |
        (alloc_df["Min Variance (%)"].abs() > 0.1) |
        (alloc_df["Max Sharpe (%)"].abs() > 0.1)
    ]

    st.dataframe(
        alloc_df.style.format({
            "Actuel (%)": "{:.1f}%",
            "Min Variance (%)": "{:.1f}%",
            "Max Sharpe (%)": "{:.1f}%",
        }),
        use_container_width=True,
        hide_index=True,
    )

    # ── Stats comparatives ──
    section_header("Metriques comparatives")
    comp_data = {
        "": ["Rendement ann.", "Volatilite ann.", "Sharpe Ratio"],
        "Actuel": [fmt_pct(cur_ret), fmt_pct(cur_vol, 1), fmt_ratio(cur_sharpe)],
        "Min Variance": [fmt_pct(min_var["return"]), fmt_pct(min_var["volatility"], 1),
                         fmt_ratio(min_var["sharpe"])],
        "Max Sharpe": [fmt_pct(max_sr["return"]), fmt_pct(max_sr["volatility"], 1),
                       fmt_ratio(max_sr["sharpe"])],
    }
    st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

    # ── Allocation bar chart ──
    section_header("Allocation optimale (Max Sharpe)")
    weights_sr = pd.Series(max_sr["weights"], index=valid_tickers)
    weights_sr = weights_sr[weights_sr.abs() > 0.005].sort_values(ascending=True)

    if not weights_sr.empty:
        fig_bar = go.Figure(go.Bar(
            x=weights_sr.values * 100,
            y=[f"{t} ({UNIVERSE.get(t, {}).get('name', t)})" for t in weights_sr.index],
            orientation="h",
            marker_color=[COLORS["accent"] if w > 0 else COLORS["negative"]
                          for w in weights_sr.values],
            text=[f"{w:.1f}%" for w in weights_sr.values * 100],
            textposition="outside",
        ))
        fig_bar.update_layout(
            template="plotly_dark",
            paper_bgcolor=COLORS["bg"],
            plot_bgcolor=COLORS["bg"],
            title="Poids optimaux — Max Sharpe",
            xaxis_title="Poids (%)",
            height=max(300, len(weights_sr) * 40 + 100),
            margin=dict(l=150, r=40, t=40, b=40),
        )
        st.plotly_chart(fig_bar, use_container_width=True)
