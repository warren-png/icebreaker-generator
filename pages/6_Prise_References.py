import streamlit as st
import anthropic
import base64
import os
import io
import re
import datetime
from pathlib import Path
from utils.auth import check_password
from utils.ui import inject_global_styles

st.set_page_config(
    page_title="Prise de Références | Entourage",
    page_icon="🔍",
    layout="wide"
)

inject_global_styles()

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
# LOGO
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
# PROMPT CLAUDE
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Tu es expert en recrutement de cadres dirigeants pour Entourage Recrutement, cabinet de chasse de têtes.

Tu reçois une retranscription libre ou une synthèse d'un entretien de prise de références pour un candidat.

Ton rôle : structurer ce contenu en un document professionnel de prise de références, organisé en sections thématiques claires.

RÈGLES ABSOLUES :
- Retourne UNIQUEMENT le code HTML des sections (pas de DOCTYPE, pas de <html>, pas de <body>)
- Organise en 5 à 7 thèmes pertinents selon le contenu (ex: Compétences managériales, Expertise technique, Qualités relationnelles, Gestion sous pression, Points de vigilance, Recommandation globale…)
- Pour chaque thème : une question courte et percutante + une réponse synthétique issue du texte
- Dans les réponses : mets en <strong> les mots-clés positifs, compétences clés, qualificatifs importants
- Les points de vigilance ou nuances doivent être dans une section dédiée avec la classe CSS "warning"
- La dernière section doit être la recommandation globale avec la classe CSS "recommendation"
- Langue : français, ton professionnel et synthétique
- N'invente rien : base-toi uniquement sur le contenu fourni
- Si le texte est une synthèse déjà structurée : reformule en Q/R thématiques
- Si le texte est une transcription brute : extrais et structure les informations clés

FORMAT HTML À RETOURNER (uniquement ces blocs, répétés pour chaque thème) :

<div class="ref-section">
  <div class="ref-question">Intitulé du thème / question posée</div>
  <div class="ref-answer">Réponse structurée avec <strong>mots-clés en gras</strong>.</div>
</div>

Pour la section points de vigilance :
<div class="ref-section warning">
  <div class="ref-question">⚠ Points de vigilance</div>
  <div class="ref-answer">Contenu...</div>
</div>

Pour la recommandation finale :
<div class="ref-section recommendation">
  <div class="ref-question">★ Recommandation globale</div>
  <div class="ref-answer">Contenu...</div>
</div>"""


def generate_reference_content(
    transcription: str,
    candidate_name: str,
    reference_name: str,
    modification: str = None,
    previous_sections: str = None
) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    if modification and previous_sections:
        user_content = f"""Voici les sections HTML de la prise de références que tu as générées pour {candidate_name} (référence : {reference_name}) :

{previous_sections}

L'utilisateur demande la modification suivante :
{modification}

Applique cette modification et retourne uniquement les sections HTML mises à jour."""
    else:
        user_content = f"""Candidat : {candidate_name}
Référence donnée par : {reference_name}

Voici la retranscription / synthèse de l'entretien de prise de références :

---
{transcription}
---

Structure ce contenu en sections thématiques professionnelles selon les instructions."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}]
    )

    sections_html = message.content[0].text.strip()
    sections_html = re.sub(r"^```[^\n]*\n", "", sections_html)
    sections_html = re.sub(r"\n```\s*$", "", sections_html.strip())
    return sections_html.strip()


# ---------------------------------------------------------------------------
# BUILD HTML DOCUMENT
# ---------------------------------------------------------------------------

