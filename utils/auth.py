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


def _get_cookie_manager():
    """Une seule instance par session — stockée dans session_state.
    Ne PAS utiliser @st.cache_resource : CookieManager est un widget Streamlit."""
    if not _COOKIES_AVAILABLE:
        return None
    if "_entourage_cookie_mgr" not in st.session_state:
        try:
            st.session_state["_entourage_cookie_mgr"] = stx.CookieManager(key="entourage_auth_cm")
        except Exception:
            st.session_state["_entourage_cookie_mgr"] = None
    return st.session_state["_entourage_cookie_mgr"]


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
        padding: 64px 0 18px;
        font-family: 'Manrope', sans-serif;
    }
    /* Même largeur que la colonne centrale (st.columns([1, 2, 1])) qui porte le champ */
    .login-logo-bar, .login-card {
        width: calc((100% - 2rem) / 2);
        min-width: min(100%, 340px);
    }
    @media (max-width: 640px) {
        .login-logo-bar, .login-card { width: 100%; }
    }
    .login-logo-bar {
        background:
            radial-gradient(360px 160px at 100% 0%, rgba(255, 215, 0, 0.16), transparent 70%),
            linear-gradient(135deg, #0A0A0A 0%, #1a1a1d 100%);
        padding: 26px 32px;
        border-radius: 18px 18px 0 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .login-brand {
        color: #fff;
        font-weight: 800;
        font-size: 15pt;
        letter-spacing: 0.12em;
    }
    .login-brand span {
        color: #FFD700;
    }
    .login-subtitle {
        color: #A1A1AA;
        font-size: 8pt;
        font-weight: 700;
        letter-spacing: 0.14em;
        border: 1px solid #2E2E33;
        border-radius: 999px;
        padding: 4px 10px;
    }
    .login-card {
        background: #fff;
        border: 1px solid #E4E4E0;
        border-top: none;
        border-radius: 0 0 18px 18px;
        padding: 30px 32px 26px;
        box-shadow: 0 2px 4px rgba(16,16,16,0.04), 0 18px 48px rgba(16,16,16,0.10);
    }
    .login-title {
        font-family: 'Manrope', sans-serif;
        font-weight: 800;
        font-size: 1.6rem;
        color: #0A0A0A;
        margin-bottom: 6px;
        letter-spacing: -0.03em;
    }
    .login-caption {
        color: #71717A;
        font-size: 0.92rem;
        margin-bottom: 0;
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
    # (styles globaux injectés ici aussi : la page principale vérifie l'auth avant inject_global_styles)
    from utils.ui import inject_global_styles
    inject_global_styles()
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
