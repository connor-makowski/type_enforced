try:
    import sys, time
    from statistics import mean
    from typing import Dict, List, Tuple, Union, get_args, get_origin

    from beartype import beartype
    import cattrs
    import msgspec
    from pydantic import validate_call
    import type_enforced
    import typeguard
    from typeguard import typechecked

    # Open the log file, clear it and redirect stdout to it
    log = open("benchmark.md", "w")
    sys.stdout.flush()  # Ensure the log file is cleared before writing
    sys.stdout = log

    REPEATS = 100

    # --- Test data
    five_key_dict = {f"key{i}": i for i in range(5)}
    big_key_dict = {f"key{i}": i for i in range(1000)}
    ten_thousand_key_dict = {f"key{i}": i for i in range(10000)}

    five_item_list = [1, 2.0, 3, 4.0, 5]
    big_item_list = [float(i) if i % 2 else i for i in range(1000)]
    ten_thousand_item_list = [float(i) if i % 2 else i for i in range(10000)]

    list_list_100x100 = [[j for j in range(100)] for _ in range(100)]
    dict_list_100x100 = {f"k{i}": [j for j in range(100)] for i in range(100)}
    list_tuple_1000 = [(i, f"str{i}", float(i)) for i in range(1000)]

    # --- Benchmark and Validation test cases
    test_cases = {
        "int": (42, "not an int"),
        "Union[int,float]": (3.14, "not a number"),
        "str": ("hello", 123),
        "dict[str,int] (5 keys)": (
            five_key_dict,
            {"k1": 1, "k2": "two", "k3": 3},
        ),
        "dict[str,int] (1000 keys)": (
            big_key_dict,
            {"k1": 1, "k2": "two", "k3": 3},
        ),
        "dict[str,int] (10000 keys)": (
            ten_thousand_key_dict,
            {"k1": 1, "k2": "two", "k3": 3},
        ),
        "list[int] (5 items)": (
            [1, 2, 3, 4, 5],
            [1, "two", 3, 4, 5],
        ),
        "list[int] (1000 items)": (
            list(range(1000)),
            [1, "two", 3, 4, 5] * 200,
        ),
        "list[int] (10000 items)": (
            list(range(10000)),
            [1, "two", 3, 4, 5] * 2000,
        ),
        "list[Union[int,float]] (5 items)": (
            five_item_list,
            [1, "two", 3, 4, 5],
        ),
        "list[Union[int,float]] (1000 items)": (
            big_item_list,
            [1, "two", 3, 4, 5] * 200,
        ),
        "list[Union[int,float]] (10000 items)": (
            ten_thousand_item_list,
            [1, "two", 3, 4, 5] * 2000,
        ),
        "list[dict[str,int]] (5 x 5 items)": (
            [{f"key{i}": i for i in range(5)} for _ in range(5)],
            [{"k1": 1, "k2": "two", "k3": 3}],
        ),
        "list[dict[str,int]] (100 x 10 items)": (
            [{f"key{i}": i for i in range(10)} for _ in range(100)],
            [{"k1": 1, "k2": "two", "k3": 3}],
        ),
        "list[dict[str,int]] (100 x 100 items)": (
            [{f"key{i}": i for i in range(100)} for _ in range(100)],
            [{"k1": 1, "k2": "two", "k3": 3}],
        ),
        "list[list[int]] (100 x 100 items)": (
            list_list_100x100,
            [[1, "two"]],
        ),
        "dict[str,list[int]] (100 x 100 items)": (
            dict_list_100x100,
            {"k": [1, "two"]},
        ),
        "list[tuple[int,str,float]] (1000 items)": (
            list_tuple_1000,
            [(1, "s", "bad")],
        ),
        "int (3 params)": (
            (1, 2, 3),
            (1, 2, "not an int"),
        ),
        "int (3 params, *args)": (
            (1, 2, 3),
            (1, 2, "not an int"),
        ),
        "int (3 params, **kwargs)": (
            (1, 2, 3),
            (1, 2, "not an int"),
        ),
        "int (3 params, *args, **kwargs)": (
            (1, 2, 3),
            (1, 2, "not an int"),
        ),
        "int (10 params)": (
            tuple(range(10)),
            tuple(range(9)) + ("not an int",),
        ),
        "int (10 params, *args)": (
            tuple(range(10)),
            tuple(range(9)) + ("not an int",),
        ),
        "int (10 params, **kwargs)": (
            tuple(range(10)),
            tuple(range(9)) + ("not an int",),
        ),
        "int (10 params, *args, **kwargs)": (
            tuple(range(10)),
            tuple(range(9)) + ("not an int",),
        ),
        "int (25 params)": (
            tuple(range(25)),
            tuple(range(24)) + ("not an int",),
        ),
        "int (50 params)": (
            tuple(range(50)),
            tuple(range(49)) + ("not an int",),
        ),
        "int (100 params)": (
            tuple(range(100)),
            tuple(range(99)) + ("not an int",),
        ),
        "int (200 params)": (
            tuple(range(200)),
            tuple(range(199)) + ("not an int",),
        ),
        "int (500 params)": (
            tuple(range(500)),
            tuple(range(499)) + ("not an int",),
        ),
    }

    # --- Typing definitions
    types = {
        "int": int,
        "Union[int,float]": Union[int, float],
        "str": str,
        "dict[str,int] (5 keys)": Dict[str, int],
        "dict[str,int] (1000 keys)": Dict[str, int],
        "dict[str,int] (10000 keys)": Dict[str, int],
        "list[int] (5 items)": List[int],
        "list[int] (1000 items)": List[int],
        "list[int] (10000 items)": List[int],
        "list[Union[int,float]] (5 items)": List[Union[int, float]],
        "list[Union[int,float]] (1000 items)": List[Union[int, float]],
        "list[Union[int,float]] (10000 items)": List[Union[int, float]],
        "list[dict[str,int]] (5 x 5 items)": List[Dict[str, int]],
        "list[dict[str,int]] (100 x 10 items)": List[Dict[str, int]],
        "list[dict[str,int]] (100 x 100 items)": List[Dict[str, int]],
        "list[list[int]] (100 x 100 items)": List[List[int]],
        "dict[str,list[int]] (100 x 100 items)": Dict[str, List[int]],
        "list[tuple[int,str,float]] (1000 items)": List[
            Tuple[int, str, float]
        ],
        "int (3 params)": "3_params",
        "int (3 params, *args)": "3_params_args",
        "int (3 params, **kwargs)": "3_params_kwargs",
        "int (3 params, *args, **kwargs)": "3_params_args_kwargs",
        "int (10 params)": "10_params",
        "int (10 params, *args)": "10_params_args",
        "int (10 params, **kwargs)": "10_params_kwargs",
        "int (10 params, *args, **kwargs)": "10_params_args_kwargs",
        "int (25 params)": "25_params",
        "int (50 params)": "50_params",
        "int (100 params)": "100_params",
        "int (200 params)": "200_params",
        "int (500 params)": "500_params",
    }

    # --- Multi-parameter benchmark functions

    def f_3_args(a0: int, a1: int, a2: int, *args) -> None:
        pass

    def f_3_kwargs(a0: int, a1: int, a2: int, **kwargs) -> None:
        pass

    def f_3_args_kwargs(a0: int, a1: int, a2: int, *args, **kwargs) -> None:
        pass

    def f_10_args(
        a0: int,
        a1: int,
        a2: int,
        a3: int,
        a4: int,
        a5: int,
        a6: int,
        a7: int,
        a8: int,
        a9: int,
        *args,
    ) -> None:
        pass

    def f_10_kwargs(
        a0: int,
        a1: int,
        a2: int,
        a3: int,
        a4: int,
        a5: int,
        a6: int,
        a7: int,
        a8: int,
        a9: int,
        **kwargs,
    ) -> None:
        pass

    def f_10_args_kwargs(
        a0: int,
        a1: int,
        a2: int,
        a3: int,
        a4: int,
        a5: int,
        a6: int,
        a7: int,
        a8: int,
        a9: int,
        *args,
        **kwargs,
    ) -> None:
        pass

    def _make_multi_param_fn(n):
        params = ", ".join(f"a{i}: int" for i in range(n))
        code = f"def f_{n}({params}) -> None: pass"
        ns = {}
        exec(code, globals(), ns)
        return ns[f"f_{n}"]

    f_3 = _make_multi_param_fn(3)
    f_10 = _make_multi_param_fn(10)
    f_25 = _make_multi_param_fn(25)
    f_50 = _make_multi_param_fn(50)    
    f_100 = _make_multi_param_fn(100)
    f_200 = _make_multi_param_fn(200)
    f_500 = _make_multi_param_fn(500)

    MULTI_PARAM_FUNCS = {
        "3_params": f_3,
        "3_params_args": f_3_args,
        "3_params_kwargs": f_3_kwargs,
        "3_params_args_kwargs": f_3_args_kwargs,
        "10_params": f_10,
        "10_params_args": f_10_args,
        "10_params_kwargs": f_10_kwargs,
        "10_params_args_kwargs": f_10_args_kwargs,
        "25_params": f_25,
        "50_params": f_50,
        "100_params": f_100,
        "200_params": f_200,
        "500_params": f_500,
    }

    MIN_REPEATS = 3
    MAX_REPEATS = 100
    MAX_TIME_PER_CASE = 0.05  # 50 ms max per test case cell

    # --- Timing helper
    def timeit(func, arg, is_multi=False):
        # Warmup run (ignored)
        if is_multi:
            func(*arg)
        else:
            func(arg)

        durations = []
        start_total = time.perf_counter()
        for _ in range(MAX_REPEATS):
            t0 = time.perf_counter()
            if is_multi:
                func(*arg)
            else:
                func(arg)
            durations.append(time.perf_counter() - t0)

            # Adaptive termination if minimum runs met and budget exceeded
            if (
                len(durations) >= MIN_REPEATS
                and (time.perf_counter() - start_total) >= MAX_TIME_PER_CASE
            ):
                break

        return (sum(durations) / len(durations)) * 1e6  # microseconds

    # --- Factory functions
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

    def typeguard_factory(typ):
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

    cattrs_conv = cattrs.Converter()

    def structure_union(val, typ):
        args = get_args(typ)
        for arg in args:
            try:
                return cattrs_conv.structure(val, arg)
            except Exception:
                continue
        raise TypeError(f"Cannot structure {val} into {typ}")

    cattrs_conv.register_structure_hook_func(
        lambda t: get_origin(t) is Union, structure_union
    )

    def cattrs_factory(typ):
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

    def type_enforced_factory(typ):
        if typ in MULTI_PARAM_FUNCS:
            return type_enforced.Enforcer()(MULTI_PARAM_FUNCS[typ])

        @type_enforced.Enforcer()
        def f(x: typ) -> None:
            pass

        return f

    def type_enforced_5pct_factory(typ):
        if typ in MULTI_PARAM_FUNCS:
            return type_enforced.Enforcer(iterable_sample_pct=5)(
                MULTI_PARAM_FUNCS[typ]
            )

        @type_enforced.Enforcer(iterable_sample_pct=5)
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

    # --- Checkers groups
    full_checkers = {
        "type_enforced": type_enforced_factory,
        "Pydantic": pydantic_factory,
        "msgspec": msgspec_factory,
        "cattrs": cattrs_factory,
        "Typeguard": typeguard_full_factory,
    }

    sampled_checkers = {
        "type_enforced (1 sample)": type_enforced_sampled_factory,
        "type_enforced (5%)": type_enforced_5pct_factory,
        "Beartype (1 sample)": beartype_factory,
        "Typeguard (1 sample)": typeguard_factory,
    }

    # --- Validation helper
    def test_validation(func, valid_value, invalid_value, is_multi=False):
        try:
            if is_multi:
                func(*valid_value)
            else:
                func(valid_value)
            valid_passed = True
        except Exception:
            valid_passed = False

        try:
            if is_multi:
                func(*invalid_value)
            else:
                func(invalid_value)
            invalid_passed = False
        except Exception:
            invalid_passed = True

        return valid_passed and invalid_passed

    # --- Final output
    print(f"# Benchmark Results (python {sys.version.split(' ')[0]})\n")
    print(
        "This file contains the benchmark results across various Python runtime type validation packages.\n"
    )
    print("Generated by `/utils/benchmark.py`\n")
    print("### Benchmark Methodology")
    print("- Every type checker is tested with the exact same data and test cases.")
    print(
        "- The reported time represents the average duration of a single validation (one function call), measured with adaptive repeats (up to 100 runs, capped at 50ms per test case, ignoring the initial warmup run)."
    )
    print(
        "- Timings with warning symbols (⚠) indicate that the checker did not catch invalid data inside collections (e.g. invalid items placed outside a sampled subset)."
    )

    def green_text(text):
        return f"<span style='color: green;'>{text}</span>"

    def red_text(text):
        return f"<span style='color: red;'>{text} ⚠</span>"

    def run_benchmark_group(checkers_dict):
        results = {}
        for case, (valid_val, invalid_val) in test_cases.items():
            typ = types[case]
            is_multi = typ in MULTI_PARAM_FUNCS
            case_data = {}
            for name, factory in checkers_dict.items():
                try:
                    fn = factory(typ)
                    avg_us = timeit(fn, valid_val, is_multi=is_multi)
                    passed = all(
                        test_validation(
                            fn, valid_val, invalid_val, is_multi=is_multi
                        )
                        for _ in range(15)
                    )
                    avg_us_colored = (
                        green_text(f"{avg_us:.2f} µs")
                        if passed
                        else red_text(f"{avg_us:.2f} µs")
                    )
                    case_data[name] = avg_us_colored
                except Exception as e:
                    case_data[name] = red_text("Error")
            results[case] = case_data
        return results

    data_full = run_benchmark_group(full_checkers)
    data_sampled = run_benchmark_group(sampled_checkers)

    # --- Section 1: Full Validation
    print("\n## 1. Full Validation (100% / Deep Validation)")
    print(
        "Checkers in this section perform full validation across all elements in collections (lists, dicts, tuples, sets)."
    )
    print(
        "- Every element is guaranteed to be validated against its type annotation.\n"
    )

    full_headers = list(full_checkers.keys())
    print("| Type | " + " | ".join(full_headers) + " |")
    print("|:---| " + " | ".join([":---"] * len(full_headers)) + " |")
    for case in test_cases:
        row = [data_full[case][name] for name in full_headers]
        print(f"| {case:<30} | " + " | ".join(row) + " |")

    # --- Section 2: Sampled & O(1) Validation
    print("\n## 2. Sampled & O(1) Validation")
    print(
        "Checkers in this section perform constant-time (O(1)) or fixed-percentage sampling of collections."
    )
    print(
        "- Warning symbols (⚠) indicate that invalid items placed outside the sampled subset went undetected.\n"
    )

    sampled_headers = list(sampled_checkers.keys())
    print("| Type | " + " | ".join(sampled_headers) + " |")
    print("|:---| " + " | ".join([":---"] * len(sampled_headers)) + " |")
    for case in test_cases:
        row = [data_sampled[case][name] for name in sampled_headers]
        print(f"| {case:<30} | " + " | ".join(row) + " |")

    sys.stdout = sys.__stdout__  # Reset stdout to original
    log.close()  # Close the log file
    print("benchmark.py passed")
except Exception as e:
    sys.stdout = sys.__stdout__
    try:
        log.close()
    except:
        pass
    print(f"benchmark.py failed: {e}")
