import pytest
import typing
import type_enforced


class Animal:
    def __init__(self) -> None:
        pass


class Dog(Animal):
    def __init__(self) -> None:
        super().__init__()


class Vehicle:
    def __init__(self) -> None:
        pass


@type_enforced.Enforcer
def make_animal(cls: type[Animal]) -> Animal:
    return cls()


@type_enforced.Enforcer
def make_typing_animal(cls: typing.Type[Animal]) -> Animal:
    return cls()


@type_enforced.Enforcer
def make_either(cls: type[Animal] | type[Vehicle]):
    return cls()


@type_enforced.Enforcer
def make_nested_union(cls: type[Animal | Vehicle]):
    return cls()


@type_enforced.Enforcer
def make_any_class(cls: type):
    return cls()


@type_enforced.Enforcer
def make_any_typing_class(cls: typing.Type):
    return cls()


@type_enforced.Enforcer
def make_any_generic_class(cls: type[typing.Any]):
    return cls()


@type_enforced.Enforcer
def get_animal_class(return_valid: bool) -> type[Animal]:
    if return_valid:
        return Animal
    return Vehicle


@type_enforced.Enforcer
def get_animal_class_bad_instance() -> type[Animal]:
    return Animal()


def test_builtin_type_single():
    inst = make_animal(Animal)
    assert isinstance(inst, Animal)

    # Subclasses of uninitialized classes are not allowed by design
    with pytest.raises(TypeError, match="Type mismatch"):
        make_animal(Dog)

    # Unrelated classes should fail
    with pytest.raises(TypeError, match="Type mismatch"):
        make_animal(Vehicle)

    # Instances should fail
    with pytest.raises(TypeError, match="Type mismatch"):
        make_animal(Animal())

    # Primitive types should fail
    with pytest.raises(TypeError, match="Type mismatch"):
        make_animal(123)

    with pytest.raises(TypeError, match="Type mismatch"):
        make_animal("Animal")


def test_typing_type_equivalence():
    inst1 = make_animal(Animal)
    inst2 = make_typing_animal(Animal)
    assert isinstance(inst1, Animal)
    assert isinstance(inst2, Animal)

    with pytest.raises(TypeError, match="Type mismatch"):
        make_typing_animal(Dog)

    with pytest.raises(TypeError, match="Type mismatch"):
        make_typing_animal(Animal())


def test_builtin_type_union():
    a = make_either(Animal)
    v = make_either(Vehicle)
    assert isinstance(a, Animal)
    assert isinstance(v, Vehicle)

    with pytest.raises(TypeError, match="Type mismatch"):
        make_either(Dog)

    with pytest.raises(TypeError, match="Type mismatch"):
        make_either(Animal())


def test_builtin_type_nested_union():
    a = make_nested_union(Animal)
    v = make_nested_union(Vehicle)
    assert isinstance(a, Animal)
    assert isinstance(v, Vehicle)

    with pytest.raises(TypeError, match="Type mismatch"):
        make_nested_union(Dog)

    with pytest.raises(TypeError, match="Type mismatch"):
        make_nested_union(Vehicle())


def test_unsubscripted_type_and_type_any():
    assert isinstance(make_any_class(Animal), Animal)
    assert isinstance(make_any_class(Dog), Dog)
    assert isinstance(make_any_class(Vehicle), Vehicle)

    assert isinstance(make_any_typing_class(Animal), Animal)
    assert isinstance(make_any_generic_class(Animal), Animal)

    with pytest.raises(TypeError, match="Type mismatch"):
        make_any_class(Animal())

    with pytest.raises(TypeError, match="Type mismatch"):
        make_any_typing_class(Animal())

    with pytest.raises(TypeError, match="Type mismatch"):
        make_any_generic_class(Animal())


def test_builtin_type_return():
    assert get_animal_class(True) is Animal

    with pytest.raises(TypeError, match="Type mismatch"):
        get_animal_class(False)

    with pytest.raises(TypeError, match="Type mismatch"):
        get_animal_class_bad_instance()
