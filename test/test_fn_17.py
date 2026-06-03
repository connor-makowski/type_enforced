import type_enforced


@type_enforced.Enforcer
def my_fn(x: list[str | int] | list[list[int]]) -> None:
    pass


@type_enforced.Enforcer
def inv_my_fn(x: list[int] | list[str] | list[list[int]]) -> None:
    pass


def test_fn_17():
    my_fn([1, 2, 3])
    my_fn(["a", "b", "c"])
    my_fn([[1, 2], [3, 4]])

    inv_my_fn([1, 2, 3])
    inv_my_fn(["a", "b", "c"])
    inv_my_fn([[1, 2], [3, 4]])
