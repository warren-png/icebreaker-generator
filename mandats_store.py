"""
═══════════════════════════════════════════════════════════════════
MANDATS — stockage des mandats (fiche de poste, audios, transcriptions)
═══════════════════════════════════════════════════════════════════

Arborescence dans le Drive partagé (GOOGLE_DRIVE_FOLDER_ID) :

    Mandats/
      2026-10-04 — Entreprise — Nom du mandat/
        mandat.json                      ← métadonnées (nom, entreprise, date, statut…)
        Fiche de poste — fiche.pdf
        Fiche de poste (texte).txt
        Audio — echange_manager.m4a
        Transcription — echange_manager.txt

Chaque fichier créé par l'app porte des appProperties (ent_app=mandats,
ent_kind=meta|fiche|audio|transcript|scorecard) : une seule requête suffit pour lister
tous les mandats et leurs fichiers.

En développement, MANDATS_STORAGE=local stocke tout dans MANDATS_LOCAL_DIR
(par défaut ./mandats_local) avec la même interface.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

APP_KEY = "mandats"
ROOT_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "0AOjfTqrPTHWmUk9PVA")
MANDATS_FOLDER_NAME = "Mandats"
META_FILENAME = "mandat.json"
FOLDER_MIME = "application/vnd.google-apps.folder"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# Taille max d'une valeur appProperties (clé + valeur ≤ 124 octets côté Drive)
_PROP_MAX = 80


class StorageError(Exception):
    """Erreur de stockage lisible par l'utilisateur."""


def _clean_props(props: dict | None) -> dict:
    out = {"ent_app": APP_KEY}
    for k, v in (props or {}).items():
        if v is None:
            continue
        v = str(v)
        while len(v.encode("utf-8")) > _PROP_MAX:
            v = v[:-1]
        out[k] = v
    return out


def folder_name_for(meta: dict) -> str:
    parts = [meta.get("date", ""), meta.get("entreprise", ""), meta.get("nom", "")]
    name = " — ".join(p.strip() for p in parts if p and p.strip())
    return name.replace("/", "-")[:200] or "Mandat"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ─────────────────────────────────────────────────────────────────────────────
# Google Drive
# ─────────────────────────────────────────────────────────────────────────────


def _drive_credentials():
    from google.oauth2 import service_account

    try:
        import streamlit as st

        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            return service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=SCOPES
            )
    except Exception:
        pass

    creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE")
    if not creds_file or not os.path.exists(creds_file):
        raise StorageError(
            "Aucune credentials Google trouvée. Configure st.secrets['gcp_service_account'] "
            "(Streamlit Cloud) ou GOOGLE_CREDENTIALS_FILE dans .env (local)."
        )
    return service_account.Credentials.from_service_account_file(creds_file, scopes=SCOPES)


