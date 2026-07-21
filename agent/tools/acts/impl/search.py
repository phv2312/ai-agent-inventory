from collections.abc import Sequence
from typing import Literal, Self

from rich.console import Console
from rich.panel import Panel

from agent.embeddings.interface import IEmbeddingModel
from agent.models.document import ScoredChunks
from agent.models.streams import (
    FunctionCallOutput,
    ImageItemOutput,
    ItemOutput,
    TextItemOutput,
)
from agent.storages.config import AnchorFields
from agent.storages.vectordb.milvus import Milvus
from agent.tools.acts.models import BaseToolCall, IToolAct, ToolActResult
from agent.tools.schemas.registry import SearchParameters, ToolNames
from agent.tracer import tool_span, tracer_provider

console = Console()
tracer = tracer_provider.get_tracer(__name__)


def convert_to_base64(remotepath: str) -> str:
    import mimetypes
    import base64

    from agent.deps.container import container

    path = container.storage.get_localpath(remotepath)

    mime_type, _ = mimetypes.guess_type(path.name)
    mime_type = mime_type or "application/octet-stream"

    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


class TextFunctionOutput(FunctionCallOutput):
    @classmethod
    def from_chunks(cls, tool_id: str, scored_chunks: ScoredChunks) -> Self:
        response_parts: list[str] = []
        for scored_chunk in scored_chunks.iter():
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

        return cls(
            call_id=tool_id,
            output=[TextItemOutput(text=response_text)],
        )


class ImageFunctionOutput(FunctionCallOutput):
    @classmethod
    def from_chunks(
        cls,
        tool_id: str,
        scored_chunks: ScoredChunks,
        detail: Literal["low", "auto", "high"] = "auto",
    ) -> Self:
        output: list[ItemOutput] = []
        image_paths: set[str] = set()

        for scored_chunk in scored_chunks.iter():
            metadata = scored_chunk.chunk.metadata

            # de-dup
            image_path = metadata.rendered_page_path
            if image_path in image_paths:
                continue

            output.append(
                TextItemOutput(
                    text=(
                        f"Document: {metadata.filename}\n\n"
                        f"Chunk-ID: {scored_chunk.chunk.chunk_id}\n\n"
                        "Source: Internal\n\n"
                    ),
                ),
            )

            image_paths.add(image_path)
            output.append(
                ImageItemOutput(image_url=convert_to_base64(image_path), detail=detail)
            )

        if not output:
            output.append(
                TextItemOutput(
                    text="No data. Try another query or escalate to web search.",
                ),
            )

        return cls(call_id=tool_id, output=output)


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
        from agent.deps.container import container

        use_image = container.env.USE_IMAGE_CONTEXT
        image_detail = container.env.IMAGE_DETAIL

        with tool_span(tracer, "SearchAct.act", tool_call) as span:
            yield f"Internal Search: {tool_call.params.query}, Use Image: {use_image}[{image_detail}]\n\n"

            embeddings = await self.embedding_model.embed(
                [tool_call.params.query],
            )
            if len(embeddings) == 0:
                raise ValueError("Query embedding is empty")

            filtered_dict: dict[str, Sequence[str | int]] | None = None
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

            output: FunctionCallOutput
            if use_image:
                output = ImageFunctionOutput.from_chunks(
                    tool_call.id,
                    scored_chunks,
                    image_detail,
                )
            else:
                output = TextFunctionOutput.from_chunks(
                    tool_call.id,
                    scored_chunks,
                )
            span.set_output(output)
            yield output

            console.print(
                Panel(
                    (f"Search Result (granularity: {tool_call.params.granularity})\n"),
                    title="🔍 Search Result",
                    style="bold magenta",
                ),
            )
