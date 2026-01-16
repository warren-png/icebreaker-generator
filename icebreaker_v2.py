"""
Script d'automatisation pour générer des icebreakers personnalisés
VERSION OPTIMISÉE 10/10 - Scraping LinkedIn + Recherche Web + Annonces + Extraction Hooks Optimisée
"""

import gspread
from google.oauth2.service_account import Credentials
import anthropic
from apify_client import ApifyClient
from config import *
from scraper_job_posting import scrape_job_posting, format_job_data_for_prompt
import time
import json
import requests

# ========================================
# PARTIE 1 : CONNEXION À GOOGLE SHEETS
# ========================================

def connect_to_google_sheet():
    """Se connecte à Google Sheets"""
    print("📊 Connexion à Google Sheets...")
    
    # Scopes mis à jour
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    # Nouvelle méthode d'authentification
    credentials = Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_FILE,
        scopes=scopes
    )
    
    client = gspread.authorize(credentials)
    sheet = client.open(GOOGLE_SHEET_NAME).worksheet(WORKSHEET_NAME)
    
    print("✅ Connecté avec succès !\n")
    return sheet


def get_prospects(sheet):
    """Récupère les prospects sans icebreaker"""
    print("🔍 Recherche des prospects à traiter...")
    
    all_data = sheet.get_all_records()
    prospects_to_process = []
    
    for index, row in enumerate(all_data, start=2):
        if not row.get('icebreaker'):
            prospects_to_process.append({
                'row_number': index,
                'first_name': row.get('first_name', ''),
                'last_name': row.get('last_name', ''),
                'company': row.get('company', ''),
                'linkedin_url': row.get('linkedin_url', ''),
                'job_posting_url': row.get('job_posting_url', '')
            })
    
    print(f"📋 {len(prospects_to_process)} prospect(s) à traiter\n")
    return prospects_to_process


# ========================================
# PARTIE 2 : SCRAPING LINKEDIN AVEC APIFY
# ========================================

def init_apify_client():
    """Initialise le client Apify"""
    return ApifyClient(APIFY_API_TOKEN)


def search_linkedin_profile(first_name, last_name, company):
    """Recherche le profil LinkedIn"""
    print(f"🔎 Recherche du profil LinkedIn de {first_name} {last_name}...")
    
    linkedin_url = f"https://www.linkedin.com/in/{first_name.lower()}-{last_name.lower()}"
    
    print(f"   URL estimé : {linkedin_url}")
    return linkedin_url


def scrape_linkedin_profile(apify_client, linkedin_url):
    """Scrape le profil LinkedIn complet"""
    print(f"🕷️  Scraping du profil LinkedIn...")
    
    try:
        run_input = {
            "profileUrls": [linkedin_url],
            "searchForEmail": False
        }
        
        print(f"   Scraping profil : {linkedin_url}")
        
        run = apify_client.actor(APIFY_ACTORS["profile"]).call(run_input=run_input)
        
        items = []
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            items.append(item)
        
        if items:
            profile_data = items[0]
            print(f"   ✅ Profil récupéré : {profile_data.get('fullName', 'N/A')}")
            return profile_data
        else:
            print(f"   ⚠️ Aucune donnée trouvée")
            return None
            
    except Exception as e:
        print(f"   ❌ Erreur scraping profil : {e}")
        return None


def scrape_linkedin_posts(apify_client, linkedin_url, limit=5):
    """Scrape les posts LinkedIn du profil avec limite paramétrable"""
    print(f"📝 Scraping de {limit} posts LinkedIn...")
    
    try:
        run_input = {
            "urls": [linkedin_url],
            "limit": limit
        }
        
        print(f"   Scraping posts de : {linkedin_url}")
        
        run = apify_client.actor(APIFY_ACTORS["profile_posts"]).call(run_input=run_input)
        
        posts = []
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            posts.append({
                "text": item.get("text", ""),
                "date": item.get("date", ""),
                "likes": item.get("numReactions", 0)
            })
            
            if len(posts) >= limit:
                break
        
        print(f"   ✅ {len(posts)} post(s) récupéré(s)")
        return posts
        
    except Exception as e:
        print(f"   ⚠️ Erreur scraping posts : {e}")
        return []

def scrape_company_posts(apify_client, company_name, limit=5):
    """Scrape les posts de l'entreprise avec limite paramétrable"""
    print(f"🏢 Scraping de {limit} posts de l'entreprise...")
    
    try:
        company_slug = company_name.lower().replace(' ', '-')
        company_url = f"https://www.linkedin.com/company/{company_slug}"
        
        run_input = {
            "urls": [company_url],
            "limit": limit
        }
        
        print(f"   Scraping posts de : {company_url}")
        
        run = apify_client.actor(APIFY_ACTORS["company_posts"]).call(run_input=run_input)
        
        posts = []
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            posts.append({
                "text": item.get("text", ""),
                "date": item.get("date", "")
            })
            
            if len(posts) >= limit:
                break
        
        print(f"   ✅ {len(posts)} post(s) entreprise récupéré(s)")
        return posts
        
    except Exception as e:
        print(f"   ⚠️ Erreur scraping entreprise : {e}")
        return []

def scrape_company_profile(apify_client, company_name):
    """Scrape le profil complet de l'entreprise"""
    print(f"🏭 Scraping du profil entreprise...")
    
    try:
        company_slug = company_name.lower().replace(' ', '-')
        company_url = f"https://www.linkedin.com/company/{company_slug}"
        
        run_input = {
            "profileUrls": [company_url]
        }
        
        print(f"   Scraping profil : {company_url}")
        
        run = apify_client.actor(APIFY_ACTORS["company_profile"]).call(run_input=run_input)
        
        items = []
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            items.append(item)
        
        if items:
            company_data = items[0]
            print(f"   ✅ Profil entreprise récupéré : {company_data.get('name', 'N/A')}")
            return company_data
        else:
            print(f"   ⚠️ Aucune donnée entreprise trouvée")
            return None
            
    except Exception as e:
        print(f"   ❌ Erreur scraping entreprise : {e}")
        return None


# ========================================
# PARTIE 3 : RECHERCHE WEB AVEC SERPER
# ========================================

