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

    # Entries beyond the first 3 are not validated in dict 'bookend_plus'
    assert fn_bookend_plus_dict({"a": 1, "b": 2, "c": 3, 123: "bad"}) == 4

    # 1st invalid
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_plus_dict({123: 1, "b": 2, "c": 3})

    # 2nd invalid
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_plus_dict({"a": 1, 123: 2, "c": 3})

    # 3rd invalid
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_bookend_plus_dict({"a": 1, "b": 2, "c": "bad"})


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
