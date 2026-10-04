"""
Accès aux mandats partagé entre les rubriques (Mandats, Scorecard, Dossier Candidature).
Caches communs : une écriture dans une rubrique est visible dans les autres.
"""

from datetime import datetime

import streamlit as st

from mandats_store import get_store


@st.cache_resource(show_spinner=False)
def store():
    return get_store()


@st.cache_data(ttl=120, show_spinner=False)
def load_snapshot() -> dict:
    return store().snapshot()


@st.cache_data(max_entries=3, show_spinner=False)
def fetch_bytes(file_id: str) -> bytes:
    return store().download(file_id)


def list_saved_scorecards() -> list[dict]:
    """Scorecards enregistrées dans les mandats, de la plus récente à la plus ancienne.

    Chaque entrée : {"file": dict, "mandat": dict, "label": str}.
    """
    snap = load_snapshot()
    by_id = {m["id"]: m for m in snap["mandats"]}
    out = []
    for mandat_id, files in snap["files"].items():
        mandat = by_id.get(mandat_id)
        if not mandat:
            continue
        for f in files:
            if f["kind"] != "scorecard":
                continue
            try:
                when = datetime.fromisoformat(f["created"].replace("Z", "+00:00")).strftime("%d/%m/%Y")
            except Exception:
                when = ""
            label = f"{mandat.get('nom', '')} — {mandat.get('entreprise', '')}" + (f" · {when}" if when else "")
            out.append({"file": f, "mandat": mandat, "label": label})
    out.sort(key=lambda x: x["file"].get("created", ""), reverse=True)
    return out