def web_search_prospect(first_name, last_name, company, title=""):
    """Recherche web sur le prospect avec validation anti-homonymes"""
    print(f"🌐 Recherche web sur {first_name} {last_name}...")
    
    if not WEB_SEARCH_ENABLED:
        print("   ⏭️  Recherche web désactivée")
        return []
    
    try:
        query = f'"{first_name} {last_name}" "{company}"'
        if title:
            query += f' "{title}"'
        query += ' after:2023'
        
        print(f"   Requête : {query}")
        
        url = "https://google.serper.dev/search"
        headers = {
            'X-API-KEY': SERPER_API_KEY,
            'Content-Type': 'application/json'
        }
        payload = {
            'q': query,
            'num': MAX_SEARCH_RESULTS
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            results = response.json()
            
            filtered_results = []
            for item in results.get('organic', [])[:MAX_SEARCH_RESULTS]:
                snippet = (item.get('snippet', '') + ' ' + item.get('title', '')).lower()
                if company.lower() in snippet:
                    filtered_results.append({
                        'title': item.get('title', ''),
                        'snippet': item.get('snippet', ''),
                        'link': item.get('link', ''),
                        'date': item.get('date', '')
                    })
            
            print(f"   ✅ {len(filtered_results)} résultat(s) pertinent(s) trouvé(s)")
            return filtered_results
        else:
            print(f"   ⚠️ Erreur API Serper : {response.status_code}")
            return []
            
    except Exception as e:
        print(f"   ❌ Erreur recherche web : {e}")
        return []


# ========================================
# PARTIE 4 : EXTRACTION DE HOOKS AVEC CLAUDE
# ========================================

def extract_hooks_with_claude(profile_data, posts_data, company_posts, company_profile, web_results, prospect_name, company_name):
    """Extrait 1-2 hooks pertinents pour l'icebreaker"""
    print(f"🎯 Extraction des hooks avec Claude...")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    data_summary = {
        "profile": {
            "fullName": profile_data.get("fullName", "") if profile_data else "",
            "headline": profile_data.get("headline", "") if profile_data else "",
            "summary": profile_data.get("summary", "") if profile_data else "",
            "location": profile_data.get("location", "") if profile_data else "",
            "current_company": profile_data.get("experiences", [{}])[0].get("companyName", "") if profile_data and profile_data.get("experiences") else "",
            "current_position": profile_data.get("experiences", [{}])[0].get("title", "") if profile_data and profile_data.get("experiences") else "",
            "education": profile_data.get("education", [])[:2] if profile_data else [],
            "certifications": profile_data.get("certifications", [])[:3] if profile_data else []
        },
        "recent_posts": posts_data[:5] if posts_data else [],
        "company_posts": company_posts[:3] if company_posts else [],
        "company_profile": {
            "name": company_profile.get("name", "") if company_profile else "",
            "description": company_profile.get("description", "") if company_profile else "",
            "industry": company_profile.get("industry", "") if company_profile else "",
            "employees": company_profile.get("employees", "") if company_profile else "",
            "headquarters": company_profile.get("headquarters", "") if company_profile else ""
        },
        "web_mentions": web_results
    }
    
    prompt = f"""# RÔLE
Tu es un expert en "Sales Intelligence" et en recherche de prospects. Ta mission est d'analyser le profil LinkedIn et la présence web d'un prospect pour extraire des informations clés permettant de rédiger un icebreaker ultra-personnalisé.

# OBJECTIF
Scanner les sources de données fournies (LinkedIn + Web) pour identifier 1 à 2 faits notables ("Hooks") qui permettront d'engager la conversation de manière pertinente et chaleureuse.

# DONNÉES À ANALYSER
{json.dumps(data_summary, indent=2, ensure_ascii=False)}

# PÉRIMÈTRE DE RECHERCHE
Tu dois scanner et analyser les éléments suivants :
1. **Activité LinkedIn :** Posts, commentaires, likes, articles partagés
2. **Réalisations professionnelles :** Promotions récentes, changement de poste, prix, certifications, diplômes
3. **Médias & Presse :** Participation à un podcast, interview vidéo, mention dans la presse (écrite ou digitale), publication d'un livre ou livre blanc
4. **Engagement personnel :** Bénévolat, causes associatives, intérêts marqués (écologie, tech, social, etc.)

# CRITÈRES DE SÉLECTION (STRICT)
1. **Récence ABSOLUE :** Le fait doit dater de MAXIMUM 6 MOIS (180 jours). 
   - Changement de poste : UNIQUEMENT si < 6 mois
   - Certification : UNIQUEMENT si < 6 mois
   - Post LinkedIn : UNIQUEMENT si < 6 mois
   - Article/Podcast : UNIQUEMENT si < 6 mois
   
   ⚠️ UN POSTE PRIS IL Y A 1 AN OU PLUS = PAS UN HOOK VALIDE
   ⚠️ Si aucun fait < 6 mois → Répondre "NOT_FOUND"
2. **Véracité :** NE RIEN INVENTER. Si l'information n'est pas explicitement présente dans les données, ne l'utilise pas.
3. **Pertinence :** Choisis l'information qui offre le meilleur prétexte pour une conversation business ou humaine.
4. **Validation anti-homonymes :** Pour les infos web, vérifie que l'entreprise "{company_name}" est bien mentionnée et que le contexte correspond au profil LinkedIn.

# EXEMPLES DE HOOKS EXCELLENTS (5/5)
✅ "A publié un article sur [sujet précis] dans [média] le [date]"
✅ "A participé au podcast [nom] épisode [X] sur [thème] en [mois année]"
✅ "A rejoint le conseil d'administration de [association] en [mois année]"
✅ "A posté sur LinkedIn à propos de [sujet très spécifique] le [date]"
✅ "A obtenu la certification [nom] en [mois année]"

# EXEMPLES DE HOOKS FAIBLES (< 3/5) À ÉVITER
❌ "A de l'expérience en [domaine]" (trop vague, non daté)
❌ "Travaille chez [entreprise]" (évident, pas un hook)
❌ "A étudié à [école]" (sauf diplôme très récent < 1 an)
❌ "Professionnel dans son domaine" (vide de sens)

# PROCESSUS D'ANALYSE
1. Recherche le **Fait Notable Principal** (le plus récent ET le plus impactant)
2. Recherche un **Fait Notable Secondaire** (uniquement s'il est distinct du premier ET date de < 1 an)
3. **Auto-critique :** 
   - Ces faits sont-ils datés de moins d'un an ?
   - Sont-ils suffisamment intéressants pour un icebreaker ?
   - Ai-je vérifié la cohérence des sources web avec le profil LinkedIn ?
   - Y a-t-il un risque d'homonyme sur les infos web ?

# RÈGLE CRITIQUE : VÉRIFIER LE RÔLE DE LA PERSONNE

Avant de valider un hook, VÉRIFIEZ TOUJOURS :

1. **Est-ce que la personne est ACTEUR ou SPECTATEUR ?**
   
   ✅ ACTEUR (validé) :
   - "J'ai animé le webinar..."
   - "Ravi d'avoir été invité au podcast..."
   - "Fier d'annoncer notre levée de fonds..."
   - "Heureux de partager que j'ai obtenu la certification..."
   
   ❌ SPECTATEUR (à rejeter) :
   - "Enchanté par ce TEDx..." → Il a ASSISTÉ, pas animé
   - "Belle conférence de X..." → Il a ÉCOUTÉ, pas présenté
   - "Intéressant article de Y..." → Il a LU, pas écrit
   - "Bravo à l'équipe pour..." → Il FÉLICITE, pas réalisé

2. **Mots-clés à surveiller :**
   
   🚨 DANGER (souvent spectateur) :
   - "Enchanté par"
   - "Belle", "Intéressant", "Inspirant"
   - "Bravo à", "Félicitations à"
   - "J'ai assisté", "J'ai participé" (en tant que public)
   
   ✅ SÛR (souvent acteur) :
   - "J'ai animé", "J'ai présenté"
   - "Ravi d'annoncer", "Fier de partager"
   - "J'ai obtenu", "J'ai rejoint"
   - "Heureux de contribuer"

3. **EN CAS DE DOUTE → REJETER LE HOOK**
   
   Mieux vaut dire "NOT_FOUND" que de faire une erreur d'interprétation.
   Une erreur = crédibilité perdue instantanément.

# FORMAT DE SORTIE (JSON UNIQUEMENT)
Si aucune information pertinente de moins d'un an n'est trouvée, réponds UNIQUEMENT avec la chaîne :
"NOT_FOUND"

Sinon, réponds avec ce JSON exact (sans texte avant ou après) :
{{
  "hook_principal": {{
    "description": "Description concise en 1 phrase",
    "contexte": "Détails clés : nom événement, sujet, titre...",
    "date": "2024-12-15",
    "source": "URL ou 'LinkedIn - Section X'",
    "pertinence": 5
  }},
  "hook_secondaire": {{
    "description": "...",
    "contexte": "...",
    "date": "2024-11-20",
    "source": "...",
    "pertinence": 3
  }},
  "validation": {{
    "tous_faits_moins_1_an": true,
    "coherence_linkedin_verifiee": true,
    "entreprise_mentionnee_si_web": true
  }}
}}

Si tu n'as qu'un seul hook, omets "hook_secondaire" du JSON.

Réponds UNIQUEMENT avec le JSON ou "NOT_FOUND"."""

    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        
        hooks_response = message.content[0].text.strip()
        hooks_response = hooks_response.replace('```json', '').replace('```', '').strip()
        
        print(f"   ✅ Hooks extraits")
        return hooks_response
        
    except Exception as e:
        print(f"   ❌ Erreur extraction hooks : {e}")
        return "NOT_FOUND"


# ========================================
# PARTIE 5 : GÉNÉRATION ICEBREAKER OPTIMISÉE 10/10
# ========================================

def generate_advanced_icebreaker(prospect_data, hooks_json, job_posting_data=None):
    """Génère un icebreaker ultra-personnalisé basé sur les hooks ET l'annonce"""
    print(f"✍️  Génération de l'icebreaker...")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Parser les hooks
    try:
        if hooks_json == "NOT_FOUND":
            hooks_data = {"status": "NOT_FOUND"}
        else:
            hooks_data = json.loads(hooks_json)
    except:
        hooks_data = {"status": "NOT_FOUND"}
    
    # 🆕 Préparer les données de l'annonce
    job_posting_context = ""
    if job_posting_data:
        job_posting_context = format_job_data_for_prompt(job_posting_data)
        print(f"   ✅ Annonce intégrée : {job_posting_data.get('title', 'N/A')[:50]}...")
    
    # ✅ PROMPT FEW-SHOT OPTIMISÉ 10/10
    prompt = f"""═══════════════════════════════════════════════════════════════════
FEW-SHOT OPTIMISÉ POUR CONVERSION MAXIMALE
Version finale - Basé sur posts LinkedIn, commentaires, web

═══════════════════════════════════════════════════════════════════

Tu es un expert en prospection B2B spécialisé dans le recrutement de profils finance critiques.

Ta mission : Rédiger un message LinkedIn qui démontre une compréhension profonde des enjeux métier du prospect, avec un ton professionnel et courtois, sans aucune auto-promotion.

═══════════════════════════════════════════════════════════════════
DONNÉES DISPONIBLES
═══════════════════════════════════════════════════════════════════

PROSPECT :
- Prénom : {prospect_data['first_name']}
- Nom : {prospect_data['last_name']}
- Entreprise : {prospect_data['company']}

{f'''
ANNONCE DE POSTE DISPONIBLE :
{job_posting_context}

→ Cette annonce révèle le BESOIN EXPLICITE. Utilise-la comme BASE PRINCIPALE.
''' if job_posting_data else ''}

HOOKS IDENTIFIÉS (posts LinkedIn, commentaires, web) :
{json.dumps(hooks_data, indent=2, ensure_ascii=False)}

NOTRE POSITIONNEMENT :
Cabinet : {COMPANY_INFO['name']}
Expertise : {COMPANY_INFO['mission']}
Profils recrutés : {COMPANY_INFO['profiles']}

═══════════════════════════════════════════════════════════════════
EXEMPLES D'EXCELLENTS ICEBREAKERS (10/10)
═══════════════════════════════════════════════════════════════════

Ces exemples suivent TOUS le même pattern :
→ Salutation + Observation factuelle
→ Insight business (défi réel)
→ Question stratégique sur LEUR approche

─────────────────────────────────────────────────────────────────

EXEMPLE 1 : Post LinkedIn + Secteur spécifique (Agriculture/Mutuelle)

CONTEXTE :
- Claire Martin, Directrice Audit Interne, Mutualia
- Hook : Recherche un auditeur interne (annonce)
- Secteur : Mutuelle agricole (ACPR)

ICEBREAKER (82 mots) :
"Bonjour Claire, en lisant votre recherche pour Mutualia, une question me vient : comment gérez-vous le grand écart culturel ? Le marché dispose de nombreux auditeurs excellents techniquement (Big 4, normes strictes), mais qui sont souvent incapables de s'adapter à la réalité du terrain agricole et aux élus mutualistes. Avez-vous tendance à privilégier le savoir-être (le fit agricole) quitte à former sur la technique, ou l'expertise reste-t-elle non négociable pour l'ACPR ?"

POURQUOI C'EST EXCELLENT :
✅ Vocabulaire ultra-précis (ACPR, élus mutualistes, Big 4)
✅ Insight puissant (grand écart culturel)
✅ Question stratégique binaire (fit vs expertise)
✅ Zéro auto-promotion
✅ Ton respectueux et courtois

─────────────────────────────────────────────────────────────────

EXEMPLE 2 : Post LinkedIn sur webinar + Contexte EPM/BI

CONTEXTE :
- Karine Dubois, Responsable CDG et Outils, GMA
- Hook : A animé un webinar sur l'automatisation EPM (post LinkedIn récent)
- Poste recherché : Solution Lead EPM BI

ICEBREAKER (70 mots) :
"Bonjour Karine, votre webinar sur l'automatisation des flux EPM résonne particulièrement. Pour votre poste de Solution Lead EPM BI, trouver un profil capable de jongler entre la rigueur du Contrôle de Gestion et l'administration technique de Tagetik ou Essbase est un défi majeur. Dans votre stratégie d'automatisation, cherchez-vous avant tout un expert capable d'optimiser l'existant ou un Project Leader capable de repenser l'architecture ?"

POURQUOI C'EST EXCELLENT :
✅ Utilise le hook (webinar) de façon naturelle
✅ Vocabulaire technique précis (Tagetik, Essbase, EPM)
✅ Question d'arbitrage (expert vs leader)
✅ Lien hook → besoin business évident
✅ 70 mots (court et percutant)

─────────────────────────────────────────────────────────────────

EXEMPLE 3 : Expansion internationale + Audit multi-pays

CONTEXTE :
- Philippe Durand, Directeur Audit Interne, CFAO
- Hook : Post LinkedIn sur expansion en Afrique de l'Ouest
- Contexte : Groupe avec filiales africaines

ICEBREAKER (68 mots) :
"Bonjour Philippe, en voyant l'expansion continue de CFAO en Afrique, je mesure le défi de gouvernance que cela représente pour votre Audit Interne : maintenir un standard groupe tout en naviguant les spécificités réglementaires locales. Sur vos recrutements actuels, privilégiez-vous des profils issus de Big 4 locaux (experts terrain) ou des auditeurs formés aux standards de grands groupes internationaux ?"

POURQUOI C'EST EXCELLENT :
✅ Utilise le contexte d'expansion (hook)
✅ Insight sur dilemme réel (standard vs local)
✅ Question binaire claire
✅ Vocabulaire adapté (Big 4, gouvernance)
✅ Concis (68 mots)

─────────────────────────────────────────────────────────────────

EXEMPLE 4 : Vocabulaire ultra-spécialisé (Réassurance)

CONTEXTE :
- Virginie Lemoine, Directrice Comptabilité, Captive de réassurance
- Hook : Recherche Comptable Technique Réassurance (annonce)
- Secteur : Réassurance corporate

ICEBREAKER (91 mots) :
"Bonjour Virginie, j'ai consulté votre recherche actuelle pour le poste de Comptable Technique en Réassurance. Sur le marché parisien, trouver un technicien qui maîtrise à la fois la complexité des traités (proportionnels et non-pro) et les spécificités d'une captive de réassurance est un véritable défi. La plupart des profils qualifiés sont actuellement captifs des grands réassureurs. Privilégiez-vous un expert issu de la réassurance classique ou cherchez-vous un profil déjà rompu aux enjeux de reporting Solvabilité II en environnement corporate ?"

POURQUOI C'EST EXCELLENT :
✅ Vocabulaire ultra-technique (traités pro/non-pro, captive)
✅ Insight marché (profils captifs)
✅ Question d'arbitrage claire
✅ 91 mots (justifié par complexité)
✅ Zéro invention (tout est factuel)

─────────────────────────────────────────────────────────────────

EXEMPLE 5 : Certification récente (post LinkedIn)

CONTEXTE :
- Marc Leblanc, Contrôleur de Gestion, Groupe industriel
- Hook : A obtenu la certification CMA (Certified Management Accountant) il y a 2 mois (post LinkedIn)
- Contexte : Groupe industriel avec transformation digitale

ICEBREAKER (78 mots) :
"Bonjour Marc, félicitations pour votre certification CMA récente. Cette expertise en contrôle de gestion stratégique résonne particulièrement dans un contexte industriel où la modélisation des coûts devient de plus en plus complexe. J'imagine que chez [Entreprise], l'équilibre entre pilotage opérationnel et vision stratégique suppose des profils capables de jongler entre les deux. Sur vos recrutements contrôle de gestion, privilégiez-vous cette double compétence ou préférez-vous segmenter les rôles ?"

POURQUOI C'EST EXCELLENT :
✅ Utilise le hook certification (< 6 mois)
✅ Lien certification → besoin business
✅ Question sur leur approche organisationnelle
✅ Vocabulaire métier (modélisation coûts, pilotage)
✅ Pas d'invention sectorielle

─────────────────────────────────────────────────────────────────

EXEMPLE 6 : Commentaire LinkedIn sur transformation finance

CONTEXTE :
- Sophie Bernard, DAF, Groupe bancaire régional
- Hook : A commenté un post sur la transformation finance digitale (LinkedIn)
- Contexte : Banque régionale, enjeux réglementaires

ICEBREAKER (82 mots) :
"Bonjour Sophie, votre commentaire sur la transformation finance digitale soulève un point clé : l'équilibre entre innovation technologique et conformité réglementaire bancaire. Dans un contexte où Bâle III et les reporting ACPR imposent une rigueur stricte, j'imagine que vos recrutements finance doivent allier culture bancaire et appétence pour les outils data. Privilégiez-vous des profils issus de banques ayant déjà opéré ces transformations ou acceptez-vous des profils plus transverses à former sur la réglementation ?"

POURQUOI C'EST EXCELLENT :
✅ Utilise le commentaire comme point d'entrée
✅ Vocabulaire bancaire précis (Bâle III, ACPR)
✅ Dilemme réel (expertise vs appétence tech)
✅ Pas d'invention (réglementation connue)
✅ 82 mots (équilibré)

─────────────────────────────────────────────────────────────────

EXEMPLE 7 : Participation podcast (mention web)

CONTEXTE :
- Thomas Dupont, Directeur Consolidation, Groupe coté
- Hook : A participé à un podcast finance "Les Consolideurs" il y a 3 mois (mention web)
- Contexte : Groupe coté, enjeux IFRS

ICEBREAKER (75 mots) :
"Bonjour Thomas, j'ai écouté votre intervention dans le podcast Les Consolideurs sur les défis IFRS 17. Votre analyse sur la complexité des impacts actuariels résonne particulièrement. Pour des groupes cotés comme le vôtre, trouver des consolideurs capables de piloter ces sujets techniques tout en gérant les délais de clôture est un vrai casse-tête. Privilégiez-vous des profils Big 4 avec forte expertise IFRS ou des consolideurs groupe déjà rompus à vos outils ?"

POURQUOI C'EST EXCELLENT :
✅ Utilise le hook podcast (< 6 mois)
✅ Référence précise (nom podcast, sujet)
✅ Vocabulaire technique (IFRS 17, impacts actuariels)
✅ Question d'arbitrage (Big 4 vs interne)
✅ 75 mots

─────────────────────────────────────────────────────────────────

EXEMPLE 8 : Post LinkedIn sur outil finance (SAP/Tagetik)

CONTEXTE :
- Isabelle Martin, Responsable Reporting Groupe, Groupe assurance
- Hook : A posté sur LinkedIn sur migration Tagetik il y a 1 mois
- Contexte : Groupe assurance, consolidation

ICEBREAKER (80 mots) :
"Bonjour Isabelle, votre post sur la migration Tagetik soulève un point crucial : la gestion du changement lors de transformations EPM. Entre résistance des équipes habituées à l'existant et montée en compétence sur le nouvel outil, j'imagine que le profil pour piloter ce type de projet doit allier pédagogie et expertise technique. Sur ce genre de recrutement, privilégiez-vous un chef de projet EPM capable de porter la conduite du changement ou un expert Tagetik pur ?"

POURQUOI C'EST EXCELLENT :
✅ Utilise le hook migration Tagetik
✅ Insight sur défi réel (conduite du changement)
✅ Question d'arbitrage (chef de projet vs expert)
✅ Pas d'invention (enjeux universels EPM)
✅ 80 mots

─────────────────────────────────────────────────────────────────

EXEMPLE 9 : Sans hook (contexte entreprise uniquement)

CONTEXTE :
- Jean Moreau, Directeur Comptabilité, Groupe funéraire
- Hook : NOT_FOUND (aucun post récent, pas d'annonce)
- Contexte : FUNECAP GROUPE (secteur funéraire)

ICEBREAKER (72 mots) :
"Bonjour Jean, en tant que Directeur Comptabilité chez FUNECAP GROUPE, j'imagine que l'équilibre entre rigueur comptable et spécificités opérationnelles suppose des profils finance capables de s'adapter aux réalités terrain. Sur vos recrutements comptables, privilégiez-vous des profils issus de groupes multi-sites habitués à cette complexité organisationnelle ou des experts comptables purs que vous formez ensuite sur vos spécificités ?"

POURQUOI C'EST EXCELLENT :
✅ Pas de hook → focus sur contexte entreprise
✅ Enjeu universel (rigueur vs opérationnel)
✅ Zéro invention sectorielle (pas de "réglementation funéraire")
✅ Question sur leur approche RH
✅ 72 mots (concis sans hook)

─────────────────────────────────────────────────────────────────

EXEMPLE 10 : Article presse (mention web récente)

CONTEXTE :
- Caroline Petit, CFO, Groupe retail
- Hook : Mentionnée dans Les Échos sur transformation digitale finance (article 2 mois)
- Contexte : Retail, transformation digitale

ICEBREAKER (77 mots) :
"Bonjour Caroline, votre interview dans Les Échos sur la transformation digitale de la fonction finance résonne particulièrement. Vous évoquiez la difficulté à trouver des profils finance capables d'allier rigueur comptable et appétence pour les outils data/BI. J'imagine que cette double compétence est devenue critique pour vos recrutements. Privilégiez-vous des profils issus du conseil habitués à ces transformations ou des finance purs avec forte curiosité tech ?"

POURQUOI C'EST EXCELLENT :
✅ Utilise l'article presse (< 6 mois)
✅ Référence précise (Les Échos)
✅ Lien article → besoin recrutement
✅ Question d'arbitrage (conseil vs finance)
✅ 77 mots

═══════════════════════════════════════════════════════════════════
EXEMPLES À NE JAMAIS REPRODUIRE (0-3/10)
═══════════════════════════════════════════════════════════════════

Ces contre-exemples montrent les ERREURS GRAVES à éviter.

─────────────────────────────────────────────────────────────────

MAUVAIS EXEMPLE 1 : Auto-promotion flagrante

"Bonjour Thomas, je sais qu'un poste de Responsable Compta Banque est rare. J'ai identifié un profil Senior qui a cette double casquette : culture audit et Key User SAP. Il pourrait soulager vos équipes instantanément. Voyez-vous un inconvénient à ce que je vous envoie sa synthèse ce matin ?"

❌ POURQUOI C'EST MAUVAIS :
- "J'ai identifié un profil" = pitch commercial pur
- Parle de NOTRE candidat, pas de LEURS enjeux
- Closing de vente ("Voyez-vous un inconvénient")
- Aucune question stratégique
- Violation GRAVE : auto-promotion

─────────────────────────────────────────────────────────────────

MAUVAIS EXEMPLE 2 : Invention sectorielle

"Bonjour Thomas, recruter un Responsable Comptabilité Banque chez FUNECAP GROUPE suppose de naviguer la réglementation sectorielle funéraire complexe. Entre normes comptables spécifiques et contraintes métier, j'imagine que ce profil doit allier expertise comptable et connaissance des spécificités funéraires. Privilégiez-vous une expertise sectorielle ou une base comptable solide ?"

❌ POURQUOI C'EST MAUVAIS :
- "Réglementation sectorielle funéraire" = INVENTÉE (n'existe pas)
- "Normes comptables spécifiques funéraire" = FAUX
- Invention tue la crédibilité instantanément
- Violation GRAVE : fabrication d'expertise

─────────────────────────────────────────────────────────────────

MAUVAIS EXEMPLE 3 : Hook obsolète (événement de 3 ans)

"Bonjour Thomas, félicitations pour votre nomination en tant que Directeur adjoint comptabilité chez FUNECAP GROUPE. Cette prise de poste suppose une structuration de l'équipe finance. J'imagine que votre recherche s'inscrit dans cette dynamique. Privilégiez-vous des profils bancaires ou comptables ?"

❌ POURQUOI C'EST MAUVAIS :
- "Félicitations pour votre nomination" → poste pris il y a 3 ANS
- Hook périmé (> 6 mois) = ridicule
- Manque de crédibilité totale
- Violation : hook obsolète

─────────────────────────────────────────────────────────────────

MAUVAIS EXEMPLE 4 : Trop long (120+ mots)

"Bonjour Marie, en tant que DAF chez XYZ, je sais que le contexte actuel de transformation digitale impose de repenser complètement la fonction finance. Entre l'automatisation des processus, la mise en place de nouveaux outils de reporting, la formation des équipes, la gestion du changement organisationnel et l'adaptation aux nouvelles normes réglementaires qui évoluent constamment, je suppose que vos enjeux de recrutement sont multiples. D'un côté vous avez besoin de profils techniques capables de maîtriser les outils, de l'autre vous cherchez des managers capables de piloter le changement. Sans oublier la dimension stratégique qui devient de plus en plus importante. Comment gérez-vous tous ces aspects dans vos recrutements actuels ?"

❌ POURQUOI C'EST MAUVAIS :
- 125 mots (50% trop long)
- Trop de détails, dilue le message
- Question finale trop vague
- Perte d'attention du lecteur
- Violation : longueur excessive

─────────────────────────────────────────────────────────────────

MAUVAIS EXEMPLE 5 : Vocabulaire vague

"Bonjour Marc, votre entreprise est en pleine croissance. Les enjeux financiers sont importants et la fonction finance doit se structurer. J'imagine que recruter les bons profils est un défi dans ce contexte. Comment gérez-vous ces enjeux de recrutement ?"

❌ POURQUOI C'EST MAUVAIS :
- "Enjeux financiers" = vide de sens
- "Fonction finance doit se structurer" = banal
- "Les bons profils" = non spécifique
- Aucun vocabulaire métier précis
- Question faible sans valeur ajoutée
- Violation : généralisme

─────────────────────────────────────────────────────────────────

MAUVAIS EXEMPLE 6 : Pitch commercial déguisé (vidéo N8N)

"Bonjour Roland, j'ai récemment vu vos masterclass sur l'excellence managériale sur LinkedIn, notamment celle avec Isabelle Saladin. Une initiative inspirante pour booster l'engagement des équipes. Chez Aisance, nous aidons les entreprises comme Incentive à intégrer l'IA dans leurs processus pour accélérer l'acquisition client. Auriez-vous un moment pour échanger sur comment cela pourrait caler votre croissance ?"

❌ POURQUOI C'EST MAUVAIS :
- "Chez Aisance, nous aidons..." = pitch commercial pur
- Parle de NOTRE entreprise, pas de LEURS enjeux
- "Auriez-vous un moment pour échanger" = closing de vente
- Aucune question stratégique sur leur approche
- Violation GRAVE : auto-promotion + closing commercial

─────────────────────────────────────────────────────────────────

MAUVAIS EXEMPLE 7 : Hook spectateur (pas acteur)

"Bonjour Pierre, j'ai vu que vous avez assisté au TEDx sur l'innovation managériale. Cette conférence devait être inspirante. En tant que DAF, j'imagine que ces sujets vous intéressent pour vos équipes. Comment intégrez-vous ces approches dans votre fonction finance ?"

❌ POURQUOI C'EST MAUVAIS :
- "Assisté au TEDx" = SPECTATEUR (pas acteur)
- Le hook n'est pas un accomplissement
- Question faible sans lien business clair
- Violation : hook spectateur

─────────────────────────────────────────────────────────────────

MAUVAIS EXEMPLE 8 : Lien hook → business artificiel

"Bonjour Sophie, j'ai vu que vous avez partagé un article sur l'IA. L'IA transforme la finance. Pour recruter un Contrôleur de Gestion, j'imagine que l'appétence IA devient importante. Privilégiez-vous des profils tech ou finance ?"

❌ POURQUOI C'EST MAUVAIS :
- Hook trop faible (partage article = pas significatif)
- Lien "IA → CDG" = forcé et artificiel
- Question banale sans insight
- Violation : lien hook/business inexistant

─────────────────────────────────────────────────────────────────

MAUVAIS EXEMPLE 9 : Ton familier

"Salut Marc, ça fait un bail ! J'ai vu que tu recrutais un CDG. C'est pas facile de trouver des bons profils en ce moment, hein ? Du coup, comment tu gères ça de ton côté ? T'es plutôt sur des profils junior à former ou tu veux du senior direct ?"

❌ POURQUOI C'EST MAUVAIS :
- Tutoiement (jamais en prospection B2B)
- Ton trop décontracté ("ça fait un bail", "du coup")
- Manque de professionnalisme total
- Violation GRAVE : ton inapproprié

─────────────────────────────────────────────────────────────────

MAUVAIS EXEMPLE 10 : Question non stratégique

"Bonjour Thomas, j'ai vu votre annonce pour un Responsable Comptabilité. Le poste a l'air intéressant. Combien de personnes il va manager ? Et c'est quoi le package salarial que vous proposez ? Le poste est en CDI ?"

❌ POURQUOI C'EST MAUVAIS :
- Questions opérationnelles (pas stratégiques)
- Aucun insight business
- Aucune valeur ajoutée
- Ressemble à un candidat, pas un expert
- Violation : questions inadaptées

═══════════════════════════════════════════════════════════════════
RÈGLES STRICTES À RESPECTER
═══════════════════════════════════════════════════════════════════

🚫 INTERDICTION ABSOLUE N°1 : AUTO-PROMOTION

JAMAIS écrire :
- "J'ai identifié un profil..."
- "Nous accompagnons..."
- "J'ai isolé un candidat..."
- "Mon réseau compte..."
- "Je dispose d'un expert..."

JAMAIS de closing commercial :
- "Voyez-vous un inconvénient..."
- "Seriez-vous intéressé..."
- "Puis-je vous proposer..."
- "Auriez-vous un moment pour échanger..."

→ Poser UNIQUEMENT des questions sur LEUR approche stratégique

─────────────────────────────────────────────────────────────────

🚫 INTERDICTION ABSOLUE N°2 : INVENTER DES SPÉCIFICITÉS SECTORIELLES

SECTEURS OÙ TU PEUX ÊTRE PRÉCIS (expertise confirmée) :
✅ Banque : Bâle III, MIF II, ACPR, CRD IV, KYC/AML
✅ Assurance : Solvabilité II, IFRS 17, ACPR, provisions techniques
✅ Finance : IFRS, US GAAP, consolidation, normes comptables
✅ Audit : Big 4, normes ISA, CNCC

SECTEURS OÙ TU DOIS RESTER GÉNÉRIQUE :
⚠️ Funéraire : PAS de "réglementation funéraire", rester sur enjeux universels
⚠️ Retail : Pas d'invention de normes sectorielles
⚠️ Services : Rester sur enjeux finance généraux

RÈGLE D'OR : En cas de doute → enjeux UNIVERSELS
- Structuration fonction finance
- Rigueur comptable vs pragmatisme opérationnel
- Équilibre technique vs management
- Transformation digitale (safe)

─────────────────────────────────────────────────────────────────

🚫 INTERDICTION ABSOLUE N°3 : HOOKS OBSOLÈTES

JAMAIS utiliser un hook de + de 6 MOIS :
- Changement de poste > 6 mois = IGNORER
- Certification > 6 mois = IGNORER
- Post LinkedIn > 6 mois = IGNORER
- Article/Podcast > 6 mois = IGNORER

Si hook obsolète → Construire sur CONTEXTE ACTUEL (entreprise, fonction, défis)

Exemple :
❌ "Félicitations pour votre nomination il y a 3 ans"
✅ "En tant que Directeur comptabilité, j'imagine que..."

─────────────────────────────────────────────────────────────────

✅ RÈGLE DE LONGUEUR (FLEXIBLE)

LONGUEUR CIBLE : 70-95 mots selon complexité

ADAPTATION PAR COMPLEXITÉ :
- Poste simple (Comptable Général) → 65-75 mots
- Poste technique (Contrôleur de Gestion) → 75-85 mots
- Poste complexe (Solution Lead EPM, Réassurance, Audit multi-pays) → 85-95 mots

LIMITE ABSOLUE : 100 mots MAXIMUM

RATIONALE : En B2B finance, démontrer une expertise réelle nécessite 
du vocabulaire technique et des insights précis. Un icebreaker de 90 mots 
bien écrit vaut mieux qu'un de 70 mots vague.

─────────────────────────────────────────────────────────────────

✅ STRUCTURE OBLIGATOIRE (3 TEMPS)

PARTIE 1 : Salutation + Observation/Hook [25-35 mots]
→ "Bonjour [Prénom],"
→ SI hook récent (< 6 mois) : l'utiliser
→ SI annonce : partir de l'annonce
→ SI aucun hook : partir du contexte entreprise/fonction

PARTIE 2 : Insight business (défi réel) [30-45 mots]
→ Identifier UN défi concret et réaliste
→ Vocabulaire métier précis
→ Formuler avec respect ("j'imagine", "je suppose")
→ JAMAIS parler de nos candidats

PARTIE 3 : Question stratégique [15-25 mots]
→ Question sur LEUR APPROCHE (pas sur nos services)
→ Formulée avec courtoisie ("Privilégiez-vous", "Comment arbitrez-vous")
→ Question binaire ou d'arbitrage (plus facile à répondre)

─────────────────────────────────────────────────────────────────

✅ TON REQUIS

TOUJOURS :
- Vouvoiement systématique
- "Bonjour [Prénom]," en ouverture
- Tournures polies ("j'imagine", "je suppose", "privilégiez-vous")
- Vocabulaire métier précis (noms d'outils, normes, réglementations)

🎯 RÈGLE CRITIQUE : VOCABULAIRE ULTRA-PRÉCIS
Utilise TOUJOURS les termes les plus précis possibles :
✅ "Big 4" pas "cabinets d'audit"
✅ "ACPR" pas "régulateur"
✅ "Bâle III" pas "normes bancaires"
✅ "IFRS 17" pas "normes comptables"
✅ "Tagetik" pas "outil EPM"
✅ "élus mutualistes" pas "gouvernance"

JAMAIS :
- Tutoiement
- Points de suspension ("...")
- "Ça veut dire", "tout ça", "du coup"
- Ton familier ou décontracté

═══════════════════════════════════════════════════════════════════
PROCESSUS DE GÉNÉRATION
═══════════════════════════════════════════════════════════════════

ÉTAPE 1 : ANALYSER LES DONNÉES DISPONIBLES

A. L'annonce est-elle disponible ?
   → OUI : Utiliser l'annonce comme BASE PRINCIPALE
   → NON : Passer aux hooks

B. Les hooks sont-ils valides (< 6 mois) ?
   → OUI : Utiliser le meilleur hook
   → NON : Passer au contexte entreprise

C. Quel est le niveau de complexité du poste ?
   → Simple : 70-75 mots
   → Technique : 75-85 mots
   → Complexe : 85-95 mots

ÉTAPE 2 : CHOISIR LE BON PATTERN

Regarder les 10 exemples excellents ci-dessus et choisir celui qui ressemble 
le plus au cas présent :
- Annonce → Exemple 1, 2, 4
- Post LinkedIn → Exemple 2, 5, 8
- Commentaire LinkedIn → Exemple 6
- Podcast/Article → Exemple 7, 10
- Sans hook → Exemple 9

ÉTAPE 3 : RÉDIGER EN SUIVANT LE PATTERN CHOISI

- Reprendre la STRUCTURE EXACTE de l'exemple choisi
- Adapter le VOCABULAIRE au secteur (banque/assurance/finance/audit)
- Vérifier la LONGUEUR (70-95 mots)
- Vérifier ZÉRO auto-promo
- Vérifier ZÉRO invention sectorielle

ÉTAPE 4 : AUTO-VÉRIFICATION

□ Ai-je commencé par "Bonjour [Prénom]," ?
□ Ai-je vouvoyé tout au long ?
□ Mon vocabulaire est-il métier et précis ?
□ Mon insight est-il factuel (pas inventé) ?
□ Mon défi business est-il réaliste ?
□ Ma question porte-t-elle sur LEUR approche (pas nos services) ?
□ Ai-je ZÉRO auto-promo ?
□ Ai-je ZÉRO closing commercial ?
□ Longueur = 70-95 mots ?
□ Pas de points de suspension ?

═══════════════════════════════════════════════════════════════════

Génère maintenant l'icebreaker en suivant EXACTEMENT ces patterns.

Réponds UNIQUEMENT avec le message final (pas de préambule, pas de markdown)."""

    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            temperature=0.4,
            messages=[{"role": "user", "content": prompt}]
        )
        
        icebreaker = message.content[0].text.strip()
        print(f"   ✅ Icebreaker généré !")
        return icebreaker
        
    except Exception as e:
        print(f"   ❌ Erreur génération : {e}")
        return "Erreur lors de la génération de l'icebreaker"


