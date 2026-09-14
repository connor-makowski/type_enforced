import pytest
import type_enforced


# ---------------------------------------------------------------------------
# 1. List enforcement with 'bookend' and 'bookend_plus'
# ---------------------------------------------------------------------------
@type_enforced.Enforcer(iterable_sample_pct="bookend")
def fn_bookend_list(data: list[int]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct="bookend_plus")
def fn_bookend_plus_list(data: list[int]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct="bookend")
def fn_bookend_list_union(data: list[int | str]) -> int:
    return len(data)


def test_bookend_list():
    # Empty, 1-item, 2-item, multi-item
    assert fn_bookend_list([]) == 0
    assert fn_bookend_list([10]) == 1
    assert fn_bookend_list([10, 20]) == 2
    assert fn_bookend_list([1, 2, 3, 4, 5]) == 5

    # Middle elements are not validated in 'bookend'
    assert fn_bookend_list([1, "bad", "bad", 4]) == 4

    # First element invalid -> raises TypeError
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_list(["bad"])

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_list(["bad", 2, 3])

    # Last element invalid -> raises TypeError
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_list([1, 2, "bad"])

    # Union list
    assert fn_bookend_list_union([1, 2.5, "str"]) == 3  # middle 2.5 ignored
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_list_union([2.5, 1, "str"])


def test_bookend_plus_list():
    assert fn_bookend_plus_list([]) == 0
    assert fn_bookend_plus_list([10]) == 1
    assert fn_bookend_plus_list([10, 20]) == 2
    assert fn_bookend_plus_list([1, 2, 3, 4, 5]) == 5

    # First element invalid
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_plus_list(["bad", 2, 3, 4])

    # Last element invalid
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_plus_list([1, 2, 3, "bad"])

    # If all middle elements are invalid in a list of len >= 3, any sampled middle item will fail
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_plus_list([1, "bad", "bad", "bad", 5])


# ---------------------------------------------------------------------------
# 2. Dict enforcement with 'bookend' and 'bookend_plus'
# ---------------------------------------------------------------------------
@type_enforced.Enforcer(iterable_sample_pct="bookend")
def fn_bookend_dict(data: dict[str, int]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct="bookend_plus")
def fn_bookend_plus_dict(data: dict[str, int]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct="bookend")
def fn_bookend_dict_unions(data: dict[str | int, int | float]) -> int:
    return len(data)


def test_bookend_dict():
    assert fn_bookend_dict({}) == 0
    assert fn_bookend_dict({"a": 1}) == 1
    assert fn_bookend_dict({"a": 1, "b": 2}) == 2
    assert fn_bookend_dict({"a": 1, "b": 2, "c": 3}) == 3

    # Entries beyond the first 2 are not validated in dict 'bookend'
    assert fn_bookend_dict({"a": 1, "b": 2, "c": "ignored", 123: "bad"}) == 4

    # First key/val invalid
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_dict({123: 1, "b": 2})

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_dict({"a": "bad", "b": 2})

    # Second key/val invalid
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_dict({"a": 1, 123: 2})

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_dict({"a": 1, "b": "bad"})

    # Union dict
    assert fn_bookend_dict_unions({"a": 1, 2: 3.5}) == 2
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_dict_unions({"a": "bad", 2: 3.5})


def test_bookend_plus_dict():
    assert fn_bookend_plus_dict({}) == 0
    assert fn_bookend_plus_dict({"a": 1}) == 1
    assert fn_bookend_plus_dict({"a": 1, "b": 2}) == 2
    assert fn_bookend_plus_dict({"a": 1, "b": 2, "c": 3}) == 3

    assert fn_bookend_plus_dict({"a": 1, "b": 2, "c": 3, "d": 4}) == 4

    # 1st invalid
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_plus_dict({123: 1, "b": 2, "c": 3})

    # 2nd invalid
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_plus_dict({"a": 1, 123: 2, "c": 3})

    # 3rd invalid (in a 3-item dict, all 3 are validated)
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_plus_dict({"a": 1, "b": 2, "c": "bad"})

    # All items beyond first 2 invalid -> random pick will fail
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_plus_dict({"a": 1, "b": 2, 123: "bad", 456: "bad2"})


