"""Run dataset queries through the agent to create Phoenix traces."""

import json
from pathlib import Path

from pydantic import ValidationError

from agent.deps.container import container
from agent.tracer import new_request_id

from evaluation.exceptions import TraceCaptureError
from evaluation.models import (
    EvaluationDataset,
    EvaluationQuery,
    TraceCaptureManifest,
    TraceCaptureRecord,
    TraceCaptureStatus,
)
from evaluation.paths import ensure_parent
from evaluation.protocols import AgentStreamRunner


class DefaultAgentStreamRunner:
    """Capture traces by consuming `agent.stream_async_answer`."""

    async def capture(
        self,
        query: EvaluationQuery,
        *,
        request_id: str,
    ) -> None:
        """Run one query and consume all stream events."""
        agentic = container.agentic.get()
        events = await agentic.stream_async_answer(
            query=query.query,
            file_ids=[],
        )
        async for _event in events.stream_events():
            pass


async def capture_dataset_traces(
    dataset: EvaluationDataset,
    *,
    manifest_path: Path,
    limit: int = 0,
    run_id: str = "",
    runner: AgentStreamRunner | None = None,
) -> TraceCaptureManifest:
    """Capture selected dataset records and persist a manifest."""
    selected = dataset.limit(limit)
    active_runner = runner or DefaultAgentStreamRunner()
    records: list[TraceCaptureRecord] = []
    for record in selected:
        request_id = new_request_id()
        try:
            await active_runner.capture(record, request_id=request_id)
            records.append(
                TraceCaptureRecord(
                    query_id=record.id,
                    request_id=request_id,
                    status=TraceCaptureStatus.CAPTURED,
                ),
            )
        except Exception as exc:
            records.append(
                TraceCaptureRecord(
                    query_id=record.id,
                    request_id=request_id,
                    status=TraceCaptureStatus.FAILED,
                    error_message=str(exc),
                ),
            )

    manifest = TraceCaptureManifest(
        run_id=run_id or manifest_path.parent.name,
        runs=records,
    )
    save_trace_capture_manifest(manifest, manifest_path)
    return manifest


def save_trace_capture_manifest(
    manifest: TraceCaptureManifest,
    path: Path,
) -> None:
    """Write a trace capture manifest to disk."""
    ensure_parent(path)
    path.write_text(
        json.dumps(
            manifest.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def load_trace_capture_manifest(path: Path) -> TraceCaptureManifest:
    """Load a trace capture manifest from disk."""
    if not path.is_file():
        msg = f"Trace manifest not found: {path}"
        raise TraceCaptureError(msg)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return TraceCaptureManifest.model_validate(raw)
    except (json.JSONDecodeError, ValidationError) as exc:
        msg = f"Invalid trace manifest: {path}"
        raise TraceCaptureError(msg) from exc
