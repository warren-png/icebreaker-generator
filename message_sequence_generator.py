"""
═══════════════════════════════════════════════════════════════════
MESSAGE SEQUENCE GENERATOR - V22 (SEMAINE 1 - MONITORING & SÉCURITÉ)
Ajouts : Logging, Cost Tracking, Validation, Fallback
Comportement : IDENTIQUE à V21
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
# 1. GÉNÉRATEUR D'OBJETS (AVEC TRACKING)
# ========================================

def generate_subject_lines(prospect_data, job_posting_data):
    """Génère les objets d'email avec tracking des coûts"""
    
    log_event('generate_subject_lines_start', {
        'prospect': prospect_data.get('_id', 'unknown')
    })
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    context_name, is_hiring = get_smart_context(job_posting_data, prospect_data)
    
    if is_hiring:
        prompt_context = f"Recrutement pour : {context_name}"
    else:
        prompt_context = f"Sujet : Organisation de {context_name} (Approche Spontanée)"
    
    prompt = f"""Tu es un copywriter B2B.
CONTEXTE :
{prompt_context}
Chez : {prospect_data.get('company', 'l\'entreprise')}

Génère 3 variantes d'objets courts :
- V1 : Question expertise
- V2 : Enjeu organisationnel
- V3 : Sujet direct
"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # ✅ NOUVEAU : Tracker les coûts
        tracker.track(message.usage, 'generate_subject_lines')
        
        result = message.content[0].text.strip()
        
        log_event('generate_subject_lines_success', {
            'length': len(result)
        })
        
        return result
        
    except anthropic.APIError as e:
        log_error('claude_api_error', str(e), {'function': 'generate_subject_lines'})
        # ✅ NOUVEAU : Fallback si erreur
        from prospection_utils.fallback_templates import generate_fallback_subjects
        return generate_fallback_subjects(prospect_data, job_posting_data)
    
    except Exception as e:
        log_error('unexpected_error', str(e), {'function': 'generate_subject_lines'})
        return f"Echange | {context_name}"


# ========================================
# 2. MESSAGE 2 : LE DILEMME (AVEC TRACKING)
# ========================================

def generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content):
    """Génère le message 2 avec tracking et fallback"""
    
    log_event('generate_message_2_start', {
        'prospect': prospect_data.get('_id', 'unknown'),
        'has_hooks': hooks_data != "NOT_FOUND"
    })
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    first_name = get_safe_firstname(prospect_data)
    context_name, is_hiring = get_smart_context(job_posting_data, prospect_data)
    hooks_str = str(hooks_data) if hooks_data and hooks_data != "NOT_FOUND" else "Aucune actualité récente"
    
    if is_hiring:
        intro_phrase = f"Je fais suite à mon message concernant le poste de {context_name}."
    else:
        intro_phrase = f"Je fais suite à mon message concernant la structuration de {context_name}."

    prompt = f"""Tu es chasseur de têtes expert.

CONTEXTE :
Prospect : {first_name}
Sujet : {context_name}
Mode : {'Recrutement Actif' if is_hiring else 'Approche Spontanée'}

CONSIGNE FORMATAGE :
1. "Bonjour {first_name},"
2. SAUTE DEUX LIGNES.

STRUCTURE :
1. Intro : "{intro_phrase}"
2. Le Dilemme : "En observant le marché, recruter ou structurer des profils [Expertise] crée souvent un dilemme : soit on a la technique mais pas le business, soit l'inverse..."
3. La Solution Hybride.
4. CONCLUSION (Strictement une de ces options) :
   - "C'est précisément sur l'identification de ces profils que j'accompagne mes clients. Auriez-vous un rapide créneau de 15 min prochainement ou seriez-vous ouvert à recevoir des candidatures qui correspondent à votre besoin ?"

