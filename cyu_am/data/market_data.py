"""Wrapper yfinance — fetch OHLCV avec cache SQLite."""

import pandas as pd
import yfinance as yf

from cyu_am.data.database import get_cached_prices, upsert_market_prices


def fetch_prices(ticker: str, start: str = "2015-01-01", end: str = None,
                 use_cache: bool = True) -> pd.DataFrame:
    """
    Récupère les prix OHLCV quotidiens pour un ticker.

    Stratégie :
    1. Vérifie le cache SQLite
    2. Détermine les dates manquantes
    3. Fetch yfinance uniquement pour le delta
    4. Stocke en cache et retourne le tout

    Returns:
        DataFrame indexé par date avec colonnes [open, high, low, close, volume].
    """
    if end is None:
        end = pd.Timestamp.now().strftime("%Y-%m-%d")

    # 1. Cache
    cached = pd.DataFrame()
    if use_cache:
        rows = get_cached_prices(ticker, start, end)
        if rows:
            cached = pd.DataFrame(rows)
            cached["date"] = pd.to_datetime(cached["date"])
            cached = cached.set_index("date")[["open", "high", "low", "close", "volume"]]

    # 2. Déterminer ce qui manque (début ET fin)
    fetch_ranges = []
    if not cached.empty:
        first_cached = cached.index.min().strftime("%Y-%m-%d")
        last_cached = cached.index.max().strftime("%Y-%m-%d")
        # Manque-t-il des données AVANT le cache ?
        if start < first_cached:
            fetch_ranges.append((start, first_cached))
        # Manque-t-il des données APRÈS le cache ?
        if last_cached < end:
            fetch_after = (cached.index.max() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            fetch_ranges.append((fetch_after, end))
    else:
        fetch_ranges.append((start, end))

    # 3. Fetch yfinance pour chaque plage manquante
    new_frames = []
    for fs, fe in fetch_ranges:
        chunk = _download(ticker, fs, fe)
        if not chunk.empty:
            new_frames.append(chunk)

    # 4. Cache les nouvelles données
    for new_data in new_frames:
        rows_to_cache = [
            (row.Index.strftime("%Y-%m-%d"), row.open, row.high, row.low, row.close,
             int(row.volume) if pd.notna(row.volume) else None)
            for row in new_data.itertuples()
        ]
        upsert_market_prices(ticker, rows_to_cache)

    # 5. Combiner
    all_parts = [cached] + new_frames
    all_parts = [df for df in all_parts if not df.empty]
    if not all_parts:
        return pd.DataFrame()
    combined = pd.concat(all_parts)
    combined = combined[~combined.index.duplicated(keep="last")]
    return combined.sort_index().loc[start:end]


def _download(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Télécharge les données via yfinance."""
    try:
        df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return df

    # Normaliser les noms de colonnes (yfinance peut retourner des MultiIndex)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]

    # S'assurer qu'on a les colonnes attendues
    expected = ["open", "high", "low", "close", "volume"]
    for col in expected:
        if col not in df.columns:
            df[col] = None

    df.index.name = "date"
    return df[expected]


def fetch_multiple(tickers: list[str], start: str = "2015-01-01",
                   end: str = None) -> dict[str, pd.DataFrame]:
    """Fetch les prix pour plusieurs tickers. Retourne {ticker: DataFrame}."""
    return {t: fetch_prices(t, start, end) for t in tickers}


def get_latest_price(ticker: str) -> float | None:
    """Retourne le dernier prix de clôture disponible."""
    df = fetch_prices(ticker, start="2020-01-01")
    if df.empty:
        return None
    return float(df["close"].iloc[-1])
