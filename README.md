# CYU AM — Portfolio Management Dashboard

Professional multi-asset portfolio tracking and analysis dashboard, developed as part of the Master 2 GIF programme at CY Tech.

---

## What Was Built

### Infrastructure & Data

- **SQLite database** with 6 tables: `portfolios`, `transactions`, `market_prices`, `fx_rates`, `assets_info`, `nav_history`. Schema includes foreign keys, indexes, and a built-in cache.
- **yfinance wrapper** with automatic SQLite cache: already-downloaded prices are stored locally, and only missing dates are fetched. Coverage: equities, ETFs, futures, forex.
- **FX module**: retrieval of daily exchange rates (EURUSD, EURGBP, EURCHF) via yfinance, automatic inversion for EUR conversion, forward-fill on non-trading days.
- **Universe of 20 pre-configured assets**: 12 equities (4 sectors), 4 ETFs, 2 commodities, 2 forex pairs. Extensible via custom Yahoo ticker.

### Portfolio Engine (Core System)

Day-by-day NAV reconstruction algorithm:

1. Loads portfolio transactions
2. For each business day, applies buys/sells
3. Values each position: `quantity x local_price x FX_rate`
4. Sums all positions + cash = **daily NAV in EUR**

Full multi-currency support: a portfolio can mix EUR, USD, GBP assets and commodities — everything is automatically converted to EUR. VWAP (volume-weighted average price) and realised/unrealised P&L computed per position.

### Financial Metrics (28 Indicators)

**Performance**: total return, CAGR, YTD, MTD, monthly returns (heatmap-ready), cumulative returns, period returns (1M, 3M, 6M, 1Y).

**Risk**: annualised volatility, Sharpe, Sortino, Omega, Calmar, Max Drawdown (value + duration), VaR 95% (historical and parametric), CVaR/Expected Shortfall, skewness, kurtosis.

**Benchmark**: Beta, Jensen's Alpha, Tracking Error, Information Ratio, correlation, Up/Down Capture Ratio.

**Rolling**: all the above metrics on 30d, 90d, 252d rolling windows.

### Portfolio Optimisation

- **Minimum variance portfolio** (scipy.optimize)
- **Max Sharpe portfolio** (tangent portfolio)
- **Efficient frontier**: 50 points computed via sequential optimisation under target-return constraints
- **Monte Carlo simulation**: up to 10,000 random portfolios
- Comparison of current allocation vs optimal allocations
- Short-selling option available

### PDF Reporting

Automatic generation of a 5-page PDF report (ReportLab):

| Page | Content |
|------|---------|
| 1 | Cover page (name, benchmark, period) |
| 2 | Executive summary: KPIs + risk metrics + benchmark comparison by period |
| 3 | Monthly returns: colour-coded heatmap (green/red) |
| 4 | Risk analysis: full 17-metric table in 2 columns |
| 5 | Composition: current positions with P&L + transaction history |

Professional dark background on every page, footer with portfolio name and page number. Export as bytes (Streamlit download) or file save.

### Streamlit Dashboard (7 Pages)

| Page | Description |
|------|-------------|
| **Overview** | 8 KPI cards, NAV base-100 curve vs benchmark, allocation by class/asset (pie charts), per-asset performance bar chart |
| **Performance** | Period comparison table vs benchmark, cumulative returns, monthly heatmap, return distribution + normal curve, underwater chart, rolling volatility/Sharpe |
| **Risk** | Table of 17+ metrics, asset correlation matrix, VaR in EUR, stress tests (-5% to -30%) |
| **Positions** | Detailed table with coloured P&L, interactive candlestick chart, asset info card |
| **Transactions** | Portfolio creation, transaction entry (universe or custom), CSV import with template, filterable history + export |
| **Optimisation** | Efficient frontier + Monte Carlo scatter coloured by Sharpe, Min Variance / Max Sharpe / Current points, allocation table, optimal weights bar chart |
| **Reporting** | Period selection (monthly/quarterly/custom), preview, PDF generation, download, save to disk |

Professional dark mode: background `#0E1117`, green accents `#00D4AA` and blue `#4A9EFF`, positive `#26A69A`, negative `#EF5350`.

---

## Getting Started

### Prerequisites

Python 3.10+ and pip.

### Installation

```bash
cd "Projet dashboard portfolio"
pip install -r requirements.txt
```

### Launch

```bash
python -m streamlit run cyu_am/app.py
```

The dashboard opens at `http://localhost:8501`.

### First Use

1. Go to **Transactions** > "Create a portfolio" tab
2. Enter name, initial capital (e.g. 100,000 EUR), creation date
3. "Add a transaction" tab: select an asset from the CYU AM universe or enter a custom Yahoo ticker
4. Go back to **Overview** to see the NAV, KPIs and allocation
5. Go to **Reporting** to generate a PDF

