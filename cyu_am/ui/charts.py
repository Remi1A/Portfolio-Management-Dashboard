"""Fonctions Plotly pour tous les graphiques du dashboard."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from cyu_am.config.settings import COLORS

_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor=COLORS["bg"],
    plot_bgcolor=COLORS["bg"],
    font=dict(color=COLORS["text"], size=12),
    margin=dict(l=40, r=20, t=40, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)


def _base_layout(**overrides):
    layout = {**_LAYOUT, **overrides}
    return layout


# ── NAV ──

def nav_chart(nav_portfolio: pd.Series, nav_benchmark: pd.Series = None,
              benchmark_name: str = "Benchmark") -> go.Figure:
    """Courbe NAV base 100, portefeuille vs benchmark."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=nav_portfolio.index, y=nav_portfolio.values,
        name="Portefeuille", line=dict(color=COLORS["accent"], width=2.5),
    ))
    if nav_benchmark is not None:
        fig.add_trace(go.Scatter(
            x=nav_benchmark.index, y=nav_benchmark.values,
            name=benchmark_name, line=dict(color=COLORS["accent2"], width=2, dash="dot"),
        ))
    fig.update_layout(**_base_layout(
        title="Valeur Liquidative (base 100)",
        xaxis_title="", yaxis_title="NAV",
        hovermode="x unified",
    ))
    return fig


# ── Allocation ──

def allocation_pie(labels: list, values: list, title: str = "Allocation") -> go.Figure:
    """Pie chart d'allocation."""
    colors = [COLORS["accent"], COLORS["accent2"], "#FF9F43", "#A855F7",
              "#EC4899", "#F59E0B", "#10B981", "#6366F1"]
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.45,
        marker=dict(colors=colors[:len(labels)]),
        textinfo="label+percent",
        textfont=dict(size=12),
    ))
    fig.update_layout(**_base_layout(title=title, showlegend=False))
    return fig


# ── Heatmap rendements mensuels ──

def monthly_heatmap(table: pd.DataFrame) -> go.Figure:
    """Heatmap des rendements mensuels (annees x mois)."""
    fig = go.Figure(go.Heatmap(
        z=table.values,
        x=table.columns.tolist(),
        y=[str(y) for y in table.index],
        colorscale=[
            [0, COLORS["negative"]],
            [0.5, COLORS["bg"]],
            [1, COLORS["positive"]],
        ],
        zmid=0,
        text=[[f"{v:.1f}%" if pd.notna(v) else "" for v in row] for row in table.values],
        texttemplate="%{text}",
        textfont=dict(size=11),
        hovertemplate="Mois: %{x}<br>Annee: %{y}<br>Rendement: %{z:.2f}%<extra></extra>",
    ))
    fig.update_layout(**_base_layout(
        title="Rendements mensuels (%)",
        xaxis=dict(side="top"),
        yaxis=dict(autorange="reversed"),
        height=max(200, len(table) * 50 + 100),
    ))
    return fig


# ── Drawdown / Underwater ──

def underwater_chart(nav: pd.Series) -> go.Figure:
    """Graphique underwater (drawdowns)."""
    from cyu_am.metrics.risk import drawdown_series
    dd = drawdown_series(nav) * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dd.index, y=dd.values,
        fill="tozeroy",
        line=dict(color=COLORS["negative"], width=1),
        fillcolor="rgba(239,83,80,0.3)",
        name="Drawdown",
    ))
    fig.update_layout(**_base_layout(
        title="Underwater Chart (Drawdowns)",
        yaxis_title="Drawdown (%)",
        hovermode="x unified",
    ))
    return fig


# ── Distribution des rendements ──

def returns_distribution(returns: pd.Series) -> go.Figure:
    """Histogramme des rendements + courbe normale."""
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=returns.values * 100,
        nbinsx=50,
        name="Rendements",
        marker_color=COLORS["accent"],
        opacity=0.7,
    ))
    # Courbe normale
    x_range = np.linspace(returns.min() * 100, returns.max() * 100, 100)
    from scipy.stats import norm
    mu, sigma = returns.mean() * 100, returns.std() * 100
    normal_curve = norm.pdf(x_range, mu, sigma) * len(returns) * (returns.max() - returns.min()) * 100 / 50
    fig.add_trace(go.Scatter(
        x=x_range, y=normal_curve,
        name="Normale", line=dict(color=COLORS["accent2"], width=2, dash="dash"),
    ))
    fig.update_layout(**_base_layout(
        title="Distribution des rendements quotidiens",
        xaxis_title="Rendement (%)", yaxis_title="Frequence",
    ))
    return fig


# ── Rendements cumulés ──

def cumulative_returns_chart(cum_port: pd.Series, cum_bench: pd.Series = None,
                             benchmark_name: str = "Benchmark") -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cum_port.index, y=cum_port.values * 100,
        name="Portefeuille", line=dict(color=COLORS["accent"], width=2.5),
    ))
    if cum_bench is not None:
        fig.add_trace(go.Scatter(
            x=cum_bench.index, y=cum_bench.values * 100,
            name=benchmark_name, line=dict(color=COLORS["accent2"], width=2, dash="dot"),
        ))
    fig.update_layout(**_base_layout(
        title="Rendements cumules (%)",
        yaxis_title="%", hovermode="x unified",
    ))
    return fig


# ── Rolling metrics ──

def rolling_chart(df: pd.DataFrame, title: str, yaxis_title: str = "") -> go.Figure:
    """Graphique de métriques rolling (une courbe par fenêtre)."""
    colors = [COLORS["accent"], COLORS["accent2"], "#FF9F43"]
    fig = go.Figure()
    for i, col in enumerate(df.columns):
        fig.add_trace(go.Scatter(
            x=df.index, y=df[col].values,
            name=col, line=dict(color=colors[i % len(colors)], width=1.5),
        ))
    fig.update_layout(**_base_layout(title=title, yaxis_title=yaxis_title, hovermode="x unified"))
    return fig


# ── Corrélation ──

def correlation_matrix(corr: pd.DataFrame) -> go.Figure:
    """Heatmap de corrélation entre actifs."""
    fig = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns.tolist(),
        y=corr.index.tolist(),
        colorscale="RdBu_r",
        zmid=0, zmin=-1, zmax=1,
        text=[[f"{v:.2f}" for v in row] for row in corr.values],
        texttemplate="%{text}",
        textfont=dict(size=10),
    ))
    fig.update_layout(**_base_layout(
        title="Matrice de correlation",
        height=max(400, len(corr) * 40 + 100),
        xaxis=dict(side="bottom"),
    ))
    return fig


# ── Bar chart performance par actif ──

def performance_bar(tickers: list, values: list, title: str = "Performance par actif (%)") -> go.Figure:
    colors = [COLORS["positive"] if v >= 0 else COLORS["negative"] for v in values]
    fig = go.Figure(go.Bar(
        x=values, y=tickers, orientation="h",
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in values],
        textposition="outside",
    ))
    fig.update_layout(**_base_layout(title=title, xaxis_title="%", height=max(300, len(tickers) * 35 + 100)))
    return fig
