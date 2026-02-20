import streamlit as st
import anthropic
import base64
import os
import io
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Scorecard | Biz Dev Entourage",
    page_icon="🎯",
    layout="wide"
)

# ---------------------------------------------------------------------------
# LOGO
# ---------------------------------------------------------------------------

def get_logo_base64() -> str | None:
    candidates = [
        Path(__file__).parent.parent / "logo_entourage.png",  # worktree root
        Path(__file__).parent / "logo_entourage.png",          # pages/ dir
        Path(os.getcwd()) / "logo_entourage.png",              # répertoire de lancement
        Path(os.getcwd()) / "pages" / "logo_entourage.png",
    ]
    for path in candidates:
        if path.exists():
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return None


# ---------------------------------------------------------------------------
# EXTRACTION TEXTE
# ---------------------------------------------------------------------------

def extract_text(uploaded_file) -> str | None:
    name = uploaded_file.name.lower()

    if name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8", errors="ignore")

    elif name.endswith(".pdf"):
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n".join(pages)
        except ImportError:
            st.error("pdfplumber non installé : `pip install pdfplumber`")
            return None

    elif name.endswith(".docx"):
        try:
            from docx import Document
            doc = Document(io.BytesIO(uploaded_file.read()))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            st.error("python-docx non installé : `pip install python-docx`")
            return None

    st.error("Format non supporté.")
    return None


# ---------------------------------------------------------------------------
# TEMPLATE HTML SCORECARD
# ---------------------------------------------------------------------------

