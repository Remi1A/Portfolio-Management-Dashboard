"""Validation des inputs utilisateur — tickers, dates, transactions."""

import pandas as pd
import yfinance as yf
from datetime import date

from cyu_am.config.tickers import UNIVERSE

# Cache des tickers deja valides pour eviter des appels yfinance repetes
_validated_tickers: dict[str, bool] = {}


def validate_ticker(ticker: str) -> tuple[bool, str]:
    """
    Verifie qu'un ticker existe sur Yahoo Finance.

    Les tickers du UNIVERSE sont acceptes sans verification.
    Pour les tickers custom, tente un appel yfinance.

    Returns:
        (is_valid, message)
    """
    ticker = ticker.strip().upper()

    if not ticker:
        return False, "Le ticker est vide."

    # Tickers de l'univers toujours valides
    if ticker in UNIVERSE:
        return True, ""

    # Cache local
    if ticker in _validated_tickers:
        if _validated_tickers[ticker]:
            return True, ""
        else:
            return False, f"Ticker '{ticker}' introuvable sur Yahoo Finance."

    # Verification via yfinance
    try:
        info = yf.Ticker(ticker).info
        # yfinance retourne un dict meme pour les tickers invalides,
        # mais les tickers invalides n'ont pas de 'regularMarketPrice'
        # ou ont un 'trailingPegRatio' == None avec peu de donnees
        if info and info.get("regularMarketPrice") is not None:
            _validated_tickers[ticker] = True
            return True, ""
        # Fallback : essayer de telecharger 5 jours de prix
        hist = yf.Ticker(ticker).history(period="5d")
        if not hist.empty:
            _validated_tickers[ticker] = True
            return True, ""

        _validated_tickers[ticker] = False
        return False, f"Ticker '{ticker}' introuvable sur Yahoo Finance."
    except Exception:
        _validated_tickers[ticker] = False
        return False, f"Impossible de verifier le ticker '{ticker}'."


def validate_transaction_date(tx_date: date) -> tuple[bool, str]:
    """Verifie que la date n'est pas dans le futur."""
    if tx_date > date.today():
        return False, "La date ne peut pas etre dans le futur."
    return True, ""


def validate_csv_columns(df: pd.DataFrame) -> tuple[bool, str]:
    """Verifie qu'un DataFrame CSV a les colonnes requises."""
    required = {"date", "ticker", "asset_class", "action", "quantity", "price"}
    missing = required - set(df.columns)
    if missing:
        return False, f"Colonnes manquantes : {', '.join(sorted(missing))}"
    return True, ""


def validate_csv_data(df: pd.DataFrame) -> list[str]:
    """
    Valide le contenu d'un CSV de transactions ligne par ligne.

    Returns:
        Liste de messages d'erreur (vide si tout est OK).
    """
    errors = []

    for i, row in df.iterrows():
        line = i + 2  # +2 car header + index 0

        # Action
        action = str(row.get("action", "")).upper()
        if action not in ("BUY", "SELL"):
            errors.append(f"Ligne {line}: action '{action}' invalide (BUY ou SELL).")

        # Quantite
        try:
            qty = float(row["quantity"])
            if qty <= 0:
                errors.append(f"Ligne {line}: quantite doit etre > 0.")
        except (ValueError, TypeError):
            errors.append(f"Ligne {line}: quantite invalide.")

        # Prix
        try:
            price = float(row["price"])
            if price <= 0:
                errors.append(f"Ligne {line}: prix doit etre > 0.")
        except (ValueError, TypeError):
            errors.append(f"Ligne {line}: prix invalide.")

        # Date
        try:
            pd.Timestamp(row["date"])
        except Exception:
            errors.append(f"Ligne {line}: date invalide '{row['date']}'.")

    return errors
