from pathlib import Path

from jinja2 import (
    Environment,
    FileSystemLoader,
    Template,
    TemplateNotFound,
    select_autoescape,
)
from pydantic import BaseModel


class Jinja2PromptSettings(BaseModel):
    trim_blocks: bool = True
    lstrip_blocks: bool = True


class Jinja2Prompts:
    def __init__(
        self,
        promptdir: Path,
        settings: Jinja2PromptSettings | None = None,
    ) -> None:
        self.promptdir = promptdir
        self.settings = settings or Jinja2PromptSettings()
        self.env = Environment(
            loader=FileSystemLoader(self.promptdir),
            autoescape=select_autoescape(),
            trim_blocks=self.settings.trim_blocks,
            lstrip_blocks=self.settings.lstrip_blocks,
        )

    def get(self, template_name: str) -> Template:
        try:
            # Visualization composition templates are authored as HTML snippets;
            # keep the historical .jinja2 extension for surrounding prompts.
            extension = ".html" if template_name.startswith("templates/") else ".jinja2"
            return self.env.get_template(
                f"{template_name}{extension}",
            )
        except TemplateNotFound as err:
            raise ValueError(
                f"Template {template_name} not found in {self.promptdir}. "
            ) from err


class PromptsFactory:
    AGENTIC = Jinja2Prompts(promptdir=Path(__file__).parent / "agentic")
    PROGRAMS = Jinja2Prompts(promptdir=Path(__file__).parent / "programs")
    TOOLS = Jinja2Prompts(promptdir=Path(__file__).parent / "tools")
    VISUALIZATION = Jinja2Prompts(
        promptdir=Path(__file__).parent / "visualization",
    )
