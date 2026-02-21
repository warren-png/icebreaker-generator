import streamlit as st
import base64
import os
import io
import datetime
from pathlib import Path
from utils.auth import check_password

st.set_page_config(
    page_title="Contrat | Biz Dev Entourage",
    page_icon="📋",
    layout="wide"
)

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
        "titre": "Consultant"
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
# GÉNÉRATION DU HTML CONTRAT
# ---------------------------------------------------------------------------

def build_contract_html(fields: dict) -> str:
    logo_b64 = get_logo_entourage()
    logo_tag = (
        f'<img src="data:image/png;base64,{logo_b64}" style="height:16mm;object-fit:contain;">'
        if logo_b64 else
        '<span class="brand">ENTOURAGE RECRUTEMENT</span>'
    )

    client_logo_tag = ""
    if fields.get("client_logo_b64"):
        client_logo_tag = (
            f'<img src="data:image/png;base64,{fields["client_logo_b64"]}" '
            f'style="max-height:20mm;max-width:60mm;object-fit:contain;">'
        )
    elif fields.get("client_logo_url"):
        client_logo_tag = (
            f'<img src="{fields["client_logo_url"]}" '
            f'style="max-height:20mm;max-width:60mm;object-fit:contain;" '
            f'onerror="this.style.display=\'none\'">'
        )

    commercial = COMMERCIAUX[fields["commercial"]]
    date_str = fields["date_signature"].strftime("%d/%m/%Y") if fields.get("date_signature") else "___/___/______"

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Contrat — {fields['client_nom']}</title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  body {{ font-family: 'Manrope', sans-serif; background: #555; display: flex; flex-direction: column; align-items: center; padding: 40px 0; gap: 24px; }}

  /* PAGE */
  .page {{ width: 210mm; background: #fff; box-shadow: 0 0 20px rgba(0,0,0,.5); display: flex; flex-direction: column; position: relative; }}

  /* HEADER */
  .header {{ background: #000; border-bottom: 2.5mm solid #FFD700; padding: 0 14mm; height: 24mm; display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; }}
  .header-right {{ text-align: right; }}
  .doc-label {{ color: #FFD700; font-size: 7.5pt; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 700; }}
  .doc-ref {{ color: #fff; font-size: 9pt; font-weight: 600; margin-top: 2px; }}

  /* COUVERTURE */
  .cover-body {{ padding: 12mm 14mm; flex-grow: 1; display: flex; flex-direction: column; gap: 8mm; }}
  .cover-title {{ font-family: 'Playfair Display', serif; font-size: 22pt; color: #000; text-align: center; padding: 8mm 0 4mm; border-bottom: 1px solid #FFD700; }}
  .cover-subtitle {{ font-size: 9pt; color: #777; text-align: center; margin-top: 2mm; text-transform: uppercase; letter-spacing: 1px; }}

  /* PARTIES */
  .parties {{ display: grid; grid-template-columns: 1fr auto 1fr; gap: 6mm; align-items: start; margin-top: 4mm; }}
  .party-box {{ background: #f8f9fa; border-left: 3px solid #000; padding: 5mm 6mm; }}
  .party-box.client {{ border-left-color: #FFD700; }}
  .party-label {{ font-size: 7pt; text-transform: uppercase; letter-spacing: 1px; color: #999; font-weight: 700; margin-bottom: 3mm; }}
  .party-name {{ font-family: 'Playfair Display', serif; font-size: 13pt; color: #000; margin-bottom: 2mm; }}
  .party-info {{ font-size: 8pt; color: #555; line-height: 1.5; }}
  .party-info strong {{ color: #000; }}
  .and-separator {{ display: flex; align-items: center; justify-content: center; }}
  .and-circle {{ width: 10mm; height: 10mm; background: #000; color: #FFD700; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 9pt; flex-shrink: 0; }}

  /* CLIENT LOGO */
  .client-logo-wrap {{ text-align: center; padding: 4mm 0 2mm; }}

  /* FOOTER COVER */
  .cover-footer {{ margin-top: auto; background: #f8f9fa; border-top: 1px solid #eee; padding: 4mm 14mm; display: flex; justify-content: space-between; align-items: center; font-size: 8pt; color: #777; }}
  .cover-footer a {{ color: #000; font-weight: 700; text-decoration: none; border-bottom: 1px solid #FFD700; }}

  /* PAGE DE CONTENU */
  .content-header {{ background: #000; height: 10mm; display: flex; align-items: center; padding: 0 14mm; border-bottom: 1.5mm solid #FFD700; flex-shrink: 0; }}
  .content-header-brand {{ color: #fff; font-size: 8pt; font-weight: 700; letter-spacing: 1px; flex: 1; }}
  .content-header-doc {{ color: #FFD700; font-size: 7pt; text-align: right; }}
  .content-body {{ padding: 8mm 14mm 6mm; flex-grow: 1; }}
  .content-footer {{ background: #f8f9fa; border-top: 1px solid #eee; padding: 3mm 14mm; display: flex; justify-content: space-between; font-size: 7.5pt; color: #999; flex-shrink: 0; }}
  .content-footer a {{ color: #000; font-weight: 700; text-decoration: none; border-bottom: 1px solid #FFD700; }}

  /* ARTICLES */
  .toc {{ background: #f8f9fa; border-left: 3px solid #FFD700; padding: 5mm 6mm; margin-bottom: 6mm; }}
  .toc-title {{ font-weight: 800; font-size: 9pt; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 3mm; color: #000; }}
  .toc-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1mm 6mm; }}
  .toc-item {{ font-size: 8pt; color: #555; }}
  .toc-item strong {{ color: #000; }}

  .article {{ margin-bottom: 6mm; }}
  .article-title {{
    font-family: 'Playfair Display', serif;
    font-size: 12pt;
    color: #000;
    border-bottom: 1px solid #eee;
    padding-bottom: 2mm;
    margin-bottom: 3mm;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .article-num {{
    background: #000;
    color: #FFD700;
    font-family: 'Manrope', sans-serif;
    font-size: 8pt;
    font-weight: 800;
    width: 7mm; height: 7mm;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
  }}
  .article-body {{ font-size: 8.5pt; line-height: 1.55; color: #333; text-align: justify; }}
  .article-body p {{ margin-bottom: 2mm; }}
  .article-body ul {{ padding-left: 5mm; margin: 1mm 0 2mm; }}
  .article-body li {{ margin-bottom: 1mm; }}
  .highlight {{ background: #fffcf0; border-left: 2px solid #FFD700; padding: 2mm 4mm; margin: 2mm 0; font-weight: 600; color: #000; font-size: 8.5pt; }}

  /* SIGNATURE */
  .signature-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8mm; margin-top: 4mm; }}
  .sig-box {{ border: 1px solid #ddd; border-radius: 4px; padding: 5mm; }}
  .sig-label {{ font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.5px; color: #999; font-weight: 700; margin-bottom: 3mm; }}
  .sig-name {{ font-weight: 800; font-size: 10pt; color: #000; }}
  .sig-title {{ font-size: 8pt; color: #777; margin-bottom: 4mm; }}
  .sig-date {{ font-size: 8pt; color: #555; margin-bottom: 2mm; }}
  .sig-area {{ border-bottom: 1px solid #ccc; height: 15mm; margin-top: 2mm; }}
  .sig-lu {{ font-size: 7pt; color: #aaa; margin-top: 1mm; font-style: italic; }}

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
    <div>{logo_tag}</div>
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

    {"<div class='client-logo-wrap'>" + client_logo_tag + "</div>" if client_logo_tag else ""}

    <div class="parties">
      <div class="party-box">
        <div class="party-label">Le Prestataire</div>
        <div class="party-name">Entourage Recrutement</div>
        <div class="party-info">
          SAS au capital de 1 000 €<br>
          RCS Paris — n° 828 310 581<br>
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
          <strong>Représenté par : {fields["client_representant"]}</strong><br>
          {fields["client_titre_rep"]}
        </div>
      </div>
    </div>

    <div class="highlight">
      📅 &nbsp;Fait à Paris, le {date_str} &nbsp;·&nbsp; Contrat à durée indéterminée
    </div>
  </div>

  <div class="cover-footer">
    <span>Entourage Recrutement · 36 rue du Faubourg Saint-Honoré, 75008 Paris</span>
    <span><a href="{commercial['linkedin']}" target="_blank">{fields["commercial"]}</a> · {commercial["tel"]}</span>
  </div>
</div>

<!-- ═══════════════════════════════════════ PAGE 2 : PRÉAMBULE + ARTICLES 1–5 ═══════════════════════════════════════ -->
<div class="page">
  <div class="content-header">
    <div class="content-header-brand">ENTOURAGE RECRUTEMENT</div>
    <div class="content-header-doc">Contrat de Prestations · {fields["client_nom"].upper()}</div>
  </div>

  <div class="content-body">
    <div class="toc">
      <div class="toc-title">Table des matières</div>
      <div class="toc-grid">
        <div class="toc-item"><strong>1.</strong> Préambule</div>
        <div class="toc-item"><strong>7.</strong> Garantie</div>
        <div class="toc-item"><strong>2.</strong> Objet</div>
        <div class="toc-item"><strong>8.</strong> Exclusivité</div>
        <div class="toc-item"><strong>3.</strong> Obligations des parties</div>
        <div class="toc-item"><strong>9.</strong> Confidentialité</div>
        <div class="toc-item"><strong>4.</strong> Durée & Résiliation</div>
        <div class="toc-item"><strong>10.</strong> Responsabilité</div>
        <div class="toc-item"><strong>5.</strong> Conditions financières</div>
        <div class="toc-item"><strong>11.</strong> Divers</div>
        <div class="toc-item"><strong>6.</strong> Facturation & Paiement</div>
        <div class="toc-item"><strong>12.</strong> Loi applicable</div>
      </div>
    </div>

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
        <p>Le présent Contrat définit les modalités selon lesquelles le Prestataire effectuera, pour le compte du Client, la <strong>recherche, la sélection et la présentation de candidats</strong> en vue d'une embauche en CDI (ci-après la « Prestation »).</p>
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
        <p style="margin-top:3mm;"><strong>3.2 Obligations du Prestataire</strong></p>
        <ul>
          <li>Réaliser la Prestation en conformité avec la législation en vigueur, sans discrimination d'aucune sorte.</li>
          <li>Conseiller et orienter le Client afin de lui proposer les profils les mieux adaptés à ses besoins.</li>
          <li>Assurer la confidentialité des informations reçues et des candidatures traitées.</li>
          <li>Informer le Client de tout risque ou contrainte inhérent à la Prestation.</li>
        </ul>
      </div>
    </div>

    <div class="article">
      <div class="article-title"><div class="article-num">4</div> Durée & Résiliation</div>
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
    <span>Page 2 / 3</span>
    <span><a href="{commercial['linkedin']}">{fields["commercial"]}</a> · {commercial["tel"]}</span>
  </div>
</div>

<!-- ═══════════════════════════════════════ PAGE 3 : ARTICLES 6–12 + SIGNATURE ═══════════════════════════════════════ -->
<div class="page">
  <div class="content-header">
    <div class="content-header-brand">ENTOURAGE RECRUTEMENT</div>
    <div class="content-header-doc">Contrat de Prestations · {fields["client_nom"].upper()}</div>
  </div>

  <div class="content-body">
    <div class="article">
      <div class="article-title"><div class="article-num">6</div> Facturation & Conditions de Paiement</div>
      <div class="article-body">
        <p>Le Prestataire émettra une facture dès qu'une offre d'embauche aura été <strong>acceptée</strong> par un candidat présenté.</p>
        <div class="highlight">Délai de paiement : <strong>{fields["paiement_jours"]} jours</strong> à compter de la date de facturation.</div>
        <p>En cas de retard, le Prestataire pourra appliquer, conformément à l'article L 441-6 du Code de Commerce, des intérêts de retard équivalents à <strong>trois (3) fois le taux légal en vigueur</strong>, ainsi qu'une indemnité forfaitaire de recouvrement de 40 €.</p>
      </div>
    </div>

    <div class="article">
      <div class="article-title"><div class="article-num">7</div> Garantie</div>
      <div class="article-body">
        <div class="highlight">Garantie de remplacement : <strong>{fields["garantie_mois"]} mois</strong> suivant la prise de poste effective du candidat.</div>
        <p>Si, pendant cette période, le candidat venait à quitter son emploi pour quelque cause que ce soit, le Prestataire s'engage à effectuer une nouvelle recherche <strong>sans frais supplémentaires</strong>, sous réserve que l'intégralité des honoraires initiaux ait été réglée.</p>
        <p>Cette garantie ne s'applique pas en cas de départ lié à : licenciement économique, restructuration, inadéquation entre le poste défini et la réalité des missions, ou faute imputable au Client.</p>
        <p>Si le candidat ne démarre jamais son emploi après acceptation de l'offre, le Prestataire remboursera l'intégralité des honoraires perçus.</p>
      </div>
    </div>

    <div class="article">
      <div class="article-title"><div class="article-num">8</div> Exclusivité</div>
      <div class="article-body">
        <p>Le Prestataire ne bénéficie pas d'un droit d'exclusivité concernant les besoins exprimés par le Client, lequel reste libre de solliciter d'autres prestataires pour tout ou partie de la Prestation.</p>
      </div>
    </div>

    <div class="article">
      <div class="article-title"><div class="article-num">9</div> Confidentialité</div>
      <div class="article-body">
        <p>Les Parties s'engagent à traiter de manière <strong>strictement confidentielle</strong> toutes les informations, documents et données dont elles auront connaissance dans le cadre du présent Contrat, pendant toute sa durée et après sa cessation.</p>
        <p>Cette obligation ne s'applique pas aux informations déjà du domaine public, connues antérieurement ou communiquées en vertu d'une décision judiciaire.</p>
      </div>
    </div>

    <div class="article">
      <div class="article-title"><div class="article-num">10</div> Responsabilité</div>
      <div class="article-body">
        <p>Le Prestataire exécute la Prestation sous une <strong>obligation de moyens</strong>. Le Client demeure seul décisionnaire quant à la sélection finale des candidats présentés.</p>
        <p>La responsabilité du Prestataire, en cas de manquement, sera limitée au montant des honoraires prévus ou perçus dans le cadre du présent Contrat. En aucun cas, le Prestataire ne pourra être tenu responsable de dommages indirects.</p>
      </div>
    </div>

    <div class="article">
      <div class="article-title"><div class="article-num">11</div> Divers</div>
      <div class="article-body">
        <p>Le présent Contrat constitue l'intégralité de l'accord entre les Parties et prévaut sur toute condition générale antérieure. Il est conclu en considération de la personne des Parties et ne pourra être cédé sans accord écrit préalable. Toute modification devra faire l'objet d'un avenant signé par les deux Parties.</p>
      </div>
    </div>

    <div class="article">
      <div class="article-title"><div class="article-num">12</div> Loi Applicable & Juridiction</div>
      <div class="article-body">
        <p>Le présent Contrat est régi par le <strong>droit français</strong>. En cas de litige, les Parties s'engagent à rechercher une solution amiable avant toute action judiciaire. À défaut d'accord, les <strong>tribunaux compétents seront ceux du Tribunal de Commerce de Paris</strong>.</p>
      </div>
    </div>

    <!-- SIGNATURES -->
    <div style="margin-top:6mm; padding-top:4mm; border-top: 2px solid #FFD700;">
      <div style="font-family:'Playfair Display',serif; font-size:12pt; color:#000; margin-bottom:4mm;">Signatures</div>
      <div class="signature-grid">
        <div class="sig-box">
          <div class="sig-label">Pour le Client</div>
          <div class="sig-name">{fields["client_representant"]}</div>
          <div class="sig-title">{fields["client_titre_rep"]} · {fields["client_nom"]}</div>
          <div class="sig-date">Fait à ____________, le {date_str}</div>
          <div class="sig-area"></div>
          <div class="sig-lu">Lu et approuvé — Bon pour accord</div>
        </div>
        <div class="sig-box">
          <div class="sig-label">Pour Entourage Recrutement</div>
          <div class="sig-name">{fields["commercial"]}</div>
          <div class="sig-title">{commercial["titre"]} · Entourage Recrutement</div>
          <div class="sig-date">Fait à Paris, le {date_str}</div>
          <div class="sig-area"></div>
          <div class="sig-lu">Lu et approuvé — Bon pour accord</div>
        </div>
      </div>
    </div>
  </div>

  <div class="content-footer">
    <span>Entourage Recrutement · SAS · RCS Paris 828 310 581</span>
    <span>Page 3 / 3</span>
    <span><a href="{commercial['linkedin']}">{fields["commercial"]}</a> · {commercial["tel"]}</span>
  </div>
</div>

</body>
</html>"""


# ---------------------------------------------------------------------------
# BOUTON IMPRESSION PDF
# ---------------------------------------------------------------------------

def get_print_button_html(html_content: str, label: str = "📄 Télécharger PDF") -> str:
    b64 = base64.b64encode(html_content.encode("utf-8")).decode()
    return f"""
    <script>
    function printDoc() {{
        var w = window.open('', '_blank');
        var html = atob('{b64}');
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
    client_representant = st.text_input("Représentant légal *", placeholder="Ex : Jean Dupont")
    client_titre_rep = st.text_input("Titre du représentant *", placeholder="Ex : Directeur Général")
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

st.divider()

# SECTION 3 — Signature
st.subheader("✍️ Signature")
col1, col2 = st.columns(2)
with col1:
    commercial = st.radio("Commercial Entourage", list(COMMERCIAUX.keys()), horizontal=True)
with col2:
    date_signature = st.date_input("Date de signature", value=datetime.date.today(), format="DD/MM/YYYY")

st.divider()

# Vérification champs obligatoires
champs_requis = [client_nom, client_siret, client_adresse, client_representant, client_titre_rep, client_activite]
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
    st.components.v1.html(st.session_state.contrat_html, height=1200, scrolling=True)
