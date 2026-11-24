from abc import ABC
from collections import OrderedDict, deque, namedtuple
from collections.abc import (
    Collection,
    Hashable,
    Mapping,
    Sequence,
    Sized as AbcSized,
)
from enum import Enum
import numbers
from typing import (
    Callable,
    Protocol,
    Sized as TypingSized,
    TypedDict,
    runtime_checkable,
)
import pytest
import type_enforced
from type_enforced import specialized
from type_enforced.enforcer import FunctionMethodEnforcer


class ColorEnum(Enum):
    RED = 1
    BLUE = 2


@runtime_checkable
class Greeter(Protocol):
    def greet(self) -> str: ...


class FriendlyGreeter:
    def greet(self) -> str:
        return "hi"


class VirtualBase(ABC):
    pass


class VirtualImpl:
    pass


VirtualBase.register(VirtualImpl)


class CustomSized:
    def __len__(self) -> int:
        return 7


class MyList(list):
    pass


class MySet(set):
    pass


Point = namedtuple("Point", ["x", "y"])


class UserTD(TypedDict):
    name: str
    age: int


# ---------------------------------------------------------------------------
# 1. Multi-variant collection unions with ABCs, Protocols, and virtual types
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
def fn_list_collection_union(val: list[Collection] | list[int]):
    return val


@type_enforced.Enforcer
def fn_list_sequence_union(val: list[Sequence] | list[int]):
    return val


@type_enforced.Enforcer
def fn_dict_mapping_union(val: dict[str, Mapping] | dict[int, int]):
    return val


@type_enforced.Enforcer
def fn_tuple_collection_union(val: tuple[Collection, ...] | tuple[int, ...]):
    return val


@type_enforced.Enforcer
def fn_set_hashable_union(val: set[Hashable] | set[int]):
    return val


@type_enforced.Enforcer
def fn_list_proto_union(val: list[Greeter] | list[int]):
    return val


@type_enforced.Enforcer
def fn_list_virtual_abc_union(val: list[VirtualBase] | list[int]):
    return val


@type_enforced.Enforcer
def fn_list_integral_union(val: list[numbers.Integral] | list[str]):
    return val


def test_multivariant_unions_with_abcs_and_protocols():
    assert fn_list_collection_union([[1, 2], ColorEnum]) == [[1, 2], ColorEnum]
    assert fn_list_collection_union([1, 2, 3]) == [1, 2, 3]
    with pytest.raises(TypeError):
        fn_list_collection_union([object()])

    assert fn_list_sequence_union([[1], "abc", (2,)]) == [[1], "abc", (2,)]
    assert fn_list_sequence_union([1, 2]) == [1, 2]
    with pytest.raises(TypeError):
        fn_list_sequence_union([{1, 2}])

    assert fn_dict_mapping_union({"a": {"x": 1}}) == {"a": {"x": 1}}
    assert fn_dict_mapping_union({1: 2}) == {1: 2}
    with pytest.raises(TypeError):
        fn_dict_mapping_union({"a": 123})

    assert fn_tuple_collection_union(([1, 2], ColorEnum)) == (
        [1, 2],
        ColorEnum,
    )
    assert fn_tuple_collection_union((1, 2)) == (1, 2)
    with pytest.raises(TypeError):
        fn_tuple_collection_union((object(),))

    assert fn_set_hashable_union({"a", "b"}) == {"a", "b"}
    assert fn_set_hashable_union({1, 2}) == {1, 2}

    g = FriendlyGreeter()
    assert fn_list_proto_union([g]) == [g]
    assert fn_list_proto_union([1, 2]) == [1, 2]
    with pytest.raises(TypeError):
        fn_list_proto_union(["not_a_greeter"])

    v = VirtualImpl()
    assert fn_list_virtual_abc_union([v]) == [v]
    assert fn_list_virtual_abc_union([1, 2]) == [1, 2]
    with pytest.raises(TypeError):
        fn_list_virtual_abc_union(["nope"])

    assert fn_list_integral_union([1, 2, True]) == [1, 2, True]
    assert fn_list_integral_union(["a", "b"]) == ["a", "b"]
    with pytest.raises(TypeError):
        fn_list_integral_union([1.5])


