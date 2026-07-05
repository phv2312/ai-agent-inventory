"""Export visualization artifacts."""

import json
from pathlib import Path

from evaluation.evaluators.visualize_fences import extract_visualization_fences
from evaluation.models import (
    AgentTrace,
    VisualizationArtifact,
    VisualizationStatus,
)
from evaluation.paths import safe_filename_part
from evaluation.widget_runtime import wrap_visualization_html


def export_visualization_artifacts(
    traces: list[AgentTrace],
    *,
    artifacts_dir: Path,
) -> dict[tuple[str, int], VisualizationArtifact]:
    """Extract visualization fences into HTML files and index JSON."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[tuple[str, int], VisualizationArtifact] = {}
    for trace in traces:
        fences = extract_visualization_fences(
            query_id=trace.query_id,
            text=trace.final_text,
        )
        for fence in fences:
            filename = (
                f"{safe_filename_part(fence.query_id)}"
                f"__viz_{fence.index}__{safe_filename_part(fence.module)}.html"
            )
            path = artifacts_dir / filename
            path.write_text(wrap_visualization_html(fence.code), encoding="utf-8")
            artifact = VisualizationArtifact(
                query_id=fence.query_id,
                request_id=trace.request_id,
                trace_id=trace.trace_id,
                fence_index=fence.index,
                module=fence.module,
                artifact_path=str(path),
                status=VisualizationStatus.RUNNABLE,
            )
            artifacts[(fence.query_id, fence.index)] = artifact
    _write_artifact_index(artifacts_dir, list(artifacts.values()))
    return artifacts


def _write_artifact_index(
    artifacts_dir: Path,
    artifacts: list[VisualizationArtifact],
) -> None:
    index_path = artifacts_dir / "index.json"
    index_path.write_text(
        json.dumps(
            [artifact.model_dump(mode="json") for artifact in artifacts],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
