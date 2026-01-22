"""
═══════════════════════════════════════════════════════════════════
MESSAGE SEQUENCE GENERATOR - V23 (OPTIMISÉ PAIN POINTS + OUTCOMES)
Modifications : Prompts optimisés avec pain points métier, outcomes cabinet,
adaptation selon richesse données scrapées
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
# PAIN POINTS ET OUTCOMES PAR MÉTIER
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
        "polyvalence extrême : comptabilité, contrôle, trésorerie, fiscalité",
        "sous-dimensionnement chronique des équipes",
        "outils finance insuffisants (ERP sous-exploité, reporting artisanal)",
        "forte dépendance à quelques personnes clés"
    ],
    'controle_gestion': [
        "données peu fiables et disponibles trop tard pour décider",
        "manque de profils hybrides finance + data",
        "difficulté à passer du reporting au business partnering",
        "projets EPM/BI qui n'aboutissent pas ou ne sont pas adoptés"
    ],
    'fpna': [
        "trop de dépendance à Excel, retraitements manuels multiples",
        "équipes cantonnées au reporting, faible influence sur les décisions",
        "multiplication des demandes métiers sans priorisation claire"
    ],
    'comptabilite': [
        "charge de clôture excessive et récurrente",
        "pénurie de profils comptables opérationnels fiables",
        "dépendance à des personnes clés",
        "qualité des données perfectible"
    ],
    'consolidation': [
        "process lourds et peu automatisés (forte dépendance Excel)",
        "pression extrême sur les délais de clôture groupe",
        "qualité hétérogène des données filiales",
        "key-man risk élevé (connaissance concentrée)"
    ],
    'audit': [
        "couverture de risques insuffisante face à la croissance du périmètre",
        "manque de profils seniors autonomes capables de dialoguer avec la DG",
        "backlog de recommandations non suivies",
        "transformation vers l'audit data-driven difficile à mener"
    ],
    'epm': [
        "projets EPM qui s'éternisent, forte dépendance aux intégrateurs",
        "faible adoption des outils (contournements Excel persistants)",
        "gouvernance des données insuffisante (multiples versions de la vérité)",
        "key-man risk élevé sur la connaissance des outils"
    ],
    'bi_data': [
        "accès aux données lent et instable",
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
        "stabilisation et montée en compétence des équipes",
        "capacité à mener la transformation sans rupture",
        "finance repositionnée comme partenaire business"
    ],
    'controle_gestion': [
        "accélération du pilotage de la performance",
        "transformation du rôle des équipes vers le business partnering",
        "réussite des projets EPM/BI par des profils sachant les porter"
    ],
    'audit': [
        "couverture de risques alignée avec la stratégie",
        "renforcement rapide du niveau senior",
        "crédibilité renforcée auprès des comités"
    ]
}


# ========================================
# DÉTECTION AUTOMATIQUE DU MÉTIER
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
        return 'general'  # Défaut finance générique


def get_relevant_pain_points(job_category, max_points=2):
    """Récupère les pain points pertinents pour le métier détecté"""
    pain_points = PAIN_POINTS_BY_JOB.get(job_category, PAIN_POINTS_BY_JOB['daf'])
    return pain_points[:max_points]


def get_relevant_outcomes(job_category, max_outcomes=2):
    """Récupère les outcomes pertinents"""
    outcomes = OUTCOMES_CABINET.get(job_category, OUTCOMES_CABINET['general'])
    return outcomes[:max_outcomes]


# ========================================
# ÉVALUATION RICHESSE DES DONNÉES
# ========================================

def assess_data_richness(hooks_data, job_posting_data):
    """
    Évalue la richesse des données scrapées pour adapter le style du message
    
    Returns:
        str: 'rich' (contenu LinkedIn/web riche) ou 'basic' (juste fiche de poste)
    """
    
    # Critères de richesse
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
    """
    Définit le sujet de la discussion.
    """
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
# 1. GÉNÉRATEUR D'OBJETS (OPTIMISÉ PAIN POINTS)
# ========================================

def generate_subject_lines(prospect_data, job_posting_data):
    """Génère les objets d'email axés pain points"""
    
    log_event('generate_subject_lines_start', {
        'prospect': prospect_data.get('_id', 'unknown')
    })
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    context_name, is_hiring = get_smart_context(job_posting_data, prospect_data)
    job_category = detect_job_category(prospect_data, job_posting_data)
    pain_points = get_relevant_pain_points(job_category, max_points=2)
    
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
Mots-clés détectés : {', '.join([
    word for word in str(job_posting_data).lower().split() 
    if word in ['tagetik', 'epm', 'sap', 'consolidation', 'ifrs', 'hyperion', 
                'anaplan', 'change', 'adoption', 'bi', 'data', 'excel', 
                'reporting', 'forecast', 'budget', 'fp&a']
][:5]) if job_posting_data else 'Aucun'}

PAIN POINTS CONTEXTUELS (à intégrer subtilement) :
- {pain_points[0] if len(pain_points) > 0 else 'recrutement complexe'}
- {pain_points[1] if len(pain_points) > 1 else 'difficulté à trouver profils'}

