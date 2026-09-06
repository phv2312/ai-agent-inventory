"""Pydantic models for evaluation datasets, traces, and reports."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class EvaluationFocus(StrEnum):
    """Supported query evaluation focus values."""

    TOOL_CALL = "tool_call"
    VISUALIZE = "visualize"


class QueryCategory(StrEnum):
    """Suggested dataset category values."""

    FACTUAL = "factual"
    RETRIEVAL = "retrieval"
    CALCULATION = "calculation"
    TRANSFORMATION = "transformation"
    TOOL_OPTIONAL = "tool_optional"
    VISUALIZATION = "visualization"
    MULTI_STEP = "multi_step"


class EvaluationRunStatus(StrEnum):
    """Terminal status for an evaluation run."""

    COMPLETED = "completed"
    FAILED = "failed"


class TraceCaptureStatus(StrEnum):
    """Status for one dataset query capture attempt."""

    CAPTURED = "captured"
    FAILED = "failed"


class ToolJudgmentLabel(StrEnum):
    """Allowed tool-call correctness labels."""

    CORRECT = "correct"
    INCORRECT = "incorrect"
    NOT_JUDGEABLE = "not-judgeable"


class VisualizationStatus(StrEnum):
    """Allowed visualization metric statuses."""

    MISSING_EXPECTED = "missing_expected"
    NOT_EXPECTED = "not_expected"
    RUNNABLE = "runnable"
    NOT_RUNNABLE = "not_runnable"


class EvaluationQuery(BaseModel):
    """One dataset item."""

    id: str
    query: str
    focus: list[EvaluationFocus]
    category: QueryCategory
    notes: str = ""


class EvaluationDataset(BaseModel):
    """Complete loaded evaluation dataset."""

    records: list[EvaluationQuery]

    def limit(self, limit: int = 0) -> list[EvaluationQuery]:
        """Return the first `limit` records, or all when limit is zero."""
        if limit > 0:
            return self.records[:limit]
        return list(self.records)


class EvaluationRun(BaseModel):
    """One evaluation run lifecycle record."""

    run_id: str
    dataset_name: str = "agent_eval_v1"
    dataset_version: str = "v1"
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    trace_manifest_path: str = ""
    query_ids: list[str] = Field(default_factory=list)
    status: EvaluationRunStatus = EvaluationRunStatus.COMPLETED


class TraceCaptureRecord(BaseModel):
    """One attempted dataset query capture."""

    query_id: str
    request_id: str = ""
    trace_id: str = ""
    status: TraceCaptureStatus = TraceCaptureStatus.CAPTURED
    error_message: str = ""


class TraceCaptureManifest(BaseModel):
    """Manifest mapping dataset queries to captured request IDs."""

    run_id: str
    dataset_name: str = "agent_eval_v1"
    dataset_version: str = "v1"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    runs: list[TraceCaptureRecord]


class ToolCall(BaseModel):
    """One observed tool invocation from a Phoenix trace."""

    order: int
    tool_name: str
    span_name: str = ""
    output_preview: str = ""


class AgentTrace(BaseModel):
    """Phoenix trace evidence for one query response."""

    query_id: str
    request_id: str = ""
    trace_id: str = ""
    query: str
    final_text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)


class ToolCallJudgment(BaseModel):
    """LLM-as-judge outcome for tool-call correctness."""

    query_id: str
    label: ToolJudgmentLabel
    explanation: str
    judge_model: str = ""
    error: str = ""


class VisualizationFence(BaseModel):
    """One detected `visualize:<module>` fence."""

    query_id: str
    index: int
    module: str
    code: str


class VisualizationArtifact(BaseModel):
    """Stored file extracted from a visualization block."""

    query_id: str
    request_id: str = ""
    trace_id: str = ""
    fence_index: int
    module: str
    artifact_path: str
    status: VisualizationStatus
    error_message: str = ""


class VisualizationBlockResult(BaseModel):
    """Runnability status for visualization output."""

    query_id: str
    status: VisualizationStatus
    fence_index: int | None = None
    module: str = ""
    artifact_path: str = ""
    error_message: str = ""


class EvaluationDeliverables(BaseModel):
    """Paths to files and folders emitted by a run."""

    json_report_path: str
    visualization_artifacts_dir: str


class ReportSummary(BaseModel):
    """Aggregate evaluation counts."""

    total_queries: int = 0
    tool_correct: int = 0
    tool_incorrect: int = 0
    tool_not_judgeable: int = 0
    visualize_runnable: int = 0
    visualize_not_runnable: int = 0
    visualize_missing_expected: int = 0
    visualize_not_expected: int = 0
    dataset_tool_focus_count: int = 0
    dataset_visualize_focus_count: int = 0


class QueryResult(BaseModel):
    """Per-query result row."""

    query_id: str
    query: str
    focus: list[EvaluationFocus]
    category: QueryCategory
    request_id: str = ""
    trace_id: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_judgment: ToolCallJudgment
    visualization_results: list[VisualizationBlockResult]
    visualization_artifact_paths: list[str] = Field(default_factory=list)
    final_text_preview: str = ""


class EvaluationReport(BaseModel):
    """Saved result of one evaluation run."""

    run: EvaluationRun
    deliverables: EvaluationDeliverables
    summary: ReportSummary
    results: list[QueryResult]
