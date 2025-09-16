import type_enforced


class Foo:
    @type_enforced.Enforcer
    def __init__(self, object: "Bar") -> None:
        pass


class Bar:
    def __init__(self) -> None:
        pass


class Baz:
    def __init__(self) -> None:
        pass


success = True
try:
    x = Foo(Bar())
except:
    success = False

try:
    y = Baz(Baz())
    success = False
except:
    pass

if success:
    print("test_class_15.py passed")
else:
    print("test_class_15.py failed")
