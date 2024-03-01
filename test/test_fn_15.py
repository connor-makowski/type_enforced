import type_enforced


@type_enforced.Enforcer()
def my_fn(a: int):
    return None


@type_enforced.Enforcer(enabled=False)
def my_fn2(a: int):
    return None


success = True

try:
    my_fn(a=1)
    my_fn2(a=1)
    my_fn2(a="1")
except:
    success = False

try:
    my_fn(a="1")
    success = False
except:
    pass

if success:
    print("test_fn_15.py passed")
else:
    print("test_fn_15.py failed")
