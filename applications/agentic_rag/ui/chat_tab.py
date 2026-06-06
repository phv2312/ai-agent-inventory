"""Chat tab UI inspired by kotaemon."""

import asyncio
from pathlib import Path
from typing import Any

import gradio as gr

from applications.agentic_rag.core.models import Conversation
from applications.agentic_rag.core.registry import FileRegistry
from applications.agentic_rag.services.chat import (
    ChatService,
    build_citation_map,
    enrich_citations,
    parse_cited_chunk_ids,
    render_info_panel,
)
from applications.agentic_rag.ui.widget import render_widget_iframe

ASSETS_DIR = str(Path(__file__).parent.parent / "assets" / "icons")


def _render_info_with_widget(
    sources: list,
    *,
    widget_code: str,
    widget_title: str | None,
) -> str:
    """Combine widget iframe + source chunks into one info panel HTML."""
    parts: list[str] = []
    if widget_code.strip():
        iframe = render_widget_iframe(widget_code, title=widget_title)
        parts.append(f'<div class="info-widget-block">{iframe}</div>')
    parts.append(render_info_panel(sources))
    return "\n".join(parts)


PLACEHOLDER = "This is the beginning of a new conversation.\nStart by uploading a file"


class ChatTab:
    """Build and wire the Chat tab."""

    def __init__(
        self,
        registry: FileRegistry,
        chat_service: ChatService,
    ) -> None:
        self.registry = registry
        self.chat_service = chat_service
        self.conversations: dict[str, Conversation] = {}
        self._active_id = ""

    # ── helpers ──────────────────────────────────────────────────────────

    def _ensure_default(self) -> Conversation:
        if not self.conversations:
            conv = Conversation(name="New conversation")
            self.conversations[conv.id] = conv
            self._active_id = conv.id
        return self.conversations[self._active_id]

    def _conv_choices(self) -> list[tuple[str, str]]:
        return [(c.name, c.id) for c in self.conversations.values()]

    def _file_choices(self) -> list[str]:
        return [f.name for f in self.registry.list_files()]

    def _sanitize_file_selection(self, value: Any) -> list[str]:
        choices = self._file_choices()
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value in choices else []
        return [v for v in value if isinstance(v, str) and v in choices]

    def _file_dropdown_update(
        self,
        *,
        value: list[str] | None = None,
        visible: bool | None = None,
    ) -> Any:
        valid = self._sanitize_file_selection(value or [])
        kwargs: dict[str, Any] = {
            "choices": self._file_choices(),
            "value": valid,
        }
        if visible is not None:
            kwargs["visible"] = visible
        return gr.update(**kwargs)

    def _resolve_file_ids(
        self,
        search_mode: str,
        selected_names: list[str],
    ) -> list[str]:
        all_files = self.registry.list_files()
        if search_mode == "all":
            return [f.fileid for f in all_files]
        name_to_id = {f.name: f.fileid for f in all_files}
        return [name_to_id[n] for n in selected_names if n in name_to_id]

    # ── layout ───────────────────────────────────────────────────────────

    def build(self) -> dict[str, Any]:
        with gr.Column():
            with gr.Row():
                # ── left sidebar ──────────────────────────────────────
                with gr.Column(
                    scale=1,
                    elem_id="conv-settings-panel",
                ) as self.conv_column:
                    gr.Markdown("## Conversations")

                    self.conversation_id = gr.State(value="")
                    with gr.Row(elem_classes=["conv-actions-row"]):
                        self.conversation_dropdown = gr.Dropdown(
                            choices=[],
                            container=False,
                            filterable=True,
                            interactive=True,
                            show_label=False,
                            elem_classes=["unset-overflow"],
                            elem_id="conversation-dropdown",
                            scale=10,
                        )
                        self.btn_delete = gr.Button(
                            value="",
                            icon=f"{ASSETS_DIR}/delete.svg",
                            min_width=36,
                            scale=0,
                            size="sm",
                            elem_classes=[
                                "no-background",
                                "body-text-color",
                                "conv-icon-btn",
                            ],
                        )
                        self.btn_new = gr.Button(
                            value="",
                            icon=f"{ASSETS_DIR}/new.svg",
                            min_width=36,
                            scale=0,
                            size="sm",
                            elem_classes=[
                                "no-background",
                                "body-text-color",
                                "conv-icon-btn",
                            ],
                            elem_id="new-conv-button",
                        )

                    with gr.Accordion(label="File Collection", open=True):
                        self.search_mode = gr.Radio(
                            choices=[
                                ("Search All", "all"),
                                ("Search In File(s)", "files"),
                            ],
                            value="all",
                            show_label=False,
                            container=False,
                            elem_id="search-mode-radio",
                        )
                        self.selected_files = gr.Dropdown(
                            label="Files",
                            choices=[],
                            multiselect=True,
                            filterable=True,
                            container=False,
                            visible=False,
                            elem_id="selected-files-dropdown",
                        )

                    with gr.Accordion(
                        label="Thought Process",
                        open=True,
                        visible=True,
                        elem_id="thought-process-panel",
                    ) as self.thought_accordion:
                        self.thought_panel = gr.Markdown(
                            value="",
                            elem_id="thought-process-content",
                        )

                # ── center chat column ────────────────────────────────
                with gr.Column(
                    scale=6,
                    elem_id="chat-area",
                    elem_classes=["chat-area-col"],
                ):
                    self.chatbot = gr.Chatbot(
                        type="messages",
                        label="Chat",
                        placeholder=PLACEHOLDER,
                        show_label=False,
                        elem_id="main-chat-bot",
                        bubble_full_width=False,
                    )

                    with gr.Group(elem_id="chat-input-group"):
                        with gr.Row(elem_classes=["chat-input-row"]):
                            self.text_input = gr.Textbox(
                                placeholder="How can I help you today?",
                                show_label=False,
                                container=False,
                                elem_id="chat-input",
                                lines=1,
                                max_lines=6,
                                scale=1,
                            )
                            self.btn_send = gr.Button(
                                value="",
                                icon=f"{ASSETS_DIR}/send.svg",
                                variant="primary",
                                scale=0,
                                min_width=48,
                                elem_id="chat-send-btn",
                            )

                # ── right info panel ──────────────────────────────────
                with gr.Column(
                    scale=4,
                    elem_id="chat-info-panel",
                ) as self.info_column:
                    with gr.Accordion(
                        label="Information panel",
                        open=True,
                        elem_id="info-expand",
                    ):
                        self.info_panel = gr.HTML(
                            value=(
                                "<p class='info-empty'>Sources will appear here.</p>"
                            ),
                            elem_id="html-info-panel",
                        )

        return {
            "conversation_id": self.conversation_id,
            "conversation_dropdown": self.conversation_dropdown,
            "btn_new": self.btn_new,
            "btn_delete": self.btn_delete,
            "search_mode": self.search_mode,
            "selected_files": self.selected_files,
            "chatbot": self.chatbot,
            "text_input": self.text_input,
            "info_panel": self.info_panel,
        }

    # ── event wiring ─────────────────────────────────────────────────────

    def register_events(self, demo: gr.Blocks) -> None:
        demo.load(
            self.on_load,
            outputs=[
                self.conversation_dropdown,
                self.conversation_id,
                self.selected_files,
            ],
        )

        clear_outputs = [
            self.conversation_dropdown,
            self.conversation_id,
            self.chatbot,
            self.info_panel,
            self.thought_panel,
            self.thought_accordion,
        ]
        self.btn_new.click(self.new_conversation, outputs=clear_outputs)
        self.btn_delete.click(
            self.delete_conversation,
            inputs=[self.conversation_id],
            outputs=clear_outputs,
        )

        self.search_mode.change(
            self.on_search_mode_change,
            inputs=[self.search_mode, self.conversation_id],
            outputs=[self.selected_files],
        )
        self.selected_files.change(
            self.on_selected_files_change,
            inputs=[self.selected_files, self.conversation_id],
        )
        self.conversation_dropdown.change(
            self.switch_conversation,
            inputs=[self.conversation_dropdown],
            outputs=[
                self.conversation_id,
                self.chatbot,
                self.search_mode,
                self.selected_files,
                self.info_panel,
            ],
        )

        submit_inputs = [
            self.text_input,
            self.chatbot,
            self.conversation_id,
            self.search_mode,
        ]
        submit_outputs = [
            self.text_input,
            self.chatbot,
            self.info_panel,
            self.conversation_dropdown,
            self.thought_panel,
            self.thought_accordion,
        ]
        self.text_input.submit(
            self.submit_message,
            inputs=submit_inputs,
            outputs=submit_outputs,
        )
        self.btn_send.click(
            self.submit_message,
            inputs=submit_inputs,
            outputs=submit_outputs,
        )

    # ── handlers ─────────────────────────────────────────────────────────

    def on_load(self) -> tuple[Any, ...]:
        conv = self._ensure_default()
        return (
            gr.Dropdown(choices=self._conv_choices(), value=conv.id),
            conv.id,
            self._file_dropdown_update(value=[]),
        )

    def on_search_mode_change(self, mode: str, conv_id: str) -> Any:
        conv = self.conversations.get(conv_id) or self._ensure_default()
        conv.search_all = mode == "all"
        if conv.search_all:
            conv.selected_file_ids = []
        return self._file_dropdown_update(
            value=conv.selected_file_ids,
            visible=mode == "files",
        )

    def on_selected_files_change(self, value: Any, conv_id: str) -> None:
        conv = self.conversations.get(conv_id) or self._ensure_default()
        conv.selected_file_ids = self._sanitize_file_selection(value)

    def new_conversation(self) -> tuple[Any, ...]:
        conv = Conversation(name=f"Chat {len(self.conversations) + 1}")
        self.conversations[conv.id] = conv
        self._active_id = conv.id
        return (
            gr.Dropdown(choices=self._conv_choices(), value=conv.id),
            conv.id,
            [],
            "<p class='info-empty'>Sources will appear here.</p>",
            "",
            gr.update(visible=False),
        )

    def delete_conversation(self, conv_id: str) -> tuple[Any, ...]:
        if conv_id in self.conversations:
            del self.conversations[conv_id]
        if not self.conversations:
            return self.new_conversation()
        next_id = next(iter(self.conversations))
        self._active_id = next_id
        conv = self.conversations[next_id]
        return (
            gr.Dropdown(choices=self._conv_choices(), value=next_id),
            next_id,
            conv.history,
            "<p class='info-empty'>Sources will appear here.</p>",
            "",
            gr.update(visible=False),
        )

    def switch_conversation(self, conv_id: str) -> tuple[Any, ...]:
        if conv_id not in self.conversations:
            conv = self._ensure_default()
            conv_id = conv.id
        else:
            self._active_id = conv_id
        conv = self.conversations[conv_id]
        mode = "all" if conv.search_all else "files"
        valid = [n for n in conv.selected_file_ids if n in self._file_choices()]
        return (
            conv_id,
            conv.history,
            mode,
            self._file_dropdown_update(value=valid, visible=not conv.search_all),
            "<p class='info-empty'>Sources will appear here.</p>",
        )

    async def submit_message(
        self,
        message: str,
        history: list[dict[str, str]],
        conv_id: str,
        search_mode: str,
    ) -> Any:
        no_op = (
            "",
            history,
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
        )
        if not message.strip():
            yield no_op
            return

        conv = self.conversations.get(conv_id) or self._ensure_default()
        conv.search_all = search_mode == "all"
        file_ids = self._resolve_file_ids(search_mode, conv.selected_file_ids)

        _THINKING = "_Thinking..._"
        history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": _THINKING},
        ]
        yield (
            "",
            history,
            gr.update(),
            gr.update(),
            "",
            gr.update(visible=True),
        )

        thought_str = ""
        response_str = ""
        widget_code = ""
        widget_title: str | None = None

        async for kind, delta in self.chat_service.stream_answer(
            message,
            file_ids,
            history,
        ):
            if kind == "thought":
                thought_str += delta
            elif kind == "widget":
                widget_code = delta
            elif kind == "widget_title":
                widget_title = delta
            else:
                response_str += delta

            history[-1]["content"] = response_str or _THINKING
            yield (
                "",
                history,
                gr.update(),
                gr.update(),
                thought_str,
                gr.update(visible=bool(thought_str)),
            )
            await asyncio.sleep(0.02)

        conv.history = history
        if len(conv.history) == 2 and conv.name == "New conversation":
            conv.name = message[:40] or "New conversation"

        chunk_ids = parse_cited_chunk_ids(response_str)
        cited_sources = await self.chat_service.fetch_chunks_by_ids(chunk_ids)
        citation_map = build_citation_map(cited_sources)
        enriched = enrich_citations(response_str, citation_map)
        history[-1]["content"] = enriched
        conv.history = history
        info_html = _render_info_with_widget(
            cited_sources,
            widget_code=widget_code,
            widget_title=widget_title,
        )
        yield (
            "",
            history,
            info_html,
            gr.Dropdown(choices=self._conv_choices(), value=conv.id),
            thought_str,
            gr.update(visible=bool(thought_str)),
        )

    def refresh_file_choices(self) -> Any:
        return self._file_dropdown_update(value=[])
