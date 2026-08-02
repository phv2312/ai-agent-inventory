---
name: agents-openai-templates
description: A small collection of OpenAI Agents SDK patterns for Azure OpenAI—tool calls, web search, skills, guardrails, approvals, handoffs, and shell execution.
---

# OpenAI Agents SDK Templates

Use these focused, runnable examples to implement common OpenAI Agents SDK
patterns. Start with `src/templates.py`: each `run_*` coroutine demonstrates a
pattern and streams its events to the terminal.

## Setup

The examples load Azure OpenAI configuration from environment variables via
`AzureOpenAISettings` in `model.py`.

```sh
export AZURE_OPENAI_ENDPOINT="https://<resource>.openai.azure.com"
export AZURE_OPENAI_API_KEY="..."
export AZURE_OPENAI_DEPLOYMENT="..."
# Optional; defaults to 2025-03-01-preview
export AZURE_OPENAI_API_VERSION="2025-03-01-preview"
```

Install the dependencies required by the containing project. Then select a
pattern below, run it with Python, or import its coroutine from
`src/templates.py`.

## Patterns

### Function-tool agent

**Use when:** the agent needs to call a deterministic application function.

`run_toolcall_agent()` defines a typed `calculate` function with
`@function_tool`, supplies it to an `Agent`, and streams the resulting tool
call and answer.

Guidance:

- Use clear parameter annotations and docstrings; they become tool guidance for
  the model.
- Keep tools small, deterministic, and easy to validate.
- Put authorization and sensitive side effects behind explicit checks.

### Web-search agent

**Use when:** the answer needs current public-web information.

`run_websearch_agent()` attaches `WebSearchTool` and instructs the agent to use
it as its knowledge source.

Guidance:

- State when the agent must search rather than rely on model knowledge.
- Select `search_context_size` according to the task’s depth and latency needs.
- Ask the agent to cite or distinguish sourced facts when that matters to users.

### Local skill agent

**Use when:** the agent should follow reusable, file-based operating guidance.

`run_agent_skills()` exposes the `skills/lavish` directory through a
`ShellToolLocalSkill`, allowing the agent to use the Lavish artifact workflow.

Guidance:

- Each skill should live in its own directory and include a `SKILL.md`.
- Give the skill a precise name, description, and absolute `path`.
- Keep skill instructions procedural: when to use it, steps, constraints, and
  any commands the agent needs.
- Update `SKILL_DIR` when the referenced skill moves; the example uses a fixed
  local path.

### Tool guardrails

**Use when:** tool inputs or outputs need policy checks before they are used.

`run_agent_tool_guardrails()` demonstrates both `@tool_input_guardrail` and
`@tool_output_guardrail` around a tool.

Guidance:

- Validate structured arguments before tool execution.
- Reject or redact sensitive output before it reaches the model or user.
- Treat the included `"sk-"` checks as a teaching example, not production-grade
  secret detection.

### Human approval

**Use when:** a tool action needs a person’s confirmation before execution.

`run_agent_human_approval()` marks `get_temperature` with
`needs_approval=True`, inspects interruptions, prompts in the terminal, then
approves or rejects each pending call before resuming the run.

Guidance:

- Require approval for actions with cost, external impact, or access to private
  information.
- Present the tool name and arguments clearly before asking for confirmation.
- Preserve the run state and resume it after each decision.

### Agent handoff

**Use when:** a triage agent should route a request to a specialist agent.

`run_agent_handoff()` creates language-specific agents and a triage agent with
their handoffs. It keeps the conversation input list and current agent between
turns.

Guidance:

- Make handoff descriptions unambiguous so the triage agent can route reliably.
- Give each specialist a narrowly scoped responsibility.
- Carry forward `events.to_input_list()` to preserve conversation history.

### Shell execution with approval

**Use when:** an agent needs to run local commands under a controlled executor.

`shell.py` provides `ShellExecutor` and a CLI example that requests approval
for shell commands before running them.

Guidance:

- Treat every shell command as potentially sensitive; default to approval.
- Set a timeout for commands that may block.
- Capture stdout, stderr, and exit status so the agent can explain failures.
- `SHELL_AUTO_APPROVE=1` is useful only for trusted, non-interactive local
  development.

## Supporting files

| File | Purpose |
| --- | --- |
| `src/templates.py` | Runnable pattern examples. |
| `src/model.py` | Azure OpenAI settings and shared model container. |
| `src/shell.py` | Shell executor and approval-aware shell-agent CLI. |

## Choosing a pattern

- Need a model to invoke application logic: use a function tool.
- Need fresh online facts: use web search.
- Need reusable operating instructions: use a local skill.
- Need to constrain tool data: add guardrails.
- Need a person to authorize an action: use human approval.
- Need specialized routing: use handoffs.
- Need local system commands: use the approval-aware shell executor.
