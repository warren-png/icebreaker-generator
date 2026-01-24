"""
Templates de fallback pour quand l'API Claude est indisponible
VERSION V27 : Fallbacks intelligents qui utilisent les compétences détectées
"""

import re

# ========================================
# TEMPLATES D'OBJETS
# ========================================

FALLBACK_SUBJECTS = {
    'hiring': [
        "Re: {job_title} - Votre recherche",
        "Candidats {job_title} - Disponibilité",
        "{job_title} - Profils qualifiés"
    ],
    'spontaneous': [
        "Organisation Finance - {company}",
        "Structuration équipe Finance",
        "Profils Finance stratégiques"
    ]
}

# ========================================
# TEMPLATES MESSAGES (AMÉLIORÉS V27)
# ========================================

FALLBACK_MESSAGE_1 = """Bonjour {first_name},

J'ai consulté votre annonce pour le poste de {context}.

Le marché actuel rend ce type de recrutement particulièrement complexe : trouver des profils qui combinent expertise technique et capacités relationnelles devient rare.

Quels sont les principaux écarts que vous observez entre vos attentes et les profils rencontrés ?

Bien à vous,"""

FALLBACK_MESSAGE_2_INTELLIGENT = """Bonjour {first_name},

Je me permets de vous relancer concernant votre recherche de {context}.

{pain_point_observation}

J'ai identifié 2 profils qui pourraient retenir votre attention :
{profile_1}
{profile_2}

Seriez-vous d'accord pour recevoir leurs synthèses anonymisées ? Cela vous permettrait de juger leur pertinence en 30 secondes.

Bien à vous,"""

FALLBACK_MESSAGE_3_FIXED = """Bonjour {first_name},

Je comprends que vous n'ayez pas eu le temps de revenir vers moi — je sais à quel point vos fonctions sont sollicitées.

Avant de clore le dossier de mon côté, une dernière question : Est-ce que le timing n'est simplement pas bon pour l'instant, ou bien travaillez-vous déjà avec d'autres cabinets/recruteurs sur ce poste ?

Si c'est une question de timing, je serai ravi de reprendre contact dans quelques semaines.

Si vous préférez gérer ce recrutement autrement, aucun souci — je vous souhaite de trouver la perle rare rapidement.

Merci en tous cas pour votre attention,

Bonne continuation,"""

# ========================================
# FONCTIONS DE GÉNÉRATION
# ========================================

