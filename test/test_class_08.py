import type_enforced


@type_enforced.Enforcer
class my_class:
    def my_fn(self, a: int, b: [int, str] = 2, c: int = 3) -> None:
        return None

    def my_fn_args(self, a: int, *args, b: [int, str] = 2, c: int = 3) -> None:
        return None

    def my_fn_kwargs(
        sellf, a: int, b: [int, str] = 2, c: int = 3, **kwargs
    ) -> None:
        return None

    def my_fn_args_kwargs(
        self, a: int, *args, b: [int, str] = 2, c: int = 3, **kwargs
    ) -> None:
        return None


obj = my_class()
success = True
success_type_error = True
try:
    obj.my_fn(a=1, b=2, c=3)  # No Error
    obj.my_fn_args(a=1, b=2, c=3)  # No Error
    obj.my_fn_kwargs(a=1, b=2, c=3)  # No Error
    obj.my_fn_args_kwargs(a=1, b=2, c=3)  # No Error
except:
    success = False

try:
    obj.my_fn(a="a", b=2, c=3)  # Error (a can only accept int)
    success = False
except Exception as e:
    if type(e) != TypeError:
        success_type_error = False

try:
    obj.my_fn_args(a="a", b=2, c=3)  # Error (a can only accept int)
    success = False
except Exception as e:
    if type(e) != TypeError:
        success_type_error = False

try:
    obj.my_fn_kwargs(a="a", b=2, c=3)  # Error (a can only accept int)
    success = False
except Exception as e:
    if type(e) != TypeError:
        success_type_error = False

try:
    obj.my_fn_args_kwargs(a="a", b=2, c=3)  # Error (a can only accept int)
    success = False
except Exception as e:
    if type(e) != TypeError:
        success_type_error = False


if success and success_type_error:
    print("test_class_08.py passed")
else:
    print("test_class_08.py failed")
