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
    
    # ✅ PROMPT OPTIMISÉ 10/10
    prompt = f"""Tu es un expert en "Sales Intelligence" et en prospection B2B avec 15 ans d'expérience dans le recrutement de profils finance critiques.

Ta mission : rédiger un message LinkedIn qui démontre une VRAIE compréhension des enjeux business du prospect, avec un ton PROFESSIONNEL et COURTOIS, sans AUCUNE auto-promotion.

CONTEXTE PROSPECT :
- Prénom : {prospect_data['first_name']}
- Nom : {prospect_data['last_name']}
- Entreprise : {prospect_data['company']}

{f'''
═══════════════════════════════════════════════════════════════════
🆕 ANNONCE DE POSTE DISPONIBLE
═══════════════════════════════════════════════════════════════════

{job_posting_context}

RÈGLE CRITIQUE : Cette annonce révèle le BESOIN EXPLICITE de l'entreprise.
L'annonce doit être utilisée comme BASE PRINCIPALE pour identifier les enjeux business.

PRIORITÉ D'UTILISATION DES SOURCES :
1. Annonce de poste (besoin explicite) → PRIORITAIRE
2. Hooks LinkedIn/Web (accomplissements personnels) → SECONDAIRE
3. Contexte entreprise général → TERTIAIRE

EXEMPLES D'UTILISATION DE L'ANNONCE :

Si l'annonce mentionne "transformation ERP SAP" :
✅ "Bonjour Marc, recruter un Contrôleur de Gestion capable de piloter la transformation SAP S/4HANA suppose une double expertise technique et finance rarement réunie sur le marché..."

Si l'annonce mentionne "consolidation IFRS 17" :
✅ "Bonjour Sophie, l'entrée en vigueur d'IFRS 17 complexifie significativement le profil de consolideur recherché, notamment sur la compréhension des impacts actuariels..."

Si l'annonce mentionne "levée de fonds" ou "scale-up" :
✅ "Bonjour Pierre, structurer la fonction finance en parallèle d'une hyper-croissance suppose des profils capables de poser des process tout en préservant l'agilité..."

INTERDICTION : Ne pas ignorer l'annonce si elle est disponible.
Si vous avez une annonce, vous DEVEZ l'utiliser comme fil conducteur de l'icebreaker.

═══════════════════════════════════════════════════════════════════
''' if job_posting_data else ''}

HOOKS IDENTIFIÉS :
{json.dumps(hooks_data, indent=2, ensure_ascii=False)}

NOTRE POSITIONNEMENT ET EXPERTISE :

Cabinet : {COMPANY_INFO['name']}
Mission : {COMPANY_INFO['mission']}

NOS DIFFÉRENCIATEURS (ce qui nous rend uniques) :
{chr(10).join(f"• {d}" for d in COMPANY_INFO['differentiators'])}

PROFILS QUE NOUS RECRUTONS :
{COMPANY_INFO['profiles']}

CLIENTS TYPES :
{COMPANY_INFO['clients']}

VALEUR CLIENT :
{COMPANY_INFO['client_value']}

═══════════════════════════════════════════════════════════════════

🎯 RÈGLE D'OR POUR L'ICEBREAKER :

{COMPANY_INFO['icebreaker_philosophy']}

Le message doit parler de LEURS enjeux (transformation, structuration, 
performance, gouvernance), PAS de notre processus de recrutement.

Notre expertise en recrutement finance critique doit transparaître dans :
✅ La QUALITÉ de notre compréhension de leurs défis
✅ La PERTINENCE de notre analyse de leur contexte
✅ L'INTELLIGENCE de notre question finale

❌ PAS dans une présentation de nos services
❌ PAS dans la proposition de candidats ("j'ai identifié un profil...")
❌ PAS dans un pitch commercial

═══════════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════════
🚫 INTERDICTIONS ABSOLUES - VIOLATIONS GRAVES
═══════════════════════════════════════════════════════════════════

INTERDICTION N°1 : AUTO-PROMOTION ET PITCH COMMERCIAL

❌ JAMAIS écrire :
- "J'ai identifié un profil..."
- "Nous accompagnons des profils..."
- "J'ai isolé deux profils rares..."
- "J'ai sélectionné un candidat..."
- "Nous avons dans notre vivier..."
- "Je dispose d'un expert..."
- "Mon réseau compte des..."

❌ JAMAIS utiliser de closing commercial :
- "Voyez-vous un inconvénient à ce que je vous envoie..."
- "Seriez-vous intéressé par..."
- "Puis-je vous proposer..."
- "Souhaitez-vous que je vous partage..."

✅ À LA PLACE : Poser une question sur LEUR approche stratégique
- "Privilégiez-vous..."
- "Comment arbitrez-vous..."
- "Sur ce type de profil, comment..."

RATIONALE : L'icebreaker n'est PAS un pitch de vente.
C'est une démonstration d'expertise par la QUALITÉ de l'analyse.
Parler de vos candidats = passer de "conseiller expert" à "commercial".

═══════════════════════════════════════════════════════════════════

INTERDICTION N°2 : LONGUEUR EXCESSIVE

❌ JAMAIS dépasser 80 mots (limite STRICTE)
❌ JAMAIS faire des listes à puces dans l'icebreaker
❌ JAMAIS détailler les compétences d'un candidat

✅ À LA PLACE : Synthèse concise en 3 phrases
- Phrase 1 : Salutation + Observation/Hook (25-30 mots)
- Phrase 2 : Insight business (30-35 mots)
- Phrase 3 : Question stratégique (15-20 mots)

RATIONALE : Un icebreaker long = non lu.
La concision démontre la maîtrise du sujet.

═══════════════════════════════════════════════════════════════════

INTERDICTION N°3 : FORMULATIONS FAMILIÈRES

❌ JAMAIS utiliser :
- Points de suspension ("...")
- "Ça veut dire", "tout ça", "du coup"
- "Pensez-vous que cela puisse être pertinent ?"
- Ton trop décontracté

✅ À LA PLACE : Tournures polies et professionnelles
- "J'imagine que..."
- "Je suppose que..."
- "Privilégiez-vous..."
- "Comment orientez-vous..."

RATIONALE : Vous contactez des DAF, CFO, Directeurs.
Le vouvoiement et la courtoisie sont NON NÉGOCIABLES.

═══════════════════════════════════════════════════════════════════

TON REQUIS :

✅ Professionnel et respectueux
✅ Utiliser le vouvoiement systématiquement
✅ Formule de salutation appropriée ("Bonjour [Prénom]")
✅ Tournures interrogatives polies ("je suppose", "j'imagine", "vous privilégiez")
✅ Vocabulaire expert mais accessible

❌ Ton trop décontracté ("ça veut dire", "tout ça")
❌ Points de suspension ("...")
❌ Ton familier ou trop direct
❌ Questions qui ressemblent à des affirmations

═══════════════════════════════════════════════════════════════════

STRUCTURE OBLIGATOIRE (70-80 mots MAXIMUM) :

**PARTIE 1 : Salutation + Accroche avec insight [25-30 mots]**
→ Toujours commencer par "Bonjour [Prénom],"

SI UNE ANNONCE EST DISPONIBLE :
→ Partir de l'annonce comme BASE PRINCIPALE
→ Identifier le défi métier derrière le recrutement
→ Exemple : "recruter un [Profil] capable de [Compétence rare] suppose..."

SI UN HOOK PERTINENT EXISTE (mais pas d'annonce) :
→ ⚠️ VÉRIFIER D'ABORD LA DATE DU HOOK
→ Si le hook date de + de 6 mois : L'IGNORER COMPLÈTEMENT
→ Exemple : "A pris son poste il y a 2 ans" = TROP VIEUX, ignorer
→ Si hook valide : Utiliser + ajouter un INSIGHT BUSINESS LOGIQUE
→ Utiliser le hook + ajouter un INSIGHT BUSINESS LOGIQUE
→ Le lien hook → insight doit être ÉVIDENT et NATUREL
→ NE JAMAIS forcer un lien artificiel

SI AUCUN HOOK OU HOOK TROP FAIBLE :
→ Partir directement du CONTEXTE ENTREPRISE/POSTE
→ Identifier un défi business réel lié à leur fonction

**PARTIE 2 : Défi business spécifique [30-35 mots]**
→ Identifier UN défi concret et réaliste lié au hook ou à l'annonce
→ Être SPÉCIFIQUE avec vocabulaire métier précis
→ Formuler avec politesse ("j'imagine", "je suppose")
→ NE JAMAIS parler de vos candidats ici

**PARTIE 3 : Question stratégique [15-20 mots]**
→ Question qui montre notre expertise
→ Question sur LEUR APPROCHE, jamais sur nos candidats
→ Formulée avec respect ("Privilégiez-vous", "Comment arbitrez-vous")
→ PAS de closing commercial ("Voyez-vous un inconvénient...")

═══════════════════════════════════════════════════════════════════

EXEMPLES EXCELLENTS (10/10) :

═══════════════════════════════════════════════════════════════════

📌 Exemple 1 : Mutuelle agricole (ACPR)
"Bonjour Claire, recruter pour Mutualia un auditeur interne suppose de gérer un grand écart culturel : le marché regorge de profils Big 4 techniquement excellents mais souvent incapables de s'adapter à la réalité du terrain agricole et aux élus mutualistes. Privilégiez-vous le savoir-être quitte à former sur la technique, ou l'expertise reste-t-elle non négociable pour l'ACPR ?"

✅ Pourquoi c'est excellent :
- Insight puissant (grand écart culturel)
- Vocabulaire ultra-précis (ACPR, élus mutualistes)
- Question stratégique (fit vs expertise)
- Zéro auto-promo
- 72 mots

═══════════════════════════════════════════════════════════════════

📌 Exemple 2 : Expansion Afrique
"Bonjour Philippe, l'expansion continue de CFAO en Afrique représente un défi de gouvernance majeur pour votre Audit Interne : maintenir un standard groupe tout en naviguant les spécificités réglementaires locales. Sur vos recrutements actuels, privilégiez-vous des profils issus de Big 4 locaux ou des auditeurs formés aux standards de grands groupes internationaux ?"

✅ Pourquoi c'est excellent :
- Contexte business précis (expansion Afrique)
- Insight sur le dilemme (standard groupe vs local)
- Question binaire claire
- Zéro auto-promo
- 68 mots

═══════════════════════════════════════════════════════════════════

EXEMPLES À REJETER (Auto-promotion) :

═══════════════════════════════════════════════════════════════════

❌ Exemple : Pitch commercial déguisé
"Bonjour Thomas, je sais qu'un poste de Responsable Compta Banque est rare. J'ai identifié un profil Senior qui a cette double casquette : culture audit et Key User SAP. Il pourrait soulager vos équipes instantanément. Voyez-vous un inconvénient à ce que je vous envoie sa synthèse ?"

🚫 Pourquoi c'est MAUVAIS :
- "J'ai identifié un profil" = pitch commercial
- Parle de NOTRE candidat, pas de LEURS enjeux
- Closing commercial ("Voyez-vous un inconvénient")
- Pas de question stratégique
- Violation GRAVE de l'interdiction N°1

❌ Exemple : Hook obsolète utilisé
"Bonjour Thomas, félicitations pour votre nomination en tant que Directeur 
adjoint il y a 3 ans..."

🚫 Pourquoi c'est MAUVAIS :
- Le poste date de 3 ANS (pas récent)
- "Félicitations" pour un événement de 2022 en 2026 = ridicule
- Le hook aurait dû être rejeté par l'extraction
- RÈGLE : Ignorer tout hook de + de 6 mois

✅ VERSION CORRECTE (sans le hook obsolète) :
"Bonjour Thomas, en tant que Directeur adjoint comptabilité chez FUNECAP GROUPE, 
j'imagine que la spécificité du secteur funéraire (gestion des contrats obsèques, 
réglementation sectorielle) complexifie vos recrutements finance. Privilégiez-vous 
des profils avec une expérience sectorielle ou une expertise comptable transverse ?"

═══════════════════════════════════════════════════════════════════

CHECKLIST FINALE (vérifie avant d'envoyer) :

□ Ai-je commencé par "Bonjour [Prénom]," ?
□ Ai-je vouvoyé tout au long du message ?
□ Mon vocabulaire est-il MÉTIER et précis ?
□ Mon insight montre-t-il une vraie compréhension ?
□ Mon défi business est-il CONCRET et RÉALISTE ?
□ Ma question est-elle sur LEUR approche (PAS sur mes candidats) ?
□ Ma question est-elle formulée avec courtoisie ?
□ Ma question démontre-t-elle notre expertise ?
□ Ai-je ZÉRO auto-promo ("j'ai identifié", "nous accompagnons") ?
□ Ai-je ZÉRO closing commercial ("voyez-vous un inconvénient") ?
□ Longueur = 70-80 mots MAXIMUM ?
□ Pas de points de suspension ?
□ Pas de listes à puces ?

═══════════════════════════════════════════════════════════════════

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