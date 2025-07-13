from pydantic import BaseModel, Field
from agent.programs.base import BaseProgram


class FollowupComparisonResponse(BaseModel):
    confidence: float = Field(
        ...,
        description=(
            "<câu 1> trả lời đúng ý <câu 2> được bao nhiêu %. Dựa vào tiêu chí : ý nghĩa, "
            "con số (tiền, khoản tiền) , thời gian (mốc thời gian, khoản thời gian, dài /ngắn, "
            "lâu/ mau/ nhanh chậm, tên , tuổi, vv)"
        ),
    )
    is_concern_solved: bool = Field(
        ...,
        description=(
            "Trả về True : nếu nội dung <câu 1> CÓ trả lời được ý của <câu 2>, "
            "hoặc <confidence> lớn hơn hoặc bằng 70%. Trả về False nếu nội dung <câu 1> "
            "KHÔNG liên quan gì <câu 2>, hoặc <câu 1> chỉ trả lời được nhỏ hơn hoặc bằng 70% ý của <câu 2>"
        ),
    )
    good_points: str = Field(
        ..., description=("liệt kê các ý mà <câu 1> ĐÃ trả lời được ở <câu 2>")
    )
    notgood_points: str = Field(
        ..., description=("Liệt kê các ý trong <câu 2> mà <câu 1> chưa trả lời được")
    )


class FollowupComparisonProgram(BaseProgram[FollowupComparisonResponse]):
    ModelOutCls = FollowupComparisonResponse
