"""
═══════════════════════════════════════════════════════════════════
MESSAGE SEQUENCE GENERATOR - V26 (FORCE 2 PROFILS SYSTÉMATIQUES)
Modifications V26 :
- Message 2 : TOUJOURS proposer 2 profils (règle absolue dans prompt)
- Vérification post-génération pour garantir présence des 2 profils
- Fonction fallback intelligente qui génère 2 profils crédibles par métier
- Extraction automatique des compétences pour profils génériques
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
    ],
    'data_ia': [
        "difficulté à trouver des profils qui combinent technique (Python, SQL, ML) et compréhension business",
        "acculturation IA lente dans les métiers (résistance au changement, manque de formation)",
        "cas d'usage IA qui n'aboutissent pas faute de sponsor métier engagé",
        "manque de profils capables d'animer un centre d'excellence IA (leadership transverse)"
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
    ],
    'data_ia': [
        "adoption réelle de l'IA dans les métiers (pas juste des POCs)",
        "ROI mesurable sur les cas d'usage déployés",
        "acculturation IA accélérée (formations, ateliers, centre d'excellence)",
        "réduction de la dépendance aux consultants externes"
    ]
}


# ========================================
# DÉTECTION AUTOMATIQUE DU MÉTIER (ENRICHI)
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
    
    # Détection par mots-clés (ordre = priorité)
    if any(word in text for word in ['data officer', 'ia officer', 'ai officer', 'data & ia', 'intelligence artificielle']):
        return 'data_ia'
    elif any(word in text for word in ['daf', 'directeur administratif', 'cfo', 'chief financial']):
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
# MATCHING FLEXIBLE (NOUVEAU)
# ========================================

def flexible_match(keyword, text):
    """
    Match flexible : insensible à la casse, espaces, tirets
    Exemple : 'power bi' matchera 'PowerBI', 'Power-BI', 'power bi'
    """
    # Échapper les caractères spéciaux regex sauf espaces
    pattern = re.escape(keyword).replace(r'\ ', r'[\s\-_]*')
    return bool(re.search(pattern, text, re.IGNORECASE))


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
# NOUVELLE FONCTION : EXTRACTION COMPÉTENCES POUR FALLBACK
# ========================================

def extract_key_skills_for_profiles(job_posting_data, job_category):
    """
    Extrait les compétences clés de la fiche de poste pour générer
    des profils génériques crédibles en cas de fallback
    Retourne un dict avec compétences adaptées au métier
    """
    skills = {
        'tool_1': 'un outil métier',
        'tool_2': 'Excel avancé',
        'technical_1': 'expertise technique',
        'technical_2': 'maîtrise opérationnelle',
        'soft': 'conduite du changement',
        'sector': 'le secteur',
        'context_1': 'grand groupe',
        'context_2': 'environnement international'
    }
    
    if not job_posting_data:
        return skills
    
    job_text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}".lower()
    
    # Outils spécifiques
    if flexible_match('tagetik', job_text):
        skills['tool_1'] = 'Tagetik'
    elif flexible_match('anaplan', job_text):
        skills['tool_1'] = 'Anaplan'
    elif flexible_match('hyperion', job_text):
        skills['tool_1'] = 'Hyperion'
    elif flexible_match('sap', job_text):
        skills['tool_1'] = 'SAP'
    elif flexible_match('sage', job_text):
        skills['tool_1'] = 'Sage'
    elif flexible_match('power bi', job_text):
        skills['tool_1'] = 'Power BI'
    
    if flexible_match('python', job_text):
        skills['tool_2'] = 'Python'
    elif flexible_match('sql', job_text):
        skills['tool_2'] = 'SQL'
    elif flexible_match('vba', job_text):
        skills['tool_2'] = 'VBA'
    elif flexible_match('power query', job_text):
        skills['tool_2'] = 'Power Query'
    
    # Compétences techniques par métier
    if job_category == 'data_ia':
        skills['technical_1'] = 'Data Science (Python, SQL, Machine Learning)'
        skills['technical_2'] = 'acculturation IA et animation de centres d\'excellence'
    elif job_category == 'epm':
        skills['technical_1'] = f'{skills["tool_1"]} (consolidation, reporting)'
        skills['technical_2'] = 'pilotage de projets EPM et adoption utilisateurs'
    elif job_category == 'comptabilite':
        skills['technical_1'] = 'comptabilité générale et clôtures'
        skills['technical_2'] = 'autonomie sur le cycle comptable complet'
    elif job_category == 'audit':
        skills['technical_1'] = 'audit interne et contrôles SOX'
        skills['technical_2'] = 'dialogue avec la Direction Générale'
    elif job_category == 'consolidation':
        skills['technical_1'] = 'consolidation IFRS'
        skills['technical_2'] = 'montée en compétence des filiales'
    elif job_category == 'controle_gestion':
        skills['technical_1'] = 'contrôle de gestion et FP&A'
        skills['technical_2'] = 'business partnering opérationnel'
    elif job_category == 'fpna':
        skills['technical_1'] = 'FP&A (budget, forecast, variance analysis)'
        skills['technical_2'] = 'modélisation financière avancée'
    
    # Secteur
    if 'banc' in job_text or 'bank' in job_text:
        skills['sector'] = 'le secteur bancaire'
        skills['context_1'] = 'banque d\'investissement'
        skills['context_2'] = 'corporate banking'
    elif 'fintech' in job_text:
        skills['sector'] = 'la fintech'
        skills['context_1'] = 'startup fintech'
        skills['context_2'] = 'scale-up tech'
    elif 'audiovisuel' in job_text or 'cinéma' in job_text:
        skills['sector'] = 'l\'audiovisuel'
        skills['context_1'] = 'production cinématographique'
        skills['context_2'] = 'groupe média'
    elif 'industrie' in job_text or 'industrial' in job_text:
        skills['sector'] = 'l\'industrie'
        skills['context_1'] = 'grand groupe industriel'
        skills['context_2'] = 'environnement manufacturier'
    
    return skills


# ========================================
# NOUVELLE FONCTION : FALLBACK MESSAGE 2 AVEC 2 PROFILS
# ========================================

def generate_message_2_fallback(first_name, context_name, is_hiring, job_posting_data, job_category, prospect_data):
    """
    Génère un Message 2 de secours avec 2 profils génériques mais crédibles
    Utilisé si Claude ne génère pas 2 profils dans sa réponse principale
    """
    log_event('message_2_fallback_triggered', {
        'prospect': prospect_data.get('_id', 'unknown'),
        'job_category': job_category,
        'reason': 'Profils manquants dans génération principale'
    })
    
    # Extraire compétences clés
    skills = extract_key_skills_for_profiles(job_posting_data, job_category)
    
    if is_hiring:
        intro = f"Je me permets de vous relancer concernant votre recherche de {context_name}."
    else:
        intro = f"Je reviens vers vous concernant la structuration de {context_name}."
    
    # Pain point adapté au métier
    pain_point = f"Le défi principal sur ce type de poste réside dans la capacité à allier {skills['technical_1']} et {skills['soft']}."
    
    # Génération des 2 profils
    profile_1 = f"- L'un possède une expertise {skills['technical_1']} avec 6+ ans en {skills['sector']}, ayant piloté des projets de transformation dans des contextes internationaux."
    profile_2 = f"- L'autre combine maîtrise de {skills['tool_1']} et {skills['technical_2']}, issu d'un {skills['context_1']} avec forte autonomie opérationnelle."
    
    message = f"""Bonjour {first_name},

