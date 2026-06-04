import pytest
import type_enforced


@type_enforced.Enforcer
def fn1(a, b: str = "b", c=None):
    pass


@type_enforced.Enforcer
def fn2(a, b: str = "b", c=None, **kwargs):
    pass


@type_enforced.Enforcer
def fn3(a, *args, b: str = "b", c=None):
    pass


@type_enforced.Enforcer
def fn4(a, *args, b: str = "b", c=None, **kwargs):
    pass


def run_tests(fn, star_capture=False):
    fn(a="a", b="b", c="c")
    fn(a="a")
    fn("a")
    fn("a", b="b")
    fn("a", "b")
    with pytest.raises(Exception):
        fn(a="a", b=2, c="c")
    with pytest.raises(Exception):
        fn("a", b=2)
    if star_capture:
        fn("a", 2)
    else:
        with pytest.raises(Exception):
            fn("a", 2)


def test_fn_06():
    run_tests(fn1, star_capture=False)
    run_tests(fn2, star_capture=False)
    run_tests(fn3, star_capture=True)
    run_tests(fn4, star_capture=True)
