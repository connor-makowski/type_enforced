from pathlib import Path
from type_enforced import Enforcer
from type_enforced.type import Constraint
from type_enforced.exception import ConstraintError
from typing import Annotated

filename = Path(__file__).name

PositiveInt = Annotated[int, Constraint(ge=0)]
PositiveFloat = Annotated[float, Constraint(ge=0)]
RunningStr = Annotated[str, Constraint(pattern=r".*running.*")]

for i, curr_test in enumerate([
    (PositiveInt, 0, True),
    (PositiveInt, -1, ConstraintError),
    (PositiveInt, "Hello There", TypeError),

    (PositiveFloat, 0.1, True),
    (PositiveFloat, -0.99, ConstraintError),
    (PositiveFloat, "Hello There", TypeError),

    (RunningStr, 0, TypeError),
    (RunningStr, "this is a stopped status", ConstraintError),
    (RunningStr, "this is running status", True),
]):
    hint, value, expected = curr_test
    failure = False


    @Enforcer
    def func(value: hint):
        return True
    try:
        response = func(value)
        assert response == expected
    except AssertionError:
        failure = True
    except Exception as err:
        try:
            assert isinstance(err, expected)
        except AssertionError:
            failure = True

    msg = f"Test[{i}]"
    if failure:
        print(f"{msg}: {filename} failed")
    else:
        print(f"{msg}: {filename} passed")
