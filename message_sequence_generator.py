"""
═══════════════════════════════════════════════════════════════════
MESSAGE SEQUENCE GENERATOR - V27.4 (CORRECTIONS QUALITÉ)
Modifications V27.4 :
- filter_recent_posts() : parsing dates multi-format + fallback
- detect_company_sector() : keywords enrichis (GEODIS→logistics)
- detect_job_category() : priorité TITRE > description
- filter_real_tools() : SAP BFC, Power Query, TCD ajoutés
- extract_certifications_and_norms() : CIA, IIA, COSO enrichis
- Pain points validés par secteur (pas industrie pour logistique)
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
# FILTRAGE HOOKS LINKEDIN - V27.4 ROBUSTE
# ========================================

def filter_recent_posts(posts, max_age_months=3, max_posts=5):
    """
    Filtre les posts LinkedIn pour ne garder que ceux <3 mois
    VERSION V27.4 : Parsing dates ROBUSTE multi-format + fallback intelligent
    """
    if not posts or posts == "NOT_FOUND":
        return []
    
    if not isinstance(posts, list):
        return []
    
    cutoff_date = datetime.now() - timedelta(days=max_age_months * 30)
    recent_posts = []
    posts_without_date = []
    
    for post in posts:
        if not isinstance(post, dict):
            continue
            
        # Chercher la date dans plusieurs champs possibles
        post_date_str = (
            post.get('date') or 
            post.get('postedDate') or 
            post.get('timestamp') or
            post.get('publishedAt') or
            post.get('created_at') or
            ''
        )
        
        if not post_date_str:
            # Pas de date → garder pour fallback
            posts_without_date.append(post)
            continue
        
        # Parser la date avec plusieurs formats
        post_date = None
        date_formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%B %d, %Y',  # "January 15, 2026"
            '%b %d, %Y',  # "Jan 15, 2026"
        ]
        
        for fmt in date_formats:
            try:
                # Tronquer à 10 caractères pour formats date seule
                date_to_parse = str(post_date_str)
                if fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                    date_to_parse = date_to_parse[:10]
                
                post_date = datetime.strptime(date_to_parse, fmt)
                break
            except (ValueError, TypeError):
                continue
        
        # Essayer de parser les dates relatives ("il y a 2 jours", "2d", "3w")
        if not post_date:
            relative_date = parse_relative_date(str(post_date_str))
            if relative_date:
                post_date = relative_date
        
        # Vérifier si la date est récente
        if post_date and post_date >= cutoff_date:
            recent_posts.append(post)
        elif post_date:
            log_event('post_filtered_old', {
                'date': str(post_date_str),
                'parsed': post_date.strftime('%Y-%m-%d') if post_date else 'N/A',
                'cutoff': cutoff_date.strftime('%Y-%m-%d')
            })
    
    # Si aucun post récent mais des posts sans date → prendre les premiers (risque assumé)
    if not recent_posts and posts_without_date:
        log_event('using_posts_without_date', {
            'count': min(max_posts, len(posts_without_date)),
            'reason': 'No dated posts found within cutoff'
        })
        recent_posts = posts_without_date[:max_posts]
    
    # Trier par date décroissante et limiter
    def get_sort_date(p):
        d = p.get('date') or p.get('postedDate') or p.get('timestamp') or '1900-01-01'
        return str(d)
    
    recent_posts = sorted(recent_posts, key=get_sort_date, reverse=True)[:max_posts]
    
    log_event('posts_filtered_v27_4', {
        'total_input': len(posts),
        'recent_output': len(recent_posts),
        'without_date': len(posts_without_date),
        'cutoff_date': cutoff_date.strftime('%Y-%m-%d')
    })
    
    return recent_posts


def parse_relative_date(date_str):
    """
    Parse les dates relatives LinkedIn ("2d", "1w", "3mo", "il y a 2 jours")
    VERSION V27.4 : Support multi-langue
    """
    if not date_str:
        return None
    
    date_str_lower = date_str.lower().strip()
    now = datetime.now()
    
    # Patterns anglais
    patterns_en = [
        (r'(\d+)\s*d(?:ay)?s?\s*ago', 'days'),
        (r'(\d+)\s*w(?:eek)?s?\s*ago', 'weeks'),
        (r'(\d+)\s*mo(?:nth)?s?\s*ago', 'months'),
        (r'(\d+)\s*h(?:our)?s?\s*ago', 'hours'),
        (r'(\d+)d\b', 'days'),
        (r'(\d+)w\b', 'weeks'),
        (r'(\d+)mo\b', 'months'),
        (r'(\d+)h\b', 'hours'),
    ]
    
    # Patterns français
    patterns_fr = [
        (r'il y a (\d+)\s*jour', 'days'),
        (r'il y a (\d+)\s*semaine', 'weeks'),
        (r'il y a (\d+)\s*mois', 'months'),
        (r'il y a (\d+)\s*heure', 'hours'),
    ]
    
    all_patterns = patterns_en + patterns_fr
    
    for pattern, unit in all_patterns:
        match = re.search(pattern, date_str_lower)
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
    
    return None


# ========================================
# DÉTECTION SECTEUR - V27.4 ENRICHIE
# ========================================

def detect_company_sector(job_posting_data):
    """
    Détecte le secteur de l'entreprise
    VERSION V27.4 : Keywords enrichis + detection sans API call
    """
    if not job_posting_data:
        return 'general'
    
    text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}".lower()
    
    # ════════════════════════════════════════════════════════════════
    # DÉTECTION PAR MOTS-CLÉS (PRIORITÉ)
    # ════════════════════════════════════════════════════════════════
    
    sector_keywords = {
        'banking': [
            'banque', 'bank', 'bancaire', 'banking', 'cib', 'retail banking',
            'private banking', 'bpce', 'bnp', 'société générale', 'crédit agricole',
            'crédit mutuel', 'lcl', 'caisse d\'épargne', 'natixis', 'hsbc',
            'banque palatine', 'banque populaire'
        ],
        'insurance': [
            'assurance', 'insurance', 'mutuelle', 'iard', 'prévoyance',
            'solvabilité', 'solvency', 'actuariat', 'actuariel', 'sinistre',
            'cnp', 'axa', 'allianz', 'generali', 'groupama', 'maif', 'macif',
            'covéa', 'ag2r', 'malakoff', 'kereis', 'camca'
        ],
        'logistics_transport': [
            'logistique', 'logistics', 'supply chain', 'transport', 'freight',
            'fret', 'entrepôt', 'warehouse', 'distribution', 'livraison',
            'geodis', 'dhl', 'fedex', 'ups', 'kuehne', 'db schenker',
            'ceva logistics', 'xpo', 'stef', 'id logistics', 'fm logistic',
            '166 pays', '120 pays', 'réseau mondial', 'hub logistique'
        ],
        'manufacturing': [
            'industrie', 'industriel', 'manufacturing', 'production', 'usine',
            'factory', 'fabrication', 'sites de production', 'atelier',
            'tarkett', 'michelin', 'renault', 'psa', 'stellantis', 'safran',
            'airbus', 'saint-gobain', 'schneider', 'legrand', 'valeo',
            '35 sites', '50 usines', 'sites industriels'
        ],
        'engineering': [
            'ingénierie', 'engineering', 'btp', 'construction', 'infrastructure',
            'travaux publics', 'génie civil', 'bureau d\'études',
            'egis', 'vinci', 'bouygues', 'eiffage', 'colas', 'spie',
            'artelia', 'setec', 'systra', 'arcadis', 'aecom',
            'concession', 'autoroute', 'pont', 'tunnel'
        ],
        'retail': [
            'retail', 'distribution', 'grande distribution', 'magasin',
            'commerce', 'enseigne', 'point de vente', 'réseau de vente',
            'carrefour', 'auchan', 'leclerc', 'intermarché', 'casino',
            'fnac', 'darty', 'decathlon', 'leroy merlin', 'ikea'
        ],
        'fintech': [
            'fintech', 'néobanque', 'neobank', 'payment', 'paiement',
            'crypto', 'blockchain', 'startup', 'scale-up', 'licorne',
            'memo bank', 'qonto', 'lydia', 'revolut', 'n26', 'alan',
            'pennylane', 'payfit', 'spendesk', 'swile'
        ],
        'gaming': [
            'jeu vidéo', 'video game', 'gaming', 'game studio', 'éditeur de jeux',
            'ubisoft', 'activision', 'electronic arts', 'ea', 'gameloft',
            'don\'t nod', 'focus entertainment', 'nacon', 'bigben'
        ],
        'services': [
            'conseil', 'consulting', 'cabinet', 'services professionnels',
            'audit externe', 'expertise comptable', 'commissariat aux comptes',
            'big 4', 'big four', 'deloitte', 'ey', 'kpmg', 'pwc', 'mazars',
            'grant thornton', 'bdo', 'rsm'
        ]
    }
    
    # Scorer chaque secteur
    sector_scores = {sector: 0 for sector in sector_keywords}
    
    for sector, keywords in sector_keywords.items():
        for keyword in keywords:
            if keyword in text:
                # Bonus si dans le nom d'entreprise (plus fiable)
                company_name = job_posting_data.get('company', '').lower()
                if keyword in company_name:
                    sector_scores[sector] += 3
                else:
                    sector_scores[sector] += 1
    
    # Trouver le secteur dominant
    max_score = max(sector_scores.values())
    
    if max_score >= 2:
        detected_sector = max(sector_scores.items(), key=lambda x: x[1])[0]
        log_event('sector_detected_v27_4', {
            'sector': detected_sector,
            'score': max_score,
            'all_scores': {k: v for k, v in sector_scores.items() if v > 0}
        })
        return detected_sector
    
    log_event('sector_fallback_general', {'reason': 'No sector keywords found'})
    return 'general'


# ========================================
# EXTRACTION OUTILS - V27.4 ENRICHIE
# ========================================

def extract_all_keywords_from_job(job_posting_data):
    """
    ÉTAPE 1 : Extraction brute de TOUS les mots-clés potentiels
    VERSION V27.4 : Patterns enrichis
    """
    if not job_posting_data:
        return {'acronyms': [], 'capitalized': [], 'technical': []}
    
    job_text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}"
    
    # 1. ACRONYMES (2-10 lettres majuscules)
    acronyms = re.findall(r'\b[A-Z]{2,10}\b', job_text)
    
    # 2. MOTS CAPITALISÉS (noms propres, outils)
    capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', job_text)
    
    # 3. EXPRESSIONS ENTRE PARENTHÈSES (souvent des listes d'outils)
    in_parens = re.findall(r'\(([^)]+)\)', job_text)
    technical_terms = []
    for content in in_parens:
        items = [item.strip() for item in content.split(',')]
        technical_terms.extend(items)
    
    # 4. PATTERNS SPÉCIFIQUES V27.4
    # SAP BFC, SAP BPC, Power BI, etc.
    compound_tools = re.findall(r'\b(?:SAP|Power|Microsoft)\s+[A-Z][a-zA-Z]*\b', job_text)
    technical_terms.extend(compound_tools)
    
    return {
        'acronyms': list(set(acronyms)),
        'capitalized': list(set(capitalized)),
        'technical': list(set(technical_terms))
    }


def filter_real_tools(extracted_keywords):
    """
    ÉTAPE 2 : Filtrage pour ne garder QUE les vrais outils
    VERSION V27.4 : Liste enrichie SAP BFC, Power Query, TCD
    """
    
    # LISTE BLANCHE : Outils connus avec certitude
    KNOWN_TOOLS = {
        # EPM / Planning
        'Pigment', 'Jedox', 'Lucanet', 'Tagetik', 'Anaplan', 'Hyperion', 
        'OneStream', 'Board', 'Prophix', 'IBM Planning Analytics', 'TM1',
        
        # ERP / SAP
        'SAP', 'SAP BFC', 'SAP BPC', 'SAP S/4HANA', 'SAP FI', 'SAP CO',
        'SAP FICO', 'SAP ECC', 'SAP R/3',
        
        # ERP Autres
        'Oracle', 'Oracle EPM', 'Oracle HFM', 'Sage', 'Sage X3', 'Sage 100',
        'Dynamics', 'Dynamics 365', 'NetSuite', 'Infor', 'Cegid', 'Navision',
        
        # BI / Analytics
        'Tableau', 'Qlik', 'QlikView', 'Qlik Sense', 'Spotfire', 'Looker', 
        'Microstrategy', 'Power BI', 'PowerBI', 'Business Objects', 'BO',
        'Cognos', 'SSRS', 'SSIS', 'Alteryx',
        
        # Langages / Data
        'Python', 'SQL', 'VBA', 'R', 'SAS', 'SPSS', 'Stata',
        
        # Office / Productivité
        'Excel', 'Power Query', 'Power Pivot', 'PowerQuery', 'TCD',
        'Access', 'Macro', 'Macros Excel',
        
        # Consolidation
        'HFM', 'Hyperion Financial Management', 'FC', 'Magnitude',
        'Sigma Conso', 'Talentia', 'Caseware',
        
        # Autres outils métier
        'Coupa', 'Ariba', 'Concur', 'Workday', 'Salesforce', 'Kyriba',
        'Blackline', 'Trintech', 'Cadency', 'FloQast', 'Vena',
        
        # Audit
        'ACL', 'IDEA', 'TeamMate', 'AuditBoard', 'Galvanize',
        
        # Trésorerie
        'Kyriba', 'FIS', 'Finastra', 'Calypso', 'Murex', 'Summit'
    }
    
    # LISTE NOIRE : Faux positifs à exclure systématiquement
    EXCLUDE_LIST = {
        # Géographie
        'USA', 'UK', 'France', 'Paris', 'Europe', 'Germany', 'Spain',
        'Lyon', 'Marseille', 'Bordeaux', 'Toulouse', 'Nantes', 'Lille',
        
        # Rôles / Titres
        'CEO', 'CFO', 'COO', 'CTO', 'DAF', 'RAF', 'DRH', 'CDO', 'CMO',
        'Manager', 'Director', 'Head', 'Chief', 'VP', 'Senior', 'Junior',
        
        # Contrats
        'CDI', 'CDD', 'VIE', 'Stage', 'Interim', 'Alternance',
        
        # Indicateurs / KPI
        'KPI', 'ROI', 'EBITDA', 'CAPEX', 'OPEX', 'SLA', 'NPS', 'MRR', 'ARR',
        'CA', 'PNL', 'P&L', 'BS', 'CF',
        
        # Organisations
        'ETI', 'PME', 'TPE', 'SME', 'BU', 'CODIR', 'COMEX', 'CSE',
        'GIE', 'SAS', 'SA', 'SARL',
        
        # Départements
        'IT', 'HR', 'RH', 'FTE', 'R&D', 'RD', 'DSI', 'DG', 'DAF',
        
        # Normes (pas des outils)
        'IFRS', 'GAAP', 'SOX', 'COSO', 'IIA', 'ISA',
        
        # Certifications (pas des outils)
        'PMP', 'SAFe', 'Scrum', 'Agile', 'PRINCE2', 'CIA', 'CPA', 'ACCA',
        'DSCG', 'DEC', 'CISA', 'CISM',
        
        # Divers
        'RTT', 'CV', 'PDF', 'EUR', 'USD', 'GBP', 'RER', 'RATP', 'SNCF',
        'Groupe', 'Group', 'Company', 'International', 'Global',
        'CDG', 'LBP', 'BNP', 'SG'  # Entreprises, pas outils
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
        elif keyword_clean.upper() in EXCLUDE_LIST or keyword_clean in EXCLUDE_LIST:
            continue
        
        # Cas spéciaux composés
        elif keyword_clean.startswith('SAP ') or keyword_clean.startswith('Power '):
            if keyword_clean not in detected_tools:
                detected_tools.append(keyword_clean)
    
    # Post-traitement : fusionner "Power" + "BI" en "Power BI"
    if 'Power' in detected_tools and 'BI' in detected_tools:
        detected_tools.remove('Power')
        detected_tools.remove('BI')
        if 'Power BI' not in detected_tools:
            detected_tools.append('Power BI')
    
    # Dédupliquer
    detected_tools = list(set(detected_tools))
    
    log_event('tools_filtered_v27_4', {
        'raw_count': len(all_keywords),
        'filtered_count': len(detected_tools),
        'tools': detected_tools
    })
    
    return detected_tools


# ========================================
# EXTRACTION CERTIFICATIONS - V27.4 ENRICHIE
# ========================================

def extract_certifications_and_norms(job_posting_data):
    """
    Détecte les certifications et normes métier mentionnées
    VERSION V27.4 : Liste enrichie CIA, IIA, COSO, Solvabilité II
    """
    if not job_posting_data:
        return []
    
    text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}".lower()
    
    certifications = {
        # Audit
        'cia': 'CIA',
        ' cia ': 'CIA',  # Avec espaces pour éviter faux positifs
        'certified internal auditor': 'CIA',
        'cpai': 'CPAI',
        'cisa': 'CISA',
        'cism': 'CISM',
        'crma': 'CRMA',
        'cfe': 'CFE',
        
        # Normes Audit
        'normes iia': 'normes IIA',
        'standards iia': 'normes IIA',
        'iia standards': 'normes IIA',
        ' iia': 'normes IIA',
        'coso': 'COSO',
        'cadre coso': 'COSO',
        
        # Comptabilité
        'dscg': 'DSCG',
        'dec': 'DEC',
        'diplôme d\'expertise comptable': 'DEC',
        'cpa': 'CPA',
        'acca': 'ACCA',
        'cma': 'CMA',
        
        # Normes Comptables
        'ifrs': 'normes IFRS',
        'normes ifrs': 'normes IFRS',
        'gaap': 'normes GAAP',
        'us gaap': 'normes US GAAP',
        'french gaap': 'French GAAP',
        'sox': 'SOX',
        'sarbanes': 'SOX',
        
        # Assurance
        'solvabilité ii': 'Solvabilité II',
        'solvabilité 2': 'Solvabilité II',
        'solvency ii': 'Solvabilité II',
        'solvency 2': 'Solvabilité II',
        
        # Project Management
        'pmp': 'PMP',
        'prince2': 'PRINCE2',
        'safe': 'SAFe',
        'scrum master': 'Scrum Master',
        'psm': 'PSM',
        'csm': 'CSM',
        
        # Finance
        'cfa': 'CFA',
        'frm': 'FRM',
        'amf': 'certification AMF'
    }
    
    detected = []
    for cert_key, cert_name in certifications.items():
        if cert_key in text:
            if cert_name not in detected:
                detected.append(cert_name)
    
    log_event('certifications_detected_v27_4', {
        'count': len(detected),
        'certifications': detected
    })
    
    return detected


# ========================================
# DÉTECTION MÉTIER - V27.4 PRIORITÉ TITRE
# ========================================

def detect_job_category(prospect_data, job_posting_data):
    """
    Détecte automatiquement la catégorie métier du prospect
    VERSION V27.4 : PRIORITÉ TITRE > DESCRIPTION + exclusions contextuelles
    """
    
    # ÉTAPE 1 : Extraire TITRE seul (prioritaire)
    job_title = ""
    if job_posting_data:
        job_title = str(job_posting_data.get('title', '')).lower()
    
    # ÉTAPE 2 : Extraire description (secondaire)
    job_desc = ""
    if job_posting_data:
        job_desc = str(job_posting_data.get('description', '')).lower()
    
    # ÉTAPE 3 : Headline prospect (tertiaire)
    headline = f"{prospect_data.get('headline', '')} {prospect_data.get('title', '')}".lower()
    
    # ════════════════════════════════════════════════════════════════
    # DÉTECTION SUR TITRE UNIQUEMENT (PRIORITÉ ABSOLUE)
    # ════════════════════════════════════════════════════════════════
    
    # Comptable / Comptabilité (AVANT audit car "comptable" est plus spécifique)
    if any(word in job_title for word in ['comptable', 'accountant', 'accounting']):
        # EXCLUSION : "comptable" dans titre mais "consolidation" aussi → consolidation
        if 'consolidation' in job_title or 'consolidateur' in job_title:
            return 'consolidation'
        return 'comptabilite'
    
    # Audit
    if any(word in job_title for word in ['audit', 'auditeur', 'auditor']):
        return 'audit'
    
    # Consolidation
    if any(word in job_title for word in ['consolidation', 'consolidateur', 'consolidator']):
        return 'consolidation'
    
    # Contrôle de gestion
    if any(word in job_title for word in ['contrôle de gestion', 'controle de gestion', 'contrôleur de gestion', 'controller', 'business controller']):
        return 'controle_gestion'
    
    # FP&A
    if any(word in job_title for word in ['fp&a', 'fpa', 'financial planning', 'fpna']):
        return 'fpna'
    
    # DAF / CFO
    if any(word in job_title for word in ['daf', 'directeur administratif', 'cfo', 'chief financial', 'directeur financier']):
        return 'daf'
    
    # RAF
    if any(word in job_title for word in ['raf', 'responsable administratif']):
        return 'raf'
    
    # Data / IA
    if any(word in job_title for word in ['data officer', 'ia officer', 'ai officer', 'data & ia', 'chief data', 'cdo']):
        return 'data_ia'
    
    # EPM
    if any(word in job_title for word in ['epm', 'anaplan', 'hyperion', 'tagetik']):
        return 'epm'
    
    # BI / Data
    if any(word in job_title for word in ['bi ', 'business intelligence', ' data ', 'analytics']):
        return 'bi_data'
    
    # ════════════════════════════════════════════════════════════════
    # SI TITRE NON CONCLUANT → DESCRIPTION (avec exclusions)
    # ════════════════════════════════════════════════════════════════
    
    # Nettoyer la description des mentions contextuelles
    desc_cleaned = job_desc
    
    # Exclure "ou audit", "contrôles de niveau 2", etc.
    contextual_exclusions = [
        r'\bou audit\b',
        r'\baudit externe\b',
        r'\bcontrôles? de niveau \d\b',
        r'\brelation avec.*audit\b',
        r'\ben collaboration avec.*audit\b',
        r'\baudit interne et externe\b'
    ]
    
    for pattern in contextual_exclusions:
        desc_cleaned = re.sub(pattern, '', desc_cleaned, flags=re.IGNORECASE)
    
    # Maintenant chercher dans description nettoyée
    if any(word in desc_cleaned for word in ['comptable', 'comptabilité', 'accounting']) and 'audit' not in job_title:
        return 'comptabilite'
    
    if any(word in desc_cleaned for word in ['auditeur', 'audit interne', 'internal audit']):
        return 'audit'
    
    if any(word in desc_cleaned for word in ['consolidation', 'ifrs 10', 'normes ifrs']):
        return 'consolidation'
    
    if any(word in desc_cleaned for word in ['contrôle de gestion', 'business controller']):
        return 'controle_gestion'
    
    # ════════════════════════════════════════════════════════════════
    # FALLBACK : HEADLINE PROSPECT
    # ════════════════════════════════════════════════════════════════
    
    if any(word in headline for word in ['daf', 'cfo', 'directeur financier']):
        return 'daf'
    elif any(word in headline for word in ['audit']):
        return 'audit'
    elif any(word in headline for word in ['comptab']):
        return 'comptabilite'
    elif any(word in headline for word in ['contrôl']):
        return 'controle_gestion'
    
    return 'general'


# ========================================
# PAIN POINTS - V27.4 VALIDATION SECTEUR
# ========================================

def get_relevant_pain_point(job_category, job_posting_data):
    """
    VERSION V27.4 : Pain points avec validation stricte secteur
    """
    if job_category not in PAIN_POINTS_DETAILED:
        return {
            'short': "recrutement complexe sur ce type de poste",
            'context': "Difficulté à trouver des profils qui combinent expertise technique et vision business."
        }
    
    pain_points = PAIN_POINTS_DETAILED[job_category]
    
    if not job_posting_data:
        for key, pain_point in pain_points.items():
            if 'data' not in key.lower() and 'tool' not in key.lower():
                return pain_point
        return list(pain_points.values())[0]
    
    job_text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}".lower()
    sector_code = detect_company_sector(job_posting_data)
    
    # MAPPING PAIN POINTS → SECTEURS AUTORISÉS
    PAIN_POINT_SECTORS = {
        'industrial_processes': ['manufacturing', 'engineering'],  # SEULEMENT industrie
        'multi_site_international': ['all'],
        'control_internal': ['all'],
        'coverage': ['all'],
        'senior_profiles': ['all'],
        'logistics': ['logistics_transport'],  # SEULEMENT logistique
        'structuration': ['all'],
        'multi_site': ['all'],
        'business_partnering': ['all'],
        'data_quality': ['all'],
        'hybrid_profiles': ['all'],
        'ifrs_expertise': ['all'],
        'multi_entity': ['all'],
        'manual_processes': ['all'],
        'deadline_pressure': ['all'],
        'technical_business': ['all'],
        'use_case_deployment': ['all'],
        'tool_deployment': ['all'],
        'functional_technical': ['all'],
        'project_delays': ['all'],
        'adoption': ['all'],
        'visibility': ['all'],
        'production_focus': ['all'],
        'transformation': ['all'],
        'excel_dependency': ['all'],
        'modeling_communication': ['all'],
        'technical_agility': ['all'],
        'closing_pressure': ['all'],
        'technical_functional': ['all'],
        'data_access': ['all'],
        'regulatory_operational': ['banking', 'insurance', 'all']
    }
    
    # Exclusions par secteur
    sector_exclusions = {
        'logistics_transport': ['industrial_processes', 'manufacturing'],
        'insurance': ['industrial_processes', 'manufacturing'],
        'services': ['industrial_processes', 'manufacturing'],
        'fintech': ['industrial_processes', 'manufacturing'],
        'banking': ['industrial_processes', 'manufacturing'],
        'gaming': ['industrial_processes']
    }
    
    valid_pain_points = {}
    
    for pain_key, pain_point in pain_points.items():
        # VALIDATION SECTEUR VIA MAPPING
        allowed_sectors = PAIN_POINT_SECTORS.get(pain_key, ['all'])
        if allowed_sectors != ['all'] and sector_code not in allowed_sectors:
            log_event('pain_point_excluded_sector', {
                'pain_key': pain_key,
                'sector': sector_code,
                'allowed': allowed_sectors
            })
            continue
        
        # Exclure par secteur (legacy - double sécurité)
        if sector_code in sector_exclusions:
            if any(excl in pain_key.lower() for excl in sector_exclusions[sector_code]):
                continue
        
        valid_pain_points[pain_key] = pain_point
    
    if not valid_pain_points:
        return {
            'short': "recrutement complexe sur ce type de poste",
            'context': "Difficulté à trouver des profils qui combinent expertise technique et compréhension métier."
        }
    
    # Scoring par mots-clés
    scoring_keywords = {
        'logistics': ['logistique', 'supply chain', 'transport', 'freight', 'entrepôt'],
        'multi_site': ['multi-sites', 'filiales', 'international', 'pays', 'réseau'],
        'industrial': ['production', 'manufacturing', 'usine', 'industriel'],
        'banking': ['bancaire', 'bank', 'cib', 'agence'],
        'insurance': ['assurance', 'solvabilité', 'actuariat', 'sinistre'],
        'certifications': ['cia', 'iia', 'coso', 'ifrs', 'certification']
    }
    
    pain_scores = {}
    for pain_key, pain_point in valid_pain_points.items():
        score = 0
        for category, kws in scoring_keywords.items():
            for kw in kws:
                if kw in job_text:
                    score += 1
        pain_scores[pain_key] = score
    
    best_pain_key = max(pain_scores.items(), key=lambda x: x[1])[0]
    
    log_event('pain_point_selected_v27_4', {
        'pain_key': best_pain_key,
        'sector': sector_code,
        'valid_count': len(valid_pain_points),
        'score': pain_scores[best_pain_key]
    })
    
    return valid_pain_points[best_pain_key]


def get_relevant_outcomes(job_category, max_outcomes=2):
    """Récupère les outcomes pertinents"""
    outcomes = OUTCOMES_DETAILED.get(job_category, OUTCOMES_DETAILED['general'])
    return outcomes[:max_outcomes]


# ========================================
# EXTRACTION SKILLS ENRICHIE
# ========================================

def extract_key_skills_from_job(job_posting_data, job_category):
    """
    VERSION V27.4 : Extraction enrichie avec secteur + certifications
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
        'processus opérationnels': 'processus opérationnels',
        'comptabilité technique': 'comptabilité technique',
        'flux réassurance': 'flux réassurance',
        'co-assurance': 'co-assurance',
        'solvabilité': 'Solvabilité II'
    }
    
    for keyword, tech_name in technical_keywords.items():
        if keyword in job_text:
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
        'animation': 'animation',
        'encadrement': 'encadrement'
    }
    
    for keyword, soft_name in soft_keywords.items():
        if keyword in job_text:
            if soft_name not in skills['soft']:
                skills['soft'].append(soft_name)
    
    # ÉTAPE 6 : Contexte secteur
    sector_contexts = {
        'banking': ('le secteur bancaire', ['environnement bancaire', 'réglementation bancaire', 'CIB']),
        'insurance': ('l\'assurance', ['compagnie d\'assurance', 'Solvabilité II', 'environnement réglementé']),
        'logistics_transport': ('la logistique et le transport', ['supply chain', 'opérations logistiques', 'réseau international']),
        'manufacturing': ('l\'industrie', ['sites de production', 'manufacturing', 'environnement industriel']),
        'engineering': ('l\'ingénierie', ['infrastructure', 'construction', 'projets d\'envergure']),
        'retail': ('le retail', ['réseau multi-sites', 'distribution']),
        'fintech': ('la fintech', ['startup fintech', 'scale-up', 'innovation financière']),
        'services': ('les services', ['conseil', 'prestations']),
        'gaming': ('le gaming', ['jeu vidéo', 'entertainment', 'revenus récurrents'])
    }
    
    if skills['sector_code'] in sector_contexts:
        skills['sector'], skills['context'] = sector_contexts[skills['sector_code']]
    else:
        skills['sector'] = 'le secteur'
        skills['context'] = ['grand groupe', 'international']
    
    log_event('skills_extracted_v27_4', {
        'tools': skills['tools'],
        'certifications': skills['certifications'],
        'sector': skills['sector_code'],
        'technical_count': len(skills['technical'])
    })
    
    return skills


