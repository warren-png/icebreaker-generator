import streamlit as st
import base64
import os
import re
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv
import fitz  # pymupdf — rendu des pages CV en images PNG
from utils.auth import check_password

load_dotenv()

st.set_page_config(
    page_title="Dossier Candidature | Entourage",
    page_icon="📄",
    layout="wide"
)

# — Authentification —
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

# ============================================================
# PROMPTS
# ============================================================
DOSSIER_SYSTEM_PROMPT = """Tu rédiges les dossiers de présentation candidats d'Entourage Recrutement, cabinet de chasse spécialisé en finance et technologie. Tu remplis un template HTML strict sans toucher au design.

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
II. CONTENU — REGISTRE ET STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REGISTRE ATTENDU
- Ton : analytique, factuel, direct. Registre conseil haut de gamme.
- Interdit : superlatifs ("excellent", "remarquable", "impressionnant", "solide", "fort profil"), formules de politesse ("nous sommes ravis"), adjectifs vagues ("bonne expérience", "profil intéressant").
- Vocabulaire : termes métier exacts issus du brief et du CV (noms de produits, marchés, réglementations, stacks techniques).
- Style : phrases courtes, présent de l'indicatif, voix active.

RÈGLE ANTI-RÉPÉTITION — ABSOLUE
Chaque section éclaire un angle distinct. Un fait mentionné dans une section ne peut pas être reformulé dans une autre.
- Notre Analyse → positionnement et trajectoire
- Points Clés → faits bruts et chiffres
- Score Card → évaluation critère par critère
- Projets Phares → réalisations concrètes avec contexte et résultat

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
III. CONTENU PAR SECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PAGE 1 — PRÉSENTATION

[A] NOTRE ANALYSE — {{ANALYSE_TEXTE_ISSUE_DU_BRIEF}}
    Objectif : justifier le choix de ce candidat pour ce poste précis.
    Contenu :
    → Cohérence du parcours avec les enjeux du poste (secteur, périmètre, niveau de responsabilité).
    → Un ou deux éléments de différenciation factuelle : type d'environnement (ETI, grand groupe, scale-up), marché couvert, compétence rare ou contexte particulier.
    → Adéquation globale avec le brief managérial si des éléments pertinents y figurent.
    Interdit : salaires, notes, reformulation des points clés, projets déjà évoqués en section D.
    Format : 5 à 7 phrases, 90 à 130 mots.

[B] POINTS CLÉS & VIGILANCE — 4 à 5 .point-card
    Objectif : informations opérationnelles à transmettre au client, non développées en [A].
    Structure imposée :
    → 1 card "Prétentions salariales" (obligatoire) : chiffre précis du brief/CV, ou "Non communiquées — à préciser."
    → 1 à 2 cards "Atout" : fait mesurable ou labelisé (ex. : certification CFA, gestion d'une équipe de X personnes, maîtrise d'un outil spécifique, scope géographique).
    → 1 à 2 cards "Point de vigilance" : élément à valider en entretien (ex. : expérience managériale limitée, secteur partiel, disponibilité, mobilité).
    Interdit : reformuler [A], anticiper le contenu du tableau [C].
    Format par card : titre court (2-4 mots) + une phrase factuelle.
    HTML : <div class="point-card"><div class="point-icon"><i class="fa-solid fa-check"></i></div><div class="point-content"><h4>Titre</h4><p>Description</p></div></div>

PAGE 2 — SCORE CARD

[C] ÉVALUATION — {{NOTE_GLOBALE}} et tableau 4 critères
    → Note globale : moyenne arithmétique des 4 notes, sur 5 (ex. : 3.8 / 5). Jamais sur 10.
    → Critères : extraire exactement les 4 critères définis dans la Score Card du poste.
    → Analyse par critère : 1 à 2 phrases factuelles, distinctes des sections [A], [B] et [D].
       Citer un élément précis du CV ou du brief pour étayer chaque note.
    → Format : <tr><td class="score-cat">Critère</td><td class="score-val">X.X / 5</td><td class="score-txt">Analyse.</td></tr>

[D] PROJETS PHARES & ADÉQUATION — {{TEXTE_PROJETS_PHARES}}
    Objectif : illustrer l'adéquation par des réalisations concrètes non mentionnées en [A] ou [B].
    Contenu : 2 à 3 missions ou projets significatifs, choisis pour leur lien direct avec les enjeux du poste.
    Structure par projet : contexte (1 proposition) → action menée → résultat chiffré si disponible.
    Interdit : répéter la trajectoire globale déjà posée en [A] ou des faits déjà cités en [B].
    Format : 4 à 6 phrases, 80 à 110 mots.
"""

