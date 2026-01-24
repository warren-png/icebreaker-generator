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

def extract_key_skills_from_job(job_posting_data, job_category):
    """
    Extrait les compétences clés de la fiche de poste
    VERSION V27 : Extraction ultra-enrichie pour profils crédibles
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
    # OUTILS SPÉCIFIQUES (ENRICHI)
    # ========================================
    tools_keywords = {
        'tagetik': 'Tagetik',
        'anaplan': 'Anaplan',
        'hyperion': 'Hyperion',
        'onestream': 'OneStream',
        'sap bpc': 'SAP BPC',
        'sap': 'SAP',
        's/4hana': 'S/4HANA',
        'oracle': 'Oracle',
        'sage': 'Sage',
        'sage x3': 'Sage X3',
        'power bi': 'Power BI',
        'powerbi': 'Power BI',
        'tableau': 'Tableau',
        'qlik': 'Qlik',
        'excel': 'Excel',
        'vba': 'VBA',
        'power query': 'Power Query',
        'python': 'Python',
        'r': 'R',
        'sql': 'SQL',
        'spotfire': 'Spotfire',
        'louma': 'Louma'
    }
    
    for keyword, tool_name in tools_keywords.items():
        if flexible_match(keyword, job_text):
            if tool_name not in skills['tools']:
                skills['tools'].append(tool_name)
    
    # ========================================
    # COMPÉTENCES TECHNIQUES PAR MÉTIER
    # ========================================
    if job_category == 'data_ia':
        tech_keywords = ['data science', 'machine learning', 'ml', 'deep learning', 'python', 'sql', 
                        'acculturation ia', 'centre d\'excellence', 'cas d\'usage', 'poc']
    elif job_category == 'epm':
        tech_keywords = ['consolidation', 'reporting statutaire', 'forecast', 'budget', 'planning',
                        'intégration erp', 'paramétrage', 'formation utilisateurs']
    elif job_category == 'comptabilite':
        tech_keywords = ['comptabilité générale', 'clôture', 'réconciliations', 'pcb', 'comptabilité bancaire',
                        'ifrs', 'gaap', 'fiscalité', 'is', 'tva', 'droits d\'auteurs', 'notes de frais']
    elif job_category == 'audit':
        tech_keywords = ['audit interne', 'contrôles sox', 'gestion des risques', 'alm', 'actif-passif',
                        'data analytics', 'liquidity', 'refinancement']
    elif job_category == 'consolidation':
        tech_keywords = ['consolidation ifrs', 'normes ifrs', 'ifrs 9', 'ifrs 15', 'ifrs 16',
                        'montée en compétence filiales', 'migration outil']
    elif job_category == 'controle_gestion':
        tech_keywords = ['contrôle de gestion', 'fp&a', 'business partnering', 'variance analysis',
                        'modélisation financière']
    elif job_category == 'fpna':
        tech_keywords = ['fp&a', 'forecast', 'budget', 'variance analysis', 'modélisation',
                        'business partnering']
    else:
        tech_keywords = ['expertise technique', 'maîtrise opérationnelle']
    
    for keyword in tech_keywords:
        if flexible_match(keyword, job_text):
            if keyword not in skills['technical']:
                skills['technical'].append(keyword)
    
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
        'project management': 'project management'
    }
    
    for keyword, soft_name in soft_keywords.items():
        if flexible_match(keyword, job_text):
            if soft_name not in skills['soft']:
                skills['soft'].append(soft_name)
    
    # ========================================
    # SECTEUR (ENRICHI)
    # ========================================
    if any(kw in job_text for kw in ['banc', 'bank', 'banque']):
        skills['sector'] = 'le secteur bancaire'
        skills['context'] = ['banque d\'investissement', 'corporate banking', 'banque de détail']
    elif 'fintech' in job_text:
        skills['sector'] = 'la fintech'
        skills['context'] = ['startup fintech', 'scale-up tech', 'néo-banque']
    elif any(kw in job_text for kw in ['audiovisuel', 'cinéma', 'production']):
        skills['sector'] = 'l\'audiovisuel'
        skills['context'] = ['production cinématographique', 'groupe média', 'droits d\'auteurs']
    elif any(kw in job_text for kw in ['industrie', 'industrial', 'manufacturing']):
        skills['sector'] = 'l\'industrie'
        skills['context'] = ['grand groupe industriel', 'environnement manufacturier']
    elif 'assurance' in job_text:
        skills['sector'] = 'l\'assurance'
        skills['context'] = ['compagnie d\'assurance', 'actuariat', 'gestion de risques']
    else:
        skills['sector'] = 'le secteur'
        skills['context'] = ['grand groupe', 'environnement international']
    
    log_event('skills_extracted', {
        'tools_count': len(skills['tools']),
        'technical_count': len(skills['technical']),
        'soft_count': len(skills['soft']),
        'sector': skills['sector']
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
    tools_str = ', '.join(skills['tools'][:3]) if skills['tools'] else 'outils métier'
    technical_str = ', '.join(skills['technical'][:3]) if skills['technical'] else 'expertise technique'
    soft_str = ', '.join(skills['soft'][:2]) if skills['soft'] else 'compétences transverses'
    
    prompt = f"""Tu es chasseur de têtes spécialisé Finance.

═══════════════════════════════════════════════════════════════════
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

COMPÉTENCES CLÉS DÉTECTÉES (À UTILISER OBLIGATOIREMENT) :
- Outils : {tools_str}
- Techniques : {technical_str}
- Transverses : {soft_str}
- Secteur : {skills['sector']}

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
   
   Pour Data & IA Officer :
   "Le défi principal sur ce type de poste réside dans la capacité à allier expertise technique (Python, R, Machine Learning) et compétences d'acculturation métier pour accompagner les transformations IA dans le secteur bancaire (ateliers d'idéation, formations, gouvernance data)."
   
   Pour EPM Tagetik + Agile :
   "Le marché combine difficilement expertise Tagetik (consolidation, reporting) et capacité à piloter des projets en méthodologie Agile/SAFe tout en garantissant l'adoption utilisateurs dans un environnement international."
   
   Pour Comptable Fintech :
   "Le marché combine difficilement expertise comptable bancaire (clôtures réglementaires, réconciliations complexes) et agilité technologique pour accompagner les lancements produits en fintech (automatisation Excel/VBA, reporting temps réel, projets transverses)."
   
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
   
   Pour EPM Tagetik + Agile :
   "- L'un combine expertise Tagetik (consolidation statutory, reporting) et certification SAFe/PMP, ayant piloté l'intégration EPM/SAP en environnement international (30+ filiales).
   - L'autre vient du conseil EPM (Big 4) avec forte capacité en Change Management et animation de formations utilisateurs multi-pays (stakeholder engagement, documentation processus)."
   
   Pour Comptable Fintech :
   "- L'un possède une expérience en comptabilité bancaire (PCB, fiscalité IS/TVA) avec forte maîtrise Excel/VBA pour l'automatisation des réconciliations et participation active aux projets Agile.
   - L'autre combine expertise comptable en environnement tech (clôtures mensuelles, trésorerie) et compétences en reporting automatisé (Power BI, R) avec excellente communication transverse."
   
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
