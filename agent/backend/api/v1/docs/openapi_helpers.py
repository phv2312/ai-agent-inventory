from typing import Any


def sse_example(asset_text: str) -> dict[str, Any]:
    return {
        "text/event-stream": {
            "example": asset_text,
        }
    }
