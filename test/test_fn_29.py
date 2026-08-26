import pytest
import type_enforced


@type_enforced.Enforcer
def fn_args_kwargs(a: int, b: str, c: float = 1.0, *args, **kwargs) -> tuple:
    return (a, b, c, args, kwargs)


@type_enforced.Enforcer
def fn_posonly_kwonly(
    p0: int, /, p1: str, *args, k0: str, k1: int = 100, **kwargs
) -> tuple:
    return (p0, p1, args, k0, k1, kwargs)


@type_enforced.Enforcer
def fn_typed_varargs(a: int, *args: int) -> int:
    return a + sum(args)


@type_enforced.Enforcer
def fn_typed_varkwargs(prefix: str, **kwargs: int) -> int:
    return sum(kwargs.values())


class VariadicClass:
    @type_enforced.Enforcer
    def method_variadic(
        self, a: int, b: str = "default", *args, **kwargs
    ) -> str:
        return f"{a}:{b}:{args}:{kwargs}"


def test_fn_29_args_kwargs():
    # Valid calls
    assert fn_args_kwargs(1, "hello") == (1, "hello", 1.0, (), {})
    assert fn_args_kwargs(1, "hello", 2.5) == (1, "hello", 2.5, (), {})
    assert fn_args_kwargs(1, "hello", 2.5, 10, 20, extra="val") == (
        1,
        "hello",
        2.5,
        (10, 20),
        {"extra": "val"},
    )

    # Invalid types
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_args_kwargs("not_an_int", "hello")

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_args_kwargs(1, 123)

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_args_kwargs(1, "hello", "not_a_float")


def test_fn_29_posonly_and_kwonly():
    # Valid calls
    res = fn_posonly_kwonly(1, "two", k0="three")
    assert res == (1, "two", (), "three", 100, {})

    res2 = fn_posonly_kwonly(
        1, "two", 30, 40, k0="three", k1=200, extra="extra_val"
    )
    assert res2 == (1, "two", (30, 40), "three", 200, {"extra": "extra_val"})

    # Positional-only passed as kwarg should fail
    with pytest.raises(TypeError):
        fn_posonly_kwonly(p0=1, p1="two", k0="three")

    # Type mismatch on positional-only
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_posonly_kwonly("bad_int", "two", k0="three")

    # Type mismatch on kwonly
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_posonly_kwonly(1, "two", k0=999)

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_posonly_kwonly(1, "two", k0="three", k1="bad_k1")


def test_fn_29_typed_varargs():
    assert fn_typed_varargs(10) == 10
    assert fn_typed_varargs(10, 1, 2, 3) == 16

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_typed_varargs("bad", 1, 2)

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_typed_varargs(10, 1, "bad", 3)


def test_fn_29_typed_varkwargs():
    assert fn_typed_varkwargs("sum", x=10, y=20) == 30

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_typed_varkwargs(123, x=10)

    with pytest.raises(TypeError, match="Type mismatch"):
        fn_typed_varkwargs("sum", x=10, y="bad")


def test_fn_29_class_method():
    obj = VariadicClass()
    assert (
        obj.method_variadic(1, "custom", 10, 20, opt=True)
        == "1:custom:(10, 20):{'opt': True}"
    )
    assert obj.method_variadic(1) == "1:default:():{}"

    with pytest.raises(TypeError, match="Type mismatch"):
        obj.method_variadic("bad_int")
