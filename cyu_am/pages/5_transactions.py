"""Page Transactions — saisie manuelle, import CSV, historique."""

import streamlit as st
import pandas as pd
from datetime import date

from cyu_am.config.tickers import UNIVERSE, ASSET_CLASSES
from cyu_am.data.database import (
    get_portfolios, insert_portfolio, insert_transaction, get_transactions,
    delete_portfolio,
)
from cyu_am.data.market_data import fetch_prices
from cyu_am.data.cached import clear_portfolio_cache, get_current_cash
from cyu_am.utils.validators import validate_ticker, validate_transaction_date, validate_csv_data


def render():
    st.title("Transactions")

    tab_portfolio, tab_add, tab_cash, tab_import, tab_history = st.tabs([
        "Creer un portefeuille", "Ajouter une transaction",
        "Depot / Retrait", "Import CSV", "Historique"
    ])

    # ── Créer un portefeuille ──
    with tab_portfolio:
        _render_create_portfolio()

    # ── Ajouter une transaction ──
    with tab_add:
        _render_add_transaction()

    # ── Dépôt / Retrait de cash ──
    with tab_cash:
        _render_cash_management()

    # ── Import CSV ──
    with tab_import:
        _render_import_csv()

    # ── Historique ──
    with tab_history:
        _render_history()


def _render_create_portfolio():
    with st.form("create_portfolio"):
        st.subheader("Nouveau portefeuille")
        name = st.text_input("Nom", placeholder="Ex: Portefeuille Croissance")
        description = st.text_area("Description", placeholder="Optionnel")
        col1, col2 = st.columns(2)
        with col1:
            currency = st.selectbox("Devise de reference", ["EUR", "USD", "GBP"])
        with col2:
            initial_cash = st.number_input("Capital initial", min_value=0.0,
                                           value=100000.0, step=1000.0)
        created_at = st.date_input("Date de creation", value=date.today())
        submitted = st.form_submit_button("Creer le portefeuille", type="primary")

        if submitted:
            if not name.strip():
                st.error("Le nom est obligatoire.")
            else:
                pid = insert_portfolio(
                    name=name.strip(),
                    currency=currency,
                    created_at=str(created_at),
                    initial_cash=initial_cash,
                    description=description.strip() or None,
                )
                st.success(f"Portefeuille '{name}' cree (ID: {pid})")
                st.rerun()

    # Liste des portefeuilles existants
    portfolios = get_portfolios()
    if portfolios:
        st.subheader("Portefeuilles existants")
        df = pd.DataFrame(portfolios)[["id", "name", "currency", "initial_cash", "created_at"]]
        df.columns = ["ID", "Nom", "Devise", "Capital initial", "Date creation"]
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Suppression
        st.subheader("Supprimer un portefeuille")
        del_names = {f"{p['name']} (#{p['id']})": p["id"] for p in portfolios}
        del_selected = st.selectbox("Portefeuille a supprimer", list(del_names.keys()),
                                    key="del_portfolio")
        del_id = del_names[del_selected]
        txn_count = len(get_transactions(del_id))
        st.warning(f"Cette action supprimera le portefeuille et ses {txn_count} transaction(s). Irreversible.")
        if st.button("Supprimer", type="secondary", key="btn_delete_portfolio"):
            delete_portfolio(del_id)
            clear_portfolio_cache()
            st.success(f"Portefeuille supprime.")
            st.rerun()


