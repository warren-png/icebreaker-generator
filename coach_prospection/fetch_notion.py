"""
Fetcher Notion : récupère une page publique notion.site et toutes ses sous-pages,
les convertit en Markdown et les sauvegarde dans coach_prospection/corpus/.

Usage :
    python -m coach_prospection.fetch_notion <URL_OU_ID_PAGE>

Exemple :
    python -m coach_prospection.fetch_notion https://grizzled-lion-14a.notion.site/Warren-Helder-Jim-Sales-Coaching-30c76152c98a80bf8d77fab62e9b0f2c

Si aucun argument n'est passé, utilise la racine définie dans la variable NOTION_ROOT_PAGE_ID
du .env (ou la constante DEFAULT_PAGE_ID ci-dessous).
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

NOTION_API_BASE = "https://www.notion.so/api/v3"
CORPUS_DIR = Path(__file__).parent / "corpus"
CHUNK_LIMIT = 100
REQUEST_DELAY = 0.25  # politesse : pause entre requêtes


def normalize_page_id(raw: str) -> str:
    """Extrait un UUID Notion d'une URL ou d'une chaîne, et le formate avec tirets."""
    # Cherche un hash de 32 caractères hex (avec ou sans tirets)
    match = re.search(r"([0-9a-f]{32}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", raw, re.IGNORECASE)
    if not match:
        raise ValueError(f"Impossible d'extraire un ID de page Notion depuis : {raw}")
    pid = match.group(1).replace("-", "").lower()
    return f"{pid[0:8]}-{pid[8:12]}-{pid[12:16]}-{pid[16:20]}-{pid[20:32]}"


def load_page_chunk(page_id: str, chunk_number: int = 0) -> dict[str, Any]:
    """Appelle l'endpoint loadPageChunk pour récupérer les blocs d'une page."""
    payload = {
        "page": {"id": page_id},
        "limit": CHUNK_LIMIT,
        "chunkNumber": chunk_number,
        "cursor": {"stack": []},
        "verticalColumns": False,
    }
    resp = requests.post(f"{NOTION_API_BASE}/loadPageChunk", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def sync_record_values(block_ids: list[str]) -> dict[str, Any]:
    """Récupère un batch de blocs par ID via syncRecordValues (jusqu'à ~100 par appel)."""
    if not block_ids:
        return {}
    payload = {
        "requests": [
            {"pointer": {"id": bid, "table": "block"}, "version": -1}
            for bid in block_ids
        ]
    }
    resp = requests.post(f"{NOTION_API_BASE}/syncRecordValues", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json().get("recordMap", {}).get("block", {})


def fetch_all_blocks_for_page(page_id: str) -> dict[str, Any]:
    """Récupère tous les blocs d'une page (pagination chunkNumber + résolution récursive)."""
    merged_block_map: dict[str, Any] = {}
    chunk_number = 0
    while True:
        time.sleep(REQUEST_DELAY)
        data = load_page_chunk(page_id, chunk_number=chunk_number)
        block_map = data.get("recordMap", {}).get("block", {})
        if not block_map:
            break
        new_blocks = {k: v for k, v in block_map.items() if k not in merged_block_map}
        merged_block_map.update(block_map)
        cursor = data.get("cursor", {})
        if not cursor.get("stack") or not new_blocks:
            break
        chunk_number += 1
        if chunk_number > 50:
            break

    # Résolution récursive des blocs référencés mais non chargés
    return resolve_missing_blocks(merged_block_map, root_id=page_id)


def resolve_missing_blocks(
    block_map: dict[str, Any],
    root_id: str,
    max_iterations: int = 10,
    batch_size: int = 80,
) -> dict[str, Any]:
    """Itère pour charger tous les blocs référencés dans 'content' mais absents du map.

    Stoppe quand plus rien n'est à résoudre, ou après max_iterations. Ne descend
    pas dans les sous-pages (type='page') autres que la racine — celles-ci sont
    traitées comme des pages séparées par fetch_recursive.
    """
    for _ in range(max_iterations):
        missing: set[str] = set()
        for bid, wrapper in block_map.items():
            v = extract_value(wrapper)
            if not v:
                continue
            # Ne pas descendre dans une sous-page (elle sera fetchée séparément)
            if v.get("type") == "page" and bid != root_id:
                continue
            for cid in v.get("content", []) or []:
                if cid not in block_map:
                    missing.add(cid)
        if not missing:
            break
        # Batch fetch
        missing_list = list(missing)
        for i in range(0, len(missing_list), batch_size):
            time.sleep(REQUEST_DELAY)
            batch = missing_list[i : i + batch_size]
            try:
                fetched = sync_record_values(batch)
            except requests.HTTPError:
                continue
            block_map.update(fetched)
    return block_map


def rich_text_to_markdown(
    rich_text: list[Any] | None,
    page_mentions: list[str] | None = None,
) -> str:
    """Convertit le 'title' Notion en Markdown.

    Si page_mentions est fourni, les IDs des pages référencées via mentions (‣)
    sont ajoutés à cette liste, pour qu'elles soient fetchées séparément.
    """
    if not rich_text:
        return ""
    parts: list[str] = []
    for fragment in rich_text:
        if not isinstance(fragment, list) or not fragment:
            continue
        text = fragment[0]
        annotations = fragment[1] if len(fragment) > 1 else []
        bold = italic = code = strike = False
        link_url = None
        page_mention_id: str | None = None
        for ann in annotations or []:
            if not isinstance(ann, list) or not ann:
                continue
            tag = ann[0]
            if tag == "b":
                bold = True
            elif tag == "i":
                italic = True
            elif tag == "c":
                code = True
            elif tag == "s":
                strike = True
            elif tag == "a" and len(ann) > 1:
                link_url = ann[1]
            elif tag == "p" and len(ann) > 1:
                # Page mention : ann = ["p", "<page-uuid>", ...]
                page_mention_id = ann[1]
            elif tag == "‣":
                pass  # caractère placeholder, traité via tag 'p' ci-dessus
            # 'h' = highlight color, 'u' = underline → ignorés en Markdown standard
        if page_mention_id and page_mentions is not None:
            page_mentions.append(page_mention_id)
            # On remplace le ‣ par un lien clair vers la sous-page
            text = f"[→ sous-page {page_mention_id[:8]}](#{page_mention_id[:8]})"
        if code:
            text = f"`{text}`"
        if bold and italic:
            text = f"***{text}***"
        elif bold:
            text = f"**{text}**"
        elif italic:
            text = f"*{text}*"
        if strike:
            text = f"~~{text}~~"
        if link_url:
            text = f"[{text}]({link_url})"
        parts.append(text)
    return "".join(parts)


def block_to_markdown(
    block_value: dict[str, Any],
    block_map: dict[str, Any],
    indent: int = 0,
    page_mentions: list[str] | None = None,
) -> str:
    """Convertit un bloc Notion + ses enfants en Markdown. Retourne '' si type non géré ou bloc vide."""
    btype = block_value.get("type")
    props = block_value.get("properties", {}) or {}
    title_md = rich_text_to_markdown(props.get("title"), page_mentions=page_mentions)
    prefix = "  " * indent
    out: list[str] = []

    if btype == "page":
        # Une sous-page n'est pas inlinée — on met juste un lien vers son fichier
        sub_title = title_md or "Sans titre"
        out.append(f"{prefix}- 📄 [{sub_title}](./{slugify(sub_title)}.md)")
    elif btype == "header":
        out.append(f"# {title_md}")
    elif btype == "sub_header":
        out.append(f"## {title_md}")
    elif btype == "sub_sub_header":
        out.append(f"### {title_md}")
    elif btype == "text":
        if title_md.strip():
            out.append(f"{prefix}{title_md}")
        else:
            out.append("")  # paragraphe vide = saut de ligne
    elif btype == "bulleted_list":
        out.append(f"{prefix}- {title_md}")
    elif btype == "numbered_list":
        out.append(f"{prefix}1. {title_md}")
    elif btype == "to_do":
        checked = props.get("checked", [[""]])[0][0] == "Yes"
        box = "[x]" if checked else "[ ]"
        out.append(f"{prefix}- {box} {title_md}")
    elif btype == "toggle":
        out.append(f"{prefix}<details><summary>{title_md}</summary>\n")
    elif btype == "quote":
        out.append(f"{prefix}> {title_md}")
    elif btype == "callout":
        icon = block_value.get("format", {}).get("page_icon", "💡")
        out.append(f"{prefix}> {icon} {title_md}")
    elif btype == "code":
        lang = (props.get("language", [[""]])[0][0] or "").lower()
        out.append(f"```{lang}\n{title_md}\n```")
    elif btype == "divider":
        out.append("---")
    elif btype == "bookmark":
        url = (props.get("link", [[""]])[0][0] or "")
        out.append(f"{prefix}🔗 [{title_md or url}]({url})")
    elif btype == "video":
        src = (props.get("source", [[""]])[0][0] or "")
        out.append(f"{prefix}🎥 Vidéo : {src}")
    elif btype == "audio":
        src = (props.get("source", [[""]])[0][0] or "")
        out.append(f"{prefix}🎙️ Audio : {src}")
    elif btype == "image":
        src = (props.get("source", [[""]])[0][0] or "")
        out.append(f"{prefix}![image]({src})")
    elif btype == "file":
        src = (props.get("source", [[""]])[0][0] or "")
        out.append(f"{prefix}📎 [{title_md or 'fichier'}]({src})")
    elif btype == "table_of_contents":
        pass  # ignoré dans l'export Markdown
    elif btype == "column_list" or btype == "column":
        pass  # les enfants seront traités via la récursion
    elif btype is None:
        return ""
    else:
        # Type inconnu : on tente d'afficher le titre s'il y en a un
        if title_md.strip():
            out.append(f"{prefix}{title_md}")

    # Récursion sur les enfants
    child_ids = block_value.get("content", []) or []
    for cid in child_ids:
        child_wrapper = block_map.get(cid, {})
        # La structure peut être {'value': {'value': {...}}} OU {'value': {...}}
        child_val = child_wrapper.get("value", {})
        if isinstance(child_val, dict) and "value" in child_val:
            child_val = child_val["value"]
        if not child_val or not isinstance(child_val, dict):
            continue
        # Les sous-pages ne sont pas inlinées dans le parent (sauf le lien déjà ajouté ci-dessus)
        if btype == "page" and child_val.get("type") == "page":
            sub_md = block_to_markdown(child_val, block_map, indent=indent, page_mentions=page_mentions)
            if sub_md:
                out.append(sub_md)
            continue
        child_md = block_to_markdown(
            child_val,
            block_map,
            indent=indent + 1 if btype in {"bulleted_list", "numbered_list", "to_do", "toggle"} else indent,
            page_mentions=page_mentions,
        )
        if child_md:
            out.append(child_md)

    if btype == "toggle":
        out.append(f"{prefix}</details>")

    return "\n".join(out)


def slugify(text: str) -> str:
    """Transforme un titre en nom de fichier safe."""
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip()
    text = re.sub(r"[-\s]+", "_", text)
    return (text or "page")[:80]


def extract_value(block_wrapper: dict[str, Any]) -> dict[str, Any] | None:
    """Extrait le dict de valeur principal d'un bloc, en gérant les deux structures de wrapping."""
    v = block_wrapper.get("value", {})
    if isinstance(v, dict) and "value" in v and isinstance(v["value"], dict):
        return v["value"]
    if isinstance(v, dict) and v.get("type"):
        return v
    return None


def find_subpages(root_page_id: str, block_map: dict[str, Any]) -> list[tuple[str, str]]:
    """Retourne (id, titre) de toutes les sous-pages présentes dans le recordMap.

    Notion charge les sous-pages d'un niveau dans le même recordMap que la racine
    (même si elles ne sont pas dans le 'content' direct). On itère donc sur tous
    les blocs de type 'page' autres que la racine elle-même.
    """
    subs: list[tuple[str, str]] = []
    for bid, wrapper in block_map.items():
        if bid == root_page_id:
            continue
        v = extract_value(wrapper)
        if not v or v.get("type") != "page":
            continue
        title = rich_text_to_markdown(v.get("properties", {}).get("title")) or "Sans titre"
        subs.append((bid, title))
    return subs


def page_to_markdown(
    page_id: str,
    block_map: dict[str, Any],
) -> tuple[str, str, list[str]]:
    """Convertit une page entière en Markdown. Retourne (titre, contenu_md, page_mentions).

    page_mentions = IDs des sous-pages mentionnées via ‣ dans le rich text.
    """
    page_mentions: list[str] = []
    root = extract_value(block_map.get(page_id, {}))
    if not root:
        return ("Page introuvable", "", page_mentions)
    title = rich_text_to_markdown(root.get("properties", {}).get("title"), page_mentions=page_mentions) or "Sans titre"
    body_parts: list[str] = [f"# {title}\n"]
    for cid in root.get("content", []) or []:
        v = extract_value(block_map.get(cid, {}))
        if not v:
            continue
        md = block_to_markdown(v, block_map, indent=0, page_mentions=page_mentions)
        if md.strip():
            body_parts.append(md)
    return (title, "\n\n".join(body_parts), page_mentions)


def fetch_recursive(root_page_id: str, output_dir: Path, max_depth: int = 4) -> None:
    """Récupère la page racine + toutes ses sous-pages (récursivement), en .md séparés."""
    output_dir.mkdir(parents=True, exist_ok=True)
    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(root_page_id, 0)]

    while queue:
        page_id, depth = queue.pop(0)
        if page_id in visited or depth > max_depth:
            continue
        visited.add(page_id)
        try:
            block_map = fetch_all_blocks_for_page(page_id)
        except requests.HTTPError as e:
            print(f"  ❌ {page_id[:8]}... → erreur HTTP {e.response.status_code}", file=sys.stderr)
            continue
        if not block_map:
            print(f"  ⚠️  {page_id[:8]}... → aucun bloc retourné", file=sys.stderr)
            continue

        title, md, page_mentions = page_to_markdown(page_id, block_map)
        if md.strip():
            filename = slugify(title) + f"_{page_id[:8]}.md"
            (output_dir / filename).write_text(md, encoding="utf-8")
            char_count = len(md)
            print(f"  ✅ {title[:55]:55} → {filename} ({char_count} car.)")

        # Découvre les sous-pages : a) celles dans le recordMap, b) celles mentionnées via ‣
        subs = find_subpages(page_id, block_map)
        for sub_id, _ in subs:
            if sub_id not in visited:
                queue.append((sub_id, depth + 1))
        for mention_id in page_mentions:
            try:
                normalized = normalize_page_id(mention_id)
            except ValueError:
                continue
            if normalized not in visited:
                queue.append((normalized, depth + 1))

    print(f"\n✨ Terminé. {len(visited)} pages traitées. Corpus dans : {output_dir}")


def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NOTION_ROOT_PAGE_ID")
    if not arg:
        print("Usage : python -m coach_prospection.fetch_notion <URL_OU_ID>", file=sys.stderr)
        sys.exit(1)
    page_id = normalize_page_id(arg)
    print(f"🚀 Récupération du Notion à partir de : {page_id}\n")
    fetch_recursive(page_id, CORPUS_DIR)


if __name__ == "__main__":
    main()
