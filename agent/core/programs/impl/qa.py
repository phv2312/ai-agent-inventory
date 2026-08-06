from agent.core.programs.base import BaseProgram
from agent.core.models.qa import GeneratedQAs


class GeneratedQAProgram(BaseProgram[GeneratedQAs]):
    ModelOutCls = GeneratedQAs
