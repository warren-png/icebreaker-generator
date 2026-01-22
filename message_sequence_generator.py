"""
═══════════════════════════════════════════════════════════════════
MESSAGE SEQUENCE GENERATOR - V24 (OPTIMISÉ COMPLET)
Modifications : 
- Pain points et outcomes complets par métier
- Prompts enrichis pour extraction précise des compétences
- Détection améliorée des mots-clés sectoriels
═══════════════════════════════════════════════════════════════════
"""

import anthropic
import os
import re 
from config import COMPANY_INFO

# ========================================
# IMPORTS DES NOUVEAUX UTILITAIRES
# ========================================
from prospection_utils.logger import log_event, log_error
from prospection_utils.cost_tracker import tracker
from prospection_utils.validator import validate_and_report
from prospection_utils.fallback_templates import generate_fallback_sequence, get_fallback_if_needed

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("❌ ANTHROPIC_API_KEY non trouvée")


# ========================================
# PAIN POINTS ET OUTCOMES PAR MÉTIER (COMPLETS)
# ========================================

PAIN_POINTS_BY_JOB = {
    'daf': [
        "reporting trop lent pour piloter en temps réel",
        "équipes finance absorbées par la production au détriment de l'analyse stratégique",
        "transformations ERP/EPM/BI qui s'éternisent",
        "difficulté à attirer et retenir des profils finance à haut potentiel",
        "dépendance forte à quelques profils clés (key-man risk)"
    ],
    'raf': [
        "polyvalence extrême : comptabilité, contrôle, trésorerie, fiscalité avec peu de relais managérial",
        "sous-dimensionnement chronique des équipes face à la charge",
        "outils finance insuffisants (ERP sous-exploité, reporting artisanal)",
        "projets de structuration à mener en parallèle de la production"
    ],
    'controle_gestion': [
        "données peu fiables et disponibles trop tard pour décider",
        "manque de profils hybrides finance + data",
        "difficulté à passer du reporting au business partnering",
        "multiplication des demandes métiers sans priorisation claire"
    ],
    'fpna': [
        "trop de dépendance à Excel, retraitements manuels multiples",
        "équipes cantonnées au reporting, faible influence sur les décisions stratégiques",
        "multiplication des demandes métiers sans priorisation claire",
        "difficulté à modéliser rapidement dans un contexte volatil"
    ],
    'comptabilite': [
        "charge de clôture excessive et récurrente avec deadlines serrées",
        "pénurie de profils comptables opérationnels fiables et autonomes",
        "dépendance à des personnes clés (connaissance concentrée)",
        "projets de transformation (ERP, CSP, e-invoicing) en parallèle de la production"
    ],
    'consolidation': [
        "process lourds et peu automatisés (forte dépendance Excel, retraitements manuels)",
        "pression extrême sur les délais de clôture groupe (deadlines non négociables)",
        "qualité hétérogène des données filiales (niveau comptable variable, retards de remontée)",
        "key-man risk élevé (connaissance concentrée sur 1-2 personnes)"
    ],
    'audit': [
        "couverture de risques insuffisante face à la croissance du périmètre",
        "manque de profils seniors autonomes capables de dialoguer avec la DG",
        "backlog de recommandations non suivies (faible taux de mise en œuvre)",
        "transformation vers l'audit data-driven difficile à mener (outillage insuffisant)"
    ],
    'epm': [
        "projets EPM qui s'éternisent avec forte dépendance aux intégrateurs",
        "faible adoption des outils par les utilisateurs (contournements Excel persistants)",
        "difficulté à trouver des profils qui font le pont entre Tech et Finance",
        "charge élevée de support utilisateurs au détriment des projets stratégiques"
    ],
    'bi_data': [
        "accès aux données lent et instable (pipelines fragiles)",
        "KPI contestés en comité de direction faute de référentiels clairs",
        "manque de profils hybrides (data engineers sans culture finance)",
        "dette analytique (tableurs critiques, retraitements manuels avant CODIR)"
    ]
}

