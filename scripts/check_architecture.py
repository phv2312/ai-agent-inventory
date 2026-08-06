import ast
from pathlib import Path


ROOT_DIRECTORY = Path(__file__).parents[1]
CORE_DIRECTORY = ROOT_DIRECTORY / "agent" / "core"
BACKEND_PACKAGE = "agent.backend"


def main() -> None:
    violations: list[str] = []

    for filepath in CORE_DIRECTORY.rglob("*.py"):
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules = [node.module]
            else:
                continue

            for module in imported_modules:
                if module == BACKEND_PACKAGE or module.startswith(
                    f"{BACKEND_PACKAGE}."
                ):
                    violations.append(f"{filepath}:{node.lineno}: {module}")

    if violations:
        details = "\n".join(violations)
        raise SystemExit(f"Core must not import backend:\n{details}")


if __name__ == "__main__":
    main()
