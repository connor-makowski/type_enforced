---
name: test
description: Run the type_enforced test suite via nox (all supported Python versions) or pytest (local venv). Use when asked to run tests, verify changes, or check CI-equivalent behavior.
---

# Running Tests

| Command | What it does |
|---|---|
| `uv run nox` | Run tests across Python 3.11, 3.12, 3.13, 3.14 |
| `uv run nox -s tests-3.14` | Run tests on a single Python version |
| `uv run pytest` | Run tests in the local venv only |
| `uv run pytest -v` | Run tests with verbose output |

Dev dependencies (pytest, autoflake, black, build, nox, nox-uv, pdoc, twine,
plus pydantic/beartype/typeguard for benchmarking) live in
`[project.optional-dependencies] dev` in `pyproject.toml`. Install them with
`uv sync --extra dev`.

Prefer `uv run pytest` for a quick local check while iterating; use
`uv run nox` before considering a change done, since it confirms behavior
across every Python version the package supports.
