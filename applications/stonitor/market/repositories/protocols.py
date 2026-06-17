"""Repository Protocol interfaces for Stonitor market layer."""

from typing import Protocol
from uuid import UUID

from applications.stonitor.market.models.dto import (
    AnalysisRunCreate,
    AnalysisRunDTO,
    AssetDTO,
    FundamentalSnapshotCreate,
    FundamentalSnapshotDTO,
    NewsArticleCreate,
    NewsArticleDTO,
    PriceSnapshotCreate,
    PriceSnapshotDTO,
    SignalCreate,
    SignalDTO,
)


class IAssetRepository(Protocol):
    async def get_by_ticker(self, ticker: str) -> AssetDTO | None: ...

    async def get_watchlisted(self) -> list[AssetDTO]: ...

    async def upsert(
        self,
        ticker: str,
        exchange: str | None,
    ) -> AssetDTO: ...

    async def set_watchlisted(
        self,
        ticker: str,
        *,
        watchlisted: bool,
    ) -> AssetDTO: ...


class IPriceSnapshotRepository(Protocol):
    async def upsert_many(
        self,
        snapshots: list[PriceSnapshotCreate],
    ) -> int: ...

    async def get_latest(
        self,
        asset_id: UUID,
        *,
        limit: int = 90,
    ) -> list[PriceSnapshotDTO]: ...


class IFundamentalSnapshotRepository(Protocol):
    async def insert(
        self,
        snapshot: FundamentalSnapshotCreate,
    ) -> FundamentalSnapshotDTO: ...

    async def get_latest(
        self,
        asset_id: UUID,
    ) -> FundamentalSnapshotDTO | None: ...


class INewsArticleRepository(Protocol):
    async def upsert_by_url(
        self,
        article: NewsArticleCreate,
    ) -> NewsArticleDTO: ...

    async def get_recent_for_asset(
        self,
        asset_id: UUID,
        *,
        days: int = 7,
    ) -> list[NewsArticleDTO]: ...


class ISignalRepository(Protocol):
    async def insert(self, signal: SignalCreate) -> SignalDTO: ...

    async def get_latest_for_asset(
        self,
        asset_id: UUID,
    ) -> list[SignalDTO]: ...


class IAnalysisRunRepository(Protocol):
    async def start(self, run: AnalysisRunCreate) -> AnalysisRunDTO: ...

    async def complete(
        self,
        run_id: UUID,
        *,
        duration_ms: int,
    ) -> AnalysisRunDTO: ...

    async def fail(
        self,
        run_id: UUID,
        *,
        error_message: str,
    ) -> AnalysisRunDTO: ...

    async def list_recent(
        self,
        *,
        limit: int = 50,
    ) -> list[AnalysisRunDTO]: ...