# ========================================
# FONCTIONS UTILITAIRES
# ========================================

def get_safe_firstname(prospect_data):
    """Trouve le prénom"""
    target_keys = [
        'first_name', 'firstname', 'first name', 
        'prénom', 'prenom', 'name',
        'user_first_name', 'user_firstname'
    ]
    
    for key, value in prospect_data.items():
        if str(key).lower().strip() in target_keys:
            if value and str(value).strip():
                return str(value).strip().capitalize()
    
    full_name = prospect_data.get('full_name') or prospect_data.get('user_full name')
    if full_name and ' ' in str(full_name):
        parts = str(full_name).split()
        if len(parts) >= 1:
            return parts[0].capitalize()
    
    return "[Prénom]"


def get_smart_context(job_posting_data, prospect_data):
    """Définit le sujet de la discussion"""
    if job_posting_data and job_posting_data.get('title') and len(str(job_posting_data.get('title'))) > 2:
        title = str(job_posting_data.get('title'))
        title = re.sub(r'\s*\(?[HhFf]\s*[/\-]\s*[HhFfMm]\)?', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*[-|]\s*.*$', '', title)
        return title.strip().title(), True

    headline = str(prospect_data.get('headline', '')).lower()
    
    if 'financ' in headline or 'daf' in headline or 'cfo' in headline:
        return "vos équipes Finance", False
    elif 'rh' in headline or 'drh' in headline or 'talents' in headline:
        return "votre stratégie Talents", False
    elif 'audit' in headline:
        return "votre département Audit", False
    else:
        return "vos équipes", False


def flexible_match(keyword, text):
    """Match flexible : insensible à la casse, espaces, tirets"""
    pattern = re.escape(keyword).replace(r'\ ', r'[\s\-_]*')
    return bool(re.search(pattern, text, re.IGNORECASE))


# ========================================
# GÉNÉRATEURS DE MESSAGES
# ========================================

def generate_subject_lines(prospect_data, job_posting_data):
    """Génère les objets d'email axés pain points"""
    
    log_event('generate_subject_lines_start', {
        'prospect': prospect_data.get('_id', 'unknown')
    })
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    context_name, is_hiring = get_smart_context(job_posting_data, prospect_data)
    job_category = detect_job_category(prospect_data, job_posting_data)
    pain_point = get_relevant_pain_point(job_category, job_posting_data)
    
    skills = extract_key_skills_from_job(job_posting_data, job_category)
    detected_keywords = skills['tools'] + skills['technical'][:3] + skills['soft'][:2]
    
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
Secteur : {skills['sector_code']}

MOTS-CLÉS DÉTECTÉS :
{', '.join(detected_keywords[:10]) if detected_keywords else 'Aucun mot-clé spécifique'}

PAIN POINT :
{pain_point['short']}

CONSIGNE :
Génère 3 objets d'email courts (40-60 caractères) :
1. Question avec mot-clé outil/secteur OU pain point
2. Constat marché avec compétence spécifique
3. Objet direct : "Re: [titre poste]"

INTERDICTIONS :
❌ Pas de "Opportunité", "Proposition", "Collaboration"
❌ Pas de points d'exclamation
❌ Pas de promesses directes

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
        
    except Exception as e:
        log_error('generate_subject_lines_error', str(e), {})
        return f"1. {pain_point['short'][:50]}\n2. {context_name} - Profils qualifiés\n3. Re: {context_name}"


def generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content):
    """Génère le message 2 avec 2 profils ultra-différenciés"""
    
    log_event('generate_message_2_start', {
        'prospect': prospect_data.get('_id', 'unknown')
    })
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    first_name = get_safe_firstname(prospect_data)
    context_name, is_hiring = get_smart_context(job_posting_data, prospect_data)
    job_category = detect_job_category(prospect_data, job_posting_data)
    pain_point = get_relevant_pain_point(job_category, job_posting_data)
    outcomes = get_relevant_outcomes(job_category, max_outcomes=2)
    
    skills = extract_key_skills_from_job(job_posting_data, job_category)
    
    if is_hiring:
        intro_phrase = f"Je me permets de vous relancer concernant votre recherche de {context_name}."
    else:
        intro_phrase = f"Je reviens vers vous concernant la structuration de {context_name}."
    
    # Préparer outils/certifications
    tools_str = ', '.join(skills['tools'][:5]) if skills['tools'] else 'AUCUN'
    certs_str = ', '.join(skills['certifications']) if skills['certifications'] else 'AUCUNE'
    technical_str = ', '.join(skills['technical'][:5]) if skills['technical'] else 'compétences métier générales'
    
    tools_warning = "" if skills['tools'] else "\n⚠️ AUCUN OUTIL DÉTECTÉ → NE MENTIONNE AUCUN OUTIL"
    cert_warning = "" if skills['certifications'] else "\n⚠️ AUCUNE CERTIFICATION → NE MENTIONNE AUCUNE CERTIFICATION"
    
    prompt = f"""Tu es chasseur de têtes spécialisé Finance.

CONTEXTE :
Prospect : {first_name}
Poste : {context_name}
Métier : {job_category}
Secteur : {skills['sector_code']}

EXTRACTION FICHE :
Outils : {tools_str}
Certifications : {certs_str}
Compétences : {technical_str}
{tools_warning}
{cert_warning}

PAIN POINT :
{pain_point['context']}

🚨 RÈGLES :
1. Utilise UNIQUEMENT les outils/certifications listés
2. Les 2 profils doivent être RADICALEMENT DIFFÉRENTS
3. Profil 1 = spécialiste secteur, Profil 2 = Big 4/reconversion

FORMAT (100-120 mots) :
1. "Bonjour {first_name},"
2. "{intro_phrase}"
3. Observation marché (pain point)
4. "J'ai identifié 2 profils qui pourraient retenir votre attention :"
5. "- L'un [profil 1]"
6. "- L'autre [profil 2]"
7. "Seriez-vous d'accord pour recevoir leurs synthèses anonymisées ?"
8. "Bien à vous,"

Génère le message :"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}]
        )
        
        tracker.track(message.usage, 'generate_message_2')
        result = message.content[0].text.strip()
        
        log_event('generate_message_2_success', {'length': len(result)})
        return result
        
    except Exception as e:
        log_error('generate_message_2_error', str(e), {})
        return generate_message_2_fallback(first_name, context_name, is_hiring, 
                                          job_posting_data, skills, pain_point)


def generate_message_2_fallback(first_name, context_name, is_hiring, job_posting_data, skills, pain_point):
    """Fallback intelligent pour Message 2"""
    
    if is_hiring:
        intro = f"Je me permets de vous relancer concernant votre recherche de {context_name}."
    else:
        intro = f"Je reviens vers vous concernant la structuration de {context_name}."
    
    observation = f"Le défi principal réside dans {pain_point['short']}."
    
    tool_1 = skills['tools'][0] if skills['tools'] else 'outils métier'
    tech_1 = skills['technical'][0] if skills['technical'] else 'expertise technique'
    soft_1 = skills['soft'][0] if skills['soft'] else 'conduite du changement'
    
    profile_1 = f"- L'un possède une expertise {tech_1} avec maîtrise de {tool_1}, ayant piloté des projets de transformation avec forte autonomie."
    profile_2 = f"- L'autre combine expérience Big 4 et {soft_1}, expert accompagnement d'équipes et communication transverse."
    
    return f"""Bonjour {first_name},

