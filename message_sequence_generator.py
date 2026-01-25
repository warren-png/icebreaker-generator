"""
═══════════════════════════════════════════════════════════════════
MESSAGE SEQUENCE GENERATOR - V27.3 (COMPLET)
Modifications V27.3 :
- Filtrage hooks LinkedIn <3 mois (filter_recent_posts)
- Détection secteur précise (logistique vs industrie vs banque)
- Extraction certifications/normes (CIA, IIA, IFRS, etc.)
- Pain points adaptés par secteur
- Extraction PURE des outils (zéro invention)
- Message 2 : TOUJOURS 2 profils ultra-différenciés avec compétences précises
- Message 3 : TOUJOURS identique (template fixe avec prénom uniquement)
═══════════════════════════════════════════════════════════════════
"""

import anthropic
import os
import re 
from datetime import datetime, timedelta
from config import COMPANY_INFO, PAIN_POINTS_DETAILED, OUTCOMES_DETAILED

# Imports utilitaires
from prospection_utils.logger import log_event, log_error
from prospection_utils.cost_tracker import tracker
from prospection_utils.validator import validate_and_report

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("❌ ANTHROPIC_API_KEY non trouvée")


# ========================================
# FILTRAGE HOOKS LINKEDIN (V27.3)
# ========================================

def filter_recent_posts(posts, max_age_months=3, max_posts=5):
    """
    Filtre les posts LinkedIn pour ne garder que ceux <3 mois
    VERSION V27.3 : Filtrage strict par date
    """
    if not posts or posts == "NOT_FOUND":
        return []
    
    cutoff_date = datetime.now() - timedelta(days=max_age_months * 30)
    recent_posts = []
    
    for post in posts:
        post_date_str = post.get('date') or post.get('postedDate') or post.get('timestamp')
        if not post_date_str:
            continue
            
        try:
            # Essayer différents formats de date
            for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%d/%m/%Y']:
                try:
                    post_date = datetime.strptime(str(post_date_str)[:10], fmt)
                    break
                except:
                    continue
            
            if post_date >= cutoff_date:
                recent_posts.append(post)
                
        except Exception as e:
            log_event('post_date_parse_error', {'error': str(e), 'date': post_date_str})
            continue
    
    # Limiter au nombre max de posts
    recent_posts = sorted(recent_posts, key=lambda x: x.get('date', ''), reverse=True)[:max_posts]
    
    log_event('posts_filtered', {
        'total': len(posts) if isinstance(posts, list) else 0,
        'recent': len(recent_posts),
        'cutoff_date': cutoff_date.strftime('%Y-%m-%d')
    })
    
    return recent_posts


def detect_company_sector(job_posting_data):
    """
    Détecte le secteur de l'entreprise avec taxonomie précise
    VERSION V27.3 : Différencie logistique, industrie, banque, services
    """
    if not job_posting_data:
        return 'general'
    
    text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}".lower()
    
    # Taxonomie secteur (ordre = priorité)
    sectors = {
        'banking': ['banque', 'bancaire', 'cib', 'corporate banking', 'investment banking', 
                    'retail banking', 'private banking', 'gestion privée'],
        
        'insurance': ['assurance', 'assureur', 'solvabilité', 'actuariat', 'mutuelle'],
        
        'logistics_transport': ['logistique', 'supply chain', 'transport', 'freight', 
                                 'forwarding', 'entreposage', 'distribution logistique',
                                 'dhl', 'kuehne', 'geodis', 'bolloré logistics'],
        
        'manufacturing': ['production', 'usine', 'fabrication', 'manufacturing', 
                          'sites de production', 'process industriel', 'ligne de production'],
        
        'engineering': ['ingénierie', 'engineering', 'construction', 'infrastructure', 
                        'btp', 'travaux publics', 'génie civil'],
        
        'retail': ['retail', 'grande distribution', 'commerce', 'magasin', 
                   'point de vente', 'réseau de magasins'],
        
        'fintech': ['fintech', 'néobanque', 'payment', 'crypto', 'blockchain'],
        
        'services': ['conseil', 'consulting', 'services', 'cabinet']
    }
    
    sector_scores = {}
    for sector, keywords in sectors.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            sector_scores[sector] = score
    
    if not sector_scores:
        return 'general'
    
    detected_sector = max(sector_scores.items(), key=lambda x: x[1])[0]
    
    log_event('sector_detected', {
        'sector': detected_sector,
        'scores': sector_scores
    })
    
    return detected_sector


