from abc import ABC, abstractmethod
import json
import aiofiles
import asyncio
from enum import StrEnum, auto
import logging
from pathlib import Path
from typing import Final, Literal, Protocol
from jinja2 import Template

from agent.container import Container
from agent.models.messages import UserMessage


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


type ParserReturnT = dict[Literal["assistant", "user", "pairs"], list[str]]


class ConversationType(StrEnum):
    chat = auto()
    call = auto()


class IParser(Protocol):
    async def parse(self, filepath: Path) -> ParserReturnT: ...


class BaseParser(ABC):
    @abstractmethod
    async def parse(self, filepath: Path) -> ParserReturnT: ...


class CallParser(BaseParser):
    ASSISTANT: Final[str] = "Agent"
    USER: Final[str] = "Human"
    SEPERATOR: Final[str] = ": "

    async def parse(self, filepath: Path) -> ParserReturnT:
        async with aiofiles.open(filepath, "r", encoding="utf-8") as file:
            contents = await file.readlines()

        mp_messages: dict[Literal["assistant", "user"], list[str]] = {
            "assistant": [],
            "user": [],
            "pairs": [],
        }

        last_key: Literal["", "assistant", "user"] = ""
        first_key: Literal["assistant", "user"] = "assistant"
        for content in contents:
            splited_contents = content.split(self.SEPERATOR, maxsplit=1)

            info = ""
            splited_content = content
            if len(splited_contents) == 2:
                info, splited_content = splited_contents[:2]

            if info.endswith(self.ASSISTANT):
                key = "assistant"
            elif info.endswith(self.USER):
                key = "user"
            else:
                logger.warning("Can not determine type of message: %s", content)
                continue

            if last_key == key and len(mp_messages[key]) > 0:
                mp_messages[key][-1] += f" {splited_content.strip()}"
            else:
                if last_key == "":
                    first_key = key
                mp_messages[key].append(splited_content.strip())
            last_key = key

        num_ai_messages = len(mp_messages["assistant"])
        user_messages = [*mp_messages["user"], ""]
        if first_key == "assistant":
            user_messages = ["", *mp_messages["user"]]

        mp_messages["pairs"] = [
            (mp_messages["assistant"][i], user_messages[i])
            for i in range(num_ai_messages)
        ]

        return mp_messages


class ChatParser(BaseParser):
    ASSISTANT: Final[str] = "Assistant:"
    USER: Final[str] = "User:"
    SEPERATOR: Final[str] = ":"

    async def parse(self, filepath: Path) -> ParserReturnT:
        async with aiofiles.open(filepath, "r", encoding="utf-8") as file:
            contents = await file.readlines()

        mp_messages: ParserReturnT = {
            "assistant": [],
            "user": [],
            "pairs": [],
        }

        last_key: Literal["assistant", "user", ""] = ""
        first_key: Literal["assistant", "user"] = "assistant"
        for content in contents:
            if content.startswith(self.ASSISTANT):
                key = "assistant"
            elif content.startswith(self.USER):
                key = "user"
            else:
                logger.warning("Can not determine type of message: %s", content)
                continue

            splits = content.split(sep=self.SEPERATOR, maxsplit=1)
            if len(splits) == 1:
                logger.warning(
                    "Failed to split content: %s with seperator: %s",
                    content,
                    self.SEPERATOR,
                )

            splited_content = splits[1] if len(splits) >= 1 else content

            if last_key == key and len(mp_messages[key]) > 0:
                mp_messages[key][-1] += f" {splited_content.strip()}"
            else:
                if last_key == "":
                    first_key = key
                mp_messages[key].append(splited_content.strip())
            last_key = key

        num_ai_messages = len(mp_messages["assistant"])
        user_messages = [*mp_messages["user"], ""]
        if first_key == "assistant":
            user_messages = ["", *mp_messages["user"]]

        mp_messages["pairs"] = [
            (mp_messages["assistant"][i], user_messages[i])
            for i in range(num_ai_messages)
        ]

        return mp_messages


async def main() -> None:
    placeholder = {
        "customer_pronoun": "anh",
        "full_name": "PHẠM HOÀI VĂN",
        "customer_name": "PHẠM HOÀI VĂN",
        "customer_first_name": "VĂN",
    }
    prompt_path = "agent/prompts/conversation_eval/groundedness.md"

    chat_history_path = Path("datas/conversation-eval/conversation1.txt")
    # call_history_path = Path("datas/conversation-eval/conversation2.txt")

    chat_parser = ChatParser()
    # call_parser = CallParser()

    mp_messages = await chat_parser.parse(chat_history_path)
    # logger.info(await call_parser.parse(call_history_path))

    print(mp_messages)

    exit()

    # Init services once
    container = Container()
    embedding_model = container.embeddings.get("azure_openai")
    milvus = container.vectordbs.get("milvus")
    evaluation_program = container.programs.get("evaluation")

    async with aiofiles.open(prompt_path, "r") as file:
        template = Template(await file.read())

    for ai_content in mp_messages["assistant"]:
        embeddings = await embedding_model.aembedding([ai_content])

        retrieved_chunks = await milvus.search(query=embeddings[0], top_k=3)

        logger.info("Similar chunks of query: %s", ai_content)
        constants: list[tuple[str, str]] = []
        for idx, scored_chunk in enumerate(retrieved_chunks.root, start=1):
            logger.info(
                "%d. Content: %s, score: %.3f",
                idx,
                scored_chunk.text,
                scored_chunk.score,
            )

            constants.append(
                (
                    scored_chunk.chunk.metadata.rendered_page_path,
                    scored_chunk.chunk.text,
                )
            )

        prompt_content = template.render(
            bot_message=ai_content,
            placeholders=json.dumps(placeholder, indent=2),
            style_constants=constants,
        )

        evaluation = await evaluation_program.aprocess(
            message=UserMessage(content=prompt_content)
        )

        print(evaluation)


if __name__ == "__main__":
    asyncio.run(main())
