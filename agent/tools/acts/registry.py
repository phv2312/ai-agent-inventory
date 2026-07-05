from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Any, Self

import structlog

from agent.models.streams import CustomFunctionCall
from agent.tools.acts.impl.inline_citations import InlineCitationsToolCall
from agent.tools.acts.impl.search import SearchToolCall
from agent.tools.acts.impl.think import ThinkToolCall
from agent.tools.acts.impl.visualize import VisualizeReadmeToolCall
from agent.tools.acts.models import BaseToolCall
from agent.tools.schemas.registry import (
    InlineCitationsParameters,
    SearchParameters,
    ThinkParameters,
    ToolNames,
    VisualizeReadmeParameters,
)

if TYPE_CHECKING:
    from agent.tools.resolver import ToolResolver

logger = structlog.get_logger(__name__)


@dataclass
class ToolActsRegistry:
    milvus: Any = field(default=None)
    embedding_model: Any = field(default=None)
    file_ids: list[str] | None = field(default=None)
    top_k: int = field(default=10)

    @cached_property
    def _resolver(self) -> "ToolResolver":
        from agent.tools.resolver import ToolResolver

        return ToolResolver(
            milvus=self.milvus,
            embedding_model=self.embedding_model,
            file_ids=self.file_ids,
            top_k=self.top_k,
        )

    def get(self, name: str) -> Any:
        return self._resolver.get(name)


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
