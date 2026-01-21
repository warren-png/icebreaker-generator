"""
═══════════════════════════════════════════════════════════════════
ICEBREAKER GENERATOR V2 (MODULE COMPLET)
Version : V17 (Scraping + IA V16 Adoucie)
Utilisé par : app_streamlit.py
═══════════════════════════════════════════════════════════════════
"""

import anthropic
import json
import os
import requests
from apify_client import ApifyClient
from config import * # Importe APIFY_TOKEN, SERPER_API_KEY, etc.
from scraper_job_posting import format_job_data_for_prompt

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("❌ ANTHROPIC_API_KEY non trouvée")


# ========================================
# PARTIE 1 : FONCTIONS DE SCRAPING (INDISPENSABLES)
# ========================================

def init_apify_client():
    """Initialise le client Apify"""
    return ApifyClient(APIFY_API_TOKEN)


def scrape_linkedin_profile(apify_client, linkedin_url):
    """Scrape le profil LinkedIn complet"""
    print(f"🕷️  Scraping du profil LinkedIn...")
    try:
        run_input = {
            "profileUrls": [linkedin_url],
            "searchForEmail": False
        }
        run = apify_client.actor(APIFY_ACTORS["profile"]).call(run_input=run_input)
        items = []
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            items.append(item)
        return items[0] if items else None
    except Exception as e:
        print(f"❌ Erreur scraping profil : {e}")
        return None


def scrape_linkedin_posts(apify_client, linkedin_url, limit=5):
    """Scrape les posts LinkedIn du profil"""
    print(f"📝 Scraping de {limit} posts LinkedIn...")
    try:
        run_input = {
            "urls": [linkedin_url],
            "limit": limit
        }
        run = apify_client.actor(APIFY_ACTORS["profile_posts"]).call(run_input=run_input)
        posts = []
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            posts.append({
                "text": item.get("text", ""),
                "date": item.get("date", ""),
                "likes": item.get("numReactions", 0)
            })
            if len(posts) >= limit: break
        return posts
    except Exception as e:
        return []


def scrape_company_posts(apify_client, company_name, limit=5):
    """Scrape les posts de l'entreprise"""
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
    """Scrape le profil entreprise"""
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
    """Recherche web sur le prospect"""
    if not WEB_SEARCH_ENABLED: return []
    try:
        query = f'"{first_name} {last_name}" "{company}"'
        if title: query += f' "{title}"'
        query += ' after:2023'
        
        url = "https://google.serper.dev/search"
        headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
        payload = {'q': query, 'num': MAX_SEARCH_RESULTS}
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            results = response.json()
            filtered = []
            for item in results.get('organic', [])[:MAX_SEARCH_RESULTS]:
                filtered.append({
                    'title': item.get('title', ''),
                    'snippet': item.get('snippet', ''),
                    'link': item.get('link', '')
                })
            return filtered
        return []
    except Exception:
        return []


# ========================================
# PARTIE 2 : INTELLIGENCE ARTIFICIELLE (V16 - Clean)
# ========================================

def extract_hooks_with_claude(profile_data, posts_data, company_posts, company_profile, web_results, prospect_name, company_name):
    """Extrait 1-2 hooks pertinents pour l'icebreaker (Limité à 3 mois)"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    data_summary = {
        "profile": {
            "fullName": profile_data.get("fullName", "") if profile_data else "",
            "headline": profile_data.get("headline", "") if profile_data else "",
            "summary": profile_data.get("summary", "") if profile_data else "",
            "current_position": profile_data.get("experiences", [{}])[0].get("title", "") if profile_data and profile_data.get("experiences") else "",
        },
        "recent_posts": posts_data[:5] if posts_data else [],
        "company_posts": company_posts[:3] if company_posts else [],
        "web_mentions": web_results
    }
    
    prompt = f"""Tu es un analyste en intelligence économique.
OBJECTIF : Trouver un prétexte (Hook) de moins de 3 mois pour engager une conversation B2B.

DONNÉES :
{json.dumps(data_summary, indent=2, ensure_ascii=False)}

RÈGLES :
1. Cherche en priorité un contenu CRÉÉ par le prospect (Post, Article).
2. Sinon, une interaction (Like/Commentaire).
3. Sinon, une actu entreprise majeure.
4. DATE LIMITE : Tout ce qui a > 3 mois est IGNORÉ.

SORTIE JSON UNIQUEMENT :
{{
  "hook_principal": {{
    "description": "Description concise",
    "type_action": "CREATOR" | "INTERACTOR" | "COMPANY",
    "date": "Date approx",
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
        response_text = message.content[0].text.strip()
        response_text = response_text.replace('```json', '').replace('```', '').strip()
        return response_text
    except Exception:
        return "NOT_FOUND"


def generate_advanced_icebreaker(prospect_data, hooks_json, job_posting_data=None):
    """Génère un icebreaker (Message 1) avec le ton adouci et le bon formatage."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Gestion des hooks
    try:
        if hooks_json and hooks_json != "NOT_FOUND":
            hooks_data = json.loads(hooks_json)
        else:
            hooks_data = {"status": "NOT_FOUND"}
    except:
        hooks_data = {"status": "NOT_FOUND"}
    
    # Contexte Annonce
    job_context = ""
    if job_posting_data:
        job_context = format_job_data_for_prompt(job_posting_data)
    
    prompt = f"""Tu es un expert en copywriting B2B pour le recrutement.
Ta mission : Rédiger le MESSAGE 1 (Icebreaker) d'une séquence d'approche directe.

CONTEXTE :
Prospect : {prospect_data['first_name']} ({prospect_data['company']})
Poste Visé (Annonce) : {job_posting_data.get('title', 'N/A') if job_posting_data else 'N/A'}
Hooks : {json.dumps(hooks_data, ensure_ascii=False)}

RÈGLES DE FORMATAGE (IMPÉRATIVES) :
1. Commence par "Bonjour {prospect_data['first_name']},"
2. SAUTE DEUX LIGNES (Laisse une ligne vide après le bonjour).
3. Commence la phrase suivante par une MAJUSCULE.
4. PAS de signature (gérée par le CRM).

TON & STYLE (MODIFIÉ - IMPORTANT) :
- Ne sois JAMAIS négatif ou critique ("lacunes", "rigide" = INTERDIT).
- Utilise la rhétorique de la "POLARISATION" pour décrire le marché.
  -> Au lieu de dire "les candidats sont mauvais", dis : "On observe souvent une polarisation : d'un côté des experts pointus, de l'autre des profils opérationnels. L'équilibre est rare."
- Sois valorisant pour le prospect.

STRUCTURE DU MESSAGE :
1. Salutation + [Hook Perso OU Mention de l'annonce].
2. L'Insight Marché (La Polarisation) :
   "Trouver un profil alliant [Compétence A] et [Compétence B] est un vrai défi. On observe souvent une polarisation sur le marché : d'un côté des experts très pointus sur [A], de l'autre des profils focalisés sur [B]. L'équilibre parfait est rare."
3. La Question d'Arbitrage :
   "Comment arbitrez-vous aujourd'hui entre privilégier [A] ou favoriser [B] ?"

Génère le Message 1.
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