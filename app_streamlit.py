"""
═══════════════════════════════════════════════════════════════════
APP STREAMLIT V28.8 - LINKEDIN AUTO + COPIER-COLLER POUR LE RESTE
═══════════════════════════════════════════════════════════════════
- URLs fiches de poste depuis Leonar (custom_text_1) ou manuelles
- LinkedIn Jobs : scraping automatique
- Indeed/HelloWork/Apec : copier-coller (JS non supporté)
- Messages injectés dans custom_variable_1/2/3 (séquence auto)
- Backup dans notes (lisible)
- Pagination Leonar (récupère tous les prospects)
═══════════════════════════════════════════════════════════════════
"""

import streamlit as st
import requests
import os
import re
import json
import time
import anthropic
from datetime import datetime, timedelta
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from cv_generator import generate_cv_content, estimate_cv_length, condense_cv_content
from cv_templates import create_cv_pdf
from google_drive_uploader import upload_cv
from message_cv_sequence import generate_sequence_with_cv, generate_subject_lines_cv

load_dotenv()

# ========================================
# CONFIGURATION
# ========================================

st.set_page_config(page_title="Icebreaker Generator V28.7", page_icon="🎯", layout="wide")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

try:
    LEONAR_EMAIL = st.secrets["LEONAR_EMAIL"]
    LEONAR_PASSWORD = st.secrets["LEONAR_PASSWORD"]
    LEONAR_CAMPAIGN_ID = st.secrets["LEONAR_CAMPAIGN_ID"]
except:
    LEONAR_EMAIL = os.getenv("LEONAR_EMAIL")
    LEONAR_PASSWORD = os.getenv("LEONAR_PASSWORD")
    LEONAR_CAMPAIGN_ID = os.getenv("LEONAR_CAMPAIGN_ID")

PROCESSED_FILE = "processed_prospects.txt"

# Session state
if 'leonar_prospects' not in st.session_state:
    st.session_state.leonar_prospects = []
if 'generation_stats' not in st.session_state:
    st.session_state.generation_stats = {'calls': 0, 'tokens': 0, 'cost': 0}


# ========================================
# LEONAR API
# ========================================

def get_leonar_token():
    """Obtient un token d'authentification Leonar"""
    try:
        r = requests.post(
            'https://dashboard.leonar.app/api/1.1/wf/auth',
            json={"email": LEONAR_EMAIL, "password": LEONAR_PASSWORD},
            timeout=10
        )
        return r.json()['response']['token'] if r.status_code == 200 else None
    except:
        return None


def get_new_prospects_leonar(token):
    """Récupère les nouveaux prospects depuis Leonar (avec pagination)"""
    try:
        all_prospects = []
        cursor = 0
        page = 1
        
        # Paginer pour récupérer TOUS les prospects
        while True:
            url = f'https://dashboard.leonar.app/api/1.1/obj/matching?constraints=[{{"key":"campaign","constraint_type":"equals","value":"{LEONAR_CAMPAIGN_ID}"}}]&cursor={cursor}&limit=100'
            
            r = requests.get(
                url,
                headers={'Authorization': f'Bearer {token}'},
                timeout=15
            )
            
            if r.status_code != 200:
                st.error(f"❌ Leonar API erreur: status {r.status_code}")
                break
            
            data = r.json()
            results = data.get('response', {}).get('results', [])
            remaining = data.get('response', {}).get('remaining', 0)
            
            all_prospects.extend(results)
            st.info(f"📊 Page {page}: {len(results)} prospects (total: {len(all_prospects)}, remaining: {remaining})")
            
            # S'il n'y a plus de résultats, arrêter
            if not results or remaining == 0:
                break
            
            # Passer à la page suivante
            cursor += len(results)
            page += 1
            
            # Sécurité : max 10 pages (1000 prospects)
            if page > 10:
                st.warning("⚠️ Limite de 1000 prospects atteinte")
                break
        
        st.info(f"📊 Debug: {len(all_prospects)} prospects TOTAL trouvés dans Leonar")
        
        processed = load_processed()
        st.info(f"📊 Debug: {len(processed)} prospects déjà traités dans le fichier")
        
        # Filtrer
        filtered = []
        for p in all_prospects:
            pid = p['_id']
            notes = p.get('notes', '')
            
            if pid in processed:
                continue  # Déjà traité (fichier local)
            
            if notes and len(notes) >= 100 and 'MESSAGE 1' in notes:
                continue  # Déjà traité (notes Leonar)
            
            filtered.append(p)
        
        st.success(f"✅ {len(filtered)} prospects à traiter après filtrage")
        return filtered
        
    except Exception as e:
        st.error(f"Erreur Leonar: {e}")
        return []


def update_prospect_leonar(token, prospect_id, sequence_data):
    """Met à jour le prospect dans Leonar avec la séquence générée"""
    try:
        # Backup dans les notes (lisible)
        formatted_notes = f"""═══════════════════════════════════════════════════════════════
OBJETS SUGGÉRÉS
═══════════════════════════════════════════════════════════════

{sequence_data.get('subject_lines', '')}

═══════════════════════════════════════════════════════════════
MESSAGE 1 (ICEBREAKER - J+0)
═══════════════════════════════════════════════════════════════

{sequence_data.get('message_1', '')}

═══════════════════════════════════════════════════════════════
MESSAGE 2 (LA PROPOSITION - J+5)
═══════════════════════════════════════════════════════════════

{sequence_data.get('message_2', '')}

═══════════════════════════════════════════════════════════════
MESSAGE 3 (BREAK-UP - J+12)
═══════════════════════════════════════════════════════════════

{sequence_data.get('message_3', '')}

═══════════════════════════════════════════════════════════════"""

        # Envoi : notes (backup) + custom_variables (séquence auto)
        requests.patch(
            f'https://dashboard.leonar.app/api/1.1/obj/matching/{prospect_id}',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={
                "notes": formatted_notes,
                "custom_variable_1": sequence_data.get('message_1', ''),
                "custom_variable_2": sequence_data.get('message_2', ''),
                "custom_variable_3": sequence_data.get('message_3', '')
            },
            timeout=10
        )
        return True
    except:
        return False


def load_processed():
    """Charge la liste des prospects déjà traités"""
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f:
            return set(f.read().splitlines())
    return set()


def save_processed(pid):
    """Sauvegarde un prospect comme traité"""
    with open(PROCESSED_FILE, 'a') as f:
        f.write(f"{pid}\n")


# ========================================
# APIFY - SCRAPING LINKEDIN
# ========================================

