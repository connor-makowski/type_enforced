import type_enforced
from typing import Type

# This test checks for Uninitialized class type checking


class Foo:
    def __init__(self) -> None:
        pass


class Bar(Foo):
    def __init__(self) -> None:
        super().__init__()


class Bum:
    def __init__(self) -> None:
        pass


@type_enforced.Enforcer
class Baz:
    def __init__(self, use_class: Type[Foo]) -> None:
        self.object = use_class


success = True
try:
    x = Baz(Foo)
except:
    success = False

try:
    x = Baz(Foo())
    success = False
except:
    pass

try:
    y = Baz(Bar)
    success = False
except:
    pass

try:
    y = Baz(Bum)
    success = False
except:
    pass

if success:
    print("test_class_04.py passed")
else:
    print("test_class_04.py failed")
