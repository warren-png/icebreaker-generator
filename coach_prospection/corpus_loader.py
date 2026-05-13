"""
Chargement du corpus du coach de prospection.

Le corpus = tous les .md dans coach_prospection/corpus/, concaténés dans un
ordre stable (par nom de fichier) avec des séparateurs explicites pour que
Claude puisse identifier la page source d'un extrait.

En prod (Streamlit Cloud) le corpus n'est PAS commité sur GitHub (confidentiel)
mais stocké sur Google Drive. ensure_corpus_present() le télécharge au besoin.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

CORPUS_DIR = Path(__file__).parent / "corpus"


def list_corpus_files() -> list[Path]:
    """Retourne tous les .md du corpus, triés par nom (ordre stable pour le cache)."""
    if not CORPUS_DIR.exists():
        return []
    return sorted(CORPUS_DIR.glob("*.md"))


def ensure_corpus_present() -> dict:
    """Si le dossier corpus est vide, télécharge depuis Google Drive.

    Retourne {'source': 'local'|'drive'|'empty', 'files': int}.
    Cette fonction est idempotente : si le corpus est déjà là, ne fait rien.
    """
    files = list_corpus_files()
    if files:
        return {"source": "local", "files": len(files)}
    # Pas de fichiers locaux : tente le download depuis Drive
    try:
        from coach_prospection.drive_sync import download_corpus_from_drive

        stats = download_corpus_from_drive(CORPUS_DIR)
        if stats["files_downloaded"] > 0:
            return {"source": "drive", "files": stats["files_downloaded"]}
    except Exception as e:
        # Logue mais ne plante pas : laisse l'UI afficher un message clair
        print(f"⚠️  Impossible de télécharger le corpus depuis Drive : {e}")
    return {"source": "empty", "files": 0}


def load_corpus_text(exclude: Iterable[str] = ()) -> str:
    """Charge tous les .md et les concatène en un seul bloc avec séparateurs.

    Les noms de fichier listés dans `exclude` sont ignorés (filename, sans le dossier).
    """
    exclude_set = set(exclude)
    parts: list[str] = []
    for path in list_corpus_files():
        if path.name in exclude_set:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not content.strip():
            continue
        parts.append(f"\n\n===== FICHIER : {path.name} =====\n\n{content}")
    return "".join(parts).strip()


def corpus_stats() -> dict[str, int | list[str]]:
    """Retourne des stats sur le corpus chargé : nb fichiers, taille, liste."""
    files = list_corpus_files()
    total_chars = sum(p.stat().st_size for p in files)
    return {
        "files_count": len(files),
        "total_chars": total_chars,
        "estimated_tokens": total_chars // 4,  # approximation grossière
        "filenames": [p.name for p in files],
    }
