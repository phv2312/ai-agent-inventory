from pydantic import BaseModel, Field
from agent.programs.base import BaseProgram


class SemanticComparisonResponse(BaseModel):
    is_same_meaning: bool = Field(
        ...,
        description=(
            "Trả về True nếu 2 câu này có cùng một nội dung chính hoặc cùng mục đích truyền đạt, "
            "dù có khác về con số (số tiền, thời gian, tuổi tác). Trả về False nếu nội dung hoặc "
            "mục đích chính có khác biệt mục đích truyền đạt"
        ),
    )
    reason_first_sentence: str = Field(
        ..., description=("Giải thích lý do NGẮN GỌN cho câu 1")
    )
    reason_second_sentence: str = Field(
        ..., description=("Giải thích lý do NGẮN GỌN cho câu 2")
    )


class SemanticComparisonProgram(BaseProgram[SemanticComparisonResponse]):
    ModelOutCls = SemanticComparisonResponse
