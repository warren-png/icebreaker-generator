import streamlit as st
import anthropic
import base64
import os
import io
from pathlib import Path
from dotenv import load_dotenv
from utils.auth import check_password
from utils.ui import inject_global_styles

load_dotenv()

st.set_page_config(
    page_title="Témoignage Client | Entourage Recrutement",
    page_icon="💬",
    layout="wide"
)

inject_global_styles()

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
            font-size: 13pt;
            color: #FFD700;
            margin-right: 2px;
        }
        .highlight-text::after {
            content: "\201D";
            font-size: 13pt;
            color: #FFD700;
            margin-left: 2px;
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
# PARSING Q&R
# ---------------------------------------------------------------------------

import re
import json


def _is_question_line(line: str) -> bool:
    """Détecte si une ligne est une question (termine par ? et assez courte)."""
    stripped = line.strip()
    if not stripped:
        return False
    # Une question se termine par ? et fait moins de ~300 caractères
    # (les réponses sont généralement plus longues)
    return stripped.endswith('?') and len(stripped) < 300


def parse_qa_blocks(qa_text: str) -> list[dict]:
    """
    Parse le texte brut Q&R en blocs [{question, reponse}, ...].
    Gère 3 formats :
      1. Préfixé : Q: / R: , Q. / R. , Question / Réponse
      2. Sans préfixe : lignes terminant par ? = questions (ligne par ligne)
      3. Fallback : découpage par paragraphes alternés
    """
    text = qa_text.strip()

    # ── FORMAT 1 : Préfixes Q:/R: ─────────────────────────────────────
    q_prefix = re.compile(
        r'^(?:Q\s*[:.\-—]|Question\s*[:.\-—])',
        re.IGNORECASE | re.MULTILINE
    )
    prefix_matches = list(q_prefix.finditer(text))

    if prefix_matches:
        blocks = []
        for i, match in enumerate(prefix_matches):
            start = match.start()
            end = prefix_matches[i + 1].start() if i + 1 < len(prefix_matches) else len(text)
            chunk = text[start:end].strip()

            r_match = re.search(
                r'\n\s*(?:R\s*[:.\-—]|Réponse\s*[:.\-—]|Reponse\s*[:.\-—])',
                chunk, re.IGNORECASE
            )
            if r_match:
                q_line = chunk[:r_match.start()].strip()
                r_line = chunk[r_match.start():].strip()
                q_line = re.sub(r'^(?:Q\s*[:.\-—]|Question\s*[:.\-—])\s*', '', q_line, flags=re.IGNORECASE).strip()
                r_line = re.sub(r'^(?:R\s*[:.\-—]|Réponse\s*[:.\-—]|Reponse\s*[:.\-—])\s*', '', r_line, flags=re.IGNORECASE).strip()
            else:
                lines = chunk.split('\n', 1)
                q_line = re.sub(r'^(?:Q\s*[:.\-—]|Question\s*[:.\-—])\s*', '', lines[0], flags=re.IGNORECASE).strip()
                r_line = lines[1].strip() if len(lines) > 1 else ""

            blocks.append({"question": q_line, "reponse": r_line})
        return blocks[:3]

    # ── FORMAT 2 : Ligne par ligne — les lignes terminant par ? sont des questions
    lines = text.split('\n')
    blocks = []
    current_question = None
    current_reponse_lines = []

    for line in lines:
        stripped = line.strip()

        if _is_question_line(stripped):
            # Sauver le bloc précédent
            if current_question is not None:
                blocks.append({
                    "question": current_question,
                    "reponse": " ".join(current_reponse_lines).strip()
                })
            current_question = stripped
            current_reponse_lines = []
        elif stripped:
            # Ligne non vide = fait partie de la réponse en cours
            if current_question is not None:
                current_reponse_lines.append(stripped)
            # sinon : texte avant la première question, on l'ignore

    # Sauver le dernier bloc
    if current_question is not None:
        blocks.append({
            "question": current_question,
            "reponse": " ".join(current_reponse_lines).strip()
        })

    if blocks:
        return blocks[:3]

    # ── FORMAT 3 : Fallback — alterner paragraphes Q/R ────────────────
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    blocks = []
    for i in range(0, len(paragraphs) - 1, 2):
        blocks.append({
            "question": paragraphs[i],
            "reponse": paragraphs[i + 1] if i + 1 < len(paragraphs) else ""
        })
    return blocks[:3]


# ---------------------------------------------------------------------------
# SYSTEM PROMPT — SEULEMENT POUR LES ÉLÉMENTS CRÉATIFS
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_CREATIVE = """Tu es un expert en communication corporate pour Entourage Recrutement.

À partir des questions/réponses d'un témoignage client, tu dois générer UNIQUEMENT les éléments créatifs suivants en JSON.

Retourne UNIQUEMENT un JSON valide (sans markdown, sans ```), avec ces clés :

{
  "headline_main": "Titre accrocheur de 4 à 7 mots (1ère partie)",
  "headline_highlight": "2 à 4 mots (partie surlignée en doré)",
  "citation": "Phrase la plus impactante extraite MOT POUR MOT des réponses du client (15-25 mots max). NE REFORMULE PAS.",
  "point_cle_1": "Bénéfice concret court (ex: Réactivité exemplaire)",
  "point_cle_2": "Bénéfice concret court (ex: Profils parfaitement ciblés)",
  "point_cle_3": "Bénéfice concret court (ex: Accompagnement sur-mesure)"
}

RÈGLES :
- La citation doit être extraite TELLE QUELLE des réponses, pas reformulée
- Les points clés : substantif + qualificatif court
- Le titre doit être accrocheur et professionnel"""


# ---------------------------------------------------------------------------
# GÉNÉRATION CLAUDE (éléments créatifs uniquement)
# ---------------------------------------------------------------------------

def generate_creative_elements(qa_text: str, metadata: dict) -> dict:
    """Appelle Claude pour générer uniquement titre, citation et points clés."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    user_content = f"""Témoignage client pour :
- Poste recruté : {metadata['poste_recrute']}
- Secteur : {metadata['secteur']}

Questions et réponses du client :
---
{qa_text}
---

Génère le JSON avec les éléments créatifs."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT_CREATIVE,
        messages=[{"role": "user", "content": user_content}]
    )

    text = message.content[0].text.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                return json.loads(part)
            except Exception:
                continue
    return json.loads(text)


