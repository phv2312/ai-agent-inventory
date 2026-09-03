from dataclasses import dataclass
from typing import Final

from agents import (
    Agent,
    OpenAIResponsesModel,
    RunResultStreaming,
    RunState,
    Runner,
    Tool,
)
from jinja2 import Template

from agent.core.embeddings.interface import IEmbeddingModel
from agent.core.models.document import DocumentMetadata
from agent.core.models.messages import Message, Messages, UserMessage
from agent.core.prompts.core import PromptsFactory
from agent.core.storages.config import AnchorFields
from agent.core.storages.vectordb.milvus import Milvus
from agent.core.tools import build_search_tool, build_visualize_tool, think_tool

from .models import AgentDeps, RunInput


@dataclass
class AgentSettings:
    max_turns: int = 20


class AgentFactory:
    GLOBAL_HANDOFF_DESCRIPTION: Final[str] = (
        "Handles broad, multi-step, synthesis, comparison, and planning requests "
        "that benefit from a reviewable plan before evidence gathering."
    )
    GLOBAL_INSTRUCTION: Final[str] = """
## Review-gated workflow

You are the global research specialist. Before searching, reflecting,
visualizing, or answering, create a complete answer outline and call
`submit_agent_plan`. Do not describe the plan in plain text and do not use any
other tool before the plan is approved.

If the plan tool is rejected with revision feedback, treat that message as
requirements. Submit a complete replacement plan and wait for approval again.
Do not continue execution after revision feedback.

After approval, the tool result is the approved plan. Execute that plan with
the available research tools and produce the final evidence-grounded answer.
Do not mention approval tools, handoffs, or internal workflow details.
"""

    @staticmethod
    def _global(model: OpenAIResponsesModel) -> Agent[None]:
        from agent.core.tools import submit_agent_plan

        return Agent(
            name="global-agent",
            handoff_description=AgentFactory.GLOBAL_HANDOFF_DESCRIPTION,
            model=model,
            instructions=AgentFactory.GLOBAL_INSTRUCTION,
            tools=[submit_agent_plan],
        )

    @staticmethod
    async def orchestrator(
        vectordb: Milvus,
        embedding: IEmbeddingModel,
        model: OpenAIResponsesModel,
        inp: RunInput,
        instruction_template: Template | None = None,
        handoffs: list[Agent[None]] | None = None,
    ) -> Agent[None]:
        async def _resolve_docnames() -> list[str]:
            if not inp.file_ids:
                return []
            chunks = await vectordb.retrieve_by_filter(
                {AnchorFields.FILE_ID: inp.file_ids},
            )
            names: set[str] = set()
            for scored_chunk in chunks.iter():
                if isinstance(scored_chunk.chunk.metadata, DocumentMetadata):
                    names.add(scored_chunk.chunk.metadata.filename)
            return sorted(names)

        def _build_tools() -> list[Tool]:
            tools: list[Tool] = [build_visualize_tool()]

            if inp.file_ids:
                tools.extend(
                    (
                        build_search_tool(
                            vectordb,
                            embedding,
                            inp.file_ids,
                            inp.top_k,
                        ),
                        think_tool,
                    ),
                )
            if inp.web_search_enabled:
                from agents import WebSearchTool

                tools.append(WebSearchTool(search_context_size="high"))

            return tools

        template = instruction_template or PromptsFactory.AGENTIC.get("agent2")

        return Agent(
            name="orchestrator",
            model=model,
            instructions=template.render(doc_names=";".join(await _resolve_docnames())),
            tools=_build_tools(),
            handoffs=handoffs,
        )


class AgentOrchestrator:
    def __init__(
        self,
        deps: AgentDeps,
        settings: AgentSettings | None = None,
    ) -> None:
        self.deps = deps
        self.settings = settings or AgentSettings()

    async def build_agent(self, inp: RunInput) -> Agent[None]:
        return await AgentFactory.orchestrator(
            self.deps.vectordb,
            self.deps.embedding_model,
            self.deps.model,
            inp,
            handoffs=[AgentFactory._global(self.deps.model)],
        )

    async def stream(self, inp: RunInput) -> RunResultStreaming:
        agent = await self.build_agent(inp)
        messages: list[Message] = [*inp.history.root, UserMessage(content=inp.query)]
        return Runner.run_streamed(
            agent,
            input=Messages(root=messages).as_responses_input(),
            max_turns=self.settings.max_turns,
        )

    async def load_run_state(
        self,
        inp: RunInput,
        state_string: str,
    ) -> tuple[Agent[None], RunState[None]]:
        agent = await self.build_agent(inp)
        return agent, await RunState.from_string(agent, state_string)

    def resume(
        self,
        agent: Agent[None],
        run_state: RunState[None],
    ) -> RunResultStreaming:
        return Runner.run_streamed(
            agent,
            input=run_state,
            max_turns=self.settings.max_turns,
        )
