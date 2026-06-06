import asyncio
from functools import lru_cache
import operator
from typing import Annotated, Literal
from uuid import uuid4
from jinja2 import Template
from pydantic import BaseModel, Field
from langgraph.types import StreamWriter
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langgraph.types import Command, interrupt, Send
from langgraph.checkpoint.memory import MemorySaver

from agent.chats import IChatModel
from agent.container import Container
from agent.env import Env
from agent.models.messages import UserMessage
from agent.models.streams import ChatRequest, StreamEventType
from agent.programs.base import BaseProgram


FEEDBACK_TEMPLATE = Template(
    """
    Please review the generated outline and provide feedback.
    {{outline}}\n
    Press 'Y' to accept, or input feedbacks.
    """
)

OUTLINE_PLANNING = Template(
    """
    You are the story topic generator.

    <Feedback from user>
    {{feedbacks}}
    </Feedback from user>

    <Task>
    Randomly generate {{num_topics}} topics to form story later. Please follow the feedback from user if any.
    The topic content should be string, consise and clear.
    </Task>

    """
)

STORY_WRITER = Template(
    """
    You are the story writer.

    <Topic>
    {{topic}}
    </Topic>

    <Task>
    Write a story about the given topic, with requirements:

    - The story content should be funny, interesting and engaging.
    - IMPORTANT: the story content should be related to the topic.
    - The story content length should be up to 300 words as a maximum.
    - Output should be in the markdown format. With ### as the topic of the story.

    </Task>

    """
)

NUM_TOPICS = 1


class Outline(BaseModel):
    topics: list[str] = Field(default_factory=list, description="List of topics")

    @property
    def content(self) -> str:
        contents = []
        for idx, topic in enumerate(self.topics, start=1):
            content = f"- Topic [{idx}]: {topic}"
            contents.append(content)

        return "\n".join(contents)


class StoryInput(BaseModel):
    topic: str = Field(description="Topic of the story")


class StoryOutput(BaseModel):
    content: str = Field(description="Content of the story")


class OutlineProgram(BaseProgram[Outline]):
    ModelOutCls = Outline


class StoryProgram(BaseProgram[StoryOutput]):
    ModelOutCls = StoryOutput


@lru_cache(maxsize=1)
def get_outline_program() -> OutlineProgram:
    env = Env()
    return OutlineProgram(
        chat_model=Container().streams.get("azure_openai"),
        model_name=env.OPENAI_CHAT_DEPLOYMENT_NAME,
    )


@lru_cache(maxsize=1)
def get_stream_provider() -> IChatModel:
    return Container().streams.get("azure_openai")


class StateInput(BaseModel):
    feedbacks: Annotated[list[str], operator.add] = Field(
        default_factory=list, description="feedbacks from user about the outline"
    )
    allow_user_feedback: bool = Field(
        default=True, description="Allow user to provide feedback"
    )
    num_topics: int = Field(
        default=NUM_TOPICS, description="Number of topics to generate"
    )


class State(StateInput):
    outline: Outline = Field(
        default_factory=Outline, description="Outline of the story"
    )
    stories: Annotated[list[StoryOutput], operator.add] = Field(
        default_factory=list, description="List of stories"
    )
    markdown: str = Field(default="", description="Markdown content of the stories")


async def plan_outline_wo_feedback(
    node_input: StateInput,
) -> Command[Literal["plan-outline", "write-story"]]:
    outline_program = get_outline_program()
    outline = await outline_program.aprocess(
        message=UserMessage(
            content=OUTLINE_PLANNING.render(
                num_topics=node_input.num_topics,
                feedbacks="\n\n".join(node_input.feedbacks),
            ),
        )
    )

    return Command(
        goto=[
            Send(
                "write-story",
                StoryInput(
                    topic=topic,
                ),
            )
            for topic in outline.topics
        ]
    )


