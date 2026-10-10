"""
Rubrique « 4 · Site » de la fiche mandat : tout ce que le site affiche,
saisi UNE fois (décision de Warren, 10 octobre 2026).

  Annonce         ce que lit le candidat sur la page publique
  Entreprise      présentation, adresse, avantages, logo
  Interlocuteurs  chaque personne du client une seule fois (nom, fonction,
                  LinkedIn, email, « Reçoit le suivi ») ; on la choisit
                  ensuite dans les étapes, sans la ressaisir
  Process         les étapes d'entretien et leurs intervenants
  Documents       ce que le candidat prépare, et une pièce jointe

Deux boutons, pas plus : « Enregistrer » (le Drive, puis le site, en
brouillon tant que l'offre n'est pas publiée) et « Publier sur le site ».
Le site répond ce qui manque et ce qui est à corriger dans la forme : on
l'affiche tel quel.

Les valeurs vivent dans st.session_state (clés « site_<mandat>_… ») ; la
saisie est enregistrée dans mandat.json (clé « site »), la dernière réponse
du site dans « site_etat ».
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from utils import equipe, site

FORMATS = ["Visio", "Présentiel", "Téléphone", "Présentiel ou visio"]
DUREES = ["", "30 min", "45 min", "1 h", "1 h 30", "2 h"]
VERTICALES = {"finance": "Finance", "tech": "Tech"}
CONTRATS = ["CDI", "Freelance"]
STATUTS_SITE = {
    "active": ":green-badge[En ligne]",
    "brouillon": ":orange-badge[Brouillon sur le site]",
    "pourvue": ":blue-badge[Pourvue]",
    "fermee": ":gray-badge[Fermée]",
}
CHAMPS = ["titre", "verticale", "contrat", "lieu", "remuneration", "typeEntreprise", "descriptionCourte",
          "contenu", "presentation", "adresse", "avantages", "documents"]
CHAMPS_INTERLOCUTEUR = ["nom", "fonction", "linkedin", "email", "suivi"]
CHAMPS_ETAPE = ["titre", "format", "duree", "intervenants", "objectif", "conseils"]
ROLES = ["Responsable de chasse", "Sourceur"]

PLACEHOLDER_CONTENU = (
    "Le poste\nNotre client, un groupe industriel de 350 collaborateurs…\n\n"
    "Vos missions\n- Piloter le reporting mensuel\n- Encadrer une équipe de 3 contrôleurs\n\n"
    "Profil recherché\n- Bac+5 école de commerce ou d'ingénieur\n- 5 à 8 ans d'expérience\n\n"
    "Les titres et les puces se mettent en forme seuls sur le site."
)


def _k(mid: str, *parts: str) -> str:
    return "site_" + mid[-12:] + "_" + "_".join(parts)


def _nouvel_id(prefixe: str) -> str:
    return f"{prefixe}-{uuid.uuid4().hex[:8]}"


def titre_par_defaut(nom: str) -> str:
    """« Contrôleur de gestion H/F » devient « Contrôleur de gestion »."""
    return re.sub(r"\s*\(?\b[HF]\s*/\s*[HF]\b\)?\s*$", "", nom or "").strip()


def _offre_par_defaut(m: dict) -> dict:
    return {
        "titre": titre_par_defaut(m.get("nom", "")),
        "verticale": "tech" if (m.get("responsable") or "").lower() == "helder" else "finance",
        "contrat": "CDI",
        "interlocuteurs": [],
        "etapes": [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# État de la saisie
# ─────────────────────────────────────────────────────────────────────────────


def _initialiser(m: dict) -> None:
    """Remplit la saisie depuis le mandat, sinon depuis l'offre déjà sur le
    site (mandats publiés à la main avant le 10 octobre), sinon par défaut.
    Se refait quand Streamlit a effacé les champs (fiche quittée puis rouverte)."""
    mid = m["id"]
    if _k(mid, "titre") in st.session_state:
        return
    offre = m.get("site")
    if not offre and m.get("leonar_project_id") and site.configure():
        try:
            reprise = site.reprendre(mid, m.get("leonar_project_id"))
        except site.SiteError as e:
            reprise = None
            st.session_state[_k(mid, "reprise_erreur")] = str(e)
        if reprise:
            offre = reprise["offre"]
            st.session_state[_k(mid, "reprise")] = True
    offre = {**_offre_par_defaut(m), **(offre or {})}

    for champ in CHAMPS:
        st.session_state[_k(mid, champ)] = offre.get(champ) or ""
    if st.session_state[_k(mid, "verticale")] not in VERTICALES:
        st.session_state[_k(mid, "verticale")] = "finance"
    if st.session_state[_k(mid, "contrat")] not in CONTRATS:
        st.session_state[_k(mid, "contrat")] = "CDI"

    ids = []
    for i in offre.get("interlocuteurs") or []:
        iid = i.get("id") or _nouvel_id("int")
        ids.append(iid)
        for champ in CHAMPS_INTERLOCUTEUR:
            st.session_state[_k(mid, "int", iid, champ)] = bool(i.get(champ)) if champ == "suivi" else (i.get(champ) or "")
    st.session_state[_k(mid, "int_ids")] = ids

    eids = []
    for e in offre.get("etapes") or []:
        eid = e.get("id") or _nouvel_id("etape")
        eids.append(eid)
        for champ in CHAMPS_ETAPE:
            valeur = e.get(champ)
            if champ == "intervenants":
                valeur = [v for v in (valeur or []) if v in ids]
            st.session_state[_k(mid, "et", eid, champ)] = valeur if valeur is not None else ""
    st.session_state[_k(mid, "et_ids")] = eids


def _initialiser_equipe(m: dict) -> None:
    """L'équipe Entourage du mandat : le responsable de chasse et les
    sourceurs, tirés du responsable et des propriétaires du mandat."""
    mid = m["id"]
    resp = m.get("responsable") or ""
    proprios = m.get("proprietaires") or [resp]
    for prenom in equipe.EQUIPE:
        st.session_state.setdefault(_k(mid, "eq", prenom, "on"), prenom == resp or prenom in proprios)
        st.session_state.setdefault(_k(mid, "eq", prenom, "role"), ROLES[0] if prenom == resp else ROLES[1])


def equipe_choisie(mid: str) -> tuple[list[str], list[str]]:
    """(responsables de chasse, sourceurs) cochés dans l'onglet Interlocuteurs."""
    resp, sourceurs = [], []
    for prenom in equipe.EQUIPE:
        if not st.session_state.get(_k(mid, "eq", prenom, "on")):
            continue
        role = st.session_state.get(_k(mid, "eq", prenom, "role")) or ROLES[1]
        (resp if role == ROLES[0] else sourceurs).append(prenom)
    return resp, sourceurs


