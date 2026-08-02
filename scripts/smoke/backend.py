import asyncio
from contextlib import asynccontextmanager
import json
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import httpx
import structlog
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from scripts.smoke.utils import create_artifacts_dir, load_cases
from scripts.smoke.models import StreamResult, SmokeCase


logger = structlog.get_logger()


class InputSettings(BaseSettings):
    ROOT_DIR: ClassVar[Path] = Path(__file__).resolve().parent

    model_config = SettingsConfigDict(case_sensitive=False)

    E2E_API_URL: str = Field(default="http://127.0.0.1:8080")
    E2E_PDF_PATH: Path = Field(default=ROOT_DIR / "fixtures" / "GraphRAG.pdf")
    E2E_CASES_PATH: Path = Field(default=ROOT_DIR / "fixtures" / "e2e_smoke_cases.json")
    E2E_ARTIFACTS_DIR: Path = Field(default=Path(".e2e-artifacts"))

    READINESS_TIMEOUT_SECONDS: float = 45
    INDEXING_TIMEOUT_SECONDS: float = 180
    CHAT_TIMEOUT_SECONDS: float = 180


settings = InputSettings()


@dataclass(frozen=True)
class ApiEndpoints:
    base_url: str

    API_PREFIX: ClassVar[str] = "/api/v1"
    COLLECTIONS_PATH: ClassVar[str] = "/collections/"
    REFERENCES_PATH: ClassVar[str] = "/references/"
    CONVERSATIONS_PATH: ClassVar[str] = "/conversations/"
    CHAT_PATH: ClassVar[str] = "/chats/chat"

    @property
    def collections(self) -> str:
        return self._url(self.COLLECTIONS_PATH)

    @property
    def references(self) -> str:
        return self._url(self.REFERENCES_PATH)

    @property
    def conversations(self) -> str:
        return self._url(self.CONVERSATIONS_PATH)

    @property
    def chat(self) -> str:
        return self._url(self.CHAT_PATH)

    def reference(self, reference_id: str) -> str:
        return f"{self.references}{reference_id}"

    def reference_chunks(self, reference_id: str) -> str:
        return f"{self.reference(reference_id)}/chunks"

    def conversation_messages(self, conversation_id: str) -> str:
        return f"{self.conversations}{conversation_id}/messages"

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}{self.API_PREFIX}{path}"


