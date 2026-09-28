import pytest
import type_enforced


def _make_multi_param_fn(n):
    params = ", ".join(f"a{i}: int" for i in range(n))
    code = f"def f({params}) -> None: pass"
    ns = {}
    exec(code, globals(), ns)
    return type_enforced.Enforcer(ns["f"])


fn_500 = _make_multi_param_fn(500)
fn_300 = _make_multi_param_fn(300)


def test_500_input_function_valid():
    args_500 = tuple(range(500))
    fn_500(*args_500)


def test_500_input_function_invalid_positions():
    for bad_idx in [0, 10, 243, 244, 255, 256, 499]:
        args = [i for i in range(500)]
        args[bad_idx] = "not_an_int"
        with pytest.raises(
            TypeError,
            match=f"Type mismatch for typed variable `a{bad_idx}`",
        ):
            fn_500(*args)


def test_500_input_function_invalid_kwarg():
    args = [i for i in range(499)]
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `a499`"
    ):
        fn_500(*args, a499="not_an_int")


def test_300_input_function():
    args_300 = tuple(range(300))
    fn_300(*args_300)

    for bad_idx in [0, 255, 256, 299]:
        args = [i for i in range(300)]
        args[bad_idx] = "not_an_int"
        with pytest.raises(
            TypeError,
            match=f"Type mismatch for typed variable `a{bad_idx}`",
        ):
            fn_300(*args)
