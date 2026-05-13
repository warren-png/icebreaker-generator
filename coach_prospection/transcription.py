"""
Transcription d'appels audio via AssemblyAI, avec diarisation (qui parle quand).

Utilisation :
    from coach_prospection.transcription import transcribe_audio_file
    result = transcribe_audio_file(file_bytes, filename="appel.m4a")
    print(result["formatted_text"])  # texte formaté lisible par humain ou IA

L'objet retourné contient :
    - formatted_text : str (lisible, format "Speaker A: ...\\nSpeaker B: ...")
    - utterances : list[dict] (détail par tour de parole avec timestamps)
    - duration_seconds : float
    - speakers_count : int
    - raw : objet brut AssemblyAI
"""

from __future__ import annotations

import os
import time
from typing import Any

try:
    import assemblyai as aai
except ImportError:  # pragma: no cover
    aai = None  # type: ignore


class TranscriptionError(Exception):
    """Erreur côté transcription (clé API manquante, fichier invalide, etc.)."""


def _ensure_configured() -> None:
    if aai is None:
        raise TranscriptionError(
            "Le package 'assemblyai' n'est pas installé. Ajoute-le à requirements.txt."
        )
    api_key = os.environ.get("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise TranscriptionError(
            "ASSEMBLYAI_API_KEY manquante dans l'environnement. "
            "Ajoute-la dans ton fichier .env."
        )
    aai.settings.api_key = api_key


def transcribe_audio_file(
    file_path_or_bytes: str | bytes,
    filename: str | None = None,
    language: str = "fr",
    progress_callback=None,
) -> dict[str, Any]:
    """Transcrit un fichier audio (M4A, MP3, WAV, MP4...) avec diarisation.

    Args:
        file_path_or_bytes : chemin local OU bytes du fichier.
        filename : utile uniquement si file_path_or_bytes est en bytes (pour log).
        language : code langue ('fr' par défaut).
        progress_callback : fonction(message: str) appelée à chaque étape, optionnelle.

    Returns:
        dict avec formatted_text, utterances, duration_seconds, speakers_count, raw.
    """
    _ensure_configured()

    def log(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    log("Préparation du fichier audio…")

    # L'API AssemblyAI exige depuis 2026 que speech_models (au pluriel) soit
    # une liste contenant 'universal-2' ou 'universal-3-pro'. On force
    # 'universal-2' qui supporte la diarisation multi-langues (dont le français).
    config = aai.TranscriptionConfig(
        speech_models=["universal-2"],
        language_code=language,
        speaker_labels=True,  # diarisation activée
        punctuate=True,
        format_text=True,
    )

    transcriber = aai.Transcriber(config=config)

    log("Envoi à AssemblyAI et transcription en cours (peut prendre quelques minutes)…")
    started = time.time()

    if isinstance(file_path_or_bytes, bytes):
        # Le SDK accepte un chemin ou une URL ; pour des bytes on écrit en temp file
        import tempfile

        suffix = ""
        if filename:
            ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
            suffix = f".{ext}" if ext else ""
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_path_or_bytes)
            tmp_path = tmp.name
        try:
            transcript = transcriber.transcribe(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    else:
        transcript = transcriber.transcribe(file_path_or_bytes)

    elapsed = time.time() - started
    log(f"Transcription terminée en {elapsed:.1f}s.")

    if transcript.status == aai.TranscriptStatus.error:
        raise TranscriptionError(
            f"AssemblyAI a renvoyé une erreur : {transcript.error}"
        )

    utterances = transcript.utterances or []
    speakers = {u.speaker for u in utterances if getattr(u, "speaker", None)}

    formatted_lines: list[str] = []
    for u in utterances:
        speaker = getattr(u, "speaker", "?") or "?"
        text = (getattr(u, "text", "") or "").strip()
        start_ms = getattr(u, "start", 0) or 0
        timestamp = _ms_to_timestamp(start_ms)
        if text:
            formatted_lines.append(f"[{timestamp}] Speaker {speaker}: {text}")
    if not formatted_lines and getattr(transcript, "text", None):
        # Fallback si pas de diarisation
        formatted_lines.append(transcript.text)

    duration_seconds = (getattr(transcript, "audio_duration", 0) or 0)

    return {
        "formatted_text": "\n".join(formatted_lines),
        "utterances": [
            {
                "speaker": getattr(u, "speaker", "?"),
                "text": getattr(u, "text", ""),
                "start_ms": getattr(u, "start", 0),
                "end_ms": getattr(u, "end", 0),
            }
            for u in utterances
        ],
        "duration_seconds": duration_seconds,
        "speakers_count": len(speakers),
        "raw": transcript,
    }


def _ms_to_timestamp(ms: int) -> str:
    """Convertit des millisecondes en mm:ss."""
    total_seconds = ms // 1000
    mm, ss = divmod(total_seconds, 60)
    return f"{mm:02d}:{ss:02d}"


def compute_speaking_time_share(utterances: list[dict]) -> dict[str, float]:
    """Retourne le % de temps de parole par speaker (somme = 100)."""
    totals: dict[str, int] = {}
    for u in utterances:
        speaker = u.get("speaker", "?")
        duration = (u.get("end_ms", 0) or 0) - (u.get("start_ms", 0) or 0)
        if duration < 0:
            duration = 0
        totals[speaker] = totals.get(speaker, 0) + duration
    grand = sum(totals.values())
    if grand == 0:
        return {}
    return {s: round(100 * v / grand, 1) for s, v in totals.items()}
