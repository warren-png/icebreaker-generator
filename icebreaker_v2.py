"""
═══════════════════════════════════════════════════════════════════
ICEBREAKER GENERATOR V2 (MODULE V21 - FUSION INTELLIGENTE)
Logique : Hook LinkedIn/Web + Annonce = Message Fusionnel
═══════════════════════════════════════════════════════════════════
"""

import anthropic
import json
import os
import requests
from apify_client import ApifyClient
from config import *
from scraper_job_posting import format_job_data_for_prompt

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("❌ ANTHROPIC_API_KEY non trouvée")


# ========================================
# PARTIE 1 : SCRAPING COMPLET (WEB + LINKEDIN)
# ========================================

def init_apify_client():
    return ApifyClient(APIFY_API_TOKEN)

def scrape_linkedin_profile(apify_client, linkedin_url):
    print(f"🕷️  Scraping profil...")
    try:
        run_input = {"profileUrls": [linkedin_url], "searchForEmail": False}
        run = apify_client.actor(APIFY_ACTORS["profile"]).call(run_input=run_input)
        items = []
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            items.append(item)
        return items[0] if items else None
    except Exception:
        return None

def scrape_linkedin_posts(apify_client, linkedin_url, limit=5):
    print(f"📝 Scraping posts & activités ({limit})...")
    try:
        run_input = {"urls": [linkedin_url], "limit": limit}
        run = apify_client.actor(APIFY_ACTORS["profile_posts"]).call(run_input=run_input)
        posts = []
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            # On prend tout : posts originaux, commentaires, reposts
            text = item.get("text") or item.get("comment", "") or ""
            if text:
                posts.append({"text": text, "date": item.get("date", ""), "likes": item.get("numReactions", 0)})
            if len(posts) >= limit: break
        return posts
    except Exception:
        return []

def scrape_company_posts(apify_client, company_name, limit=5):
    print(f"🏢 Scraping posts entreprise...")
    try:
        company_slug = company_name.lower().replace(' ', '-')
        company_url = f"https://www.linkedin.com/company/{company_slug}"
        run_input = {"urls": [company_url], "limit": limit}
        run = apify_client.actor(APIFY_ACTORS["company_posts"]).call(run_input=run_input)
        posts = []
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            posts.append({"text": item.get("text", ""), "date": item.get("date", "")})
            if len(posts) >= limit: break
        return posts
    except Exception:
        return []

def scrape_company_profile(apify_client, company_name):
    try:
        company_slug = company_name.lower().replace(' ', '-')
        company_url = f"https://www.linkedin.com/company/{company_slug}"
        run_input = {"profileUrls": [company_url]}
        run = apify_client.actor(APIFY_ACTORS["company_profile"]).call(run_input=run_input)
        items = []
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            items.append(item)
        return items[0] if items else None
    except Exception:
        return None

def web_search_prospect(first_name, last_name, company, title=""):
    """Recherche Web : Podcasts, Articles, Livres..."""
    if not WEB_SEARCH_ENABLED: return []
    try:
        # Requête large pour capturer l'intelligence (Podcast, Article, Interview)
        query = f'"{first_name} {last_name}" "{company}" (podcast OR interview OR article OR livre OR conférence)'
        
        url = "https://google.serper.dev/search"
        headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
        payload = {'q': query, 'num': 5}
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            results = response.json()
            filtered = []
            for item in results.get('organic', [])[:5]:
                filtered.append({'title': item.get('title', ''), 'snippet': item.get('snippet', ''), 'link': item.get('link', '')})
            return filtered
        return []
    except Exception:
        return []


# ========================================
# PARTIE 2 : INTELLIGENCE & EXTRACTION
# ========================================

def extract_hooks_with_claude(profile_data, posts_data, company_posts, company_profile, web_results, prospect_name, company_name):
    """Extrait les Hooks (Podcasts, Livres, Posts...)"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    data_summary = {
        "profile": {
            "fullName": profile_data.get("fullName", "") if profile_data else "",
            "headline": profile_data.get("headline", "") if profile_data else "",
            "summary": profile_data.get("summary", "") if profile_data else "",
        },
        "recent_activity_linkedin": posts_data[:7] if posts_data else [], # On en prend un peu plus
        "web_mentions": web_results # Podcasts, articles...
    }
    
    prompt = f"""Tu es un analyste en intelligence économique.
