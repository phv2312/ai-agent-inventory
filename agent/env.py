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


class OpenAIEmbeddingSettings(OpenAISettings):
    OPENAI_EMBEDDING_DEPLOYMENT_NAME: str


class MilvusSettings(BaseSettings):
    MILVUS_DB_COLLECTION_NAME: str
    MILVUS_DB_URI: str


class TavilyWebSearchSettings(BaseSettings):
    TAVILY_API_KEY: str


class AnthropicSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
    )

    ANTHROPIC_API_KEY: str = ""


class Env(
    OpenAIChatSettings,
    OpenAIEmbeddingSettings,
    MilvusSettings,
    TavilyWebSearchSettings,
    AnthropicSettings,
    BaseSettings,
):
    model_config = SettingsConfigDict(case_sensitive=False)
