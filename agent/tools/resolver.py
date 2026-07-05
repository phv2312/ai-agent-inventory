from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from agent.embeddings.interface import IEmbeddingModel
from agent.storages.vectordb.milvus import Milvus
from agent.tools.acts.models import IToolAct
from agent.tools.schemas.registry import ToolNames

if TYPE_CHECKING:
    from agent.orchestrators.agent_tool import AgentAsToolAct
    from agent.orchestrators.react import ReActAgent


@dataclass
class ToolResolver:
    milvus: Milvus | None = field(default=None)
    embedding_model: IEmbeddingModel | None = field(default=None)
    file_ids: list[str] | None = field(default=None)
    top_k: int = field(default=10)
    mp_name_agent: dict[str, "ReActAgent"] = field(default_factory=dict)

    def get(self, name: str) -> IToolAct[Any] | "AgentAsToolAct" | None:
        if name in self.mp_name_agent:
            from agent.orchestrators.agent_tool import AgentAsToolAct

            return AgentAsToolAct(
                agent=self.mp_name_agent[name],
                agent_name=name,
            )
        from agent.prompts.core import PromptsFactory
        from agent.tools.acts.impl.inline_citations import InlineCitationsAct
        from agent.tools.acts.impl.search import SearchAct
        from agent.tools.acts.impl.think import ThinkAct
        from agent.tools.acts.impl.visualize import VisualizeReadmeAct

        match name:
            case ToolNames.THINK_TOOL:
                return ThinkAct()
            case ToolNames.SEARCH_TOOL:
                if self.milvus is None or self.embedding_model is None:
                    raise ValueError(
                        "Milvus and embedding_model are required for search",
                    )
                return SearchAct(
                    self.milvus,
                    self.embedding_model,
                    self.file_ids or [],
                    top_k=self.top_k,
                )
            case ToolNames.INLINE_CITATIONS_TOOL:
                if self.milvus is None:
                    raise ValueError(
                        "Milvus is required for inline citations",
                    )
                return InlineCitationsAct(self.milvus)
            case ToolNames.VISUALIZE_README_TOOL:
                return VisualizeReadmeAct(
                    readme_template=PromptsFactory.TOOLS.get(
                        "visualize_readme",
                    ),
                    vis_templates={
                        m: PromptsFactory.VISUALIZATION.get(m)
                        for m in (
                            "interactive",
                            "chart",
                            "diagram",
                            "mockup",
                            "art",
                        )
                    },
                )
            case _:
                return None
