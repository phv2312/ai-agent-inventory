"""LLM-as-judge evaluator for tool-call correctness."""

import json

from openai import AsyncAzureOpenAI
from pydantic import BaseModel, ValidationError

from agent.core.env import Env

from evaluation.exceptions import JudgeError
from evaluation.models import AgentTrace, ToolCallJudgment, ToolJudgmentLabel
from evaluation.protocols import ToolCallJudge
from evaluation.runners.phoenix_traces import format_tool_calls_for_judge

TOOL_CALL_CORRECTNESS_TEMPLATE = """
You are evaluating whether an agent chose appropriate tools for a user query.

User query:
{query}

Tool calls, in order:
{tool_calls}

Final assistant answer:
{final_text}

Visualization guidance:
- `visualize_read_me` only returns inline-visual formatting guidance
  (chart, diagram, mockup, interactive, art). It does not provide factual
  data or numbers.
- All inline ```visualize:<module>``` fences require calling
  `visualize_read_me` first for module guidance.
- Concrete values and content belong in the fence body itself, not in
  tool output. Do not mark a trace incorrect just because numbers appear
  in the answer without a separate data-retrieval tool when the query is
  primarily asking for a visualization and the fence contains the data.

Return one label:
- "correct": tool usage was appropriate for the query and answer.
- "incorrect": tools were unnecessary, missing, or mismatched.
- "not-judgeable": trace evidence is missing or insufficient.

Respond with JSON only:
{{"label": "...", "explanation": "..."}}
""".strip()


class JudgeResponse(BaseModel):
    """Structured judge response."""

    label: ToolJudgmentLabel
    explanation: str


class AzureToolCallJudge:
    """Azure OpenAI judge for tool-call correctness."""

    def __init__(
        self,
        env: Env,
        *,
        deployment: str | None = None,
    ) -> None:
        self._client = AsyncAzureOpenAI(
            api_key=env.OPENAI_API_KEY,
            api_version=env.OPENAI_API_VERSION,
            azure_endpoint=env.OPENAI_AZURE_ENDPOINT,
        )
        self._deployment = deployment or env.OPENAI_CHAT_DEPLOYMENT_NAME

    async def judge(self, trace: AgentTrace) -> ToolCallJudgment:
        """Judge one trace."""
        if not trace.final_text and not trace.tool_calls:
            return ToolCallJudgment(
                query_id=trace.query_id,
                label=ToolJudgmentLabel.NOT_JUDGEABLE,
                explanation="Phoenix trace evidence is missing or empty.",
                judge_model=self._deployment,
            )

        prompt = TOOL_CALL_CORRECTNESS_TEMPLATE.format(
            query=trace.query,
            tool_calls=format_tool_calls_for_judge(trace.tool_calls),
            final_text=trace.final_text or "(empty)",
        )
        response = await self._client.chat.completions.create(
            model=self._deployment,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are an evaluation judge. Return JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        raw = response.choices[0].message.content or "{}"
        try:
            parsed = JudgeResponse.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as exc:
            msg = f"Invalid tool-call judge response: {raw[:200]}"
            raise JudgeError(msg) from exc

        return ToolCallJudgment(
            query_id=trace.query_id,
            label=parsed.label,
            explanation=parsed.explanation.strip(),
            judge_model=self._deployment,
        )


async def judge_tool_calls(
    trace: AgentTrace,
    *,
    judge: ToolCallJudge,
) -> ToolCallJudgment:
    """Judge tool calls with an injected judge dependency."""
    return await judge.judge(trace)
