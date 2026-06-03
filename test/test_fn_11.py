import pytest
import type_enforced
from typing import Optional


@type_enforced.Enforcer
def my_fn(a: Optional[str] = None) -> None:
    return None


def test_fn_11():
    my_fn(a="a")
    my_fn()

    with pytest.raises(TypeError, match="Type mismatch"):
        my_fn(a=1)
