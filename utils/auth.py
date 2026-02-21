"""
Authentification globale — Biz Dev Entourage
Mot de passe configuré une fois dans .streamlit/secrets.toml
"""

import streamlit as st
import os


# ---------------------------------------------------------------------------
# MOT DE PASSE
# ---------------------------------------------------------------------------
# Configurer dans .streamlit/secrets.toml :
#   app_password = "votre_mot_de_passe"
# Ou dans le fichier .env :
#   APP_PASSWORD=votre_mot_de_passe

def _get_password() -> str:
    try:
        return st.secrets["app_password"]
    except Exception:
        return os.getenv("APP_PASSWORD", "entourage2024")


# ---------------------------------------------------------------------------
# LOGIN FORM (style Entourage)
# ---------------------------------------------------------------------------

LOGIN_HTML = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;700;800&family=Playfair+Display:ital@0;1&display=swap');
    .login-wrap {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 60px 20px 40px;
        font-family: 'Manrope', sans-serif;
    }
    .login-logo-bar {
        width: 100%;
        max-width: 440px;
        background: #000;
        border-bottom: 3px solid #FFD700;
        padding: 22px 32px;
        border-radius: 8px 8px 0 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .login-brand {
        color: #fff;
        font-weight: 800;
        font-size: 15pt;
        letter-spacing: 1px;
    }
    .login-brand span {
        color: #FFD700;
    }
    .login-subtitle {
        color: #aaa;
        font-size: 9pt;
        font-weight: 400;
        letter-spacing: 0.5px;
    }
    .login-card {
        width: 100%;
        max-width: 440px;
        background: #fff;
        border: 1px solid #e0e0e0;
        border-top: none;
        border-radius: 0 0 8px 8px;
        padding: 32px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.10);
    }
    .login-title {
        font-family: 'Playfair Display', serif;
        font-size: 20pt;
        color: #000;
        margin-bottom: 6px;
    }
    .login-caption {
        color: #888;
        font-size: 9pt;
        margin-bottom: 24px;
    }
</style>
<div class="login-wrap">
    <div class="login-logo-bar">
        <div class="login-brand">BIZ DEV <span>ENTOURAGE</span></div>
        <div class="login-subtitle">ESPACE PRIVÉ</div>
    </div>
    <div class="login-card">
        <div class="login-title">Accès sécurisé</div>
        <div class="login-caption">Entrez votre mot de passe pour accéder à l'application.</div>
    </div>
</div>
"""


def check_password() -> bool:
    """
    Vérifie l'authentification. Retourne True si connecté.
    À appeler en haut de chaque page : if not check_password(): st.stop()
    """
    if st.session_state.get("authenticated"):
        return True

    correct_password = _get_password()

    # Centrer le formulaire
    st.markdown(LOGIN_HTML, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd = st.text_input(
            "Mot de passe",
            type="password",
            placeholder="••••••••",
            label_visibility="collapsed"
        )
        if st.button("→ Accéder", type="primary", use_container_width=True):
            if pwd == correct_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")

    st.stop()
    return False