OUTCOMES_CABINET = {
    'general': [
        "sécurisation rapide de profils opérationnels alignés avec vos enjeux",
        "réduction du temps de recrutement et du risque d'erreur de casting",
        "accès à des profils passifs non visibles sur les jobboards",
        "évaluation orientée contexte : capacité à réussir chez vous, pas juste savoir faire le métier"
    ],
    'daf': [
        "pilotage plus rapide et plus fiable de la performance",
        "finance repositionnée comme partenaire business",
        "capacité à mener la transformation sans rupture",
        "stabilisation et montée en compétence des équipes"
    ],
    'raf': [
        "sécurisation du socle financier",
        "structuration progressive de la fonction",
        "gain de bande passante pour le pilotage stratégique"
    ],
    'controle_gestion': [
        "accélération du pilotage de la performance",
        "transformation du rôle des équipes vers le business partnering",
        "réussite des projets EPM/BI par des profils sachant les porter"
    ],
    'fpna': [
        "amélioration de la qualité décisionnelle",
        "réduction de la dépendance aux tableurs critiques",
        "rééquilibrage production / analyse"
    ],
    'comptabilite': [
        "absorption des pics d'activité sans tension structurelle",
        "sécurisation de la production comptable",
        "réduction de la dépendance à quelques personnes clés"
    ],
    'consolidation': [
        "accélération des cycles de clôture groupe",
        "montée en compétence collective des équipes",
        "autonomie renforcée vis-à-vis des filiales"
    ],
    'audit': [
        "couverture de risques alignée avec la stratégie",
        "renforcement rapide du niveau senior",
        "crédibilité renforcée auprès des comités"
    ],
    'epm': [
        "accélération des cycles budget / forecast / clôture",
        "adoption réelle des outils par les utilisateurs",
        "autonomie vis-à-vis des intégrateurs",
        "sécurisation de la continuité opérationnelle"
    ],
    'bi_data': [
        "time-to-insight fortement réduit",
        "crédibilité renforcée du pilotage financier",
        "self-service gouverné",
        "réduction des risques opérationnels"
    ]
}


# ========================================
# DÉTECTION AUTOMATIQUE DU MÉTIER (INCHANGÉ)
# ========================================

def detect_job_category(prospect_data, job_posting_data):
    """
    Détecte automatiquement la catégorie métier du prospect
    pour adapter pain points et outcomes
    """
    
    text = f"{prospect_data.get('headline', '')} {prospect_data.get('title', '')} "
    if job_posting_data:
        text += f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}"
    
    text = text.lower()
    
    # Détection par mots-clés
    if any(word in text for word in ['daf', 'directeur administratif', 'cfo', 'chief financial']):
        return 'daf'
    elif any(word in text for word in ['raf', 'responsable administratif']):
        return 'raf'
    elif any(word in text for word in ['fp&a', 'fp a', 'financial planning']):
        return 'fpna'
    elif any(word in text for word in ['contrôle de gestion', 'controle gestion', 'business controller']):
        return 'controle_gestion'
    elif any(word in text for word in ['consolidation', 'consolidateur']):
        return 'consolidation'
    elif any(word in text for word in ['audit', 'auditeur']):
        return 'audit'
    elif any(word in text for word in ['epm', 'anaplan', 'hyperion', 'planning']):
        return 'epm'
    elif any(word in text for word in ['bi', 'business intelligence', 'data', 'analytics']):
        return 'bi_data'
    elif any(word in text for word in ['comptable', 'comptabilité', 'accounting']):
        return 'comptabilite'
    else:
        return 'general'


def get_relevant_pain_points(job_category, max_points=2):
    """Récupère les pain points pertinents pour le métier détecté"""
    pain_points = PAIN_POINTS_BY_JOB.get(job_category, PAIN_POINTS_BY_JOB['daf'])
    return pain_points[:max_points]