REVISION_SYSTEM_PROMPT = """Tu corriges les dossiers de présentation candidats d'Entourage Recrutement, cabinet de chasse spécialisé en finance et technologie.
Tu reçois les pages 1 et 2 d'un dossier HTML existant et des instructions de correction du chasseur.

RÈGLES HTML — NON NÉGOCIABLES
1. Ne modifie jamais le CSS, les couleurs, les polices, la structure des divs.
2. Conserver EXACTEMENT : src="LOGO_PLACEHOLDER" et LINKEDIN_CONTACT_ITEM_PLACEHOLDER.
3. Notes du tableau toujours /5 (jamais /10). Note globale = moyenne des 4 critères.
4. Retourner UNIQUEMENT le HTML complet des pages 1 et 2, sans markdown, sans explication.
5. Ne pas ajouter de page 3 ou suivante — le CV est géré séparément.

REGISTRE À MAINTENIR
- Ton factuel, analytique, direct. Registre conseil haut de gamme.
- Pas de superlatifs ni d'adjectifs vagues. Vocabulaire métier précis (finance/tech).
- Chaque section garde son rôle distinct : pas de répétition d'une rubrique à l'autre.
- Appliquer uniquement les corrections demandées. Ne pas réécrire ce qui n'est pas visé.
"""

# ============================================================
# PAGE
# ============================================================
st.title("📄 Générateur de Dossier de Candidature")
st.caption("Crée un dossier Entourage à partir du CV PDF + Score Card + brief entretien.")

if not claude_api_key:
    st.error("❌ Clé API Claude manquante (ANTHROPIC_API_KEY ou CLAUDE_API_KEY)")
    st.stop()

if not HTML_MASTER_TEMPLATE:
    st.error("⚠️ Fichier `dossier_template.html` introuvable. Place-le à la racine du projet.")
    st.stop()

# --- LOGO (persistant en session) ---
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

# --- INPUTS PRINCIPAUX ---
col_left, col_right = st.columns(2)

with col_left:
    cv_file = st.file_uploader(
        "📎 CV du candidat (PDF)",
        type=["pdf"],
        key="dossier_cv",
    )
    brief_text = st.text_area(
        "📝 Brief / Compte-rendu entretien",
        height=180,
        placeholder="Colle ici le brief IA issu de la retranscription visio...",
        key="dossier_brief",
    )
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
    st.caption(
        "Upload la score card HTML générée par l'outil Entourage. "
        "L'IA en extraira automatiquement les critères, notes et analyses."
    )
    scorecard_file = st.file_uploader(
        "Score Card (.html ou .pdf)",
        type=["html", "htm", "pdf"],
        key="dossier_scorecard",
    )
    if scorecard_file:
        st.success(f"Score card chargée : {scorecard_file.name} ✓")

st.divider()

