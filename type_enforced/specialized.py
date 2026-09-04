import ast
import random
import types
from itertools import islice
from typing import Type

try:
    from type_enforced import cpp as _cpp

    if not hasattr(_cpp, "validate_list_single"):
        _cpp = None
except ImportError:
    _cpp = None

_CODE_CACHE = {}


def _fast_fix_locations(root, lineno=1, col_offset=0):
    stack = [root]
    while stack:
        node = stack.pop()
        node.lineno = lineno
        node.col_offset = col_offset
        node.end_lineno = lineno
        node.end_col_offset = col_offset
        for field in node._fields:
            v = getattr(node, field, None)
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, ast.AST):
                        stack.append(item)
            elif isinstance(v, ast.AST):
                stack.append(v)


def _freeze_exp(exp):
    if exp is None:
        return None
    if isinstance(exp, dict):
        items = []
        for k, v in exp.items():
            if isinstance(k, tuple):
                k_frozen = tuple(_freeze_exp(sub) for sub in k)
            else:
                k_frozen = k
            items.append((k_frozen, _freeze_exp(v)))
        return tuple(items)
    if isinstance(exp, (tuple, list, set, frozenset)):
        return tuple(_freeze_exp(item) for item in exp)
    return exp


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
        and all(
            isinstance(k, type)
            and getattr(k, "__name__", "")
            not in ("__SelfType__", "__NeverType__")
            and getattr(k, "__origin__", None) not in (type, Type)
            for k in exp.keys()
        )
    )


def is_self_type(exp):
    return (
        isinstance(exp, dict)
        and "__extra__" not in exp
        and len(exp) == 1
        and any(
            getattr(k, "__name__", "") == "__SelfType__" for k in exp.keys()
        )
    )


def is_callable_type(exp):
    return (
        isinstance(exp, dict)
        and "__extra__" in exp
        and bool(exp["__extra__"].get("__callable__"))
    )


def is_uninitialized_class_type(exp):
    return (
        isinstance(exp, dict)
        and "__extra__" not in exp
        and bool(exp)
        and all(v is None for v in exp.values())
        and all(
            getattr(k, "__origin__", None) in (type, Type) or k in (type, Type)
            for k in exp.keys()
        )
    )


def is_typeddict_type(exp):
    return (
        isinstance(exp, dict)
        and "__extra__" in exp
        and "__typeddict__" in exp["__extra__"]
        and exp.get(dict) is None
    )


def can_specialize_type(exp):
    """
    Recursively determines if an expected type expression can be specialized via AST.
    Supports scalars, unions, lists, dicts, sets, tuples, Callables, Type[T],
    TypedDict, and Self to arbitrary nesting depths, including multi-variant collection schemas.
    """
    if (
        exp is None
        or is_simple_type(exp)
        or is_self_type(exp)
        or is_callable_type(exp)
        or is_uninitialized_class_type(exp)
    ):
        return True
    if is_typeddict_type(exp):
        td_info = exp["__extra__"]["__typeddict__"]
        return all(can_specialize_type(fe) for fe in td_info["fields"].values())
    if not isinstance(exp, dict) or len(exp) != 1 or "__extra__" in exp:
        return False
    k = next(iter(exp))
    v = exp[k]
    if k in (list, set):
        if isinstance(v, list):
            return all(can_specialize_type(variant) for variant in v)
        return can_specialize_type(v)
    if k is dict:
        if isinstance(v, list):
            return all(
                isinstance(variant, tuple)
                and len(variant) == 2
                and can_specialize_type(variant[0])
                and can_specialize_type(variant[1])
                for variant in v
            )
        return (
            isinstance(v, tuple)
            and len(v) == 2
            and can_specialize_type(v[0])
            and can_specialize_type(v[1])
        )
    if k is tuple:
        if isinstance(v, list):
            return all(
                isinstance(variant, tuple)
                and len(variant) == 2
                and (
                    can_specialize_type(variant[0])
                    if variant[1] is True
                    else (
                        isinstance(variant[0], tuple)
                        and all(
                            can_specialize_type(item) for item in variant[0]
                        )
                    )
                )
                for variant in v
            )
        if isinstance(v, tuple) and len(v) == 2:
            if v[1] is True:
                return can_specialize_type(v[0])
            elif v[1] is False and isinstance(v[0], tuple):
                return all(can_specialize_type(item) for item in v[0])
    return False


