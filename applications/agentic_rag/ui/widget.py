"""Widget streaming helpers and iframe HTML for inline visualizations."""

import html
from pathlib import Path


SVG_STYLES_PATH = Path(__file__).parent.parent / "assets" / "svg-styles.css"

CHAT_EMBED_BG = "#ffffff"

WIDGET_LIGHT_CHAT_OVERRIDES = f"""
html {{ color-scheme: light; }}
html, body {{ background-color: {CHAT_EMBED_BG} !important; }}
:root {{
  --p: #0f172a;
  --s: #475569;
  --t: #64748b;
  --bg2: #e2e8f0;
  --b: #94a3b8;
  --color-text-primary: #0f172a;
  --color-text-secondary: #475569;
  --color-text-tertiary: #64748b;
  --color-text-info: #1d4ed8;
  --color-text-danger: #b91c1c;
  --color-text-success: #15803d;
  --color-text-warning: #b45309;
  --color-background-primary: {CHAT_EMBED_BG};
  --color-background-secondary: #f1f5f9;
  --color-background-tertiary: #e2e8f0;
  --color-background-info: #dbeafe;
  --color-background-danger: #fee2e2;
  --color-background-success: #dcfce7;
  --color-background-warning: #fef3c7;
  --color-border-primary: rgba(15, 23, 42, 0.22);
  --color-border-secondary: rgba(15, 23, 42, 0.14);
  --color-border-tertiary: rgba(15, 23, 42, 0.1);
  --color-border-info: #3b82f6;
  --color-border-danger: #ef4444;
  --color-border-success: #22c55e;
  --color-border-warning: #f59e0b;
}}
input[type="text"]:focus,
input[type="number"]:focus,
textarea:focus,
select:focus {{
  box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.08) !important;
}}
"""


def _load_svg_widget_styles() -> str:
    return SVG_STYLES_PATH.read_text(encoding="utf-8")


def _widget_iframe_head() -> str:
    styles = _load_svg_widget_styles()
    return (
        '<meta charset="UTF-8"/>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>'
        f'<style id="kn-svg-widget-styles">{styles}</style>'
        f'<style id="kn-widget-chat-surface">'
        f"{WIDGET_LIGHT_CHAT_OVERRIDES}</style>"
    )


def _body_style_attr() -> str:
    return (
        f"margin:0;padding:10px;box-sizing:border-box;"
        f"background:{CHAT_EMBED_BG};"
        f"color:var(--color-text-primary);"
        f"font-family:var(--font-sans);min-height:100%"
    )


def build_widget_html(
    widget_code: str,
    *,
    title: str | None = None,
) -> str:
    """Build a full HTML document.

    Mirrors InlineVisualizationFrame.buildSrcDoc.
    """
    head = _widget_iframe_head()
    if title:
        head = f"<title>{html.escape(title.strip())}</title>{head}"
    return (
        f'<!DOCTYPE html><html lang="en"><head>{head}</head>'
        f'<body style="{_body_style_attr()}">{widget_code}</body></html>'
    )


def render_widget_iframe(
    widget_code: str,
    *,
    title: str | None = None,
) -> str:
    """Return an iframe + fullscreen overlay HTML string for gr.HTML."""
    if not widget_code.strip():
        return ""
    srcdoc = build_widget_html(widget_code, title=title)
    escaped = html.escape(srcdoc, quote=True)
    safe_title = html.escape(title.strip()) if title else "Visualization"
    title_str = html.escape(title.strip()) if title and title.strip() else ""

    header = (
        f'<div class="kn-widget-header">'
        f'<span class="kn-widget-title">{title_str}</span>'
        f'<button id="kn-fs-btn" class="kn-fs-btn" title="Fullscreen">'
        f"&#x26F6;"
        f"</button>"
        f"</div>"
    )
    iframe = (
        f'<iframe title="{safe_title}" '
        f'srcdoc="{escaped}" '
        f'class="kn-widget-iframe" '
        f'sandbox="allow-scripts"></iframe>'
    )
    overlay = (
        f'<div id="kn-fs-overlay" class="kn-fs-overlay">'
        f'<div class="kn-fs-box">'
        f'<div class="kn-fs-topbar">'
        f'<span class="kn-fs-title">{title_str}</span>'
        f'<button id="kn-fs-close" class="kn-fs-close" '
        f'title="Close">&#x2715;</button>'
        f"</div>"
        f'<iframe id="kn-fs-iframe" title="{safe_title}" '
        f'srcdoc="{escaped}" '
        f'class="kn-fs-iframe" '
        f'sandbox="allow-scripts"></iframe>'
        f"</div>"
        f"</div>"
    )
    return f"{header}{iframe}{overlay}"
