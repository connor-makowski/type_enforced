import pytest
import typing
from dataclasses import dataclass
from typing import Literal, Callable, Sized, Any
import type_enforced
from type_enforced.utils import Constraint, GenericConstraint


def test_readme_quick_start():
    @type_enforced.Enforcer
    def greet(name: str, repeat: int = 1) -> str:
        return f"Hello {name}!" * repeat

    assert greet("Alice", 2) == "Hello Alice!Hello Alice!"
    assert greet("Alice") == "Hello Alice!"

    with pytest.raises(TypeError, match="Type mismatch"):
        greet("Alice", "twice")


def test_readme_functions_and_methods():
    @type_enforced.Enforcer
    def process_user(
        user_id: int, tags: list[str], active: bool = True
    ) -> dict[str, str | int]:
        return {
            "user_id": user_id,
            "status": "active" if active else "inactive",
        }

    assert process_user(123, ["admin"]) == {
        "user_id": 123,
        "status": "active",
    }
    assert process_user(456, ["editor", "viewer"], False) == {
        "user_id": 456,
        "status": "inactive",
    }

    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `user_id`"
    ):
        process_user("123", ["admin"])

    with pytest.raises(TypeError, match="Type mismatch"):
        process_user(123, [123])


def test_readme_classes_and_dataclasses():
    @type_enforced.Enforcer
    class Account:
        def __init__(self, username: str, balance: float):
            self.username = username
            self.balance = balance

        def deposit(self, amount: float) -> float:
            self.balance += amount
            return self.balance

        @staticmethod
        def validate_code(code: str) -> bool:
            return len(code) == 6

    acc = Account("alice", 100.0)
    assert acc.username == "alice"
    assert acc.balance == 100.0
    assert acc.deposit(50.0) == 150.0
    assert Account.validate_code("123456") is True

    with pytest.raises(TypeError, match="Type mismatch"):
        Account(123, 100.0)

    with pytest.raises(TypeError, match="Type mismatch"):
        acc.deposit("fifty")

    with pytest.raises(TypeError, match="Type mismatch"):
        Account.validate_code(123456)


def test_readme_dataclass():
    @type_enforced.Enforcer
    @dataclass
    class UserConfig:
        retries: int
        endpoint: str

    cfg = UserConfig(3, "https://api.example.com")
    assert cfg.retries == 3
    assert cfg.endpoint == "https://api.example.com"

    with pytest.raises(TypeError, match="Type mismatch"):
        UserConfig("three", "https://api.example.com")


def test_readme_class_method_disabled_override():
    @type_enforced.Enforcer
    class Worker:
        def standard_job(self, task: str) -> None:
            pass

        @type_enforced.Enforcer(enabled=False)
        def high_throughput_job(self, data):
            # Type enforcement skipped for maximum throughput
            pass

    w = Worker()
    assert w.standard_job("clean") is None
    with pytest.raises(TypeError, match="Type mismatch"):
        w.standard_job(123)

    # Disabled method accepts anything
    assert w.high_throughput_job(123) is None
    assert w.high_throughput_job("anything") is None


def test_readme_module_enforcer_top_of_file():
    import sys
    import types

    mod_name = "my_readme_top_package"
    mod = types.ModuleType(mod_name)
    sys.modules[mod_name] = mod
    try:
        exec(
            """
import type_enforced

type_enforced.ModuleEnforcer()

def add(a: int, b: int) -> int:
    return a + b

class Helper:
    def run(self, flag: bool) -> str:
        return "ok" if flag else "failed"
""",
            mod.__dict__,
        )
        assert mod.add(1, 2) == 3
        with pytest.raises(TypeError, match="Type mismatch"):
            mod.add("1", 2)

        helper = mod.Helper()
        assert helper.run(True) == "ok"
        assert helper.run(False) == "failed"
        with pytest.raises(TypeError, match="Type mismatch"):
            helper.run("true")
    finally:
        sys.modules.pop(mod_name, None)


def test_readme_module_enforcer_imported():
    import types

    my_package = types.ModuleType("my_package")
    exec(
        """
def add(a: int, b: int) -> int:
    return a + b

class Helper:
    def run(self, flag: bool) -> str:
        return "ok" if flag else "failed"
""",
        my_package.__dict__,
    )

    type_enforced.ModuleEnforcer(my_package)

    assert my_package.add(10, 20) == 30
    with pytest.raises(TypeError, match="Type mismatch"):
        my_package.add("10", 20)

    helper = my_package.Helper()
    assert helper.run(True) == "ok"
    assert helper.run(False) == "failed"
    with pytest.raises(TypeError, match="Type mismatch"):
        helper.run("true")


