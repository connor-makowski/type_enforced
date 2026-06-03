import pytest
import type_enforced


class Foo:
    @type_enforced.Enforcer
    def __init__(self, object: "Bar") -> None:
        pass


class Bar:
    def __init__(self) -> None:
        pass


class Baz:
    def __init__(self) -> None:
        pass


def test_class_15():
    Foo(Bar())

    with pytest.raises(Exception):
        Baz(Baz())
