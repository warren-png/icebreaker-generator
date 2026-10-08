"""
UI globale — injection de styles Entourage sur toutes les pages.
N'altère AUCUNE fonction métier — uniquement présentation.

Le gros du thème (police, couleurs, rayons, sidebar sombre) est défini
nativement dans .streamlit/config.toml. Ce CSS ajoute la finition :
cartes, onglets segmentés, navigation, boutons, états de focus.
"""

import streamlit as st


_GLOBAL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Playfair+Display:wght@400;700&display=swap');

    :root {
        --ent-black: #0A0A0A;
        --ent-gold: #FFD700;
        --ent-gold-deep: #E0B800;
        --ent-gold-soft: #FFF8D6;
        --ent-bg: #F6F6F3;
        --ent-surface: #FFFFFF;
        --ent-border: #E4E4E0;
        --ent-border-strong: #D4D4CE;
        --ent-text: #18181B;
        --ent-muted: #71717A;
        --ent-shadow-sm: 0 1px 2px rgba(16, 16, 16, 0.04);
        --ent-shadow-md: 0 1px 2px rgba(16, 16, 16, 0.04), 0 6px 20px rgba(16, 16, 16, 0.05);
        --ent-shadow-lg: 0 2px 4px rgba(16, 16, 16, 0.05), 0 14px 36px rgba(16, 16, 16, 0.10);
        --ent-radius: 12px;
        --ent-ease: cubic-bezier(.2, .7, .2, 1);
    }

    /* ========================================
       BASE
       ======================================== */
    html, body, .stApp, [data-testid="stMarkdownContainer"],
    input, textarea, button, select {
        font-family: 'Manrope', sans-serif;
        -webkit-font-smoothing: antialiased;
    }

    .stApp {
        background:
            radial-gradient(1200px 400px at 80% -120px, rgba(255, 215, 0, 0.07), transparent 70%),
            var(--ent-bg);
    }

    [data-testid="stHeader"] {
        background: transparent !important;
        backdrop-filter: none !important;
    }
    [data-testid="stDecoration"] { display: none !important; }

    .block-container,
    [data-testid="stMainBlockContainer"] {
        padding-top: 1.6rem !important;
        padding-bottom: 3rem !important;
        max-width: 1100px !important;
    }

    ::selection { background: rgba(255, 215, 0, 0.35); }

    /* Espacement vertical plus serré entre les éléments */
    [data-testid="stMain"] [data-testid="stVerticalBlock"] { gap: 0.7rem; }
    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] { gap: 0.5rem; }

    /* ========================================
       TITRES
       ======================================== */
    [data-testid="stMain"] h1 {
        font-family: 'Manrope', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.035em !important;
        line-height: 1.15 !important;
        color: var(--ent-black) !important;
        padding: 0 0 0.35rem 0 !important;
        margin: 0 !important;
    }
    [data-testid="stMain"] h1::after { display: none; }

    [data-testid="stMain"] h2 {
        letter-spacing: -0.025em !important;
        color: var(--ent-black) !important;
        padding-top: 0.6rem !important;
    }

    [data-testid="stMain"] h3 {
        letter-spacing: -0.015em !important;
        color: var(--ent-black) !important;
        padding-top: 0.6rem !important;
        padding-bottom: 0.2rem !important;
    }

    [data-testid="stMain"] h4,
    [data-testid="stMain"] h5 {
        letter-spacing: -0.01em !important;
        color: var(--ent-black) !important;
    }

    /* Ancres "#" des titres : discrètes */
    [data-testid="stHeaderActionElements"] { opacity: 0.35; }

    [data-testid="stCaptionContainer"], .stCaption {
        color: var(--ent-muted) !important;
        font-size: 0.86rem !important;
        line-height: 1.55 !important;
    }

    [data-testid="stMain"] p { line-height: 1.6; }

    [data-testid="stMain"] a {
        text-decoration-color: rgba(224, 184, 0, 0.6);
        text-underline-offset: 3px;
    }

    /* Code inline */
    [data-testid="stMarkdownContainer"] code {
        border-radius: 6px;
        padding: 0.1em 0.4em;
        font-size: 0.85em;
    }

    /* ========================================
       DIVIDERS
       ======================================== */
    [data-testid="stMain"] hr {
        margin: 1rem 0 !important;
        border: none !important;
        height: 1px !important;
        background: var(--ent-border) !important;
    }

    /* ========================================
       BOUTONS
       ======================================== */
    .stButton > button,
    .stDownloadButton > button,
    .stFormSubmitButton > button,
    .stLinkButton > a {
        font-weight: 700 !important;
        font-size: 0.9rem !important;
        letter-spacing: 0.005em;
        min-height: 2.35rem;
        padding: 0.4rem 1rem !important;
        transition: background .18s var(--ent-ease), border-color .18s var(--ent-ease),
                    box-shadow .18s var(--ent-ease), transform .18s var(--ent-ease),
                    color .18s var(--ent-ease) !important;
    }

    /* Primaire — noir, accent or */
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button[kind="primaryFormSubmit"],
    .stDownloadButton > button {
        background: var(--ent-black) !important;
        color: #FFFFFF !important;
        border: 1px solid var(--ent-black) !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.12), inset 0 1px 0 rgba(255,255,255,0.08);
    }
    .stButton > button[kind="primary"] p,
    .stDownloadButton > button p { color: inherit !important; }
    .stButton > button[kind="primary"]:hover,
    .stFormSubmitButton > button[kind="primaryFormSubmit"]:hover,
    .stDownloadButton > button:hover {
        background: #1C1C1F !important;
        color: var(--ent-gold) !important;
        border-color: #1C1C1F !important;
        transform: translateY(-1px);
        box-shadow: 0 0 0 3px rgba(255, 215, 0, 0.28), 0 8px 20px rgba(0,0,0,0.16);
    }
    .stButton > button:active,
    .stDownloadButton > button:active {
        transform: translateY(0) scale(0.99);
    }

    /* Secondaire — surface blanche */
    .stButton > button[kind="secondary"] {
        background: var(--ent-surface) !important;
        color: var(--ent-text) !important;
        border: 1px solid var(--ent-border) !important;
        box-shadow: var(--ent-shadow-sm);
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: var(--ent-border-strong) !important;
        background: #FCFCFA !important;
        color: var(--ent-black) !important;
        box-shadow: var(--ent-shadow-md);
        transform: translateY(-1px);
    }

    /* Tertiaire — discret (actions secondaires, boutons icône) */
    .stButton > button[kind="tertiary"],
    .stDownloadButton > button[kind="tertiary"],
    [data-testid="stPopover"] button[kind="tertiary"],
    .stLinkButton > a[kind="tertiary"] {
        background: transparent !important;
        color: #3F3F46 !important;
        border: none !important;
        box-shadow: none !important;
        min-height: 2.1rem;
        padding: 0.3rem 0.6rem !important;
    }
    .stButton > button[kind="tertiary"]:hover,
    .stDownloadButton > button[kind="tertiary"]:hover,
    [data-testid="stPopover"] button[kind="tertiary"]:hover,
    .stLinkButton > a[kind="tertiary"]:hover {
        background: rgba(0, 0, 0, 0.05) !important;
        color: var(--ent-black) !important;
        transform: none;
    }

    .stButton > button:focus-visible,
    .stDownloadButton > button:focus-visible {
        outline: none !important;
        box-shadow: 0 0 0 3px rgba(255, 215, 0, 0.45) !important;
    }

    .stButton > button:disabled,
    .stDownloadButton > button:disabled {
        opacity: 0.45;
        transform: none !important;
        box-shadow: none !important;
    }

    /* ========================================
       CHAMPS DE SAISIE
       ======================================== */
    [data-testid="stMain"] [data-baseweb="input"],
    [data-testid="stMain"] [data-baseweb="textarea"],
    [data-testid="stMain"] [data-baseweb="select"] > div {
        background: var(--ent-surface) !important;
        box-shadow: var(--ent-shadow-sm);
        transition: border-color .15s var(--ent-ease), box-shadow .15s var(--ent-ease) !important;
    }
    [data-testid="stMain"] [data-baseweb="input"]:hover,
    [data-testid="stMain"] [data-baseweb="textarea"]:hover,
    [data-testid="stMain"] [data-baseweb="select"] > div:hover {
        border-color: var(--ent-border-strong) !important;
    }
    [data-baseweb="input"]:focus-within,
    [data-baseweb="textarea"]:focus-within,
    [data-baseweb="select"] > div:focus-within {
        border-color: var(--ent-gold-deep) !important;
        box-shadow: 0 0 0 3px rgba(255, 215, 0, 0.22) !important;
    }
    [data-testid="stMain"] textarea { line-height: 1.55 !important; }
    [data-testid="stMain"] input::placeholder,
    [data-testid="stMain"] textarea::placeholder {
        color: #A1A1AA !important;
        opacity: 1;
    }

    /* Labels */
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] label {
        font-weight: 650 !important;
        font-size: 0.86rem !important;
        color: #3F3F46 !important;
    }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #D4D4D8 !important;
    }

    /* ========================================
       FILE UPLOADER
       ======================================== */
    [data-testid="stFileUploaderDropzone"] {
        border: 1.5px dashed var(--ent-border-strong) !important;
        background: var(--ent-surface) !important;
        border-radius: var(--ent-radius) !important;
        transition: border-color .15s var(--ent-ease), background .15s var(--ent-ease) !important;
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        border-color: var(--ent-gold-deep) !important;
        background: #FFFDF3 !important;
    }
    [data-testid="stFileUploaderDropzone"] button {
        font-weight: 700 !important;
    }
    [data-testid="stFileUploaderFile"] {
        border-radius: 10px;
    }

    /* ========================================
       CARTES — expanders, containers, formulaires
       ======================================== */
    [data-testid="stMain"] [data-testid="stExpander"] details {
        background: var(--ent-surface) !important;
        border: 1px solid var(--ent-border) !important;
        border-radius: var(--ent-radius) !important;
        box-shadow: var(--ent-shadow-sm);
        overflow: hidden;
        transition: box-shadow .18s var(--ent-ease), border-color .18s var(--ent-ease);
    }
    [data-testid="stMain"] [data-testid="stExpander"] details:hover {
        border-color: var(--ent-border-strong) !important;
        box-shadow: var(--ent-shadow-md);
    }
    [data-testid="stExpander"] summary {
        font-weight: 700 !important;
        padding-top: 0.6rem !important;
        padding-bottom: 0.6rem !important;
    }
    [data-testid="stExpander"] summary p { font-weight: 700 !important; }
    [data-testid="stExpander"] details[open] > summary {
        border-bottom: 1px solid var(--ent-border);
    }

    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stMain"] [data-testid="stForm"] {
        background: var(--ent-surface);
        border-color: var(--ent-border) !important;
        border-radius: var(--ent-radius) !important;
        box-shadow: var(--ent-shadow-sm);
        transition: box-shadow .18s var(--ent-ease), border-color .18s var(--ent-ease);
    }
    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: var(--ent-border-strong) !important;
        box-shadow: var(--ent-shadow-md);
    }

    /* ========================================
       ALERTES
       ======================================== */
    [data-testid="stAlertContainer"] {
        border-radius: var(--ent-radius) !important;
        border: 1px solid rgba(0,0,0,0.05) !important;
        padding: 0.8rem 1rem !important;
    }
    [data-testid="stAlertContainer"] p {
        font-size: 0.9rem;
        line-height: 1.5;
    }

    /* ========================================
       ONGLETS — contrôle segmenté
       ======================================== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px !important;
        background: #ECECE7 !important;
        padding: 4px !important;
        border-radius: 12px !important;
        border: none !important;
        width: fit-content;
        max-width: 100%;
        margin-bottom: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: auto !important;
        padding: 8px 16px !important;
        border-radius: 9px !important;
        border: none !important;
        background: transparent !important;
        color: #52525B !important;
        transition: background .15s var(--ent-ease), color .15s var(--ent-ease), box-shadow .15s var(--ent-ease) !important;
    }
    .stTabs [data-baseweb="tab"] p {
        font-weight: 650 !important;
        font-size: 0.88rem !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--ent-black) !important;
        background: rgba(255,255,255,0.55) !important;
    }
    .stTabs [aria-selected="true"] {
        background: var(--ent-surface) !important;
        color: var(--ent-black) !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06), 0 2px 8px rgba(0,0,0,0.06) !important;
        border-bottom: none !important;
    }
    .stTabs [aria-selected="true"] p { font-weight: 750 !important; }
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }
    .stTabs [data-baseweb="tab-panel"] { padding-top: 1rem !important; }

    /* ========================================
       RADIOS — pastilles
       ======================================== */
    [data-testid="stMain"] .stRadio [role="radiogroup"] {
        gap: 8px !important;
    }
    [data-testid="stMain"] .stRadio [role="radiogroup"] > label {
        background: var(--ent-surface) !important;
        padding: 7px 14px 7px 10px !important;
        border-radius: 10px !important;
        border: 1px solid var(--ent-border) !important;
        box-shadow: var(--ent-shadow-sm);
        transition: border-color .15s var(--ent-ease), background .15s var(--ent-ease), box-shadow .15s var(--ent-ease) !important;
        margin: 0 !important;
    }
    [data-testid="stMain"] .stRadio [role="radiogroup"] > label:hover {
        border-color: var(--ent-border-strong) !important;
    }
    [data-testid="stMain"] .stRadio [role="radiogroup"] > label:has(input:checked) {
        border-color: var(--ent-black) !important;
        background: var(--ent-gold-soft) !important;
        box-shadow: 0 0 0 1px var(--ent-black);
    }

    /* ========================================
       SLIDER / PROGRESS
       ======================================== */
    .stSlider [data-baseweb="slider"] [role="slider"] {
        background: var(--ent-black) !important;
        border: 3px solid var(--ent-gold) !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.18) !important;
    }
    [data-testid="stProgress"] [role="progressbar"] > div {
        border-radius: 999px !important;
        overflow: hidden;
    }
    [data-testid="stProgress"] [role="progressbar"] > div > div > div {
        background: linear-gradient(90deg, var(--ent-gold-deep), var(--ent-gold)) !important;
    }

    /* ========================================
       METRICS
       ======================================== */
    [data-testid="stMetric"] {
        background: var(--ent-surface);
        border: 1px solid var(--ent-border);
        border-radius: var(--ent-radius);
        padding: 0.8rem 1rem;
        box-shadow: var(--ent-shadow-sm);
    }
    [data-testid="stMetricValue"] {
        font-weight: 800 !important;
        letter-spacing: -0.02em;
    }

    /* ========================================
       CODE / JSON / TABLES
       ======================================== */
    [data-testid="stCode"] pre,
    .stCodeBlock pre {
        border-radius: 10px !important;
        border: 1px solid var(--ent-border);
    }
    [data-testid="stJson"] {
        border-radius: 10px;
        border: 1px solid var(--ent-border);
        background: var(--ent-surface);
        padding: 0.5rem;
    }
    .stDataFrame, [data-testid="stDataFrame"] {
        border-radius: 10px !important;
        overflow: hidden !important;
    }
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] table {
        border-collapse: separate;
        border-spacing: 0;
        border: 1px solid var(--ent-border);
        border-radius: 10px;
        overflow: hidden;
        background: var(--ent-surface);
    }

    /* Aperçus de documents (iframes HTML générés) */
    [data-testid="stMain"] iframe {
        border-radius: var(--ent-radius);
    }

    /* Status / toast */
    [data-testid="stStatusWidget"],
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        border-radius: var(--ent-radius);
    }
    [data-testid="stToast"] {
        border-radius: var(--ent-radius) !important;
        box-shadow: var(--ent-shadow-lg) !important;
    }

    /* ========================================
       SIDEBAR — noir Entourage
       ======================================== */
    [data-testid="stSidebar"] {
        border-right: 1px solid #1E1E22 !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        background:
            radial-gradient(420px 220px at 0% 0%, rgba(255, 215, 0, 0.07), transparent 70%),
            #0B0B0C;
    }

    /* Marque en tête de sidebar */
    [data-testid="stSidebarHeader"] {
        align-items: center;
        padding-top: 1.2rem !important;
        padding-bottom: 0.4rem !important;
    }
    [data-testid="stLogoSpacer"] {
        display: flex;
        align-items: center;
        gap: 6px;
    }
    [data-testid="stLogoSpacer"]::before {
        content: 'BIZ DEV';
        color: #FFFFFF;
        font-weight: 800;
        font-size: 0.92rem;
        letter-spacing: 0.12em;
        white-space: nowrap;
    }
    [data-testid="stLogoSpacer"]::after {
        content: 'ENTOURAGE';
        color: var(--ent-gold);
        font-weight: 800;
        font-size: 0.92rem;
        letter-spacing: 0.12em;
        white-space: nowrap;
    }

    /* Navigation entre rubriques */
    [data-testid="stSidebarNav"] {
        padding-top: 0.4rem;
    }
    [data-testid="stSidebarNavItems"] {
        padding: 0 0.75rem !important;
        gap: 2px;
        display: flex;
        flex-direction: column;
    }
    [data-testid="stSidebarNavLink"] {
        border-radius: 9px !important;
        padding: 0.5rem 0.75rem !important;
        transition: background .15s var(--ent-ease), color .15s var(--ent-ease) !important;
        position: relative;
    }
    [data-testid="stSidebarNavLink"] span,
    [data-testid="stSidebarNavLink"] p {
        color: #A1A1AA !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        transition: color .15s var(--ent-ease);
    }
    [data-testid="stSidebarNavLink"]:hover {
        background: rgba(255, 255, 255, 0.05) !important;
    }
    [data-testid="stSidebarNavLink"]:hover span,
    [data-testid="stSidebarNavLink"]:hover p {
        color: #FFFFFF !important;
    }
    [data-testid="stSidebarNavLink"][aria-current="page"] {
        background: rgba(255, 215, 0, 0.10) !important;
    }
    [data-testid="stSidebarNavLink"][aria-current="page"]::before {
        content: '';
        position: absolute;
        left: -0.75rem;
        top: 22%;
        bottom: 22%;
        width: 3px;
        border-radius: 0 3px 3px 0;
        background: var(--ent-gold);
    }
    [data-testid="stSidebarNavLink"][aria-current="page"] span,
    [data-testid="stSidebarNavLink"][aria-current="page"] p {
        color: var(--ent-gold) !important;
        font-weight: 750 !important;
    }

    /* Icônes de rubrique (Material Symbols, déjà chargée par Streamlit) */
    [data-testid="stSidebarNavLink"] > span::before {
        font-family: 'Material Symbols Rounded';
        font-weight: 400;
        font-size: 1.15rem;
        line-height: 1;
        margin-right: 0.65rem;
        vertical-align: -0.2em;
        font-feature-settings: 'liga';
        -webkit-font-feature-settings: 'liga';
        display: inline-block;
        flex: none;
        width: 1.2rem;
        overflow: hidden;
    }
    [data-testid="stSidebarNavLink"] > span {
        display: flex !important;
        align-items: center;
        width: 100%;
    }
    [data-testid="stSidebarNavLink"] > span::after { display: none !important; }
    [data-testid="stSidebarNavLink"] > span > [data-testid="stMarkdownContainer"] {
        flex: 1 1 auto;
        min-width: 0;
        max-width: none;
    }
    [data-testid="stSidebarNavLink"] > span[label="app streamlit"]::before { content: 'work'; }
    [data-testid="stSidebarNavLink"] > span[label="Scorecard"]::before { content: 'assignment'; }
    [data-testid="stSidebarNavLink"] > span[label="Contrat"]::before { content: 'contract'; }
    [data-testid="stSidebarNavLink"] > span[label="Temoignage Client"]::before { content: 'format_quote'; }
    [data-testid="stSidebarNavLink"] > span[label="Dossier Candidature"]::before { content: 'folder_shared'; }
    [data-testid="stSidebarNavLink"] > span[label="Prise References"]::before { content: 'fact_check'; }
    [data-testid="stSidebarNavLink"] > span[label="Coach Prospection"]::before { content: 'record_voice_over'; }

    /* La page d'accueil (app_streamlit.py) s'affiche "app streamlit" : on la renomme "Mandats" */
    [data-testid="stSidebarNavLink"] > span[label="app streamlit"] [data-testid="stMarkdownContainer"] p {
        font-size: 0 !important;
    }
    [data-testid="stSidebarNavLink"] > span[label="app streamlit"] [data-testid="stMarkdownContainer"] p::after {
        content: 'Mandats';
        font-size: 0.9rem;
    }

    [data-testid="stSidebarNavSeparator"] {
        margin: 0.9rem 1.5rem 0.4rem !important;
    }
    [data-testid="stSidebarNavSeparator"] > div {
        border-color: #26262A !important;
    }

    /* Contenu de la sidebar */
    [data-testid="stSidebarUserContent"] {
        padding-top: 0.6rem !important;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #8B8B93 !important;
        text-transform: uppercase;
        letter-spacing: 0.12em !important;
        padding: 0.9rem 0 0.35rem 0 !important;
    }
    [data-testid="stSidebar"] h1::after { display: none; }
    [data-testid="stSidebar"] [data-testid="stHeaderActionElements"] { display: none; }

    [data-testid="stSidebar"] hr {
        margin: 1rem 0 !important;
        border: none !important;
        height: 1px !important;
        background: #232327 !important;
    }

    [data-testid="stSidebar"] [data-testid="stAlertContainer"] {
        padding: 0.45rem 0.7rem !important;
        border-radius: 9px !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
    }
    [data-testid="stSidebar"] [data-testid="stAlertContainer"] p {
        font-size: 0.82rem !important;
        font-weight: 600;
    }
    [data-testid="stSidebar"] [data-testid="stElementContainer"]:has([data-testid="stAlert"]) {
        margin-bottom: -0.55rem;
    }

    [data-testid="stSidebar"] [data-testid="stMetric"] {
        background: #141417;
        border: 1px solid #232327;
        box-shadow: none;
        padding: 0.6rem 0.85rem;
    }
    [data-testid="stSidebar"] [data-testid="stMetricLabel"] p {
        color: #8B8B93 !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-size: 1.35rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stElementContainer"]:has([data-testid="stMetric"]) {
        margin-bottom: -0.45rem;
    }

    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #8B8B93 !important;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        border: 1px solid #232327;
        border-radius: 10px;
        overflow: hidden;
        font-size: 0.8rem;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] th {
        background: #141417;
        color: #8B8B93;
        font-weight: 700;
        text-transform: uppercase;
        font-size: 0.68rem;
        letter-spacing: 0.08em;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] th,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] td {
        border: none !important;
        border-bottom: 1px solid #1E1E22 !important;
        padding: 0.45rem 0.65rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] tr:last-child td {
        border-bottom: none !important;
    }

    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        background: #141417 !important;
        border-color: #2E2E33 !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {
        border-color: var(--ent-gold) !important;
        background: #18170F !important;
    }
    [data-testid="stSidebar"] [data-testid="stImage"] img {
        border-radius: 10px;
    }

    [data-testid="stSidebar"] .stButton > button[kind="secondary"] {
        background: #141417 !important;
        color: #E4E4E7 !important;
        border-color: #2E2E33 !important;
        box-shadow: none;
    }
    [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
        border-color: var(--ent-gold) !important;
        color: var(--ent-gold) !important;
        background: #18170F !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: var(--ent-gold) !important;
        color: var(--ent-black) !important;
        border-color: var(--ent-gold) !important;
    }

    /* ========================================
       SCROLLBARS
       ======================================== */
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb {
        background: rgba(0,0,0,0.14);
        border-radius: 999px;
        border: 3px solid transparent;
        background-clip: content-box;
    }
    ::-webkit-scrollbar-thumb:hover { background-color: rgba(0,0,0,0.28); }
    [data-testid="stSidebar"] ::-webkit-scrollbar-thumb { background-color: rgba(255,255,255,0.12); }

    /* ========================================
       ENTRÉE EN DOUCEUR
       ======================================== */
    @keyframes entFadeUp {
        from { opacity: 0; transform: translateY(6px); }
        to   { opacity: 1; transform: none; }
    }
    [data-testid="stMainBlockContainer"] > div {
        animation: entFadeUp .35s var(--ent-ease) both;
    }

    /* ========================================
       MOBILE
       ======================================== */
    @media (max-width: 640px) {
        .block-container,
        [data-testid="stMainBlockContainer"] {
            padding-top: 1.6rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            width: 100%;
            overflow-x: auto;
        }
    }
</style>
"""


def inject_global_styles() -> None:
    """Injecte le CSS Entourage global. À appeler après st.set_page_config()."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