def collecter(mid: str) -> dict:
    """La saisie en cours, au format du site."""
    ss = st.session_state
    offre = {champ: (ss.get(_k(mid, champ)) or "").strip() for champ in CHAMPS}
    ids = ss.get(_k(mid, "int_ids"), [])
    offre["interlocuteurs"] = [
        {
            "id": iid,
            "nom": (ss.get(_k(mid, "int", iid, "nom")) or "").strip(),
            "fonction": (ss.get(_k(mid, "int", iid, "fonction")) or "").strip(),
            "linkedin": (ss.get(_k(mid, "int", iid, "linkedin")) or "").strip(),
            "email": (ss.get(_k(mid, "int", iid, "email")) or "").strip().lower(),
            "suivi": bool(ss.get(_k(mid, "int", iid, "suivi"))),
        }
        for iid in ids
    ]
    offre["interlocuteurs"] = [i for i in offre["interlocuteurs"] if i["nom"] or i["email"]]
    offre["etapes"] = [
        {
            "id": eid,
            "titre": (ss.get(_k(mid, "et", eid, "titre")) or "").strip(),
            "format": ss.get(_k(mid, "et", eid, "format")) or "",
            "duree": ss.get(_k(mid, "et", eid, "duree")) or "",
            "intervenants": [v for v in ss.get(_k(mid, "et", eid, "intervenants")) or [] if v in ids],
            "objectif": (ss.get(_k(mid, "et", eid, "objectif")) or "").strip(),
            "conseils": (ss.get(_k(mid, "et", eid, "conseils")) or "").strip(),
        }
        for eid in ss.get(_k(mid, "et_ids"), [])
    ]
    offre["etapes"] = [e for e in offre["etapes"] if e["titre"]]
    return offre