Génère le message 2.
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # ✅ NOUVEAU : Tracker les coûts
        tracker.track(message.usage, 'generate_message_2')
        
        result = message.content[0].text
        
        log_event('generate_message_2_success', {
            'length': len(result)
        })
        
        return result
        
    except anthropic.APIError as e:
        log_error('claude_api_error', str(e), {'function': 'generate_message_2'})
        # ✅ NOUVEAU : Fallback si erreur
        from prospection_utils.fallback_templates import generate_fallback_message
        return generate_fallback_message(2, prospect_data, job_posting_data)
    
    except Exception as e:
        log_error('unexpected_error', str(e), {'function': 'generate_message_2'})
        raise


# ========================================
# 3. MESSAGE 3 : BREAK-UP (AVEC TRACKING)
# ========================================

def generate_message_3(prospect_data, message_1_content, job_posting_data):
    """Génère le message 3 avec tracking et fallback"""
    
    log_event('generate_message_3_start', {
        'prospect': prospect_data.get('_id', 'unknown')
    })
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    first_name = get_safe_firstname(prospect_data)
    context_name, is_hiring = get_smart_context(job_posting_data, prospect_data)
    
    if is_hiring:
        intro_stop = "Sans retour de votre part, je vais arrêter mes relances sur ce poste."
    else:
        intro_stop = "Sans retour de votre part, je ne vous solliciterai plus sur ce sujet."

    prompt = f"""Tu es chasseur de têtes. DERNIER message.

CONTEXTE :
Prospect : {first_name}
Sujet : {context_name}

CONSIGNE FORMATAGE :
1. "Bonjour {first_name},"
2. SAUTE DEUX LIGNES.

STRUCTURE :
1. Intro : "{intro_stop}"
2. Observation Marché (Statistique Pénurie crédible).
3. CONCLUSION (Strictement celle-ci) :
   - "Je clos ce dossier. Si toutefois la tension sur ces compétences spécifiques venait à freiner vos projets, je reste à votre disposition. Bonne continuation."

Génère le message 3.
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # ✅ NOUVEAU : Tracker les coûts
        tracker.track(message.usage, 'generate_message_3')
        
        result = message.content[0].text
        
        log_event('generate_message_3_success', {
            'length': len(result)
        })
        
        return result
        
    except anthropic.APIError as e:
        log_error('claude_api_error', str(e), {'function': 'generate_message_3'})
        # ✅ NOUVEAU : Fallback si erreur
        from prospection_utils.fallback_templates import generate_fallback_message
        return generate_fallback_message(3, prospect_data, job_posting_data)
    
    except Exception as e:
        log_error('unexpected_error', str(e), {'function': 'generate_message_3'})
        raise


# ========================================
# FONCTION HELPER (AVEC VALIDATION)
# ========================================

def generate_full_sequence(prospect_data, hooks_data, job_posting_data, message_1_content):
    """
    Génère une séquence complète avec logging, tracking et validation
    Comportement identique à la version précédente, mais avec monitoring
    """
    
    log_event('sequence_generation_start', {
        'prospect_id': prospect_data.get('_id', 'unknown'),
        'prospect_name': prospect_data.get('full_name', 'unknown'),
        'company': prospect_data.get('company', 'unknown'),
        'has_job_posting': bool(job_posting_data),
        'has_hooks': hooks_data != "NOT_FOUND"
    })
    
    try:
        # Génération (identique à avant)
        subject_lines = generate_subject_lines(prospect_data, job_posting_data)
        message_2 = generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content)
        message_3 = generate_message_3(prospect_data, message_1_content, job_posting_data)
        
        sequence = {
            'subject_lines': subject_lines,
            'message_1': message_1_content,
            'message_2': message_2,
            'message_3': message_3
        }
        
        # ✅ NOUVEAU : Validation avant de retourner
        is_valid = validate_and_report(sequence, prospect_data, raise_on_error=False)
        
        if not is_valid:
            log_error('sequence_validation_failed', 'Séquence générée invalide', {
                'prospect': prospect_data.get('_id', 'unknown')
            })
            # ✅ NOUVEAU : Utiliser fallback si validation échoue
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
        
        # ✅ NOUVEAU : Fallback complet en cas d'erreur critique
        print(f"❌ Erreur lors de la génération : {e}")
        print("🔄 Génération d'une séquence de fallback...")
        return generate_fallback_sequence(prospect_data, job_posting_data, message_1_content)






