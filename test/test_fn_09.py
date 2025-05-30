import type_enforced
from typing import List, Set, Dict, Tuple


@type_enforced.Enforcer
def my_fn(
    a: List[int], b: Set[str], c: Dict[str, int], d: Tuple[str, int]
) -> None:
    return None


success_1 = True
try:
    my_fn(
        a=[1, 2, 3], b={"a", "b", "c"}, c={"a": 1, "b": 2, "c": 3}, d=("a", 1)
    )
except:
    # print("Error in my_fn with valid inputs")
    success_1 = False

success_2 = False
try:
    my_fn(
        a=[1, 2, 3],
        b={"a", "b", "c"},
        c={"a": 1, "b": 2, "c": 3},
        d=("a", 1.5),
    )  # Error (d can only accept Tuple[str, int])
    # print("Error not raised for invalid d")
except Exception as e:
    if "Type mismatch" in str(e):
        success_2 = True

success_3 = False
try:
    my_fn(
        a=[1, 2, 3],
        b={"a", "b", "c"},
        c={"a": 1, "b": 2, "c": 3},
        d=("a", 1, 1),
    )  # Error (d must be length 2)
    # print("Error not raised for invalid d length")
except Exception as e:
    if "TypeEnforced" in str(e):
        success_3 = True

if success_1 and success_2 and success_3:
    print("test_fn_09.py passed")
else:
    print("test_fn_09.py failed")
