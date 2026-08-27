import streamlit as st
import base64
import os
import io
import datetime
from pathlib import Path
from utils.auth import check_password
from utils.ui import inject_global_styles

st.set_page_config(
    page_title="Contrat | Biz Dev Entourage",
    page_icon="📋",
    layout="wide"
)

inject_global_styles()

# — Authentification —
if not check_password():
    st.stop()

# ---------------------------------------------------------------------------
# COMMERCIAUX
# ---------------------------------------------------------------------------

COMMERCIAUX = {
    "Warren Elbaz": {
        "linkedin": "https://www.linkedin.com/in/warren-elbaz/",
        "tel": "06 50 60 22 61",
        "titre": "Président"
    },
    "Helder Alturas": {
        "linkedin": "https://www.linkedin.com/in/helder-alturas-48010463/",
        "tel": "06 22 30 96 11",
        "titre": "Directeur Général"
    }
}

# ---------------------------------------------------------------------------
# LOGO ENTOURAGE (même logique que Scorecard)
# ---------------------------------------------------------------------------

@st.cache_resource
def load_logo_base64_cached():
    candidates = [
        Path(__file__).parent.parent / "logo_entourage.png",
        Path(__file__).parent / "logo_entourage.png",
        Path(os.getcwd()) / "logo_entourage.png",
    ]
    for path in candidates:
        if path.exists():
            try:
                from PIL import Image
                img = Image.open(path)
                img.thumbnail((600, 120), Image.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                return base64.b64encode(buf.getvalue()).decode()
            except ImportError:
                with open(path, "rb") as f:
                    return base64.b64encode(f.read()).decode()
    return None


def get_logo_entourage() -> str:
    if st.session_state.get("logo_b64"):
        return st.session_state.logo_b64
    cached = load_logo_base64_cached()
    if cached:
        st.session_state.logo_b64 = cached
    return cached or ""


# ---------------------------------------------------------------------------
# CLAUSE OPTIONNELLE — EXCLUSIVITÉ DE RECHERCHE (ANNEXE 1)
# ---------------------------------------------------------------------------

_NOMBRES_LETTRES = {
    15: "quinze", 30: "trente", 45: "quarante-cinq",
    60: "soixante", 75: "soixante-quinze", 90: "quatre-vingt-dix",
}


def _en_lettres(n: int) -> str:
    """Retourne le nombre en toutes lettres (fallback : chiffres)."""
    return _NOMBRES_LETTRES.get(int(n), str(n))


def build_annexe_exclusivite(
    fields: dict,
    commercial: dict,
    logo_tag_content: str,
    date_str: str,
    excl_jours_txt: str,
    excl_penalite: int,
    client_sig_name: str,
    client_sig_title_prefix: str,
    total_pages: int,
) -> str:
    """Page 5 — Annexe 1 : clause d'exclusivité de recherche (générée uniquement si l'option est cochée)."""
    return f"""
<!-- ═══════════════════════════════════════ PAGE 5 : ANNEXE 1 — EXCLUSIVITÉ DE RECHERCHE ═══════════════════════════════════════ -->
<div class="page">
  <div class="content-header">
    <div>{logo_tag_content}</div>
    <div class="content-header-doc">Annexe 1 · Exclusivité de recherche · {fields["client_nom"].upper()}</div>
  </div>

  <div class="content-body">

    <div class="article">
      <div class="article-title">
        <div class="article-num" style="width:auto;min-width:6mm;padding:0 1.5mm;border-radius:3mm;">A1</div>
        Annexe 1 — Clause d&rsquo;Exclusivité de Recherche
      </div>
      <div class="article-body">
        <p>La présente Annexe fait partie intégrante du Contrat de prestations de services conclu entre les Parties le {date_str}. Elle précise et complète l&rsquo;Article 8 du Contrat, sur lequel elle prévaut en cas de contradiction.</p>

        <p style="margin-top:2mm;"><strong>A.1 &mdash; Octroi et durée de l&rsquo;exclusivité</strong></p>
        <p>Le Client confie au Prestataire, <strong>à titre exclusif</strong>, la recherche, l&rsquo;approche et la sélection des candidats pour le ou les postes objets du Contrat (la &laquo;&nbsp;Mission&nbsp;&raquo;), pour une durée de <strong>{excl_jours_txt} jours calendaires</strong> à compter de la date de signature du Contrat (la &laquo;&nbsp;Période d&rsquo;Exclusivité&nbsp;&raquo;).</p>
        <p>À l&rsquo;expiration de la Période d&rsquo;Exclusivité, et à défaut de reconduction expresse et écrite des Parties, l&rsquo;exclusivité cesse de plein droit et sans formalité, sans effet sur les Articles 5 et 7 du Contrat qui poursuivent leurs effets.</p>

        <p style="margin-top:2mm;"><strong>A.2 &mdash; Portée de l&rsquo;engagement du Client</strong></p>
        <p>Pendant la Période d&rsquo;Exclusivité, le Client s&rsquo;interdit, directement ou indirectement, par lui-même ou par toute entité de son groupe&nbsp;:</p>
        <ul>
          <li>de confier tout ou partie de la même recherche à un autre cabinet de recrutement, chasseur de têtes, prestataire indépendant, plateforme de sourcing ou tout tiers exerçant une activité analogue&nbsp;;</li>
          <li>de mandater ou de rémunérer un tiers, à quelque titre que ce soit, pour identifier, approcher ou présenter des candidats sur les postes concernés&nbsp;;</li>
          <li>de publier ou faire publier une annonce relative à ces postes sans en avoir informé préalablement le Prestataire par écrit.</li>
        </ul>
        <p>Ne constituent pas un manquement&nbsp;: (i) les candidatures spontanées reçues avant la signature, sous réserve d&rsquo;avoir été communiquées par écrit au Prestataire dans les cinq (5) jours ouvrés suivant celle-ci&nbsp;; (ii) la cooptation et le sourcing interne, à condition que le Prestataire en soit informé sans délai.</p>

        <p style="margin-top:2mm;"><strong>A.3 &mdash; Obligation d&rsquo;information et de loyauté</strong></p>
        <p>Le Client informe le Prestataire, sans délai et par écrit, de toute candidature reçue ou de tout contact engagé sur les postes concernés, quelle qu&rsquo;en soit la source. Les Parties conviennent expressément que les articles A.2 et A.3 constituent des <strong>obligations essentielles</strong>, sans lesquelles le Prestataire n&rsquo;aurait pas contracté aux conditions financières de l&rsquo;Article 5.</p>

        <p style="margin-top:2mm;"><strong>A.4 &mdash; Contrepartie à la charge du Prestataire</strong></p>
        <p>En contrepartie, le Prestataire s&rsquo;engage à lancer la Mission dans les quarante-huit (48) heures ouvrées de la signature, à rendre compte de son avancement lors d&rsquo;un point hebdomadaire et à présenter une première sélection de candidats qualifiés avant l&rsquo;expiration de la Période d&rsquo;Exclusivité.</p>

        <p style="margin-top:2mm;"><strong>A.5 &mdash; Manquement, résiliation et pénalités</strong></p>
        <p>Tout manquement du Client aux articles A.2 ou A.3 constitue un <strong>manquement grave</strong> au sens de l&rsquo;Article 4 du Contrat. Le Prestataire pourra alors, sans préjudice de la réparation de son préjudice&nbsp;:</p>
        <ul>
          <li><strong>résilier le Contrat</strong> de plein droit et aux torts exclusifs du Client, par lettre recommandée avec accusé de réception, huit (8) jours après mise en demeure restée sans effet, sans qu&rsquo;aucune indemnité ne soit due par le Prestataire&nbsp;;</li>
          <li>exiger une <strong>pénalité forfaitaire de {excl_penalite}&nbsp;% de la rémunération annuelle brute</strong> prévue pour le poste concerné, stipulée à titre de clause pénale au sens de l&rsquo;article 1231-5 du Code civil et payable dans les {fields["paiement_jours"]} jours de sa facturation&nbsp;;</li>
          <li>percevoir l&rsquo;<strong>intégralité des honoraires</strong> de l&rsquo;Article 5 si le poste est pourvu &mdash; pendant la Période d&rsquo;Exclusivité ou dans les six (6) mois suivant son terme &mdash; par un candidat identifié, approché ou présenté en violation de la présente Annexe.</li>
        </ul>
        <p>Ces montants se cumulent et ne libèrent pas le Client des sommes déjà exigibles. Les stipulations du présent article survivent à l&rsquo;expiration de la Période d&rsquo;Exclusivité comme à la cessation du Contrat.</p>
      </div>
    </div>

    <div style="margin-top:4mm; padding-top:3mm; border-top: 2px solid #FFD700;">
      <div style="font-family:'Playfair Display',serif; font-size:10pt; color:#000; margin-bottom:2mm;">Signature de l&rsquo;Annexe 1</div>
      <div class="signature-grid">
        <div class="sig-box" style="padding:3mm;">
          <div class="sig-label">Pour le Client</div>
          <div class="sig-name">{client_sig_name}</div>
          <div class="sig-title">{client_sig_title_prefix}{fields["client_nom"]}</div>
          <div class="sig-area" style="height:9mm;"></div>
          <div class="sig-lu">Lu et approuvé &mdash; Bon pour accord sur la clause d&rsquo;exclusivité</div>
        </div>
        <div class="sig-box" style="padding:3mm;">
          <div class="sig-label">Pour Entourage Recrutement</div>
          <div class="sig-name">{fields["commercial"]}</div>
          <div class="sig-title">{commercial["titre"]} &middot; Entourage Recrutement</div>
          <div class="sig-area" style="height:9mm;"></div>
          <div class="sig-lu">Lu et approuvé &mdash; Bon pour accord sur la clause d&rsquo;exclusivité</div>
        </div>
      </div>
    </div>

  </div>

  <div class="content-footer">
    <span>Entourage Recrutement · SAS · RCS Paris 828 310 581</span>
    <span>Page 5 / {total_pages}</span>
    <span><a href="{commercial['linkedin']}">{fields["commercial"]}</a> · {commercial["tel"]}</span>
  </div>
</div>
"""


# ---------------------------------------------------------------------------
# GÉNÉRATION DU HTML CONTRAT
# ---------------------------------------------------------------------------

def build_contract_html(fields: dict) -> str:
    logo_b64 = get_logo_entourage()
    # Page 1 : header 24mm — logo plus grand
    logo_tag_cover = (
        f'<img src="data:image/png;base64,{logo_b64}" style="height:18mm;max-width:80mm;object-fit:contain;">'
        if logo_b64 else
        '<span style="color:#FFD700;font-weight:800;font-size:13pt;letter-spacing:1px;">ENTOURAGE RECRUTEMENT</span>'
    )
    # Pages 2-3-4 : header 16mm — logo contraint en hauteur et largeur
    logo_tag_content = (
        f'<img src="data:image/png;base64,{logo_b64}" style="height:11mm;max-width:55mm;object-fit:contain;display:block;">'
        if logo_b64 else
        '<span style="color:#FFD700;font-weight:800;font-size:9pt;letter-spacing:1px;">ENTOURAGE RECRUTEMENT</span>'
    )

    client_logo_tag = ""
    if fields.get("client_logo_b64"):
        client_logo_tag = (
            f'<img src="data:image/png;base64,{fields["client_logo_b64"]}" '
            f'style="max-height:35mm;max-width:90mm;object-fit:contain;">'
        )
    elif fields.get("client_logo_url"):
        client_logo_tag = (
            f'<img src="{fields["client_logo_url"]}" '
            f'style="max-height:35mm;max-width:90mm;object-fit:contain;" '
            f'onerror="this.style.display=\'none\'">'
        )

    commercial = COMMERCIAUX[fields["commercial"]]
    date_str = fields["date_signature"].strftime("%d/%m/%Y") if fields.get("date_signature") else "___/___/______"

    # Champs optionnels : représentant & titre
    rep_line = (
        f'<strong>Représenté par : {fields["client_representant"]}</strong><br>'
        if fields.get("client_representant") else ""
    )
    titre_line = (
        f'{fields["client_titre_rep"]}'
        if fields.get("client_titre_rep") else ""
    )

    client_sig_name = fields.get("client_representant") or "________________________"
    client_sig_title_prefix = f'{fields["client_titre_rep"]} &middot; ' if fields.get("client_titre_rep") else ""

    # ── Option : clause d'exclusivité de recherche (Annexe 1) ──────────────
    excl_active = bool(fields.get("exclusivite_recherche"))
    excl_jours = int(fields.get("exclusivite_jours") or 30)
    excl_penalite = int(fields.get("exclusivite_penalite_pct") or 15)
    excl_jours_txt = f"{_en_lettres(excl_jours)} ({excl_jours})"
    total_pages = 5 if excl_active else 4

    # Article 8 — texte alternatif selon l'option (longueur équivalente : mise en page page 4 préservée)
    if excl_active:
        art8_titre = "Exclusivité de Recherche"
        art8_body = (
            f'<p>Le Client confère au Prestataire une <strong>exclusivité de recherche '
            f'de {excl_jours_txt} jours calendaires</strong> à compter de la signature du '
            f'Contrat, dans les conditions fixées à l&rsquo;<strong>Annexe 1</strong>, laquelle '
            f'fait partie intégrante du présent Contrat et dont le Client reconnaît avoir pris connaissance.</p>'
        )
    else:
        art8_titre = "Exclusivité"
        art8_body = (
            "<p>Le Prestataire ne bénéficie pas d'un droit d'exclusivité concernant les besoins "
            "exprimés par le Client, lequel reste libre de solliciter d'autres prestataires pour "
            "tout ou partie de la Prestation.</p>"
        )

    toc_annexe = (
        '<div class="toc-item"><span><strong>A1.</strong> Annexe &mdash; Exclusivité de recherche</span>'
        '<span class="toc-page">p.5</span></div>'
        if excl_active else ""
    )

    annexe_html = (
        build_annexe_exclusivite(
            fields, commercial, logo_tag_content, date_str, excl_jours_txt,
            excl_penalite, client_sig_name, client_sig_title_prefix, total_pages,
        )
        if excl_active else ""
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Contrat — {fields['client_nom']}</title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  body {{ font-family: 'Manrope', sans-serif; background: #555; display: flex; flex-direction: column; align-items: center; padding: 40px 0; gap: 24px; }}

  /* PAGE — min-height uniquement pour le preview ; pas d'overflow:hidden pour que les signatures s'affichent */
  .page {{ width: 210mm; min-height: 297mm; background: #fff; box-shadow: 0 0 20px rgba(0,0,0,.5); display: flex; flex-direction: column; position: relative; }}

  /* HEADER COUVERTURE */
  .header {{ background: #000; border-bottom: 2.5mm solid #FFD700; padding: 0 14mm; height: 24mm; display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; }}
  .header-right {{ text-align: right; }}
  .doc-label {{ color: #FFD700; font-size: 7.5pt; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 700; }}
  .doc-ref {{ color: #fff; font-size: 9pt; font-weight: 600; margin-top: 2px; }}

  /* COUVERTURE */
  .cover-body {{ padding: 12mm 14mm; flex-grow: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }}
  .cover-title {{ font-family: 'Playfair Display', serif; font-size: 24pt; color: #000; padding: 8mm 0 4mm; border-bottom: 2px solid #FFD700; }}
  .cover-subtitle {{ font-size: 9.5pt; color: #777; margin-top: 4mm; text-transform: uppercase; letter-spacing: 1.5px; }}
  .client-logo-cover {{ margin-top: 14mm; display: flex; align-items: center; justify-content: center; }}

  /* FOOTER COVER */
  .cover-footer {{ margin-top: auto; background: #f8f9fa; border-top: 1px solid #eee; padding: 4mm 14mm; display: flex; justify-content: space-between; align-items: center; font-size: 8pt; color: #777; flex-shrink: 0; }}
  .cover-footer a {{ color: #000; font-weight: 700; text-decoration: none; border-bottom: 1px solid #FFD700; }}

  /* HEADER PAGES DE CONTENU (avec logo) */
  .content-header {{ background: #000; height: 16mm; display: flex; align-items: center; padding: 0 14mm; border-bottom: 1.5mm solid #FFD700; flex-shrink: 0; justify-content: space-between; overflow: hidden; }}
  .content-header-doc {{ color: #FFD700; font-size: 7pt; text-align: right; white-space: nowrap; margin-left: 4mm; }}
  .content-body {{ padding: 6mm 14mm 4mm; flex-grow: 1; }}

  /* PAGE 2 — layout flex colonne pour remplir toute la hauteur */
  .content-body-p2 {{ padding: 8mm 14mm 6mm; flex-grow: 1; display: flex; flex-direction: column; }}
  .toc-expand {{ flex-grow: 1; display: flex; flex-direction: column; margin-top: 5mm; }}
  .toc-expand .toc {{ flex-grow: 1; }}

  .content-footer {{ background: #f8f9fa; border-top: 1px solid #eee; padding: 3mm 14mm; display: flex; justify-content: space-between; font-size: 7.5pt; color: #999; flex-shrink: 0; }}
  .content-footer a {{ color: #000; font-weight: 700; text-decoration: none; border-bottom: 1px solid #FFD700; }}

  /* PARTIES */
  .parties {{ display: grid; grid-template-columns: 1fr auto 1fr; gap: 6mm; align-items: stretch; margin-bottom: 3mm; }}
  .party-box {{ background: #f8f9fa; border-left: 3px solid #000; padding: 7mm 8mm; }}
  .party-box.client {{ border-left-color: #FFD700; }}
  .party-label {{ font-size: 7pt; text-transform: uppercase; letter-spacing: 1px; color: #999; font-weight: 700; margin-bottom: 3mm; }}
  .party-name {{ font-family: 'Playfair Display', serif; font-size: 13pt; color: #000; margin-bottom: 3mm; }}
  .party-info {{ font-size: 8.5pt; color: #555; line-height: 1.55; }}
  .party-info strong {{ color: #000; }}
  .and-separator {{ display: flex; align-items: center; justify-content: center; }}
  .and-circle {{ width: 12mm; height: 12mm; background: #000; color: #FFD700; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 10pt; flex-shrink: 0; }}

  /* TABLE DES MATIÈRES — 1 colonne, items espacés */
  .toc {{ background: #f8f9fa; border-left: 3px solid #FFD700; padding: 6mm 8mm; }}
  .toc-title {{ font-weight: 800; font-size: 9.5pt; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4mm; color: #000; }}
  .toc-grid {{ display: grid; grid-template-columns: 1fr; gap: 0; }}
  .toc-item {{ font-size: 10.5pt; color: #444; padding: 2.5mm 0; border-bottom: 1px solid #e8e8e8; display: flex; justify-content: space-between; align-items: center; }}
  .toc-item:last-child {{ border-bottom: none; }}
  .toc-item strong {{ color: #000; margin-right: 4px; }}
  .toc-page {{ color: #bbb; font-size: 8.5pt; font-weight: 600; }}

  /* ARTICLES */
  .article {{ margin-bottom: 4mm; }}
  .article-title {{
    font-family: 'Playfair Display', serif;
    font-size: 11pt;
    color: #000;
    border-bottom: 1px solid #eee;
    padding-bottom: 1.5mm;
    margin-bottom: 2mm;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .article-num {{
    background: #000;
    color: #FFD700;
    font-family: 'Manrope', sans-serif;
    font-size: 8pt;
    font-weight: 800;
    width: 6mm; height: 6mm;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
  }}
  .article-body {{ font-size: 8pt; line-height: 1.45; color: #333; text-align: justify; }}
  .article-body p {{ margin-bottom: 1.5mm; }}
  .article-body ul {{ padding-left: 4mm; margin: 1mm 0 1.5mm; }}
  .article-body li {{ margin-bottom: 0.8mm; }}
  .highlight {{ background: #fffcf0; border-left: 2px solid #FFD700; padding: 1.5mm 4mm; margin: 1.5mm 0; font-weight: 600; color: #000; font-size: 8pt; }}

  /* SIGNATURE */
  .signature-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6mm; margin-top: 3mm; }}
  .sig-box {{ border: 1px solid #ddd; border-radius: 4px; padding: 4mm; }}
  .sig-label {{ font-size: 7pt; text-transform: uppercase; letter-spacing: 0.5px; color: #999; font-weight: 700; margin-bottom: 2mm; }}
  .sig-name {{ font-weight: 800; font-size: 9.5pt; color: #000; }}
  .sig-title {{ font-size: 7.5pt; color: #777; margin-bottom: 3mm; }}
  .sig-date {{ font-size: 7.5pt; color: #555; margin-bottom: 2mm; }}
  .sig-area {{ border-bottom: 1px solid #ccc; height: 12mm; margin-top: 2mm; }}
  .sig-lu {{ font-size: 6.5pt; color: #aaa; margin-top: 1mm; font-style: italic; }}

  @media print {{
    body {{ background: none; padding: 0; gap: 0; }}
    .page {{ box-shadow: none; page-break-after: always; }}
    .page:last-child {{ page-break-after: avoid; }}
  }}
</style>
</head>
<body>

<!-- ═══════════════════════════════════════ PAGE 1 : COUVERTURE ═══════════════════════════════════════ -->
<div class="page">
  <div class="header">
    <div>{logo_tag_cover}</div>
    <div class="header-right">
      <div class="doc-label">Document contractuel</div>
      <div class="doc-ref">Contrat de prestations de services — Recrutement</div>
    </div>
  </div>

  <div class="cover-body">
    <div>
      <div class="cover-title">Contrat de Prestations de Services</div>
      <div class="cover-subtitle">Recrutement &amp; Chasse de Têtes — Cadres Dirigeants</div>
    </div>

    {('<div class="client-logo-cover">' + client_logo_tag + '</div>') if client_logo_tag else ''}
  </div>

  <div class="cover-footer">
    <span>Entourage Recrutement · 36 rue du Faubourg Saint-Honoré, 75008 Paris</span>
    <span><a href="{commercial['linkedin']}" target="_blank">{fields["commercial"]}</a> · {commercial["tel"]}</span>
  </div>
</div>

<!-- ═══════════════════════════════════════ PAGE 2 : PARTIES + TABLE DES MATIÈRES ═══════════════════════════════════════ -->
<div class="page">
  <div class="content-header">
    <div>{logo_tag_content}</div>
    <div class="content-header-doc">Contrat de Prestations · {fields["client_nom"].upper()}</div>
  </div>

  <div class="content-body-p2">

    <div class="parties">
      <div class="party-box">
        <div class="party-label">Le Prestataire</div>
        <div class="party-name">Entourage Recrutement</div>
        <div class="party-info">
          SAS au capital de 1 000 &euro;<br>
          RCS Paris — n&deg; 828 310 581<br>
          36 rue du Faubourg Saint-Honoré, 75008 Paris<br>
          <strong>Représenté par : {fields["commercial"]}</strong><br>
          {commercial["titre"]}
        </div>
      </div>

      <div class="and-separator">
        <div class="and-circle">ET</div>
      </div>

      <div class="party-box client">
        <div class="party-label">Le Client</div>
        <div class="party-name">{fields["client_nom"]}</div>
        <div class="party-info">
          SIRET : {fields["client_siret"]}<br>
          {fields["client_adresse"]}<br>
          {rep_line}
          {titre_line}
        </div>
      </div>
    </div>

    <div style="text-align:right; font-size:8pt; color:#888; margin: 3mm 0 5mm;">
      Fait à Paris, le {date_str}
    </div>

    <div style="border-top: 2px solid #FFD700;"></div>

    <div class="toc-expand">
      <div class="toc">
        <div class="toc-title">Table des matières</div>
        <div class="toc-grid">
          <div class="toc-item"><span><strong>1.</strong> Préambule</span><span class="toc-page">p.3</span></div>
          <div class="toc-item"><span><strong>2.</strong> Objet</span><span class="toc-page">p.3</span></div>
          <div class="toc-item"><span><strong>3.</strong> Obligations des parties</span><span class="toc-page">p.3</span></div>
          <div class="toc-item"><span><strong>4.</strong> Durée &amp; Résiliation</span><span class="toc-page">p.3</span></div>
          <div class="toc-item"><span><strong>5.</strong> Conditions financières</span><span class="toc-page">p.3</span></div>
          <div class="toc-item"><span><strong>6.</strong> Facturation &amp; Paiement</span><span class="toc-page">p.4</span></div>
          <div class="toc-item"><span><strong>7.</strong> Garantie</span><span class="toc-page">p.4</span></div>
          <div class="toc-item"><span><strong>8.</strong> {art8_titre}</span><span class="toc-page">p.4</span></div>
          <div class="toc-item"><span><strong>9.</strong> Confidentialité</span><span class="toc-page">p.4</span></div>
          <div class="toc-item"><span><strong>10.</strong> Responsabilité</span><span class="toc-page">p.4</span></div>
          <div class="toc-item"><span><strong>11.</strong> Divers</span><span class="toc-page">p.4</span></div>
          <div class="toc-item"><span><strong>12.</strong> Loi applicable &amp; Juridiction</span><span class="toc-page">p.4</span></div>
          {toc_annexe}
        </div>
      </div>
    </div>

  </div>

  <div class="content-footer">
    <span>Entourage Recrutement · SAS · RCS Paris 828 310 581</span>
    <span>Page 2 / {total_pages}</span>
    <span><a href="{commercial['linkedin']}">{fields["commercial"]}</a> · {commercial["tel"]}</span>
  </div>
</div>

<!-- ═══════════════════════════════════════ PAGE 3 : ARTICLES 1–5 ═══════════════════════════════════════ -->
<div class="page">
  <div class="content-header">
    <div>{logo_tag_content}</div>
    <div class="content-header-doc">Contrat de Prestations · {fields["client_nom"].upper()}</div>
  </div>

  <div class="content-body">

    <div class="article">
      <div class="article-title"><div class="article-num">1</div> Préambule</div>
      <div class="article-body">
        <p><strong>{fields["client_nom"]}</strong>, {fields["client_activite"]}, souhaite recourir à un prestataire externe spécialisé pour l'assister dans la recherche et la sélection de candidats en vue de pourvoir un ou plusieurs postes au sein de ses effectifs.</p>
        <p>Le Prestataire, spécialiste du recrutement de cadres et dirigeants, déclare disposer des moyens humains, techniques et méthodologiques nécessaires pour satisfaire ce besoin avec le niveau d'exigence et de confidentialité requis.</p>
        <p>Par le présent contrat, les Parties conviennent des modalités de réalisation de la prestation et de leurs obligations réciproques.</p>
      </div>
    </div>

    <div class="article">
      <div class="article-title"><div class="article-num">2</div> Objet</div>
      <div class="article-body">
        <p>Le présent Contrat définit les modalités selon lesquelles le Prestataire effectuera, pour le compte du Client, la <strong>recherche, la sélection et la présentation de candidats</strong> en vue d'une embauche en CDI (ci-après la &laquo;&nbsp;Prestation&nbsp;&raquo;).</p>
        <p>Il est expressément convenu que ce Contrat ne comprend pas la mise à disposition de personnel au sens du Code du travail.</p>
      </div>
    </div>

    <div class="article">
      <div class="article-title"><div class="article-num">3</div> Obligations des Parties</div>
      <div class="article-body">
        <p><strong>3.1 Obligations du Client</strong></p>
        <ul>
          <li>Fournir au Prestataire toutes les informations utiles à l'exécution de la Prestation (description précise du poste, critères de sélection, contexte organisationnel).</li>
          <li>Notifier sans délai le Prestataire dès qu'une offre d'embauche est formulée à un candidat présenté, en précisant la date d'entrée effective.</li>
          <li>Désigner un interlocuteur référent pour assurer la fluidité du processus.</li>
        </ul>
        <p style="margin-top:2mm;"><strong>3.2 Obligations du Prestataire</strong></p>
        <ul>
          <li>Réaliser la Prestation en conformité avec la législation en vigueur, sans discrimination d'aucune sorte.</li>
          <li>Conseiller et orienter le Client afin de lui proposer les profils les mieux adaptés à ses besoins.</li>
          <li>Assurer la confidentialité des informations reçues et des candidatures traitées.</li>
          <li>Informer le Client de tout risque ou contrainte inhérent à la Prestation.</li>
        </ul>
      </div>
    </div>

    <div class="article">
      <div class="article-title"><div class="article-num">4</div> Durée &amp; Résiliation</div>
      <div class="article-body">
        <p>Le présent Contrat est conclu pour une <strong>durée indéterminée</strong>.</p>
        <p>Chaque Partie pourra résilier le Contrat pour convenance en respectant un <strong>préavis écrit d'un (1) mois</strong>, sans indemnité réciproque.</p>
        <p>En cas de manquement grave aux obligations contractuelles, l'une des Parties pourra résilier le Contrat par lettre recommandée avec accusé de réception, <strong>quinze (15) jours après mise en demeure restée sans effet</strong>.</p>
      </div>
    </div>

    <div class="article">
      <div class="article-title"><div class="article-num">5</div> Conditions Financières</div>
      <div class="article-body">
        <div class="highlight">
          Honoraires : <strong>{fields["honoraires_pct"]}% de la rémunération annuelle brute</strong> versée au candidat embauché — exprimés HT, TVA en sus.
        </div>
        <p>Le Prestataire conserve l'exclusivité sur les CV des candidats présentés pendant <strong>{fields["exclusivite_mois"]} mois</strong> à compter de leur présentation. Toute embauche d'un candidat présenté durant cette période, même pour un poste différent, donnera lieu au paiement des honoraires prévus.</p>
        <p>Si le Client avait connaissance d'un candidat présenté par le Prestataire dans les <strong>six (6) mois</strong> précédant son introduction, il devra en informer immédiatement le Prestataire. Au-delà de cette période, le candidat sera considéré comme présenté par le Prestataire.</p>
      </div>
    </div>

  </div>

  <div class="content-footer">
    <span>Entourage Recrutement · SAS · RCS Paris 828 310 581</span>
    <span>Page 3 / {total_pages}</span>
    <span><a href="{commercial['linkedin']}">{fields["commercial"]}</a> · {commercial["tel"]}</span>
  </div>
</div>

<!-- ═══════════════════════════════════════ PAGE 4 : ARTICLES 6–12 + SIGNATURE ═══════════════════════════════════════ -->
<div class="page">
  <div class="content-header">
    <div>{logo_tag_content}</div>
    <div class="content-header-doc">Contrat de Prestations · {fields["client_nom"].upper()}</div>
  </div>

  <div class="content-body">
    <div class="article">
      <div class="article-title"><div class="article-num">6</div> Facturation &amp; Conditions de Paiement</div>
      <div class="article-body">
        <p>Le Prestataire émettra une facture dès qu'une offre d'embauche aura été <strong>acceptée</strong> par un candidat présenté.</p>
        <div class="highlight">Délai de paiement : <strong>{fields["paiement_jours"]} jours</strong> à compter de la date de facturation.</div>
        <p>En cas de retard, des intérêts équivalents à <strong>trois (3) fois le taux légal en vigueur</strong> seront applicables, ainsi qu'une indemnité forfaitaire de recouvrement de 40 &euro;.</p>
      </div>
    </div>

    <div class="article">
      <div class="article-title"><div class="article-num">7</div> Garantie</div>
      <div class="article-body">
        <div class="highlight">Garantie de remplacement : <strong>{fields["garantie_mois"]} mois</strong> suivant la prise de poste effective du candidat.</div>
        <p>Si le candidat venait à quitter son emploi pendant cette période, le Prestataire s'engage à effectuer une nouvelle recherche <strong>sans frais supplémentaires</strong>, sous réserve que les honoraires aient été intégralement réglés.</p>
        <p>Garantie non applicable en cas de licenciement économique, restructuration ou faute imputable au Client. En cas de non-démarrage du candidat, les honoraires perçus seront remboursés.</p>
      </div>
    </div>

    <div class="article">
      <div class="article-title"><div class="article-num">8</div> {art8_titre}</div>
      <div class="article-body">
        {art8_body}
      </div>
    </div>

    <div class="article">
      <div class="article-title"><div class="article-num">9</div> Confidentialité</div>
      <div class="article-body">
        <p>Les Parties s'engagent à traiter de manière <strong>strictement confidentielle</strong> toutes les informations et données dont elles auront connaissance dans le cadre du présent Contrat, pendant toute sa durée et après sa cessation.</p>
      </div>
    </div>

    <div class="article">
      <div class="article-title"><div class="article-num">10</div> Responsabilité</div>
      <div class="article-body">
        <p>Le Prestataire exécute la Prestation sous une <strong>obligation de moyens</strong>. Sa responsabilité en cas de manquement sera limitée au montant des honoraires du présent Contrat. Aucun dommage indirect ne pourra être imputé au Prestataire.</p>
      </div>
    </div>

    <div class="article">
      <div class="article-title"><div class="article-num">11</div> Divers</div>
      <div class="article-body">
        <p>Le présent Contrat constitue l'intégralité de l'accord entre les Parties. Il ne pourra être cédé sans accord écrit préalable. Toute modification devra faire l'objet d'un avenant signé par les deux Parties.</p>
      </div>
    </div>

    <div class="article">
      <div class="article-title"><div class="article-num">12</div> Loi Applicable &amp; Juridiction</div>
      <div class="article-body">
        <p>Le présent Contrat est régi par le <strong>droit français</strong>. À défaut de solution amiable, les <strong>tribunaux du Tribunal de Commerce de Paris</strong> seront compétents.</p>
      </div>
    </div>

    <!-- SIGNATURES -->
    <div style="margin-top:5mm; padding-top:3mm; border-top: 2px solid #FFD700;">
      <div style="font-family:'Playfair Display',serif; font-size:11pt; color:#000; margin-bottom:3mm;">Signatures</div>
      <div class="signature-grid">
        <div class="sig-box">
          <div class="sig-label">Pour le Client</div>
          <div class="sig-name">{client_sig_name}</div>
          <div class="sig-title">{client_sig_title_prefix}{fields["client_nom"]}</div>
          <div class="sig-date">Fait à ____________, le {date_str}</div>
          <div class="sig-area"></div>
          <div class="sig-lu">Lu et approuvé — Bon pour accord</div>
        </div>
        <div class="sig-box">
          <div class="sig-label">Pour Entourage Recrutement</div>
          <div class="sig-name">{fields["commercial"]}</div>
          <div class="sig-title">{commercial["titre"]} &middot; Entourage Recrutement</div>
          <div class="sig-date">Fait à Paris, le {date_str}</div>
          <div class="sig-area"></div>
          <div class="sig-lu">Lu et approuvé — Bon pour accord</div>
        </div>
      </div>
    </div>
  </div>

  <div class="content-footer">
    <span>Entourage Recrutement · SAS · RCS Paris 828 310 581</span>
    <span>Page 4 / {total_pages}</span>
    <span><a href="{commercial['linkedin']}">{fields["commercial"]}</a> · {commercial["tel"]}</span>
  </div>
</div>
{annexe_html}
</body>
</html>"""


# ---------------------------------------------------------------------------
# BOUTON IMPRESSION PDF — fix encodage UTF-8 via TextDecoder
# ---------------------------------------------------------------------------

def get_print_button_html(html_content: str, label: str = "📄 Télécharger PDF") -> str:
    b64 = base64.b64encode(html_content.encode("utf-8")).decode()
    return f"""
    <script>
    function printDoc() {{
        var w = window.open('', '_blank');
        var bytes = Uint8Array.from(atob('{b64}'), function(c) {{ return c.charCodeAt(0); }});
        var html = new TextDecoder('utf-8').decode(bytes);
        w.document.open();
        w.document.write(html);
        w.document.close();
        w.onload = function() {{ setTimeout(function() {{ w.print(); }}, 400); }};
    }}
    </script>
    <button onclick="printDoc()" style="
        background:#000; color:#FFD700; border:none; padding:10px 18px;
        font-size:14px; font-weight:700; border-radius:6px; cursor:pointer;
        width:100%; font-family:sans-serif; letter-spacing:0.5px;">
        {label}
    </button>"""


# ---------------------------------------------------------------------------
# SIDEBAR — logo Entourage
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🖼 Logo Entourage")
    logo_file = st.file_uploader("Logo Entourage", type=["png", "jpg"], label_visibility="collapsed", key="logo_up_contrat")
    if logo_file:
        try:
            from PIL import Image
            img = Image.open(logo_file)
            img.thumbnail((600, 120), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            st.session_state.logo_b64 = base64.b64encode(buf.getvalue()).decode()
        except ImportError:
            st.session_state.logo_b64 = base64.b64encode(logo_file.read()).decode()
        st.success("Logo chargé ✓")
    if get_logo_entourage():
        st.image(io.BytesIO(base64.b64decode(get_logo_entourage())), use_container_width=True)

# ---------------------------------------------------------------------------
# UI — PAGE PRINCIPALE
# ---------------------------------------------------------------------------

st.title("📋 Générateur de Contrat")
st.caption("Remplis les champs → contrat professionnel généré instantanément")

st.divider()

# SECTION 1 — Client
st.subheader("🏢 Informations Client")
col1, col2 = st.columns(2)
with col1:
    client_nom = st.text_input("Nom de la société *", placeholder="Ex : TD Williamson SAS")
    client_siret = st.text_input("N° SIRET *", placeholder="Ex : 338 308 364 00011")
    client_adresse = st.text_input("Adresse du siège social *", placeholder="Ex : 11 rue de l'Atome, 67800 Bischheim")
with col2:
    client_representant = st.text_input("Représentant légal (optionnel)", placeholder="Ex : Jean Dupont")
    client_titre_rep = st.text_input("Titre du représentant (optionnel)", placeholder="Ex : Directeur Général")
    client_activite = st.text_input("Secteur / Activité *", placeholder="Ex : commerce de gros d'équipements industriels")

st.markdown("##### Logo client (optionnel)")
col_logo1, col_logo2 = st.columns([1, 1])
with col_logo1:
    client_logo_url = st.text_input("URL du logo client", placeholder="https://...")
with col_logo2:
    client_logo_file = st.file_uploader("Ou uploader le logo", type=["png", "jpg", "jpeg"], key="client_logo_up")

client_logo_b64 = None
if client_logo_file:
    try:
        from PIL import Image
        img = Image.open(client_logo_file)
        img.thumbnail((400, 200), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        client_logo_b64 = base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        client_logo_b64 = base64.b64encode(client_logo_file.read()).decode()

st.divider()

# SECTION 2 — Conditions
st.subheader("⚖️ Conditions Contractuelles")
col1, col2, col3, col4 = st.columns(4)
with col1:
    honoraires_pct = st.number_input("Honoraires (%)", min_value=1, max_value=50, value=24, step=1)
with col2:
    garantie_mois = st.number_input("Garantie (mois)", min_value=1, max_value=12, value=4, step=1)
with col3:
    paiement_jours = st.number_input("Délai paiement (jours)", min_value=15, max_value=90, value=30, step=15)
with col4:
    exclusivite_mois = st.number_input("Exclusivité CV (mois)", min_value=6, max_value=24, value=12, step=1)

st.markdown("")
exclusivite_recherche = st.checkbox(
    "🔒 Clause d'exclusivité de recherche (Annexe 1)",
    value=False,
    help=(
        "Ajoute une annexe juridique au contrat : le cabinet conserve l'exclusivité de la recherche "
        "pendant la durée choisie. Le recours du Client à une autre ressource de recrutement pendant "
        "cette période ouvre droit à résiliation aux torts du Client et au paiement de pénalités. "
        "Décoché, le contrat reste non exclusif (Article 8 d'origine)."
    ),
)

excl_jours = 30
excl_penalite_pct = 15
if exclusivite_recherche:
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        excl_jours = st.number_input(
            "Durée de l'exclusivité (jours)", min_value=15, max_value=90, value=30, step=15
        )
    with col_e2:
        excl_penalite_pct = st.number_input(
            "Pénalité forfaitaire (% rém. annuelle brute)", min_value=5, max_value=50, value=15, step=5
        )
    st.info(
        f"➕ Le contrat comportera **5 pages** : l'Article 8 renvoie à l'**Annexe 1**, "
        f"qui détaille l'exclusivité de {excl_jours} jours, l'obligation d'information du Client, "
        f"la résiliation aux torts exclusifs du Client et la pénalité de {excl_penalite_pct} %."
    )

st.divider()

# SECTION 3 — Signature
st.subheader("✍️ Signature")
col1, col2 = st.columns(2)
with col1:
    commercial = st.radio("Commercial Entourage", list(COMMERCIAUX.keys()), horizontal=True)
with col2:
    date_signature = st.date_input("Date de signature", value=datetime.date.today(), format="DD/MM/YYYY")

st.divider()

# Vérification champs obligatoires (représentant et titre ne sont plus obligatoires)
champs_requis = [client_nom, client_siret, client_adresse, client_activite]
tous_remplis = all(c.strip() for c in champs_requis)

if not tous_remplis:
    st.warning("⚠️ Remplis tous les champs obligatoires (*) pour générer le contrat.")

if st.button("⚡ Générer le Contrat", type="primary", disabled=not tous_remplis):
    fields = {
        "client_nom": client_nom,
        "client_siret": client_siret,
        "client_adresse": client_adresse,
        "client_representant": client_representant,
        "client_titre_rep": client_titre_rep,
        "client_activite": client_activite,
        "client_logo_url": client_logo_url,
        "client_logo_b64": client_logo_b64,
        "honoraires_pct": honoraires_pct,
        "garantie_mois": garantie_mois,
        "paiement_jours": paiement_jours,
        "exclusivite_mois": exclusivite_mois,
        "exclusivite_recherche": exclusivite_recherche,
        "exclusivite_jours": excl_jours,
        "exclusivite_penalite_pct": excl_penalite_pct,
        "commercial": commercial,
        "date_signature": date_signature,
    }
    st.session_state.contrat_html = build_contract_html(fields)
    st.session_state.contrat_client = client_nom
    st.rerun()

# ---------------------------------------------------------------------------
# RÉSULTAT
# ---------------------------------------------------------------------------

if "contrat_html" in st.session_state:
    st.divider()

    col1, col2, col3 = st.columns([2, 2, 6])
    with col1:
        st.components.v1.html(
            get_print_button_html(st.session_state.contrat_html),
            height=50
        )
    with col2:
        if st.button("🗑️ Réinitialiser", use_container_width=True):
            st.session_state.pop("contrat_html", None)
            st.session_state.pop("contrat_client", None)
            st.rerun()

    st.caption("💡 Cliquer sur 📄 Télécharger PDF → fenêtre d'impression → Enregistrer en PDF")

    st.subheader("Aperçu")
    st.components.v1.html(st.session_state.contrat_html, height=1500, scrolling=True)
