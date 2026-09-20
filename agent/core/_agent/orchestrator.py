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
from agent.core.tools import (
    build_search_tool,
    build_visualize_tool,
    think_tool,
)
from agent.core.tools.summary.tools import ArtifactRepository

from .models import AgentDeps, InterruptionDecision, RunInput


@dataclass
class AgentSettings:
    max_turns: int = 20


class AgentFactory:
    GLOBAL_HANDOFF_DESCRIPTION: Final[str] = (
        "Handle global queries when user explicitly requires in query, via /global pattern"
    )
    GLOBAL_INSTRUCTION: Final[str] = """
You are the global research specialist.

- First use the available research tools to gather the evidence needed to assess the request.
For a straightforward, bounded question, answer directly from that evidence.

- If the retrieved material shows that the answer would be long, multi-part, comparative, or otherwise
complex, create a complete answer outline and call `submit_agent_plan`. Do not describe the plan in plain text.

When comparing or synthesizing multiple source summaries, use `list_many` and
`read_many` to retrieve the relevant artifacts together. Cite the file ID and
artifact path for every factual claim.

"""

    @staticmethod
    def _global(
        model: OpenAIResponsesModel,
        file_ids: list[str],
        artifact_repo: ArtifactRepository,
    ) -> Agent[None]:
        from agent.core.tools.summary import build_summary_read_tools

        return Agent(
            name="global_agent",
            handoff_description=AgentFactory.GLOBAL_HANDOFF_DESCRIPTION,
            model=model,
            instructions=(
                f"{AgentFactory.GLOBAL_INSTRUCTION}\n"
                "Available source-summary file IDs: "
                f"{', '.join(file_ids) or 'None'}."
            ),
            tools=[
                *build_summary_read_tools(
                    artifact_repo,
                    file_ids,
                ),
            ],
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
            handoffs=handoffs or [],
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
            handoffs=[
                AgentFactory._global(
                    self.deps.model,
                    inp.file_ids,
                    self.deps.artifact_repo,
                ),
            ],
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

    async def resume(
        self,
        *,
        inp: RunInput,
        state_string: str,
        decision: InterruptionDecision,
        feedback: str = "",
    ) -> RunResultStreaming:
        agent, run_state = await self.load_run_state(inp, state_string)
        interruptions = run_state.get_interruptions()
        if not interruptions:
            raise ValueError("The saved run has no pending interruptions")

        if decision == "approve":
            for interruption in interruptions:
                run_state.approve(interruption)
        elif decision == "revise":
            rejection_message = self._revision_message(feedback)
            for interruption in interruptions:
                run_state.reject(
                    interruption,
                    rejection_message=rejection_message,
                )
        else:
            raise ValueError(f"Unsupported interruption decision: {decision}")

        return self.resume_state(agent, run_state)

    def resume_state(
        self,
        agent: Agent[None],
        run_state: RunState[None],
    ) -> RunResultStreaming:
        return Runner.run_streamed(
            agent,
            input=run_state,
            max_turns=self.settings.max_turns,
        )

    @staticmethod
    def _revision_message(feedback: str) -> str:
        return (
            "The human reviewer requested these plan changes:\n"
            f"{feedback}\n\n"
            "Revise the plan and submit the complete replacement plan for "
            "approval. Do not execute the plan or write the final answer."
        )
