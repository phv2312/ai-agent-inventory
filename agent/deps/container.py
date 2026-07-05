from abc import ABC, abstractmethod
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Any, Callable

from agent.programs import BaseProgram, NameSuggestionProgram
from agent.textsplitters import (
    ITextSplitter,
    LangchainTextSplitter,
)
from anthropic import AsyncAnthropic
from openai import AsyncAzureOpenAI

from agent.chats import IChatModel
from agent.chats.impl.anthropic import AnthropicProvider
from agent.chats.impl.openai import OpenAIProvider
from agent.rag.chats.deps import ChatDeps
from agent.rag.chats.strategies.agentic import AgenticChatStrategy
from agent.orchestrators.interface import IAgent
from agent.rag.chats.strategies.agentic.v1.core import AgenticSettings
from agent.tools.resolver import ToolResolver
from agent.embeddings import IEmbeddingModel, SmallOpenAIEmbeddingModel
from agent.extractors import (
    IExtractor,
    PDFExtractor,
)
from agent.storages.vectordb import Milvus
from agent.env import Env
from agent.storages.file import FileStorage

from .models import (
    EmbeddingModel,
    ProgramsModel,
    TextSplitterModel,
    ExtractorModel,
    VectorDBModel,
    ChatModel,
)

type MPReturn[NameT, ReturnT] = dict[NameT, Callable[[], ReturnT]]


class BaseProvider[NameT, ReturnT](ABC):
    @property
    def supported_models(self) -> list[NameT]:
        return list(self.mp_name_init.keys())

    @property
    @abstractmethod
    def mp_name_init(self) -> dict[NameT, Callable[[], ReturnT]]:
        raise NotImplementedError()

    def get(self, model_name: NameT) -> ReturnT:
        if model_name not in self.mp_name_init:
            raise ValueError(f"Unknown model name: {model_name}")

        return self.mp_name_init[model_name]()


class EmbeddingProvider(BaseProvider[EmbeddingModel, IEmbeddingModel]):
    def __init__(self, env: Env) -> None:
        self.env = env

    @property
    def mp_name_init(
        self,
    ) -> MPReturn[EmbeddingModel, IEmbeddingModel]:
        return {
            EmbeddingModel.AZURE_OPENAI: self.init_azure_openai,
        }

    @lru_cache(maxsize=1)
    def init_azure_openai(self) -> SmallOpenAIEmbeddingModel:
        return SmallOpenAIEmbeddingModel(
            api_key=self.env.OPENAI_API_KEY,
            api_version=self.env.OPENAI_API_VERSION,
            azure_endpoint=self.env.OPENAI_AZURE_ENDPOINT,
            deployment_name=self.env.OPENAI_EMBEDDING_DEPLOYMENT_NAME,
        )


class ProgramsProvider(BaseProvider[ProgramsModel, BaseProgram[Any]]):
    def __init__(self, env: Env, chat_provider: "ChatProvider") -> None:
        self.env = env
        self.chat_provider = chat_provider

    @property
    def mp_name_init(self) -> MPReturn[ProgramsModel, BaseProgram[Any]]:
        return {
            ProgramsModel.NAME_SUGGESTION: self.init_name_suggestion,
        }

    @lru_cache(maxsize=1)
    def init_name_suggestion(self) -> NameSuggestionProgram:
        return NameSuggestionProgram(
            chat_model=self.chat_provider.get(ChatModel.AZURE_OPENAI),
            model_name=self.env.OPENAI_CHAT_DEPLOYMENT_NAME,
        )


class TextSplitterProvider(
    BaseProvider[
        TextSplitterModel,
        ITextSplitter,
    ]
):
    def __init__(self, env: Env) -> None:
        self.env = env

    @property
    def mp_name_init(
        self,
    ) -> MPReturn[TextSplitterModel, ITextSplitter]:
        return {
            TextSplitterModel.LANGCHAIN: self.init_langchain_text_splitter,
        }

    @lru_cache(maxsize=1)
    def init_langchain_text_splitter(self) -> LangchainTextSplitter:
        return LangchainTextSplitter()


class ExtractorProvider(
    BaseProvider[
        ExtractorModel,
        IExtractor,
    ]
):
    def __init__(
        self,
        env: Env,
        storage: FileStorage,
        text_splitter_provider: TextSplitterProvider,
    ) -> None:
        self.env = env
        self.storage = storage
        self.text_splitter_provider = text_splitter_provider

    @property
    def mp_name_init(self) -> MPReturn[ExtractorModel, IExtractor]:
        return {
            ExtractorModel.PDF: self.init_pdf_extractor,
        }

    @lru_cache(maxsize=1)
    def init_pdf_extractor(self) -> PDFExtractor:
        return PDFExtractor(
            self.storage,
            self.text_splitter_provider.get(TextSplitterModel.LANGCHAIN),
        )


