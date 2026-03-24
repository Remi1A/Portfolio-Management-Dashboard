"""
Portfolio Engine — Reconstitution NAV multi-asset en EUR.

Algorithme central : à partir des transactions, reconstruit jour par jour
la valeur du portefeuille en convertissant chaque position dans la devise
de référence (EUR) via les taux de change quotidiens.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field

from cyu_am.config.settings import BASE_CURRENCY
from cyu_am.config.tickers import get_currency
from cyu_am.data.database import (
    get_transactions, get_portfolios, get_connection,
    upsert_market_prices,
)
from cyu_am.data.market_data import fetch_prices, fetch_multiple
from cyu_am.data.fx_data import fetch_fx_rate, fetch_all_fx


@dataclass
class Position:
    """Position ouverte sur un actif."""
    ticker: str
    quantity: float = 0.0
    avg_cost_local: float = 0.0   # VWAP en devise locale
    asset_currency: str = "EUR"
    asset_class: str = "EQUITY"
    total_cost_local: float = 0.0  # coût total accumulé (pour VWAP)

    def apply_buy(self, qty: float, price: float):
        self.total_cost_local += qty * price
        self.quantity += qty
        if self.quantity > 0:
            self.avg_cost_local = self.total_cost_local / self.quantity

    def apply_sell(self, qty: float, price: float) -> float:
        """Retourne le P&L réalisé en devise locale."""
        sell_qty = min(qty, self.quantity)
        pnl_local = sell_qty * (price - self.avg_cost_local)
        self.quantity -= sell_qty
        if self.quantity > 1e-10:
            self.total_cost_local = self.quantity * self.avg_cost_local
        else:
            self.quantity = 0.0
            self.total_cost_local = 0.0
            self.avg_cost_local = 0.0
        return pnl_local


@dataclass
class DailySnapshot:
    """Snapshot journalier du portefeuille."""
    date: pd.Timestamp
    nav: float                          # valeur totale en EUR
    cash: float                         # cash en EUR
    invested_value: float               # valeur des positions en EUR
    positions: dict = field(default_factory=dict)  # ticker -> {qty, value_eur, ...}


def reconstruct_nav(portfolio_id: int, start: str = None,
                    end: str = None) -> pd.DataFrame:
    """
    Reconstruit la NAV quotidienne d'un portefeuille.

    Returns:
        DataFrame indexé par date avec colonnes:
        [nav, cash, invested_value, daily_return]
    """
    # 1. Charger portefeuille et transactions
    portfolio = _get_portfolio(portfolio_id)
    txns = _load_transactions(portfolio_id)

    if txns.empty:
        return pd.DataFrame(columns=["nav", "cash", "invested_value", "daily_return"])

    initial_cash = portfolio["initial_cash"]

    # 2. Déterminer la plage de dates
    first_txn_date = txns["date"].min()
    date_start = pd.Timestamp(start) if start else first_txn_date
    date_end = pd.Timestamp(end) if end else pd.Timestamp.now()

    # 3. Identifier les tickers et devises nécessaires (exclure CASH)
    trade_txns = txns[txns["action"].isin(["BUY", "SELL"])]
    tickers = trade_txns["ticker"].unique().tolist() if not trade_txns.empty else []
    currencies_needed = list({
        trade_txns.loc[trade_txns["ticker"] == t, "asset_currency"].iloc[0]
        for t in tickers
    }) if tickers else []
    # Ajouter les devises des DEPOSIT/WITHDRAW pour le FX
    cash_txns = txns[txns["action"].isin(["DEPOSIT", "WITHDRAW"])]
    if not cash_txns.empty:
        for ccy in cash_txns["asset_currency"].unique():
            if ccy not in currencies_needed:
                currencies_needed.append(ccy)

    # 4. Pré-charger les données de marché et FX (depuis la 1ère transaction)
    fetch_start = min(first_txn_date, date_start)
    price_data = _prefetch_prices(tickers, fetch_start, date_end)
    fx_data = _prefetch_fx(currencies_needed, fetch_start, date_end)

    # 5. Construire le calendrier unifié (jours ouvrés + jours de transactions)
    bdays = pd.bdate_range(date_start, date_end)

    # 6. Grouper les transactions par date
    txns_by_date = {d: group for d, group in txns.groupby("date")}

    # Fusionner les jours ouvrés avec les dates de transactions non-ouvrées
    txn_dates_in_range = {d for d in txns_by_date if date_start <= d <= date_end}
    all_dates = sorted(set(bdays) | txn_dates_in_range)

    # 7. Rejouer les transactions antérieures à date_start
    #    pour établir l'état initial des positions et du cash
    positions: dict[str, Position] = {}
    cash_eur = initial_cash
    realized_pnl = 0.0

    prior_txns = txns[txns["date"] < date_start].sort_values("date")
    for _, tx in prior_txns.iterrows():
        cash_eur, realized_pnl = _apply_transaction(
            tx, positions, cash_eur, realized_pnl, fx_data, tx["date"]
        )

    records = []

    for day in all_dates:
        # Tracker les cashflows externes (DEPOSIT/WITHDRAW) du jour
        daily_cf = 0.0

        # Appliquer les transactions du jour
        if day in txns_by_date:
            for _, tx in txns_by_date[day].iterrows():
                if tx["action"] in ("DEPOSIT", "WITHDRAW"):
                    ccy = tx["asset_currency"]
                    fx_cf = _get_fx_on_date(fx_data, ccy, day)
                    if tx["action"] == "DEPOSIT":
                        daily_cf += tx["price"] * fx_cf
                    else:
                        daily_cf -= tx["price"] * fx_cf
                cash_eur, realized_pnl = _apply_transaction(
                    tx, positions, cash_eur, realized_pnl, fx_data, day
                )

        # Valoriser les positions
        invested_eur = 0.0
        for ticker, pos in positions.items():
            if pos.quantity <= 0:
                continue
            price = _get_price_on_date(price_data, ticker, day)
            if price is None:
                # Fallback : prix d'achat moyen si pas de donnée marché
                price = pos.avg_cost_local if pos.avg_cost_local > 0 else None
            if price is None:
                continue
            fx = _get_fx_on_date(fx_data, pos.asset_currency, day)
            value_eur = pos.quantity * price * fx
            invested_eur += value_eur

        nav = cash_eur + invested_eur
        records.append({
            "date": day,
            "nav": nav,
            "cash": cash_eur,
            "invested_value": invested_eur,
            "cashflow": daily_cf,
        })

    # 9. Construire le DataFrame résultat
    df = pd.DataFrame(records).set_index("date").sort_index()
    df = df[~df.index.duplicated(keep="last")]

    # TWR (Time-Weighted Return) : exclut l'impact des dépôts/retraits
    # r_t = NAV_t / (NAV_{t-1} + CF_t) - 1
    nav_prev = df["nav"].shift(1)
    denominator = nav_prev + df["cashflow"]
    df["daily_return"] = df["nav"] / denominator - 1
    df["daily_return"] = df["daily_return"].replace([np.inf, -np.inf], np.nan)

    return df


def get_current_cash(portfolio_id: int) -> float:
    """Retourne le cash actuel du portefeuille en EUR."""
    nav_df = reconstruct_nav(portfolio_id)
    if nav_df.empty:
        portfolio = _get_portfolio(portfolio_id)
        return portfolio["initial_cash"]
    return float(nav_df["cash"].iloc[-1])


def get_current_positions(portfolio_id: int) -> pd.DataFrame:
    """
    Retourne les positions actuelles avec valorisation.

    Colonnes: ticker, name, asset_class, quantity, avg_cost, current_price,
              market_value_eur, pnl_eur, pnl_pct, weight, currency
    """
    portfolio = _get_portfolio(portfolio_id)
    txns = _load_transactions(portfolio_id)

    if txns.empty:
        return pd.DataFrame()

    # Rejouer les transactions pour obtenir les positions
    positions: dict[str, Position] = {}
    for _, tx in txns.iterrows():
        _apply_transaction_simple(tx, positions)

    # Valoriser
    tickers = [t for t, p in positions.items() if p.quantity > 0]
    if not tickers:
        return pd.DataFrame()

    currencies = list({positions[t].asset_currency for t in tickers})
    fx_data = _prefetch_fx(currencies, "2025-01-01", None)
    today = pd.Timestamp.now()

    # Batch fetch all prices at once (avoid N+1 queries)
    all_prices = fetch_multiple(tickers, start="2025-01-01")

    rows = []
    total_value = 0.0

    for ticker in tickers:
        pos = positions[ticker]
        price_df = all_prices.get(ticker, pd.DataFrame())
        if price_df.empty:
            continue
        current_price = float(price_df["close"].iloc[-1])
        fx = _get_fx_on_date(fx_data, pos.asset_currency, today)

        market_value_eur = pos.quantity * current_price * fx
        cost_eur = pos.quantity * pos.avg_cost_local * fx
        pnl_eur = market_value_eur - cost_eur
        pnl_pct = (pnl_eur / cost_eur * 100) if cost_eur != 0 else 0.0

        total_value += market_value_eur
        rows.append({
            "ticker": ticker,
            "asset_class": pos.asset_class,
            "currency": pos.asset_currency,
            "quantity": pos.quantity,
            "avg_cost": pos.avg_cost_local,
            "current_price": current_price,
            "market_value_eur": market_value_eur,
            "pnl_eur": pnl_eur,
            "pnl_pct": pnl_pct,
        })

    df = pd.DataFrame(rows)
    if not df.empty and total_value > 0:
        df["weight"] = df["market_value_eur"] / total_value * 100
    else:
        df["weight"] = 0.0
    return df.sort_values("market_value_eur", ascending=False).reset_index(drop=True)


def get_nav_with_benchmark(portfolio_id: int, benchmark_ticker: str,
                           start: str = None, end: str = None,
                           base: float = 100.0) -> pd.DataFrame:
    """
    Retourne la NAV du portefeuille et du benchmark, normalisées base 100.

    Colonnes: nav_portfolio, nav_benchmark
    """
    from cyu_am.config.benchmarks import BENCHMARKS

    nav = reconstruct_nav(portfolio_id, start, end)
    if nav.empty:
        return pd.DataFrame()

    # Benchmark
    bench_info = None
    for _, v in BENCHMARKS.items():
        if v["ticker"] == benchmark_ticker:
            bench_info = v
            break

    bench_prices = fetch_prices(benchmark_ticker, start=nav.index[0].strftime("%Y-%m-%d"),
                                end=nav.index[-1].strftime("%Y-%m-%d"))
    if bench_prices.empty:
        return nav

    # Convertir benchmark en EUR si nécessaire
    bench_nav = bench_prices["close"].copy()
    if bench_info and bench_info["currency"] != BASE_CURRENCY:
        fx = fetch_fx_rate(bench_info["currency"],
                           start=nav.index[0].strftime("%Y-%m-%d"),
                           end=nav.index[-1].strftime("%Y-%m-%d"))
        fx_aligned = fx.reindex(bench_nav.index).ffill()
        bench_nav = bench_nav * fx_aligned

    # Aligner les index
    common_idx = nav.index.intersection(bench_nav.index)
    if common_idx.empty:
        return nav

    # Normaliser base 100
    result = pd.DataFrame(index=common_idx)
    portfolio_series = nav.loc[common_idx, "nav"]
    bench_series = bench_nav.loc[common_idx]

    result["nav_portfolio"] = portfolio_series / portfolio_series.iloc[0] * base
    result["nav_benchmark"] = bench_series / bench_series.iloc[0] * base

    return result


# ── Helpers internes ──

def _get_portfolio(portfolio_id: int) -> dict:
    portfolios = get_portfolios()
    for p in portfolios:
        if p["id"] == portfolio_id:
            return p
    raise ValueError(f"Portfolio {portfolio_id} introuvable")


def _load_transactions(portfolio_id: int) -> pd.DataFrame:
    txns = get_transactions(portfolio_id)
    if not txns:
        return pd.DataFrame()
    df = pd.DataFrame(txns)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def _prefetch_prices(tickers: list[str], start, end) -> dict[str, pd.DataFrame]:
    s = start if isinstance(start, str) else start.strftime("%Y-%m-%d")
    e = end if isinstance(end, str) else (end.strftime("%Y-%m-%d") if end else None)
    result = {}
    for t in tickers:
        result[t] = fetch_prices(t, start=s, end=e)
    return result


def _prefetch_fx(currencies, start, end) -> dict[str, pd.Series]:
    s = start if isinstance(start, str) else start.strftime("%Y-%m-%d")
    e = end if isinstance(end, str) else (end.strftime("%Y-%m-%d") if end else None)
    return fetch_all_fx(currencies, start=s, end=e)


def _get_price_on_date(price_data: dict, ticker: str, date: pd.Timestamp) -> float | None:
    """Récupère le prix de clôture. Forward-fill si pas de données ce jour."""
    df = price_data.get(ticker)
    if df is None or df.empty:
        return None
    # Chercher la date exacte ou la plus proche avant
    mask = df.index <= date
    if not mask.any():
        return None
    return float(df.loc[mask, "close"].iloc[-1])


def _get_fx_on_date(fx_data: dict, currency: str, date: pd.Timestamp) -> float:
    """Récupère le taux FX. Forward-fill si pas de données ce jour."""
    if currency == BASE_CURRENCY:
        return 1.0
    series = fx_data.get(currency)
    if series is None or series.empty:
        return 1.0
    mask = series.index <= date
    if not mask.any():
        return float(series.iloc[0])
    return float(series.loc[mask].iloc[-1])


def _apply_transaction(tx, positions: dict, cash_eur: float,
                       realized_pnl: float, fx_data: dict,
                       date: pd.Timestamp) -> tuple[float, float]:
    """Applique une transaction et met à jour cash + positions."""
    ticker = tx["ticker"]
    ccy = tx["asset_currency"]
    fx = _get_fx_on_date(fx_data, ccy, date)
    qty = tx["quantity"]
    price = tx["price"]
    fees = tx["fees"] if pd.notna(tx["fees"]) else 0.0

    if tx["action"] == "DEPOSIT":
        cash_eur += price * fx
        return cash_eur, realized_pnl
    elif tx["action"] == "WITHDRAW":
        cash_eur -= price * fx
        return cash_eur, realized_pnl

    if ticker not in positions:
        positions[ticker] = Position(
            ticker=ticker,
            asset_currency=ccy,
            asset_class=tx["asset_class"],
        )
    pos = positions[ticker]

    if tx["action"] == "BUY":
        pos.apply_buy(qty, price)
        cost_eur = qty * price * fx + fees * fx
        cash_eur -= cost_eur
    elif tx["action"] == "SELL":
        pnl_local = pos.apply_sell(qty, price)
        proceeds_eur = qty * price * fx - fees * fx
        cash_eur += proceeds_eur
        realized_pnl += pnl_local * fx

    return cash_eur, realized_pnl


def _apply_transaction_simple(tx, positions: dict):
    """Version simplifiée pour reconstituer les positions sans cash."""
    ticker = tx["ticker"]
    if ticker not in positions:
        positions[ticker] = Position(
            ticker=ticker,
            asset_currency=tx["asset_currency"],
            asset_class=tx["asset_class"],
        )
    pos = positions[ticker]
    if tx["action"] == "BUY":
        pos.apply_buy(tx["quantity"], tx["price"])
    elif tx["action"] == "SELL":
        pos.apply_sell(tx["quantity"], tx["price"])
