from typing import Literal

from jinja2 import Template

from agent.models.streams import FunctionCallOutput, TextItemOutput
from agent.tools.acts.models import BaseToolCall, IToolAct, ToolActResult
from agent.tools.schemas.registry import (
    ToolNames,
    VisualizeReadmeParameters,
)
from agent.tracer import tool_span, tracer_provider

tracer = tracer_provider.get_tracer(__name__)


class VisualizeReadmeToolCall(BaseToolCall[VisualizeReadmeParameters]):
    name: Literal[ToolNames.VISUALIZE_README_TOOL] = ToolNames.VISUALIZE_README_TOOL


class VisualizeReadmeAct(IToolAct[VisualizeReadmeToolCall]):
    """Return design guidelines to the LLM for the requested modules.s

    The LLM calls this silently before inline visualize fences to load
    CSS variable rules, color palette, and layout examples.
    """

    def __init__(
        self,
        readme_template: Template,
        vis_templates: dict[str, Template],
    ) -> None:
        self.readme_template = readme_template
        self.vis_templates = vis_templates

    async def act(
        self,
        tool_call: VisualizeReadmeToolCall,
    ) -> ToolActResult:
        """Render and return the merged module guidelines."""
        with tool_span(
            tracer,
            "VisualizeReadmeAct.act",
            tool_call,
        ) as span:
            modules = tool_call.params.modules
            yield f"Reading guidelines: {', '.join(modules)}\n\n"

            merged = "\n\n---\n\n".join(self.vis_templates[m].render() for m in modules)
            response_str = self.readme_template.render(
                vis_templates=merged,
            )
            output = FunctionCallOutput(
                call_id=tool_call.id,
                output=[
                    TextItemOutput(
                        text=(
                            f"Here is the guide-line\n{response_str}\n"
                            "**Do not repeat** the same tool call with same argument: module twice."
                        ),
                    ),
                ],
            )
            span.set_output(output)
            yield output