def build_temoignage_html(qa_text: str, metadata: dict) -> str:
    """Construit le HTML en injectant les Q&R directement + éléments créatifs de Claude."""
    # 1. Parser les Q&R
    blocks = parse_qa_blocks(qa_text)

    # 2. Obtenir les éléments créatifs de Claude
    creative = generate_creative_elements(qa_text, metadata)

    # 3. Remplir le template
    html = TEMOIGNAGE_TEMPLATE

    # Q&R injectées DIRECTEMENT (jamais passées par Claude)
    for i in range(3):
        if i < len(blocks):
            html = html.replace(f"{{{{QUESTION_{i+1}}}}}", blocks[i]["question"])
            html = html.replace(f"{{{{REPONSE_{i+1}}}}}", blocks[i]["reponse"])
        else:
            html = html.replace(f"{{{{QUESTION_{i+1}}}}}", "")
            html = html.replace(f"{{{{REPONSE_{i+1}}}}}", "")

    # Éléments créatifs
    html = html.replace("{{HEADLINE_MAIN}}", creative.get("headline_main", ""))
    html = html.replace("{{HEADLINE_HIGHLIGHT}}", creative.get("headline_highlight", ""))
    html = html.replace("{{CITATION}}", creative.get("citation", ""))
    html = html.replace("{{POINT_CLE_1}}", creative.get("point_cle_1", ""))
    html = html.replace("{{POINT_CLE_2}}", creative.get("point_cle_2", ""))
    html = html.replace("{{POINT_CLE_3}}", creative.get("point_cle_3", ""))

    return html


# ---------------------------------------------------------------------------
# MODIFICATION VIA CLAUDE
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_MODIFICATION = """Tu es un assistant qui modifie un témoignage client HTML existant.

RÈGLES ABSOLUES :
- Applique UNIQUEMENT la modification demandée par l'utilisateur
- Ne modifie RIEN d'autre dans le HTML
- Ne modifie JAMAIS les placeholders statiques (LOGO_ENTOURAGE, LOGO_CLIENT, NOM_CONTACT, ROLE_CONTACT, POSTE_RECRUTE, SECTEUR, FOOTER_COMMERCIAL) — laisse-les tels quels
- Retourne UNIQUEMENT le HTML complet modifié, sans explication, sans balises markdown"""


def apply_modification(previous_html: str, modification: str) -> str:
    """Applique une modification au HTML existant via Claude."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    user_content = f"""Voici le témoignage HTML actuel :

{previous_html}

Modification demandée :
{modification}

Applique UNIQUEMENT cette modification et retourne le HTML complet mis à jour."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8096,
        system=SYSTEM_PROMPT_MODIFICATION,
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
col1, col2 = st.columns(2)
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
    "Colle l'intégralité des échanges mail (questions & réponses). "
    "Claude conservera le contenu tel quel et créera la mise en page professionnelle."
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
champs_requis = [nom_contact, role_contact, poste_recrute, secteur, qa_text]
champs_ok = all(c.strip() for c in champs_requis)
if not champs_ok:
    st.warning("⚠️ Complète tous les champs obligatoires (*) et colle les Q&R avant de générer.")

if st.button("🚀 Générer le Témoignage", type="primary", disabled=not champs_ok):
    metadata = {
        "nom_contact": nom_contact.strip(),
        "role_contact": role_contact.strip(),
        "poste_recrute": poste_recrute.strip(),
        "secteur": secteur.strip(),
    }
    with st.spinner("Claude rédige le témoignage client..."):
        try:
            raw_html = build_temoignage_html(qa_text, metadata)
            final_html = inject_metadata(
                raw_html,
                nom_contact=nom_contact.strip(),
                role_contact=role_contact.strip(),
                poste_recrute=poste_recrute.strip(),
                secteur=secteur.strip(),
                commercial=commercial,
                client_logo_b64=client_logo_b64
            )
            st.session_state.temoignage_raw_html = raw_html
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
                "temoignage_html", "temoignage_raw_html", "temoignage_qa",
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
                    # Utiliser le raw_html si disponible, sinon le html final
                    prev_html = st.session_state.get(
                        "temoignage_raw_html",
                        st.session_state.temoignage_html
                    )
                    raw_html = apply_modification(prev_html, modification)
                    final_html = inject_metadata(
                        raw_html,
                        **st.session_state.temoignage_metadata,
                        commercial=st.session_state.temoignage_commercial,
                        client_logo_b64=st.session_state.temoignage_logo
                    )
                    st.session_state.temoignage_raw_html = raw_html
                    st.session_state.temoignage_html = final_html
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")
        else:
            st.warning("Décris d'abord les modifications souhaitées.")
