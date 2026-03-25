"""Orchestrateur de generation de rapports PDF mensuels."""

import io
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, PageBreak, Spacer

from cyu_am.config.settings import EXPORTS_DIR
from cyu_am.config.benchmarks import get_benchmark_ticker, DEFAULT_BENCHMARK
from cyu_am.data.database import get_portfolios, get_transactions
from cyu_am.data.portfolio_engine import reconstruct_nav, get_current_positions
from cyu_am.data.market_data import fetch_prices
from cyu_am.metrics.performance import (
    total_return, cagr, ytd_return, mtd_return, daily_returns,
    monthly_returns_table, periods_summary,
)
from cyu_am.metrics.risk import risk_summary

from cyu_am.config.tickers import UNIVERSE, get_sector, get_country, get_region
from cyu_am.reporting.sections.cover import build_cover
from cyu_am.reporting.sections.executive_summary import build_executive_summary
from cyu_am.reporting.sections.performance_section import build_performance_section
from cyu_am.reporting.sections.risk_section import build_risk_section
from cyu_am.reporting.sections.concentration_section import build_concentration_section
from cyu_am.reporting.sections.positions_section import build_positions_section
from cyu_am.reporting.charts_export import fig_to_temp_file
from cyu_am.ui.charts import (
    nav_chart, underwater_chart, cumulative_returns_chart, allocation_pie,
)

DARK_BG = HexColor("#0E1117")
TEXT_GRAY = HexColor("#8892A4")


