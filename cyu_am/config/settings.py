import os
import sys
from pathlib import Path

# Chemins
# En mode PyInstaller (.exe), __file__ pointe vers _MEIPASS (repertoire temporaire
# en lecture seule). La DB et les exports doivent etre a cote de l'executable.
if getattr(sys, "frozen", False):
    # Repertoire persistant = a cote du .exe (defini par launcher.py)
    _PERSISTENT_DIR = Path(os.environ.get("CYU_AM_DATA_DIR",
                                           str(Path(sys.executable).resolve().parent)))
    DB_PATH = _PERSISTENT_DIR / "data" / "cyu_am.db"
    EXPORTS_DIR = _PERSISTENT_DIR / "exports"
    # BASE_DIR pointe vers les fichiers bundled (pour CSS, etc.)
    BASE_DIR = Path(sys._MEIPASS) / "cyu_am"
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    DB_PATH = BASE_DIR / "data" / "cyu_am.db"
    EXPORTS_DIR = BASE_DIR / "exports"

# Devise de référence du portefeuille
BASE_CURRENCY = "EUR"

# Périodes de rolling par défaut
ROLLING_WINDOWS = {
    "30d": 30,
    "90d": 90,
    "252d": 252,
}

# Taux sans risque annualisé (approximation EUR, modifiable)
RISK_FREE_RATE = 0.03

# Cache TTL (secondes)
MARKET_DATA_TTL = 3600      # 1 heure
FX_DATA_TTL = 3600          # 1 heure

# VaR
VAR_CONFIDENCE = 0.95

# Plotly — palette dark mode
COLORS = {
    "bg": "#0E1117",
    "panel": "#1E2130",
    "accent": "#00D4AA",
    "accent2": "#4A9EFF",
    "positive": "#26A69A",
    "negative": "#EF5350",
    "text": "#FAFAFA",
    "text_secondary": "#8892A4",
}
