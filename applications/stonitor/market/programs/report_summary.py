"""Report summary program using structured LLM output."""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Template

from agent.chats.interface import IChatModel
from agent.models.messages import UserMessage
from agent.programs.base import BaseProgram

from applications.stonitor.market.models.dto import (
    CitedSummary,
    EvidenceRegistry,
)

_PROMPT_PATH = (
    Path(__file__).resolve().parents[2] / "prompts" / "report_summary.jinja2"
)


class ReportSummaryProgram(BaseProgram[CitedSummary]):
    """Generate cited Vietnamese summary from evidence registry."""

    ModelOutCls = CitedSummary

    def __init__(
        self,
        chat_model: IChatModel,
        model_name: str,
        *,
        template: Template | None = None,
    ) -> None:
        super().__init__(chat_model, model_name)
        if template is None:
            template = Template(_PROMPT_PATH.read_text(encoding="utf-8"))
        self.template = template

    async def generate(self, registry: EvidenceRegistry) -> CitedSummary:
        """Summarize evidence with citation IDs only."""
        evidence_json = json.dumps(
            [record.model_dump(mode="json") for record in registry.records.values()],
            ensure_ascii=False,
            indent=2,
        )
        prompt = UserMessage(
            content=self.template.render(evidence_json=evidence_json),
        )
        return await self.aprocess(prompt)
