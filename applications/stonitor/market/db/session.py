"""Database session factory."""

from collections.abc import Callable, Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from applications.stonitor.config import StonitorSettings


def _is_sqlite(database_url: str) -> bool:
    return make_url(database_url).drivername == "sqlite"


def create_db_engine(database_url: str) -> Engine:
    """Create SQLAlchemy engine from database URL."""
    connect_args: dict[str, object] = {}
    if _is_sqlite(database_url):
        connect_args["check_same_thread"] = False
    engine = create_engine(
        database_url,
        pool_pre_ping=not _is_sqlite(database_url),
        connect_args=connect_args,
    )
    if _is_sqlite(database_url):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection: object, _: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create session factory bound to engine."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def build_session_factory(
    settings: StonitorSettings | None = None,
) -> tuple[Engine, sessionmaker[Session]]:
    """Build engine and session factory from settings."""
    cfg = settings or StonitorSettings()
    engine = create_db_engine(cfg.DATABASE_URL)
    return engine, create_session_factory(engine)


SessionFactory = Callable[[], Session]