def extract_certifications_and_norms(job_posting_data):
    """
    Détecte les certifications et normes métier mentionnées
    VERSION V27.3 : Enrichit la détection des compétences
    """
    if not job_posting_data:
        return []
    
    text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}".lower()
    
    certifications = {
        # Audit
        'cia': 'CIA',
        'cpai': 'CPAI',
        'cisa': 'CISA',
        'cism': 'CISM',
        'crma': 'CRMA',
        'cfe': 'CFE',
        
        # Comptabilité
        'dscg': 'DSCG',
        'dec': 'DEC',
        'cpa': 'CPA',
        'acca': 'ACCA',
        'cma': 'CMA',
        
        # Normes
        'iia': 'normes IIA',
        'ifrs': 'normes IFRS',
        'gaap': 'normes GAAP',
        'us gaap': 'normes US GAAP',
        'sox': 'SOX',
        'coso': 'COSO',
        
        # Project Management
        'pmp': 'PMP',
        'prince2': 'PRINCE2',
        'safe': 'SAFe',
        'scrum master': 'Scrum Master'
    }
    
    detected = []
    for cert_key, cert_name in certifications.items():
        if cert_key.lower() in text:
            detected.append(cert_name)
    
    return detected


# ========================================
# DÉTECTION AUTOMATIQUE DU MÉTIER
# ========================================

def detect_job_category(prospect_data, job_posting_data):
    """Détecte automatiquement la catégorie métier du prospect"""
    
    text = f"{prospect_data.get('headline', '')} {prospect_data.get('title', '')} "
    if job_posting_data:
        text += f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}"
    
    text = text.lower()
    
    # Détection par mots-clés (ordre = priorité)
    if any(word in text for word in ['data officer', 'ia officer', 'ai officer', 'data & ia', 'intelligence artificielle']):
        return 'data_ia'
    elif any(word in text for word in ['daf', 'directeur administratif', 'cfo', 'chief financial']):
        return 'daf'
    elif any(word in text for word in ['raf', 'responsable administratif']):
        return 'raf'
    elif any(word in text for word in ['fp&a', 'fp a', 'financial planning']):
        return 'fpna'
    elif any(word in text for word in ['contrôle de gestion', 'controle gestion', 'business controller']):
        return 'controle_gestion'
    elif any(word in text for word in ['consolidation', 'consolidateur']):
        return 'consolidation'
    elif any(word in text for word in ['audit', 'auditeur']):
        return 'audit'
    elif any(word in text for word in ['epm', 'anaplan', 'hyperion', 'planning']):
        return 'epm'
    elif any(word in text for word in ['bi', 'business intelligence', 'data', 'analytics']):
        return 'bi_data'
    elif any(word in text for word in ['comptable', 'comptabilité', 'accounting']):
        return 'comptabilite'
    else:
        return 'general'


def get_relevant_pain_point(job_category, job_posting_data):
    """
    VERSION V27.3 : Pain points adaptés par secteur + validation stricte
    """
    if job_category not in PAIN_POINTS_DETAILED:
        return {
            'short': "recrutement complexe sur ce type de poste",
            'context': "Difficulté à trouver des profils qui combinent expertise technique et vision business."
        }
    
    pain_points = PAIN_POINTS_DETAILED[job_category]
    
    if not job_posting_data:
        # Retourner le premier pain point générique
        for key, pain_point in pain_points.items():
            if 'data' not in key.lower() and 'tool' not in key.lower():
                return pain_point
        return list(pain_points.values())[0]
    
    job_text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}".lower()
    sector_code = detect_company_sector(job_posting_data)
    
    # Validation pré-requis
    pain_point_prerequisites = {
        'data_driven': ['data', 'analytics', 'python', 'r', 'data science', 'machine learning'],
        'tool_adoption': ['epm', 'tagetik', 'anaplan', 'jedox', 'hyperion', 'onestream'],
        'excel_dependency': ['excel', 'tableur', 'spreadsheet'],
        'transformation_project': ['transformation', 'migration', 'déploiement']
    }
    
    # Exclusions par secteur
    sector_exclusions = {
        'logistics_transport': ['industrial_processes'],  # Logistique ≠ Industrie
        'services': ['industrial_processes'],
        'fintech': ['industrial_processes']
    }
    
    valid_pain_points = {}
    
    for pain_key, pain_point in pain_points.items():
        # Exclure par secteur
        if sector_code in sector_exclusions:
            if any(excl in pain_key.lower() for excl in sector_exclusions[sector_code]):
                continue
        
        # Vérifier pré-requis
        requires_keywords = False
        for prereq_key, keywords in pain_point_prerequisites.items():
            if prereq_key in pain_key.lower():
                requires_keywords = True
                if not any(kw in job_text for kw in keywords):
                    break  # Exclure ce pain point
                else:
                    valid_pain_points[pain_key] = pain_point
                    break
        
        if not requires_keywords:
            valid_pain_points[pain_key] = pain_point
    
    if not valid_pain_points:
        return {
            'short': "recrutement complexe sur ce type de poste",
            'context': "Difficulté à trouver des profils qui combinent expertise technique et compréhension métier."
        }
    
    # Scoring
    scoring_keywords = {
        'logistics': ['logistique', 'supply chain', 'transport', 'freight'],
        'multi_site': ['multi-sites', 'filiales', 'international', 'pays'],
        'industrial': ['production', 'manufacturing', 'usine'],
        'banking': ['bancaire', 'bank', 'cib'],
        'certifications': ['cia', 'iia', 'coso', 'ifrs']
    }
    
    pain_scores = {}
    for pain_key, pain_point in valid_pain_points.items():
        score = sum(1 for category_kws in scoring_keywords.values() 
                   for kw in category_kws if kw in job_text)
        pain_scores[pain_key] = score
    
    best_pain_key = max(pain_scores.items(), key=lambda x: x[1])[0]
    return valid_pain_points[best_pain_key]


