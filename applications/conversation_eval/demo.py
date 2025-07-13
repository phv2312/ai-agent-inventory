import asyncio
from concurrent.futures import Executor, ProcessPoolExecutor, ThreadPoolExecutor
from functools import lru_cache
import time
from typing import Final, Literal
import pandas as pd
import yaml
import json
import logging
from pathlib import Path
import aiofiles
from jinja2 import Template, UndefinedError
from difflib import Differ

from pydantic import BaseModel, ValidationError
import gradio as gr
from gradio.components.file import File

from agent.batched import Batched
from agent.container import Container
from agent.models.messages import UserMessage
from agent.programs.impl.followup_comparison import FollowupComparisonResponse
from agent.programs.impl.semantic_comparison import SemanticComparisonResponse
from agent.storages.search_engine.bm25s import BM25SSearchEngine, BM25SConfig
from applications.conversation_eval.indexing import ConstantIngestor
from applications.conversation_eval.chat import ChatParser, CallParser, ConversationType


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


bm25s_engine = None
chat_parser = ChatParser()
call_parser = CallParser()
ingestor = ConstantIngestor()
container = Container()

topk = 1
batch_size = 5
semantic_comparison_prompt_path = (
    "agent/prompts/conversation_eval/semantic_comparison.md"
)
followup_comparison_prompt_path = (
    "agent/prompts/conversation_eval/followup_comparison.md"
)


@lru_cache(maxsize=1)
def get_executor(
    max_workers: int = 4,
    executor_type: Literal["processpool", "threadpool"] = "threadpool",
) -> Executor:
    match executor_type:
        case "threadpool":
            return ThreadPoolExecutor(max_workers=max_workers)
        case "processpool":
            # TODO: future due to some concurrent read/write block process now.
            return ProcessPoolExecutor(max_workers=max_workers)
        case _:
            raise ValueError(f"Unsupported executor type: {executor_type}")


class Templates:
    missing_words: Final[Template] = Template(
        """<span style="background-color:yellow; color:red; font-weight:bold;">{{ word }}</span>"""
    )
    redundant_words: Final[Template] = Template(
        """<span style="background-color:lightgreen; color:black; font-weight:bold;">{{ word }}</span>"""
    )


class EvaluationError(BaseModel):
    error: str


class EvaluationRow(BaseModel):
    score: float
    rule: str
    rule_constant: str
    agent_message: str
    user_message: str
    is_semantic_same: bool = (True,)
    semantic_judge_reason_first_sentence: str = ("",)
    semantic_judge_reason_second_sentence: str = ("",)
    followup_resolved: bool = False
    followup_score: float = 0.0
    followup_goodpoints: str = ""
    followup_notgoodpoints: str = ""


class HighlighedOutput(BaseModel):
    query: str
    doc: str
    cli: str
    wrong: int
    correct: int

    @property
    def score(self) -> float:
        if self.wrong + self.correct == 0:
            return 0.0
        return self.correct / (self.wrong + self.correct + 1e-6)


async def get_semantic_difference(
    rule_constraint: str, ai_message: str
) -> SemanticComparisonResponse:
    program = container.programs.get("semantic_comparison")
    async with aiofiles.open(semantic_comparison_prompt_path, "r") as file:
        template = Template(await file.read())
    rendered_template = template.render(
        first_sentence=rule_constraint.strip(),
        second_sentence=ai_message.strip(),
    )

    return await program.aprocess(message=UserMessage(content=rendered_template))


async def get_followup_comparison(
    user_message: str, ai_message: str
) -> FollowupComparisonResponse:
    if user_message.strip() == "":
        return FollowupComparisonResponse(
            confidence=0.0,
            is_concern_solved=False,
            good_points="",
            notgood_points="",
        )

    program = container.programs.get("followup_comparison")
    async with aiofiles.open(followup_comparison_prompt_path, "r") as file:
        template = Template(await file.read())
    rendered_template = template.render(
        first_sentence=user_message.strip(),
        second_sentence=ai_message.strip(),
    )

    return await program.aprocess(message=UserMessage(content=rendered_template))