{intro}

{pain_point}

J'ai identifié 2 profils qui pourraient retenir votre attention :
{profile_1}
{profile_2}

Seriez-vous d'accord pour recevoir leurs synthèses anonymisées ? Cela vous permettrait de juger leur pertinence en 30 secondes.

Bien à vous,"""
    
    log_event('message_2_fallback_generated', {
        'prospect': prospect_data.get('_id', 'unknown'),
        'job_category': job_category,
        'length': len(message)
    })
    
    return message


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
        'bi', 'business intelligence', 'data', 'analytics', 'power bi', 'powerbi', 'tableau', 'qlik',
        # Finance
        'fp&a', 'fpa', 'contrôle de gestion', 'trésorerie',
        # Compétences transverses
        'change management', 'adoption', 'training', 'user support', 'transformation',
        'automatisation', 'digitalisation', 'business partnering',
        # Sectoriels
        'bancaire', 'bank', 'fintech', 'audiovisuel', 'cinéma', 'production',
        # Logiciels spécifiques
        'louma', 'excel', 'python', 'sql', 'vba', 'r',
        # IA / Data Science
        'ia', 'ai', 'intelligence artificielle', 'machine learning', 'data science',
        'copilot', 'chatgpt', 'gen ai', 'generative ai',
        # Méthodologies
        'agile', 'scrum', 'kanban', 'safe', 'prince2'
    ]
    
    detected_keywords = []
    if job_posting_data:
        job_text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}".lower()
        detected_keywords = [kw for kw in extended_keywords if flexible_match(kw, job_text)][:7]
    
    log_event('keywords_detected', {
        'count': len(detected_keywords),
        'keywords': detected_keywords
    })
    
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

IMPÉRATIF ABSOLU : Si un outil/secteur spécifique est détecté (Tagetik, SAP, bancaire, audiovisuel, IA, Agile, etc.), 
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

Si IA/Data Science détecté :
1. IA : technique ET business ?
2. Cas d'usage IA : acculturation métiers
3. Re: Data & IA Officer

Si Agile/Scrum détecté :
1. EPM + Agile : profils hybrides rares
2. SAFe : finance + project management
3. Re: Global EPM Functional Manager

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
# 2. MESSAGE 2 : LE DILEMME (OPTIMISÉ EXTRACTION + FORCE 2 PROFILS V26)
# ========================================

def generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content):
    """Génère le message 2 avec extraction précise des compétences et FORCE 2 profils"""
    
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
    
    # ========================================
    # EXTRACTION ENRICHIE DES EXPERTISES (NOUVEAU - MATCHING FLEXIBLE)
    # ========================================
    technical_skills = []
    soft_skills = []
    tools = []
    
    if job_posting_data:
        job_text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}"
        
        # Outils/technologies (ENRICHI)
        tool_keywords = [
            'tagetik', 'sap', 'anaplan', 'hyperion', 'oracle', 'sage', 'louma', 
            'power bi', 'powerbi', 'tableau', 'excel', 'python', 'r', 'sql', 'onestream',
            'agile', 'scrum', 'kanban', 'safe', 'prince2', 'pmp',  # Méthodologies
            'copilot', 'chatgpt', 'ia', 'ai', 'intelligence artificielle',  # IA
            'machine learning', 'ml', 'deep learning', 'data science',  # Data Science
            'jupyter', 'pandas', 'numpy', 'tensorflow', 'scikit-learn',  # Outils Python
            'azure', 'aws', 'gcp', 'cloud'  # Cloud
        ]
        tools = [tool for tool in tool_keywords if flexible_match(tool, job_text)]
        
        # Compétences techniques (ENRICHI)
        tech_keywords = [
            'consolidation', 'ifrs', 'reporting', 'comptabilité bancaire', 
            'fiscalité', 'trésorerie', 'budget', 'forecast', 'clôture',
            'droits d\'auteurs', 'notes de frais', 'convention collective',
            'data science', 'data governance', 'cas d\'usage', 'use case',
            'intégration sap', 'sap integration', 'erp migration'
        ]
        technical_skills = [skill for skill in tech_keywords if flexible_match(skill, job_text)]
        
        # Compétences transverses (ENRICHI)
        soft_keywords = [
            'change management', 'adoption', 'training', 'user support', 
            'automatisation', 'business partnering', 'transformation',
            'project management', 'communication', 'pédagogie',
            'idéation', 'ideation', 'design thinking', 'acculturation',
            'stakeholder', 'animation', 'centre d\'excellence', 'governance',
            'roi', 'value creation'
        ]
        soft_skills = [skill for skill in soft_keywords if flexible_match(skill, job_text)]
    
    # ========================================
    # FALLBACK SI AUCUNE COMPÉTENCE DÉTECTÉE (NOUVEAU)
    # ========================================
    if not tools and not technical_skills and not soft_skills:
        log_event('no_skills_detected_fallback', {'prospect': prospect_data.get('_id')})
        
        # Extraction de secours : mots importants (capitalisés, > 4 lettres)
        if job_posting_data:
            job_desc = str(job_posting_data.get('description', ''))
            
            # Chercher les mots capitalisés ou acronymes
            capitalized_words = re.findall(r'\b[A-Z][A-Za-z]{3,}(?:\s+[A-Z][A-Za-z]+)*\b', job_desc)
            acronyms = re.findall(r'\b[A-Z]{2,}\b', job_desc)
            
            # Filtrer les mots pertinents
            stop_words = {'Vous', 'Dans', 'Avec', 'Pour', 'Votre', 'Notre', 'Cette', 'Nous', 'Les', 'Des'}
            extracted_terms = [word for word in (capitalized_words + acronyms) 
                              if word not in stop_words and len(word) > 3]
            
            # Dédupliquer et garder les 5 premiers
            extracted_terms = list(dict.fromkeys(extracted_terms))[:5]
            
            if extracted_terms:
                tools = extracted_terms
                log_event('fallback_extraction_success', {'terms': extracted_terms})
            else:
                log_event('fallback_extraction_failed', {'desc_length': len(job_desc)})
    
    expertises_detected = f"Outils: {', '.join(tools[:3]) if tools else 'N/A'} | Techniques: {', '.join(technical_skills[:3]) if technical_skills else 'N/A'} | Transverses: {', '.join(soft_skills[:2]) if soft_skills else 'N/A'}"
    
    log_event('expertises_extracted', {
        'tools_count': len(tools),
        'technical_count': len(technical_skills),
        'soft_count': len(soft_skills),
        'tools': tools[:3],
        'technical': technical_skills[:3],
        'soft': soft_skills[:2]
    })
    
    if is_hiring:
        intro_phrase = f"Je me permets de vous relancer concernant votre recherche de {context_name}."
        context_type = "ce recrutement"
    else:
        intro_phrase = f"Je reviens vers vous concernant la structuration de {context_name}."
        context_type = "ce type de besoin"
    
    prompt = f"""Tu es chasseur de têtes spécialisé Finance.

