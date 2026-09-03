"""Protocols for injectable evaluation workflow dependencies."""

from typing import Protocol

import pandas as pd

from evaluation.models import AgentTrace, EvaluationQuery, ToolCallJudgment


class AgentStreamRunner(Protocol):
    """Dependency that captures one agent response trace."""

    async def capture(
        self,
        query: EvaluationQuery,
        *,
        request_id: str,
    ) -> None:
        """Run the agent for one query and let tracing capture the result."""


class PhoenixTraceClient(Protocol):
    """Dependency that loads Phoenix spans."""

    def fetch_spans_for_request(self, request_id: str) -> pd.DataFrame:
        """Return spans for one request ID."""

    def fetch_spans_for_trace(self, trace_id: str) -> pd.DataFrame:
        """Return spans for one trace ID."""


class ToolCallJudge(Protocol):
    """Dependency that judges tool-call correctness."""

    async def judge(self, trace: AgentTrace) -> ToolCallJudgment:
        """Return a tool-call judgment for one trace."""
