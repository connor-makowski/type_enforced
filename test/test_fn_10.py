import pytest
import type_enforced
from typing import Union


@type_enforced.Enforcer
def my_fn(a: Union[int, str], b: int | str) -> None:
    return None


def test_fn_10():
    my_fn(a=1, b=2)
    my_fn(a="a", b="b")

    with pytest.raises(TypeError, match="Type mismatch"):
        my_fn(a=1.5, b="1.5")
    with pytest.raises(TypeError, match="Type mismatch"):
        my_fn(a="1.5", b=1.5)
