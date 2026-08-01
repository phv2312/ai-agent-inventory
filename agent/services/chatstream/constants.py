from typing import Final


class ChatStreamEventNames:
    TOOL_CALLED: Final[str] = "tool_called"


class ResponseStreamEventNames:
    TEXT_DELTA: Final[str] = "response.output_text.delta"
