import streamlit as st
import anthropic
import base64
import os
import io
import re
import json
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

SECTIONS_PER_PAGE = 2

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

def get_logo_entourage():
    if st.session_state.get("logo_b64"):
        return st.session_state.logo_b64
    cached = load_logo_base64_cached()
    if cached:
        st.session_state.logo_b64 = cached
    return cached or ""

SYSTEM_PROMPT = """Tu es expert en recrutement de cadres dirigeants pour Entourage Recrutement.

Tu reçois une transcription libre ou une synthèse d'entretien de prise de références.

Retourne UNIQUEMENT un JSON valide (sans markdown, sans backticks) avec cette structure exacte :

{
  "sections": [
    {
      "theme": "TITRE DU THEME EN MAJUSCULES — Sous-question courte et percutante ?",
      "reponse": "Réponse détaillée avec les <strong>mots-clés importants en gras</strong>. Texte fluide, professionnel, rédigé à la troisième personne. Minimum 3-4 phrases."
    }
  ],
  "points_cles": ["Point fort court 1", "Point fort court 2", "Point fort court 3"],
  "vigilance": "Texte sur les points de vigilance ou null",
  "recommandation": "Phrase de recommandation globale synthétique et percutante",
  "citation": "La phrase la plus marquante de l'échange (20-35 mots)"
}

REGLES :
- Entre 5 et 7 sections thématiques bien distinctes — chaque section aborde un angle UNIQUE
- ZERO répétition entre sections : une information donnée dans une section ne doit PAS réapparaître ailleurs
- Réponses riches et détaillées — minimum 3-4 phrases par section, construites comme un paragraphe rédigé
- Mots-clés importants en strong (qualités, compétences, comportements observés, résultats concrets)
- Rédige à la 3ème personne (il/elle), ton professionnel et synthétique
- Si aucun point de vigilance : mettre null pour vigilance
- La recommandation doit être une conclusion synthétique et percutante — pas une répétition des sections
- Langue : français professionnel"""

def generate_reference_json(transcription, candidate_name, reference_name):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Candidat : {candidate_name}\nRéférence : {reference_name}\n\n---\n{transcription}\n---\n\nGénère le JSON."}]
    )
    text = message.content[0].text.strip()
    text = re.sub(r"^```[^\n]*\n", "", text)
    text = re.sub(r"\n```\s*$", "", text.strip())
    return json.loads(text)

