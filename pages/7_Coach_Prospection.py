"""
Page Coach Prospection — assistant IA qui s'appuie sur le corpus du coaching
Jim Breton pour répondre aux questions, générer des matrices d'appel, et
débriefer des appels (audio ou texte).
"""

import os
import sys
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


st.set_page_config(
    page_title="Coach Prospection | Entourage",
    page_icon="🎯",
    layout="wide",
)

inject_global_styles()

if not check_password():
    st.stop()


MODEL = "claude-sonnet-4-6"
MAX_TOKENS_RESPONSE = 4096


@st.cache_data(ttl=86400, show_spinner="📥 Téléchargement du corpus du coach…")
def ensure_corpus_ready() -> dict:
    """Garantit la présence du corpus (local ou téléchargé depuis Drive).

    Mis en cache 24h pour éviter de re-télécharger à chaque rerun Streamlit.
    """
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
        st.error("ANTHROPIC_API_KEY manquante dans le .env.")
        st.stop()
    return anthropic.Anthropic(api_key=api_key)


def call_claude(system_prompt: str, messages: list[dict]) -> str:
    """Appel Claude avec le corpus mis en cache (prompt caching ephemeral)."""
    corpus = get_corpus()
    if not corpus:
        st.error(
            "Corpus du coach introuvable. Lance d'abord :\n\n"
            "`python -m coach_prospection.fetch_notion <URL_NOTION>`"
        )
        st.stop()
    system_blocks = build_system_with_corpus(system_prompt, corpus)
    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS_RESPONSE,
        system=system_blocks,
        messages=messages,
    )
    # Récupère le texte ET les stats de cache pour affichage
    text = "".join(block.text for block in response.content if block.type == "text")
    usage = response.usage
    cache_info = {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_creation": getattr(usage, "cache_creation_input_tokens", 0),
        "cache_read": getattr(usage, "cache_read_input_tokens", 0),
    }
    return text, cache_info


# =============================================================================
# Header + sidebar
# =============================================================================

st.title("🎯 Coach Prospection")
st.caption(
    "Assistant IA qui maîtrise la méthode commerciale de Jim Breton et qui "
    "t'aide à préparer, exécuter, et débriefer tes appels de prospection."
)

# Garantit que le corpus est présent (download depuis Drive en prod si besoin)
corpus_ready = ensure_corpus_ready()
if corpus_ready["source"] == "empty":
    st.error(
        "📚 Corpus du coach introuvable.\n\n"
        "En **local** : `python -m coach_prospection.fetch_notion <URL_NOTION>`\n\n"
        "Puis upload sur Drive : `python -m coach_prospection.drive_sync upload`"
    )
    st.stop()

stats = get_corpus_stats()
with st.sidebar:
    st.subheader("📚 Corpus du coach")
    if stats["files_count"] == 0:
        st.error(
            "Aucun fichier dans `coach_prospection/corpus/`.\n\n"
            "Lance le fetcher :\n```\npython -m coach_prospection.fetch_notion <URL>\n```"
        )
    else:
        st.metric("Fichiers", stats["files_count"])
        st.metric("Taille", f"{stats['total_chars']/1000:.0f}k car.")
        st.metric("≈ Tokens", f"{stats['estimated_tokens']/1000:.0f}k")
        with st.expander("Voir les fichiers"):
            for fname in stats["filenames"]:
                st.write(f"• {fname}")


# =============================================================================
# Onglets
# =============================================================================

tab_questions, tab_matrice, tab_audio, tab_texte = st.tabs(
    [
        "💬 Questions au coach",
        "📋 Matrice d'appel",
        "🎙️ Débrief d'appel (audio)",
        "📝 Débrief d'appel (texte)",
    ]
)


