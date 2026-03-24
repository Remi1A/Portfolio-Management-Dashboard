"""Taux de change quotidiens via yfinance — conversion vers EUR."""

import pandas as pd
import yfinance as yf

from cyu_am.config.tickers import FX_PAIRS
from cyu_am.data.database import get_cached_fx, upsert_fx_rates


def fetch_fx_rate(currency: str, start: str = "2015-01-01",
                  end: str = None) -> pd.Series:
    """
    Retourne le taux de change quotidien pour convertir `currency` → EUR.

    Pour USD : récupère EURUSD=X (combien de USD pour 1 EUR),
    puis inverse pour obtenir combien d'EUR pour 1 USD.

    Returns:
        Series indexée par date, valeurs = taux (1 currency = X EUR).
    """
    if currency == "EUR":
        # Pas de conversion nécessaire
        idx = pd.date_range(start, end or pd.Timestamp.now(), freq="B")
        return pd.Series(1.0, index=idx, name="fx_rate")

    if end is None:
        end = pd.Timestamp.now().strftime("%Y-%m-%d")

    pair_ticker = FX_PAIRS.get(currency)
    if pair_ticker is None:
        raise ValueError(f"Paire FX non configurée pour {currency}. "
                         f"Ajouter dans config/tickers.py FX_PAIRS.")

    # 1. Cache — check both start and end coverage
    cached = _load_cache(currency, start, end)

    fetch_ranges = []
    if cached is not None and not cached.empty:
        first_cached = cached.index.min().strftime("%Y-%m-%d")
        last_cached = cached.index.max().strftime("%Y-%m-%d")
        if start < first_cached:
            fetch_ranges.append((start, first_cached))
        if last_cached < end:
            fetch_after = (cached.index.max() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            fetch_ranges.append((fetch_after, end))
    else:
        fetch_ranges.append((start, end))

    # Cache fully covers the range
    if not fetch_ranges:
        return cached.loc[start:end]

    # 2. Fetch missing ranges from yfinance
    all_new = []
    for fs, fe in fetch_ranges:
        rate = _download_fx(pair_ticker, fs, fe)
        if not rate.empty:
            # Le ticker EURUSD=X donne le prix de 1 EUR en USD
            # On veut 1 USD → EUR, donc on inverse
            to_eur = 1.0 / rate
            all_new.append(to_eur)
            # Save to cache
            rows = [(d.strftime("%Y-%m-%d"), float(v)) for d, v in to_eur.items() if pd.notna(v)]
            upsert_fx_rates(currency, "EUR", rows)

    if not all_new and (cached is None or cached.empty):
        raise RuntimeError(f"Impossible de récupérer le taux FX pour {currency}")

    # 3. Combine cache + new data
    parts = []
    if cached is not None and not cached.empty:
        parts.append(cached)
    parts.extend(all_new)

    if len(parts) == 1:
        combined = parts[0]
    else:
        combined = pd.concat(parts)
        combined = combined[~combined.index.duplicated(keep="last")]
        combined = combined.sort_index()

    return combined.loc[start:end]


def fetch_all_fx(currencies: list[str], start: str = "2015-01-01",
                 end: str = None) -> dict[str, pd.Series]:
    """Fetch les taux de change pour plusieurs devises vers EUR."""
    result = {}
    for ccy in set(currencies):
        result[ccy] = fetch_fx_rate(ccy, start, end)
    return result


def convert_to_eur(values: pd.Series, currency: str, fx_rates: pd.Series) -> pd.Series:
    """
    Convertit une série de valeurs en devise locale vers EUR.

    Aligne les dates et forward-fill les taux manquants (weekends/jours fériés).
    """
    if currency == "EUR":
        return values

    # Aligner les index
    aligned_fx = fx_rates.reindex(values.index).ffill()
    return values * aligned_fx


def _download_fx(pair_ticker: str, start: str, end: str) -> pd.Series:
    """Télécharge le taux de change via yfinance."""
    try:
        df = yf.download(pair_ticker, start=start, end=end, auto_adjust=True, progress=False)
    except Exception:
        return pd.Series(dtype=float)

    if df.empty:
        return pd.Series(dtype=float)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    col = "Close" if "Close" in df.columns else "close"
    if col not in df.columns:
        return pd.Series(dtype=float)

    series = df[col].dropna()
    series.index.name = "date"
    series.name = "fx_rate"
    return series


def _load_cache(currency: str, start: str, end: str) -> pd.Series | None:
    rows = get_cached_fx(currency, "EUR", start, end)
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["rate"].rename("fx_rate")
