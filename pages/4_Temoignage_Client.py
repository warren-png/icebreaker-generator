import streamlit as st
import anthropic
import base64
import os
import io
from pathlib import Path
from dotenv import load_dotenv
from utils.auth import check_password

load_dotenv()

st.set_page_config(
    page_title="Témoignage Client | Entourage Recrutement",
    page_icon="💬",
    layout="wide"
)

# — Authentification —
if not check_password():
    st.stop()

# ---------------------------------------------------------------------------
# COMMERCIAUX
# ---------------------------------------------------------------------------

COMMERCIAUX = {
    "Warren": {
        "linkedin": "https://www.linkedin.com/in/warren-elbaz/",
        "tel": "06 50 60 22 61"
    },
    "Helder": {
        "linkedin": "https://www.linkedin.com/in/helder-alturas-48010463/",
        "tel": "06 22 30 96 11"
    }
}

ENTOURAGE_URL = "https://entouragerecrutement.com/"

# ---------------------------------------------------------------------------
# LOGO ENTOURAGE (même logique que Scorecard)
# ---------------------------------------------------------------------------

@st.cache_resource
def load_logo_base64_cached() -> str | None:
    candidates = [
        Path(__file__).parent.parent / "logo_entourage.png",
        Path(__file__).parent / "logo_entourage.png",
        Path(os.getcwd()) / "logo_entourage.png",
    ]
    for path in candidates:
        if path.exists():
            try:
                from PIL import Image
                img = Image.open(path)
                img.thumbnail((600, 120), Image.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                return base64.b64encode(buf.getvalue()).decode()
            except ImportError:
                with open(path, "rb") as f:
                    return base64.b64encode(f.read()).decode()
    return None


def get_logo_base64() -> str | None:
    if st.session_state.get("logo_b64"):
        return st.session_state.logo_b64
    cached = load_logo_base64_cached()
    if cached:
        st.session_state.logo_b64 = cached
    return cached


# ---------------------------------------------------------------------------
# TEMPLATE HTML — TÉMOIGNAGE CLIENT A4
# ---------------------------------------------------------------------------

TEMOIGNAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Témoignage Client — {{NOM_CONTACT}}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;700&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        body {
            background-color: #555;
            font-family: 'Manrope', sans-serif;
            display: flex;
            justify-content: center;
            padding: 40px 0;
            color: #555555;
        }
        .page {
            width: 210mm;
            height: 297mm;
            background: #FFFFFF;
            box-shadow: 0 0 20px rgba(0,0,0,0.5);
            position: relative;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        @media print {
            @page { size: A4 portrait; margin: 0; }
            body { background: none; padding: 0; }
            .page { box-shadow: none; margin: 0; }
        }
        /* --- HEADER --- */
        .header {
            height: 40mm;
            background: #000000;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 15mm;
            border-bottom: 3mm solid #FFD700;
            flex-shrink: 0;
        }
        .brand-logo {
            max-height: 18mm;
            max-width: 100mm;
            object-fit: contain;
        }
        .doc-type {
            color: #FFD700;
            font-family: 'Manrope', sans-serif;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 9pt;
            letter-spacing: 2px;
            border: 1px solid #FFD700;
            padding: 5px 15px;
        }
        /* --- CONTENU --- */
        .main-content {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        /* COLONNE GAUCHE (SIDEBAR) */
        .sidebar {
            width: 55mm;
            background-color: #F8F9FA;
            padding: 10mm 5mm 10mm 8mm;
            border-right: 1px solid #DDDDDD;
            display: flex;
            flex-direction: column;
            gap: 8mm;
            flex-shrink: 0;
        }
        .sidebar-block h3 {
            font-family: 'Playfair Display', serif;
            color: #000000;
            font-size: 13pt;
            margin-bottom: 4mm;
            border-bottom: 2px solid #FFD700;
            padding-bottom: 2mm;
            display: inline-block;
        }
        .profile-card {
            text-align: center;
            margin-bottom: 5mm;
        }
        .profile-img {
            width: 40mm;
            height: 40mm;
            border-radius: 50%;
            background-color: #FFF;
            margin: 0 auto 5mm auto;
            border: 2px solid #FFD700;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .profile-img img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        .profile-img-initials {
            font-family: 'Playfair Display', serif;
            font-size: 20pt;
            font-weight: 700;
            color: #FFD700;
            background: #000;
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .profile-name {
            font-weight: 800;
            color: #000000;
            font-size: 10pt;
            margin-bottom: 2px;
        }
        .profile-role {
            font-size: 8pt;
            color: #555;
            font-style: italic;
        }
        .key-info {
            list-style: none;
            font-size: 8.5pt;
        }
        .key-info li {
            margin-bottom: 3mm;
            display: flex;
            align-items: flex-start;
        }
        .key-info i {
            color: #000;
            margin-right: 3mm;
            font-size: 9pt;
            margin-top: 1px;
            flex-shrink: 0;
        }
        /* COLONNE DROITE */
        .content-body {
            flex: 1;
            padding: 10mm 12mm;
            overflow: hidden;
        }
        .headline {
            font-family: 'Playfair Display', serif;
            font-size: 22pt;
            color: #000000;
            line-height: 1.2;
            margin-bottom: 7mm;
        }
        .headline span {
            color: #555;
            border-bottom: 4px solid #FFD700;
        }
        .qa-block {
            margin-bottom: 5mm;
        }
        .question {
            font-family: 'Playfair Display', serif;
            color: #000000;
            font-weight: 700;
            font-size: 10.5pt;
            margin-bottom: 2.5mm;
            display: flex;
            align-items: flex-start;
        }
        .question::before {
            content: 'Q.';
            color: #FFD700;
            font-weight: 900;
            margin-right: 3mm;
            font-family: 'Manrope', sans-serif;
            flex-shrink: 0;
        }
        .answer {
            font-size: 9pt;
            line-height: 1.5;
            color: #555555;
            text-align: justify;
            padding-left: 8mm;
            border-left: 1px solid #DDD;
        }
        /* Citation */
        .highlight-box {
            background-color: #000000;
            color: #FFFFFF;
            padding: 5mm 8mm;
            margin: 6mm 0;
            border-left: 4px solid #FFD700;
            border-radius: 0 10px 10px 0;
        }
        .highlight-text {
            font-family: 'Playfair Display', serif;
            font-style: italic;
            font-size: 11pt;
            text-align: center;
            line-height: 1.4;
            position: relative;
        }
        .highlight-text::before {
            content: "\201C";
            font-family: serif;
            font-size: 28pt;
            color: #FFD700;
            vertical-align: -10px;
            margin-right: 4px;
            line-height: 0;
        }
        .highlight-text::after {
            content: "\201D";
            font-family: serif;
            font-size: 28pt;
            color: #FFD700;
            vertical-align: -18px;
            margin-left: 4px;
            line-height: 0;
        }
        /* --- FOOTER --- */
        .footer {
            height: 15mm;
            background: #F8F9FA;
            border-top: 1px solid #DDDDDD;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 9pt;
            color: #555;
            flex-shrink: 0;
        }
        .footer a {
            color: #000;
            text-decoration: none;
            font-weight: 700;
            margin: 0 5px;
            border-bottom: 1.5px solid #FFD700;
        }
    </style>
</head>
<body>
    <div class="page">
        <!-- HEADER -->
        <header class="header">
            {{LOGO_ENTOURAGE}}
            <div class="doc-type">Témoignage Client</div>
        </header>

        <!-- MAIN CONTENT -->
        <div class="main-content">

            <!-- SIDEBAR -->
            <aside class="sidebar">
                <div class="profile-card">
                    <div class="profile-img">
                        {{LOGO_CLIENT}}
                    </div>
                    <div class="profile-name">{{NOM_CONTACT}}</div>
                    <div class="profile-role">{{ROLE_CONTACT}}</div>
                </div>

                <div class="sidebar-block">
                    <h3>Le Mandat</h3>
                    <ul class="key-info">
                        <li>
                            <i class="fa-solid fa-briefcase"></i>
                            <div><strong>Poste :</strong><br>{{POSTE_RECRUTE}}</div>
                        </li>
                        <li>
                            <i class="fa-solid fa-industry"></i>
                            <div><strong>Secteur :</strong><br>{{SECTEUR}}</div>
                        </li>
                        <li>
                            <i class="fa-solid fa-location-dot"></i>
                            <div><strong>Contexte :</strong><br>{{CONTEXTE}}</div>
                        </li>
                    </ul>
                </div>

                <div class="sidebar-block">
                    <h3>Points Clés</h3>
                    <ul class="key-info">
                        <li><i class="fa-solid fa-check" style="color:#FFD700;"></i> {{POINT_CLE_1}}</li>
                        <li><i class="fa-solid fa-check" style="color:#FFD700;"></i> {{POINT_CLE_2}}</li>
                        <li><i class="fa-solid fa-check" style="color:#FFD700;"></i> {{POINT_CLE_3}}</li>
                    </ul>
                </div>
            </aside>

            <!-- CORPS DU TEXTE -->
            <div class="content-body">
                <h1 class="headline">{{HEADLINE_MAIN}} <span>{{HEADLINE_HIGHLIGHT}}</span>.</h1>

                <div class="qa-block">
                    <div class="question">{{QUESTION_1}}</div>
                    <div class="answer">{{REPONSE_1}}</div>
                </div>

                <div class="qa-block">
                    <div class="question">{{QUESTION_2}}</div>
                    <div class="answer">{{REPONSE_2}}</div>
                </div>

                <div class="highlight-box">
                    <div class="highlight-text">{{CITATION}}</div>
                </div>

                <div class="qa-block">
                    <div class="question">{{QUESTION_3}}</div>
                    <div class="answer">{{REPONSE_3}}</div>
                </div>
            </div>
        </div>

        <!-- FOOTER -->
        <footer class="footer">
            {{FOOTER_COMMERCIAL}}
        </footer>
    </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# INJECTION METADATA (logos + footer)
# ---------------------------------------------------------------------------

def inject_metadata(
    html: str,
    nom_contact: str,
    role_contact: str,
    poste_recrute: str,
    secteur: str,
    contexte: str,
    commercial: str,
    client_logo_b64: str | None
) -> str:
    # Logo Entourage
    logo_b64 = get_logo_base64()
    if logo_b64:
        logo_tag = f'<img src="data:image/png;base64,{logo_b64}" alt="Entourage Recrutement" class="brand-logo">'
    else:
        logo_tag = '<span style="color:#FFD700;font-weight:800;font-size:13pt;letter-spacing:1px;">ENTOURAGE RECRUTEMENT</span>'
    html = html.replace("{{LOGO_ENTOURAGE}}", logo_tag)

    # Logo client
    if client_logo_b64:
        client_tag = f'<img src="data:image/png;base64,{client_logo_b64}" alt="Logo Client">'
    else:
        # Initiales en fallback
        initiales = "".join(w[0].upper() for w in nom_contact.split()[:2]) if nom_contact else "?"
        client_tag = f'<div class="profile-img-initials">{initiales}</div>'
    html = html.replace("{{LOGO_CLIENT}}", client_tag)

    # Champs contact & mandat
    html = html.replace("{{NOM_CONTACT}}", nom_contact)
    html = html.replace("{{ROLE_CONTACT}}", role_contact)
    html = html.replace("{{POSTE_RECRUTE}}", poste_recrute)
    html = html.replace("{{SECTEUR}}", secteur)
    html = html.replace("{{CONTEXTE}}", contexte)

    # Footer commercial
    info = COMMERCIAUX[commercial]
    footer_html = (
        f'Contact&nbsp;: <a href="{info["linkedin"]}" target="_blank">{commercial}</a>'
        f'&nbsp;·&nbsp;{info["tel"]}'
        f'&nbsp;&nbsp;|&nbsp;&nbsp;'
        f'<a href="{ENTOURAGE_URL}" target="_blank">Entourage Recrutement</a>'
    )
    html = html.replace("{{FOOTER_COMMERCIAL}}", footer_html)

    return html


# ---------------------------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Tu es un rédacteur expert en communication corporate pour Entourage Recrutement, cabinet de chasse de têtes spécialisé en cadres dirigeants Finance.

Tu génères des témoignages clients professionnels (études de cas) à partir de questions et réponses brutes fournies par le client.

RÈGLES ABSOLUES :
- Retourne UNIQUEMENT le code HTML complet, sans explication, sans balises markdown
- NE COPIE JAMAIS les réponses mot pour mot — élève le registre, structure, synthétise
- Adapte les questions en formulations élégantes et percutantes
- Remplace tous les placeholders {{...}} listés ci-dessous par le contenu approprié
- Ne modifie JAMAIS {{LOGO_ENTOURAGE}}, {{LOGO_CLIENT}}, {{NOM_CONTACT}}, {{ROLE_CONTACT}}, {{POSTE_RECRUTE}}, {{SECTEUR}}, {{CONTEXTE}}, {{FOOTER_COMMERCIAL}} — laisse-les tels quels
- Langage professionnel, tonalité premium, style éditorial haut de gamme

PLACEHOLDERS À REMPLIR :

{{HEADLINE_MAIN}}
→ Texte court (4 à 7 mots) — première partie du titre accrocheur.
Ex : "Un partenaire de confiance pour"

{{HEADLINE_HIGHLIGHT}}
→ Texte court (2 à 4 mots) — partie surlignée en doré du titre.
Ex : "recruter vite et bien"

{{QUESTION_1}}
→ Reformulation élégante de la 1ère question (contexte, défi initial, pourquoi Entourage).
Env. 10-15 mots. Ton journalistique.

{{REPONSE_1}}
→ Synthèse rédigée de la réponse — 3 à 5 lignes max.
Reprend l'essentiel en élevant le niveau de langue. Pas de copier-coller.

{{QUESTION_2}}
→ Reformulation élégante de la 2ème question (déroulement de la mission, qualité du service).
Env. 10-15 mots.

{{REPONSE_2}}
→ Synthèse rédigée — 3 à 5 lignes max.

{{CITATION}}
→ La phrase la plus impactante du témoignage, reformulée si nécessaire pour qu'elle soit percutante.
15 à 25 mots max. Doit sonner authentique et convaincant.

{{QUESTION_3}}
→ Reformulation élégante de la 3ème question (résultat, recommandation, satisfaction finale).
Env. 10-15 mots.

{{REPONSE_3}}
→ Synthèse rédigée — 3 à 4 lignes max. Conclusion forte.

{{POINT_CLE_1}}, {{POINT_CLE_2}}, {{POINT_CLE_3}}
→ 3 points forts synthétiques extraits du témoignage.
Format : substantif + qualificatif court. Ex : "Réactivité exemplaire", "Profils parfaitement ciblés", "Accompagnement sur-mesure"

CONTRAINTE TAILLE — PRIORITÉ ABSOLUE :
Le document DOIT tenir sur une seule page A4 (297mm). Sois concis :
- Réponses : 3 lignes max chacune (police ~9pt)
- Citation : 1 phrase courte et percutante
- Titre : 2 lignes max

Si les Q&R sont pauvres ou courtes, enrichis intelligemment dans l'esprit du témoignage.
Si une information manque, déduis-la du contexte fourni."""


# ---------------------------------------------------------------------------
# GÉNÉRATION CLAUDE
# ---------------------------------------------------------------------------

def generate_temoignage(
    qa_text: str,
    metadata: dict,
    modification: str = None,
    previous_html: str = None
) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    if modification and previous_html:
        user_content = f"""Voici le témoignage HTML que tu as généré :

{previous_html}

L'utilisateur demande la modification suivante :
{modification}

Applique cette modification et retourne le HTML complet mis à jour.
Ne modifie pas les placeholders statiques (LOGO_ENTOURAGE, LOGO_CLIENT, NOM_CONTACT, ROLE_CONTACT, POSTE_RECRUTE, SECTEUR, CONTEXTE, FOOTER_COMMERCIAL).
Retourne UNIQUEMENT le HTML, sans explication."""
    else:
        context_block = f"""INFORMATIONS DU CONTACT :
- Nom : {metadata['nom_contact']}
- Rôle : {metadata['role_contact']}
- Poste recruté : {metadata['poste_recrute']}
- Secteur : {metadata['secteur']}
- Contexte : {metadata['contexte']}"""

        user_content = f"""Voici les informations du témoignage à générer.

{context_block}

QUESTIONS ET RÉPONSES BRUTES DU CLIENT :
---
{qa_text}
---

Remplis ce template HTML avec le contenu synthétisé et enrichi.
IMPORTANT : Laisse les placeholders statiques {{{{LOGO_ENTOURAGE}}}}, {{{{LOGO_CLIENT}}}}, {{{{NOM_CONTACT}}}}, {{{{ROLE_CONTACT}}}}, {{{{POSTE_RECRUTE}}}}, {{{{SECTEUR}}}}, {{{{CONTEXTE}}}}, {{{{FOOTER_COMMERCIAL}}}} exactement tels quels.

TEMPLATE À REMPLIR :
{TEMOIGNAGE_TEMPLATE}

Retourne le HTML complet avec tous les placeholders {{{{QUESTION_X}}}}, {{{{REPONSE_X}}}}, {{{{CITATION}}}}, {{{{HEADLINE_MAIN}}}}, {{{{HEADLINE_HIGHLIGHT}}}}, {{{{POINT_CLE_X}}}} remplacés par le contenu généré."""

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}]
    )

    html = message.content[0].text.strip()
    if html.startswith("```html"):
        html = html[7:]
    if html.startswith("```"):
        html = html[3:]
    if html.endswith("```"):
        html = html[:-3]
    return html.strip()


# ---------------------------------------------------------------------------
# BOUTON IMPRESSION PDF
# ---------------------------------------------------------------------------

def get_print_button_html(html_content: str, label: str = "📄 Télécharger PDF") -> str:
    b64 = base64.b64encode(html_content.encode("utf-8")).decode()
    return f"""
    <script>
    function printTemoignage() {{
        var w = window.open('', '_blank');
        var bytes = Uint8Array.from(atob('{b64}'), function(c) {{ return c.charCodeAt(0); }});
        var html = new TextDecoder('utf-8').decode(bytes);
        w.document.open();
        w.document.write(html);
        w.document.close();
        w.onload = function() {{
            setTimeout(function() {{ w.print(); }}, 400);
        }};
    }}
    </script>
    <button onclick="printTemoignage()" style="
        background-color: #000;
        color: #FFD700;
        border: none;
        padding: 10px 18px;
        font-size: 14px;
        font-weight: 700;
        border-radius: 6px;
        cursor: pointer;
        width: 100%;
        font-family: sans-serif;
        letter-spacing: 0.5px;
    ">{label}</button>
    """


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🖼 Logo Entourage")
    logo_file = st.file_uploader(
        "Charger le logo (si non détecté)",
        type=["png", "jpg", "jpeg"],
        label_visibility="collapsed",
        key="logo_uploader_temoignage"
    )
    if logo_file:
        try:
            from PIL import Image
            img = Image.open(logo_file)
            img.thumbnail((600, 120), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            st.session_state.logo_b64 = base64.b64encode(buf.getvalue()).decode()
        except ImportError:
            st.session_state.logo_b64 = base64.b64encode(logo_file.read()).decode()
        st.success("Logo Entourage chargé ✓")

    logo = get_logo_base64()
    if logo:
        st.image(io.BytesIO(base64.b64decode(logo)), use_container_width=True)
    else:
        st.caption("⚠️ Logo non trouvé. Uploadez-le ci-dessus.")


# ---------------------------------------------------------------------------
# PAGE PRINCIPALE
# ---------------------------------------------------------------------------

st.title("💬 Générateur de Témoignage Client")
st.caption(
    "Remplis les informations, colle les Q&R du client "
    "→ support de communication PDF généré automatiquement"
)

st.divider()

# ── SECTION 1 : CONTACT CLIENT ───────────────────────────────────────────
st.subheader("👤 Contact client")
col1, col2 = st.columns(2)
with col1:
    nom_contact = st.text_input(
        "Nom du contact *",
        placeholder="Ex : Sophie Martin"
    )
    role_contact = st.text_input(
        "Titre + Entreprise *",
        placeholder="Ex : DRH chez Crédit Agricole S.A."
    )
with col2:
    st.markdown("**Logo client** (optionnel)")
    client_logo_file = st.file_uploader(
        "Logo de l'entreprise cliente",
        type=["png", "jpg", "jpeg"],
        label_visibility="collapsed",
        key="client_logo_up"
    )
    client_logo_b64 = None
    if client_logo_file:
        try:
            from PIL import Image
            img = Image.open(client_logo_file)
            img.thumbnail((400, 400), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            client_logo_b64 = base64.b64encode(buf.getvalue()).decode()
            st.success("Logo client chargé ✓")
        except ImportError:
            client_logo_b64 = base64.b64encode(client_logo_file.read()).decode()
            st.success("Logo client chargé ✓")

st.divider()

# ── SECTION 2 : MANDAT ───────────────────────────────────────────────────
st.subheader("📋 Le Mandat")
col1, col2, col3 = st.columns(3)
with col1:
    poste_recrute = st.text_input(
        "Poste recruté *",
        placeholder="Ex : Directeur Financier (DAF)"
    )
with col2:
    secteur = st.text_input(
        "Secteur d'activité *",
        placeholder="Ex : Banque & Assurance"
    )
with col3:
    contexte = st.text_input(
        "Contexte (2-3 mots) *",
        placeholder="Ex : Croissance rapide, Scale-up"
    )

st.divider()

# ── SECTION 3 : COMMERCIAL ───────────────────────────────────────────────
st.subheader("🤝 Commercial Entourage")
commercial = st.radio(
    "Apparaîtra dans le pied de page",
    list(COMMERCIAUX.keys()),
    horizontal=True
)

st.divider()

# ── SECTION 4 : Q&R ──────────────────────────────────────────────────────
st.subheader("💬 Questions & Réponses du client")
st.caption(
    "Colle l'intégralité des échanges mail. "
    "Claude va restructurer, synthétiser et élever le niveau rédactionnel — "
    "sans copier les réponses mot pour mot."
)

qa_text = st.text_area(
    "Questions & Réponses",
    height=300,
    placeholder=(
        "Q : Quel était votre défi en matière de recrutement avant de faire appel à Entourage ?\n"
        "R : Nous cherchions un DAF depuis 6 mois sans succès...\n\n"
        "Q : Comment s'est déroulée la collaboration avec l'équipe Entourage ?\n"
        "R : Warren a très bien cerné notre besoin dès le premier appel...\n\n"
        "Q : Que recommanderiez-vous à d'autres entreprises ?\n"
        "R : Je recommande Entourage sans hésitation pour leur réactivité..."
    ),
    label_visibility="collapsed"
)

# Vérification
champs_requis = [nom_contact, role_contact, poste_recrute, secteur, contexte, qa_text]
champs_ok = all(c.strip() for c in champs_requis)
if not champs_ok:
    st.warning("⚠️ Complète tous les champs obligatoires (*) et colle les Q&R avant de générer.")

if st.button("🚀 Générer le Témoignage", type="primary", disabled=not champs_ok):
    metadata = {
        "nom_contact": nom_contact.strip(),
        "role_contact": role_contact.strip(),
        "poste_recrute": poste_recrute.strip(),
        "secteur": secteur.strip(),
        "contexte": contexte.strip(),
    }
    with st.spinner("Claude rédige le témoignage client..."):
        try:
            raw_html = generate_temoignage(qa_text, metadata)
            final_html = inject_metadata(
                raw_html,
                nom_contact=nom_contact.strip(),
                role_contact=role_contact.strip(),
                poste_recrute=poste_recrute.strip(),
                secteur=secteur.strip(),
                contexte=contexte.strip(),
                commercial=commercial,
                client_logo_b64=client_logo_b64
            )
            st.session_state.temoignage_html = final_html
            st.session_state.temoignage_qa = qa_text
            st.session_state.temoignage_metadata = metadata
            st.session_state.temoignage_commercial = commercial
            st.session_state.temoignage_logo = client_logo_b64
            st.rerun()
        except Exception as e:
            st.error(f"Erreur lors de la génération : {e}")


# ---------------------------------------------------------------------------
# RÉSULTAT
# ---------------------------------------------------------------------------

if "temoignage_html" in st.session_state:
    st.divider()

    col1, col2, col3 = st.columns([2, 2, 6])
    with col1:
        st.components.v1.html(
            get_print_button_html(st.session_state.temoignage_html),
            height=50
        )
    with col2:
        if st.button("🗑️ Réinitialiser", use_container_width=True):
            for k in [
                "temoignage_html", "temoignage_qa",
                "temoignage_metadata", "temoignage_commercial", "temoignage_logo"
            ]:
                st.session_state.pop(k, None)
            st.rerun()

    st.caption(
        "💡 Cliquez sur 📄 Télécharger PDF → une fenêtre s'ouvre "
        "→ Fichier → Imprimer → Enregistrer en PDF."
    )

    st.subheader("Aperçu")
    st.components.v1.html(st.session_state.temoignage_html, height=1250, scrolling=True)

    # Zone modifications
    st.divider()
    st.subheader("✏️ Demander des modifications")
    st.caption("Un titre à changer, une citation à reformuler ? Décris la correction.")

    modification = st.text_area(
        "Modifications souhaitées",
        placeholder=(
            "Exemples :\n"
            "• \"Change le titre en : Un recrutement réussi en un temps record\"\n"
            "• \"La citation doit être : 'Entourage a trouvé notre DAF en 3 semaines'\"\n"
            "• \"Reformule la réponse 2 pour insister sur la qualité des profils\"\n"
            "• \"Ajoute comme point clé : Délai de placement < 30 jours\""
        ),
        height=120,
        label_visibility="collapsed"
    )

    if st.button("🔄 Appliquer les modifications", type="secondary"):
        if modification.strip():
            with st.spinner("Application des modifications..."):
                try:
                    raw_html = generate_temoignage(
                        st.session_state.temoignage_qa,
                        st.session_state.temoignage_metadata,
                        modification=modification,
                        previous_html=st.session_state.temoignage_html
                    )
                    final_html = inject_metadata(
                        raw_html,
                        **st.session_state.temoignage_metadata,
                        commercial=st.session_state.temoignage_commercial,
                        client_logo_b64=st.session_state.temoignage_logo
                    )
                    st.session_state.temoignage_html = final_html
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")
        else:
            st.warning("Décris d'abord les modifications souhaitées.")