═══════════════════════════════════════════════════════════════════
⚠️  RÈGLE ABSOLUE - NON NÉGOCIABLE :
═══════════════════════════════════════════════════════════════════

Tu DOIS TOUJOURS proposer EXACTEMENT 2 profils candidats dans ce message.

Format OBLIGATOIRE :
"J'ai identifié 2 profils qui pourraient retenir votre attention :
- L'un possède [compétence technique 1] avec [X ans] en [secteur], ayant [réalisation concrète 1]
- L'autre combine [compétence technique 2] et [compétence soft/contexte différent], ayant [réalisation concrète 2]"

IMPÉRATIFS :
✅ TOUJOURS 2 profils (jamais 0, jamais 1)
✅ Profils DIFFÉRENTS (parcours, secteurs, compétences complémentaires)
✅ Compétences PRÉCISES extraites de la fiche de poste
✅ Contextes et réalisations CONCRETS

Si tu n'as pas assez d'informations pour créer 2 profils ultra-précis :
→ Génère 2 profils CRÉDIBLES basés sur les compétences clés de la fiche de poste

═══════════════════════════════════════════════════════════════════

CONTEXTE :
Prospect : {first_name}
Poste recherché : {context_name}
Métier : {job_category}
Type : {'Recrutement actif' if is_hiring else 'Approche spontanée'}