def build_reference_html(fields, data):
    logo_b64 = get_logo_entourage()
    commercial = COMMERCIAUX[fields["commercial"]]
    date_str = datetime.date.today().strftime("%d/%m/%Y")

    logo_cover = (f'<img src="data:image/png;base64,{logo_b64}" style="height:18mm;max-width:100mm;object-fit:contain;">' if logo_b64 else '<span style="color:#FFD700;font-weight:800;font-size:13pt;">ENTOURAGE RECRUTEMENT</span>')

    linkedin_url = fields.get("reference_linkedin", "").strip()
    linkedin_html = (f'<a href="{linkedin_url}" target="_blank" style="color:#FFD700;font-size:7.5pt;">Voir le profil LinkedIn ↗</a>' if linkedin_url else "")

    initiales = "".join(w[0].upper() for w in fields["candidate_nom"].split()[:2])

    points_html = "".join(
        f'<li style="display:flex;align-items:flex-start;margin-bottom:3mm;font-size:8pt;line-height:1.4;"><span style="color:#FFD700;margin-right:2.5mm;font-size:9pt;flex-shrink:0;margin-top:1px;">✓</span><span style="color:#333;">{p}</span></li>'
        for p in data.get("points_cles", [])
    )

    def make_header():
        return f'''<header style="height:40mm;background:#000;display:flex;justify-content:space-between;align-items:center;padding:0 12mm;border-bottom:3mm solid #FFD700;flex-shrink:0;">{logo_cover}<div style="color:#FFD700;font-family:Manrope,sans-serif;font-weight:700;text-transform:uppercase;font-size:9pt;letter-spacing:2px;border:1px solid #FFD700;padding:5px 15px;">Prise de Références</div></header>'''

    def make_sidebar(show_citation=False):
        cit = ""
        if show_citation and data.get("citation"):
            cit = f'<div style="background:#000;border-left:3px solid #FFD700;padding:4mm;margin-top:4mm;"><div style="font-family:\'Playfair Display\',serif;font-style:italic;font-size:8pt;color:#fff;line-height:1.55;">&ldquo;{data["citation"]}&rdquo;</div></div>'
        return f'''<aside style="width:55mm;background:#F8F9FA;padding:8mm 5mm 8mm 7mm;border-right:1px solid #ddd;display:flex;flex-direction:column;gap:5mm;flex-shrink:0;overflow:hidden;">
          <div style="text-align:center;">
            <div style="width:18mm;height:18mm;border-radius:50%;background:#000;border:2px solid #FFD700;display:flex;align-items:center;justify-content:center;margin:0 auto 3mm auto;"><span style="font-family:\'Playfair Display\',serif;font-size:14pt;font-weight:700;color:#FFD700;">{initiales}</span></div>
            <div style="font-size:7.5pt;color:#777;font-style:italic;margin-top:1mm;">Candidat évalué</div>
          </div>
          <div>
            <div style="font-family:\'Playfair Display\',serif;color:#000;font-size:10pt;border-bottom:2px solid #FFD700;padding-bottom:1.5mm;margin-bottom:3mm;">La Référence</div>
            <div style="font-weight:700;color:#000;font-size:9pt;">{fields["reference_nom"]}</div>
            <div style="margin-top:1.5mm;">{linkedin_html}</div>
          </div>
          <div>
            <div style="font-family:\'Playfair Display\',serif;color:#000;font-size:10pt;border-bottom:2px solid #FFD700;padding-bottom:1.5mm;margin-bottom:3mm;">Points Clés</div>
            <ul style="list-style:none;padding:0;margin:0;">{points_html}</ul>
          </div>
          {cit}
          <div style="margin-top:auto;padding-top:4mm;border-top:1px solid #ddd;font-size:7pt;color:#aaa;line-height:1.6;">Entretien mené par<br><strong style="color:#555;">{fields["commercial"]}</strong><br>{date_str}</div>
        </aside>'''

    def make_footer(page, total):
        return f'''<footer style="height:15mm;background:#F8F9FA;border-top:1px solid #ddd;display:flex;justify-content:center;align-items:center;font-size:8.5pt;color:#555;flex-shrink:0;gap:6px;"><a href="{commercial["linkedin"]}" target="_blank" style="color:#000;font-weight:700;text-decoration:none;border-bottom:1.5px solid #FFD700;">{fields["commercial"]}</a>&nbsp;·&nbsp;{commercial["tel"]}&nbsp;&nbsp;|&nbsp;&nbsp;<a href="https://entouragerecrutement.com/" target="_blank" style="color:#000;font-weight:700;text-decoration:none;border-bottom:1.5px solid #FFD700;">Entourage Recrutement</a>&nbsp;&nbsp;·&nbsp;&nbsp;<span style="color:#bbb;">Page {page}/{total}</span></footer>'''

    # Page 1 couverture
    cover = f'''<div class="page">
      {make_header()}
      <div style="flex-grow:1;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:12mm 16mm;gap:10mm;">
        <div>
          <div style="font-family:\'Playfair Display\',serif;font-size:28pt;color:#000;padding:6mm 0 3mm;border-bottom:2px solid #FFD700;">Prise de Références</div>
          <div style="font-size:9pt;color:#999;text-transform:uppercase;letter-spacing:2px;margin-top:3mm;">Entretien confidentiel — Cabinet Entourage Recrutement</div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6mm;width:100%;max-width:155mm;">
          <div style="background:#f8f9fa;border-left:3px solid #FFD700;padding:6mm 8mm;text-align:left;">
            <div style="font-size:7pt;text-transform:uppercase;letter-spacing:1px;color:#999;font-weight:700;margin-bottom:2mm;">Candidat évalué</div>
            <div style="font-family:\'Playfair Display\',serif;font-size:14pt;color:#000;">{fields["candidate_nom"]}</div>
          </div>
          <div style="background:#f8f9fa;border-left:3px solid #000;padding:6mm 8mm;text-align:left;">
            <div style="font-size:7pt;text-transform:uppercase;letter-spacing:1px;color:#999;font-weight:700;margin-bottom:2mm;">Référence consultée</div>
            <div style="font-family:\'Playfair Display\',serif;font-size:14pt;color:#000;">{fields["reference_nom"]}</div>
            {"<div style='margin-top:2mm;'>" + linkedin_html + "</div>" if linkedin_html else ""}
          </div>
        </div>
        <div style="font-size:8pt;color:#bbb;">Entretien mené par <strong style="color:#555;">{fields["commercial"]}</strong> &nbsp;·&nbsp; {date_str}</div>
      </div>
      {make_footer(1, "—")}
    </div>'''

    # Préparer toutes les sections
    sections = list(data.get("sections", []))
    if data.get("vigilance"):
        sections.append({"theme": "⚠ POINTS DE VIGILANCE", "reponse": data["vigilance"], "_warning": True})
    if data.get("recommandation"):
        sections.append({"theme": "★ RECOMMANDATION GLOBALE", "reponse": data["recommandation"], "_reco": True})

    chunks = [sections[i:i+SECTIONS_PER_PAGE] for i in range(0, len(sections), SECTIONS_PER_PAGE)]
    total_pages = 1 + len(chunks)

    content_pages = ""
    for idx, chunk in enumerate(chunks):
        page_num = idx + 2
        secs_html = ""
        for sec in chunk:
            is_w = sec.get("_warning", False)
            is_r = sec.get("_reco", False)
            if is_w:
                dot_color = "#e74c3c"; border = "#e74c3c"; theme_c = "#c0392b"
            elif is_r:
                dot_color = "#FFD700"; border = "#FFD700"; theme_c = "#7a5c00"
            else:
                dot_color = "#FFD700"; border = "#e8e8e8"; theme_c = "#000"

            secs_html += f'''<div style="margin-bottom:8mm;">
              <div style="font-weight:800;font-size:8pt;text-transform:uppercase;letter-spacing:0.8px;color:{theme_c};margin-bottom:3mm;display:flex;align-items:flex-start;gap:3mm;">
                <span style="width:5mm;height:5mm;background:{dot_color};border-radius:50%;flex-shrink:0;display:inline-block;margin-top:0.5mm;"></span>
                <span>{sec["theme"]}</span>
              </div>
              <div style="font-size:9pt;line-height:1.7;color:#444;text-align:justify;padding-left:8mm;border-left:2px solid {border};">
                {sec["reponse"]}
              </div>
            </div>'''

        content_pages += f'''<div class="page">
          {make_header()}
          <div style="display:flex;flex:1;overflow:hidden;">
            {make_sidebar(show_citation=(idx==0))}
            <div style="flex:1;padding:9mm 12mm 6mm;overflow:hidden;display:flex;flex-direction:column;">
              <h1 style="font-family:\'Playfair Display\',serif;font-size:15pt;color:#000;margin-bottom:7mm;line-height:1.2;flex-shrink:0;">
                Synthèse de <span style="border-bottom:3px solid #FFD700;">l'entretien</span>
              </h1>
              {secs_html}
            </div>
          </div>
          {make_footer(page_num, total_pages)}
        </div>'''

    css = """<style>
      * { box-sizing:border-box; margin:0; padding:0; -webkit-print-color-adjust:exact; print-color-adjust:exact; }
      body { font-family:'Manrope',sans-serif; background:#555; display:flex; flex-direction:column; align-items:center; padding:40px 0; gap:24px; }
      .page { width:210mm; height:297mm; background:#fff; box-shadow:0 0 20px rgba(0,0,0,.5); display:flex; flex-direction:column; overflow:hidden; }
      @page { size: A4 portrait; margin: 0; }
      @media print {
        body { background:none; padding:0; gap:0; }
        .page { box-shadow:none; break-after:page; page-break-after:always; width:210mm; height:297mm; }
        .page:last-child { break-after:avoid; page-break-after:avoid; }
      }
    </style>"""

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Prise de Références — {fields["candidate_nom"]}</title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
{css}
</head>
<body>
{cover}
{content_pages}
</body>
</html>"""

def get_print_button_html(html_content, label="📄 Télécharger PDF"):
    b64 = base64.b64encode(html_content.encode("utf-8")).decode()
    return f"""<script>function printDoc(){{var w=window.open('','_blank');var bytes=Uint8Array.from(atob('{b64}'),function(c){{return c.charCodeAt(0)}});var html=new TextDecoder('utf-8').decode(bytes);w.document.open();w.document.write(html);w.document.close();w.onload=function(){{setTimeout(function(){{w.print()}},400)}}}}</script><button onclick="printDoc()" style="background:#000;color:#FFD700;border:none;padding:10px 18px;font-size:14px;font-weight:700;border-radius:6px;cursor:pointer;width:100%;font-family:sans-serif;letter-spacing:0.5px;">{label}</button>"""

# SIDEBAR
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

# UI
st.title("🔍 Prise de Références")
st.caption("Colle une transcription libre ou une synthèse → document structuré multi-pages généré automatiquement")
st.divider()

st.subheader("👤 Informations")
col1, col2, col3 = st.columns(3)
with col1:
    candidate_nom = st.text_input("Nom du candidat *", placeholder="Ex : Chloé Dupont")
with col2:
    reference_nom = st.text_input("Nom de la référence *", placeholder="Ex : Ana Meira Oliveira")
with col3:
    reference_linkedin = st.text_input("LinkedIn de la référence", placeholder="https://linkedin.com/in/...")

commercial = st.radio("Commercial Entourage", list(COMMERCIAUX.keys()), horizontal=True)
st.divider()

st.subheader("📝 Transcription ou Synthèse")
st.caption("Texte libre, notes d'appel, synthèse IA — Claude structure, rédige et met en forme.")
transcription = st.text_area("Contenu", height=300, placeholder="Colle ici ta transcription brute, tes notes ou une synthèse...", label_visibility="collapsed")
st.divider()

champs_ok = all(c.strip() for c in [candidate_nom, reference_nom, transcription])
if not champs_ok:
    st.warning("⚠️ Remplis le nom du candidat, de la référence et la transcription.")

if st.button("⚡ Générer la Prise de Références", type="primary", disabled=not champs_ok):
    fields = {"candidate_nom": candidate_nom.strip(), "reference_nom": reference_nom.strip(), "reference_linkedin": reference_linkedin.strip(), "commercial": commercial}
    with st.spinner("Claude analyse et structure l'entretien…"):
        try:
            data = generate_reference_json(transcription, candidate_nom, reference_nom)
            final_html = build_reference_html(fields, data)
            st.session_state.ref_html = final_html
            st.session_state.ref_data = data
            st.session_state.ref_fields = fields
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")

if "ref_html" in st.session_state:
    st.divider()
    col1, col2, col3 = st.columns([2, 2, 6])
    with col1:
        st.components.v1.html(get_print_button_html(st.session_state.ref_html), height=50)
    with col2:
        if st.button("🗑️ Réinitialiser", use_container_width=True):
            for k in ["ref_html", "ref_data", "ref_fields"]:
                st.session_state.pop(k, None)
            st.rerun()
    st.caption("💡 Cmd+P → Enregistrer en PDF · Décocher les en-têtes/pieds de page navigateur")

    with st.expander("✏️ Demander une modification", expanded=False):
        modif = st.text_area("Modification", height=80, placeholder="Ex : Reformule la recommandation. Ajoute une section sur son autonomie.", key="ref_modif")
        if st.button("Appliquer", key="btn_modif") and modif.strip():
            with st.spinner("Modification en cours…"):
                try:
                    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                    msg = client.messages.create(
                        model="claude-sonnet-4-6", max_tokens=4096, system=SYSTEM_PROMPT,
                        messages=[{"role": "user", "content": f"JSON actuel :\n{json.dumps(st.session_state.ref_data, ensure_ascii=False, indent=2)}\n\nModification : {modif}\n\nRetourne le JSON complet mis à jour."}]
                    )
                    text = msg.content[0].text.strip()
                    text = re.sub(r"^```[^\n]*\n", "", text)
                    text = re.sub(r"\n```\s*$", "", text.strip())
                    new_data = json.loads(text)
                    new_html = build_reference_html(st.session_state.ref_fields, new_data)
                    st.session_state.ref_html = new_html
                    st.session_state.ref_data = new_data
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

    st.subheader("Aperçu")
    st.components.v1.html(st.session_state.ref_html, height=1500, scrolling=True)
