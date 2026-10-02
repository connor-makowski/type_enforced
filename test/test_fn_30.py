import os
import platform
import pytest
import type_enforced


def test_cpp_check():
    if (
        # Hard check if passed from the system environment
        os.environ.get("TYPE_ENFORCED_REQUIRE_PYTHON") == "1"
    ):
        assert (
            not type_enforced.has_cpp()
        ), "Expected pure Python fallback, but has_cpp() is True!"
    # Hard check if C++ extension is required
    elif os.environ.get("TYPE_ENFORCED_REQUIRE_CPP") == "1":
        assert (
            type_enforced.has_cpp()
        ), "Expected C++ extension to be active, but has_cpp() is False!"
    else:
        assert isinstance(type_enforced.has_cpp(), bool)


def test_validate_env_contradiction(monkeypatch):
    from type_enforced.utils import _validate_env

    monkeypatch.setenv("TYPE_ENFORCED_REQUIRE_CPP", "1")
    monkeypatch.setenv("TYPE_ENFORCED_REQUIRE_PYTHON", "1")
    with pytest.raises(ValueError, match="Contradictory environment"):
        _validate_env()

    monkeypatch.setenv("TYPE_ENFORCED_REQUIRE_CPP", "1")
    monkeypatch.delenv("TYPE_ENFORCED_REQUIRE_PYTHON", raising=False)
    monkeypatch.setenv("TYPE_ENFORCED_NO_BUILD", "1")
    with pytest.raises(ValueError, match="Contradictory environment"):
        _validate_env()


def test_validate_env_warnings(monkeypatch):
    from type_enforced.utils import _validate_env

    # 1. Require CPP but CPP is not active -> Warning
    monkeypatch.setenv("TYPE_ENFORCED_REQUIRE_CPP", "1")
    monkeypatch.delenv("TYPE_ENFORCED_REQUIRE_PYTHON", raising=False)
    monkeypatch.delenv("TYPE_ENFORCED_NO_BUILD", raising=False)
    with pytest.raises(Exception, match="TYPE_ENFORCED_REQUIRE_CPP is set"):
        _validate_env(cpp_override=False)

    # 2. Require Python but CPP is active -> Warning
    monkeypatch.delenv("TYPE_ENFORCED_REQUIRE_CPP", raising=False)
    monkeypatch.setenv("TYPE_ENFORCED_REQUIRE_PYTHON", "1")
    with pytest.raises(Exception, match="TYPE_ENFORCED_REQUIRE_PYTHON is set"):
        _validate_env(cpp_override=True)


def test_cpp_accelerated_collections():
    @type_enforced.Enforcer
    def fn_list_int(x: list[int]) -> int:
        return sum(x)

    assert fn_list_int([1, 2, 3, 4, 5]) == 15
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_list_int([1, "bad", 3])

    @type_enforced.Enforcer
    def fn_list_union(x: list[int | float]) -> float:
        return sum(x)

    assert fn_list_union([1, 2.5, 3]) == 6.5
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_list_union([1, "bad", 3])

    @type_enforced.Enforcer
    def fn_dict_simple(d: dict[str, int]) -> int:
        return sum(d.values())

    assert fn_dict_simple({"a": 1, "b": 2}) == 3
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_dict_simple({"a": "bad"})

    @type_enforced.Enforcer
    def fn_set_simple(s: set[str]) -> int:
        return len(s)

    assert fn_set_simple({"a", "b", "c"}) == 3
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_set_simple({"a", 123})

    @type_enforced.Enforcer
    def fn_tuple_var(t: tuple[int, ...]) -> int:
        return sum(t)

    assert fn_tuple_var((10, 20, 30)) == 60
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_tuple_var((10, "bad", 30))

    @type_enforced.Enforcer
    def fn_tuple_fixed(t: tuple[str, int]) -> str:
        return f"{t[0]}_{t[1]}"

    assert fn_tuple_fixed(("key", 100)) == "key_100"
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_tuple_fixed(("key", "bad"))

    @type_enforced.Enforcer
    def fn_list_dict(x: list[dict[str, int]]) -> int:
        return sum(sum(d.values()) for d in x)

    assert fn_list_dict([{"a": 1}, {"b": 2, "c": 3}]) == 6
    with pytest.raises(TypeError, match="Type mismatch"):
        fn_list_dict([{"a": 1}, {"b": "bad"}])
