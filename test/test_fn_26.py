import pytest
import type_enforced


@type_enforced.Enforcer
def fn_mixed_3(a, b: int, c: str) -> str:
    return f"{a}:{b}:{c}"


@type_enforced.Enforcer
def fn_mixed_4(a: int, b, c: str, d=None) -> str:
    return f"{a}:{b}:{c}:{d}"


@type_enforced.Enforcer
def fn_mixed_5(a: int, b: str, c, d: float, e: bool) -> str:
    return f"{a}:{b}:{c}:{d}:{e}"


@type_enforced.Enforcer
def fn_mixed_6(a: int, b: str, c, d: float, e: bool, f: int) -> int:
    return a + f


@type_enforced.Enforcer
def fn_set(s: set[str]) -> int:
    return len(s)


@type_enforced.Enforcer
def fn_var_tuple(t: tuple[int, ...]) -> int:
    return sum(t)


@type_enforced.Enforcer
def fn_list_of_list(ll: list[list[int]]) -> int:
    return sum(sum(sub) for sub in ll)


@type_enforced.Enforcer
def fn_dict_of_list(d: dict[str, list[int]]) -> int:
    return sum(sum(v) for v in d.values())


def test_fn_26_mixed_args():
    assert fn_mixed_3([1, 2], 42, "hello") == "[1, 2]:42:hello"
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_mixed_3([1, 2], "bad", "hello")
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_mixed_3([1, 2], 42, 123)

    assert fn_mixed_4(1, {"any": "thing"}, "ok") == "1:{'any': 'thing'}:ok:None"
    assert fn_mixed_4(1, None, "ok", d="custom") == "1:None:ok:custom"
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_mixed_4("bad", None, "ok")

    assert fn_mixed_5(1, "two", None, 3.0, True) == "1:two:None:3.0:True"
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_mixed_5(1, "two", None, "bad", True)

    assert fn_mixed_6(1, "two", None, 3.0, True, 10) == 11
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_mixed_6(1, "two", None, 3.0, True, "bad")


def test_fn_26_standalone_containers():
    assert fn_set({"x", "y"}) == 2
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_set({1, 2})

    assert fn_var_tuple((10, 20, 30)) == 60
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_var_tuple((10, "bad", 30))

    assert fn_list_of_list([[1, 2], [3, 4, 5]]) == 15
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_list_of_list([[1, 2], ["bad"]])

    assert fn_dict_of_list({"k1": [1, 2], "k2": [3, 4]}) == 10
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_dict_of_list({"k1": [1, "bad"]})