def get_relevant_outcomes(job_category, max_outcomes=2):
    """Récupère les outcomes pertinents"""
    outcomes = OUTCOMES_CABINET.get(job_category, OUTCOMES_CABINET['general'])
    return outcomes[:max_outcomes]


# ========================================
# ÉVALUATION RICHESSE DES DONNÉES (INCHANGÉ)
# ========================================

def assess_data_richness(hooks_data, job_posting_data):
    """
    Évalue la richesse des données scrapées pour adapter le style du message
    """
    has_hooks = hooks_data and hooks_data != "NOT_FOUND" and len(str(hooks_data)) > 100
    has_detailed_job = job_posting_data and len(str(job_posting_data.get('description', ''))) > 200
    
    if has_hooks:
        return 'rich'
    elif has_detailed_job:
        return 'basic'
    else:
        return 'minimal'


# ========================================
# FONCTIONS UTILITAIRES (INCHANGÉES)
# ========================================

def get_safe_firstname(prospect_data):
    """Trouve le prénom (détective)"""
    target_keys = ['first_name', 'firstname', 'first name', 'prénom', 'prenom', 'name']
    for key, value in prospect_data.items():
        if str(key).lower().strip() in target_keys:
            if value and str(value).strip():
                return str(value).strip().capitalize()
    return "[Prénom]"

