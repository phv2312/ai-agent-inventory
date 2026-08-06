from pathlib import Path
from typing import Any, Protocol

from ..models.document import Document


class IExtractor(Protocol):
    async def aextract(
        self, filepath: Path, fileid: str, *_: Any, **__: Any
    ) -> Document: ...