CONSIGNE :
Génère 3 objets d'email courts (40-60 caractères) qui :
1. Mentionnent les MOTS-CLÉS du job posting (si présents)
2. Évoquent les pain points de manière INTERROGATIVE
3. Restent sobres et professionnels

FORMAT ATTENDU :
1. [Question ouverte avec mot-clé poste]
2. [Constat marché avec pain point]
3. [Objet direct : "Re: [titre poste]"]

EXEMPLES DE BONS OBJETS (selon contexte) :

Pour EPM/Tagetik :
1. Tagetik : profils Tech OU Change ?
2. Adoption EPM : le vrai défi
3. Re: Senior Functional Analyst Tagetik

Pour Consolidation :
1. Consolidation : Excel ou outil groupe ?
2. Clôture groupe : le dilemme compétences
3. Re: Responsable Consolidation

Pour FP&A :
1. FP&A : reporting ou business partner ?
2. Profils hybrides Finance + Data
3. Re: Directeur FP&A

Pour Comptabilité :
1. Comptables autonomes : marché tendu
2. Clôture : absorber les pics
3. Re: Chef Comptable

INTERDICTIONS :
- ❌ Pas de "Opportunité", "Proposition", "Collaboration"
- ❌ Pas de points d'exclamation
- ❌ Pas de promesses directes
- ❌ Pas de "Notre cabinet"

IMPÉRATIF : Si le job posting mentionne un outil précis (Tagetik, SAP, Anaplan, etc.), 
l'objet 1 ou 2 DOIT mentionner cet outil !

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
# 2. MESSAGE 2 : LE DILEMME (OPTIMISÉ)
# ========================================

def generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content):
    """Génère le message 2 avec pain points + outcomes cabinet"""
    
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
    
    if is_hiring:
        intro_phrase = f"Je me permets de vous relancer concernant votre recherche de {context_name}."
        context_type = "ce recrutement"
    else:
        intro_phrase = f"Je reviens vers vous concernant la structuration de {context_name}."
        context_type = "ce type de besoin"
    
    prompt = f"""Tu es chasseur de têtes spécialisé Finance.

CONTEXTE :
Prospect : {first_name}
Poste/Sujet : {context_name}
Métier : {job_category}
Type : {'Recrutement actif' if is_hiring else 'Approche spontanée'}

PAIN POINTS IDENTIFIÉS (à mentionner subtilement) :
- {pain_points[0] if len(pain_points) > 0 else 'difficulté à recruter'}
- {pain_points[1] if len(pain_points) > 1 else 'manque de profils qualifiés'}

OUTCOME CABINET (à suggérer sans vendre) :
- {outcomes[0] if len(outcomes) > 0 else 'sécurisation rapide de profils alignés'}

TON ET STYLE (IMPÉRATIF) :
- Consultatif, PAS commercial
- Crédibilité par l'observation marché, PAS par l'auto-promotion
- Proposition concrète sans engagement
- 100-120 mots maximum

STRUCTURE STRICTE :
1. "Bonjour {first_name},"
2. SAUT DE LIGNE
3. "{intro_phrase}"
4. Observation marché crédible mentionnant UN pain point (exemple : "Sur {context_type}, je constate souvent que...")
5. Proposition concrète : "J'ai identifié 2 profils [expertise pertinente] qui pourraient retenir votre attention."
6. Offre sans engagement : "Seriez-vous d'accord pour recevoir leurs synthèses anonymisées ? Cela vous permettrait de juger leur pertinence en 30 secondes."
7. Formule de politesse simple

INTERDICTIONS :
- Pas de "Notre cabinet", "Nos services", "Notre expertise"
- Pas de superlatifs ("meilleurs", "excellents")
- Pas de jargon cabinet ("chasse de têtes", "approche directe")
- Pas plus de 120 mots

EXEMPLES DE TON À REPRODUIRE :
"Sur ce type de poste, je constate souvent que le défi n'est pas la technique pure, mais la capacité à dialoguer avec les opérationnels..."
"Dans mes accompagnements récents, l'apport externe a surtout permis de sécuriser rapidement des profils opérationnels..."

Génère le message 2 :"""

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
# 3. MESSAGE 3 : BREAK-UP (TEMPLATE FIXE)
# ========================================

def generate_message_3(prospect_data, message_1_content, job_posting_data):
    """Génère le message 3 - Template fixe approuvé"""
    
    log_event('generate_message_3_start', {
        'prospect': prospect_data.get('_id', 'unknown')
    })
    
    first_name = get_safe_firstname(prospect_data)
    
    # Template fixe basé sur vos exemples qui fonctionnent
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
# FONCTION HELPER (AVEC VALIDATION)
# ========================================

def generate_full_sequence(prospect_data, hooks_data, job_posting_data, message_1_content):
    """
    Génère une séquence complète avec logging, tracking et validation
    Version optimisée avec pain points + outcomes
    """
    
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
        # Génération
        subject_lines = generate_subject_lines(prospect_data, job_posting_data)
        message_2 = generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content)
        message_3 = generate_message_3(prospect_data, message_1_content, job_posting_data)
        
        sequence = {
            'subject_lines': subject_lines,
            'message_1': message_1_content,
            'message_2': message_2,
            'message_3': message_3
        }
        
        # Validation
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