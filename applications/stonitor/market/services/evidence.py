"""Evidence lookup for citation drawer and explorer."""

from __future__ import annotations

from uuid import UUID

from applications.stonitor.market.exc import CitationNotFoundError
from applications.stonitor.market.models.dto import (
    EvidenceRecord,
    EvidenceRegistry,
)
from applications.stonitor.market.reports.registry import EvidenceRegistryBuilder
from applications.stonitor.market.repositories.protocols import (
    IAssetRepository,
    ISignalRepository,
)
from applications.stonitor.market.services.signal_utils import (
    latest_signal_batch,
)


class EvidenceService:
    """Resolve citations and list evidence for a ticker."""

    def __init__(
        self,
        asset_repo: IAssetRepository,
        signal_repo: ISignalRepository,
        registry_builder: EvidenceRegistryBuilder,
    ) -> None:
        self._asset_repo = asset_repo
        self._signal_repo = signal_repo
        self._registry_builder = registry_builder
        self._registry_cache: dict[str, EvidenceRegistry] = {}

    def cache_registry(self, ticker: str, registry: EvidenceRegistry) -> None:
        """Store registry from the latest report generation."""
        self._registry_cache[ticker.upper()] = registry

    async def get_evidence(
        self,
        citation_id: str,
        ticker: str,
    ) -> EvidenceRecord:
        """Resolve a citation ID for the evidence drawer."""
        registry = await self.list_all(ticker)
        record = registry.records.get(citation_id)
        if record is None:
            msg = f"Evidence no longer available: {citation_id}"
            raise CitationNotFoundError(msg)
        return record

    async def list_all(self, ticker: str) -> EvidenceRegistry:
        """Return full evidence registry for explorer tab."""
        symbol = ticker.strip().upper()
        cached = self._registry_cache.get(symbol)
        if cached is not None:
            return cached
        asset = await self._asset_repo.get_by_ticker(symbol)
        if asset is None:
            return EvidenceRegistry()
        return await self.build_for_asset(asset.id, symbol)

    async def build_for_asset(
        self,
        asset_id: UUID,
        ticker: str,
    ) -> EvidenceRegistry:
        """Build registry from persisted signals."""
        signals = latest_signal_batch(
            await self._signal_repo.get_latest_for_asset(asset_id),
        )
        registry = self._registry_builder.build(signals)
        self.cache_registry(ticker, registry)
        return registry
