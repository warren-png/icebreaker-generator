"""
═══════════════════════════════════════════════════════════════════
GOOGLE DRIVE UPLOADER - Upload automatique des CVs
Utilise les credentials existants du job monitor
═══════════════════════════════════════════════════════════════════
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import os


SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'google-credentials.json')


def get_drive_service():
    """
    Initialise le service Google Drive
    Utilise les credentials du job monitor
    """
    
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"Fichier credentials Google Cloud introuvable: {CREDENTIALS_FILE}\n"
            "Placez votre fichier de credentials (JSON) à la racine du projet."
        )
    
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, 
        scopes=SCOPES
    )
    
    service = build('drive', 'v3', credentials=credentials)
    return service


def upload_cv_to_drive(pdf_bytes, filename, folder_id=None):
    """
    Upload un CV (bytes) vers Google Drive
    
    Args:
        pdf_bytes: Bytes du PDF
        filename: Nom du fichier (ex: "CV_Controleur_Gestion_2025.pdf")
        folder_id: ID du dossier Google Drive (optionnel)
    
    Returns:
        Dict avec 'id', 'url', 'name'
    """
    
    try:
        service = get_drive_service()
        
        # Métadonnées du fichier
        file_metadata = {
            'name': filename,
            'mimeType': 'application/pdf'
        }
        
        # Si folder_id fourni, uploader dans ce dossier
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        # Upload
        media = MediaIoBaseUpload(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            resumable=True
        )
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink'
        ).execute()
        
        # Rendre le fichier accessible avec le lien (lecture seule)
        service.permissions().create(
            fileId=file['id'],
            body={
                'type': 'anyone',
                'role': 'reader'
            }
        ).execute()
        
        return {
            'id': file['id'],
            'url': file.get('webViewLink'),
            'name': file['name']
        }
        
    except Exception as e:
        print(f"Erreur upload Google Drive: {e}")
        raise


def create_cv_folder(folder_name="CVs Icebreaker"):
    """
    Crée un dossier dans Google Drive pour les CVs
    
    Returns:
        folder_id
    """
    
    try:
        service = get_drive_service()
        
        # Vérifier si le dossier existe déjà
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=query, fields='files(id, name)').execute()
        folders = results.get('files', [])
        
        if folders:
            return folders[0]['id']
        
        # Créer le dossier
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        folder = service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()
        
        return folder['id']
        
    except Exception as e:
        print(f"Erreur création dossier: {e}")
        return None


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

def upload_cv(pdf_bytes, job_title, prospect_name=None, folder_name="CVs Icebreaker"):
    """
    Fonction all-in-one pour upload un CV
    
    Args:
        pdf_bytes: Bytes du PDF
        job_title: Titre du poste
        prospect_name: Nom prospect (optionnel)
        folder_name: Nom du dossier Google Drive
    
    Returns:
        Dict avec 'id', 'url', 'name' ou None si erreur
    """
    
    try:
        # Créer/récupérer le dossier
        folder_id = create_cv_folder(folder_name)
        
        # Générer nom de fichier
        filename = generate_filename(job_title, prospect_name)
        
        # Upload
        result = upload_cv_to_drive(pdf_bytes, filename, folder_id)
        
        print(f"✅ CV uploadé : {result['url']}")
        return result
        
    except Exception as e:
        print(f"❌ Erreur upload CV: {e}")
        return None
