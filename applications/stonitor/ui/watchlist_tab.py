"""Gradio Watchlist tab."""

from __future__ import annotations

import asyncio

import gradio as gr

from applications.stonitor.deps import StonitorDeps
from applications.stonitor.market.exc import InvalidTickerError, MarketError
from applications.stonitor.market.models.dto import WatchlistRow


def _rows_to_table(rows: list[WatchlistRow]) -> list[list[str | int]]:
    return [
        [
            row.ticker,
            row.trend,
            row.severity or "—",
            row.stance or "—",
            row.last_updated.isoformat() if row.last_updated else "",
        ]
        for row in rows
    ]


def render(deps: StonitorDeps) -> None:
    """Render the Danh sách theo dõi tab."""

    async def refresh_rows() -> list[list[str | int]]:
        rows = await deps.watchlist.list_rows()
        return _rows_to_table(rows)

    def sync_refresh() -> list[list[str | int]]:
        return asyncio.run(refresh_rows())

    async def add_ticker(ticker: str) -> tuple[list[list[str | int]], str]:
        try:
            await deps.watchlist.add(ticker)
            rows = await deps.watchlist.list_rows()
            return _rows_to_table(rows), f"Đã thêm {ticker.strip().upper()}"
        except (InvalidTickerError, MarketError) as exc:
            rows = await deps.watchlist.list_rows()
            return _rows_to_table(rows), str(exc)

    def sync_add(ticker: str) -> tuple[list[list[str | int]], str]:
        return asyncio.run(add_ticker(ticker))

    async def remove_ticker(ticker: str) -> tuple[list[list[str | int]], str]:
        try:
            await deps.watchlist.remove(ticker)
            rows = await deps.watchlist.list_rows()
            return (
                _rows_to_table(rows),
                f"Đã xóa {ticker.strip().upper()} khỏi danh sách",
            )
        except (InvalidTickerError, MarketError) as exc:
            rows = await deps.watchlist.list_rows()
            return _rows_to_table(rows), str(exc)

    def sync_remove(ticker: str) -> tuple[list[list[str | int]], str]:
        return asyncio.run(remove_ticker(ticker))

    with gr.Tab("Danh sách theo dõi", id="watchlist"):
        gr.Markdown(
            "### Quản lý danh sách theo dõi\n"
            "Mã trong danh sách được phân tích tự động theo lịch "
            f"({deps.settings.ANALYZE_INTERVAL_MINUTES} phút/lần).",
        )
        with gr.Row():
            ticker_input = gr.Textbox(label="Mã CP", placeholder="FPT")
            add_btn = gr.Button("Thêm", variant="primary")
            remove_btn = gr.Button("Xóa", variant="stop")
        status = gr.Markdown("")
        table = gr.Dataframe(
            headers=[
                "Mã CP",
                "Xu hướng",
                "Mức độ",
                "Phe thắng",
                "Cập nhật",
            ],
            datatype=["str", "str", "str", "str", "str"],
            interactive=False,
        )
        refresh_btn = gr.Button("Làm mới")

        refresh_btn.click(fn=sync_refresh, outputs=table)
        add_btn.click(
            fn=sync_add,
            inputs=ticker_input,
            outputs=[table, status],
        )
        remove_btn.click(
            fn=sync_remove,
            inputs=ticker_input,
            outputs=[table, status],
        )
