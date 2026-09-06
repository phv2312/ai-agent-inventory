from dataclasses import dataclass

from agents.models.openai_responses import OpenAIResponsesModel
from pydantic import BaseModel, Field

from agent.core.embeddings.interface import IEmbeddingModel
from agent.core.models.messages import Messages
from agent.core.storages.vectordb.milvus import Milvus


class RunInput(BaseModel):
    query: str = Field(min_length=1)
    file_ids: list[str] = Field(default_factory=list)
    history: Messages = Field(default_factory=lambda: Messages(root=[]))
    memory_md_content: str = ""
    top_k: int = Field(default=10, ge=1)
    web_search_enabled: bool = False
    global_query: bool = False


@dataclass
class AgentDeps:
    vectordb: Milvus
    embedding_model: IEmbeddingModel
    model: OpenAIResponsesModel
