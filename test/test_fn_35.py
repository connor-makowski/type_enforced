import functools
import inspect
from enum import Enum, IntEnum, StrEnum, Flag, auto
from typing import Literal, Callable, Sized, Any, Optional
import pytest
import type_enforced


# ---------------------------------------------------------------------------
# 1. Complex Signatures: Positional-Only, Keyword-Only, Variadics
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
def fn_complex_sig(
    p0: int,
    p1: str,
    /,
    normal: float,
    *args: int,
    kw_req: str,
    kw_opt: int = 10,
    **kwargs: bool,
) -> tuple:
    return (p0, p1, normal, args, kw_req, kw_opt, kwargs)


def test_complex_signatures():
    # Valid call with all features exercised
    res = fn_complex_sig(1, "a", 2.5, 3, 4, kw_req="req", flag=True)
    assert res == (1, "a", 2.5, (3, 4), "req", 10, {"flag": True})

    # Positional-only parameter type mismatch
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `p0`"
    ):
        fn_complex_sig("bad", "a", 2.5, kw_req="req")

    # Regular parameter type mismatch
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `normal`"
    ):
        fn_complex_sig(1, "a", "bad_float", kw_req="req")

    # Variadic *args type mismatch
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_complex_sig(1, "a", 2.5, 3, "bad_arg", kw_req="req")

    # Keyword-only required parameter missing
    with pytest.raises(TypeError):
        fn_complex_sig(1, "a", 2.5)

    # Keyword-only parameter type mismatch
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `kw_req`"
    ):
        fn_complex_sig(1, "a", 2.5, kw_req=123)

    # Variadic **kwargs type mismatch
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_complex_sig(1, "a", 2.5, kw_req="req", flag="not_a_bool")


# ---------------------------------------------------------------------------
# 2. Zero-Argument Functions & Void/Implicit Return Values
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
def fn_zero_args() -> int:
    return 42


@type_enforced.Enforcer
def fn_void_implicit() -> None:
    pass


@type_enforced.Enforcer
def fn_void_explicit() -> None:
    return None


@type_enforced.Enforcer
def fn_void_invalid() -> None:
    return "unexpected"  # type: ignore


@type_enforced.Enforcer
def fn_union_return(flag: bool) -> int | None:
    return 100 if flag else None


@type_enforced.Enforcer
def fn_union_return_invalid() -> int | None:
    return "invalid_string"  # type: ignore


def test_zero_args_and_returns():
    assert fn_zero_args() == 42
    assert fn_void_implicit() is None
    assert fn_void_explicit() is None

    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `return`"
    ):
        fn_void_invalid()

    assert fn_union_return(True) == 100
    assert fn_union_return(False) is None

    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `return`"
    ):
        fn_union_return_invalid()


# ---------------------------------------------------------------------------
# 3. Builtin Subclasses & Numeric Type Hierarchy
# ---------------------------------------------------------------------------
class CustomInt(int):
    pass


class CustomStr(str):
    pass


class CustomList(list):
    pass


class CustomDict(dict):
    pass


@type_enforced.Enforcer
def fn_accepts_builtin_int(x: int) -> int:
    return x


@type_enforced.Enforcer
def fn_accepts_custom_int(x: CustomInt) -> CustomInt:
    return x


@type_enforced.Enforcer
def fn_accepts_builtin_str(s: str) -> str:
    return s


@type_enforced.Enforcer
def fn_accepts_custom_str(s: CustomStr) -> CustomStr:
    return s


@type_enforced.Enforcer
def fn_accepts_builtin_list(items: list) -> int:
    return len(items)


@type_enforced.Enforcer
def fn_accepts_custom_list(items: CustomList) -> int:
    return len(items)


@type_enforced.Enforcer
def fn_accepts_builtin_dict(d: dict) -> int:
    return len(d)


@type_enforced.Enforcer
def fn_accepts_custom_dict(d: CustomDict) -> int:
    return len(d)


