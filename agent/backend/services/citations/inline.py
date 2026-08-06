from __future__ import annotations

import html
import re

from agent.core.models.document import ScoredChunk

from .marker import highlight_snippets


def apply_snippet_highlights(
    chunks: list[ScoredChunk],
    mp_chunk_snippets: dict[str, list[str]],
) -> list[ScoredChunk]:
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
    parts = re.split(r"(<mark[^>]*>.*?</mark>)", text, flags=re.DOTALL)
    rendered: list[str] = []
    for part in parts:
        if part.startswith("<mark"):
            rendered.append(part)
        else:
            rendered.append(html.escape(part))
    return "".join(rendered)
