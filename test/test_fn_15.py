import pytest
import type_enforced


@type_enforced.Enforcer()
def my_fn(a: int):
    return None


@type_enforced.Enforcer(enabled=False)
def my_fn2(a: int):
    return None


def test_fn_15():
    my_fn(a=1)
    my_fn2(a=1)
    my_fn2(a="1")

    with pytest.raises(TypeError):
        my_fn(a="1")
