"""Filesystem helpers for evaluation outputs."""

from dataclasses import dataclass
from pathlib import Path


DEFAULT_DATASET_PATH = Path("evaluation/datasets/agent_eval_v1.jsonl")
DEFAULT_RUNS_DIR = Path("evaluation/runs")


@dataclass(frozen=True)
class RunPaths:
    """Standard output paths for one benchmark run."""

    run_dir: Path
    manifest: Path
    report: Path
    artifacts_dir: Path

    @property
    def run_id(self) -> str:
        """Return the run folder name, e.g. `run-12`."""
        return self.run_dir.name


def new_run_paths(runs_dir: Path = DEFAULT_RUNS_DIR) -> RunPaths:
    """Create the next numbered run directory and its output paths."""
    runs_dir.mkdir(parents=True, exist_ok=True)
    max_num = 0
    for path in runs_dir.iterdir():
        if not path.is_dir() or not path.name.startswith("run-"):
            continue
        suffix = path.name.removeprefix("run-")
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))
    run_dir = runs_dir / f"run-{max_num + 1}"
    run_dir.mkdir()
    return RunPaths(
        run_dir=run_dir,
        manifest=run_dir / "manifest.json",
        report=run_dir / "report.json",
        artifacts_dir=run_dir / "visualizations",
    )


def ensure_parent(path: Path) -> None:
    """Create parent directories for a file path."""
    path.parent.mkdir(parents=True, exist_ok=True)


def safe_filename_part(value: str) -> str:
    """Return a filesystem-safe lowercase filename component."""
    chars: list[str] = []
    for char in value.strip().lower():
        if char.isalnum() or char in {"-", "_"}:
            chars.append(char)
        elif char.isspace():
            chars.append("_")
    result = "".join(chars).strip("_")
    return result or "item"