def build_reference_html(fields: dict, sections_html: str) -> str:
    logo_b64 = get_logo_entourage()
    commercial = COMMERCIAUX[fields["commercial"]]
    date_str = datetime.date.today().strftime("%d/%m/%Y")

    logo_cover = (
        f'<img src="data:image/png;base64,{logo_b64}" style="height:18mm;max-width:80mm;object-fit:contain;">'
        if logo_b64 else
        '<span style="color:#FFD700;font-weight:800;font-size:13pt;letter-spacing:1px;">ENTOURAGE RECRUTEMENT</span>'
    )
    logo_small = (
        f'<img src="data:image/png;base64,{logo_b64}" style="height:11mm;max-width:55mm;object-fit:contain;display:block;">'
        if logo_b64 else
        '<span style="color:#FFD700;font-weight:800;font-size:9pt;letter-spacing:1px;">ENTOURAGE RECRUTEMENT</span>'
    )

    linkedin_url = fields.get("reference_linkedin", "").strip()
    linkedin_tag = (
        f'<a href="{linkedin_url}" target="_blank" style="color:#000;font-weight:700;text-decoration:none;border-bottom:1px solid #FFD700;">'
        f'{fields["reference_nom"]}</a>'
        if linkedin_url else
        f'<strong>{fields["reference_nom"]}</strong>'
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Prise de Références — {fields['candidate_nom']}</title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  body {{ font-family:'Manrope',sans-serif; background:#555; display:flex; flex-direction:column; align-items:center; padding:40px 0; gap:24px; }}

  .page {{
    width:210mm;
    height:297mm;
    background:#fff;
    box-shadow:0 0 20px rgba(0,0,0,.5);
    display:flex;
    flex-direction:column;
    overflow:hidden;
    position:relative;
  }}

  /* HEADER COUVERTURE */
  .header {{ background:#000; border-bottom:2.5mm solid #FFD700; padding:0 14mm; height:24mm; display:flex; align-items:center; justify-content:space-between; flex-shrink:0; }}
  .doc-label {{ color:#FFD700; font-size:7.5pt; text-transform:uppercase; letter-spacing:1.5px; font-weight:700; }}
  .doc-ref {{ color:#fff; font-size:9pt; font-weight:600; margin-top:2px; }}

  /* COUVERTURE */
  .cover-body {{ padding:14mm 14mm; flex-grow:1; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; gap:8mm; }}
  .cover-title {{ font-family:'Playfair Display',serif; font-size:26pt; color:#000; padding:6mm 0 4mm; border-bottom:2px solid #FFD700; }}
  .cover-subtitle {{ font-size:9.5pt; color:#777; text-transform:uppercase; letter-spacing:1.5px; }}

  .cover-card {{ background:#f8f9fa; width:100%; max-width:130mm; border-left:3px solid #FFD700; padding:6mm 8mm; text-align:left; }}
  .cover-card-label {{ font-size:7pt; text-transform:uppercase; letter-spacing:1px; color:#999; font-weight:700; margin-bottom:1.5mm; }}
  .cover-card-value {{ font-family:'Playfair Display',serif; font-size:14pt; color:#000; }}
  .cover-card-sub {{ font-size:8pt; color:#777; margin-top:1mm; }}

  .cover-sep {{ width:100%; max-width:130mm; border-top:1px solid #eee; }}

  /* FOOTER */
  .cover-footer {{ background:#f8f9fa; border-top:1px solid #eee; padding:4mm 14mm; display:flex; justify-content:space-between; align-items:center; font-size:8pt; color:#777; flex-shrink:0; height:12mm; }}
  .cover-footer a {{ color:#000; font-weight:700; text-decoration:none; border-bottom:1px solid #FFD700; }}
  .content-footer {{ background:#f8f9fa; border-top:1px solid #eee; padding:0 14mm; display:flex; justify-content:space-between; align-items:center; font-size:7.5pt; color:#999; flex-shrink:0; height:10mm; }}
  .content-footer a {{ color:#000; font-weight:700; text-decoration:none; border-bottom:1px solid #FFD700; }}

  /* HEADER CONTENU */
  .content-header {{ background:#000; height:16mm; display:flex; align-items:center; padding:0 14mm; border-bottom:1.5mm solid #FFD700; flex-shrink:0; justify-content:space-between; overflow:hidden; }}
  .content-header-doc {{ color:#FFD700; font-size:7pt; text-align:right; white-space:nowrap; margin-left:4mm; }}
  .content-body {{ padding:7mm 14mm 5mm; flex-grow:1; display:flex; flex-direction:column; gap:0; overflow:hidden; }}

  /* SECTIONS RÉFÉRENCES */
  .ref-section {{
    border-left:3px solid #000;
    padding:3.5mm 5mm 3.5mm 5mm;
    margin-bottom:3mm;
    background:#fafafa;
  }}
  .ref-section.warning {{
    border-left-color:#e67e22;
    background:#fff8f4;
  }}
  .ref-section.recommendation {{
    border-left-color:#FFD700;
    background:#fffcf0;
  }}

  .ref-question {{
    font-size:7.5pt;
    font-weight:800;
    text-transform:uppercase;
    letter-spacing:0.8px;
    color:#000;
    margin-bottom:1.5mm;
  }}
  .ref-section.warning .ref-question {{ color:#c0392b; }}
  .ref-section.recommendation .ref-question {{ color:#8a6a00; }}

  .ref-answer {{
    font-size:8.5pt;
    color:#333;
    line-height:1.55;
  }}
  .ref-answer strong {{
    color:#000;
    font-weight:700;
  }}
  .ref-section.recommendation .ref-answer {{
    font-size:9pt;
    font-weight:600;
    color:#4a3800;
  }}

  /* BANDEAU CANDIDAT EN HAUT DE PAGE 2 */
  .candidate-band {{
    background:#000;
    color:#FFD700;
    padding:2.5mm 5mm;
    font-size:8pt;
    font-weight:700;
    letter-spacing:0.5px;
    flex-shrink:0;
    display:flex;
    justify-content:space-between;
    align-items:center;
  }}
  .candidate-band span {{ color:#aaa; font-weight:400; font-size:7.5pt; }}

  @page {{ size: A4 portrait; margin: 0; }}
  @media print {{
    body {{ background:none; padding:0; gap:0; }}
    .page {{
      box-shadow:none;
      break-after: page;
      page-break-after: always;
      width:210mm;
      height:297mm;
    }}
    .page:last-child {{
      break-after: avoid;
      page-break-after: avoid;
    }}
  }}
</style>
</head>
<body>

<!-- ═══ PAGE 1 : COUVERTURE ═══ -->
<div class="page">
  <div class="header">
    {logo_cover}
    <div style="text-align:right;">
      <div class="doc-label">Document confidentiel</div>
      <div class="doc-ref">Prise de Références — {fields['candidate_nom']}</div>
    </div>
  </div>

  <div class="cover-body">
    <div>
      <div class="cover-title">Prise de Références</div>
      <div class="cover-subtitle">Entretien confidentiel — Cabinet Entourage Recrutement</div>
    </div>

    <div class="cover-card">
      <div class="cover-card-label">Candidat évalué</div>
      <div class="cover-card-value">{fields['candidate_nom']}</div>
    </div>

    <div class="cover-sep"></div>

    <div class="cover-card">
      <div class="cover-card-label">Référence consultée</div>
      <div class="cover-card-value">{linkedin_tag}</div>
      {'<div class="cover-card-sub">' + linkedin_url + '</div>' if linkedin_url else ''}
    </div>

    <div style="margin-top:4mm; font-size:7.5pt; color:#aaa;">
      Entretien mené par <strong style="color:#555;">{fields["commercial"]}</strong> · {date_str}
    </div>
  </div>

  <div class="cover-footer">
    <span>Entourage Recrutement · 36 rue du Faubourg Saint-Honoré, 75008 Paris</span>
    <span><a href="{commercial['linkedin']}" target="_blank">{fields['commercial']}</a> · {commercial['tel']}</span>
  </div>
</div>

<!-- ═══ PAGE 2 : CONTENU ═══ -->
<div class="page">
  <div class="content-header">
    {logo_small}
    <div class="content-header-doc">Références · {fields['candidate_nom'].upper()}</div>
  </div>

  <div class="candidate-band">
    <span>Référence : <strong style="color:#FFD700;">{fields['reference_nom']}</strong></span>
    <span>Candidat : {fields['candidate_nom']} · {date_str}</span>
  </div>

  <div class="content-body">
    {sections_html}
  </div>

  <div class="content-footer">
    <span>Entourage Recrutement · SAS · RCS Paris 828 310 581</span>
    <span>Document confidentiel</span>
    <span><a href="{commercial['linkedin']}">{fields['commercial']}</a> · {commercial['tel']}</span>
  </div>
</div>

</body>
</html>"""


# ---------------------------------------------------------------------------
# PRINT BUTTON
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
# SIDEBAR
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🖼 Logo Entourage")
    logo_file = st.file_uploader("Logo", type=["png", "jpg"], label_visibility="collapsed", key="logo_up_ref")
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
# UI
# ---------------------------------------------------------------------------

st.title("🔍 Prise de Références")
st.caption("Colle une transcription libre ou une synthèse → document structuré généré par Claude")

st.divider()

st.subheader("👤 Informations")
col1, col2, col3 = st.columns(3)
with col1:
    candidate_nom = st.text_input("Nom du candidat *", placeholder="Ex : Jean Dupont")
with col2:
    reference_nom = st.text_input("Nom de la référence *", placeholder="Ex : Marie Martin")
with col3:
    reference_linkedin = st.text_input("LinkedIn de la référence", placeholder="https://linkedin.com/in/...")

col4, col5 = st.columns([1, 2])
with col4:
    commercial = st.radio("Commercial Entourage", list(COMMERCIAUX.keys()), horizontal=False)

st.divider()

st.subheader("📝 Transcription / Synthèse")
st.caption("Colle ici ta transcription brute, tes notes ou une synthèse IA — Claude structure et met en forme.")

transcription = st.text_area(
    "Contenu de l'entretien",
    height=280,
    placeholder="""Exemple :
- Comment décrivez-vous ses qualités de manager ?
Il était vraiment très impliqué avec son équipe, capable de prendre des décisions difficiles rapidement...

Ou en texte libre :
Jean était un collaborateur exceptionnel chez nous pendant 3 ans. Il a dirigé une équipe de 8 personnes...""",
    label_visibility="collapsed"
)

st.divider()

champs_requis = [candidate_nom, reference_nom, transcription]
tous_remplis = all(c.strip() for c in champs_requis)

if not tous_remplis:
    st.warning("⚠️ Remplis le nom du candidat, de la référence et la transcription.")

if st.button("⚡ Générer la Prise de Références", type="primary", disabled=not tous_remplis):
    fields = {
        "candidate_nom": candidate_nom,
        "reference_nom": reference_nom,
        "reference_linkedin": reference_linkedin,
        "commercial": commercial,
    }
    with st.spinner("Claude structure l'entretien…"):
        try:
            sections_html = generate_reference_content(
                transcription=transcription,
                candidate_name=candidate_nom,
                reference_name=reference_nom,
            )
            final_html = build_reference_html(fields, sections_html)
            st.session_state.ref_html = final_html
            st.session_state.ref_sections = sections_html
            st.session_state.ref_fields = fields
            st.rerun()
        except Exception as e:
            st.error(f"Erreur lors de la génération : {e}")

# ---------------------------------------------------------------------------
# RÉSULTAT + MODIFICATION
# ---------------------------------------------------------------------------

if "ref_html" in st.session_state:
    st.divider()

    col1, col2, col3 = st.columns([2, 2, 6])
    with col1:
        st.components.v1.html(
            get_print_button_html(st.session_state.ref_html),
            height=50
        )
    with col2:
        if st.button("🗑️ Réinitialiser", use_container_width=True):
            for k in ["ref_html", "ref_sections", "ref_fields"]:
                st.session_state.pop(k, None)
            st.rerun()

    st.caption("💡 Cmd+P → Enregistrer en PDF · Décocher les en-têtes/pieds de page navigateur")

    with st.expander("✏️ Modifier le document", expanded=False):
        modification = st.text_area(
            "Demande de modification",
            placeholder="Ex : Ajoute une section sur son rapport à l'autorité. Reformule la recommandation en étant plus direct.",
            height=80,
            key="ref_modif"
        )
        if st.button("Appliquer la modification", key="btn_modif") and modification.strip():
            with st.spinner("Application de la modification…"):
                try:
                    new_sections = generate_reference_content(
                        transcription=transcription,
                        candidate_name=st.session_state.ref_fields["candidate_nom"],
                        reference_name=st.session_state.ref_fields["reference_nom"],
                        modification=modification,
                        previous_sections=st.session_state.ref_sections,
                    )
                    new_html = build_reference_html(st.session_state.ref_fields, new_sections)
                    st.session_state.ref_html = new_html
                    st.session_state.ref_sections = new_sections
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

    st.subheader("Aperçu")
    st.components.v1.html(st.session_state.ref_html, height=1400, scrolling=True)