# ---------------------------------------------------------------------------
# 2. Pure Python variant validator edge cases (len > 50 and namedtuple)
# ---------------------------------------------------------------------------
def test_pure_python_variant_validator_subclasses_and_abcs(monkeypatch):
    monkeypatch.setattr(specialized, "_cpp", None)
    specialized._VARIANT_VALIDATOR_CACHE.clear()
    try:
        val_int_str = specialized._compile_py_variant_validator(
            list, {int: None, str: None}, 100
        )
        assert val_int_str([True] * 50) is True
        assert val_int_str([True] * 51) is True
        assert val_int_str([True] * 50 + [1.5]) is False

        val_col_int = specialized._compile_py_variant_validator(
            list, {Collection: None, int: None}, 100
        )
        assert val_col_int([[1]] * 50) is True
        assert val_col_int([[1]] * 51) is True
        assert val_col_int([[1]] * 50 + [object()]) is False

        val_fixed_tuple = specialized._compile_py_variant_validator(
            tuple, (({int: None}, {str: None}), False), 100
        )
        assert val_fixed_tuple(Point(1, "a")) is True
        assert val_fixed_tuple(Point("bad", "a")) is False
    finally:
        specialized._VARIANT_VALIDATOR_CACHE.clear()


# ---------------------------------------------------------------------------
# 3. Container subclasses element validation
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
def fn_list_int(x: list[int]):
    return x


@type_enforced.Enforcer
def fn_dict_str_int(x: dict[str, int]):
    return x


@type_enforced.Enforcer
def fn_tuple_int_int(x: tuple[int, int]):
    return x


@type_enforced.Enforcer
def fn_set_int(x: set[int]):
    return x


@type_enforced.Enforcer
def fn_nested_list_int(x: list[list[int]]):
    return x


def test_container_subclasses_validate_elements():
    assert fn_list_int(MyList([1, 2, 3])) == [1, 2, 3]
    with pytest.raises(TypeError):
        fn_list_int(MyList(["bad"]))

    assert fn_dict_str_int(OrderedDict({"a": 1})) == {"a": 1}
    with pytest.raises(TypeError):
        fn_dict_str_int(OrderedDict({"a": "bad"}))

    assert fn_tuple_int_int(Point(1, 2)) == (1, 2)
    with pytest.raises(TypeError):
        fn_tuple_int_int(Point("bad", "bad"))

    assert fn_set_int(MySet({1, 2})) == {1, 2}
    with pytest.raises(TypeError):
        fn_set_int(MySet({"bad"}))

    assert fn_nested_list_int([MyList([1, 2])]) == [[1, 2]]
    with pytest.raises(TypeError):
        fn_nested_list_int([MyList(["bad"])])


# ---------------------------------------------------------------------------
# 4. TypedDict and Callable in unions
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
def fn_td_or_int(val: UserTD | int):
    return val


@type_enforced.Enforcer
def fn_td_or_none(val: UserTD | None):
    return val


@type_enforced.Enforcer(strict=False)
def fn_td_non_strict(val: UserTD):
    return val


@type_enforced.Enforcer
def fn_list_td_or_int_union(val: list[UserTD | int] | list[str]):
    return val


@type_enforced.Enforcer
def fn_callable_or_none(val: Callable | None):
    return val


@type_enforced.Enforcer
def fn_callable_or_int(val: Callable | int):
    return val


@type_enforced.Enforcer
def fn_list_callable_or_int_union(val: list[Callable | int] | list[str]):
    return val


def test_typeddict_in_unions():
    assert fn_td_or_int(42) == 42
    assert fn_td_or_int({"name": "Ada", "age": 36}) == {
        "name": "Ada",
        "age": 36,
    }
    with pytest.raises(TypeError):
        fn_td_or_int("not_valid")
    with pytest.raises(TypeError):
        fn_td_or_int({"name": "Ada"})
    with pytest.raises(TypeError):
        fn_td_or_int({"name": "Ada", "age": "thirty-six"})

    assert fn_td_or_none(None) is None
    assert fn_td_or_none({"name": "Ada", "age": 36}) == {
        "name": "Ada",
        "age": 36,
    }
    with pytest.raises(TypeError):
        fn_td_or_none(42)
    with pytest.raises(TypeError):
        fn_td_or_none({"name": "Ada"})

    # Non-strict mode should warn without crashing with AttributeError
    assert fn_td_non_strict(42) == 42

    assert fn_list_td_or_int_union([1, {"name": "Ada", "age": 36}]) == [
        1,
        {"name": "Ada", "age": 36},
    ]
    assert fn_list_td_or_int_union(["a", "b"]) == ["a", "b"]
    with pytest.raises(TypeError):
        fn_list_td_or_int_union([{"name": "Ada", "age": "bad"}])


