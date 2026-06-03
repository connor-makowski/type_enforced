import pytest
import type_enforced


@type_enforced.Enforcer
def my_fn(
    a: list[str],
    b: dict[str, int],
    c: tuple[int, float],
    d: set[str],
    e: tuple[int | float, ...] = (1.0, 2, 3),
) -> None:
    return None


def test_fn_07():
    my_fn(a=["a"], b={"a": 1}, c=(1, 1.5), d={"a"})

    with pytest.raises(TypeError, match="Type mismatch"):
        my_fn(a=[1], b={"a": 1}, c=(1, 1.5), d={"a"})
    with pytest.raises(TypeError, match="Type mismatch"):
        my_fn(a=["a"], b={"a": "a"}, c=(1, 1.5), d={"a"})
    with pytest.raises(TypeError, match="Type mismatch"):
        my_fn(a=["a"], b={"a": 1}, c=(1, "1.5"), d={"a"})
    with pytest.raises(TypeError, match="Type mismatch"):
        my_fn(a=["a"], b={"a": 1}, c=(1, 1.5), d={"a", "b"}, e=("a", "b", "c"))
