"""Page Positions — detail des positions avec valorisation."""

import streamlit as st
import pandas as pd

from cyu_am.config.tickers import UNIVERSE
from cyu_am.data.database import get_portfolios
from cyu_am.data.cached import get_current_positions, reconstruct_nav
from cyu_am.data.market_data import fetch_prices
from cyu_am.ui.components import (
    portfolio_selector, section_header, empty_state, load_css, asset_class_badge,
)
from cyu_am.utils.formatters import fmt_eur, fmt_pct, fmt_number
import plotly.graph_objects as go
from cyu_am.config.settings import COLORS


def render():
    load_css()
    st.title("Positions")

    portfolios = get_portfolios()
    pid = portfolio_selector(portfolios)
    if pid is None:
        empty_state("Creez un portefeuille dans l'onglet Transactions.")
        return

    with st.spinner("Chargement des positions..."):
        positions = get_current_positions(pid)
        nav_df = reconstruct_nav(pid)

    if positions.empty:
        empty_state("Aucune position ouverte.")
        return

    # ── Résumé ──
    total_value = positions["market_value_eur"].sum()
    total_pnl = positions["pnl_eur"].sum()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Valeur investie", fmt_eur(total_value))
    with col2:
        st.metric("P&L latent total", fmt_eur(total_pnl, 2),
                  delta=fmt_pct(total_pnl / (total_value - total_pnl) if total_value != total_pnl else 0))
    with col3:
        st.metric("Nombre de positions", str(len(positions)))

    # ── Tableau des positions ──
    section_header("Detail des positions")

    display = positions.copy()
    display["Nom"] = display["ticker"].map(
        lambda t: UNIVERSE.get(t, {}).get("name", t)
    )
    display = display.rename(columns={
        "ticker": "Ticker",
        "asset_class": "Classe",
        "currency": "Devise",
        "quantity": "Quantite",
        "avg_cost": "Prix moyen",
        "current_price": "Prix actuel",
        "market_value_eur": "Valeur (EUR)",
        "pnl_eur": "P&L (EUR)",
        "pnl_pct": "P&L (%)",
        "weight": "Poids (%)",
    })

    cols_display = ["Ticker", "Nom", "Classe", "Quantite", "Prix moyen",
                    "Prix actuel", "Devise", "Valeur (EUR)", "P&L (EUR)",
                    "P&L (%)", "Poids (%)"]
    cols_display = [c for c in cols_display if c in display.columns]

    st.dataframe(
        display[cols_display].style.format({
            "Quantite": "{:.2f}",
            "Prix moyen": "{:.2f}",
            "Prix actuel": "{:.2f}",
            "Valeur (EUR)": "{:,.0f}",
            "P&L (EUR)": "{:+,.0f}",
            "P&L (%)": "{:+.1f}%",
            "Poids (%)": "{:.1f}%",
        }).map(
            lambda v: "color: #26A69A" if isinstance(v, (int, float)) and v > 0
            else ("color: #EF5350" if isinstance(v, (int, float)) and v < 0 else ""),
            subset=["P&L (EUR)", "P&L (%)"],
        ),
        use_container_width=True,
        hide_index=True,
    )

    # ── Detail d'un actif (candlestick) ──
    section_header("Graphique d'un actif")
    ticker_select = st.selectbox("Selectionner un actif", positions["ticker"].tolist())

    period = st.select_slider("Periode", ["1M", "3M", "6M", "1A", "2A"],
                              value="6M", key="candle_period")
    period_days = {"1M": 30, "3M": 90, "6M": 180, "1A": 365, "2A": 730}
    start_date = (pd.Timestamp.now() - pd.Timedelta(days=period_days[period])).strftime("%Y-%m-%d")

    prices = fetch_prices(ticker_select, start=start_date)
    if not prices.empty:
        fig = go.Figure(go.Candlestick(
            x=prices.index,
            open=prices["open"],
            high=prices["high"],
            low=prices["low"],
            close=prices["close"],
            increasing_line_color=COLORS["positive"],
            decreasing_line_color=COLORS["negative"],
        ))
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=COLORS["bg"],
            plot_bgcolor=COLORS["bg"],
            title=f"{ticker_select} — Chandelier",
            xaxis_rangeslider_visible=False,
            height=450,
            margin=dict(l=40, r=20, t=40, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Fiche de l'actif
    info = UNIVERSE.get(ticker_select, {})
    if info:
        st.markdown(f"""
        | | |
        |---|---|
        | **Nom** | {info.get('name', ticker_select)} |
        | **Classe** | {info.get('asset_class', 'N/A')} |
        | **Secteur** | {info.get('sector', 'N/A')} |
        | **Devise** | {info.get('currency', 'N/A')} |
        """)
