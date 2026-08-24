import pytest
import type_enforced


@type_enforced.Enforcer
def fn_8_args(
    a: int,
    b: str,
    c: float,
    d: bool,
    e: int = 10,
    f: str = "f_default",
    g: float = 3.14,
    h: bool = True,
) -> int:
    return a + e


@type_enforced.Enforcer
def fn_12_args(
    a1: int,
    a2: int,
    a3: int,
    a4: int,
    a5: int,
    a6: int,
    a7: int,
    a8: int,
    a9: int,
    a10: int,
    a11: int,
    a12: int,
) -> int:
    return a1 + a12


# Function with 35 arguments (>32 to trigger generic fallback)
args_35_def = ", ".join([f"a{i}: int = {i}" for i in range(35)])
code_35 = f"""
@type_enforced.Enforcer
def fn_35_args({args_35_def}) -> int:
    return a0 + a34
"""
ns = {"type_enforced": type_enforced}
exec(code_35, ns)
fn_35_args = ns["fn_35_args"]


class BigClass:
    @type_enforced.Enforcer
    def method_8_args(
        self,
        a: int,
        b: str,
        c: float,
        d: bool,
        e: int = 10,
        f: str = "f_default",
        g: float = 3.14,
        h: bool = True,
    ) -> int:
        return a + e


# Method with 35 arguments (>32 to trigger generic fallback)
method_35_def = ", ".join(["self"] + [f"a{i}: int = {i}" for i in range(35)])
code_method_35 = f"""
class BigClass35:
    @type_enforced.Enforcer
    def method_35_args({method_35_def}) -> int:
        return a0 + a34
"""
ns_method = {"type_enforced": type_enforced}
exec(code_method_35, ns_method)
BigClass35 = ns_method["BigClass35"]


def test_fn_27_large_n_args_positional():
    # 8 args positional
    res = fn_8_args(1, "b", 2.5, False, 20, "f", 1.0, False)
    assert res == 21

    # 12 args positional
    res12 = fn_12_args(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
    assert res12 == 13

    # Type error on positional
    with pytest.raises(TypeError):
        fn_8_args("not_int", "b", 2.5, False)

    with pytest.raises(TypeError):
        fn_12_args(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, "not_int")


def test_fn_27_kwargs_and_defaults():
    # Calling with kwargs in order and out of order
    res = fn_8_args(a=5, b="hello", c=1.0, d=True)
    assert res == 15

    res2 = fn_8_args(d=False, c=2.0, b="world", a=7, e=50)
    assert res2 == 57

    # Type error on kwarg
    with pytest.raises(TypeError):
        fn_8_args(a=5, b=123, c=1.0, d=True)

    with pytest.raises(TypeError):
        fn_8_args(a=5, b="hello", c="not_float", d=True)


def test_fn_27_method_large_n_args():
    obj = BigClass()
    res = obj.method_8_args(1, "b", 2.5, False, 20)
    assert res == 21

    res_kw = obj.method_8_args(d=True, c=1.5, b="msg", a=10)
    assert res_kw == 20

    with pytest.raises(TypeError):
        obj.method_8_args(1, 2, 3.0, True)


def test_fn_27_more_than_32_args_fallback():
    # 1. Valid positional call
    args_35 = list(range(35))
    res = fn_35_args(*args_35)
    assert res == 34

    # 2. Valid kwargs call
    kwargs_35 = {f"a{i}": i * 2 for i in range(35)}
    res_kw = fn_35_args(**kwargs_35)
    assert res_kw == 0 + 34 * 2

    # 3. Default values resolution
    res_def = fn_35_args(a0=100)
    assert res_def == 100 + 34

    # 4. Type error on first argument
    with pytest.raises(TypeError):
        fn_35_args("not_int", *args_35[1:])

    # 5. Type error on last argument
    with pytest.raises(TypeError):
        fn_35_args(*args_35[:34], "not_int")

    # 6. Type error via kwargs
    with pytest.raises(TypeError):
        fn_35_args(a34="bad_string")


def test_fn_27_more_than_32_args_method_fallback():
    obj = BigClass35()

    # 1. Valid positional call on method (>32 args)
    args_35 = list(range(35))
    res = obj.method_35_args(*args_35)
    assert res == 34

    # 2. Valid kwargs call on method
    kwargs_35 = {f"a{i}": i * 3 for i in range(35)}
    res_kw = obj.method_35_args(**kwargs_35)
    assert res_kw == 0 + 34 * 3

    # 3. Type error on method argument
    with pytest.raises(TypeError):
        obj.method_35_args(a0="bad", a34=10)
