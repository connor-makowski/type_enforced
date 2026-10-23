import type_enforced

# ---------------------------------------------------------------------------
# GitHub Issue #98 Reproducer:
# Inlining overwrites module globals and adds globals that are never removed
# ---------------------------------------------------------------------------

# 1. A module-level name that shadows a builtin should not be overwritten
custom_callable = lambda: "app helper"
callable = custom_callable


@type_enforced.Enforcer
def sample_fn(x: int) -> int:
    return x


def test_issue_98_does_not_overwrite_module_globals():
    assert (
        callable is custom_callable
    ), "Module-level `callable` was overwritten with builtin callable"


def test_issue_98_no_lingering_enf_globals():
    def make():
        @type_enforced.Enforcer
        def handler(x: int) -> int:
            return x

        return handler

    before = sum(k.startswith("__enf_") for k in globals())
    for _ in range(10):
        make()
    after = sum(k.startswith("__enf_") for k in globals())

    assert (
        after == before
    ), f"Expected no lingering __enf_ globals, but {after - before} were added"
