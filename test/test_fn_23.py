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


def test_fn_23_rounding_up_percentage():
    # len=3, pct=50 -> count = (3*50+99)//100 = 2 items (indices 0 and -1)
    # Index 1 is not checked.
    sampled_check(a=[1, "bad_middle", 3])
    # First item is checked:
    with pytest.raises(TypeError):
        sampled_check(a=["bad_first", 2, 3])
    # Last item is checked:
    with pytest.raises(TypeError):
        sampled_check(a=[1, 2, "bad_last"])


# ---------------------------------------------------------
# 'first' mode tests
# ---------------------------------------------------------


def test_fn_23_first_list():
    @type_enforced.Enforcer(iterable_sample_pct="first")
    def fn_first_list(a: list[int]) -> list[int]:
        return a

    assert fn_first_list(a=[]) == []
    assert fn_first_list(a=[1, "bad", "bad2"]) == [1, "bad", "bad2"]
    with pytest.raises(TypeError):
        fn_first_list(a=["bad", 1, 2])


def test_fn_23_first_dict():
    @type_enforced.Enforcer(iterable_sample_pct="first")
    def fn_first_dict(a: dict[str, int]) -> dict[str, int]:
        return a

    assert fn_first_dict(a={}) == {}
    assert fn_first_dict(a={"a": 1, "b": "bad", 123: "bad"}) == {
        "a": 1,
        "b": "bad",
        123: "bad",
    }
    with pytest.raises(TypeError):
        fn_first_dict(a={123: 1, "b": 2})
    with pytest.raises(TypeError):
        fn_first_dict(a={"a": "bad", "b": 2})


def test_fn_23_first_tuple():
    @type_enforced.Enforcer(iterable_sample_pct="first")
    def fn_first_tuple(a: tuple[int, ...]) -> tuple[int, ...]:
        return a

    assert fn_first_tuple(a=()) == ()
    assert fn_first_tuple(a=(1, "bad", "bad2")) == (1, "bad", "bad2")
    with pytest.raises(TypeError):
        fn_first_tuple(a=("bad", 1, 2))


def test_fn_23_first_set():
    @type_enforced.Enforcer(iterable_sample_pct="first")
    def fn_first_set(a: set[int]) -> set[int]:
        return a

    assert fn_first_set(a=set()) == set()
    assert fn_first_set(a={1}) == {1}
    with pytest.raises(TypeError):
        fn_first_set(a={"bad"})


def test_fn_23_first_nested_list_of_dict():
    @type_enforced.Enforcer(iterable_sample_pct="first")
    def fn_list_dict(x: list[dict[str, int]]) -> list[dict[str, int]]:
        return x

    assert fn_list_dict(x=[{"a": 1}]) == [{"a": 1}]
    assert fn_list_dict(x=[]) == []
    assert fn_list_dict(x=[{}]) == [{}]

    sampled_input = [
        {"a": 1, "b": "bad_val", 123: "bad_key"},
        "bad_second_item",
    ]
    assert fn_list_dict(x=sampled_input) == sampled_input

    with pytest.raises(TypeError):
        fn_list_dict(x=["not_a_dict", {"a": 1}])

    with pytest.raises(TypeError):
        fn_list_dict(x=[{123: 1}, {"a": 1}])

    with pytest.raises(TypeError):
        fn_list_dict(x=[{"a": "not_int"}, {"b": 2}])


def test_fn_23_first_nested_dict_of_list():
    @type_enforced.Enforcer(iterable_sample_pct="first")
    def fn_dict_list(x: dict[str, list[int]]) -> dict[str, list[int]]:
        return x

    assert fn_dict_list(x={}) == {}
    assert fn_dict_list(x={"a": []}) == {"a": []}

    sampled_input = {"a": [1, "bad_elem"], "b": "bad_second_dict_entry"}
    assert fn_dict_list(x=sampled_input) == sampled_input

    with pytest.raises(TypeError):
        fn_dict_list(x={123: [1, 2]})

    with pytest.raises(TypeError):
        fn_dict_list(x={"a": "not_a_list"})

    with pytest.raises(TypeError):
        fn_dict_list(x={"a": ["bad_elem", 2]})


def test_fn_23_first_nested_list_of_list():
    @type_enforced.Enforcer(iterable_sample_pct="first")
    def fn_list_list(x: list[list[int]]) -> list[list[int]]:
        return x

    assert fn_list_list(x=[]) == []
    assert fn_list_list(x=[[]]) == [[]]

    sampled_input = [[1, "bad_second_elem"], ["bad_second_list"]]
    assert fn_list_list(x=sampled_input) == sampled_input

    with pytest.raises(TypeError):
        fn_list_list(x=["not_a_list", [1, 2]])

    with pytest.raises(TypeError):
        fn_list_list(x=[["not_int", 2], [3, 4]])


