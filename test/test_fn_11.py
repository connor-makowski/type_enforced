import type_enforced
from typing import Optional


@type_enforced.Enforcer
def my_fn(a: Optional[str] = None) -> None:
    return None


success_1 = True
try:
    my_fn(a="a")  # No Error
    my_fn()
except:
    success_1 = False

success_2 = False
try:
    my_fn(a=1)
except Exception as e:
    if "Type mismatch" in str(e):
        success_2 = True

if success_1 and success_2:
    print("test_fn_11.py passed")
else:
    print("test_fn_11.py failed")
