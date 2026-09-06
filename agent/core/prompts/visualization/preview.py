from html import escape
from pathlib import Path

ASSETS = Path(__file__).parent / "assets"
CHART_JS_URL = "https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js"
MERMAID_URL = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"


def render_preview(fragment: str, *, title: str = "Visualization preview") -> str:
    css = (ASSETS / "lavish.css").read_text(encoding="utf-8")
    bootstrap = (ASSETS / "preview-bootstrap.js").read_text(encoding="utf-8")
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>{css}</style>
<script src="{CHART_JS_URL}"></script>
<script src="{MERMAID_URL}"></script>
<script>{bootstrap}</script>
</head>
<body><main>{fragment}</main></body>
</html>
'''


def export_preview(
    fragment: str, output: Path, *, title: str = "Visualization preview"
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_preview(fragment, title=title), encoding="utf-8")
    return output
