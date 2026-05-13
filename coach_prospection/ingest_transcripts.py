"""
Ingestion d'un Word document contenant les retranscriptions des sessions de
coaching et ajout au corpus.

Pipeline :
    1. Lit le .docx (python-docx)
    2. Découpe en sessions (détection de séparateurs : dates, "Session X", etc.)
    3. Écrit chaque session dans coach_prospection/corpus/transcripts/
    4. Calcule le volume total du corpus
    5. Si > MAX_TOKENS_THRESHOLD : distille chaque transcript via Claude
       (résumé fidèle conservant principes + verbatim clés)
    6. Met à jour le corpus final

Usage :
    python -m coach_prospection.ingest_transcripts <chemin_du_word.docx>

Options :
    --no-distill     : ne pas distiller même si > seuil
    --force-distill  : forcer la distillation même si < seuil
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from docx import Document

from coach_prospection.corpus_loader import CORPUS_DIR, corpus_stats

TRANSCRIPTS_RAW_DIR = CORPUS_DIR / "_transcripts_raw"  # source brute (référence)
TRANSCRIPTS_FINAL_DIR = CORPUS_DIR  # ce qui finit dans le corpus
MAX_TOKENS_THRESHOLD = 180_000  # déclenche la distillation si dépassé


# ---------------------------------------------------------------------------
# Lecture .docx
# ---------------------------------------------------------------------------


def read_docx_paragraphs(docx_path: Path) -> list[tuple[str, str]]:
    """Lit un .docx et retourne [(style, texte), ...] en préservant l'ordre.

    Le 'style' est utilisé pour détecter les titres de session (Heading 1, etc.).
    """
    doc = Document(docx_path)
    out: list[tuple[str, str]] = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        style = (p.style.name if p.style else "Normal") or "Normal"
        out.append((style, text))
    return out


# ---------------------------------------------------------------------------
# Découpage en sessions
# ---------------------------------------------------------------------------

# Patterns de détection d'un nouveau bloc/session
SESSION_PATTERNS = [
    re.compile(r"^\s*(\d{2}[-/]\d{2}[-/]\d{2,4})\s*[-:]?\s*(.+)$"),  # "25-02-2026 Session 1: ..."
    re.compile(r"^\s*(session\s+\d+)\s*[-:]?\s*(.*)$", re.IGNORECASE),
    re.compile(r"^\s*(s\d+)\s*[-:]?\s*(.*)$", re.IGNORECASE),  # "S1: ..."
]


def is_session_header(style: str, text: str) -> tuple[bool, str | None]:
    """Détecte si un paragraphe est un titre de session.

    Retourne (is_header, normalized_title).
    """
    # Style heading = forte présomption
    is_heading = style.lower().startswith("heading") or style.lower().startswith("titre")
    for pattern in SESSION_PATTERNS:
        m = pattern.match(text)
        if m:
            return True, text.strip()
    if is_heading and len(text) < 150:
        return True, text.strip()
    return False, None


def split_into_sessions(
    paragraphs: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    """Découpe les paragraphes en liste [(titre_session, corps), ...].

    Si aucun titre détecté, retourne un seul bloc avec titre 'transcripts'.
    """
    sessions: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_body: list[str] = []

    for style, text in paragraphs:
        is_header, title = is_session_header(style, text)
        if is_header:
            if current_title is not None or current_body:
                sessions.append((current_title or "transcripts", current_body))
            current_title = title
            current_body = []
        else:
            current_body.append(text)
    if current_title is not None or current_body:
        sessions.append((current_title or "transcripts", current_body))

    return [(title, "\n\n".join(body)) for title, body in sessions if body or title]


# ---------------------------------------------------------------------------
# Écriture des transcripts en .md
# ---------------------------------------------------------------------------


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip()
    text = re.sub(r"[-\s]+", "_", text)
    return (text or "session")[:80]


def write_sessions_to_md(sessions: list[tuple[str, str]], output_dir: Path) -> list[Path]:
    """Écrit chaque session dans un fichier .md séparé.

    Préfixe les fichiers par 'transcript_' pour les distinguer du contenu Notion.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for i, (title, body) in enumerate(sessions, start=1):
        filename = f"transcript_{i:02d}_{slugify(title)}.md"
        path = output_dir / filename
        md = f"# Retranscription : {title}\n\n{body}\n"
        path.write_text(md, encoding="utf-8")
        written.append(path)
        print(f"  ✅ {filename} ({len(md)} car.)")
    return written


# ---------------------------------------------------------------------------
# Distillation via Claude
# ---------------------------------------------------------------------------

