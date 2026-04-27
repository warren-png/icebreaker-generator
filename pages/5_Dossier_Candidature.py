import streamlit as st
import base64
import os
import re
import json
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv
import fitz  # pymupdf
from utils.auth import check_password
from utils.ui import inject_global_styles

load_dotenv()

st.set_page_config(
    page_title="Dossier Candidature | Entourage",
    page_icon="📄",
    layout="wide"
)

inject_global_styles()

if not check_password():
    st.stop()

# ============================================================
# CONFIG
# ============================================================
claude_api_key = (
    st.secrets.get("ANTHROPIC_API_KEY")
    or st.secrets.get("CLAUDE_API_KEY")
    or os.getenv("ANTHROPIC_API_KEY")
    or os.getenv("CLAUDE_API_KEY")
)

_template_path = Path(__file__).parent.parent / "dossier_template.html"
HTML_MASTER_TEMPLATE = _template_path.read_text(encoding="utf-8") if _template_path.exists() else ""

MODEL = "claude-sonnet-4-6"

# ============================================================
# PROMPTS
# ============================================================

DOSSIER_SYSTEM_PROMPT = """Tu rédiges les dossiers de présentation candidats d'Entourage Recrutement, cabinet de chasse de têtes spécialisé en finance et technologie (DAF, CFO, M&A, contrôle de gestion, direction tech). Tes destinataires sont des DRH et dirigeants exigeants. Le dossier doit leur donner une lecture chirurgicale du candidat en 2 minutes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
I. RÈGLES HTML — NON NÉGOCIABLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. DESIGN INTOUCHABLE
   Ne modifie jamais le CSS, les couleurs, les polices, la structure des divs ni les dimensions de page.

2. PLACEHOLDERS OPAQUES
   - src="LOGO_PLACEHOLDER" : conserver tel quel dans toutes les balises <img>.
   - LINKEDIN_CONTACT_ITEM_PLACEHOLDER : conserver tel quel dans la .contact-bar.
   - La .contact-bar contient UNIQUEMENT email, téléphone et ce placeholder. Aucun autre champ.

3. NETTOYAGE
   Supprimer tout crochet [cite], balise de source ou mention "Source" dans le texte généré.

4. PIED DE PAGE
   Remplacer {{PIED_DE_PAGE_COMMERCIAL}} dans les deux pages par :
   - "Commercial : Warren" → Responsable de chasse : <a href="https://www.linkedin.com/in/warren-elbaz/">Warren</a> - 06 50 60 22 61
   - "Commercial : Helder" → Responsable de chasse : <a href="https://www.linkedin.com/in/helder-alturas-48010463/">Helder</a> - 06 22 30 96 11

5. OUTPUT
   Générer UNIQUEMENT les pages 1 et 2. Le CV est ajouté automatiquement après.
   Retourner UNIQUEMENT le HTML complet, sans markdown (pas de ```html), sans commentaire.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
II. TON ET REGISTRE — PRIORITÉ ABSOLUE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REGISTRE ATTENDU : conseil en recrutement haut de gamme, niveau grand cabinet (Korn Ferry, Spencer Stuart).
- Phrases courtes. Présent de l'indicatif. Voix active.
- Vocabulaire : termes métier exacts issus du CV et des observations du chasseur (noms de produits, marchés, réglementations, outils, stacks). Jamais de généralités.
- Chaque affirmation doit être étayée par un fait précis issu du CV ou des observations du chasseur.

MOTS ET FORMULES INTERDITS (liste exhaustive) :
- Superlatifs : "excellent", "remarquable", "impressionnant", "solide", "fort profil", "très bon", "de haut niveau"
- Formules de politesse : "nous sommes ravis", "nous avons le plaisir", "il est avec plaisir", "c'est avec enthousiasme"
- Adjectifs vagues : "bonne expérience", "profil intéressant", "belle trajectoire", "riche expérience", "grande expertise"
- Généralités : "le sens des responsabilités", "l'adaptabilité", "la rigueur", "le leadership naturel"
- Reformulations : un fait cité dans une section ne peut pas être reformulé dans une autre

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
III. RÈGLE ANTI-RÉPÉTITION — ABSOLUE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Chaque section éclaire un angle DISTINCT et EXCLUSIF :
- Notre Analyse → positionnement et trajectoire (pourquoi ce candidat pour ce poste précis)
- Points Clés → faits bruts opérationnels à transmettre au client
- Score Card → évaluation critère par critère (basée sur les notes et observations du chasseur)
- Projets Phares → réalisations concrètes avec contexte, action, résultat mesurable

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IV. CONTENU PAR SECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PAGE 1 — PRÉSENTATION

[A] NOTRE ANALYSE
    Objectif : justifier précisément le choix de ce candidat pour CE poste.
    → Cohérence du parcours avec les enjeux du poste (secteur, périmètre, niveau de responsabilité).
    → 1-2 éléments de différenciation factuelle issus des observations du chasseur : type d'environnement (ETI, grand groupe, scale-up), marché couvert, compétence rare, contexte particulier.
    → Si pertinent : adéquation avec le brief managérial.
    INTERDITS : salaires, notes scorecard, reformulation des points clés, projets déjà décrits en [D].
    Format : 5 à 7 phrases, 90 à 130 mots.

[B] POINTS CLÉS & VIGILANCE — 4 à 5 .point-card
    Objectif : informations opérationnelles à transmettre au client, non développées en [A].
    Structure imposée :
    → 1 card "Prétentions salariales" (obligatoire) : chiffre précis des observations, ou "Non communiquées — à préciser."
    → 1 à 2 cards "Atout" : fait mesurable ou labellisé (certification CFA, équipe de X personnes, outil spécifique, scope géographique précis).
    → 1 à 2 cards "Point de vigilance" : élément à valider en entretien (expérience managériale limitée, secteur partiel, disponibilité, mobilité).
    INTERDITS : reformuler [A], anticiper le contenu du tableau [C].
    Format par card : titre court (2-4 mots) + une phrase factuelle.
    HTML : <div class="point-card"><div class="point-icon"><i class="fa-solid fa-check"></i></div><div class="point-content"><h4>Titre</h4><p>Description</p></div></div>

PAGE 2 — SCORE CARD

[C] ÉVALUATION — tableau 4 critères
    RÈGLE CRITIQUE : Les critères et leurs notes (/5) sont fournis EXPLICITEMENT dans le prompt sous "ÉVALUATION PAR CRITÈRE".
    → Utilise EXACTEMENT ces critères et ces notes. Ne les modifie pas, ne les arrondis pas.
    → Note globale = moyenne arithmétique des notes fournies, sur 5. JAMAIS sur 10.

    RATTACHEMENT DES OBSERVATIONS (étape clé) :
    Les observations du chasseur sont consolidées dans un seul bloc "CONTEXTE GÉNÉRAL DU CANDIDAT" (texte libre). Pour CHAQUE critère du tableau :
    1. Identifie dans le CONTEXTE GÉNÉRAL les phrases/éléments qui se rapportent directement à ce critère (mots-clés, compétences, environnements, faits chiffrés).
    2. Croise ces éléments avec un fait précis du CV qui étaye la note.
    3. Rédige 1 à 2 phrases factuelles qui justifient la note attribuée.

    Si aucun élément du CONTEXTE GÉNÉRAL ne se rattache à un critère, appuie-toi uniquement sur le CV — sans inventer.
    Ne reproduis JAMAIS le contexte tel quel : extrais, synthétise, factualise.

    → Format : <tr><td class="score-cat">Critère</td><td class="score-val">X.X / 5</td><td class="score-txt">Analyse.</td></tr>

[D] PROJETS PHARES & ADÉQUATION
    Objectif : illustrer l'adéquation par des réalisations concrètes non mentionnées en [A] ou [B].
    Contenu : 2 à 3 missions ou projets significatifs, choisis pour leur lien direct avec les enjeux du poste.
    Structure par projet : contexte (1 phrase) → action menée → résultat chiffré si disponible.
    INTERDITS : répéter la trajectoire globale de [A] ou des faits déjà cités en [B].
    Format : 4 à 6 phrases, 80 à 110 mots.
"""

