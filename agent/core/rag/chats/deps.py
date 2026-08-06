from dataclasses import dataclass

from agent.core.embeddings.interface import IEmbeddingModel
from agent.core.storages.vectordb.milvus import Milvus


@dataclass
class ChatDeps:
    vectordb: Milvus
    embedding_model: IEmbeddingModel
