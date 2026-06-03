import pytest
import type_enforced


@type_enforced.Enforcer
def my_fn(a: dict[str, dict[str, int]], b: list[set[str]]) -> None:
    return None


def test_fn_08():
    my_fn(a={"a": {"a": 1}}, b=[{"a"}])

    with pytest.raises(TypeError, match="Type mismatch"):
        my_fn(a={"a": {"a": "2"}}, b=[{"a"}])
    with pytest.raises(TypeError, match="Type mismatch"):
        my_fn(a={"a": {"a": 1}}, b=[{"a", 1}])
    with pytest.raises(TypeError, match="Type mismatch"):
        my_fn(a={"a": {1: 1}}, b=[{"a"}])
