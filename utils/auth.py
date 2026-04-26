"""
Authentification globale — Biz Dev Entourage
Mot de passe configuré une fois dans .streamlit/secrets.toml
Persistance via cookie navigateur (jusqu'à 10 ans).
"""

import streamlit as st
import os
import hashlib
from datetime import datetime, timedelta

try:
    import extra_streamlit_components as stx
    _COOKIES_AVAILABLE = True
except ImportError:
    _COOKIES_AVAILABLE = False


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
COOKIE_NAME = "entourage_auth"
COOKIE_DAYS = 3650  # ~10 ans, expiration la plus longue raisonnable


def _get_password() -> str:
    try:
        return st.secrets["app_password"]
    except Exception:
        return os.getenv("APP_PASSWORD", "entourage2024")


def _make_token(password: str) -> str:
    """Token déterministe lié au mot de passe courant.
    Si le mot de passe change, les anciens cookies deviennent invalides."""
    return hashlib.sha256(f"entourage_v1_{password}".encode()).hexdigest()


@st.cache_resource
def _get_cookie_manager():
    """Une seule instance par session pour éviter les doublons d'iframe."""
    if not _COOKIES_AVAILABLE:
        return None
    try:
        return stx.CookieManager(key="entourage_auth_cm")
    except Exception:
        return None


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
        padding: 50px 20px 30px;
        font-family: 'Manrope', sans-serif;
    }
    .login-logo-bar {
        width: 100%;
        max-width: 460px;
        background: linear-gradient(135deg, #0A0A0A 0%, #1f1f1f 100%);
        border-bottom: 3px solid #FFD700;
        padding: 24px 32px;
        border-radius: 12px 12px 0 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .login-brand {
        color: #fff;
        font-weight: 800;
        font-size: 16pt;
        letter-spacing: 1.2px;
    }
    .login-brand span {
        color: #FFD700;
    }
    .login-subtitle {
        color: #aaa;
        font-size: 8.5pt;
        font-weight: 500;
        letter-spacing: 1px;
    }
    .login-card {
        width: 100%;
        max-width: 460px;
        background: #fff;
        border: 1px solid #ECECEC;
        border-top: none;
        border-radius: 0 0 12px 12px;
        padding: 32px;
        box-shadow: 0 12px 40px rgba(0,0,0,0.08);
    }
    .login-title {
        font-family: 'Playfair Display', serif;
        font-size: 22pt;
        color: #0A0A0A;
        margin-bottom: 6px;
        letter-spacing: -0.5px;
    }
    .login-caption {
        color: #777;
        font-size: 9.5pt;
        margin-bottom: 22px;
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
    # Déjà authentifié dans cette session
    if st.session_state.get("authenticated"):
        return True

    correct_password = _get_password()
    expected_token = _make_token(correct_password)

    # Auto-login via cookie si disponible
    cookie_mgr = _get_cookie_manager()
    if cookie_mgr is not None:
        try:
            saved_token = cookie_mgr.get(COOKIE_NAME)
            if saved_token and saved_token == expected_token:
                st.session_state.authenticated = True
                return True
        except Exception:
            pass

    # Affichage du formulaire de connexion
    st.markdown(LOGIN_HTML, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd = st.text_input(
            "Mot de passe",
            type="password",
            placeholder="••••••••",
            label_visibility="collapsed",
        )
        remember = st.checkbox(
            "Se souvenir de moi sur ce navigateur",
            value=True,
            help="Garde ta session active pendant 10 ans sur ce navigateur.",
        )
        if st.button("→ Accéder", type="primary", use_container_width=True):
            if pwd == correct_password:
                st.session_state.authenticated = True
                if remember and cookie_mgr is not None:
                    try:
                        cookie_mgr.set(
                            COOKIE_NAME,
                            expected_token,
                            expires_at=datetime.now() + timedelta(days=COOKIE_DAYS),
                            key="entourage_auth_set",
                        )
                    except Exception:
                        pass
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")

    st.stop()
    return False


def logout() -> None:
    """Déconnecte et supprime le cookie."""
    st.session_state.authenticated = False
    cookie_mgr = _get_cookie_manager()
    if cookie_mgr is not None:
        try:
            cookie_mgr.delete(COOKIE_NAME, key="entourage_auth_del")
        except Exception:
            pass
