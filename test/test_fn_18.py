import type_enforced
from typing import Literal


try:

    @type_enforced.Enforcer
    def my_fn(a: Literal["bar"] | int) -> None:
        pass

    success = True
except:
    success = False

try:
    my_fn("bar")  # Passes
    my_fn(1)  # Passes
except:
    success = False


if success:
    print(f"test_fn_18.py passed")
else:
    print(f"test_fn_18.py failed")
