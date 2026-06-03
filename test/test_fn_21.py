import type_enforced
import typing


@type_enforced.Enforcer
def my_fn(a: typing.Any, b: object) -> None:
    return None


def test_fn_21():
    my_fn(a=1, b=2)
    my_fn(a="hi", b=3.14)
