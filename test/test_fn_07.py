import type_enforced


@type_enforced.Enforcer
def my_fn(
    a: list[str], b: dict[int], c: tuple[int, float], d: set[str]
) -> None:
    return None


success_1 = True
try:
    my_fn(a=["a"], b={"a": 1}, c=(1, 1.5), d={"a"})
except:
    success_1 = False

success_2 = False
try:
    my_fn(
        a=[1], b={"a": 1}, c=(1, 1.5), d={"a"}
    )  # Error (a can only accept str)
except Exception as e:
    if "Type mismatch" in str(e):
        success_2 = True

success_3 = False
try:
    my_fn(
        a=["a"], b={"a": "a"}, c=(1, 1.5), d={"a"}
    )  # Error (b can only accept int)
except Exception as e:
    if "Type mismatch" in str(e):
        success_3 = True

if success_1 and success_2 and success_3:
    print("test_fn_07.py passed")
else:
    print("test_fn_07.py failed")