@type_enforced.Enforcer
def fn_accepts_bool(b: bool) -> bool:
    return b


def test_builtin_subclasses_and_bool_hierarchy():
    # Subclasses pass when parent type is expected
    c_int = CustomInt(10)
    assert fn_accepts_builtin_int(c_int) == 10
    assert fn_accepts_custom_int(c_int) == 10

    # Parent type fails when specific subclass is expected
    with pytest.raises(TypeError, match="Type mismatch for typed variable `x`"):
        fn_accepts_custom_int(10)

    # Custom string subclass
    c_str = CustomStr("hello")
    assert fn_accepts_builtin_str(c_str) == "hello"
    assert fn_accepts_custom_str(c_str) == "hello"
    with pytest.raises(TypeError, match="Type mismatch for typed variable `s`"):
        fn_accepts_custom_str("raw_str")

    # Custom list subclass
    c_list = CustomList([1, 2, 3])
    assert fn_accepts_builtin_list(c_list) == 3
    assert fn_accepts_custom_list(c_list) == 3
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `items`"
    ):
        fn_accepts_custom_list([1, 2, 3])

    # Custom dict subclass
    c_dict = CustomDict({"a": 1})
    assert fn_accepts_builtin_dict(c_dict) == 1
    assert fn_accepts_custom_dict(c_dict) == 1
    with pytest.raises(TypeError, match="Type mismatch for typed variable `d`"):
        fn_accepts_custom_dict({"a": 1})

    # In Python, bool is a subclass of int: True passes int check
    assert fn_accepts_builtin_int(True) is True
    assert fn_accepts_builtin_int(False) is False

    # But int does NOT pass bool check
    assert fn_accepts_bool(True) is True
    assert fn_accepts_bool(False) is False
    with pytest.raises(TypeError, match="Type mismatch for typed variable `b`"):
        fn_accepts_bool(1)


# ---------------------------------------------------------------------------
# 4. Empty Collections & Deeply Nested Generics
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
def fn_empty_list(items: list[int]) -> int:
    return len(items)


@type_enforced.Enforcer
def fn_empty_dict(data: dict[str, int]) -> int:
    return len(data)


@type_enforced.Enforcer
def fn_empty_set(tags: set[str]) -> int:
    return len(tags)


@type_enforced.Enforcer
def fn_empty_tuple_type(t: tuple[()]) -> tuple[()]:
    return t


@type_enforced.Enforcer
def fn_ellipsis_tuple(t: tuple[int, ...]) -> int:
    return len(t)


@type_enforced.Enforcer
def fn_fixed_tuple(t: tuple[int, str, float]) -> tuple:
    return t


@type_enforced.Enforcer
def fn_deeply_nested(
    payload: dict[str, list[dict[str, tuple[int, ...]]]],
) -> int:
    total = 0
    for items in payload.values():
        for d in items:
            for tup in d.values():
                total += sum(tup)
    return total


def test_empty_collections_and_nested_generics():
    # Empty collections must pass validation cleanly
    assert fn_empty_list([]) == 0
    assert fn_empty_list([1, 2, 3]) == 3
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_empty_list([1, "bad"])

    assert fn_empty_dict({}) == 0
    assert fn_empty_dict({"a": 1, "b": 2}) == 2
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_empty_dict({"a": "bad"})
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_empty_dict({1: 1})

    assert fn_empty_set(set()) == 0
    assert fn_empty_set({"a", "b"}) == 2
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_empty_set({1, 2})

    assert fn_empty_tuple_type(()) == ()
    with pytest.raises(TypeError):
        fn_empty_tuple_type((1,))

    assert fn_ellipsis_tuple(()) == 0
    assert fn_ellipsis_tuple((1, 2, 3)) == 3
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_ellipsis_tuple((1, "bad"))

    assert fn_fixed_tuple((1, "a", 3.14)) == (1, "a", 3.14)
    with pytest.raises(TypeError):
        fn_fixed_tuple(())
    with pytest.raises(TypeError):
        fn_fixed_tuple((1, "a"))
    with pytest.raises(TypeError):
        fn_fixed_tuple((1, "a", 3.14, "extra"))

    # Deeply nested generic with empty and populated sub-containers
    valid_nested = {
        "group_a": [{"ids": ()}, {"ids": (10, 20)}],
        "group_b": [],
        "group_c": [{"ids": (30,)}],
    }
    assert fn_deeply_nested(valid_nested) == 60

    invalid_nested = {
        "group_a": [{"ids": (10, "bad")}],
    }
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_deeply_nested(invalid_nested)