ANALYSE POUSSÉE DE LA FICHE DE POSTE (CRITIQUE) :
Titre exact : {job_posting_data.get('title', 'N/A') if job_posting_data else 'N/A'}

EXPERTISES DÉTECTÉES (À UTILISER OBLIGATOIREMENT) :
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
- ❌ INTERDICTION ABSOLUE de ton commercial type "auriez-vous 15 min" ou "rapide créneau"
- ❌ INTERDICTION de phrases génériques type "recruter crée un dilemme"

STRUCTURE STRICTE :
1. "Bonjour {first_name},"
2. SAUT DE LIGNE
3. "{intro_phrase}"

4. Observation marché ULTRA-SPÉCIFIQUE au poste (30-40 mots)
   → IMPÉRATIF CRITIQUE : L'observation DOIT mentionner les COMPÉTENCES DÉTECTÉES ci-dessus !
   → Si des outils sont détectés (Tagetik, SAP, Python, Agile, etc.), les NOMMER explicitement !
   → VARIER l'angle par rapport au Message 1 (autre facette du même pain point)
   
   MÉTHODE POUR CONSTRUIRE L'OBSERVATION :
   a) Prendre les 2-3 compétences les PLUS RARES détectées (pas "finance" ou "comptabilité")
   b) Formuler le pain point autour de CES compétences précises
   c) Contextualiser (secteur, environnement, type d'entreprise)
   d) TOUJOURS citer au moins 2 compétences techniques précises entre parenthèses
   
   EXEMPLES DE BONNES OBSERVATIONS CONTEXTUELLES :
   
   Pour EPM/Tagetik + Agile :
   "Le défi principal sur ce type de poste EPM en environnement international réside dans la capacité 
   à piloter des projets complexes (intégration SAP, Data Governance, méthodologies Agile) tout en 
   garantissant une adoption effective par les filiales internationales."
   
   Pour Data/IA Officer :
   "Le marché combine rarement expertise technique (Python, SQL, Machine Learning) et capacité 
   d'acculturation IA auprès des métiers (formations, ateliers idéation, animation de centres 
   d'excellence)."
   
   Pour Consolidation IFRS :
   "Trouver des profils qui allient maîtrise des normes IFRS, expérience terrain de montée en 
   compétence des filiales et pilotage de projets de migration d'outils (OneStream, Tagetik) 
   devient complexe."
   
   Pour Comptabilité bancaire :
   "La rareté porte sur des profils qui combinent rigueur comptable bancaire (clôtures réglementaires, 
   FINREP/COREP) et agilité projet pour accompagner les lancements produits (automatisation, BI)."

