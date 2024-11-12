import type_enforced
from type_enforced.utils import WithSubclasses


class Bar:
    pass


BarSubclasses = WithSubclasses(Bar)


@type_enforced.Enforcer
def foo(x: BarSubclasses):
    pass
