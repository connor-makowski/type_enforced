import type_enforced
from typing import Literal


@type_enforced.Enforcer
def my_fn(a: Literal["bar"] | int) -> None:
    pass


success = True
# TODO: In the next major version, add support to enforce combinations of literals as types
#       and not constraints.
# try:
#     my_fn("bar")  # Passes
#     my_fn(1)  # Passes
# except:
#     success = False


if success:
    print(f"test_fn_18.py passed")
else:
    print(f"test_fn_18.py failed")