# ---------------------------------------------------------------------------
# 3. Tuple enforcement with 'bookend' and 'bookend_plus'
# ---------------------------------------------------------------------------
@type_enforced.Enforcer(iterable_sample_pct="bookend")
def fn_bookend_tuple(data: tuple[int, ...]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct="bookend_plus")
def fn_bookend_plus_tuple(data: tuple[int, ...]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct="bookend")
def fn_bookend_tuple_union(data: tuple[int | str, ...]) -> int:
    return len(data)


def test_bookend_tuple():
    assert fn_bookend_tuple(()) == 0
    assert fn_bookend_tuple((1,)) == 1
    assert fn_bookend_tuple((1, 2)) == 2
    assert fn_bookend_tuple((1, "bad", "bad", 4)) == 4

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_tuple(("bad", 2, 3))

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_tuple((1, 2, "bad"))

    assert fn_bookend_tuple_union((1, 2.5, "str")) == 3


def test_bookend_plus_tuple():
    assert fn_bookend_plus_tuple(()) == 0
    assert fn_bookend_plus_tuple((1,)) == 1
    assert fn_bookend_plus_tuple((1, 2)) == 2
    assert fn_bookend_plus_tuple((1, 2, 3, 4)) == 4

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_plus_tuple(("bad", 2, 3))

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_plus_tuple((1, 2, "bad"))

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_plus_tuple((1, "bad", "bad", "bad", 5))


# ---------------------------------------------------------------------------
# 4. Set enforcement with 'bookend' and 'bookend_plus'
# ---------------------------------------------------------------------------
@type_enforced.Enforcer(iterable_sample_pct="bookend")
def fn_bookend_set(data: set[int]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct="bookend_plus")
def fn_bookend_plus_set(data: set[int]) -> int:
    return len(data)


def test_bookend_set():
    assert fn_bookend_set(set()) == 0
    assert fn_bookend_set({1}) == 1
    assert fn_bookend_set({1, 2}) == 2
    assert fn_bookend_set({1, 2, 3, 4}) == 4

    # Single invalid item in set
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_set({"bad"})


def test_bookend_plus_set():
    assert fn_bookend_plus_set(set()) == 0
    assert fn_bookend_plus_set({1}) == 1
    assert fn_bookend_plus_set({1, 2}) == 2
    assert fn_bookend_plus_set({1, 2, 3, 4}) == 4

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_plus_set({"bad"})


# ---------------------------------------------------------------------------
# 5. FastEnforcer support for 'bookend' and 'bookend_plus'
# ---------------------------------------------------------------------------
@type_enforced.FastEnforcer(iterable_sample_pct="bookend")
def fn_fast_bookend(data: list[int]) -> int:
    return len(data)


@type_enforced.FastEnforcer(iterable_sample_pct="bookend_plus")
def fn_fast_bookend_plus(data: list[int]) -> int:
    return len(data)


def test_fast_enforcer_bookend_options():
    assert fn_fast_bookend([1, "ignored", 3]) == 3
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_fast_bookend(["bad", 2, 3])

    assert fn_fast_bookend_plus([1, 2, 3]) == 3
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_fast_bookend_plus(["bad", 2, 3])


# ---------------------------------------------------------------------------
# 6. Class and Method enforcement with 'bookend' / 'bookend_plus'
# ---------------------------------------------------------------------------
@type_enforced.Enforcer(iterable_sample_pct="bookend")
class BookendClass:
    def process_list(self, items: list[int]) -> int:
        return len(items)

    @type_enforced.Enforcer(iterable_sample_pct="bookend_plus")
    def process_dict(self, mapping: dict[str, int]) -> int:
        return len(mapping)


def test_bookend_class_and_methods():
    obj = BookendClass()
    assert obj.process_list([1, "ignored", 3]) == 3
    with pytest.raises(TypeError, match="Type mismatch"):
        obj.process_list(["bad", 2])

    assert obj.process_dict({"a": 1, "b": 2, "c": 3}) == 3
    with pytest.raises(TypeError, match="Type mismatch"):
        obj.process_dict({"a": 1, "bad_key": "bad_val", "c": "bad_val"})


