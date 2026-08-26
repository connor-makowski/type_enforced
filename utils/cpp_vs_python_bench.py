import sys
import time
from typing import Dict, List, Set, Tuple, Union

import type_enforced
import type_enforced.specialized as specialized

# Check if C++ extension is available
cpp_available = specialized._cpp is not None
orig_cpp = specialized._cpp

# --- Test Data Generation ---
five_item_list = [1, 2.0, 3, 4.0, 5]
list_1000 = list(range(1000))
list_10000 = list(range(10000))
list_union_1000 = [float(i) if i % 2 else i for i in range(1000)]
list_union_10000 = [
    float(i) if i % 2 else i for i in range(10000)
]

dict_5 = {f"key{i}": i for i in range(5)}
dict_1000 = {f"key{i}": i for i in range(1000)}
dict_10000 = {f"key{i}": i for i in range(10000)}

set_1000 = set(range(1000))
set_10000 = set(range(10000))
tuple_1000 = tuple(range(1000))
tuple_10000 = tuple(range(10000))
tuple_fixed = (42, "hello", 3.14)

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


MULTI_PARAM_FUNCS = {
    "10_params": _make_multi_param_fn(10),
    "50_params": _make_multi_param_fn(50),
    "100_params": _make_multi_param_fn(100),
    "500_params": _make_multi_param_fn(500),
}

# --- Benchmark Cases ---
BENCH_CASES = [
    # 1. Scalars
    ("`int`", "scalar", int, 100, 42),
    ("`Union[int, float]`", "scalar", Union[int, float], 100, 3.14),
    ("`str`", "scalar", str, 100, "hello world"),
    # 2. Lists
    ("`list[int]`", "5 items", List[int], 100, [1, 2, 3, 4, 5]),
    ("`list[int]`", "1 000 items", List[int], 100, list_1000),
    ("`list[int]`", "10 000 items", List[int], 100, list_10000),
    (
        "`list[Union[int, float]]`",
        "1 000 items",
        List[Union[int, float]],
        100,
        list_union_1000,
    ),
    (
        "`list[Union[int, float]]`",
        "10 000 items",
        List[Union[int, float]],
        100,
        list_union_10000,
    ),
    # 3. Dictionaries
    ("`dict[str, int]`", "5 keys", Dict[str, int], 100, dict_5),
    ("`dict[str, int]`", "1 000 keys", Dict[str, int], 100, dict_1000),
    ("`dict[str, int]`", "10 000 keys", Dict[str, int], 100, dict_10000),
    # 4. Sets & Tuples
    ("`set[int]`", "1 000 items", Set[int], 100, set_1000),
    ("`set[int]`", "10 000 items", Set[int], 100, set_10000),
    (
        "`tuple[int, ...]`",
        "1 000 items",
        Tuple[int, ...],
        100,
        tuple_1000,
    ),
    (
        "`tuple[int, ...]`",
        "10 000 items",
        Tuple[int, ...],
        100,
        tuple_10000,
    ),
    (
        "`tuple[int, str, float]`",
        "fixed (3 items)",
        Tuple[int, str, float],
        100,
        tuple_fixed,
    ),
    # 5. Nested Structures
    (
        "`list[list[int]]`",
        "100 x 100 items",
        List[List[int]],
        100,
        list_list_100x100,
    ),
    (
        "`dict[str, list[int]]`",
        "100 x 100 items",
        Dict[str, List[int]],
        100,
        dict_list_100x100,
    ),
    (
        "`list[dict[str, int]]`",
        "100 x 100 items",
        List[Dict[str, int]],
        100,
        list_dict_100x100,
    ),
    (
        "`list[tuple[int, str, float]]`",
        "1 000 items",
        List[Tuple[int, str, float]],
        100,
        list_tuple_1000,
    ),
    # 6. Sampled Validations
    (
        "`list[int]` (first)",
        "1 000 items (first)",
        List[int],
        "first",
        list_1000,
    ),
    (
        "`list[int]` (last)",
        "10 000 items (last)",
        List[int],
        "last",
        list_10000,
    ),
    (
        "`dict[str, int]` (first)",
        "1 000 keys (first)",
        Dict[str, int],
        "first",
        dict_1000,
    ),
    (
        "`dict[str, int]` (last)",
        "10 000 keys (last)",
        Dict[str, int],
        "last",
        dict_10000,
    ),
    (
        "`list[int]` (5%)",
        "1 000 items (5%)",
        List[int],
        5,
        list_1000,
    ),
    (
        "`dict[str, int]` (5%)",
        "1 000 keys (5%)",
        Dict[str, int],
        5,
        dict_1000,
    ),
    # 7. Bulk Parameters
    (
        "`int` (10 params)",
        "10 params",
        "10_params",
        100,
        tuple(range(10)),
    ),
    (
        "`int` (50 params)",
        "50 params",
        "50_params",
        100,
        tuple(range(50)),
    ),
    (
        "`int` (100 params)",
        "100 params",
        "100_params",
        100,
        tuple(range(100)),
    ),
    (
        "`int` (500 params)",
        "500 params",
        "500_params",
        100,
        tuple(range(500)),
    ),
]


# --- Timing Helper ---
def timeit_adaptive(
    func, arg, is_multi=False, min_runs=5, max_runs=100, max_sec=0.05
):
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


