import pytest
import type_enforced


@type_enforced.Enforcer
def my_fn(a: int, b: int | str, c: int) -> None:
    return None


def test_fn_01():
    my_fn(a=1, b=2, c=3)
    my_fn(a=1, b="2", c=3)
    with pytest.raises(TypeError, match="Type mismatch"):
        my_fn(a="a", b=2, c=3)
