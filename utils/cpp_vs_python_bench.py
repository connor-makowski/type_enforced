import sys
import time
from typing import Dict, List, Set, Tuple, Union

import type_enforced
import type_enforced.enforcer as enforcer
import type_enforced.specialized as specialized

# Check if C++ extension is available
cpp_available = specialized._cpp is not None
orig_cpp = specialized._cpp

POOL_SIZE = 20

# --- Test Data Generation (Distinct Pools) ---
int_pool = [i * 42 for i in range(POOL_SIZE)]
union_pool = [float(i) if i % 2 else i for i in range(POOL_SIZE)]
str_pool = [f"hello_{i}" for i in range(POOL_SIZE)]

list_5_pool = [[j for j in range(5)] for _ in range(POOL_SIZE)]
list_1000_pool = [[j for j in range(1000)] for _ in range(POOL_SIZE)]
list_10000_pool = [[j for j in range(10000)] for _ in range(POOL_SIZE)]
list_union_1000_pool = [
    [float(j) if j % 2 else j for j in range(1000)] for _ in range(POOL_SIZE)
]
list_union_10000_pool = [
    [float(j) if j % 2 else j for j in range(10000)] for _ in range(POOL_SIZE)
]

dict_5_pool = [{f"key{j}": j for j in range(5)} for _ in range(POOL_SIZE)]
dict_1000_pool = [{f"key{j}": j for j in range(1000)} for _ in range(POOL_SIZE)]
dict_10000_pool = [{f"key{j}": j for j in range(10000)} for _ in range(POOL_SIZE)]

set_1000_pool = [set(range(1000)) for _ in range(POOL_SIZE)]
set_10000_pool = [set(range(10000)) for _ in range(POOL_SIZE)]
tuple_1000_pool = [tuple(range(1000)) for _ in range(POOL_SIZE)]
tuple_10000_pool = [tuple(range(10000)) for _ in range(POOL_SIZE)]
tuple_fixed_pool = [(i, f"hello_{i}", float(i)) for i in range(POOL_SIZE)]

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
list_tuple_1000_pool = [
    [(k, f"str{k}", float(k)) for k in range(1000)] for _ in range(POOL_SIZE)
]


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
    ("`int`", "scalar", int, 100, int_pool),
    ("`Union[int, float]`", "scalar", Union[int, float], 100, union_pool),
    ("`str`", "scalar", str, 100, str_pool),
    # 2. Lists
    ("`list[int]`", "5 items", List[int], 100, list_5_pool),
    ("`list[int]`", "1 000 items", List[int], 100, list_1000_pool),
    ("`list[int]`", "10 000 items", List[int], 100, list_10000_pool),
    (
        "`list[Union[int, float]]`",
        "1 000 items",
        List[Union[int, float]],
        100,
        list_union_1000_pool,
    ),
    (
        "`list[Union[int, float]]`",
        "10 000 items",
        List[Union[int, float]],
        100,
        list_union_10000_pool,
    ),
    # 3. Dictionaries
    ("`dict[str, int]`", "5 keys", Dict[str, int], 100, dict_5_pool),
    ("`dict[str, int]`", "1 000 keys", Dict[str, int], 100, dict_1000_pool),
    ("`dict[str, int]`", "10 000 keys", Dict[str, int], 100, dict_10000_pool),
    # 4. Sets & Tuples
    ("`set[int]`", "1 000 items", Set[int], 100, set_1000_pool),
    ("`set[int]`", "10 000 items", Set[int], 100, set_10000_pool),
    (
        "`tuple[int, ...]`",
        "1 000 items",
        Tuple[int, ...],
        100,
        tuple_1000_pool,
    ),
    (
        "`tuple[int, ...]`",
        "10 000 items",
        Tuple[int, ...],
        100,
        tuple_10000_pool,
    ),
    (
        "`tuple[int, str, float]`",
        "fixed (3 items)",
        Tuple[int, str, float],
        100,
        tuple_fixed_pool,
    ),
    # 5. Nested Structures
    (
        "`list[list[int]]`",
        "100 x 100 items",
        List[List[int]],
        100,
        list_list_100x100_pool,
    ),
    (
        "`dict[str, list[int]]`",
        "100 x 100 items",
        Dict[str, List[int]],
        100,
        dict_list_100x100_pool,
    ),
    (
        "`list[dict[str, int]]`",
        "100 x 100 items",
        List[Dict[str, int]],
        100,
        list_dict_100x100_pool,
    ),
    (
        "`list[tuple[int, str, float]]`",
        "1 000 items",
        List[Tuple[int, str, float]],
        100,
        list_tuple_1000_pool,
    ),
    # 6. Sampled Validations
    (
        "`list[int]` (first)",
        "1 000 items (first)",
        List[int],
        "first",
        list_1000_pool,
    ),
    (
        "`list[int]` (last)",
        "10 000 items (last)",
        List[int],
        "last",
        list_10000_pool,
    ),
    (
        "`dict[str, int]` (first)",
        "1 000 keys (first)",
        Dict[str, int],
        "first",
        dict_1000_pool,
    ),
    (
        "`dict[str, int]` (last)",
        "10 000 keys (last)",
        Dict[str, int],
        "last",
        dict_10000_pool,
    ),
    (
        "`list[int]` (5%)",
        "1 000 items (5%)",
        List[int],
        5,
        list_1000_pool,
    ),
    (
        "`dict[str, int]` (5%)",
        "1 000 keys (5%)",
        Dict[str, int],
        5,
        dict_1000_pool,
    ),
    # 7. Bulk Parameters
    (
        "`int` (10 params)",
        "10 params",
        "10_params",
        100,
        [tuple(range(i, i + 10)) for i in range(POOL_SIZE)],
    ),
    (
        "`int` (50 params)",
        "50 params",
        "50_params",
        100,
        [tuple(range(i, i + 50)) for i in range(POOL_SIZE)],
    ),
    (
        "`int` (100 params)",
        "100 params",
        "100_params",
        100,
        [tuple(range(i, i + 100)) for i in range(POOL_SIZE)],
    ),
    (
        "`int` (500 params)",
        "500 params",
        "500_params",
        100,
        [tuple(range(i, i + 500)) for i in range(POOL_SIZE)],
    ),
]