def generate_monthly_report(portfolio_id: int,
                            benchmark_name: str = None,
                            start_date: str = None,
                            end_date: str = None) -> bytes:
    """
    Genere le rapport PDF mensuel complet.

    Returns:
        bytes: contenu du fichier PDF.
    """
    if benchmark_name is None:
        benchmark_name = DEFAULT_BENCHMARK
    benchmark_ticker = get_benchmark_ticker(benchmark_name)

    # Charger les données
    portfolio = _get_portfolio_info(portfolio_id)
    nav_df = reconstruct_nav(portfolio_id, start=start_date, end=end_date)

    if nav_df.empty:
        raise ValueError("Aucune donnee NAV pour ce portefeuille.")

    nav = nav_df["nav"]
    rets = nav_df["daily_return"].dropna()

    # Benchmark
    bench_prices = fetch_prices(benchmark_ticker,
                                start=nav.index[0].strftime("%Y-%m-%d"),
                                end=nav.index[-1].strftime("%Y-%m-%d"))
    bench_rets = None
    if not bench_prices.empty:
        bench_rets = bench_prices["close"].pct_change().dropna()
        common = rets.index.intersection(bench_rets.index)
        bench_rets = bench_rets.reindex(common)
        rets_for_metrics = rets.reindex(common)
    else:
        rets_for_metrics = rets

    # Métriques
    perf_data = {
        "nav_final": nav.iloc[-1],
        "total_return": total_return(nav),
        "cagr": cagr(nav),
        "ytd": ytd_return(nav),
        "mtd": mtd_return(nav),
    }

    risk_data = risk_summary(rets, nav, bench_rets)

    # Benchmark comparison
    bench_comparison = None
    if not bench_prices.empty:
        port_periods = periods_summary(nav)
        bench_nav = bench_prices["close"]
        bench_periods = periods_summary(bench_nav)
        bench_comparison = {}
        for period in ["1M", "3M", "6M", "1Y", "YTD"]:
            bench_comparison[period] = {
                "portfolio": port_periods.get(period, 0),
                "benchmark": bench_periods.get(period, 0),
            }

    # Positions et transactions
    positions = get_current_positions(portfolio_id)
    txns_raw = get_transactions(portfolio_id)
    txns_df = pd.DataFrame(txns_raw) if txns_raw else pd.DataFrame()

    # Rendements mensuels
    monthly_table = monthly_returns_table(nav)

    # Période
    period_label = f"{nav.index[0].strftime('%d/%m/%Y')} - {nav.index[-1].strftime('%d/%m/%Y')}"
    gen_date = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Concentration sectorielle/geographique
    sector_data, country_data, region_data = _compute_concentration(positions)

    # ── Génération des graphiques PNG ──
    chart_paths = _generate_charts(nav, bench_prices, benchmark_name, rets,
                                   bench_rets, positions, sector_data, country_data)

    # ── Construction du PDF ──
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )

    elements = []

    # Page 1 : Couverture
    elements.extend(build_cover(
        portfolio_name=portfolio["name"],
        benchmark_name=benchmark_name,
        period_label=period_label,
        generation_date=gen_date,
    ))
    elements.append(PageBreak())

    # Page 2 : Résumé exécutif
    elements.extend(build_executive_summary(
        performance=perf_data,
        risk={"volatility": risk_data["volatility"],
              "sharpe": risk_data["sharpe"],
              "sortino": risk_data["sortino"],
              "max_drawdown": risk_data["max_drawdown"],
              "var_95": risk_data["var_95_hist"]},
        benchmark_comparison=bench_comparison,
        nav_chart_path=chart_paths.get("nav"),
    ))
    elements.append(PageBreak())

    # Page 3 : Performance
    elements.extend(build_performance_section(
        monthly_table=monthly_table,
        nav_chart_path=chart_paths.get("cumulative"),
    ))
    elements.append(PageBreak())

    # Page 4 : Risques
    elements.extend(build_risk_section(
        risk_metrics=risk_data,
        underwater_chart_path=chart_paths.get("underwater"),
        distribution_chart_path=chart_paths.get("distribution"),
        nav_current=float(nav.iloc[-1]),
    ))
    elements.append(PageBreak())

    # Page 5 : Concentration sectorielle & geographique
    elements.extend(build_concentration_section(
        sector_data=sector_data,
        country_data=country_data,
        region_data=region_data,
        sector_chart_path=chart_paths.get("sector_pie"),
        country_chart_path=chart_paths.get("country_pie"),
    ))
    elements.append(PageBreak())

    # Page 6 : Positions + transactions
    elements.extend(build_positions_section(
        positions=positions,
        transactions=txns_df,
        allocation_chart_path=chart_paths.get("allocation"),
    ))

    # Footer sur chaque page
    def _on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(DARK_BG)
        canvas.rect(0, 0, A4[0], A4[1], fill=1)
        canvas.setFillColor(TEXT_GRAY)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(1.5 * cm, 0.8 * cm,
                          f"CY Tech AM - {portfolio['name']} - {gen_date}")
        canvas.drawRightString(A4[0] - 1.5 * cm, 0.8 * cm,
                               f"Page {doc.page}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=_on_page, onLaterPages=_on_page)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    # Nettoyage des fichiers temporaires
    for path in chart_paths.values():
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass

    return pdf_bytes


def save_report(pdf_bytes: bytes, portfolio_name: str,
                date_label: str = None) -> Path:
    """Sauvegarde le PDF dans le dossier exports."""
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if date_label is None:
        date_label = datetime.now().strftime("%Y%m")
    filename = f"rapport_{portfolio_name.replace(' ', '_')}_{date_label}.pdf"
    filepath = EXPORTS_DIR / filename
    filepath.write_bytes(pdf_bytes)
    return filepath


def _compute_concentration(positions: pd.DataFrame) -> tuple[dict | None, dict | None, dict | None]:
    """Compute sector, country, and region concentration data from positions."""
    if positions.empty or "market_value_eur" not in positions.columns:
        return None, None, None

    # Enrich positions with sector/country/region
    sectors, countries, regions = [], [], []
    for _, row in positions.iterrows():
        ticker = row["ticker"]
        if ticker in UNIVERSE:
            sectors.append(get_sector(ticker))
            countries.append(get_country(ticker))
            regions.append(get_region(ticker))
        else:
            sectors.append(row.get("asset_class", "Other"))
            countries.append("N/A")
            regions.append("N/A")

    enriched = positions.copy()
    enriched["sector"] = sectors
    enriched["country"] = countries
    enriched["region"] = regions

    # Exclude forex
    enriched = enriched[enriched["sector"] != "FX"]
    if enriched.empty:
        return None, None, None

    total = enriched["market_value_eur"].sum()
    if total <= 0:
        return None, None, None

    # Sector
    sector_grp = enriched.groupby("sector")["market_value_eur"]
    sector_vals = sector_grp.sum()
    sector_data = {
        "weights": (sector_vals / total * 100).to_dict(),
        "values": sector_vals.to_dict(),
        "counts": sector_grp.count().to_dict(),
    }

    # Country (exclude N/A)
    geo = enriched[enriched["country"] != "N/A"]
    country_data = None
    region_data = None
    if not geo.empty:
        geo_total = geo["market_value_eur"].sum()
        country_grp = geo.groupby("country")["market_value_eur"]
        country_vals = country_grp.sum()
        country_data = {
            "weights": (country_vals / geo_total * 100).to_dict(),
            "values": country_vals.to_dict(),
            "counts": country_grp.count().to_dict(),
        }

        region_grp = geo.groupby("region")["market_value_eur"]
        region_vals = region_grp.sum()
        region_data = {
            "weights": (region_vals / geo_total * 100).to_dict(),
            "values": region_vals.to_dict(),
            "counts": region_grp.count().to_dict(),
        }

    return sector_data, country_data, region_data


def _generate_charts(nav: pd.Series, bench_prices: pd.DataFrame,
                     benchmark_name: str, rets: pd.Series,
                     bench_rets: pd.Series | None,
                     positions: pd.DataFrame,
                     sector_data: dict | None = None,
                     country_data: dict | None = None) -> dict[str, str | None]:
    """Genere les graphiques Plotly en fichiers PNG temporaires."""
    charts = {}

    # 1. NAV chart (portfolio vs benchmark)
    try:
        nav_base100 = nav / nav.iloc[0] * 100
        bench_base100 = None
        if not bench_prices.empty:
            bench_close = bench_prices["close"]
            common_start = nav.index[0]
            bench_close = bench_close.loc[common_start:]
            if not bench_close.empty:
                bench_base100 = bench_close / bench_close.iloc[0] * 100
        fig = nav_chart(nav_base100, bench_base100, benchmark_name)
        charts["nav"] = fig_to_temp_file(fig, width=750, height=380)
    except Exception:
        charts["nav"] = None

    # 2. Cumulative returns chart
    try:
        cum_port = (1 + rets).cumprod() - 1
        cum_bench = None
        if bench_rets is not None and not bench_rets.empty:
            common = rets.index.intersection(bench_rets.index)
            cum_bench = (1 + bench_rets.reindex(common)).cumprod() - 1
        fig = cumulative_returns_chart(cum_port, cum_bench, benchmark_name)
        charts["cumulative"] = fig_to_temp_file(fig, width=750, height=380)
    except Exception:
        charts["cumulative"] = None

    # 3. Underwater / drawdown chart
    try:
        fig = underwater_chart(nav)
        charts["underwater"] = fig_to_temp_file(fig, width=750, height=350)
    except Exception:
        charts["underwater"] = None

    # 4. Returns distribution
    try:
        from cyu_am.ui.charts import returns_distribution
        fig = returns_distribution(rets)
        charts["distribution"] = fig_to_temp_file(fig, width=750, height=350)
    except Exception:
        charts["distribution"] = None

    # 5. Allocation pie
    try:
        if not positions.empty and "weight" in positions.columns:
            labels = positions["ticker"].tolist()
            values = positions["weight"].tolist()
            if any(v > 0 for v in values):
                fig = allocation_pie(labels, values, title="Allocation du portefeuille")
                charts["allocation"] = fig_to_temp_file(fig, width=500, height=400)
            else:
                charts["allocation"] = None
        else:
            charts["allocation"] = None
    except Exception:
        charts["allocation"] = None

    # 6. Sector pie
    try:
        if sector_data and sector_data["weights"]:
            sorted_sectors = sorted(sector_data["weights"].items(), key=lambda x: x[1], reverse=True)
            fig = allocation_pie(
                [s[0] for s in sorted_sectors],
                [s[1] for s in sorted_sectors],
                title="Repartition sectorielle",
            )
            charts["sector_pie"] = fig_to_temp_file(fig, width=500, height=400)
        else:
            charts["sector_pie"] = None
    except Exception:
        charts["sector_pie"] = None

    # 7. Country pie
    try:
        if country_data and country_data["weights"]:
            sorted_countries = sorted(country_data["weights"].items(), key=lambda x: x[1], reverse=True)
            fig = allocation_pie(
                [c[0] for c in sorted_countries],
                [c[1] for c in sorted_countries],
                title="Repartition geographique",
            )
            charts["country_pie"] = fig_to_temp_file(fig, width=500, height=400)
        else:
            charts["country_pie"] = None
    except Exception:
        charts["country_pie"] = None

    return charts


def _get_portfolio_info(portfolio_id: int) -> dict:
    portfolios = get_portfolios()
    for p in portfolios:
        if p["id"] == portfolio_id:
            return p
    raise ValueError(f"Portfolio {portfolio_id} introuvable")
