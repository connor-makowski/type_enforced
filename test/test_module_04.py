import pytest
import type_enforced
import types
from test_module_04_utils import mod_top, mod_options, mod_external


def test_fast_module_enforcer_top():
    # Top of module enforcement
    assert mod_top.process_list([1, "bad", 3]) == 3
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `items"
    ):
        mod_top.process_list(["bad", 2, 3])

    proc = mod_top.Processor()
    assert proc.process_dict({"key": 1, "bad_key_val": "str_val"}) == 2
    with pytest.raises(TypeError, match="Type mismatch"):
        proc.process_dict({123: 1})


def test_fast_module_enforcer_options():
    # Options configured: iterable_sample_pct="last"
    assert mod_options.check_last(["bad", "bad2", 100]) == 3
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `items"
    ):
        mod_options.check_last([1, 2, "bad_last"])


def test_fast_module_enforcer_external():
    # External module enforcement
    mod_external.process_list_ext(["bad", "bad2"])  # passes before enforcement

    type_enforced.FastModuleEnforcer(mod_external)

    assert mod_external.process_list_ext([10, "bad", 30]) == 3
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `items"
    ):
        mod_external.process_list_ext(["bad", 20, 30])

    proc = mod_external.ProcessorExt()
    assert proc.process_dict_ext({"key": 100}) == 1
    with pytest.raises(TypeError, match="Type mismatch"):
        proc.process_dict_ext({123: "val"})


def test_fast_module_enforcer_disallowed_options():
    m = types.ModuleType("test_mod_disallowed")
    exec(
        """
def fn(x: list[int]) -> int:
    return len(x)
""",
        m.__dict__,
    )

    with pytest.raises(
        TypeError,
        match="FastModuleEnforcer only supports fast sampling options",
    ):
        type_enforced.FastModuleEnforcer(m, iterable_sample_pct=100)

    with pytest.raises(
        TypeError,
        match="FastModuleEnforcer only supports fast sampling options",
    ):
        type_enforced.FastModuleEnforcer(m, iterable_sample_pct=50)

    with pytest.raises(
        TypeError,
        match="FastModuleEnforcer only supports fast sampling options",
    ):
        type_enforced.FastModuleEnforcer(m, iterable_sample_pct="invalid_pct")


def test_fast_module_enforcer_only_typed():
    m = types.ModuleType("test_mod_untyped")
    exec(
        """
def untyped_fn(a, b: int) -> int:
    return b
""",
        m.__dict__,
    )

    with pytest.raises(TypeError, match="Untyped variable `a`"):
        type_enforced.FastModuleEnforcer(m, only_typed=True)


def test_fast_module_enforcer_disabled():
    m = types.ModuleType("test_mod_disabled")
    exec(
        """
def fn(x: list[int]) -> int:
    return len(x)
""",
        m.__dict__,
    )

    type_enforced.FastModuleEnforcer(m, enabled=False)
    assert m.fn(["bad", "also_bad"]) == 2