def highlight_difference(query: str, doc: str) -> HighlighedOutput:
    differ = Differ()
    diff = list(differ.compare(query.split(), doc.split()))

    wrong = correct = 0
    query_parts = []
    doc_parts = []
    difference_cli_parts = []

    for word in diff:
        if word.startswith("- "):
            wrong += 1
            query_parts.append(Templates.missing_words.render(word=word[2:]))
            difference_cli_parts.append(f"\033[91m{word[2:]}\033[0m")
        elif word.startswith("+ "):
            wrong += 1
            doc_parts.append(Templates.redundant_words.render(word=word[2:]))
            difference_cli_parts.append(f"\033[92m{word[2:]}\033[0m")
        else:
            correct += 1
            query_parts.append(word[2:])
            doc_parts.append(word[2:])
            difference_cli_parts.append(word[2:])

    return HighlighedOutput(
        query=" ".join(query_parts),
        doc=" ".join(doc_parts),
        cli=" ".join(difference_cli_parts),
        wrong=wrong,
        correct=correct,
    )


class ConstantsFile(BaseModel):
    rules: dict[str, list[str]]

    @classmethod
    async def from_file(cls, file_path: Path) -> "ConstantsFile":
        async with aiofiles.open(file_path, "r", encoding="utf-8") as file:
            content = await file.read()

        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {str(e)}")

        return cls(rules=data)


def load_environment(bm25s_collection: str):
    global bm25s_engine
    try:
        collection_name = bm25s_collection or "conversation_constants"
        checkpoint_dir = Path("./indexes") / f"bm25s_{collection_name}_index"
        bm25s_engine = BM25SSearchEngine(
            checkpoint_dir=checkpoint_dir, config=BM25SConfig()
        )

        # Let call here to trigger the cache
        get_executor()

        return "✅ Services initialized successfully"
    except ValidationError as e:
        return f"❌ Invalid configuration: {e}"
    except Exception as e:
        return f"❌ Error loading environment: {str(e)}"


async def index_constants_file(filepath: Path) -> str:
    try:
        if not bm25s_engine:
            return "❌ Services not initialized. Please configure environment first."

        chunks = await ingestor.ingest(filepath=filepath)
        logger.info("Created %d chunks from constants", len(chunks))

        await bm25s_engine.add(chunks)

        success_msg = f"✅ Successfully indexed {len(chunks)} constants from the file"
        return success_msg
    except ValidationError as e:
        error_msg = "\n".join([f"- {error['msg']}" for error in e.errors()])
        return f"❌ Validation failed:\n{error_msg}"
    except Exception as e:
        logger.error("Error indexing file: %s", str(e))
        return f"❌ Error indexing file: {str(e)}"


async def index_file_wrapper(file: File):
    if file is None:
        return "❌ Please upload a file", ""

    return await index_constants_file(Path(file.name))


