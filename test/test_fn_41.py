import sys
import subprocess
import pytest
from typing import TypedDict
import type_enforced
from type_enforced import Enforcer

# ---------------------------------------------------------------------------
# GitHub Issue #97 Reproducer:
# C++ backend: list validation reads freed memory when an element check
# modifies the list
# ---------------------------------------------------------------------------


class TD(TypedDict):
    a: int


victim = None


class K:
    fired = True

    def __hash__(self):
        return hash("a")

    def __eq__(self, other):
        if not K.fired:
            K.fired = True
            victim.clear()
        return False


@Enforcer
def f(x: list[TD], b=0, c=0, d=0):
    return len(x)


@pytest.mark.skipif(not type_enforced.has_cpp(), reason="C++ backend only")
def test_list_modification_during_typeddict_validation():
    code = """
from typing import TypedDict
import type_enforced

class TD(TypedDict):
    a: int

victim = None

class K:
    fired = True
    def __hash__(self):
        return hash("a")
    def __eq__(self, other):
        if not K.fired:
            K.fired = True
            victim.clear()
        return False

@type_enforced.Enforcer
def f(x: list[TD], b=0, c=0, d=0):
    return len(x)

keep = [{K(): 0, "a": 1} for _ in range(200000)]
victim = list(keep)
K.fired = False

assert f(victim) == 0
"""
    import os

    env = dict(os.environ, PYTHONMALLOC="debug")
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
    )
    assert (
        result.returncode == 0
    ), f"Validation crashed or failed with exit code {result.returncode}: {result.stderr.strip()}"


@pytest.mark.skipif(not type_enforced.has_cpp(), reason="C++ backend only")
def test_dict_modification_during_typeddict_validation():
    code = """
import os
from typing import TypedDict
import type_enforced

class TD(TypedDict):
    a: int

victim = None

class K:
    fired = True
    def __hash__(self):
        return hash("a")
    def __eq__(self, other):
        if not K.fired:
            K.fired = True
            victim.clear()
        return False

@type_enforced.Enforcer
def f(x: dict[str, TD]):
    return len(x)

victim = {str(i): {K(): 0, "a": 1} for i in range(200000)}
K.fired = False

assert f(victim) == 0
"""
    import os

    env = dict(os.environ, PYTHONMALLOC="debug")
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
    )
    assert (
        result.returncode == 0
    ), f"Validation crashed or failed with exit code {result.returncode}: {result.stderr.strip()}"
