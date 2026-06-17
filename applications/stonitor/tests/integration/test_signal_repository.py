"""Integration tests for SignalRepository."""

import pytest

from applications.stonitor.market.models.dto import AssetDTO
from applications.stonitor.market.models.orm.enums import SignalType
from applications.stonitor.market.repositories.signal import SignalRepository
from applications.stonitor.tests.integration import factories


@pytest.mark.asyncio
async def test_insert_and_get_latest_for_asset(
    signal_repo: SignalRepository,
    seeded_asset: AssetDTO,
) -> None:
    """Inserted signals should be retrievable for an asset."""
    trend = await signal_repo.insert(
        factories.signal_create(
            seeded_asset.id,
            signal_type=SignalType.TREND,
            value="bullish",
        ),
    )
    await signal_repo.insert(
        factories.signal_create(
            seeded_asset.id,
            signal_type=SignalType.MOMENTUM,
            value="positive",
        ),
    )

    latest = await signal_repo.get_latest_for_asset(seeded_asset.id)
    assert len(latest) == 2
    assert latest[0].id == trend.id or latest[1].id == trend.id
    assert {row.signal_type for row in latest} == {
        SignalType.TREND,
        SignalType.MOMENTUM,
    }
