import pytest
import type_enforced


@type_enforced.Enforcer
def my_fn(a: int, b: int | str = 2, c: int = 3) -> None:
    return None


@type_enforced.Enforcer
def my_fn_args(a: int, *args, b: int | str = 2, c: int = 3) -> None:
    return None


@type_enforced.Enforcer
def my_fn_kwargs(a: int, b: int | str = 2, c: int = 3, **kwargs) -> None:
    return None


@type_enforced.Enforcer
def my_fn_args_kwargs(
    a: int, *args, b: int | str = 2, c: int = 3, **kwargs
) -> None:
    return None


@type_enforced.Enforcer
def my_fn_args_kwargs_arg_default(
    a: int = 5, *args, b: int | str = 2, c: int = 3
) -> None:
    return None


def test_fn_05():
    my_fn(a=1, b=2, c=3)
    my_fn_args(a=1, b=2, c=3)
    my_fn_kwargs(a=1, b=2, c=3)
    my_fn_args_kwargs(a=1, b=2, c=3)
    my_fn_args_kwargs_arg_default(b=2, c=3)

    with pytest.raises(TypeError):
        my_fn(a="a", b=2, c=3)
    with pytest.raises(TypeError):
        my_fn_args(a="a", b=2, c=3)
    with pytest.raises(TypeError):
        my_fn_kwargs(a="a", b=2, c=3)
    with pytest.raises(TypeError):
        my_fn_args_kwargs(a="a", b=2, c=3)
