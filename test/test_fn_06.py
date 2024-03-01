import type_enforced


def run_tests(fn, success):
    try:
        fn(a="a", b="b", c="c")  # No Error
        fn(a="a")  # No Error
        fn("a")  # No Error
        fn("a", b="b")  # No Error
        fn("a", "b")  # No Error
        try:
            fn(a="a", b=2, c="c")  # Error (b can only accept str)
            success = False
        except:
            pass
        try:
            fn("a", b=2)  # Error (b can only accept str)
            success = False
        except:
            pass
        try:
            fn("a", 2)  # Error (b can only accept str)
            success = False
        except:
            pass
    except:
        success = False
    return success


success = True


@type_enforced.Enforcer
def fn1(a, b: str = "b", c=None):
    pass


@type_enforced.Enforcer
def fn2(a, b: str = "b", c=None, **kwargs):
    pass


@type_enforced.Enforcer
def fn3(a, *args, b: str = "b", c=None):
    pass


@type_enforced.Enforcer
def fn4(a, *args, b: str = "b", c=None, **kwargs):
    pass


success = run_tests(fn1, success)
success = run_tests(fn2, success)
success = run_tests(fn3, success)
success = run_tests(fn4, success)

if success:
    print("test_fn_06.py passed")
else:
    print("test_fn_06.py failed")
