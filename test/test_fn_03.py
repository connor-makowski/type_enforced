import type_enforced


@type_enforced.Enforcer
def my_fn_enforced(a: int):
    pass


@type_enforced.Enforcer
def my_fn(a):
    pass


def test_fn_03():
    assert isinstance(my_fn_enforced, type_enforced.FunctionMethodEnforcer)
    assert not isinstance(my_fn, type_enforced.FunctionMethodEnforcer)
