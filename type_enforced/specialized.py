import ast
import random
import types
from itertools import islice


def _random_dict_key(d):
    l = len(d)
    if l == 1:
        return next(iter(d))
    return next(islice(d, random.randrange(l), None))


def _random_set_item(s):
    l = len(s)
    if l == 1:
        return next(iter(s))
    return next(islice(s, random.randrange(l), None))


def _log_count(length):
    if length <= 0:
        return 0
    return max(1, (length - 1).bit_length())


def create_specialized_class(base_cls, fn_qualname, call_method):
    """
    Dynamically creates a subclass of base_cls with __slots__ = () and the given __call__ method.
    """
    clean_name = fn_qualname.replace(".", "_").replace("<", "").replace(">", "")
    return type(
        f"Specialized_{clean_name}",
        (base_cls,),
        {
            "__slots__": (),
            "__call__": call_method,
        },
    )


def is_simple_type(exp):
    """
    Returns True if exp is a scalar or union of scalar types (e.g. {int: None, str: None}).
    """
    return (
        isinstance(exp, dict)
        and "__extra__" not in exp
        and all(v is None for v in exp.values())
        and all(isinstance(k, type) for k in exp.keys())
    )


def can_specialize_type(exp):
    """
    Recursively determines if an expected type expression can be specialized via AST.
    Supports scalars, unions, lists, dicts, sets, and tuples to arbitrary nesting depths.
    """
    if exp is None or is_simple_type(exp):
        return True
    if not isinstance(exp, dict) or len(exp) != 1 or "__extra__" in exp:
        return False
    k = next(iter(exp))
    v = exp[k]
    if k in (list, set):
        return can_specialize_type(v)
    if k is dict:
        return (
            isinstance(v, tuple)
            and len(v) == 2
            and can_specialize_type(v[0])
            and can_specialize_type(v[1])
        )
    if k is tuple:
        if isinstance(v, tuple) and len(v) == 2:
            if v[1] is True:
                return can_specialize_type(v[0])
            elif v[1] is False and isinstance(v[0], tuple):
                return all(can_specialize_type(item) for item in v[0])
    return False


def _generate_scalar_check(
    var_expr, exp, fail_call, fn_globals, prefix, is_loop=False
):
    """
    Generates AST statements for checking a simple scalar or union of scalar types.
    """
    tt = tuple(exp.keys())
    fn_globals[f"{prefix}_types"] = tt
    fn_globals[f"{prefix}_t0"] = tt[0]

    t0_name = f"__loc_{prefix}_t0" if is_loop else f"{prefix}_t0"
    types_name = f"__loc_{prefix}_types" if is_loop else f"{prefix}_types"

    var_class = ast.Attribute(value=var_expr, attr="__class__", ctx=ast.Load())

    if len(tt) == 1:
        test = ast.BoolOp(
            op=ast.And(),
            values=[
                ast.Compare(
                    left=var_class,
                    ops=[ast.IsNot()],
                    comparators=[ast.Name(id=t0_name, ctx=ast.Load())],
                ),
                ast.UnaryOp(
                    op=ast.Not(),
                    operand=ast.Call(
                        func=ast.Name(id="isinstance", ctx=ast.Load()),
                        args=[
                            var_expr,
                            ast.Name(id=types_name, ctx=ast.Load()),
                        ],
                        keywords=[],
                    ),
                ),
            ],
        )
    elif len(tt) == 2:
        fn_globals[f"{prefix}_t1"] = tt[1]
        t1_name = f"__loc_{prefix}_t1" if is_loop else f"{prefix}_t1"
        test = ast.BoolOp(
            op=ast.And(),
            values=[
                ast.Compare(
                    left=var_class,
                    ops=[ast.IsNot()],
                    comparators=[ast.Name(id=t0_name, ctx=ast.Load())],
                ),
                ast.Compare(
                    left=var_class,
                    ops=[ast.IsNot()],
                    comparators=[ast.Name(id=t1_name, ctx=ast.Load())],
                ),
                ast.UnaryOp(
                    op=ast.Not(),
                    operand=ast.Call(
                        func=ast.Name(id="isinstance", ctx=ast.Load()),
                        args=[
                            var_expr,
                            ast.Name(id=types_name, ctx=ast.Load()),
                        ],
                        keywords=[],
                    ),
                ),
            ],
        )
    else:
        test = ast.UnaryOp(
            op=ast.Not(),
            operand=ast.Call(
                func=ast.Name(id="isinstance", ctx=ast.Load()),
                args=[
                    var_expr,
                    ast.Name(id=types_name, ctx=ast.Load()),
                ],
                keywords=[],
            ),
        )

    return [ast.If(test=test, body=[fail_call], orelse=[])]


