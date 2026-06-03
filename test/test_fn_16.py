import pytest
import type_enforced
from type_enforced.utils import Constraint, GenericConstraint

CustomConstraint = GenericConstraint(
    {
        "in_rgb": lambda x: x in ["red", "green", "blue"],
    }
)


@type_enforced.Enforcer()
def positive_int_lt5_test(
    value: int | Constraint(ge=0) | Constraint(le=5),
) -> bool:
    return True


@type_enforced.Enforcer()
def positive_float_test(value: int | float | Constraint(ge=0)) -> bool:
    return True


@type_enforced.Enforcer()
def running_str_test(value: str | Constraint(pattern=r".*running.*")) -> bool:
    return True


@type_enforced.Enforcer()
def custom_constraint_test(value: str | CustomConstraint) -> bool:
    return True


def test_fn_16():
    positive_int_lt5_test(0)

    with pytest.raises(TypeError):
        positive_int_lt5_test(-1)
    with pytest.raises(TypeError):
        positive_int_lt5_test(6)
    with pytest.raises(TypeError):
        positive_int_lt5_test("Hello There")

    positive_float_test(0.1)

    with pytest.raises(TypeError):
        positive_float_test(-0.99)
    with pytest.raises(TypeError):
        positive_float_test("Hello There")

    with pytest.raises(TypeError):
        running_str_test(0)
    with pytest.raises(TypeError):
        running_str_test("this is a stopped status")

    running_str_test("this is running status")

    custom_constraint_test("red")

    with pytest.raises(TypeError):
        custom_constraint_test("yellow")