# ---------------------------------------------------------------------------
# 5. Enum Types & Flags
# ---------------------------------------------------------------------------
class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"


class Level(IntEnum):
    LOW = 1
    HIGH = 2


class Permission(Flag):
    READ = auto()
    WRITE = auto()
    EXEC = auto()


@type_enforced.Enforcer
def fn_enums(
    r: Role, l: Level, p: Permission
) -> tuple[Role, Level, Permission]:
    return (r, l, p)


def test_enum_types_and_flags():
    # Valid Enum instances
    res = fn_enums(Role.ADMIN, Level.HIGH, Permission.READ | Permission.WRITE)
    assert res == (Role.ADMIN, Level.HIGH, Permission.READ | Permission.WRITE)

    # Raw string instead of StrEnum instance
    with pytest.raises(TypeError, match="Type mismatch for typed variable `r`"):
        fn_enums("admin", Level.HIGH, Permission.READ)

    # Raw integer instead of IntEnum instance
    with pytest.raises(TypeError, match="Type mismatch for typed variable `l`"):
        fn_enums(Role.ADMIN, 2, Permission.READ)

    # Invalid flag type
    with pytest.raises(TypeError, match="Type mismatch for typed variable `p`"):
        fn_enums(Role.ADMIN, Level.LOW, "read")


# ---------------------------------------------------------------------------
# 6. Literals with Falsy Values, Stacked Unions & Types
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
def fn_literal_falsy(val: Literal[0, False, "", None]) -> str:
    return f"val:{val}"


@type_enforced.Enforcer
def fn_literal_stacked(
    color: Literal["red", "green"] | Literal["blue", "yellow"] | None,
) -> str:
    return str(color)


@type_enforced.Enforcer
def fn_literal_with_type(mode: Literal["auto", "manual"] | int | None) -> str:
    return f"mode:{mode}"


def test_literals_falsy_stacked_and_unions():
    # All falsy literal variants must match their exact literal value
    assert fn_literal_falsy(0) == "val:0"
    assert fn_literal_falsy(False) == "val:False"
    assert fn_literal_falsy("") == "val:"
    assert fn_literal_falsy(None) == "val:None"

    # Non-matching truthy and other falsy values fail
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_literal_falsy(1)
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_literal_falsy(True)
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_literal_falsy("non_empty")
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_literal_falsy([])

    # Stacked literals
    assert fn_literal_stacked("red") == "red"
    assert fn_literal_stacked("yellow") == "yellow"
    assert fn_literal_stacked(None) == "None"
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_literal_stacked("purple")

    # Literal combined with type
    assert fn_literal_with_type("auto") == "mode:auto"
    assert fn_literal_with_type("manual") == "mode:manual"
    assert fn_literal_with_type(42) == "mode:42"
    assert fn_literal_with_type(None) == "mode:None"
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_literal_with_type("invalid_mode")
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_literal_with_type(3.14)


# ---------------------------------------------------------------------------
# 7. Callable and Sized Protocol Types
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
def fn_takes_callable(cb: Callable, arg: int) -> int:
    return cb(arg)


@type_enforced.Enforcer
def fn_takes_sized(s: Sized) -> int:
    return len(s)


def sample_generator(n):
    for i in range(n):
        yield i