OBJECTIF : Trouver un "Hook" (Point d'accroche) pour contacter ce prospect.

HIÉRARCHIE DES HOOKS (DU MEILLEUR AU MOINS BON) :
1. **Contenu Intellectuel** (Le Graal) : A-t-il écrit un article ? Participé à un podcast ? Écrit un livre ?
2. **Engagement LinkedIn** : A-t-il posté ou commenté récemment ?
3. **News Entreprise** : Levée de fonds, rachat...

DONNÉES :
{json.dumps(data_summary, indent=2, ensure_ascii=False)}

RÈGLES :
- Date limite : Contenus de moins de 4 mois.
- Si le prospect a un Podcast ou un Article -> C'EST LE MEILLEUR HOOK.

SORTIE JSON UNIQUEMENT :
{{
  "hook_principal": {{
    "description": "Description précise (ex: Son passage dans le podcast X)",
    "type_action": "CONTENT_CREATOR" | "LINKEDIN_ACTIVE" | "COMPANY_NEWS",
    "pertinence": 5
   }}
}}
Si rien trouvé : Réponds "NOT_FOUND".
"""
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text.strip().replace('```json', '').replace('```', '').strip()
        return response_text
    except Exception:
        return "NOT_FOUND"


# ========================================
# PARTIE 3 : GÉNÉRATION DU MESSAGE 1 (FUSION)
# ========================================

def generate_advanced_icebreaker(prospect_data, hooks_json, job_posting_data=None):
    """Génère un icebreaker FUSIONNEL (Hook Prospect + Annonce)."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # 1. Parsing des Hooks
    try:
        hooks_data = json.loads(hooks_json) if hooks_json and hooks_json != "NOT_FOUND" else {"status": "NOT_FOUND"}
    except:
        hooks_data = {"status": "NOT_FOUND"}
    
    # 2. Parsing de l'Annonce
    has_job = job_posting_data and job_posting_data.get('title') and len(str(job_posting_data.get('title'))) > 2
    job_context = str(job_posting_data) if has_job else "PAS_D_ANNONCE"
    
    # 3. Le Prompt FUSION (Logique conditionnelle stricte)
    prompt = f"""Tu es un expert en copywriting B2B (Recrutement).
Ta mission : Rédiger le MESSAGE 1 (Icebreaker).

CONTEXTE :
Prospect : {prospect_data['first_name']} ({prospect_data['company']})
Hook Prospect (Activité/Web) : {json.dumps(hooks_data, ensure_ascii=False)}
Annonce de recrutement : {job_context}

RÈGLES DE FORMATAGE :
1. "Bonjour {prospect_data['first_name']},"
2. SAUTE DEUX LIGNES.
3. Phrase suivante commence par MAJUSCULE.

STRATÉGIE DE CONTENU (LA FUSION) :

CAS A : IL Y A UN HOOK (Podcast/Post) **ET** UNE ANNONCE (Le Top)
-> TU DOIS LIER LES DEUX.
-> Structure : "J'ai lu votre post sur [Sujet Hook]... Cela fait écho à votre recherche actuelle de [Poste]..."
-> Objectif : Montrer que tu as tout lu (Profil + Annonce).

CAS B : IL Y A UNE ANNONCE MAIS PAS DE HOOK
-> Structure : "J'ai vu votre recherche de [Poste]..."
-> Focus : La difficulté du recrutement.

CAS C : IL N'Y A PAS D'ANNONCE (Approche Spontanée)
-> Utilise le Hook pour parler des enjeux du département du prospect.
-> Structure : "Votre intervention sur [Sujet Hook] soulève un point clé... Dans le pilotage de vos équipes..."

TON OBLIGATOIRE :
- Valorise la "Polarisation du marché" (Experts vs Business Partners).
- Ne sois jamais critique.

EXEMPLE TYPE (CAS A - FUSION) :
"Bonjour [Prénom],
(Saut de ligne)
Votre intervention dans le podcast 'CFO 4.0' sur la digitalisation était passionnante. Ce sujet résonne particulièrement avec votre recherche actuelle de [Poste] chez [Entreprise].
Trouver un profil capable de [Compétence] tout en [Autre Compétence] est un défi..."

Génère le Message 1 selon ces règles.
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            temperature=0.4,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()
        
    except Exception:
        return f"Bonjour {prospect_data['first_name']},\n\nErreur de génération."