# ── Ajouter, retirer, déplacer (rappels : l'état change avant le rendu) ─────


def _ajouter_interlocuteur(mid: str) -> None:
    iid = _nouvel_id("int")
    for champ in CHAMPS_INTERLOCUTEUR:
        st.session_state[_k(mid, "int", iid, champ)] = False if champ == "suivi" else ""
    st.session_state[_k(mid, "int_ids")] = [*st.session_state.get(_k(mid, "int_ids"), []), iid]


def _retirer_interlocuteur(mid: str, iid: str) -> None:
    st.session_state[_k(mid, "int_ids")] = [x for x in st.session_state.get(_k(mid, "int_ids"), []) if x != iid]
    for eid in st.session_state.get(_k(mid, "et_ids"), []):
        cle = _k(mid, "et", eid, "intervenants")
        st.session_state[cle] = [v for v in st.session_state.get(cle) or [] if v != iid]


def _ajouter_etape(mid: str) -> None:
    eid = _nouvel_id("etape")
    for champ in CHAMPS_ETAPE:
        st.session_state[_k(mid, "et", eid, champ)] = [] if champ == "intervenants" else ""
    st.session_state[_k(mid, "et", eid, "format")] = "Visio"
    st.session_state[_k(mid, "et_ids")] = [*st.session_state.get(_k(mid, "et_ids"), []), eid]


def _retirer_etape(mid: str, eid: str) -> None:
    st.session_state[_k(mid, "et_ids")] = [x for x in st.session_state.get(_k(mid, "et_ids"), []) if x != eid]


def _deplacer_etape(mid: str, eid: str, sens: int) -> None:
    ids = list(st.session_state.get(_k(mid, "et_ids"), []))
    i = ids.index(eid)
    j = i + sens
    if 0 <= j < len(ids):
        ids[i], ids[j] = ids[j], ids[i]
        st.session_state[_k(mid, "et_ids")] = ids


# ─────────────────────────────────────────────────────────────────────────────
# Rendu
# ─────────────────────────────────────────────────────────────────────────────


