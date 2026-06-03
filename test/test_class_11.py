import pytest
import type_enforced
from dataclasses import dataclass


@type_enforced.Enforcer
@dataclass
class Foo:
    bar: int
    baz: str


def test_class_11():
    Foo(bar=1, baz="a")

    with pytest.raises(Exception):
        Foo(bar="a", baz=1)
