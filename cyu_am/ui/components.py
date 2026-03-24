"""Composants UI réutilisables — KPI cards, badges, etc."""

import streamlit as st


def load_css():
    """Charge le CSS custom."""
    import os
    css_path = os.path.join(os.path.dirname(__file__), "style.css")
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def kpi_card(label: str, value: str, delta: str = None, positive: bool = True):
    """Affiche une carte KPI stylisée."""
    card_class = "kpi-card" if positive else "kpi-card negative"
    delta_class = "positive" if positive else "negative"
    delta_html = ""
    if delta:
        arrow = "+" if positive else ""
        delta_html = f'<p class="kpi-delta {delta_class}">{delta}</p>'

    st.markdown(f"""
    <div class="{card_class}">
        <p class="kpi-label">{label}</p>
        <p class="kpi-value">{value}</p>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def section_header(text: str):
    st.markdown(f'<p class="section-header">{text}</p>', unsafe_allow_html=True)


def asset_class_badge(asset_class: str) -> str:
    """Retourne le HTML d'un badge coloré pour une classe d'actif."""
    css_class = f"badge-{asset_class.lower()}"
    return f'<span class="badge {css_class}">{asset_class}</span>'


def empty_state(message: str = "Aucune donnee disponible."):
    """Affiche un message quand il n'y a pas de données."""
    st.info(message)


def portfolio_selector(portfolios: list[dict]) -> int | None:
    """Selecteur de portefeuille dans la sidebar. Retourne l'id ou None."""
    if not portfolios:
        st.sidebar.warning("Aucun portefeuille. Creez-en un dans Transactions.")
        return None

    names = [f"{p['name']} (#{p['id']})" for p in portfolios]
    selected = st.sidebar.selectbox("Portefeuille", names)
    idx = names.index(selected)
    return portfolios[idx]["id"]
