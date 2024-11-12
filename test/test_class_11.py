import type_enforced
from dataclasses import dataclass


@type_enforced.Enforcer
@dataclass
class Foo:
    bar: int
    baz: str


passed = True
try:
    foo = Foo(bar=1, baz="a")
except:
    passed = False

try:
    foo = Foo(bar="a", baz=1)
    passed = False
except:
    pass

if passed:
    print("test_class_11.py passed")
else:
    print("test_class_11.py failed")