def get_relevant_outcomes(job_category, max_outcomes=2):
    """Récupère les outcomes pertinents"""
    outcomes = OUTCOMES_DETAILED.get(job_category, OUTCOMES_DETAILED['general'])
    return outcomes[:max_outcomes]


# ========================================
# MATCHING FLEXIBLE
# ========================================

def flexible_match(keyword, text):
    """
    Match flexible : insensible à la casse, espaces, tirets
    Exemple : 'power bi' matchera 'PowerBI', 'Power-BI', 'power bi'
    """
    pattern = re.escape(keyword).replace(r'\ ', r'[\s\-_]*')
    return bool(re.search(pattern, text, re.IGNORECASE))


# ========================================
# EXTRACTION PURE DES OUTILS (V27.2)
# ========================================

def extract_all_keywords_from_job(job_posting_data):
    """
    ÉTAPE 1 : Extraction brute de TOUS les mots-clés potentiels
    VERSION V27.2 : Extraction pure sans interprétation
    """
    if not job_posting_data:
        return {'acronyms': [], 'capitalized': [], 'technical': []}
    
    job_text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}"
    
    # 1. ACRONYMES (2-10 lettres majuscules)
    acronyms = re.findall(r'\b[A-Z]{2,10}\b', job_text)
    
    # 2. MOTS CAPITALISÉS (noms propres, outils)
    capitalized = re.findall(r'\b[A-Z][a-z]+\b', job_text)
    
    # 3. EXPRESSIONS ENTRE PARENTHÈSES (souvent des listes d'outils)
    in_parens = re.findall(r'\(([^)]+)\)', job_text)
    technical_terms = []
    for content in in_parens:
        items = [item.strip() for item in content.split(',')]
        technical_terms.extend(items)
    
    return {
        'acronyms': list(set(acronyms)),
        'capitalized': list(set(capitalized)),
        'technical': technical_terms
    }


