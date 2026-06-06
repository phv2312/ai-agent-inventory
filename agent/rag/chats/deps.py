from dataclasses import dataclass

from agent.chats.interface import IChatModel
from agent.embeddings.interface import IEmbeddingModel
from agent.storages.vectordb.milvus import Milvus


@dataclass
class ChatDeps:
    vectordb: Milvus
    embedding_model: IEmbeddingModel
    stream_provider: IChatModel
