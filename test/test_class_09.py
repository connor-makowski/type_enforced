import type_enforced
from type_enforced.utils import WithSubclasses


# This test is no longer officially needed, but is kept to check for backwards compatibility
# TODO: Remove/Modify this test in the next major release of type_enforced


class Foo:
    def __init__(self) -> None:
        pass


class Bar(Foo):
    def __init__(self) -> None:
        super().__init__()


@type_enforced.Enforcer
class Baz:
    def __init__(self, use_class: WithSubclasses(Foo)) -> None:
        self.object = use_class


success = True
try:
    x = Baz(Foo())
except:
    success = False

try:
    y = Baz(Bar())
except:
    success = False

if success:
    print("test_class_09.py passed")
else:
    print("test_class_09.py failed")
