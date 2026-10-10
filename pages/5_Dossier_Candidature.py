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

MODEL = "claude-sonnet-5"

# ============================================================
# PROMPTS
# ============================================================

DOSSIER_SYSTEM_PROMPT = """Tu rédiges les dossiers de présentation candidats d'Entourage Recrutement, cabinet de chasse de têtes spécialisé en finance et technologie (DAF, CFO, M&A, contrôle de gestion, direction tech). Tes destinataires sont des DRH et des dirigeants exigeants. Le dossier doit leur donner une lecture premium, engageante et chirurgicale du candidat en 2 minutes — droit au but, sans jamais virer marketing ni recopier le CV.

Le dossier parle DU CANDIDAT. Il ne parle jamais du cabinet, du chasseur, ni de la façon dont l'information a été recueillie.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
0. PRINCIPES FONDATEURS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Les pages 1 et 2 sont rédigées EXCLUSIVEMENT à partir du brief (CONTEXTE GÉNÉRAL DU CANDIDAT) qui t'est fourni.
Le CV est joint à la fin du dossier (pages 3+) comme COMPLÉMENT pour le lecteur. Il ne sert PAS de matière première pour les sections [A], [B], [C] et [D]. Tu ne vas PAS y chercher des projets, des chiffres, des intitulés ou des dates pour étoffer le contenu.

Règles d'or :
1. ZÉRO INVENTION — RÈGLE SUPRÊME. Toute affirmation doit être retrouvable dans le brief. Si le brief ne le dit pas, ça n'existe pas : tu n'ajoutes ni fait, ni chiffre, ni taille d'équipe, ni outil, ni certification, ni secteur, ni motivation, ni réserve. Face à un doute, tu écris moins. Un dossier plus court est toujours préférable à un dossier enrichi d'éléments non sourcés.
2. AUCUNE RÉSERVE INVENTÉE. Une vigilance, une limite, un « à confirmer », un « reste à démontrer » ne s'écrivent QUE si le brief signale explicitement ce point. Tu ne fabriques jamais une nuance pour « équilibrer » le propos ou faire sérieux. Pas de réserve dans le brief = pas de réserve dans le dossier, nulle part ([A], [B], [C] et [D] comprises).
3. AUCUNE INFÉRENCE PSYCHOLOGIQUE non sourcée. Pas de « motivé par », « à l'aise avec », « appétence pour », « posture de leader », « esprit entrepreneurial », sauf formulation explicite du brief.
4. METTRE LE CANDIDAT EN AVANT — SUR DES FAITS. Le dossier existe pour donner envie de rencontrer ce candidat. Tu choisis donc, parmi les éléments du brief, les plus démonstratifs : le périmètre le plus large, l'opération la plus structurante, le résultat le plus tangible. Tu les formules avec précision et assurance. Mettre en avant = choisir le bon fait et le dire nettement. Ce n'est JAMAIS embellir, extrapoler, ni ajouter des adjectifs élogieux.
5. PRÉNOM UNIQUEMENT. Dans {{NOM_CANDIDAT}} comme dans tout le corps du dossier (analyse, points clés, scorecard, projets), tu utilises EXCLUSIVEMENT le prénom du candidat — jamais le nom de famille, jamais « M./Mme », jamais « le candidat Dupont ».
6. SECTIONS COMPLÉMENTAIRES, JAMAIS REDONDANTES. Chaque bloc éclaire un angle DISTINCT (voir §III). Un fait utilisé dans [A] ne peut PAS réapparaître en [B], [C] ou [D]. Avant d'écrire chaque bloc, vérifie que tu apportes un angle nouveau.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
I. RÈGLES HTML — NON NÉGOCIABLES (FORME INTOUCHABLE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. DESIGN ET IMAGERIE INTOUCHABLES
   Ne modifie JAMAIS le CSS, les couleurs, les polices, les icônes <i class="fa-...">, la structure des divs, les classes, ni les dimensions de page.
   Tu ne changes pas non plus les titres de section fixes du gabarit (« Notre Analyse », « Points Clés & Vigilance », « NOTE GLOBALE », « Projets Phares & Adéquation », en-têtes du tableau).
   Tu remplis UNIQUEMENT le texte des placeholders {{...}} et le contenu des zones prévues (.point-card, <tr> du tableau).

2. PLACEHOLDERS OPAQUES
   - src="LOGO_PLACEHOLDER" : conserver tel quel dans toutes les balises <img>.
   - LINKEDIN_CONTACT_ITEM_PLACEHOLDER : conserver tel quel dans la .contact-bar.
   - La .contact-bar contient UNIQUEMENT email, téléphone et ce placeholder. Aucun autre champ.

3. NETTOYAGE
   Supprimer tout crochet [cite], balise de source ou mention "Source" dans le texte généré.

4. PIED DE PAGE
   Remplacer {{PIED_DE_PAGE_COMMERCIAL}} dans les deux pages par :
   - "Commercial : Warren" → §PIED_WARREN§
   - "Commercial : Helder" → §PIED_HELDER§
   - "Commercial : Bruno" → §PIED_BRUNO§
   C'est la SEULE mention du cabinet autorisée dans tout le dossier. Elle appartient au gabarit : tu la reproduis à l'identique, sans jamais la commenter ni l'étendre.

5. OUTPUT
   Générer EXACTEMENT 2 pages, soit EXACTEMENT 2 blocs <div class="page">...</div> entre <body> et </body>.
   - Bloc 1 = page 1 (Présentation, Notre Analyse, Points Clés)
   - Bloc 2 = page 2 (Score Card + Projets Phares & Adéquation, dans cet ordre, dans la même page)
   Le CV est ajouté automatiquement après (pages 3+) — tu n'as PAS à le générer.
   Retourner UNIQUEMENT le HTML complet, sans markdown (pas de ```html), sans commentaire.
   CONTRAINTE A4 STRICTE : la page 2 doit tenir sur un seul A4. Le tableau Score Card + le bloc Projets Phares ne doivent JAMAIS déborder. C'est le risque n°1 du dossier — respecte impérativement les limites de longueur ci-dessous.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
II. VOIX ET NARRATION — LE DOSSIER PARLE DU CANDIDAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Le lecteur doit lire une analyse de profil, pas le compte rendu d'un processus de recrutement. Le sujet de chaque phrase est le candidat, son parcours, son périmètre, ses réalisations.

INTERDICTION ABSOLUE — ces mots et tournures ne doivent JAMAIS apparaître dans le texte généré :
- « le chasseur », « notre chasseur », « la chasseuse », « le consultant en charge », « notre consultant », « le recruteur », « notre cabinet », « Entourage » dans le corps du texte.
- « le brief », « d'après le brief », « selon le brief », « dans le brief », « non couvert dans le brief », « le brief ne précise pas ».
- Tout récit de la prise d'information : « nous avons rencontré », « nous avons échangé », « lors de notre entretien », « lors de nos échanges », « il nous a confié », « elle nous a indiqué », « le candidat nous a précisé », « selon nos observations », « d'après nos échanges ».

À la place : énonce le fait directement, au présent, comme une caractéristique du profil.
- ✗ « Le chasseur souligne qu'il a piloté deux intégrations. » → ✓ « Il a piloté deux intégrations post-acquisition. »
- ✗ « Il nous a indiqué viser 125k€. » → ✓ « Prétentions : 125k€ fixe + 20% variable. »
- ✗ « Le brief ne couvre pas ce critère. » → ✓ « Point à approfondir en entretien. »

Seule projection autorisée vers le processus : « à approfondir en entretien » / « à valider en entretien », en fin de phrase, et uniquement là où les règles ci-dessous le prévoient.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
III. TON ET REGISTRE — NIVEAU CABINET EXECUTIVE SEARCH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REGISTRE ATTENDU : executive search haut de gamme (Korn Ferry, Spencer Stuart, Egon Zehnder). Le texte doit pouvoir être lu tel quel par un président de directoire. Premium, sobre, assuré, ENGAGEANT — mais factuel et droit au but. Agréable à lire, impactant, sans verbiage.
- Phrases courtes, affirmatives, denses. Présent de l'indicatif. Voix active. Aucune liaison superflue.
- Registre soutenu et professionnel : pas de familiarité, pas d'oral, pas d'abréviation (« resp. », « exp. »), pas d'emoji, pas de point d'exclamation.
- Assurance sans emphase : on affirme un fait, on ne le vend pas. La force vient de la précision du fait, jamais de l'adjectif qui l'accompagne.
- Vocabulaire : termes métier exacts issus du brief (marchés, scope, opérations, réglementations, outils, stack). Jamais de généralités.
- Chaque affirmation est étayée par un fait précis du brief.
- Le candidat est désigné par son PRÉNOM uniquement, ou par un neutre (« le profil », « la candidate »). Jamais de nom de famille.

MOTS ET FORMULES INTERDITS (liste exhaustive) :
- Superlatifs à outrance : "excellent", "remarquable", "impressionnant", "exceptionnel", "très fort", "de très haut niveau", empilements d'adjectifs élogieux. Un superlatif ponctuel et justifié est toléré ; la surenchère ne l'est pas.
- Formules marketing : "nous sommes ravis", "nous avons le plaisir", "c'est avec enthousiasme", "candidat rare", "perle rare", "pépite", "coup de cœur", "profil incontournable".
- Adjectifs vagues : "bonne expérience", "profil intéressant", "belle trajectoire", "riche expérience", "grande expertise", "solide".
- Généralités : "le sens des responsabilités", "l'adaptabilité", "la rigueur", "le leadership naturel".
- Inférences psychologiques non sourcées : "motivé par", "à l'aise avec", "appétence pour", "posture de", "capacité à" (sauf reprise littérale du brief).
- Reformulations : un fait cité dans une section ne peut PAS être reformulé dans une autre.
- INTERDIT FORMEL ABSOLU : ne JAMAIS écrire que les prétentions salariales du candidat sont "en adéquation avec le budget", "alignées avec l'enveloppe", "cohérentes avec la fourchette", ni aucune variante. Tu reportes les chiffres bruts, sans commentaire sur leur adéquation au budget de l'entreprise cliente.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IV. RÈGLE ANTI-RÉPÉTITION — ABSOLUE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Les quatre sections sont strictement COMPLÉMENTAIRES et n'éclairent JAMAIS le même angle :

- [A] Notre Analyse → vue haute, 4 phrases max : profil synthétique + pertinence pour LE POSTE + pertinence pour L'ENTREPRISE + motivations (clôture). Pas de chiffres détaillés.
- [B] Points Clés & Vigilance → faits opérationnels chiffrés du brief : rémunération (actuel + prétentions) en premier, 2-3 atouts factuels, 0-1 vigilance UNIQUEMENT si le brief la signale.
- [C] Score Card → angle "critères du poste". Chaque ligne apporte un argument NOUVEAU lié à la note, qui n'a PAS été utilisé en [A] ni en [B].
- [D] Projets Phares → les 3 réalisations concrètes du brief, en mode contexte + action + résultat.

Avant d'écrire chaque bloc, demande-toi : "Ce fait a-t-il déjà été utilisé ailleurs ?" Si oui, change d'angle ou de fait. Diversifie systématiquement le contenu d'un bloc à l'autre.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
V. CONTENU PAR SECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PAGE 1 — PRÉSENTATION

[A] NOTRE ANALYSE — 4 PHRASES MAXIMUM, STRUCTURE IMPOSÉE
    Objectif : donner au DRH une lecture premium, attractive et engageante du candidat en 4 phrases — pas un résumé de CV, pas une thèse marketing, pas une énumération.
    Structure (1 phrase par bloc, dans cet ordre) :
    1) PROFIL SYNTHÉTIQUE — qui est le candidat aujourd'hui (poste / signature métier / spécialité dominante), en une phrase dense.
    2) PERTINENCE POSTE — pourquoi son périmètre / ses environnements collent au job recherché, en une phrase précise.
    3) PERTINENCE ENTREPRISE — pourquoi il s'inscrit dans le contexte spécifique de l'entreprise cliente (taille, secteur, enjeu, contexte de transformation), en une phrase ancrée.
    4) MOTIVATIONS — ce qui le tire vers ce poste, tel qu'exprimé dans le brief. Une phrase concise, ton humain, clôture du paragraphe. Si le brief ne dit rien des motivations, tu SUPPRIMES cette phrase — tu ne la devines pas.
    Règles :
    - 4 phrases MAXIMUM, environ 60 à 90 mots au total. Si le brief est silencieux sur un bloc, tu peux fusionner en 3 phrases — JAMAIS plus de 4.
    - PRÉNOM uniquement quand tu nommes le candidat. Le candidat est le sujet des phrases, jamais le cabinet.
    - Phrases courtes, denses, sans liaisons inutiles. Agréable à lire, impactant.
    - AUCUN chiffre détaillé (les chiffres vont en [B], [C], [D]).
    - AUCUNE réserve ici : cette section met le profil en avant. Une limite ne s'exprime qu'en [B] ou [C], et seulement si le brief la signale.
    - INTERDITS : salaires, notes scorecard, énumération de projets, narratif CV, listing de postes, "candidat motivé par" hors brief, autosatisfaction, formules marketing, toute mention du chasseur, du brief ou de l'entretien de qualification.

[B] POINTS CLÉS & VIGILANCE — 3 à 5 .point-card, ORDRE IMPOSÉ, 100% ISSU DU BRIEF
    Objectif : faits opérationnels issus du brief (PAS du CV). Ne reformule jamais [A].
    Structure obligatoire DANS CET ORDRE :
    → CARD 1 — "Rémunération" (TOUJOURS EN PREMIER, OBLIGATOIRE) :
       UNE SEULE card qui affiche le salaire ACTUEL et les PRÉTENTIONS, tels que renseignés dans le brief.
       Format conseillé du <p> : "Actuel : XXk€. Prétentions : YYk€." (ajouter variable / package / BSPCE si présents au brief).
       Si l'un des deux volets est absent du brief : "Non communiqué — à préciser." pour ce volet uniquement.
       INTERDICTION ABSOLUE d'écrire que ces prétentions sont "en adéquation avec le budget", "alignées avec l'enveloppe", "cohérentes avec la fourchette client", ou toute formule équivalente. Tu reportes les chiffres, point final.
    → CARDS SUIVANTES — "Atout" : 2 OU 3 atouts factuels TIRÉS DU BRIEF (équipe de X personnes managée, certification explicite, environnement traversé, scope géographique, levée/budget piloté, secteur ou outil spécifique mentionné). Choisis les plus démonstratifs pour le poste. MAXIMUM 3 atouts. Pas un de plus.
    → DERNIÈRE CARD — "Point de vigilance" : UNE SEULE card, et UNIQUEMENT si le brief signale EXPLICITEMENT un point à valider (mobilité, scope partiel, disponibilité, expérience limitée sur un volet, prétentions tendues, préavis long). 
       Si le brief ne signale aucune réserve : tu n'écris AUCUNE card vigilance. Tu n'en inventes pas une, tu n'en déduis pas une d'un manque d'information, tu ne transformes pas un silence du brief en réserve. Un dossier à 3 ou 4 cards sans vigilance est un dossier VALIDE et attendu.
    Total possible : 3 cards minimum (1 rému + 2 atouts) à 5 cards maximum (1 rému + 3 atouts + 1 vigilance). Jamais en dehors de cette fourchette.
    Source : EXCLUSIVEMENT le brief. Ne va PAS chercher dans le CV pour fabriquer un atout.
    INTERDITS : reformuler [A], anticiper [C], aller chercher un atout dans le CV, inventer une vigilance non signalée, commenter le budget de l'entreprise cliente, recopier un projet qui ira en [D], mentionner le chasseur ou le brief.
    Format par card : titre court (2-4 mots) + une phrase factuelle.
    HTML : <div class="point-card"><div class="point-icon"><i class="fa-solid fa-check"></i></div><div class="point-content"><h4>Titre</h4><p>Description</p></div></div>

PAGE 2 — SCORE CARD + PROJETS PHARES (les deux sur la même page A4, dans cet ordre)

[C] ÉVALUATION — tableau 4 critères, ANGLE COMPLÉMENTAIRE OBLIGATOIRE
    RÈGLE CRITIQUE : Les critères et leurs notes (/5) sont fournis EXPLICITEMENT dans le prompt sous "ÉVALUATION PAR CRITÈRE".
    → Utilise EXACTEMENT ces critères et ces notes. Ne les modifie pas, ne les arrondis pas.
    → Note globale = moyenne arithmétique des notes fournies, sur 5. JAMAIS sur 10.

    ANGLE OBLIGATOIRE — COMPLÉMENTAIRE, NON RÉPÉTITIF :
    Chaque ligne du tableau apporte un argument NOUVEAU, qui n'a PAS été utilisé en [A] ni en [B], et qui n'est PAS une paraphrase du CV. Tu ne reformules pas l'analyse — tu justifies LA NOTE par un fait précis du brief, lié AU CRITÈRE.
    Méthode :
    1. Identifie dans le brief les éléments qui se rapportent DIRECTEMENT à ce critère.
    2. Calibre l'argument sur la note attribuée :
       - Note haute (≥4) → le fait le plus fort et le plus précis dont tu disposes, énoncé avec assurance.
       - Note moyenne (3 / 3.5) → constat nuancé : ce qui est acquis, puis ce qui reste à confirmer — uniquement si le brief permet de nommer cet écart.
       - Note basse (≤2.5) → l'écart est nommé factuellement, sans jugement (ex. "scope partiel sur X", "expérience limitée sur Y"), et uniquement s'il ressort du brief.
    3. Le contenu doit refléter la note. Pas de justification flatteuse pour une note basse, pas de constat tiède pour une note haute.
    4. Si le brief ne fournit aucun élément sur ce critère, écris exactement : "Point à approfondir en entretien." Tu n'inventes pas de justification et tu ne vas pas chercher dans le CV pour combler. Tu ne mentionnes jamais le brief comme raison.
    → Format : <tr><td class="score-cat">Critère</td><td class="score-val">X.X / 5</td><td class="score-txt">Analyse.</td></tr>
    LONGUEUR STRICTE NON NÉGOCIABLE : chaque analyse de critère = 1 à 2 phrases, 20 à 35 mots MAX (idéalement 25-30). Plus court qu'une analyse complète, c'est volontaire — la page 2 doit aussi accueillir 3 projets en bas.

[D] PROJETS PHARES & ADÉQUATION (bloc texte en bas de la page 2, structure graphique inchangée)
    Objectif : les 3 réalisations majeures du candidat TELLES QUE MENTIONNÉES DANS LE BRIEF (pas dans le CV), choisies pour leur lien direct avec les enjeux du poste. C'est la section qui doit donner envie de rencontrer le candidat : sélectionne les opérations les plus structurantes et les résultats les plus tangibles que le brief fournit.
    Source : EXCLUSIVEMENT le brief. Tu n'extrais AUCUN projet du CV pour étoffer ce bloc. Le CV est joint à la fin pour que le lecteur puisse compléter de lui-même.

    FORMAT — texte plat à insérer dans {{TEXTE_PROJETS_PHARES}} :
    - 3 projets séparés par <br><br>.
    - Structure d'un projet : "<strong>Intitulé court (entreprise) :</strong> 1 à 2 phrases qui combinent contexte + action + résultat chiffré si le brief le donne."
    - Pas de tableau, pas de div, pas de classe CSS — juste du texte avec <strong> et <br>.

    LONGUEUR STRICTE NON NÉGOCIABLE (sinon le 3ème projet sera coupé du PDF) :
    - EXACTEMENT 3 projets, ni 2 ni 4.
    - Chaque projet : 2 à 3 phrases, 40 à 55 mots MAX (titre <strong> compris).
    - Total du bloc Projets Phares : 150 mots MAX, AUCUNE EXCEPTION.
    - Vise 45-50 mots par projet pour donner de la matière substantielle — la Score Card a été compactée justement pour libérer ce budget.

    RÈGLES :
    - Si le brief ne fournit pas de résultat chiffré pour un projet, décris l'action sans chiffre — n'invente pas et n'emprunte pas au CV.
    - Si le brief ne propose pas 3 projets identifiables, choisis les 3 éléments les plus structurants/concrets qu'il mentionne (mission, dossier, transformation, dispositif) — toujours sans aller piocher dans le CV.
    - Si possible, structure ainsi : 1ère phrase = contexte + action ; 2ème phrase courte = résultat/impact concret.
    INTERDITS : répéter la trajectoire globale de [A], reprendre les faits déjà cités en [B], reformuler le tableau [C], aller chercher un projet ou un chiffre dans le CV, inventer un résultat absent du brief, dépasser 150 mots au total, dépasser 55 mots pour un projet, mettre moins ou plus de 3 projets, mentionner le chasseur ou le brief.
"""

