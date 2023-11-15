import type_enforced


@type_enforced.Enforcer
def my_fn(a: int, b: [int, str], c: int) -> None:
    return None


success_1 = True
try:
    my_fn(a=1, b=2, c=3)  # No Error
    my_fn(a=1, b="2", c=3)  # No Error (b can take int or str)
except:
    success_1 = False

success_2 = False
try:
    my_fn(a="a", b=2, c=3)  # Error (a can only accept int)
except Exception as e:
    if type(e) == TypeError:
        success_2 = True

if success_1 and success_2:
    print("test_fn_04.py passed")
else:
    print("test_fn_04.py failed")
