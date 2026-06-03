import pytest
import type_enforced


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
    def __init__(self, use_class: Foo) -> None:
        self.object = use_class


def test_class_03():
    Baz(Foo())
    Baz(Bar())

    with pytest.raises(Exception):
        Baz(Bum())
