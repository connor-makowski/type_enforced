import pytest
import type_enforced
from dataclasses import dataclass


# 1. Basic @FastEnforcer without parentheses
@type_enforced.FastEnforcer
def fn_fast_noparens(items: list[int], name: str) -> int:
    return len(items)


def test_fast_enforcer_noparens():
    # Valid call
    assert fn_fast_noparens([1, 2, 3], "test") == 3

    # Scalar check fails on mismatch
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `name`"
    ):
        fn_fast_noparens([1, 2, 3], 123)

    # First item is int (valid), subsequent item is invalid str -> passes because of O(1) sampling ('first')
    assert fn_fast_noparens([1, "invalid_second_item", 3], "test") == 3

    # First item is invalid str -> raises TypeError
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `items"
    ):
        fn_fast_noparens(["invalid_first_item", 2, 3], "test")


# 2. @FastEnforcer() with parentheses
@type_enforced.FastEnforcer()
def fn_fast_parens(items: list[int]) -> int:
    return len(items)


def test_fast_enforcer_parens():
    assert fn_fast_parens([10, "bad", 30]) == 3
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `items"
    ):
        fn_fast_parens(["bad", 20, 30])


# 3. Class, staticmethod, classmethod, and method enforcement
@type_enforced.FastEnforcer
class FastService:
    def __init__(self, tag: str):
        self.tag = tag

    def process_items(self, items: list[int]) -> str:
        return f"{self.tag}:{len(items)}"

    @staticmethod
    def static_process(items: list[str]) -> int:
        return len(items)

    @classmethod
    def class_process(cls, items: list[float]) -> int:
        return len(items)


def test_fast_enforcer_class():
    service = FastService("prod")
    assert service.process_items([1, "bad", 3]) == "prod:3"
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `items"
    ):
        service.process_items(["bad", 2, 3])

    assert FastService.static_process(["valid_str", 123]) == 2
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `items"
    ):
        FastService.static_process([123, "valid_str"])

    assert FastService.class_process([1.0, "bad"]) == 2
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `items"
    ):
        FastService.class_process(["bad", 2.0])


# 4. Dataclass enforcement
@type_enforced.FastEnforcer
@dataclass
class FastData:
    id: int
    tags: list[str]


def test_fast_enforcer_dataclass():
    data = FastData(1, ["tag1", 123])
    assert data.id == 1
    assert data.tags == ["tag1", 123]

    with pytest.raises(TypeError, match="Type mismatch"):
        FastData("not_an_int", ["tag1"])


# 5. Allowed fast sampling options: 'last', 'log', 0
@type_enforced.FastEnforcer(iterable_sample_pct="last")
def fn_fast_last(items: list[int]) -> int:
    return len(items)


def test_fast_enforcer_last():
    # Last item is valid int, first item is invalid -> passes with 'last'
    assert fn_fast_last(["invalid_first", "invalid_mid", 42]) == 3

    # Last item is invalid -> raises TypeError
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `items"
    ):
        fn_fast_last([1, 2, "invalid_last"])


@type_enforced.FastEnforcer(iterable_sample_pct="log")
def fn_fast_log(items: list[int]) -> int:
    return len(items)


def test_fast_enforcer_log():
    assert fn_fast_log([1, 2, 3, 4, 5]) == 5
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `items"
    ):
        fn_fast_log(["bad", 2, 3, 4, 5])


@type_enforced.FastEnforcer(iterable_sample_pct=0)
def fn_fast_zero(items: list[int]) -> int:
    return len(items)


def test_fast_enforcer_zero():
    assert fn_fast_zero([10, 20, 30]) == 3


# 6. Disallowed iterable_sample_pct in FastEnforcer
def test_fast_enforcer_disallowed_options():
    with pytest.raises(
        TypeError, match="FastEnforcer only supports fast sampling options"
    ):

        @type_enforced.FastEnforcer(iterable_sample_pct=100)
        def fn_disallowed_100(x: list[int]) -> int:
            return len(x)

    with pytest.raises(
        TypeError, match="FastEnforcer only supports fast sampling options"
    ):

        @type_enforced.FastEnforcer(iterable_sample_pct=50)
        def fn_disallowed_50(x: list[int]) -> int:
            return len(x)

    with pytest.raises(
        TypeError, match="FastEnforcer only supports fast sampling options"
    ):

        @type_enforced.FastEnforcer(iterable_sample_pct="middle")
        def fn_disallowed_middle(x: list[int]) -> int:
            return len(x)

    with pytest.raises(
        TypeError, match="FastEnforcer only supports fast sampling options"
    ):

        @type_enforced.FastEnforcer(iterable_sample_pct=True)
        def fn_disallowed_bool(x: list[int]) -> int:
            return len(x)

    with pytest.raises(
        TypeError, match="FastEnforcer only supports fast sampling options"
    ):

        @type_enforced.FastEnforcer(iterable_sample_pct=3.14)
        def fn_disallowed_float(x: list[int]) -> int:
            return len(x)


# 7. Additional configuration parameters
def test_fast_enforcer_strict_false():
    @type_enforced.FastEnforcer(strict=False)
    def fn_lenient(a: int) -> int:
        return a

    # Does not raise on mismatch when strict=False
    assert fn_lenient("not_an_int") == "not_an_int"


def test_fast_enforcer_only_typed():
    with pytest.raises(TypeError, match="Untyped variable `b`"):

        @type_enforced.FastEnforcer(only_typed=True)
        def fn_untyped(a: int, b):
            return a


def test_fast_enforcer_disabled():
    @type_enforced.FastEnforcer(enabled=False)
    def fn_disabled(a: int) -> int:
        return a

    assert fn_disabled("not_an_int") == "not_an_int"
