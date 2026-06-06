"""Tool acts for inline visualization (readme + show-widget)."""

from typing import Literal

from jinja2 import Template

from agent.models.streams import FunctionCallOutput
from agent.tools.acts.models import BaseToolCall, IToolAct, ToolActResult
from agent.tools.schemas.registry import (
    ToolNames,
    VisualizeReadmeParameters,
    VisualizeShowWidgetParameters,
)


class VisualizeReadmeToolCall(BaseToolCall[VisualizeReadmeParameters]):
    """Parsed call for the visualize_read_me tool."""

    name: Literal[ToolNames.VISUALIZE_README_TOOL] = ToolNames.VISUALIZE_README_TOOL


class VisualizeShowWidgetToolCall(BaseToolCall[VisualizeShowWidgetParameters]):
    """Parsed call for the visualize_show_widget tool."""

    name: Literal[ToolNames.VISUALIZE_SHOW_WIDGET_TOOL] = (
        ToolNames.VISUALIZE_SHOW_WIDGET_TOOL
    )


class VisualizeReadmeAct(IToolAct[VisualizeReadmeToolCall]):
    """Return design guidelines to the LLM for the requested modules.

    The LLM calls this silently before show_widget to load CSS
    variable rules, color palette, and layout examples.
    """

    def __init__(
        self,
        readme_template: Template,
        vis_templates: dict[str, Template],
    ) -> None:
        self.readme_template = readme_template
        self.vis_templates = vis_templates

    async def act(self, tool_call: VisualizeReadmeToolCall) -> ToolActResult:
        """Render and return the merged module guidelines."""
        modules = tool_call.params.modules
        yield f"Reading guidelines: {', '.join(modules)}\n\n"

        merged = "\n\n---\n\n".join(self.vis_templates[m].render() for m in modules)
        response_str = self.readme_template.render(
            vis_templates=merged,
        )
        yield FunctionCallOutput(
            call_id=tool_call.id,
            output=response_str,
        )


class VisualizeShowWidgetAct(IToolAct[VisualizeShowWidgetToolCall]):
    """No-op act: rendering happens client-side from streamed args."""

    async def act(self, tool_call: VisualizeShowWidgetToolCall) -> ToolActResult:
        """Acknowledge the widget so the LLM does not repeat it."""
        yield FunctionCallOutput(
            call_id=tool_call.id,
            output=(
                "Content rendered and shown to the user. "
                "Do not duplicate the shown content in text."
            ),
        )
