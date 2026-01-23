"""
═══════════════════════════════════════════════════════════════════
ICEBREAKER GENERATOR V3 - SCORING INTELLIGENT DES HOOKS
Modifications V3 :
- Système de scoring 1-5 basé sur l'alignement hook/poste
- Sélection du hook le PLUS pertinent (pas juste le premier valide)
- Logs détaillés pour transparence
- COMPLET avec fonctions Apify pour app_streamlit.py
═══════════════════════════════════════════════════════════════════
"""

import anthropic
import os
import re
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
    """
    Initialise le client Apify
    """
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
    """
    Scrape un profil LinkedIn via Apify
    """
    try:
        log_event('scrape_linkedin_profile_start', {'url': linkedin_url})
        
        # Lancer l'actor Apify pour scraper le profil
        # Utilise dev_fusion/Linkedin-Profile-Scraper (No Cookies)
        run_input = {
            "startUrls": [linkedin_url],
            "proxyConfiguration": {"useApifyProxy": True}
        }
        
        run = apify_client.actor("dev_fusion/Linkedin-Profile-Scraper").call(run_input=run_input)
        
        # Récupérer les résultats
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
    """
    Scrape les posts LinkedIn d'un profil via Apify
    """
    try:
        log_event('scrape_linkedin_posts_start', {'url': linkedin_url})
        
        # Utilise supreme_coder/linkedin-post
        run_input = {
            "startUrls": [linkedin_url],
            "resultsLimit": 10,
            "proxyConfiguration": {"useApifyProxy": True}
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
    """
    try:
        log_event('extract_hooks_start', {'full_name': full_name})
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Préparer le contexte pour Claude
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

Retourne UNIQUEMENT une liste JSON des hooks :
[
  {{"text": "hook 1", "type": "post", "date": "2024-01"}},
  {{"text": "hook 2", "type": "certification", "date": "2024-02"}}
]
"""
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        tracker.track(message.usage, 'extract_hooks_with_claude')
        
        result = message.content[0].text.strip()
        
        # Parser le JSON retourné
        import json
        try:
            hooks = json.loads(result)
            log_event('extract_hooks_success', {'hooks_count': len(hooks)})
            return hooks
        except json.JSONDecodeError:
            log_event('extract_hooks_json_error', {'raw_result': result})
            return "NOT_FOUND"
        
    except Exception as e:
        log_error('extract_hooks_error', str(e), {'full_name': full_name})
        return "NOT_FOUND"


def format_posts_for_extraction(posts_data):
    """Formate les posts pour l'extraction de hooks"""
    if not posts_data:
        return "Aucun post disponible"
    
    formatted = []
    for i, post in enumerate(posts_data[:5]):  # Prendre les 5 derniers posts
        text = post.get('text', '')
        date = post.get('date', 'N/A')
        formatted.append(f"Post {i+1} ({date}):\n{text[:300]}")
    
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
    """
    Wrapper pour appeler generate_icebreaker (pour compatibilité avec app_streamlit.py)
    """
    return generate_icebreaker(prospect_data, hooks_data, job_posting_data)


# ========================================
# EXTRACTION ET VALIDATION DES HOOKS
# ========================================

def extract_hooks_from_linkedin(hooks_data):
    """
    Extrait les hooks valides depuis les données LinkedIn scrapées
    Retourne une liste de hooks avec métadonnées
    """
    if not hooks_data or hooks_data == "NOT_FOUND":
        log_event('no_hooks_available', {})
        return []
    
    hooks_list = []
    
    # Cas 1 : hooks_data est déjà une liste de posts
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
    
    # Cas 2 : hooks_data est un dict avec une clé 'posts' ou 'content'
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
    
    # Cas 3 : hooks_data est un string (ancien format)
    elif isinstance(hooks_data, str) and len(hooks_data) > 50:
        hooks_list.append({
            'text': hooks_data.strip(),
            'type': 'legacy',
            'index': 0,
            'title': '',
            'date': ''
        })
    
    # Filtrer les hooks trop courts (< 30 caractères)
    valid_hooks = [h for h in hooks_list if len(h['text']) >= 30]
    
    log_event('hooks_extracted', {
        'total_found': len(hooks_list),
        'valid_hooks': len(valid_hooks)
    })
    
    return valid_hooks


def score_hook_relevance(hook, job_posting_data):
    """
    Score un hook de 1 à 5 selon sa pertinence avec le poste
    
    SCORING :
    5 = Mentionne compétences clés + secteur + contexte technique
    4 = Mentionne compétences clés + contexte professionnel
    3 = Mentionne le secteur ou des compétences générales
    2 = Lien faible mais professionnel
    1 = Générique ou peu pertinent
    """
    if not job_posting_data:
        return 2  # Score par défaut si pas de fiche
    
    hook_text = hook['text'].lower()
    hook_title = hook.get('title', '').lower()
    combined_text = f"{hook_text} {hook_title}"
    
    job_title = str(job_posting_data.get('title', '')).lower()
    job_desc = str(job_posting_data.get('description', '')).lower()
    job_full = f"{job_title} {job_desc}"
    
    score = 0
    matching_keywords = []
    
    # ========================================
    # NIVEAU 1 : COMPÉTENCES TECHNIQUES PRÉCISES (+3 points)
    # ========================================
    technical_keywords = [
        # Outils EPM/Planning
        'tagetik', 'epm', 'anaplan', 'hyperion', 'oracle planning', 'sap bpc', 'onestream',
        # ERP
        'sap', 's/4hana', 's4hana', 'oracle', 'sage', 'sage x3', 'dynamics',
        # Consolidation/Normes
        'ifrs', 'consolidation', 'statutory reporting', 'gaap', 'sox',
        # BI/Data
        'power bi', 'powerbi', 'tableau', 'qlik', 'data science', 'python', 'sql', 'r',
        # Méthodologies
        'agile', 'scrum', 'kanban', 'safe', 'prince2', 'pmp',
        # IA/Automation
        'ia', 'ai', 'intelligence artificielle', 'machine learning', 'copilot', 'chatgpt',
        # Finance spécialisée
        'trésorerie', 'cash management', 'fiscalité', 'tax', 'fp&a', 'fpa',
        # Sectoriels spécifiques
        'bancaire', 'bank', 'fintech', 'audiovisuel', 'cinéma', 'production',
        'droits d\'auteur', 'convention collective'
    ]
    
    for kw in technical_keywords:
        if kw in job_full and kw in combined_text:
            score += 3
            matching_keywords.append(kw)
            break  # Un seul match technique suffit
    
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
        'contrôle de gestion', 'fpa', 'audit', 'consolidation'
    ]
    
    if any(kw in job_full and kw in combined_text for kw in sector_keywords):
        score += 1
        matching_keywords.append("sector match")
    
    # ========================================
    # PÉNALITÉS
    # ========================================
    
    # Pénalité si le hook est trop générique
    generic_phrases = [
        'heureux de', 'ravi de', 'fier de', 'merci', 'bravo',
        'félicitations', 'congratulations', 'honneur'
    ]
    if any(phrase in combined_text for phrase in generic_phrases) and score < 3:
        score -= 1
        matching_keywords.append("generic_penalty")
    
    # ========================================
    # CALCUL FINAL (1-5)
    # ========================================
    final_score = max(1, min(5, score))
    
    log_event('hook_scored', {
        'hook_index': hook.get('index'),
        'score': final_score,
        'matching_keywords': matching_keywords,
        'hook_preview': hook_text[:100]
    })
    
    return final_score, matching_keywords


