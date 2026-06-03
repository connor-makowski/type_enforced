# type_enforced — Developer Guide

## Project Purpose

`type_enforced` is a pure Python runtime type enforcer for type annotations. It has one job:
- **Enforce type hints** on function/method inputs and return values at runtime, without any special compiler or preprocessor.

It supports functions, methods, classes, dataclasses, and modules. It has zero external runtime dependencies.

---

> **IMPORTANT — DO NOT RUN A RELEASE CYCLE.** Do not bump versions, generate docs, build distributions, or publish to PyPI. Release steps are owner-only. If you think a release is needed, flag it and stop.

---

## Directory Layout (relevant files only)

```
type_enforced/
  __init__.py        # Package exports (Enforcer, FunctionMethodEnforcer) + README as docstring
  enforcer.py        # Core: Enforcer decorator, FunctionMethodEnforcer class
  utils.py           # Utilities: Constraint, GenericConstraint, Partial, DeepMerge, WithSubclasses
test/
  test_fn_*.py       # Function/method enforcement tests (23 files)
  test_class_*.py    # Class enforcement tests (15 files)
  test_class_12_utils/ # Helper for delayed binding test
utils/
  benchmark.py       # Performance benchmarks vs pydantic, beartype, typeguard
  prettify.py        # autoflake (unused imports) + black (line-length=80)
  docs.py            # Generate pdoc HTML docs — DO NOT RUN (release only)
noxfile.py           # nox sessions: runs pytest across Python 3.11–3.14
pyproject.toml       # project metadata, black + pytest config, dependencies
setup.cfg            # version mirrored here (both must match pyproject.toml on release)
publish.sh           # PyPI publishing script — DO NOT RUN
```

---

## Development Commands

| Command | What it does |
|---|---|
| `uv run nox` | Run tests across Python 3.11, 3.12, 3.13, 3.14 |
| `uv run nox -s tests-3.14` | Run tests on a single Python version |
| `uv run pytest` | Run tests in the local venv only |
| `uv run pytest -v` | Run tests with verbose output |
| `uv run python utils/prettify.py` | Format with autoflake + black |
| `uv run python utils/benchmark.py` | Run performance benchmarks |

Dev dependencies are declared in `[project.optional-dependencies] dev` in `pyproject.toml`. Install them with `uv sync --extra dev`.

**Docs**: **DO NOT generate docs** unless you are the maintainer doing a release. Docs are regenerated and versioned at release time only.

---

## Core Architecture

### Key Files

**`enforcer.py`** — the heart of the library:
- `Enforcer` — public decorator (wrapped with `Partial` to allow `@Enforcer` or `@Enforcer()`). When applied to a class, recursively wraps all annotated methods. When applied to a function/method, returns a `FunctionMethodEnforcer`.
- `FunctionMethodEnforcer` — wraps a single callable. Lazily parses type hints on first call, validates all annotated inputs and the return value.

**`utils.py`** — supporting utilities:
- `Partial` — enables decorators to be called with or without parentheses
- `DeepMerge` — recursively merges dicts; used to unify union types into one validation dict
- `GenericConstraint` — creates a constraint validator from a dict of `name → lambda` pairs
- `Constraint` — pre-built constraint with `gt`, `lt`, `ge`, `le`, `eq`, `ne`, `includes`, `excludes`, `pattern`
- `WithSubclasses` — legacy no-op (subclass checking is now default; scheduled for removal)

### Enforcer Parameters

```python
@type_enforced.Enforcer(enabled=True, strict=True, clean_traceback=True)
```

- `enabled` (True): Set `False` to disable a specific function/method/class. Method-level takes precedence over class-level.
- `strict` (True): Set `False` to warn instead of raise on type mismatch.
- `clean_traceback` (True): Strips type_enforced internal frames from tracebacks.

### How Type Checking Works

