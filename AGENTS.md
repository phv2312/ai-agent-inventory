# Repository Agent Instructions

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
- Avoid hard-coded literals when they represent stable behavior, protocol values, routes, filenames, environment keys, limits, or reusable defaults. Prefer named constants on the owning class or module over repeated literals.

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


## Comments and Documentation

Apply to `**/*.py` and `README.md`.

- Use short, consecutive `#` comments for implementation guidance; do not add
  docstrings for this purpose.
- Keep comments to a maximum line length of 79.
- Update README correspondingly if new features are introduced.
