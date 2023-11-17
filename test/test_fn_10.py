import type_enforced
from typing import Union
import sys

# Test | only if python version >= 3.10
if sys.version_info < (3, 10):
    print("test_fn_10.py skipped")
    exit()


@type_enforced.Enforcer
def my_fn(a: Union[int, str], b: [int | str]) -> None:
    return None


success_1 = True
try:
    my_fn(a=1, b=2)  # No Error
    my_fn(a="a", b="b")  # No Error
except:
    success_1 = False

success_2 = False
try:
    my_fn(a=1.5, b="1.5")
except Exception as e:
    if "Type mismatch" in str(e):
        success_2 = True

success_3 = False
try:
    my_fn(a="1.5", b=1.5)
except Exception as e:
    if "Type mismatch" in str(e):
        success_3 = True


if success_1 and success_2 and success_3:
    print("test_fn_10.py passed")
else:
    print("test_fn_10.py failed")
