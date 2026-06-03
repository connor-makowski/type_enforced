import pytest
import type_enforced
from typing import Literal


@type_enforced.Enforcer
def my_fn(a: int | Literal["a"] | Literal["b"]):
    pass


def my_fn_2(a: int | str | Literal["a", "b"]):
    pass


def test_fn_13():
    my_fn(a="a")
    my_fn(a="b")
    my_fn(a=1)
    my_fn_2(a="a")
    my_fn_2(a="b")
    my_fn_2(a=1)
    # str type passes even if the Literal fails
    my_fn_2(a="c")

    with pytest.raises(Exception):
        my_fn(a="c")
