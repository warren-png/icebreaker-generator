"""
Système de logging structuré pour l'outil de prospection
Version: 1.0
"""

import logging
import json
from datetime import datetime
import os

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
        log_data.update(data)
    
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
        error_data['context'] = context
    
    logger.error(json.dumps(error_data, ensure_ascii=False))