def make_enforced_fn(typ, sample_pct, data, is_multi=False, use_cpp=True):
    try:
        if not use_cpp:
            specialized._cpp = None
        else:
            specialized._cpp = orig_cpp

        if typ in MULTI_PARAM_FUNCS:
            fn = type_enforced.Enforcer(
                iterable_sample_pct=sample_pct
            )(MULTI_PARAM_FUNCS[typ])
        else:

            @type_enforced.Enforcer(iterable_sample_pct=sample_pct)
            def fn(x: typ) -> None:
                pass

        # Trigger AST specialization compilation under the selected backend
        if is_multi:
            fn(*data)
        else:
            fn(data)

        return fn
    finally:
        specialized._cpp = orig_cpp


def run_benchmark():
    if not cpp_available:
        print(
            "ERROR: C++ module is not compiled or available. Run build first."
        )
        sys.exit(1)

    results = []
    for type_label, size_label, typ, sample_pct, data in BENCH_CASES:
        is_multi = typ in MULTI_PARAM_FUNCS

        # Build & warm up pure Python enforcer
        py_fn = make_enforced_fn(
            typ, sample_pct, data, is_multi=is_multi, use_cpp=False
        )
        py_us = timeit_adaptive(py_fn, data, is_multi=is_multi)

        # Build & warm up C++ enforcer
        cpp_fn = make_enforced_fn(
            typ, sample_pct, data, is_multi=is_multi, use_cpp=True
        )
        cpp_us = timeit_adaptive(cpp_fn, data, is_multi=is_multi)

        speedup = py_us / cpp_us if cpp_us > 0 else 1.0
        results.append(
            (type_label, size_label, py_us, cpp_us, speedup)
        )

    return results


def print_table(results):
    headers = [
        "Type",
        "Size / Configuration",
        "Pure Python",
        "C++ Accelerated",
        "Speedup",
    ]
    col_w = [30, 24, 14, 16, 10]

    header_row = (
        f"| {headers[0]:<{col_w[0]}} | {headers[1]:<{col_w[1]}} | "
        f"{headers[2]:>{col_w[2]}} | {headers[3]:>{col_w[3]}} | {headers[4]:>{col_w[4]}} |"
    )
    sep_row = (
        f"|:{'-' * (col_w[0] - 1)} |:{'-' * (col_w[1] - 1)} |"
        f"{'-' * (col_w[2] + 1)}:|{'-' * (col_w[3] + 1)}:|{'-' * (col_w[4] + 1)}:|"
    )

    print("\n# type_enforced: C++ Accelerated vs Pure Python Performance\n")
    print(header_row)
    print(sep_row)

    for type_label, size_label, py_us, cpp_us, speedup in results:
        speedup_str = f"{speedup:.2f}x"
        if speedup >= 1.3:
            speedup_str = f"**{speedup:.2f}x**"
        print(
            f"| {type_label:<{col_w[0]}} | {size_label:<{col_w[1]}} | "
            f"{py_us:>11.2f} µs | {cpp_us:>13.2f} µs | {speedup_str:>{col_w[4]}} |"
        )
    print()


def print_summary_stats(results):
    total_py = sum(r[2] for r in results)
    total_cpp = sum(r[3] for r in results)
    overall_speedup = total_py / total_cpp if total_cpp > 0 else 1.0

    large_collections = [
        r for r in results if "10 000" in r[1] or "100 x 100" in r[1]
    ]
    nested_collections = [r for r in results if "100 x 100" in r[1]]
    scalar_cases = [
        r
        for r in results
        if "scalar" in r[1] or "first" in r[1] or "last" in r[1]
    ]

    max_speedup_case = max(results, key=lambda r: r[4])

    large_speedup = (
        sum(r[2] for r in large_collections)
        / sum(r[3] for r in large_collections)
        if large_collections
        else 1.0
    )
    nested_speedup = (
        sum(r[2] for r in nested_collections)
        / sum(r[3] for r in nested_collections)
        if nested_collections
        else 1.0
    )

    if scalar_cases:
        scalar_py = sum(r[2] for r in scalar_cases)
        scalar_cpp = sum(r[3] for r in scalar_cases)
        scalar_speedup = scalar_py / scalar_cpp if scalar_cpp > 0 else 1.0
        avg_py_ns = (scalar_py / len(scalar_cases)) * 1000
        avg_cpp_ns = (scalar_cpp / len(scalar_cases)) * 1000
        diff_ns = avg_py_ns - avg_cpp_ns
        scalar_summary_str = f"{scalar_speedup:.2f}x average (avg: {avg_py_ns:.1f} ns py vs {avg_cpp_ns:.1f} ns cpp, diff: {diff_ns:+.1f} ns)"
    else:
        scalar_summary_str = "1.00x"

    print("### Summary Performance Statistics\n")
    print(
        f"- **Overall Suite Aggregate Speedup:** {overall_speedup:.2f}x ({total_py:.1f} µs total Pure Python vs {total_cpp:.1f} µs total C++)"
    )
    print(
        f"- **Maximum Speedup:** {max_speedup_case[4]:.2f}x ({max_speedup_case[0]} with {max_speedup_case[1]}: {max_speedup_case[2]:.2f} µs py vs {max_speedup_case[3]:.2f} µs cpp)"
    )
    print(
        f"- **Large Collections (10k items / 100x100 nested):** {large_speedup:.2f}x aggregate speedup"
    )
    print(
        f"- **Nested Structures (100x100 matrix/nested):** {nested_speedup:.2f}x aggregate speedup"
    )
    print(
        f"- **Scalars & O(1) Sampled Checks:** {scalar_summary_str}"
    )
    print()


def main():
    print("Benchmarking C++ Accelerated vs Pure Python type_enforced...")
    results = run_benchmark()
    print_table(results)
    print_summary_stats(results)


if __name__ == "__main__":
    main()
