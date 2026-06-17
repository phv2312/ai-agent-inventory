"""Evidence registry builder assigning TECH/FUND/NEWS citation IDs."""

from __future__ import annotations

from typing import Literal

from applications.stonitor.market.models.dto import (
    EvidenceRecord,
    EvidenceRegistry,
    SignalDTO,
)
from applications.stonitor.market.models.orm.enums import SignalCategory


def _inline_text(text: str, *, max_len: int = 400) -> str:
    cleaned = " ".join(str(text).split())
    if len(cleaned) <= max_len:
        return cleaned.replace('"', "'")
    return cleaned[: max_len - 3].replace('"', "'") + "..."


def _decode_news_content(text: str) -> str:
    """Decode literal escape sequences and sanitize for value storage."""
    return (
        str(text)
        .replace("\\r\\n", "\n")
        .replace("\\n", "\n")
        .replace("\\r", "\n")
        .replace("\\t", " ")
        .replace('"', "'")
        .strip()
    )


class EvidenceRegistryBuilder:
    """Build evidence registry from persisted signals."""

    _PREFIX: dict[SignalCategory, str] = {
        SignalCategory.TECHNICAL: "TECH",
        SignalCategory.FUNDAMENTAL: "FUND",
        SignalCategory.NEWS: "NEWS",
    }

    def build(self, signals: list[SignalDTO]) -> EvidenceRegistry:
        """Assign citation IDs to signal evidence records."""
        records: dict[str, EvidenceRecord] = {}
        counters = {"TECH": 0, "FUND": 0, "NEWS": 0}

        for signal in signals:
            prefix = self._PREFIX.get(signal.category)
            if prefix is None:
                continue
            counters[prefix] += 1
            evidence_id = f"{prefix}-{counters[prefix]:03d}"
            records[evidence_id] = self._signal_record(
                evidence_id,
                signal,
            )

        return EvidenceRegistry(records=records)

    @staticmethod
    def _signal_record(
        evidence_id: str,
        signal: SignalDTO,
    ) -> EvidenceRecord:
        if signal.category == SignalCategory.NEWS:
            return EvidenceRegistryBuilder._news_record(evidence_id, signal)

        category_map: dict[
            SignalCategory,
            Literal["technical", "fundamental", "news"],
        ] = {
            SignalCategory.TECHNICAL: "technical",
            SignalCategory.FUNDAMENTAL: "fundamental",
            SignalCategory.NEWS: "news",
        }
        evidence = signal.evidence_json
        detail = ", ".join(f"{key}={value}" for key, value in evidence.items())
        source = str(evidence.get("source", "stonitor/signals"))
        return EvidenceRecord(
            id=evidence_id,
            category=category_map[signal.category],
            label=f"{signal.signal_type.value}: {signal.value}",
            value=detail or signal.value,
            source=source if source != "stonitor/signals" else None,
            captured_at=signal.created_at,
        )

    @staticmethod
    def _news_record(
        evidence_id: str,
        signal: SignalDTO,
    ) -> EvidenceRecord:
        evidence = signal.evidence_json
        title = _inline_text(str(evidence.get("title", "")))
        content = _decode_news_content(str(evidence.get("content", "")))
        day = str(evidence.get("day", ""))
        sentiment = str(evidence.get("sentiment", signal.value))
        url = str(evidence.get("url", ""))
        source = str(evidence.get("source", "")) or None
        url_part = f', url="{url}"' if url else ""
        return EvidenceRecord(
            id=evidence_id,
            category="news",
            label=title or "news",
            value=(
                f"day={day}, sentiment={sentiment}{url_part}, "
                f'title="{title}", content="{content}"'
            ),
            source=source,
            captured_at=signal.created_at,
        )
