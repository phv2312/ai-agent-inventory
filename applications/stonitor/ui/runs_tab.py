"""Gradio Runs tab."""

from __future__ import annotations

import asyncio

import gradio as gr

from applications.stonitor.deps import StonitorDeps
from applications.stonitor.market.models.dto import AnalysisRunDTO


def _runs_to_table(runs: list[AnalysisRunDTO]) -> list[list[str | int | None]]:
    return [
        [
            str(run.id),
            run.ticker or "",
            run.run_type.value,
            run.status.value,
            run.duration_ms if run.duration_ms is not None else "",
            run.error_message or "",
            run.started_at.isoformat(),
        ]
        for run in runs
    ]


def render(deps: StonitorDeps) -> None:
    """Render the Lịch sử chạy tab."""

    async def refresh_runs() -> list[list[str | int | None]]:
        runs = await deps.analysis.list_runs(limit=50)
        return _runs_to_table(runs)

    def sync_refresh() -> list[list[str | int | None]]:
        return asyncio.run(refresh_runs())

    with gr.Tab("Lịch sử chạy", id="runs"):
        gr.Markdown("### Lịch sử phân tích và job nền")
        table = gr.Dataframe(
            headers=[
                "ID",
                "Mã CP",
                "Loại",
                "Trạng thái",
                "Thời gian (ms)",
                "Lỗi",
                "Bắt đầu",
            ],
            datatype=[
                "str",
                "str",
                "str",
                "str",
                "number",
                "str",
                "str",
            ],
            interactive=False,
        )
        refresh_btn = gr.Button("Làm mới")
        refresh_btn.click(fn=sync_refresh, outputs=table)
