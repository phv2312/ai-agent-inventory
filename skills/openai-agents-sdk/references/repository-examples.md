# Local OpenAI Agents SDK examples

Read this reference for working `openai-agents` examples in this repository.
It is not a replacement for the package documentation.

| Package capability | Local example | Notes |
|---|---|---|
| Agent creation and streamed runs | `agent/rag/chats/strategies/agentic/core.py` | Builds an `Agent` per request and calls `Runner.run_streamed`. |
| Application history | `agent/models/messages.py` and `agent/rag/chats/strategies/agentic/core.py` | Validates Pydantic messages, then converts them with `Messages.as_responses_input()`. |
| Function tools | `agent/rag/chats/strategies/agentic/tools.py` | `@function_tool` with `Annotated` Pydantic fields and async functions. |
| Built-in web search | `agent/rag/chats/strategies/agentic/tools.py` | Adds `WebSearchTool` only when `web_search_enabled` is true. |
| Structured outputs | `agent/programs/base.py` | Passes a Pydantic class as `output_type` and reads `final_output_as`. |
| Azure Responses model | `agent/deps/container.py` | Configures `OpenAIResponsesModel` and tracing. |
| Stream event adapter | `agent/services/chatstream/core.py` | Adapts raw response and completed run-item events to SSE. |
| User-visible tool progress | `agent/services/chatstream/tool_progress.py` | Maps tool calls to readable internal-search, thinking, visualization, and web-search status. |

## Project-specific constraints

- Tool lists are request scoped because document filters and capability flags are
  per conversation.
- The chat stream transformer owns text, snippets, and inline visual-widget
  blocks; the endpoint persists a response only after a successful stream.
- Internal retrieval returns document name, chunk ID, source, and text so the
  agent prompt can produce citations.