def _fetch_price_for_date(ticker: str, tx_date: str) -> float | None:
    """Recupere le prix de cloture d'un ticker a une date donnee via yfinance."""
    try:
        dt = pd.Timestamp(tx_date)
        start = (dt - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
        end = (dt + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        df = fetch_prices(ticker, start=start, end=end)
        if df.empty:
            return None
        valid = df.loc[:tx_date]
        if valid.empty:
            return None
        return float(valid["close"].iloc[-1])
    except Exception:
        return None


def _render_add_transaction():
    portfolios = get_portfolios()
    if not portfolios:
        st.warning("Creez d'abord un portefeuille.")
        return

    st.subheader("Nouvelle transaction")

    # ── Sélection du portefeuille ──
    portfolio_names = {f"{p['name']} (#{p['id']})": p["id"] for p in portfolios}
    selected = st.selectbox("Portefeuille", list(portfolio_names.keys()), key="tx_portfolio")
    portfolio_id = portfolio_names[selected]

    # ── Affichage du cash disponible ──
    current_cash = get_current_cash(portfolio_id)
    cash_color = "green" if current_cash > 0 else "red"
    st.markdown(f"**Cash disponible** : :{cash_color}[**{current_cash:,.2f} EUR**]")

    col1, col2 = st.columns(2)
    with col1:
        tx_date = st.date_input("Date", value=date.today(), max_value=date.today(), key="tx_date")
        action = st.selectbox("Action", ["BUY", "SELL"], key="tx_action")
    with col2:
        ticker_mode = st.radio("Ticker", ["Univers CYU AM", "Personnalise"],
                               horizontal=True, key="tx_mode")

    if ticker_mode == "Univers CYU AM":
        ticker_options = [f"{t} — {m['name']}" for t, m in UNIVERSE.items()]
        selected_ticker = st.selectbox("Actif", ticker_options, key="tx_asset")
        ticker = selected_ticker.split(" — ")[0]
        asset_class = UNIVERSE[ticker]["asset_class"]
        asset_currency = UNIVERSE[ticker]["currency"]
    else:
        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            ticker = st.text_input("Ticker Yahoo", placeholder="Ex: TSLA", key="tx_ticker").strip().upper()
        with col_t2:
            asset_class = st.selectbox("Classe d'actif", ASSET_CLASSES, key="tx_class")
        with col_t3:
            asset_currency = st.selectbox("Devise de l'actif", ["EUR", "USD", "GBP", "CHF"],
                                          key="tx_currency")

    # ── Affichage du prix en temps réel ──
    auto_price = st.checkbox("Prix automatique (Yahoo Finance)", value=True, key="tx_auto")
    fetched_price = None
    if ticker and auto_price:
        fetched_price = _fetch_price_for_date(ticker, str(tx_date))
        if fetched_price is not None:
            st.info(f"Prix de **{ticker}** au **{tx_date}** : **{fetched_price:.2f} {asset_currency}**")
        else:
            st.warning(f"Prix introuvable pour {ticker} au {tx_date}.")

    # ── Formulaire de confirmation ──
    with st.form("add_transaction"):
        col3, col4 = st.columns(2)
        with col3:
            quantity = st.number_input("Quantite", min_value=0.001, value=10.0, step=1.0)
        with col4:
            if auto_price and fetched_price is not None:
                st.metric("Prix unitaire", f"{fetched_price:.2f} {asset_currency}")
                price = fetched_price
            elif not auto_price:
                price = st.number_input("Prix unitaire", min_value=0.01, value=100.0, step=0.01)
            else:
                st.warning("Prix non disponible.")
                price = None

        # Afficher le montant total estimé
        if price is not None:
            total = quantity * price
            st.caption(f"Montant total estime : **{total:,.2f} {asset_currency}**")

        fees = st.number_input("Frais", min_value=0.0, value=0.0, step=0.1)
        notes = st.text_input("Notes", placeholder="Optionnel")
        submitted = st.form_submit_button("Enregistrer la transaction", type="primary")

        if submitted:
            if not ticker:
                st.error("Le ticker est obligatoire.")
                st.stop()

            date_ok, date_msg = validate_transaction_date(tx_date)
            if not date_ok:
                st.error(date_msg)
                st.stop()

            if ticker_mode == "Personnalise":
                with st.spinner(f"Verification de {ticker}..."):
                    valid, msg = validate_ticker(ticker)
                if not valid:
                    st.error(msg)
                    st.stop()

            if price is None:
                st.error(
                    f"Impossible de recuperer le prix de {ticker} au {tx_date}. "
                    "Verifiez le ticker ou decochez le prix automatique."
                )
                st.stop()

            # Validation cash suffisant pour un achat
            if action == "BUY":
                # Estimation du coût en EUR (approximatif si devise != EUR)
                from cyu_am.data.fx_data import fetch_fx_rate
                if asset_currency != "EUR":
                    fx_series = fetch_fx_rate(asset_currency,
                                              start=str(tx_date),
                                              end=str(tx_date))
                    fx_rate = float(fx_series.iloc[-1]) if not fx_series.empty else 1.0
                else:
                    fx_rate = 1.0
                cost_eur = quantity * price * fx_rate + fees * fx_rate
                if cost_eur > current_cash:
                    st.error(
                        f"Cash insuffisant. Cout estime : {cost_eur:,.2f} EUR, "
                        f"cash disponible : {current_cash:,.2f} EUR. "
                        f"Faites un depot dans l'onglet 'Depot / Retrait'."
                    )
                    st.stop()

            insert_transaction(
                portfolio_id=portfolio_id,
                date=str(tx_date),
                ticker=ticker,
                asset_class=asset_class,
                action=action,
                quantity=quantity,
                price=price,
                asset_currency=asset_currency,
                fees=fees,
                notes=notes.strip() or None,
            )
            clear_portfolio_cache()
            st.success(f"{action} {quantity} x {ticker} @ {price:.2f} {asset_currency}")
            st.rerun()


def _render_cash_management():
    portfolios = get_portfolios()
    if not portfolios:
        st.warning("Creez d'abord un portefeuille.")
        return

    st.subheader("Depot / Retrait de cash")

    portfolio_names = {f"{p['name']} (#{p['id']})": p["id"] for p in portfolios}
    selected = st.selectbox("Portefeuille", list(portfolio_names.keys()), key="cash_portfolio")
    portfolio_id = portfolio_names[selected]

    # Afficher le cash actuel
    current_cash = get_current_cash(portfolio_id)
    cash_color = "green" if current_cash > 0 else "red"
    st.markdown(f"### Cash actuel : :{cash_color}[**{current_cash:,.2f} EUR**]")

    with st.form("cash_form"):
        col1, col2 = st.columns(2)
        with col1:
            cash_action = st.selectbox("Operation", ["DEPOSIT", "WITHDRAW"],
                                       format_func=lambda x: "Depot" if x == "DEPOSIT" else "Retrait")
        with col2:
            cash_date = st.date_input("Date", value=date.today(), max_value=date.today(),
                                      key="cash_date")

        amount = st.number_input("Montant (EUR)", min_value=0.01, value=10000.0, step=1000.0)
        cash_notes = st.text_input("Notes", placeholder="Ex: Virement initial, apport mensuel...",
                                   key="cash_notes")
        submitted = st.form_submit_button("Valider", type="primary")

        if submitted:
            if cash_action == "WITHDRAW" and amount > current_cash:
                st.error(
                    f"Retrait impossible : montant ({amount:,.2f} EUR) "
                    f"superieur au cash disponible ({current_cash:,.2f} EUR)."
                )
                st.stop()

            insert_transaction(
                portfolio_id=portfolio_id,
                date=str(cash_date),
                ticker="CASH",
                asset_class=None,
                action=cash_action,
                quantity=1,
                price=amount,
                asset_currency="EUR",
                fees=0,
                notes=cash_notes.strip() or None,
            )
            clear_portfolio_cache()
            label = "Depot" if cash_action == "DEPOSIT" else "Retrait"
            st.success(f"{label} de {amount:,.2f} EUR effectue.")
            st.rerun()


def _render_import_csv():
    st.subheader("Import CSV")

    portfolios = get_portfolios()
    if not portfolios:
        st.warning("Creez d'abord un portefeuille.")
        return

    portfolio_names = {f"{p['name']} (#{p['id']})": p["id"] for p in portfolios}
    selected = st.selectbox("Portefeuille cible", list(portfolio_names.keys()),
                            key="import_portfolio")
    portfolio_id = portfolio_names[selected]

    # Template
    st.markdown("**Format attendu** (colonnes obligatoires) :")
    template = pd.DataFrame({
        "date": ["2025-01-15", "2025-01-20"],
        "ticker": ["AAPL", "MC.PA"],
        "asset_class": ["EQUITY", "EQUITY"],
        "action": ["BUY", "BUY"],
        "quantity": [50, 20],
        "price": [195.0, 750.0],
        "asset_currency": ["USD", "EUR"],
        "fees": [10.0, 5.0],
        "notes": ["", ""],
    })
    st.dataframe(template, use_container_width=True, hide_index=True)
    st.download_button(
        "Telecharger le template CSV",
        template.to_csv(index=False),
        "template_transactions.csv",
        "text/csv",
    )

    # Upload
    uploaded = st.file_uploader("Charger un fichier CSV", type=["csv"])
    if uploaded:
        try:
            df = pd.read_csv(uploaded)
        except Exception as e:
            st.error(f"Erreur de lecture : {e}")
            return

        required = {"date", "ticker", "asset_class", "action", "quantity", "price"}
        missing = required - set(df.columns)
        if missing:
            st.error(f"Colonnes manquantes : {missing}")
            return

        # Validation du contenu
        data_errors = validate_csv_data(df)
        if data_errors:
            st.error("Erreurs dans le CSV :")
            for err in data_errors[:10]:
                st.warning(err)
            if len(data_errors) > 10:
                st.warning(f"... et {len(data_errors) - 10} autres erreurs.")
            return

        st.dataframe(df, use_container_width=True, hide_index=True)
        st.write(f"**{len(df)} transactions** detectees.")

        if st.button("Importer toutes les transactions", type="primary"):
            count = 0
            for _, row in df.iterrows():
                insert_transaction(
                    portfolio_id=portfolio_id,
                    date=str(row["date"]),
                    ticker=str(row["ticker"]).strip(),
                    asset_class=str(row.get("asset_class", "EQUITY")),
                    action=str(row["action"]).upper(),
                    quantity=float(row["quantity"]),
                    price=float(row["price"]),
                    asset_currency=str(row.get("asset_currency", "EUR")),
                    fees=float(row.get("fees", 0)),
                    notes=str(row.get("notes", "")) or None,
                )
                count += 1
            clear_portfolio_cache()
            st.success(f"{count} transactions importees.")
            st.rerun()


def _render_history():
    portfolios = get_portfolios()
    if not portfolios:
        st.warning("Aucun portefeuille.")
        return

    portfolio_names = {f"{p['name']} (#{p['id']})": p["id"] for p in portfolios}
    selected = st.selectbox("Portefeuille", list(portfolio_names.keys()),
                            key="history_portfolio")
    portfolio_id = portfolio_names[selected]

    txns = get_transactions(portfolio_id)
    if not txns:
        st.info("Aucune transaction enregistree.")
        return

    df = pd.DataFrame(txns)
    display_cols = ["date", "ticker", "asset_class", "action", "quantity",
                    "price", "asset_currency", "fees", "notes"]
    display_cols = [c for c in display_cols if c in df.columns]

    # Filtres
    col1, col2, col3 = st.columns(3)
    with col1:
        tickers = ["Tous"] + sorted(df["ticker"].unique().tolist())
        filter_ticker = st.selectbox("Filtrer par ticker", tickers, key="filter_ticker")
    with col2:
        actions = ["Tous", "BUY", "SELL"]
        filter_action = st.selectbox("Filtrer par action", actions, key="filter_action")
    with col3:
        classes = ["Tous"] + sorted(df["asset_class"].dropna().unique().tolist())
        filter_class = st.selectbox("Filtrer par classe", classes, key="filter_class")

    filtered = df.copy()
    if filter_ticker != "Tous":
        filtered = filtered[filtered["ticker"] == filter_ticker]
    if filter_action != "Tous":
        filtered = filtered[filtered["action"] == filter_action]
    if filter_class != "Tous":
        filtered = filtered[filtered["asset_class"] == filter_class]

    st.write(f"**{len(filtered)} transactions**")
    st.dataframe(filtered[display_cols], use_container_width=True, hide_index=True)

    # Export
    csv = filtered[display_cols].to_csv(index=False)
    st.download_button("Exporter en CSV", csv, "transactions_export.csv", "text/csv")