def _calc_sample_count_ast(var_expr, sample_pct, prefix, fn_globals):
    """
    Generates AST expression computing sample count for any sampling mode.
    """
    if sample_pct in ("first", "last", 0):
        return ast.Constant(value=1)
    if sample_pct == "bookend":
        return ast.Constant(value=2)
    if sample_pct == "bookend_plus":
        return ast.Constant(value=3)
    if sample_pct == "log":
        fn_globals["_log_count"] = _log_count
        return ast.Call(
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
    fn_globals[f"{prefix}_pct"] = sample_pct
    return ast.Call(
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
                        right=ast.Name(id=f"{prefix}_pct", ctx=ast.Load()),
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


def _generate_variant_test_ast(
    var_expr, k, variant, sample_pct, prefix, fn_globals
):
    """
    Generates a boolean AST expression evaluating whether var_expr matches variant schema.
    """
    if k in (list, set):
        if is_simple_type(variant):
            tt = tuple(variant.keys())
            t0 = tt[0]
            if k is set:
                if sample_pct == 100:
                    if _cpp is not None:
                        if len(tt) == 1:
                            fn_name = f"_cpp_val_set_s_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_set_single
                            fn_globals[f"{prefix}_t0"] = t0
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_t0", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                        else:
                            fn_name = f"_cpp_val_set_u_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_set_union
                            fn_globals[f"{prefix}_tt"] = tt
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_tt", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                    else:
                        fn_name = f"_py_val_set_s_{prefix}"
                        if len(tt) == 1:
                            fn_globals[fn_name] = lambda obj, t=t0: all(
                                type(x) is t or isinstance(x, t) for x in obj
                            )
                        else:
                            fn_globals[fn_name] = lambda obj, types=tt: all(
                                type(x) in types or isinstance(x, types)
                                for x in obj
                            )
                        return ast.Call(
                            func=ast.Name(id=fn_name, ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        )
                else:
                    count_ast = _calc_sample_count_ast(
                        var_expr, sample_pct, prefix, fn_globals
                    )
                    if _cpp is not None:
                        if len(tt) == 1:
                            fn_name = f"_cpp_val_set_samp_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_set_sample
                            fn_globals[f"{prefix}_t0"] = t0
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_t0", ctx=ast.Load()),
                                    count_ast,
                                ],
                                keywords=[],
                            )
                        else:
                            fn_name = f"_cpp_val_set_sampu_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_set_sample_union
                            fn_globals[f"{prefix}_tt"] = tt
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_tt", ctx=ast.Load()),
                                    count_ast,
                                ],
                                keywords=[],
                            )
                    else:
                        fn_globals["_islice"] = islice
                        fn_name = f"_py_val_set_samp_{prefix}"
                        if len(tt) == 1:
                            fn_globals[fn_name] = lambda obj, cnt, t=t0: all(
                                type(x) is t or isinstance(x, t)
                                for x in islice(obj, cnt)
                            )
                        else:
                            fn_globals[fn_name] = (
                                lambda obj, cnt, types=tt: all(
                                    type(x) in types or isinstance(x, types)
                                    for x in islice(obj, cnt)
                                )
                            )
                        return ast.Call(
                            func=ast.Name(id=fn_name, ctx=ast.Load()),
                            args=[var_expr, count_ast],
                            keywords=[],
                        )
            elif k is list:
                if sample_pct == 100:
                    if _cpp is not None:
                        if len(tt) == 1:
                            fn_name = f"_cpp_val_list_s_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_list_single
                            fn_globals[f"{prefix}_t0"] = t0
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_t0", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                        else:
                            fn_name = f"_cpp_val_list_u_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_list_union
                            fn_globals[f"{prefix}_tt"] = tt
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_tt", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                    else:
                        fn_name = f"_py_val_list_s_{prefix}"
                        if len(tt) == 1:
                            fn_globals[fn_name] = lambda obj, t=t0: all(
                                type(x) is t or isinstance(x, t) for x in obj
                            )
                        else:
                            fn_globals[fn_name] = lambda obj, types=tt: all(
                                type(x) in types or isinstance(x, types)
                                for x in obj
                            )
                        return ast.Call(
                            func=ast.Name(id=fn_name, ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        )
                elif sample_pct == "first":
                    if _cpp is not None:
                        if len(tt) == 1:
                            fn_name = f"_cpp_val_list_f_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_list_first
                            fn_globals[f"{prefix}_t0"] = t0
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_t0", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                        else:
                            fn_name = f"_cpp_val_list_fu_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_list_first_union
                            fn_globals[f"{prefix}_tt"] = tt
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_tt", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                    else:
                        fn_name = f"_py_val_first_{prefix}"
                        if len(tt) == 1:
                            fn_globals[fn_name] = (
                                lambda obj, t=t0: len(obj) == 0
                                or type(obj[0]) is t
                                or isinstance(obj[0], t)
                            )
                        else:
                            fn_globals[fn_name] = (
                                lambda obj, types=tt: len(obj) == 0
                                or type(obj[0]) in types
                                or isinstance(obj[0], types)
                            )
                        return ast.Call(
                            func=ast.Name(id=fn_name, ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        )
                elif sample_pct == "last":
                    if _cpp is not None:
                        if len(tt) == 1:
                            fn_name = f"_cpp_val_list_l_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_list_last
                            fn_globals[f"{prefix}_t0"] = t0
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_t0", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                        else:
                            fn_name = f"_cpp_val_list_lu_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_list_last_union
                            fn_globals[f"{prefix}_tt"] = tt
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_tt", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                    else:
                        fn_name = f"_py_val_last_{prefix}"
                        if len(tt) == 1:
                            fn_globals[fn_name] = lambda obj, t=t0: len(
                                obj
                            ) == 0 or (
                                type(obj[-1]) is t or isinstance(obj[-1], t)
                            )
                        else:
                            fn_globals[fn_name] = lambda obj, types=tt: len(
                                obj
                            ) == 0 or (
                                type(obj[-1]) in types
                                or isinstance(obj[-1], types)
                            )
                        return ast.Call(
                            func=ast.Name(id=fn_name, ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        )
                elif sample_pct == "bookend":
                    if _cpp is not None:
                        if len(tt) == 1:
                            fn_name = f"_cpp_val_list_bk_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_list_bookend
                            fn_globals[f"{prefix}_t0"] = t0
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_t0", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                        else:
                            fn_name = f"_cpp_val_list_bku_{prefix}"
                            fn_globals[fn_name] = (
                                _cpp.validate_list_bookend_union
                            )
                            fn_globals[f"{prefix}_tt"] = tt
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_tt", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                    else:
                        fn_name = f"_py_val_bk_{prefix}"
                        if len(tt) == 1:
                            fn_globals[fn_name] = lambda obj, t=t0: (
                                len(obj) == 0
                                or (
                                    (type(obj[0]) is t or isinstance(obj[0], t))
                                    and (
                                        len(obj) == 1
                                        or type(obj[-1]) is t
                                        or isinstance(obj[-1], t)
                                    )
                                )
                            )
                        else:
                            fn_globals[fn_name] = lambda obj, types=tt: (
                                len(obj) == 0
                                or (
                                    (
                                        type(obj[0]) in types
                                        or isinstance(obj[0], types)
                                    )
                                    and (
                                        len(obj) == 1
                                        or type(obj[-1]) in types
                                        or isinstance(obj[-1], types)
                                    )
                                )
                            )
                        return ast.Call(
                            func=ast.Name(id=fn_name, ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        )
                elif sample_pct == "bookend_plus":
                    if _cpp is not None:
                        if len(tt) == 1:
                            fn_name = f"_cpp_val_list_bkp_{prefix}"
                            fn_globals[fn_name] = (
                                _cpp.validate_list_bookend_plus
                            )
                            fn_globals[f"{prefix}_t0"] = t0
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_t0", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                        else:
                            fn_name = f"_cpp_val_list_bkpu_{prefix}"
                            fn_globals[fn_name] = (
                                _cpp.validate_list_bookend_plus_union
                            )
                            fn_globals[f"{prefix}_tt"] = tt
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_tt", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                    else:
                        fn_name = f"_py_val_bkp_{prefix}"
                        if len(tt) == 1:
                            fn_globals[fn_name] = lambda obj, t=t0: (
                                len(obj) == 0
                                or (
                                    (type(obj[0]) is t or isinstance(obj[0], t))
                                    and (
                                        len(obj) == 1
                                        or type(obj[-1]) is t
                                        or isinstance(obj[-1], t)
                                    )
                                    and (
                                        len(obj) <= 2
                                        or type(
                                            obj[
                                                random.randrange(
                                                    1, len(obj) - 1
                                                )
                                            ]
                                        )
                                        is t
                                        or isinstance(
                                            obj[
                                                random.randrange(
                                                    1, len(obj) - 1
                                                )
                                            ],
                                            t,
                                        )
                                    )
                                )
                            )
                        else:
                            fn_globals[fn_name] = lambda obj, types=tt: (
                                len(obj) == 0
                                or (
                                    (
                                        type(obj[0]) in types
                                        or isinstance(obj[0], types)
                                    )
                                    and (
                                        len(obj) == 1
                                        or type(obj[-1]) in types
                                        or isinstance(obj[-1], types)
                                    )
                                    and (
                                        len(obj) <= 2
                                        or type(
                                            obj[
                                                random.randrange(
                                                    1, len(obj) - 1
                                                )
                                            ]
                                        )
                                        in types
                                        or isinstance(
                                            obj[
                                                random.randrange(
                                                    1, len(obj) - 1
                                                )
                                            ],
                                            types,
                                        )
                                    )
                                )
                            )
                        return ast.Call(
                            func=ast.Name(id=fn_name, ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        )
                else:
                    count_ast = _calc_sample_count_ast(
                        var_expr, sample_pct, prefix, fn_globals
                    )
                    if _cpp is not None:
                        if len(tt) == 1:
                            fn_name = f"_cpp_val_list_samp_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_list_sample
                            fn_globals[f"{prefix}_t0"] = t0
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_t0", ctx=ast.Load()),
                                    count_ast,
                                ],
                                keywords=[],
                            )
                        else:
                            fn_name = f"_cpp_val_list_sampu_{prefix}"
                            fn_globals[fn_name] = (
                                _cpp.validate_list_sample_union
                            )
                            fn_globals[f"{prefix}_tt"] = tt
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_tt", ctx=ast.Load()),
                                    count_ast,
                                ],
                                keywords=[],
                            )
                    else:
                        fn_name = f"_py_val_sample_{prefix}"
                        if len(tt) == 1:
                            fn_globals[fn_name] = lambda obj, cnt, t=t0: all(
                                type(obj[idx]) is t or isinstance(obj[idx], t)
                                for idx in range(min(len(obj), cnt))
                            )
                        else:
                            fn_globals[fn_name] = (
                                lambda obj, cnt, types=tt: all(
                                    type(obj[idx]) in types
                                    or isinstance(obj[idx], types)
                                    for idx in range(min(len(obj), cnt))
                                )
                            )
                        return ast.Call(
                            func=ast.Name(id=fn_name, ctx=ast.Load()),
                            args=[var_expr, count_ast],
                            keywords=[],
                        )

    elif k is dict:
        key_exp, val_exp = variant
        if is_simple_type(key_exp) and is_simple_type(val_exp):
            k_tt = tuple(key_exp.keys())
            v_tt = tuple(val_exp.keys())
            if sample_pct == 100:
                if _cpp is not None:
                    if len(k_tt) == 1 and len(v_tt) == 1:
                        fn_name = f"_cpp_val_dict_s_{prefix}"
                        fn_globals[fn_name] = _cpp.validate_dict_single
                        fn_globals[f"{prefix}_kt0"] = k_tt[0]
                        fn_globals[f"{prefix}_vt0"] = v_tt[0]
                        return ast.Call(
                            func=ast.Name(id=fn_name, ctx=ast.Load()),
                            args=[
                                var_expr,
                                ast.Name(id=f"{prefix}_kt0", ctx=ast.Load()),
                                ast.Name(id=f"{prefix}_vt0", ctx=ast.Load()),
                            ],
                            keywords=[],
                        )
                    else:
                        fn_name = f"_cpp_val_dict_u_{prefix}"
                        fn_globals[fn_name] = _cpp.validate_dict_unions
                        fn_globals[f"{prefix}_ktt"] = k_tt
                        fn_globals[f"{prefix}_vtt"] = v_tt
                        return ast.Call(
                            func=ast.Name(id=fn_name, ctx=ast.Load()),
                            args=[
                                var_expr,
                                ast.Name(id=f"{prefix}_ktt", ctx=ast.Load()),
                                ast.Name(id=f"{prefix}_vtt", ctx=ast.Load()),
                            ],
                            keywords=[],
                        )
                else:
                    fn_name = f"_py_val_dict_s_{prefix}"
                    if len(k_tt) == 1 and len(v_tt) == 1:
                        kt0, vt0 = k_tt[0], v_tt[0]
                        fn_globals[fn_name] = lambda obj, kt=kt0, vt=vt0: all(
                            (type(k) is kt or isinstance(k, kt))
                            and (type(v) is vt or isinstance(v, vt))
                            for k, v in obj.items()
                        )
                    else:
                        fn_globals[fn_name] = (
                            lambda obj, ktypes=k_tt, vtypes=v_tt: all(
                                (type(k) in ktypes or isinstance(k, ktypes))
                                and (type(v) in vtypes or isinstance(v, vtypes))
                                for k, v in obj.items()
                            )
                        )
                    return ast.Call(
                        func=ast.Name(id=fn_name, ctx=ast.Load()),
                        args=[var_expr],
                        keywords=[],
                    )
            elif sample_pct == "last":
                fn_name = f"_py_val_dict_last_{prefix}"
                if len(k_tt) == 1 and len(v_tt) == 1:
                    kt0, vt0 = k_tt[0], v_tt[0]
                    fn_globals[fn_name] = lambda obj, kt=kt0, vt=vt0: bool(
                        obj
                    ) and (
                        lambda k: (type(k) is kt or isinstance(k, kt))
                        and (type(obj[k]) is vt or isinstance(obj[k], vt))
                    )(
                        next(reversed(obj))
                    )
                else:
                    fn_globals[
                        fn_name
                    ] = lambda obj, ktypes=k_tt, vtypes=v_tt: bool(obj) and (
                        lambda k: (type(k) in ktypes or isinstance(k, ktypes))
                        and (
                            type(obj[k]) in vtypes or isinstance(obj[k], vtypes)
                        )
                    )(
                        next(reversed(obj))
                    )
                return ast.Call(
                    func=ast.Name(id=fn_name, ctx=ast.Load()),
                    args=[var_expr],
                    keywords=[],
                )
            else:
                count_ast = _calc_sample_count_ast(
                    var_expr, sample_pct, prefix, fn_globals
                )
                if _cpp is not None:
                    if len(k_tt) == 1 and len(v_tt) == 1:
                        fn_name = f"_cpp_val_dict_samp_{prefix}"
                        fn_globals[fn_name] = _cpp.validate_dict_sample
                        fn_globals[f"{prefix}_kt0"] = k_tt[0]
                        fn_globals[f"{prefix}_vt0"] = v_tt[0]
                        return ast.Call(
                            func=ast.Name(id=fn_name, ctx=ast.Load()),
                            args=[
                                var_expr,
                                ast.Name(id=f"{prefix}_kt0", ctx=ast.Load()),
                                ast.Name(id=f"{prefix}_vt0", ctx=ast.Load()),
                                count_ast,
                            ],
                            keywords=[],
                        )
                    else:
                        fn_name = f"_cpp_val_dict_sampu_{prefix}"
                        fn_globals[fn_name] = _cpp.validate_dict_sample_unions
                        fn_globals[f"{prefix}_ktt"] = k_tt
                        fn_globals[f"{prefix}_vtt"] = v_tt
                        return ast.Call(
                            func=ast.Name(id=fn_name, ctx=ast.Load()),
                            args=[
                                var_expr,
                                ast.Name(id=f"{prefix}_ktt", ctx=ast.Load()),
                                ast.Name(id=f"{prefix}_vtt", ctx=ast.Load()),
                                count_ast,
                            ],
                            keywords=[],
                        )
                else:
                    fn_globals["_islice"] = islice
                    fn_name = f"_py_val_dict_samp_{prefix}"
                    if len(k_tt) == 1 and len(v_tt) == 1:
                        kt0, vt0 = k_tt[0], v_tt[0]
                        fn_globals[fn_name] = (
                            lambda obj, cnt, kt=kt0, vt=vt0: all(
                                (type(k) is kt or isinstance(k, kt))
                                and (type(v) is vt or isinstance(v, vt))
                                for k, v in islice(obj.items(), cnt)
                            )
                        )
                    else:
                        fn_globals[fn_name] = (
                            lambda obj, cnt, ktypes=k_tt, vtypes=v_tt: all(
                                (type(k) in ktypes or isinstance(k, ktypes))
                                and (type(v) in vtypes or isinstance(v, vtypes))
                                for k, v in islice(obj.items(), cnt)
                            )
                        )
                    return ast.Call(
                        func=ast.Name(id=fn_name, ctx=ast.Load()),
                        args=[var_expr, count_ast],
                        keywords=[],
                    )

    elif k is tuple:
        expected_args, is_ellipsis = variant
        if is_ellipsis:
            if is_simple_type(expected_args):
                tt = tuple(expected_args.keys())
                t0 = tt[0]
                if sample_pct == 100:
                    if _cpp is not None:
                        if len(tt) == 1:
                            fn_name = f"_cpp_val_tup_s_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_tuple_single
                            fn_globals[f"{prefix}_t0"] = t0
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_t0", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                        else:
                            fn_name = f"_cpp_val_tup_u_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_tuple_union
                            fn_globals[f"{prefix}_tt"] = tt
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_tt", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                    else:
                        fn_name = f"_py_val_tup_s_{prefix}"
                        if len(tt) == 1:
                            fn_globals[fn_name] = lambda obj, t=t0: all(
                                type(x) is t or isinstance(x, t) for x in obj
                            )
                        else:
                            fn_globals[fn_name] = lambda obj, types=tt: all(
                                type(x) in types or isinstance(x, types)
                                for x in obj
                            )
                        return ast.Call(
                            func=ast.Name(id=fn_name, ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        )
                elif sample_pct == "first":
                    if _cpp is not None:
                        if len(tt) == 1:
                            fn_name = f"_cpp_val_tup_f_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_tuple_first
                            fn_globals[f"{prefix}_t0"] = t0
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_t0", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                        else:
                            fn_name = f"_cpp_val_tup_fu_{prefix}"
                            fn_globals[fn_name] = (
                                _cpp.validate_tuple_first_union
                            )
                            fn_globals[f"{prefix}_tt"] = tt
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_tt", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                    else:
                        fn_name = f"_py_val_tup_f_{prefix}"
                        if len(tt) == 1:
                            fn_globals[fn_name] = (
                                lambda obj, t=t0: len(obj) == 0
                                or type(obj[0]) is t
                                or isinstance(obj[0], t)
                            )
                        else:
                            fn_globals[fn_name] = (
                                lambda obj, types=tt: len(obj) == 0
                                or type(obj[0]) in types
                                or isinstance(obj[0], types)
                            )
                        return ast.Call(
                            func=ast.Name(id=fn_name, ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        )
                elif sample_pct == "last":
                    if _cpp is not None:
                        if len(tt) == 1:
                            fn_name = f"_cpp_val_tup_l_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_tuple_last
                            fn_globals[f"{prefix}_t0"] = t0
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_t0", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                        else:
                            fn_name = f"_cpp_val_tup_lu_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_tuple_last_union
                            fn_globals[f"{prefix}_tt"] = tt
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_tt", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                    else:
                        fn_name = f"_py_val_tup_l_{prefix}"
                        if len(tt) == 1:
                            fn_globals[fn_name] = (
                                lambda obj, t=t0: len(obj) == 0
                                or type(obj[-1]) is t
                                or isinstance(obj[-1], t)
                            )
                        else:
                            fn_globals[fn_name] = (
                                lambda obj, types=tt: len(obj) == 0
                                or type(obj[-1]) in types
                                or isinstance(obj[-1], types)
                            )
                        return ast.Call(
                            func=ast.Name(id=fn_name, ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        )
                elif sample_pct == "bookend":
                    if _cpp is not None:
                        if len(tt) == 1:
                            fn_name = f"_cpp_val_tup_bk_{prefix}"
                            fn_globals[fn_name] = _cpp.validate_tuple_bookend
                            fn_globals[f"{prefix}_t0"] = t0
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_t0", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                        else:
                            fn_name = f"_cpp_val_tup_bku_{prefix}"
                            fn_globals[fn_name] = (
                                _cpp.validate_tuple_bookend_union
                            )
                            fn_globals[f"{prefix}_tt"] = tt
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_tt", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                    else:
                        fn_name = f"_py_val_tup_bk_{prefix}"
                        if len(tt) == 1:
                            fn_globals[fn_name] = lambda obj, t=t0: len(
                                obj
                            ) == 0 or (
                                (type(obj[0]) is t or isinstance(obj[0], t))
                                and (
                                    len(obj) == 1
                                    or type(obj[-1]) is t
                                    or isinstance(obj[-1], t)
                                )
                            )
                        else:
                            fn_globals[fn_name] = lambda obj, types=tt: len(
                                obj
                            ) == 0 or (
                                (
                                    type(obj[0]) in types
                                    or isinstance(obj[0], types)
                                )
                                and (
                                    len(obj) == 1
                                    or type(obj[-1]) in types
                                    or isinstance(obj[-1], types)
                                )
                            )
                        return ast.Call(
                            func=ast.Name(id=fn_name, ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        )
                elif sample_pct == "bookend_plus":
                    if _cpp is not None:
                        if len(tt) == 1:
                            fn_name = f"_cpp_val_tup_bkp_{prefix}"
                            fn_globals[fn_name] = (
                                _cpp.validate_tuple_bookend_plus
                            )
                            fn_globals[f"{prefix}_t0"] = t0
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_t0", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                        else:
                            fn_name = f"_cpp_val_tup_bkpu_{prefix}"
                            fn_globals[fn_name] = (
                                _cpp.validate_tuple_bookend_plus_union
                            )
                            fn_globals[f"{prefix}_tt"] = tt
                            return ast.Call(
                                func=ast.Name(id=fn_name, ctx=ast.Load()),
                                args=[
                                    var_expr,
                                    ast.Name(id=f"{prefix}_tt", ctx=ast.Load()),
                                ],
                                keywords=[],
                            )
                    else:
                        fn_name = f"_py_val_tup_bkp_{prefix}"
                        if len(tt) == 1:
                            fn_globals[fn_name] = lambda obj, t=t0: len(
                                obj
                            ) == 0 or (
                                (type(obj[0]) is t or isinstance(obj[0], t))
                                and (
                                    len(obj) == 1
                                    or type(obj[-1]) is t
                                    or isinstance(obj[-1], t)
                                )
                                and (
                                    len(obj) <= 2
                                    or type(
                                        obj[random.randrange(1, len(obj) - 1)]
                                    )
                                    is t
                                    or isinstance(
                                        obj[random.randrange(1, len(obj) - 1)],
                                        t,
                                    )
                                )
                            )
                        else:
                            fn_globals[fn_name] = lambda obj, types=tt: len(
                                obj
                            ) == 0 or (
                                (
                                    type(obj[0]) in types
                                    or isinstance(obj[0], types)
                                )
                                and (
                                    len(obj) == 1
                                    or type(obj[-1]) in types
                                    or isinstance(obj[-1], types)
                                )
                                and (
                                    len(obj) <= 2
                                    or type(
                                        obj[random.randrange(1, len(obj) - 1)]
                                    )
                                    in types
                                    or isinstance(
                                        obj[random.randrange(1, len(obj) - 1)],
                                        types,
                                    )
                                )
                            )
                        return ast.Call(
                            func=ast.Name(id=fn_name, ctx=ast.Load()),
                            args=[var_expr],
                            keywords=[],
                        )
        else:
            if all(is_simple_type(a) and len(a) == 1 for a in expected_args):
                types_tuple = tuple(tuple(a.keys())[0] for a in expected_args)
                if _cpp is not None:
                    fn_name = f"_cpp_val_tup_f_{prefix}"
                    fn_globals[fn_name] = _cpp.validate_tuple_fixed
                    fn_globals[f"{prefix}_types"] = types_tuple
                    return ast.Call(
                        func=ast.Name(id=fn_name, ctx=ast.Load()),
                        args=[
                            var_expr,
                            ast.Name(id=f"{prefix}_types", ctx=ast.Load()),
                        ],
                        keywords=[],
                    )
                else:
                    fn_name = f"_py_val_tup_f_{prefix}"
                    fn_globals[fn_name] = lambda obj, types=types_tuple: len(
                        obj
                    ) == len(types) and all(
                        type(x) is t or isinstance(x, t)
                        for x, t in zip(obj, types)
                    )
                    return ast.Call(
                        func=ast.Name(id=fn_name, ctx=ast.Load()),
                        args=[var_expr],
                        keywords=[],
                    )

    # Fallback to dynamic check function
    fn_name = f"_py_val_custom_var_{prefix}"
    fn_globals[fn_name] = (
        lambda obj, o_type=k, var=variant: _validate_variant_fallback(
            obj, o_type, var, sample_pct
        )
    )
    return ast.Call(
        func=ast.Name(id=fn_name, ctx=ast.Load()),
        args=[var_expr],
        keywords=[],
    )


def _validate_variant_fallback(obj, obj_type, variant, sample_pct):
    from .enforcer import FunctionMethodEnforcer

    enforcer = FunctionMethodEnforcer(
        lambda: None, __iterable_sample_pct__=sample_pct
    )
    return enforcer.__validate_collection_variant__(obj, obj_type, variant)


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
                args=[var_expr, ast.Name(id=types_name, ctx=ast.Load())],
                keywords=[],
            ),
        )

    return [ast.If(test=test, body=[fail_call], orelse=[])]


def _generate_uninitialized_class_check(
    var_expr, exp, fail_call, fn_globals, prefix
):
    target_classes = []
    has_bare_type = False
    for k in exp.keys():
        if k in (type, Type):
            has_bare_type = True
        elif getattr(k, "__origin__", None) in (type, Type):
            args = getattr(k, "__args__", ())
            if args:
                target_classes.extend(args)
            else:
                has_bare_type = True
        elif isinstance(k, type):
            target_classes.append(k)

    is_type_check = ast.Call(
        func=ast.Name(id="isinstance", ctx=ast.Load()),
        args=[var_expr, ast.Name(id="type", ctx=ast.Load())],
        keywords=[],
    )

    if has_bare_type or object in target_classes:
        test = ast.UnaryOp(op=ast.Not(), operand=is_type_check)
    elif len(target_classes) == 1:
        fn_globals[f"{prefix}_tgt_cls"] = target_classes[0]
        match_check = ast.Compare(
            left=var_expr,
            ops=[ast.Is()],
            comparators=[ast.Name(id=f"{prefix}_tgt_cls", ctx=ast.Load())],
        )
        test = ast.UnaryOp(
            op=ast.Not(),
            operand=ast.BoolOp(
                op=ast.And(), values=[is_type_check, match_check]
            ),
        )
    else:
        fn_globals[f"{prefix}_tgt_classes"] = tuple(target_classes)
        match_check = ast.Compare(
            left=var_expr,
            ops=[ast.In()],
            comparators=[ast.Name(id=f"{prefix}_tgt_classes", ctx=ast.Load())],
        )
        test = ast.UnaryOp(
            op=ast.Not(),
            operand=ast.BoolOp(
                op=ast.And(), values=[is_type_check, match_check]
            ),
        )

    return [ast.If(test=test, body=[fail_call], orelse=[])]


def _generate_callable_check(var_expr, fail_call):
    test = ast.UnaryOp(
        op=ast.Not(),
        operand=ast.Call(
            func=ast.Name(id="callable", ctx=ast.Load()),
            args=[var_expr],
            keywords=[],
        ),
    )
    return [ast.If(test=test, body=[fail_call], orelse=[])]


def _generate_typeddict_check(
    var_expr, exp, fail_call, fn_globals, prefix, sample_pct
):
    td_info = exp["__extra__"]["__typeddict__"]
    req_keys = td_info["required"]
    fields = td_info["fields"]

    stmts = []
    # 1. Check outer type is dict
    stmts.append(_outer_type_guard(var_expr, "dict", fail_call))

    # Partition fields into required and optional
    req_fields = [(fk, fexp) for fk, fexp in fields.items() if fk in req_keys]
    opt_fields = [
        (fk, fexp) for fk, fexp in fields.items() if fk not in req_keys
    ]

    # Handle required fields: retrieve in a single try-except block
    if req_fields:
        req_assigns = []
        req_checks = []
        for i, (fk, fexp) in enumerate(req_fields):
            clean_fk = "".join(c if c.isalnum() else "_" for c in fk)
            val_id = f"{prefix}_req_{i}_{clean_fk}"
            req_assigns.append(
                ast.Assign(
                    targets=[ast.Name(id=val_id, ctx=ast.Store())],
                    value=ast.Subscript(
                        value=var_expr,
                        slice=ast.Constant(value=fk),
                        ctx=ast.Load(),
                    ),
                )
            )
            val_expr = ast.Name(id=val_id, ctx=ast.Load())
            field_checks = generate_type_check_ast(
                val_expr,
                fexp,
                fail_call,
                fn_globals,
                val_id,
                sample_pct,
            )
            req_checks.extend(field_checks)

        stmts.append(
            ast.Try(
                body=req_assigns,
                handlers=[
                    ast.ExceptHandler(
                        type=ast.Name(id="KeyError", ctx=ast.Load()),
                        name=None,
                        body=[fail_call],
                    )
                ],
                orelse=[],
                finalbody=[],
            )
        )
        stmts.extend(req_checks)

    # Handle optional fields: use .get(fk, _sentinel)
    if opt_fields:
        sentinel_name = f"{prefix}_sentinel"
        fn_globals[sentinel_name] = object()
        for i, (fk, fexp) in enumerate(opt_fields):
            clean_fk = "".join(c if c.isalnum() else "_" for c in fk)
            val_id = f"{prefix}_opt_{i}_{clean_fk}"
            assign_opt = ast.Assign(
                targets=[ast.Name(id=val_id, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=var_expr,
                        attr="get",
                        ctx=ast.Load(),
                    ),
                    args=[
                        ast.Constant(value=fk),
                        ast.Name(id=sentinel_name, ctx=ast.Load()),
                    ],
                    keywords=[],
                ),
            )
            val_expr = ast.Name(id=val_id, ctx=ast.Load())
            field_checks = generate_type_check_ast(
                val_expr,
                fexp,
                fail_call,
                fn_globals,
                val_id,
                sample_pct,
            )
            cond_check = ast.If(
                test=ast.Compare(
                    left=val_expr,
                    ops=[ast.IsNot()],
                    comparators=[ast.Name(id=sentinel_name, ctx=ast.Load())],
                ),
                body=field_checks,
                orelse=[],
            )
            stmts.extend([assign_opt, cond_check])

    return stmts


def _outer_type_guard(var_expr, type_name, fail_stmt):
    """
    Generates class comparison and isinstance fallback guard for containers.
    """
    outer_class_test = ast.Compare(
        left=ast.Attribute(value=var_expr, attr="__class__", ctx=ast.Load()),
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
    return ast.If(
        test=ast.BoolOp(
            op=ast.And(), values=[outer_class_test, outer_isinstance_test]
        ),
        body=[fail_stmt],
        orelse=[],
    )


def _emit_cpp_call(fn_name, fn_obj, args_list, fail_stmt, fn_globals):
    """
    Registers a C++ function and emits an AST If check calling it.
    """
    fn_globals[fn_name] = fn_obj
    call_args = []
    for arg_name, arg_val in args_list:
        if arg_name is None:
            call_args.append(arg_val)
        else:
            fn_globals[arg_name] = arg_val
            call_args.append(ast.Name(id=arg_name, ctx=ast.Load()))
    return [
        ast.If(
            test=ast.UnaryOp(
                op=ast.Not(),
                operand=ast.Call(
                    func=ast.Name(id=fn_name, ctx=ast.Load()),
                    args=call_args,
                    keywords=[],
                ),
            ),
            body=[fail_stmt],
            orelse=[],
        )
    ]


def _emit_strided_sequence_check(
    var_expr, loop_var_id, sub_checks, count_expr, prefix
):
    """
    Generates strided AST index checking (first, last, and strided steps) for sequences.
    """
    short_loop = ast.For(
        target=ast.Name(id=loop_var_id, ctx=ast.Store()),
        iter=var_expr,
        body=sub_checks,
        orelse=[],
    )
    assign_0 = ast.Assign(
        targets=[ast.Name(id=loop_var_id, ctx=ast.Store())],
        value=ast.Subscript(
            value=var_expr, slice=ast.Constant(value=0), ctx=ast.Load()
        ),
    )
    assign_last = ast.Assign(
        targets=[ast.Name(id=loop_var_id, ctx=ast.Store())],
        value=ast.Subscript(
            value=var_expr, slice=ast.Constant(value=-1), ctx=ast.Load()
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
        [assign_0] + sub_checks + [assign_last] + sub_checks + [range_loop]
    )
    return ast.If(
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


def _emit_set_superset_fallback(
    var_expr, sub_exp, loop_var_id, sub_checks, fail_stmt, prefix, fn_globals
):
    """
    Generates fast frozenset superset check fallback for pure Python mode.
    """
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
                    value=ast.Name(id=f"{prefix}_elem_set", ctx=ast.Load()),
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
    return [
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

    if is_self_type(exp):
        first_name = fn_globals.get("__enf_first_param_name")
        if first_name:
            self_inst_cls = ast.Attribute(
                value=ast.Name(id=first_name, ctx=ast.Load()),
                attr="__class__",
                ctx=ast.Load(),
            )
            test = ast.UnaryOp(
                op=ast.Not(),
                operand=ast.Call(
                    func=ast.Name(id="isinstance", ctx=ast.Load()),
                    args=[var_expr, self_inst_cls],
                    keywords=[],
                ),
            )
            return [ast.If(test=test, body=[fail_call], orelse=[])]
        return [fail_call]

    if is_callable_type(exp):
        return _generate_callable_check(var_expr, fail_call)

    if is_uninitialized_class_type(exp):
        return _generate_uninitialized_class_check(
            var_expr, exp, fail_call, fn_globals, prefix
        )

    if is_typeddict_type(exp):
        return _generate_typeddict_check(
            var_expr, exp, fail_call, fn_globals, prefix, sample_pct
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
        outer_type_guard = _outer_type_guard(var_expr, type_name, fail_stmt)

        if isinstance(v, list):
            variant_tests = [
                _generate_variant_test_ast(
                    var_expr, k, var, sample_pct, f"{prefix}_v{i}", fn_globals
                )
                for i, var in enumerate(v)
            ]
            content_check = ast.If(
                test=ast.UnaryOp(
                    op=ast.Not(),
                    operand=ast.BoolOp(op=ast.Or(), values=variant_tests),
                ),
                body=[fail_stmt],
                orelse=[],
            )
            return [outer_type_guard, content_check]

        sub_exp = v
        elem_is_simple = is_simple_type(sub_exp)

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

        if k is set:
            if sample_pct == 100:
                if _cpp is not None and elem_is_simple:
                    if len(sub_exp) == 1:
                        content_check = _emit_cpp_call(
                            "_cpp_val_set_s",
                            _cpp.validate_set_single,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_t0", tuple(sub_exp.keys())[0]),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                    else:
                        content_check = _emit_cpp_call(
                            "_cpp_val_set_u",
                            _cpp.validate_set_union,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_types", tuple(sub_exp.keys())),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                elif elem_is_simple:
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
                        content_check = _emit_set_superset_fallback(
                            var_expr,
                            sub_exp,
                            loop_var_id,
                            sub_checks,
                            fail_stmt,
                            prefix,
                            fn_globals,
                        )
                else:
                    content_check = [
                        ast.For(
                            target=ast.Name(id=loop_var_id, ctx=ast.Store()),
                            iter=var_expr,
                            body=sub_checks,
                            orelse=[],
                        )
                    ]
            elif sample_pct == 0:
                rand_call = ast.Call(
                    func=ast.Name(id="_random_set_item", ctx=ast.Load()),
                    args=[var_expr],
                    keywords=[],
                )
                content_check = ast.If(
                    test=var_expr,
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id=loop_var_id, ctx=ast.Store())],
                            value=rand_call,
                        )
                    ]
                    + sub_checks,
                    orelse=[],
                )
            else:
                count_expr = _calc_sample_count_ast(
                    var_expr, sample_pct, prefix, fn_globals
                )
                if _cpp is not None and elem_is_simple:
                    if len(sub_exp) == 1:
                        content_check = _emit_cpp_call(
                            "_cpp_val_set_samp",
                            _cpp.validate_set_sample,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_t0", tuple(sub_exp.keys())[0]),
                                (None, count_expr),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                    else:
                        content_check = _emit_cpp_call(
                            "_cpp_val_set_samp_u",
                            _cpp.validate_set_sample_union,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_types", tuple(sub_exp.keys())),
                                (None, count_expr),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                else:
                    fn_globals["_islice"] = islice
                    content_check = ast.For(
                        target=ast.Name(id=loop_var_id, ctx=ast.Store()),
                        iter=ast.Call(
                            func=ast.Name(id="_islice", ctx=ast.Load()),
                            args=[var_expr, count_expr],
                            keywords=[],
                        ),
                        body=sub_checks,
                        orelse=[],
                    )
        elif k is list:
            if sample_pct == "first":
                if _cpp is not None and elem_is_simple:
                    if len(sub_exp) == 1:
                        content_check = _emit_cpp_call(
                            "_cpp_val_list_first",
                            _cpp.validate_list_first,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_t0", tuple(sub_exp.keys())[0]),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                    else:
                        content_check = _emit_cpp_call(
                            "_cpp_val_list_first_u",
                            _cpp.validate_list_first_union,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_types", tuple(sub_exp.keys())),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                else:
                    content_check = ast.If(
                        test=var_expr,
                        body=[
                            ast.Assign(
                                targets=[
                                    ast.Name(id=loop_var_id, ctx=ast.Store())
                                ],
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
                if _cpp is not None and elem_is_simple:
                    if len(sub_exp) == 1:
                        content_check = _emit_cpp_call(
                            "_cpp_val_list_last",
                            _cpp.validate_list_last,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_t0", tuple(sub_exp.keys())[0]),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                    else:
                        content_check = _emit_cpp_call(
                            "_cpp_val_list_last_u",
                            _cpp.validate_list_last_union,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_types", tuple(sub_exp.keys())),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                else:
                    content_check = ast.If(
                        test=var_expr,
                        body=[
                            ast.Assign(
                                targets=[
                                    ast.Name(id=loop_var_id, ctx=ast.Store())
                                ],
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
            elif sample_pct == "bookend":
                if _cpp is not None and elem_is_simple:
                    if len(sub_exp) == 1:
                        content_check = _emit_cpp_call(
                            "_cpp_val_list_bookend",
                            _cpp.validate_list_bookend,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_t0", tuple(sub_exp.keys())[0]),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                    else:
                        content_check = _emit_cpp_call(
                            "_cpp_val_list_bookend_u",
                            _cpp.validate_list_bookend_union,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_types", tuple(sub_exp.keys())),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                else:
                    content_check = ast.If(
                        test=var_expr,
                        body=[
                            ast.Assign(
                                targets=[
                                    ast.Name(id=loop_var_id, ctx=ast.Store())
                                ],
                                value=ast.Subscript(
                                    value=var_expr,
                                    slice=ast.Constant(value=0),
                                    ctx=ast.Load(),
                                ),
                            )
                        ]
                        + sub_checks
                        + [
                            ast.If(
                                test=ast.Compare(
                                    left=ast.Call(
                                        func=ast.Name(id="len", ctx=ast.Load()),
                                        args=[var_expr],
                                        keywords=[],
                                    ),
                                    ops=[ast.Gt()],
                                    comparators=[ast.Constant(value=1)],
                                ),
                                body=[
                                    ast.Assign(
                                        targets=[
                                            ast.Name(
                                                id=loop_var_id, ctx=ast.Store()
                                            )
                                        ],
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
                        ],
                        orelse=[],
                    )
            elif sample_pct == "bookend_plus":
                if _cpp is not None and elem_is_simple:
                    if len(sub_exp) == 1:
                        content_check = _emit_cpp_call(
                            "_cpp_val_list_bookend_plus",
                            _cpp.validate_list_bookend_plus,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_t0", tuple(sub_exp.keys())[0]),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                    else:
                        content_check = _emit_cpp_call(
                            "_cpp_val_list_bookend_plus_u",
                            _cpp.validate_list_bookend_plus_union,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_types", tuple(sub_exp.keys())),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                else:
                    fn_globals["_randrange"] = random.randrange
                    content_check = ast.If(
                        test=var_expr,
                        body=[
                            ast.Assign(
                                targets=[
                                    ast.Name(id=loop_var_id, ctx=ast.Store())
                                ],
                                value=ast.Subscript(
                                    value=var_expr,
                                    slice=ast.Constant(value=0),
                                    ctx=ast.Load(),
                                ),
                            )
                        ]
                        + sub_checks
                        + [
                            ast.If(
                                test=ast.Compare(
                                    left=ast.Call(
                                        func=ast.Name(id="len", ctx=ast.Load()),
                                        args=[var_expr],
                                        keywords=[],
                                    ),
                                    ops=[ast.Gt()],
                                    comparators=[ast.Constant(value=1)],
                                ),
                                body=[
                                    ast.Assign(
                                        targets=[
                                            ast.Name(
                                                id=loop_var_id, ctx=ast.Store()
                                            )
                                        ],
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
                        ]
                        + [
                            ast.If(
                                test=ast.Compare(
                                    left=ast.Call(
                                        func=ast.Name(id="len", ctx=ast.Load()),
                                        args=[var_expr],
                                        keywords=[],
                                    ),
                                    ops=[ast.Gt()],
                                    comparators=[ast.Constant(value=2)],
                                ),
                                body=[
                                    ast.Assign(
                                        targets=[
                                            ast.Name(
                                                id=loop_var_id,
                                                ctx=ast.Store(),
                                            )
                                        ],
                                        value=ast.Subscript(
                                            value=var_expr,
                                            slice=ast.Call(
                                                func=ast.Name(
                                                    id="_randrange",
                                                    ctx=ast.Load(),
                                                ),
                                                args=[
                                                    ast.Constant(value=1),
                                                    ast.BinOp(
                                                        left=ast.Call(
                                                            func=ast.Name(
                                                                id="len",
                                                                ctx=ast.Load(),
                                                            ),
                                                            args=[var_expr],
                                                            keywords=[],
                                                        ),
                                                        op=ast.Sub(),
                                                        right=ast.Constant(
                                                            value=1
                                                        ),
                                                    ),
                                                ],
                                                keywords=[],
                                            ),
                                            ctx=ast.Load(),
                                        ),
                                    )
                                ]
                                + sub_checks,
                                orelse=[],
                            )
                        ],
                        orelse=[],
                    )
            elif sample_pct == 0:
                rand_call = ast.Call(
                    func=ast.Name(id="_choice", ctx=ast.Load()),
                    args=[var_expr],
                    keywords=[],
                )
                content_check = ast.If(
                    test=var_expr,
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id=loop_var_id, ctx=ast.Store())],
                            value=rand_call,
                        )
                    ]
                    + sub_checks,
                    orelse=[],
                )
            elif sample_pct == 100:
                if _cpp is not None and elem_is_simple:
                    if len(sub_exp) == 1:
                        content_check = _emit_cpp_call(
                            "_cpp_val_list_s",
                            _cpp.validate_list_single,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_t0", tuple(sub_exp.keys())[0]),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                    else:
                        content_check = _emit_cpp_call(
                            "_cpp_val_list_u",
                            _cpp.validate_list_union,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_types", tuple(sub_exp.keys())),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                elif (
                    _cpp is not None
                    and isinstance(sub_exp, dict)
                    and len(sub_exp) == 1
                    and list in sub_exp
                    and is_simple_type(sub_exp[list])
                    and len(sub_exp[list]) == 1
                ):
                    content_check = _emit_cpp_call(
                        "_cpp_val_list_list",
                        _cpp.validate_list_list,
                        [
                            (None, var_expr),
                            (f"{prefix}_el_t0", tuple(sub_exp[list].keys())[0]),
                        ],
                        fail_stmt,
                        fn_globals,
                    )
                elif (
                    _cpp is not None
                    and isinstance(sub_exp, dict)
                    and len(sub_exp) == 1
                    and dict in sub_exp
                    and isinstance(sub_exp[dict], (tuple, list))
                    and len(sub_exp[dict]) == 2
                    and is_simple_type(sub_exp[dict][0])
                    and is_simple_type(sub_exp[dict][1])
                    and len(sub_exp[dict][0]) == 1
                    and len(sub_exp[dict][1]) == 1
                ):
                    content_check = _emit_cpp_call(
                        "_cpp_val_list_dict",
                        _cpp.validate_list_dict,
                        [
                            (None, var_expr),
                            (
                                f"{prefix}_k_t0",
                                tuple(sub_exp[dict][0].keys())[0],
                            ),
                            (
                                f"{prefix}_v_t0",
                                tuple(sub_exp[dict][1].keys())[0],
                            ),
                        ],
                        fail_stmt,
                        fn_globals,
                    )
                elif (
                    _cpp is not None
                    and isinstance(sub_exp, dict)
                    and len(sub_exp) == 1
                    and tuple in sub_exp
                    and isinstance(sub_exp[tuple], tuple)
                    and len(sub_exp[tuple]) == 2
                    and sub_exp[tuple][1] is False
                    and isinstance(sub_exp[tuple][0], tuple)
                    and all(
                        is_simple_type(item) and len(item) == 1
                        for item in sub_exp[tuple][0]
                    )
                ):
                    content_check = _emit_cpp_call(
                        "_cpp_val_list_tup_f",
                        _cpp.validate_list_tuple_fixed,
                        [
                            (None, var_expr),
                            (
                                f"{prefix}_tup_types",
                                tuple(
                                    tuple(item.keys())[0]
                                    for item in sub_exp[tuple][0]
                                ),
                            ),
                        ],
                        fail_stmt,
                        fn_globals,
                    )
                elif elem_is_simple:
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
                        content_check = _emit_set_superset_fallback(
                            var_expr,
                            sub_exp,
                            loop_var_id,
                            sub_checks,
                            fail_stmt,
                            prefix,
                            fn_globals,
                        )
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
                count_expr = _calc_sample_count_ast(
                    var_expr, sample_pct, prefix, fn_globals
                )
                if _cpp is not None and elem_is_simple:
                    if len(sub_exp) == 1:
                        content_check = _emit_cpp_call(
                            "_cpp_val_list_samp",
                            _cpp.validate_list_sample,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_t0", tuple(sub_exp.keys())[0]),
                                (None, count_expr),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                    else:
                        content_check = _emit_cpp_call(
                            "_cpp_val_list_samp_u",
                            _cpp.validate_list_sample_union,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_types", tuple(sub_exp.keys())),
                                (None, count_expr),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                else:
                    content_check = _emit_strided_sequence_check(
                        var_expr,
                        loop_var_id,
                        sub_checks,
                        count_expr,
                        prefix,
                    )

        return [outer_type_guard] + (
            content_check
            if isinstance(content_check, list)
            else [content_check]
        )

    if k is dict:
        outer_type_guard = _outer_type_guard(var_expr, "dict", fail_stmt)

        if isinstance(v, list):
            variant_tests = [
                _generate_variant_test_ast(
                    var_expr, k, var, sample_pct, f"{prefix}_v{i}", fn_globals
                )
                for i, var in enumerate(v)
            ]
            content_check = ast.If(
                test=ast.UnaryOp(
                    op=ast.Not(),
                    operand=ast.BoolOp(op=ast.Or(), values=variant_tests),
                ),
                body=[fail_stmt],
                orelse=[],
            )
            return [outer_type_guard, content_check]

        k_exp, v_exp = v
        kv_is_simple = is_simple_type(k_exp) and is_simple_type(v_exp)

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

        if sample_pct == 100:
            if _cpp is not None and kv_is_simple:
                if len(k_exp) == 1 and len(v_exp) == 1:
                    content_check = _emit_cpp_call(
                        "_cpp_val_dict_s",
                        _cpp.validate_dict_single,
                        [
                            (None, var_expr),
                            (f"{prefix}_k_t0", tuple(k_exp.keys())[0]),
                            (f"{prefix}_v_t0", tuple(v_exp.keys())[0]),
                        ],
                        fail_stmt,
                        fn_globals,
                    )
                else:
                    content_check = _emit_cpp_call(
                        "_cpp_val_dict_u",
                        _cpp.validate_dict_unions,
                        [
                            (None, var_expr),
                            (f"{prefix}_k_types", tuple(k_exp.keys())),
                            (f"{prefix}_v_types", tuple(v_exp.keys())),
                        ],
                        fail_stmt,
                        fn_globals,
                    )
            elif (
                _cpp is not None
                and is_simple_type(k_exp)
                and len(k_exp) == 1
                and isinstance(v_exp, dict)
                and len(v_exp) == 1
                and list in v_exp
                and is_simple_type(v_exp[list])
                and len(v_exp[list]) == 1
            ):
                content_check = _emit_cpp_call(
                    "_cpp_val_dict_list",
                    _cpp.validate_dict_list,
                    [
                        (None, var_expr),
                        (f"{prefix}_k_t0", tuple(k_exp.keys())[0]),
                        (f"{prefix}_v_t0", tuple(v_exp[list].keys())[0]),
                    ],
                    fail_stmt,
                    fn_globals,
                )
            elif kv_is_simple:
                fn_globals[f"{prefix}_k_set"] = frozenset(k_exp.keys())
                fn_globals[f"{prefix}_v_set"] = frozenset(v_exp.keys())

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
        else:
            count_expr = _calc_sample_count_ast(
                var_expr, sample_pct, prefix, fn_globals
            )
            if _cpp is not None and kv_is_simple:
                if len(k_exp) == 1 and len(v_exp) == 1:
                    content_check = _emit_cpp_call(
                        "_cpp_val_dict_samp",
                        _cpp.validate_dict_sample,
                        [
                            (None, var_expr),
                            (f"{prefix}_k_t0", tuple(k_exp.keys())[0]),
                            (f"{prefix}_v_t0", tuple(v_exp.keys())[0]),
                            (None, count_expr),
                        ],
                        fail_stmt,
                        fn_globals,
                    )
                else:
                    content_check = _emit_cpp_call(
                        "_cpp_val_dict_samp_u",
                        _cpp.validate_dict_sample_unions,
                        [
                            (None, var_expr),
                            (f"{prefix}_k_types", tuple(k_exp.keys())),
                            (f"{prefix}_v_types", tuple(v_exp.keys())),
                            (None, count_expr),
                        ],
                        fail_stmt,
                        fn_globals,
                    )
            else:
                content_check = ast.For(
                    target=ast.Name(id=k_var_id, ctx=ast.Store()),
                    iter=ast.Call(
                        func=ast.Name(id="_get_sample_keys", ctx=ast.Load()),
                        args=[
                            ast.Name(id="__enf_self__", ctx=ast.Load()),
                            var_expr,
                        ],
                        keywords=[],
                    ),
                    body=dict_loop_body,
                    orelse=[],
                )

        return [outer_type_guard] + (
            content_check
            if isinstance(content_check, list)
            else [content_check]
        )

    if k is tuple:
        outer_type_guard = _outer_type_guard(var_expr, "tuple", fail_stmt)

        if isinstance(v, list):
            variant_tests = [
                _generate_variant_test_ast(
                    var_expr, k, var, sample_pct, f"{prefix}_v{i}", fn_globals
                )
                for i, var in enumerate(v)
            ]
            content_check = ast.If(
                test=ast.UnaryOp(
                    op=ast.Not(),
                    operand=ast.BoolOp(op=ast.Or(), values=variant_tests),
                ),
                body=[fail_stmt],
                orelse=[],
            )
            return [outer_type_guard, content_check]

        if isinstance(v, tuple) and len(v) == 2 and v[1] is True:
            # Variable-length tuple[T, ...]
            sub_exp = v[0]
            elem_is_simple = is_simple_type(sub_exp)

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
                if _cpp is not None and elem_is_simple:
                    if len(sub_exp) == 1:
                        content_check = _emit_cpp_call(
                            "_cpp_val_tup_first",
                            _cpp.validate_tuple_first,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_t0", tuple(sub_exp.keys())[0]),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                    else:
                        content_check = _emit_cpp_call(
                            "_cpp_val_tup_first_u",
                            _cpp.validate_tuple_first_union,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_types", tuple(sub_exp.keys())),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                else:
                    content_check = ast.If(
                        test=var_expr,
                        body=[
                            ast.Assign(
                                targets=[
                                    ast.Name(id=loop_var_id, ctx=ast.Store())
                                ],
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
                if _cpp is not None and elem_is_simple:
                    if len(sub_exp) == 1:
                        content_check = _emit_cpp_call(
                            "_cpp_val_tup_last",
                            _cpp.validate_tuple_last,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_t0", tuple(sub_exp.keys())[0]),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                    else:
                        content_check = _emit_cpp_call(
                            "_cpp_val_tup_last_u",
                            _cpp.validate_tuple_last_union,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_types", tuple(sub_exp.keys())),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                else:
                    content_check = ast.If(
                        test=var_expr,
                        body=[
                            ast.Assign(
                                targets=[
                                    ast.Name(id=loop_var_id, ctx=ast.Store())
                                ],
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
            elif sample_pct == "bookend":
                if _cpp is not None and elem_is_simple:
                    if len(sub_exp) == 1:
                        content_check = _emit_cpp_call(
                            "_cpp_val_tup_bookend",
                            _cpp.validate_tuple_bookend,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_t0", tuple(sub_exp.keys())[0]),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                    else:
                        content_check = _emit_cpp_call(
                            "_cpp_val_tup_bookend_u",
                            _cpp.validate_tuple_bookend_union,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_types", tuple(sub_exp.keys())),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                else:
                    content_check = ast.If(
                        test=var_expr,
                        body=[
                            ast.Assign(
                                targets=[
                                    ast.Name(id=loop_var_id, ctx=ast.Store())
                                ],
                                value=ast.Subscript(
                                    value=var_expr,
                                    slice=ast.Constant(value=0),
                                    ctx=ast.Load(),
                                ),
                            )
                        ]
                        + sub_checks
                        + [
                            ast.If(
                                test=ast.Compare(
                                    left=ast.Call(
                                        func=ast.Name(id="len", ctx=ast.Load()),
                                        args=[var_expr],
                                        keywords=[],
                                    ),
                                    ops=[ast.Gt()],
                                    comparators=[ast.Constant(value=1)],
                                ),
                                body=[
                                    ast.Assign(
                                        targets=[
                                            ast.Name(
                                                id=loop_var_id, ctx=ast.Store()
                                            )
                                        ],
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
                        ],
                        orelse=[],
                    )
            elif sample_pct == "bookend_plus":
                if _cpp is not None and elem_is_simple:
                    if len(sub_exp) == 1:
                        content_check = _emit_cpp_call(
                            "_cpp_val_tup_bookend_plus",
                            _cpp.validate_tuple_bookend_plus,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_t0", tuple(sub_exp.keys())[0]),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                    else:
                        content_check = _emit_cpp_call(
                            "_cpp_val_tup_bookend_plus_u",
                            _cpp.validate_tuple_bookend_plus_union,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_types", tuple(sub_exp.keys())),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                else:
                    fn_globals["_randrange"] = random.randrange
                    content_check = ast.If(
                        test=var_expr,
                        body=[
                            ast.Assign(
                                targets=[
                                    ast.Name(id=loop_var_id, ctx=ast.Store())
                                ],
                                value=ast.Subscript(
                                    value=var_expr,
                                    slice=ast.Constant(value=0),
                                    ctx=ast.Load(),
                                ),
                            )
                        ]
                        + sub_checks
                        + [
                            ast.If(
                                test=ast.Compare(
                                    left=ast.Call(
                                        func=ast.Name(id="len", ctx=ast.Load()),
                                        args=[var_expr],
                                        keywords=[],
                                    ),
                                    ops=[ast.Gt()],
                                    comparators=[ast.Constant(value=1)],
                                ),
                                body=[
                                    ast.Assign(
                                        targets=[
                                            ast.Name(
                                                id=loop_var_id, ctx=ast.Store()
                                            )
                                        ],
                                        value=ast.Subscript(
                                            value=var_expr,
                                            slice=ast.Constant(value=-1),
                                            ctx=ast.Load(),
                                        ),
                                    )
                                ]
                                + sub_checks
                                + [
                                    ast.If(
                                        test=ast.Compare(
                                            left=ast.Call(
                                                func=ast.Name(
                                                    id="len", ctx=ast.Load()
                                                ),
                                                args=[var_expr],
                                                keywords=[],
                                            ),
                                            ops=[ast.Gt()],
                                            comparators=[ast.Constant(value=2)],
                                        ),
                                        body=[
                                            ast.Assign(
                                                targets=[
                                                    ast.Name(
                                                        id=loop_var_id,
                                                        ctx=ast.Store(),
                                                    )
                                                ],
                                                value=ast.Subscript(
                                                    value=var_expr,
                                                    slice=ast.Call(
                                                        func=ast.Name(
                                                            id="_randrange",
                                                            ctx=ast.Load(),
                                                        ),
                                                        args=[
                                                            ast.Constant(
                                                                value=1
                                                            ),
                                                            ast.BinOp(
                                                                left=ast.Call(
                                                                    func=ast.Name(
                                                                        id="len",
                                                                        ctx=ast.Load(),
                                                                    ),
                                                                    args=[
                                                                        var_expr
                                                                    ],
                                                                    keywords=[],
                                                                ),
                                                                op=ast.Sub(),
                                                                right=ast.Constant(
                                                                    value=1
                                                                ),
                                                            ),
                                                        ],
                                                        keywords=[],
                                                    ),
                                                    ctx=ast.Load(),
                                                ),
                                            )
                                        ]
                                        + sub_checks,
                                        orelse=[],
                                    )
                                ],
                                orelse=[],
                            )
                        ],
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
                if _cpp is not None and elem_is_simple:
                    if len(sub_exp) == 1:
                        content_check = _emit_cpp_call(
                            "_cpp_val_tup_s",
                            _cpp.validate_tuple_single,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_t0", tuple(sub_exp.keys())[0]),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                    else:
                        content_check = _emit_cpp_call(
                            "_cpp_val_tup_u",
                            _cpp.validate_tuple_union,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_types", tuple(sub_exp.keys())),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                elif elem_is_simple:
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
                        content_check = _emit_set_superset_fallback(
                            var_expr,
                            sub_exp,
                            loop_var_id,
                            sub_checks,
                            fail_stmt,
                            prefix,
                            fn_globals,
                        )
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
                count_expr = _calc_sample_count_ast(
                    var_expr, sample_pct, prefix, fn_globals
                )
                if _cpp is not None and elem_is_simple:
                    if len(sub_exp) == 1:
                        content_check = _emit_cpp_call(
                            "_cpp_val_tup_samp",
                            _cpp.validate_tuple_sample,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_t0", tuple(sub_exp.keys())[0]),
                                (None, count_expr),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                    else:
                        content_check = _emit_cpp_call(
                            "_cpp_val_tup_samp_u",
                            _cpp.validate_tuple_sample_union,
                            [
                                (None, var_expr),
                                (f"{prefix}_el_types", tuple(sub_exp.keys())),
                                (None, count_expr),
                            ],
                            fail_stmt,
                            fn_globals,
                        )
                else:
                    content_check = _emit_strided_sequence_check(
                        var_expr, loop_var_id, sub_checks, count_expr, prefix
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

            if (
                _cpp is not None
                and expected_len > 4
                and all(
                    is_simple_type(item_exp) and len(item_exp) == 1
                    for item_exp in elem_exps
                )
            ):
                return _emit_cpp_call(
                    "_cpp_val_tup_f",
                    _cpp.validate_tuple_fixed,
                    [
                        (None, var_expr),
                        (
                            f"{prefix}_tup_types",
                            tuple(
                                tuple(item_exp.keys())[0]
                                for item_exp in elem_exps
                            ),
                        ),
                    ],
                    fail_stmt,
                    fn_globals,
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

    first_param_name = (
        posonly_names[0]
        if posonly_names
        else (pos_names[0] if pos_names else None)
    )
    if first_param_name:
        fn_globals["__enf_first_param_name"] = first_param_name

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
    elif ret_mode == 3 and first_param_name:
        fn_globals["_ret_exp"] = ret_exp
        body.append(
            ast.Assign(
                targets=[ast.Name(id="__enf_res__", ctx=ast.Store())],
                value=fn_call,
            )
        )
        self_inst_cls = ast.Attribute(
            value=ast.Name(id=first_param_name, ctx=ast.Load()),
            attr="__class__",
            ctx=ast.Load(),
        )
        body.append(
            ast.If(
                test=ast.Call(
                    func=ast.Name(id="isinstance", ctx=ast.Load()),
                    args=[
                        ast.Name(id="__enf_res__", ctx=ast.Load()),
                        self_inst_cls,
                    ],
                    keywords=[],
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
    elif ret_mode == 5:
        fn_globals["_ret_exp"] = ret_exp
        body.append(
            ast.Assign(
                targets=[ast.Name(id="__enf_res__", ctx=ast.Store())],
                value=fn_call,
            )
        )
        body.append(
            ast.If(
                test=ast.Call(
                    func=ast.Name(id="callable", ctx=ast.Load()),
                    args=[ast.Name(id="__enf_res__", ctx=ast.Load())],
                    keywords=[],
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
    elif ret_mode == 6:
        fn_globals["_ret_exp"] = ret_exp
        body.append(
            ast.Assign(
                targets=[ast.Name(id="__enf_res__", ctx=ast.Store())],
                value=fn_call,
            )
        )
        ret_res_expr = ast.Name(id="__enf_res__", ctx=ast.Load())
        ret_fail_call = ast.Expr(
            value=ast.Call(
                func=ast.Name(id="_check_fn", ctx=ast.Load()),
                args=[
                    ast.Name(id="__enf_self__", ctx=ast.Load()),
                    ret_res_expr,
                    ast.Name(id="_ret_exp", ctx=ast.Load()),
                    ast.Constant(value="return"),
                ],
                keywords=[],
            )
        )
        ret_checks = generate_type_check_ast(
            ret_res_expr,
            ret_exp,
            ret_fail_call,
            fn_globals,
            "_ret",
            sample_pct,
        )
        body.extend(ret_checks)
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

    cache_key = (
        tuple(posonly_names),
        tuple(pos_names),
        tuple(kwonly_names),
        vararg_name,
        kwarg_name,
        sample_pct,
        ret_mode,
        _freeze_exp(ret_exp),
        tuple(
            (name, _freeze_exp(param_exps.get(name))) for name in check_params
        ),
        _cpp is not None,
    )

    func_code = _CODE_CACHE.get(cache_key)
    if func_code is None:
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
        _fast_fix_locations(module)
        code_mod = compile(module, "<type_enforced_specialized>", "exec")
        func_code = [
            c
            for c in code_mod.co_consts
            if isinstance(c, types.CodeType) and c.co_name == "__call__"
        ][0]
        _CODE_CACHE[cache_key] = func_code

    call_method = types.FunctionType(
        func_code, fn_globals, name="__call__", argdefs=defaults
    )
    if kwdefaults:
        call_method.__kwdefaults__ = kwdefaults

    return call_method
