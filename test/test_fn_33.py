import pytest
import type_enforced
from typing import Union


# 1. Fixed tuple unions
@type_enforced.Enforcer
def fn_tuple_union(t: tuple[int, str] | tuple[str, int]) -> int:
    return len(t)


def test_tuple_union():
    # Valid calls
    assert fn_tuple_union((1, "hello")) == 2
    assert fn_tuple_union(("hello", 1)) == 2

    # Invalid calls
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_tuple_union((1, 1))

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_tuple_union(("hello", "world"))

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_tuple_union((1, "hello", 2))

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_tuple_union("not_a_tuple")


# 2. Fixed tuple unions with different lengths
@type_enforced.Enforcer
def fn_tuple_different_lengths(
    t: tuple[int, str, float] | tuple[int, int],
) -> int:
    return len(t)


def test_tuple_different_lengths():
    assert fn_tuple_different_lengths((1, "a", 2.5)) == 3
    assert fn_tuple_different_lengths((1, 2)) == 2

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_tuple_different_lengths((1, "a"))

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_tuple_different_lengths((1, 2, 3))


# 3. Variadic vs fixed tuple unions
@type_enforced.Enforcer
def fn_tuple_fixed_or_var(t: tuple[int, str] | tuple[int, ...]) -> int:
    return len(t)


def test_tuple_fixed_or_var():
    assert fn_tuple_fixed_or_var((1, "a")) == 2
    assert fn_tuple_fixed_or_var((1, 2, 3, 4)) == 4
    assert fn_tuple_fixed_or_var(()) == 0

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_tuple_fixed_or_var(("a", 1))

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_tuple_fixed_or_var((1, "a", 3))


# 4. Variadic tuple unions
@type_enforced.Enforcer
def fn_tuple_var_union(t: tuple[int, ...] | tuple[str, ...]) -> int:
    return len(t)


def test_tuple_var_union():
    assert fn_tuple_var_union((1, 2, 3)) == 3
    assert fn_tuple_var_union(("a", "b")) == 2
    assert fn_tuple_var_union(()) == 0

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_tuple_var_union((1, "a"))


# 5. Dict value unions (disallowing mixed dictionaries)
@type_enforced.Enforcer
def fn_dict_val_union(d: dict[str, list[int]] | dict[str, int]) -> int:
    return len(d)


def test_dict_val_union():
    # All list[int] values
    assert fn_dict_val_union({"a": [1, 2], "b": [3, 4]}) == 2
    # All int values
    assert fn_dict_val_union({"a": 1, "b": 2}) == 2
    # Empty dict matches
    assert fn_dict_val_union({}) == 0

    # Mixed values must fail
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_dict_val_union({"a": 1, "b": [2]})

    # Bad key type must fail
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_dict_val_union({1: 1, 2: 2})

    # Bad nested element type must fail
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_dict_val_union({"a": ["bad"]})


# 6. Dict key and value unions
@type_enforced.Enforcer
def fn_dict_key_val_union(d: dict[str, int] | dict[int, str]) -> int:
    return len(d)


def test_dict_key_val_union():
    assert fn_dict_key_val_union({"a": 1, "b": 2}) == 2
    assert fn_dict_key_val_union({1: "a", 2: "b"}) == 2

    # Mixed keys/values must fail
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_dict_key_val_union({"a": 1, 2: "b"})

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_dict_key_val_union({"a": "b"})

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_dict_key_val_union({1: 2})


# 7. List unions (homogeneous list[int] OR list[str]) vs list[int | str]
@type_enforced.Enforcer
def fn_list_union(items: list[int] | list[str]) -> int:
    return len(items)


@type_enforced.Enforcer
def fn_list_mixed_allowed(items: list[int | str]) -> int:
    return len(items)


def test_list_union():
    assert fn_list_union([1, 2, 3]) == 3
    assert fn_list_union(["a", "b"]) == 2
    assert fn_list_union([]) == 0

    # list[int] | list[str] rejects mixed
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_list_union([1, "a"])

    # list[int | str] allows mixed
    assert fn_list_mixed_allowed([1, "a", 2]) == 3


# 8. Set unions
@type_enforced.Enforcer
def fn_set_union(s: set[int] | set[str]) -> int:
    return len(s)


def test_set_union():
    assert fn_set_union({1, 2, 3}) == 3
    assert fn_set_union({"a", "b"}) == 2
    assert fn_set_union(set()) == 0

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_set_union({1, "a"})


# 9. Deeply nested collection unions
@type_enforced.Enforcer
def fn_nested_collection_union(
    data: list[tuple[int, str] | tuple[str, int]],
) -> int:
    return len(data)


def test_nested_collection_union():
    assert fn_nested_collection_union([(1, "a"), ("b", 2), (3, "c")]) == 3
    assert fn_nested_collection_union([]) == 0

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_nested_collection_union([(1, "a"), (1, 1)])


# 10. Deeply nested dict with tuple unions
@type_enforced.Enforcer
def fn_nested_dict_tuple_union(
    data: dict[str, tuple[int, str] | tuple[str, int]],
) -> int:
    return len(data)


def test_nested_dict_tuple_union():
    assert fn_nested_dict_tuple_union({"x": (1, "a"), "y": ("b", 2)}) == 2

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_nested_dict_tuple_union({"x": (1, 1)})


# 11. Tuple of collection unions
@type_enforced.Enforcer
def fn_tuple_of_unions(
    data: tuple[list[int] | list[str], dict[str, int] | dict[str, str]],
) -> int:
    return len(data)


def test_tuple_of_unions():
    assert fn_tuple_of_unions(([1, 2], {"a": 1})) == 2
    assert fn_tuple_of_unions((["a", "b"], {"a": "hello"})) == 2

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_tuple_of_unions(([1, "bad"], {"a": 1}))

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_tuple_of_unions(([1, 2], {"a": 1, "b": "bad_mix"}))


# 12. Collection unions with scalars and None
@type_enforced.Enforcer
def fn_collection_scalar_none(t: tuple[int, str] | int | None = None) -> str:
    if t is None:
        return "none"
    if isinstance(t, int):
        return f"int:{t}"
    return f"tuple:{t}"


def test_collection_scalar_none():
    assert fn_collection_scalar_none() == "none"
    assert fn_collection_scalar_none(None) == "none"
    assert fn_collection_scalar_none(42) == "int:42"
    assert fn_collection_scalar_none((1, "a")) == "tuple:(1, 'a')"

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_collection_scalar_none(("a", 1))

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_collection_scalar_none((1, 1))

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_collection_scalar_none("invalid")


# 13. FastEnforcer sampled enforcement on collection unions
@type_enforced.FastEnforcer
def fn_fast_list_union(items: list[int] | list[str]) -> int:
    return len(items)


def test_fast_list_union():
    assert fn_fast_list_union([1, 2, 3]) == 3
    assert fn_fast_list_union(["a", "b"]) == 2

    # In FastEnforcer (default 'first'), first element is checked
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_fast_list_union([1.5, 2, 3])


# 14. Return type enforcement with collection unions
@type_enforced.Enforcer
def fn_return_tuple_union(mode: int) -> tuple[int, str] | tuple[str, int]:
    if mode == 1:
        return (1, "a")
    elif mode == 2:
        return ("a", 1)
    elif mode == 3:
        return (1, 1)  # Invalid return
    return ("a", "b")  # Invalid return


def test_return_tuple_union():
    assert fn_return_tuple_union(1) == (1, "a")
    assert fn_return_tuple_union(2) == ("a", 1)

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_return_tuple_union(3)

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_return_tuple_union(4)
