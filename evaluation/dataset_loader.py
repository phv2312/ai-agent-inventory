"""Dataset JSONL loading and validation."""

import json
from pathlib import Path

from pydantic import ValidationError

from evaluation.exceptions import DatasetValidationError
from evaluation.models import EvaluationDataset, EvaluationQuery


def load_dataset(path: Path) -> EvaluationDataset:
    """Load and validate an evaluation dataset from JSONL."""
    if not path.is_file():
        msg = f"Dataset not found: {path}"
        raise DatasetValidationError(msg)

    records: list[EvaluationQuery] = []
    errors: list[str] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            records.append(EvaluationQuery.model_validate(raw))
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            errors.append(f"{path}:{line_number}: {exc}")

    if errors:
        raise DatasetValidationError("\n".join(errors))

    return EvaluationDataset(records=records)

