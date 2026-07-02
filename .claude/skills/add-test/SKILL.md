---
name: add-test
description: Add or extend a test for type_enforced. Use when asked to write a test, add test coverage, or verify new type_enforced behavior.
---

# Adding a Test

Tests use pytest, run via nox across Python 3.11–3.14. `testpaths = ["test"]`
and `python_files = ["*.py"]` in `pyproject.toml`, so **every** `.py` file
under `test/` is collected.

**Convention**: files are named `test_fn_NN.py` for function/method
enforcement tests and `test_class_NN.py` for class enforcement tests, where
`NN` is a zero-padded two-digit number. Extend an existing numbered file if
the new case fits its topic; otherwise add the next number in the
appropriate series (`test_fn_*` vs `test_class_*`).

**Pattern:**

```python
import pytest
import type_enforced


@type_enforced.Enforcer
def my_fn(a: int, b: int | str, c: int) -> None:
    return None


def test_fn_01():
    my_fn(a=1, b=2, c=3)                  # valid input — no exception expected
    my_fn(a=1, b="2", c=3)

    with pytest.raises(TypeError, match="Type mismatch"):
        my_fn(a="a", b=2, c=3)            # invalid input — TypeError expected
```

Use `pytest.raises(TypeError)` for expected validation failures — only add
`match=` when the message content matters for the assertion.

After adding a test, run it with the [test](../test/SKILL.md) skill.