{intro}

{observation}

J'ai identifié 2 profils qui pourraient retenir votre attention :
{profile_1}
{profile_2}

Seriez-vous d'accord pour recevoir leurs synthèses anonymisées ? Cela vous permettrait de juger leur pertinence en 30 secondes.

Bien à vous,"""


def generate_message_3(prospect_data, message_1_content, job_posting_data):
    """Message 3 - TEMPLATE FIXE"""
    
    first_name = get_safe_firstname(prospect_data)
    
    return f"""Bonjour {first_name},

Je comprends que vous n'ayez pas eu le temps de revenir vers moi — je sais à quel point vos fonctions sont sollicitées.

Avant de clore le dossier de mon côté, une dernière question : Est-ce que le timing n'est simplement pas bon pour l'instant, ou bien travaillez-vous déjà avec d'autres cabinets/recruteurs sur ce poste ?

Si c'est une question de timing, je serai ravi de reprendre contact dans quelques semaines.

Si vous préférez gérer ce recrutement autrement, aucun souci — je vous souhaite de trouver la perle rare rapidement.

Merci en tous cas pour votre attention,

Bonne continuation,"""


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
        
        log_event('sequence_generation_success', {
            'prospect_id': prospect_data.get('_id', 'unknown'),
            'valid': is_valid
        })
        
        return sequence
        
    except Exception as e:
        log_error('sequence_generation_failed', str(e), {
            'prospect_id': prospect_data.get('_id', 'unknown')
        })
        raise
