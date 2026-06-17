"""Live integration tests for ReportGenerator with real LLM output."""

from uuid import uuid4

import pytest

from applications.stonitor.market.models.dto import SignalDTO
from applications.stonitor.market.models.orm.enums import (
    SignalCategory,
    SignalType,
)
from applications.stonitor.market.reports.generator import ReportGenerator
from applications.stonitor.tests.integration import factories

pytestmark = [pytest.mark.external, pytest.mark.asyncio]

_CONTRACT_TICKER = "VNM"


def _sample_signals(asset_id) -> list[SignalDTO]:
    now = factories.utc_now()
    return [
        SignalDTO(
            id=uuid4(),
            asset_id=asset_id,
            signal_type=SignalType.TREND,
            category=SignalCategory.TECHNICAL,
            value="bullish",
            score=1.5,
            confidence=0.85,
            evidence_json={
                "sma_20": 85.2,
                "sma_50": 82.1,
                "close": 86.0,
            },
            created_at=now,
        ),
        SignalDTO(
            id=uuid4(),
            asset_id=asset_id,
            signal_type=SignalType.SENTIMENT,
            category=SignalCategory.NEWS,
            value="positive",
            score=0.4,
            confidence=0.7,
            evidence_json={"articles": 3, "avg_sentiment": 0.4},
            created_at=now,
        ),
    ]


async def test_generate_produces_cited_report(
    report_generator: ReportGenerator,
) -> None:
    """Live LLM summary should pass citation filter and return sections."""
    asset_id = uuid4()
    report = await report_generator.generate(
        _CONTRACT_TICKER,
        _sample_signals(asset_id),
    )

    assert report.ticker == _CONTRACT_TICKER
    assert report.evidence_registry.records
    assert report.ai_explanation.strip()
    assert "[" in report.ai_explanation
    assert report.technical_summary != "Không có dữ liệu đủ để tóm tắt."