REVISION_SYSTEM_PROMPT = """Tu corriges les dossiers de présentation candidats d'Entourage Recrutement, cabinet de chasse spécialisé en finance et technologie.
Tu reçois les pages 1 et 2 d'un dossier HTML existant et des instructions de correction du chasseur.

RÈGLES HTML — NON NÉGOCIABLES
1. Ne modifie jamais le CSS, les couleurs, les polices, la structure des divs.
2. Conserver EXACTEMENT : src="LOGO_PLACEHOLDER" et LINKEDIN_CONTACT_ITEM_PLACEHOLDER.
3. Notes du tableau toujours /5 (jamais /10). Note globale = moyenne des critères.
4. Retourner UNIQUEMENT le HTML complet des pages 1 et 2, sans markdown, sans explication.
5. Ne pas ajouter de page 3 ou suivante — le CV est géré séparément.

REGISTRE À MAINTENIR
- Ton factuel, analytique, direct. Registre conseil haut de gamme (niveau Korn Ferry, Spencer Stuart).
- Phrases courtes, présent de l'indicatif, voix active. Vocabulaire métier précis.
- Aucun superlatif ni adjectif vague. Chaque affirmation étayée par un fait précis.
- Appliquer uniquement les corrections demandées. Ne pas réécrire ce qui n'est pas visé.
- Chaque section garde son rôle distinct : pas de répétition d'une rubrique à l'autre.
"""

