"""Page Reporting — generation et telechargement de rapports PDF."""

import streamlit as st
from datetime import date, timedelta

from cyu_am.config.benchmarks import list_benchmarks, DEFAULT_BENCHMARK
from cyu_am.data.database import get_portfolios
from cyu_am.reporting.pdf_generator import generate_monthly_report, save_report
from cyu_am.ui.components import portfolio_selector, section_header, empty_state, load_css


def render():
    load_css()
    st.title("Reporting PDF")

    portfolios = get_portfolios()
    pid = portfolio_selector(portfolios)
    if pid is None:
        empty_state("Creez un portefeuille dans l'onglet Transactions.")
        return

    portfolio = next((p for p in portfolios if p["id"] == pid), None)

    section_header("Generer un rapport")

    col1, col2 = st.columns(2)
    with col1:
        benchmark_name = st.selectbox("Benchmark de reference", list_benchmarks(),
                                      index=list_benchmarks().index(DEFAULT_BENCHMARK),
                                      key="report_bench")
    with col2:
        report_type = st.selectbox("Type de rapport",
                                   ["Mensuel", "Trimestriel", "Personnalise"])

    # Dates selon le type
    today = date.today()
    if report_type == "Mensuel":
        first_of_month = today.replace(day=1)
        last_month_end = first_of_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        start_date = st.date_input("Debut", value=last_month_start, key="report_start")
        end_date = st.date_input("Fin", value=last_month_end, key="report_end")
    elif report_type == "Trimestriel":
        quarter_start = today.replace(month=((today.month - 1) // 3) * 3 + 1, day=1)
        prev_quarter_end = quarter_start - timedelta(days=1)
        prev_quarter_start = prev_quarter_end.replace(
            month=((prev_quarter_end.month - 1) // 3) * 3 + 1, day=1
        )
        start_date = st.date_input("Debut", value=prev_quarter_start, key="report_start")
        end_date = st.date_input("Fin", value=prev_quarter_end, key="report_end")
    else:
        start_date = st.date_input("Debut", value=today - timedelta(days=90), key="report_start")
        end_date = st.date_input("Fin", value=today, key="report_end")

    st.markdown("---")

    # Apercu du contenu
    st.markdown(f"""
    **Rapport a generer :**
    - Portefeuille : **{portfolio['name']}**
    - Benchmark : **{benchmark_name}**
    - Periode : **{start_date.strftime('%d/%m/%Y')}** au **{end_date.strftime('%d/%m/%Y')}**
    - Type : **{report_type}**

    **Contenu du rapport :**
    1. Page de garde
    2. Resume executif (KPIs + benchmark)
    3. Performance (rendements mensuels)
    4. Analyse des risques (metriques + stress tests)
    5. Concentration sectorielle et geographique
    6. Composition du portefeuille + transactions
    """)

    # Verifier que le portefeuille a des transactions
    from cyu_am.data.database import get_transactions
    txns = get_transactions(pid)
    if not txns:
        st.warning("Ce portefeuille n'a aucune transaction. Ajoutez des transactions avant de generer un rapport.")
        return

    col_gen, col_save = st.columns(2)

    with col_gen:
        if st.button("Generer le PDF", type="primary", use_container_width=True):
            try:
                with st.spinner("Generation du rapport en cours..."):
                    pdf_bytes = generate_monthly_report(
                        portfolio_id=pid,
                        benchmark_name=benchmark_name,
                        start_date=str(start_date),
                        end_date=str(end_date),
                    )
                st.session_state["last_pdf"] = pdf_bytes
                st.session_state["last_pdf_name"] = portfolio["name"]
                st.success("Rapport genere avec succes !")
            except ValueError as e:
                st.warning(str(e))
            except Exception as e:
                st.error(f"Erreur lors de la generation : {e}")

    # Téléchargement
    if "last_pdf" in st.session_state:
        pdf_bytes = st.session_state["last_pdf"]
        pdf_name = st.session_state.get("last_pdf_name", "rapport")
        filename = f"rapport_{pdf_name.replace(' ', '_')}_{start_date.strftime('%Y%m')}.pdf"

        st.download_button(
            "Telecharger le PDF",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            use_container_width=True,
        )

        with col_save:
            if st.button("Sauvegarder sur disque", use_container_width=True):
                filepath = save_report(pdf_bytes, pdf_name,
                                       start_date.strftime("%Y%m"))
                st.success(f"Sauvegarde : {filepath}")
