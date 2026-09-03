"""Classify visualization block runnability."""

from collections.abc import Callable

from evaluation.evaluators.visualize_fences import (
    extract_visualization_fences,
    invalid_visualize_modules,
)
from evaluation.models import (
    AgentTrace,
    EvaluationFocus,
    EvaluationQuery,
    VisualizationBlockResult,
    VisualizationFence,
    VisualizationStatus,
)

type VisualizationExecutor = Callable[[VisualizationFence], str]


def classify_visualizations(
    query: EvaluationQuery,
    trace: AgentTrace,
    *,
    execute: VisualizationExecutor | None = None,
) -> list[VisualizationBlockResult]:
    """Classify visualization results for one query response."""
    invalid_modules = invalid_visualize_modules(trace.final_text)
    if invalid_modules:
        return [
            VisualizationBlockResult(
                query_id=query.id,
                status=VisualizationStatus.NOT_RUNNABLE,
                error_message=(
                    f"Unknown visualize module(s): {', '.join(invalid_modules)}"
                ),
            ),
        ]

    fences = extract_visualization_fences(
        query_id=query.id,
        text=trace.final_text,
    )
    if not fences and EvaluationFocus.VISUALIZE in query.focus:
        return [
            VisualizationBlockResult(
                query_id=query.id,
                status=VisualizationStatus.MISSING_EXPECTED,
                error_message="Expected a visualize fence but none was found.",
            ),
        ]
    if not fences:
        return [
            VisualizationBlockResult(
                query_id=query.id,
                status=VisualizationStatus.NOT_EXPECTED,
            ),
        ]

    results: list[VisualizationBlockResult] = []
    for fence in fences:
        error_message = ""
        if execute is not None:
            error_message = execute(fence)
        if error_message:
            results.append(
                VisualizationBlockResult(
                    query_id=query.id,
                    status=VisualizationStatus.NOT_RUNNABLE,
                    fence_index=fence.index,
                    module=fence.module,
                    error_message=error_message,
                ),
            )
            continue
        results.append(
            VisualizationBlockResult(
                query_id=query.id,
                status=VisualizationStatus.RUNNABLE,
                fence_index=fence.index,
                module=fence.module,
            ),
        )
    return results


def syntax_smoke_executor(fence: VisualizationFence) -> str:
    """Return an error message when a fence body is obviously not runnable."""
    code = fence.code.strip()
    if not code:
        return "Visualization block is empty."
    opens = code.count("<script")
    closes = code.count("</script>")
    if opens != closes:
        return "Mismatched script tags."
    open_braces = code.count("{")
    close_braces = code.count("}")
    if open_braces > close_braces:
        return "Missing closing curly brace."
    if close_braces > open_braces:
        return "Missing opening curly brace."
    return ""
