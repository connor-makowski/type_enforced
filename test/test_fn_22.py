import pytest
from type_enforced import Enforcer
from unittest.mock import MagicMock


@Enforcer
def my_fn(a: int, b: int | str = 2, c: int = 3) -> None:
    pass


def test_fn_22():
    my_fn(a=MagicMock(spec=int), b=MagicMock(spec=str), c=3)

    with pytest.raises(TypeError):
        my_fn(a=MagicMock(spec=str), b=MagicMock(spec=str), c=3)
