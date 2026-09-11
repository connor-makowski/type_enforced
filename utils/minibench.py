import argparse
import re
import sys
import time
from typing import Dict, List, Tuple, Union, get_args, get_origin

try:
    from beartype import beartype
except ImportError:
    beartype = None

try:
    import cattrs
except ImportError:
    cattrs = None

try:
    import msgspec
except ImportError:
    msgspec = None

try:
    from pydantic import validate_call
except ImportError:
    validate_call = None

try:
    import typeguard
except ImportError:
    typeguard = None

import type_enforced

# --- Cattrs Union structure hook ---
cattrs_conv = cattrs.Converter() if cattrs is not None else None


def structure_union(val, typ):
    args = get_args(typ)
    for arg in args:
        try:
            return cattrs_conv.structure(val, arg)
        except Exception:
            continue
    raise TypeError(f"Cannot structure {val} into {typ}")


if cattrs_conv is not None:
    cattrs_conv.register_structure_hook_func(
        lambda t: get_origin(t) is Union, structure_union
    )

POOL_SIZE = 20

# --- Test Data Generation (Distinct Pools) ---
int_pool = [i * 42 for i in range(POOL_SIZE)]
union_pool = [float(i) if i % 2 else i for i in range(POOL_SIZE)]
str_pool = [f"hello_{i}" for i in range(POOL_SIZE)]

list_1000_pool = [[j for j in range(1000)] for _ in range(POOL_SIZE)]
list_10000_pool = [[j for j in range(10000)] for _ in range(POOL_SIZE)]

dict_1000_pool = [{f"key{j}": j for j in range(1000)} for _ in range(POOL_SIZE)]
dict_10000_pool = [{f"key{j}": j for j in range(10000)} for _ in range(POOL_SIZE)]

list_list_100x100_pool = [
    [[k for k in range(100)] for _ in range(100)] for _ in range(POOL_SIZE)
]
dict_list_100x100_pool = [
    {f"k{j}": [k for k in range(100)] for j in range(100)}
    for _ in range(POOL_SIZE)
]
list_dict_100x100_pool = [
    [{f"key{k}": k for k in range(100)} for _ in range(100)]
    for _ in range(POOL_SIZE)
]


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
    # (Display Type, Size Label, typ, valid_pool, invalid_val)
    ("`int`", "—", int, int_pool, "not an int"),
    (
        "`Union[int, float]`",
        "—",
        Union[int, float],
        union_pool,
        "not a number",
    ),
    ("`str`", "—", str, str_pool, 123),
    (
        "`list[int]`",
        "1 000 items",
        List[int],
        list_1000_pool,
        [1, "two", 3] * 333,
    ),
    (
        "`list[int]`",
        "10 000 items",
        List[int],
        list_10000_pool,
        [1, "two", 3] * 3333,
    ),
    (
        "`dict[str, int]`",
        "1 000 keys",
        Dict[str, int],
        dict_1000_pool,
        {"k1": 1, "k2": "two"},
    ),
    (
        "`dict[str, int]`",
        "10 000 keys",
        Dict[str, int],
        dict_10000_pool,
        {"k1": 1, "k2": "two"},
    ),
    (
        "`list[list[int]]`",
        "100 x 100 items",
        List[List[int]],
        list_list_100x100_pool,
        [[1, "two"]],
    ),
    (
        "`dict[str, list[int]]`",
        "100 x 100 items",
        Dict[str, List[int]],
        dict_list_100x100_pool,
        {"k": [1, "two"]},
    ),
    (
        "`list[dict[str, int]]`",
        "100 x 100 items",
        List[Dict[str, int]],
        list_dict_100x100_pool,
        [{"k1": 1, "k2": "two"}],
    ),
]


# --- Checker Factories ---
def base_factory(typ):
    if typ in MULTI_PARAM_FUNCS:
        return MULTI_PARAM_FUNCS[typ]

    def f(x: typ) -> None:
        pass

    return f


def pydantic_factory(typ):
    if validate_call is None:
        raise ImportError("pydantic is not installed")
    if typ in MULTI_PARAM_FUNCS:
        return validate_call(MULTI_PARAM_FUNCS[typ])

    @validate_call
    def f(x: typ) -> None:
        pass

    return f