1. **Lazy parse**: Type hints are parsed into a nested dict on first call, then cached.
2. **Build assignment dict**: Merge positional args, kwargs, and defaults into one dict keyed by parameter name.
3. **Validate each annotated parameter**: Recursively check type against expected types dict.
4. **Validate return value** if `-> ReturnType` is annotated.

**Internal type representation:**
```
int | str        → {int: None, str: None}
list[str]        → {list: {str: None}}
dict[str, int]   → {dict: ({str: None}, {int: None})}
```

**Subclass checking**: By default, subclass instances pass type checks (e.g. `Bar()` passes `Foo` if `Bar(Foo)`). Uninitialized class objects are not checked for subclasses.

**Constraints**: Evaluated AFTER type checking, independently. `str | Constraint(ge=0)` always fails — if a string is passed, the constraint fails; if an int is passed, the type check fails.

**Literals**: Evaluated at the same time as type checks (OR logic). `int | Literal['a']` accepts any int or the value `'a'`.


---

## Supported Type Annotations

- All Python built-ins: `int`, `str`, `float`, `bool`, `list`, `dict`, `tuple`, `set`, etc.
- Custom class instances (and subclasses thereof)
- `typing.Type[ClassName]` for uninitialized class objects
- Union: `int | str`, `typing.Union[int, str]`, `typing.Optional[str]`
- Nested generics: `list[int]`, `dict[str, int]`, `set[str]`, `tuple[int, str]`
- Variable-length tuples: `tuple[int, ...]`
- Deeply nested: `dict[str, list[int]]`, `list[set[str]]`
- `typing.Literal['a', 'b']` — value equality check, stackable
- `typing.Callable` — accepts functions, methods, generators
- `typing.Sized` — accepts list, tuple, dict, set, str, bytes, bytearray, memoryview, range (no nested type)
- `typing.Any` — accepts anything
- `Constraint(ge=0, ...)` and `GenericConstraint({...})` — post-type-check value validation
- `from __future__ import annotations` — string annotation style is supported

**Not supported:**
- `tuple[int, str] | tuple[str, int]` (union of two tuples)
- `Sized[int]` (nested type inside Sized)

---

## Test Structure

Tests use pytest, collected by nox across Python 3.11–3.14. All files matching `*.py` in `test/`.

**Naming conventions:**
- `test_fn_*.py` — tests for function/method enforcement
- `test_class_*.py` — tests for class-level enforcement
- `utils/benchmark.py` — performance comparison (not a pass/fail test)

**Test pattern:**
```python
import pytest
import type_enforced

@type_enforced.Enforcer
def my_fn(a: int) -> None:
    pass

def test_my_fn():
    my_fn(1)                          # valid input — no exception expected

    with pytest.raises(TypeError):
        my_fn("a")                    # invalid input — TypeError expected

    with pytest.raises(TypeError, match="Type mismatch"):
        my_fn(1.5)                    # check message when it matters
```

When adding a new feature, add a corresponding `test_fn_*.py` or `test_class_*.py` file. Tests are picked up automatically by pytest.

---

## Coding Conventions

- **Line length**: 80 characters (black config in `pyproject.toml`)
- **Python version**: 3.11+ (use `str | None` union syntax, not `Optional[str]`)
- **Formatting**: Always run `uv run python utils/prettify.py` before committing
- **No external dependencies**: Runtime code must stay pure Python with zero imports outside stdlib
- **No unnecessary abstractions**: Don't create shared helpers unless the same logic appears 3+ times
- **Lazy evaluation**: Type hints are parsed once and cached — keep `__get_checkable_types__` fast
- **DO NOT generate docs**: Only the maintainer generates docs at release time

---

## Release Checklist (owner only — do not execute)

1. Bump `version` in `pyproject.toml` and `setup.cfg` (must match)
2. Run `uv run python utils/prettify.py`
3. Run `uv run nox` — all sessions must pass
4. Run `uv run python utils/docs.py` to regenerate docs
5. Publish via `publish.sh`

---

Python: **≥ 3.11** | No runtime dependencies