@dataclass
class BackendQA:
    endpoints: ApiEndpoints
    pdf_paths: list[Path]
    timeout: int = field(default=60)
    collection_id: str | None = field(init=False, default=None)
    reference_ids: list[str] = field(init=False, default_factory=list)
    results: dict[str, StreamResult] = field(init=False, default_factory=dict)
    _client: httpx.AsyncClient | None = field(init=False, default=None, repr=False)

    @asynccontextmanager
    async def ensure_client(self) -> AsyncGenerator[httpx.AsyncClient]:
        if self._client is not None:
            raise RuntimeError("BackendQA client is already active")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            self._client = client
            logger.info(
                "backend_smoke.client_started", base_url=self.endpoints.base_url
            )
            try:
                yield client
            finally:
                self._client = None
                logger.info("backend_smoke.client_closed")

    async def wait_until_ready(self) -> None:
        logger.info("backend_smoke.waiting_for_api", base_url=self.endpoints.base_url)
        deadline = time.monotonic() + settings.READINESS_TIMEOUT_SECONDS
        logged_unavailable = False
        while time.monotonic() < deadline:
            try:
                response = await self.client.get(self.endpoints.collections)
                if response.status_code == 200:
                    logger.info(
                        "backend_smoke.api_ready", base_url=self.endpoints.base_url
                    )
                    return
                if not logged_unavailable:
                    logger.warning(
                        "backend_smoke.api_not_ready",
                        status_code=response.status_code,
                    )
                    logged_unavailable = True
            except httpx.HTTPError:
                if not logged_unavailable:
                    logger.warning("backend_smoke.api_unreachable")
                    logged_unavailable = True
            await asyncio.sleep(0.5)
        raise TimeoutError("API did not become ready before the readiness deadline")

    async def create_collection(self) -> str:
        logger.info("backend_smoke.creating_collection")
        response = await self.client.post(
            self.endpoints.collections,
            json={
                "name": "E2E GraphRAG",
                "description": "Isolated platform smoke test",
            },
        )
        response.raise_for_status()
        collection_id = self._response_id(response)
        self.collection_id = collection_id
        logger.info("backend_smoke.collection_created", collection_id=collection_id)
        return collection_id

    async def upload_reference(self, collection_id: str) -> list[str]:
        reference_ids: list[str] = []
        for pdf_path in self.pdf_paths:
            logger.info("backend_smoke.uploading_reference", pdf_path=str(pdf_path))
            with pdf_path.open("rb") as pdf_file:
                response = await self.client.post(
                    self.endpoints.references,
                    data={
                        "collection_id": collection_id,
                        "metadata": json.dumps({"doc_name": pdf_path.name}),
                    },
                    files={
                        "reference": (
                            pdf_path.name,
                            pdf_file,
                            "application/pdf",
                        )
                    },
                )
            response.raise_for_status()
            reference_id = self._response_id(response)
            logger.info(
                "backend_smoke.reference_uploaded",
                reference_id=reference_id,
                pdf_path=str(pdf_path),
            )
            await self._wait_for_index(reference_id)
            reference_ids.append(reference_id)

        self.reference_ids = reference_ids
        logger.info(
            "backend_smoke.references_indexed", reference_count=len(reference_ids)
        )
        return reference_ids

    async def get_chunks(self, reference_id: str) -> list[dict[str, Any]]:
        logger.info("backend_smoke.loading_chunks", reference_id=reference_id)
        response = await self.client.get(self.endpoints.reference_chunks(reference_id))
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise ValueError("Reference chunks response must contain an items list")
        if not all(isinstance(item, dict) for item in payload["items"]):
            raise ValueError("Reference chunks response items must be JSON objects")
        logger.info(
            "backend_smoke.chunks_loaded",
            reference_id=reference_id,
            chunk_count=len(payload["items"]),
        )
        return payload["items"]

    async def run_case(self, case: SmokeCase) -> bool:
        logger.info(
            "backend_smoke.case_started",
            case_name=case.name,
            requires_reference=case.requires_reference,
        )
        conversation_id = await self._create_conversation()
        form_data = {
            "conversation_id": conversation_id,
            "message": case.message,
            "system_prompt": case.system_prompt,
            "web_search_enabled": str(case.web_search_enabled).lower(),
        }
        if case.requires_reference:
            if self.collection_id is None:
                raise ValueError(f"Case {case.name} requires an indexed collection")
            form_data["collection_ids"] = self.collection_id

        result = StreamResult()
        async with self.client.stream(
            "POST",
            self.endpoints.chat,
            data=form_data,
            headers={"Accept": "text/event-stream"},
            timeout=settings.CHAT_TIMEOUT_SECONDS,
        ) as response:
            response.raise_for_status()
            async for event in self._read_sse(response):
                result.events.append(event)

        self._validate_stream(case, result)
        await self._validate_persisted_response(case, conversation_id)
        self.results[case.name] = result
        logger.info(
            "backend_smoke.case_passed",
            case_name=case.name,
            conversation_id=conversation_id,
            event_count=len(result.events),
        )
        return True

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Use BackendQA methods inside ensure_client()")
        return self._client

    @staticmethod
    def _response_id(response: httpx.Response) -> str:
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("id"), str):
            raise ValueError("API response must contain a string id")
        return payload["id"]

    async def _wait_for_index(self, reference_id: str) -> None:
        logger.info("backend_smoke.waiting_for_index", reference_id=reference_id)
        deadline = time.monotonic() + settings.INDEXING_TIMEOUT_SECONDS
        previous_status: str | None = None
        while time.monotonic() < deadline:
            response = await self.client.get(self.endpoints.reference(reference_id))
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Reference status response must be a JSON object")
            status = payload.get("status")
            if status != previous_status:
                logger.info(
                    "backend_smoke.index_status",
                    reference_id=reference_id,
                    status=status,
                )
                previous_status = status
            match status:
                case "completed":
                    logger.info(
                        "backend_smoke.index_completed", reference_id=reference_id
                    )
                    return
                case "failed":
                    msg = payload.get("error_message") or "unknown indexing error"
                    logger.warning(
                        "backend_smoke.index_failed",
                        reference_id=reference_id,
                        error_message=msg,
                    )
                    raise RuntimeError(f"Reference indexing failed: {msg}")
                case _:
                    await asyncio.sleep(1)
        raise TimeoutError("Reference did not finish indexing before the deadline")

    async def _create_conversation(self) -> str:
        response = await self.client.post(
            self.endpoints.conversations, json={"title": ""}
        )
        response.raise_for_status()
        return self._response_id(response)

    async def _read_sse(
        self, response: httpx.Response
    ) -> AsyncGenerator[tuple[str, Any]]:
        event_name = "message"
        async for line in response.aiter_lines():
            if line.startswith("event: "):
                event_name = line[7:].strip()
                continue
            if line.startswith("data: "):
                yield event_name, json.loads(line[6:])

    @staticmethod
    def _validate_stream(case: SmokeCase, result: StreamResult) -> None:
        errors = [event for event in result.events if event[0] == "error"]
        if errors:
            raise RuntimeError(f"{case.name} streamed an error: {errors[-1][1]}")
        if case.expected_reasoning not in result.reasoning:
            msg = f"{case.name} did not emit {case.expected_reasoning}: {result.reasoning}"
            raise AssertionError(msg)
        if case.expected_text and case.expected_text not in result.text.lower():
            msg = (
                f"{case.name} response did not include {case.expected_text}: "
                f"{result.text}"
            )
            raise AssertionError(msg)
        if case.expects_visual_widget and not result.has_visual_widget:
            raise AssertionError(f"{case.name} did not open a visual widget block")

    async def _validate_persisted_response(
        self, case: SmokeCase, conversation_id: str
    ) -> None:
        response = await self.client.get(
            self.endpoints.conversation_messages(conversation_id)
        )
        response.raise_for_status()
        saved_messages = response.json()
        if not isinstance(saved_messages, list) or len(saved_messages) < 2:
            raise AssertionError(f"{case.name} did not persist an assistant response")
        assistant_message = saved_messages[-1]
        if (
            not isinstance(assistant_message, dict)
            or assistant_message.get("role") != "assistant"
        ):
            raise AssertionError(f"{case.name} did not persist an assistant response")
        if case.requires_reference and not assistant_message.get("mapping_evidence"):
            raise AssertionError(f"{case.name} did not persist retrieval evidence")


