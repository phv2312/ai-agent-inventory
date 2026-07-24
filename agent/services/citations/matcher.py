from difflib import SequenceMatcher

from agent.models.document import ScoredChunk


def find_quote_span(
    text: str,
    quote: str,
    *,
    min_length: int = 5,
    min_ratio: float = 0.35,
) -> tuple[int, int] | None:
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


def find_start_end_phrase(
    start_phrase: str | None,
    end_phrase: str | None,
    context: str,
    *,
    min_length: int = 5,
    max_excerpt_length: int = 300,
) -> tuple[tuple[int, int] | None, int]:
    if not start_phrase and not end_phrase:
        return None, 0

    normed_context = context.replace("\n", " ").lower()
    matches: list[tuple[int, int]] = []
    matched_length = 0

    for phrase in (start_phrase, end_phrase):
        if phrase is None:
            continue
        sentence = phrase.lower()
        match = SequenceMatcher(
            None,
            sentence,
            normed_context,
            autojunk=False,
        ).find_longest_match()
        if match.size > max(len(sentence) * 0.35, min_length):
            matches.append((match.b, match.b + match.size))
            matched_length += match.size

    if len(matches) == 2 and matches[1][0] < matches[0][0]:
        matches = [matches[0]]

    if not matches:
        return None, 0

    start_idx = min(start for start, _ in matches)
    end_idx = max(end for _, end in matches)
    if end_idx - start_idx > max_excerpt_length:
        end_idx = start_idx + max_excerpt_length

    return (start_idx, end_idx), matched_length


def match_entry_to_chunk(
    *,
    start_phrase: str | None,
    end_phrase: str | None,
    chunks_by_id: dict[str, ScoredChunk],
) -> tuple[str, tuple[int, int]] | None:
    if not start_phrase and not end_phrase:
        return None

    best_chunk_id: str | None = None
    best_span: tuple[int, int] | None = None
    best_length = 0

    for chunk_id, scored in chunks_by_id.items():
        span, length = find_start_end_phrase(
            start_phrase,
            end_phrase,
            scored.chunk.text,
        )
        if span is None:
            continue
        if best_span is None or length > best_length:
            best_chunk_id = chunk_id
            best_span = span
            best_length = length

    if best_chunk_id is None or best_span is None:
        return None

    return best_chunk_id, best_span
