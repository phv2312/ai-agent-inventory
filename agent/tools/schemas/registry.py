from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from agent.models.streams import (
    FunctionCallDefinition,
    ToolDefinition,
    WebSearchToolDefinition,
)


class ToolNames(StrEnum):
    THINK_TOOL = "think_tool"
    SEARCH_TOOL = "internal_search_tool"
    INLINE_CITATIONS_TOOL = "inline_citations_tool"
    WEB_SEARCH_TOOL = "web_search_tool"
    VISUALIZE_README_TOOL = "visualize_read_me"


type VisualizeModule = Literal[
    "interactive",
    "chart",
    "diagram",
    "mockup",
    "art",
]


class BaseToolParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ThinkParameters(BaseToolParameters):
    reflection: str = Field(
        ...,
        description=(
            "Your reflection. No list or bullet points. "
            "Should be short and direct, ideally within 100 words."
        ),
    )


class SearchParameters(BaseToolParameters):
    query: str = Field(
        ...,
        description="Search query describing the information to retrieve",
    )
    granularity: Literal["section", "page", "document"] = Field(
        ...,
        description=(
            "Retrieval level: section for targeted queries, "
            "page for full page content, document for overviews."
        ),
    )
    page_idxs: list[int] | None = Field(
        ...,
        description="Optional page indexes to restrict search scope.",
    )
    doc_names: list[str] | None = Field(
        ...,
        description="Optional document names to restrict search scope.",
    )


class VisualizeReadmeParameters(BaseToolParameters):
    modules: list[VisualizeModule] = Field(
        ...,
        description="Which module(s) to load. Pick all that fit.",
    )


class InlineCitationItem(BaseToolParameters):
    chunk_id: str = Field(
        ...,
        description="Chunk-ID returned by search_tool.",
    )
    snippets: list[str] = Field(
        ...,
        min_length=1,
        description=(
            "Exact-copy spans from that chunk's body, copied "
            "character-for-character from search results."
        ),
    )


class InlineCitationsParameters(BaseToolParameters):
    citations: list[InlineCitationItem] = Field(
        ...,
        min_length=1,
        description=(
            "Rows to validate: each chunk_id with exact-copy snippets "
            "from internal search results."
        ),
    )


class ToolDescriptionArgs:
    THINK_TOOL: str = """
        Act as the scratchpad for your thoughts.
        Use it for extra searches when the gathered context is not sufficent for the final answer.
        Ideally call before performing extra internal search or escalating to web-search.
    """

    SEARCH_TOOL: str = """
        Prefer calling internal search first if there're document names provided
        to update your knowledge-base.
        **Do not use your built-in knowledge**. Use either internal knowledge-base
        or web source only.
    """

    INLINE_CITATIONS_TOOL: str = """
        Precisely cite snippets from internal chunks, which support for your final answer.
        It's mandatory that internal search tool should be call first.
    """

    VISUALIZE_README_TOOL: str = (
        "Returns required context for inline visualize fences (CSS variables, "
        "colors, typography, layout rules, examples). Call exactly once "
        "before your first ```visualize:<module> fence in the answer, "
        "with the intended module(s) in `modules` (for example, "
        "`['chart']` for charts or `['diagram']` for flowcharts). Do "
        "NOT mention or narrate this call to the user; it is an "
        "internal setup step."
    )


class ToolSchemaRegistry:
    """Canonical tool schemas for streaming and OpenAI Responses API."""

    MP_NAME_TOOLS: Final[dict[ToolNames, ToolDefinition]] = {
        ToolNames.THINK_TOOL: FunctionCallDefinition(
            name=ToolNames.THINK_TOOL,
            description=ToolDescriptionArgs.THINK_TOOL,
            input_schema=ThinkParameters.model_json_schema(),
        ),
        ToolNames.SEARCH_TOOL: FunctionCallDefinition(
            name=ToolNames.SEARCH_TOOL,
            description=ToolDescriptionArgs.SEARCH_TOOL,
            input_schema=SearchParameters.model_json_schema(),
        ),
        ToolNames.INLINE_CITATIONS_TOOL: FunctionCallDefinition(
            name=ToolNames.INLINE_CITATIONS_TOOL,
            description=ToolDescriptionArgs.INLINE_CITATIONS_TOOL,
            input_schema=InlineCitationsParameters.model_json_schema(),
        ),
        ToolNames.WEB_SEARCH_TOOL: WebSearchToolDefinition(
            search_context_size="high",
        ),
        ToolNames.VISUALIZE_README_TOOL: FunctionCallDefinition(
            name=ToolNames.VISUALIZE_README_TOOL,
            description=ToolDescriptionArgs.VISUALIZE_README_TOOL,
            input_schema=(VisualizeReadmeParameters.model_json_schema()),
        ),
    }

    _AGENTIC_STREAM_TOOL_ORDER: Final[tuple[ToolNames, ...]] = (
        ToolNames.WEB_SEARCH_TOOL,
        ToolNames.VISUALIZE_README_TOOL,
    )

    @staticmethod
    def agentic_tools(*, internal_search: bool = True) -> list[ToolDefinition]:
        tools = [
            ToolSchemaRegistry.MP_NAME_TOOLS[name]
            for name in ToolSchemaRegistry._AGENTIC_STREAM_TOOL_ORDER
        ]

        if internal_search:
            tools = [
                *tools,
                ToolSchemaRegistry.MP_NAME_TOOLS[ToolNames.SEARCH_TOOL],
                ToolSchemaRegistry.MP_NAME_TOOLS[ToolNames.INLINE_CITATIONS_TOOL],
                ToolSchemaRegistry.MP_NAME_TOOLS[ToolNames.THINK_TOOL],
            ]

        return tools
