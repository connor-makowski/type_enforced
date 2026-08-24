import pytest
import type_enforced


@type_enforced.Enforcer
class AdvancedReceiverService:
    def with_this(this, x: int, y: str) -> str:
        return f"{this.__class__.__name__}:{y * x}"

    def with_me(me, items: list[int]) -> int:
        return sum(items)

    def with_ctx(ctx, d: dict[str, list[int]]) -> int:
        return sum(sum(v) for v in d.values())

    def with_custom(custom_first_arg, s: set[str]) -> int:
        return len(s)

    def with_tuple(self, t: tuple[int, ...]) -> int:
        return sum(t)

    def with_nested_list(self, ll: list[list[int]]) -> int:
        return sum(sum(sub) for sub in ll)

    @classmethod
    def from_val(cls, val: int) -> int:
        return val * 2


svc = AdvancedReceiverService()


def test_class_17_custom_first_arg_specialization():
    res = svc.with_this(3, "ab")
    assert res == "AdvancedReceiverService:ababab"
    assert svc.with_this(x=2, y="c") == "AdvancedReceiverService:cc"
    assert (
        AdvancedReceiverService.with_this(svc, 2, "d")
        == "AdvancedReceiverService:dd"
    )

    with pytest.raises(TypeError, match="Type mismatch"):
        svc.with_this("bad", "ab")
    with pytest.raises(TypeError, match="Type mismatch"):
        svc.with_this(2, 123)


def test_class_17_containers_with_custom_receivers():
    assert svc.with_me([1, 2, 3, 4]) == 10
    with pytest.raises(TypeError, match="Type mismatch"):
        svc.with_me([1, "bad", 3])

    assert svc.with_ctx({"a": [1, 2], "b": [3, 4]}) == 10
    with pytest.raises(TypeError, match="Type mismatch"):
        svc.with_ctx({"a": [1, "bad"]})

    assert svc.with_custom({"a", "b", "c"}) == 3
    with pytest.raises(TypeError, match="Type mismatch"):
        svc.with_custom({1, 2, 3})


def test_class_17_tuple_and_nested_list():
    assert svc.with_tuple((1, 2, 3, 4)) == 10
    with pytest.raises(TypeError, match="Type mismatch"):
        svc.with_tuple((1, "bad", 3))

    assert svc.with_nested_list([[1, 2], [3, 4]]) == 10
    with pytest.raises(TypeError, match="Type mismatch"):
        svc.with_nested_list([[1, "bad"], [3]])


def test_class_17_classmethod():
    assert AdvancedReceiverService.from_val(5) == 10
    with pytest.raises(TypeError, match="Type mismatch"):
        AdvancedReceiverService.from_val("bad")
