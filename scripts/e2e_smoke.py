#!/usr/bin/env python3

import argparse
import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PDF_PATH = ROOT_DIR / "assets" / "fixtures" / "GraphRAG.pdf"
READINESS_TIMEOUT_SECONDS = 45
INDEXING_TIMEOUT_SECONDS = 180
CHAT_TIMEOUT_SECONDS = 180


@dataclass(frozen=True)
class SmokeCase:
    name: str
    message: str
    system_prompt: str
    web_search_enabled: bool = False
    requires_reference: bool = False
    expected_reasoning: str = ""
    expected_text: str = ""
    expects_visual_widget: bool = False


@dataclass
class StreamResult:
    events: list[tuple[str, Any]] = field(default_factory=list)

    @property
    def reasoning(self) -> str:
        return "".join(
            event[1][0].get("content", "")
            for event in self.events
            if event[0] == "reasoning" and isinstance(event[1], list) and event[1]
        )

    @property
    def text(self) -> str:
        return "".join(
            event[1].get("content", "")
            for event in self.events
            if event[0] == "block-delta"
            and isinstance(event[1], dict)
            and event[1].get("type") == "text"
        )

    @property
    def has_visual_widget(self) -> bool:
        return any(
            event[0] == "block-open"
            and isinstance(event[1], dict)
            and event[1].get("type") == "visual_widget"
            for event in self.events
        )


SMOKE_CASES = (
    SmokeCase(
        name="web-search-hoa-phat",
        message="Tình hình cổ phiếu Hoà Phát",
        system_prompt="Use web search before answering and cite the web source.",
        web_search_enabled=True,
        expected_reasoning="[Web Search]",
    ),
    SmokeCase(
        name="graphrag-vs-traditional-rag",
        message="Compare GraphRAG and traditional RAG using the uploaded paper.",
        system_prompt=(
            "Use internal_search_tool before answering. Cite the uploaded paper "
            "with its chunk IDs and include the required snippets block."
        ),
        requires_reference=True,
        expected_reasoning="[Internal Search]",
        expected_text="graphrag",
    ),
    SmokeCase(
        name="milvus-architecture-visualization",
        message="Visualize the Milvus architecture.",
        system_prompt=(
            "Call visualize_read_me with the diagram module before answering, "
            "then return one valid visualize:diagram fence."
        ),
        expected_reasoning="[Visualization]",
        expects_visual_widget=True,
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the isolated platform smoke suite."
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path(os.environ.get("E2E_PDF_PATH", DEFAULT_PDF_PATH)),
        help="Path to the GraphRAG PDF used for document ingestion.",
    )
    parser.add_argument(
        "--with-ui",
        action="store_true",
        help="Also run the small Playwright upload and chat journey.",
    )
    parser.add_argument(
        "--keep-artifacts",
        action="store_true",
        help="Keep the temporary data and logs after a successful run.",
    )
    return parser.parse_args()


def reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def require_pdf(pdf_path: Path) -> Path:
    resolved = pdf_path.expanduser().resolve()
    if not resolved.is_file():
        msg = f"Smoke PDF was not found: {resolved}"
        raise FileNotFoundError(msg)
    if resolved.suffix.lower() != ".pdf":
        msg = f"Smoke input must be a PDF: {resolved}"
        raise ValueError(msg)
    return resolved


async def wait_for_api(client: httpx.AsyncClient, base_url: str) -> None:
    deadline = time.monotonic() + READINESS_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            response = await client.get(f"{base_url}/api/v1/collections/")
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.5)
    raise TimeoutError("API did not become ready before the readiness deadline")


async def create_collection(client: httpx.AsyncClient, base_url: str) -> str:
    response = await client.post(
        f"{base_url}/api/v1/collections/",
        json={"name": "E2E GraphRAG", "description": "Isolated platform smoke test"},
    )
    response.raise_for_status()
    return str(response.json()["id"])


async def upload_reference(
    client: httpx.AsyncClient,
    base_url: str,
    collection_id: str,
    pdf_path: Path,
) -> str:
    with pdf_path.open("rb") as pdf_file:
        response = await client.post(
            f"{base_url}/api/v1/references/",
            data={
                "collection_id": collection_id,
                "metadata": json.dumps({"doc_name": "GraphRAG.pdf"}),
            },
            files={"reference": ("GraphRAG.pdf", pdf_file, "application/pdf")},
        )
    response.raise_for_status()
    return str(response.json()["id"])


async def wait_for_index(
    client: httpx.AsyncClient, base_url: str, reference_id: str
) -> None:
    deadline = time.monotonic() + INDEXING_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        response = await client.get(f"{base_url}/api/v1/references/{reference_id}")
        response.raise_for_status()
        payload = response.json()
        match payload["status"]:
            case "completed":
                return
            case "failed":
                msg = payload.get("error_message") or "unknown indexing error"
                raise RuntimeError(f"Reference indexing failed: {msg}")
            case _:
                await asyncio.sleep(1)
    raise TimeoutError("Reference did not finish indexing before the deadline")


async def create_conversation(client: httpx.AsyncClient, base_url: str) -> str:
    response = await client.post(
        f"{base_url}/api/v1/conversations/", json={"title": ""}
    )
    response.raise_for_status()
    return str(response.json()["id"])


async def read_sse(response: httpx.Response) -> AsyncIterator[tuple[str, Any]]:
    event_name = "message"
    async for line in response.aiter_lines():
        if line.startswith("event: "):
            event_name = line[7:].strip()
            continue
        if not line.startswith("data: "):
            continue
        yield event_name, json.loads(line[6:])


