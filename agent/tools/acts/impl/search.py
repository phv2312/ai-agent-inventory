from typing import Literal

from rich.console import Console
from rich.panel import Panel

from agent.embeddings.interface import IEmbeddingModel
from agent.models.streams import FunctionCallOutput
from agent.storages.config import AnchorFields
from agent.storages.vectordb.milvus import Milvus
from agent.tools.acts.models import BaseToolCall, IToolAct, ToolActResult
from agent.tools.schemas.registry import SearchParameters, ToolNames

console = Console()


class SearchToolCall(BaseToolCall[SearchParameters]):
    name: Literal[ToolNames.SEARCH_TOOL] = ToolNames.SEARCH_TOOL


class SearchAct(IToolAct[SearchToolCall]):
    def __init__(
        self,
        milvus: Milvus,
        embedding_model: IEmbeddingModel,
        file_ids: list[str],
        top_k: int = 10,
    ) -> None:
        self.milvus = milvus
        self.embedding_model = embedding_model
        self.file_ids = file_ids
        self.top_k = top_k

    async def act(self, tool_call: SearchToolCall) -> ToolActResult:
        yield f"Internal Search: {tool_call.params.query}\n\n"

        embeddings = await self.embedding_model.embed(
            [tool_call.params.query],
        )
        if len(embeddings) == 0:
            raise ValueError("Query embedding is empty")

        filtered_dict: dict[str, list[str | int]] | None = None
        if self.file_ids:
            filtered_dict = {AnchorFields.FILE_ID: list(self.file_ids)}
        if tool_call.params.doc_names:
            filtered_dict = {
                **(filtered_dict or {}),
                AnchorFields.FILE_NAME: list(tool_call.params.doc_names),
            }

        scored_chunks = await self.milvus.search(
            query=embeddings[0],
            top_k=self.top_k,
            filtered_dict=filtered_dict,
        )

        response_parts: list[str] = []
        for scored_chunk in scored_chunks.root:
            metadata = scored_chunk.chunk.metadata.model_dump()
            response_parts.append(
                (
                    f"Document: {metadata.get('filename', '')}\n\n"
                    f"Chunk-ID: {scored_chunk.chunk.chunk_id}\n\n"
                    f"Source: Internal\n\n"
                    f"{scored_chunk.text}"
                ),
            )

        response_text = (
            "\n\n---\n\n".join(response_parts)
            or "No data. Try another query or escalate to web search."
        )

        yield FunctionCallOutput(
            call_id=tool_call.id,
            output=response_text,
        )

        console.print(
            Panel(
                (
                    f"Search Result (granularity: "
                    f"{tool_call.params.granularity})\n"
                    f"{response_text[:1000]}..."
                ),
                title="🔍 Search Result",
                style="bold magenta",
            ),
        )