def test_readme_builtins_and_unions():
    @type_enforced.Enforcer
    def fn(
        a: int,
        b: str | float,
        c: int | None = None,
    ) -> None:
        pass

    assert fn(1, "hello") is None
    assert fn(1, 3.14, 42) is None

    with pytest.raises(TypeError, match="Type mismatch"):
        fn("invalid", "hello")

    with pytest.raises(TypeError, match="Type mismatch"):
        fn(1, [1, 2])

    with pytest.raises(TypeError, match="Type mismatch"):
        fn(1, "hello", "none")


def test_readme_collections_and_nested_generics():
    @type_enforced.Enforcer
    def fn(
        items: list[int | float],
        mapping: dict[str, list[int]],
        unique_ids: set[str],
        fixed_pair: tuple[str, int],
        var_tuple: tuple[int, ...],
    ) -> None:
        pass

    assert (
        fn(
            items=[1, 2.5, 3],
            mapping={"numbers": [10, 20]},
            unique_ids={"user_1", "user_2"},
            fixed_pair=("key", 100),
            var_tuple=(1, 2, 3, 4),
        )
        is None
    )

    with pytest.raises(TypeError, match="Type mismatch"):
        fn(["bad_type"], {"a": [1]}, {"id"}, ("x", 1), (1, 2))

    with pytest.raises(TypeError, match="Type mismatch"):
        fn([1], {"a": ["not_int"]}, {"id"}, ("x", 1), (1, 2))

    with pytest.raises(TypeError, match="Type mismatch"):
        fn([1], {"a": [1]}, {123}, ("x", 1), (1, 2))

    with pytest.raises(TypeError, match="Type mismatch"):
        fn([1], {"a": [1]}, {"id"}, ("x", "not_int"), (1, 2))

    with pytest.raises(TypeError, match="Type mismatch"):
        fn([1], {"a": [1]}, {"id"}, ("x", 1), (1, "two", 3))


def test_readme_classes_and_subclass_inheritance():
    class Animal:
        pass

    class Dog(Animal):
        pass

    class Vehicle:
        pass

    @type_enforced.Enforcer
    def feed(animal: Animal) -> None:
        pass

    assert feed(Animal()) is None
    assert feed(Dog()) is None

    with pytest.raises(TypeError, match="Type mismatch"):
        feed(Vehicle())

    with pytest.raises(TypeError, match="Type mismatch"):
        feed(Animal)


def test_readme_uninitialized_class_type():
    class Animal:
        pass

    @type_enforced.Enforcer
    def make_instance(cls: typing.Type[Animal]) -> Animal:
        return cls()

    inst = make_instance(Animal)
    assert isinstance(inst, Animal)

    with pytest.raises(Exception):
        make_instance(Animal())


def test_readme_literals_and_special_types():
    @type_enforced.Enforcer
    def fn(
        mode: Literal["read", "write"],
        handler: Callable,
        container: Sized,
        wildcard: Any,
    ) -> None:
        pass

    assert fn("read", lambda: None, [1, 2, 3], {"any": "thing"}) is None
    assert fn("write", len, "string_container", 42) is None

    with pytest.raises(TypeError, match="Type mismatch"):
        fn("execute", lambda: None, [1], "wildcard")

    with pytest.raises(TypeError, match="Type mismatch"):
        fn("read", "not_a_callable", [1], "wildcard")

    with pytest.raises(TypeError, match="Type mismatch"):
        fn("read", lambda: None, 12345, "wildcard")


def test_readme_stacking_literals_with_unions():
    @type_enforced.Enforcer
    def fn(val: int | Literal["auto"]) -> str:
        return str(val)

    assert fn(42) == "42"
    assert fn("auto") == "auto"

    with pytest.raises(TypeError, match="Type mismatch"):
        fn("manual")

    with pytest.raises(TypeError, match="Type mismatch"):
        fn(3.14)


def test_readme_builtin_constraints():
    @type_enforced.Enforcer
    def set_score(
        score: int | Constraint(ge=0, le=100),
        code: str | Constraint(pattern=r"^[A-Z]{3}-\d{4}$"),
    ) -> bool:
        return True

    assert set_score(85, "ABC-1234") is True
    assert set_score(0, "ZZZ-9999") is True
    assert set_score(100, "AAA-0000") is True

    # Out of range constraints
    with pytest.raises(TypeError, match="Constraint `Less Than Or Equal To"):
        set_score(105, "ABC-1234")

    with pytest.raises(TypeError, match="Constraint `Greater Than Or Equal To"):
        set_score(-1, "ABC-1234")

    # Regex pattern mismatch
    with pytest.raises(TypeError, match="Constraint `Regex Pattern Match`"):
        set_score(85, "invalid")

    with pytest.raises(TypeError, match="Constraint `Regex Pattern Match`"):
        set_score(85, "abc-1234")