async def run_chat_case(
    client: httpx.AsyncClient,
    base_url: str,
    case: SmokeCase,
    collection_id: str | None,
) -> StreamResult:
    conversation_id = await create_conversation(client, base_url)
    form_data: list[tuple[str, str]] = [
        ("conversation_id", conversation_id),
        ("message", case.message),
        ("system_prompt", case.system_prompt),
        ("web_search_enabled", str(case.web_search_enabled).lower()),
    ]
    if case.requires_reference:
        if collection_id is None:
            raise ValueError(f"Case {case.name} requires an indexed collection")
        form_data.append(("collection_ids", collection_id))

    result = StreamResult()
    async with client.stream(
        "POST",
        f"{base_url}/api/v1/chats/chat",
        data=form_data,
        headers={"Accept": "text/event-stream"},
        timeout=CHAT_TIMEOUT_SECONDS,
    ) as response:
        response.raise_for_status()
        async for event in read_sse(response):
            result.events.append(event)

    errors = [event for event in result.events if event[0] == "error"]
    if errors:
        raise RuntimeError(f"{case.name} streamed an error: {errors[-1][1]}")
    if case.expected_reasoning not in result.reasoning:
        msg = f"{case.name} did not emit {case.expected_reasoning}: {result.reasoning}"
        raise AssertionError(msg)
    if case.expected_text and case.expected_text not in result.text.lower():
        msg = (
            f"{case.name} response did not include {case.expected_text}: {result.text}"
        )
        raise AssertionError(msg)
    if case.expects_visual_widget and not result.has_visual_widget:
        msg = f"{case.name} did not open a visual widget block"
        raise AssertionError(msg)

    messages = await client.get(
        f"{base_url}/api/v1/conversations/{conversation_id}/messages"
    )
    messages.raise_for_status()
    saved_messages = messages.json()
    if len(saved_messages) < 2 or saved_messages[-1]["role"] != "assistant":
        raise AssertionError(f"{case.name} did not persist an assistant response")
    if case.requires_reference and not saved_messages[-1]["mapping_evidence"]:
        raise AssertionError(f"{case.name} did not persist retrieval evidence")
    return result


async def run_api_smoke(base_url: str, pdf_path: Path, artifacts_dir: Path) -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        await wait_for_api(client, base_url)
        collection_id = await create_collection(client, base_url)
        reference_id = await upload_reference(client, base_url, collection_id, pdf_path)
        await wait_for_index(client, base_url, reference_id)

        chunks = await client.get(f"{base_url}/api/v1/references/{reference_id}/chunks")
        chunks.raise_for_status()
        if chunks.json()["total"] < 1:
            raise AssertionError("Indexed GraphRAG PDF did not produce any chunks")

        for case in SMOKE_CASES:
            result = await run_chat_case(client, base_url, case, collection_id)
            output_path = artifacts_dir / f"{case.name}.json"
            output_path.write_text(
                json.dumps(result.events, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )


async def wait_for_frontend(client: httpx.AsyncClient, frontend_url: str) -> None:
    deadline = time.monotonic() + READINESS_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            response = await client.get(frontend_url)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.5)
    raise TimeoutError("Frontend did not become ready before the readiness deadline")


async def run_ui_smoke(frontend_url: str, base_url: str, pdf_path: Path) -> None:
    env = os.environ | {
        "E2E_FRONTEND_URL": frontend_url,
        "E2E_API_URL": base_url,
        "E2E_PDF_PATH": str(pdf_path),
    }
    process = await asyncio.create_subprocess_exec(
        "npm",
        "run",
        "e2e:smoke",
        cwd=ROOT_DIR / "frontend",
        env=env,
    )
    return_code = await process.wait()
    if return_code != 0:
        raise RuntimeError(f"Browser smoke test exited with status {return_code}")


async def run(args: argparse.Namespace) -> None:
    pdf_path = require_pdf(args.pdf)
    api_port = reserve_port()
    frontend_port = reserve_port()
    temp_root = Path(tempfile.mkdtemp(prefix="ai-agent-inventory-e2e-"))
    data_dir = temp_root / "data"
    artifacts_dir = temp_root / "artifacts"
    artifacts_dir.mkdir()
    log_path = artifacts_dir / "platform.log"
    launch_env = os.environ | {
        "AGENT_API_PORT": str(api_port),
        "FRONTEND_PORT": str(frontend_port),
        "AGENT_API_DATA_DIR": str(data_dir),
        "OPENAI_AGENTS_DISABLE_TRACING": "1",
        "PHOENIX_TRACING_ENABLED": "false",
    }
    command = ["bash", "scripts/run.sh"]
    if not args.with_ui:
        command.append("--api-only")

    try:
        with log_path.open("w", encoding="utf-8") as log_file:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=ROOT_DIR,
                env=launch_env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
            try:
                api_url = f"http://127.0.0.1:{api_port}"
                await run_api_smoke(api_url, pdf_path, artifacts_dir)
                if args.with_ui:
                    frontend_url = f"http://127.0.0.1:{frontend_port}"
                    async with httpx.AsyncClient(timeout=10) as client:
                        await wait_for_frontend(client, frontend_url)
                    await run_ui_smoke(frontend_url, api_url, pdf_path)
            finally:
                if process.returncode is None:
                    process.terminate()
                    await process.wait()
    except Exception:
        print(f"Artifacts retained at {temp_root}", file=sys.stderr)
        raise

    if args.keep_artifacts:
        print(f"Smoke run passed. Artifacts kept at {temp_root}")
        return
    shutil.rmtree(temp_root)
    print("Platform smoke test passed.")


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(run(args))
    except Exception as exc:
        print(f"Platform smoke test failed: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
