import base64
from collections.abc import Sequence
from enum import StrEnum, auto
from pathlib import Path
from typing import Annotated, Literal, Self
from uuid import uuid4

from pydantic import BaseModel, BeforeValidator, Discriminator, Field

from agent.typedefs import ListModel


def encode_image_base64(imagepath: Path) -> str:
    with open(imagepath, "rb") as file:
        base64_image = base64.b64encode(file.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{base64_image}"


class MessageRole(StrEnum):
    system = auto()
    user = auto()
    assistant = auto()


class ContentType(StrEnum):
    image = "image_url"
    text = "text"


class BaseContent(BaseModel):
    type: ContentType


class ImageURL(BaseModel):
    url: Annotated[str, BeforeValidator(lambda path: encode_image_base64(path))]
    detail: Literal["low", "medium", "high"] = "low"


class ImageContent(BaseContent):
    type: Literal[ContentType.image] = ContentType.image
    image_url: ImageURL

    @classmethod
    def from_path(
        cls, path: Path, detail: Literal["low", "medium", "high"] = "low"
    ) -> "ImageContent":
        return cls(image_url=ImageURL(url=str(path), detail=detail))


class TextContent(BaseContent):
    type: Literal[ContentType.text] = ContentType.text
    text: str


MessageContent = Annotated[ImageContent | TextContent, Discriminator("type")]


class BaseMessage(BaseModel):
    role: MessageRole
    content: str | Annotated[list[MessageContent], Field(min_length=1)]
    id: str = Field(default_factory=lambda: str(uuid4()))


class UserMessage(BaseMessage):
    role: Literal[MessageRole.user] = MessageRole.user

    @classmethod
    def from_content(
        cls,
        content: str,
    ) -> Self:
        return cls(content=content, role=MessageRole.user)


class AssistantMessage(BaseMessage):
    role: Literal[MessageRole.assistant] = MessageRole.assistant

    @classmethod
    def from_content(
        cls,
        content: str,
    ) -> Self:
        return cls(content=content, role=MessageRole.assistant)


class SystemMessage(BaseMessage):
    role: Literal[MessageRole.system] = MessageRole.system


class ToolResponseMessage(BaseModel):
    role: Literal["tool"] = "tool"
    tool_call_id: str
    content: str


Message = Annotated[
    UserMessage | AssistantMessage | SystemMessage | ToolResponseMessage,
    Field(
        discriminator="role",
    ),
]


class Messages(ListModel[Message]):
    @classmethod
    def from_conversation(
        cls,
        message: UserMessage | None = None,
        system_message: SystemMessage | None = None,
        history: Sequence[AssistantMessage | UserMessage] | None = None,
    ) -> "Messages":
        if message is None and system_message is None:
            raise ValueError("Either message or system_message must be provided.")

        messages: list[Message] = [
            *(history or []),
        ]

        if message:
            messages = [message, *messages]

        if system_message:
            messages = [
                system_message,
                *messages,
            ]

        return cls(root=messages)

    def as_list(self) -> list[Message]:
        return self.root
