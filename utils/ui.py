"""
UI globale — injection de styles Entourage sur toutes les pages.
N'altère AUCUNE fonction métier — uniquement présentation.
"""

import streamlit as st


_GLOBAL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Playfair+Display:wght@400;700&display=swap');

    /* ========================================
       BASE — typo et fond
       ======================================== */
    html, body, [class*="css"], .stApp, .block-container {
        font-family: 'Manrope', sans-serif !important;
    }

    .block-container {
        padding-top: 2.2rem !important;
        padding-bottom: 4rem !important;
        max-width: 1280px !important;
    }

    /* ========================================
       TITRES — Playfair pour H1, Manrope bold pour le reste
       ======================================== */
    h1 {
        font-family: 'Playfair Display', serif !important;
        font-weight: 700 !important;
        color: #0A0A0A !important;
        letter-spacing: -0.5px !important;
        position: relative;
        padding-bottom: 14px;
        margin-bottom: 8px !important;
    }
    h1::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        width: 60px;
        height: 3px;
        background: #FFD700;
        border-radius: 2px;
    }

    h2, h3 {
        font-family: 'Manrope', sans-serif !important;
        font-weight: 800 !important;
        color: #0A0A0A !important;
        letter-spacing: -0.3px !important;
    }

    /* Captions plus douces */
    [data-testid="stCaptionContainer"], .stCaption {
        color: #6B6B6B !important;
        font-size: 0.9rem !important;
    }

    /* ========================================
       BOUTONS — noir avec accent or
       ======================================== */
    .stButton > button {
        font-family: 'Manrope', sans-serif !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        padding: 0.55rem 1.4rem !important;
        transition: all 0.15s ease !important;
        border: 2px solid transparent !important;
        letter-spacing: 0.2px !important;
    }

    .stButton > button[kind="primary"] {
        background: #0A0A0A !important;
        color: #FFD700 !important;
        border-color: #0A0A0A !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #FFD700 !important;
        color: #0A0A0A !important;
        border-color: #0A0A0A !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.18);
    }
    .stButton > button[kind="primary"]:active {
        transform: translateY(0);
    }

    .stButton > button[kind="secondary"] {
        background: #FFFFFF !important;
        color: #0A0A0A !important;
        border-color: #E2E2E2 !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: #FFFCF0 !important;
        border-color: #FFD700 !important;
        color: #0A0A0A !important;
    }

    /* Boutons download */
    .stDownloadButton > button {
        font-weight: 700 !important;
        border-radius: 8px !important;
        padding: 0.55rem 1.4rem !important;
        transition: all 0.15s ease !important;
        background: #0A0A0A !important;
        color: #FFD700 !important;
        border: 2px solid #0A0A0A !important;
    }
    .stDownloadButton > button:hover {
        background: #FFD700 !important;
        color: #0A0A0A !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.18);
    }

    /* ========================================
       INPUTS — focus or
       ======================================== */
    .stTextInput > div > div > input,
    .stTextArea textarea,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input {
        border-radius: 8px !important;
        border: 1.5px solid #E5E5E5 !important;
        font-family: 'Manrope', sans-serif !important;
        transition: all 0.15s ease !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea textarea:focus,
    .stNumberInput > div > div > input:focus,
    .stDateInput > div > div > input:focus {
        border-color: #FFD700 !important;
        box-shadow: 0 0 0 3px rgba(255, 215, 0, 0.15) !important;
        outline: none !important;
    }

    /* Labels */
    .stTextInput label, .stTextArea label, .stNumberInput label,
    .stDateInput label, .stSelectbox label, .stRadio label,
    .stFileUploader label, .stCheckbox label {
        font-weight: 600 !important;
        color: #1A1A1A !important;
        font-size: 0.92rem !important;
    }

    /* ========================================
       FILE UPLOADER — zone de drop améliorée
       ======================================== */
    [data-testid="stFileUploader"] section {
        border-radius: 10px !important;
        border: 2px dashed #D5D5D5 !important;
        background: #FAFAFA !important;
        transition: all 0.15s ease !important;
        padding: 18px !important;
    }
    [data-testid="stFileUploader"] section:hover {
        border-color: #FFD700 !important;
        background: #FFFCF0 !important;
    }
    [data-testid="stFileUploader"] section button {
        border-radius: 6px !important;
        font-weight: 600 !important;
    }

    /* ========================================
       SIDEBAR — fond légèrement teinté
       ======================================== */
    [data-testid="stSidebar"] {
        background-color: #FAFAFA !important;
        border-right: 1px solid #EEEEEE !important;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #0A0A0A !important;
    }
    [data-testid="stSidebar"] h1::after {
        display: none;
    }

    /* ========================================
       DIVIDERS — discret
       ======================================== */
    hr {
        margin: 1.6rem 0 !important;
        border: none !important;
        height: 1px !important;
        background: linear-gradient(to right, transparent, #E0E0E0, transparent) !important;
    }

    /* ========================================
       ALERTES — coins arrondis
       ======================================== */
    [data-baseweb="notification"],
    .stAlert {
        border-radius: 8px !important;
        border-left-width: 4px !important;
    }

    /* ========================================
       EXPANDERS — sobres
       ======================================== */
    [data-testid="stExpander"] {
        border-radius: 10px !important;
        border: 1px solid #EBEBEB !important;
        background: #FFFFFF !important;
    }
    [data-testid="stExpander"] summary {
        font-weight: 700 !important;
        font-size: 0.95rem !important;
    }
    [data-testid="stExpander"] summary:hover {
        color: #0A0A0A !important;
    }

    /* ========================================
       CONTAINERS BORDÉS — la liste de critères
       ======================================== */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 10px !important;
        border-color: #ECECEC !important;
        transition: all 0.15s ease;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #FFD700 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    /* ========================================
       SLIDERS — accent or
       ======================================== */
    .stSlider [data-baseweb="slider"] [role="slider"] {
        background: #0A0A0A !important;
        border: 2.5px solid #FFD700 !important;
    }

    /* ========================================
       RADIOS — pill style
       ======================================== */
    .stRadio [role="radiogroup"] {
        gap: 8px !important;
    }
    .stRadio [role="radiogroup"] label {
        background: #FFFFFF !important;
        padding: 8px 16px !important;
        border-radius: 8px !important;
        border: 1.5px solid #E5E5E5 !important;
        transition: all 0.15s ease !important;
        margin: 0 !important;
    }
    .stRadio [role="radiogroup"] label:hover {
        border-color: #FFD700 !important;
        background: #FFFCF0 !important;
    }

    /* ========================================
       CHECKBOX — accent or
       ======================================== */
    .stCheckbox [data-baseweb="checkbox"] [data-checked="true"] {
        background: #0A0A0A !important;
        border-color: #0A0A0A !important;
    }

    /* ========================================
       TABS — barre dorée sur l'onglet actif
       ======================================== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px !important;
        border-bottom: 1px solid #EEEEEE !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-weight: 600 !important;
        padding: 10px 18px !important;
    }
    .stTabs [aria-selected="true"] {
        color: #0A0A0A !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #FFD700 !important;
        height: 3px !important;
    }

    /* ========================================
       STATUS / SPINNER — ton sobre
       ======================================== */
    [data-testid="stStatusWidget"] {
        border-radius: 10px !important;
        border: 1px solid #EBEBEB !important;
    }

    /* ========================================
       DATAFRAME / TABLES
       ======================================== */
    .stDataFrame {
        border-radius: 8px !important;
        overflow: hidden !important;
    }

    /* Petit polish — scrollbars */
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: #F5F5F5; }
    ::-webkit-scrollbar-thumb { background: #CCCCCC; border-radius: 5px; }
    ::-webkit-scrollbar-thumb:hover { background: #999999; }
</style>
"""


def inject_global_styles() -> None:
    """Injecte le CSS Entourage global. À appeler après st.set_page_config()."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