def init_apify_client():
    """Initialise le client Apify"""
    from apify_client import ApifyClient
    if not APIFY_API_TOKEN:
        raise ValueError("APIFY_API_TOKEN manquant")
    return ApifyClient(APIFY_API_TOKEN)


def scrape_linkedin_profile(apify_client, linkedin_url):
    """Scrape un profil LinkedIn"""
    try:
        run = apify_client.actor("dev_fusion/Linkedin-Profile-Scraper").call(
            run_input={"profileUrls": [linkedin_url]}
        )
        items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())
        return items[0] if items else {}
    except:
        return {}


def scrape_linkedin_posts(apify_client, linkedin_url):
    """Scrape les posts LinkedIn"""
    try:
        run = apify_client.actor("supreme_coder/linkedin-post").call(
            run_input={
                "deepScrape": True,
                "limitPerSource": 10,
                "rawData": False,
                "urls": [linkedin_url]
            }
        )
        items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())
        # Filtre strict 6 mois
        return filter_recent_posts(items, max_age_months=6)
    except:
        return []


def filter_recent_posts(posts, max_age_months=6):
    """
    Filtre les posts < 6 mois
    Si date non parsable → on INCLUT le post (moins strict)
    """
    if not posts:
        return []
    
    cutoff = datetime.now() - timedelta(days=max_age_months * 30)
    recent = []
    
    for post in posts:
        if not isinstance(post, dict):
            continue
        
        # Récupérer la date - chercher TOUS les champs possibles
        date_str = (
            post.get('date') or 
            post.get('postedDate') or 
            post.get('postedAt') or
            post.get('timestamp') or
            post.get('publishedAt') or
            post.get('time') or
            post.get('posted') or
            post.get('datePosted') or
            ''
        )
        
        # Si pas de date trouvée, on INCLUT quand même le post
        # (approche permissive - mieux vaut un post potentiellement vieux qu'aucun post)
        if not date_str:
            recent.append(post)
            continue
        
        # Parser la date
        post_date = parse_date(date_str)
        
        # Si parsing échoue, on inclut quand même
        if post_date is None:
            recent.append(post)
            continue
        
        # Si date récente, on inclut
        if post_date >= cutoff:
            recent.append(post)
    
    return recent[:5]


def parse_date(date_str):
    """Parse une date avec plusieurs formats"""
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # Formats standards
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%fZ',
        '%Y-%m-%dT%H:%M:%SZ',
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%Y/%m/%d',
        '%B %d, %Y',
        '%b %d, %Y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str[:19], fmt)
        except:
            continue
    
    # Dates relatives ("2d ago", "3w ago", "il y a 2 jours")
    return parse_relative_date(date_str)


def parse_relative_date(date_str):
    """Parse les dates relatives - formats LinkedIn et autres"""
    if not date_str:
        return None
    
    date_str = date_str.lower().strip()
    now = datetime.now()
    
    # Patterns anglais et français
    patterns = [
        # Anglais complet
        (r'(\d+)\s*d(?:ay)?s?\s*ago', 'days'),
        (r'(\d+)\s*w(?:eek)?s?\s*ago', 'weeks'),
        (r'(\d+)\s*mo(?:nth)?s?\s*ago', 'months'),
        (r'(\d+)\s*h(?:our)?s?\s*ago', 'hours'),
        (r'(\d+)\s*yr?s?\s*ago', 'years'),
        # Anglais court (LinkedIn style: "1d", "2w", "3mo")
        (r'^(\d+)d$', 'days'),
        (r'^(\d+)w$', 'weeks'),
        (r'^(\d+)mo$', 'months'),
        (r'^(\d+)h$', 'hours'),
        (r'^(\d+)yr?$', 'years'),
        # Avec espace
        (r'(\d+)\s*d\b', 'days'),
        (r'(\d+)\s*w\b', 'weeks'),
        (r'(\d+)\s*mo\b', 'months'),
        (r'(\d+)\s*h\b', 'hours'),
        # Français
        (r'il y a (\d+)\s*jour', 'days'),
        (r'il y a (\d+)\s*semaine', 'weeks'),
        (r'il y a (\d+)\s*mois', 'months'),
        (r'il y a (\d+)\s*heure', 'hours'),
        (r'il y a (\d+)\s*an', 'years'),
        # "posted X days ago"
        (r'posted\s*(\d+)\s*d', 'days'),
        (r'posted\s*(\d+)\s*w', 'weeks'),
        (r'posted\s*(\d+)\s*mo', 'months'),
        # "X days" sans "ago"
        (r'^(\d+)\s*days?$', 'days'),
        (r'^(\d+)\s*weeks?$', 'weeks'),
        (r'^(\d+)\s*months?$', 'months'),
    ]
    
    for pattern, unit in patterns:
        match = re.search(pattern, date_str)
        if match:
            value = int(match.group(1))
            if unit == 'hours':
                return now - timedelta(hours=value)
            elif unit == 'days':
                return now - timedelta(days=value)
            elif unit == 'weeks':
                return now - timedelta(weeks=value)
            elif unit == 'months':
                return now - timedelta(days=value * 30)
            elif unit == 'years':
                return now - timedelta(days=value * 365)
    
    return None


# ========================================
# SCRAPING WEB (SERPER)
# ========================================

