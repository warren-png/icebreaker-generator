"""
═══════════════════════════════════════════════════════════════════
ICEBREAKER GENERATOR V4.0 - OPTIMISÉ POUR QUALITÉ MAXIMALE
Modifications V4.0 :
- Prompts renforcés pour hooks ultra-précis
- Meilleure extraction des citations exactes
- Scoring amélioré avec bonus événements majeurs
- Question finale TOUJOURS identique
- Suppression totale des signatures parasites
═══════════════════════════════════════════════════════════════════
"""

import anthropic
import os
import re
from config import COMPANY_INFO, PAIN_POINTS_DETAILED

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
    VERSION V4.0 : Citations exactes OBLIGATOIRES, pas de généralisation
    """
    try:
        log_event('extract_hooks_start', {'full_name': full_name})
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        context = f"""
PROFIL : {full_name} - {company_name}

POSTS LINKEDIN :
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

EXEMPLES DE BONS VS MAUVAIS HOOKS :

❌ MAUVAIS (trop vague) :
"Votre récente initiative autour du Centre d'Excellence Data & IA"

✅ BON (spécifique) :
"Votre organisation du premier Data & AI Day chez LCL avec plus de 130 collaborateurs au 19 LCL à Paris"

❌ MAUVAIS (générique) :
"Votre réflexion sur l'IA en banque"

✅ BON (citation exacte) :
"Votre participation au podcast Inside Banking avec Richard Michaud sur l'adoption de l'IA et le déploiement d'Aria"

❌ MAUVAIS (invention) :
"Votre intervention à la conférence sur la transformation digitale"

✅ BON (si non mentionné) :
Ne pas inclure ce hook

═══════════════════════════════════════════════════════════════════

Format de retour (JSON uniquement, sans texte avant/après) :
[
  {{"text": "Votre participation au podcast Inside Banking avec Richard Michaud sur l'adoption de l'IA et le déploiement d'Aria", "type": "post", "date": "2025-01"}},
  {{"text": "Votre organisation du premier Data & AI Day chez LCL avec plus de 130 collaborateurs", "type": "post", "date": "2024-11"}},
  {{"text": "Votre intervention lors de l'événement Memo Bank dédié aux femmes, aux côtés des dirigeantes de l'AMF et de la DFCG", "type": "post", "date": "2025-01"}}
]

Si aucun hook pertinent n'est trouvé, retourne : []
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
                'cleaned_json': json_str[:500] if 'json_str' in locals() else 'N/A',
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
        date = post.get('date', 'N/A')
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
                    'date': post.get('date', '')
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
                        'date': post.get('date', '')
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
    VERSION V4.0 : Bonus massifs pour événements majeurs
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
        'tagetik', 'epm', 'anaplan', 'hyperion', 'oracle planning', 'sap bpc', 'onestream',
        'sap', 's/4hana', 's4hana', 'oracle', 'sage', 'sage x3', 'dynamics',
        'ifrs', 'consolidation', 'statutory reporting', 'gaap', 'sox',
        'power bi', 'powerbi', 'tableau', 'qlik', 'data science', 'python', 'sql', 'r',
        'agile', 'scrum', 'kanban', 'safe', 'prince2', 'pmp',
        'ia', 'ai', 'intelligence artificielle', 'machine learning', 'copilot', 'chatgpt',
        'adoption ia', 'acculturation ia', 'acculturation', 'adoption',
        'data & ai day', 'ai day', 'centre d\'excellence', 'centre excellence',
        'trésorerie', 'cash management', 'fiscalité', 'tax', 'fp&a', 'fpa',
        'bancaire', 'bank', 'banque', 'fintech', 'audiovisuel', 'cinéma', 'production',
        'alm', 'actif-passif', 'liquidité', 'refinancement'
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
    # BONUS ÉVÉNEMENTS MAJEURS (V4.0)
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
    cert_keywords = ['certifié', 'certification', 'safe', 'pmp', 'aws', 'diplôme', 'formation certifiante']
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
    
    # 7. BONUS RÉCENCE (+0.5)
    hook_date = hook.get('date', '')
    if 'j' in hook_date or 'day' in hook_date.lower() or '1 semaine' in hook_date.lower():
        score += 0.5
        matching_keywords.append("recent_bonus_+0.5")
    
    # 8. BONUS VISION/RÉFLEXION (+0.3)
    vision_keywords = ['vrai défi', 'défi', 'clé', 'essentiel', 'permet de', 'conviction']
    if any(kw in combined_text for kw in vision_keywords):
        score += 0.3
        matching_keywords.append("vision_bonus_+0.3")
    
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
# DÉTECTION DU MÉTIER
# ========================================

def detect_job_category(prospect_data, job_posting_data):
    """Détecte automatiquement la catégorie métier du prospect"""
    
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


