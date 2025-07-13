## Pre-commit & Continuous Integration

There are two tools that contributors must satisfy before committing to the repository:

| Tool | Purpose | Reason |
|:-----|:--------|:-------|
| mypy | Static type checking | - Serves as a substitute for unit tests during the early stages of the project. <br> - Improves code quality and increases confidence in code correctness from the start. |
| ruff | Linting & code style checking | - Extremely fast compared to other linters. <br> - Supports a wide range of linting rules. |

These checks are enforced on every commit to the *main* branch or any pull request targeting *main*, and are supported by GitHub Actions.
