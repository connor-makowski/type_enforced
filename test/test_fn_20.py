import pytest
import type_enforced
import sys
from collections import OrderedDict


def my_fn(a: int, b: int | str, c: int) -> None:
    return None


class MyClass:
    def my_fn(self, a: int, b: int | str, c: int) -> None:
        return None


my_ordered_dict = OrderedDict()

# Enforce all annotated functions/methods in this module at import time
type_enforced.Enforcer(sys.modules[__name__])


def test_fn_20():
    my_fn(a=1, b=2, c=3)
    my_fn(a=1, b="2", c=3)

    my_class = MyClass()
    my_class.my_fn(a=1, b=2, c=3)
    my_class.my_fn(a=1, b="2", c=3)

    with pytest.raises(Exception):
        my_fn(a=1, b=2, c="3")
