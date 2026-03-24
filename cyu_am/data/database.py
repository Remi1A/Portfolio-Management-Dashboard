"""Connexion SQLite et gestion du schéma."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from cyu_am.config.settings import DB_PATH


def _ensure_dir():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection():
    """Context manager pour une connexion SQLite avec foreign keys activées."""
    _ensure_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Crée toutes les tables si elles n'existent pas, et applique les migrations."""
    with get_connection() as conn:
        conn.executescript(_SCHEMA)
        _migrate_transactions_actions(conn)


def _migrate_transactions_actions(conn):
    """Migration : ajouter DEPOSIT/WITHDRAW à la contrainte action."""
    # Vérifier si la contrainte actuelle accepte DEPOSIT
    try:
        conn.execute(
            "INSERT INTO transactions (portfolio_id, date, ticker, asset_class, action, quantity, price) "
            "VALUES (-999, '1900-01-01', '_TEST_', 'EQUITY', 'DEPOSIT', 0, 0)"
        )
        # Ça marche → contrainte déjà à jour, supprimer la ligne de test
        conn.execute("DELETE FROM transactions WHERE portfolio_id = -999")
    except Exception:
        # Contrainte trop restrictive → recréer la table
        conn.execute("ALTER TABLE transactions RENAME TO _transactions_old")
        conn.executescript("""
            CREATE TABLE transactions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id    INTEGER NOT NULL REFERENCES portfolios(id),
                date            DATE NOT NULL,
                ticker          TEXT NOT NULL,
                asset_class     TEXT CHECK(asset_class IN ('EQUITY','ETF','BOND','FOREX','COMMODITY')),
                action          TEXT CHECK(action IN ('BUY','SELL','DEPOSIT','WITHDRAW')),
                quantity        REAL NOT NULL,
                price           REAL NOT NULL,
                asset_currency  TEXT DEFAULT 'EUR',
                fees            REAL DEFAULT 0,
                notes           TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO transactions SELECT * FROM _transactions_old;
            DROP TABLE _transactions_old;
            CREATE INDEX IF NOT EXISTS idx_transactions_portfolio
                ON transactions(portfolio_id, date);
        """)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    description     TEXT,
    currency        TEXT DEFAULT 'EUR',
    created_at      DATE NOT NULL,
    initial_cash    REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id    INTEGER NOT NULL REFERENCES portfolios(id),
    date            DATE NOT NULL,
    ticker          TEXT NOT NULL,
    asset_class     TEXT CHECK(asset_class IN ('EQUITY','ETF','BOND','FOREX','COMMODITY')),
    action          TEXT CHECK(action IN ('BUY','SELL','DEPOSIT','WITHDRAW')),
    quantity        REAL NOT NULL,
    price           REAL NOT NULL,
    asset_currency  TEXT DEFAULT 'EUR',
    fees            REAL DEFAULT 0,
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS market_prices (
    ticker      TEXT NOT NULL,
    date        DATE NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL NOT NULL,
    volume      INTEGER,
    fetched_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS fx_rates (
    base_currency   TEXT NOT NULL,
    quote_currency  TEXT NOT NULL,
    date            DATE NOT NULL,
    rate            REAL NOT NULL,
    PRIMARY KEY (base_currency, quote_currency, date)
);

CREATE TABLE IF NOT EXISTS assets_info (
    ticker          TEXT PRIMARY KEY,
    name            TEXT,
    sector          TEXT,
    industry        TEXT,
    currency        TEXT,
    market_cap      REAL,
    pe_ratio        REAL,
    dividend_yield  REAL,
    beta            REAL,
    updated_at      TIMESTAMP
);

CREATE TABLE IF NOT EXISTS nav_history (
    portfolio_id    INTEGER NOT NULL REFERENCES portfolios(id),
    date            DATE NOT NULL,
    nav             REAL NOT NULL,
    cash            REAL,
    invested_value  REAL,
    PRIMARY KEY (portfolio_id, date)
);

CREATE INDEX IF NOT EXISTS idx_transactions_portfolio
    ON transactions(portfolio_id, date);

CREATE INDEX IF NOT EXISTS idx_market_prices_date
    ON market_prices(ticker, date);

CREATE INDEX IF NOT EXISTS idx_fx_rates_date
    ON fx_rates(base_currency, quote_currency, date);
"""


# ── Helpers CRUD ──

def insert_portfolio(name: str, currency: str = "EUR", created_at: str = None,
                     initial_cash: float = 0, description: str = None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO portfolios (name, description, currency, created_at, initial_cash) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, description, currency, created_at, initial_cash),
        )
        return cur.lastrowid


def insert_transaction(portfolio_id: int, date: str, ticker: str, asset_class: str,
                       action: str, quantity: float, price: float,
                       asset_currency: str = "EUR", fees: float = 0,
                       notes: str = None):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO transactions "
            "(portfolio_id, date, ticker, asset_class, action, quantity, price, "
            "asset_currency, fees, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (portfolio_id, date, ticker, asset_class, action, quantity, price,
             asset_currency, fees, notes),
        )


def delete_portfolio(portfolio_id: int):
    """Supprime un portefeuille et toutes ses transactions/NAV."""
    with get_connection() as conn:
        conn.execute("DELETE FROM nav_history WHERE portfolio_id = ?", (portfolio_id,))
        conn.execute("DELETE FROM transactions WHERE portfolio_id = ?", (portfolio_id,))
        conn.execute("DELETE FROM portfolios WHERE id = ?", (portfolio_id,))


def get_portfolios() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM portfolios ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_transactions(portfolio_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE portfolio_id = ? ORDER BY date",
            (portfolio_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def upsert_market_prices(ticker: str, rows: list[tuple]):
    """Insère ou met à jour les prix. rows = [(date, open, high, low, close, volume), ...]"""
    with get_connection() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO market_prices "
            "(ticker, date, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(ticker, *row) for row in rows],
        )


def upsert_fx_rates(base_ccy: str, quote_ccy: str, rows: list[tuple]):
    """Insère ou met à jour les taux FX. rows = [(date, rate), ...]"""
    with get_connection() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO fx_rates "
            "(base_currency, quote_currency, date, rate) "
            "VALUES (?, ?, ?, ?)",
            [(base_ccy, quote_ccy, d, r) for d, r in rows],
        )


def get_cached_prices(ticker: str, start: str = None, end: str = None):
    """Récupère les prix en cache. Retourne list[dict]."""
    with get_connection() as conn:
        query = "SELECT * FROM market_prices WHERE ticker = ?"
        params = [ticker]
        if start:
            query += " AND date >= ?"
            params.append(start)
        if end:
            query += " AND date <= ?"
            params.append(end)
        query += " ORDER BY date"
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_cached_fx(base_ccy: str, quote_ccy: str, start: str = None, end: str = None):
    with get_connection() as conn:
        query = "SELECT date, rate FROM fx_rates WHERE base_currency = ? AND quote_currency = ?"
        params = [base_ccy, quote_ccy]
        if start:
            query += " AND date >= ?"
            params.append(start)
        if end:
            query += " AND date <= ?"
            params.append(end)
        query += " ORDER BY date"
        return [dict(r) for r in conn.execute(query, params).fetchall()]
