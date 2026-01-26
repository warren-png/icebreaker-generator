"""
═══════════════════════════════════════════════════════════════════
ICEBREAKER GENERATOR V27.5 - PAIN POINTS 100% DYNAMIQUES
Modifications V27.5 :
- Pain points extraits dynamiquement de la fiche (plus de config.py)
- Prompts renforcés : interdiction "Je travaille", termes génériques
- Compétences rares injectées dans les prompts
- Formulations d'intro imposées
═══════════════════════════════════════════════════════════════════
"""

import anthropic
import os
import re
from datetime import datetime, timedelta
from config import COMPANY_INFO

# Imports utilitaires
from prospection_utils.logger import log_event, log_error
from prospection_utils.cost_tracker import tracker

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

if not ANTHROPIC_API_KEY:
    raise ValueError("❌ ANTHROPIC_API_KEY non trouvée")


# ========================================
# FONCTIONS APIFY (POUR APP_STREAMLIT.PY)
# ========================================

def init_apify_client():
    """Initialise le client Apify"""
    try:
        from apify_client import ApifyClient
        
        if not APIFY_API_TOKEN:
            raise ValueError("❌ APIFY_API_TOKEN non trouvée")
        
        client = ApifyClient(APIFY_API_TOKEN)
        log_event('apify_client_initialized', {'success': True})
        return client
        
    except ImportError:
        log_error('apify_import_error', 'apify_client non installé', {})
        raise ImportError("❌ Installez apify-client : pip install apify-client")
    
    except Exception as e:
        log_error('apify_init_error', str(e), {})
        raise


def scrape_linkedin_profile(apify_client, linkedin_url):
    """Scrape un profil LinkedIn via Apify"""
    try:
        log_event('scrape_linkedin_profile_start', {'url': linkedin_url})
        
        run_input = {
            "profileUrls": [linkedin_url]
        }
        
        run = apify_client.actor("dev_fusion/Linkedin-Profile-Scraper").call(run_input=run_input)
        items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if items:
            profile_data = items[0]
            log_event('scrape_linkedin_profile_success', {'items_count': len(items)})
            return profile_data
        else:
            log_event('scrape_linkedin_profile_empty', {'url': linkedin_url})
            return {}
        
    except Exception as e:
        log_error('scrape_linkedin_profile_error', str(e), {'url': linkedin_url})
        return {}


def scrape_linkedin_posts(apify_client, linkedin_url):
    """Scrape les posts LinkedIn d'un profil via Apify"""
    try:
        log_event('scrape_linkedin_posts_start', {'url': linkedin_url})
        
        run_input = {
            "deepScrape": True,
            "limitPerSource": 5,
            "rawData": False,
            "urls": [linkedin_url]
        }
        
        run = apify_client.actor("supreme_coder/linkedin-post").call(run_input=run_input)
        items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if items:
            log_event('scrape_linkedin_posts_success', {'posts_count': len(items)})
            return items
        else:
            log_event('scrape_linkedin_posts_empty', {'url': linkedin_url})
            return []
        
    except Exception as e:
        log_error('scrape_linkedin_posts_error', str(e), {'url': linkedin_url})
        return []


