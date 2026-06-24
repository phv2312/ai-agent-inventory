from pydantic import BaseModel


class ChunkItemResponse(BaseModel):
    id: str
    text: str | None = None
    metadata: dict[str, object] | None = None
    status: str
    warnings: list[str] | None = None


class ChunksBatchResponse(BaseModel):
    items: list[ChunkItemResponse]