You can also import a CSV transaction file (downloadable template available in the interface).

---

## Code Architecture

```
cyu_am/
  app.py                   Streamlit entry point
  config/
    settings.py            Parameters (DB path, colours, risk-free rate)
    tickers.py             Universe of 20 assets + helpers
    benchmarks.py          4 benchmarks (S&P 500, CAC 40, MSCI World, Euro Stoxx 50)
  data/
    database.py            SQLite: schema, connection, CRUD
    market_data.py         yfinance + SQLite cache
    fx_data.py             Daily exchange rates
    portfolio_engine.py    Multi-asset/multi-currency NAV reconstruction
  metrics/
    performance.py         Returns, CAGR, YTD, MTD, heatmap
    risk.py                28 risk metrics + risk_summary()
    rolling.py             Metrics on rolling windows
    optimization.py        Markowitz, Monte Carlo, efficient frontier
  pages/
    1_overview.py          Overview page
    2_performance.py       Performance analysis page
    3_risk.py              Risk analysis page
    4_positions.py         Positions detail page
    5_transactions.py      Transaction management page
    6_optimization.py      Markowitz optimisation page
    7_reporting.py         PDF generation page
  reporting/
    pdf_generator.py       PDF orchestrator
    charts_export.py       Plotly to PNG (requires kaleido)
    sections/              5 PDF report sections
  ui/
    components.py          KPI cards, badges, selectors
    charts.py              10 Plotly functions
    style.css              Dark mode CSS
  utils/
    formatters.py          EUR, %, ratio formatting
```

### Data Flow

```
yfinance -----> market_data.py + fx_data.py -----> SQLite (cache)
                                                        |
transactions (SQLite) -----> portfolio_engine.py -----> daily NAV in EUR
                                                        |
                        metrics/ (performance, risk, benchmark, rolling)
                                                        |
                        ui/charts.py -----> pages/*.py -----> app.py
                                                        |
                        reporting/pdf_generator.py -----> PDF
```

### Design Principles

- **Metrics = pure functions**: input DataFrame/Series, output scalar. Easy to test independently.
- **SQLite cache**: prices and FX rates are stored locally; only new dates are fetched.
- **No API key required**: everything is free (yfinance).
- **Multi-portfolio**: each portfolio is independent with its own transactions and metrics.
- **Centralised FX conversion**: multi-currency conversion happens in the portfolio engine, not in the UI.

---

## Dependencies

| Package | Role |
|---------|------|
| `streamlit` | Dashboard framework |
| `streamlit-option-menu` | Sidebar navigation with icons |
| `yfinance` | Market data (OHLCV, fundamentals) |
| `plotly` | Interactive charts (dark mode) |
| `pandas` / `numpy` | Data manipulation |
| `scipy` | Optimisation (Markowitz) + normal distribution (VaR) |
| `reportlab` | PDF generation |
| `openpyxl` | Excel read/write |

---

## Roadmap

### High Priority

- **Unit tests**: write tests for `metrics/performance.py`, `metrics/risk.py` and `portfolio_engine.py`. Metrics are pure functions, making them very easy to test with synthetic series.
- **Charts in PDF**: install `kaleido` (`pip install kaleido`) to export Plotly charts as PNG and embed them in the report. The code is already wired (`charts_export.py`) — just call `fig_to_temp_file()` and pass the path to the sections.
- **yfinance error handling**: some tickers (e.g. `MC.PA`) may intermittently return "possibly delisted". Add a retry with cache fallback.

### Medium Priority

- **Dividends and splits**: yfinance with `auto_adjust=True` adjusts historical prices, but the displayed P&L does not distinguish capital gain from dividend yield. Add separate dividend tracking.
- **Performance attribution**: decompose total return by asset and asset class (Brinson attribution).
- **Management commentary**: add a free-text field in the Reporting page so the manager can write a comment to be included in the PDF.
- **3D efficient frontier**: add a 3D view (return x volatility x Sharpe) using Plotly Surface or Scatter3d.
- **Alerts**: notifications when an asset exceeds a drawdown threshold or when the portfolio drifts too far from the target allocation.

### Low Priority

- **PostgreSQL migration**: if the project evolves toward multi-user, migrate from SQLite to PostgreSQL (schema is compatible).
- **Streamlit Cloud deployment**: host the dashboard online for remote access.
- **DuckDB**: replace SQLite with DuckDB for more performant analytical queries on large OHLCV volumes.
- **Integrated backtest**: allow simulation of trading strategies (momentum, mean-reversion) directly from the dashboard using historical data.
- **REST API**: expose metrics via a FastAPI endpoint for integration with other tools.

---

*Master 2 GIF Project — CY Tech / CYU Asset Management*
