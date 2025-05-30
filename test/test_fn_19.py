from __future__ import annotations
import type_enforced, sys


success_1 = True
try:

    @type_enforced.Enforcer
    def my_fn(a: int, b: int | str, c: int) -> None:
        return None

except:
    success_1 = False


try:
    my_fn(a=1, b=2, c=3)  # No Error
    my_fn(a=1, b="2", c=3)  # No Error (b can take int or str)
except:
    success_1 = False

success_2 = False
try:
    my_fn(a="a", b=2, c=3)  # Error (a can only accept int)
except Exception as e:
    if "Type mismatch" in str(e):
        success_2 = True

if success_1 and success_2:
    print("test_fn_19.py passed")
elif sys.version_info < (3, 11, 0):
    print("test_fn_19.py skipped")
else:
    print("test_fn_19.py failed")
