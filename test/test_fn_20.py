import type_enforced, sys

from collections import OrderedDict


def my_fn(a: int, b: int | str, c: int) -> None:
    return None


class MyClass:
    def my_fn(self, a: int, b: int | str, c: int) -> None:
        return None


my_ordered_dict = OrderedDict()

success = True

try:
    # Enforce all modules in this file (anything above)
    type_enforced.Enforcer(sys.modules[__name__])
except:
    success = False


try:
    my_fn(a=1, b=2, c=3)  # No Error
    my_fn(a=1, b="2", c=3)  # No Error (b can take int or str)

    my_class = MyClass()
    my_class.my_fn(a=1, b=2, c=3)  # No Error
    my_class.my_fn(a=1, b="2", c=3)  # No Error (b can take int or str)
except:
    success = False

try:
    my_fn(a=1, b=2, c="3")  # Error: Type of c is not int
    success = False
except:
    pass

if success:
    print("test_fn_20.py passed")
else:
    print("test_fn_20.py failed")
