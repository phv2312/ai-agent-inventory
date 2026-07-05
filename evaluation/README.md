# Evaluation

This package owns the agent evaluation dataset, Phoenix trace capture,
metric evaluation, and maintainer-facing deliverables.

Primary workflow:

1. Load `evaluation/datasets/agent_eval_v1.jsonl`.
2. Run the CLI to capture traces, evaluate them, and export deliverables
   into a numbered run folder under `evaluation/runs/`.

See `specs/013-evaluation-dataset/quickstart.md` for the current command
contract.

## Command

```bash
uv run python -m evaluation.cli \
  --dataset evaluation/datasets/agent_eval_v1.jsonl \
  --limit 3
```

Each run creates a folder such as `evaluation/runs/run-12/` containing:

- `manifest.json`
- `report.json`
- `visualizations/`

## Compatibility Notes

- `scripts/agent_eval/*` remains available for the earlier ad hoc trace
  workflow.
- `evaluation/runners/phoenix_traces.py` reuses the same Phoenix span naming
  conventions and canonical tool-name mapping.
- Generated run outputs are ignored by git except for `.gitkeep` placeholders.
