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


def test_module_01_only_typed():
    import types

    # Module with untyped variable fails when only_typed=True
    m1 = types.ModuleType("mod_untyped")
    exec(
        """
def bad_fn(a, b: int) -> int:
    return b
""",
        m1.__dict__,
    )
    with pytest.raises(TypeError, match="Untyped variable `a`"):
        type_enforced.ModuleEnforcer(m1, only_typed=True)

    # Fully typed module passes when only_typed=True
    m2 = types.ModuleType("mod_typed")
    exec(
        """
def good_fn(a: int, b: int) -> int:
    return a + b
""",
        m2.__dict__,
    )
    type_enforced.ModuleEnforcer(m2, only_typed=True)
    assert m2.good_fn(1, 2) == 3
    with pytest.raises(TypeError, match="Type mismatch"):
        m2.good_fn("1", 2)


def test_module_01_disabled():
    import types

    m = types.ModuleType("mod_disabled")
    exec(
        """
def untyped_fn(a, b):
    return a + b

def typed_fn(x: int) -> int:
    return x * 2
""",
        m.__dict__,
    )

    # When enabled=False, enforcement is skipped even with only_typed=True
    type_enforced.ModuleEnforcer(m, enabled=False, only_typed=True)

    assert m.untyped_fn(1, 2) == 3
    assert m.typed_fn("not_an_int") == "not_an_intnot_an_int"
