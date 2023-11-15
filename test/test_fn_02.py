import type_enforced


@type_enforced.Enforcer
def my_fn(a: int, b: [int, str] = 2, c: int = 3) -> None:
    return 1


success = False

try:
    my_fn(a=1, b=2, c=3)  # Error (return is not None)
except Exception as e:
    if "Type mismatch" in str(e):
        success = True

if success:
    print("test_fn_02.py passed")
else:
    print("test_fn_02.py failed")