def test_callable_in_unions():
    assert fn_callable_or_none(None) is None
    assert fn_callable_or_none(len) is len
    with pytest.raises(TypeError):
        fn_callable_or_none(123)

    assert fn_callable_or_int(1) == 1
    assert fn_callable_or_int(len) is len
    with pytest.raises(TypeError):
        fn_callable_or_int("bad")

    assert fn_list_callable_or_int_union([1, len]) == [1, len]
    assert fn_list_callable_or_int_union(["a", "b"]) == ["a", "b"]
    with pytest.raises(TypeError):
        fn_list_callable_or_int_union([3.14])


# ---------------------------------------------------------------------------
# 5. typing.Sized vs collections.abc.Sized parity
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
def fn_typing_sized(val: TypingSized):
    return len(val)


@type_enforced.Enforcer
def fn_abc_sized(val: AbcSized):
    return len(val)


def test_typing_sized_and_abc_sized_parity():
    for valid_val, expected_len in [
        ([1, 2], 2),
        (frozenset([1, 2, 3]), 3),
        (deque([1]), 1),
        (ColorEnum, 2),
        (CustomSized(), 7),
    ]:
        assert fn_typing_sized(valid_val) == expected_len
        assert fn_abc_sized(valid_val) == expected_len

    for invalid_val in (123, None, object()):
        with pytest.raises(TypeError):
            fn_typing_sized(invalid_val)
        with pytest.raises(TypeError):
            fn_abc_sized(invalid_val)


# ---------------------------------------------------------------------------
# 6. No unnecessary fallback to __check_type__ on valid calls
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
def fn_const_ret_collection() -> Collection:
    return "hello"


@type_enforced.Enforcer
def fn_const_ret_int() -> int:
    return True


@type_enforced.Enforcer
def fn_collection_or_none(val: Collection | None):
    return val


@type_enforced.Enforcer
def fn_4args_collection(a: int, b: int, c: int, val: Collection):
    return val


@type_enforced.Enforcer
def fn_list_collection(val: list[Collection]):
    return val


def test_no_fallback_to_check_type_on_valid_calls(monkeypatch):
    calls = []
    orig_check_type = FunctionMethodEnforcer.__check_type__

    def spy_check_type(self, obj, expected, key):
        calls.append((self.__fn__.__qualname__, key))
        return orig_check_type(self, obj, expected, key)

    monkeypatch.setattr(
        FunctionMethodEnforcer, "__check_type__", spy_check_type
    )

    assert fn_const_ret_collection() == "hello"
    assert fn_const_ret_int() is True
    assert fn_collection_or_none([1, 2]) == [1, 2]
    assert fn_collection_or_none(ColorEnum) is ColorEnum
    assert fn_4args_collection(1, 2, 3, [1]) == [1]
    assert fn_4args_collection(1, 2, 3, ColorEnum) is ColorEnum
    assert fn_list_collection([[1, 2], ColorEnum]) == [[1, 2], ColorEnum]

    if type_enforced.has_cpp():
        assert fn_callable_or_none(None) is None
        assert fn_td_or_none(None) is None
        assert fn_td_or_int(42) == 42

    assert calls == []


# ---------------------------------------------------------------------------
# 7. Safe set iteration when __instancecheck__ mutates the set
# ---------------------------------------------------------------------------
def test_set_mutation_in_instancecheck_does_not_crash():
    target_set = set()

    class MutatingMeta(type):
        def __instancecheck__(cls, instance):
            target_set.add(999)
            return isinstance(instance, int)

    class MutatingType(metaclass=MutatingMeta):
        pass

    @type_enforced.Enforcer
    def fn_mutating_set(s: set[MutatingType]):
        return s

    target_set.update({1, 2, 3})
    # Should either validate or raise TypeError/RuntimeError cleanly, never segfault
    try:
        fn_mutating_set(target_set)
    except (TypeError, RuntimeError):
        pass
