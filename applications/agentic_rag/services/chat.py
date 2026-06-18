"""Chat service and HTML rendering helpers."""

import html
import re
from collections.abc import AsyncGenerator

from agent.citations import mp_chunk_id_snippets_from_items
from agent.citations.inline import render_highlighted_body
from agent.deps import Container, VectorDBModel
from agent.models.document import DocumentMetadata, ScoredChunk
from agent.models.messages import AssistantMessage, UserMessage
from agent.models.streams import (
    CustomFunctionCall,
    FunctionCallArgsDeltaEvent,
    FunctionCallArgsDoneEvent,
    FunctionCallStartEvent,
    FunctionCallTextDeltaEvent,
    TextDeltaEvent,
    WebSearchFunctionCall,
)
from agent.storages.config import AnchorFields
from agent.tools.schemas.registry import (
    InlineCitationsParameters,
    ToolNames,
    VisualizeShowWidgetParameters,
)
from applications.agentic_rag.ui.widget import WidgetCodeStreamExtractor


class ChatService:
    """Stream agentic answers and retrieve source chunks."""

    def __init__(self, container: Container) -> None:
        self.container = container

    def _to_messages(
        self,
        history: list[dict[str, str]],
    ) -> list[UserMessage | AssistantMessage]:
        messages: list[UserMessage | AssistantMessage] = []
        for item in history:
            role = item.get("role", "")
            content = item.get("content", "")
            if role == "user":
                messages.append(UserMessage(content=content))
            elif role == "assistant":
                messages.append(AssistantMessage(content=content))
        return messages

    async def stream_answer(
        self,
        query: str,
        file_ids: list[str],
        history: list[dict[str, str]],
    ) -> AsyncGenerator[tuple[str, str], None]:
        """Stream answer events.

        Yields tuples of (kind, payload) where kind is one of:
        - ``"thought"`` — reasoning / tool-call text delta
        - ``"text"`` — final answer text delta
        - ``"citations"`` — inline snippet map ``chunk_id -> [snippets]``
        - ``"widget"`` — complete widget_code once generation is done
        - ``"widget_title"`` — widget title (emitted with widget)
        """
        strategy = self.container.agentic.get()
        prior = self._to_messages(history[:-1] if history else [])
        widget_extractor = WidgetCodeStreamExtractor()
        widget_call_id: str | None = None
        widget_code = ""
        mp_chunk_snippets: dict[str, list[str]] = {}

        async for event in strategy.stream_async_answer(
            query=query,
            file_ids=file_ids,
            history=prior,
            model_name=self.container.env.OPENAI_CHAT_DEPLOYMENT_NAME,
        ):
            if (
                isinstance(event, FunctionCallStartEvent)
                and isinstance(event.item, CustomFunctionCall)
                and event.item.name == ToolNames.VISUALIZE_SHOW_WIDGET_TOOL
            ):
                widget_call_id = event.id
                widget_code = ""

            elif (
                isinstance(event, FunctionCallArgsDeltaEvent)
                and event.id == widget_call_id
            ):
                # Accumulate silently — no UI updates during streaming
                delta = widget_extractor.feed(event.delta)
                if delta:
                    widget_code += delta

            elif isinstance(event, FunctionCallArgsDoneEvent):
                if isinstance(event.item, WebSearchFunctionCall):
                    yield "thought", f"{event.item.as_str}\n\n"
                elif (
                    isinstance(event.item, CustomFunctionCall)
                    and event.item.name == ToolNames.INLINE_CITATIONS_TOOL
                ):
                    try:
                        params = InlineCitationsParameters.model_validate_json(
                            event.item.arguments,
                        )
                        mp_chunk_snippets.update(
                            mp_chunk_id_snippets_from_items(params.citations),
                        )
                        yield "citations", mp_chunk_snippets
                    except Exception:
                        pass
                elif (
                    isinstance(event.item, CustomFunctionCall)
                    and event.item.name == ToolNames.VISUALIZE_SHOW_WIDGET_TOOL
                ):
                    try:
                        params = VisualizeShowWidgetParameters.model_validate_json(
                            event.item.arguments
                        )
                        final_code = params.widget_code or widget_code
                        if final_code:
                            yield "widget_title", params.title or ""
                            yield "widget", final_code
                    except Exception:
                        if widget_code:
                            yield "widget_title", ""
                            yield "widget", widget_code

            elif isinstance(event, FunctionCallTextDeltaEvent):
                yield "thought", event.delta
            elif isinstance(event, TextDeltaEvent):
                yield "text", event.content

    async def fetch_chunks_by_ids(
        self,
        chunk_ids: list[str],
    ) -> list[ScoredChunk]:
        """Fetch exact chunks from Milvus by their chunk IDs."""
        if not chunk_ids:
            return []
        scored = await self.container.vectordbs.get(
            VectorDBModel.MILVUS,
        ).retrieve_by_filter(
            filtered_dict={AnchorFields.ID: chunk_ids},
        )
        id_order = {cid: i for i, cid in enumerate(chunk_ids)}
        return sorted(
            scored.root,
            key=lambda s: id_order.get(str(s.chunk.chunk_id), 9999),
        )


