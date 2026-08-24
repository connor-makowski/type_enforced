import pytest
import type_enforced


@type_enforced.Enforcer
def full_check(a: list[int]) -> None:
    return None


@type_enforced.Enforcer(iterable_sample_pct=50)
def sampled_check(a: list[int]) -> None:
    return None


@type_enforced.Enforcer(iterable_sample_pct=50)
def sampled_dict(a: dict[str, int]) -> None:
    return None


@type_enforced.Enforcer(iterable_sample_pct=50)
def sampled_tuple(a: tuple[int, ...]) -> None:
    return None


@type_enforced.Enforcer(iterable_sample_pct=0)
def zero_pct_check(a: list[int]) -> None:
    return None


def test_fn_23_full_check():
    full_check(a=[1, 2, 3, 4, 5])
    with pytest.raises(TypeError):
        full_check(a=[1, 2, "bad", 4, 5])


def test_fn_23_sampled_check():
    sampled_check(a=list(range(100)))
    with pytest.raises(TypeError):
        sampled_check(a=["bad"] + list(range(1, 100)))
    with pytest.raises(TypeError):
        sampled_check(a=list(range(99)) + ["bad"])


def test_fn_23_sampled_dict():
    sampled_dict(a={str(i): i for i in range(100)})
    d = {str(i): i for i in range(100)}
    first_key = list(d.keys())[0]
    d[first_key] = "bad_value"
    with pytest.raises(TypeError):
        sampled_dict(a=d)


def test_fn_23_sampled_tuple():
    sampled_tuple(a=tuple(range(100)))
    with pytest.raises(TypeError):
        sampled_tuple(a=("bad",) + tuple(range(1, 100)))


def test_fn_23_short_list():
    # Short list (<=3): all items checked even with sampling
    with pytest.raises(TypeError):
        sampled_check(a=[1, "bad", 3])


def test_fn_23_zero_pct():
    with pytest.raises(TypeError):
        zero_pct_check(a=["bad", 2, 3, 4, 5])
    # Last item not checked at pct=0
    zero_pct_check(a=[1, 2, 3, 4, "bad"])
    zero_pct_check(a=[])


def test_fn_23_zero_pct_nested_list_of_dict():
    @type_enforced.Enforcer(iterable_sample_pct=0)
    def fn_list_dict(x: list[dict[str, int]]) -> list[dict[str, int]]:
        return x

    # 1. Fully valid inputs (single item, multi-item, multi-key)
    assert fn_list_dict(x=[{"a": 1}]) == [{"a": 1}]
    assert fn_list_dict(x=[{"a": 1, "b": 2}, {"c": 3, "d": 4}]) == [
        {"a": 1, "b": 2},
        {"c": 3, "d": 4},
    ]

    # 2. Empty valid edge cases
    assert fn_list_dict(x=[]) == []
    assert fn_list_dict(x=[{}]) == [{}]

    # 3. Sampled valid cases (first item & first key/val valid; subsequent items/keys ignored at 0% sample)
    sampled_input = [
        {"a": 1, "b": "bad_val", 123: "bad_key"},
        "bad_second_item",
    ]
    assert fn_list_dict(x=sampled_input) == sampled_input

    # 4. Failures: first item not a dict
    with pytest.raises(TypeError):
        fn_list_dict(x=["not_a_dict", {"a": 1}])

    # 5. Failures: first item's first key is not str
    with pytest.raises(TypeError):
        fn_list_dict(x=[{123: 1}, {"a": 1}])

    # 6. Failures: first item's first value is not int
    with pytest.raises(TypeError):
        fn_list_dict(x=[{"a": "not_int"}, {"b": 2}])

    # 7. Failures: outer type is not list
    with pytest.raises(TypeError):
        fn_list_dict(x="not_a_list")