def get_relevant_pain_point(job_category, job_posting_data):
    """
    Sélectionne LE pain point le plus pertinent selon le métier et la fiche de poste
    Retourne un dict avec 'short' et 'context'
    """
    if job_category not in PAIN_POINTS_DETAILED:
        return {
            'short': "recrutement complexe sur ce type de poste",
            'context': "Difficulté à trouver des profils qui combinent expertise technique et vision business."
        }
    
    pain_points = PAIN_POINTS_DETAILED[job_category]
    
    # Si pas de fiche de poste, prendre le premier pain point
    if not job_posting_data:
        first_key = list(pain_points.keys())[0]
        return pain_points[first_key]
    
    # Sinon, chercher le pain point le plus pertinent selon la fiche
    job_text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}".lower()
    
    # Mots-clés pour chaque type de pain point
    pain_point_keywords = {
        'visibility': ['reporting', 'pilotage', 'indicateurs', 'kpi', 'tableau de bord'],
        'production_focus': ['clôture', 'production', 'charge', 'opérationnel'],
        'transformation': ['erp', 'epm', 'bi', 'transformation', 'projet', 'digitalisation'],
        'key_man_risk': ['clé', 'senior', 'expertise', 'dépendance'],
        'data_quality': ['données', 'data', 'qualité', 'fiabilité'],
        'hybrid_profiles': ['hybride', 'technique', 'business', 'polyvalence'],
        'excel_dependency': ['excel', 'tableur', 'manuel', 'automatisation'],
        'adoption': ['adoption', 'change', 'utilisateurs', 'formation'],
        'manual_processes': ['manuel', 'automatisation', 'process'],
        'acculturation': ['acculturation', 'formation', 'accompagnement', 'pédagogie']
    }
    
    # Scorer chaque pain point
    best_score = 0
    best_pain_point = None
    
    for key, pain_point in pain_points.items():
        score = 0
        # Chercher les mots-clés dans la fiche
        for keyword_type, keywords in pain_point_keywords.items():
            if keyword_type in key or any(kw in key for kw in keywords):
                for kw in keywords:
                    if kw in job_text:
                        score += 1
        
        if score > best_score:
            best_score = score
            best_pain_point = pain_point
    
    # Si aucun match, prendre le premier
    if not best_pain_point:
        first_key = list(pain_points.keys())[0]
        best_pain_point = pain_points[first_key]
    
    return best_pain_point


# ========================================
# GÉNÉRATEUR D'ICEBREAKER (MESSAGE 1)
# ========================================

def generate_icebreaker(prospect_data, hooks_data, job_posting_data):
    """
    Génère l'icebreaker (Message 1) en sélectionnant le meilleur hook
    VERSION V4.1 : Filtrage hooks <3 mois AVANT sélection
    """
    log_event('generate_icebreaker_start', {
        'prospect': prospect_data.get('_id', 'unknown'),
        'has_job_posting': bool(job_posting_data),
        'hooks_type': type(hooks_data).__name__
    })
    
    # NOUVEAU V4.1 : Filtrer hooks <3 mois
    from message_sequence_generator import filter_recent_posts
    
    if hooks_data != "NOT_FOUND" and isinstance(hooks_data, list):
        filtered_posts = filter_recent_posts(hooks_data, max_age_months=3, max_posts=5)
        if filtered_posts:
            hooks_data = filtered_posts
        else:
            hooks_data = "NOT_FOUND"
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    first_name = get_safe_firstname(prospect_data)
    context_name, is_hiring = get_smart_context(job_posting_data, prospect_data)
    job_category = detect_job_category(prospect_data, job_posting_data)
    pain_point = get_relevant_pain_point(job_category, job_posting_data)
    
    hooks_list = extract_hooks_from_linkedin(hooks_data)
    best_hook, hook_score, hook_keywords = select_best_hook(hooks_list, job_posting_data)
    
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

FICHE DE POSTE (pour identifier le pain point précis) :
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

4. Transition naturelle vers le pain point (25-35 mots)
   → "Cela résonne avec votre recherche de {context_name}."
   → Formule le pain point de manière spécifique au contexte
   → Utilise les compétences RARES de la fiche de poste

5. Question finale OBLIGATOIRE (TOUJOURS LA MÊME) :
   "Quels sont les principaux écarts que vous observez entre vos attentes et les profils rencontrés ?"

6. "Bien à vous,"

═══════════════════════════════════════════════════════════════════
EXEMPLES DE BONS MESSAGES
═══════════════════════════════════════════════════════════════════

EXEMPLE 1 (Data & IA Officer) :

Bonjour Guillaume,

Votre intervention dans Inside Banking sur le déploiement d'Aria est particulièrement éclairante. Atteindre un taux d'adoption de près de 2/3 chez les conseillers LCL montre que l'IA est perçue comme un véritable outil d'expertise opérationnelle, et non comme une simple initiative technologique.

Cela résonne directement avec votre recherche de Data & IA Officer. Au-delà des compétences techniques, l'enjeu me semble surtout d'identifier des profils capables de transformer une roadmap IA en impacts concrets pour les équipes terrain et les métiers.

