from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, env_prefix="AGENT_API_")

    DATA_DIR: Path = Field(default=Path(".agent-api-data"))
    DATABASE_URL: str | None = None
    MAX_UPLOAD_BYTES: int = Field(default=50 * 1024 * 1024)
    MAX_MESSAGE_LENGTH: int = Field(default=32_000)
    MAX_CHUNK_IDS: int = Field(default=50)
    MAX_SNIPPETS: int = Field(default=20)
    DEFAULT_PAGE_LIMIT: int = Field(default=20)
    DEFAULT_HISTORY_INTERACTIONS: int = Field(default=5)
    INDEXING_CONSUMER_COUNT: int = Field(default=2, ge=1)

    def resolved_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        db_path = self.DATA_DIR / "agent-api.db"
        return f"sqlite+aiosqlite:///{db_path.resolve()}"
