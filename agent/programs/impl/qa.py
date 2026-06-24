from agent.programs.base import BaseProgram
from agent.models.qa import GeneratedQAs


class GeneratedQAProgram(BaseProgram[GeneratedQAs]):
    ModelOutCls = GeneratedQAs
