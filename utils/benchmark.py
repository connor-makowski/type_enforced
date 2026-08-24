try:
    import time, sys
    from typing import Union, Dict, List
    from statistics import mean

    from beartype import beartype
    from typeguard import typechecked
    import type_enforced

    from pydantic import BaseModel, validate_call

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
        "int (10 params)": (
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
        "int (10 params)": "10_params",
        "int (25 params)": "25_params",
        "int (50 params)": "50_params",
        "int (100 params)": "100_params",
    }

    # --- Multi-parameter benchmark functions
    def f_10(
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
    ) -> None:
        pass

    def f_25(
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
        a10: int,
        a11: int,
        a12: int,
        a13: int,
        a14: int,
        a15: int,
        a16: int,
        a17: int,
        a18: int,
        a19: int,
        a20: int,
        a21: int,
        a22: int,
        a23: int,
        a24: int,
    ) -> None:
        pass

    def f_50(
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
        a10: int,
        a11: int,
        a12: int,
        a13: int,
        a14: int,
        a15: int,
        a16: int,
        a17: int,
        a18: int,
        a19: int,
        a20: int,
        a21: int,
        a22: int,
        a23: int,
        a24: int,
        a25: int,
        a26: int,
        a27: int,
        a28: int,
        a29: int,
        a30: int,
        a31: int,
        a32: int,
        a33: int,
        a34: int,
        a35: int,
        a36: int,
        a37: int,
        a38: int,
        a39: int,
        a40: int,
        a41: int,
        a42: int,
        a43: int,
        a44: int,
        a45: int,
        a46: int,
        a47: int,
        a48: int,
        a49: int,
    ) -> None:
        pass

    def f_100(
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
        a10: int,
        a11: int,
        a12: int,
        a13: int,
        a14: int,
        a15: int,
        a16: int,
        a17: int,
        a18: int,
        a19: int,
        a20: int,
        a21: int,
        a22: int,
        a23: int,
        a24: int,
        a25: int,
        a26: int,
        a27: int,
        a28: int,
        a29: int,
        a30: int,
        a31: int,
        a32: int,
        a33: int,
        a34: int,
        a35: int,
        a36: int,
        a37: int,
        a38: int,
        a39: int,
        a40: int,
        a41: int,
        a42: int,
        a43: int,
        a44: int,
        a45: int,
        a46: int,
        a47: int,
        a48: int,
        a49: int,
        a50: int,
        a51: int,
        a52: int,
        a53: int,
        a54: int,
        a55: int,
        a56: int,
        a57: int,
        a58: int,
        a59: int,
        a60: int,
        a61: int,
        a62: int,
        a63: int,
        a64: int,
        a65: int,
        a66: int,
        a67: int,
        a68: int,
        a69: int,
        a70: int,
        a71: int,
        a72: int,
        a73: int,
        a74: int,
        a75: int,
        a76: int,
        a77: int,
        a78: int,
        a79: int,
        a80: int,
        a81: int,
        a82: int,
        a83: int,
        a84: int,
        a85: int,
        a86: int,
        a87: int,
        a88: int,
        a89: int,
        a90: int,
        a91: int,
        a92: int,
        a93: int,
        a94: int,
        a95: int,
        a96: int,
        a97: int,
        a98: int,
        a99: int,
    ) -> None:
        pass

    MULTI_PARAM_FUNCS = {
        "10_params": f_10,
        "25_params": f_25,
        "50_params": f_50,
        "100_params": f_100,
    }

    # --- Timing helper
    def timeit(func, arg, is_multi=False):
        durations = []
        for _ in range(REPEATS + 1):
            start = time.perf_counter()
            if is_multi:
                func(*arg)
            else:
                func(arg)
            durations.append(time.perf_counter() - start)
        return mean(durations[1:]) * 1e6  # microseconds (ignore first run)

    # --- Factory functions
    def pydantic_factory(typ):
        if typ in MULTI_PARAM_FUNCS:
            return validate_call(MULTI_PARAM_FUNCS[typ])

        class PModel(BaseModel):
            x: typ

        @validate_call
        def f(x: typ) -> None:
            PModel(x=x)

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
            return typechecked(MULTI_PARAM_FUNCS[typ])

        @typechecked
        def f(x: typ) -> None:
            pass

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

    # --- Checkers and factories
    checkers = {
        "type_enforced (100%)": type_enforced_factory,
        "type_enforced (5%)": type_enforced_5pct_factory,
        "type_enforced (1 sample)": type_enforced_sampled_factory,
        "Pydantic": pydantic_factory,
        "Beartype": beartype_factory,
        "Typeguard": typeguard_factory,
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
        "This file contains the results of the benchmark tests for various type checkers.\n"
    )
    print("Generated by /utils/benchmark.py\n")
    print("Each checker is tested with different data types and structures")
    print("- Every checker gets the same data and test cases")
    print(
        f"- The reported time represents the average duration of a single validation (one function call), measured over {REPEATS} runs (ignoring the initial warmup run)."
    )
    print("\n## Results Summary")
    print(
        "The following table summarizes the average time taken per single validation by each type checker for different data types and structures.\n"
    )
    print(
        "- Note: Timings with warning symbols(⚠) indicate that the checker did not consistently catch invalid types for the given type or structure."
    )
    print(
        "    - This could be due to the type checker not raising an error when it should or raising an error when it shouldn't."
    )
    print(
        f"    - The validation is run {REPEATS} times to ensure type checking results are consistent."
    )
    print(
        "\n| Type                        | type_enforced (100%) | type_enforced (5%) | type_enforced (1 sample) | Pydantic (100%) | Beartype (1 sample) | Typeguard (1 sample) |"
    )
    print(
        "|:-----------------------------|:----------------------|:--------------------|:--------------------------|:-----------------|:---------------------|:----------------------|"
    )

    def green_text(text):
        return f"<span style='color: green;'>{text}</span>"

    def red_text(text):
        return f"<span style='color: red;'>{text} ⚠</span>"

    data = {}

    for case, (valid_val, invalid_val) in test_cases.items():
        typ = types[case]
        is_multi = typ in MULTI_PARAM_FUNCS
        case_data = {}
        for name, factory in checkers.items():
            try:
                fn = factory(typ)
                avg_us = timeit(fn, valid_val, is_multi=is_multi)
                passed = all(
                    [
                        test_validation(
                            fn, valid_val, invalid_val, is_multi=is_multi
                        )
                        for _ in range(REPEATS)
                    ]
                )
                avg_us_colored = (
                    green_text(f"{avg_us:.2f} µs")
                    if passed
                    else red_text(f"{avg_us:.2f} µs")
                )
                case_data[name] = avg_us_colored
            except Exception as e:
                case_data[name] = red_text(f"Error")
        data[case] = case_data
    for case, results in data.items():
        print(f"| {case:<30} | " + " | ".join(results.values()) + " |")
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