def filter_real_tools(extracted_keywords):
    """
    ÉTAPE 2 : Filtrage pour ne garder QUE les vrais outils
    VERSION V27.2 : Liste blanche + détection intelligente
    """
    
    # LISTE BLANCHE : Outils connus avec certitude
    KNOWN_TOOLS = {
        # EPM / Planning
        'Pigment', 'Jedox', 'Lucanet', 'Tagetik', 'Anaplan', 'Hyperion', 
        'OneStream', 'Board', 'Prophix',
        # ERP
        'SAP', 'Oracle', 'Sage', 'Dynamics', 'NetSuite', 'Infor',
        # BI / Analytics
        'Tableau', 'Qlik', 'Spotfire', 'Looker', 'Microstrategy',
        'Power BI', 'PowerBI', 'Power', 'BI',
        # Langages
        'Python', 'SQL', 'VBA', 'R',
        # Office / Productivité
        'Excel', 'Power Query', 'Power Pivot', 'PowerQuery',
        # Autres outils métier
        'Coupa', 'Ariba', 'Concur', 'Workday', 'Salesforce', 'Kyriba',
        'Blackline', 'Trintech'
    }
    
    # LISTE NOIRE : Faux positifs à exclure systématiquement
    EXCLUDE_LIST = {
        # Géographie
        'USA', 'UK', 'France', 'Paris', 'Europe', 'Germany', 'Spain',
        # Rôles / Titres
        'CEO', 'CFO', 'COO', 'CTO', 'DAF', 'RAF', 'DRH', 'CDO', 'CMO',
        # Contrats
        'CDI', 'CDD', 'VIE', 'Stage', 'Interim',
        # Indicateurs / KPI
        'KPI', 'ROI', 'EBITDA', 'CAPEX', 'OPEX', 'SLA',
        # Organisations
        'ETI', 'PME', 'TPE', 'SME', 'BU', 'CODIR',
        # Départements
        'IT', 'HR', 'RH', 'FTE', 'R&D', 'RD',
        # Divers
        'RTT', 'CV', 'PDF', 'EUR', 'USD', 'GBP',
        # Mots génériques
        'Groupe', 'Group', 'Company', 'International', 'Global',
        # Certifications (pas des outils)
        'PMP', 'SAFe', 'Scrum', 'Agile', 'PRINCE2'
    }
    
    detected_tools = []
    
    # Collecter tous les mots-clés
    all_keywords = (
        extracted_keywords.get('acronyms', []) + 
        extracted_keywords.get('capitalized', []) + 
        extracted_keywords.get('technical', [])
    )
    
    for keyword in all_keywords:
        keyword_clean = keyword.strip()
        
        # Ignorer vide ou trop court
        if not keyword_clean or len(keyword_clean) < 2:
            continue
        
        # Si dans liste blanche → garder
        if keyword_clean in KNOWN_TOOLS:
            if keyword_clean not in detected_tools:
                detected_tools.append(keyword_clean)
        
        # Si dans liste noire → ignorer
        elif keyword_clean in EXCLUDE_LIST:
            continue
    
    # Post-traitement : fusionner "Power" + "BI" en "Power BI"
    if 'Power' in detected_tools and 'BI' in detected_tools:
        detected_tools.remove('Power')
        detected_tools.remove('BI')
        if 'Power BI' not in detected_tools:
            detected_tools.append('Power BI')
    
    # Dédupliquer
    detected_tools = list(set(detected_tools))
    
    log_event('tools_filtered_v27_3', {
        'raw_count': len(all_keywords),
        'filtered_count': len(detected_tools),
        'tools': detected_tools
    })
    
    return detected_tools


def extract_key_skills_from_job(job_posting_data, job_category):
    """
    VERSION V27.3 : Extraction enrichie avec secteur + certifications
    """
    skills = {
        'tools': [],
        'technical': [],
        'soft': [],
        'certifications': [],
        'sector': 'le secteur',
        'sector_code': 'general',
        'context': []
    }
    
    if not job_posting_data:
        return skills
    
    job_text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}".lower()
    
    # ÉTAPE 1 : Détection secteur
    skills['sector_code'] = detect_company_sector(job_posting_data)
    
    # ÉTAPE 2 : Extraction outils
    extracted = extract_all_keywords_from_job(job_posting_data)
    detected_tools = filter_real_tools(extracted)
    skills['tools'] = detected_tools
    
    # ÉTAPE 3 : Certifications et normes
    skills['certifications'] = extract_certifications_and_norms(job_posting_data)
    
    # ÉTAPE 4 : Compétences techniques
    technical_keywords = {
        'consolidation': 'consolidation',
        'ifrs': 'normes IFRS',
        'gaap': 'normes GAAP',
        'sox': 'contrôles SOX',
        'budget': 'budget',
        'forecast': 'forecast',
        'clôture': 'clôture',
        'reporting': 'reporting',
        'fp&a': 'FP&A',
        'business partnering': 'business partnering',
        'audit interne': 'audit interne',
        'audit financier': 'audit financier',
        'contrôle interne': 'contrôle interne',
        'trésorerie': 'trésorerie',
        'supply chain': 'supply chain',
        'processus opérationnels': 'processus opérationnels'
    }
    
    for keyword, tech_name in technical_keywords.items():
        if flexible_match(keyword, job_text):
            if tech_name not in skills['technical']:
                skills['technical'].append(tech_name)
    
    # ÉTAPE 5 : Soft skills
    soft_keywords = {
        'change management': 'change management',
        'conduite du changement': 'conduite du changement',
        'adoption': 'adoption utilisateurs',
        'formation': 'formation',
        'pédagogie': 'pédagogie',
        'communication': 'communication',
        'stakeholder': 'stakeholder management',
        'accompagnement': 'accompagnement',
        'acculturation': 'acculturation',
        'agile': 'méthodologie Agile',
        'scrum': 'Scrum',
        'project management': 'project management',
        'autonomie': 'autonomie',
        'rigueur': 'rigueur',
        'animation': 'animation'
    }
    
    for keyword, soft_name in soft_keywords.items():
        if flexible_match(keyword, job_text):
            if soft_name not in skills['soft']:
                skills['soft'].append(soft_name)
    
    # ÉTAPE 6 : Contexte secteur
    sector_contexts = {
        'banking': ('le secteur bancaire', ['environnement bancaire', 'réglementation bancaire', 'CIB']),
        'insurance': ('l\'assurance', ['compagnie d\'assurance', 'Solvabilité II']),
        'logistics_transport': ('la logistique et le transport', ['supply chain', 'opérations logistiques', 'réseau international']),
        'manufacturing': ('l\'industrie', ['sites de production', 'manufacturing', 'environnement industriel']),
        'engineering': ('l\'ingénierie', ['infrastructure', 'construction', 'projets d\'envergure']),
        'retail': ('le retail', ['réseau multi-sites', 'distribution']),
        'fintech': ('la fintech', ['startup fintech', 'scale-up', 'innovation financière']),
        'services': ('les services', ['conseil', 'prestations'])
    }
    
    if skills['sector_code'] in sector_contexts:
        skills['sector'], skills['context'] = sector_contexts[skills['sector_code']]
    else:
        skills['sector'] = 'le secteur'
        skills['context'] = ['grand groupe', 'international']
    
    log_event('skills_extracted_v27_3', {
        'tools': skills['tools'],
        'certifications': skills['certifications'],
        'sector': skills['sector_code']
    })
    
    return skills


