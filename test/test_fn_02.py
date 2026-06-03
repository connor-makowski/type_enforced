import pytest
import type_enforced


@type_enforced.Enforcer
def my_fn(a: int, b: int | str = 2, c: int = 3) -> None:
    return 1


def test_fn_02():
    with pytest.raises(TypeError, match="Type mismatch"):
        my_fn(a=1, b=2, c=3)
