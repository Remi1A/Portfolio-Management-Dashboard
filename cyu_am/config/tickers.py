"""Univers d'investissement CYU AM — actifs, classes et métadonnées."""

ASSET_CLASSES = ("EQUITY", "ETF", "BOND", "FOREX", "COMMODITY")

# Univers complet : ticker Yahoo → métadonnées
UNIVERSE = {
    # ── Technologie ──
    "AAPL":    {"name": "Apple",            "asset_class": "EQUITY", "sector": "Technology",  "currency": "USD", "country": "United States", "region": "North America"},
    "MSFT":    {"name": "Microsoft",        "asset_class": "EQUITY", "sector": "Technology",  "currency": "USD", "country": "United States", "region": "North America"},
    "ASML.AS": {"name": "ASML",             "asset_class": "EQUITY", "sector": "Technology",  "currency": "EUR", "country": "Netherlands",   "region": "Europe"},
    "NVDA":    {"name": "NVIDIA",           "asset_class": "EQUITY", "sector": "Technology",  "currency": "USD", "country": "United States", "region": "North America"},
    # ── Santé ──
    "SAN.PA":  {"name": "Sanofi",           "asset_class": "EQUITY", "sector": "Healthcare",  "currency": "EUR", "country": "France",        "region": "Europe"},
    "NVO":     {"name": "Novo Nordisk",     "asset_class": "EQUITY", "sector": "Healthcare",  "currency": "USD", "country": "Denmark",       "region": "Europe"},
    # ── Finance ──
    "BNP.PA":  {"name": "BNP Paribas",     "asset_class": "EQUITY", "sector": "Finance",     "currency": "EUR", "country": "France",        "region": "Europe"},
    "GS":      {"name": "Goldman Sachs",    "asset_class": "EQUITY", "sector": "Finance",     "currency": "USD", "country": "United States", "region": "North America"},
    # ── Consommation ──
    "MC.PA":   {"name": "LVMH",             "asset_class": "EQUITY", "sector": "Consumer",    "currency": "EUR", "country": "France",        "region": "Europe"},
    "OR.PA":   {"name": "L'Oréal",          "asset_class": "EQUITY", "sector": "Consumer",    "currency": "EUR", "country": "France",        "region": "Europe"},
    "AMZN":    {"name": "Amazon",           "asset_class": "EQUITY", "sector": "Consumer",    "currency": "USD", "country": "United States", "region": "North America"},
    # ── Énergie ──
    "TTE.PA":  {"name": "TotalEnergies",    "asset_class": "EQUITY", "sector": "Energy",      "currency": "EUR", "country": "France",        "region": "Europe"},
    # ── ETF ──
    "CW8.PA":  {"name": "Amundi MSCI World","asset_class": "ETF",    "sector": "Broad Market","currency": "EUR", "country": "Global",        "region": "Global"},
    "SPY":     {"name": "SPDR S&P 500",     "asset_class": "ETF",    "sector": "US Equity",   "currency": "USD", "country": "United States", "region": "North America"},
    "IWDA.AS": {"name": "iShares MSCI World","asset_class": "ETF",   "sector": "Broad Market","currency": "USD", "country": "Global",        "region": "Global"},
    "LQD":     {"name": "iShares IG Corp Bond","asset_class": "ETF", "sector": "Credit",      "currency": "USD", "country": "United States", "region": "North America"},
    # ── Matières premières ──
    "GC=F":    {"name": "Gold Futures",     "asset_class": "COMMODITY","sector": "Precious Metals","currency": "USD", "country": "Global", "region": "Global"},
    "CL=F":    {"name": "WTI Crude Oil",    "asset_class": "COMMODITY","sector": "Energy",     "currency": "USD", "country": "Global",        "region": "Global"},
    # ── Forex ──
    "EURUSD=X":{"name": "EUR/USD",          "asset_class": "FOREX",  "sector": "FX",          "currency": "USD", "country": "N/A",           "region": "N/A"},
    "EURGBP=X":{"name": "EUR/GBP",          "asset_class": "FOREX",  "sector": "FX",          "currency": "GBP", "country": "N/A",           "region": "N/A"},
}


def get_tickers_by_class(asset_class: str) -> list[str]:
    return [t for t, m in UNIVERSE.items() if m["asset_class"] == asset_class]


def get_tickers_by_sector(sector: str) -> list[str]:
    return [t for t, m in UNIVERSE.items() if m["sector"] == sector]


def get_currency(ticker: str) -> str:
    return UNIVERSE.get(ticker, {}).get("currency", "EUR")


def get_sector(ticker: str) -> str:
    return UNIVERSE.get(ticker, {}).get("sector", "Other")


def get_country(ticker: str) -> str:
    return UNIVERSE.get(ticker, {}).get("country", "N/A")


def get_region(ticker: str) -> str:
    return UNIVERSE.get(ticker, {}).get("region", "N/A")


# Paires FX nécessaires pour convertir vers EUR
FX_PAIRS = {
    "USD": "EURUSD=X",
    "GBP": "EURGBP=X",
    "CHF": "EURCHF=X",
}
