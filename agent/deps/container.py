from abc import ABC, abstractmethod
from functools import cached_property, lru_cache
from typing import Any, Callable

from agents.models.openai_responses import OpenAIResponsesModel
from agent.programs import BaseProgram, NameSuggestionProgram
from agent.textsplitters import (
    ITextSplitter,
    LangchainTextSplitter,
)
from openai import AsyncAzureOpenAI

from agent.rag.chats.deps import ChatDeps
from agent.rag.chats.strategies.agentic import AgenticChatStrategy
from agent.rag.chats.strategies.agentic.core import AgenticSettings
from agent.embeddings import IEmbeddingModel, SmallOpenAIEmbeddingModel
from agent.extractors import (
    IExtractor,
    PDFExtractor,
)
from agent.storages.vectordb import Milvus
from agent.env import Env
from agent.storages.files.impl.local import LocalFileStorage
from agent.storages.files.interface import IFileStorage

from .models import (
    EmbeddingModel,
    ProgramsModel,
    TextSplitterModel,
    ExtractorModel,
    VectorDBModel,
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
    def __init__(self, env: Env, model: OpenAIResponsesModel) -> None:
        self.env = env
        self.model = model

    @property
    def mp_name_init(self) -> MPReturn[ProgramsModel, BaseProgram[Any]]:
        return {
            ProgramsModel.NAME_SUGGESTION: self.init_name_suggestion,
        }

    @lru_cache(maxsize=1)
    def init_name_suggestion(self) -> NameSuggestionProgram:
        return NameSuggestionProgram(
            model=self.model,
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
        storage: IFileStorage,
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
            uri=self.env.resolved_milvus_db_uri(),
            collection_name=self.env.MILVUS_DB_COLLECTION_NAME,
        )


class AgenticStrategyProvider:
    def __init__(
        self,
        env: Env,
        vectordb_provider: VectorDBProvider,
        embedding_provider: EmbeddingProvider,
        model: OpenAIResponsesModel,
    ) -> None:
        self.env = env
        self.vectordb_provider = vectordb_provider
        self.embedding_provider = embedding_provider
        self.model = model

    def get(self) -> AgenticChatStrategy:
        return AgenticChatStrategy(
            deps=ChatDeps(
                vectordb=self.vectordb_provider.get(VectorDBModel.MILVUS),
                embedding_model=self.embedding_provider.get(
                    EmbeddingModel.AZURE_OPENAI
                ),
            ),
            model=self.model,
            settings=AgenticSettings(
                model_name=self.env.OPENAI_CHAT_DEPLOYMENT_NAME,
            ),
        )


class Container:
    def __init__(
        self, env: Env | None = None, storage: IFileStorage | None = None
    ) -> None:
        self.env = env or Env()
        self.storage = storage or LocalFileStorage(self.env.DATA_DIR)

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
    def model(self) -> OpenAIResponsesModel:
        client = AsyncAzureOpenAI(
            api_key=self.env.OPENAI_API_KEY,
            api_version=self.env.OPENAI_API_VERSION,
            azure_endpoint=self.env.OPENAI_AZURE_ENDPOINT,
        )
        return OpenAIResponsesModel(
            model=self.env.OPENAI_CHAT_DEPLOYMENT_NAME,
            openai_client=client,
        )

    @cached_property
    def agentic(self) -> AgenticStrategyProvider:
        return AgenticStrategyProvider(
            self.env,
            self.vectordbs,
            self.embeddings,
            self.model,
        )

    @cached_property
    def programs(self) -> ProgramsProvider:
        return ProgramsProvider(self.env, self.model)


container = Container()
