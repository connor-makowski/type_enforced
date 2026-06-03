import type_enforced
from type_enforced.utils import WithSubclasses

# WithSubclasses is a legacy no-op kept for backwards compatibility


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


def test_class_09():
    Baz(Foo())
    Baz(Bar())
