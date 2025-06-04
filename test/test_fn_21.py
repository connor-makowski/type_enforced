import type_enforced, typing

# Test for Any / object type checking


@type_enforced.Enforcer
def my_fn(a: typing.Any, b: object) -> None:
    return None


my_fn(a=1, b=2)  # No Error
my_fn(a="hi", b=3.14)  # No Error

success = True


if success:
    print("test_fn_21.py passed")
else:
    print("test_fn_21.py failed")
