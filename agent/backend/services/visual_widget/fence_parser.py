from typing import Protocol
from collections.abc import Sequence

import re
from dataclasses import dataclass, field
from enum import StrEnum

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
    SNIPPET_DELTA = "snipet_delta"

    OPEN_WIDGET = "open_widget"
    OPEN_SNIPPET = "open_snippet"

    WIDGET_ERROR = "widget_error"
    SNIPPET_ERROR = "snippet_error"

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
        self, line: str, state: ParserState, events: Sequence[FenceEvent]
    ) -> tuple[ParserState, list[FenceEvent]]: ...


class WidgetRegexAct:
    def detect_pattern(self, line: str) -> bool:
        match = RegexPatterns.WIDGET_OPENING.search(line)
        return match is not None

    def update(
        self, line: str, state: ParserState, events: Sequence[FenceEvent]
    ) -> tuple[ParserState, list[FenceEvent]]:
        match = RegexPatterns.WIDGET_OPENING.search(line)
        if match is None:
            raise ValueError("Ensure pattern matched first.")

        updated_state = state
        updated_events = list(events)

        before, module, after = match.groups()
        if before:
            updated_events.append(FenceEvent(FenceEventType.PROSE_DELTA, before))

        if module in VALID_MODULES:
            updated_state = ParserState.WIDGET
            updated_events.append(FenceEvent(FenceEventType.OPEN_WIDGET, module=module))
            if after:
                updated_events.append(FenceEvent(FenceEventType.WIDGET_DELTA, after))
        else:
            updated_events.append(
                FenceEvent(
                    FenceEventType.WIDGET_ERROR,
                    module=module,
                    error_message=f"Unknown visualize module: {module}",
                ),
            )
        return updated_state, updated_events


class SnippetRegexAct:
    def detect_pattern(self, line: str) -> bool:
        match = RegexPatterns.SNIPPET_OPENING.search(line)
        return match is not None

    def update(
        self, line: str, state: ParserState, events: Sequence[FenceEvent]
    ) -> tuple[ParserState, list[FenceEvent]]:
        match = RegexPatterns.SNIPPET_OPENING.search(line)
        if match is None:
            raise ValueError("Ensure pattern matched first.")

        updated_state = state
        updated_events = list(events)
        before, after = match.groups()
        if before:
            updated_events.append(FenceEvent(FenceEventType.PROSE_DELTA, before))

        updated_state = ParserState.SNIPPET
        updated_events.append(FenceEvent(FenceEventType.OPEN_SNIPPET))
        if after:
            updated_events.append(FenceEvent(FenceEventType.SNIPPET_DELTA, after))

        return updated_state, updated_events


@dataclass
class FenceParser:
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
            case ParserState.WIDGET | ParserState.SNIPPET:
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
            # - prose can be transformed into snippet if it starts with +++snippet
            # - otherwise, prose is just prose

            stripped = line.strip()
            actors: list[RegexAct] = [WidgetRegexAct(), SnippetRegexAct()]

            events: list[FenceEvent] = []
            has_match = False
            for actor in actors:
                if actor.detect_pattern(stripped) is False:
                    continue
                (self.state, events) = actor.update(stripped, self.state, events)
                has_match = True
                print(f"Matched {type(actor)}")
                break

            if has_match is False:
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

        def _handle_snippet(line: str) -> list[FenceEvent]:
            # Transformation rules:
            # - snippet can be transformed into prose if it starts with +++
            # - otherwise, snippet is just snippet
            stripped = line.strip()
            match = RegexPatterns.SNIPPET_CLOSING.search(stripped)
            events: list[FenceEvent] = []
            if match:
                self.state = ParserState.PROSE
                before, after = match.groups()
                if before:
                    events.append(FenceEvent(FenceEventType.SNIPPET_DELTA, before))
                events.append(FenceEvent(FenceEventType.CLOSE_SNIPPET))
                if after:
                    events.append(FenceEvent(FenceEventType.PROSE_DELTA, after))
            else:
                events.append(FenceEvent(FenceEventType.SNIPPET_DELTA, line))

            return events

        match self.state:
            case ParserState.PROSE:
                # (prose -> widget|snippet)
                return _handle_prose(text_line)
            case ParserState.WIDGET:
                # (widget -> prose)
                return _handle_widget(text_line)
            case ParserState.SNIPPET:
                # (snippet -> snippet)
                return _handle_snippet(text_line)
