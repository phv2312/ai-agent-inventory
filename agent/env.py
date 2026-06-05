from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAISettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
    )

    openai_api_key: str
    openai_azure_endpoint: str
    openai_api_version: str


class OpenAIChatSettings(OpenAISettings):
    openai_chat_deployment_name: str


class OpenAIEmbeddingSettings(OpenAISettings):
    openai_embedding_deployment_name: str


class MilvusSettings(BaseSettings):
    milvus_collection_name: str
    milvus_uri: str
    milvus_token: str


class TavilyWebSearchSettings(BaseSettings):
    tavily_api_key: str


class AnthropicSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
    )

    anthropic_api_key: str = ""


class Env(
    OpenAIChatSettings,
    OpenAIEmbeddingSettings,
    MilvusSettings,
    TavilyWebSearchSettings,
    AnthropicSettings,
    BaseSettings,
):
    model_config = SettingsConfigDict(case_sensitive=False)
