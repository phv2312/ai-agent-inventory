from typing import Final


class ChatStreamEventNames:
    TOOL_CALLED: Final[str] = "tool_called"


class ResponseStreamEventNames:
    TEXT_DELTA: Final[str] = "response.output_text.delta"


class AgentToolNames:
    INTERNAL_SEARCH: Final[str] = "internal_search_tool"
    THINK: Final[str] = "think_tool"
    VISUALIZE_README: Final[str] = "visualize_read_me"


class ToolProgressMessages:
    INTERNAL_SEARCH: Final[str] = "[Internal Search] {query}\n\n"
    THINK: Final[str] = "[Thinking] {reflection}\n\n"
    VISUALIZE: Final[str] = "[Visualization] Loading {modules}\n\n"
    WEB_SEARCH: Final[str] = "[Web Search] {query}\n\n"
    FALLBACK: Final[str] = "[Tool Call] {name}\n\n"
