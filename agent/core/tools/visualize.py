from functools import lru_cache
from typing import Annotated, Literal

from agents import Tool, function_tool
from pydantic import Field

from agent.core.prompts.core import PromptsFactory


type VisualizeModule = Literal[
    "interactive",
    "chart",
    "diagram",
    "mockup",
    "art",
]

VISUALIZATION_MODULES: tuple[VisualizeModule, ...] = (
    "interactive",
    "chart",
    "diagram",
    "mockup",
    "art",
)


MODULE_TEMPLATES: dict[VisualizeModule, tuple[str, ...]] = {
    "interactive": ("layout", "controls"),
    "chart": ("layout", "chart"),
    "diagram": ("layout", "mermaid"),
    "mockup": ("layout", "controls"),
    "art": ("svg",),
}


@lru_cache(maxsize=None)
def _render(name: str) -> str:
    return PromptsFactory.VISUALIZATION.get(name).render()


def render_module_guidance(modules: list[VisualizeModule]) -> str:
    """Assemble shared guidance and each requested module/template exactly once."""
    requested = list(dict.fromkeys(modules))
    for module in requested:
        if module not in MODULE_TEMPLATES:
            raise ValueError(f"Unknown visualization module: {module}")
    templates = dict.fromkeys(
        template for module in requested for template in MODULE_TEMPLATES[module]
    )
    sections = [_render("shared")]
    sections.extend(_render(module) for module in requested)
    sections.extend(_render(f"templates/{name}") for name in templates)
    return "\n\n---\n\n".join(sections)


def build_visualize_tool() -> Tool:
    @function_tool
    async def read_module_guideline(
        modules: Annotated[
            list[VisualizeModule],
            Field(description="Visualization modules required for the response"),
        ],
    ) -> str:
        """Read composable visualization guidance for all needed modules together."""
        return render_module_guidance(modules)

    return read_module_guideline
