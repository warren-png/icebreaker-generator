"""
═══════════════════════════════════════════════════════════════════
GOOGLE DRIVE UPLOADER - Upload automatique des CVs
Utilise les credentials Google Cloud avec support Streamlit secrets
═══════════════════════════════════════════════════════════════════
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import os

# ID du dossier partagé dans Google Drive (env var prioritaire, fallback hardcodé)
FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID', "0AOjfTqrPTHWmUk9PVA")

SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE')


def get_drive_service():
    """
    Initialise le service Google Drive
    Utilise Streamlit secrets si disponible, sinon fichier local
    """
    try:
        # Essayer d'abord avec Streamlit secrets (pour Streamlit Cloud)
        import streamlit as st
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=SCOPES
            )
            service = build('drive', 'v3', credentials=credentials)
            print("✅ Google Drive service initialisé via Streamlit secrets")
            return service
    except Exception as e:
        print(f"⚠️ Pas de Streamlit secrets disponibles: {e}")

    # Fallback : fichier local (pour développement local)
    if not CREDENTIALS_FILE or not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"❌ Fichier credentials Google Cloud introuvable: {CREDENTIALS_FILE}\n"
            "Et pas de secrets Streamlit configurés.\n"
            "Place ton fichier google-credentials.json à la racine du projet."
        )
    
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, 
        scopes=SCOPES
    )
    
    service = build('drive', 'v3', credentials=credentials)
    print("✅ Google Drive service initialisé via fichier local")
    return service


def upload_cv_to_drive(pdf_bytes, filename, folder_id):
    """
    Upload un CV (bytes) vers Google Drive
    
    Args:
        pdf_bytes: Bytes du PDF
        filename: Nom du fichier (ex: "CV_Controleur_Gestion_2025.pdf")
        folder_id: ID du dossier Google Drive
    
    Returns:
        Dict avec 'id', 'url', 'name'
    """
    
    try:
        service = get_drive_service()
        
        # Métadonnées du fichier
        file_metadata = {
            'name': filename,
            'mimeType': 'application/pdf',
            'parents': [folder_id]  # Upload dans le dossier partagé
        }
        
        # Upload
        media = MediaIoBaseUpload(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            resumable=True
        )
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink',
            supportsAllDrives=True
        ).execute()
        
        # Rendre le fichier accessible avec le lien (lecture seule)
        service.permissions().create(
            fileId=file['id'],
            body={
                'type': 'anyone',
                'role': 'reader'
            },
            supportsAllDrives=True
        ).execute()
        
        return {
            'id': file['id'],
            'url': file.get('webViewLink'),
            'name': file['name']
        }
        
    except Exception as e:
        print(f"Erreur upload Google Drive: {e}")
        raise


def generate_filename(job_title, prospect_name=None):
    """
    Génère un nom de fichier unique et descriptif
    
    Args:
        job_title: Titre du poste (ex: "Contrôleur de Gestion")
        prospect_name: Nom du prospect (optionnel)
    
    Returns:
        String (ex: "CV_Controleur_Gestion_20250211_143022.pdf")
    """
    
    import re
    from datetime import datetime
    
    # Nettoyer le titre
    title_clean = re.sub(r'[^\w\s-]', '', job_title)
    title_clean = re.sub(r'\s+', '_', title_clean)
    title_clean = title_clean[:50]  # Limiter la longueur
    
    # Timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if prospect_name:
        name_clean = re.sub(r'[^\w\s-]', '', prospect_name)
        name_clean = re.sub(r'\s+', '_', name_clean)
        filename = f"CV_{title_clean}_{name_clean}_{timestamp}.pdf"
    else:
        filename = f"CV_{title_clean}_{timestamp}.pdf"
    
    return filename


# ========================================
# FONCTION PRINCIPALE
# ========================================

def upload_cv(pdf_bytes, job_title, prospect_name=None):
    """
    Fonction all-in-one pour upload un CV
    
    Args:
        pdf_bytes: Bytes du PDF
        job_title: Titre du poste
        prospect_name: Nom prospect (optionnel)
    
    Returns:
        Dict avec 'id', 'url', 'name' ou None si erreur
    """
    
    try:
        # Générer nom de fichier
        filename = generate_filename(job_title, prospect_name)
        
        # Upload dans le dossier partagé
        result = upload_cv_to_drive(pdf_bytes, filename, FOLDER_ID)
        
        print(f"✅ CV uploadé : {result['url']}")
        return result
        
    except Exception as e:
        print(f"❌ Erreur upload CV: {e}")
        return None
