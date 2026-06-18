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
    SEARCH_TOOL = "search_tool"
    INLINE_CITATIONS_TOOL = "inline_citations_tool"
    WEB_SEARCH_TOOL = "web_search_tool"
    VISUALIZE_SHOW_WIDGET_TOOL = "visualize_show_widget"
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


class VisualizeShowWidgetParameters(BaseToolParameters):
    widget_code: str = Field(
        ...,
        description=(
            "SVG or HTML code to render. For SVG: raw SVG code "
            "starting with <svg>. For HTML: raw HTML content, no "
            "DOCTYPE/<html>/<body> tags. Use CSS variables for "
            "theming. Structure for streaming: <style> first, "
            "content next, <script> last."
        ),
    )
    title: str = Field(
        ...,
        description=(
            "Short snake_case identifier for this visual. Used as download filename."
        ),
    )
    loading_messages: list[str] = Field(
        ...,
        min_length=1,
        max_length=4,
        description=(
            "1-4 loading messages shown while the visual renders, "
            "each ~5 words. Match the user's language."
        ),
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
        Reflect on the search results and decide whether to continue
        searching or escalate to web search.
        Called after each search call.
        Called before escalating to web search.
    """

    SEARCH_TOOL: str = """
        IMPORTANT: always call `search_tool` as the 1st tool, before
        calling any other tools, to update internal knowledge base.
        Retrieve information from the internal knowledge base.
        For every query, you MUST perform at least one internal search
        call before escalating to web search.
    """

    INLINE_CITATIONS_TOOL: str = """
        IMPORTANT: call this tool RIGHT BEFORE THE FINAL ANSWER.
        `search_tool` must be called before this tool.
        Internal KB only. Submit chunk_id values from `search_tool`
        together with snippets copied character-for-character from that
        chunk's body. The host validates each snippet against the chunk
        text and highlights matching spans in the evidence panel.
    """

    VISUALIZE_SHOW_WIDGET_TOOL: str = (
        "Show visual content — SVG graphics, diagrams, charts, or "
        "interactive HTML widgets — that renders inline alongside "
        "your text response. Use for flowcharts, architecture "
        "diagrams, dashboards, forms, calculators, data tables, "
        "games, illustrations, or any visual content. "
        "The code is auto-detected: starts with <svg = SVG mode, "
        "otherwise HTML mode. "
        "IMPORTANT: Call visualize_read_me before your first "
        "show_widget call. Do NOT narrate or mention the read_me "
        "call to the user."
    )

    VISUALIZE_README_TOOL: str = (
        "Returns required context for show_widget (CSS variables, "
        "colors, typography, layout rules, examples). Call before "
        "your first show_widget call. Do NOT mention or narrate "
        "this call to the user — it is an internal setup step."
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
        ToolNames.VISUALIZE_SHOW_WIDGET_TOOL: FunctionCallDefinition(
            name=ToolNames.VISUALIZE_SHOW_WIDGET_TOOL,
            description=ToolDescriptionArgs.VISUALIZE_SHOW_WIDGET_TOOL,
            input_schema=(VisualizeShowWidgetParameters.model_json_schema()),
        ),
        ToolNames.VISUALIZE_README_TOOL: FunctionCallDefinition(
            name=ToolNames.VISUALIZE_README_TOOL,
            description=ToolDescriptionArgs.VISUALIZE_README_TOOL,
            input_schema=(VisualizeReadmeParameters.model_json_schema()),
        ),
    }

    _AGENTIC_STREAM_TOOL_ORDER: Final[tuple[ToolNames, ...]] = (
        ToolNames.WEB_SEARCH_TOOL,
        ToolNames.VISUALIZE_SHOW_WIDGET_TOOL,
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