def test_fn_23_zero_pct_nested_dict_of_list():
    @type_enforced.Enforcer(iterable_sample_pct=0)
    def fn_dict_list(x: dict[str, list[int]]) -> dict[str, list[int]]:
        return x

    # 1. Fully valid inputs (single key, multi-key, multi-item lists)
    assert fn_dict_list(x={"a": [1, 2], "b": [3, 4]}) == {
        "a": [1, 2],
        "b": [3, 4],
    }

    # 2. Empty valid edge cases
    assert fn_dict_list(x={}) == {}
    assert fn_dict_list(x={"a": []}) == {"a": []}

    # 3. Sampled valid cases (first key str, first val list with int; subsequent entries ignored)
    sampled_input = {"a": [1, "bad_elem"], "b": "bad_second_dict_entry"}
    assert fn_dict_list(x=sampled_input) == sampled_input

    # 4. Failures: first key not str
    with pytest.raises(TypeError):
        fn_dict_list(x={123: [1, 2]})

    # 5. Failures: first val not a list
    with pytest.raises(TypeError):
        fn_dict_list(x={"a": "not_a_list"})

    # 6. Failures: first item in first val's list not int
    with pytest.raises(TypeError):
        fn_dict_list(x={"a": ["bad_elem", 2]})

    # 7. Failures: outer type not dict
    with pytest.raises(TypeError):
        fn_dict_list(x=[("a", [1])])


def test_fn_23_zero_pct_nested_list_of_list():
    @type_enforced.Enforcer(iterable_sample_pct=0)
    def fn_list_list(x: list[list[int]]) -> list[list[int]]:
        return x

    # 1. Fully valid inputs
    assert fn_list_list(x=[[1, 2], [3, 4]]) == [[1, 2], [3, 4]]

    # 2. Empty valid edge cases
    assert fn_list_list(x=[]) == []
    assert fn_list_list(x=[[]]) == [[]]

    # 3. Sampled valid cases
    sampled_input = [[1, "bad_second_elem"], ["bad_second_list"]]
    assert fn_list_list(x=sampled_input) == sampled_input

    # 4. Failures: first item not a list
    with pytest.raises(TypeError):
        fn_list_list(x=["not_a_list", [1, 2]])

    # 5. Failures: first item in first list not int
    with pytest.raises(TypeError):
        fn_list_list(x=[["not_int", 2], [3, 4]])

    # 6. Failures: outer type not list
    with pytest.raises(TypeError):
        fn_list_list(x=([1], [2]))


def test_fn_23_zero_pct_nested_dict_of_dict():
    @type_enforced.Enforcer(iterable_sample_pct=0)
    def fn_dict_dict(
        x: dict[str, dict[str, int]],
    ) -> dict[str, dict[str, int]]:
        return x

    # 1. Fully valid inputs
    assert fn_dict_dict(
        x={"outer1": {"inner1": 1, "inner2": 2}, "outer2": {"inner3": 3}}
    ) == {"outer1": {"inner1": 1, "inner2": 2}, "outer2": {"inner3": 3}}

    # 2. Empty valid edge cases
    assert fn_dict_dict(x={}) == {}
    assert fn_dict_dict(x={"outer": {}}) == {"outer": {}}

    # 3. Sampled valid cases
    sampled_input = {
        "outer": {"inner": 1, "inner2": "bad"},
        "outer2": "bad_outer2",
    }
    assert fn_dict_dict(x=sampled_input) == sampled_input

    # 4. Failures: outer key not str
    with pytest.raises(TypeError):
        fn_dict_dict(x={123: {"inner": 1}})

    # 5. Failures: outer val not dict
    with pytest.raises(TypeError):
        fn_dict_dict(x={"outer": "not_dict"})

    # 6. Failures: inner key not str
    with pytest.raises(TypeError):
        fn_dict_dict(x={"outer": {123: 1}})

    # 7. Failures: inner val not int
    with pytest.raises(TypeError):
        fn_dict_dict(x={"outer": {"inner": "not_int"}})


def test_fn_23_zero_pct_nested_list_of_tuple():
    @type_enforced.Enforcer(iterable_sample_pct=0)
    def fn_list_tuple(x: list[tuple[int, ...]]) -> list[tuple[int, ...]]:
        return x

    # 1. Fully valid inputs
    assert fn_list_tuple(x=[(1, 2, 3), (4, 5)]) == [(1, 2, 3), (4, 5)]

    # 2. Empty valid edge cases
    assert fn_list_tuple(x=[]) == []
    assert fn_list_tuple(x=[()]) == [()]

    # 3. Sampled valid cases
    sampled_input = [(1, "bad_second"), "bad_second_list_item"]
    assert fn_list_tuple(x=sampled_input) == sampled_input

    # 4. Failures: first item not tuple
    with pytest.raises(TypeError):
        fn_list_tuple(x=["not_tuple", (1, 2)])

    # 5. Failures: first item in tuple not int
    with pytest.raises(TypeError):
        fn_list_tuple(x=[("bad", 2), (1, 2)])


