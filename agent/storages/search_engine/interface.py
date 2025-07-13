from collections.abc import Sequence
from typing import Any, Protocol

from agent.models.document import Chunk, ScoredChunks


class ISearchEngine(Protocol):
    async def add(self, chunks: Sequence[Chunk]) -> None: ...

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filtered_dict: dict[str, list[str | int]] | None = None,
        **__: Any,
    ) -> ScoredChunks: ...
