from collections.abc import Sequence
from typing import Annotated

from agents import function_tool, Tool
from pydantic import Field

from agent.core.embeddings.interface import IEmbeddingModel
from agent.core.models.document import ScoredChunks
from agent.core.storages.config import AnchorFields
from agent.core.storages.vectordb.milvus import Milvus


def build_search_tool(
    vectordb: Milvus,
    embedding_model: IEmbeddingModel,
    file_ids: list[str],
    top_k: int,
) -> Tool:
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

    @function_tool
    async def internal_search_tool(
        query: Annotated[str, Field(description="One focused evidence-seeking query")],
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

    return internal_search_tool


@function_tool
async def think_tool(
    reflection: Annotated[
        str,
        Field(description="Private concise reasoning and retrieval plan"),
    ],
) -> str:
    # Record a concise private reasoning and retrieval plan.
    return reflection