async def run_api_smoke(
    base_url: str,
    pdf_path: Path,
    cases: tuple[SmokeCase, ...],
    artifacts_dir: Path,
) -> None:
    logger.info(
        "backend_smoke.started",
        case_count=len(cases),
        pdf_path=str(pdf_path),
    )
    qa = BackendQA(endpoints=ApiEndpoints(base_url), pdf_paths=[pdf_path])
    async with qa.ensure_client():
        await qa.wait_until_ready()
        collection_id = await qa.create_collection()
        reference_ids = await qa.upload_reference(collection_id)
        for reference_id in reference_ids:
            if not await qa.get_chunks(reference_id):
                logger.warning(
                    "backend_smoke.no_chunks_indexed", reference_id=reference_id
                )
                raise AssertionError("Indexed GraphRAG PDF did not produce any chunks")

        for case in cases:
            await qa.run_case(case)
            output_path = artifacts_dir / f"{case.name}.json"
            output_path.write_text(
                json.dumps(qa.results[case.name].events, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info(
                "backend_smoke.transcript_written",
                case_name=case.name,
                output_path=str(output_path),
            )


async def run() -> None:
    cases = load_cases(settings.E2E_CASES_PATH)
    artifacts_dir = create_artifacts_dir(settings.E2E_ARTIFACTS_DIR)

    try:
        await run_api_smoke(
            settings.E2E_API_URL,
            settings.E2E_PDF_PATH,
            cases,
            artifacts_dir,
        )
    except Exception:
        logger.exception("backend_smoke.failed", artifacts_dir=str(artifacts_dir))
        raise

    logger.info("backend_smoke.passed", artifacts_dir=str(artifacts_dir))


if __name__ == "__main__":
    asyncio.run(run())
