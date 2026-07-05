from dataclasses import dataclass

from agent.chats.interface import IChatModel
from agent.embeddings.interface import IEmbeddingModel
from agent.models.streams import ToolDefinition
from agent.orchestrators.react import ReActAgent
from agent.prompts.core import PromptsFactory
from agent.storages.vectordb.milvus import Milvus
from agent.tools.resolver import ToolResolver
from agent.tools.schemas.registry import ToolNames, ToolSchemaRegistry


@dataclass
class AgentPairFactory:
    streamer: IChatModel
    model: str
    temperature: float
    max_turns: int = 20
    visualization_max_turns: int = 8

    def build_visualization_agent(self) -> ReActAgent:
        return ReActAgent(
            streamer=self.streamer,
            resolver=ToolResolver(),
            model=self.model,
            tools=ToolSchemaRegistry.visualization_tools(),
            temperature=self.temperature,
            instructions=PromptsFactory.AGENTIC.get("visualization").render(),
            max_turns=self.visualization_max_turns,
        )

    def build_agentic_resolver(
        self,
        *,
        milvus: Milvus,
        embedding_model: IEmbeddingModel,
        file_ids: list[str],
        top_k: int,
        visualization_agent: ReActAgent,
    ) -> ToolResolver:
        return ToolResolver(
            milvus=milvus,
            embedding_model=embedding_model,
            file_ids=file_ids,
            top_k=top_k,
            mp_name_agent={
                ToolNames.VISUALIZATION_AGENT_TOOL: visualization_agent,
            },
        )

    def build_agentic_agent(
        self,
        *,
        resolver: ToolResolver,
        tools: list[ToolDefinition],
        instructions: str,
    ) -> ReActAgent:
        return ReActAgent(
            streamer=self.streamer,
            resolver=resolver,
            model=self.model,
            tools=tools,
            temperature=self.temperature,
            instructions=instructions,
            max_turns=self.max_turns,
        )
