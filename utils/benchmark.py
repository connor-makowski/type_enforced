try:
    import sys, time
    from statistics import mean
    from typing import (
        Callable,
        Dict,
        List,
        NewType,
        Tuple,
        Type,
        TypeVar,
        TypedDict,
        Union,
        get_args,
        get_origin,
    )

    try:
        from typing import LiteralString
    except ImportError:
        LiteralString = str

    try:
        from typing import Self
    except ImportError:
        Self = object

    UserId = NewType("UserId", int)
    T_bound = TypeVar("T_bound", bound=int)

    class UserProfile(TypedDict):
        id: int
        name: str
        active: bool
        score: float
        tag: str

    class BenchmarkClass:
        pass

    class BenchmarkSubclass(BenchmarkClass):
        pass

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

    import type_enforced

    try:
        import typeguard
        from typeguard import typechecked
    except ImportError:
        typeguard = None
        typechecked = None

    # Open the log file, clear it and redirect stdout to it
    log = open("benchmark.md", "w")
    sys.stdout.flush()  # Ensure the log file is cleared before writing
    sys.stdout = log

    POOL_SIZE = 20

    # --- Test Data & Input Pools ---
    def make_test_pools():
        pools = {}
        invalid_cases = {}

        # Scalars
        pools["int"] = [i * 42 for i in range(POOL_SIZE)]
        invalid_cases["int"] = "not an int"

        pools["Union[int,float]"] = [
            float(i) if i % 2 else i for i in range(POOL_SIZE)
        ]
        invalid_cases["Union[int,float]"] = "not a number"

        pools["str"] = [f"hello_{i}" for i in range(POOL_SIZE)]
        invalid_cases["str"] = 123

        pools["NewType (int)"] = [UserId(i + 1) for i in range(POOL_SIZE)]
        invalid_cases["NewType (int)"] = "not an int"

        pools["LiteralString"] = [
            f"SELECT * FROM users WHERE id = {i}" for i in range(POOL_SIZE)
        ]
        invalid_cases["LiteralString"] = 12345

        pools["type[BenchmarkClass]"] = [
            BenchmarkClass for _ in range(POOL_SIZE)
        ]
        invalid_cases["type[BenchmarkClass]"] = BenchmarkSubclass()

        pools["Callable[[int,str],bool]"] = [
            lambda n, s: True for _ in range(POOL_SIZE)
        ]
        invalid_cases["Callable[[int,str],bool]"] = "not a callable"

        pools["TypedDict (5 fields)"] = [
            {
                "id": i,
                "name": f"User_{i}",
                "active": bool(i % 2),
                "score": float(i) * 1.5,
                "tag": "admin" if i % 2 == 0 else "user",
            }
            for i in range(POOL_SIZE)
        ]
        invalid_cases["TypedDict (5 fields)"] = {
            "id": 1,
            "name": "Alice",
            "active": True,
            "score": "not_a_float",
            "tag": "admin",
        }

        pools["class method Self"] = [i for i in range(POOL_SIZE)]
        invalid_cases["class method Self"] = "not an int"

        pools["TypeVar (bound int)"] = [i for i in range(POOL_SIZE)]
        invalid_cases["TypeVar (bound int)"] = "not an int"

        pools["tuple[float,float]"] = [
            (float(i), float(i + 1)) for i in range(POOL_SIZE)
        ]
        invalid_cases["tuple[float,float]"] = (1.5, "bad")

        pools["tuple[int,...] (1000 items)"] = [
            tuple(range(i, i + 1000)) for i in range(POOL_SIZE)
        ]
        invalid_cases["tuple[int,...] (1000 items)"] = (
            tuple(range(999)) + ("not an int",)
        )

        # Dicts
        for prefix in [
            "dict[str,int]",
            "Dict[str,int]",
            "class method dict[str,int]",
        ]:
            pools[f"{prefix} (5 keys)"] = [
                {f"key{j}": j for j in range(5)} for _ in range(POOL_SIZE)
            ]
            invalid_cases[f"{prefix} (5 keys)"] = {
                "k1": 1,
                "k2": "two",
                "k3": 3,
            }

            pools[f"{prefix} (1000 keys)"] = [
                {f"key{j}": j for j in range(1000)} for _ in range(POOL_SIZE)
            ]
            invalid_cases[f"{prefix} (1000 keys)"] = {
                "k1": 1,
                "k2": "two",
                "k3": 3,
            }

            pools[f"{prefix} (10000 keys)"] = [
                {f"key{j}": j for j in range(10000)} for _ in range(POOL_SIZE)
            ]
            invalid_cases[f"{prefix} (10000 keys)"] = {
                "k1": 1,
                "k2": "two",
                "k3": 3,
            }

        # Lists
        for prefix in ["list[int]", "List[int]"]:
            pools[f"{prefix} (5 items)"] = [
                [j for j in range(5)] for _ in range(POOL_SIZE)
            ]
            invalid_cases[f"{prefix} (5 items)"] = [1, "two", 3, 4, 5]

            pools[f"{prefix} (1000 items)"] = [
                [j for j in range(1000)] for _ in range(POOL_SIZE)
            ]
            invalid_cases[f"{prefix} (1000 items)"] = [1, "two", 3, 4, 5] * 200

            pools[f"{prefix} (10000 items)"] = [
                [j for j in range(10000)] for _ in range(POOL_SIZE)
            ]
            invalid_cases[f"{prefix} (10000 items)"] = (
                [1, "two", 3, 4, 5] * 2000
            )

        pools["list[Union[int,float]] (5 items)"] = [
            [float(j) if j % 2 else j for j in range(5)]
            for _ in range(POOL_SIZE)
        ]
        invalid_cases["list[Union[int,float]] (5 items)"] = [1, "two", 3, 4, 5]

        pools["list[Union[int,float]] (1000 items)"] = [
            [float(j) if j % 2 else j for j in range(1000)]
            for _ in range(POOL_SIZE)
        ]
        invalid_cases["list[Union[int,float]] (1000 items)"] = (
            [1, "two", 3, 4, 5] * 200
        )

        pools["list[Union[int,float]] (10000 items)"] = [
            [float(j) if j % 2 else j for j in range(10000)]
            for _ in range(POOL_SIZE)
        ]
        invalid_cases["list[Union[int,float]] (10000 items)"] = (
            [1, "two", 3, 4, 5] * 2000
        )

        pools["list[int] | list[str] (5 items)"] = [
            [j for j in range(5)] for _ in range(POOL_SIZE)
        ]
        invalid_cases["list[int] | list[str] (5 items)"] = [1, "two", 3, 4, 5]

        pools["list[int] | list[str] (1000 items)"] = [
            [j for j in range(1000)] for _ in range(POOL_SIZE)
        ]
        invalid_cases["list[int] | list[str] (1000 items)"] = (
            [1, "two", 3, 4, 5] * 200
        )

        pools["list[int] | list[str] (10000 items)"] = [
            [j for j in range(10000)] for _ in range(POOL_SIZE)
        ]
        invalid_cases["list[int] | list[str] (10000 items)"] = (
            [1, "two", 3, 4, 5] * 2000
        )

        # Nested
        pools["list[dict[str,int]] (5 x 5 items)"] = [
            [{f"key{j}": j for j in range(5)} for _ in range(5)]
            for _ in range(POOL_SIZE)
        ]
        invalid_cases["list[dict[str,int]] (5 x 5 items)"] = [
            {"k1": 1, "k2": "two", "k3": 3}
        ]

        pools["list[dict[str,int]] (100 x 10 items)"] = [
            [{f"key{j}": j for j in range(10)} for _ in range(100)]
            for _ in range(POOL_SIZE)
        ]
        invalid_cases["list[dict[str,int]] (100 x 10 items)"] = [
            {"k1": 1, "k2": "two", "k3": 3}
        ]

        pools["list[dict[str,int]] (100 x 100 items)"] = [
            [{f"key{j}": j for j in range(100)} for _ in range(100)]
            for _ in range(POOL_SIZE)
        ]
        invalid_cases["list[dict[str,int]] (100 x 100 items)"] = [
            {"k1": 1, "k2": "two", "k3": 3}
        ]

        pools["list[list[int]] (100 x 100 items)"] = [
            [[k for k in range(100)] for _ in range(100)]
            for _ in range(POOL_SIZE)
        ]
        invalid_cases["list[list[int]] (100 x 100 items)"] = [[1, "two"]]

        pools["dict[str,list[int]] (100 x 100 items)"] = [
            {f"k{j}": [k for k in range(100)] for j in range(100)}
            for _ in range(POOL_SIZE)
        ]
        invalid_cases["dict[str,list[int]] (100 x 100 items)"] = {
            "k": [1, "two"]
        }

        pools["list[tuple[int,str,float]] (1000 items)"] = [
            [(k, f"str{k}", float(k)) for k in range(1000)]
            for _ in range(POOL_SIZE)
        ]
        invalid_cases["list[tuple[int,str,float]] (1000 items)"] = [
            (1, "s", "bad")
        ]

        # Multi params
        for n in [3, 10, 25, 50, 100, 200, 500]:
            pools[f"int ({n} params)"] = [
                tuple(range(i, i + n)) for i in range(POOL_SIZE)
            ]
            invalid_cases[f"int ({n} params)"] = (
                tuple(range(n - 1)) + ("not an int",)
            )

        pools["int (3 params, *args)"] = [
            tuple(range(i, i + 5)) for i in range(POOL_SIZE)
        ]
        invalid_cases["int (3 params, *args)"] = (1, 2, "not an int")

        pools["int (3 params, **kwargs)"] = [
            (i, i + 1, i + 2) for i in range(POOL_SIZE)
        ]
        invalid_cases["int (3 params, **kwargs)"] = (1, 2, "not an int")

        pools["int (3 params, *args, **kwargs)"] = [
            (i, i + 1, i + 2) for i in range(POOL_SIZE)
        ]
        invalid_cases["int (3 params, *args, **kwargs)"] = (1, 2, "not an int")

        pools["int (10 params, *args)"] = [
            tuple(range(i, i + 15)) for i in range(POOL_SIZE)
        ]
        invalid_cases["int (10 params, *args)"] = (
            tuple(range(9)) + ("not an int",)
        )

        pools["int (10 params, **kwargs)"] = [
            tuple(range(i, i + 10)) for i in range(POOL_SIZE)
        ]
        invalid_cases["int (10 params, **kwargs)"] = (
            tuple(range(9)) + ("not an int",)
        )

        pools["int (10 params, *args, **kwargs)"] = [
            tuple(range(i, i + 10)) for i in range(POOL_SIZE)
        ]
        invalid_cases["int (10 params, *args, **kwargs)"] = (
            tuple(range(9)) + ("not an int",)
        )

        return pools, invalid_cases

    pools, invalid_cases = make_test_pools()

    # --- Typing definitions
    types = {
        "int": int,
        "Union[int,float]": Union[int, float],
        "str": str,
        "NewType (int)": UserId,
        "LiteralString": LiteralString,
        "type[BenchmarkClass]": Type[BenchmarkClass],
        "Callable[[int,str],bool]": Callable[[int, str], bool],
        "TypedDict (5 fields)": UserProfile,
        "class method Self": "method_self",
        "TypeVar (bound int)": T_bound,
        "tuple[float,float]": Tuple[float, float],
        "tuple[int,...] (1000 items)": Tuple[int, ...],
        "dict[str,int] (5 keys)": dict[str, int],
        "dict[str,int] (1000 keys)": dict[str, int],
        "dict[str,int] (10000 keys)": dict[str, int],
        "Dict[str,int] (5 keys)": Dict[str, int],
        "Dict[str,int] (1000 keys)": Dict[str, int],
        "Dict[str,int] (10000 keys)": Dict[str, int],
        "class method dict[str,int] (5 keys)": "method_dict_str_int",
        "class method dict[str,int] (1000 keys)": "method_dict_str_int",
        "class method dict[str,int] (10000 keys)": "method_dict_str_int",
        "list[int] (5 items)": list[int],
        "list[int] (1000 items)": list[int],
        "list[int] (10000 items)": list[int],
        "List[int] (5 items)": List[int],
        "List[int] (1000 items)": List[int],
        "List[int] (10000 items)": List[int],
        "list[Union[int,float]] (5 items)": List[Union[int, float]],
        "list[Union[int,float]] (1000 items)": List[Union[int, float]],
        "list[Union[int,float]] (10000 items)": List[Union[int, float]],
        "list[int] | list[str] (5 items)": Union[List[int], List[str]],
        "list[int] | list[str] (1000 items)": Union[List[int], List[str]],
        "list[int] | list[str] (10000 items)": Union[List[int], List[str]],
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

    # --- Timing helper with distinct input pool iteration ---
    def timeit(func, pool, is_multi=False, target_batch_time=0.003, repeats=5):
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

        # Determine cycles to take ~target_batch_time (capped for responsiveness)
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
        return (sum(best) / len(best)) * 1e6  # microseconds (µs)

    # --- Factory functions
    def base_factory(typ):
        if typ in MULTI_PARAM_FUNCS:
            return MULTI_PARAM_FUNCS[typ]
        if typ == "method_dict_str_int":

            class _PlainCls:
                def method(self, x: Dict[str, int]) -> None:
                    pass

            _inst = _PlainCls()
            return _inst.method
        if typ == "method_self":

            class _PlainSelfCls:
                def method(self, x: int) -> Self:
                    return self

            _inst = _PlainSelfCls()
            return _inst.method

        def f(x: typ) -> None:
            pass

        return f

    def pydantic_factory(typ):
        if typ in MULTI_PARAM_FUNCS:
            return validate_call(MULTI_PARAM_FUNCS[typ])
        if typ == "method_dict_str_int":

            class _PydanticCls:
                @validate_call
                def method(self, x: Dict[str, int]) -> None:
                    pass

            _inst = _PydanticCls()
            return _inst.method
        if typ == "method_self":

            class _PydanticSelfCls:
                @validate_call
                def method(self, x: int) -> Self:
                    return self

            _inst = _PydanticSelfCls()
            return _inst.method

        @validate_call
        def f(x: typ) -> None:
            pass

        return f

    def beartype_factory(typ):
        if typ in MULTI_PARAM_FUNCS:
            return beartype(MULTI_PARAM_FUNCS[typ])
        if typ == "method_dict_str_int":

            class _BeartypeCls:
                @beartype
                def method(self, x: Dict[str, int]) -> None:
                    pass

            _inst = _BeartypeCls()
            return _inst.method
        if typ == "method_self":

            class _BeartypeSelfCls:
                @beartype
                def method(self, x: int) -> Self:
                    return self

            _inst = _BeartypeSelfCls()
            return _inst.method

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

        if typ == "method_dict_str_int":

            def f(x):
                return typeguard.check_type(
                    x,
                    Dict[str, int],
                    collection_check_strategy=typeguard.CollectionCheckStrategy.FIRST_ITEM,
                )

            return f

        if typ == "method_self":

            class _TypeguardSelfCls:
                def method(self, x: int) -> Self:
                    typeguard.check_type(
                        x,
                        int,
                        collection_check_strategy=typeguard.CollectionCheckStrategy.FIRST_ITEM,
                    )
                    return self

            _inst = _TypeguardSelfCls()
            return _inst.method

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

        if typ == "method_dict_str_int":

            def f(x):
                return typeguard.check_type(
                    x,
                    Dict[str, int],
                    collection_check_strategy=typeguard.CollectionCheckStrategy.ALL_ITEMS,
                )

            return f

        if typ == "method_self":

            class _TypeguardFullSelfCls:
                def method(self, x: int) -> Self:
                    typeguard.check_type(
                        x,
                        int,
                        collection_check_strategy=typeguard.CollectionCheckStrategy.ALL_ITEMS,
                    )
                    return self

            _inst = _TypeguardFullSelfCls()
            return _inst.method

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

        if typ == "method_dict_str_int":

            class _MsgspecCls:
                def method(self, x: Dict[str, int]) -> None:
                    msgspec.convert(x, type=Dict[str, int])

            _inst = _MsgspecCls()
            return _inst.method

        if typ == "method_self":

            class _MsgspecSelfCls:
                def method(self, x: int) -> Self:
                    msgspec.convert(x, type=int)
                    return self

            _inst = _MsgspecSelfCls()
            return _inst.method

        def f(x):
            return msgspec.convert(x, type=typ)

        return f

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

        if typ == "method_dict_str_int":

            class _CattrsCls:
                def method(self, x: Dict[str, int]) -> None:
                    cattrs_conv.structure(x, Dict[str, int])

            _inst = _CattrsCls()
            return _inst.method

        if typ == "method_self":

            class _CattrsSelfCls:
                def method(self, x: int) -> Self:
                    cattrs_conv.structure(x, int)
                    return self

            _inst = _CattrsSelfCls()
            return _inst.method

        def f(x):
            return cattrs_conv.structure(x, typ)

        return f

    def type_enforced_factory(typ):
        if typ in MULTI_PARAM_FUNCS:
            return type_enforced.Enforcer()(MULTI_PARAM_FUNCS[typ])
        if typ == "method_dict_str_int":

            @type_enforced.Enforcer
            class _TECls:
                def method(self, x: Dict[str, int]) -> None:
                    pass

            _inst = _TECls()
            return _inst.method

        if typ == "method_self":

            @type_enforced.Enforcer
            class _TESelfCls:
                def method(self, x: int) -> Self:
                    return self

            _inst = _TESelfCls()
            return _inst.method

        @type_enforced.Enforcer()
        def f(x: typ) -> None:
            pass

        return f

    def type_enforced_5pct_factory(typ):
        if typ in MULTI_PARAM_FUNCS:
            return type_enforced.Enforcer(iterable_sample_pct=5)(
                MULTI_PARAM_FUNCS[typ]
            )
        if typ == "method_dict_str_int":

            @type_enforced.Enforcer(iterable_sample_pct=5)
            class _TE5Cls:
                def method(self, x: Dict[str, int]) -> None:
                    pass

            _inst = _TE5Cls()
            return _inst.method

        if typ == "method_self":

            @type_enforced.Enforcer(iterable_sample_pct=5)
            class _TE5SelfCls:
                def method(self, x: int) -> Self:
                    return self

            _inst = _TE5SelfCls()
            return _inst.method

        @type_enforced.Enforcer(iterable_sample_pct=5)
        def f(x: typ) -> None:
            pass

        return f

    def type_enforced_sampled_factory(typ):
        if typ in MULTI_PARAM_FUNCS:
            return type_enforced.Enforcer(iterable_sample_pct="first")(
                MULTI_PARAM_FUNCS[typ]
            )
        if typ == "method_dict_str_int":

            @type_enforced.Enforcer(iterable_sample_pct="first")
            class _TESampleCls:
                def method(self, x: Dict[str, int]) -> None:
                    pass

            _inst = _TESampleCls()
            return _inst.method

        if typ == "method_self":

            @type_enforced.Enforcer(iterable_sample_pct="first")
            class _TESampleSelfCls:
                def method(self, x: int) -> Self:
                    return self

            _inst = _TESampleSelfCls()
            return _inst.method

        @type_enforced.Enforcer(iterable_sample_pct="first")
        def f(x: typ) -> None:
            pass

        return f

    def type_enforced_bookend_plus_factory(typ):
        if typ in MULTI_PARAM_FUNCS:
            return type_enforced.Enforcer(iterable_sample_pct="bookend_plus")(
                MULTI_PARAM_FUNCS[typ]
            )
        if typ == "method_dict_str_int":

            @type_enforced.Enforcer(iterable_sample_pct="bookend_plus")
            class _TEBookendPlusCls:
                def method(self, x: Dict[str, int]) -> None:
                    pass

            _inst = _TEBookendPlusCls()
            return _inst.method

        if typ == "method_self":

            @type_enforced.Enforcer(iterable_sample_pct="bookend_plus")
            class _TEBookendPlusSelfCls:
                def method(self, x: int) -> Self:
                    return self

            _inst = _TEBookendPlusSelfCls()
            return _inst.method

        @type_enforced.Enforcer(iterable_sample_pct="bookend_plus")
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
        "type_enforced (bookend_plus)": type_enforced_bookend_plus_factory,
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
    print(
        "- Every type checker is tested with the exact same data and test cases."
    )
    print(
        "- Measurements cycle through pre-allocated pools of distinct input instances to eliminate warm-cache bias and simulate realistic independent calls."
    )
    print(
        "- The reported time represents the differential added time (overhead) introduced by type validation in microseconds (µs), calculated by subtracting the baseline execution time of the identical non-enforced function call over the same input pool (`enforced_time - non_enforced_time`)."
    )
    print(
        "- Timings with warning symbols (⚠) indicate that the checker did not catch invalid data inside collections (e.g. invalid items placed outside a sampled subset)."
    )

    def run_benchmark_group(checkers_dict):
        results = {}
        for case, pool in pools.items():
            typ = types[case]
            invalid_val = invalid_cases[case]
            is_multi = typ in MULTI_PARAM_FUNCS
            case_data = {}
            base_fn = base_factory(typ)
            base_us = timeit(base_fn, pool, is_multi=is_multi)
            for name, factory in checkers_dict.items():
                try:
                    fn = factory(typ)
                    avg_us = timeit(fn, pool, is_multi=is_multi)
                    diff_us = max(0.0, avg_us - base_us)
                    passed = all(
                        test_validation(
                            fn,
                            pool[i % len(pool)],
                            invalid_val,
                            is_multi=is_multi,
                        )
                        for i in range(15)
                    )
                    cell_text = (
                        f"{diff_us:.3f} µs"
                        if passed
                        else f"{diff_us:.3f} µs ⚠"
                    )
                    case_data[name] = cell_text
                except Exception as e:
                    case_data[name] = "Error"
            results[case] = case_data
        return results

    def print_benchmark_table(checkers_dict, results_dict):
        headers = list(checkers_dict.keys())
        type_col_w = max(len(c.replace("|", "\\|")) for c in pools)
        type_col_w = max(type_col_w, 42)

        col_widths = {h: max(len(h), 16) for h in headers}
        for case in pools:
            for h in headers:
                val = results_dict[case].get(h, "")
                col_widths[h] = max(col_widths[h], len(val))

        header_cols = [f"{h:<{col_widths[h]}}" for h in headers]
        print(f"| {'Type':<{type_col_w}} | " + " | ".join(header_cols) + " |")
        sep_cols = [":" + "-" * (col_widths[h] - 1) for h in headers]
        print(f"|:{'-' * (type_col_w - 1)}| " + " | ".join(sep_cols) + " |")

        for case in pools:
            case_display = case.replace("|", "\\|")
            row_cols = [
                f"{results_dict[case][h]:<{col_widths[h]}}" for h in headers
            ]
            print(
                f"| {case_display:<{type_col_w}} | "
                + " | ".join(row_cols)
                + " |"
            )

    data_full = run_benchmark_group(full_checkers)
    data_sampled = run_benchmark_group(sampled_checkers)

    # --- Section 1: Full Validation
    print("\n## 1. Full Validation (100% / Deep Validation)")
    print(
        "Checkers in this section perform full validation across all elements in collections (lists, dicts, tuples, sets)."
    )
    print(
        "- Every element is guaranteed to be validated against its type annotation."
    )
    print(
        "- All reported times are the net differential validation overhead in microseconds (µs) with baseline execution time subtracted.\n"
    )
    print_benchmark_table(full_checkers, data_full)

    # --- Section 2: Sampled & O(1) Validation
    print("\n## 2. Sampled & O(1) Validation")
    print(
        "Checkers in this section perform constant-time (O(1)) or fixed-percentage sampling of collections."
    )
    print(
        "- All reported times are the net differential validation overhead in microseconds (µs) with baseline execution time subtracted."
    )
    print(
        "- Warning symbols (⚠) indicate that invalid items placed outside the sampled subset went undetected.\n"
    )
    print_benchmark_table(sampled_checkers, data_sampled)

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
