import pytest
import type_enforced


@type_enforced.Enforcer
class my_class:
    def my_fn(self, a: int, b: int | str = 2, c: int = 3) -> None:
        return None

    def my_fn_args(self, a: int, *args, b: int | str = 2, c: int = 3) -> None:
        return None

    def my_fn_kwargs(
        sellf, a: int, b: int | str = 2, c: int = 3, **kwargs
    ) -> None:
        return None

    def my_fn_args_kwargs(
        self, a: int, *args, b: int | str = 2, c: int = 3, **kwargs
    ) -> None:
        return None


obj = my_class()


def test_class_08():
    obj.my_fn(a=1, b=2, c=3)
    obj.my_fn_args(a=1, b=2, c=3)
    obj.my_fn_kwargs(a=1, b=2, c=3)
    obj.my_fn_args_kwargs(a=1, b=2, c=3)

    with pytest.raises(TypeError):
        obj.my_fn(a="a", b=2, c=3)
    with pytest.raises(TypeError):
        obj.my_fn_args(a="a", b=2, c=3)
    with pytest.raises(TypeError):
        obj.my_fn_kwargs(a="a", b=2, c=3)
    with pytest.raises(TypeError):
        obj.my_fn_args_kwargs(a="a", b=2, c=3)