# ---------------------------------------------------------
# 'last' mode tests
# ---------------------------------------------------------


def test_fn_23_last_list():
    @type_enforced.Enforcer(iterable_sample_pct="last")
    def fn_last_list(a: list[int]) -> list[int]:
        return a

    assert fn_last_list(a=[]) == []
    assert fn_last_list(a=["bad", "bad2", 3]) == ["bad", "bad2", 3]
    with pytest.raises(TypeError):
        fn_last_list(a=[1, 2, "bad"])


def test_fn_23_last_dict():
    @type_enforced.Enforcer(iterable_sample_pct="last")
    def fn_last_dict(a: dict[str, int]) -> dict[str, int]:
        return a

    assert fn_last_dict(a={}) == {}
    assert fn_last_dict(a={"bad": "bad_val", "good": 2}) == {
        "bad": "bad_val",
        "good": 2,
    }
    with pytest.raises(TypeError):
        fn_last_dict(a={"a": 1, 123: 2})
    with pytest.raises(TypeError):
        fn_last_dict(a={"a": 1, "b": "bad"})


def test_fn_23_last_tuple():
    @type_enforced.Enforcer(iterable_sample_pct="last")
    def fn_last_tuple(a: tuple[int, ...]) -> tuple[int, ...]:
        return a

    assert fn_last_tuple(a=()) == ()
    assert fn_last_tuple(a=("bad", "bad2", 3)) == ("bad", "bad2", 3)
    with pytest.raises(TypeError):
        fn_last_tuple(a=(1, 2, "bad"))


def test_fn_23_last_set():
    @type_enforced.Enforcer(iterable_sample_pct="last")
    def fn_last_set(a: set[int]) -> set[int]:
        return a

    assert fn_last_set(a=set()) == set()
    assert fn_last_set(a={1}) == {1}
    with pytest.raises(TypeError):
        fn_last_set(a={"bad"})


def test_fn_23_last_nested_list_of_dict():
    @type_enforced.Enforcer(iterable_sample_pct="last")
    def fn_list_dict(x: list[dict[str, int]]) -> list[dict[str, int]]:
        return x

    assert fn_list_dict(x=[]) == []
    assert fn_list_dict(x=[{}]) == [{}]

    sampled_input = [
        "bad_first_item",
        {"a": "bad_val", "b": 2},
    ]
    assert fn_list_dict(x=sampled_input) == sampled_input

    with pytest.raises(TypeError):
        fn_list_dict(x=[{"a": 1}, "not_a_dict"])

    with pytest.raises(TypeError):
        fn_list_dict(x=[{"a": 1}, {123: 1}])

    with pytest.raises(TypeError):
        fn_list_dict(x=[{"a": 1}, {"b": "not_int"}])


# ---------------------------------------------------------
# 0 (random single item) mode tests
# ---------------------------------------------------------


def test_fn_23_zero_pct_random_sampling():
    @type_enforced.Enforcer(iterable_sample_pct=0)
    def fn_rand_list(a: list[int]) -> list[int]:
        return a

    assert fn_rand_list(a=[]) == []
    assert fn_rand_list(a=[1]) == [1]
    with pytest.raises(TypeError):
        fn_rand_list(a=["bad"])

    @type_enforced.Enforcer(iterable_sample_pct=0)
    def fn_rand_dict(a: dict[str, int]) -> dict[str, int]:
        return a

    assert fn_rand_dict(a={}) == {}
    assert fn_rand_dict(a={"a": 1}) == {"a": 1}
    with pytest.raises(TypeError):
        fn_rand_dict(a={123: 1})
    with pytest.raises(TypeError):
        fn_rand_dict(a={"a": "bad"})

    @type_enforced.Enforcer(iterable_sample_pct=0)
    def fn_rand_tuple(a: tuple[int, ...]) -> tuple[int, ...]:
        return a

    assert fn_rand_tuple(a=()) == ()
    assert fn_rand_tuple(a=(1,)) == (1,)
    with pytest.raises(TypeError):
        fn_rand_tuple(a=("bad",))

    @type_enforced.Enforcer(iterable_sample_pct=0)
    def fn_rand_set(a: set[int]) -> set[int]:
        return a

    assert fn_rand_set(a=set()) == set()
    assert fn_rand_set(a={1}) == {1}
    with pytest.raises(TypeError):
        fn_rand_set(a={"bad"})


