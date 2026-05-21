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


def _load_template() -> str:
    """Read the template from disk on every generation — avoids any Streamlit / Python module cache."""
    return _template_path.read_text(encoding="utf-8") if _template_path.exists() else ""


# Module-level constant kept for the existing existence check at page boot only.
HTML_MASTER_TEMPLATE = _load_template()

MODEL = "claude-sonnet-4-6"

# ============================================================
# PROMPTS
# ============================================================

DOSSIER_SYSTEM_PROMPT = """Tu rédiges les dossiers de présentation candidats d'Entourage Recrutement, cabinet de chasse de têtes spécialisé en finance et technologie (DAF, CFO, M&A, contrôle de gestion, direction tech). Tes destinataires sont des DRH et dirigeants exigeants. Le dossier doit leur donner une lecture chirurgicale du candidat en 2 minutes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
0. PRINCIPE FONDATEUR — HIÉRARCHIE DES SOURCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Le brief du chasseur (CONTEXTE GÉNÉRAL DU CANDIDAT) est la SOURCE PRIMAIRE et PRIORITAIRE.
Le CV est une source SECONDAIRE qui sert uniquement à :
- Donner des chiffres, dates, intitulés exacts quand le brief y fait référence sans les détailler.
- Compléter ponctuellement quand un critère scorecard n'est pas couvert par le brief.

Règles d'or :
1. ZÉRO INVENTION. Toute affirmation doit pouvoir être retrouvée mot pour mot, ou en reformulation directe, dans le brief OU dans le CV. Si ce n'est ni dans l'un ni dans l'autre, ÇA N'EXISTE PAS.
2. AUCUNE INFÉRENCE PSYCHOLOGIQUE. Pas de "motivé par", "à l'aise avec", "appétence pour", "posture de leader", "esprit entrepreneurial", "capacité à fédérer", sauf si le chasseur l'a écrit explicitement dans son brief.
3. AUCUNE THÈSE AJOUTÉE. Tu ne construis pas un argumentaire pour "vendre" le candidat. Tu restitues ce que le chasseur a observé. Si le brief ne dit pas pourquoi ce candidat colle au poste, tu n'inventes pas la raison.
4. PRIORITÉ AU BRIEF. Quand le brief couvre un sujet, c'est la formulation du brief qui prime — pas l'angle que tu aurais choisi. Tu reformules pour le registre, tu ne réorientes pas le propos.
5. LE BRIEF NE RECOPIE PAS LE CV. Le chasseur ne réécrit jamais le CV dans son brief — ce serait redondant. Donc même si un poste/diplôme du CV n'apparaît pas dans le brief, c'est NORMAL : le CV est joint à part. N'en déduis surtout pas que le chasseur "a oublié" et ne complète pas son brief en y rapatriant des éléments CV. Les deux sources sont COMPLÉMENTAIRES, pas concurrentes.

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
   Générer EXACTEMENT 2 pages, soit EXACTEMENT 2 blocs <div class="page">...</div> entre <body> et </body>.
   - Bloc 1 = page 1 (Présentation, Notre Analyse, Points Clés)
   - Bloc 2 = page 2 (Score Card + Projets Phares & Adéquation, dans cet ordre, dans la même page)
   Le CV est ajouté automatiquement après (pages 3+) — tu n'as PAS à le générer.
   Retourner UNIQUEMENT le HTML complet, sans markdown (pas de ```html), sans commentaire.
   CONTRAINTE A4 STRICTE : la page 2 doit tenir sur un seul A4. Le tableau Score Card + le bloc Projets Phares ne doivent JAMAIS déborder. C'est le risque n°1 du dossier — respecte impérativement les limites de longueur ci-dessous.

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
- Inférences psychologiques non sourcées : "motivé par", "à l'aise avec", "appétence pour", "posture de", "capacité à"
- Reformulations : un fait cité dans une section ne peut pas être reformulé dans une autre

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
III. RÈGLE ANTI-RÉPÉTITION — ABSOLUE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Chaque section éclaire un angle DISTINCT et EXCLUSIF :
- Notre Analyse (page 1) → restitution structurée du brief du chasseur (positionnement, trajectoire, fit poste — tels qu'observés par le chasseur)
- Points Clés (page 1) → faits bruts opérationnels à transmettre au client (tirés du brief)
- Score Card (page 2, haut) → évaluation critère par critère (basée sur les notes et observations du chasseur)
- Projets Phares (page 2, bas) → réalisations concrètes du CV avec contexte, action, résultat mesurable

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IV. CONTENU PAR SECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PAGE 1 — PRÉSENTATION

[A] NOTRE ANALYSE
    Objectif : RESTITUER, dans le registre conseil haut de gamme, ce que le chasseur a observé dans son brief sur ce candidat et son fit avec le poste.
    Méthode :
    → Extraire du brief les éléments qui parlent de positionnement, trajectoire, fit poste, environnements traversés, contexte de la recherche.
    → Les structurer en un paragraphe analytique cohérent, en gardant le sens et l'angle du chasseur.
    → Compléter avec un (et UN seul) fait du CV uniquement si nécessaire pour rendre l'analyse lisible (ex : intitulé exact du poste actuel, scope chiffré).
    → Si le brief est court ou silencieux sur un aspect, l'analyse est plus courte. Mieux vaut 4 phrases denses qu'une 5ème phrase inventée.
    INTERDITS : salaires, notes scorecard, reformulation des points clés, projets déjà décrits en [D], thèse ou jugement qui ne figure pas dans le brief, inférence sur la personnalité ou la motivation.
    Format : 4 à 7 phrases, 70 à 130 mots (longueur indicative — adaptable selon densité du brief).

[B] POINTS CLÉS & VIGILANCE — 4 à 5 .point-card
    Objectif : informations opérationnelles tirées du brief, non développées en [A].
    Structure imposée :
    → 1 card "Prétentions salariales" (obligatoire) : chiffre précis du brief, ou "Non communiquées — à préciser." si absent. Ne jamais inventer un chiffre.
    → 1 à 2 cards "Atout" : fait mesurable ou labellisé MENTIONNÉ DANS LE BRIEF (certification CFA, équipe de X personnes, outil spécifique, scope géographique précis). Si le brief n'en mentionne pas, tu peux prendre un fait chiffré indiscutable du CV (ex : "8 ans chez X").
    → 1 à 2 cards "Point de vigilance" : élément à valider en entretien EXPLICITEMENT signalé par le chasseur dans son brief (expérience managériale limitée, secteur partiel, disponibilité, mobilité). NE PAS inventer un point de vigilance que le chasseur n'a pas relevé.
    INTERDITS : reformuler [A], anticiper le contenu du tableau [C], inventer un atout ou une vigilance non sourcés.
    Format par card : titre court (2-4 mots) + une phrase factuelle.
    HTML : <div class="point-card"><div class="point-icon"><i class="fa-solid fa-check"></i></div><div class="point-content"><h4>Titre</h4><p>Description</p></div></div>

PAGE 2 — SCORE CARD + PROJETS PHARES (les deux sur la même page A4, dans cet ordre)

[C] ÉVALUATION — tableau 4 critères
    RÈGLE CRITIQUE : Les critères et leurs notes (/5) sont fournis EXPLICITEMENT dans le prompt sous "ÉVALUATION PAR CRITÈRE".
    → Utilise EXACTEMENT ces critères et ces notes. Ne les modifie pas, ne les arrondis pas.
    → Note globale = moyenne arithmétique des notes fournies, sur 5. JAMAIS sur 10.

    RATTACHEMENT DES OBSERVATIONS (étape clé) :
    Pour CHAQUE critère du tableau :
    1. PRIORITÉ AU BRIEF : identifie dans le CONTEXTE GÉNÉRAL les phrases/éléments qui se rapportent directement à ce critère. Ce sont eux qui justifient la note.
    2. Complément CV : si — et seulement si — le brief ne couvre pas du tout ce critère, va chercher dans le CV un fait précis (poste, durée, scope, outil).
    3. Rédige 1 à 2 phrases factuelles qui justifient la note, en restant fidèle à ce que le chasseur a observé.

    Ne reproduis JAMAIS le brief tel quel : extrais, synthétise, factualise — mais sans réorienter le propos.
    Si la note est haute (≥4) mais que le brief ne dit pas pourquoi, ne fabrique pas une justification flatteuse. Reste descriptif et factuel.

    → Format : <tr><td class="score-cat">Critère</td><td class="score-val">X.X / 5</td><td class="score-txt">Analyse.</td></tr>
    LONGUEUR STRICTE NON NÉGOCIABLE : chaque analyse de critère = 1 à 2 phrases, 20 à 35 mots MAX (idéalement 25-30). Plus court qu'une analyse complète, c'est volontaire — la page 2 doit aussi accueillir 3 projets en bas.

[D] PROJETS PHARES & ADÉQUATION (bloc texte en bas de la page 2, structure graphique inchangée)
    Objectif : illustrer l'adéquation par 3 réalisations CONCRÈTES tirées du CV (section où le CV prime, car le brief ne recopie pas les expériences).
    Contenu : EXACTEMENT 3 missions/projets significatifs du CV, choisis pour leur lien direct avec les enjeux du poste.

    FORMAT — texte plat à insérer dans {{TEXTE_PROJETS_PHARES}} :
    - 3 projets séparés par <br><br>.
    - Structure d'un projet : "<strong>Intitulé court (entreprise) :</strong> 1 phrase qui combine contexte + action + résultat chiffré si dispo."
    - Pas de tableau, pas de div, pas de classe CSS — juste du texte avec <strong> et <br>.

    LONGUEUR STRICTE NON NÉGOCIABLE (sinon le 3ème projet sera coupé du PDF) :
    - EXACTEMENT 3 projets, ni 2 ni 4.
    - Chaque projet : UNE SEULE PHRASE, 18 à 28 mots MAX (titre <strong> compris).
    - Total du bloc Projets Phares : 75 mots MAX, AUCUNE EXCEPTION.

    RÈGLES :
    - Si aucun résultat chiffré n'apparaît dans le CV pour un projet, n'invente pas — décris l'action sans chiffre.
    - Préfère un projet condensé en une phrase nominale percutante à une phrase longue.
    INTERDITS : répéter la trajectoire globale de [A], reprendre les faits déjà cités en [B], inventer un chiffre/résultat absent du CV, dépasser 75 mots au total, dépasser 28 mots pour un projet, mettre moins ou plus de 3 projets.
"""

