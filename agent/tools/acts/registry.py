from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Self

import structlog

from agent.embeddings.interface import IEmbeddingModel
from agent.models.streams import CustomFunctionCall
from agent.storages.vectordb.milvus import Milvus
from agent.prompts.core import PromptsFactory
from agent.tools.acts.impl.inline_citations import (
    InlineCitationsAct,
    InlineCitationsToolCall,
)
from agent.tools.acts.impl.search import SearchAct, SearchToolCall
from agent.tools.acts.impl.think import ThinkAct, ThinkToolCall
from agent.tools.acts.impl.visualize import (
    VisualizeReadmeAct,
    VisualizeReadmeToolCall,
)
from agent.tools.acts.models import BaseToolCall, IToolAct
from agent.tools.schemas.registry import (
    InlineCitationsParameters,
    SearchParameters,
    ThinkParameters,
    ToolNames,
    VisualizeReadmeParameters,
)

logger = structlog.get_logger(__name__)


@dataclass
class ToolActsRegistry:
    milvus: Milvus | None = field(default=None)
    embedding_model: IEmbeddingModel | None = field(default=None)
    file_ids: list[str] | None = field(default=None)
    top_k: int = field(default=10)

    def get(self, name: str) -> IToolAct[Any] | None:
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


@dataclass
class ToolParser:
    name: str
    arguments: str
    id: str

    @classmethod
    def from_function_call(
        cls,
        tool_call: CustomFunctionCall,
    ) -> Self:
        return cls(
            name=tool_call.name,
            arguments=tool_call.arguments,
            id=tool_call.call_id,
        )

    @cached_property
    def parsed(self) -> BaseToolCall[Any] | None:
        match self.name:
            case ToolNames.SEARCH_TOOL:
                return SearchToolCall(
                    id=self.id,
                    params=SearchParameters.model_validate_json(
                        self.arguments,
                    ),
                )
            case ToolNames.INLINE_CITATIONS_TOOL:
                return InlineCitationsToolCall(
                    id=self.id,
                    params=InlineCitationsParameters.model_validate_json(
                        self.arguments,
                    ),
                )
            case ToolNames.THINK_TOOL:
                return ThinkToolCall(
                    id=self.id,
                    params=ThinkParameters.model_validate_json(
                        self.arguments,
                    ),
                )
            case ToolNames.VISUALIZE_README_TOOL:
                return VisualizeReadmeToolCall(
                    id=self.id,
                    params=VisualizeReadmeParameters.model_validate_json(
                        self.arguments,
                    ),
                )
            case _:
                logger.warning("Unknown tool name", name=self.name)
                return None
