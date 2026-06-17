"""Stonitor Gradio application entrypoint."""

from __future__ import annotations

from pathlib import Path

import gradio as gr

from applications.stonitor.config import StonitorSettings
from applications.stonitor.deps import StonitorDeps
from applications.stonitor.market.db.init_schema import ensure_schema
from applications.stonitor.market.logging import configure_logging
from applications.stonitor.ui import (
    analyze_tab,
    evidence_tab,
    runs_tab,
    watchlist_tab,
)

_STYLES_PATH = Path(__file__).resolve().parent / "ui" / "assets" / "styles.css"


def create_app(deps: StonitorDeps | None = None) -> gr.Blocks:
    container = deps or StonitorDeps()
    css = _STYLES_PATH.read_text(encoding="utf-8")
    with gr.Blocks(title="Stonitor", css=css) as demo:
        gr.Markdown("# Stonitor — Nền tảng quan sát thị trường")
        with gr.Tabs():
            analyze_tab.render(container)
            watchlist_tab.render(container)
            runs_tab.render(container)
            evidence_tab.render(container)
    return demo


def main() -> None:
    settings = StonitorSettings()
    deps = StonitorDeps(settings)
    ensure_schema(settings.DATABASE_URL)
    demo = create_app(deps)
    deps.scheduler.start()
    try:
        demo.launch(
            server_port=settings.GRADIO_SERVER_PORT,
            show_error=True,
        )
    finally:
        deps.scheduler.shutdown()


if __name__ == "__main__":
    main()
