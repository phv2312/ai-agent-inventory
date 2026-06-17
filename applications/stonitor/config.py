"""Stonitor application settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_STONITOR_DIR = Path(__file__).resolve().parent
_DEFAULT_SQLITE_PATH = _STONITOR_DIR / "data" / "stonitor.db"


class StonitorSettings(BaseSettings):
    """Environment configuration for Stonitor."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        extra="ignore",
    )

    DATABASE_URL: str = f"sqlite:///{_DEFAULT_SQLITE_PATH.as_posix()}"
    VNSTOCK_API_KEY: str = ""
    TAVILY_API_KEY: str = ""
    ANALYZE_INTERVAL_MINUTES: int = 30
    NEWS_INGEST_INTERVAL_HOURS: int = 1
    GRADIO_SERVER_PORT: int = 7860
