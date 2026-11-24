from collections.abc import Collection
from dataclasses import dataclass
from enum import Enum
from typing import Self
import pytest
import type_enforced
from type_enforced.enforcer import FunctionMethodEnforcer


class StatusEnum(Enum):
    OK = 1
    ERR = 2


class PlainClass:
    pass


@type_enforced.Enforcer
@dataclass
class DataclassCollection:
    val: Collection


@type_enforced.Enforcer
class Node:
    def merge(self, other: Self | int) -> Self | str:
        if isinstance(other, int):
            return "merged_int"
        return self

    def merge_collection(self, other: Self | Collection) -> Self | Collection:
        return other

    def bad_return(self) -> Self | str:
        return 123  # type: ignore


@type_enforced.Enforcer
class Box:
    @classmethod
    def create(cls) -> Self:
        return cls()

    @classmethod
    def create_many(cls, a: int, b: int, c: int) -> Self:
        return cls()

    @classmethod
    def create_bad(cls, a: int, b: int, c: int) -> Self:
        return 123  # type: ignore


class SubBox(Box):
    pass


def test_dataclass_collection_does_not_fallback_to_check_type(monkeypatch):
    calls = []
    orig_check_type = FunctionMethodEnforcer.__check_type__

    def spy_check_type(self, obj, expected, key):
        calls.append((self.__fn__.__qualname__, key))
        return orig_check_type(self, obj, expected, key)

    monkeypatch.setattr(
        FunctionMethodEnforcer, "__check_type__", spy_check_type
    )

    d1 = DataclassCollection([1, 2, 3])
    assert d1.val == [1, 2, 3]
    d2 = DataclassCollection(StatusEnum)
    assert d2.val is StatusEnum
    assert calls == []

    with pytest.raises(TypeError):
        DataclassCollection(PlainClass)
    with pytest.raises(TypeError):
        DataclassCollection(123)


def test_self_in_unions():
    n = Node()
    assert n.merge(1) == "merged_int"
    assert n.merge(n) is n

    with pytest.raises(TypeError):
        n.merge("bad")  # type: ignore

    with pytest.raises(TypeError):
        n.bad_return()

    assert n.merge_collection(n) is n
    assert n.merge_collection(StatusEnum) is StatusEnum
    assert n.merge_collection([1, 2]) == [1, 2]
    with pytest.raises(TypeError):
        n.merge_collection(PlainClass)  # type: ignore


def test_classmethod_self_no_fallback(monkeypatch):
    calls = []
    orig_check_type = FunctionMethodEnforcer.__check_type__

    def spy_check_type(self, obj, expected, key):
        calls.append((self.__fn__.__qualname__, key))
        return orig_check_type(self, obj, expected, key)

    monkeypatch.setattr(
        FunctionMethodEnforcer, "__check_type__", spy_check_type
    )

    b1 = Box.create()
    assert isinstance(b1, Box)
    b2 = Box.create_many(1, 2, 3)
    assert isinstance(b2, Box)

    sb1 = SubBox.create()
    assert isinstance(sb1, SubBox)
    sb2 = SubBox.create_many(1, 2, 3)
    assert isinstance(sb2, SubBox)

    assert calls == []

    with pytest.raises(TypeError):
        Box.create_bad(1, 2, 3)
