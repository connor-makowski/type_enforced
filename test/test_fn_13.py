import type_enforced
from typing import Literal


@type_enforced.Enforcer
def my_fn(a: int | Literal["a"] | Literal["b"]):
    pass


def my_fn_2(a: int | str | Literal["a", "b"]):
    pass


success_1 = True
try:
    my_fn(a="a")
    my_fn(a="b")
    my_fn(a=1)
    my_fn_2(a="a")
    my_fn_2(a="b")
    my_fn_2(a=1)
    # This should work for my_fn_2 because the str type passes even if the Literal fails.
    my_fn_2(a="c")
except:
    success_1 = False

success_2 = False
try:
    my_fn(a="c")
except Exception as e:
    success_2 = True

if success_1 and success_2:
    print("test_fn_13.py passed")
else:
    print("test_fn_13.py failed")
