import type_enforced


@type_enforced.Enforcer
def my_fn(
    a: list[str],
    b: dict[str, int],
    c: tuple[int, float],
    d: set[str],
    e: tuple[int | float, ...] = (1.0, 2, 3),
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

success_4 = False
try:
    my_fn(
        a=["a"], b={"a": 1}, c=(1, "1.5"), d={"a"}
    )  # Error (c can only accept int and float)
except Exception as e:
    if "Type mismatch" in str(e):
        success_4 = True

success_5 = False
try:
    my_fn(
        a=["a"], b={"a": 1}, c=(1, 1.5), d={"a", "b"}, e=("a", "b", "c")
    )  # Error (e can only accept int or float)
except Exception as e:
    if "Type mismatch" in str(e):
        success_5 = True

if success_1 and success_2 and success_3 and success_4 and success_5:
    print("test_fn_07.py passed")
else:
    print("test_fn_07.py failed")