def search_web_prospect(full_name, company_name):
    """
    Recherche web sur le prospect via Serper
    Retourne les résultats récents (<6 mois)
    """
    if not SERPER_API_KEY:
        return []
    
    try:
        # Recherche actualités récentes
        query = f'"{full_name}" "{company_name}" OR "{full_name}" finance'
        
        response = requests.post(
            'https://google.serper.dev/search',
            headers={
                'X-API-KEY': SERPER_API_KEY,
                'Content-Type': 'application/json'
            },
            json={
                'q': query,
                'num': 10,
                'tbs': 'qdr:m6'  # Derniers 6 mois
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        results = []
        
        # Organic results
        for item in data.get('organic', [])[:5]:
            results.append({
                'title': item.get('title', ''),
                'snippet': item.get('snippet', ''),
                'link': item.get('link', ''),
                'type': 'web'
            })
        
        # News results (souvent plus récents)
        for item in data.get('news', [])[:3]:
            results.append({
                'title': item.get('title', ''),
                'snippet': item.get('snippet', ''),
                'link': item.get('link', ''),
                'date': item.get('date', ''),
                'type': 'news'
            })
        
        return results
        
    except Exception as e:
        print(f"Erreur Serper: {e}")
        return []


# ========================================
# SCRAPING FICHE DE POSTE - MULTI-SITES
# ========================================

def scrape_job_posting(url):
    """
    Scrape une fiche de poste depuis différents job boards
    Supporte : HelloWork, LinkedIn, Apec, Indeed, générique
    """
    if not url or not url.strip():
        return None
    
    url = url.strip()
    
    try:
        if "hellowork.com" in url:
            return scrape_hellowork_apify(url)
        elif "linkedin.com/jobs" in url:
            return scrape_linkedin_job(url)
        elif "apec.fr" in url:
            return scrape_apec(url)
        elif "indeed.com" in url or "indeed.fr" in url:
            return scrape_indeed_apify(url)
        else:
            return scrape_generic(url)
    except Exception as e:
        print(f"Erreur scraping: {e}")
        return scrape_generic(url)


# ========================================
# NOUVEAU : SCRAPING APIFY POUR HELLOWORK/INDEED
# ========================================

def scrape_hellowork_apify(url):
    """
    HelloWork : pas de scraper Apify fiable pour URL directe
    Retourne None pour déclencher le fallback copier-coller
    """
    # Les scrapers HelloWork Apify sont conçus pour des recherches, pas des URLs directes
    # On retourne None pour que l'UI demande le copier-coller
    print("HelloWork: scraping auto non supporté, utiliser copier-coller")
    return None


def scrape_indeed_apify(url):
    """
    Indeed : pas de scraper Apify fiable pour URL directe
    Retourne None pour déclencher le fallback copier-coller
    """
    print("Indeed: scraping auto non supporté, utiliser copier-coller")
    return None


def extract_title_from_text(text):
    """Extrait le titre depuis le contenu textuel"""
    if not text:
        return "[Poste]"
    
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        # Chercher une ligne qui ressemble à un titre de poste
        if line and 10 < len(line) < 150:
            # Éviter les lignes trop génériques
            if not any(skip in line.lower() for skip in ['cookie', 'accept', 'menu', 'navigation', 'connexion', 'login']):
                # Nettoyer H/F
                title = re.sub(r'\s*\(?[HhFf]\s*[/\-]\s*[HhFfMm]\)?', '', line)
                return title.strip()
    
    return "[Poste]"


# Fallback : scraping basique (sans JS)
def scrape_hellowork_basic(url):
    """Scrape HelloWork - Fallback sans Apify"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Titre - plusieurs sélecteurs possibles
        title = ""
        for selector in ['h1.tw-text-3xl', 'h1[data-cy="job-title"]', 'h1']:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                break
        
        # Description - chercher dans plusieurs conteneurs
        description = ""
        for selector in ['div[data-cy="job-description"]', 'div.job-description', 'div.description', 'article', 'main']:
            elem = soup.select_one(selector)
            if elem:
                description = elem.get_text(separator='\n', strip=True)
                if len(description) > 200:
                    break
        
        # Fallback : tous les paragraphes
        if len(description) < 200:
            paragraphs = soup.find_all(['p', 'li'])
            description = '\n'.join([p.get_text(strip=True) for p in paragraphs])
        
        if len(description) < 100:
            return None  # Pas assez de contenu
        
        return {
            'title': title[:200],
            'description': description[:4000],
            'source': 'HelloWork',
            'url': url
        }
    except:
        return None


def scrape_indeed_basic(url):
    """Scrape Indeed - Fallback sans Apify"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Titre
        title = ""
        for selector in ['h1.jobsearch-JobInfoHeader-title', 'h1[data-testid="jobTitle"]', 'h1']:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                break
        
        # Description
        description = ""
        for selector in ['div#jobDescriptionText', 'div.jobsearch-jobDescriptionText', 'div[data-testid="jobDescription"]']:
            elem = soup.select_one(selector)
            if elem:
                description = elem.get_text(separator='\n', strip=True)
                break
        
        if len(description) < 100:
            return None  # Pas assez de contenu
        
        return {
            'title': title[:200],
            'description': description[:4000],
            'source': 'Indeed',
            'url': url
        }
    except:
        return None


def scrape_linkedin_job(url):
    """Scrape LinkedIn Jobs"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return scrape_generic(url)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Titre
        title = ""
        for selector in ['h1.top-card-layout__title', 'h1.topcard__title', 'h1']:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                break
        
        # Description
        description = ""
        for selector in ['div.show-more-less-html__markup', 'div.description__text', 'div.job-description']:
            elem = soup.select_one(selector)
            if elem:
                description = elem.get_text(separator='\n', strip=True)
                break
        
        return {
            'title': title[:200],
            'description': description[:4000],
            'source': 'LinkedIn',
            'url': url
        }
    except:
        return scrape_generic(url)


def scrape_apec(url):
    """Scrape Apec"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'fr-FR,fr;q=0.9',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return scrape_generic(url)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Titre
        title = ""
        for selector in ['h1[data-cy="offerTitle"]', 'h1.offer-title', 'h1']:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                break
        
        # Description - Apec structure spécifique
        description = ""
        
        # Chercher les sections de contenu
        content_sections = soup.select('div.offer-description, div.job-description, section.description, div[class*="description"]')
        for section in content_sections:
            text = section.get_text(separator='\n', strip=True)
            if len(text) > len(description):
                description = text
        
        # Fallback
        if len(description) < 200:
            main_content = soup.select_one('main') or soup.select_one('article')
            if main_content:
                description = main_content.get_text(separator='\n', strip=True)
        
        return {
            'title': title[:200],
            'description': description[:4000],
            'source': 'Apec',
            'url': url
        }
    except:
        return scrape_generic(url)


def scrape_generic(url):
    """Scraping générique pour sites non supportés"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Supprimer scripts et styles
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        
        # Titre
        title = ""
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
        
        # Description - prendre le contenu principal
        description = ""
        
        # Chercher le contenu principal
        main = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile('content|description|job', re.I))
        if main:
            description = main.get_text(separator='\n', strip=True)
        else:
            # Fallback : tous les paragraphes
            paragraphs = soup.find_all(['p', 'li'])
            description = '\n'.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
        
        return {
            'title': title[:200],
            'description': description[:4000],
            'source': 'Generic',
            'url': url
        }
    except Exception as e:
        print(f"Erreur scraping générique: {e}")
        return None


# ========================================
# GÉNÉRATION V28 - UN SEUL APPEL CLAUDE
# ========================================

def generate_sequence_v28(prospect_data, posts_data, web_data, job_posting_data):
    """
    Génère M1 + M2 en UN SEUL appel Claude
    Intègre posts LinkedIn + résultats web
    """
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Extraire données
    prenom = get_firstname(prospect_data)
    titre_poste = get_job_title(job_posting_data)
    
    # Formater pour le prompt
    posts_formatted = format_posts(posts_data)
    web_formatted = format_web_results(web_data)
    profile_formatted = format_profile(prospect_data)
    fiche_formatted = job_posting_data.get('description', '') if job_posting_data else ''
    
    prompt = f"""Tu es chasseur de têtes Finance chez Entourage Recrutement.
Tu dois générer 2 messages de prospection pour ce prospect.

═══════════════════════════════════════════════════════════════════
DONNÉES PROSPECT
═══════════════════════════════════════════════════════════════════
{profile_formatted}

═══════════════════════════════════════════════════════════════════
POSTS LINKEDIN RÉCENTS (<6 mois uniquement)
═══════════════════════════════════════════════════════════════════
{posts_formatted}

═══════════════════════════════════════════════════════════════════
ACTUALITÉS WEB RÉCENTES (<6 mois uniquement)
═══════════════════════════════════════════════════════════════════
{web_formatted}

═══════════════════════════════════════════════════════════════════
FICHE DE POSTE : {titre_poste}
═══════════════════════════════════════════════════════════════════
{fiche_formatted[:2500]}

═══════════════════════════════════════════════════════════════════
GÉNÈRE LES 2 MESSAGES
═══════════════════════════════════════════════════════════════════

**MESSAGE 1 (Icebreaker)** - Structure EXACTE :

Bonjour {prenom},

[HOOK - CHOISIS UNE OPTION - PRIORITÉ AUX INFOS RÉCENTES :]
Option A (si un post LinkedIn OU une actualité web est pertinente) : 
  Référence personnalisée (sujet PRÉCIS, événement, publication, nomination...)
  Puis transition vers le poste.
Option B (si aucune info récente pertinente) :
  "Je vous contacte concernant votre recherche de {titre_poste}."

[PAIN POINT #1]
Identifie LA difficulté principale de ce recrutement avec le VOCABULAIRE EXACT de la fiche.
Mentionne les compétences RARES demandées (réassurance, consolidation IFRS, provisions techniques, etc.)
PAS de généralités ("rigueur", "agilité", "dynamisme").

Quels sont les principaux écarts que vous observez entre vos attentes et les profils rencontrés ?

Bien à vous,

---

**MESSAGE 2 (Relance avec profils)** - Structure EXACTE :

Bonjour {prenom},

Je me permets de vous relancer concernant votre recherche de {titre_poste}.

[PAIN POINT #2 - DIFFÉRENT DE M1]
Autre angle sur une AUTRE difficulté, autres compétences de la fiche.

J'ai identifié 2 profils qui pourraient retenir votre attention :

- L'un [PROFIL 1 : spécialiste avec compétences EXACTES de la fiche, expérience cohérente]

- L'autre [PROFIL 2 : parcours DIFFÉRENT mais pertinent, PAS "Big 4" par défaut]

Seriez-vous d'accord pour recevoir leurs synthèses anonymisées ?

Bien à vous,

═══════════════════════════════════════════════════════════════════
INTERDICTIONS ABSOLUES
═══════════════════════════════════════════════════════════════════
❌ "Je travaille sur...", "Je travaille actuellement..."
❌ "rigueur", "agilité", "dynamisme", "dynamique", "croissance"
❌ Inventer des compétences/certifications NON dans la fiche
❌ Répéter le MÊME pain point entre M1 et M2
❌ Utiliser des informations datant de plus de 6 mois
❌ Profils incohérents avec la fiche

═══════════════════════════════════════════════════════════════════
FORMAT DE RÉPONSE
═══════════════════════════════════════════════════════════════════
---MESSAGE_1---
[contenu message 1]
---MESSAGE_2---
[contenu message 2]
"""

    try:
        # Retry avec backoff exponentiel pour rate limit
        max_retries = 3
        base_delay = 30  # secondes
        
        for attempt in range(max_retries):
            try:
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1500,
                    messages=[{"role": "user", "content": prompt}]
                )
                break  # Succès, sortir de la boucle
            except anthropic.RateLimitError as e:
                if attempt < max_retries - 1:
                    wait_time = base_delay * (2 ** attempt)  # 30s, 60s, 120s
                    st.warning(f"⏳ Rate limit atteint. Attente {wait_time}s avant retry ({attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    raise e  # Dernière tentative échouée, propager l'erreur
        
        # Stats
        st.session_state.generation_stats['calls'] += 1
        st.session_state.generation_stats['tokens'] += message.usage.input_tokens + message.usage.output_tokens
        st.session_state.generation_stats['cost'] += (message.usage.input_tokens * 0.003 + message.usage.output_tokens * 0.015) / 1000
        
        result = message.content[0].text.strip()
        m1, m2 = parse_messages(result)
        m3 = generate_message_3(prenom)
        subject_lines = generate_subject_lines(titre_poste)
        
        return {
            'subject_lines': subject_lines,
            'message_1': m1,
            'message_2': m2,
            'message_3': m3
        }
        
    except Exception as e:
        st.error(f"Erreur Claude: {e}")
        return None


def parse_messages(response):
    """Parse la réponse Claude"""
    if '---MESSAGE_1---' in response and '---MESSAGE_2---' in response:
        parts = response.split('---MESSAGE_2---')
        m1 = parts[0].replace('---MESSAGE_1---', '').strip()
        m2 = parts[1].strip() if len(parts) > 1 else ""
    else:
        lines = response.split('\n\n')
        mid = len(lines) // 2
        m1 = '\n\n'.join(lines[:mid])
        m2 = '\n\n'.join(lines[mid:])
    return m1, m2


def generate_message_3(prenom):
    """Message 3 - Template fixe"""
    return f"""Bonjour {prenom},

Je comprends que vous n'ayez pas eu le temps de revenir vers moi — je sais à quel point vos fonctions sont sollicitées.

Avant de clore le dossier de mon côté, une dernière question : Est-ce que le timing n'est simplement pas bon pour l'instant, ou bien travaillez-vous déjà avec d'autres cabinets/recruteurs sur ce poste ?

Si c'est une question de timing, je serai ravi de reprendre contact dans quelques semaines.

Si vous préférez gérer ce recrutement autrement, aucun souci — je vous souhaite de trouver la perle rare rapidement.

Merci en tous cas pour votre attention,

Bonne continuation,"""


def generate_subject_lines(titre_poste):
    """Génère les objets d'email"""
    return f"""1. {titre_poste} - profils qualifiés ?
2. Re: {titre_poste}
3. Question rapide sur votre recrutement"""


# ========================================
# UTILITAIRES
# ========================================

def get_firstname(prospect_data):
    """Extrait le prénom"""
    for key in ['first_name', 'firstname', 'prénom']:
        if prospect_data.get(key):
            return str(prospect_data[key]).strip().capitalize()
    
    full_name = prospect_data.get('full_name') or prospect_data.get('user_full name', '')
    if full_name and ' ' in str(full_name):
        return str(full_name).split()[0].capitalize()
    return "[Prénom]"


def get_job_title(job_posting_data):
    """Extrait le titre du poste"""
    if not job_posting_data:
        return "[Poste]"
    title = job_posting_data.get('title', '')
    title = re.sub(r'\s*\(?[HhFf]\s*[/\-]\s*[HhFfMm]\)?', '', title)
    return title.strip() or "[Poste]"


def format_posts(posts):
    """Formate les posts LinkedIn pour le prompt"""
    if not posts:
        return "Aucun post LinkedIn récent trouvé."
    
    formatted = []
    for i, post in enumerate(posts[:5], 1):
        # Chercher le texte dans plusieurs champs possibles
        text = (
            post.get('text') or 
            post.get('postText') or 
            post.get('content') or 
            post.get('commentary') or
            post.get('description') or
            post.get('body') or
            ''
        )[:500]
        
        # Chercher la date
        date = (
            post.get('date') or 
            post.get('postedDate') or 
            post.get('postedAt') or
            post.get('time') or
            post.get('timestamp') or
            'Date inconnue'
        )
        
        # Récupérer les interactions si disponibles
        reactions = post.get('numLikes') or post.get('reactions') or post.get('likes') or ''
        comments = post.get('numComments') or post.get('comments') or ''
        
        stats = ""
        if reactions or comments:
            stats = f" | 👍{reactions} 💬{comments}"
        
        if text:
            formatted.append(f"POST {i} ({date}{stats}):\n{text}")
    
    if not formatted:
        return "Aucun post LinkedIn avec contenu trouvé."
    
    return "\n\n".join(formatted)


def format_web_results(web_data):
    """Formate les résultats web pour le prompt"""
    if not web_data:
        return "Aucune actualité web récente trouvée."
    
    formatted = []
    for i, item in enumerate(web_data[:5], 1):
        title = item.get('title', '')
        snippet = item.get('snippet', '')
        date = item.get('date', '')
        item_type = item.get('type', 'web')
        formatted.append(f"[{item_type.upper()}] {title}\n{snippet}\n({date})")
    return "\n\n".join(formatted)


def format_profile(prospect_data):
    """Formate le profil pour le prompt"""
    return f"""Nom: {prospect_data.get('full_name') or prospect_data.get('user_full name', 'N/A')}
Titre: {prospect_data.get('headline') or prospect_data.get('linkedin_headline', 'N/A')}
Entreprise: {prospect_data.get('company') or prospect_data.get('linkedin_company', 'N/A')}"""


def extract_prospect_data(leonar_prospect):
    """Extrait les données du prospect Leonar"""
    full_name = leonar_prospect.get('user_full name', '')
    first_name = ''
    
    if full_name and ' ' in str(full_name):
        first_name = str(full_name).split()[0]
    
    return {
        '_id': leonar_prospect.get('_id', ''),
        'full_name': full_name,
        'user_full name': full_name,
        'first_name': first_name,
        'company': leonar_prospect.get('linkedin_company', ''),
        'linkedin_company': leonar_prospect.get('linkedin_company', ''),
        'linkedin_url': leonar_prospect.get('linkedin_url', ''),
        'headline': leonar_prospect.get('linkedin_headline', ''),
        'linkedin_headline': leonar_prospect.get('linkedin_headline', '')
    }


# ========================================
# INTERFACE
# ========================================

st.title("🎯 Icebreaker Generator V28.8")
st.caption("Leonar + Scraping LinkedIn/Web + Génération IA | LinkedIn auto, autres copier-coller")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    if ANTHROPIC_API_KEY:
        st.success("✅ Anthropic API")
    else:
        st.error("❌ ANTHROPIC_API_KEY")
    
    if APIFY_API_TOKEN:
        st.success("✅ Apify API")
    else:
        st.error("❌ APIFY_API_TOKEN")
    
    if SERPER_API_KEY:
        st.success("✅ Serper API (web)")
    else:
        st.warning("⚠️ SERPER_API_KEY (optionnel)")
    
    if all([LEONAR_EMAIL, LEONAR_PASSWORD, LEONAR_CAMPAIGN_ID]):
        if get_leonar_token():
            st.success("✅ Leonar connecté")
        else:
            st.error("❌ Erreur Leonar")
    else:
        st.warning("⚠️ Config Leonar incomplète")
    
    st.divider()
    st.header("📊 Stats session")
    st.metric("Appels API", st.session_state.generation_stats['calls'])
    st.metric("Tokens", f"{st.session_state.generation_stats['tokens']:,}")
    st.metric("Coût", f"${st.session_state.generation_stats['cost']:.4f}")
    
    st.divider()
    st.header("ℹ️ Sources supportées")
    st.markdown("""
    | Source | Méthode |
    |--------|---------|
    | **LinkedIn Jobs** | Auto ✅ |
    | **Indeed** | Copier-coller 📋 |
    | **HelloWork** | Copier-coller 📋 |
    | **Apec** | Copier-coller 📋 |
    """)


# Onglets
tab1, tab2, tab3 = st.tabs(["🚀 Génération Leonar", "🧪 Test Manuel", "🎯 Génération avec CV"])


# ========================================
# TAB 1 : GÉNÉRATION LEONAR
# ========================================
with tab1:
    st.header("Génération automatique depuis Leonar")
    
    if not all([LEONAR_EMAIL, LEONAR_PASSWORD, LEONAR_CAMPAIGN_ID]):
        st.error("Configuration Leonar manquante dans .env ou secrets")
        st.stop()
    
    token = get_leonar_token()
    if not token:
        st.error("Impossible de se connecter à Leonar")
        st.stop()
    
    # Zone URLs fiches de poste - AGRANDIE
    st.subheader("📄 URLs des fiches de poste (optionnel)")
    st.caption("💡 Priorité : URL dans Leonar (`custom_text_1`) > URL ci-dessous. LinkedIn/HelloWork/Indeed sont scrapés automatiquement.")
    
    job_urls_input = st.text_area(
        "URLs (une par ligne)",
        height=200,
        placeholder="https://www.hellowork.com/...\nhttps://www.indeed.fr/...\nhttps://www.linkedin.com/jobs/..."
    )
    
    # Parser les URLs
    job_urls_list = []
    has_manual_urls = False
    if job_urls_input:
        job_urls_list = [u.strip() for u in job_urls_input.strip().split('\n') if u.strip()]
        st.info(f"✅ {len(job_urls_list)} URL(s) détectée(s)")
        
        # Détecter URLs nécessitant copier-coller (HelloWork, Apec, Indeed)
        manual_urls = [u for u in job_urls_list if 'apec.fr' in u.lower() or 'hellowork.com' in u.lower() or 'indeed.' in u.lower()]
        if manual_urls:
            has_manual_urls = True
            st.warning(f"⚠️ {len(manual_urls)} URL(s) HelloWork/Apec/Indeed détectée(s). Collez le texte ci-dessous.")
    
    # Champ fallback pour HelloWork/Apec/Indeed
    manual_description = ""
    if has_manual_urls:
        manual_description = st.text_area(
            "📋 Description de la fiche de poste (copier-coller)",
            height=300,
            placeholder="Copiez-collez ici le contenu de la fiche de poste HelloWork, Apec ou Indeed...\n\nAstuce : Sur la page, sélectionnez tout le texte de la description et collez-le ici."
        )
    
    # Rafraîchir prospects
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔄 Rafraîchir", type="secondary"):
            with st.spinner("Chargement depuis Leonar..."):
                st.session_state.leonar_prospects = get_new_prospects_leonar(token)
    
    with col2:
        if st.button("🗑️ Reset traités", type="secondary"):
            if os.path.exists(PROCESSED_FILE):
                os.remove(PROCESSED_FILE)
                st.success("✅ Liste des prospects traités effacée")
            with st.spinner("Rechargement..."):
                st.session_state.leonar_prospects = get_new_prospects_leonar(token)
    
    with col3:
        if st.session_state.leonar_prospects:
            st.success(f"✅ {len(st.session_state.leonar_prospects)} prospects à traiter")
        else:
            st.warning("⚠️ 0 prospect - Cliquez sur Rafraîchir")
    
    # Liste des prospects
    if st.session_state.leonar_prospects:
        with st.expander(f"👥 Voir les {len(st.session_state.leonar_prospects)} prospects", expanded=True):
            for i, p in enumerate(st.session_state.leonar_prospects):
                name = p.get('user_full name', 'Inconnu')
                company = p.get('linkedin_company', 'N/A')
                has_linkedin = "✅" if p.get('linkedin_url') else "❌"
                
                # URL fiche : priorité Leonar (custom_text_1) > manuelle
                leonar_url = p.get('custom_text_1', '').strip()
                manual_url = job_urls_list[i] if (job_urls_list and i < len(job_urls_list)) else None
                
                if leonar_url:
                    has_url = "📄 URL Leonar ✅"
                elif manual_url:
                    has_url = f"📄 URL manuelle"
                else:
                    has_url = "⚠️ Pas d'URL"
                
                st.write(f"{i+1}. **{name}** | {company} | LinkedIn: {has_linkedin} | {has_url}")
        
        # Debug : voir les champs disponibles
        with st.expander("🔍 Debug: voir les champs Leonar", expanded=False):
            if st.session_state.leonar_prospects:
                p = st.session_state.leonar_prospects[0]
                st.write("**Champs disponibles sur le 1er prospect :**")
                for key in sorted(p.keys()):
                    value = p.get(key, '')
                    if value and str(value).strip():
                        st.write(f"- `{key}` = {str(value)[:100]}")
        
        # Bouton génération
        if st.button("🚀 LANCER LA GÉNÉRATION", type="primary", use_container_width=True):
            
            # Vérifier qu'on a des URLs (Leonar ou manuelles)
            has_any_url = False
            for i, p in enumerate(st.session_state.leonar_prospects):
                leonar_url = p.get('custom_text_1', '').strip()
                manual_url = job_urls_list[i] if (job_urls_list and i < len(job_urls_list)) else None
                if leonar_url or manual_url:
                    has_any_url = True
                    break
            
            if not has_any_url:
                st.error("⚠️ Aucune URL de fiche de poste. Ajoutez-les dans Leonar (custom_text_1) ou collez-les ci-dessus.")
                st.stop()
            
            # Init Apify
            try:
                apify_client = init_apify_client()
            except Exception as e:
                st.error(f"Erreur Apify: {e}")
                st.stop()
            
            # Progress
            progress = st.progress(0)
            status = st.empty()
            
            # Traiter chaque prospect
            for i, prospect in enumerate(st.session_state.leonar_prospects):
                progress.progress((i + 1) / len(st.session_state.leonar_prospects))
                
                name = prospect.get('user_full name', 'Inconnu')
                company = prospect.get('linkedin_company', '')
                status.write(f"⚙️ Traitement de **{name}**...")
                
                try:
                    # Extraire données prospect
                    p_data = extract_prospect_data(prospect)
                    
                    # URL fiche de poste : priorité Leonar (custom_text_1) > manuelle
                    leonar_url = prospect.get('custom_text_1', '').strip()
                    manual_url = job_urls_list[i] if (job_urls_list and i < len(job_urls_list)) else None
                    
                    if leonar_url:
                        job_url = leonar_url
                        st.caption(f"   📄 URL depuis Leonar")
                    elif manual_url:
                        job_url = manual_url
                        st.caption(f"   📄 URL manuelle")
                    else:
                        st.warning(f"   ⚠️ Pas d'URL pour ce prospect - ignoré")
                        continue
                    
                    # 1. Scraper la fiche de poste (ou utiliser description manuelle pour HelloWork/Apec/Indeed)
                    job_data = None
                    is_manual_url = 'apec.fr' in job_url.lower() or 'hellowork.com' in job_url.lower() or 'indeed.' in job_url.lower()
                    
                    if is_manual_url and manual_description:
                        # Utiliser la description manuelle
                        job_data = {
                            'title': 'Poste',
                            'description': manual_description,
                            'source': 'Manuel (copier-coller)',
                            'url': job_url
                        }
                        st.caption(f"   ✅ Description manuelle")
                    elif is_manual_url and not manual_description:
                        st.warning(f"   ⚠️ URL HelloWork/Apec/Indeed détectée mais pas de description manuelle")
                    else:
                        with st.spinner(f"📄 Scraping fiche de poste..."):
                            job_data = scrape_job_posting(job_url)
                            if job_data:
                                st.caption(f"   ✅ Fiche ({job_data.get('source', 'N/A')}): {job_data.get('title', 'N/A')[:40]}...")
                            else:
                                st.warning(f"   ⚠️ Scraping échoué pour {job_url[:50]}...")
                    
                    if not job_data or len(job_data.get('description', '')) < 100:
                        st.warning(f"   ⚠️ Pas de description valide - ignoré")
                        continue
                    
                    # 2. Scraper LinkedIn posts
                    posts = []
                    if p_data.get('linkedin_url'):
                        with st.spinner(f"🔍 Scraping LinkedIn..."):
                            posts = scrape_linkedin_posts(apify_client, p_data['linkedin_url'])
                            st.caption(f"   ✅ {len(posts)} posts LinkedIn (<6 mois)")
                    
                    # 3. Recherche web
                    web_results = []
                    if SERPER_API_KEY and name != 'Inconnu':
                        with st.spinner(f"🌐 Recherche web..."):
                            web_results = search_web_prospect(name, company)
                            st.caption(f"   ✅ {len(web_results)} résultats web")
                    
                    # 4. Générer séquence
                    with st.spinner(f"✨ Génération messages..."):
                        sequence = generate_sequence_v28(p_data, posts, web_results, job_data)
                    
                    if sequence:
                        # Update Leonar
                        if update_prospect_leonar(token, prospect['_id'], sequence):
                            save_processed(prospect['_id'])
                            st.toast(f"✅ {name}")
                        else:
                            st.warning(f"⚠️ Erreur export Leonar pour {name}")
                    else:
                        st.error(f"❌ Erreur génération pour {name}")
                
                except Exception as e:
                    st.error(f"❌ Erreur pour {name}: {e}")
                
                # Pause anti-rate-limit entre chaque prospect (sauf le dernier)
                if i < len(st.session_state.leonar_prospects) - 1:
                    status.write(f"⏳ Pause anti-rate-limit (3s)...")
                    time.sleep(3)
            
            progress.progress(1.0)
            status.empty()
            st.success("✅ Génération terminée !")
            st.balloons()
            
            # Reset liste
            st.session_state.leonar_prospects = []


# ========================================
# TAB 2 : TEST MANUEL
# ========================================
with tab2:
    st.header("Test manuel")
    
    col1, col2 = st.columns(2)
    
    with col1:
        t_prenom = st.text_input("Prénom", "Alexandre")
        t_nom = st.text_input("Nom", "Dupont")
        t_company = st.text_input("Entreprise", "CAMCA")
        t_linkedin = st.text_input("URL LinkedIn (optionnel)")
    
    with col2:
        t_job_url = st.text_input("URL fiche de poste")
        t_headline = st.text_input("Titre LinkedIn", "Responsable Comptabilité")
    
    if st.button("🚀 Générer", type="primary"):
        
        # Préparer données
        prospect = {
            'first_name': t_prenom,
            'full_name': f"{t_prenom} {t_nom}",
            'company': t_company,
            'headline': t_headline,
            'linkedin_url': t_linkedin
        }
        
        # Scraper fiche
        job_data = None
        if t_job_url:
            with st.spinner("📄 Scraping fiche de poste..."):
                job_data = scrape_job_posting(t_job_url)
                if job_data:
                    st.success(f"✅ Fiche ({job_data.get('source', 'N/A')}): {job_data.get('title', '')[:50]}")
                else:
                    st.error("❌ Scraping échoué")
        
        if not job_data:
            st.error("❌ Pas de fiche de poste valide")
            st.stop()
        
        # Scraper LinkedIn
        posts = []
        if t_linkedin:
            try:
                apify_client = init_apify_client()
                with st.spinner("🔍 Scraping LinkedIn..."):
                    posts = scrape_linkedin_posts(apify_client, t_linkedin)
                    st.success(f"✅ {len(posts)} posts LinkedIn (<6 mois)")
            except Exception as e:
                st.warning(f"Scraping LinkedIn échoué: {e}")
        
        # Recherche web
        web_results = []
        if SERPER_API_KEY:
            with st.spinner("🌐 Recherche web..."):
                web_results = search_web_prospect(f"{t_prenom} {t_nom}", t_company)
                st.success(f"✅ {len(web_results)} résultats web")
        
        # Générer
        with st.spinner("✨ Génération..."):
            sequence = generate_sequence_v28(prospect, posts, web_results, job_data)
        
        if sequence:
            st.divider()
            
            st.subheader("📧 Objets")
            st.code(sequence['subject_lines'])
            
            st.subheader("✉️ Message 1")
            st.info(sequence['message_1'])
            
            st.subheader("✉️ Message 2")
            st.info(sequence['message_2'])
            
            st.subheader("✉️ Message 3")
            st.info(sequence['message_3'])

# ========================================
# TAB 3 : GÉNÉRATION AVEC CV
# ========================================
with tab3:
    st.header("🎯 Génération avec CV anonymisé")
    st.caption("Séquence 2 messages : Message 1 (CV joint) + Message 2 (relance douce)")
    
    if not all([LEONAR_EMAIL, LEONAR_PASSWORD, LEONAR_CAMPAIGN_ID]):
        st.error("Configuration Leonar manquante")
        st.stop()
    
    token = get_leonar_token()
    if not token:
        st.error("Impossible de se connecter à Leonar")
        st.stop()
    
    # ========================================
    # CONFIGURATION
    # ========================================
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Fiche de poste")
        job_url_cv = st.text_input("URL fiche de poste", key="job_url_cv")
        
        # Fallback copier-coller
        manual_desc_cv = st.text_area(
            "📋 Ou collez la description (HelloWork/Indeed/Apec)",
            height=200,
            key="manual_desc_cv",
            placeholder="Copiez-collez le contenu de la fiche..."
        )
    
    with col2:
        st.subheader("👤 Prospect")
        
        # Rafraîchir prospects
        if st.button("🔄 Charger prospects", type="secondary", key="refresh_cv"):
            with st.spinner("Chargement..."):
                st.session_state.leonar_prospects_cv = get_new_prospects_leonar(token)
        
        # Sélection prospect
        if 'leonar_prospects_cv' not in st.session_state:
            st.session_state.leonar_prospects_cv = []
        
        if st.session_state.leonar_prospects_cv:
            prospect_cv = st.selectbox(
                "Sélectionner un prospect",
                options=st.session_state.leonar_prospects_cv,
                format_func=lambda x: f"{x.get('user_full name', 'Inconnu')} - {x.get('linkedin_company', 'N/A')}",
                key="prospect_select_cv"
            )
        else:
            st.warning("Aucun prospect chargé. Cliquez sur 'Charger prospects'")
            prospect_cv = None
    
    # ========================================
    # GÉNÉRATION
    # ========================================
    
    if st.button("🚀 GÉNÉRER CV + SÉQUENCE", type="primary", use_container_width=True):
        
        if not job_url_cv and not manual_desc_cv:
            st.error("⚠️ Fournissez une URL ou collez la description")
            st.stop()
        
        if not prospect_cv:
            st.error("⚠️ Sélectionnez un prospect")
            st.stop()
        
        # Extraire données prospect
        p_data = extract_prospect_data(prospect_cv)
        first_name = get_firstname(p_data)
        
        # ========================================
        # ÉTAPE 1 : SCRAPER FICHE DE POSTE
        # ========================================
        
        with st.spinner("📄 Scraping fiche de poste..."):
            job_data = None
            
            if manual_desc_cv:
                # Utiliser description manuelle
                job_data = {
                    'title': 'Poste',
                    'description': manual_desc_cv,
                    'source': 'Manuel',
                    'url': job_url_cv or ''
                }
                st.success("✅ Description manuelle")
            elif job_url_cv:
                # Scraper l'URL
                job_data = scrape_job_posting(job_url_cv)
                if job_data:
                    st.success(f"✅ Fiche scrapée : {job_data.get('title', 'N/A')[:50]}")
                else:
                    st.error("❌ Scraping échoué")
                    st.stop()
        
        if not job_data or len(job_data.get('description', '')) < 100:
            st.error("❌ Description trop courte ou invalide")
            st.stop()
        
        # ========================================
        # ÉTAPE 2 : GÉNÉRER LE CV
        # ========================================
        
        with st.spinner("✨ Génération du CV (15-20 sec)..."):
            try:
                cv_content = generate_cv_content(job_data, p_data)
                st.success(f"✅ CV généré : {cv_content['metadata']['job_title']}")
                
                # Vérifier longueur
                if not estimate_cv_length(cv_content):
                    st.warning("⚠️ CV trop long, condensation automatique...")
                    cv_content = condense_cv_content(cv_content)
                
            except Exception as e:
                st.error(f"❌ Erreur génération CV : {e}")
                st.stop()
        
        # ========================================
        # ÉTAPE 3 : CRÉER LE PDF
        # ========================================
        
        with st.spinner("📄 Création du PDF..."):
            try:
                pdf_bytes = create_cv_pdf(cv_content, template_name='classic')
                st.success("✅ PDF créé")
            except Exception as e:
                st.error(f"❌ Erreur création PDF : {e}")
                st.stop()
        
        # ========================================
        # ÉTAPE 4 : UPLOAD GOOGLE DRIVE
        # ========================================
        
        with st.spinner("☁️ Upload Google Drive..."):
            try:
                upload_result = upload_cv(
                    pdf_bytes,
                    job_data['title'],
                    prospect_name=p_data.get('full_name')
                )
                
                if upload_result:
                    cv_url = upload_result['url']
                    st.success(f"✅ CV uploadé : [Voir le CV]({cv_url})")
                else:
                    st.error("❌ Erreur upload Google Drive")
                    st.stop()
                    
            except Exception as e:
                st.error(f"❌ Erreur upload : {e}")
                st.stop()
        
        # ========================================
        # ÉTAPE 5 : GÉNÉRER LES MESSAGES
        # ========================================
        
        with st.spinner("✉️ Génération des messages..."):
            try:
                sequence = generate_sequence_with_cv(
                    prospect_data=p_data,
                    job_posting_data=job_data,
                    cv_url=cv_url,
                    cv_gaps=cv_content.get('gaps_vs_fiche', [])
                )
                
                subject_lines = generate_subject_lines_cv(job_data['title'])
                
                st.success("✅ Séquence générée")
                
            except Exception as e:
                st.error(f"❌ Erreur génération messages : {e}")
                st.stop()
        
        # ========================================
        # ÉTAPE 6 : SAUVEGARDER DANS LEONAR
        # ========================================
        
        with st.spinner("💾 Sauvegarde dans Leonar..."):
            try:
                # Format pour Leonar
                formatted_notes = f'''═══════════════════════════════════════════════════════════════
OBJETS SUGGÉRÉS
═══════════════════════════════════════════════════════════════

{subject_lines}

═══════════════════════════════════════════════════════════════
MESSAGE 1 (CV JOINT - J+0)
═══════════════════════════════════════════════════════════════

{sequence['message_1']}

═══════════════════════════════════════════════════════════════
MESSAGE 2 (RELANCE - J+7)
═══════════════════════════════════════════════════════════════

{sequence['message_2']}

═══════════════════════════════════════════════════════════════
LIEN CV
═══════════════════════════════════════════════════════════════
{cv_url}
'''
                
                # Update Leonar
                requests.patch(
                    f'https://dashboard.leonar.app/api/1.1/obj/matching/{prospect_cv["_id"]}',
                    headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                    json={
                        "notes": formatted_notes,
                        "custom_variable_1": sequence['message_1'],
                        "custom_variable_2": sequence['message_2'],
                        "custom_text_2": cv_url  # Stocker l'URL du CV
                    },
                    timeout=10
                )
                
                save_processed(prospect_cv['_id'])
                st.success("✅ Sauvegardé dans Leonar")
                
            except Exception as e:
                st.error(f"❌ Erreur Leonar : {e}")
        
        # ========================================
        # AFFICHAGE DES RÉSULTATS
        # ========================================
        
        st.divider()
        st.balloons()
        
        # CV
        st.subheader("📄 CV Généré")
        st.markdown(f"**[👉 Voir le CV sur Google Drive]({cv_url})**")
        
        with st.expander("🔍 Détails du CV", expanded=False):
            st.json(cv_content.get('gaps_vs_fiche', []))
        
        # Objets
        st.subheader("📧 Objets d'email")
        st.code(subject_lines)
        
        # Message 1
        st.subheader("✉️ Message 1 (à envoyer maintenant)")
        st.text_area("Message 1", value=sequence['message_1'], height=300, key="result_msg1")
        if st.button("📋 Copier Message 1", key="copy_msg1"):
            st.code(sequence['message_1'])
        
        # Message 2
        st.subheader("✉️ Message 2 (à envoyer J+7)")
        st.text_area("Message 2", value=sequence['message_2'], height=200, key="result_msg2")
        if st.button("📋 Copier Message 2", key="copy_msg2"):
            st.code(sequence['message_2'])
        
        st.info(f"📅 Dates d'envoi suggérées : {sequence['send_dates']['message_1']} et {sequence['send_dates']['message_2']}")