REVISION_SYSTEM_PROMPT = """Tu corriges les dossiers de présentation candidats d'Entourage Recrutement, cabinet de chasse spécialisé en finance et technologie.
Tu reçois les pages 1 et 2 d'un dossier HTML existant (page 1 : Analyse + Points Clés ; page 2 : Score Card + Projets Phares) et des instructions de correction du chasseur.

PRINCIPE FONDATEUR
- Les corrections du chasseur sont la SOURCE PRIMAIRE absolue : applique-les littéralement, sans réinterprétation.
- ZÉRO INVENTION : tu n'ajoutes aucun fait, aucune inférence (personnalité, motivation, posture) qui ne soit pas explicitement écrit dans les corrections, dans le brief initial, ou dans le CV joint.
- Le brief du chasseur ne recopie pas le CV — c'est NORMAL. Ne rapatrie pas le contenu du CV dans les pages 1-2 pour "combler" un brief que tu trouverais court.

RÈGLES HTML — NON NÉGOCIABLES
1. Ne modifie jamais le CSS, les couleurs, les polices, la structure des divs.
2. Conserver EXACTEMENT : src="LOGO_PLACEHOLDER" et LINKEDIN_CONTACT_ITEM_PLACEHOLDER.
3. Notes du tableau toujours /5 (jamais /10). Note globale = moyenne des critères.
4. Retourner UNIQUEMENT le HTML complet des pages 1 et 2, sans markdown, sans explication.
5. Ne pas ajouter de page 3 ou suivante — le CV est géré séparément.
6. Chaque page doit tenir sur un A4 strict. Si une correction allonge une section, raccourcis ailleurs pour éviter toute coupure visuelle en PDF.
   Page 2 (Score Card + Projets Phares) — LIMITES STRICTES : analyses critères = 20-35 mots chacune ; EXACTEMENT 3 projets phares, 18-28 mots chacun, 75 mots MAX au total. Si tu dépasses, le 3ème projet sera coupé du PDF.

REGISTRE À MAINTENIR
- Ton factuel, analytique, direct. Registre conseil haut de gamme (niveau Korn Ferry, Spencer Stuart).
- Phrases courtes, présent de l'indicatif, voix active. Vocabulaire métier précis.
- Aucun superlatif, adjectif vague, ni inférence psychologique non sourcée.
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
            "CONTEXTE GÉNÉRAL DU CANDIDAT — SOURCE PRIMAIRE\n"
            "Ce brief est consolidé par le chasseur et constitue la source PRIORITAIRE pour la rédaction "
            "des pages 1 et 2. Le chasseur n'y recopie volontairement PAS le CV (qui est joint séparément) — "
            "les deux sources sont complémentaires. Si un sujet n'apparaît pas dans le brief, NE LE COMPENSE PAS "
            "en allant chercher dans le CV au-delà de ce qui est strictement nécessaire pour une section donnée.\n\n"
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
        "- HIÉRARCHIE DES SOURCES : le CONTEXTE GÉNÉRAL est la source PRIMAIRE. Le CV est secondaire et "
        "ne sert qu'à donner des faits précis (chiffres, intitulés, dates) ou à couvrir un critère scorecard "
        "totalement absent du brief.\n"
        "- ZÉRO INVENTION : si une affirmation n'est ni dans le brief ni dans le CV, elle n'existe pas. Pas "
        "d'inférence psychologique, pas de thèse ajoutée, pas de motivation devinée.\n"
        "- Le brief ne recopie pas le CV (c'est volontaire — éviter la redondance). Donc ne complète pas le "
        "brief en y rapatriant des éléments CV, et ne considère pas qu'un sujet absent du brief est un oubli.\n"
        "- [A] NOTRE ANALYSE : restitue le brief du chasseur dans le registre conseil haut de gamme. "
        "Tu reformules pour le ton, tu ne réorientes pas le propos. Si le brief est court, l'analyse est courte.\n"
        "- [B] POINTS CLÉS : tirés du brief. N'invente pas un atout ou une vigilance que le chasseur n'a pas relevés.\n"
        "- [C] SCORE CARD : utilise EXACTEMENT les notes ci-dessus. Pour chaque critère, justifie d'abord avec "
        "le brief ; ne complète avec le CV que si le brief est silencieux sur ce critère. Reste descriptif, "
        "même quand la note est haute.\n"
        "- [D] PROJETS PHARES (bloc texte en bas de page 2) : EXACTEMENT 3 réalisations CV en lien direct avec la scorecard, "
        "sans inventer de chiffres absents du CV. Format texte plat dans {{TEXTE_PROJETS_PHARES}} : 3 projets séparés par <br><br>, "
        "intitulé en <strong>, UNE SEULE PHRASE par projet, 18-28 mots par projet, 75 mots MAX au total.\n"
        "- MISE EN PAGE A4 — RISQUE N°1 : la page 2 doit tenir SANS DÉBORDER (Score Card 4 critères + 3 Projets Phares sur le même A4). "
        "Limites strictes NON NÉGOCIABLES : chaque analyse scorecard = 20-35 mots ; chaque projet phare = 18-28 mots ; total Projets Phares = 75 mots MAX. "
        "Si tu dépasses, le 3ème projet sera COUPÉ du PDF.\n"
        "- Génère les pages 1 ET 2. Le CV original sera ajouté automatiquement après (pages 3+).\n"
        f"\nVOICI LE CODE HTML MAÎTRE À REMPLIR (recharge à chaque appel — STRUCTURE INTOUCHABLE) :\n{_load_template()}"
    )

    content_blocks.append({"type": "text", "text": "\n".join(eval_lines)})
    return content_blocks


def _count_words(text: str) -> int:
    """Count words in plain text (strips HTML tags first)."""
    clean = re.sub(r"<[^>]+>", " ", text)
    return len(re.findall(r"\b\w+\b", clean, flags=re.UNICODE))


def check_length_budgets(html: str) -> list[str]:
    """Return a list of human-readable warnings if the page-2 content overflows our A4 budget.

    Budgets (calibrated to ensure 3 projets phares + 4 score card rows fit on a single A4 page) :
    - Each score card analysis : ≤ 35 words
    - Each project phare : ≤ 28 words
    - Total projets phares block : ≤ 75 words, exactly 3 projets
    """
    warnings: list[str] = []

    # Score card analyses (td.score-txt)
    for i, m in enumerate(re.finditer(r'<td class="score-txt">(.*?)</td>', html, flags=re.DOTALL), start=1):
        wc = _count_words(m.group(1))
        if wc > 35:
            warnings.append(f"Score Card critère {i} : {wc} mots (max 35) — risque de débordement A4.")

    # Projets phares block (whole gray box)
    pp_match = re.search(
        r'border-left:\s*3mm\s*solid\s*#FFD700[^>]*>(.*?)</div>\s*</div>',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if pp_match:
        pp_html = pp_match.group(1)
        total_words = _count_words(pp_html)
        if total_words > 75:
            warnings.append(f"Projets Phares : {total_words} mots au total (max 75) — le 3ème projet risque d'être coupé du PDF.")
        # Count projets (separated by <br><br>)
        parts = re.split(r"<br\s*/?>\s*<br\s*/?>", pp_html, flags=re.IGNORECASE)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) != 3:
            warnings.append(f"Projets Phares : {len(parts)} projet(s) détecté(s) au lieu de 3.")
        for i, part in enumerate(parts, start=1):
            wc = _count_words(part)
            if wc > 28:
                warnings.append(f"Projet phare #{i} : {wc} mots (max 28) — réduire pour éviter coupure A4.")

    return warnings


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

                def _call_claude(messages_payload):
                    return claude_client.messages.create(
                        model=MODEL,
                        max_tokens=8000,
                        system=DOSSIER_SYSTEM_PROMPT,
                        messages=messages_payload,
                        timeout=240.0,
                    )

                base_messages = [{"role": "user", "content": content_blocks}]
                response = _call_claude(base_messages)
                generated_html = response.content[0].text

                if response.stop_reason == "max_tokens":
                    st.warning("⚠️ Génération interrompue (limite de tokens atteinte). Les pages 1 et 2 peuvent être incomplètes.")

                st.write("🖼 Injection du logo et finalisation…")
                generated_html = re.sub(r"^```[^\n]*\n", "", generated_html)
                generated_html = re.sub(r"\n```\s*$", "", generated_html.strip())

                # --- GARDE-FOU 1 : nombre de pages dossier ---
                nb_pages = len(re.findall(r'<div class="page"', generated_html))
                if nb_pages != 2:
                    st.warning(
                        f"⚠️ Claude a généré {nb_pages} page(s) dossier au lieu de 2 — vérifie le rendu."
                    )

                # --- GARDE-FOU 2 : longueur des sections page 2 ---
                length_warnings = check_length_budgets(generated_html)
                if length_warnings:
                    st.write("📏 Dépassement de longueur détecté — relance automatique pour resserrer le texte…")
                    correction_msg = (
                        "Le brouillon que tu viens de produire dépasse les limites de longueur strictes "
                        "pour la page 2. Voici les dépassements à corriger :\n\n"
                        + "\n".join(f"- {w}" for w in length_warnings)
                        + "\n\nReprends le HTML précédent et raccourcis UNIQUEMENT les sections concernées, "
                        "sans rien changer d'autre. Respecte impérativement :\n"
                        "- Chaque analyse Score Card ≤ 35 mots\n"
                        "- EXACTEMENT 3 projets phares\n"
                        "- Chaque projet ≤ 28 mots\n"
                        "- Total Projets Phares ≤ 75 mots\n"
                        "Retourne UNIQUEMENT le HTML corrigé, sans markdown, sans commentaire."
                    )
                    retry_messages = base_messages + [
                        {"role": "assistant", "content": generated_html},
                        {"role": "user", "content": correction_msg},
                    ]
                    retry_response = _call_claude(retry_messages)
                    retry_html = retry_response.content[0].text
                    retry_html = re.sub(r"^```[^\n]*\n", "", retry_html)
                    retry_html = re.sub(r"\n```\s*$", "", retry_html.strip())

                    # Use retry only if it actually improved things
                    new_warnings = check_length_budgets(retry_html)
                    if len(new_warnings) < len(length_warnings):
                        generated_html = retry_html
                        if new_warnings:
                            for w in new_warnings:
                                st.warning(f"⚠️ {w}")
                        else:
                            st.write("✅ Longueurs corrigées après relance.")
                    else:
                        for w in length_warnings:
                            st.warning(f"⚠️ {w}")

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
            "Décris ce que tu veux modifier (ton, scores, analyse, points clés, projets phares…). "
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
