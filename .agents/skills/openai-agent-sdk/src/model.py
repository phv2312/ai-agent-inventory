from functools import cached_property
from pathlib import Path
from typing import Literal

from agents import OpenAIResponsesModel, ShellExecutor as ShellExecutorT
from openai import AsyncAzureOpenAI
from pydantic_settings import BaseSettings, SettingsConfigDict


class AzureOpenAISettings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False)

    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_DEPLOYMENT: str
    AZURE_OPENAI_API_VERSION: str = "2025-03-01-preview"

    OPENAI_AGENTS_DISABLE_TRACING: Literal[0, 1] = 1


class Container:
    def __init__(
        self,
        cwd: Path | None = None,
        settings: AzureOpenAISettings | None = None,
    ) -> None:
        self.cwd = cwd
        self.settings = settings or AzureOpenAISettings()

    @cached_property
    def async_azure_openai(self) -> AsyncAzureOpenAI:
        return AsyncAzureOpenAI(
            api_key=self.settings.AZURE_OPENAI_API_KEY,
            api_version=self.settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
        )

    @cached_property
    def chat_model(self) -> OpenAIResponsesModel:
        return OpenAIResponsesModel(
            model=self.settings.AZURE_OPENAI_DEPLOYMENT,
            openai_client=self.async_azure_openai,
        )

    @cached_property
    def shell_executor(self) -> ShellExecutorT:
        from shell import ShellExecutor

        return ShellExecutor(self.cwd)


container = Container()
