import type_enforced
from typing import Literal


@type_enforced.Enforcer
def my_fn(a: Literal["a", "b"]):
    pass


success_1 = True
try:
    my_fn(a="a")
    my_fn(a="b")
except:
    success_1 = False

success_2 = False
try:
    my_fn(a="c")
except Exception as e:
    if "Literal validation error" in str(e):
        success_2 = True

if success_1 and success_2:
    print("test_fn_13.py passed")
else:
    print("test_fn_13.py failed")
