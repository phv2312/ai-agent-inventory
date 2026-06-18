"""Fuzzy text matching for inline evidence spans."""

from difflib import SequenceMatcher


def find_quote_span(
    text: str,
    quote: str,
    *,
    min_length: int = 5,
    min_ratio: float = 0.35,
) -> tuple[int, int] | None:
    """Return ``(start, end)`` of the best fuzzy match for *quote* in *text*."""
    if len(quote.strip()) < min_length:
        return None

    normed_text = text.replace("\n", " ")
    normed_quote = quote.replace("\n", " ")

    match = SequenceMatcher(
        None,
        normed_quote.lower(),
        normed_text.lower(),
        autojunk=False,
    ).find_longest_match()
    threshold = max(len(normed_quote) * min_ratio, min_length)
    if match.size <= threshold:
        return None

    return match.b, match.b + match.size