# --- Timing Helper with Distinct Input Pool Iteration ---
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


def make_enforced_fn(typ, sample_pct, pool, is_multi=False, use_cpp=True):
    try:
        if not use_cpp:
            specialized._cpp = None
            enforcer._cpp = None
        else:
            specialized._cpp = orig_cpp
            enforcer._cpp = orig_cpp

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
            fn(*pool[0])
        else:
            fn(pool[0])

        return fn
    finally:
        specialized._cpp = orig_cpp
        enforcer._cpp = orig_cpp


def base_factory(typ):
    if typ in MULTI_PARAM_FUNCS:
        return MULTI_PARAM_FUNCS[typ]

    def f(x: typ) -> None:
        pass

    return f


def run_benchmark():
    if not cpp_available:
        print(
            "ERROR: C++ module is not compiled or available. Run build first."
        )
        sys.exit(1)

    results = []
    for type_label, size_label, typ, sample_pct, pool in BENCH_CASES:
        is_multi = typ in MULTI_PARAM_FUNCS

        base_fn = base_factory(typ)
        base_us = timeit_pool(base_fn, pool, is_multi=is_multi)

        # Build & warm up pure Python enforcer
        py_fn = make_enforced_fn(
            typ, sample_pct, pool, is_multi=is_multi, use_cpp=False
        )
        py_raw_us = timeit_pool(py_fn, pool, is_multi=is_multi)
        py_us = max(0.001, py_raw_us - base_us)

        # Build & warm up C++ enforcer
        cpp_fn = make_enforced_fn(
            typ, sample_pct, pool, is_multi=is_multi, use_cpp=True
        )
        cpp_raw_us = timeit_pool(cpp_fn, pool, is_multi=is_multi)
        cpp_us = max(0.001, cpp_raw_us - base_us)

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

    print("\n# type_enforced: C++ Accelerated vs Pure Python Performance")
    print(
        "Note: Reported times represent added differential validation time in microseconds (µs) with baseline execution time subtracted over distinct input pools.\n"
    )
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
