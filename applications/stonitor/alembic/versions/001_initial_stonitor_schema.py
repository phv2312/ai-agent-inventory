"""initial stonitor schema

Revision ID: 001_initial
Revises:
Create Date: 2026-06-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False)


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column(
            "exchange",
            _enum("exchange_enum", "HOSE", "HNX", "UPCOM"),
            nullable=True,
        ),
        sa.Column("sector", sa.String(length=64), nullable=True),
        sa.Column("is_tracked", sa.Boolean(), nullable=False),
        sa.Column("is_watchlisted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker"),
    )
    op.create_table(
        "price_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("high", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("low", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("close", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "timestamp", name="uq_price_ts"),
    )
    op.create_table(
        "fundamental_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("revenue_growth", sa.Float(), nullable=True),
        sa.Column("eps", sa.Float(), nullable=True),
        sa.Column("net_margin", sa.Float(), nullable=True),
        sa.Column("pe_ratio", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "ingested_at", name="uq_fundamental_ingest"),
    )
    op.create_table(
        "news_articles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url", name="uq_news_url"),
    )
    op.create_table(
        "signals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column(
            "signal_type",
            _enum(
                "signal_type_enum",
                "trend",
                "momentum",
                "volatility",
                "fundamental",
                "sentiment",
            ),
            nullable=False,
        ),
        sa.Column(
            "category",
            _enum("signal_category_enum", "technical", "fundamental", "news"),
            nullable=False,
        ),
        sa.Column("value", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column(
            "alert_type",
            _enum(
                "alert_type_enum",
                "volume_spike",
                "volatility_spike",
                "sentiment_spike",
                "trend_reversal",
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            _enum("alert_severity_enum", "low", "medium", "high"),
            nullable=False,
        ),
        sa.Column(
            "status",
            _enum("alert_status_enum", "active", "acknowledged"),
            nullable=False,
        ),
        sa.Column("z_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=True),
        sa.Column(
            "run_type",
            _enum(
                "run_type_enum",
                "analysis",
                "price_ingest",
                "news_ingest",
                "signal_calc",
                "alert_gen",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            _enum("run_status_enum", "started", "completed", "failed"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("analysis_runs")
    op.drop_table("alerts")
    op.drop_table("signals")
    op.drop_table("news_articles")
    op.drop_table("fundamental_snapshots")
    op.drop_table("price_snapshots")
    op.drop_table("assets")