def select_best_hook(hooks_list, job_posting_data):
    """
    Sélectionne le hook avec le meilleur score de pertinence
    Retourne le hook choisi + son score + les keywords matchés
    """
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
    
    # Trier par score décroissant
    scored_hooks.sort(key=lambda x: x['score'], reverse=True)
    
    best = scored_hooks[0]
    
    log_event('best_hook_selected', {
        'score': best['score'],
        'keywords': best['keywords'],
        'total_hooks_analyzed': len(scored_hooks),
        'all_scores': [h['score'] for h in scored_hooks]
    })
    
    # Log si on a plusieurs hooks avec le même score
    if len(scored_hooks) > 1 and scored_hooks[1]['score'] == best['score']:
        log_event('multiple_hooks_same_score', {
            'count': sum(1 for h in scored_hooks if h['score'] == best['score'])
        })
    
    return best['hook'], best['score'], best['keywords']


# ========================================
# GÉNÉRATEUR D'ICEBREAKER
# ========================================

def generate_icebreaker(prospect_data, hooks_data, job_posting_data):
    """
    Génère l'icebreaker (Message 1) en sélectionnant le meilleur hook
    """
    log_event('generate_icebreaker_start', {
        'prospect': prospect_data.get('_id', 'unknown'),
        'has_job_posting': bool(job_posting_data),
        'hooks_type': type(hooks_data).__name__
    })
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Extraction du prénom
    first_name = get_safe_firstname(prospect_data)
    
    # Contexte du poste
    context_name, is_hiring = get_smart_context(job_posting_data, prospect_data)
    
    # Extraction et sélection du meilleur hook
    hooks_list = extract_hooks_from_linkedin(hooks_data)
    best_hook, hook_score, hook_keywords = select_best_hook(hooks_list, job_posting_data)
    
    # Déterminer le type de message selon la qualité du hook
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
        'hook_keywords': hook_keywords
    })
    
    # Construction du prompt selon le cas
    if message_type == "CAS A (Hook LinkedIn + Annonce)":
        prompt = build_prompt_case_a(first_name, context_name, hook_text, hook_title, 
                                     job_posting_data, hook_keywords)
    elif message_type == "CAS B (Hook faible + Focus annonce)":
        prompt = build_prompt_case_b(first_name, context_name, hook_text, 
                                     job_posting_data)
    else:
        prompt = build_prompt_case_c(first_name, context_name, job_posting_data)
    
    # Génération via Claude API
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        
        tracker.track(message.usage, 'generate_icebreaker')
        result = message.content[0].text
        
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
                        job_posting_data, hook_keywords):
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