async def plan_outline(
    node_input: StateInput,
    # node_input: State,
) -> Command[Literal["plan-outline", "write-story"]]:
    def _send_topic(topics: list[str]) -> Command[Literal["write-story"]]:
        return Command(
            goto=[
                Send(
                    "write-story",
                    StoryInput(
                        topic=topic,
                    ),
                )
                for topic in topics
            ]
        )

    print("call outline planning with feedback:", node_input.allow_user_feedback)

    outline_program = get_outline_program()
    outline = await outline_program.aprocess(
        message=UserMessage(
            content=OUTLINE_PLANNING.render(
                num_topics=node_input.num_topics,
                feedbacks="\n\n".join(node_input.feedbacks),
            ),
        )
    )

    if node_input.allow_user_feedback:
        feedback = interrupt(FEEDBACK_TEMPLATE.render(outline=outline.content))
        match feedback.lower():
            case "y":
                return _send_topic(outline.topics)
            case _:
                return Command(
                    goto="plan-outline",
                    update=StateInput(
                        feedbacks=[feedback],
                    ),
                )
    else:
        return {
            "outline": outline,
        }


async def write_story(
    node_input: StoryInput,
    writer: StreamWriter,
) -> dict[Literal["stories"], list[StoryOutput]]:
    streamer = get_stream_provider()
    env = Env()

    full_content = ""
    request = ChatRequest(
        model=env.OPENAI_CHAT_DEPLOYMENT_NAME,
        messages=[
            UserMessage(
                content=STORY_WRITER.render(
                    topic=node_input.topic,
                ),
            ),
        ],
    )
    async for event in streamer.stream(request):
        if event.type != StreamEventType.TEXT_DELTA:
            continue
        full_content += event.content
        writer({"story-streaming": {"content": event.content}})

    return {"stories": [StoryOutput(content=full_content)]}


async def gather_story(state: State) -> dict[Literal["markdown"], str]:
    markdown = "\n\n".join([story.content for story in state.stories])
    return {"markdown": markdown}


class LangGraphConfigurable(BaseModel):
    thread_id: str = Field(default_factory=lambda _: str(uuid4()))


class RunConfigurable(BaseModel):
    configurable: LangGraphConfigurable = Field(LangGraphConfigurable())


@lru_cache(maxsize=1)
def get_run_config() -> RunConfigurable:
    return RunConfigurable()


@lru_cache(maxsize=1)
def get_graph() -> CompiledGraph:
    memory = MemorySaver()

    return (
        StateGraph(State)
        .add_node("plan-outline", plan_outline)
        .add_node("write-story", write_story)
        .add_node("gather-stories", gather_story)
        .add_edge("write-story", "gather-stories")
        .set_entry_point("plan-outline")
        .compile(checkpointer=memory)
    )


async def main():
    graph = get_graph()
    run_config = get_run_config()

    print("Graph state:")
    async for event in graph.astream(
        StateInput(allow_user_feedback=False),
        config=run_config.model_dump(),
        stream_mode=["updates", "custom"],
    ):
        print(event)


async def main_interactive():
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.live import Live

    console = Console()
    graph = get_graph()
    run_config = get_run_config()

    is_interrupt = False
    while True:
        if is_interrupt:
            user_feedback = console.input("[bold green]Your answer: [/bold green]")
            graph_input = Command(
                resume=user_feedback,
            )
        else:
            graph_input = StateInput()
        console.rule()

        with Live() as live:
            streaming_message: str = ""
            async for stream_mode, event in graph.astream(
                graph_input,
                config=run_config.model_dump(),
                stream_mode=["custom", "updates"],
            ):
                if stream_mode != "custom":
                    streaming_message = ""

                if "__interrupt__" in event:
                    content = event["__interrupt__"][0].value
                    console.print(Markdown(content))
                elif "story-streaming" in event:
                    streaming_message += event["story-streaming"]["content"]
                    live.update(Markdown(streaming_message))
                    await asyncio.sleep(0.1)

                is_interrupt = "__interrupt__" in event

        if not is_interrupt:
            break


if __name__ == "__main__":
    # asyncio.run(main())
    asyncio.run(main_interactive())
