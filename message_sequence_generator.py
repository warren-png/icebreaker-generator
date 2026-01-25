"""
═══════════════════════════════════════════════════════════════════
MESSAGE SEQUENCE GENERATOR - V27 (QUALITÉ MAXIMALE)
Modifications V27 :
- Message 2 : TOUJOURS 2 profils ultra-différenciés avec compétences précises
- Prompt massivement renforcé avec exemples concrets
- Fallback intelligent qui utilise vraiment la fiche de poste
- Message 3 : TOUJOURS identique (template fixe avec prénom uniquement)
- Extraction compétences enrichie
- Suppression totale des fallbacks génériques
═══════════════════════════════════════════════════════════════════
"""

import anthropic
import os
import re 
from config import COMPANY_INFO, PAIN_POINTS_DETAILED, OUTCOMES_DETAILED

# Imports utilitaires
from prospection_utils.logger import log_event, log_error
from prospection_utils.cost_tracker import tracker
from prospection_utils.validator import validate_and_report

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("❌ ANTHROPIC_API_KEY non trouvée")


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
    Sélectionne LE pain point le plus pertinent selon le métier et la fiche de poste
    Retourne un dict avec 'short' et 'context'
    """
    if job_category not in PAIN_POINTS_DETAILED:
        return {
            'short': "recrutement complexe sur ce type de poste",
            'context': "Difficulté à trouver des profils qui combinent expertise technique et vision business."
        }
    
    pain_points = PAIN_POINTS_DETAILED[job_category]
    
    # Si pas de fiche de poste, prendre le premier pain point
    if not job_posting_data:
        first_key = list(pain_points.keys())[0]
        return pain_points[first_key]
    
    # Sinon, chercher le pain point le plus pertinent selon la fiche
    job_text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}".lower()
    
    # Mots-clés pour chaque type de pain point
    pain_point_keywords = {
        'visibility': ['reporting', 'pilotage', 'indicateurs', 'kpi', 'tableau de bord'],
        'production_focus': ['clôture', 'production', 'charge', 'opérationnel'],
        'transformation': ['erp', 'epm', 'bi', 'transformation', 'projet', 'digitalisation'],
        'key_man_risk': ['clé', 'senior', 'expertise', 'dépendance'],
        'data_quality': ['données', 'data', 'qualité', 'fiabilité'],
        'hybrid_profiles': ['hybride', 'technique', 'business', 'polyvalence'],
        'excel_dependency': ['excel', 'tableur', 'manuel', 'automatisation'],
        'adoption': ['adoption', 'change', 'utilisateurs', 'formation'],
        'manual_processes': ['manuel', 'automatisation', 'process'],
        'acculturation': ['acculturation', 'formation', 'accompagnement', 'pédagogie']
    }
    
    # Scorer chaque pain point
    best_score = 0
    best_pain_point = None
    
    for key, pain_point in pain_points.items():
        score = 0
        for keyword_type, keywords in pain_point_keywords.items():
            if keyword_type in key or any(kw in key for kw in keywords):
                for kw in keywords:
                    if kw in job_text:
                        score += 1
        
        if score > best_score:
            best_score = score
            best_pain_point = pain_point
    
    # Si aucun match, prendre le premier
    if not best_pain_point:
        first_key = list(pain_points.keys())[0]
        best_pain_point = pain_points[first_key]
    
    return best_pain_point


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
# EXTRACTION COMPÉTENCES (ENRICHI V27)
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
    # Exemple : "EPM (Pigment, Jedox, Lucanet)"
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
    
    log_event('tools_filtered_v27_2', {
        'raw_count': len(all_keywords),
        'filtered_count': len(detected_tools),
        'tools': detected_tools
    })
    
    return detected_tools


# ========================================
# FONCTION PRINCIPALE (REMPLACE L'ANCIENNE)
# ========================================

def extract_key_skills_from_job(job_posting_data, job_category):
    """
    Extrait les compétences clés de la fiche de poste
    VERSION V27.2 : EXTRACTION PURE - Zéro invention d'outils
    """
    skills = {
        'tools': [],
        'technical': [],
        'soft': [],
        'sector': 'le secteur',
        'context': []
    }
    
    if not job_posting_data:
        return skills
    
    job_text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}".lower()
    
    # ========================================
    # ÉTAPE 1 : EXTRACTION PURE DES OUTILS
    # ========================================
    extracted = extract_all_keywords_from_job(job_posting_data)
    detected_tools = filter_real_tools(extracted)
    
    skills['tools'] = detected_tools
    
    # ========================================
    # ÉTAPE 2 : COMPÉTENCES TECHNIQUES
    # ========================================
    technical_keywords = {
        # Finance générale
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
        'variance analysis': 'analyse des écarts',
        # Comptabilité
        'comptabilité générale': 'comptabilité générale',
        'comptabilité analytique': 'comptabilité analytique',
        'réconciliations': 'réconciliations',
        'pcb': 'plan comptable bancaire',
        # Audit
        'audit interne': 'audit interne',
        'audit financier': 'audit financier',
        'audit opérationnel': 'audit opérationnel',
        'contrôle interne': 'contrôle interne',
        'gestion des risques': 'gestion des risques',
        # Bancaire
        'alm': 'ALM (actif-passif)',
        'liquidité': 'gestion de liquidité',
        'refinancement': 'refinancement',
        # Autres
        'trésorerie': 'trésorerie',
        'fiscalité': 'fiscalité',
        'valorisation stocks': 'valorisation des stocks',
        'kpi': 'construction de KPI',
        'tableaux de bord': 'tableaux de bord',
        'process': 'process',
        'référentiels': 'référentiels'
    }
    
    for keyword, tech_name in technical_keywords.items():
        if flexible_match(keyword, job_text):
            if tech_name not in skills['technical']:
                skills['technical'].append(tech_name)
    
    # ========================================
    # ÉTAPE 3 : COMPÉTENCES SOFT
    # ========================================
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
    
    # ========================================
    # ÉTAPE 4 : SECTEUR
    # ========================================
    if any(kw in job_text for kw in ['banque', 'bank', 'bancaire', 'cib', 'corporate banking']):
        skills['sector'] = 'le secteur bancaire'
        skills['context'] = ['environnement bancaire', 'réglementation', 'CIB']
    
    elif 'fintech' in job_text or 'neo-banque' in job_text:
        skills['sector'] = 'la fintech'
        skills['context'] = ['startup fintech', 'scale-up', 'agilité']
    
    elif 'assurance' in job_text:
        skills['sector'] = 'l\'assurance'
        skills['context'] = ['compagnie d\'assurance', 'Solvabilité II']
    
    elif any(kw in job_text for kw in ['industrie', 'industrial', 'manufacturing', 'production', 'usine']):
        skills['sector'] = 'l\'industrie'
        skills['context'] = ['groupe industriel', 'sites de production', 'manufacturing']
    
    elif any(kw in job_text for kw in ['retail', 'distribution', 'réseau', 'agences', 'magasins']):
        skills['sector'] = 'le retail'
        skills['context'] = ['réseau multi-sites', 'distribution']
    
    elif 'négoce' in job_text or 'negoce' in job_text:
        skills['sector'] = 'le négoce'
        skills['context'] = ['négoce international', 'trading']
    
    elif any(kw in job_text for kw in ['audiovisuel', 'cinéma', 'production', 'média']):
        skills['sector'] = 'l\'audiovisuel'
        skills['context'] = ['production', 'droits d\'auteurs']
    
    else:
        skills['sector'] = 'le secteur'
        skills['context'] = ['grand groupe', 'international']
    
    log_event('skills_extracted_v27_2', {
        'tools_count': len(skills['tools']),
        'tools': skills['tools'],
        'technical_count': len(skills['technical']),
        'soft_count': len(skills['soft']),
        'sector': skills['sector']
    })
    
    return skills
    
    
    # ========================================
    # OUTILS SPÉCIFIQUES (ORDRE DE PRIORITÉ)
    # ========================================
    
    # 1. OUTILS EPM (Priorité haute)
    epm_tools = {
        'pigment': 'Pigment',
        'jedox': 'Jedox',
        'lucanet': 'Lucanet',
        'tagetik': 'Tagetik',
        'anaplan': 'Anaplan',
        'hyperion': 'Hyperion',
        'onestream': 'OneStream',
        'sap bpc': 'SAP BPC',
        'board': 'Board'
    }
    
    for keyword, tool_name in epm_tools.items():
        if flexible_match(keyword, job_text):
            if tool_name not in skills['tools']:
                skills['tools'].append(tool_name)
    
    # 2. ERP (Priorité haute)
    erp_tools = {
        'sap': 'SAP',
        's/4hana': 'S/4HANA',
        's4hana': 'S/4HANA',
        'oracle': 'Oracle',
        'sage': 'Sage',
        'sage x3': 'Sage X3',
        'dynamics': 'Dynamics'
    }
    
    for keyword, tool_name in erp_tools.items():
        if flexible_match(keyword, job_text):
            if tool_name not in skills['tools']:
                skills['tools'].append(tool_name)
    
    # 3. BI / DATA ANALYTICS (Seulement si explicitement mentionnés)
    bi_tools = {
        'power bi': 'Power BI',
        'powerbi': 'Power BI',
        'tableau': 'Tableau',
        'qlik': 'Qlik',
        'spotfire': 'Spotfire',
        'looker': 'Looker'
    }
    
    for keyword, tool_name in bi_tools.items():
        if flexible_match(keyword, job_text):
            if tool_name not in skills['tools']:
                skills['tools'].append(tool_name)
    
    # 4. LANGAGES PROGRAMMATION (Seulement si explicitement mentionnés)
    # ATTENTION : Ne pas détecter "R" tout seul (trop de faux positifs)
    if 'python' in job_text:
        skills['tools'].append('Python')
    
    if ' r ' in job_text or 'langage r' in job_text or ', r' in job_text or 'r,' in job_text:
        skills['tools'].append('R')
    
    if 'sql' in job_text:
        skills['tools'].append('SQL')
    
    # 5. EXCEL / OFFICE (Toujours présent dans finance)
    if 'excel' in job_text:
        skills['tools'].append('Excel')
        
        # Détecter niveau Excel
        if 'vba' in job_text or 'macro' in job_text:
            if 'VBA' not in skills['tools']:
                skills['tools'].append('VBA')
        
        if 'power query' in job_text or 'powerquery' in job_text:
            if 'Power Query' not in skills['tools']:
                skills['tools'].append('Power Query')
    
    # ========================================
    # COMPÉTENCES TECHNIQUES PAR MÉTIER
    # VERSION V27.1 : Détection précise selon fiche de poste
    # ========================================
    
    # Détection générale (tous métiers)
    general_tech = {
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
        'variance analysis': 'analyse des écarts',
        'comptabilité générale': 'comptabilité générale',
        'audit interne': 'audit interne',
        'contrôle interne': 'contrôle interne',
        'alm': 'ALM (actif-passif)',
        'liquidité': 'gestion de liquidité',
        'trésorerie': 'trésorerie',
        'fiscalité': 'fiscalité',
        'pcb': 'plan comptable bancaire',
        'valorisation stocks': 'valorisation des stocks',
        'kpi': 'construction de KPI',
        'tableaux de bord': 'tableaux de bord'
    }
    
    for keyword, tech_name in general_tech.items():
        if flexible_match(keyword, job_text):
            if tech_name not in skills['technical']:
                skills['technical'].append(tech_name)
    
    # Compétences spécifiques Data/IA (seulement si explicitement mentionnées)
    if job_category == 'data_ia':
        data_keywords = {
            'data science': 'Data Science',
            'machine learning': 'Machine Learning',
            'deep learning': 'Deep Learning',
            'acculturation ia': 'acculturation IA',
            'centre d\'excellence': 'centre d\'excellence',
            'cas d\'usage': 'cas d\'usage IA',
            'poc': 'POCs'
        }
        
        for keyword, tech_name in data_keywords.items():
            if flexible_match(keyword, job_text):
                if tech_name not in skills['technical']:
                    skills['technical'].append(tech_name)
    
    # ========================================
    # COMPÉTENCES SOFT (ENRICHI)
    # ========================================
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
        'idéation': 'ateliers idéation',
        'agile': 'méthodologie Agile',
        'scrum': 'Scrum',
        'safe': 'SAFe',
        'pmp': 'PMP',
        'project management': 'project management',
        'structuration': 'structuration',
        'autonomie': 'autonomie',
        'esprit d\'équipe': 'esprit d\'équipe',
        'animation': 'animation d\'équipe'
    }
    
    for keyword, soft_name in soft_keywords.items():
        if flexible_match(keyword, job_text):
            if soft_name not in skills['soft']:
                skills['soft'].append(soft_name)
    
    # ========================================
    # SECTEUR (AMÉLIORATION V27.1)
    # ========================================
    
    # Secteur Bancaire / Finance
    if any(kw in job_text for kw in ['banque', 'bank', 'bancaire', 'cib', 'corporate banking', 'banque d\'investissement']):
        skills['sector'] = 'le secteur bancaire'
        if 'cib' in job_text or 'corporate & investment banking' in job_text:
            skills['context'] = ['banque d\'investissement', 'CIB', 'environnement international']
        else:
            skills['context'] = ['banque de détail', 'corporate banking', 'environnement réglementé']
    
    # Fintech
    elif 'fintech' in job_text or 'neo-banque' in job_text or 'neobanque' in job_text:
        skills['sector'] = 'la fintech'
        skills['context'] = ['startup fintech', 'scale-up tech', 'environnement agile']
    
    # Assurance
    elif 'assurance' in job_text or 'actuariat' in job_text:
        skills['sector'] = 'l\'assurance'
        skills['context'] = ['compagnie d\'assurance', 'gestion de risques', 'réglementation Solvabilité II']
    
    # Industrie manufacturière
    elif any(kw in job_text for kw in ['industrie', 'industrial', 'manufacturing', 'production', 'usine', 'site de production']):
        skills['sector'] = 'l\'industrie'
        skills['context'] = ['groupe industriel', 'sites de production', 'environnement manufacturier']
    
    # Retail / Distribution
    elif any(kw in job_text for kw in ['retail', 'distribution', 'réseau', 'agences', 'magasins', 'points de vente']):
        skills['sector'] = 'le retail'
        skills['context'] = ['réseau multi-sites', 'distribution', 'gestion de réseau']
    
    # Négoce
    elif 'négoce' in job_text or 'negoce' in job_text or 'trading' in job_text:
        skills['sector'] = 'le négoce'
        skills['context'] = ['négoce international', 'trading', 'gestion stocks']
    
    # Audiovisuel / Média
    elif any(kw in job_text for kw in ['audiovisuel', 'cinéma', 'production', 'média', 'media']):
        skills['sector'] = 'l\'audiovisuel'
        skills['context'] = ['production cinématographique', 'groupe média', 'droits d\'auteurs']
    
    # Contexte générique si rien de détecté
    else:
        skills['sector'] = 'le secteur'
        skills['context'] = ['grand groupe', 'environnement international']
    
    log_event('skills_extracted', {
        'tools_count': len(skills['tools']),
        'technical_count': len(skills['technical']),
        'soft_count': len(skills['soft']),
        'sector': skills['sector'],
        'tools_detected': skills['tools'][:5]
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
    full_name = prospect_data.get('full_name') or prospect_data.get('user_full name')
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
# 2. MESSAGE 2 : LA PROPOSITION (V27 OPTIMISÉ)
# ========================================

def generate_message_2(prospect_data, hooks_data, job_posting_data, message_1_content):
    """
    Génère le message 2 avec 2 profils TOUJOURS ultra-différenciés
    VERSION V27 : Prompt massivement renforcé avec exemples concrets
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
        'technical': skills['technical'][:3],
        'soft': skills['soft'][:2],
        'sector': skills['sector']
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
    soft_str = ', '.join(skills['soft'][:3]) if skills['soft'] else 'compétences transverses'
    
    prompt = f"""Tu es chasseur de têtes spécialisé Finance.

═══════════════════════════════════════════════════════════════
⚠️  RÈGLE ABSOLUE - NON NÉGOCIABLE :
═══════════════════════════════════════════════════════════════

Tu DOIS TOUJOURS proposer EXACTEMENT 2 profils candidats dans ce message.
Les 2 profils DOIVENT être TRÈS DIFFÉRENTS (parcours, secteurs, compétences).

FORMAT OBLIGATOIRE :
"J'ai identifié 2 profils qui pourraient retenir votre attention :
- L'un [profil 1 avec détails précis]
- L'autre [profil 2 avec parcours différent]"

═══════════════════════════════════════════════════════════════

CONTEXTE :
Prospect : {first_name}
Poste recherché : {context_name}
Métier : {job_category}
Type : {'Recrutement actif' if is_hiring else 'Approche spontanée'}

ANALYSE DE LA FICHE DE POSTE :
Titre exact : {job_posting_data.get('title', 'N/A') if job_posting_data else 'N/A'}

═══════════════════════════════════════════════════════════════
🚨 OUTILS DÉTECTÉS DANS LA FICHE (UTILISE UNIQUEMENT CEUX-CI)
═══════════════════════════════════════════════════════════════

OUTILS DÉTECTÉS : {tools_str}
COMPÉTENCES TECHNIQUES : {technical_str}
COMPÉTENCES TRANSVERSES : {soft_str}
SECTEUR : {skills['sector']}{no_tools_warning}

🚨 RÈGLES ABSOLUES SUR LES OUTILS :

1️⃣ SI des outils sont listés ci-dessus (ex: SAP, Jedox, Excel) :
   ✅ Utilise UNIQUEMENT ces outils
   ✅ Mentionne-les explicitement dans les profils
   ❌ N'ajoute AUCUN autre outil

2️⃣ SI AUCUN OUTIL détecté :
   ✅ NE MENTIONNE AUCUN OUTIL
   ✅ Focus sur : "expertise audit", "maîtrise consolidation"
   ✅ Focus contexte : "environnement industriel", "multi-sites"
   ❌ N'invente PAS d'outils

3️⃣ INTERDICTIONS STRICTES :
   ❌ JAMAIS ajouter Python si non listé
   ❌ JAMAIS ajouter R si non listé
   ❌ JAMAIS ajouter Tableau si non listé
   ❌ JAMAIS ajouter Power BI si non listé
   ❌ JAMAIS inventer un outil absent de la liste

EXEMPLES CONCRETS :

📌 Si outils = [SAP, Excel] :
✅ BON : "maîtrise de SAP et Excel avancé"
❌ MAUVAIS : "maîtrise de SAP, Excel et Python"

📌 Si outils = [Jedox, Pigment] :
✅ BON : "expertise Jedox ou Pigment"
❌ MAUVAIS : "expertise Jedox, Pigment et Tableau"

📌 Si outils = [] (AUCUN) :
✅ BON : "expertise audit avec forte compréhension des enjeux industriels"
❌ MAUVAIS : "expertise audit avec Python et R"

═══════════════════════════════════════════════════════════════

Description fiche (extraits) :
{str(job_posting_data.get('description', ''))[:800] if job_posting_data else 'N/A'}

PAIN POINT IDENTIFIÉ :
{pain_point['short']}
Contexte : {pain_point['context']}

═══════════════════════════════════════════════════════════════
STRUCTURE STRICTE DU MESSAGE (100-120 mots max)
═══════════════════════════════════════════════════════════════
"""
    
    prompt = f"""Tu es chasseur de têtes spécialisé Finance.

═══════════════════════════════════════════════════════════════
⚠️  RÈGLE ABSOLUE - NON NÉGOCIABLE :
═══════════════════════════════════════════════════════════════════

Tu DOIS TOUJOURS proposer EXACTEMENT 2 profils candidats dans ce message.
Les 2 profils DOIVENT être TRÈS DIFFÉRENTS (parcours, secteurs, compétences).

FORMAT OBLIGATOIRE :
"J'ai identifié 2 profils qui pourraient retenir votre attention :
- L'un [profil 1 avec détails précis]
- L'autre [profil 2 avec parcours différent]"

═══════════════════════════════════════════════════════════════════

CONTEXTE :
Prospect : {first_name}
Poste recherché : {context_name}
Métier : {job_category}
Type : {'Recrutement actif' if is_hiring else 'Approche spontanée'}

ANALYSE DE LA FICHE DE POSTE :
Titre exact : {job_posting_data.get('title', 'N/A') if job_posting_data else 'N/A'}

⚠️  COMPÉTENCES DÉTECTÉES DANS LA FICHE (UTILISE UNIQUEMENT CELLES-CI) :
- Outils détectés : {tools_str}
- Compétences techniques détectées : {technical_str}
- Compétences transverses détectées : {soft_str}
- Secteur détecté : {skills['sector']}

🚨 RÈGLE ABSOLUE : N'INVENTE AUCUN OUTIL NON LISTÉ CI-DESSUS
Si la fiche mentionne "SAP" → utilise SAP (pas Python/R)
Si la fiche mentionne "Jedox" → utilise Jedox (pas Tableau)
Si la fiche mentionne "Excel" → utilise Excel (pas Python/R)

Description complète (extraits) :
{str(job_posting_data.get('description', ''))[:800] if job_posting_data else 'N/A'}

PAIN POINT IDENTIFIÉ :
{pain_point['short']}
Contexte : {pain_point['context']}

═══════════════════════════════════════════════════════════════════
STRUCTURE STRICTE DU MESSAGE (100-120 mots max)
═══════════════════════════════════════════════════════════════════

1. "Bonjour {first_name},"
2. SAUT DE LIGNE
3. "{intro_phrase}"
4. SAUT DE LIGNE
5. Observation marché ULTRA-SPÉCIFIQUE (30-40 mots)
   
   RÈGLES IMPÉRATIVES pour l'observation :
   ✅ DOIT mentionner AU MOINS 2 compétences RARES détectées ci-dessus
   ✅ DOIT citer les outils/technologies entre parenthèses
   ✅ DOIT contextualiser (secteur, environnement)
   ✅ PAS de phrases bateau type "recruter crée un dilemme"
   
   EXEMPLES DE BONNES OBSERVATIONS :
   
   Pour Data & IA Officer (avec Python, R détectés) :
   "Le défi principal sur ce type de poste réside dans la capacité à allier expertise technique (Python, R, Machine Learning) et compétences d'acculturation métier pour accompagner les transformations IA dans le secteur bancaire (ateliers d'idéation, formations, gouvernance data)."
   
   Pour EPM Tagetik (si Tagetik détecté) :
   "Le marché combine difficilement expertise Tagetik (consolidation, reporting) et capacité à piloter des projets en méthodologie Agile/SAFe tout en garantissant l'adoption utilisateurs dans un environnement international."
   
   Pour EPM Pigment/Jedox (si Pigment ou Jedox détectés) :
   "Le défi principal réside dans la capacité à allier expertise en outils EPM (Pigment, Jedox) et compétences en structuration financière pour bâtir from scratch le pilotage d'un réseau multi-sites, tout en fiabilisant les données et accélérant la production d'indicateurs."
   
   Pour Comptable Fintech :
   "Le marché combine difficilement expertise comptable bancaire (clôtures réglementaires, réconciliations complexes) et agilité technologique pour accompagner les lancements produits en fintech (automatisation Excel/VBA, reporting temps réel, projets transverses)."
   
   Pour Auditeur avec SAP (si SAP détecté) :
   "Le défi principal dans un groupe industriel international réside dans la capacité à allier expertise audit financier et opérationnel avec une forte compréhension des enjeux industriels (sites de production, réseaux internationaux) et la maîtrise de SAP pour analyser efficacement les processus."
   
   Pour Auditeur ALM Bancaire :
   "Le défi principal réside dans la capacité à allier expertise des risques ALM (gestion actif-passif, liquidité, refinancement) et connaissance approfondie de l'environnement CIB (financement structuré, produits de marché)."

6. Proposition de 2 PROFILS ULTRA-DIFFÉRENCIÉS (40-50 mots)
   
   "J'ai identifié 2 profils qui pourraient retenir votre attention :"
   
   RÈGLES IMPÉRATIVES pour les profils :
   ✅ Les 2 profils DOIVENT être TRÈS DIFFÉRENTS :
      - Parcours différent (banque vs conseil, junior vs senior, France vs international)
      - Secteurs différents si possible
      - Compétences complémentaires (pas les mêmes outils)
   ✅ Chaque profil DOIT mentionner :
      - Compétences techniques PRÉCISES (outils/technologies entre parenthèses)
      - Contexte précis (secteur, taille entreprise, type de mission)
      - Réalisation concrète ou expérience significative
   ✅ Profils crédibles basés sur les compétences détectées
   
   EXEMPLES DE BONNES PROPOSITIONS :
   
   Pour Data & IA Officer :
   "- L'un possède une expertise Data Science (Python, R, SQL) acquise en banque d'investissement, ayant piloté des projets d'acculturation IA auprès des équipes trading (ateliers idéation, POCs métier).
   - L'autre vient du corporate banking avec une solide maîtrise de Sage et Excel avancé, reconverti en Data Science et spécialisé dans l'accompagnement au changement pour les transformations digitales."
   
   Pour EPM Tagetik + Agile (si Tagetik détecté) :
   "- L'un combine expertise Tagetik (consolidation statutory, reporting) et certification SAFe/PMP, ayant piloté l'intégration EPM/SAP en environnement international (30+ filiales).
   - L'autre vient du conseil EPM (Big 4) avec forte capacité en Change Management et animation de formations utilisateurs multi-pays (stakeholder engagement, documentation processus)."
   
   Pour EPM Jedox (si Jedox détecté) :
   "- L'un possède une expertise contrôle de gestion retail multi-sites avec maîtrise de Jedox, ayant structuré le reporting d'un réseau de 50+ agences et déployé le processus budgétaire dans un environnement négoce.
   - L'autre combine expérience Big 4 en transformation Finance et expertise Excel avancée (macros, Power Query), spécialisé dans la mise en place de référentiels financiers et l'accompagnement au changement dans les PME en forte croissance."
   
   Pour Comptable Fintech :
   "- L'un possède une expérience en comptabilité bancaire (PCB, fiscalité IS/TVA) avec forte maîtrise Excel/VBA pour l'automatisation des réconciliations et participation active aux projets Agile.
   - L'autre combine expertise comptable en environnement tech (clôtures mensuelles, trésorerie) et compétences en reporting automatisé (Power BI) avec excellente communication transverse."
   
   Pour Auditeur avec SAP (si SAP détecté) :
   "- L'un possède une expertise audit interne acquise en Big 4 avec forte expérience en environnement industriel international (manufacturing, supply chain) et maîtrise de SAP, ayant audité des sites de production dans 15+ pays.
   - L'autre combine expérience opérationnelle en contrôle financier industriel et reconversion vers l'audit, apportant une compréhension terrain des processus de clôture et de contrôle interne avec excellentes capacités relationnelles multilingues."
   
   Pour Auditeur ALM Bancaire :
   "- L'un possède une expertise ALM (gestion actif-passif, liquidité, ratios réglementaires) acquise dans une grande banque internationale, avec 7+ ans en audit des risques de marché.
   - L'autre combine expérience en front office CIB (produits structurés) et reconversion vers l'audit interne, apportant une compréhension opérationnelle fine des métiers de financement."

7. Offre sans engagement (15-20 mots) :
   "Seriez-vous d'accord pour recevoir leurs synthèses anonymisées ? Cela vous permettrait de juger leur pertinence en 30 secondes."

8. "Bien à vous,"

═══════════════════════════════════════════════════════════════════
INTERDICTIONS ABSOLUES
═══════════════════════════════════════════════════════════════════

❌ JAMAIS "Notre cabinet", "Nos services", "Notre expertise"
❌ JAMAIS de superlatifs ("meilleurs", "excellents")
❌ JAMAIS proposer des profils GÉNÉRIQUES sans compétences précises
❌ JAMAIS de formulations vagues type "maîtrise avancée" sans préciser l'outil
❌ JAMAIS plus de 120 mots
❌ JAMAIS de ton commercial type "Auriez-vous un rapide créneau de 15 min"
❌ JAMAIS proposer un appel téléphonique directement
❌ JAMAIS de profils trop similaires (même secteur, même profil, mêmes outils)

═══════════════════════════════════════════════════════════════════
VALIDATION AVANT ENVOI
═══════════════════════════════════════════════════════════════════

Avant de finaliser le message, vérifie :
1. ✅ Les 2 profils sont-ils VRAIMENT différents ? (parcours, secteur, outils)
2. ✅ Les profils mentionnent-ils des compétences PRÉCISES entre parenthèses ?
3. ✅ L'observation cite-t-elle au moins 2 compétences RARES ?
4. ✅ Le message fait-il moins de 120 mots ?

Si une réponse est NON → RECOMMENCE

Génère le message 2 selon ces règles STRICTES :"""
    
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
    VERSION V27 : Utilise VRAIMENT les compétences détectées
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
