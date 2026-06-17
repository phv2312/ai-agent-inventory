"""add news article content column

Revision ID: 004_add_news_content
Revises: 003_drop_alerts
Create Date: 2026-06-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_add_news_content"
down_revision: Union[str, None] = "003_drop_alerts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("news_articles")}
    if "content" in columns:
        return
    op.add_column(
        "news_articles",
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("news_articles", "content")
