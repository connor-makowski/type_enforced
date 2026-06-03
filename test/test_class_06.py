import pytest
import type_enforced


class Foo:
    @type_enforced.Enforcer
    @classmethod
    def add(self, a: int, b: int) -> int:
        return a + b

    @type_enforced.Enforcer
    @staticmethod
    def subtract(a: int, b: int) -> int:
        return a - b


def test_class_06():
    assert Foo.add(1, 2) == 3
    assert Foo.subtract(4, 3) == 1

    with pytest.raises(Exception):
        Foo.add(1, 2.0)
    with pytest.raises(Exception):
        Foo.subtract(1, 2.0)
