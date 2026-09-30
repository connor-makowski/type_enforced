import pytest
import type_enforced


@pytest.mark.parametrize(
    "name", ["value", "a_parameter_with_a_long_name", "παράμετρος"]
)
def test_keyword_name_lookup(name):
    namespace = {}
    exec(
        f"def fn({name}: int, *, label: str, **extra: float):\n"
        f"    return {name}, label, extra\n",
        namespace,
    )
    fn = type_enforced.Enforcer(namespace["fn"])
    # Equal names created at runtime must work as well as literal keywords.
    key = name.encode().decode()
    kwargs = {key: 1, "label": "ok", "extra_value": 2.5}
    assert fn(**kwargs) == (1, "ok", {"extra_value": 2.5})
    assert fn(1, label="ok", extra_value=2.5) == (
        1,
        "ok",
        {"extra_value": 2.5},
    )

    for bad_key in kwargs:
        with pytest.raises(TypeError, match="Type mismatch"):
            fn(**(kwargs | {bad_key: None}))


def test_keyword_lookup_preserves_embedded_null():
    @type_enforced.Enforcer
    def fn(value: int, **extra: str):
        return value, extra

    # This is an extra keyword, not the parameter named "value".
    assert fn(1, **{"value\0suffix": "ok"}) == (
        1,
        {"value\0suffix": "ok"},
    )
    with pytest.raises(TypeError, match="Type mismatch"):
        fn(1, **{"value\0suffix": 2})
