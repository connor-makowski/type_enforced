# type_enforced

[![PyPI version](https://img.shields.io/pypi/v/type_enforced.svg?color=blue)](https://pypi.org/project/type_enforced/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://joss.theoj.org/papers/10.21105/joss.08832/status.svg)](https://doi.org/10.21105/joss.08832)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/type-enforced?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=ORANGE&left_text=Downloads)](https://pepy.tech/projects/type-enforced)

Fast, pure-Python runtime type enforcement for Python 3.11+ type annotations. Zero dependencies, near-instant validation, and uncompromising performance.

---

## Quick Start

```python
import type_enforced

@type_enforced.Enforcer
def greet(name: str, repeat: int = 1) -> str:
    return f"Hello {name}!" * repeat

greet("Alice", 2)       # Returns "Hello Alice!Hello Alice!"
greet("Alice", "twice")  # Raises TypeError at runtime!
```

---

## Why type_enforced?

Static type checkers (like `mypy` or `pyright`) catch errors during development, but offer zero protection at runtime against dynamic payloads, untyped API inputs, or user data.

Existing runtime type checkers force an unnecessary compromise:
- **Pydantic** provides thorough validation, but comes with heavy runtime overhead and steep execution slowdowns.
- **Beartype & Typeguard** achieve high speed primarily by taking shortcuts. They sample a small number of elements in collections and miss invalid items in unsampled data.

`type_enforced` eliminates this compromise:

- **Guaranteed Complete Validation**: Validates every single item across large collections and nested data structures (e.g. `list[dict[str, int]]` or dicts with 10,000+ keys) by default, with zero shortcuts.
- **2–9× Faster than Pydantic**: Delivers full, uncompromising validation at a fraction of Pydantic's overhead.
- **Fastest Sampled Mode (Up to 2× Faster than Beartype)**: Need O(1) sampling for massive collections? Set `iterable_sample_pct=0` for sampled validation that runs up to 2× faster than Beartype across all tested data structures (~0.18–0.35 µs).
- **Pure Python, Zero Dependencies**: A lightweight decorator with zero external packages, C-extensions, or compilation steps. Compatible everywhere Python 3.11+ runs.
- **Rich Type Support & Constraints**: Seamlessly supports standard Python `|` unions, nested generics, Literals, Callables, Dataclasses, custom class inheritance, and custom validation `Constraint` rules.
- **Clean Tracebacks**: Strips internal validation frames from tracebacks by default, pinpointing the exact line in your code that caused the issue.

### Performance at a Glance

Timings are averages over 100 runs. ⚠ = checker did not consistently catch invalid types for this case (see [full benchmarks](benchmark.md)).

| Type | type_enforced (100%) | type_enforced (sample) | beartype (sample) | Pydantic (100%) | Typeguard (sample) |
|:-----|:--------------------:|:----------------------:|:-----------------:|:---------------:|:------------------:|
| `int` | **0.21 µs** | **0.18 µs** | 0.27 µs | 1.37 µs | 2.43 µs |
| `Union[int, float]` | **0.19 µs** | **0.18 µs** | 0.30 µs | 1.46 µs | 5.60 µs |
| `str` | **0.18 µs** | **0.17 µs** | 0.28 µs | 1.23 µs | 2.51 µs |
| `list[int]` (1 000 items) | **12.63 µs** | **0.22 µs ⚠** | 0.42 µs ⚠ | 22.31 µs | 3.84 µs ⚠ |
| `dict[str, int]` (1 000 keys) | **27.34 µs** | **0.30 µs ⚠** | 0.43 µs ⚠ | 81.58 µs | 6.97 µs ⚠ |
| `dict[str, int]` (10 000 keys) | **270.78 µs** | **0.31 µs ⚠** | 0.44 µs ⚠ | 873.62 µs | 5.07 µs ⚠ |
| `list[dict[str, int]]` (100 x 10 items) | **60.26 µs** | **0.35 µs ⚠** | 0.55 µs ⚠ | 83.71 µs | 6.51 µs ⚠ |
| `list[dict[str, int]]` (100 x 100 items) | **320.77 µs** | **0.35 µs ⚠** | 0.59 µs ⚠ | 785.22 µs | 6.33 µs ⚠ |

> **Note:** Beartype and Typeguard's speed on complex types reflects incomplete validation — they sample rather than check all items. When full validation is required, `type_enforced` is **2–9× faster than Pydantic**. When sampled validation is desired, `type_enforced(iterable_sample_pct=0)` is **up to 2× faster than Beartype**.

---

## Installation

Install via `pip`:

```bash
pip install type_enforced
```

Or using `uv`:

```bash
uv add type_enforced
```

### Requirements
- **Python 3.11+**
- Zero external runtime dependencies

<details>
<summary>Legacy Python Compatibility</summary>

For older Python versions, pin to legacy releases:
- **Python 3.10**: `pip install "type_enforced<=1.10.2"`
- **Python 3.9**: `pip install "type_enforced<=1.9.0"`
- **Python 3.7 – 3.8**: `pip install "type_enforced==0.0.16"`
</details>

---

## Usage Guide

### 1. Functions and Methods

Apply `@type_enforced.Enforcer` to any callable. It validates positional arguments, keyword arguments, default parameters, and the return type.

```python
import type_enforced

@type_enforced.Enforcer
def process_user(user_id: int, tags: list[str], active: bool = True) -> dict[str, str | int]:
    return {"user_id": user_id, "status": "active" if active else "inactive"}

# Passing invalid types raises a descriptive TypeError:
process_user("123", ["admin"])
# TypeError: TypeEnforced Exception (process_user): Type mismatch for typed variable `user_id`.
# Expected one of the following `[<class 'int'>]` but got `<class 'str'>` with value `123` instead.
```

### 2. Classes and Dataclasses

Decorating a class automatically enforces types on all annotated methods (including `__init__`, `@classmethod`, and `@staticmethod`):

```python
import type_enforced
from dataclasses import dataclass

@type_enforced.Enforcer
class Account:
    def __init__(self, username: str, balance: float):
        self.username = username
        self.balance = balance

    def deposit(self, amount: float) -> float:
        self.balance += amount
        return self.balance

    @staticmethod
    def validate_code(code: str) -> bool:
        return len(code) == 6

# Dataclasses work seamlessly:
@type_enforced.Enforcer
@dataclass
class UserConfig:
    retries: int
    endpoint: str
```

To disable enforcement on a specific method within an enforced class:

```python
@type_enforced.Enforcer
class Worker:
    def standard_job(self, task: str) -> None:
        pass

    @type_enforced.Enforcer(enabled=False)
    def high_throughput_job(self, data):
        # Type enforcement skipped for maximum throughput
        pass
```

### 3. Module-Level Enforcement (`ModuleEnforcer`)

Enforce typing across an entire module in a single line without decorating every function and class individually:

```python
# Place at the top of your module file (e.g., my_package/core.py)
import type_enforced

type_enforced.ModuleEnforcer()

def add(a: int, b: int) -> int:
    return a + b

class Helper:
    def run(self, flag: bool) -> str:
        return "ok" if flag else "failed"
```

You can also enforce an imported module:

```python
import my_package
import type_enforced

type_enforced.ModuleEnforcer(my_package)
```

> **Note:** By default, `submodules=True`, which recursively enforces all sub-packages/sub-modules in the same namespace (e.g. `mypkg.submodule`), while safely ignoring third-party and standard library imports.

---

## Supported Type Annotations

`type_enforced` supports all standard Python 3.11+ typing constructs:

### Standard Built-ins & Unions
```python
@type_enforced.Enforcer
def fn(
    a: int,
    b: str | float,                    # Standard union syntax
    c: int | None = None,              # Optional syntax
) -> None:
    pass
```

### Collections & Nested Generics
```python
@type_enforced.Enforcer
def fn(
    items: list[int | float],
    mapping: dict[str, list[int]],      # Dicts require [KeyType, ValType]
    unique_ids: set[str],
    fixed_pair: tuple[str, int],        # Exact positional tuple: (str, int)
    var_tuple: tuple[int, ...],         # Variable-length tuple
) -> None:
    pass
```

### Custom Classes & Subclass Inheritance
By default, subclasses pass type validation (e.g. `Bar()` satisfies `Foo` if `class Bar(Foo)`):

```python
class Animal: pass
class Dog(Animal): pass
class Vehicle: pass

@type_enforced.Enforcer
def feed(animal: Animal) -> None:
    pass

feed(Animal())  # OK
feed(Dog())     # OK (subclasses allowed)
feed(Vehicle()) # Raises TypeError
```

To enforce uninitialized class objects (the class itself, rather than an instance), use `typing.Type`:

```python
import typing

@type_enforced.Enforcer
def make_instance(cls: typing.Type[Animal]) -> Animal:
    return cls()
```

### Literals & Special Types
```python
from typing import Literal, Callable, Sized, Any

@type_enforced.Enforcer
def fn(
    mode: Literal["read", "write"],        # Value check: must equal "read" or "write"
    handler: Callable,                     # Functions, methods, generators
    container: Sized,                      # list, dict, set, str, tuple, bytes, etc.
    wildcard: Any,                         # Permissive bypass
) -> None:
    pass
```

- **Stacking Literals**: Literals combine with unions using OR logic (`int | Literal['auto']` allows any `int` or the literal string `'auto'`).

---

## Value Validation with Constraints

`type_enforced` allows post-type-check value constraints directly in type annotations.

### Built-in `Constraint`
Validate bounds, numeric comparisons, string patterns (regex), and inclusion/exclusion:

```python
import type_enforced
from type_enforced.utils import Constraint

@type_enforced.Enforcer
def set_score(
    score: int | Constraint(ge=0, le=100),
    code: str | Constraint(pattern=r"^[A-Z]{3}-\d{4}$"),
) -> bool:
    return True

set_score(85, "ABC-1234")    # Passes
set_score(105, "ABC-1234")   # Raises TypeError (Constraint `Less Than Or Equal To (100)` not met)
set_score(85, "invalid")     # Raises TypeError (Constraint `Regex Pattern Match` not met)
```

Available `Constraint` parameters:
- `gt`, `lt`, `ge`, `le`, `eq`, `ne` (numeric / comparison bounds)
- `pattern` (regular expression string match)
- `includes`, `excludes` (membership checks)

### Custom `GenericConstraint`
Write arbitrary validation logic using custom predicates:

```python
import type_enforced
from type_enforced.utils import GenericConstraint

RGBColor = str | GenericConstraint({
    "valid_hex_color": lambda c: c.startswith("#") and len(c) in (4, 7)
})

@type_enforced.Enforcer
def render(color: RGBColor) -> None:
    pass

render("#ffffff")  # Passes
render("red")      # Raises TypeError (Constraint `valid_hex_color` not met)
```

> **Note:** Constraints are evaluated *after* type checking. Constraints stack with unions: `int | Constraint(ge=0) | Constraint(le=10)`.

---

## Configuration Reference

Both `@Enforcer` and `ModuleEnforcer` accept the following configuration arguments:

| Parameter | Type | Default | Description |
|:---|:---:|:---:|:---|
| `enabled` | `bool` | `True` | Toggle enforcement. Set `False` to bypass type checks (useful for production vs. debugging or per-method overrides). |
| `strict` | `bool` | `True` | When `True`, raises `TypeError` on mismatch. When `False`, logs a warning to the console instead of raising. |
| `clean_traceback` | `bool` | `True` | Filters internal `type_enforced` stack frames so tracebacks point directly to user code. |
| `iterable_sample_pct` | `int` | `100` | Percentage (0–100) of iterable items to validate. `100` validates all elements. `0` validates only the first element in O(1) time. |
| `only_typed` | `bool` | `False` | When `True`, raises an exception upon decoration if any parameter or return value lacks a type hint. |
| `submodules` *(ModuleEnforcer only)* | `bool` | `True` | Recursively enforces all sub-packages/sub-modules in the same namespace. |

### Configuration Options in Depth

#### 1. Strict Typing Mode (`only_typed=True`)
To catch unannotated parameters or missing return annotations across your codebase, enable `only_typed=True`. This raises a `TypeError` at definition time if any parameter (excluding `self`/`cls`) or the return type lacks an annotation:

```python
import type_enforced

@type_enforced.Enforcer(only_typed=True)
def calculate(a: int, b: int) -> int:
    return a + b

# Missing annotation on parameter `b` or missing return annotation raises immediately:
@type_enforced.Enforcer(only_typed=True)
def invalid_fn(a: int, b):
    return a
# TypeError: TypeEnforced Exception (invalid_fn): Untyped variable `b` found in function/method `invalid_fn`.
```

#### 2. Warning Mode (`strict=False`)
Print warnings to the console instead of raising exceptions (useful for gradual adoption or debugging without breaking execution):

```python
@type_enforced.Enforcer(strict=False)
def lenient_fn(x: int) -> int:
    return x

lenient_fn("not_an_int")
# Logs: TypeEnforced Warning (lenient_fn): Type mismatch for typed variable `x`...
# Returns "not_an_int" without raising an exception.
```

#### 3. Sampled Validation (`iterable_sample_pct=0`)
For massive collections where full validation overhead is unacceptable, check only the first item in O(1) time (runs up to 2× faster than Beartype):

```python
@type_enforced.Enforcer(iterable_sample_pct=0)
def fast_check(items: list[int]) -> int:
    return len(items)

fast_check([1, 2, 3])           # OK
fast_check(["bad_first", 2, 3])  # Raises TypeError
```

---

## Contributing

Contributions are welcome!

### Development Setup

We use [uv](https://docs.astral.sh/uv/) for dependency management and testing in a Unix-based environment (Linux, macOS, or WSL2 on Windows).

```bash
# Clone the repository
git clone https://github.com/connor-makowski/type_enforced.git
cd type_enforced

# Install dev dependencies
uv sync --extra dev
```

### Development Commands

| Command | Description |
|:---|:---|
| `uv run pytest` | Run tests in local environment |
| `uv run pytest -v` | Run tests with verbose output |
| `uv run nox` | Run test suite across Python 3.11, 3.12, 3.13, 3.14 |
| `uv run nox -s tests-3.14` | Run test suite on a specific Python version |
| `uv run python utils/prettify.py` | Auto-format with `autoflake` and `black` (80 col) |

### Guidelines
1. Fork the repo and create your branch from `main`.
2. Ensure all tests pass across versions (`uv run nox`).
3. Format code before committing (`uv run python utils/prettify.py`).
4. Keep commits atomic and clearly described.
5. Submit a pull request.

---

## Academic Citation

If you use `type_enforced` in academic research, please cite our [JOSS paper](https://doi.org/10.21105/joss.08832):

```bibtex
@article{Makowski2026,
  doi = {10.21105/joss.08832},
  url = {https://doi.org/10.21105/joss.08832},
  year = {2026},
  publisher = {The Open Journal},
  volume = {11},
  number = {118},
  pages = {8832},
  author = {Connor Makowski},
  title = {type_enforced: A pure Python runtime type enforcer},
  journal = {Journal of Open Source Software}
}
```

---

## License

Distributed under the [MIT License](https://opensource.org/licenses/MIT). See `LICENSE` for details.