"""Incremental parser for ```visualize:<module> fences in text streams."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

VALID_MODULES: frozenset[str] = frozenset(
    {"chart", "diagram", "mockup", "interactive", "art"},
)

_OPENER_RE = re.compile(
    r"^```visualize:(chart|diagram|mockup|interactive|art)\s*$",
)
_INVALID_OPENER_RE = re.compile(r"^```visualize:(\S+)\s*$")
_CLOSER_RE = re.compile(r"^```\s*$")
_OPENER_MARKER = "```visualize:"


class ParserState(StrEnum):
    PROSE = "prose"
    WIDGET = "widget"


class FenceEventType(StrEnum):
    PROSE_DELTA = "prose_delta"
    OPEN_WIDGET = "open_widget"
    WIDGET_DELTA = "widget_delta"
    CLOSE_WIDGET = "close_widget"
    WIDGET_ERROR = "widget_error"


@dataclass(frozen=True)
class FenceEvent:
    type: FenceEventType
    content: str = ""
    module: str | None = None
    error_message: str | None = None


@dataclass
class VisualizeFenceParser:
    """Line-oriented state machine for visualize fence syntax."""

    state: ParserState = ParserState.PROSE
    _partial_line: str = field(default="", repr=False)

    def feed(self, fragment: str) -> list[FenceEvent]:
        """Consume a text delta; return ordered fence events."""
        if not fragment:
            return []
        events: list[FenceEvent] = []
        self._partial_line += fragment
        while "\n" in self._partial_line:
            line, self._partial_line = self._partial_line.split("\n", 1)
            events.extend(self._process_line(line))
        if self.state == ParserState.PROSE and self._partial_line:
            if not _is_prose_hold_prefix(self._partial_line):
                events.append(
                    FenceEvent(FenceEventType.PROSE_DELTA, self._partial_line),
                )
                self._partial_line = ""
        elif self.state == ParserState.WIDGET and self._partial_line:
            if _is_closer_prefix(self._partial_line):
                pass
            else:
                events.append(
                    FenceEvent(FenceEventType.WIDGET_DELTA, self._partial_line),
                )
                self._partial_line = ""
        return events

    def flush_partial_prose(self) -> list[FenceEvent]:
        """Release buffered partial line as prose (stream abort)."""
        if not self._partial_line:
            return []
        if self.state == ParserState.WIDGET and _CLOSER_RE.match(
            self._partial_line.strip(),
        ):
            self._partial_line = ""
            self.state = ParserState.PROSE
            return [FenceEvent(FenceEventType.CLOSE_WIDGET)]
        event_type = (
            FenceEventType.WIDGET_DELTA
            if self.state == ParserState.WIDGET
            else FenceEventType.PROSE_DELTA
        )
        content = self._partial_line
        self._partial_line = ""
        return [FenceEvent(event_type, content)]

    def _process_line(self, line: str) -> list[FenceEvent]:
        if self.state == ParserState.PROSE:
            return self._process_prose_line(line)
        return self._process_widget_line(line)

    def _process_prose_line(self, line: str) -> list[FenceEvent]:
        stripped = line.lstrip()
        match = _OPENER_RE.match(stripped)
        if match:
            self.state = ParserState.WIDGET
            return [FenceEvent(FenceEventType.OPEN_WIDGET, module=match.group(1))]
        invalid = _INVALID_OPENER_RE.match(stripped)
        if invalid and invalid.group(1) not in VALID_MODULES:
            return [
                FenceEvent(
                    FenceEventType.WIDGET_ERROR,
                    module=invalid.group(1),
                    error_message=(f"Unknown visualize module: {invalid.group(1)}"),
                ),
            ]
        text = line + "\n"
        if not text:
            return []
        return [FenceEvent(FenceEventType.PROSE_DELTA, text)]

    def _process_widget_line(self, line: str) -> list[FenceEvent]:
        if _CLOSER_RE.match(line.strip()):
            self.state = ParserState.PROSE
            return [FenceEvent(FenceEventType.CLOSE_WIDGET)]
        return [FenceEvent(FenceEventType.WIDGET_DELTA, line + "\n")]


def _is_prose_hold_prefix(line: str) -> bool:
    """True when a partial line may still become a fence opener."""
    leading = len(line) - len(line.lstrip())
    rest = line[leading:]
    if rest.startswith("```"):
        return True
    return rest in ("`", "``")


def _is_closer_prefix(line: str) -> bool:
    """True when a partial line may still become a closing fence."""
    stripped = line.strip()
    return stripped in ("`", "``", "```")
