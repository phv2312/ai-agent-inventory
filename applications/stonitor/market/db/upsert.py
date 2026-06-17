"""Dialect-specific INSERT helpers for upsert operations."""

from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.sql.dml import Insert


def dialect_insert(session: Session, table: Any) -> Insert:
    """Return an INSERT construct with ON CONFLICT support."""
    dialect_name = session.get_bind().dialect.name
    if dialect_name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert

        return insert(table)
    if dialect_name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert

        return insert(table)
    msg = f"Upsert not supported for dialect: {dialect_name}"
    raise NotImplementedError(msg)
