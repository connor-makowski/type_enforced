import type_enforced


@type_enforced.Enforcer
def my_fn(a: int, b: [int, str] = 2, c: int = 3) -> None:
    return None


@type_enforced.Enforcer
def my_fn_args(a: int, *args, b: [int, str] = 2, c: int = 3) -> None:
    return None


@type_enforced.Enforcer
def my_fn_kwargs(a: int, b: [int, str] = 2, c: int = 3, **kwargs) -> None:
    return None


@type_enforced.Enforcer
def my_fn_args_kwargs(
    a: int, *args, b: [int, str] = 2, c: int = 3, **kwargs
) -> None:
    return None


success = True
success_type_error = True
try:
    my_fn(a=1, b=2, c=3)  # No Error
    my_fn_args(a=1, b=2, c=3)  # No Error
    my_fn_kwargs(a=1, b=2, c=3)  # No Error
    my_fn_args_kwargs(a=1, b=2, c=3)  # No Error
except:
    success = False

try:
    my_fn(a="a", b=2, c=3)  # Error (a can only accept int)
    success = False
except Exception as e:
    if type(e) != TypeError:
        success_type_error = False

try:
    my_fn_args(a="a", b=2, c=3)  # Error (a can only accept int)
    success = False
except Exception as e:
    if type(e) != TypeError:
        success_type_error = False

try:
    my_fn_kwargs(a="a", b=2, c=3)  # Error (a can only accept int)
    success = False
except Exception as e:
    if type(e) != TypeError:
        success_type_error = False

try:
    my_fn_args_kwargs(a="a", b=2, c=3)  # Error (a can only accept int)
    success = False
except Exception as e:
    if type(e) != TypeError:
        success_type_error = False


if success and success_type_error:
    print("test_fn_05.py passed")
else:
    print("test_fn_05.py failed")