DISTILL_SYSTEM_PROMPT = """Tu es chargé de DISTILLER une retranscription d'une session de coaching commercial entre Jim Breton (le coach) et Warren/Helder (les coachés).

Ta mission : produire un résumé fidèle qui conserve TOUT ce qui est exploitable pour reproduire la méthode de Jim, en supprimant le bruit (digressions, redites, hésitations, parlé conversationnel sans valeur pédagogique).

GARDER ABSOLUMENT :
1. **Tous les principes / cadres** énoncés par Jim (avec son vocabulaire exact).
2. **Tous les verbatim de Jim** qui sont des formulations à reproduire (exemples d'ouverture, de questions, de relances, de gestion d'objections).
3. **Les exemples concrets** : situations, secteurs, profils mentionnés.
4. **Les corrections** que Jim apporte aux propositions de Warren/Helder ("non, plutôt comme ça", "évite de dire X").
5. **Les TO-DOs** ou engagements pris en fin de session.

ENLEVER :
- Salutations, météo, hors-sujet
- Reprises et reformulations sans valeur ajoutée
- Hésitations ("euh", "donc", "voilà") sauf si pédagogiquement intéressantes
- Confirmations passives ("oui", "ok", "d'accord")

FORMAT DE SORTIE (Markdown) :
```
# [Titre de la session]

## Principes énoncés
- [Principe 1] (verbatim Jim : "...")
- ...

## Cadres / méthodes
- [Nom du cadre] : [explication]

## Verbatim de formulations clés (à reproduire)
- Pour [contexte] : "..."
- ...

## Exemples concrets
- [Description] : ...

## Corrections apportées
- À éviter : "..." → Préférer : "..."

## TO-DO / engagements
- [...]
```

Sois exhaustif sur ce qui est gardé. La distillation doit faire 25-40% de la taille originale, pas moins."""


def distill_session(raw_md: str, model: str = "claude-sonnet-4-6") -> str:
    """Appelle Claude pour distiller une retranscription brute."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=model,
        max_tokens=8000,
        system=DISTILL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": raw_md}],
    )
    return "".join(b.text for b in response.content if b.type == "text")


def distill_all(transcript_paths: list[Path]) -> None:
    """Distille chaque transcript : sauvegarde le brut dans _transcripts_raw/ et
    écrase l'original par la version distillée."""
    TRANSCRIPTS_RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n🧪 Distillation de {len(transcript_paths)} transcripts via Claude…\n")
    for i, path in enumerate(transcript_paths, start=1):
        raw_md = path.read_text(encoding="utf-8")
        # Sauvegarde le brut
        backup_path = TRANSCRIPTS_RAW_DIR / path.name
        backup_path.write_text(raw_md, encoding="utf-8")
        # Distille
        try:
            print(f"  [{i}/{len(transcript_paths)}] {path.name} ({len(raw_md)} car.) → distillation…")
            distilled = distill_session(raw_md)
            path.write_text(distilled, encoding="utf-8")
            ratio = (len(distilled) / len(raw_md)) * 100 if raw_md else 0
            print(f"      ↳ {len(distilled)} car. ({ratio:.0f}% du brut)")
        except Exception as e:
            print(f"      ❌ Échec : {e} — on garde le brut.")


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Ingère un Word de transcripts dans le corpus.")
    parser.add_argument("docx_path", help="Chemin vers le fichier .docx")
    parser.add_argument("--no-distill", action="store_true", help="Pas de distillation même si > seuil")
    parser.add_argument("--force-distill", action="store_true", help="Force la distillation")
    args = parser.parse_args()

    docx_path = Path(args.docx_path)
    if not docx_path.exists():
        print(f"❌ Fichier introuvable : {docx_path}", file=sys.stderr)
        sys.exit(1)

    print(f"📖 Lecture de {docx_path.name}…")
    paragraphs = read_docx_paragraphs(docx_path)
    print(f"   {len(paragraphs)} paragraphes lus.\n")

    print("✂️  Découpage en sessions…")
    sessions = split_into_sessions(paragraphs)
    print(f"   {len(sessions)} sessions détectées :")
    for title, body in sessions:
        print(f"   - {title[:60]} ({len(body)} car.)")

    print("\n💾 Écriture des transcripts dans le corpus…")
    written = write_sessions_to_md(sessions, TRANSCRIPTS_FINAL_DIR)

    # Mesure du corpus final
    stats = corpus_stats()
    print(
        f"\n📊 Corpus total : {stats['files_count']} fichiers, "
        f"{stats['total_chars']/1000:.0f}k car., ≈ {stats['estimated_tokens']/1000:.0f}k tokens"
    )

    needs_distill = (
        stats["estimated_tokens"] > MAX_TOKENS_THRESHOLD and not args.no_distill
    ) or args.force_distill

    if needs_distill:
        if stats["estimated_tokens"] > MAX_TOKENS_THRESHOLD:
            print(
                f"\n⚠️  Corpus dépasse {MAX_TOKENS_THRESHOLD/1000:.0f}k tokens, "
                "distillation automatique enclenchée."
            )
        distill_all(written)
        stats_after = corpus_stats()
        print(
            f"\n✅ Distillation terminée. Corpus final : "
            f"{stats_after['total_chars']/1000:.0f}k car., "
            f"≈ {stats_after['estimated_tokens']/1000:.0f}k tokens"
        )
    else:
        print(
            f"\n✅ Corpus sous le seuil ({MAX_TOKENS_THRESHOLD/1000:.0f}k tokens), "
            "pas de distillation nécessaire."
        )

    print("\n💡 Pense à uploader le corpus mis à jour sur Drive :")
    print("   python -m coach_prospection.drive_sync upload")


if __name__ == "__main__":
    main()
