from pathlib import Path


def load_instructions() -> str:
    """Load the repository-owned Lavish guidance for the agent prompt."""
    path = Path(__file__).with_name("lavish") / "SKILL.md"
    return path.read_text(encoding="utf-8")