class VectorDBProvider(
    BaseProvider[
        VectorDBModel,
        Milvus,
    ]
):
    def __init__(self, env: Env) -> None:
        self.env = env

    @property
    def mp_name_init(self) -> MPReturn[VectorDBModel, Milvus]:
        return {
            VectorDBModel.MILVUS: self.init_milvus,
        }

    @lru_cache(maxsize=1)
    def init_milvus(self) -> Milvus:
        return Milvus(
            uri=self.env.MILVUS_DB_URI,
            collection_name=self.env.MILVUS_DB_COLLECTION_NAME,
        )


class ChatProvider(
    BaseProvider[ChatModel, IChatModel],
):
    def __init__(self, env: Env) -> None:
        self.env = env

    @property
    def mp_name_init(
        self,
    ) -> MPReturn[ChatModel, IChatModel]:
        return {
            ChatModel.AZURE_OPENAI: self.init_azure_openai,
            ChatModel.ANTHROPIC: self.init_anthropic,
        }

    @lru_cache(maxsize=1)
    def init_azure_openai(self) -> OpenAIProvider:
        client = AsyncAzureOpenAI(
            api_key=self.env.OPENAI_API_KEY,
            api_version=self.env.OPENAI_API_VERSION,
            azure_endpoint=self.env.OPENAI_AZURE_ENDPOINT,
        )
        return OpenAIProvider(client)

    @lru_cache(maxsize=1)
    def init_anthropic(self) -> AnthropicProvider:
        client = AsyncAnthropic(
            api_key=self.env.ANTHROPIC_API_KEY,
        )
        return AnthropicProvider(client)


class AgenticStrategyProvider:
    def __init__(
        self,
        env: Env,
        vectordb_provider: VectorDBProvider,
        embedding_provider: EmbeddingProvider,
        chat_provider: ChatProvider,
    ) -> None:
        self.env = env
        self.vectordb_provider = vectordb_provider
        self.embedding_provider = embedding_provider
        self.chat_provider = chat_provider

    def get(self) -> AgenticChatStrategy:
        return AgenticChatStrategy(
            deps=ChatDeps(
                vectordb=self.vectordb_provider.get(VectorDBModel.MILVUS),
                embedding_model=self.embedding_provider.get(
                    EmbeddingModel.AZURE_OPENAI
                ),
                stream_provider=self.chat_provider.get(ChatModel.AZURE_OPENAI),
            ),
            settings=AgenticSettings(
                model_name=self.env.OPENAI_CHAT_DEPLOYMENT_NAME,
            ),
        )


class ToolResolverProvider:
    def __init__(
        self,
        vectordb_provider: VectorDBProvider,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self.vectordb_provider = vectordb_provider
        self.embedding_provider = embedding_provider

    def get(
        self,
        *,
        file_ids: list[str],
        top_k: int = 10,
        agents: dict[str, IAgent] | None = None,
    ) -> ToolResolver:
        return ToolResolver(
            milvus=self.vectordb_provider.get(VectorDBModel.MILVUS),
            embedding_model=self.embedding_provider.get(
                EmbeddingModel.AZURE_OPENAI,
            ),
            file_ids=file_ids,
            top_k=top_k,
            mp_name_agent=agents or {},
        )


class Container:
    def __init__(
        self, env: Env | None = None, storage: FileStorage | None = None
    ) -> None:
        self.env = env or Env()
        self.storage = storage or FileStorage(imagedir=Path("images"))

    @cached_property
    def embeddings(self) -> EmbeddingProvider:
        return EmbeddingProvider(self.env)

    @cached_property
    def extractors(self) -> ExtractorProvider:
        return ExtractorProvider(
            self.env,
            self.storage,
            self.text_splitters,
        )

    @cached_property
    def vectordbs(self) -> VectorDBProvider:
        return VectorDBProvider(self.env)

    @cached_property
    def text_splitters(self) -> TextSplitterProvider:
        return TextSplitterProvider(self.env)

    @cached_property
    def chats(self) -> ChatProvider:
        return ChatProvider(self.env)

    @cached_property
    def tool_resolvers(self) -> ToolResolverProvider:
        return ToolResolverProvider(self.vectordbs, self.embeddings)

    @cached_property
    def agentic(self) -> AgenticStrategyProvider:
        return AgenticStrategyProvider(
            self.env,
            self.vectordbs,
            self.embeddings,
            self.chats,
        )

    @cached_property
    def programs(self) -> ProgramsProvider:
        return ProgramsProvider(self.env, self.chats)


container = Container()