def beartype_factory(typ):
    if beartype is None:
        raise ImportError("beartype is not installed")
    if typ in MULTI_PARAM_FUNCS:
        return beartype(MULTI_PARAM_FUNCS[typ])

    @beartype
    def f(x: typ) -> None:
        pass

    return f


def typeguard_sampled_factory(typ):
    if typeguard is None:
        raise ImportError("typeguard is not installed")
    if typ in MULTI_PARAM_FUNCS:
        fn = MULTI_PARAM_FUNCS[typ]
        hints = [
            t
            for k, t in getattr(fn, "__annotations__", {}).items()
            if k != "return"
        ]

        def f(*args, **kwargs):
            for t, v in zip(hints, args):
                typeguard.check_type(
                    v,
                    t,
                    collection_check_strategy=typeguard.CollectionCheckStrategy.FIRST_ITEM,
                )
            return fn(*args, **kwargs)

        return f

    def f(x):
        return typeguard.check_type(
            x,
            typ,
            collection_check_strategy=typeguard.CollectionCheckStrategy.FIRST_ITEM,
        )

    return f


def typeguard_full_factory(typ):
    if typeguard is None:
        raise ImportError("typeguard is not installed")
    if typ in MULTI_PARAM_FUNCS:
        fn = MULTI_PARAM_FUNCS[typ]
        hints = [
            t
            for k, t in getattr(fn, "__annotations__", {}).items()
            if k != "return"
        ]

        def f(*args, **kwargs):
            for t, v in zip(hints, args):
                typeguard.check_type(
                    v,
                    t,
                    collection_check_strategy=typeguard.CollectionCheckStrategy.ALL_ITEMS,
                )
            return fn(*args, **kwargs)

        return f

    def f(x):
        return typeguard.check_type(
            x,
            typ,
            collection_check_strategy=typeguard.CollectionCheckStrategy.ALL_ITEMS,
        )

    return f


def msgspec_factory(typ):
    if msgspec is None:
        raise ImportError("msgspec is not installed")
    if typ in MULTI_PARAM_FUNCS:
        fn = MULTI_PARAM_FUNCS[typ]
        hints = [
            t
            for k, t in getattr(fn, "__annotations__", {}).items()
            if k != "return"
        ]

        def f(*args, **kwargs):
            for t, v in zip(hints, args):
                msgspec.convert(v, type=t)
            return fn(*args, **kwargs)

        return f

    def f(x):
        return msgspec.convert(x, type=typ)

    return f


def cattrs_factory(typ):
    if cattrs is None or cattrs_conv is None:
        raise ImportError("cattrs is not installed")
    if typ in MULTI_PARAM_FUNCS:
        fn = MULTI_PARAM_FUNCS[typ]
        hints = [
            t
            for k, t in getattr(fn, "__annotations__", {}).items()
            if k != "return"
        ]

        def f(*args, **kwargs):
            for t, v in zip(hints, args):
                cattrs_conv.structure(v, t)
            return fn(*args, **kwargs)

        return f

    def f(x):
        return cattrs_conv.structure(x, typ)

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
    "Typeguard (sample=1)": (typeguard_sampled_factory, True),
    "type_enforced (100%)": (type_enforced_full_factory, False),
    "Pydantic (100%)": (pydantic_factory, False),
    "msgspec (100%)": (msgspec_factory, False),
    "cattrs (100%)": (cattrs_factory, False),
    "Typeguard (100%)": (typeguard_full_factory, False),
}


