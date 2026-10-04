"""
Logo Entourage par défaut — logo_entourage.png à la racine du projet.
Évite d'avoir à uploader le logo à la main dans chaque rubrique.
"""

import base64
from pathlib import Path

import streamlit as st

LOGO_PATH = Path(__file__).resolve().parent.parent / "logo_entourage.png"


@st.cache_resource
def load_default_logo_b64() -> str | None:
    """Logo du projet en base64 (pleine résolution), ou None s'il est absent."""
    if LOGO_PATH.exists():
        return base64.b64encode(LOGO_PATH.read_bytes()).decode()
    return None
