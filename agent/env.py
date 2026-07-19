from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAISettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
    )

    OPENAI_API_KEY: str
    OPENAI_AZURE_ENDPOINT: str
    OPENAI_API_VERSION: str


class OpenAIChatSettings(OpenAISettings):
    OPENAI_CHAT_DEPLOYMENT_NAME: str

    # Per million token cost
    OPENAI_CHAT_INPUT_TOKEN_COST: float = 1.75
    OPENAI_CHAT_OUTPUT_TOKEN_COST: float = 14.0


class OpenAIEmbeddingSettings(OpenAISettings):
    OPENAI_EMBEDDING_DEPLOYMENT_NAME: str


class MilvusSettings(BaseSettings):
    MILVUS_DB_COLLECTION_NAME: str
    MILVUS_DB_URI: str


class AnthropicSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
    )

    ANTHROPIC_API_KEY: str = ""


class PhoenixSettings(BaseSettings):
    PHOENIX_TRACING_ENABLED: bool = False
    PHOENIX_PROJECT_NAME: str = "agent-demo"
    PHOENIX_ENDPOINT: str = "http://localhost:6006/v1/traces"
    PHOENIX_PROTOCOL: Literal["http/protobuf", "grpc"] = "http/protobuf"


class Env(
    OpenAIChatSettings,
    OpenAIEmbeddingSettings,
    MilvusSettings,
    AnthropicSettings,
    PhoenixSettings,
    BaseSettings,
):
    model_config = SettingsConfigDict(case_sensitive=False)
