import pytest
import type_enforced


def test_fn_24_only_typed_default_false():
    # By default only_typed is False, untyped variables are allowed
    @type_enforced.Enforcer
    def default_fn(a, b: int) -> int:
        return b

    assert default_fn("hello", 5) == 5
    with pytest.raises(TypeError, match="Type mismatch"):
        default_fn("hello", "5")


def test_fn_24_only_typed_untyped_param():
    # When only_typed=True, untyped parameters raise TypeError upon decoration
    with pytest.raises(TypeError, match="Untyped variable `a`"):

        @type_enforced.Enforcer(only_typed=True)
        def untyped_param_fn(a, b: int) -> int:
            return b


def test_fn_24_only_typed_untyped_return():
    # When only_typed=True, untyped return raises TypeError upon decoration
    with pytest.raises(TypeError, match="Untyped return value"):

        @type_enforced.Enforcer(only_typed=True)
        def untyped_return_fn(a: int, b: int):
            return a + b


def test_fn_24_only_typed_fully_typed_passes():
    @type_enforced.Enforcer(only_typed=True)
    def fully_typed_fn(a: int, b: str) -> str:
        return f"{a}: {b}"

    assert fully_typed_fn(1, "one") == "1: one"
    with pytest.raises(TypeError, match="Type mismatch"):
        fully_typed_fn("1", "one")
    with pytest.raises(TypeError, match="Type mismatch"):
        fully_typed_fn(1, 2)


def test_fn_24_only_typed_class_and_methods():
    @type_enforced.Enforcer(only_typed=True)
    class ValidClass:
        def method(self, x: int) -> int:
            return x * 2

        @classmethod
        def class_method(cls, y: str) -> str:
            return y.upper()

        @staticmethod
        def static_method(z: float) -> float:
            return z + 1.0

    obj = ValidClass()
    assert obj.method(3) == 6
    assert ValidClass.class_method("abc") == "ABC"
    assert ValidClass.static_method(2.5) == 3.5

    with pytest.raises(TypeError, match="Type mismatch"):
        obj.method("3")

    with pytest.raises(TypeError, match="Untyped variable `x`"):

        @type_enforced.Enforcer(only_typed=True)
        class InvalidMethodClass:
            def method(self, x) -> int:
                return 1

    with pytest.raises(TypeError, match="Untyped return value"):

        @type_enforced.Enforcer(only_typed=True)
        class InvalidReturnClass:
            def method(self, x: int):
                return x


def test_fn_24_disabled_with_only_typed():
    # When enabled=False, only_typed checks are skipped and functions/methods run unenforced
    @type_enforced.Enforcer(enabled=False, only_typed=True)
    def disabled_untyped_fn(a, b):
        return a + b

    assert disabled_untyped_fn(1, 2) == 3
    assert disabled_untyped_fn("a", "b") == "ab"

    # Method-level disabled overrides class-level only_typed
    @type_enforced.Enforcer(only_typed=True)
    class MixedClass:
        def typed_method(self, x: int) -> int:
            return x

        @type_enforced.Enforcer(enabled=False)
        def untyped_method(self, x):
            return x

    obj = MixedClass()
    assert obj.typed_method(5) == 5
    with pytest.raises(TypeError, match="Type mismatch"):
        obj.typed_method("5")
    assert obj.untyped_method("anything") == "anything"

    # Class-level disabled disables all methods
    @type_enforced.Enforcer(enabled=False, only_typed=True)
    class DisabledClass:
        def bad_method(self, x):
            return x

    assert DisabledClass().bad_method("any") == "any"
