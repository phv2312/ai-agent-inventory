---
name: openai-agents-sdk
description: Build, migrate, debug, and review Python applications with the OpenAI Agents SDK (`openai-agents`). Use when creating Agent or Runner flows, function tools, WebSearchTool, structured outputs, conversation state, streaming events, Azure OpenAI Responses models, or SDK tracing.
---

# OpenAI Agents SDK

Use this skill to implement the Python `openai-agents` package correctly. This
repository is the local reference implementation: use its examples when they
match the task, but do not treat its RAG-specific behavior as a package rule.

## Start with the package and local examples

1. Confirm the installed `openai-agents` version in `pyproject.toml`.
2. Read [local package examples](references/repository-examples.md) for the
   closest working implementation in this repository.
3. Check the installed SDK and official Agents SDK docs before relying on an
   unfamiliar event type or API surface; package APIs evolve independently of
   this repository.

## Use the core runtime

- Define an `Agent` with a name, instructions, model, optional `tools`, and
  optional `output_type` for a Pydantic structured result.
- Use `await Runner.run(...)` for a completed run, and
  `Runner.run_streamed(...)` plus `stream_events()` when output must be consumed
  incrementally.
- Treat one runner invocation as one application turn. Let the SDK handle its
  agent loop, tool calls, and handoffs; do not add a second ReAct loop around it.
- Choose one conversation strategy per chat: replayable local history,
  SDK-backed session, or Responses API continuation. Avoid combining them unless
  deliberately reconciling duplicate context.

## Define tools and outputs

- Decorate typed Python functions with `@function_tool`. Function names, type
  hints, descriptions, and return values are the model-facing contract.
- Return concise, model-readable data. Keep authorization, side effects,
  validation, and idempotency in application code.
- Use `WebSearchTool` for built-in internet retrieval only when the product has
  enabled it for that request.
- Use `output_type=MyPydanticModel` for structured results, then consume
  `result.final_output` or `result.final_output_as(MyPydanticModel)` as
  appropriate to the SDK version.

## Stream deliberately

- Process raw response text-delta events for visible text and completed run-item
  events for tool or handoff progress. Verify exact event classes against the
  installed package.
- Do not treat the final output as settled until the stream completes.
- Convert SDK events at the integration boundary (for example an SSE adapter),
  leaving API endpoints and UI components independent of SDK event classes.
- Map tool names to meaningful product progress rather than presenting every
  call as a generic tool-started message.

## Configure and verify

- Configure the model through the SDK model interface. This repository uses
  `OpenAIResponsesModel` for Azure OpenAI Responses; use the provider-specific
  model configuration required by the target application.
- Treat Agents SDK tracing as an explicit deployment choice. This repository
  disables it with `OPENAI_AGENTS_DISABLE_TRACING` and keeps Phoenix tracing
  separate.
- Test a normal run, every changed tool, structured output when used, and the
  full streamed event path when streaming is exposed.

## Repository-specific follow-through

- For changes in this repository, preserve its API, SSE, citation, and
  persisted-message contracts; consult `README.md` and
  `agent/api/docs/integration-guide.md`.
- Update [local package examples](references/repository-examples.md) whenever a
  deliberate code change makes its file map stale.
