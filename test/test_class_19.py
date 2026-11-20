from collections.abc import Collection
from dataclasses import dataclass
from enum import Enum
import pytest
import type_enforced


class SomeEnum(Enum):
    ONE = 1
    TWO = 2


class AnotherEnum(Enum):
    A = "a"
    B = "b"


class RegularNonCollectionClass:
    pass


@type_enforced.Enforcer
@dataclass
class DataclassCollection:
    val: Collection


@type_enforced.Enforcer
class NormalClassCollection:
    def __init__(self, val: Collection):
        self.val = val


@type_enforced.Enforcer
def enforce_collection(val: Collection):
    return val


@type_enforced.Enforcer
def enforce_list_of_collections(val: list[Collection]):
    return val


def test_dataclass_enum_collection():
    # Valid enum passed to dataclass typed with Collection
    d1 = DataclassCollection(SomeEnum)
    assert d1.val is SomeEnum

    d2 = DataclassCollection(AnotherEnum)
    assert d2.val is AnotherEnum

    # Valid standard collection passed to dataclass
    d3 = DataclassCollection([1, 2, 3])
    assert d3.val == [1, 2, 3]

    # Non-collection class passed to dataclass should raise TypeError
    with pytest.raises(TypeError):
        DataclassCollection(RegularNonCollectionClass)

    # Primitive non-collection passed to dataclass should raise TypeError
    with pytest.raises(TypeError):
        DataclassCollection(123)


def test_normal_class_enum_collection():
    c1 = NormalClassCollection(SomeEnum)
    assert c1.val is SomeEnum

    with pytest.raises(TypeError):
        NormalClassCollection(RegularNonCollectionClass)

    with pytest.raises(TypeError):
        NormalClassCollection(123)


def test_function_enum_collection():
    assert enforce_collection(SomeEnum) is SomeEnum
    assert enforce_collection([1, 2]) == [1, 2]

    with pytest.raises(TypeError):
        enforce_collection(RegularNonCollectionClass)

    with pytest.raises(TypeError):
        enforce_collection(123)


def test_nested_collection_with_enum():
    result = enforce_list_of_collections([SomeEnum, [1, 2]])
    assert result == [SomeEnum, [1, 2]]

    with pytest.raises(TypeError):
        enforce_list_of_collections([SomeEnum, 123])
