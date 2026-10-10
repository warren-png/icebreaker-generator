"""
Client du site entouragerecrutement.com : la porte /api/icebreaker.

Décision de Warren (10 octobre 2026) : tout mandat se saisit UNE fois, ici.
Chaque enregistrement de la fiche « Site » met à jour l'offre (annonce et
espace candidat) et la page de suivi du client ; la publication est un
bouton à part ; le dossier de candidature s'envoie au client d'ici.

Le site fait les contrôles (ce qui manque, la forme) : Icebreaker affiche ses
réponses telles quelles, sans les refaire à sa façon.

Secret partagé : SITE_ICEBREAKER_SECRET (secrets Streamlit), la même valeur
que ICEBREAKER_SECRET dans les réglages de Vercel. Aucune IA ici.
"""

from __future__ import annotations

import base64
import os

import requests

TIMEOUT = 60
SITE_URL_DEFAUT = "https://www.entouragerecrutement.com"


class SiteError(Exception):
    """Réponse du site lisible par l'utilisateur."""


def _dans_les_secrets(cle: str) -> str | None:
    """La clé dans les secrets Streamlit, en tête OU dans une section : une
    ligne collée en bas du fichier tombe dans la dernière section entre
    crochets (vu le 10 octobre 2026). Majuscules ou minuscules."""
    try:
        import streamlit as st
        secrets = st.secrets
        noms = (cle, cle.lower())
        for nom in noms:
            if nom in secrets and isinstance(secrets[nom], str):
                return secrets[nom]
        for section in secrets.values():
            if hasattr(section, "keys"):
                for nom in noms:
                    if nom in section and isinstance(section[nom], str):
                        return section[nom]
    except Exception:
        return None
    return None


def _reglage(cle: str) -> str | None:
    val = os.getenv(cle) or _dans_les_secrets(cle)
    if not val:
        from pathlib import Path
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
        val = os.getenv(cle)
    return val


def site_url() -> str:
    return (_reglage("SITE_URL") or SITE_URL_DEFAUT).rstrip("/")


def configure() -> bool:
    return bool(_reglage("SITE_ICEBREAKER_SECRET"))


def _appel(methode: str, params: dict | None = None, corps: dict | None = None) -> dict:
    secret = _reglage("SITE_ICEBREAKER_SECRET")
    if not secret:
        raise SiteError("Le lien avec le site n'est pas réglé (SITE_ICEBREAKER_SECRET manquant dans les secrets).")
    try:
        r = requests.request(
            methode, f"{site_url()}/api/icebreaker",
            headers={"Authorization": f"Bearer {secret}"},
            params=params, json=corps, timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        raise SiteError(f"Le site ne répond pas : {e}") from e
    if r.status_code == 401:
        raise SiteError("Le site refuse la clé d'Icebreaker : vérifiez SITE_ICEBREAKER_SECRET.")
    try:
        data = r.json()
    except ValueError:
        raise SiteError(f"Réponse illisible du site ({r.status_code}).")
    if not data.get("ok"):
        raise SiteError(data.get("erreur") or f"Le site a refusé ({r.status_code}).")
    return data


def corps_mandat(m: dict) -> dict:
    """Le mandat tel que le site l'attend."""
    return {
        "id": m["id"],
        "nom": m.get("nom", ""),
        "entreprise": m.get("entreprise", ""),
        "date": m.get("date", ""),
        "responsable": m.get("responsable", ""),
        "proprietaires": m.get("proprietaires") or [],
        "statut": m.get("statut", ""),
        "leonarProjectId": m.get("leonar_project_id"),
        "offre": m.get("site") or {},
    }


def piece(nom: str, type_mime: str, data: bytes) -> dict:
    return {"nom": nom, "type": type_mime, "base64": base64.b64encode(data).decode()}


def reprendre(mandat_id: str, leonar_project_id: str | None) -> dict | None:
    """L'offre déjà sur le site pour ce mandat (saisie à la main avant Icebreaker)."""
    params = {"action": "reprendre", "mandat": mandat_id}
    if leonar_project_id:
        params["leonar"] = leonar_project_id
    return _appel("GET", params=params).get("reprise")


def enregistrer(m: dict, publier: bool = False, logo: dict | None = None,
                document_pdf: dict | None = None, retirer_document_pdf: bool = False) -> dict:
    """Met le site à jour ; renvoie l'état (statut, liens, ce qui manque)."""
    corps = {"action": "publier" if publier else "enregistrer", "mandat": corps_mandat(m)}
    if logo:
        corps["logo"] = logo
    if document_pdf:
        corps["documentPdf"] = document_pdf
    if retirer_document_pdf:
        corps["retirerDocumentPdf"] = True
    return _appel("POST", corps=corps)["etat"]


def envoyer_candidature(m: dict, contact_id: str, mot: str = "") -> dict:
    """Envoie le dossier au client, au nom du responsable du mandat."""
    return _appel("POST", corps={
        "action": "envoyer-candidature", "mandat": corps_mandat(m), "contactId": contact_id, "mot": mot,
    })["envoi"]


def consultants() -> list[dict]:
    """Les coordonnées de l'équipe, telles qu'enregistrées sur le site."""
    return _appel("GET", params={"action": "consultants"}).get("consultants") or []
