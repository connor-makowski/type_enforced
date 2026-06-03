import pytest
import type_enforced


@type_enforced.Enforcer
def full_check(a: list[int]) -> None:
    return None


@type_enforced.Enforcer(iterable_sample_pct=50)
def sampled_check(a: list[int]) -> None:
    return None


@type_enforced.Enforcer(iterable_sample_pct=50)
def sampled_dict(a: dict[str, int]) -> None:
    return None


@type_enforced.Enforcer(iterable_sample_pct=50)
def sampled_tuple(a: tuple[int, ...]) -> None:
    return None


@type_enforced.Enforcer(iterable_sample_pct=0)
def zero_pct_check(a: list[int]) -> None:
    return None


def test_fn_23_full_check():
    full_check(a=[1, 2, 3, 4, 5])
    with pytest.raises(TypeError):
        full_check(a=[1, 2, "bad", 4, 5])


def test_fn_23_sampled_check():
    sampled_check(a=list(range(100)))
    with pytest.raises(TypeError):
        sampled_check(a=["bad"] + list(range(1, 100)))
    with pytest.raises(TypeError):
        sampled_check(a=list(range(99)) + ["bad"])


def test_fn_23_sampled_dict():
    sampled_dict(a={str(i): i for i in range(100)})
    d = {str(i): i for i in range(100)}
    first_key = list(d.keys())[0]
    d[first_key] = "bad_value"
    with pytest.raises(TypeError):
        sampled_dict(a=d)


def test_fn_23_sampled_tuple():
    sampled_tuple(a=tuple(range(100)))
    with pytest.raises(TypeError):
        sampled_tuple(a=("bad",) + tuple(range(1, 100)))


def test_fn_23_short_list():
    # Short list (<=3): all items checked even with sampling
    with pytest.raises(TypeError):
        sampled_check(a=[1, "bad", 3])


def test_fn_23_zero_pct():
    with pytest.raises(TypeError):
        zero_pct_check(a=["bad", 2, 3, 4, 5])
    # Last item not checked at pct=0
    zero_pct_check(a=[1, 2, 3, 4, "bad"])
    zero_pct_check(a=[])
