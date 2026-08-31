import argparse
import re
import sys
import time
from typing import Dict, List, Tuple, Union

from beartype import beartype
from pydantic import validate_call
import type_enforced

# --- Test Data Generation ---
five_item_list = [1, 2.0, 3, 4.0, 5]
list_1000 = list(range(1000))
list_10000 = list(range(10000))

dict_1000 = {f"key{i}": i for i in range(1000)}
dict_10000 = {f"key{i}": i for i in range(10000)}

list_list_100x100 = [[j for j in range(100)] for _ in range(100)]
dict_list_100x100 = {f"k{i}": [j for j in range(100)] for i in range(100)}
list_dict_100x100 = [
    {f"key{i}": i for i in range(100)} for _ in range(100)
]
list_tuple_1000 = [(i, f"str{i}", float(i)) for i in range(1000)]


def _make_multi_param_fn(n):
    params = ", ".join(f"a{i}: int" for i in range(n))
    code = f"def f_{n}({params}) -> None: pass"
    ns = {}
    exec(code, globals(), ns)
    return ns[f"f_{n}"]


f_10 = _make_multi_param_fn(10)
f_100 = _make_multi_param_fn(100)

MULTI_PARAM_FUNCS = {
    "10_params": f_10,
    "100_params": f_100,
}

# --- Test Cases & Sizes ---
CASES = [
    # (Display Type, Size Label, typ, valid_val, invalid_val)
    ("`int`", "—", int, 42, "not an int"),
    (
        "`Union[int, float]`",
        "—",
        Union[int, float],
        3.14,
        "not a number",
    ),
    ("`str`", "—", str, "hello", 123),
    (
        "`list[int]`",
        "1 000 items",
        List[int],
        list_1000,
        [1, "two", 3] * 333,
    ),
    (
        "`list[int]`",
        "10 000 items",
        List[int],
        list_10000,
        [1, "two", 3] * 3333,
    ),
    (
        "`list[int] | list[str]`",
        "1 000 items",
        Union[List[int], List[str]],
        list_1000,
        [1, "two", 3] * 333,
    ),
    (
        "`dict[str, int]`",
        "1 000 keys",
        Dict[str, int],
        dict_1000,
        {"k1": 1, "k2": "two"},
    ),
    (
        "`dict[str, int]`",
        "10 000 keys",
        Dict[str, int],
        dict_10000,
        {"k1": 1, "k2": "two"},
    ),
    (
        "`list[list[int]]`",
        "100 x 100 items",
        List[List[int]],
        list_list_100x100,
        [[1, "two"]],
    ),
    (
        "`dict[str, list[int]]`",
        "100 x 100 items",
        Dict[str, List[int]],
        dict_list_100x100,
        {"k": [1, "two"]},
    ),
    (
        "`list[dict[str, int]]`",
        "100 x 100 items",
        List[Dict[str, int]],
        list_dict_100x100,
        [{"k1": 1, "k2": "two"}],
    ),
]


# --- Checker Factories ---
def pydantic_factory(typ):
    if typ in MULTI_PARAM_FUNCS:
        return validate_call(MULTI_PARAM_FUNCS[typ])

    @validate_call
    def f(x: typ) -> None:
        pass

    return f


def beartype_factory(typ):
    if typ in MULTI_PARAM_FUNCS:
        return beartype(MULTI_PARAM_FUNCS[typ])

    @beartype
    def f(x: typ) -> None:
        pass

    return f


def type_enforced_full_factory(typ):
    if typ in MULTI_PARAM_FUNCS:
        return type_enforced.Enforcer()(MULTI_PARAM_FUNCS[typ])

    @type_enforced.Enforcer()
    def f(x: typ) -> None:
        pass

    return f


def type_enforced_sampled_factory(typ):
    if typ in MULTI_PARAM_FUNCS:
        return type_enforced.Enforcer(iterable_sample_pct="first")(
            MULTI_PARAM_FUNCS[typ]
        )

    @type_enforced.Enforcer(iterable_sample_pct="first")
    def f(x: typ) -> None:
        pass

    return f


CHECKERS = {
    "type_enforced (sample=1)": (type_enforced_sampled_factory, True),
    "Beartype (sample=1)": (beartype_factory, True),
    "type_enforced (100%)": (type_enforced_full_factory, False),
    "Pydantic (100%)": (pydantic_factory, False),
}


# --- Timing & Validation ---
def timeit_adaptive(
    func, arg, is_multi=False, min_runs=3, max_runs=100, max_sec=0.05
):
    if is_multi:
        func(*arg)
    else:
        func(arg)

    durations = []
    start = time.perf_counter()
    for _ in range(max_runs):
        t0 = time.perf_counter()
        if is_multi:
            func(*arg)
        else:
            func(arg)
        durations.append(time.perf_counter() - t0)

        if (
            len(durations) >= min_runs
            and (time.perf_counter() - start) >= max_sec
        ):
            break

    return (sum(durations) / len(durations)) * 1e6


def test_validation(func, valid_val, invalid_val, is_multi=False):
    try:
        if is_multi:
            func(*valid_val)
        else:
            func(valid_val)
        valid_ok = True
    except Exception:
        valid_ok = False

    try:
        if is_multi:
            func(*invalid_val)
        else:
            func(invalid_val)
        invalid_caught = False
    except Exception:
        invalid_caught = True

    return valid_ok and invalid_caught


def run_minibench():
    results = []
    for type_label, size_label, typ, valid_val, invalid_val in CASES:
        is_multi = typ in MULTI_PARAM_FUNCS
        row_times = {}
        row_warnings = {}

        for checker_name, (factory, is_sampled) in CHECKERS.items():
            try:
                fn = factory(typ)
                us = timeit_adaptive(fn, valid_val, is_multi=is_multi)
                passed = all(
                    test_validation(
                        fn, valid_val, invalid_val, is_multi=is_multi
                    )
                    for _ in range(10)
                )
                row_times[checker_name] = us
                row_warnings[checker_name] = not passed
            except Exception as e:
                row_times[checker_name] = None
                row_warnings[checker_name] = True

        results.append(
            (type_label, size_label, row_times, row_warnings)
        )

    return results


def format_table(results):
    headers = [
        "Type",
        "Size",
        "type_enforced (sample=1)",
        "Beartype (sample=1)",
        "type_enforced (100%)",
        "Pydantic (100%)",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|:---|:---:|:---:|:---:|:---:|:---:|",
    ]

    for type_label, size_label, times, warnings in results:
        cols = [type_label, size_label]
        for name in headers[2:]:
            t = times.get(name)
            warn = warnings.get(name, False)
            if t is None:
                cell = "Error"
            else:
                cell = f"{t:.2f} µs"
                if warn:
                    cell += " ⚠"
            cols.append(cell)

        lines.append("| " + " | ".join(cols) + " |")

    return "\n".join(lines)


def update_markdown_file(file_path, new_table):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"(\| Type \| Size \|.*?\n(?:\|.*?\n)+)"
    if re.search(pattern, content):
        updated_content = re.sub(
            pattern, new_table + "\n", content, count=1
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        print(f"Updated {file_path}")
    else:
        print(f"Could not find table in {file_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Run quick Glance benchmark"
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update table in README.md and type_enforced/__init__.py",
    )
    args = parser.parse_args()

    print("Running Performance at a Glance benchmarks...")
    results = run_minibench()
    table = format_table(results)

    print("\n### Performance at a Glance\n")
    print(table)
    print()

    if args.update:
        update_markdown_file("README.md", table)
        update_markdown_file("type_enforced/__init__.py", table)


if __name__ == "__main__":
    main()