5. Proposition ULTRA-SPÉCIFIQUE (40-50 mots)
   "J'ai identifié 2 profils qui pourraient retenir votre attention :"
   
   → RÈGLE ABSOLUE : Les profils DOIVENT mentionner LES COMPÉTENCES DÉTECTÉES !
   → INTERDICTION de formulations vagues type "expertise comptable" ou "expérience finance"
   → OBLIGATION de citer les outils/compétences précises entre parenthèses
   → Structure : "L'un [outil/techno 1 + techno 2 + contexte]. L'autre [profil différent avec variante]."
   
   EXEMPLES DE BONNES PROPOSITIONS (PRÉCISES) :
   
   Pour EPM/Tagetik + Agile :
   "- L'un combine expertise Tagetik (consolidation statutory, reporting) et certification SAFe/PMP, 
     ayant piloté l'intégration EPM/SAP en environnement international.
   - L'autre vient du conseil EPM (Big 4) avec forte capacité en Change Management et animation de 
     formations utilisateurs multi-pays (stakeholder engagement, documentation)."
   
   Pour Data/IA Officer :
   "- L'un possède une expertise en Data Science (Python, SQL, Machine Learning) avec 5 ans en 
     finance de marché, ayant piloté des projets d'acculturation IA auprès des traders (ateliers 
     idéation, POCs métier).
   - L'autre vient de la finance corporate (FP&A) avec une reconversion technique (certification 
     Azure Data Engineer), ayant accompagné des métiers dans l'adoption de solutions IA pour 
     l'automatisation des reportings."
   
   Pour Consolidation IFRS :
   "- L'un est expert IFRS (10+ ans, normes IFRS 9/15/16) avec expérience de montée en compétence 
     des filiales et pilotage de projet de migration OneStream.
   - L'autre combine expertise normative IFRS, maîtrise Excel/VBA avancée et forte pédagogie 
     (formations équipes locales, documentation processus)."
   
   Pour Comptabilité bancaire :
   "- L'un possède une expérience en comptabilité bancaire (clôtures réglementaires FINREP/COREP, 
     PCB) et a piloté l'automatisation des réconciliations via Excel/VBA et Power BI.
   - L'autre vient de la fintech et combine expertise fiscale bancaire (IS, TVA) avec participation 
     active aux projets d'implémentation de nouveaux produits (Agile/Scrum)."