# --- BOUTON GÉNÉRER ---
if st.button("✨ Générer le Dossier", type="primary", key="dossier_generate"):
    errors = []
    if not st.session_state.get("dossier_logo_b64"):
        errors.append("Upload le logo Entourage (section en haut)")
    if not cv_file:
        errors.append("Upload le CV PDF du candidat")
    if not brief_text.strip():
        errors.append("Le brief / compte-rendu est obligatoire")
    if not scorecard_file:
        errors.append("Upload la Score Card du poste")

    if errors:
        for err in errors:
            st.error(f"❌ {err}")
    else:
        with st.status("Génération du dossier en cours…", expanded=True) as status:
            try:
                # ÉTAPE 1 — Lecture des fichiers
                st.write("📄 Lecture du CV et de la Score Card…")
                pdf_bytes = cv_file.read()
                pdf_b64 = base64.b64encode(pdf_bytes).decode()
                scorecard_bytes = scorecard_file.read()
                scorecard_ext = scorecard_file.name.rsplit(".", 1)[-1].lower()

                # ÉTAPE 2 — Construction du message Claude
                st.write("🧠 Envoi à Claude pour analyse et génération…")
                content_blocks = [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                        "title": "CV du candidat",
                    },
                ]

                if scorecard_ext in ("html", "htm"):
                    scorecard_text = scorecard_bytes.decode("utf-8", errors="ignore")
                    content_blocks.append({
                        "type": "text",
                        "text": f"SCORE CARD DU POSTE (HTML) :\n{scorecard_text}",
                    })
                else:
                    sc_b64 = base64.b64encode(scorecard_bytes).decode()
                    content_blocks.append({
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": sc_b64,
                        },
                        "title": "Score Card du poste",
                    })

                user_prompt = (
                    f"BRIEF / COMPTE-RENDU ENTRETIEN :\n{brief_text.strip()}\n\n"
                    f"COMMERCIAL : {commercial}\n\n"
                    "INSTRUCTIONS SCORE CARD :\n"
                    "Lis la Score Card du poste ci-dessus. "
                    "Extrais les 4 critères, notes (/5) et analyses. "
                    "Utilise-les pour remplir le tableau page 2.\n\n"
                    "RAPPEL : génère UNIQUEMENT les pages 1 et 2. "
                    "Le CV original sera ajouté automatiquement après.\n\n"
                    f"VOICI LE CODE HTML MAÎTRE À REMPLIR :\n{HTML_MASTER_TEMPLATE}"
                )
                content_blocks.append({"type": "text", "text": user_prompt})

                # ÉTAPE 3 — Appel Claude (timeout 3 min)
                claude_client = Anthropic(api_key=claude_api_key)
                response = claude_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=8000,
                    system=DOSSIER_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": content_blocks}],
                    timeout=240.0,
                )
                generated_html = response.content[0].text

                if response.stop_reason == "max_tokens":
                    st.warning(
                        "⚠️ Génération interrompue (limite de tokens atteinte). "
                        "Les pages 1 et 2 peuvent être incomplètes."
                    )

                # ÉTAPE 4 — Nettoyage, injection logo + LinkedIn
                st.write("🖼 Injection du logo et finalisation…")
                generated_html = re.sub(r"^```[^\n]*\n", "", generated_html)
                generated_html = re.sub(r"\n```\s*$", "", generated_html.strip())

                logo_b64 = st.session_state["dossier_logo_b64"]
                if 'LOGO_PLACEHOLDER' not in generated_html:
                    st.warning("⚠️ Logo : le placeholder n'a pas été conservé par Claude — le logo n'apparaîtra pas dans le header.")
                final_html = generated_html.replace(
                    'src="LOGO_PLACEHOLDER"',
                    f'src="data:image/png;base64,{logo_b64}"',
                )

                if linkedin_url.strip():
                    li_html = (
                        '<div class="contact-item">'
                        '<i class="fa-brands fa-linkedin-in"></i> '
                        f'<a href="{linkedin_url.strip()}" target="_blank">Profil LinkedIn</a>'
                        '</div>'
                    )
                else:
                    li_html = ""
                final_html = final_html.replace("LINKEDIN_CONTACT_ITEM_PLACEHOLDER", li_html)
                final_html = final_html.replace('href="{{LIEN_LINKEDIN}}"', f'href="{linkedin_url.strip() or "#"}"')
                final_html = final_html.replace('{{LIEN_LINKEDIN}}', linkedin_url.strip() or "#")

                # Sauvegarde pages 1+2 (placeholders intacts) pour révisions
                st.session_state["dossier_html_pages12"] = generated_html
                st.session_state["dossier_pdf_bytes"] = pdf_bytes

                # ÉTAPE 5 — Conversion CV en images PNG
                st.write("📄 Conversion du CV en images…")
                pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                cv_pages_html = ""
                mat = fitz.Matrix(150 / 72, 150 / 72)  # 150 DPI
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
                final_html = final_html.replace("</body>", f"{cv_pages_html}</body>", 1)

                # ÉTAPE 6 — Bouton impression navigateur
                print_button_html = """
<div class="no-print" style="position:fixed;top:20px;right:20px;z-index:9999;background:#FFD700;border-radius:8px;box-shadow:0 4px 15px rgba(0,0,0,0.3);">
  <button onclick="window.print()" style="background:#FFD700;color:#000;border:none;padding:12px 24px;font-size:14px;font-weight:800;cursor:pointer;border-radius:8px;font-family:sans-serif;letter-spacing:0.5px;">
    🖨️ Enregistrer en PDF
  </button>
</div>
<style>@media print { .no-print { display:none!important; } }</style>
"""
                st.session_state["_print_button_html"] = print_button_html
                final_html = final_html.replace("<body>", f"<body>\n{print_button_html}", 1)

                st.session_state["dossier_html"] = final_html
                status.update(label="✅ Dossier généré !", state="complete")

            except Exception as e:
                status.update(label="❌ Erreur", state="error")
                st.error(f"Erreur : {e}")

