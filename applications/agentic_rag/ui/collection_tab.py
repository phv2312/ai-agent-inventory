"""Collection tab UI for uploading and managing indexed files."""

import shutil
from pathlib import Path
from typing import Any

import gradio as gr
import pandas as pd

from applications.agentic_rag.core.registry import FileRegistry
from applications.agentic_rag.services.chat import render_chunks_html
from applications.agentic_rag.services.indexing import IndexingService

FILE_HEADERS = [
    "id",
    "name",
    "size",
    "token",
    "loader",
    "date_created",
]
SELECTED_NONE = "Selected file: (please select above)"


class CollectionTab:
    """Build and wire the File Collection tab."""

    def __init__(
        self,
        registry: FileRegistry,
        indexing_service: IndexingService,
    ) -> None:
        self.registry = registry
        self.indexing_service = indexing_service
        self.upload_dir = Path("data/uploads")
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def _files_dataframe(self) -> pd.DataFrame:
        files = self.registry.list_files()
        rows = [f.as_row() for f in files]
        return pd.DataFrame(rows, columns=FILE_HEADERS)

    def build(self) -> dict[str, Any]:
        with gr.Column(elem_classes=["indices-tab"]):
            with gr.Row():
                with gr.Column(scale=1):
                    with gr.Tab("Upload Files"):
                        self.upload_files = gr.File(
                            file_types=[".pdf"],
                            file_count="multiple",
                            show_label=False,
                        )
                        gr.Markdown(
                            "- Supported file types: .pdf\n"
                            "- Maximum file size: 1000 MB",
                        )
                    with gr.Accordion(
                        "Advanced indexing options",
                        open=False,
                    ):
                        self.force_reindex = gr.Checkbox(
                            label="Force reindex file",
                            value=False,
                        )
                    self.upload_button = gr.Button(
                        "Upload and Index",
                        variant="primary",
                    )

                with gr.Column(scale=4):
                    with gr.Column(
                        visible=False,
                    ) as self.upload_progress_panel:
                        gr.Markdown("## Upload Progress")
                        with gr.Row():
                            self.upload_result = gr.Textbox(
                                label="Upload result",
                                lines=3,
                            )
                            self.upload_info = gr.Textbox(
                                label="Upload info",
                                lines=8,
                            )
                        self.btn_close_progress = gr.Button(
                            "Clear Upload Info and Close",
                            elem_classes=["right-button"],
                        )

                    with gr.Tab("Files"):
                        self.file_list = gr.DataFrame(
                            headers=FILE_HEADERS,
                            interactive=False,
                            wrap=False,
                            elem_id="file_list_view",
                        )
                        with gr.Row():
                            self.chat_button = gr.Button(
                                "Go to Chat",
                                visible=False,
                            )
                            self.download_button = gr.DownloadButton(
                                "Download",
                                visible=False,
                                value=None,
                            )
                            self.delete_button = gr.Button(
                                "Delete",
                                variant="secondary",
                                visible=False,
                                elem_classes=["danger-button"],
                            )
                            self.close_button = gr.Button(
                                "Close",
                                visible=False,
                            )
                        self.selected_file_id = gr.State(value=None)
                        self.selected_panel = gr.Markdown(SELECTED_NONE)
                        self.chunk_header = gr.Markdown(visible=False)
                        self.chunk_type_filter = gr.Dropdown(
                            choices=["all", "text"],
                            value="all",
                            label="Chunk type",
                            show_label=False,
                            visible=False,
                        )
                        self.chunks_html = gr.HTML(visible=False)

        return {
            "upload_files": self.upload_files,
            "upload_button": self.upload_button,
            "file_list": self.file_list,
            "chat_button": self.chat_button,
            "tabs": None,
        }

    def register_events(
        self,
        demo: gr.Blocks,
        main_tabs: gr.Tabs,
        chat_tab: Any,
    ) -> None:
        demo.load(
            self.refresh_file_list,
            outputs=[self.file_list],
        )
        self.upload_button.click(
            self.upload_and_index,
            inputs=[self.upload_files, self.force_reindex],
            outputs=[
                self.upload_progress_panel,
                self.upload_result,
                self.upload_info,
                self.file_list,
                chat_tab.selected_files,
            ],
        )
        self.btn_close_progress.click(
            lambda: gr.Column(visible=False),
            outputs=[self.upload_progress_panel],
        )
        self.file_list.select(
            self.on_file_select,
            inputs=[self.file_list],
            outputs=[
                self.selected_file_id,
                self.selected_panel,
                self.chat_button,
                self.download_button,
                self.delete_button,
                self.close_button,
                self.chunk_header,
                self.chunk_type_filter,
                self.chunks_html,
            ],
        )
        self.chunk_type_filter.change(
            self.load_chunks,
            inputs=[self.selected_file_id, self.chunk_type_filter],
            outputs=[self.chunks_html, self.chunk_header],
        )
        self.close_button.click(
            self.clear_selection,
            outputs=[
                self.selected_file_id,
                self.selected_panel,
                self.chat_button,
                self.download_button,
                self.delete_button,
                self.close_button,
                self.chunk_header,
                self.chunk_type_filter,
                self.chunks_html,
            ],
        )
        self.delete_button.click(
            self.delete_selected,
            inputs=[self.selected_file_id],
            outputs=[
                self.file_list,
                self.selected_file_id,
                self.selected_panel,
                self.chat_button,
                self.download_button,
                self.delete_button,
                self.close_button,
                self.chunk_header,
                self.chunk_type_filter,
                self.chunks_html,
                chat_tab.selected_files,
            ],
        )
        self.chat_button.click(
            lambda: gr.Tabs(selected="chat-tab"),
            outputs=[main_tabs],
        )

    def refresh_file_list(self) -> pd.DataFrame:
        return self._files_dataframe()

    async def upload_and_index(
        self,
        files: list[str] | None,
        force: bool,
    ) -> tuple[Any, ...]:
        if not files:
            return (
                gr.Column(visible=True),
                "No files selected.",
                "",
                self._files_dataframe(),
                gr.update(),
            )

        results: list[str] = []
        logs: list[str] = []
        for src in files:
            src_path = Path(src)
            dest = self.upload_dir / src_path.name
            if dest.exists():
                dest.unlink()
            shutil.copy2(src_path, dest)
            record, file_logs = await self.indexing_service.index_file(
                dest,
                force=force,
            )
            results.append(f"✅ {record.name}")
            logs.extend(file_logs)

        return (
            gr.Column(visible=True),
            "\n".join(results),
            "\n".join(logs),
            self._files_dataframe(),
            chat_tab_refresh(self.registry),
        )

    async def on_file_select(
        self,
        df: pd.DataFrame,
        evt: gr.SelectData,
    ) -> tuple[Any, ...]:
        if df is None or df.empty:
            return self._empty_selection()
        row = df.iloc[evt.index[0]]
        fileid = str(row["id"])
        name = str(row["name"])
        record = self.registry.get(fileid)
        if record is None:
            return self._empty_selection()

        chunks = await self.indexing_service.get_chunks(fileid)
        text_count = len(chunks)
        header = f"**{len(chunks)} chunks** ({text_count} text)"
        chunk_html = render_chunks_html(chunks)
        download_path = record.filepath or None

        return (
            fileid,
            f"Selected file: **{name}**",
            gr.update(visible=True),
            gr.update(visible=True, value=download_path),
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(value=header, visible=True),
            gr.update(visible=True),
            gr.update(value=chunk_html, visible=True),
        )

    def _empty_selection(self) -> tuple[Any, ...]:
        return (
            None,
            SELECTED_NONE,
            gr.update(visible=False),
            gr.update(visible=False, value=None),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    def clear_selection(self) -> tuple[Any, ...]:
        return self._empty_selection()

    async def load_chunks(
        self,
        fileid: str | None,
        chunk_filter: str,
    ) -> tuple[Any, ...]:
        if not fileid:
            return gr.update(visible=False), gr.update(visible=False)
        chunks = await self.indexing_service.get_chunks(
            fileid,
            chunk_filter=chunk_filter,
        )
        return (
            gr.update(value=render_chunks_html(chunks), visible=True),
            gr.update(value=f"**{len(chunks)} chunks**", visible=True),
        )

    async def delete_selected(
        self,
        fileid: str | None,
    ) -> tuple[Any, ...]:
        if fileid:
            await self.indexing_service.delete_file(fileid)
        return (
            self._files_dataframe(),
            *self._empty_selection(),
            chat_tab_refresh(self.registry),
        )


def chat_tab_refresh(registry: FileRegistry) -> Any:
    choices = [f.name for f in registry.list_files()]
    return gr.update(choices=choices, value=[])
