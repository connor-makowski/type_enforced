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


def test_class_10():
    foo = Foo()
    foo.bar(a=1)
    foo.baz(a="a")

    boo = Boo()
    boo.bar(a=1)
    boo.baz(a="a")
