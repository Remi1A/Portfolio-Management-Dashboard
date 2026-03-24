"""Export des graphiques Plotly en images PNG pour insertion PDF."""

import io
import tempfile
from pathlib import Path


def fig_to_image_bytes(fig, width: int = 700, height: int = 400) -> bytes | None:
    """Convertit une figure Plotly en bytes PNG."""
    try:
        return fig.to_image(format="png", width=width, height=height, scale=2)
    except Exception:
        return None


def fig_to_temp_file(fig, width: int = 700, height: int = 400) -> str | None:
    """Sauvegarde une figure Plotly en fichier PNG temporaire. Retourne le chemin."""
    img_bytes = fig_to_image_bytes(fig, width, height)
    if img_bytes is None:
        return None
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.write(img_bytes)
    tmp.close()
    return tmp.name
