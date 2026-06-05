from typing import Any, Protocol

from agent.models.document import ScoredChunks


class IWebSearch(Protocol):
    async def asearch(
        self,
        query: str,
        *args: Any,
        **kwargs: Any,
    ) -> ScoredChunks: ...
