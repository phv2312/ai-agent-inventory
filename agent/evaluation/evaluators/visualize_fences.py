"""Extraction of module-qualified `visualize` fences."""

import re

from evaluation.models import VisualizationFence

VALID_MODULES: frozenset[str] = frozenset(
    {"chart", "diagram", "mockup", "interactive", "art"},
)

FENCE_RE = re.compile(
    r"```visualize:(chart|diagram|mockup|interactive|art)\s*\n(.*?)```",
    re.DOTALL,
)
INVALID_FENCE_RE = re.compile(r"```visualize:(\S+)")


def extract_visualization_fences(
    *,
    query_id: str,
    text: str,
) -> list[VisualizationFence]:
    """Extract valid visualization fences from assistant text."""
    fences: list[VisualizationFence] = []
    for index, match in enumerate(FENCE_RE.finditer(text), start=1):
        fences.append(
            VisualizationFence(
                query_id=query_id,
                index=index,
                module=match.group(1),
                code=match.group(2).strip(),
            ),
        )
    return fences


def invalid_visualize_modules(text: str) -> list[str]:
    """Return unknown modules mentioned in visualize fences."""
    modules: list[str] = []
    for match in INVALID_FENCE_RE.finditer(text):
        module = match.group(1).strip()
        if module not in VALID_MODULES:
            modules.append(module)
    return modules