# ========================================
# PARTIE 6 : MISE À JOUR GOOGLE SHEET
# ========================================

def update_sheet(sheet, row_number, linkedin_url, hooks_json, icebreaker):
    """Met à jour le Google Sheet en une seule fois (optimisé)"""
    print(f"💾 Mise à jour de la ligne {row_number}...")
    
    try:
        # Extraire les hooks pour la colonne G
        try:
            if hooks_json != "NOT_FOUND":
                hooks_data = json.loads(hooks_json)
                notable = json.dumps(hooks_data, ensure_ascii=False)[:1500]
            else:
                notable = "Aucun hook pertinent trouvé"
        except:
            notable = str(hooks_json)[:1500]
        
        # Mise à jour en BATCH
        values = [[
            linkedin_url,  # D
            "",            # E
            "",            # F
            notable,       # G
            "",            # H
            "",            # I
            "",            # J
            icebreaker     # K
        ]]
        
        range_name = f'D{row_number}:K{row_number}'
        sheet.update(range_name, values)
        
        print(f"   ✅ Mise à jour réussie !\n")
        
    except Exception as e:
        print(f"   ❌ Erreur mise à jour : {e}\n")
        import traceback
        traceback.print_exc()


# ========================================
# FONCTION PRINCIPALE
# ========================================