# ---------------------------------------------------------------------------
# 7. Direct Slot Sampling for Dicts & Sets ('first', 'last', 'bookend', 'bookend_plus', 0)
# ---------------------------------------------------------------------------
@type_enforced.Enforcer(iterable_sample_pct="first")
def fn_first_dict(data: dict[str, int]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct="last")
def fn_last_dict(data: dict[str, int]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct=0)
def fn_zero_dict(data: dict[str, int]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct="first")
def fn_first_set(data: set[int]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct="last")
def fn_last_set(data: set[int]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct=0)
def fn_zero_set(data: set[int]) -> int:
    return len(data)


def test_direct_slot_sampling_dict():
    # Large dict with 1000 items
    valid_d = {f"k{i}": i for i in range(1000)}
    assert fn_first_dict(valid_d) == 1000
    assert fn_last_dict(valid_d) == 1000
    assert fn_zero_dict(valid_d) == 1000

    # first fails on first entry
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_first_dict({123: 1, "b": 2})

    # last fails on first entry (since last on dict checks first entry)
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_last_dict({123: 3, "a": 1, "b": 2})

    # zero (random pick) fails on dict with all invalid keys
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_zero_dict({i: i for i in range(100)})


def test_direct_slot_sampling_set():
    # Large set with 1000 items
    valid_s = set(range(1000))
    assert fn_first_set(valid_s) == 1000
    assert fn_last_set(valid_s) == 1000
    assert fn_zero_set(valid_s) == 1000

    # All invalid fails in first, last, zero
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_first_set({"bad"})
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_last_set({"bad"})
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_zero_set({"bad"})


# ---------------------------------------------------------------------------
# 8. Weyl pseudo-random start offset sequence sampling tests
# ---------------------------------------------------------------------------
def test_weyl_random_start_sampling_list():
    @type_enforced.Enforcer(iterable_sample_pct=10)
    def fn_sample_10(data: list[int]) -> int:
        return len(data)

    valid_data = list(range(100))
    assert fn_sample_10(valid_data) == 100

    # A list where only index 3 is invalid
    # Over repeated calls, the Weyl sequence will hit start offset 3 and raise TypeError
    bad_data = [("bad" if i == 3 else i) for i in range(100)]
    caught = False
    for _ in range(50):
        try:
            fn_sample_10(bad_data)
        except TypeError:
            caught = True
            break
    assert (
        caught
    ), "Expected Weyl pseudo-random sampling to catch bad element at index 3"


def test_weyl_random_start_sampling_tuple():
    @type_enforced.Enforcer(iterable_sample_pct=25)
    def fn_sample_25(data: tuple[int, ...]) -> int:
        return len(data)

    valid_data = tuple(range(100))
    assert fn_sample_25(valid_data) == 100

    # Tuple where only index 2 is invalid
    bad_data = tuple(("bad" if i == 2 else i) for i in range(100))
    caught = False
    for _ in range(50):
        try:
            fn_sample_25(bad_data)
        except TypeError:
            caught = True
            break
    assert (
        caught
    ), "Expected Weyl pseudo-random sampling to catch bad element at index 2"


def test_weyl_sample_indices_helper():
    enforcer = type_enforced.FunctionMethodEnforcer(
        lambda: None, __iterable_sample_pct__=10
    )
    # len=100, pct=10 -> count=10, step=10
    indices1 = list(enforcer.__get_sample_indices__(100))
    indices2 = list(enforcer.__get_sample_indices__(100))
    assert len(indices1) == 10
    assert len(indices2) == 10
    assert all(0 <= idx < 100 for idx in indices1)
    assert all(0 <= idx < 100 for idx in indices2)
    # Check step interval
    assert all(
        indices1[i + 1] - indices1[i] == 10 for i in range(len(indices1) - 1)
    )
    assert all(
        indices2[i + 1] - indices2[i] == 10 for i in range(len(indices2) - 1)
    )
