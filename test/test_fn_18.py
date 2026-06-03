import type_enforced
from typing import Literal


@type_enforced.Enforcer
def my_fn(a: Literal["bar"] | int) -> None:
    pass


def test_fn_18():
    my_fn("bar")
    my_fn(1)
