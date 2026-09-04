import sys
from typing import (
    Any,
    Callable,
    Literal,
    NewType,
    NoReturn,
    Optional,
    TypeVar,
    Union,
    get_type_hints,
)
import pytest
import type_enforced

# Safely import optional typing constructs
try:
    from typing import Self
except ImportError:
    Self = None

try:
    from typing import Never
except ImportError:
    Never = None

try:
    from typing import LiteralString
except ImportError:
    LiteralString = None

try:
    from typing import TypeGuard
except ImportError:
    TypeGuard = None

try:
    from typing import TypeIs
except ImportError:
    TypeIs = None

try:
    from typing import TypedDict
except ImportError:
    TypedDict = None

try:
    from typing import ParamSpec, TypeVarTuple
except ImportError:
    ParamSpec = None
    TypeVarTuple = None


# ---------------------------------------------------------------------------
# 1. PEP 673: typing.Self
# ---------------------------------------------------------------------------
if Self is not None:

    class Builder:
        def __init__(self, value: int = 0):
            self.value = value

        @type_enforced.Enforcer
        def set_value(self, value: int) -> Self:
            self.value = value
            return self

        @type_enforced.Enforcer
        def invalid_return(self) -> Self:
            return "not_a_builder"  # type: ignore

        @type_enforced.Enforcer
        def combine(self, other: Self) -> Self:
            self.value += other.value
            return self

    class SubBuilder(Builder):
        pass


def test_pep_673_self():
    if Self is None:
        pytest.skip("typing.Self not available in this Python version")

    b = Builder(10)
    res = b.set_value(20)
    assert res is b
    assert b.value == 20

    b2 = Builder(5)
    b.combine(b2)
    assert b.value == 25

    # Subclass instance satisfies Self
    sub = SubBuilder(100)
    sub_res = sub.set_value(200)
    assert sub_res is sub
    assert sub.value == 200

    # Type mismatch on return
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `return`"
    ):
        b.invalid_return()

    # Type mismatch on parameter
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `other`"
    ):
        b.combine("not_a_builder")  # type: ignore


# ---------------------------------------------------------------------------
# 2. PEP 484 & PEP 654: typing.NoReturn and typing.Never
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
def fn_raises_noreturn(msg: str) -> NoReturn:
    raise RuntimeError(msg)


@type_enforced.Enforcer
def fn_invalid_noreturn() -> NoReturn:
    return None  # type: ignore


if Never is not None:

    @type_enforced.Enforcer
    def fn_raises_never(msg: str) -> Never:
        raise ValueError(msg)

    @type_enforced.Enforcer
    def fn_invalid_never() -> Never:
        return 42  # type: ignore

    @type_enforced.Enforcer
    def fn_accepts_never(x: Never) -> None:
        pass


def test_pep_484_654_noreturn_never():
    with pytest.raises(RuntimeError, match="boom"):
        fn_raises_noreturn("boom")

    with pytest.raises(TypeError, match="Expected `NoReturn` / `Never`"):
        fn_invalid_noreturn()

    if Never is not None:
        with pytest.raises(ValueError, match="never"):
            fn_raises_never("never")

        with pytest.raises(TypeError, match="Expected `NoReturn` / `Never`"):
            fn_invalid_never()

        with pytest.raises(TypeError, match="Expected `NoReturn` / `Never`"):
            fn_accepts_never(123)  # type: ignore


# ---------------------------------------------------------------------------
# 3. PEP 484: typing.NewType
# ---------------------------------------------------------------------------
UserId = NewType("UserId", int)
UserName = NewType("UserName", str)


@type_enforced.Enforcer
def get_user_profile(user_id: UserId, name: UserName) -> dict[str, int | str]:
    return {"id": user_id, "name": name}


@type_enforced.Enforcer
def get_user_ids(ids: list[UserId]) -> list[UserId]:
    return ids


