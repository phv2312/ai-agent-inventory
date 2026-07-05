"""Command line interface for the evaluation benchmark workflow."""

import argparse
import asyncio
from pathlib import Path

from agent.env import Env

from evaluation.dataset_loader import load_dataset
from evaluation.exports import export_visualization_artifacts
from evaluation.models import (
    AgentTrace,
    EvaluationDeliverables,
    EvaluationDataset,
    EvaluationRun,
)
from evaluation.paths import RunPaths, new_run_paths
from evaluation.reports import build_report, write_json_report
from evaluation.runners.phoenix_traces import (
    PhoenixTraceLoader,
    build_agent_traces,
)
from evaluation.runners.trace_capture import capture_dataset_traces

PHOENIX_INDEX_SLEEP_SECONDS = 2.0


def build_parser() -> argparse.ArgumentParser:
    """Build the benchmark CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0)
    return parser


async def run_benchmark(
    *,
    dataset_path: Path,
    limit: int,
    paths: RunPaths,
) -> None:
    """Capture traces, evaluate them, and write deliverables."""
    dataset = load_dataset(dataset_path)
    manifest = await capture_dataset_traces(
        dataset,
        manifest_path=paths.manifest,
        limit=limit,
        run_id=paths.run_id,
    )
    await asyncio.sleep(PHOENIX_INDEX_SLEEP_SECONDS)
    env = Env()
    loader = PhoenixTraceLoader.from_env(env)
    traces = build_agent_traces(
        dataset,
        manifest,
        loader=loader,
    )
    run = EvaluationRun(
        run_id=manifest.run_id,
        trace_manifest_path=str(paths.manifest),
        query_ids=[record.query_id for record in manifest.runs],
    )
    await _write_outputs(paths, dataset=dataset, run=run, traces=traces)


async def _write_outputs(
    paths: RunPaths,
    *,
    dataset: EvaluationDataset,
    run: EvaluationRun,
    traces: list[AgentTrace],
) -> None:
    artifacts = export_visualization_artifacts(
        traces,
        artifacts_dir=paths.artifacts_dir,
    )
    deliverables = EvaluationDeliverables(
        json_report_path=str(paths.report),
        visualization_artifacts_dir=str(paths.artifacts_dir),
    )
    report = await build_report(
        dataset,
        run=run,
        traces=traces,
        artifacts=artifacts,
        deliverables=deliverables,
    )
    write_json_report(report, paths.report)
    print(f"Run dir: {paths.run_dir}")
    print(f"Manifest: {paths.manifest}")
    print(f"Report: {paths.report}")
    print(f"Artifacts: {paths.artifacts_dir}")


def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()
    paths = new_run_paths()
    asyncio.run(
        run_benchmark(
            dataset_path=args.dataset,
            limit=args.limit,
            paths=paths,
        ),
    )


if __name__ == "__main__":
    main()