# ========================================
# FONCTIONS UTILITAIRES
# ========================================

def get_safe_firstname(prospect_data):
    """
    Trouve le prénom (détective amélioré)
    VERSION V27 : Gestion correcte des champs Leonar
    """
    # Essayer différents champs possibles
    target_keys = [
        'first_name', 'firstname', 'first name', 
        'prénom', 'prenom', 'name',
        'user_first_name', 'user_firstname'  # Champs Leonar
    ]
    
    for key, value in prospect_data.items():
        if str(key).lower().strip() in target_keys:
            if value and str(value).strip():
                return str(value).strip().capitalize()
    
    # Dernier recours : essayer de splitter full_name
    full_name = prospect_data.get('full_name') or prospect_data.get('user_full_name')
    if full_name and ' ' in str(full_name):
        parts = str(full_name).split()
        if len(parts) >= 1:
            return parts[0].capitalize()
    
    return "[Prénom]"


def get_smart_context(job_posting_data, prospect_data):
    """Définit le sujet de la discussion"""
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


# ========================================
# 1. GÉNÉRATEUR D'OBJETS (ENRICHI)
# ========================================

def generate_subject_lines(prospect_data, job_posting_data):
    """Génère les objets d'email axés pain points avec détection enrichie"""
    
    log_event('generate_subject_lines_start', {
        'prospect': prospect_data.get('_id', 'unknown')
    })
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    context_name, is_hiring = get_smart_context(job_posting_data, prospect_data)
    job_category = detect_job_category(prospect_data, job_posting_data)
    pain_point = get_relevant_pain_point(job_category, job_posting_data)
    
    # Extraction mots-clés enrichie
    skills = extract_key_skills_from_job(job_posting_data, job_category)
    detected_keywords = skills['tools'] + skills['technical'][:3] + skills['soft'][:2]
    
    log_event('keywords_detected', {
        'count': len(detected_keywords),
        'keywords': detected_keywords
    })
    
    if is_hiring:
        prompt_type = "recrutement actif"
        subject_focus = f"Poste : {context_name}"
    else:
        prompt_type = "approche spontanée"
        subject_focus = f"Sujet : {context_name}"
    
    job_title = job_posting_data.get('title', 'N/A') if job_posting_data else 'N/A'
    
    prompt = f"""Tu es expert en copywriting B2B pour cabinet de recrutement Finance.

CONTEXTE :
{prompt_type.capitalize()}
{subject_focus}
Entreprise : {prospect_data.get('company', 'l\'entreprise')}
Métier détecté : {job_category}

FICHE DE POSTE :
Titre : {job_title}

MOTS-CLÉS DÉTECTÉS (à intégrer dans les objets) :
{', '.join(detected_keywords[:10]) if detected_keywords else 'Aucun mot-clé spécifique détecté'}

PAIN POINT CONTEXTUEL :
{pain_point['short']}

CONSIGNE :
Génère 3 objets d'email courts (40-60 caractères) qui :
1. Mentionnent les MOTS-CLÉS DÉTECTÉS (outils, secteur, compétences spécifiques)
2. Évoquent le pain point de manière INTERROGATIVE
3. Restent sobres et professionnels

IMPÉRATIF : Si un outil/secteur spécifique est détecté (Tagetik, SAP, bancaire, IA, Agile, etc.), 
AU MOINS UN des objets DOIT le mentionner explicitement !

FORMAT ATTENDU :
1. [Question avec mot-clé outil/secteur OU pain point]
2. [Constat marché avec compétence spécifique]
3. [Objet direct : "Re: [titre poste]"]

EXEMPLES SELON CONTEXTE :

Si Tagetik/EPM détecté :
1. EPM : profils Tech OU Fonctionnel ?
2. Adoption Tagetik : le vrai défi
3. Re: {job_title}

Si IA/Data Science détecté :
1. IA : technique ET business ?
2. Cas d'usage IA : acculturation métiers
3. Re: {job_title}

Si Agile/Scrum détecté :
1. EPM + Agile : profils hybrides rares
2. SAFe : finance + project management
3. Re: {job_title}

Si comptabilité bancaire :
1. Comptabilité bancaire : marché tendu
2. Clôtures réglementaires : profils rares
3. Re: {job_title}

Si consolidation IFRS :
1. Consolidation : Excel ou outil groupe ?
2. IFRS : expertise + pédagogie filiales
3. Re: {job_title}

INTERDICTIONS :
❌ Pas de "Opportunité", "Proposition", "Collaboration"
❌ Pas de points d'exclamation
❌ Pas de promesses directes
❌ Pas de "Notre cabinet"

Génère les 3 objets (numérotés 1, 2, 3) :"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        
        tracker.track(message.usage, 'generate_subject_lines')
        result = message.content[0].text.strip()
        
        log_event('generate_subject_lines_success', {'length': len(result)})
        return result
        
    except anthropic.APIError as e:
        log_error('claude_api_error', str(e), {'function': 'generate_subject_lines'})
        return f"1. {pain_point['short'][:50]}\n2. {context_name} - Profils qualifiés\n3. Re: {context_name}"
    
    except Exception as e:
        log_error('unexpected_error', str(e), {'function': 'generate_subject_lines'})
        return f"Re: {context_name}"


# ========================================
# 2. MESSAGE 2 : LA PROPOSITION (V27.3 OPTIMISÉ)
# ========================================

def generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content):
    """
    Génère le message 2 avec 2 profils TOUJOURS ultra-différenciés
    VERSION V27.3 : Secteur + certifications + outils exacts
    """
    
    log_event('generate_message_2_start', {
        'prospect': prospect_data.get('_id', 'unknown'),
        'has_hooks': hooks_data != "NOT_FOUND"
    })
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    first_name = get_safe_firstname(prospect_data)
    context_name, is_hiring = get_smart_context(job_posting_data, prospect_data)
    job_category = detect_job_category(prospect_data, job_posting_data)
    pain_point = get_relevant_pain_point(job_category, job_posting_data)
    
    # Extraction compétences enrichie
    skills = extract_key_skills_from_job(job_posting_data, job_category)
    
    log_event('message_2_skills_extracted', {
        'tools': skills['tools'],
        'certifications': skills['certifications'],
        'technical': skills['technical'][:3],
        'soft': skills['soft'][:2],
        'sector': skills['sector_code']
    })
    
    if is_hiring:
        intro_phrase = f"Je me permets de vous relancer concernant votre recherche de {context_name}."
    else:
        intro_phrase = f"Je reviens vers vous concernant la structuration de {context_name}."
    
    # Préparer les compétences pour le prompt
    if skills['tools']:
        tools_str = ', '.join(skills['tools'][:5])
        no_tools_warning = ""
    else:
        tools_str = 'AUCUN OUTIL SPÉCIFIQUE DÉTECTÉ'
        no_tools_warning = """