def test_callable_and_sized_typing():
    # Standard functions, lambdas, and builtins pass Callable
    assert fn_takes_callable(lambda x: x * 2, 5) == 10
    assert fn_takes_callable(abs, -42) == 42

    def local_fn(x: int) -> int:
        return x + 1

    assert fn_takes_callable(local_fn, 7) == 8

    # Non-callables fail
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `cb`"
    ):
        fn_takes_callable(123, 5)
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `cb`"
    ):
        fn_takes_callable("not_a_func", 5)

    # Sized types
    assert fn_takes_sized([1, 2, 3]) == 3
    assert fn_takes_sized((1, 2)) == 2
    assert fn_takes_sized({"a": 1}) == 1
    assert fn_takes_sized({10, 20, 30}) == 3
    assert fn_takes_sized("hello") == 5
    assert fn_takes_sized(b"bytes") == 5
    assert fn_takes_sized(bytearray(b"bytearray")) == 9
    assert fn_takes_sized(memoryview(b"mem")) == 3
    assert fn_takes_sized(range(10)) == 10

    # Non-sized types fail
    with pytest.raises(TypeError, match="Type mismatch for typed variable `s`"):
        fn_takes_sized(123)
    with pytest.raises(TypeError, match="Type mismatch for typed variable `s`"):
        fn_takes_sized(None)


# ---------------------------------------------------------------------------
# 8. Higher-Order Functions & Callable Returns
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
def make_multiplier(factor: int) -> Callable:
    def multiplier(x: int) -> int:
        return x * factor

    return multiplier


def test_higher_order_functions():
    mult3 = make_multiplier(3)
    assert mult3(10) == 30

    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `factor`"
    ):
        make_multiplier("bad_factor")


# ---------------------------------------------------------------------------
# 9. Decorator Chaining & Introspection Metadata Preservation
# ---------------------------------------------------------------------------
def custom_wrapper(fn):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        return fn(*args, **kwargs)

    return inner


# When custom wrapper is on top of Enforcer: Enforcer enforces types directly
@custom_wrapper
@type_enforced.Enforcer
def fn_with_metadata(x: int, y: str = "default") -> str:
    """Documented function docstring."""
    return f"{x}:{y}"


def test_decorator_chaining_and_metadata():
    assert fn_with_metadata(5) == "5:default"
    assert fn_with_metadata(5, "custom") == "5:custom"

    with pytest.raises(TypeError, match="Type mismatch for typed variable `x`"):
        fn_with_metadata("bad")

    # Verify standard function metadata is preserved
    assert fn_with_metadata.__name__ == "fn_with_metadata"
    assert fn_with_metadata.__doc__ == "Documented function docstring."

    # Verify inspect.signature
    sig = inspect.signature(fn_with_metadata)
    assert "x" in sig.parameters
    assert "y" in sig.parameters
    assert sig.parameters["x"].annotation is int
    assert sig.parameters["y"].default == "default"


# ---------------------------------------------------------------------------
# 10. Only-Typed Mode & Strict/Non-Strict Modes
# ---------------------------------------------------------------------------
def test_only_typed_and_strict_modes():
    # Fully annotated function passes with only_typed=True
    @type_enforced.Enforcer(only_typed=True)
    def fn_fully_typed(a: int, b: str) -> bool:
        return len(b) == a

    assert fn_fully_typed(3, "abc") is True

    # Function missing return annotation raises in only_typed mode
    with pytest.raises(
        TypeError, match="Untyped return value found in function/method"
    ):

        @type_enforced.Enforcer(only_typed=True)
        def fn_missing_return(a: int):
            return a

    # Function missing parameter annotation raises in only_typed mode
    with pytest.raises(TypeError, match="Untyped variable `b` found"):

        @type_enforced.Enforcer(only_typed=True)
        def fn_missing_param(a: int, b) -> int:
            return a

    # Non-strict mode does not raise TypeError on mismatch
    @type_enforced.Enforcer(strict=False)
    def fn_non_strict(x: int) -> int:
        return x

    assert fn_non_strict("not_an_int") == "not_an_int"
