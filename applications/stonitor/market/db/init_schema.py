"""Database schema initialization."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url


def _stonitor_root() -> Path:
    return Path(__file__).resolve().parents[2]


def ensure_sqlite_directory(database_url: str) -> None:
    """Create parent directory for SQLite file databases."""
    url = make_url(database_url)
    if url.drivername != "sqlite" or not url.database or url.database == ":memory:":
        return
    db_path = Path(url.database)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)


def ensure_schema(database_url: str) -> None:
    """Apply Alembic migrations when schema is missing or outdated."""
    ensure_sqlite_directory(database_url)
    root = _stonitor_root()
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, "head")