async def analyze_conversation(
    conversation_text: str, conversation_type: ConversationType, placeholder_json: str
) -> list[EvaluationRow | EvaluationError]:
    temp_file = Path("/tmp/temp_conversation.txt")
    async with aiofiles.open(temp_file, "w", encoding="utf-8") as file:
        await file.write(conversation_text)

    try:
        if not all([bm25s_engine]):
            return [
                EvaluationError(
                    error="Services not initialized. Please configure environment first."
                )
            ]

        try:
            placeholder = (
                json.loads(placeholder_json) if placeholder_json.strip() else {}
            )
        except json.JSONDecodeError as e:
            return [EvaluationError(error=f"Error while parsing JSON: {str(e)}")]

        match conversation_type:
            case ConversationType.chat:
                mp_messages = await chat_parser.parse(temp_file)
            case ConversationType.call:
                mp_messages = await call_parser.parse(temp_file)

        responses: list[EvaluationRow] = []
        counter = 1
        num_ai_messages = len(mp_messages["assistant"])

        for pairs_contents in Batched.iter(mp_messages["pairs"], batch_size=batch_size):
            ai_contents = [pair[0] for pair in pairs_contents]
            user_contents = [pair[1] for pair in pairs_contents]

            start_time = time.perf_counter()
            retrieved_chunks_list = await asyncio.gather(
                *[
                    bm25s_engine.search(ai_content, top_k=topk, executor=get_executor())
                    for ai_content in ai_contents
                ]
            )

            for ai_content, user_content, retrieved_chunks in zip(
                ai_contents, user_contents, retrieved_chunks_list
            ):
                if len(retrieved_chunks) == 0:
                    raise ValueError(
                        f"No constants found for AI message: {ai_content[:50]}"
                    )

                most_similar_chunk = retrieved_chunks.root[0]
                template = Template(most_similar_chunk.chunk.text)

                try:
                    prompt_content = template.render(
                        **{"raw_call_assignment": placeholder}
                    )
                except UndefinedError:
                    logger.warning(
                        "Placeholder keys not found in template: %s",
                        ", ".join(template.undefined_variables),
                    )
                    prompt_content = most_similar_chunk.chunk.text

                difference = highlight_difference(ai_content, prompt_content)
                semantic_result = await get_semantic_difference(
                    prompt_content, ai_content
                )
                followup_result = await get_followup_comparison(
                    user_message=user_content, ai_message=ai_content
                )

                responses.append(
                    EvaluationRow(
                        score=difference.score,
                        rule=most_similar_chunk.chunk.metadata.group_name,
                        agent_message=difference.query,
                        user_message=user_content,
                        rule_constant=difference.doc,
                        is_semantic_same=semantic_result.is_same_meaning,
                        semantic_judge_reason_first_sentence=semantic_result.reason_first_sentence,
                        semantic_judge_reason_second_sentence=semantic_result.reason_second_sentence,
                        followup_resolved=followup_result.is_concern_solved,
                        followup_score=followup_result.confidence,
                        followup_goodpoints=followup_result.good_points,
                        followup_notgoodpoints=followup_result.notgood_points,
                    )
                )
                logger.info(
                    "[%s] Highlighted: %s",
                    conversation_type,
                    difference.cli,
                )

            gr.Info(
                "[%.3d/%.3d]Evaluated messages in %.3f seconds"
                % (
                    min(counter * batch_size, num_ai_messages),
                    num_ai_messages,
                    time.perf_counter() - start_time,
                ),
                duration=3,
            )
            counter += 1

        return responses
    except Exception as e:
        logger.error("Error analyzing conversation: %s", str(e))
        return [EvaluationError(error=str(e))]
    finally:
        temp_file.unlink(missing_ok=True)


async def analyze_conversation_wrapper(
    conversation_text: str, conversation_type: ConversationType, placeholder_json: str
) -> tuple[str, pd.DataFrame | None]:
    if not conversation_text.strip():
        return "❌ Please provide conversation text", None

    try:
        results = await analyze_conversation(
            conversation_text, conversation_type, placeholder_json
        )

        if len(results) == 0:
            return (
                "❌ No results found. Please check your conversation text, types and constants.",
                None,
            )

        match results[0]:
            case EvaluationError():
                error_msg = results[0].error
                return f"❌ Error: {error_msg}", None
            case EvaluationRow():
                df = pd.DataFrame([result.model_dump() for result in results])
                return f"✅ Analyzed {len(results)} assistant messages", df

    except Exception as e:
        return f"❌ Error: {str(e)}", None


