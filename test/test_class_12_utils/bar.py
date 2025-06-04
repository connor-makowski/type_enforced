import type_enforced


class Bar:
    pass


@type_enforced.Enforcer
def foo(x: Bar) -> None:
    pass