def _date_courte(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Paris")).strftime("%d/%m à %H:%M")
    except Exception:
        return ""


def _onglet_annonce(mid: str) -> None:
    c1, c2 = st.columns([3, 2])
    c1.text_input("Intitulé publié", key=_k(mid, "titre"), placeholder="Contrôleur de gestion industriel")
    c2.text_input("Lieu", key=_k(mid, "lieu"), placeholder="Paris")
    c3, c4, c5 = st.columns(3)
    c3.selectbox("Verticale", list(VERTICALES), format_func=VERTICALES.get, key=_k(mid, "verticale"))
    c4.selectbox("Contrat", CONTRATS, key=_k(mid, "contrat"))
    c5.text_input("Rémunération (facultatif)", key=_k(mid, "remuneration"), placeholder="60 à 70 k€")
    st.text_input("Type d'entreprise, anonymisé", key=_k(mid, "typeEntreprise"),
                  placeholder="Groupe industriel coté, 3 000 collaborateurs")
    st.text_area("Description courte", key=_k(mid, "descriptionCourte"), height=80,
                 placeholder="Une ou deux phrases, affichées sur la carte de l'offre.")
    st.text_area("Contenu de l'offre", key=_k(mid, "contenu"), height=320, placeholder=PLACEHOLDER_CONTENU)


def _onglet_entreprise(mid: str) -> None:
    st.text_area("Présentation de l'entreprise", key=_k(mid, "presentation"), height=150,
                 placeholder="Mission, secteur, taille, implantation… Lue par le candidat avant ses entretiens.")
    st.text_input("Adresse des entretiens", key=_k(mid, "adresse"), placeholder="12 rue de la Paix, 75002 Paris")
    st.text_area("Avantages", key=_k(mid, "avantages"), height=120,
                 placeholder="Une ligne par avantage :\nVariable jusqu'à 15 %\n2 jours de télétravail par semaine")
    st.file_uploader("Logo du client, pour sa page de suivi (facultatif)", type=["png", "jpg", "jpeg", "webp", "svg"],
                     key=_k(mid, "logo"))


def _onglet_interlocuteurs(mid: str) -> None:
    st.markdown("**L'équipe Entourage**")
    st.caption("Cochez qui mène le mandat. Les coordonnées viennent de la fiche consultant du site : rien à retaper.")
    for prenom in equipe.EQUIPE:
        f = equipe.fiche(prenom)
        actif = bool(st.session_state.get(_k(mid, "eq", prenom, "on")))
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            st.checkbox(f["nom"], key=_k(mid, "eq", prenom, "on"), width=190)
            st.segmented_control("Rôle", ROLES, key=_k(mid, "eq", prenom, "role"), label_visibility="collapsed",
                                 disabled=not actif)
            st.caption(" · ".join(x for x in (f.get("email"), f.get("tel")) if x))

    st.markdown("**Les interlocuteurs du client**")
    st.caption("Chaque personne une seule fois : vous la choisissez ensuite dans les étapes du process. "
               "« Reçoit le suivi » lui envoie les candidatures et le lien de la page de suivi.")
    for iid in st.session_state.get(_k(mid, "int_ids"), []):
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 3])
            c1.text_input("Nom", key=_k(mid, "int", iid, "nom"), placeholder="Prénom Nom")
            c2.text_input("Fonction", key=_k(mid, "int", iid, "fonction"), placeholder="DAF")
            c3.text_input("LinkedIn", key=_k(mid, "int", iid, "linkedin"), placeholder="https://www.linkedin.com/in/…")
            with st.container(horizontal=True, vertical_alignment="bottom", gap="small"):
                st.text_input("Email", key=_k(mid, "int", iid, "email"), placeholder="prenom.nom@client.fr", width=340)
                st.toggle("Reçoit le suivi", key=_k(mid, "int", iid, "suivi"), width="stretch")
                st.button("", icon=":material/delete:", type="tertiary", help="Retirer", key=_k(mid, "int", iid, "x"),
                          on_click=_retirer_interlocuteur, args=(mid, iid))
    st.button("Ajouter un interlocuteur", icon=":material/person_add:", type="tertiary",
              key=_k(mid, "int_plus"), on_click=_ajouter_interlocuteur, args=(mid,))