⚠️  AUCUN OUTIL DÉTECTÉ → NE MENTIONNE AUCUN OUTIL DANS LE MESSAGE
Focus uniquement sur les compétences métier et le contexte."""
    
    technical_str = ', '.join(skills['technical'][:5]) if skills['technical'] else 'compétences métier générales'
    certs_str = ', '.join(skills['certifications']) if skills['certifications'] else 'Aucune'
    
    prompt = f"""Tu es chasseur de têtes spécialisé Finance.

CONTEXTE :
Prospect : {first_name}
Poste : {context_name}
Secteur détecté : {skills['sector_code']}

OUTILS DÉTECTÉS : {tools_str}
CERTIFICATIONS DÉTECTÉES : {certs_str}
COMPÉTENCES TECHNIQUES : {technical_str}

🚨 RÈGLES ABSOLUES :

1. Utilise UNIQUEMENT les outils listés ci-dessus
2. Utilise UNIQUEMENT les certifications listées ci-dessus
3. Si outils = AUCUN → NE MENTIONNE AUCUN OUTIL
4. Adapte le secteur des profils au secteur détecté

FORMAT OBLIGATOIRE :
"J'ai identifié 2 profils qui pourraient retenir votre attention :
- L'un [profil 1 avec outils/certifications exacts]
- L'autre [profil 2 parcours différent]"

