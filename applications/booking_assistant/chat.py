import asyncio
import logging
from pathlib import Path
from uuid import uuid4

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live

from agent.graphs.workflows.booking_assistant import (
    BookingAssistantGraph,
    GraphDependencies,
)
from agent.models.document import ScoredChunks
from agent.models.messages import AssistantMessage, UserMessage
from agent.models.stream import StreamChatData, StreamChunksData, StreamInterruptData

# For demo purpose, disable logging
logging.disable(logging.CRITICAL)

console = Console()


def pretty_print_evidences(
    chunks: ScoredChunks,
    max_length: int = 1024,
    max_chunks: int = 3,
) -> Table:
    table = Table(title="Evidence(s)", show_lines=True)
    table.add_column("Reference", justify="left")
    table.add_column("Content", justify="left")

    for idx, scored_chunk in enumerate(chunks.root[:max_chunks], start=1):
        truncated_text = scored_chunk.text
        if len(truncated_text) > max_length:
            truncated_text = f"{truncated_text[:max_length]} [bold red]...[/bold red]"
        table.add_row(f"[bold green]【28†{idx}】[/bold green]", truncated_text)

    if len(chunks.root) > max_chunks:
        table.add_row(
            f"[bold green] {len(chunks.root) - max_chunks} more chunk(s) ...[/bold green]",
            "[bold green]...[/bold green]",
        )

    return table


async def interactive_demo():
    samplepath = Path("datas/tickets/samples.json")
    dependencies = GraphDependencies(samplepath)
    graph = BookingAssistantGraph(dependencies)
    conversation_id = str(uuid4())

    history: list[UserMessage | AssistantMessage] = []
    is_interrupted = False
    while True:
        user_content = console.input("[bold yellow]User:[/bold yellow] ")
        if user_content.lower() in ["q", "quit", "exit"]:
            break

        full_chat = "`Assistant:` \n"
        with Live(console=console) as live:
            async for response in graph.stream_async_answer(
                query=user_content,
                history=history,
                is_interrupted=is_interrupted,
                conversation_id=conversation_id,
            ):
                match response:
                    case StreamChatData():
                        full_chat += response.data.content
                        live.update(Markdown(full_chat))
                        await asyncio.sleep(0.043)
                    case StreamInterruptData():
                        is_interrupted = response.data.is_interrupted
                    case StreamChunksData():
                        console.print(pretty_print_evidences(response.data))

    console.print("[bold green]Assistant:[/bold green] thanks for using our service")
    await asyncio.Future()


def get_graph():
    samplepath = Path("datas/tickets/samples.json")
    dependencies = GraphDependencies(samplepath)
    graph = BookingAssistantGraph(dependencies)

    print(graph.graph.get_graph(xray=3).draw_mermaid(with_styles=False))


if __name__ == "__main__":
    asyncio.run(interactive_demo())