# --- RÉSULTAT : TÉLÉCHARGEMENT + APERÇU ---
if st.session_state.get("dossier_html"):
    html_content = st.session_state["dossier_html"]

    name_match = re.search(r'class="candidate-name">([^<]+)<', html_content)
    candidate_name = (
        name_match.group(1).strip().replace(" ", "_") if name_match else "candidat"
    )

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
                            model="claude-sonnet-4-20250514",
                            max_tokens=8000,
                            system=REVISION_SYSTEM_PROMPT,
                            messages=[{"role": "user", "content": revision_user_prompt}],
                            timeout=240.0,
                        )
                        revised = rev_response.content[0].text
                        revised = re.sub(r"^```[^\n]*\n", "", revised)
                        revised = re.sub(r"\n```\s*$", "", revised.strip())

                        st.session_state["dossier_html_pages12"] = revised

                        # Re-injection logo
                        logo_b64_rev = st.session_state["dossier_logo_b64"]
                        revised = revised.replace(
                            'src="LOGO_PLACEHOLDER"',
                            f'src="data:image/png;base64,{logo_b64_rev}"',
                        )

                        # Re-injection LinkedIn
                        li_url = st.session_state.get("dossier_linkedin", "")
                        if li_url.strip():
                            li_div = (
                                '<div class="contact-item">'
                                '<i class="fa-brands fa-linkedin-in"></i> '
                                f'<a href="{li_url.strip()}" target="_blank">Profil LinkedIn</a>'
                                '</div>'
                            )
                        else:
                            li_div = ""
                        revised = revised.replace("LINKEDIN_CONTACT_ITEM_PLACEHOLDER", li_div)

                        # Re-append pages CV
                        if pdf_bytes_rev:
                            pdf_doc_rev = fitz.open(stream=pdf_bytes_rev, filetype="pdf")
                            cv_imgs = ""
                            mat_rev = fitz.Matrix(150 / 72, 150 / 72)
                            for pn in range(len(pdf_doc_rev)):
                                pix_rev = pdf_doc_rev[pn].get_pixmap(matrix=mat_rev)
                                i64 = base64.b64encode(pix_rev.tobytes("png")).decode()
                                cv_imgs += (
                                    '<div class="page" style="padding:0;overflow:hidden;">'
                                    f'<img src="data:image/png;base64,{i64}" '
                                    'style="width:210mm;height:297mm;object-fit:contain;display:block;margin:0;" />'
                                    '</div>\n'
                                )
                            pdf_doc_rev.close()
                            revised = revised.replace("</body>", f"{cv_imgs}</body>", 1)

                        # Re-injection bouton print
                        print_btn = st.session_state.get("_print_button_html", "")
                        if print_btn:
                            revised = revised.replace("<body>", f"<body>\n{print_btn}", 1)

                        st.session_state["dossier_html"] = revised
                        rev_status.update(label="✅ Dossier révisé !", state="complete")
                        st.rerun()

                    except Exception as rev_e:
                        rev_status.update(label="❌ Erreur", state="error")
                        st.error(f"Erreur : {rev_e}")