with gr.Blocks(title="Conversation Evaluation Tool", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 Conversation Evaluation Tool")
    gr.Markdown(
        "Configure environment, upload constants files and analyze conversations for compliance and quality."
    )

    # Common configuration panel (merged environment settings)
    with gr.Row():
        with gr.Column():
            bm25s_collection_input = gr.Textbox(
                label="BM25S Collection Name",
                placeholder="conversation-eval",
                value="conversation-eval",
            )

        with gr.Column():
            env_status = gr.Textbox(
                label="Status",
                interactive=False,
                value="Please configure and load environment to use the application.",
            )

        with gr.Column():
            gr.Markdown("## ⚠️ Initialize services before using")
            load_env_btn = gr.Button(
                "Initialize Services", variant="primary", size="lg"
            )

    load_env_btn.click(
        fn=load_environment,
        inputs=[bm25s_collection_input],
        outputs=[env_status],
    )

    with gr.Tabs():
        with gr.Tab("📁 Indexing"):
            gr.Markdown("## Upload Constants File")
            gr.Markdown(
                "Upload a YAML file containing conversation constants/templates."
            )

            with gr.Row():
                with gr.Column():
                    file_upload = gr.File(
                        label="Upload YAML File",
                        file_types=[".yaml", ".yml"],
                        type="filepath",
                    )
                    index_btn = gr.Button("Index File", variant="primary")

                with gr.Column():
                    index_status = gr.Textbox(label="Status", interactive=False)

            index_btn.click(
                fn=index_file_wrapper, inputs=[file_upload], outputs=[index_status]
            )

        with gr.Tab("💬 Conversation Analysis"):
            gr.Markdown("## Analyze Conversation")
            gr.Markdown(
                "Paste conversation text and analyze it against indexed constants."
            )

            with gr.Row():
                with gr.Column():
                    conversation_input = gr.Textbox(
                        label="Conversation Text",
                        placeholder=(
                            "Paste your conversation here...\n\nFor Chat format:\nUser: Hello\nAssistant: "
                            "Hi there!\n\nFor Call format:\n[2024-01-01 10:00] Agent: Hello\n[2024-01-01 10:01] Human: Hi"
                        ),
                    )

                    conversation_type = gr.Radio(
                        choices=[ConversationType.chat, ConversationType.call],
                        label="Conversation Type",
                        value=ConversationType.chat,
                    )

                    placeholder_input = gr.Textbox(
                        label="Placeholders (JSON)",
                        placeholder=(
                            '{"customer_pronoun": "Mr", "full_name": "John Cena", "customer_name": "John Cena", '
                            '"customer_first_name": "John"}'
                        ),
                        lines=3,
                    )

                    analyze_btn = gr.Button("Analyze Conversation", variant="primary")

                with gr.Column():
                    analysis_status = gr.Textbox(
                        label="Analysis Status", interactive=False
                    )

                    download_btn = gr.DownloadButton(
                        label="Download Results as Excel", visible=False
                    )

            # Add HTML output for highlighted results with center alignment
            gr.Markdown("### Analysis Results with Highlighted Differences")
            highlighted_output = gr.HTML(label="Highlighted Results", visible=False)

            async def update_ui_after_analysis(
                conversation_text: str,
                conversation_type: ConversationType,
                placeholder_json: str,
            ):
                status, df = await analyze_conversation_wrapper(
                    conversation_text, conversation_type, placeholder_json
                )

                if df is not None:
                    pathout = "conv_analysis.xlsx"

                    # Create Excel export with plain text highlighting
                    df_excel = df.copy()
                    if "highlight" in df_excel.columns:
                        import re

                        for i, highlight_html in enumerate(df_excel["highlight"]):
                            # Remove HTML tags and convert to plain text format
                            plain_text = re.sub(
                                r"<span[^>]*>(.*?)</span>", r"[\1]", highlight_html
                            )
                            df_excel.loc[i, "highlight"] = plain_text

                    df_excel.to_excel(
                        pathout, sheet_name="Conversation_Analysis", index=False
                    )

                    # Simple HTML output using DataFrame's built-in to_html
                    html_content = df.to_html(escape=False, index=False)

                    return (
                        status,
                        gr.HTML(value=html_content, visible=True),
                        gr.DownloadButton(value=pathout, visible=True),
                    )
                else:
                    return (
                        status,
                        gr.HTML(visible=False),
                        gr.DownloadButton(visible=False),
                    )

            analyze_btn.click(
                fn=update_ui_after_analysis,
                inputs=[conversation_input, conversation_type, placeholder_input],
                outputs=[analysis_status, highlighted_output, download_btn],
            )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