class DriveStore:
    """Stockage des mandats dans le Drive partagé Entourage."""

    def __init__(self):
        from googleapiclient.discovery import build

        self._build = build
        self._creds = _drive_credentials()
        self._local = threading.local()
        self._mandats_folder_id: str | None = None

    # -- infra ---------------------------------------------------------------

    @property
    def svc(self):
        # httplib2 n'est pas thread-safe : un client par thread
        if not hasattr(self._local, "svc"):
            self._local.svc = self._build(
                "drive", "v3", credentials=self._creds, cache_discovery=False
            )
        return self._local.svc

    def _call(self, request):
        from googleapiclient.errors import HttpError

        try:
            return request.execute()
        except HttpError as e:
            status = getattr(e.resp, "status", None)
            if status == 403:
                raise StorageError(
                    "Google Drive a refusé l'opération (403). Le compte de service doit être "
                    "« Gestionnaire de contenu » du Drive partagé pour pouvoir supprimer."
                ) from e
            if status == 404:
                raise StorageError("Fichier introuvable sur le Drive (déjà supprimé ?).") from e
            raise StorageError(f"Erreur Google Drive : {e}") from e

    def _mandats_folder(self) -> str:
        if self._mandats_folder_id:
            return self._mandats_folder_id
        q = (
            f"name='{MANDATS_FOLDER_NAME}' and mimeType='{FOLDER_MIME}' "
            f"and '{ROOT_FOLDER_ID}' in parents and trashed=false"
        )
        res = self._call(
            self.svc.files().list(
                q=q,
                fields="files(id)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
        )
        files = res.get("files", [])
        if files:
            self._mandats_folder_id = files[0]["id"]
        else:
            folder = self._call(
                self.svc.files().create(
                    body={
                        "name": MANDATS_FOLDER_NAME,
                        "mimeType": FOLDER_MIME,
                        "parents": [ROOT_FOLDER_ID],
                    },
                    fields="id",
                    supportsAllDrives=True,
                )
            )
            self._mandats_folder_id = folder["id"]
        return self._mandats_folder_id

    @staticmethod
    def _file_dict(f: dict) -> dict:
        props = f.get("appProperties") or {}
        return {
            "id": f["id"],
            "name": f.get("name", ""),
            "mime": f.get("mimeType", ""),
            "size": int(f.get("size") or 0),
            "created": f.get("createdTime", ""),
            "kind": props.get("ent_kind", ""),
            "props": props,
            "mandat_id": (f.get("parents") or [None])[0],
        }

    # -- lecture -------------------------------------------------------------

    def snapshot(self) -> dict:
        """Tous les mandats + leurs fichiers, en une requête de listing."""
        self._mandats_folder()
        files: list[dict] = []
        page_token = None
        while True:
            res = self._call(
                self.svc.files().list(
                    q=(
                        f"appProperties has {{ key='ent_app' and value='{APP_KEY}' }} "
                        "and trashed=false"
                    ),
                    corpora="allDrives",
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    pageSize=1000,
                    pageToken=page_token,
                    fields=(
                        "nextPageToken, files(id, name, mimeType, size, createdTime, "
                        "parents, appProperties)"
                    ),
                )
            )
            files.extend(res.get("files", []))
            page_token = res.get("nextPageToken")
            if not page_token:
                break

        metas = [f for f in files if (f.get("appProperties") or {}).get("ent_kind") == "meta"]

        def load(meta_file):
            try:
                data = json.loads(self.download(meta_file["id"]).decode("utf-8"))
            except Exception:
                return None
            data["id"] = (meta_file.get("parents") or [None])[0]
            data["_meta_file_id"] = meta_file["id"]
            return data

        with ThreadPoolExecutor(max_workers=8) as pool:
            mandats = [m for m in pool.map(load, metas) if m and m.get("id")]

        by_mandat: dict[str, list[dict]] = {}
        for f in files:
            d = self._file_dict(f)
            if d["kind"] in ("fiche", "audio", "transcript", "scorecard"):
                by_mandat.setdefault(d["mandat_id"], []).append(d)
        return {"mandats": mandats, "files": by_mandat}

    def download(self, file_id: str) -> bytes:
        from googleapiclient.http import MediaIoBaseDownload

        buf = io.BytesIO()
        request = self.svc.files().get_media(fileId=file_id, supportsAllDrives=True)
        downloader = MediaIoBaseDownload(buf, request, chunksize=16 * 1024 * 1024)
        done = False
        try:
            while not done:
                _, done = downloader.next_chunk()
        except Exception as e:
            raise StorageError(f"Téléchargement impossible : {e}") from e
        return buf.getvalue()

    def folder_link(self, mandat_id: str) -> str | None:
        return f"https://drive.google.com/drive/folders/{mandat_id}"

    # -- écriture ------------------------------------------------------------

    def create_mandat(self, meta: dict) -> str:
        parent = self._mandats_folder()
        folder = self._call(
            self.svc.files().create(
                body={
                    "name": folder_name_for(meta),
                    "mimeType": FOLDER_MIME,
                    "parents": [parent],
                    "appProperties": _clean_props({"ent_kind": "folder"}),
                },
                fields="id",
                supportsAllDrives=True,
            )
        )
        mandat_id = folder["id"]
        meta = {**meta, "created_at": _now_iso(), "updated_at": _now_iso()}
        self.upload(
            mandat_id,
            META_FILENAME,
            json.dumps(_public_meta(meta), ensure_ascii=False, indent=2).encode("utf-8"),
            "application/json",
            {"ent_kind": "meta"},
        )
        return mandat_id

    def save_meta(self, mandat: dict) -> None:
        meta = {**mandat, "updated_at": _now_iso()}
        body = json.dumps(_public_meta(meta), ensure_ascii=False, indent=2).encode("utf-8")
        if mandat.get("_meta_file_id"):
            self.replace_content(mandat["_meta_file_id"], META_FILENAME, body, "application/json")
        else:
            self.upload(mandat["id"], META_FILENAME, body, "application/json", {"ent_kind": "meta"})
        self._call(
            self.svc.files().update(
                fileId=mandat["id"],
                body={"name": folder_name_for(meta)},
                supportsAllDrives=True,
            )
        )

    def upload(self, mandat_id: str, name: str, data: bytes, mime: str, props: dict) -> dict:
        from googleapiclient.http import MediaIoBaseUpload

        media = MediaIoBaseUpload(
            io.BytesIO(data),
            mimetype=mime or "application/octet-stream",
            resumable=len(data) > 5 * 1024 * 1024,
            chunksize=8 * 1024 * 1024,
        )
        f = self._call(
            self.svc.files().create(
                body={"name": name, "parents": [mandat_id], "appProperties": _clean_props(props)},
                media_body=media,
                fields="id, name, mimeType, size, createdTime, parents, appProperties",
                supportsAllDrives=True,
            )
        )
        return self._file_dict(f)

    def replace_content(self, file_id: str, name: str, data: bytes, mime: str, props: dict | None = None) -> None:
        from googleapiclient.http import MediaIoBaseUpload

        media = MediaIoBaseUpload(
            io.BytesIO(data),
            mimetype=mime or "application/octet-stream",
            resumable=len(data) > 5 * 1024 * 1024,
        )
        body: dict = {"name": name}
        if props is not None:
            body["appProperties"] = _clean_props(props)
        self._call(
            self.svc.files().update(
                fileId=file_id, body=body, media_body=media, supportsAllDrives=True
            )
        )

    def trash(self, file_or_folder_id: str) -> None:
        """Met à la corbeille du Drive (récupérable 30 jours)."""
        self._call(
            self.svc.files().update(
                fileId=file_or_folder_id, body={"trashed": True}, supportsAllDrives=True
            )
        )


# ─────────────────────────────────────────────────────────────────────────────
# Stockage local (développement)
# ─────────────────────────────────────────────────────────────────────────────


class LocalStore:
    """Même interface que DriveStore, sur le disque. Pour tester l'UI en local."""

    def __init__(self, root: str | None = None):
        self.root = Path(root or os.getenv("MANDATS_LOCAL_DIR", "mandats_local")) / MANDATS_FOLDER_NAME
        self.root.mkdir(parents=True, exist_ok=True)

    def _props_path(self, path: Path) -> Path:
        return path.parent / f".{path.name}.props.json"

    def _find(self, file_id: str) -> Path:
        for p in self.root.rglob("*"):
            if p.is_file() and not p.name.startswith("."):
                pp = self._props_path(p)
                if pp.exists() and json.loads(pp.read_text())["id"] == file_id:
                    return p
        raise StorageError("Fichier introuvable.")

    def snapshot(self) -> dict:
        mandats, by_mandat = [], {}
        for folder in sorted(self.root.iterdir()):
            if not folder.is_dir() or folder.name.startswith("."):
                continue
            mandat_id = (folder / ".id").read_text()
            for p in folder.iterdir():
                if p.name.startswith("."):
                    continue
                info = json.loads(self._props_path(p).read_text())
                if info["props"].get("ent_kind") == "meta":
                    data = json.loads(p.read_text())
                    data["id"] = mandat_id
                    data["_meta_file_id"] = info["id"]
                    mandats.append(data)
                else:
                    by_mandat.setdefault(mandat_id, []).append({
                        "id": info["id"],
                        "name": p.name,
                        "mime": info.get("mime", ""),
                        "size": p.stat().st_size,
                        "created": info.get("created", ""),
                        "kind": info["props"].get("ent_kind", ""),
                        "props": info["props"],
                        "mandat_id": mandat_id,
                    })
        return {"mandats": mandats, "files": by_mandat}

    def _folder(self, mandat_id: str) -> Path:
        for folder in self.root.iterdir():
            if folder.is_dir() and (folder / ".id").exists() and (folder / ".id").read_text() == mandat_id:
                return folder
        raise StorageError("Mandat introuvable.")

    def download(self, file_id: str) -> bytes:
        return self._find(file_id).read_bytes()

    def folder_link(self, mandat_id: str) -> str | None:
        return None

    def create_mandat(self, meta: dict) -> str:
        mandat_id = uuid.uuid4().hex
        folder = self.root / f"{folder_name_for(meta)} [{mandat_id[:6]}]"
        folder.mkdir()
        (folder / ".id").write_text(mandat_id)
        meta = {**meta, "created_at": _now_iso(), "updated_at": _now_iso()}
        self.upload(
            mandat_id, META_FILENAME,
            json.dumps(_public_meta(meta), ensure_ascii=False, indent=2).encode("utf-8"),
            "application/json", {"ent_kind": "meta"},
        )
        return mandat_id

    def save_meta(self, mandat: dict) -> None:
        meta = {**mandat, "updated_at": _now_iso()}
        self._find(mandat["_meta_file_id"]).write_text(
            json.dumps(_public_meta(meta), ensure_ascii=False, indent=2)
        )

    def upload(self, mandat_id: str, name: str, data: bytes, mime: str, props: dict) -> dict:
        folder = self._folder(mandat_id)
        path = folder / name
        i = 2
        while path.exists():
            path = folder / f"{Path(name).stem} ({i}){Path(name).suffix}"
            i += 1
        path.write_bytes(data)
        info = {"id": uuid.uuid4().hex, "props": _clean_props(props), "mime": mime, "created": _now_iso()}
        self._props_path(path).write_text(json.dumps(info))
        return {"id": info["id"], "name": path.name, "mime": mime, "size": len(data),
                "created": info["created"], "kind": info["props"].get("ent_kind", ""),
                "props": info["props"], "mandat_id": mandat_id}

    def replace_content(self, file_id: str, name: str, data: bytes, mime: str, props: dict | None = None) -> None:
        path = self._find(file_id)
        info = json.loads(self._props_path(path).read_text())
        self._props_path(path).unlink()
        path.unlink()
        new_path = path.parent / name
        new_path.write_bytes(data)
        info["mime"] = mime
        if props is not None:
            info["props"] = _clean_props(props)
        self._props_path(new_path).write_text(json.dumps(info))

    def trash(self, file_or_folder_id: str) -> None:
        try:
            shutil.rmtree(self._folder(file_or_folder_id))
            return
        except StorageError:
            pass
        path = self._find(file_or_folder_id)
        self._props_path(path).unlink()
        path.unlink()


# ─────────────────────────────────────────────────────────────────────────────


def _public_meta(meta: dict) -> dict:
    """Retire les champs techniques avant écriture de mandat.json."""
    return {k: v for k, v in meta.items() if k != "id" and not k.startswith("_")}


def get_store():
    if os.getenv("MANDATS_STORAGE", "").lower() == "local":
        return LocalStore()
    return DriveStore()
