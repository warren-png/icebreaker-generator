"""
Sync du corpus du coach vers/depuis Google Drive.

Permet à l'app déployée sur Streamlit Cloud de lire le corpus depuis Drive
sans le committer dans GitHub (contenu confidentiel du coaching).

Usage :
    # Upload du corpus local vers Drive (à faire après chaque fetch_notion)
    python -m coach_prospection.drive_sync upload

    # Download depuis Drive vers local (au runtime de l'app, mis en cache)
    python -m coach_prospection.drive_sync download

Le sous-dossier "Coach Prospection - Corpus" est créé automatiquement dans le
dossier Drive racine (GOOGLE_DRIVE_FOLDER_ID).
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2 import service_account

from coach_prospection.corpus_loader import CORPUS_DIR

CORPUS_FOLDER_NAME = "Coach_Prospection_Corpus"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
ROOT_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "0AOjfTqrPTHWmUk9PVA")


def _get_drive_service():
    """Crée un client Drive depuis Streamlit secrets ou fichier local."""
    # Streamlit secrets (prod)
    try:
        import streamlit as st  # noqa: F401

        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=SCOPES
            )
            return build("drive", "v3", credentials=credentials)
    except Exception:
        pass

    # Fichier local (dev)
    creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE")
    if not creds_file or not os.path.exists(creds_file):
        raise FileNotFoundError(
            "Aucune credentials Google trouvée. Définis GOOGLE_CREDENTIALS_FILE "
            "dans .env ou configure st.secrets['gcp_service_account']."
        )
    credentials = service_account.Credentials.from_service_account_file(
        creds_file, scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials)


def _find_or_create_subfolder(service, parent_id: str, name: str) -> str:
    """Retourne l'ID du sous-dossier, le crée s'il n'existe pas (parmi ceux que voit l'app)."""
    query = (
        f"name='{name}' and mimeType='application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents and trashed=false"
    )
    res = service.files().list(
        q=query,
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    # Création
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(
        body=metadata, fields="id", supportsAllDrives=True
    ).execute()
    return folder["id"]


def _list_corpus_files_on_drive(service, folder_id: str) -> dict[str, str]:
    """Retourne {filename: file_id} pour tous les .md du dossier corpus sur Drive."""
    results: dict[str, str] = {}
    page_token = None
    while True:
        res = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false and name contains '.md'",
            fields="nextPageToken, files(id, name)",
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageSize=200,
        ).execute()
        for f in res.get("files", []):
            results[f["name"]] = f["id"]
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return results


def upload_corpus_to_drive(corpus_dir: Path = CORPUS_DIR) -> dict:
    """Upload tous les .md du corpus local vers Drive (écrase les versions existantes).

    Retourne un dict de stats : files_uploaded, files_updated, errors.
    """
    if not corpus_dir.exists() or not list(corpus_dir.glob("*.md")):
        raise FileNotFoundError(
            f"Aucun .md trouvé dans {corpus_dir}. Lance d'abord fetch_notion."
        )
    service = _get_drive_service()
    folder_id = _find_or_create_subfolder(service, ROOT_FOLDER_ID, CORPUS_FOLDER_NAME)
    existing = _list_corpus_files_on_drive(service, folder_id)

    stats = {"files_uploaded": 0, "files_updated": 0, "errors": []}
    for md_path in sorted(corpus_dir.glob("*.md")):
        try:
            content_bytes = md_path.read_bytes()
            media = MediaIoBaseUpload(
                io.BytesIO(content_bytes), mimetype="text/markdown", resumable=True
            )
            if md_path.name in existing:
                service.files().update(
                    fileId=existing[md_path.name],
                    media_body=media,
                    supportsAllDrives=True,
                ).execute()
                stats["files_updated"] += 1
                print(f"  ↻ {md_path.name}")
            else:
                service.files().create(
                    body={"name": md_path.name, "parents": [folder_id]},
                    media_body=media,
                    fields="id",
                    supportsAllDrives=True,
                ).execute()
                stats["files_uploaded"] += 1
                print(f"  ↑ {md_path.name}")
        except HttpError as e:
            stats["errors"].append(f"{md_path.name}: {e}")
            print(f"  ❌ {md_path.name}: {e}")
    return stats


def download_corpus_from_drive(target_dir: Path = CORPUS_DIR) -> dict:
    """Télécharge tous les .md du dossier Drive 'Coach_Prospection_Corpus' vers target_dir.

    Retourne {files_downloaded, total_bytes}.
    """
    service = _get_drive_service()
    folder_id = _find_or_create_subfolder(service, ROOT_FOLDER_ID, CORPUS_FOLDER_NAME)
    drive_files = _list_corpus_files_on_drive(service, folder_id)

    target_dir.mkdir(parents=True, exist_ok=True)
    stats = {"files_downloaded": 0, "total_bytes": 0}
    for name, fid in drive_files.items():
        buf = io.BytesIO()
        request = service.files().get_media(fileId=fid, supportsAllDrives=True)
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        data = buf.getvalue()
        (target_dir / name).write_bytes(data)
        stats["files_downloaded"] += 1
        stats["total_bytes"] += len(data)
    return stats


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    if cmd == "upload":
        print(f"📤 Upload du corpus local → Drive ({CORPUS_FOLDER_NAME})…\n")
        stats = upload_corpus_to_drive()
        print(
            f"\n✅ Terminé : {stats['files_uploaded']} nouveaux, "
            f"{stats['files_updated']} mis à jour, {len(stats['errors'])} erreurs."
        )
    elif cmd == "download":
        print(f"📥 Download du corpus Drive → local…\n")
        stats = download_corpus_from_drive()
        print(
            f"\n✅ Terminé : {stats['files_downloaded']} fichiers "
            f"({stats['total_bytes']/1000:.0f} ko)."
        )
    else:
        print("Usage : python -m coach_prospection.drive_sync [upload|download]")
        sys.exit(1)


if __name__ == "__main__":
    main()
