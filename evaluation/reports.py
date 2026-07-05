"""Build, write, and summarize evaluation reports."""

import json
from pathlib import Path

from agent.env import Env

from evaluation.evaluators.tool_call_correctness import AzureToolCallJudge
from evaluation.evaluators.visualize_runnability import (
    classify_visualizations,
    syntax_smoke_executor,
)
from evaluation.models import (
    AgentTrace,
    EvaluationDataset,
    EvaluationDeliverables,
    EvaluationFocus,
    EvaluationReport,
    EvaluationRun,
    QueryResult,
    ReportSummary,
    ToolCallJudgment,
    ToolJudgmentLabel,
    VisualizationArtifact,
    VisualizationBlockResult,
    VisualizationStatus,
)
from evaluation.paths import ensure_parent
from evaluation.protocols import ToolCallJudge


async def build_report(
    dataset: EvaluationDataset,
    *,
    run: EvaluationRun,
    traces: list[AgentTrace],
    artifacts: dict[tuple[str, int], VisualizationArtifact],
    deliverables: EvaluationDeliverables,
    judge: ToolCallJudge | None = None,
) -> EvaluationReport:
    """Build a complete report from traces and metric outputs."""
    active_judge = judge or AzureToolCallJudge(Env())
    mp_query_id_record = {
        record.id: record for record in dataset.limit()
    }
    results: list[QueryResult] = []
    for trace in traces:
        record = mp_query_id_record[trace.query_id]
        tool_judgment = await _judge_trace(active_judge, trace)
        visual_results = classify_visualizations(
            record,
            trace,
            execute=syntax_smoke_executor,
        )
        visual_results = _attach_artifact_paths(visual_results, artifacts)
        results.append(
            QueryResult(
                query_id=record.id,
                query=record.query,
                focus=record.focus,
                category=record.category,
                request_id=trace.request_id,
                trace_id=trace.trace_id,
                tool_calls=trace.tool_calls,
                tool_judgment=tool_judgment,
                visualization_results=visual_results,
                visualization_artifact_paths=[
                    result.artifact_path
                    for result in visual_results
                    if result.artifact_path
                ],
                final_text_preview=trace.final_text[:500],
            ),
        )

    report = EvaluationReport(
        run=run,
        deliverables=deliverables,
        summary=_build_summary(dataset, results),
        results=results,
    )
    return report


def write_json_report(report: EvaluationReport, path: Path) -> None:
    """Write a canonical JSON report."""
    ensure_parent(path)
    path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def summarize_report(path: Path) -> str:
    """Return a concise text summary for one report file."""
    report = EvaluationReport.model_validate_json(
        path.read_text(encoding="utf-8"),
    )
    lines = [
        f"total_queries={report.summary.total_queries}",
        (
            "tool_call_correctness="
            f"correct:{report.summary.tool_correct} "
            f"incorrect:{report.summary.tool_incorrect} "
            f"not-judgeable:{report.summary.tool_not_judgeable}"
        ),
        (
            "visualizations="
            f"runnable:{report.summary.visualize_runnable} "
            f"not_runnable:{report.summary.visualize_not_runnable} "
            f"missing:{report.summary.visualize_missing_expected}"
        ),
    ]
    failed = _failed_query_ids(report)
    if failed:
        lines.append("failed_query_ids=" + ", ".join(failed))
    return "\n".join(lines)


async def _judge_trace(
    judge: ToolCallJudge,
    trace: AgentTrace,
) -> ToolCallJudgment:
    if not trace.final_text and not trace.tool_calls:
        return ToolCallJudgment(
            query_id=trace.query_id,
            label=ToolJudgmentLabel.NOT_JUDGEABLE,
            explanation="Phoenix trace evidence is missing or empty.",
        )
    return await judge.judge(trace)


def _attach_artifact_paths(
    results: list[VisualizationBlockResult],
    artifacts: dict[tuple[str, int], VisualizationArtifact],
) -> list[VisualizationBlockResult]:
    updated: list[VisualizationBlockResult] = []
    for result in results:
        if result.fence_index is None:
            updated.append(result)
            continue
        artifact = artifacts.get((result.query_id, result.fence_index))
        if artifact is None:
            updated.append(result)
            continue
        updated.append(
            result.model_copy(update={"artifact_path": artifact.artifact_path}),
        )
    return updated


def _build_summary(
    dataset: EvaluationDataset,
    results: list[QueryResult],
) -> ReportSummary:
    records = dataset.records
    return ReportSummary(
        total_queries=len(results),
        tool_correct=sum(
            result.tool_judgment.label == ToolJudgmentLabel.CORRECT
            for result in results
        ),
        tool_incorrect=sum(
            result.tool_judgment.label == ToolJudgmentLabel.INCORRECT
            for result in results
        ),
        tool_not_judgeable=sum(
            result.tool_judgment.label == ToolJudgmentLabel.NOT_JUDGEABLE
            for result in results
        ),
        visualize_runnable=sum(
            visual.status == VisualizationStatus.RUNNABLE
            for result in results
            for visual in result.visualization_results
        ),
        visualize_not_runnable=sum(
            visual.status == VisualizationStatus.NOT_RUNNABLE
            for result in results
            for visual in result.visualization_results
        ),
        visualize_missing_expected=sum(
            visual.status == VisualizationStatus.MISSING_EXPECTED
            for result in results
            for visual in result.visualization_results
        ),
        visualize_not_expected=sum(
            visual.status == VisualizationStatus.NOT_EXPECTED
            for result in results
            for visual in result.visualization_results
        ),
        dataset_tool_focus_count=sum(
            EvaluationFocus.TOOL_CALL in record.focus for record in records
        ),
        dataset_visualize_focus_count=sum(
            EvaluationFocus.VISUALIZE in record.focus for record in records
        ),
    )


def _failed_query_ids(report: EvaluationReport) -> list[str]:
    ids: list[str] = []
    for result in report.results:
        tool_failed = result.tool_judgment.label != ToolJudgmentLabel.CORRECT
        visual_failed = any(
            visual.status in {
                VisualizationStatus.NOT_RUNNABLE,
                VisualizationStatus.MISSING_EXPECTED,
            }
            for visual in result.visualization_results
        )
        if tool_failed or visual_failed:
            ids.append(result.query_id)
    return ids
