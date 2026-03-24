"""Benchmarks disponibles pour la comparaison de performance."""

BENCHMARKS = {
    "S&P 500":      {"ticker": "^GSPC",     "currency": "USD"},
    "CAC 40":       {"ticker": "^FCHI",     "currency": "EUR"},
    "MSCI World":   {"ticker": "URTH",      "currency": "USD"},
    "Euro Stoxx 50":{"ticker": "^STOXX50E", "currency": "EUR"},
}

DEFAULT_BENCHMARK = "S&P 500"


def get_benchmark_ticker(name: str) -> str:
    return BENCHMARKS[name]["ticker"]


def get_benchmark_currency(name: str) -> str:
    return BENCHMARKS[name]["currency"]


def list_benchmarks() -> list[str]:
    return list(BENCHMARKS.keys())
