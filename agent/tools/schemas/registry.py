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
    WEB_SEARCH_TOOL = "web_search_tool"
    VISUALIZE_SHOW_WIDGET_TOOL = "visualize_show_widget"


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
        default=None,
        description="Optional page indexes to restrict search scope.",
    )
    doc_names: list[str] | None = Field(
        default=None,
        description="Optional document names to restrict search scope.",
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
        ToolNames.WEB_SEARCH_TOOL: WebSearchToolDefinition(
            search_context_size="high",
        ),
    }

    _AGENTIC_STREAM_TOOL_ORDER: Final[tuple[ToolNames, ...]] = (
        ToolNames.WEB_SEARCH_TOOL,
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
                ToolSchemaRegistry.MP_NAME_TOOLS[ToolNames.THINK_TOOL],
            ]

        return tools
