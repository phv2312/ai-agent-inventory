"""Apply inline snippet highlights to retrieved chunks."""

from __future__ import annotations

import html
import re
from typing import Protocol

from agent.models.document import ScoredChunk

from .marker import highlight_snippets


class CitationItem(Protocol):
    chunk_id: str
    snippets: list[str]


def mp_chunk_id_snippets_from_items(
    items: list[CitationItem],
) -> dict[str, list[str]]:
    """Merge citation rows into ``chunk_id -> snippets``."""
    mp_chunk_snippets: dict[str, list[str]] = {}
    for item in items:
        chunk_id = str(item.chunk_id).strip()
        if not chunk_id:
            continue
        mp_chunk_snippets.setdefault(chunk_id, []).extend(item.snippets)
    return mp_chunk_snippets


def apply_snippet_highlights(
    chunks: list[ScoredChunk],
    mp_chunk_snippets: dict[str, list[str]],
) -> list[ScoredChunk]:
    """Return chunks with kotaemon-style ``<mark>`` highlights applied."""
    if not mp_chunk_snippets:
        return chunks

    highlighted: list[ScoredChunk] = []
    for scored in chunks:
        chunk_id = str(scored.chunk.chunk_id)
        snippets = mp_chunk_snippets.get(chunk_id)
        if not snippets:
            highlighted.append(scored)
            continue

        updated = scored.model_copy(deep=True)
        updated.chunk.text = highlight_snippets(
            updated.chunk.text,
            snippets,
            chunk_id=chunk_id,
        )
        highlighted.append(updated)

    return highlighted


def render_highlighted_body(text: str) -> str:
    """Escape plain text while preserving ``<mark>`` highlight tags."""
    parts = re.split(r"(<mark[^>]*>.*?</mark>)", text, flags=re.DOTALL)
    rendered: list[str] = []
    for part in parts:
        if part.startswith("<mark"):
            rendered.append(part)
        else:
            rendered.append(html.escape(part))
    return "".join(rendered)
