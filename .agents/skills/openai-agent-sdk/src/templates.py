import asyncio
from typing import Annotated

from agents import WebSearchTool, Agent, Runner, function_tool

from .model import container
from .utils import StreamUtils


async def run_toolcall_agent() -> None:
    # Use our customized tool

    @function_tool
    async def calculate(
        a: Annotated[int, "first number"], b: Annotated[int, "second number"]
    ) -> int:
        "Calculate the magic number based on two given integers"
        return (a - b) + 0.5

    agent = Agent(name="magic-number", model=container.chat_model, tools=[calculate])

    events = Runner().run_streamed(
        agent, input="What is the magic calculated result between 15 and 27"
    )

    await StreamUtils.print_event(events)


async def run_websearch_agent() -> None:
    # Use web-search or any built-in tool

    agent = Agent(
        name="websearch-agent",
        model=container.chat_model,
        instructions="You answer for all of questions, using websearch as the knowledge base searcher",
        tools=[
            WebSearchTool(
                search_context_size="high",
            )
        ],
    )

    events = Runner().run_streamed(
        agent, input="Tổng hợp thông tin về cổ phiếu Hoà Phát"
    )

    await StreamUtils.print_event(events)


async def run_agent_skills() -> None:
    # Load skills from local dir
    # Run in a implementation of ShellTool Executor

    from agents import ShellToolLocalSkill, ShellTool

    def build_local_skills() -> list[ShellToolLocalSkill]:
        SKILL_DIR = "/Users/phamhoaivan/Desktop/projects/fun-repos/lavish-axi-python/src/lavish_axi_python/skills/lavish"

        return [
            ShellToolLocalSkill(
                name="lavish",
                description=(
                    "Turn complex or visual agent responses into rich, reviewable HTML artifacts "
                    "the user can annotate and send feedback on, using the lavish-axi CLI. "
                    "Use when about to give a plan, comparison, diagram, table, code diff, report, "
                    "or anything easier to grasp visually than as prose."
                ),
                path=SKILL_DIR,
            )
        ]

    agent = Agent(
        name="skilled-agent",
        model=container.chat_model,
        tools=[
            ShellTool(
                executor=container.shell_executor,
                environment={"skills": build_local_skills()},
            )
        ],
    )

    query = "Explain the milvus architecture?"
    events = Runner.run_streamed(agent, input=query)

    await StreamUtils.print_event(events)


async def run_agent_tool_guardrails() -> None:
    # Use tool guardrails to control the agent's tool usage
    # Check from https://openai.github.io/openai-agents-python/guardrails/

    import json
    from agents import (
        function_tool,
        tool_input_guardrail,
        tool_output_guardrail,
        ToolGuardrailFunctionOutput,
        ToolInputGuardrailData,
        ToolOutputGuardrailData,
    )

    @tool_input_guardrail
    async def block_secrets(
        data: ToolInputGuardrailData,
    ) -> ToolGuardrailFunctionOutput:
        print("tool_input_guardrail", type(data))
        args = json.loads(data.context.tool_arguments or "{}")
        if "sk-" in json.dumps(args):
            return ToolGuardrailFunctionOutput.reject_content(
                "Remove secrets before calling this tool."
            )
        return ToolGuardrailFunctionOutput.allow()

    @tool_output_guardrail
    async def redact_output(
        data: ToolOutputGuardrailData,
    ) -> ToolGuardrailFunctionOutput:
        print("tool_output_guardrail", type(data))
        text = str(data.output or "")
        if "sk-" in text:
            return ToolGuardrailFunctionOutput.reject_content(
                "Output contained sensitive data."
            )
        return ToolGuardrailFunctionOutput.allow()

    @function_tool(
        tool_input_guardrails=[block_secrets],
        tool_output_guardrails=[redact_output],
    )
    async def classify_text(text: str) -> str:
        """Classify text for internal routing."""
        return f"length:{len(text)}"

    agent = Agent(
        name="classifier-agent", model=container.chat_model, tools=[classify_text]
    )

    events = Runner().run_streamed(
        agent, input="Classify this text: 'This is a test message with a secret.'"
    )

    await StreamUtils.print_event(events)


async def run_agent_human_approval() -> None:
    # Use human approval to control the agent's tool usage
    # Check from https://openai.github.io/openai-agents-python/human_in_the_loop/

    from typing import Annotated
    from agents import function_tool, Runner

    @function_tool(needs_approval=True)
    async def get_temperature(
        city: Annotated[str, "The city to get temperature for."],
    ) -> str:
        # Get the temperature for a given city.
        return f"The temperature in {city} is 20° Celsius"

    @function_tool
    async def get_weather(city: Annotated[str, "The city to get weather for."]) -> str:
        # Get the weather for the given city
        return f"The weather in {city} is sunny."

    async def confirm(question: str) -> bool:
        default = "y"
        answer = input(f"{question} (y/n): ").strip().lower()
        if not answer:
            return default
        return answer in {"y", "yes"}

    agent = Agent(
        name="weather-assistant",
        model=container.chat_model,
        instructions=(
            "You are a helpful weather assistant. "
            "Answer questions about weather and temperature using the available tools."
        ),
        tools=[get_temperature, get_weather],
    )

    events = Runner.run_streamed(
        agent,
        "What is the weather and temperature in Oakland?",
    )

    await StreamUtils.print_event(events)

    # Handle interruptions
    while len(events.interruptions) > 0:
        print("\n" + "=" * 80)
        print("Human-in-the-loop: approval required for the following tool calls:")
        print("=" * 80)

        state = events.to_state()

        for interruption in events.interruptions:
            print("\nTool call details:")
            print(f"  Agent: {interruption.agent.name}")
            print(f"  Tool: {interruption.name}")
            print(f"  Arguments: {interruption.arguments}")

            confirmed = await confirm("\n Do you approve this tool call?")

            if confirmed:
                print(f"✓ Approved: {interruption.name}")
                state.approve(interruption)
            else:
                print(f"✗ Rejected: {interruption.name}")
                state.reject(interruption)

        # Resume execution with streaming
        print("\nResuming agent execution...")
        events = Runner.run_streamed(agent, state)
        await StreamUtils.print_event(events)

    print("Done")


async def run_agent_handoff() -> None:
    # Use handoff to control the agent's tool usage
    # Check: https://github.com/openai/openai-agents-python/blob/main/examples/agent_patterns/routing.py

    french_agent = Agent(
        name="french_agent",
        instructions="You only speak French",
        handoff_description="Handle french",
        model=container.chat_model,
    )

    vietnam_agent = Agent(
        name="vietname_agent",
        instructions="You only speak Vietnameese",
        handoff_description="Handle Vietnamese",
        model=container.chat_model,
    )

    english_agent = Agent(
        name="english_agent",
        instructions="You only speak English",
        handoff_description="Handle english",
        model=container.chat_model,
    )

    triage_agent = Agent(
        name="triage_agent",
        instructions="Handoff to the appropriate agent based on the language of the request.",
        handoffs=[french_agent, vietnam_agent, english_agent],
        model=container.chat_model,
    )

    message = "Xin chào bạn"

    inputs = [
        {
            "content": message,
            "role": "user",
        }
    ]

    print(message)

    while True:
        events = Runner.run_streamed(
            triage_agent,
            input=inputs,
        )

        await StreamUtils.print_event(events)

        inputs = events.to_input_list()
        print("\n")

        user_message = input("Enter a message: ")
        inputs.append({"content": user_message, "role": "user"})

        # Question: do we need this?
        triage_agent = events.current_agent


if __name__ == "__main__":
    asyncio.run(run_agent_handoff())