Sur ce type de poste très transverse, quels sont aujourd'hui les écarts les plus fréquents que vous constatez entre vos attentes et les profils rencontrés en entretien ?

Bien à vous,

EXEMPLE 2 (Comptable Fintech) :

Bonjour Candice,

J'ai vu votre intervention lors de la deuxième édition de l'événement Memo Bank dédié aux femmes, aux côtés des dirigeantes de l'AMF et de la DFCG.

Cela résonne avec votre recherche de Comptable. En banque tech, le défi va au-delà de la comptabilité bancaire pure : il faut automatiser les process tout en participant aux projets transverses nouveaux produits.

Quels sont les principaux écarts que vous observez entre vos attentes et les profils rencontrés ?

Bien à vous,

═══════════════════════════════════════════════════════════════════
INTERDICTIONS ABSOLUES
═══════════════════════════════════════════════════════════════════

❌ Jamais citer verbatim plus de 5 mots du hook
❌ Jamais inventer des informations non présentes dans le hook
❌ Jamais mentionner le cabinet ou "nos services"
❌ Jamais de superlatifs ou ton commercial
❌ Jamais modifier la question finale (elle est TOUJOURS identique)
❌ Jamais ajouter de signature au-delà de "Bien à vous,"

Génère l'icebreaker maintenant :"""


def build_prompt_case_b(first_name, context_name, hook_text, job_posting_data, pain_point):
    """Prompt pour CAS B : Hook faible + Focus annonce"""
    
    job_title = job_posting_data.get('title', 'N/A') if job_posting_data else 'N/A'
    job_desc = job_posting_data.get('description', 'N/A') if job_posting_data else 'N/A'
    
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
Contexte : {pain_point['context']}

═══════════════════════════════════════════════════════════════════
STRATÉGIE : Le hook est peu pertinent, donc structure ainsi
═══════════════════════════════════════════════════════════════════

1. "Bonjour {first_name},"
2. SAUT DE LIGNE
3. Référence BRÈVE au hook (10-15 mots max)
4. Pivot RAPIDE vers le poste et pain point (35-40 mots)
5. Question finale OBLIGATOIRE : "Quels sont les principaux écarts que vous observez entre vos attentes et les profils rencontrés ?"
6. "Bien à vous,"

Total : 70-90 mots

INTERDICTIONS :
❌ Jamais modifier la question finale
❌ Jamais ajouter de signature au-delà de "Bien à vous,"

Génère l'icebreaker maintenant :"""


def build_prompt_case_c(first_name, context_name, job_posting_data, pain_point):
    """Prompt pour CAS C : Annonce seule (pas de hook)"""
    
    job_title = job_posting_data.get('title', 'N/A') if job_posting_data else 'N/A'
    job_desc = job_posting_data.get('description', 'N/A') if job_posting_data else 'N/A'
    
    return f"""Tu es expert en prospection B2B pour cabinet de recrutement Finance.

CONTEXTE :
Prénom : {first_name}
Poste recherché : {context_name}

FICHE DE POSTE :
Titre : {job_title}
Description : {str(job_desc)[:600]}

PAIN POINT IDENTIFIÉ :
Court : {pain_point['short']}
Contexte : {pain_point['context']}

═══════════════════════════════════════════════════════════════════
STRATÉGIE : Pas de hook LinkedIn disponible
═══════════════════════════════════════════════════════════════════

1. "Bonjour {first_name},"
2. SAUT DE LIGNE
3. Introduction directe sur l'annonce (15-20 mots)
4. Pain point précis du poste (35-40 mots)
5. Question finale OBLIGATOIRE : "Quels sont les principaux écarts que vous observez entre vos attentes et les profils rencontrés ?"
6. "Bien à vous,"

Total : 70-90 mots

INTERDICTIONS :
❌ Jamais modifier la question finale
❌ Jamais ajouter de signature au-delà de "Bien à vous,"

Génère l'icebreaker maintenant :"""


# ========================================
# FONCTIONS UTILITAIRES
# ========================================

def get_safe_firstname(prospect_data):
    """
    Trouve le prénom (détective amélioré)
    VERSION V4.0 : Gestion améliorée des champs Leonar
    """
    # Essayer différents champs possibles
    target_keys = [
        'first_name', 'firstname', 'first name', 
        'prénom', 'prenom', 'name',
        'user_first_name', 'user_firstname'  # Champs Leonar
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
    VERSION V4.0 : Nettoyage agressif
    """
    if not message:
        return ""
    
    # Supprimer tout ce qui suit "Bien à vous," (y compris les signatures parasites)
    patterns_to_remove = [
        r'Bien à vous,\s*\n+.*',  # Tout après "Bien à vous,"
        r'\[Votre signature\]',
        r'\[Prénom\]\s*$',
        r'Cordialement,\s*\[.*?\]',
        r'\n{3,}'  # Trop de lignes vides
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
    VERSION V4.0 : Question finale correcte
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
