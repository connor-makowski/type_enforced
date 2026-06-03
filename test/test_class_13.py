from __future__ import annotations
import pytest
import type_enforced


@type_enforced.Enforcer
class my_class:
    def __init__(self):
        self.a = 10

    @type_enforced.Enforcer
    def my_fn(self, b: int):
        pass


mc = my_class()


def test_class_13():
    mc.my_fn(1)

    with pytest.raises(TypeError, match="Type mismatch"):
        mc.my_fn("a")
