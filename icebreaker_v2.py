"""
Script d'automatisation pour générer des icebreakers personnalisés
VERSION CORRIGÉE - Scraping LinkedIn + Recherche Web + Extraction Hooks Optimisée
"""

import gspread
from google.oauth2.service_account import Credentials
import anthropic
from apify_client import ApifyClient
from config import *
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
                'linkedin_url': row.get('linkedin_url', '')
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
            "profileUrls": [linkedin_url],  # ✅ CORRIGÉ
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


def scrape_linkedin_posts(apify_client, linkedin_url):
    """Scrape les 10 derniers posts LinkedIn du profil"""
    print(f"📝 Scraping des posts LinkedIn...")
    
    try:
        run_input = {
            "urls": [linkedin_url],
            "limit": 10
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
            
            # ✅ CORRIGÉ : Limiter à 10 posts maximum
            if len(posts) >= 10:
                break
        
        print(f"   ✅ {len(posts)} post(s) récupéré(s)")
        return posts
        
    except Exception as e:
        print(f"   ⚠️ Erreur scraping posts : {e}")
        return []


def scrape_company_posts(apify_client, company_name):
    """Scrape les 10 derniers posts de l'entreprise"""
    print(f"🏢 Scraping des posts de l'entreprise...")
    
    try:
        company_slug = company_name.lower().replace(' ', '-')
        company_url = f"https://www.linkedin.com/company/{company_slug}"
        
        run_input = {
            "urls": [company_url],
            "limit": 5
        }
        
        print(f"   Scraping posts de : {company_url}")
        
        run = apify_client.actor(APIFY_ACTORS["company_posts"]).call(run_input=run_input)
        
        posts = []
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            posts.append({
                "text": item.get("text", ""),
                "date": item.get("date", "")
            })
            
            # ✅ CORRIGÉ : Limiter à 10 posts maximum
            if len(posts) >= 10:
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
            "profileUrls": [company_url]  # ✅ CORRIGÉ
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
        # Construire une requête stricte pour éviter les homonymes
        query = f'"{first_name} {last_name}" "{company}"'
        if title:
            query += f' "{title}"'
        
        # Limiter aux 2 dernières années
        query += ' after:2023'
        
        print(f"   Requête : {query}")
        
        # Appel API Serper
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
            
            # Filtrer les résultats pour validation anti-homonymes
            filtered_results = []
            for item in results.get('organic', [])[:MAX_SEARCH_RESULTS]:
                # Vérifier que l'entreprise est mentionnée dans le résultat
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
1. **Récence :** Le fait doit dater de MOINS D'UN AN. Priorité absolue aux événements des 3 derniers mois.
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
        
        # Nettoyer la réponse (enlever les ```json si présents)
        hooks_response = hooks_response.replace('```json', '').replace('```', '').strip()
        
        print(f"   ✅ Hooks extraits")
        return hooks_response
        
    except Exception as e:
        print(f"   ❌ Erreur extraction hooks : {e}")
        return "NOT_FOUND"


# ========================================
# PARTIE 5 : GÉNÉRATION ICEBREAKER
# ========================================

def generate_advanced_icebreaker(prospect_data, hooks_json):
    """Génère un icebreaker ultra-personnalisé basé sur les hooks"""
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
    
    # ✅ PROMPT OPTIMISÉ - Avec insight, profondeur ET courtoisie professionnelle
    prompt = f"""Tu es un expert en prospection B2B avec 15 ans d'expérience. Tu dois rédiger un message LinkedIn qui démontre une VRAIE compréhension des enjeux business du prospect, avec un ton PROFESSIONNEL et COURTOIS.

CONTEXTE PROSPECT :
- Prénom : {prospect_data['first_name']}
- Nom : {prospect_data['last_name']}
- Entreprise : {prospect_data['company']}

HOOKS IDENTIFIÉS :
{json.dumps(hooks_data, indent=2, ensure_ascii=False)}

NOTRE EXPERTISE :
- {COMPANY_INFO['name']} : spécialistes du recrutement finance
- Notre valeur : identifier LES bons profils financiers pour chaque contexte

═══════════════════════════════════════════════════════════════════

🎯 OBJECTIF : Expert courtois qui comprend les enjeux (pas un pote ni un vendeur)

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

STRUCTURE OBLIGATOIRE (70-80 mots) :

**PARTIE 1 : Salutation + Accroche avec insight [25-30 mots]**
→ Toujours commencer par "Bonjour [Prénom],"
→ Utiliser le hook + ajouter un INSIGHT sur ce que cela implique
→ Ton professionnel mais pas pompeux

❌ "300 communes partenaires, ça veut dire gérer la scalabilité des process tout en gardant la proximité terrain..."
✅ "Bonjour Julien, 300 communes partenaires représente un beau défi de scalabilité tout en maintenant la proximité opérationnelle."

**PARTIE 2 : Défi business spécifique [30-35 mots]**
→ Identifier UN défi concret et réaliste lié au hook
→ Être SPÉCIFIQUE avec vocabulaire métier précis
→ Formuler avec politesse ("j'imagine", "je suppose")

❌ "Entre la gestion multi-sites et les cycles de facturation publics, je suppose que le profil du DAF/RAF est crucial pour structurer tout ça ?"
✅ "J'imagine qu'entre la gestion multi-sites et les spécificités des cycles de facturation publics, le rôle du DAF/RAF devient structurant."

**PARTIE 3 : Question d'expert courtoise [15-20 mots]**
→ Question qui montre notre expertise
→ Formulée avec respect ("Pourriez-vous", "Vous privilégiez", "Comment")
→ Sur leur APPROCHE, pas leurs besoins

❌ "Vous privilégiez plutôt un profil cabinet conseil ou quelqu'un du public ?"
✅ "Privilégiez-vous plutôt un profil issu du conseil ou du secteur public ?"

═══════════════════════════════════════════════════════════════════

RÈGLES IMPÉRATIVES :

✅ TOUJOURS vouvoyer
✅ Utiliser "Bonjour [Prénom]," en ouverture
✅ Vocabulaire MÉTIER précis (pas du jargon RH)
✅ Tournures polies : "j'imagine", "je suppose", "privilégiez-vous"
✅ Mentionner des défis RÉELS et CONCRETS
✅ Poser une question qui démontre notre expertise
✅ Ton = consultant expert et respectueux

❌ Vocabulaire/formulations interdits :
- Points de suspension ("...")
- "Ça veut dire", "tout ça", "du coup"
- "Nous accompagnons", "Notre expertise", "Nous aidons"
- "Aspects financiers", "enjeux de croissance" (trop vague)
- "Renforcer vos équipes", "gérez-vous ces enjeux"
- Questions trop directes sans formule de politesse

═══════════════════════════════════════════════════════════════════

EXEMPLES EXCELLENTS (ton professionnel et courtois) :

📌 Contexte : Scale-up tech qui lève 20M€

❌ Version trop décontractée : 
"20M€ levés, ça change la donne côté reporting investisseurs... Vous partez plutôt sur un profil scale-up ou grand groupe ?"

✅ Version professionnelle : 
"Bonjour Marc, une levée de 20M€ implique naturellement un renforcement du reporting investisseurs et une structuration du FP&A en vue d'une prochaine levée. J'imagine que le profil du VP Finance devient stratégique dans ce contexte. Privilégiez-vous plutôt une expertise scale-up ou grande entreprise ?"

📌 Contexte : Ouverture de 50 nouvelles agences

❌ Version trop décontractée :
"50 agences en 18 mois, le sujet n'est plus juste le recrutement mais l'industrialisation du modèle financier. Vous privilégiez quel type de profil pour piloter ça ?"

✅ Version professionnelle :
"Bonjour Sarah, 50 agences en 18 mois suppose une industrialisation du modèle financier bien au-delà des enjeux de recrutement classiques. Entre la gestion de trésorerie multi-sites et la consolidation comptable, j'imagine que le profil pour piloter ces sujets est clé. Comment orientez-vous vos recherches sur ce type de poste ?"

📌 Contexte : Certification obtenue / nouveau partenariat

❌ Version trop décontractée :
"La certif ISO change souvent la donne niveau contrôle de gestion. Entre la traçabilité renforcée et les nouveaux KPIs à monitorer, vous avez renforcé l'équipe finance ou c'est géré en interne ?"

✅ Version professionnelle :
"Bonjour Pierre, une certification ISO implique généralement un renforcement du contrôle de gestion, notamment sur les aspects de traçabilité et de suivi des KPIs. J'imagine que cela a pu vous amener à revoir l'organisation de l'équipe finance. Avez-vous privilégié un renforcement interne ou des recrutements externes ?"

═══════════════════════════════════════════════════════════════════

CHECKLIST FINALE (vérifie avant d'envoyer) :

□ Ai-je commencé par "Bonjour [Prénom]," ?
□ Ai-je vouvoyé tout au long du message ?
□ Mon vocabulaire est-il MÉTIER et précis ?
□ Mon insight montre-t-il une vraie compréhension ?
□ Mon défi business est-il CONCRET et RÉALISTE ?
□ Ma question est-elle formulée avec courtoisie ?
□ Ma question démontre-t-elle notre expertise ?
□ Ai-je évité les tournures trop décontractées ?
□ Est-ce que je parle de LEUR réalité (pas de nous) ?
□ Longueur = 70-80 mots ?
□ Pas de points de suspension ?

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
        
        # ✅ CORRIGÉ : Mise à jour en BATCH (1 seul appel API au lieu de 3)
        # Colonnes D, E, F, G, H, I, J, K
        # On met à jour D (linkedin), G (hooks), K (icebreaker)
        values = [[
            linkedin_url,  # D
            "",            # E (vide)
            "",            # F (vide)
            notable,       # G
            "",            # H (vide)
            "",            # I (vide)
            "",            # J (vide)
            icebreaker     # K
        ]]
        
        # Mise à jour en une fois
        range_name = f'D{row_number}:K{row_number}'
        sheet.update(range_name, values)
        
        print(f"   ✅ Mise à jour réussie !\n")
        
    except Exception as e:
        print(f"   ❌ Erreur mise à jour : {e}\n")
        # Logger l'erreur pour debug
        import traceback
        traceback.print_exc()


# ========================================
# FONCTION PRINCIPALE
# ========================================

def main():
    """Fonction principale"""
    print("\n" + "="*80)
    print("🚀 ICEBREAKER AUTOMATION - VERSION CORRIGÉE")
    print("   LinkedIn Scraping + Web Search + Smart Hook Extraction")
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
            
            # 2. Scraping LinkedIn
            profile_data = scrape_linkedin_profile(apify_client, linkedin_url)
            time.sleep(3)
            
            posts_data = scrape_linkedin_posts(apify_client, linkedin_url)
            time.sleep(3)
            
            company_posts = scrape_company_posts(apify_client, prospect['company'])
            time.sleep(3)
            
            company_profile = scrape_company_profile(apify_client, prospect['company'])
            time.sleep(3)
            
            # 3. Recherche Web
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
            
            # 4. Extraction des hooks
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
            
            # 5. Génération icebreaker
            icebreaker = generate_advanced_icebreaker(prospect, hooks_json)
            
            # 6. Mise à jour Google Sheet
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
