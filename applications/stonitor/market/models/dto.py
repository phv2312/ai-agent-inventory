"""Pydantic DTOs for Stonitor market domain."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from applications.stonitor.market.models.orm.enums import (
    Exchange,
    RunStatus,
    RunType,
    SignalCategory,
    SignalType,
)


class AssetDTO(BaseModel):
    id: UUID
    ticker: str
    exchange: Exchange | None
    sector: str | None
    is_watchlisted: bool
    created_at: datetime
    updated_at: datetime


class PriceSnapshotCreate(BaseModel):
    asset_id: UUID
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    ingested_at: datetime


class PriceSnapshotDTO(BaseModel):
    id: UUID
    asset_id: UUID
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    ingested_at: datetime


class FundamentalSnapshotCreate(BaseModel):
    asset_id: UUID
    revenue_growth: float | None
    eps: float | None
    net_margin: float | None
    pe_ratio: float | None
    source: str
    ingested_at: datetime


class FundamentalSnapshotDTO(BaseModel):
    id: UUID
    asset_id: UUID
    revenue_growth: float | None
    eps: float | None
    net_margin: float | None
    pe_ratio: float | None
    source: str
    ingested_at: datetime


class NewsArticleCreate(BaseModel):
    asset_id: UUID
    title: str
    content: str = ""
    source: str
    url: str
    sentiment_score: float
    published_at: datetime
    ingested_at: datetime


class NewsArticleDTO(BaseModel):
    id: UUID
    asset_id: UUID
    title: str
    content: str
    source: str
    url: str
    sentiment_score: float
    published_at: datetime
    ingested_at: datetime


class SignalCreate(BaseModel):
    asset_id: UUID
    signal_type: SignalType
    category: SignalCategory
    value: str
    score: float | None
    confidence: float
    evidence_json: dict
    created_at: datetime


class SignalDTO(BaseModel):
    id: UUID
    asset_id: UUID
    signal_type: SignalType
    category: SignalCategory
    value: str
    score: float | None
    confidence: float
    evidence_json: dict
    created_at: datetime


class CitedStatement(BaseModel):
    text: str
    citation_ids: list[str]
    stance: Literal["bullish", "bearish", "neutral"] | None = None
    severity: Literal["low", "medium", "high"] | None = None


class MarketAssessment(BaseModel):
    severity: Literal["low", "medium", "high"]
    stance: Literal["bullish", "bearish", "neutral"]
    summary: str
    citation_ids: list[str]


class CitedSummary(BaseModel):
    assessment: MarketAssessment
    statements: list[CitedStatement]


class EvidenceRecord(BaseModel):
    id: str
    category: Literal["technical", "fundamental", "news"]
    label: str
    value: str
    source: str | None
    captured_at: datetime


class EvidenceRegistry(BaseModel):
    records: dict[str, EvidenceRecord] = Field(default_factory=dict)


class Report(BaseModel):
    ticker: str
    technical_summary: str
    fundamental_summary: str
    news_summary: str
    severity: Literal["low", "medium", "high"]
    stance: Literal["bullish", "bearish", "neutral"]
    ai_explanation: str
    evidence_registry: EvidenceRegistry
    generated_at: datetime


class WatchlistRow(BaseModel):
    ticker: str
    trend: str
    severity: str | None
    stance: str | None
    last_updated: datetime | None


class AnalysisRunCreate(BaseModel):
    asset_id: UUID | None
    run_type: RunType
    started_at: datetime


class AnalysisRunDTO(BaseModel):
    id: UUID
    asset_id: UUID | None
    ticker: str | None = None
    run_type: RunType
    status: RunStatus
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
    error_message: str | None
