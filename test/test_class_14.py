from __future__ import annotations
import pytest
import type_enforced


@type_enforced.Enforcer(strict=True)
class my_class:
    def __init__(self):
        pass

    def fn_1(self, a: int):
        pass

    @type_enforced.Enforcer(strict=False)
    def fn_2(self, a: int):
        pass


@type_enforced.Enforcer(strict=False)
class my_class_2:
    def __init__(self):
        pass

    def fn_1(self, a: int):
        pass

    @type_enforced.Enforcer(strict=True)
    def fn_2(self, a: int):
        pass


mc = my_class()
mc_2 = my_class_2()


def test_class_14():
    # strict=False methods warn instead of raise
    mc.fn_2("a")
    mc_2.fn_1("a")

    with pytest.raises(Exception):
        mc.fn_1("a")
    with pytest.raises(Exception):
        mc_2.fn_2("a")
