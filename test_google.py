"""Test de connexion Google Sheets"""
from config import *
import gspread
from google.oauth2.service_account import Credentials

print("🧪 Test de connexion Google Sheets...\n")

try:
    # Connexion
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    credentials = Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_FILE,
        scopes=scopes
    )
    
    client = gspread.authorize(credentials)
    sheet = client.open(GOOGLE_SHEET_NAME).worksheet(WORKSHEET_NAME)
    
    print(f"✅ Connexion réussie !")
    print(f"   Feuille : {GOOGLE_SHEET_NAME}")
    print(f"   Onglet : {WORKSHEET_NAME}")
    
    # Lire la première ligne pour test
    first_row = sheet.row_values(1)
    print(f"\n   Colonnes détectées : {first_row}")
    
    # Compter les lignes
    all_data = sheet.get_all_records()
    print(f"   Nombre de prospects : {len(all_data)}")
    
except FileNotFoundError:
    print(f"❌ Fichier {GOOGLE_CREDENTIALS_FILE} non trouvé !")
    print("   Avez-vous bien téléchargé et placé le fichier google-credentials.json ?")
except Exception as e:
    print(f"❌ Erreur : {e}")
    import traceback
    traceback.print_exc()