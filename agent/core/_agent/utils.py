from collections.abc import Sequence

import structlog
from agents import (
    RunResultStreaming,
    AgentUpdatedStreamEvent,
    RawResponsesStreamEvent,
    RunItemStreamEvent,
    ToolCallItem,
    ToolCallOutputItem,
)


logger = structlog.get_logger(__name__)

DEFAULT_RESPONSE_DATA_TYPES: Sequence[str] = [
    "response.output_text.delta",
    "response.function_call_arguments.done",
    "response.output_item.done",
    "response.completed",
]

DEFAULT_RUN_ITEM_EVENT_NAMES: Sequence[str] = ["tool_called", "tool_output"]


def _handle_raw_response(
    event: RawResponsesStreamEvent,
    response_data_types: Sequence[str] | None = None,
) -> None:
    data = event.data

    if response_data_types is not None and data.type not in response_data_types:
        return

    if data.type == "response.output_text.delta":
        logger.info("response_text_delta", delta=data.delta)

    elif data.type == "response.function_call_arguments.delta":
        logger.info("tool_arguments_delta", delta=data.delta)

    elif data.type == "response.function_call_arguments.done":
        logger.info(
            "tool_arguments_completed", name=data.name, arguments=data.arguments
        )

    elif data.type == "response.output_item.done":
        response_item = data.item
        if response_item.type == "function_call":
            logger.info(
                "tool_call_emitted",
                name=response_item.name,
                arguments=response_item.arguments,
            )

    elif data.type == "response.completed":
        logger.info("response_completed")


def _handle_run_item(
    event: RunItemStreamEvent, run_item_event_names: Sequence[str] | None = None
) -> None:
    if run_item_event_names is not None and event.name not in run_item_event_names:
        return

    if event.name == "tool_called":
        tool_call_item = event.item
        if not isinstance(tool_call_item, ToolCallItem):
            logger.info("tool_called", item_type=type(tool_call_item).__name__)
            return

        # checking for prebuilt websearch call
        if isinstance(tool_call_item.raw_item, dict):
            pass
        elif tool_call_item.raw_item.type == "web_search_call":
            logger.info("web_search_started", call_id=tool_call_item.call_id)
            return

        logger.info(
            "tool_started",
            name=tool_call_item.tool_name,
            call_id=tool_call_item.call_id,
        )

    elif event.name == "tool_output":
        tool_output_item = event.item
        if not isinstance(tool_output_item, ToolCallOutputItem):
            logger.info(
                "tool_output_received", item_type=type(tool_output_item).__name__
            )
            return
        logger.info("tool_finished", output=tool_output_item.output)


class StreamUtils:
    @staticmethod
    async def print_event(
        events: RunResultStreaming,
        *,
        response_data_types: Sequence[str] | None = DEFAULT_RESPONSE_DATA_TYPES,
        run_item_event_names: Sequence[str] | None = DEFAULT_RUN_ITEM_EVENT_NAMES,
    ) -> None:
        async for event in events.stream_events():
            if isinstance(event, RawResponsesStreamEvent):
                _handle_raw_response(event, response_data_types=response_data_types)
            elif isinstance(event, RunItemStreamEvent):
                _handle_run_item(event, run_item_event_names=run_item_event_names)
            elif isinstance(event, AgentUpdatedStreamEvent):
                logger.info("agent_changed", name=event.new_agent.name)
