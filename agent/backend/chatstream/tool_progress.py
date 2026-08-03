import json
from typing import Any

from agents.items import ToolCallItem
from openai.types.responses import ResponseFunctionWebSearch
from openai.types.responses.response_function_tool_call import ResponseFunctionToolCall
from openai.types.responses.response_function_web_search import ActionSearch

from agent.backend.chatstream.constants import AgentToolNames, ToolProgressMessages


class ToolProgressFormatter:
    @staticmethod
    def format(item: ToolCallItem) -> str:
        # Convert SDK tool calls into the existing reasoning-timeline language.
        raw_item = item.raw_item
        if isinstance(raw_item, ResponseFunctionToolCall):
            return ToolProgressFormatter._format_function_call(raw_item)
        if isinstance(raw_item, ResponseFunctionWebSearch):
            return ToolProgressFormatter._format_web_search(raw_item)
        return ToolProgressMessages.FALLBACK.format(name=raw_item.type)

    @staticmethod
    def _format_function_call(item: ResponseFunctionToolCall) -> str:
        # Parse tool arguments only after the SDK reports a complete tool call.
        try:
            mp_str_any = json.loads(item.arguments)
        except json.JSONDecodeError:
            return ToolProgressMessages.FALLBACK.format(name=item.name)
        if not isinstance(mp_str_any, dict):
            return ToolProgressMessages.FALLBACK.format(name=item.name)

        match item.name:
            case AgentToolNames.INTERNAL_SEARCH:
                return ToolProgressMessages.INTERNAL_SEARCH.format(
                    query=ToolProgressFormatter._value(mp_str_any, "query"),
                )
            case AgentToolNames.THINK:
                return ToolProgressMessages.THINK.format(
                    reflection=ToolProgressFormatter._value(
                        mp_str_any,
                        "reflection",
                    ),
                )
            case AgentToolNames.VISUALIZE_README:
                return ToolProgressMessages.VISUALIZE.format(
                    modules=ToolProgressFormatter._value(mp_str_any, "modules"),
                )
            case _:
                return ToolProgressMessages.FALLBACK.format(name=item.name)

    @staticmethod
    def _format_web_search(item: ResponseFunctionWebSearch) -> str:
        # The search query is present for the built-in search action.
        if isinstance(item.action, ActionSearch):
            return ToolProgressMessages.WEB_SEARCH.format(
                query=item.action.query or "the web",
            )
        return ToolProgressMessages.WEB_SEARCH.format(query="the web")

    @staticmethod
    def _value(mp_str_any: dict[str, Any], key: str) -> str:
        value = mp_str_any.get(key)
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return str(value or "")
