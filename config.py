# Configuration de l'automatisation Icebreaker
import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# ========================================
# 1. CLÉ API CLAUDE
# ========================================
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# ========================================
# 2. CLÉ API APIFY
# ========================================
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

# ========================================
# 3. CLÉ API SERPER
# ========================================
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# ========================================
# 4. ACTEURS APIFY
# ========================================
APIFY_ACTORS = {
    "profile": "dev_fusion/Linkedin-Profile-Scraper", 
    "profile_posts": "supreme_coder/Linkedin-post",
    "company_posts": "supreme_coder/Linkedin-post",
    "company_profile": "dev_fusion/Linkedin-Company-Scraper"
}

# ========================================
# 5. GOOGLE SHEET
# ========================================
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Prospects Icebreaker")
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME", "Feuille 1")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "google-credentials.json")

# ========================================
# 6. INFORMATIONS ENTREPRISE
# ========================================

COMPANY_INFO = {
    # Identité
    'name': 'Entourage Recrutement',
    
    # Positionnement (essence de votre différence)
    'positioning': 'Cabinet de chasse spécialisé en recrutements critiques de profils finance à fort impact business',
    
    # Notre rôle unique
    'mission': 'Sécuriser les décisions de recrutement sur des postes où une erreur est coûteuse en temps, organisation et crédibilité managériale',
    
    # Différenciateurs clés (3 points max)
    'differentiators': [
        'Approche 100% chasse ciblée et confidentielle (pas de diffusion d\'annonces)',
        'Évaluation orientée contexte : capacité à réussir CHEZ VOUS, pas juste "savoir faire le métier"',
        'Compréhension fine du besoin réel : priorités opérationnelles, irritants équipes, critères d\'échec'
    ],
    
    # Profils recrutés (synthèse)
    'profiles': 'DAF/CFO/RAF, Contrôle de gestion/FP&A, M&A/Corporate Dev, Transformation Finance, BI/Data Finance, MOA Finance',
    
    # Clients types
    'clients': 'Groupes, ETI, filiales. Secteurs : assurance, banque, services financiers. Contextes : transformation, structuration finance, croissance externe',
    
    # Ce que vous NE faites PAS
    'not_us': 'Pas de recrutement de masse, pas de start-ups early stage, pas de logiques de volume',
    
    # Valeur client (ce qu'ils gagnent)
    'client_value': 'Moins d\'entretiens non pertinents, profils réellement comparables, décision plus rapide et sécurisée, meilleure tenue dans le temps',
    
    # Philosophie icebreaker
    'icebreaker_philosophy': 'L\'icebreaker doit démontrer qu\'on comprend LEURS enjeux business/finance spécifiques. Notre expertise doit transparaître dans la qualité de l\'analyse, pas dans l\'auto-promotion.'
}


# ========================================
# 7. PARAMÈTRES
# ========================================
DELAY_BETWEEN_PROSPECTS = 5  # Délai entre chaque prospect (secondes)
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Paramètres de recherche web
WEB_SEARCH_ENABLED = True  # Activer/désactiver facilement
MAX_SEARCH_RESULTS = 5  # Limiter le nombre de résultats

# ========================================
# 8. COLONNES GOOGLE SHEET
# ========================================
COL_LINKEDIN_URL = 4      # Colonne D
COL_HOOKS = 7             # Colonne G
COL_ICEBREAKER = 11       # Colonne K

# ========================================
# 9. VÉRIFICATION DES CLÉS API
# ========================================
def check_api_keys():
    """Vérifie que toutes les clés API sont configurées"""
    missing_keys = []
    
    if not ANTHROPIC_API_KEY:
        missing_keys.append("ANTHROPIC_API_KEY")
    if not APIFY_API_TOKEN:
        missing_keys.append("APIFY_API_TOKEN")
    if not SERPER_API_KEY:
        missing_keys.append("SERPER_API_KEY")
    
    if missing_keys:
        raise ValueError(
            f"❌ Clés API manquantes dans le fichier .env : {', '.join(missing_keys)}\n"
            f"Veuillez créer un fichier .env avec ces clés."
        )
    
    print("✅ Toutes les clés API sont configurées")

# Vérifier au démarrage
if __name__ != "__main__":
    check_api_keys()