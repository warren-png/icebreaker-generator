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
    prompt = f"""Tu es un expert en copywriting B2B pour cabinet de recrutement Finance.

CONTEXTE :
Prospect : {prospect_data['first_name']} {prospect_data.get('last_name', '')}
Entreprise : {prospect_data.get('company', '')}
Poste : {prospect_data.get('title', 'N/A')}

Hook Prospect (LinkedIn/Web) : {json.dumps(hooks_data, ensure_ascii=False)}
Annonce de recrutement : {job_context}

IMPÉRATIF ABSOLU DE LONGUEUR : 80-100 MOTS MAXIMUM (compter chaque mot !)

FORMAT STRICT NON NÉGOCIABLE :
1. "Bonjour {prospect_data['first_name']},"
2. SAUT DE LIGNE (ligne vide)
3. Corps du message (60-80 mots)
4. Question finale (10-15 mots)

STRATÉGIE CONTENU (FUSION INTELLIGENTE) :

═══════════════════════════════════════════════════════════════════
CAS A : Hook (podcast/article) + Annonce (LE MEILLEUR)
═══════════════════════════════════════════════════════════════════

Structure OBLIGATOIRE :
- Phrase 1 (15-20 mots) : "J'ai [écouté/lu/consulté] [type contenu précis avec nom]"
  → IMPÉRATIF : Mentionner le NOM du podcast/article/conférence !
  
- Phrase 2 (15-20 mots) : "Votre analyse sur [sujet précis extrait hook] était [qualificatif sobre]."
  → Citer UNE idée spécifique du hook
  
- Phrase 3 (20-25 mots) : "Cela résonne avec votre recherche de [titre poste]. Le défi est [pain point marché]."
  → Lier hook + annonce + observation marché
  
- Phrase 4 (15-20 mots) : "Quels sont les principaux écarts que vous observez entre vos attentes et les profils rencontrés ?"

EXEMPLE TYPE :
"Bonjour Marie,

J'ai écouté votre intervention dans le podcast CFO 4.0 sur la digitalisation finance. Votre analyse sur la nécessité d'acculturer les équipes métiers était très juste.

Cela résonne avec votre recherche de Directeur Contrôle de Gestion. Le défi n'est plus seulement de trouver des experts techniques, mais ces profils hybrides capables d'embarquer les opérationnels.

Quels sont les principaux écarts que vous observez entre vos attentes et les profils rencontrés ?

Bien à vous,"

═══════════════════════════════════════════════════════════════════
CAS B : Annonce seule (PAS DE HOOK détecté)
═══════════════════════════════════════════════════════════════════

Structure OBLIGATOIRE :
- Phrase 1 (15-20 mots) : "J'ai consulté votre recherche de [titre poste exact]."
  OU "Je me permets de vous contacter concernant votre recherche de [titre]."
  
- Phrase 2-3 (40-50 mots) : Observation marché spécifique au métier
  → Mentionner un pain point CONTEXTUEL (pas générique)
  → Ex EPM : "profils qui parlent Tech ET Business sur Tagetik"
  → Ex Consolidation : "profils sachant piloter clôture ET former les filiales"
  
- Phrase 4 (15-20 mots) : "Quels sont les principaux écarts que vous observez entre vos attentes et les profils rencontrés ?"

EXEMPLE TYPE :
"Bonjour Clémentine,

J'ai consulté votre recherche de Senior Functional Analyst pour votre EPM CoE chez Pernod Ricard.

Sur ce type de poste, je constate que le défi n'est pas la maîtrise technique de Tagetik seule, mais la capacité à faire le pont entre les équipes IT et les utilisateurs finance tout en animant l'adoption des outils.

Quels sont les principaux écarts que vous observez entre vos attentes et les profils rencontrés ?

Bien à vous,"

═══════════════════════════════════════════════════════════════════
CAS C : Hook seul (PAS D'ANNONCE - Approche spontanée)
═══════════════════════════════════════════════════════════════════

Structure OBLIGATOIRE :
- Phrase 1 (15-20 mots) : Référence précise au hook
- Phrase 2-3 (40-50 mots) : Lien avec enjeux département du prospect
- Phrase 4 (15-20 mots) : Question ouverte sur les défis actuels

EXEMPLE TYPE :
"Bonjour Thomas,

Votre post récent sur LinkedIn concernant la transformation de vos process de consolidation était très instructif.

Dans le pilotage de vos équipes Finance, vous devez certainement constater cette tension entre expertise technique pointue (IFRS, consolidation) et vision business globale. Trouver des profils qui combinent les deux devient un véritable défi.

Est-ce aujourd'hui une difficulté que vous rencontrez sur vos recrutements ou dans la structuration de vos équipes ?

Bien à vous,"

═══════════════════════════════════════════════════════════════════
INTERDICTIONS ABSOLUES :
═══════════════════════════════════════════════════════════════════
- ❌ Jamais "Notre cabinet", "Nos services", "Notre expertise"
- ❌ Jamais de superlatifs ("excellents", "meilleurs", "top")
- ❌ Jamais de jargon cabinet ("chasse de têtes", "approche directe")
- ❌ Jamais plus de 100 mots au total
- ❌ Jamais de formules creuses ("soulève un point clé", "retenu mon attention")

VALIDATION AVANT ENVOI :
1. Compter les mots → Si > 100 mots : RECOMMENCER
2. Vérifier référence explicite au hook (si CAS A) → Si manque : RECOMMENCER
3. Vérifier question finale présente → Si manque : AJOUTER

Génère le Message 1 selon ces règles STRICTES.
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