def get_smart_context(job_posting_data, prospect_data):
    """Définit le sujet de la discussion."""
    # Cas 1 : Il y a une annonce
    if job_posting_data and job_posting_data.get('title') and len(str(job_posting_data.get('title'))) > 2:
        title = str(job_posting_data.get('title'))
        # Nettoyage
        title = re.sub(r'\s*\(?[HhFf]\s*[/\-]\s*[HhFfMm]\)?', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*[-|]\s*.*$', '', title)
        return title.strip().title(), True

    # Cas 2 : Pas d'annonce (Approche Spontanée)
    headline = str(prospect_data.get('headline', '')).lower()
    
    if 'financ' in headline or 'daf' in headline or 'cfo' in headline:
        return "vos équipes Finance", False
    elif 'rh' in headline or 'drh' in headline or 'talents' in headline:
        return "votre stratégie Talents", False
    elif 'audit' in headline:
        return "votre département Audit", False
    else:
        return "vos équipes", False


# ========================================
# 1. GÉNÉRATEUR D'OBJETS (ENRICHI MOTS-CLÉS)
# ========================================

def generate_subject_lines(prospect_data, job_posting_data):
    """Génère les objets d'email axés pain points avec détection enrichie"""
    
    log_event('generate_subject_lines_start', {
        'prospect': prospect_data.get('_id', 'unknown')
    })
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    context_name, is_hiring = get_smart_context(job_posting_data, prospect_data)
    job_category = detect_job_category(prospect_data, job_posting_data)
    pain_points = get_relevant_pain_points(job_category, max_points=2)
    
    # ENRICHISSEMENT : Liste étendue de mots-clés à détecter
    extended_keywords = [
        # Outils EPM/Planning
        'tagetik', 'epm', 'anaplan', 'hyperion', 'oracle planning', 'sap bpc', 'onestream',
        # ERP
        'sap', 's/4hana', 'oracle', 'sage', 'sage x3', 'microsoft dynamics',
        # Consolidation/Reporting
        'consolidation', 'ifrs', 'reporting', 'forecast', 'budget', 'clôture',
        # BI/Data
        'bi', 'business intelligence', 'data', 'analytics', 'power bi', 'tableau', 'qlik',
        # Finance
        'fp&a', 'fpa', 'contrôle de gestion', 'trésorerie',
        # Compétences transverses
        'change management', 'adoption', 'training', 'user support', 'transformation',
        'automatisation', 'digitalisation', 'business partnering',
        # Sectoriels
        'bancaire', 'bank', 'fintech', 'audiovisuel', 'cinéma', 'production',
        # Logiciels spécifiques
        'louma', 'excel', 'python', 'sql', 'vba'
    ]
    
    detected_keywords = []
    if job_posting_data:
        job_text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}".lower()
        detected_keywords = [kw for kw in extended_keywords if kw in job_text][:7]
    
    if is_hiring:
        prompt_type = "recrutement actif"
        subject_focus = f"Poste : {context_name}"
    else:
        prompt_type = "approche spontanée"
        subject_focus = f"Sujet : {context_name}"
    
    prompt = f"""Tu es expert en copywriting B2B pour cabinet de recrutement Finance.

CONTEXTE :
{prompt_type.capitalize()}
{subject_focus}
Entreprise : {prospect_data.get('company', 'l\'entreprise')}
Métier détecté : {job_category}

DONNÉES JOB POSTING (à utiliser IMPÉRATIVEMENT) :
Titre poste : {job_posting_data.get('title', 'N/A') if job_posting_data else 'N/A'}

MOTS-CLÉS DÉTECTÉS DANS LA FICHE (CRITIQUE - à intégrer dans les objets) :
{', '.join(detected_keywords) if detected_keywords else 'Aucun mot-clé spécifique détecté'}

PAIN POINTS CONTEXTUELS (à intégrer subtilement) :
- {pain_points[0] if len(pain_points) > 0 else 'recrutement complexe'}
- {pain_points[1] if len(pain_points) > 1 else 'difficulté à trouver profils'}

CONSIGNE :
Génère 3 objets d'email courts (40-60 caractères) qui :
1. Mentionnent les MOTS-CLÉS DÉTECTÉS (outils, secteur, compétences spécifiques)
2. Évoquent les pain points de manière INTERROGATIVE
3. Restent sobres et professionnels

IMPÉRATIF ABSOLU : Si un outil/secteur spécifique est détecté (Tagetik, SAP, bancaire, audiovisuel, etc.), 
AU MOINS UN des objets DOIT le mentionner explicitement !

FORMAT ATTENDU :
1. [Question avec mot-clé outil/secteur OU pain point]
2. [Constat marché avec compétence spécifique]
3. [Objet direct : "Re: [titre poste]"]

EXEMPLES DE BONS OBJETS (selon contexte détecté) :

Si Tagetik/EPM détecté :
1. EPM : profils Tech OU Fonctionnel ?
2. Adoption Tagetik : le vrai défi
3. Re: Senior Functional Analyst Tagetik

Si comptabilité bancaire détectée :
1. Comptabilité bancaire : marché tendu
2. Clôtures réglementaires : profils rares
3. Re: Comptable Memo Bank

Si audiovisuel détecté :
1. Comptable audiovisuel : convention collective ?
2. Production ciné : droits d'auteurs + notes de frais
3. Re: Comptable PHANTASM

Si consolidation IFRS détectée :
1. Consolidation : Excel ou outil groupe ?
2. IFRS : expertise + pédagogie filiales
3. Re: Responsable Consolidation

Si FP&A détecté :
1. FP&A : reporting ou business partner ?
2. Profils hybrides Finance + Data
3. Re: Directeur FP&A

INTERDICTIONS :
- ❌ Pas de "Opportunité", "Proposition", "Collaboration"
- ❌ Pas de points d'exclamation
- ❌ Pas de promesses directes
- ❌ Pas de "Notre cabinet"

Génère les 3 objets (numérotés 1, 2, 3) :"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        
        tracker.track(message.usage, 'generate_subject_lines')
        result = message.content[0].text.strip()
        
        log_event('generate_subject_lines_success', {'length': len(result)})
        return result
        
    except anthropic.APIError as e:
        log_error('claude_api_error', str(e), {'function': 'generate_subject_lines'})
        from prospection_utils.fallback_templates import generate_fallback_subjects
        return generate_fallback_subjects(prospect_data, job_posting_data)
    
    except Exception as e:
        log_error('unexpected_error', str(e), {'function': 'generate_subject_lines'})
        return f"Re: {context_name}"


# ========================================
# 2. MESSAGE 2 : LE DILEMME (OPTIMISÉ EXTRACTION)
# ========================================

def generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content):
    """Génère le message 2 avec extraction précise des compétences"""
    
    log_event('generate_message_2_start', {
        'prospect': prospect_data.get('_id', 'unknown'),
        'has_hooks': hooks_data != "NOT_FOUND"
    })
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    first_name = get_safe_firstname(prospect_data)
    context_name, is_hiring = get_smart_context(job_posting_data, prospect_data)
    job_category = detect_job_category(prospect_data, job_posting_data)
    pain_points = get_relevant_pain_points(job_category, max_points=2)
    outcomes = get_relevant_outcomes(job_category, max_outcomes=1)
    
    # ENRICHISSEMENT : Extraction poussée des expertises
    technical_skills = []
    soft_skills = []
    tools = []
    
    if job_posting_data:
        job_text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}".lower()
        
        # Outils/technologies
        tool_keywords = ['tagetik', 'sap', 'anaplan', 'hyperion', 'oracle', 'sage', 'louma', 
                        'power bi', 'tableau', 'excel', 'python', 'sql', 'onestream']
        tools = [tool for tool in tool_keywords if tool in job_text]
        
        # Compétences techniques
        tech_keywords = ['consolidation', 'ifrs', 'reporting', 'comptabilité bancaire', 
                        'fiscalité', 'trésorerie', 'budget', 'forecast', 'clôture',
                        'droits d\'auteurs', 'notes de frais', 'convention collective']
        technical_skills = [skill for skill in tech_keywords if skill in job_text]
        
        # Compétences transverses
        soft_keywords = ['change management', 'adoption', 'training', 'user support', 
                        'automatisation', 'business partnering', 'transformation',
                        'project management', 'communication', 'pédagogie']
        soft_skills = [skill for skill in soft_keywords if skill in job_text]
    
    expertises_detected = f"Outils: {', '.join(tools[:3]) if tools else 'N/A'} | Techniques: {', '.join(technical_skills[:3]) if technical_skills else 'N/A'} | Transverses: {', '.join(soft_skills[:2]) if soft_skills else 'N/A'}"
    
    if is_hiring:
        intro_phrase = f"Je me permets de vous relancer concernant votre recherche de {context_name}."
        context_type = "ce recrutement"
    else:
        intro_phrase = f"Je reviens vers vous concernant la structuration de {context_name}."
        context_type = "ce type de besoin"
    
    prompt = f"""Tu es chasseur de têtes spécialisé Finance.

