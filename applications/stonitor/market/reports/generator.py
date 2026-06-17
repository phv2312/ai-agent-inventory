"""Report assembly with LLM summary and citation filtering."""

from __future__ import annotations

from datetime import UTC, datetime

from applications.stonitor.market.models.dto import (
    EvidenceRegistry,
    Report,
    SignalDTO,
)
from applications.stonitor.market.models.orm.enums import SignalCategory
from applications.stonitor.market.programs.report_summary import (
    ReportSummaryProgram,
)
from applications.stonitor.market.reports.citation_filter import CitationFilter
from applications.stonitor.market.reports.registry import EvidenceRegistryBuilder


class ReportGenerator:
    """Orchestrate section summaries, LLM output, and citation filter."""

    def __init__(
        self,
        registry_builder: EvidenceRegistryBuilder,
        summary_program: ReportSummaryProgram,
        citation_filter: CitationFilter,
    ) -> None:
        self._registry_builder = registry_builder
        self._summary_program = summary_program
        self._citation_filter = citation_filter

    async def generate(
        self,
        ticker: str,
        signals: list[SignalDTO],
    ) -> Report:
        """Build full report with cited AI explanation."""
        registry = self._registry_builder.build(signals)
        technical = self._section_summary(registry, SignalCategory.TECHNICAL)
        fundamental_text = self._section_summary(
            registry,
            SignalCategory.FUNDAMENTAL,
        )
        news_text = self._news_section_summary(registry)
        cited = await self._summary_program.generate(registry)
        ai_explanation, assessment = self._citation_filter.validate(
            cited,
            registry,
        )
        return Report(
            ticker=ticker.upper(),
            technical_summary=technical,
            fundamental_summary=fundamental_text,
            news_summary=news_text,
            severity=assessment.severity,
            stance=assessment.stance,
            ai_explanation=ai_explanation,
            evidence_registry=registry,
            generated_at=datetime.now(tz=UTC),
        )

    @staticmethod
    def _news_section_summary(registry: EvidenceRegistry) -> str:
        lines = [
            f"- {record.value} [{record.id}]"
            for record in registry.records.values()
            if record.category == "news"
        ]
        if not lines:
            return "Không có dữ liệu đủ để tóm tắt."
        return "\n".join(lines)

    @staticmethod
    def _section_summary(
        registry: EvidenceRegistry,
        category: SignalCategory,
    ) -> str:
        category_name = {
            SignalCategory.TECHNICAL: "technical",
            SignalCategory.FUNDAMENTAL: "fundamental",
            SignalCategory.NEWS: "news",
        }[category]
        lines = [
            f"- {record.label}: {record.value} [{record.id}]"
            for record in registry.records.values()
            if record.category == category_name
        ]
        if not lines:
            return "Không có dữ liệu đủ để tóm tắt."
        return "\n".join(lines)