def test_fn_23_zero_pct_nested_list_of_set():
    @type_enforced.Enforcer(iterable_sample_pct=0)
    def fn_list_set(x: list[set[str]]) -> list[set[str]]:
        return x

    # 1. Fully valid inputs
    assert fn_list_set(x=[{"valid1", "valid2"}, {"valid3"}]) == [
        {"valid1", "valid2"},
        {"valid3"},
    ]

    # 2. Empty valid edge cases
    assert fn_list_set(x=[]) == []
    assert fn_list_set(x=[set()]) == [set()]

    # 3. Sampled valid cases
    sampled_input = [{"valid"}, "bad_second_list_item"]
    assert fn_list_set(x=sampled_input) == sampled_input

    # 4. Failures: first item not set
    with pytest.raises(TypeError):
        fn_list_set(x=["not_set", {"valid"}])

    # 5. Failures: first item in set not str
    with pytest.raises(TypeError):
        fn_list_set(x=[{123}, {"valid"}])


def test_fn_23_zero_pct_deeply_nested():
    @type_enforced.Enforcer(iterable_sample_pct=0)
    def fn_deep(
        x: list[dict[str, list[int]]],
    ) -> list[dict[str, list[int]]]:
        return x

    # 1. Fully valid inputs (3-level nesting)
    full_valid = [{"a": [1, 2], "b": [3]}, {"c": [4, 5]}]
    assert fn_deep(x=full_valid) == full_valid

    # 2. Empty valid edge cases
    assert fn_deep(x=[]) == []
    assert fn_deep(x=[{}]) == [{}]
    assert fn_deep(x=[{"a": []}]) == [{"a": []}]

    # 3. Sampled valid cases
    sampled_input = [
        {"a": [1, "bad_inner"], "b": "bad_dict"},
        "bad_outer",
    ]
    assert fn_deep(x=sampled_input) == sampled_input

    # 4. Failures: level 1 item not dict
    with pytest.raises(TypeError):
        fn_deep(x=["not_dict"])

    # 5. Failures: level 2 dict key not str
    with pytest.raises(TypeError):
        fn_deep(x=[{123: [1]}])

    # 6. Failures: level 2 dict val not list
    with pytest.raises(TypeError):
        fn_deep(x=[{"a": "not_list"}])

    # 7. Failures: level 3 list item not int
    with pytest.raises(TypeError):
        fn_deep(x=[{"a": ["not_int"]}])


def test_fn_23_zero_pct_multi_arg_and_return():
    @type_enforced.Enforcer(iterable_sample_pct=0)
    def multi_arg(
        a: list[dict[str, int]], b: dict[str, list[str]]
    ) -> list[dict[str, int]]:
        return a

    # 1. Fully valid multi-arg call
    full_a = [{"x": 10, "y": 20}, {"z": 30}]
    full_b = {"k1": ["one", "two"], "k2": ["three"]}
    assert multi_arg(a=full_a, b=full_b) == full_a

    # 2. Sampled valid multi-arg call
    sampled_a = [{"x": 10, "y": "bad"}, "bad_second_item"]
    sampled_b = {"k": ["valid", 123], "k2": "bad"}
    assert multi_arg(a=sampled_a, b=sampled_b) == sampled_a

    # 3. Invalid first param first item
    with pytest.raises(TypeError):
        multi_arg(
            a=[{"x": "not_int"}],
            b={"k": ["valid"]},
        )

    # 4. Invalid second param first item
    with pytest.raises(TypeError):
        multi_arg(
            a=[{"x": 10}],
            b={"k": [123]},
        )

    # 5. Invalid return value
    @type_enforced.Enforcer(iterable_sample_pct=0)
    def bad_return() -> list[dict[str, int]]:
        return ["not_a_dict"]

    with pytest.raises(TypeError):
        bad_return()
