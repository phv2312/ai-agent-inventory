"""Highlight matched evidence spans in chunk text."""

from .matcher import find_quote_span


def highlight_snippet(
    text: str,
    snippet: str,
    *,
    mark_id: str | None = None,
) -> str:
    """Wrap the first fuzzy match of *snippet* in ``<mark>``."""
    if not snippet.strip():
        return text

    if snippet in text:
        start = text.index(snippet)
        end = start + len(snippet)
    else:
        span = find_quote_span(text, snippet)
        if span is None:
            return text
        start, end = span

    id_attr = f" id='mark-{mark_id}'" if mark_id else ""
    marked = f"<mark{id_attr}>{text[start:end]}</mark>"
    return text[:start] + marked + text[end:]


def highlight_snippets(
    text: str,
    snippets: list[str],
    *,
    chunk_id: str,
) -> str:
    """Apply multiple snippet highlights, longest first to reduce overlap."""
    highlighted = text
    ordered = sorted(
        {snippet.strip() for snippet in snippets if snippet.strip()},
        key=len,
        reverse=True,
    )
    for idx, snippet in enumerate(ordered):
        highlighted = highlight_snippet(
            highlighted,
            snippet,
            mark_id=f"{chunk_id}-{idx}",
        )
    return highlighted
