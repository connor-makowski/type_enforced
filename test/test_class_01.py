import pytest
import type_enforced


class my_class:
    def __init__(self):
        self.a = 10

    @type_enforced.Enforcer
    def my_fn(self, b: int):
        pass


mc = my_class()


def test_class_01():
    with pytest.raises(TypeError, match="Type mismatch"):
        mc.my_fn("a")