# -----------------------------------------------------------------------------
# Onglet 1 — Questions libres
# -----------------------------------------------------------------------------
with tab_questions:
    st.subheader("Poser une question au coach")
    st.caption(
        "Le coach répond depuis sa méthode (Menu of Pain, conséquences émotionnelles, "
        "Permission-Based Opener, etc.). Tes échanges sont gardés dans cette session."
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Afficher l'historique
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ta question (ex : comment ouvrir un cold call sur un DAF ?)")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("_Le coach réfléchit…_")
            try:
                response_text, cache_info = call_claude(
                    SYSTEM_PROMPT_QUESTIONS,
                    [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.chat_history
                    ],
                )
                placeholder.markdown(response_text)
                st.caption(
                    f"💾 Cache : {cache_info['cache_read']} tokens lus du cache · "
                    f"{cache_info['cache_creation']} créés · "
                    f"{cache_info['output_tokens']} générés"
                )
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": response_text}
                )
            except Exception as e:
                placeholder.error(f"Erreur : {e}")

    if st.session_state.chat_history:
        if st.button("🗑️ Effacer la conversation", key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()


# -----------------------------------------------------------------------------
# Onglet 2 — Matrice d'appel
# -----------------------------------------------------------------------------
with tab_matrice:
    st.subheader("Générer une matrice d'appel")
    st.caption(
        "Fournis le contexte du prospect, l'IA produit un script structuré "
        "(préparation, 20 premières secondes, qualification, objections, conclusion)."
    )

    col1, col2 = st.columns(2)
    with col1:
        prospect_nom = st.text_input("Nom du prospect", placeholder="Ex : Marie Dupont")
        prospect_poste = st.text_input("Poste", placeholder="Ex : DAF, CTO, Head of Talent…")
    with col2:
        prospect_entreprise = st.text_input("Entreprise", placeholder="Ex : Acme Corp")
        prospect_secteur = st.text_input("Secteur / contexte", placeholder="Ex : ETI tech 200M€ CA")

    declencheur = st.text_area(
        "Déclencheur de l'appel (signaux faibles, actu récente, profil LinkedIn…)",
        placeholder=(
            "Ex : a posté la semaine dernière sur la difficulté à recruter des "
            "ingénieurs seniors ; entreprise en levée de fonds Series B"
        ),
        height=100,
    )
    objectif = st.text_input(
        "Objectif spécifique de cet appel (facultatif)",
        placeholder="Ex : qualifier un besoin sur 2-3 postes Tech grands comptes",
    )

    if st.button("📋 Générer la matrice", type="primary", disabled=not (prospect_poste and prospect_entreprise)):
        contexte = f"""Contexte du prospect :
- Nom : {prospect_nom or 'non précisé'}
- Poste : {prospect_poste}
- Entreprise : {prospect_entreprise}
- Secteur / contexte : {prospect_secteur or 'non précisé'}
- Déclencheur : {declencheur or 'pas de déclencheur identifié'}
- Objectif spécifique : {objectif or 'qualifier, engager une conversation à valeur'}

Génère la matrice d'appel selon la méthode du coach."""
        with st.spinner("Génération de la matrice…"):
            try:
                response_text, cache_info = call_claude(
                    SYSTEM_PROMPT_MATRICE,
                    [{"role": "user", "content": contexte}],
                )
                st.markdown(response_text)
                st.caption(
                    f"💾 Cache : {cache_info['cache_read']} tokens lus · "
                    f"{cache_info['output_tokens']} générés"
                )
                st.download_button(
                    "💾 Télécharger la matrice (.md)",
                    data=response_text,
                    file_name=f"matrice_{prospect_entreprise.replace(' ', '_')}_{datetime.date.today()}.md",
                    mime="text/markdown",
                )
            except Exception as e:
                st.error(f"Erreur : {e}")


# -----------------------------------------------------------------------------
# Onglet 3 — Débrief d'appel (audio)
# -----------------------------------------------------------------------------
with tab_audio:
    st.subheader("Débrief d'un appel — audio")
    st.caption(
        "Upload un enregistrement (M4A du dictaphone Mac/iPhone, MP3, WAV, MP4). "
        "AssemblyAI transcrit avec diarisation (qui parle quand), puis l'IA analyse "
        "selon la grille du coach."
    )

    audio_file = st.file_uploader(
        "Enregistrement audio",
        type=["m4a", "mp3", "wav", "mp4", "ogg", "webm", "flac"],
        accept_multiple_files=False,
    )
    commercial_nom = st.selectbox(
        "Qui était le commercial ?",
        options=["Warren Elbaz", "Helder Alturas", "Autre"],
        index=0,
    )
    contexte_appel = st.text_area(
        "Contexte de l'appel (facultatif — aide l'IA à interpréter)",
        placeholder="Ex : cold call sur un DAF d'ETI, 1er contact, objectif qualifier",
        height=80,
    )

    if audio_file is not None and st.button("🎙️ Transcrire et débriefer", type="primary"):
        if not os.getenv("ASSEMBLYAI_API_KEY"):
            st.error("ASSEMBLYAI_API_KEY manquante dans le .env.")
        else:
            file_bytes = audio_file.read()
            progress_placeholder = st.empty()
            try:
                progress_placeholder.info("⏳ Étape 1/2 — Transcription AssemblyAI…")
                result = transcribe_audio_file(
                    file_bytes,
                    filename=audio_file.name,
                    progress_callback=lambda m: progress_placeholder.info(f"⏳ {m}"),
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
                f"✅ Transcription terminée — {duration_min:.1f} min, "
                f"{result['speakers_count']} locuteurs détectés."
            )

            with st.expander("📜 Voir la retranscription complète"):
                st.text(result["formatted_text"])
                if share:
                    st.write("**Temps de parole :**")
                    for spk, pct in share.items():
                        st.write(f"- Speaker {spk} : {pct}%")
                st.download_button(
                    "💾 Télécharger la retranscription (.txt)",
                    data=result["formatted_text"],
                    file_name=f"transcription_{audio_file.name}.txt",
                    mime="text/plain",
                )

            # Étape 2 : envoi à Claude pour analyse
            with st.spinner("🧠 Étape 2/2 — Analyse par le coach…"):
                share_text = ""
                if share:
                    share_text = "\nRépartition temps de parole : " + ", ".join(
                        f"Speaker {s}={p}%" for s, p in share.items()
                    )
                user_msg = f"""Commercial : {commercial_nom}
Contexte : {contexte_appel or 'non précisé'}
Durée : {duration_min:.1f} min{share_text}

=== RETRANSCRIPTION ===
{result['formatted_text']}
=== FIN RETRANSCRIPTION ===

Produis le débrief structuré selon la grille du coach."""
                try:
                    response_text, cache_info = call_claude(
                        SYSTEM_PROMPT_DEBRIEF,
                        [{"role": "user", "content": user_msg}],
                    )
                    st.markdown("---")
                    st.markdown("## 📊 Débrief du coach")
                    st.markdown(response_text)
                    st.caption(
                        f"💾 Cache : {cache_info['cache_read']} tokens lus · "
                        f"{cache_info['output_tokens']} générés"
                    )
                    st.download_button(
                        "💾 Télécharger le débrief (.md)",
                        data=response_text,
                        file_name=f"debrief_{commercial_nom.replace(' ', '_')}_{datetime.date.today()}.md",
                        mime="text/markdown",
                    )
                except Exception as e:
                    st.error(f"Erreur d'analyse : {e}")


# -----------------------------------------------------------------------------
# Onglet 4 — Débrief d'appel (texte)
# -----------------------------------------------------------------------------
with tab_texte:
    st.subheader("Débrief d'un appel — texte")
    st.caption(
        "Si tu as déjà une retranscription (depuis Otter, Notta, Tella, Claap…), "
        "colle-la ici. Pas de passage par AssemblyAI."
    )

    commercial_nom_2 = st.selectbox(
        "Qui était le commercial ?",
        options=["Warren Elbaz", "Helder Alturas", "Autre"],
        index=0,
        key="commercial_select_2",
    )
    contexte_appel_2 = st.text_area(
        "Contexte de l'appel (facultatif)",
        placeholder="Ex : cold call sur un DAF d'ETI, 1er contact, objectif qualifier",
        height=80,
        key="contexte_2",
    )
    transcription_collee = st.text_area(
        "Colle la retranscription complète ici",
        height=300,
        placeholder=(
            "Speaker A: Bonjour Marie, ici Warren d'Entourage Recrutement, vous avez "
            "deux minutes ?\nSpeaker B: ..."
        ),
    )

    if st.button("📝 Débriefer", type="primary", disabled=not transcription_collee.strip()):
        with st.spinner("🧠 Analyse par le coach…"):
            user_msg = f"""Commercial : {commercial_nom_2}
Contexte : {contexte_appel_2 or 'non précisé'}

=== RETRANSCRIPTION ===
{transcription_collee}
=== FIN RETRANSCRIPTION ===

Produis le débrief structuré selon la grille du coach."""
            try:
                response_text, cache_info = call_claude(
                    SYSTEM_PROMPT_DEBRIEF,
                    [{"role": "user", "content": user_msg}],
                )
                st.markdown("---")
                st.markdown("## 📊 Débrief du coach")
                st.markdown(response_text)
                st.caption(
                    f"💾 Cache : {cache_info['cache_read']} tokens lus · "
                    f"{cache_info['output_tokens']} générés"
                )
                st.download_button(
                    "💾 Télécharger le débrief (.md)",
                    data=response_text,
                    file_name=f"debrief_{commercial_nom_2.replace(' ', '_')}_{datetime.date.today()}.md",
                    mime="text/markdown",
                )
            except Exception as e:
                st.error(f"Erreur : {e}")
