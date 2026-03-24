"""
CYU AM - Launcher pour le dashboard.

Lance Streamlit directement (sans subprocess) pour compatibilite .exe PyInstaller.
"""

import sys
import os
import webbrowser
import time
import threading
import socket


def get_base_path():
    """Retourne le repertoire de base des fichiers bundled."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def get_data_dir():
    """Retourne le repertoire pour les donnees persistantes (DB, exports)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def is_port_open(port, timeout=1):
    """Verifie si le port est ouvert (Streamlit pret)."""
    try:
        with socket.create_connection(("localhost", port), timeout=timeout):
            return True
    except (ConnectionRefusedError, OSError):
        return False


def open_browser_when_ready(port=8501, max_wait=30):
    """Ouvre le navigateur UNE SEULE FOIS quand Streamlit est pret."""
    for _ in range(max_wait):
        time.sleep(1)
        if is_port_open(port):
            webbrowser.open(f"http://localhost:{port}")
            return
    webbrowser.open(f"http://localhost:{port}")


def main():
    base = get_base_path()
    data_dir = get_data_dir()
    app_path = os.path.join(base, "cyu_am", "app.py")

    if not os.path.exists(app_path):
        print(f"ERREUR: {app_path} introuvable")
        input("Appuyez sur Entree pour fermer...")
        sys.exit(1)

    # ── Environnement PyInstaller ──
    # Exporter le chemin des donnees persistantes (lu par settings.py)
    os.environ["CYU_AM_DATA_DIR"] = data_dir

    # Desactiver la navigation sidebar native de Streamlit (evite le doublon)
    os.environ["STREAMLIT_CLIENT_SHOW_SIDEBAR_NAVIGATION"] = "false"

    # S'assurer que _MEIPASS est dans sys.path pour les imports cyu_am.*
    if getattr(sys, "frozen", False) and base not in sys.path:
        sys.path.insert(0, base)

    # Copier .streamlit/config.toml vers data_dir pour que Streamlit le trouve
    src_streamlit = os.path.join(base, ".streamlit")
    dst_streamlit = os.path.join(data_dir, ".streamlit")
    if os.path.isdir(src_streamlit) and not os.path.isdir(dst_streamlit):
        import shutil
        shutil.copytree(src_streamlit, dst_streamlit)

    # Definir le working directory
    os.chdir(data_dir)

    print("=" * 50)
    print("   CYU AM - Portfolio Dashboard")
    print("=" * 50)
    print()
    print("Demarrage du serveur...")
    print("Le navigateur va s'ouvrir automatiquement.")
    print("(Ne fermez pas cette fenetre)")
    print()

    # Ouvrir le navigateur UNE SEULE FOIS dans un thread
    browser_thread = threading.Thread(target=open_browser_when_ready, daemon=True)
    browser_thread.start()

    # ── Lancer Streamlit en appelant bootstrap.run() directement ──
    # On evite stcli.main() (Click CLI) qui peut mal parser les options
    # booleennes dans un contexte PyInstaller.
    try:
        # Configurer Streamlit via ses options avant le lancement
        from streamlit import config as st_config
        from streamlit.web import bootstrap

        flag_options = {
            "global.developmentMode": False,
            "server.headless": True,
            "server.fileWatcherType": "none",
            "browser.gatherUsageStats": False,
            "browser.serverAddress": "localhost",
            "server.enableStaticServing": False,
            "client.showSidebarNavigation": False,
        }
        st_config._main_script_path = os.path.abspath(app_path)
        bootstrap.load_config_options(flag_options=flag_options)

        from streamlit.runtime.credentials import check_credentials
        check_credentials()

        bootstrap.run(
            main_script_path=os.path.abspath(app_path),
            is_hello=False,
            args=[],
            flag_options=flag_options,
        )
    except KeyboardInterrupt:
        print("\nDashboard arrete.")
    except Exception as e:
        print(f"ERREUR: {e}")
        import traceback
        traceback.print_exc()
        input("Appuyez sur Entree pour fermer...")
        sys.exit(1)


if __name__ == "__main__":
    main()
