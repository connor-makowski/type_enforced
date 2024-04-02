import type_enforced
from type_enforced.utils import Constraint, GenericConstraint

CustomConstraint = GenericConstraint(
    {
        "in_rgb": lambda x: x in ["red", "green", "blue"],
    }
)


@type_enforced.Enforcer()
def positive_int_test(value: [int, Constraint(ge=0)]) -> bool:
    return True


@type_enforced.Enforcer()
def positive_float_test(value: [int, float, Constraint(ge=0)]) -> bool:
    return True


@type_enforced.Enforcer()
def running_str_test(value: [str, Constraint(pattern=r".*running.*")]) -> bool:
    return True


@type_enforced.Enforcer()
def custom_constraint_test(value: [str, CustomConstraint]) -> bool:
    return True


success = True
try:
    positive_int_test(0)
except TypeError as err:
    success = False

try:
    positive_int_test(-1)
    success = False
except TypeError:
    pass

try:
    positive_int_test("Hello There")
    success = False
except TypeError:
    pass

try:
    positive_float_test(0.1)
except TypeError:
    success = False

try:
    positive_float_test(-0.99)
    success = False
except TypeError:
    pass

try:
    positive_float_test("Hello There")
    success = False
except TypeError:
    pass

try:
    running_str_test(0)
    success = False
except TypeError:
    pass

try:
    running_str_test("this is a stopped status")
    success = False
except TypeError:
    pass

try:
    running_str_test("this is running status")
except TypeError:
    success = False

try:
    custom_constraint_test("red")
except TypeError:
    success = False

try:
    custom_constraint_test("yellow")
    success = False
except TypeError:
    pass


if success:
    print(f"test_fn_16.py passed")
else:
    print(f"test_fn_16.py failed")
