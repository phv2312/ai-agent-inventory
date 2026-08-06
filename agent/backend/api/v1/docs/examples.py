from pathlib import Path
from typing import Any

ASSETS_DIR = Path(__file__).parent / "assets"


def load_text(relative: str) -> str:
    return (ASSETS_DIR / relative).read_text(encoding="utf-8")


def load_json_example(relative: str) -> dict[str, Any]:
    import json

    return json.loads((ASSETS_DIR / relative).read_text(encoding="utf-8"))
