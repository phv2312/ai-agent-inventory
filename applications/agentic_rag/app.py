import os

os.environ.setdefault("GRPC_VERBOSITY", "NONE")
os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "0")

from pathlib import Path

import gradio as gr

from agent.deps import Container
from applications.agentic_rag.core.registry import FileRegistry
from applications.agentic_rag.services.chat import ChatService
from applications.agentic_rag.services.indexing import IndexingService
from applications.agentic_rag.ui.chat_tab import ChatTab
from applications.agentic_rag.ui.collection_tab import CollectionTab
from applications.agentic_rag.ui.theme import KotaemonTheme

APP_VERSION = "0.1.0"
ASSETS_DIR = Path(__file__).parent / "assets"
STYLES_PATH = Path(__file__).parent / "styles.css"


def create_demo() -> gr.Blocks:
    """Build the Gradio Blocks demo."""
    container = Container()
    registry = FileRegistry()
    indexing_service = IndexingService(container, registry)
    chat_service = ChatService(container)

    chat_tab = ChatTab(registry, chat_service)
    collection_tab = CollectionTab(registry, indexing_service)

    css = STYLES_PATH.read_text(encoding="utf-8")
    js = (ASSETS_DIR / "main.js").read_text(encoding="utf-8")
    js = js.replace("APP_VERSION", APP_VERSION)
    theme = KotaemonTheme()

    with gr.Blocks(
        title="Agentic RAG",
        theme=theme,
        css=css,
        js=js,
        analytics_enabled=False,
        fill_width=True,
    ) as demo:
        with gr.Tabs() as main_tabs:
            with gr.Tab("Chat", elem_id="chat-tab", id="chat-tab"):
                chat_tab.build()
            with gr.Tab(
                "File Collection",
                elem_id="indices-tab",
                elem_classes=[
                    "fill-main-area-height",
                    "scrollable",
                    "indices-tab",
                ],
                id="indices-tab",
            ):
                collection_tab.build()

        chat_tab.register_events(demo)
        collection_tab.register_events(demo, main_tabs, chat_tab)

    return demo


def main() -> None:
    demo = create_demo()
    demo.queue(default_concurrency_limit=4)
    demo.launch()


if __name__ == "__main__":
    main()
