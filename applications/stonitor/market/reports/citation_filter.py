"""Validate cited summaries against the evidence registry."""

from __future__ import annotations

from applications.stonitor.market.exc import InsufficientEvidenceError
from applications.stonitor.market.models.dto import (
    CitedStatement,
    CitedSummary,
    EvidenceRegistry,
    MarketAssessment,
)

_SEVERITY_LABELS = {
    "low": "Thấp",
    "medium": "Trung bình",
    "high": "Cao",
}

_STANCE_LABELS = {
    "bullish": "Bull đang thắng thế",
    "bearish": "Bear đang thắng thế",
    "neutral": "Trung lập",
}


class CitationFilter:
    """Strip uncited or invalid statements from LLM output."""

    INSUFFICIENT_MESSAGE = "Insufficient evidence."

    def validate(
        self,
        summary: CitedSummary,
        registry: EvidenceRegistry,
    ) -> tuple[str, MarketAssessment]:
        """Return formatted explanation and validated assessment."""
        assessment = self._validate_assessment(summary.assessment, registry)
        statements = self._filter_statements(summary, registry)
        if not statements:
            raise InsufficientEvidenceError(self.INSUFFICIENT_MESSAGE)
        return self.format_summary(assessment, statements), assessment

    def _validate_assessment(
        self,
        assessment: MarketAssessment,
        registry: EvidenceRegistry,
    ) -> MarketAssessment:
        summary = assessment.summary.strip()
        if not summary or not assessment.citation_ids:
            raise InsufficientEvidenceError(self.INSUFFICIENT_MESSAGE)
        if not all(
            citation_id in registry.records
            for citation_id in assessment.citation_ids
        ):
            raise InsufficientEvidenceError(self.INSUFFICIENT_MESSAGE)
        return assessment

    def _filter_statements(
        self,
        summary: CitedSummary,
        registry: EvidenceRegistry,
    ) -> list[CitedStatement]:
        valid: list[CitedStatement] = []
        for statement in summary.statements:
            text = statement.text.strip()
            if not text or not statement.citation_ids:
                continue
            if all(
                citation_id in registry.records
                for citation_id in statement.citation_ids
            ):
                valid.append(statement)
        return valid

    @staticmethod
    def _table_cell(text: str) -> str:
        return " ".join(text.split()).replace("|", "\\|")

    @classmethod
    def format_summary(
        cls,
        assessment: MarketAssessment,
        statements: list[CitedStatement],
    ) -> str:
        """Render assessment and statements as markdown tables."""
        cites = ", ".join(f"`{item}`" for item in assessment.citation_ids)
        severity = _SEVERITY_LABELS[assessment.severity]
        stance = _STANCE_LABELS[assessment.stance]
        summary = cls._table_cell(assessment.summary.strip())
        lines = [
            "## Đánh giá tổng quan",
            "",
            "| Chỉ số | Giá trị | Trích dẫn |",
            "| --- | --- | --- |",
            f"| **Tóm tắt** | {summary} | {cites} |",
            f"| **Mức độ nghiêm trọng** | <mark>{severity}</mark> | |",
            f"| **Xu hướng** | <mark>{stance}</mark> | |",
            "",
            "## Chi tiết",
            "",
            "| # | Nội dung | Xu hướng | Rủi ro | Trích dẫn |",
            "| --- | --- | --- | --- | --- |",
        ]
        for index, statement in enumerate(statements, start=1):
            statement_cites = ", ".join(
                f"`{item}`" for item in statement.citation_ids
            )
            text = cls._table_cell(statement.text.strip())
            stmt_stance = (
                f"<mark>{_STANCE_LABELS[statement.stance]}</mark>"
                if statement.stance
                else ""
            )
            stmt_severity = (
                f"<mark>{_SEVERITY_LABELS[statement.severity]}</mark>"
                if statement.severity
                else ""
            )
            lines.append(
                f"| {index} | {text} | {stmt_stance}"
                f" | {stmt_severity} | {statement_cites} |",
            )
        return "\n".join(lines)
