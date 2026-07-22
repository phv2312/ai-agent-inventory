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
            "Private reasoning and retrieval plan. Decide whether the question "
            "is single-hop or multi-hop. For multi-hop questions, identify the "
            "ordered subquestions, the bridge entity/fact needed at each step, "
            "and the evidence required before answering. Use short prose only; "
            "no lists, bullets, citations, or user-facing text. Keep it under "
            "150 words."
        ),
    )


class SearchParameters(BaseToolParameters):
    query: str = Field(
        ...,
        description=(
            "A single focused evidence-seeking query for one retrieval hop. "
            "Include the relevant entity, relation, constraint, and requested "
            "fact. Do not combine unrelated subquestions in one query."
        ),
    )
    granularity: Literal["section", "page", "document"] = Field(
        ...,
        description=(
            "Retrieval level: use section for a precise fact or relation, "
            "page when surrounding context is needed, and document only for "
            "document-level overviews or when locating the relevant section."
        ),
    )
    page_idxs: list[int] | None = Field(
        ...,
        description=(
            "Optional page indexes to restrict this hop. Use when a previous "
            "hop identified likely relevant pages."
        ),
    )
    doc_names: list[str] | None = Field(
        ...,
        description=(
            "Optional document names to restrict this hop. Use when the user "
            "names documents or a prior hop identifies the relevant document."
        ),
    )


class VisualizeReadmeParameters(BaseToolParameters):
    modules: list[VisualizeModule] = Field(
        ...,
        description="Which module(s) to load. Pick all that fit.",
    )


class ToolDescriptionArgs:
    THINK_TOOL: str = (
        "Acts as a private scratchpad for concise reasoning and retrieval "
        "planning. Use before searching when the question may require entity "
        "resolution, comparison, causal reasoning, or multiple dependent facts. "
        "Determine whether it is single-hop or multi-hop. For multi-hop tasks, "
        "decompose the request into ordered evidence-seeking subquestions: "
        "retrieve the prerequisite or bridge fact first, inspect the result, "
        "then derive the next search query from retrieved evidence only. "
        "Never assume an intermediate fact or final conclusion. Do not write "
        "lists or user-facing prose; keep `reflection` direct and under 150 words."
    )

    SEARCH_TOOL: str = (
        "Searches the internal knowledge base for document-grounded context. "
        "Use one focused query for each unresolved fact. For multi-hop questions, "
        "search the first prerequisite or bridge fact, inspect its returned "
        "content and Chunk-IDs, then issue a follow-up query using entities and "
        "relations supported by that evidence. Do not merge dependent hops into "
        "one broad query and do not invent intermediate facts. Use returned "
        "Chunk-IDs for internal citations. Do NOT rely on built-in knowledge "
        "when internal or web sources are required."
    )

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
        # ToolNames.WEB_SEARCH_TOOL,
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
                ToolSchemaRegistry.MP_NAME_TOOLS[ToolNames.THINK_TOOL],
            ]

        return tools
