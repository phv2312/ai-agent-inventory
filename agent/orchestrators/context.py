from dataclasses import dataclass, field

from agent.models.streams import ChatRequest, CustomFunctionCall


@dataclass
class AgentTurnState:
    assistant_text: str = ""
    mp_id_tool_name: dict[str, str] = field(default_factory=dict)
    function_calls: list[CustomFunctionCall] = field(default_factory=list)


@dataclass
class AgentContext:
    request: ChatRequest
    turn: AgentTurnState = field(default_factory=AgentTurnState)

    def new_turn(self) -> AgentTurnState:
        self.turn = AgentTurnState()
        return self.turn