# ---------------------------------------------------------
# 'log' mode tests
# ---------------------------------------------------------


def test_fn_23_log_list():
    @type_enforced.Enforcer(iterable_sample_pct="log")
    def fn_log_list(a: list[int]) -> list[int]:
        return a

    assert fn_log_list(a=[]) == []
    assert fn_log_list(a=[1]) == [1]
    assert fn_log_list(a=list(range(100))) == list(range(100))

    with pytest.raises(TypeError):
        fn_log_list(a=["bad"])

    with pytest.raises(TypeError):
        fn_log_list(a=["bad"] + list(range(1, 100)))

    with pytest.raises(TypeError):
        fn_log_list(a=list(range(99)) + ["bad"])


def test_fn_23_log_dict():
    @type_enforced.Enforcer(iterable_sample_pct="log")
    def fn_log_dict(a: dict[str, int]) -> dict[str, int]:
        return a

    assert fn_log_dict(a={}) == {}
    assert fn_log_dict(a={"a": 1}) == {"a": 1}
    assert fn_log_dict(a={str(i): i for i in range(100)}) == {
        str(i): i for i in range(100)
    }

    with pytest.raises(TypeError):
        fn_log_dict(a={123: 1})

    with pytest.raises(TypeError):
        d = {str(i): i for i in range(100)}
        first_k = list(d.keys())[0]
        d[first_k] = "bad"
        fn_log_dict(a=d)

    with pytest.raises(TypeError):
        d = {str(i): i for i in range(100)}
        last_k = list(d.keys())[-1]
        d[last_k] = "bad"
        fn_log_dict(a=d)


def test_fn_23_log_tuple():
    @type_enforced.Enforcer(iterable_sample_pct="log")
    def fn_log_tuple(a: tuple[int, ...]) -> tuple[int, ...]:
        return a

    assert fn_log_tuple(a=()) == ()
    assert fn_log_tuple(a=(1,)) == (1,)
    assert fn_log_tuple(a=tuple(range(100))) == tuple(range(100))

    with pytest.raises(TypeError):
        fn_log_tuple(a=("bad",))

    with pytest.raises(TypeError):
        fn_log_tuple(a=("bad",) + tuple(range(1, 100)))

    with pytest.raises(TypeError):
        fn_log_tuple(a=tuple(range(99)) + ("bad",))


def test_fn_23_log_set():
    @type_enforced.Enforcer(iterable_sample_pct="log")
    def fn_log_set(a: set[int]) -> set[int]:
        return a

    assert fn_log_set(a=set()) == set()
    assert fn_log_set(a={1}) == {1}
    assert fn_log_set(a=set(range(100))) == set(range(100))

    with pytest.raises(TypeError):
        fn_log_set(a={"bad"})


def test_fn_23_log_nested():
    @type_enforced.Enforcer(iterable_sample_pct="log")
    def fn_log_nested(x: list[dict[str, int]]) -> list[dict[str, int]]:
        return x

    assert fn_log_nested(x=[]) == []
    assert fn_log_nested(x=[{}]) == [{}]
    assert fn_log_nested(x=[{"a": 1, "b": 2}]) == [{"a": 1, "b": 2}]

    with pytest.raises(TypeError):
        fn_log_nested(x=["not_a_dict"])

    with pytest.raises(TypeError):
        fn_log_nested(x=[{123: 1}])


# ---------------------------------------------------------
# Parameter validation for iterable_sample_pct
# ---------------------------------------------------------


def test_fn_23_invalid_sample_pct():
    with pytest.raises(TypeError, match="Invalid iterable_sample_pct"):

        @type_enforced.Enforcer(iterable_sample_pct="middle")
        def fn_bad1(x: list[int]) -> None:
            pass

    with pytest.raises(TypeError, match="Invalid iterable_sample_pct"):

        @type_enforced.Enforcer(iterable_sample_pct=-1)
        def fn_bad2(x: list[int]) -> None:
            pass

    with pytest.raises(TypeError, match="Invalid iterable_sample_pct"):

        @type_enforced.Enforcer(iterable_sample_pct=101)
        def fn_bad3(x: list[int]) -> None:
            pass

    with pytest.raises(TypeError, match="Invalid iterable_sample_pct"):

        @type_enforced.Enforcer(iterable_sample_pct=True)
        def fn_bad4(x: list[int]) -> None:
            pass

    with pytest.raises(TypeError, match="Invalid iterable_sample_pct"):

        @type_enforced.Enforcer(iterable_sample_pct=3.5)
        def fn_bad5(x: list[int]) -> None:
            pass
