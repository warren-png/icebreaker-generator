"""
═══════════════════════════════════════════════════════════════════
SEQUENCE GENERATOR V28 - ARCHITECTURE SIMPLIFIÉE
═══════════════════════════════════════════════════════════════════
Philosophie :
- ZÉRO logique de détection (métier, secteur, pain points)
- Claude analyse TOUT en un seul appel
- Structures de messages FIXES
- Scraping LinkedIn/Web MAINTENU
═══════════════════════════════════════════════════════════════════
"""

import anthropic
import os
import re
import json
from datetime import datetime, timedelta

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

if not ANTHROPIC_API_KEY:
    raise ValueError("❌ ANTHROPIC_API_KEY non trouvée")


# ========================================
# LOGGER & COST TRACKER INTÉGRÉS
# ========================================

def log_event(event_name, data=None):
    """Log un événement"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event': event_name
    }
    if data:
        log_entry.update(data)
    print(f"📋 {json.dumps(log_entry, ensure_ascii=False)}")


def log_error(error_type, message, data=None):
    """Log une erreur"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'error_type': error_type,
        'message': message
    }
    if data:
        log_entry.update(data)
    print(f"❌ {json.dumps(log_entry, ensure_ascii=False)}")


class CostTracker:
    """Tracker de coûts API"""
    
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0
        self.calls = []
    
    def track(self, usage, function_name):
        """Enregistre un appel API"""
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens
        
        # Prix Claude Sonnet
        cost = (input_tokens * 0.003 + output_tokens * 0.015) / 1000
        
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost
        
        self.calls.append({
            'function': function_name,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cost': cost
        })
        
        print(f"💰 [{function_name}] Tokens: {input_tokens}→{output_tokens} | Coût: ${cost:.4f}")
    
    def get_summary(self):
        return {
            'total_calls': len(self.calls),
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_cost': self.total_cost
        }
    
    def reset(self):
        self.__init__()


# Instance globale
tracker = CostTracker()


# ========================================
# APIFY - SCRAPING LINKEDIN (INCHANGÉ)
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


def scrape_linkedin_profile(apify_client, linkedin_url):
    """Scrape un profil LinkedIn via Apify"""
    try:
        log_event('scrape_linkedin_profile_start', {'url': linkedin_url})
        
        run_input = {"profileUrls": [linkedin_url]}
        run = apify_client.actor("dev_fusion/Linkedin-Profile-Scraper").call(run_input=run_input)
        items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if items:
            log_event('scrape_linkedin_profile_success', {'items_count': len(items)})
            return items[0]
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
        
        # Filtrer posts < 3 mois
        filtered = filter_recent_posts(items)
        
        log_event('scrape_linkedin_posts_success', {
            'total': len(items),
            'filtered': len(filtered)
        })
        return filtered
        
    except Exception as e:
        log_error('scrape_linkedin_posts_error', str(e), {'url': linkedin_url})
        return []


def filter_recent_posts(posts, max_age_months=3):
    """Filtre les posts < 3 mois"""
    if not posts:
        return []
    
    cutoff = datetime.now() - timedelta(days=max_age_months * 30)
    recent = []
    
    for post in posts[:10]:
        if not isinstance(post, dict):
            continue
        
        date_str = post.get('date') or post.get('postedDate') or ''
        
        # Parser la date
        post_date = None
        for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%d/%m/%Y']:
            try:
                post_date = datetime.strptime(str(date_str)[:10], fmt)
                break
            except:
                continue
        
        if post_date and post_date >= cutoff:
            recent.append(post)
        elif not post_date:
            # Pas de date → garder par défaut (max 3)
            if len(recent) < 3:
                recent.append(post)
    
    return recent[:5]


# ========================================
# UTILITAIRES
# ========================================

def get_firstname(prospect_data):
    """Extrait le prénom du prospect"""
    for key in ['first_name', 'firstname', 'prénom', 'prenom']:
        val = prospect_data.get(key)
        if val:
            return str(val).strip().capitalize()
    
    full_name = prospect_data.get('full_name', '')
    if full_name and ' ' in str(full_name):
        return str(full_name).split()[0].capitalize()
    
    return "[Prénom]"


def get_job_title(job_posting_data):
    """Extrait le titre du poste"""
    if not job_posting_data:
        return "[Poste]"
    
    title = job_posting_data.get('title', '')
    if not title:
        return "[Poste]"
    
    # Nettoyer H/F, F/H, etc.
    title = re.sub(r'\s*\(?[HhFf]\s*[/\-]\s*[HhFfMm]\)?', '', title)
    title = re.sub(r'\s*[-|]\s*.*$', '', title)
    
    return title.strip()


