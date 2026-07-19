from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

from opentelemetry.trace import Status, StatusCode
from openinference.instrumentation import TracerProvider
from openinference.instrumentation._spans import OpenInferenceSpan
from openinference.instrumentation._tracers import OITracer
from openinference.instrumentation.context_attributes import using_attributes
from openinference.instrumentation.helpers import safe_json_dumps
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes
from phoenix.otel import register

from .env import Env


def create_tracer(env: Env) -> TracerProvider:
    """Create a Phoenix-backed or no-export tracing provider."""
    if not env.PHOENIX_TRACING_ENABLED:
        return TracerProvider()
    return register(
        project_name=env.PHOENIX_PROJECT_NAME,
        endpoint=env.PHOENIX_ENDPOINT,
        protocol=env.PHOENIX_PROTOCOL,
        batch=False,
        verbose=False,
    )


def new_request_id() -> str:
    return uuid4().hex[:12]


def format_trace_id(trace_id: int) -> str:
    return format(trace_id, "032x")


@contextmanager
def chain_span(
    tracer: OITracer,
    name: str,
    input_value: str,
    *,
    request_id: str | None = None,
    file_ids: list[str] | None = None,
) -> Generator[OpenInferenceSpan, None, None]:
    rid = request_id or new_request_id()
    with using_attributes(
        session_id=rid,
        metadata={"request_id": rid},
        tags=[rid],
    ):
        with tracer.start_as_current_span(
            name,
            openinference_span_kind=OpenInferenceSpanKindValues.CHAIN,
        ) as span:
            span.set_attribute(SpanAttributes.SESSION_ID, rid)
            span.set_attribute(
                SpanAttributes.METADATA,
                safe_json_dumps(
                    {"request_id": rid, "file_ids": file_ids or []},
                ),
            )
            span.set_attribute(SpanAttributes.TAG_TAGS, [rid])
            span.set_input(input_value)
            try:
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception:
                span.set_status(Status(StatusCode.ERROR))
                raise


@contextmanager
def tool_span(
    tracer: OITracer,
    name: str,
    input_value: Any,
) -> Generator[OpenInferenceSpan, None, None]:
    with tracer.start_as_current_span(
        name,
        openinference_span_kind=OpenInferenceSpanKindValues.TOOL,
    ) as span:
        span.set_input(input_value)
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception:
            span.set_status(Status(StatusCode.ERROR))
            raise


@contextmanager
def llm_span(
    tracer: OITracer,
    name: str,
    input_value: Any,
) -> Generator[OpenInferenceSpan, None, None]:
    with tracer.start_as_current_span(
        name,
        openinference_span_kind=OpenInferenceSpanKindValues.LLM,
    ) as span:
        span.set_input(input_value)
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception:
            span.set_status(Status(StatusCode.ERROR))
            raise


tracer_provider = create_tracer(Env())
