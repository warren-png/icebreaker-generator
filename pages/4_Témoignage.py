import re
import streamlit as st
from dotenv import load_dotenv
from utils.auth import check_password
from testimonial_generator import analyze_testimonial, create_testimonial_pdf

load_dotenv()

st.set_page_config(
    page_title="Témoignage | Biz Dev Entourage",
    page_icon="⭐",
    layout="wide"
)

# — Authentification —
if not check_password():
    st.stop()


def sanitize_text(text, max_length=2000):
    if not text or not isinstance(text, str):
        return ""
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text[:max_length]


st.header("⭐ Témoignage Client — Génération PDF")
st.caption("Collez les réponses du client, uploadez les logos — le PDF est prêt en 10 secondes.")

# ── LOGOS ──────────────────────────────────────────────────────
col_logo1, col_logo2 = st.columns(2)
with col_logo1:
    logo_er = st.file_uploader("Logo Entourage Recrutement", type=["png", "jpg", "jpeg"], key="t_logo_er")
with col_logo2:
    logo_client = st.file_uploader("Logo client", type=["png", "jpg", "jpeg"], key="t_logo_client")

st.divider()

# ── INFOS CONTACT ──────────────────────────────────────────────
st.subheader("👤 Contact client")
col_a, col_b, col_c = st.columns(3)
with col_a:
    t_prenom_nom = st.text_input("Prénom Nom", placeholder="Marie Dupont", key="t_prenom_nom")
with col_b:
    t_poste_contact = st.text_input("Titre / Poste", placeholder="Directrice Financière", key="t_poste_contact")
with col_c:
    t_entreprise = st.text_input("Entreprise", placeholder="Nom de l'entreprise", key="t_entreprise")

st.subheader("📋 Le Mandat")
col_d, col_e, col_f = st.columns(3)
with col_d:
    t_poste_recrute = st.text_input("Poste recruté", placeholder="Contrôleur de Gestion Senior", key="t_poste_recrute")
with col_e:
    t_secteur = st.text_input("Secteur", placeholder="Data / Tech", key="t_secteur")
with col_f:
    t_contexte = st.text_input("Contexte (court)", placeholder="Croissance rapide, scale-up", key="t_contexte")

st.divider()

# ── RÉPONSES CLIENT ────────────────────────────────────────────
st.subheader("💬 Réponses du client")

Q1_LABEL = "Contexte du recrutement et difficultés rencontrées avant notre intervention ?"
Q2_LABEL = "Comment définiriez-vous votre relation avec le cabinet et la qualité des intervenants ?"
Q3_LABEL = "Recommanderiez-vous Entourage Recrutement à d'autres entreprises ? Pourquoi ?"

t_q1 = st.text_area(
    f"Q1 — {Q1_LABEL}",
    height=140,
    key="t_q1",
    placeholder="Réponse du client..."
)
t_q2 = st.text_area(
    f"Q2 — {Q2_LABEL}",
    height=120,
    key="t_q2",
    placeholder="Réponse du client..."
)
t_q3 = st.text_area(
    f"Q3 — {Q3_LABEL}",
    height=120,
    key="t_q3",
    placeholder="Réponse du client..."
)

st.divider()

# ── GÉNÉRATION ─────────────────────────────────────────────────
if st.button("✨ GÉNÉRER LE PDF TÉMOIGNAGE", type="primary", use_container_width=True):

    missing = []
    if not t_prenom_nom:
        missing.append("Prénom Nom")
    if not t_entreprise:
        missing.append("Entreprise")
    if not t_poste_recrute:
        missing.append("Poste recruté")
    if not t_q1.strip():
        missing.append("Réponse Q1")
    if not t_q2.strip():
        missing.append("Réponse Q2")
    if not t_q3.strip():
        missing.append("Réponse Q3")

    if missing:
        st.error(f"Champs obligatoires manquants : {', '.join(missing)}")
        st.stop()

    q1_clean = sanitize_text(t_q1)
    q2_clean = sanitize_text(t_q2)
    q3_clean = sanitize_text(t_q3)

    with st.spinner("Analyse IA en cours (extraction citation, titre, points clés)..."):
        try:
            ai = analyze_testimonial(
                q1=q1_clean,
                q2=q2_clean,
                q3=q3_clean,
                poste_recrute=t_poste_recrute or "Non précisé",
                secteur=t_secteur or "Non précisé",
                contexte=t_contexte or "Non précisé",
            )
            st.success("Analyse IA terminée")
        except Exception as e:
            st.error(f"Erreur analyse IA : {e}")
            st.stop()

    with st.expander("Éléments extraits par Claude (modifiables avant génération)", expanded=True):
        ai['titre_principal'] = st.text_input("Titre principal", value=ai.get('titre_principal', ''), key="t_titre")
        ai['citation_choc']   = st.text_input("Citation mise en avant", value=ai.get('citation_choc', ''), key="t_citation")
        pts = ai.get('points_cles', ['', '', ''])
        ai['points_cles'] = [
            st.text_input("Point clé 1", value=pts[0] if len(pts) > 0 else '', key="t_pt1"),
            st.text_input("Point clé 2", value=pts[1] if len(pts) > 1 else '', key="t_pt2"),
            st.text_input("Point clé 3", value=pts[2] if len(pts) > 2 else '', key="t_pt3"),
        ]

    with st.spinner("Génération du PDF..."):
        try:
            data = {
                'prenom_nom':      t_prenom_nom,
                'poste_contact':   t_poste_contact or "",
                'entreprise':      t_entreprise,
                'poste_recrute':   t_poste_recrute or "Non précisé",
                'secteur':         t_secteur or "Non précisé",
                'contexte':        t_contexte or "Non précisé",
                'q1_label':        Q1_LABEL,
                'q1':              q1_clean,
                'q2_label':        Q2_LABEL,
                'q2':              q2_clean,
                'q3_label':        Q3_LABEL,
                'q3':              q3_clean,
                'titre_principal': ai.get('titre_principal', 'Témoignage client'),
                'titre_surligne':  ai.get('titre_surligne', ''),
                'citation_choc':   ai.get('citation_choc', ''),
                'points_cles':     ai.get('points_cles', ['', '', '']),
            }

            logo_er_bytes     = logo_er.read()     if logo_er     else None
            logo_client_bytes = logo_client.read() if logo_client else None

            pdf_bytes = create_testimonial_pdf(data, logo_er_bytes, logo_client_bytes)
            st.success("PDF généré avec succès !")

        except Exception as e:
            st.error(f"Erreur génération PDF : {e}")
            st.stop()

    filename = f"temoignage_{t_entreprise.replace(' ', '_').lower()}.pdf"
    st.download_button(
        label="Télécharger le PDF",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
        use_container_width=True,
    )
