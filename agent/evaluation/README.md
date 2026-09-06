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
  --limit 50
```

Each run creates a numbered folder under `evaluation/runs/` containing:

- `manifest.json` — captured request IDs per query
- `report.json` — full JSON report with per-query judgments
- `visualizations/` — extracted HTML artifacts from visualize fences

## Latest result: run-2

| Field | Value |
|:------|:------|
| Run | run-2 |
| Started | 2026-07-05 07:19 UTC |
| Queries evaluated | 50 (`--limit 50`) |

### Summary

| Metric | Count |
|:-------|------:|
| Tool-call correct | 47 |
| Tool-call incorrect | 3 |
| Tool-call not judgeable | 0 |
| Visualizations runnable | 31 |
| Visualizations not runnable | 0 |
| Visualizations missing expected | 0 |

**Tool-call accuracy:** 47 / 50 (94%)

**Visualization pass rate (visualize focus only):** 31 / 31 runnable (100%)

### Failed queries

Three retrieval queries were judged **incorrect** because the agent made no
tool calls and replied that no uploaded document was available:

- `retrieval_policy_summary`
- `retrieval_contract_deadline`
- `retrieval_find_definition`

Eval capture runs queries with `file_ids=[]`, so document-grounded retrieval
items are expected to fail unless the agent searches anyway. The remaining 47
queries in this run passed tool-call judgment, including all 30 visualization
queries and the other retrieval/calculation items in the slice.

### Re-run

```bash
uv run python -m evaluation.cli \
  --dataset evaluation/datasets/agent_eval_v1.jsonl \
  --limit 50
```

Omit `--limit` to evaluate all 100 dataset queries.

## Compatibility Notes

- `scripts/agent_eval/*` remains available for the earlier ad hoc trace
  workflow.
- `evaluation/runners/phoenix_traces.py` reuses the same Phoenix span naming
  conventions and canonical tool-name mapping.
- Generated run outputs are ignored by git except for `.gitkeep` placeholders.
