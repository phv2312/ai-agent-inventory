import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


VALID_MODULES: frozenset[str] = frozenset(
    {"chart", "diagram", "mockup", "interactive", "art"},
)


class RegexPatterns:
    WIDGET_OPENING = re.compile(r"^(.*?)```visualize:(\S+)(.*?)$")
    WIDGET_CLOSING = re.compile(r"^(.*?)```(.*)$")
    SNIPPET_OPENING = re.compile(r"^(.*?)```snippets(.*?)$")
    SNIPPET_CLOSING = re.compile(r"^(.*?)```(.*)$")


class ParserState(StrEnum):
    PROSE = "prose"
    WIDGET = "widget"
    SNIPPET = "snippet"


class FenceEventType(StrEnum):
    PROSE_DELTA = "prose_delta"
    WIDGET_DELTA = "widget_delta"
    SNIPPET_DELTA = "snippet_delta"
    OPEN_WIDGET = "open_widget"
    OPEN_SNIPPET = "open_snippet"
    WIDGET_ERROR = "widget_error"
    CLOSE_WIDGET = "close_widget"
    CLOSE_SNIPPET = "close_snippet"


@dataclass(frozen=True)
class FenceEvent:
    type: FenceEventType
    content: str = ""
    module: str | None = None
    error_message: str | None = None


class RegexAct(Protocol):
    def detect_pattern(self, line: str) -> bool: ...

    def update(
        self,
        line: str,
        state: ParserState,
        events: Sequence[FenceEvent],
    ) -> tuple[ParserState, list[FenceEvent]]: ...


class WidgetRegexAct:
    def detect_pattern(self, line: str) -> bool:
        return RegexPatterns.WIDGET_OPENING.search(line) is not None

    def update(
        self,
        line: str,
        state: ParserState,
        events: Sequence[FenceEvent],
    ) -> tuple[ParserState, list[FenceEvent]]:
        match = RegexPatterns.WIDGET_OPENING.search(line)
        if match is None:
            raise ValueError("Ensure pattern matched first.")
        before, module, after = match.groups()
        updated_events = list(events)
        if before:
            updated_events.append(FenceEvent(FenceEventType.PROSE_DELTA, before))
        if module not in VALID_MODULES:
            updated_events.append(
                FenceEvent(
                    FenceEventType.WIDGET_ERROR,
                    module=module,
                    error_message=f"Unknown visualize module: {module}",
                ),
            )
            return state, updated_events
        updated_events.append(FenceEvent(FenceEventType.OPEN_WIDGET, module=module))
        if after:
            updated_events.append(FenceEvent(FenceEventType.WIDGET_DELTA, after))
        return ParserState.WIDGET, updated_events


class SnippetRegexAct:
    def detect_pattern(self, line: str) -> bool:
        return RegexPatterns.SNIPPET_OPENING.search(line) is not None

    def update(
        self,
        line: str,
        state: ParserState,
        events: Sequence[FenceEvent],
    ) -> tuple[ParserState, list[FenceEvent]]:
        match = RegexPatterns.SNIPPET_OPENING.search(line)
        if match is None:
            raise ValueError("Ensure pattern matched first.")
        before, after = match.groups()
        updated_events = list(events)
        if before:
            updated_events.append(FenceEvent(FenceEventType.PROSE_DELTA, before))
        updated_events.append(FenceEvent(FenceEventType.OPEN_SNIPPET))
        if after:
            updated_events.append(FenceEvent(FenceEventType.SNIPPET_DELTA, after))
        return ParserState.SNIPPET, updated_events


@dataclass
class FenceParser:
    state: ParserState = ParserState.PROSE
    scratchpad: str = ""
    split_char: str = "\n"

    def feed(self, fragment: str) -> list[FenceEvent]:
        if not fragment:
            return []
        self.scratchpad += fragment
        events: list[FenceEvent] = []
        while self.split_char in self.scratchpad:
            processing, self.scratchpad = self.scratchpad.split(self.split_char, 1)
            events.extend(self._handle_line(processing + self.split_char))
        if not self.scratchpad:
            return events
        if self.state == ParserState.PROSE and self._is_prose_prefix(self.scratchpad):
            return events
        if self.state != ParserState.PROSE and self._is_closer_prefix(self.scratchpad):
            return events
        events.extend(self._handle_line(self.scratchpad))
        self.scratchpad = ""
        return events

    def finalize(self) -> list[FenceEvent]:
        if not self.scratchpad:
            return []
        events = self._handle_line(self.scratchpad)
        self.scratchpad = ""
        return events

    @staticmethod
    def _is_prose_prefix(line: str) -> bool:
        rest = line[len(line) - len(line.lstrip()) :]
        return rest.startswith("```") or rest in ("`", "``")

    @staticmethod
    def _is_closer_prefix(line: str) -> bool:
        return line.strip() in ("`", "``", "```")

    def _handle_line(self, line: str) -> list[FenceEvent]:
        match self.state:
            case ParserState.PROSE:
                return self._handle_prose(line)
            case ParserState.WIDGET:
                return self._handle_widget(line)
            case ParserState.SNIPPET:
                return self._handle_snippet(line)

    def _handle_prose(self, line: str) -> list[FenceEvent]:
        events: list[FenceEvent] = []
        for actor in (WidgetRegexAct(), SnippetRegexAct()):
            if actor.detect_pattern(line.strip()):
                self.state, events = actor.update(line.strip(), self.state, events)
                return events
        return [FenceEvent(FenceEventType.PROSE_DELTA, line)]

    def _handle_widget(self, line: str) -> list[FenceEvent]:
        match = RegexPatterns.WIDGET_CLOSING.search(line.strip())
        if match is None:
            return [FenceEvent(FenceEventType.WIDGET_DELTA, line)]
        self.state = ParserState.PROSE
        before, after = match.groups()
        events = [] if not before else [FenceEvent(FenceEventType.WIDGET_DELTA, before)]
        events.append(FenceEvent(FenceEventType.CLOSE_WIDGET))
        if after:
            events.append(FenceEvent(FenceEventType.PROSE_DELTA, after))
        return events

    def _handle_snippet(self, line: str) -> list[FenceEvent]:
        match = RegexPatterns.SNIPPET_CLOSING.search(line.strip())
        if match is None:
            return [FenceEvent(FenceEventType.SNIPPET_DELTA, line)]
        self.state = ParserState.PROSE
        before, after = match.groups()
        events = (
            [] if not before else [FenceEvent(FenceEventType.SNIPPET_DELTA, before)]
        )
        events.append(FenceEvent(FenceEventType.CLOSE_SNIPPET))
        if after:
            events.append(FenceEvent(FenceEventType.PROSE_DELTA, after))
        return events
