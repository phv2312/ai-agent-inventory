import json
from typing import Any

from agents import ToolApprovalItem
from pydantic import BaseModel, Field, ValidationError


class PlanSection(BaseModel):
    title: str = Field(min_length=1, description="Concise answer-section heading")
    purpose: str = Field(
        min_length=1,
        description="What this answer section will establish",
    )


class AgentPlan(BaseModel):
    query: str = Field(min_length=1)
    sections: list[PlanSection] = Field(min_length=1)


class AgentInterruption(BaseModel):
    id: str
    agent: str
    tool_name: str
    plan: AgentPlan | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_approval_item(cls, item: ToolApprovalItem) -> "AgentInterruption":
        tool_name = item.name or "unknown"
        mp_str_any = cls._parse_arguments(item.arguments)
        plan = cls._parse_plan(tool_name, mp_str_any)
        return cls(
            id=item.call_id or "unknown",
            agent=item.agent.name,
            tool_name=tool_name,
            plan=plan,
            arguments=mp_str_any,
        )

    @staticmethod
    def _parse_arguments(arguments: str | None) -> dict[str, Any]:
        if not arguments:
            return {}
        try:
            value = json.loads(arguments)
        except json.JSONDecodeError:
            return {"raw": arguments}
        return value if isinstance(value, dict) else {"value": value}

    @staticmethod
    def _parse_plan(
        tool_name: str,
        mp_str_any: dict[str, Any],
    ) -> AgentPlan | None:
        if tool_name != "submit_agent_plan":
            return None
        plan_data = mp_str_any.get("agent_plan", mp_str_any)
        try:
            return AgentPlan.model_validate(plan_data)
        except ValidationError:
            return None
