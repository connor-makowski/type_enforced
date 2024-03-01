import type_enforced
import sys


class Foo:
    @type_enforced.Enforcer
    @classmethod
    def add(self, a: int, b: int) -> int:
        return a + b

    @type_enforced.Enforcer
    @staticmethod
    def subtract(a: int, b: int) -> int:
        return a - b


success = True

try:
    x = Foo.add(1, 2)
    y = Foo.subtract(4, 3)
    success = success and x == 3 and y == 1
except:
    success = False

try:
    Foo.add(1, 2.0)
    success = False
except:
    pass

try:
    Foo.subtract(1, 2.0)
    success = False
except:
    pass

# classmethod and staticmethod wrappers do not contain annotations prior to 3.9
if success or sys.version_info <= (3, 10, 0):
    print("test_class_06.py passed")
else:
    print("test_class_06.py failed")
