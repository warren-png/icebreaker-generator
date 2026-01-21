"""
Validateur de séquences de messages
Vérifie que les messages sont corrects avant envoi
Version: 1.0
"""

from prospection_utils.logger import log_error, log_event

def validate_sequence(sequence_data, prospect_data=None):
    """
    Valide une séquence de messages avant envoi
    
    Args:
        sequence_data (dict): Séquence générée
        prospect_data (dict): Données du prospect (optionnel)
    
    Returns:
        tuple: (is_valid, errors_list)
    """
    errors = []
    
    # ========================================
    # 1. VÉRIFICATIONS DE BASE
    # ========================================
    
    # Messages obligatoires
    required_keys = ['message_1', 'message_2', 'message_3', 'subject_lines']
    for key in required_keys:
        if key not in sequence_data or not sequence_data[key]:
            errors.append(f"❌ {key} manquant ou vide")
    
    # ========================================
    # 2. VÉRIFICATIONS CONTENU
    # ========================================
    
    # Vérifier que [Prénom] n'est pas resté
    for key in ['message_1', 'message_2', 'message_3']:
        if key in sequence_data:
            content = str(sequence_data[key])
            if '[Prénom]' in content or '[prénom]' in content.lower():
                errors.append(f"❌ {key}: Prénom non remplacé - '[Prénom]' présent")
    
    # Vérifier longueur minimale (au moins 50 caractères)
    for key in ['message_1', 'message_2', 'message_3']:
        if key in sequence_data:
            content = str(sequence_data[key])
            if len(content.strip()) < 50:
                errors.append(f"⚠️  {key}: Trop court ({len(content)} caractères)")
    
    # Vérifier longueur maximale (pas plus de 3000 caractères pour email)
    for key in ['message_1', 'message_2', 'message_3']:
        if key in sequence_data:
            content = str(sequence_data[key])
            if len(content) > 3000:
                errors.append(f"⚠️  {key}: Trop long ({len(content)} caractères, max 3000)")
    
    # ========================================
    # 3. VÉRIFICATIONS OBJETS
    # ========================================
    
    if 'subject_lines' in sequence_data:
        subject_lines = str(sequence_data['subject_lines'])
        
        # Vérifier qu'il y a bien plusieurs objets (au moins 2 lignes)
        if '\n' not in subject_lines and len(subject_lines) < 20:
            errors.append("⚠️  subject_lines: Semble incomplet")
        
        # Vérifier longueur des objets (max 100 caractères par ligne)
        for i, line in enumerate(subject_lines.split('\n'), 1):
            if len(line.strip()) > 100:
                errors.append(f"⚠️  Objet ligne {i}: Trop long ({len(line)} caractères)")
    
    # ========================================
    # 4. VÉRIFICATIONS COHÉRENCE
    # ========================================
    
    # Vérifier que les 3 messages sont différents
    if 'message_1' in sequence_data and 'message_2' in sequence_data:
        if sequence_data['message_1'] == sequence_data['message_2']:
            errors.append("⚠️  Message 1 et 2 identiques")
    
    # Vérifier présence de "Bonjour" dans les messages
    for key in ['message_1', 'message_2', 'message_3']:
        if key in sequence_data:
            content = str(sequence_data[key]).lower()
            if 'bonjour' not in content and 'hello' not in content:
                errors.append(f"⚠️  {key}: Manque formule de politesse")
    
    # ========================================
    # 5. VÉRIFICATIONS DONNÉES PROSPECT
    # ========================================
    
    if prospect_data:
        # Vérifier que le nom d'entreprise est présent dans au moins 1 message
        company = prospect_data.get('company', '')
        if company and len(company) > 2:
            found = False
            for key in ['message_1', 'message_2', 'message_3']:
                if key in sequence_data and company.lower() in str(sequence_data[key]).lower():
                    found = True
                    break
            
            if not found:
                errors.append(f"⚠️  Nom entreprise '{company}' absent des messages")
    
    # ========================================
    # 6. RETOUR
    # ========================================
    
    is_valid = len(errors) == 0
    
    if not is_valid:
        log_error('sequence_validation_failed', 'Erreurs de validation', {'errors': errors})
    else:
        log_event('sequence_validation_success', {'message': 'Séquence validée'})
    
    return is_valid, errors


def print_validation_report(is_valid, errors):
    """Affiche un rapport de validation lisible"""
    
    print("\n" + "="*60)
    print("🔍 RAPPORT DE VALIDATION")
    print("="*60)
    
    if is_valid:
        print("✅ Séquence VALIDE - Prête à être envoyée")
    else:
        print(f"❌ Séquence INVALIDE - {len(errors)} erreur(s) détectée(s)")
        print("\nDétails des erreurs:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    
    print("="*60 + "\n")


def validate_and_report(sequence_data, prospect_data=None, raise_on_error=False):
    """
    Valide et affiche le rapport
    
    Args:
        sequence_data (dict): Séquence à valider
        prospect_data (dict): Données prospect (optionnel)
        raise_on_error (bool): Lever une exception si invalide
    
    Returns:
        bool: True si valide, False sinon
    """
    is_valid, errors = validate_sequence(sequence_data, prospect_data)
    print_validation_report(is_valid, errors)
    
    if not is_valid and raise_on_error:
        raise ValueError(f"Séquence invalide: {len(errors)} erreur(s)")
    
    return is_valid


# Fonction helper pour valider rapidement
def is_sequence_valid(sequence_data):
    """Version rapide - retourne juste True/False"""
    is_valid, _ = validate_sequence(sequence_data)
    return is_valid