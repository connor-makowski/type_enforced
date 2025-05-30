import type_enforced


@type_enforced.Enforcer
def my_fn(a: dict[str, dict[str, int]], b: list[set[str]]) -> None:
    return None


success_1 = True
try:
    my_fn(a={"a": {"a": 1}}, b=[{"a"}])
except:
    success_1 = False

success_2 = False
try:
    my_fn(a={"a": {"a": "2"}}, b=[{"a"}])  # Error (a can only accept int)
except Exception as e:
    if "Type mismatch" in str(e):
        success_2 = True

success_3 = False
try:
    my_fn(a={"a": {"a": 1}}, b=[{"a", 1}])  # Error (b can only accept str)
except Exception as e:
    if "Type mismatch" in str(e):
        success_3 = True

success_4 = False
try:
    my_fn(a={"a": {1: 1}}, b=[{"a"}])  # Error Dict keys must be str
except Exception as e:
    if "Type mismatch" in str(e):
        success_4 = True

if success_1 and success_2 and success_3 and success_4:
    print("test_fn_08.py passed")
else:
    print("test_fn_08.py failed")