def test_readme_all_constraint_options():
    @type_enforced.Enforcer
    def validate_bounds(
        val_gt: int | Constraint(gt=10),
        val_lt: int | Constraint(lt=10),
        val_eq: int | Constraint(eq=5),
        val_ne: int | Constraint(ne=5),
        val_inc: str | Constraint(includes=["a", "b"]),
        val_exc: str | Constraint(excludes=["x", "y"]),
    ) -> bool:
        return True

    assert (
        validate_bounds(
            val_gt=15,
            val_lt=5,
            val_eq=5,
            val_ne=6,
            val_inc="a",
            val_exc="z",
        )
        is True
    )

    with pytest.raises(TypeError, match="Greater Than"):
        validate_bounds(10, 5, 5, 6, "a", "z")

    with pytest.raises(TypeError, match="Less Than"):
        validate_bounds(15, 10, 5, 6, "a", "z")

    with pytest.raises(TypeError, match="Equal To"):
        validate_bounds(15, 5, 6, 6, "a", "z")

    with pytest.raises(TypeError, match="Not Equal To"):
        validate_bounds(15, 5, 5, 5, "a", "z")

    with pytest.raises(TypeError, match="Includes"):
        validate_bounds(15, 5, 5, 6, "c", "z")

    with pytest.raises(TypeError, match="Excludes"):
        validate_bounds(15, 5, 5, 6, "a", "x")


def test_readme_generic_constraint():
    RGBColor = str | GenericConstraint(
        {"valid_hex_color": lambda c: c.startswith("#") and len(c) in (4, 7)}
    )

    @type_enforced.Enforcer
    def render(color: RGBColor) -> None:
        pass

    assert render("#ffffff") is None
    assert render("#fff") is None

    with pytest.raises(TypeError, match="Constraint `valid_hex_color` not met"):
        render("red")

    with pytest.raises(TypeError, match="Constraint `valid_hex_color` not met"):
        render("#12345678")


def test_readme_stacked_constraints():
    @type_enforced.Enforcer
    def bound_check(x: int | Constraint(ge=0) | Constraint(le=10)) -> int:
        return x

    assert bound_check(0) == 0
    assert bound_check(5) == 5
    assert bound_check(10) == 10

    with pytest.raises(TypeError, match="Greater Than Or Equal To"):
        bound_check(-1)

    with pytest.raises(TypeError, match="Less Than Or Equal To"):
        bound_check(11)

    with pytest.raises(TypeError, match="Type mismatch"):
        bound_check("5")


def test_readme_only_typed_mode():
    @type_enforced.Enforcer(only_typed=True)
    def calculate(a: int, b: int) -> int:
        return a + b

    assert calculate(5, 10) == 15

    with pytest.raises(TypeError, match="Type mismatch"):
        calculate("5", 10)

    # Missing parameter annotation raises TypeError at decoration time
    with pytest.raises(TypeError, match="Untyped variable `b`"):

        @type_enforced.Enforcer(only_typed=True)
        def invalid_param_fn(a: int, b):
            return a

    # Missing return annotation raises TypeError at decoration time
    with pytest.raises(TypeError, match="Untyped return value"):

        @type_enforced.Enforcer(only_typed=True)
        def invalid_return_fn(a: int, b: int):
            return a + b


def test_readme_only_typed_classes_and_modules():
    import types

    # Class with only_typed=True
    @type_enforced.Enforcer(only_typed=True)
    class Config:
        def get_value(self, key: str) -> str:
            return key

    c = Config()
    assert c.get_value("test") == "test"

    with pytest.raises(TypeError, match="Untyped variable `key`"):

        @type_enforced.Enforcer(only_typed=True)
        class BadConfig:
            def get_value(self, key):
                return key

    # Module with only_typed=True
    mod = types.ModuleType("only_typed_mod")
    exec(
        """
def untyped_param(x):
    return x
""",
        mod.__dict__,
    )
    with pytest.raises(TypeError, match="Untyped variable `x`"):
        type_enforced.ModuleEnforcer(mod, only_typed=True)


def test_readme_configuration_strict_false(capsys):
    @type_enforced.Enforcer(strict=False)
    def lenient_fn(x: int) -> int:
        return x

    # When strict=False, does not raise exception, prints warning
    result = lenient_fn("not_an_int")
    assert result == "not_an_int"
    captured = capsys.readouterr()
    assert "TypeEnforced Warning" in captured.out


def test_readme_configuration_iterable_sample_pct():
    # iterable_sample_pct='first' validates only first item in O(1) time
    @type_enforced.Enforcer(iterable_sample_pct="first")
    def fast_check(items: list[int]) -> int:
        return len(items)

    assert fast_check([1, 2, 3]) == 3
    with pytest.raises(TypeError, match="Type mismatch"):
        fast_check(["bad_first", 2, 3])


def test_readme_clean_traceback():
    @type_enforced.Enforcer(clean_traceback=True)
    def strict_fn(x: int) -> int:
        return x

    with pytest.raises(TypeError, match="Type mismatch"):
        strict_fn("invalid")