CONTEXTE :
Prospect : {first_name}
Poste recherché : {context_name}
Métier : {job_category}
Type : {'Recrutement actif' if is_hiring else 'Approche spontanée'}

ANALYSE POUSSÉE DE LA FICHE DE POSTE (CRITIQUE) :
Titre exact : {job_posting_data.get('title', 'N/A') if job_posting_data else 'N/A'}

EXPERTISES DÉTECTÉES :
{expertises_detected}

Description complète (extraits) :
{str(job_posting_data.get('description', ''))[:800] if job_posting_data else 'N/A'}

PAIN POINTS IDENTIFIÉS (à mentionner subtilement) :
- {pain_points[0] if len(pain_points) > 0 else 'difficulté à recruter'}
- {pain_points[1] if len(pain_points) > 1 else 'manque de profils qualifiés'}

TON ET STYLE (IMPÉRATIF) :
- Consultatif, PAS commercial
- Crédibilité par observation marché, PAS auto-promotion
- 100-120 mots maximum

STRUCTURE STRICTE :
1. "Bonjour {first_name},"
2. SAUT DE LIGNE
3. "{intro_phrase}"

4. Observation marché ULTRA-SPÉCIFIQUE au poste (30-40 mots)
   → IMPÉRATIF : L'observation doit mentionner les COMPÉTENCES DÉTECTÉES !
   
   MÉTHODE POUR CONSTRUIRE L'OBSERVATION :
   a) Identifier les 2-3 compétences RARES du poste (pas juste "comptabilité" ou "finance")
   b) Formuler le pain point autour de ces compétences rares
   c) Contextualiser (secteur, environnement, type d'entreprise si pertinent)
   
   EXEMPLES DE BONNES OBSERVATIONS CONTEXTUELLES :
   
   Pour EPM/Tagetik :
   "Sur ce type de poste EPM en environnement international, je constate que le défi n'est pas 
   la maîtrise technique de Tagetik seule, mais la capacité à piloter l'adoption de l'outil 
   auprès des affiliates globales tout en animant le change management."
   
   Pour Consolidation IFRS :
   "Sur ce type de poste consolidation, je constate que le marché combine rarement expertise 
   normative IFRS poussée et capacité pédagogique pour faire monter le niveau des filiales 
   internationales."
   
   Pour Comptabilité bancaire :
   "Sur ce type de poste en banque tech, je constate que le défi n'est pas la comptabilité 
   bancaire seule, mais la capacité à automatiser les process tout en participant activement 
   aux projets transverses (nouveaux produits, évolutions réglementaires)."
   
   Pour Comptabilité audiovisuelle :
   "Sur ce type de poste en production audiovisuelle, je constate que le défi va au-delà 
   de la comptabilité générale : il faut maîtriser les spécificités sectorielles (droits 
   d'auteurs, convention collective production) tout en gérant plusieurs productions simultanées."

5. Proposition ULTRA-SPÉCIFIQUE (40-50 mots)
   "J'ai identifié 2 profils qui pourraient retenir votre attention :"
   
   → IMPÉRATIF : Mentionner EXPLICITEMENT les expertises détectées !
   → Structure : "L'un [expertise 1 + expertise 2]. L'autre [expertise 1 + variante]."
   
   EXEMPLES DE BONNES PROPOSITIONS :
   
   Pour EPM/Tagetik :
   "- L'un combine expertise Tagetik (consolidation & reporting) et expérience en project management, 
     ayant piloté l'intégration EPM/ERP en environnement international.
   - L'autre vient du conseil EPM, avec une forte capacité d'animation du change management 
     auprès d'affiliates globales (formations, stakeholder engagement)."
   
   Pour Consolidation :
   "- L'un est expert IFRS (10+ ans) avec expérience de montée en compétence des filiales.
   - L'autre a piloté un projet de migration d'outil de consolidation et excelle dans 
     la pédagogie normative."
   
   Pour Comptabilité bancaire :
   "- L'un possède une expérience en comptabilité bancaire (clôtures réglementaires, IFRS) 
     et a piloté l'automatisation des réconciliations via Excel/VBA.
   - L'autre vient de la fintech et combine expertise fiscale avec participation active 
     aux projets d'implémentation de nouveaux produits."
   
   Pour Comptabilité audiovisuelle :
   "- L'un possède une expérience en comptabilité audiovisuelle (production cinéma/pub), 
     maîtrise la gestion des droits d'auteurs et connaît la convention collective production.
   - L'autre vient de l'événementiel avec forte dimension projet (multi-productions simultanées) 
     et connaissance de logiciels sectoriels comme Louma."

6. Offre sans engagement (15-20 mots) :
   "Seriez-vous d'accord pour recevoir leurs synthèses anonymisées ? Cela vous permettrait 
   de juger leur pertinence en 30 secondes."
   
7. Formule de politesse : "Bien à vous,"

INTERDICTIONS ABSOLUES :
- ❌ Jamais "Notre cabinet", "Nos services", "Notre expertise"
- ❌ Jamais de superlatifs ("meilleurs", "excellents")
- ❌ Jamais proposer des profils génériques ("contrôle de gestion", "FP&A") si le poste 
     demande EPM/Consolidation/Comptabilité spécialisée !
- ❌ Jamais plus de 120 mots

VALIDATION CRITIQUE AVANT ENVOI :
1. Les expertises proposées correspondent-elles EXACTEMENT aux compétences détectées ? → Si NON : RECOMMENCER
2. L'observation mentionne-t-elle les compétences RARES du poste ? → Si NON : RECOMMENCER
3. Le message fait-il plus de 120 mots ? → Si OUI : RÉDUIRE

Génère le message 2 selon ces règles STRICTES.
"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        tracker.track(message.usage, 'generate_message_2')
        result = message.content[0].text
        
        log_event('generate_message_2_success', {'length': len(result)})
        return result
        
    except anthropic.APIError as e:
        log_error('claude_api_error', str(e), {'function': 'generate_message_2'})
        from prospection_utils.fallback_templates import generate_fallback_message
        return generate_fallback_message(2, prospect_data, job_posting_data)
    
    except Exception as e:
        log_error('unexpected_error', str(e), {'function': 'generate_message_2'})
        raise


# ========================================
# 3. MESSAGE 3 : BREAK-UP (INCHANGÉ)
# ========================================

def generate_message_3(prospect_data, message_1_content, job_posting_data):
    """Génère le message 3 - Template fixe approuvé"""
    
    log_event('generate_message_3_start', {
        'prospect': prospect_data.get('_id', 'unknown')
    })
    
    first_name = get_safe_firstname(prospect_data)
    
    message_3_template = f"""Bonjour {first_name},

Je comprends que vous n'ayez pas eu le temps de revenir vers moi — je sais à quel point vos fonctions sont sollicitées.

Avant de clore le dossier de mon côté, une dernière question : Est-ce que le timing n'est simplement pas bon pour l'instant, ou bien travaillez-vous déjà avec d'autres cabinets/recruteurs sur ce poste ?

Si c'est une question de timing, je serai ravi de reprendre contact dans quelques semaines.

Si vous préférez gérer ce recrutement autrement, aucun souci — je vous souhaite de trouver la perle rare rapidement.

Merci en tous cas pour votre attention,

Bonne continuation,"""
    
    log_event('generate_message_3_success', {
        'length': len(message_3_template)
    })
    
    return message_3_template


# ========================================
# FONCTION HELPER (INCHANGÉE)
# ========================================

def generate_full_sequence(prospect_data, hooks_data, job_posting_data, message_1_content):
    """Génère une séquence complète avec validation"""
    
    log_event('sequence_generation_start', {
        'prospect_id': prospect_data.get('_id', 'unknown'),
        'prospect_name': prospect_data.get('full_name', 'unknown'),
        'company': prospect_data.get('company', 'unknown'),
        'has_job_posting': bool(job_posting_data),
        'has_hooks': hooks_data != "NOT_FOUND",
        'data_richness': assess_data_richness(hooks_data, job_posting_data),
        'job_category': detect_job_category(prospect_data, job_posting_data)
    })
    
    try:
        subject_lines = generate_subject_lines(prospect_data, job_posting_data)
        message_2 = generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content)
        message_3 = generate_message_3(prospect_data, message_1_content, job_posting_data)
        
        sequence = {
            'subject_lines': subject_lines,
            'message_1': message_1_content,
            'message_2': message_2,
            'message_3': message_3
        }
        
        is_valid = validate_and_report(sequence, prospect_data, raise_on_error=False)
        
        if not is_valid:
            log_error('sequence_validation_failed', 'Séquence générée invalide', {
                'prospect': prospect_data.get('_id', 'unknown')
            })
            print("⚠️  Séquence invalide détectée, génération d'un fallback...")
            sequence = generate_fallback_sequence(prospect_data, job_posting_data, message_1_content)
        
        log_event('sequence_generation_success', {
            'prospect_id': prospect_data.get('_id', 'unknown'),
            'is_fallback': sequence.get('is_fallback', False)
        })
        
        return sequence
        
    except Exception as e:
        log_error('sequence_generation_failed', str(e), {
            'prospect_id': prospect_data.get('_id', 'unknown')
        })
        
        print(f"❌ Erreur lors de la génération : {e}")
        print("🔄 Génération d'une séquence de fallback...")
        return generate_fallback_sequence(prospect_data, job_posting_data, message_1_content)