def main():
    """Fonction principale"""
    print("\n" + "="*80)
    print("🚀 ICEBREAKER AUTOMATION - VERSION OPTIMISÉE 10/10")
    print("   LinkedIn + Web + Annonces + Smart Hook Extraction")
    print("="*80 + "\n")
    
    try:
        sheet = connect_to_google_sheet()
        apify_client = init_apify_client()
        
        prospects = get_prospects(sheet)
        
        if not prospects:
            print("✨ Aucun prospect à traiter !")
            return
        
        for i, prospect in enumerate(prospects, 1):
            print(f"\n{'='*80}")
            print(f"PROSPECT {i}/{len(prospects)} : {prospect['first_name']} {prospect['last_name']}")
            print(f"{'='*80}\n")
            
            # 1. URL LinkedIn
            if not prospect['linkedin_url']:
                linkedin_url = search_linkedin_profile(
                    prospect['first_name'],
                    prospect['last_name'],
                    prospect['company']
                )
            else:
                linkedin_url = prospect['linkedin_url']
                print(f"🔗 URL LinkedIn fourni : {linkedin_url}\n")
            
            # 2. Scraping annonce (si URL fournie)
            job_posting_data = None
            if prospect.get('job_posting_url'):
                print(f"📋 Scraping de l'annonce de poste...")
                job_posting_data = scrape_job_posting(prospect['job_posting_url'])
                time.sleep(2)
            
            # 3. Scraping LinkedIn - PHASE 1 : 5 posts
            profile_data = scrape_linkedin_profile(apify_client, linkedin_url)
            time.sleep(3)
            
            posts_data = scrape_linkedin_posts(apify_client, linkedin_url, limit=5)
            time.sleep(3)
            
            company_posts = scrape_company_posts(apify_client, prospect['company'], limit=5)
            time.sleep(3)
            
            company_profile = scrape_company_profile(apify_client, prospect['company'])
            time.sleep(3)
            
            # 4. Recherche Web
            title = ""
            if profile_data and profile_data.get('experiences'):
                title = profile_data['experiences'][0].get('title', '')
            
            web_results = web_search_prospect(
                prospect['first_name'],
                prospect['last_name'],
                prospect['company'],
                title
            )
            time.sleep(2)
            
            # 5. Extraction des hooks - TENTATIVE 1 avec 5 posts
            print(f"🎯 Tentative 1 : Extraction hooks avec 5 posts...")
            hooks_json = extract_hooks_with_claude(
                profile_data, 
                posts_data, 
                company_posts, 
                company_profile,
                web_results,
                f"{prospect['first_name']} {prospect['last_name']}",
                prospect['company']
            )
            time.sleep(2)
            
            # 6. SI AUCUN HOOK TROUVÉ → Scraper 5 posts supplémentaires
            if hooks_json == "NOT_FOUND":
                print(f"⚠️  Aucun hook trouvé avec 5 posts")
                print(f"🔄 Tentative 2 : Scraping de 5 posts supplémentaires...")
                
                # Scraper 5 posts supplémentaires (total = 10)
                additional_posts = scrape_linkedin_posts(apify_client, linkedin_url, limit=10)
                time.sleep(3)
                
                additional_company_posts = scrape_company_posts(apify_client, prospect['company'], limit=10)
                time.sleep(3)
                
                # Réessayer l'extraction avec 10 posts
                print(f"🎯 Tentative 2 : Extraction hooks avec 10 posts...")
                hooks_json = extract_hooks_with_claude(
                    profile_data, 
                    additional_posts,  # 10 posts au lieu de 5
                    additional_company_posts,  # 10 posts au lieu de 5
                    company_profile,
                    web_results,
                    f"{prospect['first_name']} {prospect['last_name']}",
                    prospect['company']
                )
                time.sleep(2)
            
            # 7. Génération icebreaker (avec annonce si disponible)
            icebreaker = generate_advanced_icebreaker(prospect, hooks_json, job_posting_data)
            
            # 8. Mise à jour Google Sheet
            update_sheet(sheet, prospect['row_number'], linkedin_url, hooks_json, icebreaker)
            
            # Pause entre prospects
            if i < len(prospects):
                print(f"⏳ Pause de {DELAY_BETWEEN_PROSPECTS} secondes...\n")
                time.sleep(DELAY_BETWEEN_PROSPECTS)
        
        print("\n" + "="*80)
        print("✅ AUTOMATISATION TERMINÉE AVEC SUCCÈS !")
        print("="*80)
        print(f"\n📊 {len(prospects)} prospect(s) traité(s)")
        print(f"💡 Consultez votre Google Sheet pour voir les résultats\n")
        
    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()