def _onglet_process(mid: str) -> None:
    ids = st.session_state.get(_k(mid, "int_ids"), [])
    noms = {iid: (st.session_state.get(_k(mid, "int", iid, "nom")) or "Sans nom") for iid in ids}
    fonctions = {iid: st.session_state.get(_k(mid, "int", iid, "fonction")) or "" for iid in ids}
    etapes = st.session_state.get(_k(mid, "et_ids"), [])
    if not ids:
        st.caption("Ajoutez d'abord les interlocuteurs : chaque étape choisit les siens parmi eux.")
    for n, eid in enumerate(etapes, start=1):
        with st.container(border=True):
            with st.container(horizontal=True, vertical_alignment="bottom", gap="small"):
                st.text_input(f"Étape {n}", key=_k(mid, "et", eid, "titre"), placeholder="Entretien avec le DAF",
                              width="stretch")
                fmt = st.session_state.get(_k(mid, "et", eid, "format")) or ""
                st.session_state[_k(mid, "et", eid, "format")] = fmt
                st.selectbox("Format", FORMATS if fmt in FORMATS else [fmt, *FORMATS],
                             key=_k(mid, "et", eid, "format"), width=190, format_func=lambda f: f or "À préciser")
                dur = st.session_state.get(_k(mid, "et", eid, "duree")) or ""
                st.session_state[_k(mid, "et", eid, "duree")] = dur
                st.selectbox("Durée", DUREES if dur in DUREES else [dur, *DUREES], key=_k(mid, "et", eid, "duree"),
                             width=110, format_func=lambda d: d or "—")
                st.button("", icon=":material/arrow_upward:", type="tertiary", help="Monter",
                          key=_k(mid, "et", eid, "up"), disabled=n == 1,
                          on_click=_deplacer_etape, args=(mid, eid, -1))
                st.button("", icon=":material/arrow_downward:", type="tertiary", help="Descendre",
                          key=_k(mid, "et", eid, "down"), disabled=n == len(etapes),
                          on_click=_deplacer_etape, args=(mid, eid, 1))
                st.button("", icon=":material/delete:", type="tertiary", help="Retirer l'étape",
                          key=_k(mid, "et", eid, "x"), on_click=_retirer_etape, args=(mid, eid))
            st.multiselect("Intervenants", ids, key=_k(mid, "et", eid, "intervenants"),
                           format_func=lambda i: f"{noms.get(i, '?')}{' · ' + fonctions[i] if fonctions.get(i) else ''}",
                           placeholder="Choisir parmi les interlocuteurs…")
            st.text_input("Objectif de l'étape (facultatif)", key=_k(mid, "et", eid, "objectif"),
                          placeholder="Valider l'adéquation technique et la vision du poste")
            st.text_area("Conseils de préparation (facultatif)", key=_k(mid, "et", eid, "conseils"), height=90)
    st.button("Ajouter une étape", icon=":material/add:", type="tertiary",
              key=_k(mid, "et_plus"), on_click=_ajouter_etape, args=(mid,))


def _onglet_documents(mid: str, etat: dict | None) -> None:
    st.text_area("Ce que le candidat prépare (facultatif)", key=_k(mid, "documents"), height=120,
                 placeholder="Notes de votre consultant : chiffres à connaître, cas pratique, documents à apporter…")
    piece = (etat or {}).get("offre", {}).get("pieceJointe")
    st.file_uploader("Pièce jointe PDF (facultatif, 3 Mo au plus)", type=["pdf"], key=_k(mid, "pdf"))
    if piece:
        st.checkbox(f"Retirer la pièce jointe actuelle ({piece})", key=_k(mid, "pdf_retirer"))


def _liste(titre: str, items: list[str]) -> str:
    return f"**{titre}** · " + " · ".join(items)


def _rendre_controles(etat: dict) -> None:
    c = etat.get("controles") or {}
    groupes = [
        ("Pour publier", c.get("publier") or []),
        ("Forme à corriger", c.get("forme") or []),
        ("Espace candidat, avant le premier envoi de candidature", c.get("espace") or []),
        ("Suivi client", c.get("suivi") or []),
    ]
    manquants = [(t, i) for t, i in groupes if i]
    if not manquants:
        st.markdown(":green[:material/check_circle:] Annonce, espace candidat et suivi client complets.")
        return
    for titre, items in manquants:
        st.markdown(f":orange[:material/error:] **{titre}** : " + " ; ".join(items))


