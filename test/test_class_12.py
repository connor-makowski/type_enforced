import pytest
from test_class_12_utils.bar import Bar, foo
from test_class_12_utils.baz import Baz


def test_class_12():
    foo(Baz())
    foo(Bar())

    with pytest.raises(Exception):
        foo(1)
