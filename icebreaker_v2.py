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
    """Extrait 1-2 hooks pertinents pour l'icebreaker (Limité à 3 mois)"""
    print(f"🎯 Extraction des hooks avec Claude (Filtre strict 3 mois)...")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    data_summary = {
        "profile": {
            "fullName": profile_data.get("fullName", "") if profile_data else "",
            "headline": profile_data.get("headline", "") if profile_data else "",
            "summary": profile_data.get("summary", "") if profile_data else "",
            "location": profile_data.get("location", "") if profile_data else "",
            "current_company": profile_data.get("experiences", [{}])[0].get("companyName", "") if profile_data and profile_data.get("experiences") else "",
            "current_position": profile_data.get("experiences", [{}])[0].get("title", "") if profile_data and profile_data.get("experiences") else "",
            # On conserve les données mais Claude filtrera sur la date
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
    
    # PROMPT MIS À JOUR : CRITÈRE STRICT 3 MOIS
    prompt = f"""# RÔLE
Tu es un analyste en intelligence économique. Ta mission : trouver un prétexte (Hook) pour engager une conversation avec un prospect B2B.

# OBJECTIF
Identifier 1 à 2 faits notables (Hooks) dans les données JSON fournies.

# DONNÉES À ANALYSER
{json.dumps(data_summary, indent=2, ensure_ascii=False)}

# CRITÈRE ABSOLU DE TEMPS : 3 MOIS (90 JOURS)
La règle d'or est la "FRAÎCHEUR". 
Tout événement datant de plus de 3 mois est considéré comme "PÉRIMÉ" et doit être ignoré.

# HIÉRARCHIE DE SÉLECTION (Si < 3 mois uniquement)

1. **Le Prospect a CRÉÉ du contenu (Priorité 1)**
   - Post LinkedIn écrit par lui, Article, Interview.
   - ⚠️  DOIT DATER DE MOINS DE 3 MOIS.

2. **Le Prospect a INTERAGI (Priorité 2)**
   - Like ou Commentaire sur un sujet métier (Finance, Tech, RH, Stratégie).
   - ⚠️  DOIT DATER DE MOINS DE 3 MOIS.

3. **Actu Entreprise (Priorité 3)**
   - Rachat, Levée de fonds, Lancement produit majeur.
   - ⚠️  DOIT DATER DE MOINS DE 3 MOIS.

# CE QUI EST INTERDIT (BLACKLIST)
❌ TOUT ce qui a plus de 3 mois (même si c'est génial, on jette).
❌ Une prise de poste il y a 4 mois = PÉRIMÉ.
❌ Une certification il y a 6 mois = PÉRIMÉ.
❌ Anniversaire, Vœux de bonne année (sauf en janvier).

# FORMAT DE SORTIE (JSON STRICT)
Si AUCUN hook de MOINS DE 3 MOIS n'est trouvé, réponds UNIQUEMENT : "NOT_FOUND"

Sinon, réponds avec ce JSON exact :
{{
  "hook_principal": {{
    "description": "Description concise",
    "type_action": "CREATOR" | "INTERACTOR" | "COMPANY",
    "contexte": "Détails clés",
    "date": "Date approximative",
    "source": "Source",
    "pertinence": 5
   }}
 }}

Réponds UNIQUEMENT avec le JSON. Pas de texte."""

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=1000,
            temperature=0.2, # Température basse pour être rigoureux sur la date
            messages=[{"role": "user", "content": prompt}]
        )
        
        hooks_response = message.content[0].text.strip()
        hooks_response = hooks_response.replace('```json', '').replace('```', '').strip()
        
        print(f"   ✅ Analyse terminée (Filtre 3 mois appliqué)")
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
  Version 2.1 FINALE - Hiérarchie Hook prioritaire + Variantes obligatoires
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

→ Cette annonce révèle le BESOIN EXPLICITE.
''' if job_posting_data else ''}

HOOKS IDENTIFIÉS (posts LinkedIn, commentaires, web) :
{json.dumps(hooks_data, indent=2, ensure_ascii=False)}

NOTRE POSITIONNEMENT :
Cabinet : {COMPANY_INFO['name']}
Expertise : {COMPANY_INFO['mission']}
Profils recrutés : {COMPANY_INFO['profiles']}

═══════════════════════════════════════════════════════════════════
HIÉRARCHIE DE PRIORISATION (OPTION A SÉCURISÉE)
═══════════════════════════════════════════════════════════════════

ORDRE DE PRIORITÉ STRICTE :

1️⃣ SI Hook valide (< 6 mois) + Annonce publique :
   → Structure : Hook (intro) → Lien hook/annonce (insight) → Question
   → Exemple : "Votre webinar EPM... Pour votre recherche de Solution Lead... Privilégiez-vous..."
   
2️⃣ SI Hook valide (< 6 mois) SANS annonce publique :
   → Structure : Hook (intro) → Défi métier GÉNÉRAL (insight) → Question
   → ⚠️ PAS de mention de recrutement spécifique
   → Exemple : "Votre certification CMA... Allier pilotage et stratégie est un vrai défi... Privilégiez-vous..."
   
3️⃣ SI Annonce publique SANS hook :
   → Structure : Annonce (intro) → Défi technique (insight) → Question
   → Exemple : "J'ai consulté votre recherche... Trouver un profil... Privilégiez-vous..."
   
4️⃣ SI ni Hook ni Annonce :
   → Structure : Contexte entreprise (intro) → Défi organisationnel (insight) → Question
   → Exemple : "En tant que DAF chez X... J'imagine qu'allier rigueur et opérationnel... Privilégiez-vous..."

RÈGLE DE SÉLECTION :
Si plusieurs hooks disponibles → Choisir le PLUS FORT (post acteur > certification > podcast > commentaire > post entreprise)

═══════════════════════════════════════════════════════════════════
VARIANTES OBLIGATOIRES (ANTI-RÉPÉTITION)
═══════════════════════════════════════════════════════════════════

🎯 OBJECTIF : Éviter l'effet template en variant les formulations

─────────────────────────────────────────────────────────────────

A) VARIANTES POUR L'INSIGHT (Partie 2)

INTERDICTION : Utiliser toujours "J'imagine que..."

VARIANTES À ALTERNER (répartition cible) :

30% → "Trouver un profil..." (direct)
      Exemple : "Trouver un profil maîtrisant à la fois les traités proportionnels et..."

20% → "J'imagine qu'allier X et Y..." 
      Exemple : "J'imagine qu'allier rigueur ACPR et terrain agricole..."

15% → "[Défi] est un vrai défi/casse-tête"
      Exemple : "Allier agilité et rigueur de consolidation est un vrai défi."

15% → "Le marché dispose de..."
      Exemple : "Le marché dispose d'excellents auditeurs Big 4, mais qui peinent à..."

10% → "Cette tension entre X et Y..."
      Exemple : "Cette tension entre innovation tech et conformité Bâle III..."

10% → "Je suppose que..." / autres variantes
      Exemple : "Je suppose que piloter ce type de projet demande d'allier..."

─────────────────────────────────────────────────────────────────

B) VARIANTES POUR LA QUESTION (Partie 3)

INTERDICTION : Utiliser toujours "Privilégiez-vous..."

VARIANTES À ALTERNER (répartition cible) :

35% → "Privilégiez-vous X ou Y ?"
      Exemple : "Privilégiez-vous des profils Big 4 ou des auditeurs internes ?"

20% → "Cherchez-vous avant tout X ou Y ?"
      Exemple : "Cherchez-vous avant tout un expert capable d'optimiser l'existant ou..."

15% → "Comment arbitrez-vous entre X et Y ?"
      Exemple : "Comment arbitrez-vous entre expertise sectorielle et base comptable solide ?"

15% → "Avez-vous tendance à privilégier X ou Y ?"
      Exemple : "Avez-vous tendance à privilégier le savoir-être quitte à former sur la technique ?"

10% → "Quelle approche privilégiez-vous ?"
      Exemple : "Quelle approche privilégiez-vous : former sur la technique ou recruter l'expertise ?"

5% → Autres variantes contextuelles
      Exemple : "Sur vos recrutements EPM, privilégiez-vous..."

═══════════════════════════════════════════════════════════════════
EXEMPLES D'EXCELLENTS ICEBREAKERS (10/10)
═══════════════════════════════════════════════════════════════════

Ces exemples suivent TOUS le même pattern :
→ Salutation + Observation factuelle
→ Insight business (défi réel) - AVEC VARIANTES
→ Question stratégique - AVEC VARIANTES

─────────────────────────────────────────────────────────────────

EXEMPLE 1 : Post LinkedIn + Secteur spécifique (Agriculture/Mutuelle)
[SCÉNARIO 1 : Hook + Annonce]

CONTEXTE :
- Claire Martin, Directrice Audit Interne, Mutualia
- Hook : Recherche un auditeur interne (annonce)
- Secteur : Mutuelle agricole (ACPR)

ICEBREAKER (75 mots) :
"Bonjour Claire, en lisant votre recherche pour Mutualia, une question me vient : comment gérez-vous le grand écart culturel ? Le marché dispose de nombreux auditeurs excellents techniquement (Big 4, normes strictes), mais qui peinent souvent à s'adapter à la réalité du terrain agricole et aux élus mutualistes. Avez-vous tendance à privilégier le savoir-être (le fit agricole) quitte à former sur la technique, ou l'expertise reste-t-elle non négociable pour l'ACPR ?"

VARIANTES UTILISÉES :
✅ Insight : "Le marché dispose de..." (variante 15%)
✅ Question : "Avez-vous tendance à privilégier..." (variante 15%)

─────────────────────────────────────────────────────────────────

EXEMPLE 2 : Post LinkedIn sur webinar + Contexte EPM/BI
[SCÉNARIO 1 : Hook + Annonce]

CONTEXTE :
- Karine Dubois, Responsable CDG et Outils, GMA
- Hook : A animé un webinar sur l'automatisation EPM (post LinkedIn récent)
- Poste recherché : Solution Lead EPM BI

ICEBREAKER (73 mots) :
"Bonjour Karine, votre webinar sur l'automatisation des flux EPM résonne particulièrement. Trouver un profil maîtrisant à la fois la rigueur du Contrôle de Gestion et l'administration technique de Tagetik ou Essbase est rare sur le marché. Pour votre recherche de Solution Lead EPM BI, cherchez-vous avant tout un expert capable d'optimiser l'existant ou un Project Leader capable de repenser l'architecture ?"

VARIANTES UTILISÉES :
✅ Insight : "Trouver un profil... est rare sur le marché" (variante 30% + marché)
✅ Question : "Cherchez-vous avant tout..." (variante 20%)

─────────────────────────────────────────────────────────────────

EXEMPLE 3 : Expansion internationale + Audit multi-pays
[SCÉNARIO 1 : Hook + Annonce - mais hook = post entreprise]

CONTEXTE :
- Philippe Durand, Directeur Audit Interne, CFAO
- Hook : Post LinkedIn sur expansion en Afrique de l'Ouest
- Contexte : Groupe avec filiales africaines

ICEBREAKER (68 mots) :
"Bonjour Philippe, en voyant l'expansion continue de CFAO en Afrique, je mesure le défi de gouvernance que cela représente pour votre Audit Interne : maintenir un standard groupe tout en naviguant les spécificités réglementaires locales. Sur vos recrutements actuels, privilégiez-vous des profils issus de Big 4 locaux (experts terrain) ou des auditeurs formés aux standards de grands groupes internationaux ?"

VARIANTES UTILISÉES :
✅ Insight : "Je mesure le défi..." (variante autre 10%)
✅ Question : "Privilégiez-vous..." (variante 35% - standard)

─────────────────────────────────────────────────────────────────

EXEMPLE 4 : Vocabulaire ultra-spécialisé (Réassurance)
[SCÉNARIO 3 : Annonce SANS hook]

CONTEXTE :
- Virginie Lemoine, Directrice Comptabilité, Captive de réassurance
- Hook : NOT_FOUND
- Annonce : Recherche Comptable Technique Réassurance

ICEBREAKER (78 mots) :
"Bonjour Virginie, j'ai consulté votre recherche pour le poste de Comptable Technique en Réassurance. Trouver un technicien maîtrisant à la fois les traités (proportionnels et non-pro) et les spécificités d'une captive de réassurance est un vrai défi. La plupart des profils qualifiés sont captifs des grands réassureurs. Privilégiez-vous un expert issu de la réassurance classique ou cherchez-vous un profil déjà rompu aux enjeux Solvabilité II en environnement corporate ?"

VARIANTES UTILISÉES :
✅ Insight : "Trouver un... est un vrai défi" (variante 30% + 15%)
✅ Question : "Privilégiez-vous... ou cherchez-vous..." (mix variantes)

─────────────────────────────────────────────────────────────────

EXEMPLE 5 : Certification récente (post LinkedIn)
[SCÉNARIO 2 : Hook SANS annonce]

CONTEXTE :
- Marc Leblanc, Contrôleur de Gestion, Groupe industriel
- Hook : A obtenu la certification CMA il y a 2 mois (post LinkedIn)
- Annonce : ❌ Aucune annonce publique

ICEBREAKER (72 mots) :
"Bonjour Marc, félicitations pour votre certification CMA récente. Cette expertise résonne particulièrement dans un contexte industriel où la modélisation des coûts se complexifie. Allier pilotage opérationnel et vision stratégique est un vrai défi pour structurer des équipes finance performantes. Comment arbitrez-vous entre recruter cette double compétence ou segmenter les rôles (opérationnel vs stratégique) ?"

VARIANTES UTILISÉES :
✅ Insight : "Allier X et Y est un vrai défi" (variante 15%)
✅ Question : "Comment arbitrez-vous..." (variante 15%)
⚠️ PAS de mention de recrutement spécifique (pas d'annonce)

─────────────────────────────────────────────────────────────────

EXEMPLE 6 : Commentaire LinkedIn sur transformation finance
[SCÉNARIO 2 : Hook SANS annonce]

CONTEXTE :
- Sophie Bernard, DAF, Groupe bancaire régional
- Hook : A commenté un post sur la transformation finance digitale (LinkedIn)
- Annonce : ❌ Aucune annonce publique

ICEBREAKER (77 mots) :
"Bonjour Sophie, votre commentaire sur la transformation digitale de la fonction finance soulève un point clé : l'équilibre entre innovation technologique et conformité réglementaire bancaire. Avec Bâle III et les reporting ACPR, cette tension devient particulièrement critique pour structurer des équipes finance. Quelle approche privilégiez-vous : recruter des profils issus de banques ayant déjà opéré ces transformations ou former des profils plus transverses sur la réglementation ?"

VARIANTES UTILISÉES :
✅ Insight : "Cette tension devient..." (variante 10%)
✅ Question : "Quelle approche privilégiez-vous..." (variante 10%)
⚠️ Formulation générale (pas d'annonce publique)

─────────────────────────────────────────────────────────────────

EXEMPLE 7 : Participation podcast (mention web)
[SCÉNARIO 1 : Hook + Annonce]

CONTEXTE :
- Thomas Dupont, Directeur Consolidation, Groupe coté
- Hook : A participé à un podcast finance "Les Consolideurs" il y a 3 mois (mention web)
- Annonce : Recherche Consolideur Senior

ICEBREAKER (77 mots) :
"Bonjour Thomas, j'ai écouté votre intervention dans le podcast Les Consolideurs sur les défis IFRS 17. Votre analyse sur la complexité des impacts actuariels était particulièrement éclairante. Pour des groupes cotés comme le vôtre, gérer ces sujets techniques tout en tenant les délais de clôture est un vrai casse-tête. Pour votre recherche de Consolideur Senior, privilégiez-vous des profils Big 4 avec forte expertise IFRS ou des consolideurs groupe déjà rompus à vos outils ?"

VARIANTES UTILISÉES :
✅ Insight : "Gérer X et Y est un vrai casse-tête" (variante 15%)
✅ Question : "Privilégiez-vous..." (variante 35% - standard)

─────────────────────────────────────────────────────────────────

EXEMPLE 8 : Post LinkedIn sur outil finance (SAP/Tagetik)
[SCÉNARIO 2 : Hook SANS annonce]

CONTEXTE :
- Isabelle Martin, Responsable Reporting Groupe, Groupe assurance
- Hook : A posté sur LinkedIn sur migration Tagetik il y a 1 mois
- Annonce : ❌ Aucune annonce publique

ICEBREAKER (76 mots) :
"Bonjour Isabelle, votre post sur la migration Tagetik soulève un point crucial : la gestion du changement lors de transformations EPM. Entre résistance des équipes habituées à l'existant et montée en compétence sur le nouvel outil, je suppose que piloter ce type de projet demande d'allier pédagogie et expertise technique. Sur ce genre de transformation, privilégiez-vous des chefs de projet EPM capables de porter la conduite du changement ou des experts Tagetik purs ?"

VARIANTES UTILISÉES :
✅ Insight : "Je suppose que piloter... demande d'allier..." (variante 10%)
✅ Question : "Privilégiez-vous..." (variante 35%)
⚠️ "Sur ce genre de transformation" (général, pas de recrutement)

─────────────────────────────────────────────────────────────────

EXEMPLE 9 : Sans hook (contexte entreprise uniquement)
[SCÉNARIO 4 : Ni hook ni annonce]

CONTEXTE :
- Jean Moreau, Directeur Comptabilité, Groupe funéraire
- Hook : NOT_FOUND (aucun post récent, pas d'annonce)
- Annonce : ❌ Aucune annonce publique
- Contexte : FUNECAP GROUPE (secteur funéraire)

ICEBREAKER (68 mots) :
"Bonjour Jean, en tant que Directeur Comptabilité chez FUNECAP GROUPE, j'imagine qu'allier rigueur comptable et spécificités opérationnelles est un vrai défi pour structurer vos équipes. Privilégiez-vous des profils issus de groupes multi-sites habitués à cette complexité organisationnelle ou des experts comptables purs que vous formez ensuite sur vos spécificités ?"

VARIANTES UTILISÉES :
✅ Insight : "J'imagine qu'allier X et Y est un vrai défi" (variante 20% + 15%)
✅ Question : "Privilégiez-vous..." (variante 35%)

─────────────────────────────────────────────────────────────────

EXEMPLE 10 : Article presse (mention web récente)
[SCÉNARIO 2 : Hook SANS annonce]

CONTEXTE :
- Caroline Petit, CFO, Groupe retail
- Hook : Mentionnée dans Les Échos sur transformation digitale finance (article 2 mois)
- Annonce : ❌ Aucune annonce publique

ICEBREAKER (73 mots) :
"Bonjour Caroline, votre interview dans Les Échos sur la transformation digitale de la fonction finance résonne particulièrement. Vous évoquiez la difficulté à trouver des profils finance alliant rigueur comptable et appétence pour les outils data/BI. Le marché dispose de nombreux profils excellents SOIT en rigueur SOIT en tech, rarement les deux. Cherchez-vous avant tout des profils issus du conseil habitués à ces transformations ou des finance purs avec forte curiosité tech ?"

VARIANTES UTILISÉES :
✅ Insight : "Le marché dispose de... rarement les deux" (variante 15%)
✅ Question : "Cherchez-vous avant tout..." (variante 20%)
⚠️ Formulation générale (pas d'annonce)

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

MAUVAIS EXEMPLE 6 : Pitch commercial déguisé

"Bonjour Roland, j'ai récemment vu vos masterclass sur l'excellence managériale sur LinkedIn, notamment celle avec Isabelle Saladin. Une initiative inspirante pour booster l'engagement des équipes. Chez Aisance, nous aidons les entreprises comme Incentive à intégrer l'IA dans leurs processus pour accélérer l'acquisition client. Auriez-vous un moment pour échanger sur comment cela pourrait caler votre croissance ?"

❌ POURQUOI C'EST MAUVAIS :
- "Chez Aisance, nous aidons..." = pitch commercial pur
- Parle de NOTRE entreprise, pas de LEURS enjeux
- "Auriez-vous un moment pour échanger" = closing de vente
- Aucune question stratégique sur leur approche
- Violation GRAVE : auto-promotion + closing commercial

─────────────────────────────────────────────────────────────────

MAUVAIS EXEMPLE 7 : Répétition systématique ("J'imagine" + "Privilégiez-vous")

"Bonjour Sophie, votre certification récente est intéressante. J'imagine que cela va vous aider. J'imagine que dans votre entreprise, vous avez des défis. J'imagine que recruter est compliqué. Privilégiez-vous des profils avec certification ou sans certification ?"

❌ POURQUOI C'EST MAUVAIS :
- "J'imagine" répété 3 fois (effet robot)
- "Privilégiez-vous" = formulation systématique
- Aucune variante = détecté comme template
- Violation : répétition mécanique

─────────────────────────────────────────────────────────────────

MAUVAIS EXEMPLE 8 : Formulations lourdes (93 mots)

"Bonjour Yasmine, félicitations pour votre certification SAFe® 6 Agilist récemment obtenue. Cette expertise en méthodologie agile résonne particulièrement dans le contexte de votre recherche d'un Consolidation & Reporting EPM Configuration Specialist. Allier agilité et rigueur des processus de consolidation suppose des profils capables de naviguer entre flexibilité méthodologique et contraintes réglementaires strictes. Dans votre approche de recrutement, privilégiez-vous des candidats déjà formés aux méthodes agiles ou des experts EPM purs que vous accompagnez ensuite sur cette transformation culturelle ?"

❌ POURQUOI C'EST MAUVAIS :
- 93 mots (13 mots de trop)
- "suppose des profils capables de" = 5 mots inutiles
- "Dans votre approche de recrutement" = lourd
- "naviguer entre" = alambiqué
- Violation : formulations lourdes

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

🚫 INTERDICTION ABSOLUE N°4 : RÉPÉTITION MÉCANIQUE

JAMAIS utiliser systématiquement les mêmes formulations :
❌ "J'imagine que..." dans TOUS les messages
❌ "Privilégiez-vous..." dans TOUS les messages

→ OBLIGATOIRE : Varier selon la matrice de variabilité (voir section VARIANTES)

─────────────────────────────────────────────────────────────────

✅ RÈGLE DE LONGUEUR STRICTE

LONGUEUR STRICTE : 68-80 mots

ADAPTATION PAR COMPLEXITÉ :
- Poste simple (Comptable Général) → 68-72 mots
- Poste technique (Contrôleur de Gestion) → 73-77 mots
- Poste très complexe (Solution Lead EPM, Réassurance, Audit multi-pays) → 78-80 mots MAX

LIMITE ABSOLUE : 80 mots MAXIMUM (au-delà = ÉCHEC de concision)

RATIONALE : Un icebreaker de 75 mots bien écrit convertit mieux qu'un de 93 mots dilué.
La concision force la précision et maintient l'attention du lecteur.

─────────────────────────────────────────────────────────────────

✅ CONCISION MAXIMALE

INTERDICTIONS DE FORMULATIONS LOURDES :

❌ "suppose des profils capables de" 
✅ "est un vrai défi"

❌ "Dans votre approche de recrutement, privilégiez-vous" 
✅ "Privilégiez-vous"

❌ "Dans votre stratégie de, privilégiez-vous"
✅ "Privilégiez-vous"

❌ "Sur vos recrutements actuels, privilégiez-vous"
✅ "Privilégiez-vous"

❌ "j'imagine que chez [Entreprise], l'équilibre entre X et Y suppose" 
✅ "J'imagine qu'allier X et Y"

❌ "qui sont souvent incapables de" 
✅ "qui peinent souvent à"

❌ "naviguer entre flexibilité et rigueur"
✅ "allier flexibilité et rigueur"

RÈGLE D'OR DE CONCISION :
Chaque phrase doit être DIRECTE. Supprimer tous les mots de liaison inutiles.
Aller DROIT AU BUT. Pas de subordonnées multiples.

─────────────────────────────────────────────────────────────────

✅ STRUCTURE OBLIGATOIRE (3 TEMPS)

PARTIE 1 : Salutation + Observation/Hook [22-30 mots]
→ "Bonjour [Prénom],"
→ SI hook récent (< 6 mois) : l'utiliser
→ SI annonce SANS hook : partir de l'annonce
→ SI aucun hook ni annonce : partir du contexte entreprise/fonction

PARTIE 2 : Insight business (défi réel) [28-38 mots]
→ Identifier UN défi concret et réaliste
→ Vocabulaire métier précis
→ VARIANTES OBLIGATOIRES (voir matrice de variabilité)
→ JAMAIS parler de nos candidats
→ SI annonce ET hook : mentionner l'annonce dans cette partie ("Pour votre recherche de...")
→ SI hook SANS annonce : rester sur défi général (PAS de mention de recrutement)

PARTIE 3 : Question stratégique [12-18 mots]
→ Question sur LEUR APPROCHE (pas sur nos services)
→ VARIANTES OBLIGATOIRES (voir matrice de variabilité)
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

ÉTAPE 1 : ANALYSER LES DONNÉES ET DÉTERMINER LE SCÉNARIO

A. Y a-t-il un hook valide (< 6 mois) ?
   → OUI : Aller en B
   → NON : Aller en C

B. Y a-t-il une annonce publique ?
   → OUI : SCÉNARIO 1 (Hook + Annonce)
   → NON : SCÉNARIO 2 (Hook SANS annonce)

C. Y a-t-il une annonce publique ?
   → OUI : SCÉNARIO 3 (Annonce SANS hook)
   → NON : SCÉNARIO 4 (Ni hook ni annonce)

D. Quel est le niveau de complexité du poste ?
   → Simple : 68-72 mots
   → Technique : 73-77 mots
   → Complexe : 78-80 mots

ÉTAPE 2 : CHOISIR LE BON PATTERN

Regarder les 10 exemples excellents ci-dessus et choisir celui qui correspond au SCÉNARIO identifié :

SCÉNARIO 1 (Hook + Annonce) → Exemples 1, 2, 3, 7
SCÉNARIO 2 (Hook SANS annonce) → Exemples 5, 6, 8, 10
SCÉNARIO 3 (Annonce SANS hook) → Exemple 4
SCÉNARIO 4 (Ni hook ni annonce) → Exemple 9

ÉTAPE 3 : SÉLECTIONNER LES VARIANTES À UTILISER

IMPORTANT : Ne PAS utiliser systématiquement "J'imagine que..." + "Privilégiez-vous..."

A. Choisir UNE variante pour l'insight (Partie 2) :
   - 30% chance → "Trouver un profil..."
   - 20% chance → "J'imagine qu'allier..."
   - 15% chance → "[Défi] est un vrai défi/casse-tête"
   - 15% chance → "Le marché dispose de..."
   - 10% chance → "Cette tension entre..."
   - 10% chance → Autre variante

B. Choisir UNE variante pour la question (Partie 3) :
   - 35% chance → "Privilégiez-vous X ou Y ?"
   - 20% chance → "Cherchez-vous avant tout X ou Y ?"
   - 15% chance → "Comment arbitrez-vous entre X et Y ?"
   - 15% chance → "Avez-vous tendance à privilégier X ou Y ?"
   - 10% chance → "Quelle approche privilégiez-vous ?"
   - 5% chance → Autre variante contextuelle

ÉTAPE 4 : RÉDIGER EN SUIVANT LE PATTERN + VARIANTES

- Reprendre la STRUCTURE EXACTE du scénario
- Adapter le VOCABULAIRE au secteur (banque/assurance/finance/audit)
- APPLIQUER LES VARIANTES sélectionnées (PAS de répétition mécanique)
- APPLIQUER LA CONCISION MAXIMALE (supprimer formulations lourdes)
- Vérifier la LONGUEUR (68-80 mots MAX)
- Vérifier ZÉRO auto-promo
- Vérifier ZÉRO invention sectorielle

ÉTAPE 5 : AUTO-VÉRIFICATION STRICTE

CHECKLIST OBLIGATOIRE :

□ Scénario correctement identifié (1/2/3/4) ?
□ Longueur = 68-80 mots ? (PAS 85, PAS 93)
□ Ai-je utilisé "suppose des profils capables de" ? → SUPPRIMER et remplacer par "est un vrai défi"
□ Ai-je utilisé "Dans votre approche de recrutement" ? → SUPPRIMER, commencer direct
□ Ai-je utilisé "Dans votre stratégie de" ? → SUPPRIMER
□ Ai-je VARIÉ les formulations (pas "J'imagine" + "Privilégiez-vous" systématiques) ?
□ Chaque phrase est-elle DIRECTE (pas de subordonnées multiples) ?
□ Vocabulaire ultra-précis ? (Big 4, ACPR, Tagetik, Bâle III - pas "standards", "outils")
□ Question finale COURTE (12-18 mots max) ?
□ Question finale utilise UNE VARIANTE (pas toujours "Privilégiez-vous") ?
□ Ai-je commencé par "Bonjour [Prénom]," ?
□ Ai-je vouvoyé tout au long ?
□ Mon insight est-il factuel (pas inventé) ?
□ SCÉNARIO 1 : Hook en intro + annonce mentionnée dans insight ?
□ SCÉNARIO 2 : Hook en intro + ZÉRO mention de recrutement spécifique ?
□ SCÉNARIO 3 : Annonce en intro + défi technique ?
□ SCÉNARIO 4 : Contexte entreprise + défi organisationnel ?
□ Ma question porte-t-elle sur LEUR approche (pas nos services) ?
□ Ai-je ZÉRO auto-promo ?
□ Ai-je ZÉRO closing commercial ?
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