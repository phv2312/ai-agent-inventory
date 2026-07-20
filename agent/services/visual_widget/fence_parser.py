"""Incremental parser for ```visualize:<module> fences in text streams."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

VALID_MODULES: frozenset[str] = frozenset(
    {"chart", "diagram", "mockup", "interactive", "art"},
)


class RegexPatterns:
    WIDGET_OPENING = re.compile(r"^(.*?)```visualize:(\S+)(.*?)$")
    WIDGET_CLOSING = re.compile(r"^(.*?)```(.*)$")


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
    state: ParserState = ParserState.PROSE
    scratchpad: str = field(default="")
    split_char: str = "\n"

    def is_prose_hold_prefix(self, line: str) -> bool:
        leading = len(line) - len(line.lstrip())
        rest = line[leading:]
        if rest.startswith("```"):
            return True
        return rest in ("`", "``")

    def is_closer_prefix(self, line: str) -> bool:
        return line.strip() in ("`", "``", "```")

    def feed(self, fragment: str) -> list[FenceEvent]:
        if not fragment:
            return []

        self.scratchpad += fragment
        events: list[FenceEvent] = []
        while self.split_char in self.scratchpad:
            processing, self.scratchpad = self.scratchpad.split(self.split_char, 1)
            events.extend(self.handle_scratchpad(processing + self.split_char))

        if not self.scratchpad:
            return events

        match self.state:
            case ParserState.PROSE:
                if self.is_prose_hold_prefix(self.scratchpad):
                    return events
            case ParserState.WIDGET:
                if self.is_closer_prefix(self.scratchpad):
                    return events

        events.extend(self.handle_scratchpad(self.scratchpad))
        self.scratchpad = ""
        return events

    def flush_partial_prose(self) -> list[FenceEvent]:
        if not self.scratchpad:
            return []
        events = self.handle_scratchpad(self.scratchpad)
        self.scratchpad = ""
        return events

    def finalize(self) -> list[FenceEvent]:
        return self.flush_partial_prose()

    def handle_scratchpad(self, text_line: str) -> list[FenceEvent]:
        def _handle_prose(line: str) -> list[FenceEvent]:
            # Transformation rules:
            # - prose can be transformed into widget if it starts with ```visualize:<module>
            # - prose can be transformed into widget error if it starts with ```visualize:<invalid_module>
            # - otherwise, prose is just prose

            stripped = line.strip()
            match = RegexPatterns.WIDGET_OPENING.search(stripped)

            events: list[FenceEvent] = []
            if match:
                before, module, after = match.groups()
                if before:
                    events.append(FenceEvent(FenceEventType.PROSE_DELTA, before))

                if module in VALID_MODULES:
                    self.state = ParserState.WIDGET
                    events.append(FenceEvent(FenceEventType.OPEN_WIDGET, module=module))
                    if after:
                        events.append(FenceEvent(FenceEventType.WIDGET_DELTA, after))
                else:
                    events.append(
                        FenceEvent(
                            FenceEventType.WIDGET_ERROR,
                            module=module,
                            error_message=f"Unknown visualize module: {module}",
                        ),
                    )
            else:
                events.append(FenceEvent(FenceEventType.PROSE_DELTA, line))

            return events

        def _handle_widget(line: str) -> list[FenceEvent]:
            # Transformation rules:
            # - widget can be transformed into prose if it starts with ```
            # - otherwise, widget is just widget

            stripped = line.strip()
            match = RegexPatterns.WIDGET_CLOSING.search(stripped)
            events: list[FenceEvent] = []
            if match:
                self.state = ParserState.PROSE
                before, after = match.groups()
                if before:
                    events.append(FenceEvent(FenceEventType.WIDGET_DELTA, before))
                events.append(FenceEvent(FenceEventType.CLOSE_WIDGET))
                if after:
                    events.append(FenceEvent(FenceEventType.PROSE_DELTA, after))
            else:
                events.append(FenceEvent(FenceEventType.WIDGET_DELTA, line))

            return events

        match self.state:
            case ParserState.PROSE:
                return _handle_prose(text_line)
            case ParserState.WIDGET:
                return _handle_widget(text_line)