# --- Timing & Validation with Distinct Input Pool Iteration ---
def timeit_pool(func, pool, is_multi=False, target_batch_time=0.003, repeats=5):
    pool_len = len(pool)
    # Warmup across the pool
    if is_multi:
        for obj in pool:
            func(*obj)
    else:
        for obj in pool:
            func(obj)

    # Estimate time for 1 pass of the pool
    t0 = time.perf_counter()
    if is_multi:
        for obj in pool:
            func(*obj)
    else:
        for obj in pool:
            func(obj)
    t1 = time.perf_counter()
    pool_pass_time = max(1e-9, t1 - t0)

    # Determine cycles to take ~target_batch_time
    cycles = max(1, min(int(target_batch_time / pool_pass_time), 5000))
    total_calls_per_batch = cycles * pool_len

    durations = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        if is_multi:
            for _ in range(cycles):
                for obj in pool:
                    func(*obj)
        else:
            for _ in range(cycles):
                for obj in pool:
                    func(obj)
        t1 = time.perf_counter()
        durations.append((t1 - t0) / total_calls_per_batch)

    durations.sort()
    best = durations[:3]
    return (sum(best) / len(best)) * 1e6


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
    for type_label, size_label, typ, valid_pool, invalid_val in CASES:
        is_multi = typ in MULTI_PARAM_FUNCS
        row_times = {}
        row_warnings = {}
        base_fn = base_factory(typ)
        base_us = timeit_pool(base_fn, valid_pool, is_multi=is_multi)

        for checker_name, (factory, is_sampled) in CHECKERS.items():
            try:
                fn = factory(typ)
                us = timeit_pool(fn, valid_pool, is_multi=is_multi)
                diff_us = max(0.0, us - base_us)
                passed = all(
                    test_validation(
                        fn,
                        valid_pool[i % len(valid_pool)],
                        invalid_val,
                        is_multi=is_multi,
                    )
                    for i in range(10)
                )
                row_times[checker_name] = diff_us
                row_warnings[checker_name] = not passed
            except Exception as e:
                row_times[checker_name] = None
                row_warnings[checker_name] = True

        results.append((type_label, size_label, row_times, row_warnings))

    return results


def format_table(results):
    headers = ["Type", "Size"] + list(CHECKERS.keys())
    rows = []
    for type_label, size_label, times, warnings in results:
        cols = [type_label, size_label]
        for name in headers[2:]:
            t = times.get(name)
            warn = warnings.get(name, False)
            if t is None:
                cell = "Error"
            else:
                cell = f"{t:.3f} µs"
                if warn:
                    cell += " ⚠"
            cols.append(cell)
        rows.append(cols)

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(val))

    # Add extra padding for wider columns
    for i in range(len(col_widths)):
        col_widths[i] = max(col_widths[i], 16)

    header_cols = [
        f"{headers[0]:<{col_widths[0]}}",
        f"{headers[1]:^{col_widths[1]}}",
        *[f"{h:^{col_widths[i+2]}}" for i, h in enumerate(headers[2:])],
    ]
    sep_cols = [
        ":" + "-" * (col_widths[0] - 1),
        ":" + "-" * (col_widths[1] - 2) + ":",
        *[
            ":" + "-" * (col_widths[i + 2] - 2) + ":"
            for i in range(len(headers[2:]))
        ],
    ]

    lines = [
        "| " + " | ".join(header_cols) + " |",
        "| " + " | ".join(sep_cols) + " |",
    ]

    for row in rows:
        row_cols = [
            f"{row[0]:<{col_widths[0]}}",
            f"{row[1]:^{col_widths[1]}}",
            *[
                f"{row[i+2]:^{col_widths[i+2]}}"
                for i in range(len(headers[2:]))
            ],
        ]
        lines.append("| " + " | ".join(row_cols) + " |")

    return "\n".join(lines)


def update_markdown_file(file_path, new_table):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    old_explanation = "Timings represent the added differential validation time (enforced call time minus non-enforced baseline call time) in nanoseconds (ns), averaged over 100 runs. ⚠ = checker did not consistently catch invalid types for this case (generated by utils/minibench.py). For full benchmarks see [utils/benchmark.py](utils/benchmark.py) and [benchmark.md](benchmark.md)."
    new_explanation = "Timings represent the added differential validation time (enforced call time minus non-enforced baseline call time) in microseconds (µs), averaged over 100 runs. ⚠ = checker did not consistently catch invalid types for this case (generated by utils/minibench.py). For full benchmarks see [utils/benchmark.py](utils/benchmark.py) and [benchmark.md](benchmark.md)."
    if old_explanation in content:
        content = content.replace(old_explanation, new_explanation)

    pattern = r"(\|\s*Type\s*\|\s*Size\s*\|.*?\n(?:\|.*?\n)+)"
    if re.search(pattern, content):
        updated_content = re.sub(pattern, new_table + "\n", content, count=1)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        print(f"Updated {file_path}")
    else:
        print(f"Could not find table in {file_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Run quick Glance benchmark measuring added validation differential in microseconds (µs)"
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update table in README.md and type_enforced/__init__.py",
    )
    args = parser.parse_args()

    print("Running Performance at a Glance benchmarks...")
    print(
        "Note: Reported times represent the added differential validation time in microseconds (µs) with baseline execution time subtracted over distinct input pools."
    )
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
