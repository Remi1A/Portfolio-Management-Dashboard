# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CY Tech AM** — Professional portfolio management dashboard for Master 2 GIF (CY Tech).

Multi-asset portfolio tracker (equities, ETFs, bonds, forex, commodities) with:
- Transaction-based NAV reconstruction with multi-currency conversion to EUR
- Benchmarking vs S&P 500, CAC 40, MSCI World, Euro Stoxx 50
- Markowitz optimization and Monte Carlo simulation
- Automated monthly PDF reporting (ReportLab)
- 7 fully functional Streamlit pages

Full specification: `CYU_AM_CAHIER_DES_CHARGES.md`

## Tech Stack

- **Framework**: Streamlit (dark mode, `streamlit-option-menu` for sidebar navigation)
- **Data**: yfinance (no API key), SQLite (single-file DB at `cyu_am/data/cyu_am.db`)
- **Visualization**: Plotly (`plotly_dark` theme)
- **PDF**: ReportLab (5-page dark mode report)
- **Optimization**: scipy.optimize (Markowitz)
- **Core libs**: pandas, numpy, scipy

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the dashboard
python -m streamlit run cyu_am/app.py

# Run tests (tests/ exists but tests not yet written)
python -m pytest cyu_am/tests/
python -m pytest cyu_am/tests/test_metrics.py -v          # single test file
python -m pytest cyu_am/tests/test_metrics.py::test_sharpe # single test
```

## Architecture

All code lives under `cyu_am/`. Entry point: `app.py`.

```
cyu_am/
  app.py                         # Streamlit entry point — routes to pages via option_menu
  config/
    settings.py                  # DB_PATH, COLORS, RISK_FREE_RATE, ROLLING_WINDOWS
    tickers.py                   # UNIVERSE dict (20 assets), FX_PAIRS, helpers
    benchmarks.py                # BENCHMARKS dict (4 indices), helpers
  data/
    database.py                  # SQLite schema (6 tables), get_connection(), CRUD helpers
    market_data.py               # fetch_prices() — yfinance + SQLite cache, delta-fetch only
    fx_data.py                   # fetch_fx_rate() — daily FX rates, inverse EURUSD for USD->EUR
    portfolio_engine.py          # reconstruct_nav(), get_current_positions(), get_nav_with_benchmark()
  metrics/
    performance.py               # total_return, cagr, ytd, mtd, monthly_returns_table, periods_summary
    risk.py                      # 17 metrics + risk_summary() — all pure functions
    rolling.py                   # rolling_volatility/sharpe/beta/mdd/correlation, all_rolling_metrics()
    optimization.py              # min_variance, max_sharpe, efficient_frontier, monte_carlo_simulation
  pages/
    1_overview.py                # 8 KPI cards, NAV vs benchmark, allocation pies, perf bar chart
    2_performance.py             # Period table, cumulative, heatmap, distribution, underwater, rolling
    3_risk.py                    # Risk metrics table, correlation matrix, VaR, stress tests
    4_positions.py               # Positions table with P&L, candlestick chart, asset info
    5_transactions.py            # Create portfolio, add transaction, CSV import, history with filters
    6_optimization.py            # Efficient frontier + Monte Carlo scatter, allocation comparison
    7_reporting.py               # Period selector, PDF generation, download, save to disk
  reporting/
    pdf_generator.py             # generate_monthly_report() -> bytes, save_report() -> file
    charts_export.py             # fig_to_image_bytes() / fig_to_temp_file() (needs kaleido)
    sections/
      cover.py                   # Page de garde
      executive_summary.py       # KPIs + risk metrics + benchmark comparison table
      performance_section.py     # Monthly returns heatmap (colored cells)
      risk_section.py            # 17 metrics in 2-column table
      positions_section.py       # Positions table + transactions table
  ui/
    components.py                # kpi_card(), section_header(), portfolio_selector(), load_css()
    charts.py                    # 10 Plotly functions: nav, pie, heatmap, underwater, distribution, etc.
    style.css                    # Dark mode CSS (KPI cards, badges, overrides)
  utils/
    formatters.py                # fmt_eur(), fmt_pct(), fmt_ratio(), fmt_number(), fmt_days()
  tests/                         # Test directory (empty, to be written)
  exports/                       # Generated PDF reports
  data/cyu_am.db                 # SQLite database (auto-created on first run)
