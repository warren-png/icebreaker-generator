"""
Client Leonar (API REST v1) pour l'outil : projets (mandats), entreprises,
membres, fichiers joints aux projets et aux fiches candidats.
"""

import base64
import os
import re

import requests

BASE_URL = "https://app.leonar.app/api/v1"
DASHBOARD_URL = "https://app.leonar.app/dashboard/4c56aa38"
TIMEOUT = 30


class LeonarError(Exception):
    """Erreur Leonar lisible par l'utilisateur."""


def _api_key() -> str:
    key = os.getenv("LEONAR_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("LEONAR_API_KEY")
        except Exception:
            key = None
    if not key:
        # Développement local : clé dans le .env du projet
        from pathlib import Path
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
        key = os.getenv("LEONAR_API_KEY")
    if not key:
        raise LeonarError("LEONAR_API_KEY manquante (secrets Streamlit ou .env).")
    return key


def _request(method: str, path: str, full: bool = False, **kwargs):
    """Appel API ; renvoie le champ « data » (ou toute la réponse si full=True)."""
    headers = {"Authorization": f"Bearer {_api_key()}"}
    try:
        r = requests.request(method, BASE_URL + path, headers=headers, timeout=TIMEOUT, **kwargs)
    except requests.RequestException as e:
        raise LeonarError(f"Leonar injoignable : {e}") from e
    if r.status_code >= 400:
        try:
            msg = r.json().get("error", {}).get("message") or r.text[:200]
        except Exception:
            msg = r.text[:200]
        raise LeonarError(f"Leonar a refusé la requête ({r.status_code}) : {msg}")
    if r.status_code == 204 or not r.content:
        return None
    body = r.json()
    return body if full else body.get("data")


def project_url(project_id: str) -> str:
    return f"{DASHBOARD_URL}/projects/{project_id}/pipeline"


def contact_url(contact_id: str) -> str:
    return f"{DASHBOARD_URL}/contacts?contact={contact_id}"


# ── Membres ─────────────────────────────────────────────────────────────────


def members() -> dict[str, str]:
    """{prénom: user_id} des membres du workspace."""
    return {m["first_name"]: m["user_id"] for m in _request("GET", "/workspace/members") or []}


# ── Projets ─────────────────────────────────────────────────────────────────


def project_client(project: dict) -> str:
    company = project.get("client_company") or {}
    return (company.get("name") or project.get("client_name") or "").strip()


def list_mandate_projects(status: str = "active") -> list[dict]:
    """Projets rattachés à un client (= mandats), du plus récent au plus ancien."""
    projects, offset = [], 0
    while True:
        page = _request("GET", "/projects", full=True,
                        params={"limit": 100, "offset": offset, "status": status}) or {}
        projects.extend(page.get("data") or [])
        meta = page.get("meta") or {}
        if not meta.get("has_more"):
            break
        offset += meta.get("limit") or 100
    mandats = [p for p in projects if project_client(p)]
    mandats.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    return mandats


def find_or_create_company(name: str) -> str:
    """ID de la fiche entreprise Leonar portant ce nom (créée si absente)."""
    name = name.strip()
    for c in _request("GET", "/companies", params={"search": name, "limit": 50}) or []:
        if (c.get("name") or "").strip().lower() == name.lower():
            return c["id"]
    return _request("POST", "/companies", json={"name": name})["id"]


def create_project(name: str, company_name: str, owner_first_names: list[str]) -> dict:
    """Crée le projet Leonar du mandat, rattaché à l'entreprise et à ses propriétaires."""
    ids = members()
    owner_ids = [ids[n] for n in owner_first_names if n in ids]
    body = {"name": name[:100], "client_company_id": find_or_create_company(company_name)}
    if owner_ids:
        body["owner_ids"] = owner_ids
    return _request("POST", "/projects", json=body)


def upload_project_file(project_id: str, filename: str, data: bytes, content_type: str = "application/pdf") -> dict:
    return _request("POST", f"/projects/{project_id}/files", json={
        "filename": filename[:255],
        "content_type": content_type,
        "file_base64": base64.b64encode(data).decode(),
    })


def list_project_files(project_id: str) -> list[dict]:
    return (_request("GET", f"/projects/{project_id}/files") or {}).get("data") or []


def replace_project_file(project_id: str, filename: str, data: bytes, content_type: str = "application/pdf") -> dict:
    """Envoie le fichier en retirant d'abord les fichiers du projet portant le même nom."""
    for f in list_project_files(project_id):
        if (f.get("filename") or "") == filename[:255]:
            try:
                delete_project_file(project_id, f["id"])
            except LeonarError:
                pass  # l'ancienne version reste, sans gravité
    return upload_project_file(project_id, filename, data, content_type)


def delete_project_file(project_id: str, file_id: str) -> None:
    _request("DELETE", f"/projects/{project_id}/files/{file_id}")


# ── Candidats ───────────────────────────────────────────────────────────────


def linkedin_slug(url: str) -> str:
    m = re.search(r"linkedin\.com/in/([^/?#\s]+)", url or "", re.I)
    return m.group(1).strip().lower().rstrip("/") if m else ""


def find_contact_by_linkedin(url: str) -> dict | None:
    """Contact Leonar dont le profil LinkedIn correspond exactement à l'URL."""
    slug = linkedin_slug(url)
    if not slug:
        return None
    for query in (f"https://www.linkedin.com/in/{slug}", url.strip(), slug):
        for c in _request("GET", "/contacts", params={"search": query, "limit": 10}) or []:
            if linkedin_slug(c.get("linkedin_profile") or "") == slug:
                return c
    return None


def upload_contact_file(contact_id: str, filename: str, data: bytes, content_type: str = "application/pdf") -> dict:
    return _request("POST", f"/contacts/{contact_id}/files", json={
        "filename": filename[:255],
        "content_type": content_type,
        "file_base64": base64.b64encode(data).decode(),
    })
