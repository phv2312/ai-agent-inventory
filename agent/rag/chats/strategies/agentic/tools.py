from collections.abc import Sequence
from typing import Annotated, Literal

from agents import Tool, WebSearchTool, function_tool
from pydantic import Field

from agent.embeddings.interface import IEmbeddingModel
from agent.models.document import ScoredChunks
from agent.storages.config import AnchorFields
from agent.storages.vectordb.milvus import Milvus

type VisualizeModule = Literal[
    "interactive",
    "chart",
    "diagram",
    "mockup",
    "art",
]


def _format_chunks(chunks: ScoredChunks) -> str:
    # Format retrieved chunks as model-readable, citation-ready context.
    parts: list[str] = []
    for scored_chunk in chunks.iter():
        metadata = scored_chunk.chunk.metadata.model_dump()
        parts.append(
            "\n\n".join(
                (
                    f"Document: {metadata.get('filename', '')}",
                    f"Chunk-ID: {scored_chunk.chunk.chunk_id}",
                    "Source: Internal",
                    scored_chunk.text,
                )
            )
        )
    return "\n\n---\n\n".join(parts) or "No data. Try another query."


def build_tools(
    *,
    vectordb: Milvus,
    embedding_model: IEmbeddingModel,
    file_ids: list[str],
    top_k: int,
    visualization_guidance: dict[VisualizeModule, str],
    visualization_readme: str,
    web_search_enabled: bool,
) -> list[Tool]:
    # Build request-scoped OpenAI Agents SDK tools.

    @function_tool
    async def internal_search_tool(
        query: Annotated[str, Field(description="One focused evidence-seeking query")],
        granularity: Annotated[
            str,
            Field(description="section, page, or document"),
        ],
        doc_names: Annotated[
            list[str] | None,
            Field(description="Optional document-name filters"),
        ] = None,
    ) -> str:
        # Search the internal knowledge base and return citation-ready chunks.
        embeddings = await embedding_model.embed([query])
        if not embeddings:
            raise ValueError("Query embedding is empty")
        filters: dict[str, Sequence[str | int]] = {}
        if file_ids:
            filters[AnchorFields.FILE_ID] = file_ids
        if doc_names:
            filters[AnchorFields.FILE_NAME] = doc_names
        chunks = await vectordb.search(
            query=embeddings[0],
            top_k=top_k,
            filtered_dict=filters or None,
        )
        return _format_chunks(chunks)

    @function_tool
    async def think_tool(
        reflection: Annotated[
            str,
            Field(description="Private concise reasoning and retrieval plan"),
        ],
    ) -> str:
        # Record a concise private reasoning and retrieval plan.
        return reflection

    @function_tool
    async def visualize_read_me(
        modules: Annotated[
            list[VisualizeModule],
            Field(description="Visualization modules required for the response"),
        ],
    ) -> str:
        # Load only the application's requested inline visualization guidance.
        merged_guidance = "\n\n---\n\n".join(
            visualization_guidance[module] for module in modules
        )
        return visualization_readme.replace("{vis_templates}", merged_guidance)

    tools: list[Tool] = [visualize_read_me]
    if file_ids:
        tools.extend((internal_search_tool, think_tool))
    if web_search_enabled:
        tools.append(WebSearchTool(search_context_size="high"))
    return tools
