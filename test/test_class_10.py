import type_enforced


@type_enforced.Enforcer
class Foo:
    def bar(self, a: int) -> None:
        pass

    @type_enforced.Enforcer(enabled=False)
    def baz(self, a: int) -> None:
        pass


@type_enforced.Enforcer(enabled=False)
class Boo:
    @type_enforced.Enforcer(enabled=True)
    def bar(self, a: int) -> None:
        pass

    def baz(self, a: int) -> None:
        pass


try:
    foo = Foo()
    foo.bar(a=1)  # => No Exception
    foo.baz(a="a")  # => No Exception

    boo = Boo()
    boo.bar(a=1)  # => No Exception
    boo.baz(a="a")  # => No Exception
    print("test_class_10.py passed")
except:
    print("test_class_10.py failed")
