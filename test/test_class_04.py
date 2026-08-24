import pytest
import type_enforced
from typing import Type


class Foo:
    def __init__(self) -> None:
        pass


class Bar(Foo):
    def __init__(self) -> None:
        super().__init__()


class Bum:
    def __init__(self) -> None:
        pass


@type_enforced.Enforcer
class Baz:
    def __init__(self, use_class: Type[Foo]) -> None:
        self.object = use_class


@type_enforced.Enforcer
class BazBuiltin:
    def __init__(self, use_class: type[Foo]) -> None:
        self.object = use_class


def test_class_04():
    Baz(Foo)

    with pytest.raises(Exception):
        Baz(Foo())
    with pytest.raises(Exception):
        Baz(Bar)
    with pytest.raises(Exception):
        Baz(Bum)

    BazBuiltin(Foo)

    with pytest.raises(Exception):
        BazBuiltin(Foo())
    with pytest.raises(Exception):
        BazBuiltin(Bar)
    with pytest.raises(Exception):
        BazBuiltin(Bum)
