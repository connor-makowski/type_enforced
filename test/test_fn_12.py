import type_enforced
from typing import Sized


@type_enforced.Enforcer
def my_fn(a: Sized) -> int:
    return a.__len__()


success_1 = True
try:
    my_fn(a=["a"])  # No Error
    my_fn(a={"a": 1})  # No Error
    my_fn(a=(1,))  # No Error
    my_fn(a={1})  # No Error
    my_fn(a="a")  # No Error
    my_fn(a=memoryview(b"abc"))  # No Error
    my_fn(a=b"abc")  # No Error
    my_fn(a=bytearray(b"abc"))  # No Error
    my_fn(a=range(1))  # No Error
except:
    success_1 = False

success_2 = False
try:
    my_fn(a=1)
except Exception as e:
    if "Type mismatch" in str(e):
        success_2 = True

if success_1 and success_2:
    print("test_fn_12.py passed")
else:
    print("test_fn_12.py failed")