Mots-clés détectés (alignement hook/poste) : {', '.join(hook_keywords) if hook_keywords else 'Aucun'}

FICHE DE POSTE (pour identifier le pain point précis) :
Titre : {job_title}
Description (extraits clés) : {str(job_desc)[:600]}

MISSION :
Rédige un icebreaker de 70-90 mots structuré ainsi :

1. "Bonjour {first_name},"
2. SAUT DE LIGNE
3. Référence au hook LinkedIn (20-25 mots)
   → Mentionne le sujet précis du post/événement/certification
   → Montre que tu as vraiment lu (cite un élément spécifique)
   → INTERDICTION de citer des phrases complètes, paraphrase intelligemment

4. Transition naturelle vers le pain point (25-30 mots)
   → "Cela résonne avec votre recherche de {context_name}."
   → Identifie LE pain point précis du poste (pas générique)
   → Utilise les compétences RARES détectées dans la fiche

5. Question ouverte engageante (15-20 mots)
   → "Quels sont les principaux écarts que vous observez entre vos attentes et les profils rencontrés ?"
   OU variante pertinente selon contexte

6. "Bien à vous,"

EXEMPLES DE BONS PAIN POINTS (SPÉCIFIQUES) :

Pour EPM/Tagetik :
❌ "Le défi est la maîtrise de Tagetik"
✅ "Le défi n'est plus seulement la maîtrise de Tagetik, mais cette capacité à faire le pont entre IT et finance tout en pilotant l'adoption utilisateurs."

Pour Consolidation IFRS :
❌ "Le défi est de trouver des profils IFRS"
✅ "Au-delà de l'expertise IFRS, le défi est de trouver des profils capables de faire monter le niveau des équipes locales tout en respectant les délais groupe."

Pour Data/IA Officer :
❌ "Le défi est de maîtriser les technologies"
✅ "Le défi n'est plus seulement de maîtriser les technologies, mais de trouver ces profils capables d'accompagner les métiers dans l'idéation et l'acculturation IA."

Pour Comptabilité bancaire :
❌ "Le défi est la comptabilité bancaire"
✅ "En banque tech, le défi va au-delà de la comptabilité bancaire pure : il faut automatiser les process tout en participant aux projets transverses nouveaux produits."

INTERDICTIONS :
- ❌ Jamais citer verbatim plus de 5 mots du hook
- ❌ Jamais inventer des informations non présentes dans le hook
- ❌ Jamais mentionner le cabinet ou "nos services"
- ❌ Jamais de superlatifs ou ton commercial

Génère l'icebreaker maintenant :"""


def build_prompt_case_b(first_name, context_name, hook_text, job_posting_data):
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

STRATÉGIE :
Le hook est peu pertinent, donc structure le message ainsi :

1. "Bonjour {first_name},"
2. SAUT DE LIGNE
3. Référence BRÈVE au hook (10-15 mots max)
   → Juste pour montrer que tu as regardé le profil
   → Pas de développement

4. Pivot RAPIDE vers le poste (30-35 mots)
   → "J'ai vu votre recherche de {context_name}."
   → Identifie le pain point SPÉCIFIQUE du poste

5. Question ouverte (15-20 mots)

6. "Bien à vous,"

Total : 70-90 mots

Génère l'icebreaker maintenant :"""


def build_prompt_case_c(first_name, context_name, job_posting_data):
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

STRATÉGIE (Pas de hook LinkedIn disponible) :
Structure le message ainsi :

1. "Bonjour {first_name},"
2. SAUT DE LIGNE
3. Introduction directe (15-20 mots)
   → "J'ai consulté votre annonce pour le poste de {context_name}."

4. Pain point précis du poste (35-40 mots)
   → Identifie LE défi spécifique du recrutement
   → Utilise les compétences rares de la fiche

5. Question ouverte (15-20 mots)

6. "Bien à vous,"

Total : 70-90 mots

Génère l'icebreaker maintenant :"""


# ========================================
# FONCTIONS UTILITAIRES
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

    # Cas 2 : Pas d'annonce
    headline = str(prospect_data.get('headline', '')).lower()
    
    if 'financ' in headline or 'daf' in headline or 'cfo' in headline:
        return "vos équipes Finance", False
    elif 'rh' in headline or 'drh' in headline or 'talents' in headline:
        return "votre stratégie Talents", False
    elif 'audit' in headline:
        return "votre département Audit", False
    else:
        return "vos équipes", False


def generate_fallback_icebreaker(first_name, context_name, is_hiring):
    """Génère un icebreaker de secours"""
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

Seriez-vous ouvert à échanger sur vos enjeux actuels ?

Bien à vous,"""
    