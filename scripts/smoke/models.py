from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SmokeCase:
    name: str
    message: str
    system_prompt: str
    web_search_enabled: bool = False
    requires_reference: bool = False
    expected_reasoning: str = ""
    expected_text: str = ""
    expects_visual_widget: bool = False

    @classmethod
    def from_payload(cls, payload: object) -> "SmokeCase":
        if not isinstance(payload, dict):
            raise ValueError("Each smoke case must be a JSON object")

        required_fields = ("name", "message", "system_prompt")
        for field_name in required_fields:
            if not isinstance(payload.get(field_name), str) or not payload[field_name]:
                raise ValueError(f"Smoke case requires a non-empty {field_name}")

        string_fields = ("expected_reasoning", "expected_text")
        boolean_fields = (
            "web_search_enabled",
            "requires_reference",
            "expects_visual_widget",
        )
        for field_name in string_fields:
            if field_name in payload and not isinstance(payload[field_name], str):
                raise ValueError(f"Smoke case {field_name} must be a string")
        for field_name in boolean_fields:
            if field_name in payload and not isinstance(payload[field_name], bool):
                raise ValueError(f"Smoke case {field_name} must be a boolean")

        return cls(
            name=payload["name"],
            message=payload["message"],
            system_prompt=payload["system_prompt"],
            web_search_enabled=payload.get("web_search_enabled", False),
            requires_reference=payload.get("requires_reference", False),
            expected_reasoning=payload.get("expected_reasoning", ""),
            expected_text=payload.get("expected_text", ""),
            expects_visual_widget=payload.get("expects_visual_widget", False),
        )


@dataclass
class StreamResult:
    events: list[tuple[str, Any]] = field(default_factory=list)

    @property
    def reasoning(self) -> str:
        return "".join(
            event[1][0].get("content", "")
            for event in self.events
            if event[0] == "reasoning" and isinstance(event[1], list) and event[1]
        )

    @property
    def text(self) -> str:
        return "".join(
            event[1].get("content", "")
            for event in self.events
            if event[0] == "block-delta"
            and isinstance(event[1], dict)
            and event[1].get("type") == "text"
        )

    @property
    def has_visual_widget(self) -> bool:
        return any(
            event[0] == "block-open"
            and isinstance(event[1], dict)
            and event[1].get("type") == "visual_widget"
            for event in self.events
        )
