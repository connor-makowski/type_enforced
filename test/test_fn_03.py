import type_enforced


@type_enforced.Enforcer
def my_fn_enforced(a: int):
    pass


@type_enforced.Enforcer
def my_fn(a):
    pass


# Ensure that functions without annotations are not type enforced to prevent unnecessary overhead
success = isinstance(
    my_fn_enforced, type_enforced.FunctionMethodEnforcer
) and not isinstance(my_fn, type_enforced.FunctionMethodEnforcer)

if success:
    print("test_fn_03.py passed")
else:
    print("test_fn_03.py failed")
