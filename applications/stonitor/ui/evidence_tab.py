"""Gradio Evidence Explorer tab."""

from __future__ import annotations

import asyncio

import gradio as gr

from applications.stonitor.deps import StonitorDeps
from applications.stonitor.market.models.dto import EvidenceRegistry


def _registry_to_table(registry: EvidenceRegistry) -> list[list[str]]:
    return [
        [
            record.id,
            record.category,
            record.label,
            record.value,
            record.source or "",
            record.captured_at.isoformat(),
        ]
        for record in registry.records.values()
    ]


def render(deps: StonitorDeps) -> None:
    """Render the Bằng chứng tab."""

    async def load_evidence(ticker: str) -> list[list[str]]:
        symbol = ticker.strip().upper()
        if not symbol:
            return []
        registry = await deps.evidence.list_all(symbol)
        return _registry_to_table(registry)

    def sync_load(ticker: str) -> list[list[str]]:
        return asyncio.run(load_evidence(ticker))

    with gr.Tab("Bằng chứng", id="evidence"):
        gr.Markdown("### Khám phá bằng chứng tín hiệu")
        with gr.Row():
            ticker_input = gr.Textbox(label="Mã CP", placeholder="VNM")
            load_btn = gr.Button("Tải bằng chứng", variant="primary")
        table = gr.Dataframe(
            headers=[
                "ID",
                "Danh mục",
                "Nhãn",
                "Giá trị",
                "Nguồn",
                "Thời điểm",
            ],
            datatype=["str", "str", "str", "str", "str", "str"],
            interactive=False,
        )
        load_btn.click(fn=sync_load, inputs=ticker_input, outputs=table)