# Le pied de page reprend la fiche consultant du site (utils/equipe.py).
from utils import equipe as _equipe
DOSSIER_SYSTEM_PROMPT = DOSSIER_SYSTEM_PROMPT.replace("§PIED_WARREN§", _equipe.ligne_pied_de_page("Warren")).replace(
    "§PIED_HELDER§", _equipe.ligne_pied_de_page("Helder")).replace("§PIED_BRUNO§", _equipe.ligne_pied_de_page("Bruno"))

REVISION_SYSTEM_PROMPT = """Tu corriges les dossiers de présentation candidats d'Entourage Recrutement, cabinet de chasse spécialisé en finance et technologie.
Tu reçois les pages 1 et 2 d'un dossier HTML existant (page 1 : Analyse + Points Clés ; page 2 : Score Card + Projets Phares), le brief initial, les notes par critère, et des instructions de correction.

PRINCIPES FONDATEURS
- Les corrections reçues sont la SOURCE PRIMAIRE absolue : applique-les littéralement, sans réinterprétation.
- ZÉRO INVENTION : tu n'ajoutes aucun fait, aucun chiffre, aucune inférence (personnalité, motivation, posture) qui ne soit explicitement écrit dans les corrections ou dans le brief. Face à un doute, tu écris moins.
- AUCUNE RÉSERVE INVENTÉE : une vigilance, une limite, un « à confirmer » ne s'écrivent QUE si les corrections ou le brief les signalent explicitement. Tu ne fabriques jamais une nuance pour « équilibrer » le propos. Si une correction supprime la seule vigilance, le dossier reste sans card vigilance — c'est valide.
- METTRE LE CANDIDAT EN AVANT — SUR DES FAITS : le dossier doit donner envie de rencontrer ce candidat. Tu retiens les faits les plus démonstratifs du brief et tu les énonces nettement. Mettre en avant n'est jamais embellir ni extrapoler.
- LE BRIEF est la source des pages 1 et 2. Le CV est joint en fin de dossier comme complément et ne doit PAS servir à étoffer ces deux pages.
- PRÉNOM uniquement : le candidat est désigné par son prénom partout (dans {{NOM_CANDIDAT}} et dans le corps du texte), jamais par son nom de famille.

VOIX ET NARRATION — LE DOSSIER PARLE DU CANDIDAT
Le sujet de chaque phrase est le candidat, jamais le cabinet ni la façon dont l'information a été recueillie.
Ces mots et tournures ne doivent JAMAIS apparaître dans le texte : « le chasseur », « notre chasseur », « le consultant en charge », « notre consultant », « le recruteur », « notre cabinet », « le brief », « d'après le brief », « selon le brief », « dans le brief », « nous avons rencontré », « nous avons échangé », « lors de notre entretien », « il nous a confié », « elle nous a indiqué », « le candidat nous a précisé », « selon nos observations ».
Énonce le fait directement, au présent : ✗ « Le chasseur souligne qu'il a piloté deux intégrations. » → ✓ « Il a piloté deux intégrations post-acquisition. »
Seule projection autorisée vers le processus : « à approfondir en entretien » / « à valider en entretien ». Si un critère n'est couvert par aucun élément, écris exactement : "Point à approfondir en entretien."
Exception unique : le pied de page « Responsable de chasse : … » appartient au gabarit — tu le reproduis à l'identique.

RÈGLES HTML — NON NÉGOCIABLES (FORME ET IMAGERIE INTOUCHABLES)
1. Ne modifie JAMAIS le CSS, les couleurs, les polices, les icônes <i class="fa-...">, les classes, la structure des divs, ni les titres de section fixes du gabarit (« Notre Analyse », « Points Clés & Vigilance », « NOTE GLOBALE », « Projets Phares & Adéquation », en-têtes du tableau). Tu ne touches qu'au TEXTE.
2. Conserver EXACTEMENT : src="LOGO_PLACEHOLDER" et LINKEDIN_CONTACT_ITEM_PLACEHOLDER.
3. Notes du tableau toujours /5 (jamais /10). Note globale = moyenne des critères.
4. Retourner UNIQUEMENT le HTML complet des pages 1 et 2, sans markdown, sans explication.
5. Ne pas ajouter de page 3 ou suivante — le CV est géré séparément.
6. Chaque page doit tenir sur un A4 strict. Si une correction allonge une section, raccourcis ailleurs pour éviter toute coupure visuelle en PDF.
   Page 2 (Score Card + Projets Phares) — LIMITES STRICTES : analyses critères = 20-35 mots chacune ; EXACTEMENT 3 projets phares, 40-55 mots chacun, 150 mots MAX au total. Si tu dépasses, le 3ème projet sera coupé du PDF.
   Page 1 — [A] Notre Analyse : 4 phrases MAX (profil synthétique / pertinence poste / pertinence entreprise / motivations), aucune réserve dans cette section. [B] Points Clés : card Rémunération en premier (salaire actuel + prétentions, JAMAIS « en adéquation avec le budget » ni équivalent), puis 2-3 atouts, puis 0 ou 1 vigilance UNIQUEMENT si elle est explicitement signalée. Total 3 à 5 cards.

ANTI-RÉPÉTITION
- Chaque section garde son rôle distinct : [A] vue haute, [B] faits opérationnels, [C] angle critère, [D] projets concrets.
- Un fait utilisé dans une section ne doit pas réapparaître ailleurs. Quand une correction déplace un fait, retire-le de l'ancienne section.

REGISTRE À MAINTENIR — NIVEAU CABINET EXECUTIVE SEARCH
- Executive search haut de gamme (Korn Ferry, Spencer Stuart, Egon Zehnder). Le texte doit pouvoir être lu tel quel par un président de directoire.
- Ton factuel, analytique, premium, assuré, ENGAGEANT. Agréable à lire, impactant, droit au but.
- Phrases courtes, affirmatives. Présent de l'indicatif, voix active. Vocabulaire métier précis.
- Registre soutenu : pas de familiarité, pas d'oral, pas d'abréviation, pas d'emoji, pas de point d'exclamation.
- Pas de superlatifs à outrance, pas d'adjectifs vagues, pas d'inférence psychologique non sourcée, pas de formules marketing ("perle rare", "pépite", "coup de cœur").
- Appliquer uniquement les corrections demandées. Ne pas réécrire ce qui n'est pas visé.
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

    # Le raisonnement adaptatif consomme des jetons avant la réponse :
    # plafond large + effort faible pour cette extraction simple.
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": content}],
        extra_body={"output_config": {"effort": "low"}},
    )

    raw = response_text(response).strip()
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
        "- SOURCE UNIQUE pour les pages 1 et 2 : le CONTEXTE GÉNÉRAL ci-dessus. Le CV est joint à la "
        "fin (pages 3+) comme COMPLÉMENT pour le lecteur — il ne doit PAS servir à étoffer [A], [B], [C] ou [D].\n"
        "- ZÉRO INVENTION : si ce n'est pas dans le brief, ça n'existe pas. Pas d'inférence, pas de thèse, "
        "pas de motivation devinée, pas de chiffre approché. Face à un doute, écris moins.\n"
        "- AUCUNE RÉSERVE INVENTÉE : une vigilance, une limite ou un « à confirmer » ne s'écrivent QUE si le "
        "brief les signale explicitement. Un silence du brief n'est PAS une réserve. Pas de nuance ajoutée "
        "pour « équilibrer » le propos.\n"
        "- LE DOSSIER PARLE DU CANDIDAT, JAMAIS DU CHASSEUR : n'écris jamais « le chasseur », « le consultant », "
        "« le recruteur », « notre cabinet », « le brief », « d'après le brief », « nous avons rencontré », "
        "« il nous a confié », ni aucune variante. Énonce le fait directement, au présent, comme une "
        "caractéristique du profil. Seule exception : le pied de page « Responsable de chasse : … », qui "
        "appartient au gabarit.\n"
        "- METTRE LE CANDIDAT EN AVANT, SUR DES FAITS : retiens les éléments les plus démonstratifs du brief "
        "(périmètre le plus large, opération la plus structurante, résultat le plus tangible) et énonce-les "
        "nettement. Mettre en avant = choisir le bon fait, pas ajouter des adjectifs.\n"
        "- REGISTRE : executive search haut de gamme (Korn Ferry, Spencer Stuart, Egon Zehnder). Phrases courtes, "
        "affirmatives, présent de l'indicatif, voix active. Soutenu, sobre, assuré. Pas de familiarité, "
        "pas d'abréviation, pas d'emoji, pas de point d'exclamation, pas de formule marketing.\n"
        "- FORME ET IMAGERIE INTOUCHABLES : ne change ni le CSS, ni les couleurs, ni les polices, ni les icônes "
        "<i class=\"fa-...\">, ni les classes, ni les titres de section du gabarit. Tu ne remplis que le texte.\n"
        "- PRÉNOM UNIQUEMENT : utilise EXCLUSIVEMENT le prénom du candidat dans {{NOM_CANDIDAT}} et partout "
        "dans le dossier. Jamais le nom de famille, jamais M./Mme, jamais le nom complet.\n"
        "- [A] NOTRE ANALYSE — 4 PHRASES MAX, structure imposée : "
        "1) profil synthétique, 2) pertinence pour le poste, 3) pertinence pour l'entreprise, 4) motivations "
        "(à supprimer si le brief n'en dit rien). Premium, attractif, engageant, droit au but. 60-90 mots au "
        "total. Pas de chiffres détaillés, pas de listes, pas de narratif CV, AUCUNE réserve dans cette section.\n"
        "- [B] POINTS CLÉS — ordre imposé, 3 à 5 cards : "
        "CARD 1 obligatoire = Rémunération (Actuel : XXk€. Prétentions : YYk€.) — INTERDICTION ABSOLUE d'écrire "
        "que c'est « en adéquation avec le budget » ou toute formule équivalente, tu reportes les chiffres point. "
        "Puis 2 à 3 atouts factuels TIRÉS DU BRIEF (pas du CV), MAXIMUM 3. "
        "Puis 0 ou 1 card de vigilance, UNIQUEMENT si le brief la signale explicitement. Sans réserve au brief, "
        "le dossier n'a PAS de card vigilance — c'est valide et attendu.\n"
        "- [C] SCORE CARD : utilise EXACTEMENT les notes ci-dessus. Pour chaque critère, un argument NOUVEAU "
        "(pas déjà dit en [A] ni en [B]) calibré sur la note (haute = fait fort, moyenne = constat nuancé, "
        "basse = écart nommé). Si le brief ne fournit aucun élément sur le critère, écris exactement "
        "« Point à approfondir en entretien. » — NE VA PAS chercher dans le CV pour combler et ne mentionne "
        "jamais le brief comme raison.\n"
        "- [D] PROJETS PHARES (bas de page 2) : EXACTEMENT 3 réalisations TIRÉES DU BRIEF (pas du CV) en lien "
        "direct avec la scorecard, sans inventer de chiffres absents du brief. Format texte plat dans "
        "{{TEXTE_PROJETS_PHARES}} : 3 projets séparés par <br><br>, intitulé en <strong>, 2 à 3 phrases par "
        "projet, 40-55 mots par projet, 150 mots MAX au total. Vise 45-50 mots par projet.\n"
        "- ANTI-RÉPÉTITION : un fait utilisé dans une section ne doit PAS réapparaître ailleurs. Les 4 blocs "
        "sont strictement complémentaires, jamais redondants.\n"
        "- MISE EN PAGE A4 — RISQUE N°1 : la page 2 doit tenir SANS DÉBORDER (Score Card 4 critères + 3 Projets "
        "Phares sur le même A4). Limites strictes NON NÉGOCIABLES : chaque analyse scorecard = 20-35 mots ; "
        "chaque projet phare = 40-55 mots ; total Projets Phares = 150 mots MAX. Si tu dépasses, le 3ème projet "
        "sera COUPÉ du PDF.\n"
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

    Budgets (calibrated after the Score Card was compacted ~15% to free room for richer projets) :
    - Each score card analysis : ≤ 35 words
    - Each projet phare : ≤ 55 words
    - Total projets phares block : ≤ 150 words, exactly 3 projets
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
        if total_words > 150:
            warnings.append(f"Projets Phares : {total_words} mots au total (max 150) — le 3ème projet risque d'être coupé du PDF.")
        # Count projets (separated by <br><br>)
        parts = re.split(r"<br\s*/?>\s*<br\s*/?>", pp_html, flags=re.IGNORECASE)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) != 3:
            warnings.append(f"Projets Phares : {len(parts)} projet(s) détecté(s) au lieu de 3.")
        for i, part in enumerate(parts, start=1):
            wc = _count_words(part)
            if wc > 55:
                warnings.append(f"Projet phare #{i} : {wc} mots (max 55) — réduire pour éviter coupure A4.")

    return warnings


def inject_logo_and_linkedin(html: str, logo_b64: str, linkedin_url: str) -> str:
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


# Sonnet 5 raisonne avant de répondre, et ces tokens de réflexion comptent dans
# max_tokens : mesuré à ~10 600 tokens de sortie pour un dossier complet en effort
# "medium", il faut de la marge, sinon le HTML sort tronqué.
MAX_TOKENS_DOSSIER = 24000

# Effort de raisonnement (mesuré sur un dossier réel, cf. README) :
#   low    ~35 s  — trop juste : titres de Points Clés génériques ("Atout", "Atout")
#   medium ~98 s  — qualité conforme au brief, coût maîtrisé  ← retenu
#   high  ~193 s  — même qualité, 2,5× plus lent et plus cher
EFFORT_DOSSIER = "medium"

# extra_body : le SDK installé (0.40.x) ne connaît pas encore output_config comme
# paramètre nommé, mais le corps JSON brut passe quelle que soit la version.
DOSSIER_REQUEST_EXTRA = {"output_config": {"effort": EFFORT_DOSSIER}}

REPAIR_INSTRUCTIONS = (
    "Reprends le HTML précédent et corrige UNIQUEMENT les points listés, sans rien changer d'autre : "
    "ni le CSS, ni les couleurs, ni les polices, ni les icônes, ni les classes, ni les titres de section "
    "du gabarit. Rappels non négociables :\n"
    "- Chaque analyse Score Card ≤ 35 mots\n"
    "- EXACTEMENT 3 projets phares\n"
    "- Chaque projet ≤ 55 mots\n"
    "- Total Projets Phares ≤ 150 mots\n"
    "- Le dossier parle DU CANDIDAT : jamais « le chasseur », « le consultant », « le recruteur », "
    "« notre cabinet », « le brief », « d'après le brief », « nous avons rencontré », « il nous a confié » "
    "ni aucune variante. Énonce le fait directement, au présent. Le pied de page "
    "« Responsable de chasse : … » appartient au gabarit et reste inchangé.\n"
    "- Si un critère n'est couvert par aucun élément, écris exactement « Point à approfondir en entretien. »\n"
    "- Aucune réserve inventée : une vigilance ne s'écrit que si elle est explicitement signalée.\n"
    "- Le gabarit graphique est intouchable : conserve src=\"LOGO_PLACEHOLDER\" sur les deux pages, "
    "LINKEDIN_CONTACT_ITEM_PLACEHOLDER, les classes hunter-box / points-grid / score-table et les "
    "titres de section, à l'identique.\n"
    "Retourne UNIQUEMENT le HTML corrigé, sans markdown, sans commentaire."
)

# Tournures qui trahissent le processus de recrutement au lieu de parler du candidat.
# Le pied de page « Responsable de chasse : … » appartient au gabarit : il est exclu du scan.
FORBIDDEN_MENTION_PATTERNS: list[tuple[str, str]] = [
    (r"chasseu(?:r|se)s?\b", "mention du chasseur"),
    (r"\bbriefs?\b", "mention du brief"),
    (r"\b(?:notre|nos|le)\s+consultants?\b", "mention du consultant"),
    (r"\brecruteurs?\b", "mention du recruteur"),
    (r"\bnotre\s+cabinet\b", "mention du cabinet"),
    (r"\bnous\s+(?:avons|l'avons)\s+\w+", "récit de la prise d'information (« nous avons… »)"),
    (r"\bnous\s+a\s+(?:confié|indiqué|précisé|déclaré|dit|expliqué|fait)\b",
     "récit de la prise d'information (« nous a… »)"),
    (r"\bnous\s+(?:a|ont)\s+parlé\b", "récit de la prise d'information"),
    (r"\blors\s+de\s+(?:notre|nos|cet|l')\s*(?:entretien|échange|entrevue)",
     "renvoi à l'entretien de qualification"),
    (r"\bselon\s+nos?\s+(?:observations|échanges|constats)\b", "renvoi aux observations"),
    (r"\bd['’]après\s+nos?\s+(?:observations|échanges)\b", "renvoi aux observations"),
    (r"\ble\s+candidat\s+nous\b", "récit de la prise d'information"),
]


def extract_visible_text(html: str) -> str:
    """Plain text a reader actually sees — CSS, comments and the template footer excluded."""
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.DOTALL)
    html = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<div class="footer">.*?</div>', " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html)


def check_forbidden_mentions(html: str) -> list[str]:
    """Le dossier doit parler du candidat, jamais du chasseur ni de la façon dont
    l'information a été recueillie. Le prompt le demande ; ceci le vérifie."""
    text = extract_visible_text(html)
    problems: list[str] = []
    for pattern, label in FORBIDDEN_MENTION_PATTERNS:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            excerpt = text[max(0, m.start() - 40): m.end() + 40].strip()
            problems.append(f"{label} — à reformuler côté candidat : « …{excerpt}… »")
    return problems


