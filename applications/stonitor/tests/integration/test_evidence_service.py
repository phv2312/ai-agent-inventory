"""Integration tests for EvidenceService."""

import pytest

from applications.stonitor.market.exc import CitationNotFoundError
from applications.stonitor.market.models.dto import AssetDTO, EvidenceRecord
from applications.stonitor.market.models.orm.enums import (
    SignalCategory,
    SignalType,
)
from applications.stonitor.market.repositories.signal import SignalRepository
from applications.stonitor.market.services.evidence import EvidenceService
from applications.stonitor.tests.integration import factories


@pytest.mark.asyncio
async def test_build_for_asset_assigns_citation_ids(
    evidence_service: EvidenceService,
    signal_repo: SignalRepository,
    seeded_asset: AssetDTO,
) -> None:
    """Registry should include technical, fundamental, and news signals."""
    batch_at = factories.utc_now()
    await signal_repo.insert(
        factories.signal_create(
            seeded_asset.id,
            signal_type=SignalType.TREND,
            category=SignalCategory.TECHNICAL,
            created_at=batch_at,
        ),
    )
    await signal_repo.insert(
        factories.signal_create(
            seeded_asset.id,
            signal_type=SignalType.FUNDAMENTAL,
            category=SignalCategory.FUNDAMENTAL,
            value="positive",
            created_at=batch_at,
        ),
    )
    await signal_repo.insert(
        factories.signal_create(
            seeded_asset.id,
            signal_type=SignalType.SENTIMENT,
            category=SignalCategory.NEWS,
            value="positive",
            created_at=batch_at,
        ),
    )

    registry = await evidence_service.build_for_asset(
        seeded_asset.id,
        seeded_asset.ticker,
    )

    categories = {record.category for record in registry.records.values()}
    assert "technical" in categories
    assert "news" in categories
    assert "fundamental" in categories


@pytest.mark.asyncio
async def test_get_evidence_resolves_known_citation(
    evidence_service: EvidenceService,
    signal_repo: SignalRepository,
    seeded_asset: AssetDTO,
) -> None:
    """Known citation ID should resolve to an evidence record."""
    await signal_repo.insert(factories.signal_create(seeded_asset.id))
    registry = await evidence_service.build_for_asset(
        seeded_asset.id,
        seeded_asset.ticker,
    )
    citation_id = next(iter(registry.records))

    record = await evidence_service.get_evidence(
        citation_id,
        seeded_asset.ticker,
    )
    assert record.id == citation_id


@pytest.mark.asyncio
async def test_get_evidence_raises_for_unknown_citation(
    evidence_service: EvidenceService,
    seeded_asset: AssetDTO,
) -> None:
    """Unknown citation ID should raise CitationNotFoundError."""
    with pytest.raises(CitationNotFoundError):
        await evidence_service.get_evidence("TECH-999", seeded_asset.ticker)


@pytest.mark.asyncio
async def test_list_all_uses_cache_when_populated(
    evidence_service: EvidenceService,
) -> None:
    """Cached registry should be returned without hitting repositories."""
    from applications.stonitor.market.models.dto import EvidenceRegistry

    cached = EvidenceRegistry(
        records={
            "TECH-001": EvidenceRecord(
                id="TECH-001",
                category="technical",
                label="cached",
                value="1",
                source=None,
                captured_at=factories.utc_now(),
            ),
        },
    )
    evidence_service.cache_registry("VNM", cached)

    result = await evidence_service.list_all("VNM")
    assert list(result.records) == ["TECH-001"]
