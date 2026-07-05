"""Standalone HTML shell for exported visualization artifacts."""

import re
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
KN_RUNTIME_BUNDLE_PATH = REPO_ROOT / "frontend/src/assets/kn-runtime.iife.js"
SVG_WIDGET_STYLES_PATH = REPO_ROOT / "frontend/src/assets/svg-styles.css"
CHAT_EMBED_BG = "#1a1a1a"

_WIDGET_DARK_OVERRIDES = f"""
html {{ color-scheme: dark; }}
html, body {{
  background-color: {CHAT_EMBED_BG} !important;
  overflow-x: auto;
  overflow-y: visible;
}}
"""

_BODY_STYLE = (
    "margin:0;padding:0;box-sizing:border-box;"
    f"background:{CHAT_EMBED_BG};"
    "color:var(--color-text-primary);"
    "font-family:system-ui,sans-serif;min-height:min-content"
)


@lru_cache(maxsize=1)
def load_kn_runtime_bundle() -> str:
    """Return the inline KN runtime bundle used by the chat iframe."""
    if not KN_RUNTIME_BUNDLE_PATH.is_file():
        msg = f"KN runtime bundle not found: {KN_RUNTIME_BUNDLE_PATH}"
        raise FileNotFoundError(msg)
    return KN_RUNTIME_BUNDLE_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def load_svg_widget_styles() -> str:
    """Return SVG widget styles shared with the chat iframe."""
    if not SVG_WIDGET_STYLES_PATH.is_file():
        msg = f"SVG widget styles not found: {SVG_WIDGET_STYLES_PATH}"
        raise FileNotFoundError(msg)
    return SVG_WIDGET_STYLES_PATH.read_text(encoding="utf-8")


def wrap_visualization_html(widget_code: str) -> str:
    """Wrap widget fragment HTML in the same runtime shell as the frontend."""
    runtime_bundle = load_kn_runtime_bundle().strip()
    svg_styles = load_svg_widget_styles()
    runtime_script = f"<script>{runtime_bundle}</script>" if runtime_bundle else ""
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="UTF-8"/>\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>\n'
        f'<style id="kn-svg-widget-styles">{svg_styles}</style>\n'
        f'<style id="kn-widget-chat-surface">{_WIDGET_DARK_OVERRIDES}</style>\n'
        f"{runtime_script}\n"
        "</head>\n"
        f'<body style="{_BODY_STYLE}">\n'
        f'<div id="kn-root">{widget_code}</div>\n'
        "</body>\n"
        "</html>\n"
    )


def extract_widget_code_from_artifact(html: str) -> str:
    """Extract the widget fragment from a stored artifact HTML file."""
    kn_root_match = re.search(
        r'<div id="kn-root">(.*?)</div>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if kn_root_match:
        return kn_root_match.group(1).strip()

    body_match = re.search(
        r"<body[^>]*>(.*?)</body>",
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if body_match:
        return body_match.group(1).strip()

    msg = "Could not extract widget code from visualization artifact HTML"
    raise ValueError(msg)


def rewrap_artifacts_in_dir(artifacts_dir: Path) -> int:
    """Re-wrap existing artifact HTML files with the current runtime shell."""
    count = 0
    for path in sorted(artifacts_dir.glob("*.html")):
        widget_code = extract_widget_code_from_artifact(
            path.read_text(encoding="utf-8"),
        )
        path.write_text(
            wrap_visualization_html(widget_code),
            encoding="utf-8",
        )
        count += 1
    return count