def test_pep_484_newtype():
    uid = UserId(42)
    uname = UserName("Alice")

    res = get_user_profile(uid, uname)
    assert res == {"id": 42, "name": "Alice"}

    # Also accepts underlying primitive types as NewType is an alias at runtime
    res2 = get_user_profile(100, "Bob")
    assert res2 == {"id": 100, "name": "Bob"}

    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `user_id`"
    ):
        get_user_profile("bad_id", uname)  # type: ignore

    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `name`"
    ):
        get_user_profile(uid, 999)  # type: ignore

    # Nested generics with NewType
    assert get_user_ids([UserId(1), UserId(2)]) == [1, 2]
    with pytest.raises(TypeError, match="Type mismatch"):
        get_user_ids([UserId(1), "bad_id"])  # type: ignore


# ---------------------------------------------------------------------------
# 4. PEP 589: typing.TypedDict
# ---------------------------------------------------------------------------
if TypedDict is not None:

    class Person(TypedDict):
        name: str
        age: int

    class OptionalPerson(TypedDict, total=False):
        nickname: str
        score: float

    class Company(TypedDict):
        owner: Person
        employees: list[Person]

    @type_enforced.Enforcer
    def register_person(p: Person) -> str:
        return f"{p['name']} ({p['age']})"

    @type_enforced.Enforcer
    def register_optional(p: OptionalPerson) -> int:
        return len(p)

    @type_enforced.Enforcer
    def register_company(c: Company) -> int:
        return len(c["employees"])


def test_pep_589_typeddict():
    if TypedDict is None:
        pytest.skip("TypedDict not available")

    # Valid TypedDict
    p: Person = {"name": "Alice", "age": 30}
    assert register_person(p) == "Alice (30)"

    # Missing required key
    with pytest.raises(TypeError, match="missing required key"):
        register_person({"name": "Alice"})  # type: ignore

    # Invalid field type
    with pytest.raises(TypeError, match="Type mismatch"):
        register_person({"name": "Alice", "age": "thirty"})  # type: ignore

    # Non-dict passed
    with pytest.raises(TypeError):
        register_person("not_a_dict")  # type: ignore

    # Optional TypedDict (total=False)
    assert register_optional({}) == 0
    assert register_optional({"nickname": "Al"}) == 1
    assert register_optional({"nickname": "Al", "score": 9.5}) == 2
    with pytest.raises(TypeError, match="Type mismatch"):
        register_optional({"nickname": 123})  # type: ignore

    # Nested TypedDict
    comp: Company = {
        "owner": {"name": "Alice", "age": 30},
        "employees": [
            {"name": "Bob", "age": 25},
            {"name": "Charlie", "age": 28},
        ],
    }
    assert register_company(comp) == 2

    # Nested TypedDict with invalid item
    bad_comp = {
        "owner": {"name": "Alice", "age": 30},
        "employees": [
            {"name": "Bob", "age": "invalid_age"},
        ],
    }
    with pytest.raises(TypeError):
        register_company(bad_comp)  # type: ignore


# ---------------------------------------------------------------------------
# 5. PEP 484 & PEP 612: Subscripted typing.Callable
# ---------------------------------------------------------------------------
class CustomCallable:
    def __call__(self, x: int) -> int:
        return x * 2


@type_enforced.Enforcer
def apply_fn(
    fn: Callable[[int, str], str],
    count: int,
    prefix: str,
) -> str:
    return fn(count, prefix)


@type_enforced.Enforcer
def apply_any_callable(fn: Callable[..., Any], *args: Any) -> Any:
    return fn(*args)


def test_pep_484_612_callable():
    # Regular function
    def my_callback(n: int, s: str) -> str:
        return f"{s}_{n}"

    assert apply_fn(my_callback, 3, "item") == "item_3"

    # Lambda
    assert apply_fn(lambda n, s: f"{s}*{n}", 2, "ok") == "ok*2"

    # Custom callable class instance
    custom = CustomCallable()
    assert apply_any_callable(custom, 5) == 10

    # Built-in function
    assert apply_any_callable(len, [1, 2, 3]) == 3

    # Non-callable passed
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `fn`"
    ):
        apply_fn("not_a_func", 1, "test")  # type: ignore

    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `fn`"
    ):
        apply_any_callable(42, 1, 2)  # type: ignore