def format_posts_for_prompt(posts):
    """Formate les posts LinkedIn pour le prompt"""
    if not posts:
        return "Aucun post LinkedIn récent trouvé."
    
    formatted = []
    for i, post in enumerate(posts[:5], 1):
        text = post.get('text', '')[:400]
        date = post.get('date', post.get('postedDate', 'date inconnue'))
        title = post.get('title', '')
        
        entry = f"POST {i} ({date})"
        if title:
            entry += f"\nTitre: {title}"
        entry += f"\nContenu: {text}"
        formatted.append(entry)
    
    return "\n\n".join(formatted)


def format_profile_for_prompt(profile_data):
    """Formate le profil LinkedIn pour le prompt"""
    if not profile_data:
        return "Profil LinkedIn non disponible."
    
    return f"""
Nom: {profile_data.get('full_name', 'N/A')}
Titre: {profile_data.get('headline', 'N/A')}
Entreprise: {profile_data.get('company', 'N/A')}
Localisation: {profile_data.get('location', 'N/A')}
"""


# ========================================
# MESSAGE 3 - TEMPLATE FIXE
# ========================================

MESSAGE_3_TEMPLATE = """Bonjour {prenom},

Je comprends que vous n'ayez pas eu le temps de revenir vers moi — je sais à quel point vos fonctions sont sollicitées.

Avant de clore le dossier de mon côté, une dernière question : Est-ce que le timing n'est simplement pas bon pour l'instant, ou bien travaillez-vous déjà avec d'autres cabinets/recruteurs sur ce poste ?

Si c'est une question de timing, je serai ravi de reprendre contact dans quelques semaines.

Si vous préférez gérer ce recrutement autrement, aucun souci — je vous souhaite de trouver la perle rare rapidement.

Merci en tous cas pour votre attention,

Bonne continuation,"""


# ========================================
# GÉNÉRATION SÉQUENCE - 1 APPEL CLAUDE
# ========================================

