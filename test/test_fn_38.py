import ast
import inspect
import pathlib
import sys
import traceback
import pytest
import type_enforced


# ---------------------------------------------------------------------------
# 1. GitHub Issue #87 Reproducer: co_lines() line table fidelity
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
def issue_87_fn(x: int) -> int:
    y = x + 1
    z = y * 2
    return z


def test_issue_87_line_table_fidelity():
    tree = ast.parse(pathlib.Path(__file__).read_text())
    (fn_node,) = [
        n for n in tree.body if getattr(n, "name", None) == "issue_87_fn"
    ]
    body_lines = {stmt.lineno for stmt in fn_node.body}

    code = getattr(issue_87_fn, "__fn__", issue_87_fn).__code__
    claimed_lines = {line for _, _, line in code.co_lines() if line}

    # co_lines must be a superset of actual body line numbers
    assert (
        body_lines <= claimed_lines
    ), f"Missing lines: {sorted(body_lines - claimed_lines)}"
    assert issue_87_fn(5) == 12


# ---------------------------------------------------------------------------
# 2. Multiple Decorators Line Table Fidelity
# ---------------------------------------------------------------------------
def passthrough_dec(f):
    return f


@passthrough_dec
@type_enforced.Enforcer
@passthrough_dec
def multi_dec_fn(a: int, b: str) -> str:
    c = str(a)
    res = c + b
    return res


def test_multi_decorator_line_table():
    tree = ast.parse(pathlib.Path(__file__).read_text())
    (fn_node,) = [
        n for n in tree.body if getattr(n, "name", None) == "multi_dec_fn"
    ]
    body_lines = {stmt.lineno for stmt in fn_node.body}

    code = getattr(multi_dec_fn, "__fn__", multi_dec_fn).__code__
    claimed_lines = {line for _, _, line in code.co_lines() if line}

    assert (
        body_lines <= claimed_lines
    ), f"Missing lines: {sorted(body_lines - claimed_lines)}"
    assert multi_dec_fn(42, "items") == "42items"


# ---------------------------------------------------------------------------
# 3. Class Method Line Table Fidelity
# ---------------------------------------------------------------------------
class Service:
    @type_enforced.Enforcer
    def compute(self, val: int) -> int:
        step1 = val * 3
        step2 = step1 + 7
        return step2


def test_class_method_line_table():
    tree = ast.parse(pathlib.Path(__file__).read_text())
    (cls_node,) = [
        n for n in tree.body if getattr(n, "name", None) == "Service"
    ]
    (method_node,) = [
        n for n in cls_node.body if getattr(n, "name", None) == "compute"
    ]
    body_lines = {stmt.lineno for stmt in method_node.body}

    method_code = getattr(Service.compute, "__fn__", Service.compute).__code__
    claimed_lines = {line for _, _, line in method_code.co_lines() if line}

    assert (
        body_lines <= claimed_lines
    ), f"Missing lines: {sorted(body_lines - claimed_lines)}"
    s = Service()
    assert s.compute(10) == 37


# ---------------------------------------------------------------------------
# 4. Multi-line Signature with Docstring Line Table Fidelity
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
def multiline_sig_fn(
    first: int,
    second: int,
) -> int:
    """A sample docstring for multiline test."""
    step_a = first + 10
    step_b = second + 20
    return step_a + step_b


def test_multiline_sig_line_table():
    tree = ast.parse(pathlib.Path(__file__).read_text())
    (fn_node,) = [
        n for n in tree.body if getattr(n, "name", None) == "multiline_sig_fn"
    ]
    body_lines = {stmt.lineno for stmt in fn_node.body}

    code = getattr(multiline_sig_fn, "__fn__", multiline_sig_fn).__code__
    claimed_lines = {line for _, _, line in code.co_lines() if line}

    assert (
        body_lines <= claimed_lines
    ), f"Missing lines: {sorted(body_lines - claimed_lines)}"
    assert multiline_sig_fn(1, 2) == 33


# ---------------------------------------------------------------------------
# 5. Body Exception Line Number in Traceback
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
def error_in_body_fn(x: int) -> int:
    a = x + 1
    raise RuntimeError("error_on_this_exact_line")


def test_body_exception_traceback_line():
    tree = ast.parse(pathlib.Path(__file__).read_text())
    (fn_node,) = [
        n for n in tree.body if getattr(n, "name", None) == "error_in_body_fn"
    ]
    raise_stmt = [s for s in fn_node.body if isinstance(s, ast.Raise)][0]
    expected_line = raise_stmt.lineno

    try:
        error_in_body_fn(10)
    except RuntimeError:
        _, _, tb = sys.exc_info()
        tb_frames = traceback.extract_tb(tb)
        # Find the frame for error_in_body_fn
        fn_frame = [f for f in tb_frames if f.name == "error_in_body_fn"][0]
        assert (
            fn_frame.lineno == expected_line
        ), f"Expected line {expected_line}, got {fn_frame.lineno}"
