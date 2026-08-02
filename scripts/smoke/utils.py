from datetime import UTC, datetime
import json
from pathlib import Path
from urllib.parse import urlparse
from .models import SmokeCase


def require_url(url: str | None, name: str) -> str:
    if not url:
        raise ValueError(f"{name} is required")
    normalized = url.rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{name} must be an absolute HTTP(S) URL: {url}")
    return normalized


def require_pdf(pdf_path: Path) -> Path:
    resolved = pdf_path.expanduser().resolve()
    if not resolved.is_file():
        msg = f"Smoke PDF was not found: {resolved}"
        raise FileNotFoundError(msg)
    if resolved.suffix.lower() != ".pdf":
        msg = f"Smoke input must be a PDF: {resolved}"
        raise ValueError(msg)
    return resolved


def load_cases(cases_path: Path) -> tuple[SmokeCase, ...]:
    resolved = cases_path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Smoke case file was not found: {resolved}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Smoke case file is not valid JSON: {resolved}") from exc
    if not isinstance(payload, list) or not payload:
        raise ValueError("Smoke case file must contain a non-empty JSON array")

    cases = tuple(SmokeCase.from_payload(item) for item in payload)
    case_names = [case.name for case in cases]
    if len(case_names) != len(set(case_names)):
        raise ValueError("Smoke case names must be unique")
    return cases


def create_artifacts_dir(parent_dir: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    artifacts_dir = parent_dir.expanduser().resolve() / timestamp
    artifacts_dir.mkdir(parents=True, exist_ok=False)
    return artifacts_dir
