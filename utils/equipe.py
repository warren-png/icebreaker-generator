"""
Les coordonnées des consultants : une seule fiche, celle du site
(administration du site, rubrique Consultants). Décision de Warren du
10 octobre 2026 : les quatre copies écrites en dur dans les rubriques
Scorecard, Contrat, Témoignage et Références dérivaient en silence.

Le site est lu au plus une fois par heure. S'il ne répond pas, les valeurs
ci-dessous prennent le relais : un contrat se génère même hors ligne.
Les titres (Président, Directeur Général) ne vivent qu'ici.
"""

from __future__ import annotations

import streamlit as st

from utils import site

REPLI = {
    "Warren": {"nom": "Warren Elbaz", "linkedin": "https://www.linkedin.com/in/warren-elbaz/",
               "tel": "06 50 60 22 61", "titre": "Président"},
    "Helder": {"nom": "Helder Alturas", "linkedin": "https://www.linkedin.com/in/helder-alturas-48010463/",
               "tel": "06 22 30 96 11", "titre": "Directeur Général"},
    "Bruno": {"nom": "Bruno Dos Santos", "linkedin": "https://www.linkedin.com/in/bruno-dos-santos-86b878184/",
              "tel": "06 76 77 94 26", "titre": ""},
}

# L'équipe qui mène un mandat : chacun peut être responsable de chasse ou
# sourceur. Les documents commerciaux (contrat, témoignage, références)
# restent signés de Warren ou d'Helder.
EQUIPE = ("Warren", "Helder", "Bruno")
COMMERCIAUX = ("Warren", "Helder")


def _tel_lisible(tel: str) -> str:
    """« 0650602261 » devient « 06 50 60 22 61 » ; un autre format reste tel quel."""
    chiffres = "".join(c for c in tel or "" if c.isdigit())
    if len(chiffres) == 10 and chiffres.startswith("0"):
        return " ".join(chiffres[i:i + 2] for i in range(0, 10, 2))
    return (tel or "").strip()


@st.cache_data(ttl=3600, show_spinner=False)
def _du_site() -> list[dict]:
    try:
        return site.consultants()
    except site.SiteError:
        return []


def fiche(prenom: str) -> dict:
    """{nom, email, linkedin, tel, titre} d'un consultant, le site d'abord."""
    base = dict(REPLI.get(prenom, {"nom": prenom, "linkedin": "", "tel": "", "titre": ""}))
    c = next((x for x in _du_site() if (x.get("prenom") or "").lower() == prenom.lower()), None)
    base["email"] = ""
    if c:
        base["nom"] = f"{c.get('prenom', '')} {c.get('nom', '')}".strip() or base["nom"]
        base["email"] = c.get("email") or ""
        base["linkedin"] = c.get("linkedin") or base["linkedin"]
        base["tel"] = _tel_lisible(c.get("telephone") or "") or base["tel"]
    return base


def commerciaux(noms_complets: bool = False, prenoms: tuple = COMMERCIAUX) -> dict:
    """Le dictionnaire des responsables, à la forme qu'attendent les rubriques :
    clé « Warren » (ou « Warren Elbaz »), valeur {linkedin, tel, titre}."""
    out = {}
    for prenom in prenoms:
        f = fiche(prenom)
        out[f["nom"] if noms_complets else prenom] = {"linkedin": f["linkedin"], "tel": f["tel"], "titre": f["titre"]}
    return out


def ligne_pied_de_page(prenom: str) -> str:
    """La ligne du pied de page du dossier de candidature."""
    f = fiche(prenom)
    return f'Responsable de chasse : <a href="{f["linkedin"]}">{prenom}</a> - {f["tel"]}'
