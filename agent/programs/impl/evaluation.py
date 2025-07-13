from typing import Literal
from pydantic import BaseModel, Field
from agent.programs.base import BaseProgram


class EvaluationResponse(BaseModel):
    score: Literal["high", "medium", "low"] = Field(
        default="low",
        description="Score adherence using one of three categories: high, medium, low",
    )
    reasoning: str = Field(
        default="", description="Short & clear reasoning for the score"
    )
    rule: str = Field(
        default="",
        description="Identify the most relevant rule name",
    )


class EvaluationProgram(BaseProgram[EvaluationResponse]):
    ModelOutCls = EvaluationResponse