def extract_hooks_with_claude(profile_data, posts_data, web_results, company_data, 
                               news_results, full_name, company_name):
    """
    Extrait les meilleurs hooks depuis les données scrapées via Claude
    VERSION V27.4 : Filtrage dates AVANT extraction
    """
    try:
        log_event('extract_hooks_start', {'full_name': full_name})
        
        # NOUVEAU V27.4 : Filtrer les posts <3 mois AVANT envoi à Claude
        from message_sequence_generator import filter_recent_posts
        
        if posts_data and isinstance(posts_data, list):
            filtered_posts = filter_recent_posts(posts_data, max_age_months=3, max_posts=5)
            if filtered_posts:
                posts_data = filtered_posts
            else:
                log_event('no_recent_posts', {'full_name': full_name})
                return []
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        context = f"""
PROFIL : {full_name} - {company_name}

POSTS LINKEDIN (filtrés <3 mois) :
{format_posts_for_extraction(posts_data)}

PROFIL LINKEDIN :
{format_profile_for_extraction(profile_data)}
"""
        
        prompt = f"""Analyse ces données LinkedIn et extrait les 3-5 meilleurs hooks pour un message de prospection.

{context}

Un bon hook est :
- Récent (moins de 3 mois)
- Professionnel et pertinent
- Spécifique (mention d'un événement, projet, accomplissement)
- Authentique (vérifiable)

═══════════════════════════════════════════════════════════════════
⚠️  RÈGLES ABSOLUES - RESPECTE-LES IMPÉRATIVEMENT :
═══════════════════════════════════════════════════════════════════

1. ❌ JAMAIS généraliser ou paraphraser vaguement
   ✅ TOUJOURS citer des éléments CONCRETS des posts

2. ❌ JAMAIS écrire "votre initiative autour de..." ou "votre démarche sur..."
   ✅ TOUJOURS utiliser les termes EXACTS : "Data & AI Day", "Centre d'Excellence", "podcast Inside Banking"

3. ❌ JAMAIS inventer des informations non présentes
   ✅ TOUJOURS extraire uniquement ce qui est EXPLICITEMENT mentionné

4. ✅ Si un post mentionne un événement → cite le NOM exact de l'événement
5. ✅ Si un post mentionne un projet → cite le NOM exact du projet
6. ✅ Si un post mentionne une certification → cite la certification EXACTE
7. ✅ Si un post mentionne un podcast → cite le NOM du podcast ET l'invité si mentionné
8. ✅ Si un post mentionne un article → cite le TITRE et la publication

═══════════════════════════════════════════════════════════════════

Format de retour (JSON uniquement, sans texte avant/après) :
[
  {{"text": "Votre participation au podcast Inside Banking avec Richard Michaud sur l'adoption de l'IA", "type": "post", "date": "2025-01"}},
  {{"text": "Votre organisation du premier Data & AI Day chez LCL avec plus de 130 collaborateurs", "type": "post", "date": "2024-11"}}
]

Si aucun hook pertinent récent n'est trouvé, retourne : []
"""
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        tracker.track(message.usage, 'extract_hooks_with_claude')
        
        result = message.content[0].text.strip()
        
        # Parser le JSON en gérant les backticks Markdown
        import json
        
        json_match = re.search(r'```json\s*(\[.*?\])\s*```', result, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(1)
        else:
            json_array_match = re.search(r'(\[.*?\])', result, re.DOTALL)
            if json_array_match:
                json_str = json_array_match.group(1)
            else:
                json_str = result
        
        try:
            hooks = json.loads(json_str)
            
            if not isinstance(hooks, list):
                log_event('extract_hooks_invalid_format', {'type': type(hooks).__name__})
                return []
            
            log_event('extract_hooks_success', {'hooks_count': len(hooks)})
            return hooks
            
        except json.JSONDecodeError as e:
            log_event('extract_hooks_json_error', {
                'raw_result': result[:500],
                'error': str(e)
            })
            return []
        
    except Exception as e:
        log_error('extract_hooks_error', str(e), {'full_name': full_name})
        return []


def format_posts_for_extraction(posts_data):
    """Formate les posts pour l'extraction de hooks"""
    if not posts_data:
        return "Aucun post disponible"
    
    formatted = []
    for i, post in enumerate(posts_data[:5]):
        text = post.get('text', '')
        date = post.get('date', post.get('postedDate', 'N/A'))
        title = post.get('title', '')
        
        post_content = f"Post {i+1} ({date})"
        if title:
            post_content += f"\nTitre: {title}"
        post_content += f"\nContenu: {text[:500]}"
        
        formatted.append(post_content)
    
    return "\n\n".join(formatted)


def format_profile_for_extraction(profile_data):
    """Formate le profil pour l'extraction de hooks"""
    if not profile_data:
        return "Aucune donnée de profil disponible"
    
    return f"""
Titre : {profile_data.get('headline', 'N/A')}
Entreprise : {profile_data.get('company', 'N/A')}
Expériences : {profile_data.get('experiences', [])}
Certifications : {profile_data.get('certifications', [])}
"""


def generate_advanced_icebreaker(prospect_data, hooks_data, job_posting_data):
    """Wrapper pour appeler generate_icebreaker (compatibilité app_streamlit.py)"""
    return generate_icebreaker(prospect_data, hooks_data, job_posting_data)


# ========================================
# EXTRACTION ET VALIDATION DES HOOKS
# ========================================

def extract_hooks_from_linkedin(hooks_data):
    """Extrait les hooks valides depuis les données LinkedIn scrapées"""
    if not hooks_data or hooks_data == "NOT_FOUND":
        log_event('no_hooks_available', {})
        return []
    
    hooks_list = []
    
    if isinstance(hooks_data, list):
        for idx, post in enumerate(hooks_data):
            if isinstance(post, dict) and post.get('text'):
                hooks_list.append({
                    'text': str(post.get('text', '')).strip(),
                    'type': post.get('type', 'post'),
                    'index': idx,
                    'title': post.get('title', ''),
                    'date': post.get('date', post.get('postedDate', ''))
                })
    
    elif isinstance(hooks_data, dict):
        posts = hooks_data.get('posts', hooks_data.get('content', []))
        if isinstance(posts, list):
            for idx, post in enumerate(posts):
                if isinstance(post, dict) and post.get('text'):
                    hooks_list.append({
                        'text': str(post.get('text', '')).strip(),
                        'type': post.get('type', 'post'),
                        'index': idx,
                        'title': post.get('title', ''),
                        'date': post.get('date', post.get('postedDate', ''))
                    })
    
    elif isinstance(hooks_data, str) and len(hooks_data) > 50:
        hooks_list.append({
            'text': hooks_data.strip(),
            'type': 'legacy',
            'index': 0,
            'title': '',
            'date': ''
        })
    
    valid_hooks = [h for h in hooks_list if len(h['text']) >= 30]
    
    log_event('hooks_extracted', {
        'total_found': len(hooks_list),
        'valid_hooks': len(valid_hooks)
    })
    
    return valid_hooks


def score_hook_relevance(hook, job_posting_data):
    """
    Score un hook de 1 à 10 selon sa pertinence
    VERSION V27.4 : Bonus massifs pour événements majeurs
    """
    if not job_posting_data:
        return 2, []
    
    hook_text = hook['text'].lower()
    hook_title = hook.get('title', '').lower()
    combined_text = f"{hook_text} {hook_title}"
    
    job_title = str(job_posting_data.get('title', '')).lower()
    job_desc = str(job_posting_data.get('description', '')).lower()
    job_full = f"{job_title} {job_desc}"
    
    score = 0
    matching_keywords = []
    
    # ========================================
    # NIVEAU 1 : COMPÉTENCES TECHNIQUES (+3 points)
    # ========================================
    technical_keywords = [
        'tagetik', 'epm', 'anaplan', 'hyperion', 'oracle planning', 'sap bpc', 'sap bfc', 'onestream',
        'sap', 's/4hana', 's4hana', 'oracle', 'sage', 'sage x3', 'dynamics',
        'ifrs', 'consolidation', 'statutory reporting', 'gaap', 'sox',
        'power bi', 'powerbi', 'tableau', 'qlik', 'data science', 'python', 'sql', 'r',
        'agile', 'scrum', 'kanban', 'safe', 'prince2', 'pmp',
        'ia', 'ai', 'intelligence artificielle', 'machine learning', 'copilot', 'chatgpt',
        'adoption ia', 'acculturation ia', 'acculturation', 'adoption',
        'data & ai day', 'ai day', 'centre d\'excellence', 'centre excellence',
        'trésorerie', 'cash management', 'fiscalité', 'tax', 'fp&a', 'fpa',
        'bancaire', 'bank', 'banque', 'fintech', 'audiovisuel', 'cinéma', 'production',
        'alm', 'actif-passif', 'liquidité', 'refinancement',
        'solvabilité', 'solvency', 'iard', 'assurance', 'actuariat'
    ]
    
    for kw in technical_keywords:
        if kw in job_full and kw in combined_text:
            score += 3
            matching_keywords.append(kw)
            break
    
    # ========================================
    # NIVEAU 2 : CONTEXTE PROFESSIONNEL (+2 points)
    # ========================================
    context_keywords = [
        'transformation', 'digitalisation', 'automatisation', 'projet',
        'déploiement', 'implémentation', 'migration', 'change management',
        'adoption', 'formation', 'training', 'accompagnement',
        'gouvernance', 'data governance', 'process', 'efficiency',
        'reporting', 'forecast', 'budget', 'clôture'
    ]
    
    context_matches = sum(1 for kw in context_keywords if kw in job_full and kw in combined_text)
    if context_matches >= 2:
        score += 2
        matching_keywords.append(f"{context_matches} context keywords")
    
    # ========================================
    # NIVEAU 3 : SECTEUR/INDUSTRIE (+1 point)
    # ========================================
    sector_keywords = [
        'finance', 'financial', 'comptabilité', 'accounting',
        'contrôle de gestion', 'fpa', 'audit', 'consolidation',
        'data', 'données', 'analytics'
    ]
    
    if any(kw in job_full and kw in combined_text for kw in sector_keywords):
        score += 1
        matching_keywords.append("sector match")
    
    # ========================================
    # BONUS ÉVÉNEMENTS MAJEURS
    # ========================================
    
    # 1. PODCAST/INTERVIEW (+3.0) - PRIORITÉ ABSOLUE
    podcast_keywords = ['podcast', 'inside banking', 'interview', 'échange avec', 'j\'ai eu le plaisir']
    if any(kw in combined_text for kw in podcast_keywords):
        score += 3.0
        matching_keywords.append("podcast_bonus_+3.0")
    
    # 2. ARTICLE PUBLIÉ (+2.5)
    article_keywords = ['article', 'publié dans', 'tribune', 'j\'ai écrit', 'publication']
    if any(kw in combined_text for kw in article_keywords):
        score += 2.5
        matching_keywords.append("article_bonus_+2.5")
    
    # 3. AWARD/RÉCOMPENSE (+2.5)
    award_keywords = ['award', 'prix', 'récompense', 'distinction', 'lauréat', 'trophée']
    if any(kw in combined_text for kw in award_keywords):
        score += 2.5
        matching_keywords.append("award_bonus_+2.5")
    
    # 4. CERTIFICATION (+2.0)
    cert_keywords = ['certifié', 'certification', 'safe', 'pmp', 'aws', 'diplôme', 'formation certifiante', 'cia', 'cisa']
    if any(kw in combined_text for kw in cert_keywords):
        score += 2.0
        matching_keywords.append("certification_bonus_+2.0")
    
    # 5. ÉVÉNEMENT/CONFÉRENCE (+2.0)
    event_keywords = ['conférence', 'webinar', 'speaker', 'intervenant', 'table ronde', 'vivatech', 'salon', 'événement dédié']
    if any(kw in combined_text for kw in event_keywords):
        score += 2.0
        matching_keywords.append("event_bonus_+2.0")
    
    # 6. LANCEMENT PROJET (+2.0)
    launch_keywords = ['lancement', 'lancer', 'accélère', 'démarrage', 'inauguration', 'premier', 'première']
    if any(kw in combined_text for kw in launch_keywords):
        score += 2.0
        matching_keywords.append("launch_bonus_+2.0")
    
    # ========================================
    # PÉNALITÉS
    # ========================================
    generic_phrases = ['heureux de', 'ravi de', 'fier de', 'merci', 'bravo', 'félicitations']
    if any(phrase in combined_text for phrase in generic_phrases) and score < 3:
        score -= 1
        matching_keywords.append("generic_penalty")
    
    # ========================================
    # CALCUL FINAL
    # ========================================
    final_score = max(1, min(10, score))
    
    log_event('hook_scored', {
        'hook_index': hook.get('index'),
        'score': final_score,
        'matching_keywords': matching_keywords,
        'hook_preview': hook_text[:100]
    })
    
    return final_score, matching_keywords


def select_best_hook(hooks_list, job_posting_data):
    """Sélectionne le hook avec le meilleur score"""
    if not hooks_list:
        log_event('no_hooks_to_select', {})
        return None, 0, []
    
    scored_hooks = []
    
    for hook in hooks_list:
        score, keywords = score_hook_relevance(hook, job_posting_data)
        scored_hooks.append({
            'hook': hook,
            'score': score,
            'keywords': keywords
        })
    
    scored_hooks.sort(key=lambda x: x['score'], reverse=True)
    
    best = scored_hooks[0]
    
    log_event('best_hook_selected', {
        'score': best['score'],
        'keywords': best['keywords'],
        'total_hooks_analyzed': len(scored_hooks),
        'all_scores': [h['score'] for h in scored_hooks]
    })
    
    return best['hook'], best['score'], best['keywords']


# ========================================
# DÉTECTION DU MÉTIER - V27.4 AMÉLIORÉE
# ========================================

def detect_job_category(prospect_data, job_posting_data):
    """
    Détecte automatiquement la catégorie métier du prospect
    VERSION V27.4 : PRIORITÉ TITRE > DESCRIPTION + exclusions contextuelles
    """
    
    # ÉTAPE 1 : Extraire TITRE seul (prioritaire)
    job_title = ""
    if job_posting_data:
        job_title = str(job_posting_data.get('title', '')).lower()
    
    # ÉTAPE 2 : Extraire description (secondaire)
    job_desc = ""
    if job_posting_data:
        job_desc = str(job_posting_data.get('description', '')).lower()
    
    # ÉTAPE 3 : Headline prospect (tertiaire)
    headline = f"{prospect_data.get('headline', '')} {prospect_data.get('title', '')}".lower()
    
    # ════════════════════════════════════════════════════════════════
    # DÉTECTION SUR TITRE UNIQUEMENT (PRIORITÉ ABSOLUE)
    # ════════════════════════════════════════════════════════════════
    
    # Comptable / Comptabilité
    if any(word in job_title for word in ['comptable', 'accountant', 'accounting']):
        # EXCLUSION : "comptable" dans titre mais "consolidation" aussi → consolidation
        if 'consolidation' in job_title or 'consolidateur' in job_title:
            return 'consolidation'
        return 'comptabilite'
    
    # Audit
    if any(word in job_title for word in ['audit', 'auditeur', 'auditor']):
        return 'audit'
    
    # Consolidation
    if any(word in job_title for word in ['consolidation', 'consolidateur', 'consolidator']):
        return 'consolidation'
    
    # Contrôle de gestion
    if any(word in job_title for word in ['contrôle de gestion', 'controle de gestion', 'contrôleur de gestion', 'controller', 'business controller']):
        return 'controle_gestion'
    
    # FP&A
    if any(word in job_title for word in ['fp&a', 'fpa', 'financial planning', 'fpna']):
        return 'fpna'
    
    # DAF / CFO
    if any(word in job_title for word in ['daf', 'directeur administratif', 'cfo', 'chief financial', 'directeur financier']):
        return 'daf'
    
    # RAF
    if any(word in job_title for word in ['raf', 'responsable administratif']):
        return 'raf'
    
    # Data / IA
    if any(word in job_title for word in ['data officer', 'ia officer', 'ai officer', 'data & ia', 'chief data', 'cdo']):
        return 'data_ia'
    
    # EPM
    if any(word in job_title for word in ['epm', 'anaplan', 'hyperion', 'tagetik']):
        return 'epm'
    
    # BI / Data
    if any(word in job_title for word in ['bi ', 'business intelligence', ' data ', 'analytics']):
        return 'bi_data'
    
    # ════════════════════════════════════════════════════════════════
    # SI TITRE NON CONCLUANT → DESCRIPTION (avec exclusions)
    # ════════════════════════════════════════════════════════════════
    
    # Nettoyer la description des mentions contextuelles
    desc_cleaned = job_desc
    
    # Exclure "ou audit", "contrôles de niveau 2", etc.
    contextual_exclusions = [
        r'\bou audit\b',
        r'\baudit externe\b',  # Souvent mentionné comme "en lien avec audit externe"
        r'\bcontrôles? de niveau \d\b',
        r'\brelation avec.*audit\b',
        r'\ben collaboration avec.*audit\b',
        r'\baudit interne et externe\b'  # Contexte, pas le poste
    ]
    
    for pattern in contextual_exclusions:
        desc_cleaned = re.sub(pattern, '', desc_cleaned, flags=re.IGNORECASE)
    
    # Maintenant chercher dans description nettoyée
    if any(word in desc_cleaned for word in ['comptable', 'comptabilité', 'accounting']) and 'audit' not in job_title:
        return 'comptabilite'
    
    if any(word in desc_cleaned for word in ['auditeur', 'audit interne', 'internal audit']):
        return 'audit'
    
    if any(word in desc_cleaned for word in ['consolidation', 'ifrs 10', 'normes ifrs']):
        return 'consolidation'
    
    if any(word in desc_cleaned for word in ['contrôle de gestion', 'business controller']):
        return 'controle_gestion'
    
    # ════════════════════════════════════════════════════════════════
    # FALLBACK : HEADLINE PROSPECT
    # ════════════════════════════════════════════════════════════════
    
    if any(word in headline for word in ['daf', 'cfo', 'directeur financier']):
        return 'daf'
    elif any(word in headline for word in ['audit']):
        return 'audit'
    elif any(word in headline for word in ['comptab']):
        return 'comptabilite'
    elif any(word in headline for word in ['contrôl']):
        return 'controle_gestion'
    
    return 'general'


def get_relevant_pain_point(job_category, job_posting_data):
    """
    Sélectionne LE pain point le plus pertinent selon le métier et la fiche de poste
    VERSION V27.5 : 100% dynamique via Claude, plus de fallback config.py
    """
    # Importer depuis message_sequence_generator pour cohérence
    from message_sequence_generator import get_relevant_pain_point as get_pain_point_v2
    return get_pain_point_v2(job_category, job_posting_data)


# ========================================
# GÉNÉRATEUR D'ICEBREAKER (MESSAGE 1)
# ========================================

def generate_icebreaker(prospect_data, hooks_data, job_posting_data):
    """
    Génère l'icebreaker (Message 1) en sélectionnant le meilleur hook
    VERSION V27.4 : Filtrage hooks <3 mois AVANT sélection
    """
    log_event('generate_icebreaker_start', {
        'prospect': prospect_data.get('_id', 'unknown'),
        'has_job_posting': bool(job_posting_data),
        'hooks_type': type(hooks_data).__name__
    })
    
    # NOUVEAU V27.4 : Filtrer hooks <3 mois
    from message_sequence_generator import filter_recent_posts
    
    if hooks_data != "NOT_FOUND" and isinstance(hooks_data, list):
        filtered_posts = filter_recent_posts(hooks_data, max_age_months=3, max_posts=5)
        if filtered_posts:
            hooks_data = filtered_posts
        else:
            log_event('hooks_filtered_out_all', {'reason': 'No posts within 3 months'})
            hooks_data = "NOT_FOUND"
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    first_name = get_safe_firstname(prospect_data)
    context_name, is_hiring = get_smart_context(job_posting_data, prospect_data)
    job_category = detect_job_category(prospect_data, job_posting_data)
    pain_point = get_relevant_pain_point(job_category, job_posting_data)
    
    hooks_list = extract_hooks_from_linkedin(hooks_data)
    best_hook, hook_score, hook_keywords = select_best_hook(hooks_list, job_posting_data)
    
    if best_hook and hook_score >= 3:
        message_type = "CAS A (Hook LinkedIn + Annonce)"
        hook_text = best_hook['text']
        hook_title = best_hook.get('title', '')
    elif best_hook and hook_score >= 2:
        message_type = "CAS B (Hook faible + Focus annonce)"
        hook_text = best_hook['text']
        hook_title = best_hook.get('title', '')
    else:
        message_type = "CAS C (Annonce seule)"
        hook_text = None
        hook_title = None
    
    log_event('icebreaker_strategy', {
        'message_type': message_type,
        'hook_score': hook_score,
        'hook_keywords': hook_keywords,
        'job_category': job_category,
        'pain_point_used': pain_point['short']
    })
    
    if message_type == "CAS A (Hook LinkedIn + Annonce)":
        prompt = build_prompt_case_a(first_name, context_name, hook_text, hook_title, 
                                     job_posting_data, pain_point)
    elif message_type == "CAS B (Hook faible + Focus annonce)":
        prompt = build_prompt_case_b(first_name, context_name, hook_text, 
                                     job_posting_data, pain_point)
    else:
        prompt = build_prompt_case_c(first_name, context_name, job_posting_data, pain_point)
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        
        tracker.track(message.usage, 'generate_icebreaker')
        result = message.content[0].text.strip()
        
        # Nettoyage des signatures parasites
        result = clean_signature(result)
        
        log_event('icebreaker_generated', {
            'length': len(result),
            'message_type': message_type,
            'hook_score': hook_score
        })
        
        return result
        
    except anthropic.APIError as e:
        log_error('claude_api_error', str(e), {'function': 'generate_icebreaker'})
        return generate_fallback_icebreaker(first_name, context_name, is_hiring)
    
    except Exception as e:
        log_error('unexpected_error', str(e), {'function': 'generate_icebreaker'})
        raise


# ========================================
# CONSTRUCTION DES PROMPTS
# ========================================

def build_prompt_case_a(first_name, context_name, hook_text, hook_title, 
                        job_posting_data, pain_point):
    """Prompt pour CAS A : Hook pertinent + Annonce"""
    
    job_title = job_posting_data.get('title', 'N/A') if job_posting_data else 'N/A'
    job_desc = job_posting_data.get('description', 'N/A') if job_posting_data else 'N/A'
    
    return f"""Tu es expert en prospection B2B pour cabinet de recrutement Finance.

CONTEXTE :
Prénom : {first_name}
Poste recherché : {context_name}

HOOK LINKEDIN SÉLECTIONNÉ (Score élevé - Très pertinent) :
Titre : {hook_title if hook_title else 'N/A'}
Contenu : {hook_text[:500]}

FICHE DE POSTE (pour identifier les compétences RARES) :
Titre : {job_title}
Description (extraits clés) : {str(job_desc)[:600]}

PAIN POINT IDENTIFIÉ :
Court : {pain_point['short']}
Contexte : {pain_point['context']}

═══════════════════════════════════════════════════════════════════
MISSION : Rédiger un icebreaker de 70-90 mots
═══════════════════════════════════════════════════════════════════

STRUCTURE OBLIGATOIRE :

1. "Bonjour {first_name},"

2. SAUT DE LIGNE (ligne vide)

3. Référence au hook LinkedIn (20-30 mots)
   → Mentionne le sujet PRÉCIS du post/événement/certification
   → Cite des éléments SPÉCIFIQUES (noms, chiffres, contexte)
   → INTERDICTION de citer des phrases complètes du hook
   → Paraphrase intelligemment en conservant les détails clés

4. Transition vers le pain point SPÉCIFIQUE (25-35 mots)
   → "Cela résonne avec votre recherche de {context_name}."
   → Mentionne des compétences EXACTES de la fiche (ex: réassurance, consolidation IFRS, etc.)
   → JAMAIS de généralités ("rigueur", "agilité", "dynamisme")

5. Question finale OBLIGATOIRE (TOUJOURS LA MÊME) :
   "Quels sont les principaux écarts que vous observez entre vos attentes et les profils rencontrés ?"

6. "Bien à vous,"

═══════════════════════════════════════════════════════════════════
INTERDICTIONS ABSOLUES
═══════════════════════════════════════════════════════════════════

❌ JAMAIS écrire "Je travaille sur..." ou "Je travaille actuellement..."
❌ JAMAIS inventer des compétences/outils non mentionnés dans la fiche
❌ JAMAIS utiliser de termes génériques ("rigueur", "agilité", "dynamique", "croissance")
❌ Jamais citer verbatim plus de 5 mots du hook
❌ Jamais mentionner le cabinet ou "nos services"
❌ Jamais de superlatifs ou ton commercial
❌ Jamais modifier la question finale (elle est TOUJOURS identique)
❌ Jamais ajouter de signature au-delà de "Bien à vous,"

Génère l'icebreaker maintenant :"""


def build_prompt_case_b(first_name, context_name, hook_text, job_posting_data, pain_point):
    """Prompt pour CAS B : Hook faible + Focus annonce"""
    
    job_title = job_posting_data.get('title', 'N/A') if job_posting_data else 'N/A'
    job_desc = job_posting_data.get('description', 'N/A') if job_posting_data else 'N/A'
    
    # Extraire les compétences rares si disponibles
    competences_str = ""
    if pain_point.get('competences_rares'):
        competences_str = f"\nCOMPÉTENCES RARES EXTRAITES : {', '.join(pain_point['competences_rares'])}"
    
    return f"""Tu es expert en prospection B2B pour cabinet de recrutement Finance.

CONTEXTE :
Prénom : {first_name}
Poste recherché : {context_name}

HOOK LINKEDIN DISPONIBLE (Score faible - Peu aligné) :
{hook_text[:300]}

FICHE DE POSTE (élément principal) :
Titre : {job_title}
Description : {str(job_desc)[:600]}

PAIN POINT IDENTIFIÉ :
Court : {pain_point['short']}
Contexte : {pain_point['context']}{competences_str}

═══════════════════════════════════════════════════════════════════
STRATÉGIE : Le hook est peu pertinent, donc structure ainsi
═══════════════════════════════════════════════════════════════════

1. "Bonjour {first_name},"
2. SAUT DE LIGNE
3. Phrase d'introduction (UTILISE UNE DE CES FORMULATIONS EXACTES) :
   - "Je vous contacte concernant votre recherche de {context_name}."
   - "J'ai consulté votre annonce pour le poste de {context_name}."
4. Référence BRÈVE au hook (10-15 mots max)
5. Pain point SPÉCIFIQUE avec vocabulaire EXACT de la fiche (25-30 mots)
6. Question finale OBLIGATOIRE : "Quels sont les principaux écarts que vous observez entre vos attentes et les profils rencontrés ?"
7. "Bien à vous,"

Total : 70-90 mots

═══════════════════════════════════════════════════════════════════
INTERDICTIONS ABSOLUES
═══════════════════════════════════════════════════════════════════
❌ JAMAIS écrire "Je travaille sur..." ou "Je travaille actuellement..."
❌ JAMAIS utiliser de termes génériques ("rigueur", "agilité", "dynamique", "croissance")
❌ JAMAIS inventer des compétences non mentionnées dans la fiche
❌ Jamais modifier la question finale
❌ Jamais ajouter de signature au-delà de "Bien à vous,"

Génère l'icebreaker maintenant :"""


def build_prompt_case_c(first_name, context_name, job_posting_data, pain_point):
    """Prompt pour CAS C : Annonce seule (pas de hook)"""
    
    job_title = job_posting_data.get('title', 'N/A') if job_posting_data else 'N/A'
    job_desc = job_posting_data.get('description', 'N/A') if job_posting_data else 'N/A'
    
    # Extraire les compétences rares si disponibles
    competences_str = ""
    if pain_point.get('competences_rares'):
        competences_str = f"\n\nCOMPÉTENCES RARES À MENTIONNER : {', '.join(pain_point['competences_rares'])}"
    
    return f"""Tu es expert en prospection B2B pour cabinet de recrutement Finance.

CONTEXTE :
Prénom : {first_name}
Poste recherché : {context_name}

FICHE DE POSTE :
Titre : {job_title}
Description : {str(job_desc)[:600]}

PAIN POINT IDENTIFIÉ :
Court : {pain_point['short']}
Contexte : {pain_point['context']}{competences_str}

═══════════════════════════════════════════════════════════════════
STRATÉGIE : Pas de hook LinkedIn disponible
═══════════════════════════════════════════════════════════════════

1. "Bonjour {first_name},"
2. SAUT DE LIGNE
3. Phrase d'introduction (UTILISE UNE DE CES FORMULATIONS EXACTES) :
   - "Je vous contacte concernant votre recherche de {context_name}."
   - "Je me permets de vous écrire au sujet de votre poste de {context_name}."
   - "J'ai consulté votre annonce pour le poste de {context_name}."
4. Pain point SPÉCIFIQUE extrait de la fiche (35-40 mots)
   → Mentionne les COMPÉTENCES RARES demandées dans la fiche
   → Utilise le VOCABULAIRE EXACT de la fiche (ex: réassurance, coassurance, provisions)
5. Question finale OBLIGATOIRE : "Quels sont les principaux écarts que vous observez entre vos attentes et les profils rencontrés ?"
6. "Bien à vous,"

Total : 70-90 mots

═══════════════════════════════════════════════════════════════════
INTERDICTIONS ABSOLUES
═══════════════════════════════════════════════════════════════════
❌ JAMAIS écrire "Je travaille sur..." ou "Je travaille actuellement..."
❌ JAMAIS écrire "Je gère un poste de..."
❌ JAMAIS inventer des compétences non mentionnées dans la fiche
❌ JAMAIS utiliser des pain points génériques ("rigueur", "agilité", "dynamique")
❌ Jamais modifier la question finale
❌ Jamais ajouter de signature au-delà de "Bien à vous,"

Génère l'icebreaker maintenant :"""


# ========================================
# FONCTIONS UTILITAIRES
# ========================================

def get_safe_firstname(prospect_data):
    """
    Trouve le prénom (détective amélioré)
    VERSION V27.4 : Gestion améliorée des champs Leonar
    """
    target_keys = [
        'first_name', 'firstname', 'first name', 
        'prénom', 'prenom', 'name',
        'user_first_name', 'user_firstname'
    ]
    
    for key, value in prospect_data.items():
        if str(key).lower().strip() in target_keys:
            if value and str(value).strip():
                return str(value).strip().capitalize()
    
    # Dernier recours : essayer de splitter full_name
    full_name = prospect_data.get('full_name') or prospect_data.get('user_full name')
    if full_name and ' ' in str(full_name):
        parts = str(full_name).split()
        if len(parts) >= 1:
            return parts[0].capitalize()
    
    return "[Prénom]"


def get_smart_context(job_posting_data, prospect_data):
    """Définit le sujet de la discussion"""
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


def clean_signature(message):
    """
    Nettoie les signatures parasites du message
    VERSION V27.4 : Nettoyage agressif
    """
    if not message:
        return ""
    
    # Supprimer tout ce qui suit "Bien à vous," (y compris les signatures parasites)
    patterns_to_remove = [
        r'Bien à vous,\s*\n+.*',
        r'\[Votre signature\]',
        r'\[Prénom\]\s*$',
        r'Cordialement,\s*\[.*?\]',
        r'\n{3,}'
    ]
    
    for pattern in patterns_to_remove:
        message = re.sub(pattern, 'Bien à vous,', message, flags=re.DOTALL)
    
    # S'assurer qu'on finit par "Bien à vous,"
    if not message.strip().endswith('Bien à vous,'):
        message = message.strip() + '\n\nBien à vous,'
    
    return message.strip()


def generate_fallback_icebreaker(first_name, context_name, is_hiring):
    """
    Génère un icebreaker de secours
    VERSION V27.4 : Question finale correcte
    """
    if is_hiring:
        return f"""Bonjour {first_name},

J'ai consulté votre annonce pour le poste de {context_name}.

Le marché actuel rend ce type de recrutement particulièrement complexe : trouver des profils qui combinent expertise technique et capacités relationnelles devient rare.

Quels sont les principaux écarts que vous observez entre vos attentes et les profils rencontrés ?

Bien à vous,"""
    else:
        return f"""Bonjour {first_name},

J'accompagne des entreprises comme la vôtre dans la structuration de {context_name}.

Le défi principal que nous observons est de trouver des profils qui allient expertise technique et vision stratégique.

Quels sont les principaux écarts que vous observez entre vos attentes et les profils rencontrés ?

Bien à vous,"""