def generate_sequence_v28(prospect_data, posts_data, job_posting_data, profile_data=None):
    """
    Génère M1 + M2 en UN SEUL appel Claude
    M3 = template fixe
    """
    
    log_event('generate_sequence_v28_start', {
        'prospect': prospect_data.get('full_name', 'unknown'),
        'has_posts': bool(posts_data),
        'has_job_posting': bool(job_posting_data)
    })
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Extraire données
    prenom = get_firstname(prospect_data)
    titre_poste = get_job_title(job_posting_data)
    
    # Formater pour le prompt
    posts_formatted = format_posts_for_prompt(posts_data)
    profile_formatted = format_profile_for_prompt(profile_data or prospect_data)
    fiche_formatted = job_posting_data.get('description', 'Fiche de poste non disponible') if job_posting_data else 'Fiche de poste non disponible'
    
    prompt = f"""Tu es chasseur de têtes Finance chez Entourage Recrutement.
Tu dois générer 2 messages de prospection pour ce prospect.

═══════════════════════════════════════════════════════════════════
DONNÉES PROSPECT
═══════════════════════════════════════════════════════════════════
{profile_formatted}

═══════════════════════════════════════════════════════════════════
POSTS LINKEDIN RÉCENTS
═══════════════════════════════════════════════════════════════════
{posts_formatted}

═══════════════════════════════════════════════════════════════════
FICHE DE POSTE : {titre_poste}
═══════════════════════════════════════════════════════════════════
{fiche_formatted[:2500]}

═══════════════════════════════════════════════════════════════════
GÉNÈRE LES 2 MESSAGES SUIVANTS
═══════════════════════════════════════════════════════════════════

**MESSAGE 1 (Icebreaker)** - Structure EXACTE :

Bonjour {prenom},

[HOOK - CHOISIS UNE OPTION :]
Option A (si un post LinkedIn est pertinent et récent) : 
  Référence personnalisée au post (mentionne le sujet PRÉCIS, pas de généralités)
  Puis transition vers le poste.
Option B (si pas de post pertinent) :
  "Je vous contacte concernant votre recherche de {titre_poste}."

[PAIN POINT #1]
Identifie LA difficulté principale de ce recrutement en utilisant le VOCABULAIRE EXACT de la fiche.
Exemples de bons pain points :
- "La maîtrise simultanée des flux de réassurance, coassurance et provisions techniques est une combinaison rare."
- "Trouver un profil qui allie expertise consolidation IFRS et accompagnement des filiales reste complexe."
PAS de généralités comme "rigueur", "agilité", "dynamisme".

[QUESTION FINALE CONTEXTUALISÉE]
Formule une question courte qui reprend 2-3 compétences critiques identifiées dans le pain point.
Structure : "Qu'est-ce qui manque le plus dans les profils rencontrés aujourd'hui : [compétence A], [compétence B], ou les deux ?"
Exemples :
- "Qu'est-ce qui manque le plus : le niveau de modélisation, l'expérience d'exécution end-to-end, ou les deux ?"
- "Qu'est-ce qui manque le plus : la maîtrise des flux de réassurance, l'expérience en consolidation IFRS, ou les deux ?"
La question DOIT être spécifique au poste, JAMAIS générique.

Bien à vous,

---

**MESSAGE 2 (Relance avec profils)** - Structure EXACTE :

Bonjour {prenom},

Je me permets de vous relancer concernant votre recherche de {titre_poste}.

[PAIN POINT #2 - DIFFÉRENT DE M1]
Angle complémentaire sur une AUTRE difficulté du recrutement.
Utilise d'AUTRES compétences/exigences de la fiche que M1.

J'ai identifié 2 profils qui pourraient retenir votre attention :

- L'un [PROFIL 1 : spécialiste avec les compétences EXACTES de la fiche. 
  Respecte l'expérience demandée. Mentionne le secteur si exigé.]

- L'autre [PROFIL 2 : parcours DIFFÉRENT mais compétences pertinentes.
  PAS "Big 4" ou "reconversion" par défaut - seulement si cohérent avec la fiche.]

Seriez-vous d'accord pour recevoir leurs synthèses anonymisées ?

Bien à vous,

═══════════════════════════════════════════════════════════════════
INTERDICTIONS ABSOLUES
═══════════════════════════════════════════════════════════════════
❌ "Je travaille sur...", "Je travaille actuellement..."
❌ "rigueur", "agilité", "dynamisme", "dynamique", "croissance"
❌ Inventer des compétences/certifications NON MENTIONNÉES dans la fiche
❌ Répéter le MÊME pain point entre M1 et M2
❌ Profils incohérents avec la fiche (ex: "Solvabilité II" si pas mentionné)
❌ Exagérer l'expérience (si la fiche dit "5 ans", respecter)
❌ Modifier la proposition de M2 (synthèses anonymisées)
❌ Utiliser une question finale générique type "Quels sont les principaux écarts..."

═══════════════════════════════════════════════════════════════════
FORMAT DE RÉPONSE
═══════════════════════════════════════════════════════════════════
Retourne UNIQUEMENT les 2 messages, séparés par une ligne :
---MESSAGE_1---
[contenu message 1]
---MESSAGE_2---
[contenu message 2]
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        tracker.track(message.usage, 'generate_sequence_v28')
        result = message.content[0].text.strip()
        
        # Parser les messages
        m1, m2 = parse_messages(result)
        m3 = MESSAGE_3_TEMPLATE.format(prenom=prenom)
        
        log_event('generate_sequence_v28_success', {
            'm1_length': len(m1),
            'm2_length': len(m2)
        })
        
        return {
            'message_1': m1,
            'message_2': m2,
            'message_3': m3
        }
        
    except Exception as e:
        log_error('generate_sequence_v28_error', str(e), {})
        raise


def parse_messages(response):
    """Parse la réponse Claude pour extraire M1 et M2"""
    
    # Chercher les délimiteurs
    if '---MESSAGE_1---' in response and '---MESSAGE_2---' in response:
        parts = response.split('---MESSAGE_2---')
        m1 = parts[0].replace('---MESSAGE_1---', '').strip()
        m2 = parts[1].strip() if len(parts) > 1 else ""
    else:
        # Fallback : couper au milieu
        lines = response.split('\n\n')
        mid = len(lines) // 2
        m1 = '\n\n'.join(lines[:mid])
        m2 = '\n\n'.join(lines[mid:])
    
    return m1, m2


# ========================================
# FONCTION PRINCIPALE - COMPATIBILITÉ
# ========================================

def generate_full_sequence(prospect_data, hooks_data, job_posting_data, message_1_content=None):
    """
    Point d'entrée compatible avec l'ancienne API
    """
    return generate_sequence_v28(
        prospect_data=prospect_data,
        posts_data=hooks_data if hooks_data != "NOT_FOUND" else [],
        job_posting_data=job_posting_data,
        profile_data=prospect_data
    )


def generate_icebreaker(prospect_data, hooks_data, job_posting_data):
    """
    Compatibilité : génère seulement M1
    """
    result = generate_sequence_v28(
        prospect_data=prospect_data,
        posts_data=hooks_data if hooks_data != "NOT_FOUND" else [],
        job_posting_data=job_posting_data,
        profile_data=prospect_data
    )
    return result['message_1']


def generate_advanced_icebreaker(prospect_data, hooks_data, job_posting_data):
    """Alias pour compatibilité"""
    return generate_icebreaker(prospect_data, hooks_data, job_posting_data)


# ========================================
# EXPORT FONCTIONS APIFY (COMPATIBILITÉ)
# ========================================

def extract_hooks_with_claude(profile_data, posts_data, web_results, company_data, 
                               news_results, full_name, company_name):
    """
    Compatibilité : retourne simplement les posts formatés
    V28 n'a plus besoin d'extraction séparée des hooks
    """
    if not posts_data:
        return []
    
    hooks = []
    for post in posts_data[:5]:
        if isinstance(post, dict) and post.get('text'):
            hooks.append({
                'text': post.get('text', ''),
                'type': 'post',
                'date': post.get('date', post.get('postedDate', ''))
            })
    
    return hooks
