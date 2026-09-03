from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class InterruptionDecision(StrEnum):
    APPROVE = "approve"
    REVISE = "revise"
    CANCEL = "cancel"


class InterruptionDecisionRequest(BaseModel):
    version: int = Field(ge=1)
    interruption_ids: list[str] = Field(min_length=1)
    decision: InterruptionDecision
    feedback: str | None = None

    @model_validator(mode="after")
    def validate_feedback(self) -> "InterruptionDecisionRequest":
        normalized_feedback = (self.feedback or "").strip()
        if self.decision == InterruptionDecision.REVISE and not normalized_feedback:
            raise ValueError("feedback is required when decision is revise")
        if self.decision != InterruptionDecision.REVISE and normalized_feedback:
            raise ValueError("feedback is only accepted when decision is revise")
        self.feedback = normalized_feedback or None
        return self


class LinkPreviewRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=20)


class LinkPreviewItemResponse(BaseModel):
    url: str
    title: str | None = None
    description: str | None = None
    image: str | None = None
    favicon: str | None = None
    site_name: str | None = None
    published_at: str | None = None


class LinkPreviewResponse(BaseModel):
    items: list[LinkPreviewItemResponse]


class ChatForm(BaseModel):
    conversation_id: str
    message: str = Field(min_length=1)
    collection_ids: list[str] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)
    collection_name: str | None = None
    num_history_interactions: int = Field(default=5, ge=0)
    top_k: int = Field(default=10, ge=1)
    system_prompt: str | None = None
    web_search_enabled: bool = False
    global_query: bool = False