def audit_dossier_content(html: str) -> list[str]:
    """Toutes les règles vérifiables automatiquement : longueurs, voix, gabarit."""
    return (
        check_length_budgets(html)
        + check_forbidden_mentions(html)
        + check_template_integrity(html)
    )


def response_text(response) -> str:
    """Texte de la réponse, blocs de raisonnement exclus.

    Les modèles à raisonnement adaptatif (Sonnet 5, Opus 5…) renvoient un bloc
    `thinking` en premier : `response.content[0].text` y vaut None.
    """
    return "".join(b.text for b in response.content if b.type == "text")


def strip_code_fences(text: str) -> str:
    """Remove a ```html fence around the model output, whatever the surrounding whitespace."""
    text = text.strip()
    text = re.sub(r"^```[^\n]*\n", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def restore_template_shell(html: str) -> tuple[str, bool]:
    """Réimpose l'en-tête du gabarit (DOCTYPE, <head>, polices, Font Awesome, CSS).

    Le CSS et l'imagerie ne sont pas au modèle de les produire : à effort réduit il
    lui arrive de les recompresser, ce qui casse la mise en page A4. On restaure la
    coquille au lieu de la lui demander — le <body> généré est conservé tel quel.
    Retourne (html, restauré).
    """
    template = _load_template()
    m_tpl = re.search(r"\A(.*?<body[^>]*>)", template, re.DOTALL)
    m_gen = re.search(r"\A(.*?<body[^>]*>)", html, re.DOTALL)
    if not (m_tpl and m_gen):
        return html, False
    if m_tpl.group(1) == m_gen.group(1):
        return html, False
    return template[: m_tpl.end(1)] + html[m_gen.end(1):], True


# Éléments de gabarit que le modèle doit reproduire à l'identique dans le <body>.
TEMPLATE_LANDMARKS: list[tuple[str, str]] = [
    ('src="LOGO_PLACEHOLDER"', "placeholder du logo"),
    ("LINKEDIN_CONTACT_ITEM_PLACEHOLDER", "placeholder LinkedIn"),
    ('class="hunter-box"', "encadré Notre Analyse"),
    ('class="points-grid"', "grille Points Clés"),
    ('class="score-table"', "tableau Score Card"),
    ("Notre Analyse", "titre « Notre Analyse »"),
    ("Points Clés &amp; Vigilance", "titre « Points Clés & Vigilance »"),
    ("Projets Phares &amp; Adéquation", "titre « Projets Phares & Adéquation »"),
    ("NOTE GLOBALE", "bandeau « NOTE GLOBALE »"),
]


def check_template_integrity(html: str) -> list[str]:
    """Le gabarit graphique doit ressortir intact du modèle."""
    problems = [
        f"Élément de gabarit perdu : {label}."
        for marker, label in TEMPLATE_LANDMARKS
        if marker not in html
    ]
    if html.count('src="LOGO_PLACEHOLDER"') != 2:
        problems.append(
            f"Logo attendu sur les 2 pages, trouvé {html.count('src=\"LOGO_PLACEHOLDER\"')} fois."
        )
    return problems


def decode_model_html(response) -> str:
    """Sortie modèle → HTML exploitable : texte seul, sans fences, coquille du gabarit imposée."""
    html = strip_code_fences(response_text(response))
    html, _ = restore_template_shell(html)
    return html


def is_structurally_valid(html: str) -> bool:
    """Minimal shape a dossier must have to be worth keeping."""
    return (
        "</html>" in html
        and len(re.findall(r'<div class="page"', html)) == 2
        and '<td class="score-txt">' in html
    )


def repair_content_issues(html: str, issues: list[str], call_fn, prior_messages: list[dict]):
    """One automatic pass to fix A4 overflows and forbidden mentions.

    Returns (html, issues) — the retry is kept only if it actually improved things.
    """
    st.write("📏 Écart aux règles détecté — relance automatique pour corriger le texte…")
    correction_msg = (
        "Le HTML que tu viens de produire enfreint des règles non négociables du dossier. "
        "Points à corriger :\n\n"
        + "\n".join(f"- {w}" for w in issues)
        + "\n\n"
        + REPAIR_INSTRUCTIONS
    )
    retry_response = call_fn(
        prior_messages
        + [
            {"role": "assistant", "content": html},
            {"role": "user", "content": correction_msg},
        ]
    )
    retry_html = decode_model_html(retry_response)

    # Un HTML tronqué ou hors-format ne déclenche aucun warning de longueur : sans ce
    # garde-fou, il passerait pour "plus court donc meilleur" et écraserait le dossier.
    if not is_structurally_valid(retry_html):
        return html, issues

    new_issues = audit_dossier_content(retry_html)
    if len(new_issues) < len(issues):
        if new_issues:
            return retry_html, new_issues
        st.write("✅ Règles respectées après relance.")
        return retry_html, []
    return html, issues


def check_dossier_html(html: str, response) -> list[str]:
    """Structural sanity checks shared by the generation and the revision paths."""
    problems: list[str] = []
    if response.stop_reason == "max_tokens":
        problems.append(
            "Réponse interrompue (limite de tokens atteinte) — le HTML est probablement tronqué."
        )
    nb_pages = len(re.findall(r'<div class="page"', html))
    if nb_pages != 2:
        problems.append(f"Claude a produit {nb_pages} page(s) dossier au lieu de 2.")
    if "</html>" not in html:
        problems.append("Le HTML retourné est incomplet (balise </html> manquante).")
    if "LOGO_PLACEHOLDER" not in html:
        problems.append("Le placeholder du logo n'a pas été conservé — le logo n'apparaîtra pas.")
    return problems


def read_table_scores(html: str) -> list[float]:
    """Notes telles qu'affichées dans le tableau Score Card."""
    return [
        float(v.replace(",", "."))
        for v in re.findall(r'<td class="score-val">\s*(\d+(?:[.,]\d+)?)\s*/', html)
    ]


def enforce_global_score(html: str, criteria_scores: list[dict] | None = None) -> tuple[str, bool]:
    """La note globale est une moyenne arithmétique : on la calcule au lieu de la
    demander au modèle, qui se trompe d'un dixième de temps en temps.

    `criteria_scores` = notes saisies dans le formulaire (génération). En révision on
    passe None : les notes de référence sont alors celles du tableau corrigé, sinon une
    correction du type « mets Management à 2.5 » verrait sa note globale réécrite à
    partir de valeurs périmées.

    Seul le nombre est réécrit — le balisage, la classe et l'espacement sont conservés.
    Retourne (html, corrigé).
    """
    values = (
        [float(c["score"]) for c in criteria_scores]
        if criteria_scores
        else read_table_scores(html)
    )
    if not values:
        return html, False
    expected = round(sum(values) / len(values), 1)
    m = re.search(r'(<div class="score-big">)\s*(\d+(?:[.,]\d+)?)\s*(<span)', html)
    if not m:
        return html, False
    if abs(float(m.group(2).replace(",", ".")) - expected) < 0.05:
        return html, False
    return html[: m.start()] + f"{m.group(1)}{expected:.1f} {m.group(3)}" + html[m.end():], True


def check_scores_match(html: str, criteria_scores: list[dict]) -> list[str]:
    """Les notes du tableau sont saisies à la main : Claude ne doit jamais les changer."""
    if not criteria_scores:
        return []
    shown = sorted(read_table_scores(html))
    expected = sorted(float(c["score"]) for c in criteria_scores)
    if shown != expected:
        return [
            f"Notes du tableau modifiées par Claude : {shown} au lieu de {expected} — vérifie la Score Card."
        ]
    return []


@st.cache_data(max_entries=6, show_spinner=False)
def dossier_pdf(html: str) -> bytes:
    from utils.pdf_export import html_to_pdf
    return html_to_pdf(html)


def finalize_dossier(pages12_html: str, logo_b64: str, linkedin_url: str, pdf_bytes: bytes) -> str:
    """Pages 1+2 (placeholders intacts) → dossier complet prêt à télécharger."""
    html = inject_logo_and_linkedin(pages12_html, logo_b64, linkedin_url)
    if pdf_bytes:
        html = append_cv_pages(html, pdf_bytes)
    return html.replace("<body>", f"<body>\n{PRINT_BUTTON_HTML}", 1)


PRINT_BUTTON_HTML = """
<div class="no-print" style="position:fixed;top:20px;right:20px;z-index:9999;background:#FFD700;border-radius:8px;box-shadow:0 4px 15px rgba(0,0,0,0.3);">
  <button onclick="window.print()" style="background:#FFD700;color:#000;border:none;padding:12px 24px;font-size:14px;font-weight:800;cursor:pointer;border-radius:8px;font-family:sans-serif;letter-spacing:0.5px;">
    🖨️ Enregistrer en PDF
  </button>
</div>
<style>@media print { .no-print { display:none!important; } }</style>
"""


# ============================================================
# ENVOI AU CLIENT (Warren, 10 octobre 2026)
# ============================================================


def render_envoi_client(current_hash: str) -> None:
    """Après la version finale : l'envoi du dossier au client, par le site.

    L'email part au nom du RESPONSABLE DU MANDAT (pas de celui qui clique),
    aux interlocuteurs cochés « Reçoit le suivi », dossier en pièce jointe ;
    toute l'équipe du mandat en reçoit la copie et le candidat passe en Send-out.
    Le site refuse tant que quelque chose manque, et dit quoi."""
    from utils import site
    from utils.mandats_data import load_snapshot

    with st.container(border=True):
        st.markdown("**Envoyer au client**")
        fait = st.session_state.get("dossier_envoi")
        if fait and fait.get("hash") == current_hash:
            st.success(fait["message"])
            return

        mandat_id = st.session_state.get("dossier_mandat_id")
        contact = st.session_state.get("dossier_contact")
        mandat = next((x for x in load_snapshot()["mandats"] if x["id"] == mandat_id), None) if mandat_id else None
        if not mandat:
            st.caption("Choisissez la score card du mandat dans la liste, en haut : c'est elle qui relie le dossier au client.")
            return
        if not mandat.get("site_etat"):
            st.caption("Enregistrez d'abord la rubrique « 4 · Site » du mandat : interlocuteurs et espace candidat.")
            return
        if not contact:
            st.caption("Validez la version finale : le dossier part de la fiche Leonar du candidat.")
            return

        destinataires = [i.get("nom") or i.get("email") for i in (mandat.get("site") or {}).get("interlocuteurs") or []
                         if i.get("suivi") and i.get("email")]
        responsable = (mandat.get("site_etat") or {}).get("responsable") or mandat.get("responsable", "")
        if not destinataires:
            st.caption("Aucun interlocuteur du client n'est coché « Reçoit le suivi » dans la rubrique « 4 · Site » du mandat.")
            return
        st.caption(
            f"Au nom de {responsable}, à {', '.join(destinataires)}. Le dossier part en pièce jointe, "
            "toute l'équipe du mandat en reçoit la copie et le candidat passe en Send-out dans Leonar."
        )
        mot = st.text_area("Un mot pour le client (facultatif)", key="dossier_mot", height=80,
                           placeholder="Par exemple : son préavis est d'un mois, il est disponible dès la semaine prochaine.")
        with st.popover("Envoyer au client", icon=":material/send:", type="primary"):
            st.markdown(f"Envoyer la candidature de **{contact['nom']}** à {', '.join(destinataires)} ?")
            if st.button("Confirmer l'envoi", type="primary", key="dossier_envoi_ok"):
                try:
                    with st.spinner("Envoi…"):
                        r = site.envoyer_candidature(mandat, contact["id"], (mot or "").strip())
                except site.SiteError as e:
                    st.error(str(e))
                    return
                from datetime import datetime
                from zoneinfo import ZoneInfo
                quand = datetime.fromisoformat(r["le"].replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Paris"))
                message = (
                    f"Envoyé le {quand.strftime('%d/%m à %H:%M')} à {', '.join(r['destinataires'])}, "
                    f"au nom de {r['responsable']}. Toute l'équipe du mandat en a reçu la copie"
                    + (" et le candidat est passé en Send-out." if r.get("deplace") else ".")
                )
                if r.get("avertissement"):
                    message += " " + r["avertissement"]
                st.session_state["dossier_envoi"] = {"hash": current_hash, "message": message}
                st.rerun()


# ============================================================
# PAGE
# ============================================================
st.title("Dossier de candidature")

if not claude_api_key:
    st.error("❌ Clé API Claude manquante (ANTHROPIC_API_KEY ou CLAUDE_API_KEY)")
    st.stop()

if not HTML_MASTER_TEMPLATE:
    st.error("⚠️ Fichier `dossier_template.html` introuvable. Place-le à la racine du projet.")
    st.stop()

# --- LOGO ---
# Logo par défaut : logo_entourage.png du projet (l'upload ci-dessous permet de le remplacer)
if not st.session_state.get("dossier_logo_b64"):
    from utils.logo import load_default_logo_b64
    _default_logo = load_default_logo_b64()
    if _default_logo:
        st.session_state["dossier_logo_b64"] = _default_logo

with st.sidebar.expander("Remplacer le logo", expanded=not st.session_state.get("dossier_logo_b64")):
    logo_file = st.file_uploader(
        "Logo Entourage Recrutement (.png / .jpg)",
        type=["png", "jpg", "jpeg"],
        key="dossier_logo_upload",
        label_visibility="collapsed",
    )
    if logo_file:
        st.session_state["dossier_logo_b64"] = base64.b64encode(logo_file.read()).decode()
        st.success("Logo chargé ✓")

# --- FICHIERS + INFOS ---
col_left, col_right = st.columns(2)

with col_left:
    cv_file = st.file_uploader("CV du candidat (PDF)", type=["pdf"], key="dossier_cv")
    linkedin_url = st.text_input(
        "LinkedIn du candidat",
        placeholder="https://www.linkedin.com/in/prenom-nom/",
        key="dossier_linkedin",
    )
    commercial = st.radio(
        "Responsable de chasse",
        ["Warren", "Helder", "Bruno"],
        horizontal=True,
        key="dossier_commercial",
    )

with col_right:

    # Scorecards enregistrées dans les mandats (rubrique Mandats / Scorecard)
    try:
        from utils.mandats_data import list_saved_scorecards, fetch_bytes as fetch_mandat_file
        saved_scorecards = list_saved_scorecards()
    except Exception:
        saved_scorecards = []
    saved_idx = None
    if saved_scorecards:
        def _aligner_responsable():
            """Le responsable de chasse est celui du mandat choisi : c'est en
            son nom que le dossier partira chez le client."""
            i = st.session_state.get("dossier_scorecard_saved")
            if i is not None and i < len(saved_scorecards):
                resp = saved_scorecards[i]["mandat"].get("responsable")
                if resp in ("Warren", "Helder", "Bruno"):
                    st.session_state["dossier_commercial"] = resp

        saved_idx = st.selectbox(
            "Score card du poste",
            list(range(len(saved_scorecards))),
            format_func=lambda i: saved_scorecards[i]["label"],
            index=None,
            placeholder="Choisir un mandat…",
            key="dossier_scorecard_saved",
            on_change=_aligner_responsable,
        )
        with st.expander("Ancien mandat : charger un fichier"):
            scorecard_file = st.file_uploader(
                "Score card (.html ou .pdf)", type=["html", "htm", "pdf"],
                key="dossier_scorecard", label_visibility="collapsed",
            )
    else:
        scorecard_file = st.file_uploader(
            "Score card du poste (.html ou .pdf)",
            type=["html", "htm", "pdf"],
            key="dossier_scorecard",
        )

    # Le fichier chargé est prioritaire ; sinon, la scorecard choisie dans la liste
    sc_source = None
    if scorecard_file:
        st.session_state.pop("dossier_mandat_id", None)
        sc_source = {
            "key": f"sc_{scorecard_file.name}_{scorecard_file.size}",
            "name": scorecard_file.name,
            "ext": scorecard_file.name.rsplit(".", 1)[-1].lower(),
            "read": scorecard_file.read,
        }
    elif saved_idx is not None:
        _entry = saved_scorecards[saved_idx]
        st.session_state["dossier_mandat_id"] = _entry["mandat"]["id"]
        sc_source = {
            "key": f"mandat_{_entry['file']['id']}",
            "name": _entry["label"],
            "ext": "html",
            "read": lambda fid=_entry["file"]["id"]: fetch_mandat_file(fid),
        }

    if sc_source:
        file_cache_key = sc_source["key"]

        if st.session_state.get("dossier_scorecard_cache_key") != file_cache_key:
            with st.spinner("Extraction des critères..."):
                try:
                    sc_bytes = sc_source["read"]()
                    sc_ext = sc_source["ext"]
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
            st.caption(f":green[✓] {n} critères extraits de la score card")

st.divider()

# --- FORMULAIRE STRUCTURÉ (apparaît après extraction) ---
criteria = st.session_state.get("dossier_criteria", [])

if not criteria:
    st.caption("Choisis la score card du poste pour accéder à l'évaluation.")
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
                    # Streaming obligatoire : avec un max_tokens élevé, une requête
                    # non streamée dépasse le timeout HTTP du SDK.
                    with claude_client.messages.stream(
                        model=MODEL,
                        max_tokens=MAX_TOKENS_DOSSIER,
                        system=DOSSIER_SYSTEM_PROMPT,
                        messages=messages_payload,
                        extra_body=DOSSIER_REQUEST_EXTRA,
                        timeout=600.0,
                    ) as stream:
                        return stream.get_final_message()

                base_messages = [{"role": "user", "content": content_blocks}]
                response = _call_claude(base_messages)
                # Le CSS et l'en-tête viennent du gabarit, jamais du modèle.
                generated_html = strip_code_fences(response_text(response))
                generated_html, shell_restored = restore_template_shell(generated_html)
                if shell_restored:
                    st.write("🎨 En-tête et CSS du gabarit restaurés à l'identique.")

                st.write("🖼 Injection du logo et finalisation…")

                # --- GARDE-FOU 1 : structure du HTML ---
                for problem in check_dossier_html(generated_html, response):
                    st.warning(f"⚠️ {problem}")

                # --- GARDE-FOU 2 : longueurs page 2 + voix du dossier ---
                content_issues = audit_dossier_content(generated_html)
                if content_issues:
                    generated_html, content_issues = repair_content_issues(
                        generated_html, content_issues, _call_claude, base_messages
                    )
                content_issues += check_scores_match(generated_html, criteria_scores)
                for w in content_issues:
                    st.warning(f"⚠️ {w}")

                # --- GARDE-FOU 3 : la note globale est calculée, pas devinée ---
                generated_html, fixed_score = enforce_global_score(generated_html, criteria_scores)
                if fixed_score:
                    st.write("🔢 Note globale recalculée (moyenne des critères).")

                # Sauvegarde pages 1+2 (placeholders intacts) pour révisions
                st.session_state["dossier_html_pages12"] = generated_html
                st.session_state["dossier_pdf_bytes"] = pdf_bytes
                st.session_state["dossier_criteria_scores"] = criteria_scores
                st.session_state["dossier_brief"] = context.strip()
                st.session_state["dossier_version"] = 1
                st.session_state["dossier_history"] = []
                st.session_state.pop("dossier_revision_notice", None)

                st.write("📄 Conversion du CV en images…")
                final_html = finalize_dossier(
                    generated_html,
                    st.session_state["dossier_logo_b64"],
                    linkedin_url,
                    pdf_bytes,
                )

                st.session_state["dossier_html"] = final_html
                st.session_state.pop("dossier_validated_hash", None)  # nouveau dossier : rien de validé
                status.update(label="✅ Dossier généré !", state="complete")

            except Exception as e:
                status.update(label="❌ Erreur", state="error")
                st.error(f"Erreur : {e}")

# --- RÉSULTAT ---
if st.session_state.get("dossier_html"):
    html_content = st.session_state["dossier_html"]

    name_match = re.search(r'class="candidate-name">([^<]+)<', html_content)
    candidate_name = name_match.group(1).strip().replace(" ", "_") if name_match else "candidat"
    version = st.session_state.get("dossier_version", 1)

    # Une révision se termine par un st.rerun() : sans ce bloc, l'écran revient à
    # l'identique et le chasseur croit que sa correction n'a pas été prise en compte.
    notice = st.session_state.pop("dossier_revision_notice", None)
    if notice:
        if notice.get("undo"):
            st.success(f"↩️ Correction annulée — retour à la version {notice['version']}.")
        else:
            st.success(f"✅ Corrections appliquées — dossier en version {notice['version']}.")
            if notice.get("corrections"):
                with st.expander("Corrections prises en compte", expanded=False):
                    st.write(notice["corrections"])
        for problem in notice.get("problems", []):
            st.warning(f"⚠️ {problem}")

    version_suffix = f"_v{version}" if version > 1 else ""

    # --- Validation de la version finale (envoi sur la fiche Leonar) + PDF ---
    import hashlib
    from utils.pdf_export import html_to_pdf, PdfExportError
    from utils import leonar

    pdf_name = f"Dossier de candidature — {candidate_name.replace('_', ' ')}.pdf"
    current_hash = hashlib.sha1(html_content.encode("utf-8")).hexdigest()
    validated = st.session_state.get("dossier_validated_hash") == current_hash
    has_linkedin = bool(leonar.linkedin_slug(st.session_state.get("dossier_linkedin", "")))

    notice_final = st.session_state.pop("dossier_validation_notice", None)
    if notice_final:
        getattr(st, notice_final[0])(notice_final[1])

    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        validate = st.button(
            "Version finale validée" if validated
            else "Valider la nouvelle version finale" if st.session_state.get("dossier_validated_hash")
            else "Valider la version finale",
            icon=":material/task_alt:",
            type="primary",
            key="dossier_validate_final",
            disabled=validated or not has_linkedin,
            help="Envoie le dossier en PDF sur la fiche Leonar du candidat (retrouvée par son URL LinkedIn). "
                 "Rien n'est envoyé avant ; une nouvelle validation remplace la précédente.",
        )
        try:
            with st.spinner("Préparation du PDF…"):
                pdf_bytes = dossier_pdf(html_content)
            st.download_button(
                "PDF", data=pdf_bytes, file_name=pdf_name, mime="application/pdf",
                icon=":material/download:", on_click="ignore", key="dossier_download_pdf", type="tertiary",
            )
        except Exception:
            # Repli : HTML à imprimer en PDF depuis Chrome (bouton intégré au document)
            st.download_button(
                "HTML (à imprimer en PDF)", data=html_content, mime="text/html",
                file_name=f"dossier_{candidate_name}{version_suffix}.html",
                icon=":material/download:", key="dossier_download_html", type="tertiary",
            )
    if not has_linkedin:
        st.caption("Renseigne l'URL LinkedIn du candidat (en haut) pour valider la version finale.")
    if validate:
        try:
            with st.spinner("Recherche du candidat dans Leonar…"):
                contact = leonar.find_contact_by_linkedin(st.session_state["dossier_linkedin"])
            if not contact:
                st.error("Aucune fiche Leonar ne correspond à cette URL LinkedIn. Vérifie l'URL ou crée le contact dans Leonar.")
            else:
                with st.spinner("Conversion en PDF et envoi sur la fiche Leonar…"):
                    leonar.replace_contact_file(contact["id"], pdf_name, dossier_pdf(html_content))
                full_name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
                st.session_state["dossier_validated_hash"] = current_hash
                st.session_state["dossier_contact"] = {"id": contact["id"], "nom": full_name}
                st.session_state["dossier_validation_notice"] = (
                    "success", f"Version finale envoyée sur la fiche Leonar de **{full_name}** "
                               f"([ouvrir]({leonar.contact_url(contact['id'])})).",
                )
                st.rerun()
        except (PdfExportError, leonar.LeonarError) as e:
            st.error(f"Envoi sur Leonar impossible : {e}")

    if validated:
        render_envoi_client(current_hash)

    # Ouvert d'office après une révision pour que le changement soit visible tout de suite.
    with st.expander("Aperçu du dossier", expanded=bool(notice)):
        st.components.v1.html(html_content, height=900, scrolling=True)

    # --- MODE RÉVISION ---
    with st.expander(
        "✏️ Corrections — décrire et régénérer",
        expanded=bool(notice),
    ):
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

        col_fix, col_undo = st.columns([3, 1])
        with col_fix:
            do_revise = st.button(
                "🔄 Régénérer avec les corrections", type="primary", key="fix_regenerate"
            )
        with col_undo:
            can_undo = bool(st.session_state.get("dossier_history"))
            do_undo = st.button(
                "↩️ Annuler la dernière",
                key="fix_undo",
                disabled=not can_undo,
                help="Revenir à la version précédente du dossier"
                if can_undo
                else "Aucune correction à annuler",
            )

        if do_undo and st.session_state.get("dossier_history"):
            previous = st.session_state["dossier_history"].pop()
            st.session_state["dossier_html_pages12"] = previous["pages12"]
            st.session_state["dossier_html"] = previous["full"]
            st.session_state["dossier_version"] = previous["version"]
            st.session_state["dossier_revision_notice"] = {
                "version": previous["version"],
                "corrections": "",
                "problems": [],
                "undo": True,
            }
            st.rerun()

        if do_revise:
            if not user_corrections.strip():
                st.warning("Écris tes corrections avant de régénérer.")
            elif not st.session_state.get("dossier_html_pages12"):
                st.error("Génère d'abord un dossier.")
            else:
                with st.status("Révision en cours…", expanded=True) as rev_status:
                    try:
                        html_p12 = st.session_state["dossier_html_pages12"]
                        pdf_bytes_rev = st.session_state.get("dossier_pdf_bytes", b"")

                        # Le brief et les notes sont la source de vérité du dossier :
                        # sans eux, Claude ne peut pas honorer une correction qui y renvoie.
                        brief = st.session_state.get("dossier_brief", "")
                        scores = st.session_state.get("dossier_criteria_scores", [])

                        prompt_parts = [
                            f"CORRECTIONS DEMANDÉES :\n{user_corrections.strip()}"
                        ]
                        if brief:
                            prompt_parts.append(
                                "BRIEF INITIAL (source des pages 1 et 2, rappelé pour référence — "
                                "ne réécris que ce que les corrections visent) :\n"
                                + brief
                            )
                        if scores:
                            prompt_parts.append(
                                "NOTES ACTUELLES PAR CRITÈRE (à conserver telles quelles, "
                                "sauf si les corrections demandent explicitement de les changer) :\n"
                                + "\n".join(
                                    f"- {c['name']}"
                                    + (f" ({c['weight']})" if c.get("weight") else "")
                                    + f" : {c['score']}/5"
                                    for c in scores
                                )
                            )
                        prompt_parts.append(
                            "PAGES 1 ET 2 ACTUELLES (HTML à corriger) :\n" + html_p12
                        )
                        revision_user_prompt = "\n\n".join(prompt_parts)

                        claude_client_rev = Anthropic(api_key=claude_api_key)

                        def _call_claude_rev(messages_payload):
                            # Streaming : même raison que pour la génération.
                            with claude_client_rev.messages.stream(
                                model=MODEL,
                                max_tokens=MAX_TOKENS_DOSSIER,
                                system=REVISION_SYSTEM_PROMPT,
                                messages=messages_payload,
                                extra_body=DOSSIER_REQUEST_EXTRA,
                                timeout=600.0,
                            ) as stream:
                                return stream.get_final_message()

                        rev_messages = [
                            {"role": "user", "content": revision_user_prompt}
                        ]
                        st.write("🧠 Application des corrections…")
                        rev_response = _call_claude_rev(rev_messages)
                        # Le CSS et l'en-tête viennent du gabarit, jamais du modèle.
                        revised = strip_code_fences(response_text(rev_response))
                        revised, shell_restored = restore_template_shell(revised)
                        if shell_restored:
                            st.write("🎨 En-tête et CSS du gabarit restaurés à l'identique.")

                        # Mêmes garde-fous que la génération : une correction ne doit
                        # jamais casser la structure ni faire déborder la page 2.
                        if not is_structurally_valid(revised):
                            raise ValueError(
                                "Claude a renvoyé un HTML inexploitable (tronqué ou hors format) — "
                                "dossier inchangé. Reformule tes corrections, ou découpe-les en deux passes."
                            )

                        problems = check_dossier_html(revised, rev_response)
                        content_issues = audit_dossier_content(revised)
                        if content_issues:
                            revised, content_issues = repair_content_issues(
                                revised, content_issues, _call_claude_rev, rev_messages
                            )
                        problems += content_issues

                        # La note globale reste une moyenne : on la recalcule sur les notes
                        # du tableau corrigé, qui font foi après une correction.
                        revised, fixed_score = enforce_global_score(revised)
                        if fixed_score:
                            st.write("🔢 Note globale recalculée (moyenne des critères).")

                        st.write("📄 Réassemblage du dossier…")
                        # Historique AVANT écrasement, pour pouvoir annuler.
                        history = st.session_state.setdefault("dossier_history", [])
                        history.append(
                            {
                                "pages12": html_p12,
                                "full": st.session_state["dossier_html"],
                                "version": st.session_state.get("dossier_version", 1),
                            }
                        )
                        del history[:-10]

                        # Une correction peut changer une note : la session doit suivre,
                        # sinon la révision suivante repartirait des notes d'origine.
                        table_scores = read_table_scores(revised)
                        if scores and len(table_scores) == len(scores):
                            st.session_state["dossier_criteria_scores"] = [
                                {**c, "score": v} for c, v in zip(scores, table_scores)
                            ]

                        new_version = st.session_state.get("dossier_version", 1) + 1
                        st.session_state["dossier_html_pages12"] = revised
                        st.session_state["dossier_html"] = finalize_dossier(
                            revised,
                            st.session_state.get("dossier_logo_b64", ""),
                            st.session_state.get("dossier_linkedin", ""),
                            pdf_bytes_rev,
                        )
                        st.session_state["dossier_version"] = new_version
                        st.session_state["dossier_revision_notice"] = {
                            "version": new_version,
                            "corrections": user_corrections.strip(),
                            "problems": problems,
                            "undo": False,
                        }

                        rev_status.update(label="✅ Dossier révisé !", state="complete")
                        st.rerun()

                    except Exception as rev_e:
                        rev_status.update(label="❌ Erreur", state="error")
                        st.error(f"Erreur : {rev_e}")
