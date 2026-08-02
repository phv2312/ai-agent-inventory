from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageEnv(BaseSettings):
    DATA_DIR: Path = Path(".agent-api-data")


class OpenAISettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
    )

    OPENAI_API_KEY: str
    OPENAI_AZURE_ENDPOINT: str
    OPENAI_API_VERSION: str
    OPENAI_AGENTS_DISABLE_TRACING: bool = True


class OpenAIChatSettings(OpenAISettings):
    OPENAI_CHAT_DEPLOYMENT_NAME: str

    # Per million token cost
    OPENAI_CHAT_INPUT_TOKEN_COST: float = 1.75
    OPENAI_CHAT_OUTPUT_TOKEN_COST: float = 14.0


class OpenAIEmbeddingSettings(OpenAISettings):
    OPENAI_EMBEDDING_DEPLOYMENT_NAME: str


class ContextGenerationSettings(BaseSettings):
    USE_IMAGE_CONTEXT: bool = False
    IMAGE_DETAIL: Literal["low", "auto", "high"] = "auto"


class MilvusSettings(StorageEnv):
    MILVUS_DB_COLLECTION_NAME: str
    MILVUS_DB_URI: Path = Path("milvus.db")

    def resolved_milvus_db_uri(self) -> str:
        uri = self.MILVUS_DB_URI
        if uri.is_absolute() or ".." in uri.parts:
            raise ValueError("MILVUS_DB_URI must be relative to DATA_DIR")
        return str((self.DATA_DIR / uri).resolve())


class PhoenixSettings(BaseSettings):
    PHOENIX_TRACING_ENABLED: bool = False
    PHOENIX_PROJECT_NAME: str = "agent-demo"
    PHOENIX_ENDPOINT: str = "http://localhost:6006/v1/traces"
    PHOENIX_PROTOCOL: Literal["http/protobuf", "grpc"] = "http/protobuf"


class Env(
    ContextGenerationSettings,
    OpenAIChatSettings,
    OpenAIEmbeddingSettings,
    MilvusSettings,
    PhoenixSettings,
    BaseSettings,
):
    model_config = SettingsConfigDict(case_sensitive=False)