6. Offre sans engagement (15-20 mots) :
   "Seriez-vous d'accord pour recevoir leurs synthèses anonymisées ? Cela vous permettrait 
   de juger leur pertinence en 30 secondes."
   
7. Formule de politesse : "Bien à vous,"

INTERDICTIONS ABSOLUES :
- ❌ Jamais "Notre cabinet", "Nos services", "Notre expertise"
- ❌ Jamais de superlatifs ("meilleurs", "excellents")
- ❌ Jamais proposer des profils GÉNÉRIQUES ("contrôle de gestion", "FP&A") sans compétences précises !
- ❌ Jamais de formulations vagues type "maîtrise avancée d'Excel" sans préciser (VBA, Power Query, etc.)
- ❌ Jamais plus de 120 mots
- ❌ JAMAIS de ton commercial type : "Auriez-vous un rapide créneau de 15 min"
- ❌ JAMAIS de phrases bateau : "recruter crée un dilemme : technique vs business"
- ❌ JAMAIS proposer un appel téléphonique directement

VALIDATION CRITIQUE AVANT ENVOI :
1. Les profils proposés mentionnent-ils EXPLICITEMENT les compétences détectées ? → Si NON : RECOMMENCER
2. L'observation mentionne-t-elle au moins 2 compétences RARES entre parenthèses ? → Si NON : RECOMMENCER
3. Y a-t-il des formulations vagues type "expertise", "maîtrise", "expérience" SANS précision ? → Si OUI : RECOMMENCER
4. Le message fait-il plus de 120 mots ? → Si OUI : RÉDUIRE

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
        
        # ========================================
        # VÉRIFICATION POST-GÉNÉRATION (NOUVEAU V26)
        # ========================================
        if "2 profils" not in result.lower() and "deux profils" not in result.lower():
            log_event('message_2_missing_profiles', {
                'prospect': prospect_data.get('_id', 'unknown'),
                'message_preview': result[:200]
            })
            
            print("⚠️  Message 2 sans profils détecté - Utilisation du fallback...")
            result = generate_message_2_fallback(first_name, context_name, is_hiring, 
                                                  job_posting_data, job_category, prospect_data)
        
        log_event('generate_message_2_success', {'length': len(result)})
        return result
        
    except anthropic.APIError as e:
        log_error('claude_api_error', str(e), {'function': 'generate_message_2'})
        return generate_message_2_fallback(first_name, context_name, is_hiring, 
                                          job_posting_data, job_category, prospect_data)
    
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