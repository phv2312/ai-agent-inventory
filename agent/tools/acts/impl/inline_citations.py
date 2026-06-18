import json
from typing import Literal

from agent.citations.matcher import find_quote_span
from agent.models.streams import FunctionCallOutput
from agent.storages.config import AnchorFields
from agent.storages.vectordb.milvus import Milvus
from agent.tools.acts.models import BaseToolCall, IToolAct, ToolActResult
from agent.tools.schemas.registry import InlineCitationsParameters, ToolNames


class InlineCitationsToolCall(BaseToolCall[InlineCitationsParameters]):
    name: Literal[ToolNames.INLINE_CITATIONS_TOOL] = ToolNames.INLINE_CITATIONS_TOOL


class InlineCitationsAct(IToolAct[InlineCitationsToolCall]):
    def __init__(self, milvus: Milvus) -> None:
        self.milvus = milvus

    async def act(self, tool_call: InlineCitationsToolCall) -> ToolActResult:
        yield (f"Validating {len(tool_call.params.citations)} inline citation(s)\n\n")

        validated: list[dict[str, object]] = []
        rejected: list[dict[str, str]] = []

        for item in tool_call.params.citations:
            chunk_id = str(item.chunk_id).strip()
            scored = await self.milvus.retrieve_by_filter(
                {AnchorFields.ID: [chunk_id]},
            )
            if len(scored.root) == 0:
                rejected.append(
                    {
                        "chunk_id": chunk_id,
                        "reason": "chunk_id not found in knowledge base",
                    },
                )
                continue

            chunk_text = scored.root[0].text
            accepted_snippets: list[str] = []
            for snippet in item.snippets:
                quote = snippet.strip()
                if not quote:
                    continue
                if quote in chunk_text or find_quote_span(chunk_text, quote):
                    accepted_snippets.append(snippet)
                else:
                    rejected.append(
                        {
                            "chunk_id": chunk_id,
                            "reason": (
                                f"snippet not found in chunk text: {quote[:80]}"
                            ),
                        },
                    )

            if accepted_snippets:
                validated.append(
                    {
                        "chunk_id": chunk_id,
                        "snippets": accepted_snippets,
                    },
                )

        payload = {
            "validated": validated,
            "rejected": rejected,
        }
        yield FunctionCallOutput(
            call_id=tool_call.id,
            output=json.dumps(payload, ensure_ascii=False),
        )
