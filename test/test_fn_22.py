from type_enforced import Enforcer
from unittest.mock import MagicMock


# A magic mock test to ensure that the type enforcement works with mocks
@Enforcer
def my_fn(a: int, b: int | str = 2, c: int = 3) -> None:
    pass


my_fn(a=MagicMock(spec=int), b=MagicMock(spec=str), c=3)

success = True

try:
    my_fn(a=MagicMock(spec=int), b=MagicMock(spec=str), c=3)
except TypeError as e:
    success = False

try:
    my_fn(a=MagicMock(spec=str), b=MagicMock(spec=str), c=3)
    success = False
except TypeError as e:
    pass

if success:
    print("test_fn_22.py passed")
else:
    print("test_fn_22.py failed")
