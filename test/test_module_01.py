import pytest
import type_enforced
from test_module_01_utils import mod_top, mod_bottom, mod_external


def test_module_01():
    # Top of module enforcement
    assert mod_top.subtract(5, 2) == 3
    with pytest.raises(TypeError, match="Type mismatch"):
        mod_top.subtract("5", 2)

    divider = mod_top.Divider()
    assert divider.divide(6, 2) == 3
    with pytest.raises(TypeError, match="Type mismatch"):
        divider.divide("6", 2)

    # Bottom of module enforcement
    assert mod_bottom.add(1, 2) == 3
    with pytest.raises(TypeError, match="Type mismatch"):
        mod_bottom.add("1", 2)

    calc = mod_bottom.Calculator()
    assert calc.multiply(2, 3) == 6
    with pytest.raises(TypeError, match="Type mismatch"):
        calc.multiply("2", 3)

    # External module enforcement
    mod_external.multiply_ext("1", 2)  # passes before enforcement

    type_enforced.ModuleEnforcer(mod_external)

    assert mod_external.multiply_ext(2, 3) == 6
    with pytest.raises(TypeError, match="Type mismatch"):
        mod_external.multiply_ext("2", 3)

    greeter = mod_external.Greeter()
    assert greeter.greet("World") == "Hello World"
    with pytest.raises(TypeError, match="Type mismatch"):
        greeter.greet(123)


def test_module_01_module_enforcer_direct():
    import types

    m = types.ModuleType("custom_mod")
    exec(
        """
def fn(x: int) -> int:
    return x * 2
""",
        m.__dict__,
    )

    type_enforced.ModuleEnforcer(m)
    assert m.fn(2) == 4
    with pytest.raises(TypeError, match="Type mismatch"):
        m.fn("2")