def generate_type_check_ast(
    var_expr,
    exp,
    fail_call,
    fn_globals,
    prefix,
    sample_pct,
    is_loop=False,
    use_local_t0=False,
):
    """
    Recursively generates AST check statements for an arbitrary type expression.
    Handles scalars, unions, lists, dicts, sets, and tuples at any nesting level.
    """
    if exp is None:
        return []

    if is_simple_type(exp):
        return _generate_scalar_check(
            var_expr, exp, fail_call, fn_globals, prefix, is_loop=use_local_t0
        )

    fail_stmt = fail_call
    loop_fail = (
        ast.If(
            test=ast.Constant(value=True),
            body=[fail_call, ast.Break()],
            orelse=[],
        )
        if is_loop
        else fail_call
    )

    k = next(iter(exp))
    v = exp[k]

    if k in (list, set):
        type_name = k.__name__
        sub_exp = v
        elem_is_simple = is_simple_type(sub_exp)

        # Outer type check
        outer_class_test = ast.Compare(
            left=ast.Attribute(
                value=var_expr, attr="__class__", ctx=ast.Load()
            ),
            ops=[ast.IsNot()],
            comparators=[ast.Name(id=type_name, ctx=ast.Load())],
        )
        outer_isinstance_test = ast.UnaryOp(
            op=ast.Not(),
            operand=ast.Call(
                func=ast.Name(id="isinstance", ctx=ast.Load()),
                args=[var_expr, ast.Name(id=type_name, ctx=ast.Load())],
                keywords=[],
            ),
        )
        outer_type_guard = ast.If(
            test=ast.BoolOp(
                op=ast.And(), values=[outer_class_test, outer_isinstance_test]
            ),
            body=[fail_stmt],
            orelse=[],
        )

        loop_var_id = f"{prefix}_el"
        loop_var_expr = ast.Name(id=loop_var_id, ctx=ast.Load())
        sub_checks = generate_type_check_ast(
            loop_var_expr,
            sub_exp,
            fail_stmt,
            fn_globals,
            f"{prefix}_el",
            sample_pct,
            is_loop=True,
        )

        if sample_pct == "first":
            content_check = ast.If(
                test=var_expr,
                body=[
                    ast.Assign(
                        targets=[ast.Name(id=loop_var_id, ctx=ast.Store())],
                        value=ast.Subscript(
                            value=var_expr,
                            slice=ast.Constant(value=0),
                            ctx=ast.Load(),
                        ),
                    )
                ]
                + sub_checks,
                orelse=[],
            )
        elif sample_pct == "last":
            if k is list:
                content_check = ast.If(
                    test=var_expr,
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id=loop_var_id, ctx=ast.Store())],
                            value=ast.Subscript(
                                value=var_expr,
                                slice=ast.Constant(value=-1),
                                ctx=ast.Load(),
                            ),
                        )
                    ]
                    + sub_checks,
                    orelse=[],
                )
            else:
                content_check = ast.If(
                    test=var_expr,
                    body=[
                        ast.For(
                            target=ast.Name(id=loop_var_id, ctx=ast.Store()),
                            iter=var_expr,
                            body=[ast.Pass()],
                            orelse=[],
                        )
                    ]
                    + sub_checks,
                    orelse=[],
                )
        elif sample_pct == 0:
            if k is list:
                content_check = ast.If(
                    test=var_expr,
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id=loop_var_id, ctx=ast.Store())],
                            value=ast.Call(
                                func=ast.Name(id="_choice", ctx=ast.Load()),
                                args=[var_expr],
                                keywords=[],
                            ),
                        )
                    ]
                    + sub_checks,
                    orelse=[],
                )
            else:
                content_check = ast.If(
                    test=var_expr,
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id=loop_var_id, ctx=ast.Store())],
                            value=ast.Call(
                                func=ast.Name(
                                    id="_random_set_item", ctx=ast.Load()
                                ),
                                args=[var_expr],
                                keywords=[],
                            ),
                        )
                    ]
                    + sub_checks,
                    orelse=[],
                )
        elif sample_pct == 100:
            if elem_is_simple:
                if len(sub_exp) == 1:
                    sub_checks_fast = generate_type_check_ast(
                        loop_var_expr,
                        sub_exp,
                        loop_fail,
                        fn_globals,
                        f"{prefix}_el",
                        sample_pct,
                        is_loop=True,
                        use_local_t0=True,
                    )
                    assign_locs = [
                        ast.Assign(
                            targets=[
                                ast.Name(
                                    id=f"__loc_{prefix}_el_t0", ctx=ast.Store()
                                )
                            ],
                            value=ast.Name(
                                id=f"{prefix}_el_t0", ctx=ast.Load()
                            ),
                        ),
                        ast.Assign(
                            targets=[
                                ast.Name(
                                    id=f"__loc_{prefix}_el_types",
                                    ctx=ast.Store(),
                                )
                            ],
                            value=ast.Name(
                                id=f"{prefix}_el_types", ctx=ast.Load()
                            ),
                        ),
                    ]
                    for_loop = ast.For(
                        target=ast.Name(id=loop_var_id, ctx=ast.Store()),
                        iter=var_expr,
                        body=sub_checks_fast,
                        orelse=[],
                    )
                    content_check = assign_locs + [for_loop]
                else:
                    elem_set = frozenset(sub_exp.keys())
                    fn_globals[f"{prefix}_elem_set"] = elem_set

                    for_loop = ast.For(
                        target=ast.Name(id=loop_var_id, ctx=ast.Store()),
                        iter=var_expr,
                        body=sub_checks,
                        orelse=[],
                    )
                    set_check = ast.If(
                        test=ast.UnaryOp(
                            op=ast.Not(),
                            operand=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(
                                        id=f"{prefix}_elem_set", ctx=ast.Load()
                                    ),
                                    attr="issuperset",
                                    ctx=ast.Load(),
                                ),
                                args=[
                                    ast.Call(
                                        func=ast.Name(id="map", ctx=ast.Load()),
                                        args=[
                                            ast.Name(id="type", ctx=ast.Load()),
                                            var_expr,
                                        ],
                                        keywords=[],
                                    )
                                ],
                                keywords=[],
                            ),
                        ),
                        body=[fail_stmt],
                        orelse=[],
                    )
                    content_check = [
                        ast.If(
                            test=ast.Compare(
                                left=ast.Call(
                                    func=ast.Name(id="len", ctx=ast.Load()),
                                    args=[var_expr],
                                    keywords=[],
                                ),
                                ops=[ast.LtE()],
                                comparators=[ast.Constant(value=50)],
                            ),
                            body=[for_loop],
                            orelse=[set_check],
                        )
                    ]
            else:
                content_check = [
                    ast.For(
                        target=ast.Name(id=loop_var_id, ctx=ast.Store()),
                        iter=var_expr,
                        body=sub_checks,
                        orelse=[],
                    )
                ]
        else:
            if sample_pct == "log":
                count_expr = ast.Call(
                    func=ast.Name(id="_log_count", ctx=ast.Load()),
                    args=[
                        ast.Call(
                            func=ast.Name(id="len", ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        )
                    ],
                    keywords=[],
                )
            else:
                fn_globals[f"{prefix}_pct"] = sample_pct
                count_expr = ast.Call(
                    func=ast.Name(id="max", ctx=ast.Load()),
                    args=[
                        ast.Constant(value=1),
                        ast.BinOp(
                            left=ast.BinOp(
                                left=ast.BinOp(
                                    left=ast.Call(
                                        func=ast.Name(id="len", ctx=ast.Load()),
                                        args=[var_expr],
                                        keywords=[],
                                    ),
                                    op=ast.Mult(),
                                    right=ast.Name(
                                        id=f"{prefix}_pct", ctx=ast.Load()
                                    ),
                                ),
                                op=ast.Add(),
                                right=ast.Constant(value=99),
                            ),
                            op=ast.FloorDiv(),
                            right=ast.Constant(value=100),
                        ),
                    ],
                    keywords=[],
                )

            if k is list:
                short_loop = ast.For(
                    target=ast.Name(id=loop_var_id, ctx=ast.Store()),
                    iter=var_expr,
                    body=sub_checks,
                    orelse=[],
                )
                assign_0 = ast.Assign(
                    targets=[ast.Name(id=loop_var_id, ctx=ast.Store())],
                    value=ast.Subscript(
                        value=var_expr,
                        slice=ast.Constant(value=0),
                        ctx=ast.Load(),
                    ),
                )
                assign_last = ast.Assign(
                    targets=[ast.Name(id=loop_var_id, ctx=ast.Store())],
                    value=ast.Subscript(
                        value=var_expr,
                        slice=ast.Constant(value=-1),
                        ctx=ast.Load(),
                    ),
                )
                idx_var_id = f"{prefix}_idx"
                step_expr = ast.Call(
                    func=ast.Name(id="max", ctx=ast.Load()),
                    args=[
                        ast.Constant(value=1),
                        ast.BinOp(
                            left=ast.BinOp(
                                left=ast.Call(
                                    func=ast.Name(id="len", ctx=ast.Load()),
                                    args=[var_expr],
                                    keywords=[],
                                ),
                                op=ast.Sub(),
                                right=ast.Constant(value=1),
                            ),
                            op=ast.FloorDiv(),
                            right=ast.Call(
                                func=ast.Name(id="max", ctx=ast.Load()),
                                args=[
                                    ast.Constant(value=1),
                                    ast.BinOp(
                                        left=count_expr,
                                        op=ast.Sub(),
                                        right=ast.Constant(value=1),
                                    ),
                                ],
                                keywords=[],
                            ),
                        ),
                    ],
                    keywords=[],
                )
                range_loop = ast.For(
                    target=ast.Name(id=idx_var_id, ctx=ast.Store()),
                    iter=ast.Call(
                        func=ast.Name(id="range", ctx=ast.Load()),
                        args=[
                            step_expr,
                            ast.BinOp(
                                left=ast.Call(
                                    func=ast.Name(id="len", ctx=ast.Load()),
                                    args=[var_expr],
                                    keywords=[],
                                ),
                                op=ast.Sub(),
                                right=ast.Constant(value=1),
                            ),
                            step_expr,
                        ],
                        keywords=[],
                    ),
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id=loop_var_id, ctx=ast.Store())],
                            value=ast.Subscript(
                                value=var_expr,
                                slice=ast.Name(id=idx_var_id, ctx=ast.Load()),
                                ctx=ast.Load(),
                            ),
                        )
                    ]
                    + sub_checks,
                    orelse=[],
                )
                long_check = (
                    [assign_0]
                    + sub_checks
                    + [assign_last]
                    + sub_checks
                    + [range_loop]
                )
                content_check = ast.If(
                    test=ast.Compare(
                        left=ast.Call(
                            func=ast.Name(id="len", ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        ),
                        ops=[ast.LtE()],
                        comparators=[ast.Constant(value=3)],
                    ),
                    body=[short_loop],
                    orelse=long_check,
                )
            else:
                short_loop = ast.For(
                    target=ast.Name(id=loop_var_id, ctx=ast.Store()),
                    iter=var_expr,
                    body=sub_checks,
                    orelse=[],
                )
                islice_loop = ast.For(
                    target=ast.Name(id=loop_var_id, ctx=ast.Store()),
                    iter=ast.Call(
                        func=ast.Name(id="islice", ctx=ast.Load()),
                        args=[var_expr, count_expr],
                        keywords=[],
                    ),
                    body=sub_checks,
                    orelse=[],
                )
                content_check = ast.If(
                    test=ast.Compare(
                        left=ast.Call(
                            func=ast.Name(id="len", ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        ),
                        ops=[ast.LtE()],
                        comparators=[ast.Constant(value=3)],
                    ),
                    body=[short_loop],
                    orelse=[islice_loop],
                )

        return [outer_type_guard] + (
            content_check
            if isinstance(content_check, list)
            else [content_check]
        )

    if k is dict:
        k_exp, v_exp = v
        kv_is_simple = is_simple_type(k_exp) and is_simple_type(v_exp)

        # Outer dict check
        outer_class_test = ast.Compare(
            left=ast.Attribute(
                value=var_expr, attr="__class__", ctx=ast.Load()
            ),
            ops=[ast.IsNot()],
            comparators=[ast.Name(id="dict", ctx=ast.Load())],
        )
        outer_isinstance_test = ast.UnaryOp(
            op=ast.Not(),
            operand=ast.Call(
                func=ast.Name(id="isinstance", ctx=ast.Load()),
                args=[var_expr, ast.Name(id="dict", ctx=ast.Load())],
                keywords=[],
            ),
        )
        outer_type_guard = ast.If(
            test=ast.BoolOp(
                op=ast.And(), values=[outer_class_test, outer_isinstance_test]
            ),
            body=[fail_stmt],
            orelse=[],
        )

        k_var_id = f"{prefix}_k"
        v_var_id = f"{prefix}_v"
        k_var_expr = ast.Name(id=k_var_id, ctx=ast.Load())
        v_var_expr = ast.Name(id=v_var_id, ctx=ast.Load())

        k_checks = generate_type_check_ast(
            k_var_expr,
            k_exp,
            fail_stmt,
            fn_globals,
            f"{prefix}_k",
            sample_pct,
            is_loop=True,
        )
        v_checks = generate_type_check_ast(
            v_var_expr,
            v_exp,
            fail_stmt,
            fn_globals,
            f"{prefix}_v",
            sample_pct,
            is_loop=True,
        )

        assign_val = ast.Assign(
            targets=[ast.Name(id=v_var_id, ctx=ast.Store())],
            value=ast.Subscript(
                value=var_expr, slice=k_var_expr, ctx=ast.Load()
            ),
        )
        dict_loop_body = k_checks + [assign_val] + v_checks

        if sample_pct == "first":
            content_check = ast.If(
                test=var_expr,
                body=[
                    ast.Assign(
                        targets=[ast.Name(id=k_var_id, ctx=ast.Store())],
                        value=ast.Call(
                            func=ast.Name(id="next", ctx=ast.Load()),
                            args=[
                                ast.Call(
                                    func=ast.Name(id="iter", ctx=ast.Load()),
                                    args=[var_expr],
                                    keywords=[],
                                )
                            ],
                            keywords=[],
                        ),
                    )
                ]
                + dict_loop_body,
                orelse=[],
            )
        elif sample_pct == "last":
            content_check = ast.If(
                test=var_expr,
                body=[
                    ast.Assign(
                        targets=[ast.Name(id=k_var_id, ctx=ast.Store())],
                        value=ast.Call(
                            func=ast.Name(id="next", ctx=ast.Load()),
                            args=[
                                ast.Call(
                                    func=ast.Name(
                                        id="reversed", ctx=ast.Load()
                                    ),
                                    args=[var_expr],
                                    keywords=[],
                                )
                            ],
                            keywords=[],
                        ),
                    )
                ]
                + dict_loop_body,
                orelse=[],
            )
        elif sample_pct == 0:
            content_check = ast.If(
                test=var_expr,
                body=[
                    ast.Assign(
                        targets=[ast.Name(id=k_var_id, ctx=ast.Store())],
                        value=ast.Call(
                            func=ast.Name(
                                id="_random_dict_key", ctx=ast.Load()
                            ),
                            args=[var_expr],
                            keywords=[],
                        ),
                    )
                ]
                + dict_loop_body,
                orelse=[],
            )
        elif sample_pct == 100:
            if kv_is_simple:
                k_set = frozenset(k_exp.keys())
                v_set = frozenset(v_exp.keys())
                fn_globals[f"{prefix}_k_set"] = k_set
                fn_globals[f"{prefix}_v_set"] = v_set

                for_loop = ast.For(
                    target=ast.Tuple(
                        elts=[
                            ast.Name(id=k_var_id, ctx=ast.Store()),
                            ast.Name(id=v_var_id, ctx=ast.Store()),
                        ],
                        ctx=ast.Store(),
                    ),
                    iter=ast.Call(
                        func=ast.Attribute(
                            value=var_expr, attr="items", ctx=ast.Load()
                        ),
                        args=[],
                        keywords=[],
                    ),
                    body=k_checks + v_checks,
                    orelse=[],
                )
                set_check = ast.If(
                    test=ast.UnaryOp(
                        op=ast.Not(),
                        operand=ast.BoolOp(
                            op=ast.And(),
                            values=[
                                ast.Call(
                                    func=ast.Attribute(
                                        value=ast.Name(
                                            id=f"{prefix}_k_set", ctx=ast.Load()
                                        ),
                                        attr="issuperset",
                                        ctx=ast.Load(),
                                    ),
                                    args=[
                                        ast.Call(
                                            func=ast.Name(
                                                id="map", ctx=ast.Load()
                                            ),
                                            args=[
                                                ast.Name(
                                                    id="type", ctx=ast.Load()
                                                ),
                                                var_expr,
                                            ],
                                            keywords=[],
                                        )
                                    ],
                                    keywords=[],
                                ),
                                ast.Call(
                                    func=ast.Attribute(
                                        value=ast.Name(
                                            id=f"{prefix}_v_set", ctx=ast.Load()
                                        ),
                                        attr="issuperset",
                                        ctx=ast.Load(),
                                    ),
                                    args=[
                                        ast.Call(
                                            func=ast.Name(
                                                id="map", ctx=ast.Load()
                                            ),
                                            args=[
                                                ast.Name(
                                                    id="type", ctx=ast.Load()
                                                ),
                                                ast.Call(
                                                    func=ast.Attribute(
                                                        value=var_expr,
                                                        attr="values",
                                                        ctx=ast.Load(),
                                                    ),
                                                    args=[],
                                                    keywords=[],
                                                ),
                                            ],
                                            keywords=[],
                                        )
                                    ],
                                    keywords=[],
                                ),
                            ],
                        ),
                    ),
                    body=[fail_stmt],
                    orelse=[],
                )
                content_check = ast.If(
                    test=ast.Compare(
                        left=ast.Call(
                            func=ast.Name(id="len", ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        ),
                        ops=[ast.LtE()],
                        comparators=[ast.Constant(value=50)],
                    ),
                    body=[for_loop],
                    orelse=[set_check],
                )
            else:
                content_check = ast.For(
                    target=ast.Name(id=k_var_id, ctx=ast.Store()),
                    iter=var_expr,
                    body=dict_loop_body,
                    orelse=[],
                )
        else:
            if sample_pct == "log":
                count_expr = ast.Call(
                    func=ast.Name(id="_log_count", ctx=ast.Load()),
                    args=[
                        ast.Call(
                            func=ast.Name(id="len", ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        )
                    ],
                    keywords=[],
                )
            else:
                fn_globals[f"{prefix}_pct"] = sample_pct
                count_expr = ast.Call(
                    func=ast.Name(id="max", ctx=ast.Load()),
                    args=[
                        ast.Constant(value=1),
                        ast.BinOp(
                            left=ast.BinOp(
                                left=ast.BinOp(
                                    left=ast.Call(
                                        func=ast.Name(id="len", ctx=ast.Load()),
                                        args=[var_expr],
                                        keywords=[],
                                    ),
                                    op=ast.Mult(),
                                    right=ast.Name(
                                        id=f"{prefix}_pct", ctx=ast.Load()
                                    ),
                                ),
                                op=ast.Add(),
                                right=ast.Constant(value=99),
                            ),
                            op=ast.FloorDiv(),
                            right=ast.Constant(value=100),
                        ),
                    ],
                    keywords=[],
                )
            short_loop = ast.For(
                target=ast.Name(id=k_var_id, ctx=ast.Store()),
                iter=var_expr,
                body=dict_loop_body,
                orelse=[],
            )
            assign_k0 = ast.Assign(
                targets=[ast.Name(id=k_var_id, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Name(id="next", ctx=ast.Load()),
                    args=[
                        ast.Call(
                            func=ast.Name(id="iter", ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        )
                    ],
                    keywords=[],
                ),
            )
            assign_kl = ast.Assign(
                targets=[ast.Name(id=k_var_id, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Name(id="next", ctx=ast.Load()),
                    args=[
                        ast.Call(
                            func=ast.Name(id="reversed", ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        )
                    ],
                    keywords=[],
                ),
            )
            mid_count = ast.BinOp(
                left=ast.Call(
                    func=ast.Name(id="max", ctx=ast.Load()),
                    args=[ast.Constant(value=3), count_expr],
                    keywords=[],
                ),
                op=ast.Sub(),
                right=ast.Constant(value=2),
            )
            mid_loop = ast.For(
                target=ast.Name(id=k_var_id, ctx=ast.Store()),
                iter=ast.Call(
                    func=ast.Name(id="islice", ctx=ast.Load()),
                    args=[var_expr, ast.Constant(value=1), mid_count],
                    keywords=[],
                ),
                body=dict_loop_body,
                orelse=[],
            )
            long_check = (
                [assign_k0]
                + dict_loop_body
                + [assign_kl]
                + dict_loop_body
                + [mid_loop]
            )
            content_check = ast.If(
                test=ast.Compare(
                    left=ast.Call(
                        func=ast.Name(id="len", ctx=ast.Load()),
                        args=[var_expr],
                        keywords=[],
                    ),
                    ops=[ast.LtE()],
                    comparators=[ast.Constant(value=3)],
                ),
                body=[short_loop],
                orelse=long_check,
            )

        return [outer_type_guard, content_check]

    if k is tuple:
        if isinstance(v, tuple) and len(v) == 2 and v[1] is True:
            # Variable-length tuple[T, ...]
            sub_exp = v[0]
            elem_is_simple = is_simple_type(sub_exp)

            outer_class_test = ast.Compare(
                left=ast.Attribute(
                    value=var_expr, attr="__class__", ctx=ast.Load()
                ),
                ops=[ast.IsNot()],
                comparators=[ast.Name(id="tuple", ctx=ast.Load())],
            )
            outer_isinstance_test = ast.UnaryOp(
                op=ast.Not(),
                operand=ast.Call(
                    func=ast.Name(id="isinstance", ctx=ast.Load()),
                    args=[var_expr, ast.Name(id="tuple", ctx=ast.Load())],
                    keywords=[],
                ),
            )
            outer_type_guard = ast.If(
                test=ast.BoolOp(
                    op=ast.And(),
                    values=[outer_class_test, outer_isinstance_test],
                ),
                body=[fail_stmt],
                orelse=[],
            )

            loop_var_id = f"{prefix}_el"
            loop_var_expr = ast.Name(id=loop_var_id, ctx=ast.Load())
            sub_checks = generate_type_check_ast(
                loop_var_expr,
                sub_exp,
                fail_stmt,
                fn_globals,
                f"{prefix}_el",
                sample_pct,
                is_loop=True,
            )

            if sample_pct == "first":
                content_check = ast.If(
                    test=var_expr,
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id=loop_var_id, ctx=ast.Store())],
                            value=ast.Subscript(
                                value=var_expr,
                                slice=ast.Constant(value=0),
                                ctx=ast.Load(),
                            ),
                        )
                    ]
                    + sub_checks,
                    orelse=[],
                )
            elif sample_pct == "last":
                content_check = ast.If(
                    test=var_expr,
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id=loop_var_id, ctx=ast.Store())],
                            value=ast.Subscript(
                                value=var_expr,
                                slice=ast.Constant(value=-1),
                                ctx=ast.Load(),
                            ),
                        )
                    ]
                    + sub_checks,
                    orelse=[],
                )
            elif sample_pct == 0:
                content_check = ast.If(
                    test=var_expr,
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id=loop_var_id, ctx=ast.Store())],
                            value=ast.Call(
                                func=ast.Name(id="_choice", ctx=ast.Load()),
                                args=[var_expr],
                                keywords=[],
                            ),
                        )
                    ]
                    + sub_checks,
                    orelse=[],
                )
            elif sample_pct == 100:
                if elem_is_simple:
                    if len(sub_exp) == 1:
                        sub_checks_fast = generate_type_check_ast(
                            loop_var_expr,
                            sub_exp,
                            loop_fail,
                            fn_globals,
                            f"{prefix}_el",
                            sample_pct,
                            is_loop=True,
                            use_local_t0=True,
                        )
                        assign_locs = [
                            ast.Assign(
                                targets=[
                                    ast.Name(
                                        id=f"__loc_{prefix}_el_t0",
                                        ctx=ast.Store(),
                                    )
                                ],
                                value=ast.Name(
                                    id=f"{prefix}_el_t0", ctx=ast.Load()
                                ),
                            ),
                            ast.Assign(
                                targets=[
                                    ast.Name(
                                        id=f"__loc_{prefix}_el_types",
                                        ctx=ast.Store(),
                                    )
                                ],
                                value=ast.Name(
                                    id=f"{prefix}_el_types", ctx=ast.Load()
                                ),
                            ),
                        ]
                        for_loop = ast.For(
                            target=ast.Name(id=loop_var_id, ctx=ast.Store()),
                            iter=var_expr,
                            body=sub_checks_fast,
                            orelse=[],
                        )
                        content_check = assign_locs + [for_loop]
                    else:
                        elem_set = frozenset(sub_exp.keys())
                        fn_globals[f"{prefix}_elem_set"] = elem_set

                        for_loop = ast.For(
                            target=ast.Name(id=loop_var_id, ctx=ast.Store()),
                            iter=var_expr,
                            body=sub_checks,
                            orelse=[],
                        )
                        set_check = ast.If(
                            test=ast.UnaryOp(
                                op=ast.Not(),
                                operand=ast.Call(
                                    func=ast.Attribute(
                                        value=ast.Name(
                                            id=f"{prefix}_elem_set",
                                            ctx=ast.Load(),
                                        ),
                                        attr="issuperset",
                                        ctx=ast.Load(),
                                    ),
                                    args=[
                                        ast.Call(
                                            func=ast.Name(
                                                id="map", ctx=ast.Load()
                                            ),
                                            args=[
                                                ast.Name(
                                                    id="type", ctx=ast.Load()
                                                ),
                                                var_expr,
                                            ],
                                            keywords=[],
                                        )
                                    ],
                                    keywords=[],
                                ),
                            ),
                            body=[fail_stmt],
                            orelse=[],
                        )
                        content_check = [
                            ast.If(
                                test=ast.Compare(
                                    left=ast.Call(
                                        func=ast.Name(id="len", ctx=ast.Load()),
                                        args=[var_expr],
                                        keywords=[],
                                    ),
                                    ops=[ast.LtE()],
                                    comparators=[ast.Constant(value=50)],
                                ),
                                body=[for_loop],
                                orelse=[set_check],
                            )
                        ]
                else:
                    content_check = [
                        ast.For(
                            target=ast.Name(id=loop_var_id, ctx=ast.Store()),
                            iter=var_expr,
                            body=sub_checks,
                            orelse=[],
                        )
                    ]
            else:
                if sample_pct == "log":
                    count_expr = ast.Call(
                        func=ast.Name(id="_log_count", ctx=ast.Load()),
                        args=[
                            ast.Call(
                                func=ast.Name(id="len", ctx=ast.Load()),
                                args=[var_expr],
                                keywords=[],
                            )
                        ],
                        keywords=[],
                    )
                elif sample_pct == "sqrt":
                    count_expr = ast.Call(
                        func=ast.Name(id="max", ctx=ast.Load()),
                        args=[
                            ast.Constant(value=1),
                            ast.Call(
                                func=ast.Name(id="int", ctx=ast.Load()),
                                args=[
                                    ast.BinOp(
                                        left=ast.Call(
                                            func=ast.Name(
                                                id="len", ctx=ast.Load()
                                            ),
                                            args=[var_expr],
                                            keywords=[],
                                        ),
                                        op=ast.Pow(),
                                        right=ast.Constant(value=0.5),
                                    )
                                ],
                                keywords=[],
                            ),
                        ],
                        keywords=[],
                    )
                else:
                    fn_globals[f"{prefix}_pct"] = sample_pct
                    count_expr = ast.Call(
                        func=ast.Name(id="max", ctx=ast.Load()),
                        args=[
                            ast.Constant(value=1),
                            ast.BinOp(
                                left=ast.BinOp(
                                    left=ast.BinOp(
                                        left=ast.Call(
                                            func=ast.Name(
                                                id="len", ctx=ast.Load()
                                            ),
                                            args=[var_expr],
                                            keywords=[],
                                        ),
                                        op=ast.Mult(),
                                        right=ast.Name(
                                            id=f"{prefix}_pct", ctx=ast.Load()
                                        ),
                                    ),
                                    op=ast.Add(),
                                    right=ast.Constant(value=99),
                                ),
                                op=ast.FloorDiv(),
                                right=ast.Constant(value=100),
                            ),
                        ],
                        keywords=[],
                    )

                idx_var_id = f"{prefix}_idx"
                assign_0 = ast.Assign(
                    targets=[ast.Name(id=loop_var_id, ctx=ast.Store())],
                    value=ast.Subscript(
                        value=var_expr,
                        slice=ast.Constant(value=0),
                        ctx=ast.Load(),
                    ),
                )
                assign_last = ast.Assign(
                    targets=[ast.Name(id=loop_var_id, ctx=ast.Store())],
                    value=ast.Subscript(
                        value=var_expr,
                        slice=ast.Constant(value=-1),
                        ctx=ast.Load(),
                    ),
                )
                short_loop = ast.For(
                    target=ast.Name(id=loop_var_id, ctx=ast.Store()),
                    iter=var_expr,
                    body=sub_checks,
                    orelse=[],
                )
                step_expr = ast.Call(
                    func=ast.Name(id="max", ctx=ast.Load()),
                    args=[
                        ast.Constant(value=1),
                        ast.BinOp(
                            left=ast.BinOp(
                                left=ast.Call(
                                    func=ast.Name(id="len", ctx=ast.Load()),
                                    args=[var_expr],
                                    keywords=[],
                                ),
                                op=ast.Sub(),
                                right=ast.Constant(value=1),
                            ),
                            op=ast.FloorDiv(),
                            right=ast.Call(
                                func=ast.Name(id="max", ctx=ast.Load()),
                                args=[
                                    ast.Constant(value=1),
                                    ast.BinOp(
                                        left=count_expr,
                                        op=ast.Sub(),
                                        right=ast.Constant(value=1),
                                    ),
                                ],
                                keywords=[],
                            ),
                        ),
                    ],
                    keywords=[],
                )
                range_loop = ast.For(
                    target=ast.Name(id=idx_var_id, ctx=ast.Store()),
                    iter=ast.Call(
                        func=ast.Name(id="range", ctx=ast.Load()),
                        args=[
                            step_expr,
                            ast.BinOp(
                                left=ast.Call(
                                    func=ast.Name(id="len", ctx=ast.Load()),
                                    args=[var_expr],
                                    keywords=[],
                                ),
                                op=ast.Sub(),
                                right=ast.Constant(value=1),
                            ),
                            step_expr,
                        ],
                        keywords=[],
                    ),
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id=loop_var_id, ctx=ast.Store())],
                            value=ast.Subscript(
                                value=var_expr,
                                slice=ast.Name(id=idx_var_id, ctx=ast.Load()),
                                ctx=ast.Load(),
                            ),
                        )
                    ]
                    + sub_checks,
                    orelse=[],
                )
                long_check = (
                    [assign_0]
                    + sub_checks
                    + [assign_last]
                    + sub_checks
                    + [range_loop]
                )
                content_check = ast.If(
                    test=ast.Compare(
                        left=ast.Call(
                            func=ast.Name(id="len", ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        ),
                        ops=[ast.LtE()],
                        comparators=[ast.Constant(value=3)],
                    ),
                    body=[short_loop],
                    orelse=long_check,
                )

            return [outer_type_guard] + (
                content_check
                if isinstance(content_check, list)
                else [content_check]
            )

        elif (
            isinstance(v, tuple)
            and len(v) == 2
            and v[1] is False
            and isinstance(v[0], tuple)
        ):
            # Fixed-length tuple[T1, T2, ...]
            elem_exps = v[0]
            expected_len = len(elem_exps)
            outer_test = ast.BoolOp(
                op=ast.Or(),
                values=[
                    ast.Compare(
                        left=ast.Attribute(
                            value=var_expr, attr="__class__", ctx=ast.Load()
                        ),
                        ops=[ast.IsNot()],
                        comparators=[ast.Name(id="tuple", ctx=ast.Load())],
                    ),
                    ast.Compare(
                        left=ast.Call(
                            func=ast.Name(id="len", ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        ),
                        ops=[ast.NotEq()],
                        comparators=[ast.Constant(value=expected_len)],
                    ),
                ],
            )
            outer_type_guard = ast.If(
                test=outer_test, body=[fail_stmt], orelse=[]
            )

            elem_checks = []
            for j, item_exp in enumerate(elem_exps):
                t_var_id = f"{prefix}_t{j}"
                t_var_expr = ast.Name(id=t_var_id, ctx=ast.Load())
                elem_assign = ast.Assign(
                    targets=[ast.Name(id=t_var_id, ctx=ast.Store())],
                    value=ast.Subscript(
                        value=var_expr,
                        slice=ast.Constant(value=j),
                        ctx=ast.Load(),
                    ),
                )
                t_checks = generate_type_check_ast(
                    t_var_expr,
                    item_exp,
                    fail_stmt,
                    fn_globals,
                    f"{prefix}_t{j}",
                    sample_pct,
                )
                elem_checks.extend([elem_assign] + t_checks)

            return [outer_type_guard] + elem_checks

    return [fail_stmt]


def build_specialized_call(
    fn,
    posonly_names,
    pos_names,
    kwonly_names,
    vararg_name,
    kwarg_name,
    defaults,
    kwdefaults,
    param_exps,
    check_type_fn,
    sample_pct,
    get_sample_indices_fn,
    get_sample_keys_fn,
    ret_mode,
    ret_t0=None,
    ret_t1=None,
    ret_types=None,
    ret_exp=None,
):
    """
    Generates a specialized __call__ method using dynamic AST compilation.
    Supports positional, positional-only, keyword-only, and variadic (*args, **kwargs) parameters.
    Zero eval() or exec().
    """
    fn_globals = {
        "_fn": fn,
        "_check_fn": check_type_fn,
        "isinstance": isinstance,
        "len": len,
        "range": range,
        "set": set,
        "map": map,
        "type": type,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "islice": islice,
        "enumerate": enumerate,
        "next": next,
        "iter": iter,
        "reversed": reversed,
        "int": int,
        "max": max,
        "_choice": random.choice,
        "_random_dict_key": _random_dict_key,
        "_random_set_item": _random_set_item,
        "_log_count": _log_count,
        "_get_sample_indices": get_sample_indices_fn,
        "_get_sample_keys": get_sample_keys_fn,
    }

    if posonly_names:
        posonlyargs = [ast.arg(arg="__enf_self__")] + [
            ast.arg(arg=name) for name in posonly_names
        ]
        args = [ast.arg(arg=name) for name in pos_names]
    else:
        posonlyargs = []
        args = [ast.arg(arg="__enf_self__")] + [
            ast.arg(arg=name) for name in pos_names
        ]

    kwonlyargs = [ast.arg(arg=name) for name in kwonly_names]
    kw_defaults = [None] * len(kwonly_names)
    vararg = ast.arg(arg=vararg_name) if vararg_name else None
    kwarg = ast.arg(arg=kwarg_name) if kwarg_name else None

    body = []

    check_params = list(posonly_names) + list(pos_names) + list(kwonly_names)
    if vararg_name and vararg_name in param_exps:
        check_params.append(vararg_name)
    if kwarg_name and kwarg_name in param_exps:
        check_params.append(kwarg_name)

    for i, name in enumerate(check_params):
        exp = param_exps.get(name)
        if exp is None:
            continue

        fn_globals[f"_param_exp_{i}"] = exp
        fail_call = ast.Expr(
            value=ast.Call(
                func=ast.Name(id="_check_fn", ctx=ast.Load()),
                args=[
                    ast.Name(id="__enf_self__", ctx=ast.Load()),
                    ast.Name(id=name, ctx=ast.Load()),
                    ast.Name(id=f"_param_exp_{i}", ctx=ast.Load()),
                    ast.Constant(value=name),
                ],
                keywords=[],
            )
        )

        var_expr = ast.Name(id=name, ctx=ast.Load())
        param_checks = generate_type_check_ast(
            var_expr,
            exp,
            fail_call,
            fn_globals,
            f"_p{i}",
            sample_pct,
        )
        body.extend(param_checks)

    call_args_fixed = [
        ast.Name(id=name, ctx=ast.Load())
        for name in list(posonly_names) + list(pos_names)
    ]
    call_kw_fixed = [
        ast.keyword(arg=name, value=ast.Name(id=name, ctx=ast.Load()))
        for name in kwonly_names
    ]

    if not vararg_name and not kwarg_name:
        fn_call = ast.Call(
            func=ast.Name(id="_fn", ctx=ast.Load()),
            args=call_args_fixed,
            keywords=call_kw_fixed,
        )
    elif vararg_name and not kwarg_name:
        call_args_starred = list(call_args_fixed) + [
            ast.Starred(
                value=ast.Name(id=vararg_name, ctx=ast.Load()), ctx=ast.Load()
            )
        ]
        fn_call = ast.IfExp(
            test=ast.Name(id=vararg_name, ctx=ast.Load()),
            body=ast.Call(
                func=ast.Name(id="_fn", ctx=ast.Load()),
                args=call_args_starred,
                keywords=call_kw_fixed,
            ),
            orelse=ast.Call(
                func=ast.Name(id="_fn", ctx=ast.Load()),
                args=call_args_fixed,
                keywords=call_kw_fixed,
            ),
        )
    elif kwarg_name and not vararg_name:
        call_kw_starred = list(call_kw_fixed) + [
            ast.keyword(arg=None, value=ast.Name(id=kwarg_name, ctx=ast.Load()))
        ]
        fn_call = ast.IfExp(
            test=ast.Name(id=kwarg_name, ctx=ast.Load()),
            body=ast.Call(
                func=ast.Name(id="_fn", ctx=ast.Load()),
                args=call_args_fixed,
                keywords=call_kw_starred,
            ),
            orelse=ast.Call(
                func=ast.Name(id="_fn", ctx=ast.Load()),
                args=call_args_fixed,
                keywords=call_kw_fixed,
            ),
        )
    else:
        call_args_starred = list(call_args_fixed) + [
            ast.Starred(
                value=ast.Name(id=vararg_name, ctx=ast.Load()), ctx=ast.Load()
            )
        ]
        call_kw_starred = list(call_kw_fixed) + [
            ast.keyword(arg=None, value=ast.Name(id=kwarg_name, ctx=ast.Load()))
        ]
        fn_call = ast.IfExp(
            test=ast.BoolOp(
                op=ast.Or(),
                values=[
                    ast.Name(id=vararg_name, ctx=ast.Load()),
                    ast.Name(id=kwarg_name, ctx=ast.Load()),
                ],
            ),
            body=ast.Call(
                func=ast.Name(id="_fn", ctx=ast.Load()),
                args=call_args_starred,
                keywords=call_kw_starred,
            ),
            orelse=ast.Call(
                func=ast.Name(id="_fn", ctx=ast.Load()),
                args=call_args_fixed,
                keywords=call_kw_fixed,
            ),
        )

    if ret_mode == 0:
        body.append(ast.Return(value=fn_call))
    elif ret_mode == 1:
        fn_globals["_ret_exp"] = ret_exp
        body.append(
            ast.Assign(
                targets=[ast.Name(id="__enf_res__", ctx=ast.Store())],
                value=fn_call,
            )
        )
        body.append(
            ast.If(
                test=ast.Compare(
                    left=ast.Name(id="__enf_res__", ctx=ast.Load()),
                    ops=[ast.Is()],
                    comparators=[ast.Constant(value=None)],
                ),
                body=[
                    ast.Return(value=ast.Name(id="__enf_res__", ctx=ast.Load()))
                ],
                orelse=[],
            )
        )
        body.append(
            ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="_check_fn", ctx=ast.Load()),
                    args=[
                        ast.Name(id="__enf_self__", ctx=ast.Load()),
                        ast.Name(id="__enf_res__", ctx=ast.Load()),
                        ast.Name(id="_ret_exp", ctx=ast.Load()),
                        ast.Constant(value="return"),
                    ],
                    keywords=[],
                )
            )
        )
        body.append(
            ast.Return(value=ast.Name(id="__enf_res__", ctx=ast.Load()))
        )
    else:
        fn_globals["_ret_t0"] = ret_t0
        fn_globals["_ret_t1"] = ret_t1
        fn_globals["_ret_types"] = ret_types
        fn_globals["_ret_exp"] = ret_exp

        body.append(
            ast.Assign(
                targets=[ast.Name(id="__enf_res__", ctx=ast.Store())],
                value=fn_call,
            )
        )
        ret_class = ast.Attribute(
            value=ast.Name(id="__enf_res__", ctx=ast.Load()),
            attr="__class__",
            ctx=ast.Load(),
        )
        ret_check_test = ast.BoolOp(
            op=ast.Or(),
            values=[
                ast.Compare(
                    left=ret_class,
                    ops=[ast.Is()],
                    comparators=[ast.Name(id="_ret_t0", ctx=ast.Load())],
                ),
                ast.Compare(
                    left=ret_class,
                    ops=[ast.Is()],
                    comparators=[ast.Name(id="_ret_t1", ctx=ast.Load())],
                ),
                ast.Call(
                    func=ast.Name(id="isinstance", ctx=ast.Load()),
                    args=[
                        ast.Name(id="__enf_res__", ctx=ast.Load()),
                        ast.Name(id="_ret_types", ctx=ast.Load()),
                    ],
                    keywords=[],
                ),
            ],
        )
        body.append(
            ast.If(
                test=ret_check_test,
                body=[
                    ast.Return(value=ast.Name(id="__enf_res__", ctx=ast.Load()))
                ],
                orelse=[],
            )
        )
        body.append(
            ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="_check_fn", ctx=ast.Load()),
                    args=[
                        ast.Name(id="__enf_self__", ctx=ast.Load()),
                        ast.Name(id="__enf_res__", ctx=ast.Load()),
                        ast.Name(id="_ret_exp", ctx=ast.Load()),
                        ast.Constant(value="return"),
                    ],
                    keywords=[],
                )
            )
        )
        body.append(
            ast.Return(value=ast.Name(id="__enf_res__", ctx=ast.Load()))
        )

    fn_def = ast.FunctionDef(
        name="__call__",
        args=ast.arguments(
            posonlyargs=posonlyargs,
            args=args,
            vararg=vararg,
            kwonlyargs=kwonlyargs,
            kw_defaults=kw_defaults,
            kwarg=kwarg,
            defaults=[],
        ),
        body=body,
        decorator_list=[],
    )
    module = ast.Module(body=[fn_def], type_ignores=[])
    ast.fix_missing_locations(module)
    code_mod = compile(module, "<type_enforced_specialized>", "exec")
    func_code = [
        c
        for c in code_mod.co_consts
        if isinstance(c, types.CodeType) and c.co_name == "__call__"
    ][0]

    call_method = types.FunctionType(
        func_code, fn_globals, name="__call__", argdefs=defaults
    )
    if kwdefaults:
        call_method.__kwdefaults__ = kwdefaults

    return call_method
