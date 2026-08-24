import pytest
import type_enforced


@type_enforced.Enforcer
class Service:
    def get_count(self) -> int:
        return 42

    def double(self, x: int) -> int:
        return x * 2

    def repeat(self, a: int, b: str = "yo") -> str:
        return b * a

    def process_list(self, items: list[int]) -> int:
        return sum(items)

    def process_dict(self, d: dict[str, int]) -> int:
        return sum(d.values())

    def process_list_dict(self, items: list[dict[str, int]]) -> int:
        return sum(sum(d.values()) for d in items)

    def partial(self, a: int, b) -> int:
        return a


svc = Service()


def test_class_16_zero_arg():
    assert svc.get_count() == 42
    assert Service.get_count(svc) == 42


def test_class_16_scalar():
    assert svc.double(5) == 10
    assert svc.double(x=5) == 10
    assert Service.double(svc, 5) == 10
    with pytest.raises(TypeError, match="Type mismatch"):
        svc.double("not_an_int")


def test_class_16_multi_arg():
    assert svc.repeat(3) == "yoyoyo"
    assert svc.repeat(2, "ha") == "haha"
    assert svc.repeat(b="hi", a=2) == "hihi"
    assert Service.repeat(svc, a=2, b="hey") == "heyhey"
    with pytest.raises(TypeError, match="Type mismatch"):
        svc.repeat("not_an_int")
    with pytest.raises(TypeError, match="Type mismatch"):
        svc.repeat(2, 123)


def test_class_16_collections():
    assert svc.process_list([1, 2, 3]) == 6
    assert svc.process_dict({"a": 1, "b": 2}) == 3
    assert svc.process_list_dict([{"a": 1}, {"b": 2}]) == 3

    with pytest.raises(TypeError, match="Type mismatch"):
        svc.process_list([1, "two", 3])
    with pytest.raises(TypeError, match="Type mismatch"):
        svc.process_dict({"a": "bad"})
    with pytest.raises(TypeError, match="Type mismatch"):
        svc.process_list_dict([{"a": "bad"}])


def test_class_16_partial():
    assert svc.partial(10, "anything") == 10
    assert svc.partial(10, None) == 10
    with pytest.raises(TypeError, match="Type mismatch"):
        svc.partial("not_an_int", "anything")