```

### Data Flow

```
yfinance -----> market_data.py + fx_data.py -----> SQLite cache (market_prices, fx_rates)
                                                        |
transactions (SQLite) -----> portfolio_engine.py -----> NAV quotidienne EUR
                                                        |
                              metrics/ (performance, risk, rolling, optimization)
                                                        |
                              ui/charts.py -----> pages/*.py -----> app.py (Streamlit)
                                                        |
                              reporting/pdf_generator.py -----> PDF 5 pages
```

### Key Design Decisions

- **NAV reconstruction** (`portfolio_engine.py`) is the core algorithm: iterate daily over business days, apply transactions, multiply positions by local prices, convert to EUR using daily FX rates, sum to portfolio NAV + cash
- **All portfolio values normalized to EUR** — FX conversion happens at the portfolio engine level, not in UI
- **Metrics are pure functions**: input Series/DataFrame, output scalar — easy to test independently
- **SQLite cache**: market_data and fx_data only fetch missing dates from yfinance, everything else comes from cache
- **Multi-portfolio support**: each portfolio has independent transactions, NAV history, and metrics
- **No benchmark.py module**: benchmark metrics (Beta, Alpha, Tracking Error, etc.) are in `risk.py` alongside other risk metrics via `risk_summary()`
- **Page routing**: `app.py` uses lazy imports (`from cyu_am.pages.X import render`) inside if/elif blocks — pages with numeric prefixes can't be imported via normal `from` syntax but work via this pattern

### Important Implementation Details

**FX conversion logic** (`fx_data.py`):
- EURUSD=X gives "price of 1 EUR in USD", so for USD->EUR we invert: `1 / EURUSD`
- Forward-fill handles weekends/holidays

**Portfolio engine positions** (`portfolio_engine.py`):
- `Position` dataclass tracks quantity, VWAP (`avg_cost_local`), and total cost
- `apply_buy()` updates VWAP, `apply_sell()` returns realized P&L in local currency
- Cash is tracked in EUR: buys deduct `qty * price * fx_rate`, sells add proceeds

**Optimization** (`optimization.py`):
- Uses `scipy.optimize.minimize` with SLSQP method
- Constraint: weights sum to 1. Bounds: [0,1] (long only) or [-1,1] (short allowed)
- `monte_carlo_simulation` uses `np.random.dirichlet` for random weight generation

## Design System

Dark mode professional theme (defined in `config/settings.py` COLORS dict and `ui/style.css`):
- Background: `#0E1117` / Panels: `#1E2130`
- Primary accent: `#00D4AA` (green) / Secondary: `#4A9EFF` (blue)
- Positive: `#26A69A` / Negative: `#EF5350`
- Text: `#FAFAFA` / Secondary text: `#8892A4`

## Asset Universe

20 assets in `config/tickers.py` UNIVERSE dict:
- 12 equities across 5 sectors (Tech: AAPL/MSFT/ASML.AS/NVDA, Healthcare: SAN.PA/NVO, Finance: BNP.PA/GS, Consumer: MC.PA/OR.PA/AMZN, Energy: TTE.PA)
- 4 ETFs (CW8.PA, SPY, IWDA.AS, LQD)
- 2 commodity futures (GC=F, CL=F)
- 2 forex pairs (EURUSD=X, EURGBP=X)

Users can also add custom tickers via the Transactions page.

## Known Issues

- `MC.PA` (LVMH) intermittently returns "possibly delisted" from yfinance — cached data still works, but fresh fetches may fail
- `FutureWarning` on `pd.concat` with empty entries in `market_data.py` — cosmetic, no impact
- PDF reports don't include Plotly charts as images unless `kaleido` is installed (`pip install kaleido`)
- `streamlit` command not on PATH on some Windows installs — use `python -m streamlit run` instead

## What Still Needs to Be Built

- **Tests**: `tests/` directory is empty — priority is testing `metrics/` (pure functions) and `portfolio_engine.py`
- **Plotly charts in PDF**: install kaleido, wire `fig_to_temp_file()` into `pdf_generator.py` sections
- **Validators**: `utils/validators.py` not yet created — validate tickers via yfinance, dates, CSV import format
- **Cache with TTL**: `utils/cache.py` not yet created — currently cache never expires