def render_chunks_html(chunks: list[ScoredChunk]) -> str:
    if not chunks:
        return "<p class='info-empty'>No chunks to display.</p>"
    parts: list[str] = []
    total = len(chunks)
    for idx, scored in enumerate(chunks, start=1):
        meta = scored.chunk.metadata
        page = ""
        if isinstance(meta, DocumentMetadata):
            page = f"Page {meta.pageidx}"
        header = f"▼ [{idx}/{total}] [{page}] (text) {html.escape(scored.text[:80])}..."
        body = html.escape(scored.text)
        parts.append(
            f"<details class='evidence' open>"
            f"<summary>{header}</summary>"
            f"<div class='evidence-content'>"
            f"<pre class='chunk-body'>{body}</pre>"
            f"</div></details>",
        )
    return "\n".join(parts)


def render_info_panel(chunks: list[ScoredChunk]) -> str:
    """Render source chunks as collapsible evidence panels with anchors."""
    if not chunks:
        return "<p class='info-empty'>No sources retrieved.</p>"
    parts: list[str] = []
    for idx, scored in enumerate(chunks, start=1):
        meta = scored.chunk.metadata
        filename = "unknown"
        page = ""
        if isinstance(meta, DocumentMetadata):
            filename = meta.filename
            page = f"Page {meta.pageidx}"
        chunk_id = str(scored.chunk.chunk_id)
        summary = (
            f"<span class='citation-idx'>source-{idx}</span> "
            f"[{page}] {html.escape(filename)} "
            f"<span class='score-badge'>"
            f"[score: {scored.score:.1f}]</span>"
        )
        body = render_highlighted_body(scored.text[:800])
        parts.append(
            f"<details id='chunk-{chunk_id}' class='evidence' open>"
            f"<summary>{summary}</summary>"
            f"<div class='evidence-content'>"
            f"<pre>{body}</pre>"
            f"</div></details>",
        )
    return "\n".join(parts)


def build_citation_map(chunks: list[ScoredChunk]) -> dict[str, str]:
    """Map chunk_id → sequential index label, e.g. 'source-1'."""
    mp: dict[str, str] = {}
    for idx, scored in enumerate(chunks, start=1):
        chunk_id = str(scored.chunk.chunk_id)
        mp[chunk_id] = f"source-{idx}"
    return mp


def parse_cited_chunk_ids(response: str) -> list[str]:
    """Extract unique chunk IDs from <CITE>...</CITE> tags, preserving order."""
    seen: set[str] = set()
    ids: list[str] = []
    for raw in re.findall(r"<CITE>(.*?)</CITE>", response, re.DOTALL):
        cid = raw.strip()
        if cid and cid not in seen:
            seen.add(cid)
            ids.append(cid)
    return ids


def enrich_citations(response: str, citation_map: dict[str, str]) -> str:
    """Replace <CITE>chunk_id</CITE> with styled anchor links."""

    def _replace(m: re.Match[str]) -> str:
        chunk_id = m.group(1).strip()
        label = citation_map.get(chunk_id, "source")
        return (
            f"<a class='citation' href='#chunk-{chunk_id}' "
            f"onclick=\"scrollToChunk('{chunk_id}');return false;\">"
            f"{html.escape(label)}</a>"
        )

    return re.sub(r"<CITE>(.*?)</CITE>", _replace, response, flags=re.DOTALL)
