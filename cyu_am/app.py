"""CY Tech AM - Dashboard de gestion de portefeuille."""

import importlib

from streamlit import config as _st_config
_st_config.set_option("client.showSidebarNavigation", False)

import streamlit as st

from cyu_am.data.database import init_db

# Config Streamlit
st.set_page_config(
    page_title="CY Tech AM - Portfolio Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Init DB au premier lancement
init_db()

# Navigation sidebar
try:
    from streamlit_option_menu import option_menu

    with st.sidebar:
        st.markdown("## CY Tech AM")
        page = option_menu(
            menu_title=None,
            options=[
                "Overview",
                "Performance",
                "Risques",
                "Positions",
                "Transactions",
                "Optimisation",
                "Reporting",
            ],
            icons=[
                "house",
                "graph-up",
                "shield-exclamation",
                "briefcase",
                "list-ul",
                "cpu",
                "file-earmark-pdf",
            ],
            default_index=0,
        )
except ImportError:
    with st.sidebar:
        st.markdown("## CY Tech AM")
        page = st.radio(
            "Navigation",
            [
                "Overview",
                "Performance",
                "Risques",
                "Positions",
                "Transactions",
                "Optimisation",
                "Reporting",
            ],
        )

# Routing (imports dynamiques pour modules pages nommes 1_*, 2_*, ...)
page_modules = {
    "Overview": "cyu_am.pages.1_overview",
    "Performance": "cyu_am.pages.2_performance",
    "Risques": "cyu_am.pages.3_risk",
    "Positions": "cyu_am.pages.4_positions",
    "Transactions": "cyu_am.pages.5_transactions",
    "Optimisation": "cyu_am.pages.6_optimization",
    "Reporting": "cyu_am.pages.7_reporting",
}

module_name = page_modules.get(page)
if not module_name:
    st.error(f"Page inconnue: {page}")
else:
    module = importlib.import_module(module_name)
    module.render()
