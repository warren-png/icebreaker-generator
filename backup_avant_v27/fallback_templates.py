"""
Templates de fallback pour quand l'API Claude est indisponible
Messages pré-écrits de qualité pour éviter les crashs
Version: 1.0
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
# TEMPLATES MESSAGES
# ========================================

FALLBACK_MESSAGE_1 = """Bonjour {first_name},

Je me permets de vous contacter concernant {context}.

Le marché des profils finance combine rarement expertise technique et vision business. C'est précisément sur l'identification de ces profils hybrides que j'accompagne mes clients.

Seriez-vous ouvert à un échange de 15 minutes sur ce sujet ?

Cordialement,
{signature}"""

FALLBACK_MESSAGE_2 = """Bonjour {first_name},

Je fais suite à mon message concernant {context}.

En observant le marché, recruter des profils finance crée souvent un dilemme : soit on a la technique mais pas le business, soit l'inverse. Les profils qui combinent les deux sont rares et très sollicités.

C'est précisément sur l'identification de ces profils hybrides que j'accompagne mes clients.

Auriez-vous un rapide créneau de 15 min prochainement ou seriez-vous ouvert à recevoir des candidatures qui correspondent à votre besoin ?

Cordialement,
{signature}"""

FALLBACK_MESSAGE_3 = """Bonjour {first_name},

Sans retour de votre part, je ne vous solliciterai plus sur ce sujet.

Le marché des profils finance senior est particulièrement tendu. D'après nos observations, 70% des recrutements sur ces postes prennent plus de 3 mois.

Je clos ce dossier. Si toutefois la tension sur ces compétences spécifiques venait à freiner vos projets, je reste à votre disposition.

Bonne continuation,
{signature}"""

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
    """Trouve le prénom ou retourne placeholder"""
    target_keys = ['first_name', 'firstname', 'first name', 'prénom', 'prenom', 'name']
    for key, value in prospect_data.items():
        if str(key).lower().strip() in target_keys:
            if value and str(value).strip():
                return str(value).strip().capitalize()
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


def generate_fallback_message(message_number, prospect_data, job_posting_data, signature="[Votre signature]"):
    """
    Génère un message de fallback
    
    Args:
        message_number (int): 1, 2 ou 3
        prospect_data (dict): Données du prospect
        job_posting_data (dict): Données de l'annonce
        signature (str): Signature à inclure
    
    Returns:
        str: Message de fallback formaté
    """
    
    first_name = get_fallback_firstname(prospect_data)
    context_name, is_hiring = get_fallback_context(job_posting_data, prospect_data)
    
    # Sélectionner le template
    if message_number == 1:
        template = FALLBACK_MESSAGE_1
    elif message_number == 2:
        template = FALLBACK_MESSAGE_2
    elif message_number == 3:
        template = FALLBACK_MESSAGE_3
    else:
        raise ValueError(f"message_number doit être 1, 2 ou 3 (reçu: {message_number})")
    
    # Formater le message
    message = template.format(
        first_name=first_name,
        context=context_name,
        signature=signature
    )
    
    return message


def generate_fallback_sequence(prospect_data, job_posting_data, message_1_content=None, signature="[Votre signature]"):
    """
    Génère une séquence complète de fallback
    
    Args:
        prospect_data (dict): Données du prospect
        job_posting_data (dict): Données de l'annonce
        message_1_content (str): Contenu du message 1 si déjà généré
        signature (str): Signature à inclure
    
    Returns:
        dict: Séquence complète
    """
    
    return {
        'subject_lines': generate_fallback_subjects(prospect_data, job_posting_data),
        'message_1': message_1_content or generate_fallback_message(1, prospect_data, job_posting_data, signature),
        'message_2': generate_fallback_message(2, prospect_data, job_posting_data, signature),
        'message_3': generate_fallback_message(3, prospect_data, job_posting_data, signature),
        'is_fallback': True  # Flag pour indiquer que c'est un fallback
    }


# ========================================
# FONCTION HELPER
# ========================================

def get_fallback_if_needed(original_sequence, prospect_data, job_posting_data):
    """
    Vérifie si la séquence originale est OK, sinon retourne fallback
    
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
            print(f"⚠️  Séquence corrompue ({key} invalide), utilisation fallback")
            return generate_fallback_sequence(prospect_data, job_posting_data)
    
    # Séquence originale OK
    return original_sequence