def get_fallback_context(job_posting_data, prospect_data):
    """Détermine le contexte pour les templates"""
    
    # Cas 1 : Il y a une annonce
    if job_posting_data and job_posting_data.get('title') and len(str(job_posting_data.get('title'))) > 2:
        title = str(job_posting_data.get('title'))
        # Nettoyage
        title = re.sub(r'\s*\(?[HhFf]\s*[/\-]\s*[HhFfMm]\)?', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*[-|]\s*.*$', '', title)
        return title.strip().title(), True
    
    # Cas 2 : Approche spontanée
    headline = str(prospect_data.get('headline', '')).lower()
    
    if 'financ' in headline or 'daf' in headline or 'cfo' in headline:
        return "vos équipes Finance", False
    elif 'rh' in headline or 'drh' in headline or 'talents' in headline:
        return "votre stratégie Talents", False
    elif 'audit' in headline:
        return "votre département Audit", False
    else:
        return "vos équipes", False


def get_fallback_firstname(prospect_data):
    """
    Trouve le prénom ou retourne placeholder
    VERSION V27 : Gestion correcte des champs Leonar
    """
    target_keys = [
        'first_name', 'firstname', 'first name', 
        'prénom', 'prenom', 'name',
        'user_first_name', 'user_firstname'
    ]
    
    for key, value in prospect_data.items():
        if str(key).lower().strip() in target_keys:
            if value and str(value).strip():
                return str(value).strip().capitalize()
    
    # Dernier recours : splitter full_name
    full_name = prospect_data.get('full_name') or prospect_data.get('user_full name')
    if full_name and ' ' in str(full_name):
        parts = str(full_name).split()
        if len(parts) >= 1:
            return parts[0].capitalize()
    
    return "[Prénom]"


def generate_fallback_subjects(prospect_data, job_posting_data):
    """Génère des objets de fallback"""
    
    context_name, is_hiring = get_fallback_context(job_posting_data, prospect_data)
    company = prospect_data.get('company', 'l\'entreprise')
    
    if is_hiring:
        subjects = [
            subject.format(job_title=context_name) 
            for subject in FALLBACK_SUBJECTS['hiring']
        ]
    else:
        subjects = [
            subject.format(company=company) 
            for subject in FALLBACK_SUBJECTS['spontaneous']
        ]
    
    return "\n".join(subjects)


def extract_skills_for_fallback(job_posting_data):
    """
    Extrait compétences de base pour fallback intelligent
    VERSION V27 : Extraction simplifiée mais efficace
    """
    skills = {
        'tools': [],
        'technical': [],
        'soft': [],
        'sector': 'le secteur'
    }
    
    if not job_posting_data:
        return skills
    
    job_text = f"{job_posting_data.get('title', '')} {job_posting_data.get('description', '')}".lower()
    
    # Outils basiques
    tools_map = {
        'tagetik': 'Tagetik', 'anaplan': 'Anaplan', 'sap': 'SAP',
        'excel': 'Excel', 'power bi': 'Power BI', 'python': 'Python', 'sql': 'SQL'
    }
    
    for keyword, tool in tools_map.items():
        if keyword in job_text and tool not in skills['tools']:
            skills['tools'].append(tool)
    
    # Compétences techniques basiques
    if 'data science' in job_text or 'machine learning' in job_text:
        skills['technical'].append('Data Science')
    if 'consolidation' in job_text or 'ifrs' in job_text:
        skills['technical'].append('consolidation IFRS')
    if 'audit' in job_text:
        skills['technical'].append('audit interne')
    if 'comptabilité' in job_text or 'comptable' in job_text:
        skills['technical'].append('comptabilité')
    
    # Compétences soft basiques
    if 'change' in job_text or 'changement' in job_text:
        skills['soft'].append('conduite du changement')
    if 'formation' in job_text or 'training' in job_text:
        skills['soft'].append('formation')
    if 'agile' in job_text or 'scrum' in job_text:
        skills['soft'].append('Agile')
    
    # Secteur
    if 'banc' in job_text or 'bank' in job_text:
        skills['sector'] = 'le secteur bancaire'
    elif 'fintech' in job_text:
        skills['sector'] = 'la fintech'
    
    return skills


def generate_fallback_message(message_number, prospect_data, job_posting_data):
    """
    Génère un message de fallback
    VERSION V27 : Message 2 intelligent, Message 3 fixe
    
    Args:
        message_number (int): 1, 2 ou 3
        prospect_data (dict): Données du prospect
        job_posting_data (dict): Données de l'annonce
    
    Returns:
        str: Message de fallback formaté
    """
    
    first_name = get_fallback_firstname(prospect_data)
    context_name, is_hiring = get_fallback_context(job_posting_data, prospect_data)
    
    # MESSAGE 1 : Template simple
    if message_number == 1:
        return FALLBACK_MESSAGE_1.format(
            first_name=first_name,
            context=context_name
        )
    
    # MESSAGE 2 : Intelligent avec compétences
    elif message_number == 2:
        skills = extract_skills_for_fallback(job_posting_data)
        
        # Construire observation
        if skills['tools'] and skills['technical']:
            pain_point_observation = f"Le marché combine difficilement {skills['technical'][0]} ({', '.join(skills['tools'][:2])}) et {skills['soft'][0] if skills['soft'] else 'compétences transverses'} dans {skills['sector']}."
        else:
            pain_point_observation = "Le marché actuel rend ce type de recrutement particulièrement complexe : trouver des profils qui combinent expertise technique et vision business devient rare."
        
        # Construire profils
        tool_1 = skills['tools'][0] if skills['tools'] else 'outils métier'
        tool_2 = skills['tools'][1] if len(skills['tools']) > 1 else 'Excel avancé'
        tech_1 = skills['technical'][0] if skills['technical'] else 'expertise technique'
        
        profile_1 = f"- L'un possède une expertise {tech_1} avec maîtrise de {tool_1}, ayant piloté des projets de transformation dans un grand groupe avec forte autonomie opérationnelle."
        profile_2 = f"- L'autre combine {tech_1} et {skills['soft'][0] if skills['soft'] else 'conduite du changement'}, issu d'un environnement international avec expérience significative en {tool_2}."
        
        return FALLBACK_MESSAGE_2_INTELLIGENT.format(
            first_name=first_name,
            context=context_name,
            pain_point_observation=pain_point_observation,
            profile_1=profile_1,
            profile_2=profile_2
        )
    
    # MESSAGE 3 : Template fixe
    elif message_number == 3:
        return FALLBACK_MESSAGE_3_FIXED.format(
            first_name=first_name
        )
    
    else:
        raise ValueError(f"message_number doit être 1, 2 ou 3 (reçu: {message_number})")


def generate_fallback_sequence(prospect_data, job_posting_data, message_1_content=None):
    """
    Génère une séquence complète de fallback
    VERSION V27 : Fallbacks intelligents
    
    Args:
        prospect_data (dict): Données du prospect
        job_posting_data (dict): Données de l'annonce
        message_1_content (str): Contenu du message 1 si déjà généré
    
    Returns:
        dict: Séquence complète
    """
    
    return {
        'subject_lines': generate_fallback_subjects(prospect_data, job_posting_data),
        'message_1': message_1_content or generate_fallback_message(1, prospect_data, job_posting_data),
        'message_2': generate_fallback_message(2, prospect_data, job_posting_data),
        'message_3': generate_fallback_message(3, prospect_data, job_posting_data),
        'is_fallback': True
    }


# ========================================
# FONCTION HELPER
# ========================================

def get_fallback_if_needed(original_sequence, prospect_data, job_posting_data):
    """
    Vérifie si la séquence originale est OK, sinon retourne fallback
    VERSION V27 : Fallback intelligent plutôt que générique
    
    Args:
        original_sequence (dict): Séquence générée par Claude
        prospect_data (dict): Données prospect
        job_posting_data (dict): Données annonce
    
    Returns:
        dict: Séquence originale ou fallback
    """
    
    # Vérifier si la séquence originale est vide ou corrompue
    if not original_sequence:
        return generate_fallback_sequence(prospect_data, job_posting_data)
    
    # Vérifier les champs obligatoires
    required_keys = ['message_1', 'message_2', 'message_3']
    for key in required_keys:
        if key not in original_sequence or not original_sequence[key] or len(str(original_sequence[key])) < 20:
            print(f"⚠️  Séquence corrompue ({key} invalide), utilisation fallback intelligent")
            return generate_fallback_sequence(prospect_data, job_posting_data, original_sequence.get('message_1'))
    
    # Séquence originale OK
    return original_sequence
