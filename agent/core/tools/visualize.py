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


@lru_cache(1)
def _load_guidance() -> dict[VisualizeModule, str]:
    return {
        module: PromptsFactory.VISUALIZATION.get(module).render()
        for module in VISUALIZATION_MODULES
    }


@lru_cache(1)
def _load_readme() -> str:
    return PromptsFactory.TOOLS.get("visualize_readme").render(
        vis_templates="{vis_templates}",
    )


def build_visualize_tool() -> Tool:
    mp_module_guidance = _load_guidance()
    frontmatter = _load_readme()

    @function_tool
    async def read_readme(
        modules: Annotated[
            list[VisualizeModule],
            Field(description="Visualization modules required for the response"),
        ],
    ) -> str:
        # Load only the application's requested inline visualization guidance.
        merged_guidance = "\n\n---\n\n".join(
            mp_module_guidance[module] for module in modules
        )
        return frontmatter.replace("{vis_templates}", merged_guidance)

    return read_readme
