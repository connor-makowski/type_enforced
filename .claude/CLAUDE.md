# type_enforced: Claude Instructions

## Project Purpose

`type_enforced` is a pure Python runtime type enforcer for type annotations. It has one job:
- **Enforce type hints** on function/method inputs and return values at runtime, without any special compiler or preprocessor.

It supports functions, methods, classes, dataclasses, and modules. It has zero external runtime dependencies.

---

## Directory Layout (relevant files only)

```
type_enforced/
  __init__.py        # Package exports (Enforcer, FunctionMethodEnforcer) + README as docstring
  enforcer.py        # Core: Enforcer decorator, FunctionMethodEnforcer class
  utils.py           # Utilities: Constraint, GenericConstraint, Partial, DeepMerge, WithSubclasses
test/
  test_fn_*.py       # Function/method enforcement tests (22 files)
  test_class_*.py    # Class enforcement tests (15 files)
  test_class_12_utils/ # Helper for delayed binding test
  benchmark.py       # Performance benchmarks vs pydantic, beartype, typeguard
utils/
  test.sh            # Run all test/*.py files with python
  prettify.sh        # autoflake (unused imports) + black (line-length=80)
  docs.sh            # Generate pdoc HTML docs — do NOT run unless releasing
pyproject.toml       # black config: line-length=80, target py39; project version
setup.cfg            # Version mirrored here too (both must be updated on release)
run.sh               # Docker wrapper for all dev commands
Dockerfile           # Python 3.13 by default; edit to test other versions
requirements.txt     # Dev dependencies (black, autoflake, pdoc, twine, pydantic, beartype, typeguard)
publish.sh           # PyPI publishing script
```

---

## Development Commands

All commands use Docker via `./run.sh`:

| Command | What it does |
|---|---|
| `./run.sh test` | Run all tests inside Docker |
| `./run.sh prettify` | Format with autoflake + black (line-length=80) |
| `./run.sh docs` | Regenerate pdoc documentation |
| `./run.sh` | Drop into a Docker shell |

> **Note:** `./run.sh` requires a TTY. In non-interactive contexts (CI, background tasks) it will fail with "the input device is not a TTY". Ask the user to run it themselves.

**Test runner details** (`utils/test.sh`): Runs every `.py` file in `test/` with `python`. Each file prints its own pass/fail message and exits.

**Prettify details** (`utils/prettify.sh`):
1. `autoflake` removes unused imports from `type_enforced/`
2. `black` formats `type_enforced/` and `test/` (line-length=80, py39 target)

**Docs**: **DO NOT generate docs** unless the user is doing a release. Docs are regenerated and versioned at release time only.

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

Tests are in `test/`. Each file is standalone, imports whatever it needs, runs assertions, and prints its own result.

**Naming conventions:**
- `test_fn_*.py` — tests for function/method enforcement
- `test_class_*.py` — tests for class-level enforcement
- `benchmark.py` — performance comparison (not a pass/fail test)

**Test pattern:**
```python
success = True

try:
    my_fn(valid_input)   # should pass
except:
    success = False

try:
    my_fn(invalid_input)  # should raise TypeError
    success = False
except TypeError:
    pass

print("Tests: Passed!" if success else "Tests: Failed!")
```

When adding a new feature, add a corresponding `test_fn_*.py` or `test_class_*.py` file. Tests are picked up automatically by `utils/test.sh`.

---

## Coding Conventions

- **Line length**: 80 characters (black config in `pyproject.toml`)
- **Python version**: 3.11+ (use `str | None` union syntax, not `Optional[str]`)
- **Formatting**: Always run `./run.sh prettify` before committing
- **No external dependencies**: Runtime code must stay pure Python with zero imports outside stdlib
- **No unnecessary abstractions**: Don't create shared helpers unless the same logic appears 3+ times
- **Lazy evaluation**: Type hints are parsed once and cached — keep `__get_checkable_types__` fast
- **DO NOT generate docs**: Only the maintainer generates docs at release time

---

## Release Process

1. Ensure all tests pass: `./run.sh test`
2. Prettify: `./run.sh prettify`
3. Update `version` in **both** `pyproject.toml`


Python: **≥ 3.11** | No runtime dependencies
