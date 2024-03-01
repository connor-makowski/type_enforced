import type_enforced
from typing import Callable


# Create a generator to return items in a list
def get_sum_till_now(items):
    total = 0
    for item in items:
        total += item
        yield total


def my_function(x):
    return x


class MyClass:
    def __init__(self):
        pass

    def my_method(self, x):
        return x

    @staticmethod
    def my_static_method(x):
        return x

    @classmethod
    def my_class_method(self, x):
        return x


@type_enforced.Enforcer
def foo(out: str) -> Callable:
    if out == "sum":
        return sum
    elif out == "generator":
        return get_sum_till_now(range(10))
    elif out == "lambda":
        return lambda x: x
    elif out == "function":
        return my_function
    elif out == "method":
        x = MyClass()
        return x.my_method
    elif out == "staticmethod":
        return MyClass.my_static_method
    elif out == "classmethod":
        x = MyClass()
        return x.my_class_method
    else:
        return None


passed = True
try:
    foo("sum")
    foo("generator")
    foo("lambda")
    foo("function")
    foo("method")
    foo("staticmethod")
    foo("classmethod")
except:
    passed = False

try:
    foo("other")
    passed = False
except:
    pass

if passed:
    print("test_fn_14.py passed")
else:
    print("test_fn_14.py failed")
