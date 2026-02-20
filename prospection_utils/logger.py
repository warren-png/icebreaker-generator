"""
Système de logging structuré pour l'outil de prospection
Version: 1.1 - Redaction PII
"""

import logging
import json
import re
from datetime import datetime
import os

# Champs considérés comme PII — leur valeur sera masquée dans les logs
_PII_FIELDS = {
    'name', 'full_name', 'user_full name', 'email', 'linkedin_url',
    'firstname', 'lastname', 'prenom', 'nom', 'prospect_name',
    'phone', 'telephone', 'mobile',
}

_EMAIL_RE = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
_LINKEDIN_RE = re.compile(r'https?://(?:www\.)?linkedin\.com/\S+')


def _redact_value(value):
    """Masque une valeur PII"""
    if not value:
        return value
    s = str(value)
    if len(s) <= 2:
        return '***'
    return s[0] + '***' + s[-1]


def _redact_dict(data):
    """Parcourt récursivement un dict et masque les champs PII"""
    if not isinstance(data, dict):
        return data
    redacted = {}
    for k, v in data.items():
        if k.lower() in _PII_FIELDS:
            redacted[k] = _redact_value(v)
        elif isinstance(v, dict):
            redacted[k] = _redact_dict(v)
        elif isinstance(v, str):
            # Masquer emails et URLs LinkedIn inline
            v = _EMAIL_RE.sub('[email]', v)
            v = _LINKEDIN_RE.sub('[linkedin_url]', v)
            redacted[k] = v
        else:
            redacted[k] = v
    return redacted

# Créer le dossier logs s'il n'existe pas
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configuration du logger
def setup_logger():
    """Configure le logger avec fichier + console"""
    
    # Nom du fichier avec la date
    log_filename = f'logs/prospection_{datetime.now().strftime("%Y%m%d")}.log'
    
    # Configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            # Fichier
            logging.FileHandler(log_filename, encoding='utf-8'),
            # Console
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('prospection')

# Logger global
logger = setup_logger()

def log_event(event_type, data=None):
    """
    Log un événement avec données structurées
    
    Args:
        event_type (str): Type d'événement (ex: 'sequence_start', 'api_call', 'error')
        data (dict): Données additionnelles à logger
    """
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'event': event_type,
    }
    
    if data:
        log_data.update(_redact_dict(data))

    logger.info(json.dumps(log_data, ensure_ascii=False))

def log_error(error_type, error_message, context=None):
    """
    Log une erreur avec contexte
    
    Args:
        error_type (str): Type d'erreur
        error_message (str): Message d'erreur
        context (dict): Contexte additionnel
    """
    error_data = {
        'timestamp': datetime.now().isoformat(),
        'error_type': error_type,
        'error_message': str(error_message)
    }
    
    if context:
        error_data['context'] = _redact_dict(context)

    logger.error(json.dumps(error_data, ensure_ascii=False))