SCORECARD_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Brief de Mission - {{TITRE_POSTE}}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        body {
            background-color: #555;
            font-family: 'Manrope', sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 0;
        }
        .page {
            width: 210mm;
            min-height: 297mm;
            background: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.5);
            position: relative;
            display: flex;
            flex-direction: column;
        }
        @media print {
            body { background: none; padding: 0; }
            .page { margin: 0; box-shadow: none; width: 210mm; }
        }
        .header {
            height: 25mm;
            background: #000;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 15mm;
            border-bottom: 2mm solid #FFD700;
            flex-shrink: 0;
        }
        .brand img { height: 18mm; object-fit: contain; }
        .brand-text { color: white; font-weight: 800; font-size: 13pt; letter-spacing: 1px; }
        .doc-title { color: #fff; opacity: 0.9; font-size: 10pt; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; text-align: right; }
        .doc-title span { display: block; font-size: 7pt; color: #FFD700; margin-top: 2px; }
        .content { padding: 8mm 15mm; flex-grow: 1; display: flex; flex-direction: column; gap: 6mm; }
        .section-title {
            font-family: 'Playfair Display', serif;
            font-size: 14pt;
            color: #000;
            border-bottom: 1px solid #eee;
            padding-bottom: 2mm;
            margin-bottom: 4mm;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .section-title i { color: #FFD700; font-size: 12pt; }
        .summary-box {
            background: #f8f9fa;
            border-left: 3mm solid #000;
            padding: 5mm;
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 5mm;
        }
        .sum-col h4 { font-family: 'Playfair Display', serif; font-size: 11pt; margin-bottom: 2mm; color: #000; border-bottom: 1px solid #FFD700; display: inline-block; text-transform: uppercase; }
        .sum-col p { font-size: 8.5pt; line-height: 1.4; color: #444; text-align: justify; }
        .score-table { width: 100%; border-collapse: collapse; font-size: 9pt; }
        .score-table th { text-align: left; padding: 2mm 3mm; background: #000; color: #fff; text-transform: uppercase; font-size: 8pt; letter-spacing: 0.5px; }
        .score-table td { padding: 3mm 3mm; border-bottom: 1px solid #eee; vertical-align: middle; }
        .score-cat { width: 25%; font-weight: 800; color: #000; border-right: 2px solid #FFD700; text-transform: uppercase; }
        .score-weight { width: 15%; text-align: center; font-weight: 800; color: #000; font-size: 9pt; background-color: #fcfcfc; border-right: 1px solid #eee; }
        .score-desc { color: #444; line-height: 1.3; padding-left: 15px !important; }
        .score-desc strong { color: #000; }
        .process-container {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-top: 2mm;
            position: relative;
        }
        .process-container::before {
            content: ''; position: absolute; top: 7mm; left: 20px; right: 20px; height: 1px; background: #ddd; z-index: 0;
        }
        .step { position: relative; z-index: 1; text-align: center; width: 22%; }
        .step-num {
            width: 14mm; height: 14mm; background: #000; color: #FFD700;
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            font-weight: 800; font-size: 10pt; margin: 0 auto 3mm auto;
            border: 2px solid #fff; box-shadow: 0 0 0 1px #000;
        }
        .step-title { font-weight: 800; font-size: 9pt; margin-bottom: 2px; text-transform: uppercase; }
        .step-who { font-size: 8pt; color: #555; font-style: italic; }
        .salary-box {
            margin-top: 8mm;
            text-align: center;
            border: 1px dashed #ccc;
            padding: 3mm;
            border-radius: 4px;
            background: #fffcf5;
            font-family: 'Playfair Display', serif;
            font-size: 11pt;
            color: #000;
        }
        .footer {
            height: 12mm;
            background: #f8f9fa;
            border-top: 1px solid #ddd;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 9pt;
            color: #555;
            margin-top: auto;
        }
        .footer a {
            color: #000;
            font-weight: 800;
            text-decoration: none;
            border-bottom: 2px solid #FFD700;
            margin-right: 10px;
        }
    </style>
</head>
<body>
    <div class="page">
        <div class="header">
            <div class="brand">
                {{LOGO}}
            </div>
            <div class="doc-title">
                BRIEF DE MISSION
                <span>MANDAT : {{TITRE_POSTE}}</span>
            </div>
        </div>

        <div class="content">
            <div>
                <h2 class="section-title"><i class="fa-solid fa-bullseye"></i> Vision & Contexte</h2>
                <div class="summary-box">
                    <div class="sum-col">
                        <h4>{{TITRE_BLOC_1}}</h4>
                        <p>{{TEXTE_BLOC_1}}</p>
                    </div>
                    <div class="sum-col">
                        <h4>{{TITRE_BLOC_2}}</h4>
                        <p>{{TEXTE_BLOC_2}}</p>
                    </div>
                    <div class="sum-col">
                        <h4>{{TITRE_BLOC_3}}</h4>
                        <p>{{TEXTE_BLOC_3}}</p>
                    </div>
                </div>
            </div>

            <div>
                <h2 class="section-title"><i class="fa-solid fa-star"></i> Scorecard</h2>
                <table class="score-table">
                    <thead>
                        <tr>
                            <th>Critère Clé</th>
                            <th style="text-align:center">Pondération</th>
                            <th>Définition du Succès (Indicateurs)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {{LIGNES_SCORECARD}}
                    </tbody>
                </table>
            </div>

            <div>
                <h2 class="section-title"><i class="fa-solid fa-users-viewfinder"></i> Processus de Recrutement</h2>
                <div class="process-container">
                    {{ETAPES_PROCESSUS}}
                </div>
                <div class="salary-box">
                    <strong>PACKAGE CIBLE :</strong> {{PACKAGE}}
                </div>
            </div>
        </div>

        <div class="footer">
            <a href="https://www.linkedin.com/in/warren-elbaz/" target="_blank">Warren</a> 06 50 60 22 61
        </div>
    </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# GENERATION CLAUDE
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Tu es expert en recrutement de cadres dirigeants pour Entourage Recrutement, cabinet de chasse de têtes spécialisé en finance (DAF, CFO, M&A, contrôle de gestion).

Tu génères des Briefs de Mission (scorecards) professionnels à partir de retranscriptions d'appels de qualification client.

Règles absolues :
- Retourne UNIQUEMENT le code HTML complet, sans explication, sans balises markdown
- Respecte scrupuleusement la structure du template fourni
- Les pondérations de la scorecard doivent totaliser exactement 100%
- Entre 4 et 6 critères dans la scorecard selon la complexité du poste
- Utilise un langage professionnel, précis et orienté résultats
- Si une info n'est pas explicite dans la retranscription, déduis-la intelligemment du contexte"""


def generate_scorecard(
    transcription: str,
    modification: str = None,
    previous_html: str = None
) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    logo_b64 = get_logo_base64()
    if logo_b64:
        logo_tag = f'<img src="data:image/png;base64,{logo_b64}" alt="Entourage Recrutement" style="height: 18mm;">'
    else:
        logo_tag = '<span class="brand-text">ENTOURAGE RECRUTEMENT</span>'

    template = SCORECARD_TEMPLATE.replace("{{LOGO}}", logo_tag)

    if modification and previous_html:
        user_content = f"""Voici la scorecard HTML que tu as générée :

{previous_html}

L'utilisateur demande la modification suivante :
{modification}

Applique cette modification et retourne le HTML complet mis à jour. Retourne UNIQUEMENT le HTML, sans explication."""
    else:
        user_content = f"""Voici la retranscription d'un appel de qualification client :

---
{transcription}
---

Remplis ce template HTML de scorecard avec les informations extraites de la retranscription.

TEMPLATE À REMPLIR :
{template}

Retourne le HTML complet avec tous les placeholders {{{{...}}}} remplacés par les vraies informations."""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}]
    )

    html = message.content[0].text.strip()
    # Nettoyer les balises markdown si présentes
    if html.startswith("```html"):
        html = html[7:]
    if html.startswith("```"):
        html = html[3:]
    if html.endswith("```"):
        html = html[:-3]
    return html.strip()


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("🎯 Générateur de Scorecard")
st.caption("Upload une retranscription → génération automatique du Brief de Mission")

# Avertissement logo si absent
if not get_logo_base64():
    st.warning(
        "⚠️ Logo non trouvé. Sauvegardez votre logo comme **`logo_entourage.png`** "
        "à la racine du projet pour qu'il apparaisse dans les documents."
    )

st.divider()

# Upload
uploaded_file = st.file_uploader(
    "Retranscription de l'appel de qualification",
    type=["pdf", "txt", "docx"],
    help="Formats acceptés : PDF, TXT, DOCX"
)

if uploaded_file:
    transcription_text = extract_text(uploaded_file)

    if transcription_text:
        char_count = len(transcription_text)
        st.success(f"✅ Fichier lu — {char_count:,} caractères extraits")

        if st.button("🚀 Générer la Scorecard", type="primary"):
            with st.spinner("Claude analyse la retranscription et génère le Brief de Mission..."):
                try:
                    html = generate_scorecard(transcription_text)
                    st.session_state.scorecard_html = html
                    st.session_state.scorecard_transcription = transcription_text
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de la génération : {e}")

# Affichage du résultat
if "scorecard_html" in st.session_state:
    st.divider()

    col1, col2, col3 = st.columns([2, 2, 6])
    with col1:
        st.download_button(
            label="⬇️ Télécharger HTML",
            data=st.session_state.scorecard_html,
            file_name="brief_de_mission.html",
            mime="text/html",
            use_container_width=True
        )
    with col2:
        if st.button("🗑️ Réinitialiser", use_container_width=True):
            del st.session_state.scorecard_html
            del st.session_state.scorecard_transcription
            st.rerun()

    st.caption("💡 Pour exporter en PDF : ouvrez le fichier HTML dans Chrome → Fichier → Imprimer → Enregistrer en PDF")

    # Aperçu HTML
    st.subheader("Aperçu")
    st.components.v1.html(st.session_state.scorecard_html, height=1250, scrolling=True)

    # Zone de modifications
    st.divider()
    st.subheader("✏️ Demander des modifications")
    st.caption("Une information manquante, une erreur, un ajout ? Décris-le ici.")

    modification = st.text_area(
        "Modifications souhaitées",
        placeholder=(
            "Exemples :\n"
            "• \"Ajoute un critère sur l'expérience internationale à 15%\"\n"
            "• \"Le package est 90-100k fixe + 20% variable\"\n"
            "• \"Le processus a 3 étapes : Entourage, DRH, CEO\"\n"
            "• \"Modifie le bloc Contexte : l'entreprise est en phase de croissance externe\""
        ),
        height=130,
        label_visibility="collapsed"
    )

    if st.button("🔄 Appliquer les modifications", type="secondary"):
        if modification.strip():
            with st.spinner("Application des modifications..."):
                try:
                    html = generate_scorecard(
                        st.session_state.scorecard_transcription,
                        modification=modification,
                        previous_html=st.session_state.scorecard_html
                    )
                    st.session_state.scorecard_html = html
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")
        else:
            st.warning("Décris d'abord les modifications souhaitées.")