EXEMPLES PAR SECTEUR :

🏦 Banking :
"- L'un possède 8 ans d'audit interne bancaire (CIB, retail banking) avec certification CIA et expertise normes BPCE"

🚚 Logistique :
"- L'un dispose de 7 ans d'audit opérationnel supply chain chez un groupe de transport international (40+ pays)"

🏭 Industrie :
"- L'un possède 6 ans d'audit interne en groupe industriel (15 sites de production européens)"

STRUCTURE (100-120 mots max) :
1. "Bonjour {first_name},"
2. SAUT DE LIGNE
3. "{intro_phrase}"
4. SAUT DE LIGNE
5. Observation marché ULTRA-SPÉCIFIQUE (30-40 mots)
6. SAUT DE LIGNE
7. Proposition de 2 PROFILS avec outils/certifications exacts
8. SAUT DE LIGNE
9. "Seriez-vous d'accord pour recevoir leurs synthèses anonymisées ? Cela vous permettrait de juger leur pertinence en 30 secondes."
10. SAUT DE LIGNE
11. "Bien à vous,"

Génère le message (100-120 mots max) :"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}]
        )
        
        tracker.track(message.usage, 'generate_message_2')
        result = message.content[0].text.strip()
        
        # Vérification post-génération
        if "2 profils" not in result.lower() and "deux profils" not in result.lower():
            log_event('message_2_missing_profiles', {
                'prospect': prospect_data.get('_id', 'unknown'),
                'message_preview': result[:200]
            })
            
            print("⚠️  Message 2 sans profils détecté - Régénération avec fallback intelligent...")
            result = generate_message_2_fallback(first_name, context_name, is_hiring, 
                                                  job_posting_data, skills, pain_point)
        
        log_event('generate_message_2_success', {'length': len(result)})
        return result
        
    except anthropic.APIError as e:
        log_error('claude_api_error', str(e), {'function': 'generate_message_2'})
        return generate_message_2_fallback(first_name, context_name, is_hiring, 
                                          job_posting_data, skills, pain_point)
    
    except Exception as e:
        log_error('unexpected_error', str(e), {'function': 'generate_message_2'})
        return generate_message_2_fallback(first_name, context_name, is_hiring, 
                                          job_posting_data, skills, pain_point)


