"""Markdown formatters for Stonitor UI."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from applications.stonitor.market.models.dto import EvidenceRecord

_NEWS_VALUE = re.compile(
    r"day=(?P<day>[^,]+),\s*sentiment=(?P<sentiment>[^,]+),\s*"
    r'(?:url="(?P<url>[^"]*)",\s*)?'
    r'title="(?P<title>[^"]*)",\s*content="(?P<content>.*)"\s*$',
    re.DOTALL,
)


@dataclass(frozen=True)
class NewsFields:
    """Parsed news evidence fields."""

    day: str
    sentiment: str
    title: str
    content: str
    url: str = field(default="")


def parse_news_record(record: EvidenceRecord) -> NewsFields:
    """Extract structured news fields from an evidence record."""
    match = _NEWS_VALUE.match(record.value.strip())
    if match is not None:
        # Decode any residual literal \n from old records stored before the fix
        content = match.group("content").replace("\\n", "\n").replace("\\r", "")
        return NewsFields(
            day=match.group("day"),
            sentiment=match.group("sentiment"),
            title=match.group("title") or record.label,
            content=content,
            url=match.group("url") or "",
        )
    return NewsFields(
        day=record.captured_at.date().isoformat(),
        sentiment="neutral",
        title=record.label,
        content=record.value.replace("\\n", "\n").replace("\\r", ""),
        url="",
    )