CRITERIA_EXTRACTION_PROMPT = """Extrais les critères d'évaluation de cette scorecard de poste.
Retourne UNIQUEMENT un JSON array, sans markdown, sans explication :
[
  {"name": "Nom court du critère (2-4 mots)", "weight": "XX%", "description": "Ce que ce critère évalue en 8-12 mots"},
  ...
]
Maximum 5 critères. Respecte exactement les critères tels qu'ils apparaissent dans la scorecard."""


# ============================================================
# FONCTIONS
# ============================================================

def extract_criteria_from_scorecard(scorecard_bytes: bytes, ext: str) -> list[dict]:
    client = Anthropic(api_key=claude_api_key)

    if ext in ("html", "htm"):
        content = [{"type": "text", "text": f"Scorecard HTML :\n{scorecard_bytes.decode('utf-8', errors='ignore')}"}]
    else:
        sc_b64 = base64.b64encode(scorecard_bytes).decode()
        content = [{
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": sc_b64},
            "title": "Score Card du poste",
        }]

    content.append({"type": "text", "text": CRITERIA_EXTRACTION_PROMPT})

    response = client.messages.create(
        model=MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": content}],
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```[^\n]*\n", "", raw)
    raw = re.sub(r"\n```\s*$", "", raw.strip())
    return json.loads(raw)


def build_structured_user_prompt(
    cv_b64: str,
    scorecard_bytes: bytes,
    scorecard_ext: str,
    context: str,
    criteria_scores: list[dict],
    commercial: str,
) -> list[dict]:
    content_blocks = [
        {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": cv_b64},
            "title": "CV du candidat",
        }
    ]

    if scorecard_ext in ("html", "htm"):
        content_blocks.append({
            "type": "text",
            "text": f"SCORE CARD DU POSTE (HTML) :\n{scorecard_bytes.decode('utf-8', errors='ignore')}",
        })
    else:
        sc_b64 = base64.b64encode(scorecard_bytes).decode()
        content_blocks.append({
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": sc_b64},
            "title": "Score Card du poste",
        })

    # Structured evaluation block
    eval_lines = [f"COMMERCIAL : {commercial}\n"]

    if context.strip():
        eval_lines.append(
            "CONTEXTE GÉNÉRAL DU CANDIDAT (brief consolidé du chasseur — à utiliser pour étayer chaque critère ci-dessous) :\n"
            f"{context.strip()}\n"
        )

    eval_lines.append("ÉVALUATION PAR CRITÈRE (notes attribuées par le chasseur — à utiliser TELLES QUELLES) :")
    for cs in criteria_scores:
        eval_lines.append(f"\n— Critère : {cs['name']} ({cs.get('weight', '')})")
        eval_lines.append(f"  Note attribuée : {cs['score']} / 5")

    avg = round(sum(cs["score"] for cs in criteria_scores) / len(criteria_scores), 1) if criteria_scores else 0
    eval_lines.append(f"\nNote globale calculée : {avg} / 5 (à utiliser telle quelle dans l'en-tête scorecard)")

    eval_lines.append(
        "\n\nINSTRUCTIONS FINALES :\n"
        "- Pour le tableau [C] : utilise EXACTEMENT les notes ci-dessus.\n"
        "- Pour l'analyse de chaque critère : extrais du CONTEXTE GÉNÉRAL les éléments qui se rattachent au critère, "
        "croise avec un fait du CV, et rédige 1-2 phrases factuelles qui justifient la note.\n"
        "- Si aucun élément du contexte ne correspond à un critère, appuie-toi uniquement sur le CV — sans inventer.\n"
        "- Génère UNIQUEMENT les pages 1 et 2. Le CV original sera ajouté automatiquement après.\n"
        f"\nVOICI LE CODE HTML MAÎTRE À REMPLIR :\n{HTML_MASTER_TEMPLATE}"
    )

    content_blocks.append({"type": "text", "text": "\n".join(eval_lines)})
    return content_blocks


def inject_logo_and_linkedin(html: str, logo_b64: str, linkedin_url: str) -> str:
    if "LOGO_PLACEHOLDER" not in html:
        st.warning("⚠️ Logo : le placeholder n'a pas été conservé par Claude — le logo n'apparaîtra pas dans le header.")
    html = html.replace('src="LOGO_PLACEHOLDER"', f'src="data:image/png;base64,{logo_b64}"')

    if linkedin_url.strip():
        li_html = (
            '<div class="contact-item">'
            '<i class="fa-brands fa-linkedin-in"></i> '
            f'<a href="{linkedin_url.strip()}" target="_blank">Profil LinkedIn</a>'
            '</div>'
        )
    else:
        li_html = ""
    html = html.replace("LINKEDIN_CONTACT_ITEM_PLACEHOLDER", li_html)
    html = html.replace('href="{{LIEN_LINKEDIN}}"', f'href="{linkedin_url.strip() or "#"}"')
    html = html.replace('{{LIEN_LINKEDIN}}', linkedin_url.strip() or "#")
    return html


def append_cv_pages(html: str, pdf_bytes: bytes) -> str:
    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    cv_pages_html = ""
    mat = fitz.Matrix(150 / 72, 150 / 72)
    for page_num in range(len(pdf_doc)):
        pix = pdf_doc[page_num].get_pixmap(matrix=mat)
        img_b64 = base64.b64encode(pix.tobytes("png")).decode()
        cv_pages_html += (
            '<div class="page" style="padding:0;overflow:hidden;">'
            f'<img src="data:image/png;base64,{img_b64}" '
            'style="width:210mm;height:297mm;object-fit:contain;display:block;margin:0;" />'
            '</div>\n'
        )
    pdf_doc.close()
    return html.replace("</body>", f"{cv_pages_html}</body>", 1)


PRINT_BUTTON_HTML = """
<div class="no-print" style="position:fixed;top:20px;right:20px;z-index:9999;background:#FFD700;border-radius:8px;box-shadow:0 4px 15px rgba(0,0,0,0.3);">
  <button onclick="window.print()" style="background:#FFD700;color:#000;border:none;padding:12px 24px;font-size:14px;font-weight:800;cursor:pointer;border-radius:8px;font-family:sans-serif;letter-spacing:0.5px;">
    🖨️ Enregistrer en PDF
  </button>
</div>
<style>@media print { .no-print { display:none!important; } }</style>
"""


# ============================================================
# PAGE
# ============================================================
st.title("📄 Générateur de Dossier de Candidature")
st.caption("Crée un dossier Entourage à partir du CV PDF + Score Card + tes observations d'entretien.")

if not claude_api_key:
    st.error("❌ Clé API Claude manquante (ANTHROPIC_API_KEY ou CLAUDE_API_KEY)")
    st.stop()

if not HTML_MASTER_TEMPLATE:
    st.error("⚠️ Fichier `dossier_template.html` introuvable. Place-le à la racine du projet.")
    st.stop()

# --- LOGO ---
with st.expander(
    "🖼 Logo Entourage" + (" ✓" if st.session_state.get("dossier_logo_b64") else " — à uploader une fois"),
    expanded=not st.session_state.get("dossier_logo_b64"),
):
    logo_file = st.file_uploader(
        "Logo Entourage Recrutement (.png / .jpg)",
        type=["png", "jpg", "jpeg"],
        key="dossier_logo_upload",
    )
    if logo_file:
        st.session_state["dossier_logo_b64"] = base64.b64encode(logo_file.read()).decode()
        st.success("Logo chargé et conservé pour la session ✓")
    elif st.session_state.get("dossier_logo_b64"):
        st.info("Logo déjà chargé en session ✓")

st.divider()

# --- FICHIERS + INFOS ---
col_left, col_right = st.columns(2)

with col_left:
    cv_file = st.file_uploader("📎 CV du candidat (PDF)", type=["pdf"], key="dossier_cv")
    linkedin_url = st.text_input(
        "🔗 LinkedIn du candidat",
        placeholder="https://www.linkedin.com/in/prenom-nom/",
        key="dossier_linkedin",
    )
    commercial = st.radio(
        "👤 Responsable de chasse",
        ["Warren", "Helder"],
        horizontal=True,
        key="dossier_commercial",
    )

with col_right:
    st.markdown("**📊 Score Card du poste**")
    st.caption("Upload la score card HTML générée par l'outil Entourage. Les critères seront extraits automatiquement.")
    scorecard_file = st.file_uploader(
        "Score Card (.html ou .pdf)",
        type=["html", "htm", "pdf"],
        key="dossier_scorecard",
    )

    if scorecard_file:
        file_cache_key = f"sc_{scorecard_file.name}_{scorecard_file.size}"

        if st.session_state.get("dossier_scorecard_cache_key") != file_cache_key:
            with st.spinner("Extraction des critères..."):
                try:
                    sc_bytes = scorecard_file.read()
                    sc_ext = scorecard_file.name.rsplit(".", 1)[-1].lower()
                    criteria = extract_criteria_from_scorecard(sc_bytes, sc_ext)
                    st.session_state["dossier_scorecard_bytes"] = sc_bytes
                    st.session_state["dossier_scorecard_ext"] = sc_ext
                    st.session_state["dossier_criteria"] = criteria
                    st.session_state["dossier_scorecard_cache_key"] = file_cache_key
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur extraction critères : {e}")
        else:
            n = len(st.session_state.get("dossier_criteria", []))
            st.success(f"{scorecard_file.name} ✓ — {n} critères extraits")

st.divider()

# --- FORMULAIRE STRUCTURÉ (apparaît après extraction) ---
criteria = st.session_state.get("dossier_criteria", [])

if not criteria:
    st.info("⬆️ Upload la Score Card pour accéder au formulaire d'évaluation.")
    st.stop()

st.subheader("📝 Brief & Évaluation")

st.markdown("**Contexte général du candidat**")
st.caption(
    "Colle ici l'intégralité de ton brief / compte-rendu d'entretien. "
    "Claude rattachera automatiquement les bons éléments à chaque critère."
)
context = st.text_area(
    "Contexte général du candidat",
    height=180,
    placeholder=(
        "Ex : Candidat rencontré en visio le 15/04. Très à l'aise sur les sujets M&A, "
        "a piloté 3 LBO en tant que DAF chez X. Maîtrise SAP et Anaplan. "
        "Actuellement en poste, disponible sous 3 mois. Motivé par la dimension "
        "transformation post-acquisition. Prétentions : 110k€ fixe + 20% variable. "
        "Anglais courant, expérience ETI internationale, équipe gérée de 12 personnes…"
    ),
    key="dossier_context",
    label_visibility="collapsed",
)

st.markdown("**Notes par critère**")
st.caption("Attribue manuellement la note de 1.0 à 5.0 pour chaque critère de la scorecard.")

criteria_scores = []
for i, crit in enumerate(criteria):
    with st.container(border=True):
        col_title, col_score = st.columns([4, 1])
        with col_title:
            weight_str = f" — {crit.get('weight', '')}" if crit.get("weight") else ""
            st.markdown(f"**{crit['name']}**{weight_str}")
            if crit.get("description"):
                st.caption(crit["description"])
        with col_score:
            score = st.select_slider(
                "Note",
                options=[1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
                value=3.0,
                key=f"score_{i}",
                label_visibility="collapsed",
            )
            st.markdown(
                f"<div style='text-align:center;font-size:18px;font-weight:800'>{score}/5</div>",
                unsafe_allow_html=True,
            )

        criteria_scores.append({
            "name": crit["name"],
            "weight": crit.get("weight", ""),
            "score": score,
        })

st.divider()

# --- BOUTON GÉNÉRER ---
if st.button("✨ Générer le Dossier", type="primary", key="dossier_generate"):
    errors = []
    if not st.session_state.get("dossier_logo_b64"):
        errors.append("Upload le logo Entourage (section en haut)")
    if not cv_file:
        errors.append("Upload le CV PDF du candidat")
    if not context.strip():
        errors.append("Renseigne le contexte général du candidat (brief consolidé)")

    if errors:
        for err in errors:
            st.error(f"❌ {err}")
    else:
        with st.status("Génération du dossier en cours…", expanded=True) as status:
            try:
                st.write("📄 Lecture du CV…")
                pdf_bytes = cv_file.read()
                pdf_b64 = base64.b64encode(pdf_bytes).decode()

                sc_bytes = st.session_state["dossier_scorecard_bytes"]
                sc_ext = st.session_state["dossier_scorecard_ext"]

                st.write("🧠 Envoi à Claude pour analyse et génération…")
                content_blocks = build_structured_user_prompt(
                    cv_b64=pdf_b64,
                    scorecard_bytes=sc_bytes,
                    scorecard_ext=sc_ext,
                    context=context,
                    criteria_scores=criteria_scores,
                    commercial=commercial,
                )

                claude_client = Anthropic(api_key=claude_api_key)
                response = claude_client.messages.create(
                    model=MODEL,
                    max_tokens=8000,
                    system=DOSSIER_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": content_blocks}],
                    timeout=240.0,
                )
                generated_html = response.content[0].text

                if response.stop_reason == "max_tokens":
                    st.warning("⚠️ Génération interrompue (limite de tokens atteinte). Les pages 1 et 2 peuvent être incomplètes.")

                st.write("🖼 Injection du logo et finalisation…")
                generated_html = re.sub(r"^```[^\n]*\n", "", generated_html)
                generated_html = re.sub(r"\n```\s*$", "", generated_html.strip())

                final_html = inject_logo_and_linkedin(
                    generated_html,
                    st.session_state["dossier_logo_b64"],
                    linkedin_url,
                )

                # Sauvegarde pages 1+2 (placeholders intacts) pour révisions
                st.session_state["dossier_html_pages12"] = generated_html
                st.session_state["dossier_pdf_bytes"] = pdf_bytes
                st.session_state["dossier_criteria_scores"] = criteria_scores

                st.write("📄 Conversion du CV en images…")
                final_html = append_cv_pages(final_html, pdf_bytes)
                final_html = final_html.replace("<body>", f"<body>\n{PRINT_BUTTON_HTML}", 1)

                st.session_state["dossier_html"] = final_html
                status.update(label="✅ Dossier généré !", state="complete")

            except Exception as e:
                status.update(label="❌ Erreur", state="error")
                st.error(f"Erreur : {e}")

# --- RÉSULTAT ---
if st.session_state.get("dossier_html"):
    html_content = st.session_state["dossier_html"]

    name_match = re.search(r'class="candidate-name">([^<]+)<', html_content)
    candidate_name = name_match.group(1).strip().replace(" ", "_") if name_match else "candidat"

    st.info(
        "**Comment obtenir le PDF :**  \n"
        "1. Télécharge le fichier HTML ci-dessous  \n"
        "2. Ouvre-le dans **Chrome**  \n"
        "3. Clique le bouton **🖨️ Enregistrer en PDF** en haut à droite de la page  \n"
        "4. Dans la boîte de dialogue : format A4, sans marges → Enregistrer"
    )

    st.download_button(
        label="⬇️ Télécharger le Dossier (.html → PDF via Chrome)",
        data=html_content,
        file_name=f"dossier_{candidate_name}.html",
        mime="text/html",
        type="primary",
        key="dossier_download_html",
    )

    with st.expander("👁 Aperçu du dossier"):
        st.components.v1.html(html_content, height=900, scrolling=True)

    st.divider()

    # --- MODE RÉVISION ---
    with st.expander("✏️ Corrections — décrire et régénérer"):
        st.caption(
            "Décris ce que tu veux modifier (ton, scores, analyse, points clés…). "
            "Claude régénère les pages 1 et 2 en intégrant tes corrections. Le CV reste inchangé."
        )
        user_corrections = st.text_area(
            "Tes corrections",
            placeholder=(
                "Exemples :\n"
                "— L'analyse manque de conviction, rends-la plus assertive\n"
                "— Note Expertise Technique trop haute, mettre 3.0/5\n"
                "— Ajouter un point de vigilance sur la mobilité géographique\n"
                "— Prétentions : 70k€ fixe + 15k€ variable"
            ),
            height=160,
            key="fix_comments",
        )

        if st.button("🔄 Régénérer avec les corrections", type="primary", key="fix_regenerate"):
            if not user_corrections.strip():
                st.warning("Écris tes corrections avant de régénérer.")
            elif not st.session_state.get("dossier_html_pages12"):
                st.error("Génère d'abord un dossier.")
            else:
                with st.status("Révision en cours…", expanded=True) as rev_status:
                    try:
                        html_p12 = st.session_state["dossier_html_pages12"]
                        pdf_bytes_rev = st.session_state.get("dossier_pdf_bytes", b"")

                        revision_user_prompt = (
                            f"CORRECTIONS DEMANDÉES :\n{user_corrections.strip()}\n\n"
                            "PAGES 1 ET 2 ACTUELLES (HTML à corriger) :\n"
                            f"{html_p12}"
                        )

                        claude_client_rev = Anthropic(api_key=claude_api_key)
                        rev_response = claude_client_rev.messages.create(
                            model=MODEL,
                            max_tokens=8000,
                            system=REVISION_SYSTEM_PROMPT,
                            messages=[{"role": "user", "content": revision_user_prompt}],
                            timeout=240.0,
                        )
                        revised = rev_response.content[0].text
                        revised = re.sub(r"^```[^\n]*\n", "", revised)
                        revised = re.sub(r"\n```\s*$", "", revised.strip())

                        st.session_state["dossier_html_pages12"] = revised

                        revised = inject_logo_and_linkedin(
                            revised,
                            st.session_state["dossier_logo_b64"],
                            st.session_state.get("dossier_linkedin", ""),
                        )

                        if pdf_bytes_rev:
                            revised = append_cv_pages(revised, pdf_bytes_rev)

                        revised = revised.replace("<body>", f"<body>\n{PRINT_BUTTON_HTML}", 1)

                        st.session_state["dossier_html"] = revised
                        rev_status.update(label="✅ Dossier révisé !", state="complete")
                        st.rerun()

                    except Exception as rev_e:
                        rev_status.update(label="❌ Erreur", state="error")
                        st.error(f"Erreur : {rev_e}")
