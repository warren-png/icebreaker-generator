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
    "name": "Entourage Recrutement",
    "description": "Nous aidons les entreprises à recruter les talents dans le domaine de la finance",
    "value_proposition": "Notre expertise permet d'identifier votre future recrue avec précision"
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