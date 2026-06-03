import pytest
import type_enforced
from typing import Sized


@type_enforced.Enforcer
def my_fn(a: Sized) -> int:
    return a.__len__()


def test_fn_12():
    my_fn(a=["a"])
    my_fn(a={"a": 1})
    my_fn(a=(1,))
    my_fn(a={1})
    my_fn(a="a")
    my_fn(a=memoryview(b"abc"))
    my_fn(a=b"abc")
    my_fn(a=bytearray(b"abc"))
    my_fn(a=range(1))

    with pytest.raises(TypeError, match="Type mismatch"):
        my_fn(a=1)