def render(m: dict, enregistrer_meta, rafraichir) -> None:
    """La rubrique « 4 · Site » de la fiche mandat.

    enregistrer_meta(mandat) écrit mandat.json ; rafraichir(message) recharge."""
    mid = m["id"]
    etat = m.get("site_etat")

    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        st.subheader("4 · Site", width="stretch")
        if etat:
            off = etat.get("offre") or {}
            st.markdown(STATUTS_SITE.get(off.get("statut"), "") + (
                f" :gray[à jour le {_date_courte(etat.get('majLe', ''))}]" if etat.get("majLe") else ""), width="content")
            if off.get("apercu"):
                st.link_button("Aperçu", off["apercu"], icon=":material/visibility:", type="tertiary")
            if off.get("url"):
                st.link_button("Annonce", off["url"], icon=":material/open_in_new:", type="tertiary")

    if not m.get("leonar_project_id"):
        st.caption("Liez d'abord le mandat à Leonar (en haut de la fiche) : c'est par son projet que le site le retrouve.")
        return
    if not site.configure():
        st.warning("Le lien avec le site n'est pas réglé : ajoutez SITE_ICEBREAKER_SECRET dans les secrets d'Icebreaker.")
        return

    _initialiser(m)
    _initialiser_equipe(m)
    if st.session_state.pop(_k(mid, "reprise"), False):
        st.info("Repris de l'offre déjà sur le site : vérifiez, puis enregistrez. Elle se modifiera ensuite ici seulement.")
    erreur_reprise = st.session_state.pop(_k(mid, "reprise_erreur"), None)
    if erreur_reprise:
        st.warning(f"L'offre du site n'a pas pu être reprise : {erreur_reprise}")

    onglets = st.tabs(["Annonce", "Entreprise", "Interlocuteurs", "Process", "Documents"])
    with onglets[0]:
        _onglet_annonce(mid)
    with onglets[1]:
        _onglet_entreprise(mid)
    with onglets[2]:
        _onglet_interlocuteurs(mid)
    with onglets[3]:
        _onglet_process(mid)
    with onglets[4]:
        _onglet_documents(mid, etat)

    en_ligne = (etat or {}).get("offre", {}).get("statut") == "active"
    ferme = (m.get("statut") or "") in ("Pourvu", "Clos")
    c = (etat or {}).get("controles") or {}
    bloque = not etat or bool(c.get("publier") or c.get("forme"))

    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        enregistrer = st.button("Enregistrer", type="primary", key=_k(mid, "save"),
                                help="Enregistre la fiche et met le site à jour" + ("" if en_ligne else " (en brouillon)") + ".")
        publier = False
        if not en_ligne and not ferme:
            publier = st.button("Publier sur le site", icon=":material/public:", key=_k(mid, "pub"), disabled=bloque,
                                help="Disponible quand rien ne manque pour publier et que la forme est bonne.")

    if etat:
        _rendre_controles(etat)
        if etat.get("suivi"):
            st.caption(f"Lien de la page de suivi du client (Réf. {etat['suivi'].get('reference', '')}) :")
            st.code(etat["suivi"]["lien"], language=None)
        if etat.get("migrationManquante"):
            st.caption(":gray[Le site attend sa migration 0045 : l'offre reste modifiable dans son administration.]")

    if enregistrer or publier:
        _envoyer(m, mid, publier, enregistrer_meta, rafraichir)


def _envoyer(m: dict, mid: str, publier: bool, enregistrer_meta, rafraichir) -> None:
    responsables, sourceurs = equipe_choisie(mid)
    if len(responsables) != 1:
        st.error("Choisissez un responsable de chasse, et un seul, dans l'onglet Interlocuteurs.")
        return
    offre = collecter(mid)
    logo = st.session_state.get(_k(mid, "logo"))
    pdf = st.session_state.get(_k(mid, "pdf"))
    # Le responsable et les sourceurs SONT le responsable et les propriétaires du mandat.
    mandat = {**m, "site": offre, "responsable": responsables[0], "proprietaires": responsables + sourceurs}
    try:
        with st.spinner("Mise à jour du site…"):
            etat = site.enregistrer(
                mandat,
                publier=publier,
                logo=site.piece(logo.name, logo.type or "image/png", logo.getvalue()) if logo else None,
                document_pdf=site.piece(pdf.name, "application/pdf", pdf.getvalue()) if pdf else None,
                retirer_document_pdf=bool(st.session_state.get(_k(mid, "pdf_retirer"))),
            )
    except site.SiteError as e:
        # La saisie n'est jamais perdue : elle part sur le Drive même quand le site refuse.
        enregistrer_meta(mandat)
        st.error(str(e))
        return
    enregistrer_meta({**mandat, "site_etat": etat})
    for cle in ("logo", "pdf", "pdf_retirer"):
        st.session_state.pop(_k(mid, cle), None)
    rafraichir("Publié sur le site." if publier else "Enregistré, site à jour.")