# ---------------------------------------------------------------------------
# 6. PEP 675: typing.LiteralString
# ---------------------------------------------------------------------------
if LiteralString is not None:

    @type_enforced.Enforcer
    def execute_sql(query: LiteralString) -> str:
        return f"EXECUTING: {query}"


def test_pep_675_literalstring():
    if LiteralString is None:
        pytest.skip("LiteralString not available")

    assert (
        execute_sql("SELECT * FROM table") == "EXECUTING: SELECT * FROM table"
    )

    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `query`"
    ):
        execute_sql(12345)  # type: ignore


# ---------------------------------------------------------------------------
# 7. PEP 647 & PEP 742: TypeGuard and TypeIs
# ---------------------------------------------------------------------------
if TypeGuard is not None:

    @type_enforced.Enforcer
    def is_int_list(val: list[object]) -> TypeGuard[list[int]]:
        return all(isinstance(x, int) for x in val)

    @type_enforced.Enforcer
    def invalid_guard_return() -> TypeGuard[int]:
        return "not_a_bool"  # type: ignore


def test_pep_647_typeguard():
    if TypeGuard is None:
        pytest.skip("TypeGuard not available")

    assert is_int_list([1, 2, 3]) is True
    assert is_int_list([1, "2", 3]) is False

    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `return`"
    ):
        invalid_guard_return()


if TypeIs is not None:

    @type_enforced.Enforcer
    def is_str_typeis(val: object) -> TypeIs[str]:
        return isinstance(val, str)


def test_pep_742_typeis():
    if TypeIs is None:
        pytest.skip("TypeIs not available in this Python version")

    assert is_str_typeis("hello") is True
    assert is_str_typeis(123) is False


# ---------------------------------------------------------------------------
# 8. PEP 484: TypeVar, ParamSpec, TypeVarTuple
# ---------------------------------------------------------------------------
T = TypeVar("T")
T_bound = TypeVar("T_bound", bound=int | float)
T_constrained = TypeVar("T_constrained", str, bytes)


@type_enforced.Enforcer
def identity_generic(x: T) -> T:
    return x


@type_enforced.Enforcer
def add_numbers(a: T_bound, b: T_bound) -> T_bound:
    return a + b  # type: ignore


@type_enforced.Enforcer
def process_data(data: T_constrained) -> int:
    return len(data)


def test_pep_484_typevar():
    # Unconstrained TypeVar accepts anything
    assert identity_generic(10) == 10
    assert identity_generic("abc") == "abc"
    assert identity_generic([1, 2]) == [1, 2]

    # Bound TypeVar accepts bound subtypes
    assert add_numbers(3, 4) == 7
    assert add_numbers(1.5, 2.5) == 4.0
    with pytest.raises(TypeError, match="Type mismatch for typed variable `a`"):
        add_numbers("1", 2)  # type: ignore

    # Constrained TypeVar accepts only constraint types
    assert process_data("hello") == 5
    assert process_data(b"world") == 5
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `data`"
    ):
        process_data([1, 2, 3])  # type: ignore


# ---------------------------------------------------------------------------
# 9. PEP 695: Type Aliases & Generics (Python 3.12+)
# ---------------------------------------------------------------------------
def test_pep_695_type_alias_and_generics():
    if sys.version_info < (3, 12):
        pytest.skip("PEP 695 syntax requires Python 3.12+")

    code = """
type Point = tuple[float, float]

@type_enforced.Enforcer
def distance(p: Point) -> float:
    return (p[0]**2 + p[1]**2)**0.5

@type_enforced.Enforcer
def generic_fn[T](val: T, count: int) -> list[T]:
    return [val] * count
"""
    local_ns = {"type_enforced": type_enforced, "pytest": pytest}
    exec(code, local_ns, local_ns)

    distance = local_ns["distance"]
    generic_fn = local_ns["generic_fn"]

    assert distance((3.0, 4.0)) == 5.0

    with pytest.raises(TypeError):
        distance(("3.0", 4.0))

    assert generic_fn("a", 3) == ["a", "a", "a"]
    assert generic_fn(42, 2) == [42, 42]
