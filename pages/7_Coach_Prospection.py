"""
Page Coach Prospection — assistant IA qui s'appuie sur le corpus du coaching
Jim Breton pour répondre aux questions, générer des matrices d'appel, et
débriefer des appels (audio ou texte).
"""

import os
import sys
import re
import datetime
import anthropic
import streamlit as st

# Permet d'importer coach_prospection.* quand Streamlit lance le fichier
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.auth import check_password
from utils.ui import inject_global_styles
from coach_prospection.corpus_loader import (
    load_corpus_text,
    corpus_stats,
    ensure_corpus_present,
)
from coach_prospection.prompts import (
    SYSTEM_PROMPT_QUESTIONS,
    SYSTEM_PROMPT_MATRICE,
    SYSTEM_PROMPT_DEBRIEF,
    build_system_with_corpus,
)
from coach_prospection.transcription import (
    transcribe_audio_file,
    compute_speaking_time_share,
    TranscriptionError,
)
from coach_prospection.exporters import markdown_to_docx, markdown_to_pdf


st.set_page_config(
    page_title="Coach Prospection | Entourage",
    page_icon="🎯",
    layout="wide",
)

inject_global_styles()

# ─────────────────────────────────────────────────────────────────────────────
# Styles spécifiques à la page (registre exécutif, accent or sobre)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
      .cp-header {
          background: linear-gradient(180deg, #0A0A0A 0%, #181818 100%);
          color: #fff;
          padding: 24px 32px;
          border-radius: 6px;
          margin-bottom: 22px;
          border-left: 4px solid #C9A227;
      }
      .cp-header h1 {
          color: #fff !important;
          font-family: 'Playfair Display', serif !important;
          font-weight: 700 !important;
          font-size: 28pt !important;
          margin: 0 0 6px 0 !important;
          padding: 0 !important;
          letter-spacing: -0.5px !important;
      }
      .cp-header h1::after { display: none !important; }
      .cp-header .cp-tagline {
          color: #C9A227;
          text-transform: uppercase;
          letter-spacing: 2px;
          font-size: 9pt;
          font-weight: 700;
          margin-bottom: 10px;
      }
      .cp-header .cp-subtitle {
          color: #d8d8d8;
          font-size: 11pt;
          font-weight: 400;
          line-height: 1.5;
          max-width: 760px;
      }
      .cp-section-title {
          font-family: 'Playfair Display', serif;
          font-size: 18pt;
          color: #0A0A0A;
          margin: 6px 0 4px 0;
          padding-bottom: 6px;
          border-bottom: 1.5px solid #C9A227;
          display: inline-block;
      }
      .cp-helper {
          color: #5a5a5a;
          font-size: 10.5pt;
          margin: 4px 0 18px 0;
          max-width: 720px;
      }
      .cp-result-frame {
          background: #FAFAF8;
          border-left: 3px solid #C9A227;
          padding: 18px 26px;
          border-radius: 4px;
          margin-top: 8px;
      }
      .cp-meta {
          color: #888;
          font-size: 9pt;
          margin-top: 12px;
          font-style: italic;
      }
      .stTabs [data-baseweb="tab-list"] {
          gap: 6px;
          border-bottom: 1px solid #e5e5e5;
      }
      .stTabs [data-baseweb="tab"] {
          padding: 10px 18px;
          font-weight: 600;
          font-size: 10.5pt;
          color: #555;
      }
      .stTabs [aria-selected="true"] {
          color: #0A0A0A !important;
          border-bottom: 3px solid #C9A227 !important;
      }
      div[data-testid="stDownloadButton"] button {
          background: #0A0A0A;
          color: #fff;
          border: 1px solid #0A0A0A;
          font-weight: 600;
          font-size: 10pt;
          letter-spacing: 0.3px;
      }
      div[data-testid="stDownloadButton"] button:hover {
          background: #C9A227;
          border-color: #C9A227;
          color: #0A0A0A;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

if not check_password():
    st.stop()


MODEL = "claude-sonnet-4-6"
MAX_TOKENS_RESPONSE = 4096


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


@st.cache_data(ttl=86400, show_spinner="Initialisation du corpus du coach…")
def ensure_corpus_ready() -> dict:
    return ensure_corpus_present()


@st.cache_data(show_spinner=False)
def get_corpus() -> str:
    return load_corpus_text()


@st.cache_data(show_spinner=False)
def get_corpus_stats() -> dict:
    return corpus_stats()


def get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("ANTHROPIC_API_KEY manquante dans l'environnement.")
        st.stop()
    return anthropic.Anthropic(api_key=api_key)


def call_claude(system_prompt: str, messages: list[dict]) -> tuple[str, dict]:
    """Appel Claude avec le corpus mis en cache (prompt caching ephemeral)."""
    corpus = get_corpus()
    if not corpus:
        st.error("Corpus du coach indisponible. Vérifiez la connexion Google Drive.")
        st.stop()
    system_blocks = build_system_with_corpus(system_prompt, corpus)
    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS_RESPONSE,
        system=system_blocks,
        messages=messages,
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    usage = response.usage
    cache_info = {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_creation": getattr(usage, "cache_creation_input_tokens", 0),
        "cache_read": getattr(usage, "cache_read_input_tokens", 0),
    }
    return text, cache_info


def _slug(text: str, max_len: int = 50) -> str:
    text = re.sub(r"[^\w\s-]", "", text or "", flags=re.UNICODE).strip()
    text = re.sub(r"[-\s]+", "_", text)
    return (text or "doc")[:max_len]


def render_download_pair(content_md: str, basename: str, title: str, subtitle: str | None = None):
    """Affiche deux boutons côte à côte : DOCX et PDF."""
    col_a, col_b = st.columns(2)
    today = datetime.date.today().isoformat()
    with col_a:
        try:
            docx_bytes = markdown_to_docx(content_md, title=title, subtitle=subtitle)
            st.download_button(
                "Télécharger en Word",
                data=docx_bytes,
                file_name=f"{basename}_{today}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        except Exception as e:
            st.warning(f"Word indisponible : {e}")
    with col_b:
        try:
            pdf_bytes = markdown_to_pdf(content_md, title=title, subtitle=subtitle)
            st.download_button(
                "Télécharger en PDF",
                data=pdf_bytes,
                file_name=f"{basename}_{today}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.warning(f"PDF indisponible : {e}")


def render_cache_info(cache_info: dict):
    st.markdown(
        f"<div class='cp-meta'>Cache : {cache_info['cache_read']:,} tokens lus · "
        f"{cache_info['cache_creation']:,} créés · "
        f"{cache_info['output_tokens']:,} générés</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="cp-header">
      <div class="cp-tagline">Module exécutif · Coach Prospection</div>
      <h1>Préparer, exécuter, débriefer.</h1>
      <div class="cp-subtitle">
        Assistant fondé sur la méthode commerciale enseignée par Jim Breton,
        appliquée à la chasse de cadres dirigeants. Les livrables sont produits
        en Word et PDF, prêts à être partagés.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Vérification corpus
corpus_ready = ensure_corpus_ready()
if corpus_ready["source"] == "empty":
    st.error(
        "Corpus du coach indisponible. En local : "
        "`python -m coach_prospection.fetch_notion <URL_NOTION>` puis "
        "`python -m coach_prospection.drive_sync upload`."
    )
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Onglets
# ─────────────────────────────────────────────────────────────────────────────

tab_questions, tab_matrice, tab_audio, tab_texte = st.tabs(
    [
        "Questions au coach",
        "Préparation d'appel",
        "Débrief — audio",
        "Débrief — texte",
    ]
)


# ─── Onglet 1 — Questions au coach ──────────────────────────────────────────
with tab_questions:
    st.markdown('<div class="cp-section-title">Consultation libre</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="cp-helper">Posez une question stratégique. La réponse est synthétique '
        '(réponse directe, principe sous-jacent, mise en application immédiate).</div>',
        unsafe_allow_html=True,
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Votre question (ex : comment ouvrir un appel sur un DAF d'ETI ?)")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("_Analyse en cours…_")
            try:
                response_text, cache_info = call_claude(
                    SYSTEM_PROMPT_QUESTIONS,
                    [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.chat_history
                    ],
                )
                placeholder.markdown(response_text)
                render_cache_info(cache_info)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": response_text}
                )
            except Exception as e:
                placeholder.error(f"Erreur : {e}")

    if st.session_state.chat_history:
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Effacer la conversation", key="clear_chat"):
                st.session_state.chat_history = []
                st.rerun()
        with col2:
            # Export de la conversation entière
            full_md = "\n\n".join(
                f"### {'Question' if m['role']=='user' else 'Réponse du coach'}\n\n{m['content']}"
                for m in st.session_state.chat_history
            )
            render_download_pair(
                full_md,
                basename="consultation_coach",
                title="Consultation Coach Prospection",
                subtitle="Synthèse des échanges",
            )


# ─── Onglet 2 — Préparation d'appel ─────────────────────────────────────────
with tab_matrice:
    st.markdown('<div class="cp-section-title">Note de préparation d\'appel</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="cp-helper">Renseignez le prospect. Vous obtenez une note structurée '
        'spécifique à ce contact : lecture stratégique, angle d\'ouverture, verbatims prêts, '
        'questions de qualification, anticipation d\'objections.</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        prospect_nom = st.text_input("Nom du prospect", placeholder="Ex : Marie Dupont")
        prospect_poste = st.text_input("Fonction", placeholder="Ex : DAF, CTO, Directrice des talents…")
    with col2:
        prospect_entreprise = st.text_input("Entreprise", placeholder="Ex : Acme Corp")
        prospect_secteur = st.text_input("Secteur / contexte", placeholder="Ex : ETI tech 200 M€ CA")

    declencheur = st.text_area(
        "Signal de déclenchement (actualité, profil LinkedIn, élément récent)",
        placeholder=(
            "Ex : a publié il y a une semaine sur la difficulté à recruter des ingénieurs seniors ; "
            "entreprise en levée de fonds Series B"
        ),
        height=110,
    )
    objectif = st.text_input(
        "Objectif spécifique de l'appel (facultatif)",
        placeholder="Ex : qualifier un besoin sur 2 à 3 postes tech grands comptes",
    )

    disabled = not (prospect_poste and prospect_entreprise)
    if st.button("Générer la note de préparation", type="primary", disabled=disabled):
        contexte = f"""Contexte du prospect :
- Nom : {prospect_nom or 'non précisé'}
- Fonction : {prospect_poste}
- Entreprise : {prospect_entreprise}
- Secteur / contexte : {prospect_secteur or 'non précisé'}
- Signal de déclenchement : {declencheur or 'aucun signal explicite'}
- Objectif spécifique : {objectif or 'qualifier le besoin et établir une conversation à valeur'}

Produis la note de préparation selon la méthode du coach."""
        with st.spinner("Élaboration de la note de préparation…"):
            try:
                response_text, cache_info = call_claude(
                    SYSTEM_PROMPT_MATRICE,
                    [{"role": "user", "content": contexte}],
                )
                st.markdown('<div class="cp-result-frame">', unsafe_allow_html=True)
                st.markdown(response_text)
                st.markdown('</div>', unsafe_allow_html=True)
                render_cache_info(cache_info)
                render_download_pair(
                    response_text,
                    basename=f"preparation_{_slug(prospect_entreprise)}",
                    title=f"Préparation d'appel — {prospect_entreprise}",
                    subtitle=f"{prospect_nom or prospect_poste} · {prospect_secteur or ''}",
                )
            except Exception as e:
                st.error(f"Erreur : {e}")


# ─── Onglet 3 — Débrief audio ───────────────────────────────────────────────
with tab_audio:
    st.markdown('<div class="cp-section-title">Débrief d\'appel — fichier audio</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="cp-helper">Déposez un enregistrement (M4A, MP3, WAV, MP4). '
        'L\'audio est transcrit avec identification des locuteurs, puis analysé selon '
        'la matrice de lecture officielle du coach (5 critères, décision GO / NO GO).</div>',
        unsafe_allow_html=True,
    )

    audio_file = st.file_uploader(
        "Enregistrement audio",
        type=["m4a", "mp3", "wav", "mp4", "ogg", "webm", "flac"],
        accept_multiple_files=False,
        label_visibility="collapsed",
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        commercial_nom = st.selectbox(
            "Commercial",
            options=["Warren Elbaz", "Helder Alturas", "Autre"],
            index=0,
        )
    with col2:
        contexte_appel = st.text_input(
            "Contexte (facultatif)",
            placeholder="Ex : cold call sur DAF d'ETI, 1er contact, objectif qualifier",
        )

    if audio_file is not None and st.button("Transcrire et débriefer", type="primary"):
        if not os.getenv("ASSEMBLYAI_API_KEY"):
            st.error("ASSEMBLYAI_API_KEY manquante.")
        else:
            file_bytes = audio_file.read()
            progress_placeholder = st.empty()
            try:
                progress_placeholder.info("Étape 1/2 — Transcription en cours…")
                result = transcribe_audio_file(
                    file_bytes,
                    filename=audio_file.name,
                    progress_callback=lambda m: progress_placeholder.info(m),
                )
            except TranscriptionError as e:
                progress_placeholder.error(f"Transcription échouée : {e}")
                st.stop()
            except Exception as e:
                progress_placeholder.error(f"Erreur inattendue : {e}")
                st.stop()

            duration_min = result["duration_seconds"] / 60 if result["duration_seconds"] else 0
            share = compute_speaking_time_share(result["utterances"])
            progress_placeholder.success(
                f"Transcription terminée — {duration_min:.1f} min, "
                f"{result['speakers_count']} locuteurs."
            )

            with st.expander("Voir la retranscription complète"):
                st.text(result["formatted_text"])
                if share:
                    st.write("**Temps de parole :**")
                    for spk, pct in share.items():
                        st.write(f"- Speaker {spk} : {pct} %")

            with st.spinner("Étape 2/2 — Analyse selon la matrice du coach…"):
                share_text = ""
                if share:
                    share_text = "\nRépartition temps de parole : " + ", ".join(
                        f"Speaker {s} = {p}%" for s, p in share.items()
                    )
                user_msg = f"""Commercial : {commercial_nom}
Contexte : {contexte_appel or 'non précisé'}
Durée : {duration_min:.1f} min{share_text}

=== RETRANSCRIPTION ===
{result['formatted_text']}
=== FIN RETRANSCRIPTION ===

Produis le débrief selon la matrice du coach."""
                try:
                    response_text, cache_info = call_claude(
                        SYSTEM_PROMPT_DEBRIEF,
                        [{"role": "user", "content": user_msg}],
                    )
                    st.markdown("---")
                    st.markdown('<div class="cp-section-title">Débrief</div>', unsafe_allow_html=True)
                    st.markdown('<div class="cp-result-frame">', unsafe_allow_html=True)
                    st.markdown(response_text)
                    st.markdown('</div>', unsafe_allow_html=True)
                    render_cache_info(cache_info)
                    render_download_pair(
                        response_text,
                        basename=f"debrief_{_slug(commercial_nom)}",
                        title=f"Débrief d'appel — {commercial_nom}",
                        subtitle=contexte_appel or f"Appel du {datetime.date.today().strftime('%d/%m/%Y')}",
                    )
                except Exception as e:
                    st.error(f"Erreur d'analyse : {e}")


# ─── Onglet 4 — Débrief texte ───────────────────────────────────────────────
with tab_texte:
    st.markdown('<div class="cp-section-title">Débrief d\'appel — retranscription texte</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="cp-helper">Si vous disposez déjà d\'une retranscription (Otter, Notta, Tella, Claap…), '
        'collez-la ici pour obtenir un débrief immédiat selon la matrice du coach.</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        commercial_nom_2 = st.selectbox(
            "Commercial",
            options=["Warren Elbaz", "Helder Alturas", "Autre"],
            index=0,
            key="commercial_select_2",
        )
    with col2:
        contexte_appel_2 = st.text_input(
            "Contexte (facultatif)",
            placeholder="Ex : cold call sur DAF d'ETI, 1er contact",
            key="contexte_2",
        )

    transcription_collee = st.text_area(
        "Retranscription complète",
        height=320,
        placeholder=(
            "Speaker A : Bonjour Marie, ici Warren d'Entourage Recrutement, vous avez deux minutes ?\n"
            "Speaker B : ..."
        ),
    )

    if st.button("Débriefer", type="primary", disabled=not transcription_collee.strip()):
        with st.spinner("Analyse selon la matrice du coach…"):
            user_msg = f"""Commercial : {commercial_nom_2}
Contexte : {contexte_appel_2 or 'non précisé'}

=== RETRANSCRIPTION ===
{transcription_collee}
=== FIN RETRANSCRIPTION ===

Produis le débrief selon la matrice du coach."""
            try:
                response_text, cache_info = call_claude(
                    SYSTEM_PROMPT_DEBRIEF,
                    [{"role": "user", "content": user_msg}],
                )
                st.markdown("---")
                st.markdown('<div class="cp-section-title">Débrief</div>', unsafe_allow_html=True)
                st.markdown('<div class="cp-result-frame">', unsafe_allow_html=True)
                st.markdown(response_text)
                st.markdown('</div>', unsafe_allow_html=True)
                render_cache_info(cache_info)
                render_download_pair(
                    response_text,
                    basename=f"debrief_{_slug(commercial_nom_2)}",
                    title=f"Débrief d'appel — {commercial_nom_2}",
                    subtitle=contexte_appel_2 or f"Appel du {datetime.date.today().strftime('%d/%m/%Y')}",
                )
            except Exception as e:
                st.error(f"Erreur : {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — état du corpus (discret)
# ─────────────────────────────────────────────────────────────────────────────
stats = get_corpus_stats()
with st.sidebar:
    st.markdown("### Corpus du coach")
    if stats["files_count"] == 0:
        st.error("Aucun fichier")
    else:
        st.caption(
            f"{stats['files_count']} fichiers · "
            f"≈ {stats['estimated_tokens']/1000:.0f}k tokens"
        )
        with st.expander("Détail"):
            for fname in stats["filenames"]:
                st.caption(f"• {fname}")
        st.markdown("---")
        if st.button("Mettre à jour le corpus", use_container_width=True):
            # Force le re-téléchargement depuis Drive et vide les caches
            import shutil
            from coach_prospection.corpus_loader import CORPUS_DIR

            if CORPUS_DIR.exists():
                shutil.rmtree(CORPUS_DIR)
            ensure_corpus_ready.clear()
            get_corpus.clear()
            get_corpus_stats.clear()
            st.success("Corpus rechargé depuis Google Drive.")
            st.rerun()
        st.caption(
            "À cliquer après avoir poussé une nouvelle version du corpus "
            "sur Drive (`drive_sync upload`)."
        )
