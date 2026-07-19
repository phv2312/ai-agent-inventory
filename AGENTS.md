# Repository Agent Instructions

## Current Spec Context

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan at
`specs/013-evaluation-dataset/plan.md`.
<!-- SPECKIT END -->

## General Python Practices

Apply to `**/*.py`.

- Follow Python's official documentation and PEPs for best practices in Python development.
- Write simple and clear code; avoid unnecessary complexity.
- Prefer list comprehensions for creating lists when appropriate.
- Use try-except blocks to handle exceptions gracefully.
- Limit the use of global variables to reduce side effects.
- Prefer `pathlib` to `os.path`.
- Do not use `getattr`; prefer explicit attributes, typed fields, or direct access.
- Do not add `from __future__ import annotations` unless required, for example recursive types that cannot use quoted forward refs. Quoted forward references such as `"ClassA"` are fine.

## Advanced Python Practices

Apply to `**/*.py`.

- Always use guard clauses and fail fast.
- Use type hints for clarity and type checking; follow mypy best practices.
- Keep code style consistent using Ruff.
- Use Python 3.12+ syntax, especially `type` aliases, generic syntax, and paramspec `**P` syntax where appropriate.
- Clearly separate behavioral classes from data classes.
- Use `pydantic.BaseModel` for data classes that need validation and serialization.
- Use `dataclasses.dataclass` or `pydantic.dataclasses.dataclass` for simpler data classes.
- Use the Receive an Object, Return an Object (RORO) pattern.
- For intermediate dictionary variables, use names shaped like `mp_<keytype>_<valuetype>`.
- Prioritize OOP over functional programming.
- For Ruff FBT001, boolean-typed arguments must be keyword-only in function definitions.
- For `StrEnum`, prefer upper-case member names over lower-case.

## SOLID Design

Apply to `**/*.py`.

- Follow SOLID principles when designing classes and modules.
- Define interfaces with `typing.Protocol` or `abc.ABC` when multiple implementations or dependency injection is needed.
- Avoid deep inheritance hierarchies with more than two levels; they are hard to read and maintain.
- Prefer composition over inheritance; inject behavior via attributes or protocols instead of subclassing.
- Reserve inheritance for genuine "is-a" relationships; use composition for "has-a" or shared behavior.

## Modular Design

Apply globally.

- Use modular design with distinct files for models, services, controllers, and utilities.
- For separated modules, handle exceptions using a dedicated set of module exceptions, fine-grained to each case.

## Documentation

Apply to `**/*.py` and `README.md`.

- Use docstrings to document functions and classes.
- Keep docstrings to a maximum line length of 79.
- Update README correspondingly if new features are introduced.

## Unit Testing

Apply to `**/tests/**/*`.

- Implement unit tests to ensure code reliability.
- Parametrize tests using `pytest.mark.parametrize` to handle as many cases as possible.
- Follow all Ruff standards when writing unit tests.
- Always use tuple syntax for the variable list of `pytest.mark.parametrize`.
- Use `pytest.mark.asyncio` for async functions.
- Use fixtures to mock third-party dependencies; use autospec whenever possible.
- Use only pytest and pytest plugins. Do not use the `unittest` module.
- All tests should have typing annotations.
- All tests should live in `./tests`.
- Create all necessary files and folders under `./tests`.
- If creating files inside `./tests` or `./src/goob_ai`, add an `__init__.py` if one does not exist.
- All tests should be fully annotated and contain docstrings.
- Import the following under `if TYPE_CHECKING` when needed:

```python
from _pytest.capture import CaptureFixture
from _pytest.fixtures import FixtureRequest
from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch
from pytest_mock.plugin import MockerFixture
```
