"""Load Phoenix traces and convert them into evaluation models."""

import json
from typing import Any

import pandas as pd
from phoenix.client import Client
from phoenix.trace.dsl import SpanQuery

from agent.core.env import Env

from evaluation.models import (
    AgentTrace,
    EvaluationDataset,
    ToolCall,
    TraceCaptureManifest,
    TraceCaptureStatus,
)
from evaluation.protocols import PhoenixTraceClient

SPAN_TO_TOOL: dict[str, str] = {
    "SearchAct.act": "search_tool",
    "ThinkAct.act": "think_tool",
    "InlineCitationsAct.act": "inline_citations_tool",
    "VisualizeReadmeAct.act": "visualize_read_me",
}


class PhoenixTraceLoader:
    """Phoenix client wrapper for trace span loading."""

    def __init__(self, client: Client, *, project_name: str) -> None:
        self._client = client
        self._project_name = project_name

    @classmethod
    def from_env(cls, env: Env) -> "PhoenixTraceLoader":
        """Create a loader from project environment settings."""
        base_url = env.PHOENIX_ENDPOINT.rsplit("/v1", 1)[0]
        return cls(
            Client(base_url=base_url),
            project_name=env.PHOENIX_PROJECT_NAME,
        )

    def fetch_spans_for_request(self, request_id: str) -> pd.DataFrame:
        """Return spans for one request ID."""
        root_query = (
            SpanQuery()
            .where(f"session.id == '{request_id}' and span_kind == 'CHAIN'")
            .select(trace_id="context.trace_id")
        )
        root_df = self._client.spans.get_spans_dataframe(
            query=root_query,  # type: ignore[arg-type]
            project_identifier=self._project_name,
        )
        if root_df.empty:
            return pd.DataFrame()
        trace_id = _trace_id_from_row(root_df.iloc[0])
        if not trace_id:
            return pd.DataFrame()
        return self.fetch_spans_for_trace(trace_id)

    def fetch_spans_for_trace(self, trace_id: str) -> pd.DataFrame:
        """Return spans for one trace ID."""
        query = (
            SpanQuery()
            .where(f"trace_id == '{trace_id}'")
            .select(
                name="name",
                span_kind="span_kind",
                input="input.value",
                output="output.value",
                trace_id="context.trace_id",
                start_time="start_time",
            )
        )
        return self._client.spans.get_spans_dataframe(
            query=query,  # type: ignore[arg-type]
            project_identifier=self._project_name,
        )


def build_agent_traces(
    dataset: EvaluationDataset,
    manifest: TraceCaptureManifest,
    *,
    loader: PhoenixTraceClient,
) -> list[AgentTrace]:
    """Fetch Phoenix traces for manifest records."""
    selected = dataset.limit()
    mp_query_id_record = {record.id: record for record in selected}
    traces: list[AgentTrace] = []
    for capture in manifest.runs:
        record = mp_query_id_record.get(capture.query_id)
        if record is None:
            continue
        if capture.status == TraceCaptureStatus.FAILED:
            traces.append(
                AgentTrace(
                    query_id=record.id,
                    request_id=capture.request_id,
                    trace_id=capture.trace_id,
                    query=record.query,
                ),
            )
            continue
        spans_df = _fetch_capture_spans(capture.request_id, capture.trace_id, loader)
        traces.append(
            build_agent_trace(
                query_id=record.id,
                query=record.query,
                request_id=capture.request_id,
                spans_df=spans_df,
            ),
        )
    return traces


def build_agent_trace(
    *,
    query_id: str,
    query: str,
    request_id: str,
    spans_df: pd.DataFrame,
) -> AgentTrace:
    """Build one evaluation trace from Phoenix spans."""
    if spans_df.empty:
        return AgentTrace(
            query_id=query_id,
            request_id=request_id,
            query=query,
        )

    chain_rows = spans_df.loc[spans_df["span_kind"] == "CHAIN"]
    root = chain_rows.iloc[0] if not chain_rows.empty else spans_df.iloc[0]
    final_text = str(_row_value(root, "output") or "")
    trace_id = _trace_id_from_row(root)
    trace_query = _query_from_root_input(str(_row_value(root, "input") or ""))
    return AgentTrace(
        query_id=query_id,
        request_id=request_id,
        trace_id=trace_id,
        query=trace_query or query,
        final_text=final_text,
        tool_calls=extract_tool_calls(spans_df),
    )


def extract_tool_calls(spans_df: pd.DataFrame) -> list[ToolCall]:
    """Extract ordered tool calls from Phoenix spans."""
    if spans_df.empty:
        return []
    tool_rows = spans_df.loc[spans_df["span_kind"] == "TOOL"].copy()
    if tool_rows.empty:
        return []
    tool_rows = tool_rows.sort_values("start_time")
    calls: list[ToolCall] = []
    for order, (_, row) in enumerate(tool_rows.iterrows(), start=1):
        span_name = str(_row_value(row, "name") or "")
        tool_name = SPAN_TO_TOOL.get(span_name, span_name)
        output = str(_row_value(row, "output") or "")
        calls.append(
            ToolCall(
                order=order,
                span_name=span_name,
                tool_name=tool_name,
                output_preview=output[:1000],
            ),
        )
    return calls


def format_tool_calls_for_judge(tool_calls: list[ToolCall]) -> str:
    """Render tool calls for an LLM judge prompt."""
    if not tool_calls:
        return "(no tool calls)"
    parts = [
        f"{call.order}. {call.tool_name}\noutput:\n{call.output_preview or '(empty)'}"
        for call in tool_calls
    ]
    return "\n\n".join(parts)


def _fetch_capture_spans(
    request_id: str,
    trace_id: str,
    loader: PhoenixTraceClient,
) -> pd.DataFrame:
    if trace_id:
        return loader.fetch_spans_for_trace(trace_id)
    if request_id:
        return loader.fetch_spans_for_request(request_id)
    return pd.DataFrame()


def _trace_id_from_row(row: pd.Series) -> str:
    raw = _row_value(row, "trace_id") or _row_value(row, "context.trace_id")
    return str(raw or "").strip()


def _row_value(row: pd.Series, key: str) -> Any:
    if key not in row.index:
        return None
    return row[key]


def _query_from_root_input(raw_input: str) -> str:
    text = raw_input.strip()
    if not text:
        return ""
    if not text.startswith("{"):
        return text
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(parsed, dict) and "query" in parsed:
        return str(parsed["query"])
    return text