def generate_message_2_fallback(first_name, context_name, is_hiring, job_posting_data, skills, pain_point):
    """
    Fallback intelligent pour Message 2
    VERSION V27.3 : Utilise secteur + certifications + outils
    """
    log_event('message_2_fallback_triggered', {
        'reason': 'API error or validation failed'
    })
    
    if is_hiring:
        intro = f"Je me permets de vous relancer concernant votre recherche de {context_name}."
    else:
        intro = f"Je reviens vers vous concernant la structuration de {context_name}."
    
    # Construire l'observation avec les compétences détectées
    if skills['tools'] and skills['technical']:
        observation = f"Le marché combine difficilement {skills['technical'][0] if skills['technical'] else 'expertise technique'} ({', '.join(skills['tools'][:2])}) et {skills['soft'][0] if skills['soft'] else 'compétences transverses'} dans {skills['sector']}."
    else:
        observation = f"Le défi principal réside dans {pain_point['short']}."
    
    # Générer 2 profils crédibles basés sur les compétences
    tool_1 = skills['tools'][0] if skills['tools'] else 'outils métier'
    tool_2 = skills['tools'][1] if len(skills['tools']) > 1 else 'Excel avancé'
    tech_1 = skills['technical'][0] if skills['technical'] else 'expertise technique'
    tech_2 = skills['technical'][1] if len(skills['technical']) > 1 else 'maîtrise opérationnelle'
    soft_1 = skills['soft'][0] if skills['soft'] else 'conduite du changement'
    context_1 = skills['context'][0] if skills['context'] else 'grand groupe'
    context_2 = skills['context'][1] if len(skills['context']) > 1 else 'environnement international'
    cert_1 = skills['certifications'][0] if skills['certifications'] else None
    
    if cert_1:
        profile_1 = f"- L'un possède une expertise {tech_1} avec maîtrise de {tool_1} et certification {cert_1}, ayant piloté des projets de transformation dans un {context_1} avec forte autonomie opérationnelle."
    else:
        profile_1 = f"- L'un possède une expertise {tech_1} avec maîtrise de {tool_1}, ayant piloté des projets de transformation dans un {context_1} avec forte autonomie opérationnelle."
    
    profile_2 = f"- L'autre combine {tech_2} et {soft_1}, issu d'un {context_2} avec expérience significative en {tool_2} et accompagnement d'équipes."
    
    message = f"""Bonjour {first_name},

{intro}

{observation}

J'ai identifié 2 profils qui pourraient retenir votre attention :
{profile_1}
{profile_2}

Seriez-vous d'accord pour recevoir leurs synthèses anonymisées ? Cela vous permettrait de juger leur pertinence en 30 secondes.

Bien à vous,"""
    
    log_event('message_2_fallback_generated', {
        'length': len(message)
    })
    
    return message


# ========================================
# 3. MESSAGE 3 : BREAK-UP (TEMPLATE FIXE V27)
# ========================================

def generate_message_3(prospect_data, message_1_content, job_posting_data):
    """
    Génère le message 3 - TOUJOURS LE MÊME (seul le prénom change)
    VERSION V27 : Template fixe immuable
    """
    
    log_event('generate_message_3_start', {
        'prospect': prospect_data.get('_id', 'unknown')
    })
    
    first_name = get_safe_firstname(prospect_data)
    
    # MESSAGE 3 FIXE - NE JAMAIS MODIFIER
    message_3_template = f"""Bonjour {first_name},

Je comprends que vous n'ayez pas eu le temps de revenir vers moi — je sais à quel point vos fonctions sont sollicitées.

Avant de clore le dossier de mon côté, une dernière question : Est-ce que le timing n'est simplement pas bon pour l'instant, ou bien travaillez-vous déjà avec d'autres cabinets/recruteurs sur ce poste ?

Si c'est une question de timing, je serai ravi de reprendre contact dans quelques semaines.

Si vous préférez gérer ce recrutement autrement, aucun souci — je vous souhaite de trouver la perle rare rapidement.

Merci en tous cas pour votre attention,

Bonne continuation,"""
    
    log_event('generate_message_3_success', {
        'length': len(message_3_template)
    })
    
    return message_3_template


# ========================================
# FONCTION PRINCIPALE
# ========================================

def generate_full_sequence(prospect_data, hooks_data, job_posting_data, message_1_content):
    """Génère une séquence complète avec validation"""
    
    log_event('sequence_generation_start', {
        'prospect_id': prospect_data.get('_id', 'unknown'),
        'prospect_name': prospect_data.get('full_name', 'unknown'),
        'company': prospect_data.get('company', 'unknown'),
        'has_job_posting': bool(job_posting_data),
        'has_hooks': hooks_data != "NOT_FOUND"
    })
    
    try:
        subject_lines = generate_subject_lines(prospect_data, job_posting_data)
        message_2 = generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content)
        message_3 = generate_message_3(prospect_data, message_1_content, job_posting_data)
        
        sequence = {
            'subject_lines': subject_lines,
            'message_1': message_1_content,
            'message_2': message_2,
            'message_3': message_3
        }
        
        is_valid = validate_and_report(sequence, prospect_data, raise_on_error=False)
        
        if not is_valid:
            log_event('sequence_validation_warning', {
                'prospect': prospect_data.get('_id', 'unknown'),
                'message': 'Validation failed but sequence returned anyway'
            })
        
        log_event('sequence_generation_success', {
            'prospect_id': prospect_data.get('_id', 'unknown')
        })
        
        return sequence
        
    except Exception as e:
        log_error('sequence_generation_failed', str(e), {
            'prospect_id': prospect_data.get('_id', 'unknown')
        })
        raise