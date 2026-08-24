import types


def bind_parameter_names(func, param_names, defaults=None):
    """
    Given a template function with signature (self, a, b, ...) and target param_names,
    returns a new FunctionType with parameter names updated to (self, *param_names).
    """
    code = func.__code__
    n_params = len(param_names)
    new_varnames = (
        ("self",) + tuple(param_names) + code.co_varnames[1 + n_params :]
    )
    new_code = code.replace(co_varnames=new_varnames)
    return types.FunctionType(
        new_code,
        func.__globals__,
        "__call__",
        defaults,
        func.__closure__,
    )


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


# --- Type Inspection Helpers ---
def is_simple_type(exp):
    return (
        exp is not None
        and "__extra__" not in exp
        and all(v is None for v in exp.values())
        and all(isinstance(k, type) for k in exp.keys())
    )


def is_simple_list(exp):
    return (
        isinstance(exp, dict)
        and len(exp) == 1
        and list in exp
        and isinstance(exp[list], dict)
        and is_simple_type(exp[list])
    )


def is_simple_dict(exp):
    return (
        isinstance(exp, dict)
        and len(exp) == 1
        and dict in exp
        and isinstance(exp[dict], tuple)
        and len(exp[dict]) == 2
        and is_simple_type(exp[dict][0])
        and is_simple_type(exp[dict][1])
    )


def is_simple_set(exp):
    return (
        isinstance(exp, dict)
        and len(exp) == 1
        and set in exp
        and isinstance(exp[set], dict)
        and is_simple_type(exp[set])
    )


def is_simple_var_tuple(exp):
    return (
        isinstance(exp, dict)
        and len(exp) == 1
        and tuple in exp
        and isinstance(exp[tuple], tuple)
        and len(exp[tuple]) == 2
        and exp[tuple][1] is True
        and is_simple_type(exp[tuple][0])
    )


def is_simple_list_of_dict(exp):
    return (
        isinstance(exp, dict)
        and len(exp) == 1
        and list in exp
        and isinstance(exp[list], dict)
        and is_simple_dict(exp[list])
    )


def is_simple_list_of_list(exp):
    return (
        isinstance(exp, dict)
        and len(exp) == 1
        and list in exp
        and isinstance(exp[list], dict)
        and is_simple_list(exp[list])
    )


def is_simple_dict_of_list(exp):
    return (
        isinstance(exp, dict)
        and len(exp) == 1
        and dict in exp
        and isinstance(exp[dict], tuple)
        and len(exp[dict]) == 2
        and is_simple_type(exp[dict][0])
        and is_simple_list(exp[dict][1])
    )


# --- Zero Arg Builders ---
def build_zero_arg(
    fn,
    check_type_fn,
    ret_mode,
    ret_t0=None,
    ret_t1=None,
    ret_types=None,
    ret_exp=None,
):
    if ret_mode == 0:

        def template(self):
            return fn()

        return template
    elif ret_mode == 1:

        def template(self):
            res = fn()
            if res is None:
                return res
            check_type_fn(self, res, ret_exp, "return")
            return res

        return template
    else:

        def template(self):
            res = fn()
            if (
                type(res) is ret_t0
                or type(res) is ret_t1
                or isinstance(res, ret_types)
            ):
                return res
            check_type_fn(self, res, ret_exp, "return")
            return res

        return template


# --- Simple N-Arg Builders ---
def build_simple_n_arg(
    fn,
    param_names,
    defaults,
    check_type_fn,
    p_t0s,
    p_t1s,
    p_types,
    p_exps,
    ret_mode,
    ret_t0=None,
    ret_t1=None,
    ret_types=None,
    ret_exp=None,
):
    n = len(param_names)

    if n == 1:
        p0_name = param_names[0]
        p0_t0 = p_t0s[0]
        p0_t1 = p_t1s[0]
        p0_types = p_types[0]
        p0_exp = p_exps[0]

        if p0_t0 is None:
            if ret_mode == 0:

                def template(self, a):
                    return fn(a)

            elif ret_mode == 1:

                def template(self, a):
                    res = fn(a)
                    if res is None:
                        return res
                    check_type_fn(self, res, ret_exp, "return")
                    return res

            else:

                def template(self, a):
                    res = fn(a)
                    if (
                        type(res) is ret_t0
                        or type(res) is ret_t1
                        or isinstance(res, ret_types)
                    ):
                        return res
                    check_type_fn(self, res, ret_exp, "return")
                    return res

        elif p0_t1 is None:
            if ret_mode == 0:

                def template(self, a):
                    if type(a) is not p0_t0 and not isinstance(a, p0_types):
                        check_type_fn(self, a, p0_exp, p0_name)
                    return fn(a)

            elif ret_mode == 1:

                def template(self, a):
                    if type(a) is not p0_t0 and not isinstance(a, p0_types):
                        check_type_fn(self, a, p0_exp, p0_name)
                    res = fn(a)
                    if res is None:
                        return res
                    check_type_fn(self, res, ret_exp, "return")
                    return res

            else:

                def template(self, a):
                    if type(a) is not p0_t0 and not isinstance(a, p0_types):
                        check_type_fn(self, a, p0_exp, p0_name)
                    res = fn(a)
                    if (
                        type(res) is ret_t0
                        or type(res) is ret_t1
                        or isinstance(res, ret_types)
                    ):
                        return res
                    check_type_fn(self, res, ret_exp, "return")
                    return res

        else:
            if ret_mode == 0:

                def template(self, a):
                    t = type(a)
                    if (
                        t is not p0_t0
                        and t is not p0_t1
                        and not isinstance(a, p0_types)
                    ):
                        check_type_fn(self, a, p0_exp, p0_name)
                    return fn(a)

            elif ret_mode == 1:

                def template(self, a):
                    t = type(a)
                    if (
                        t is not p0_t0
                        and t is not p0_t1
                        and not isinstance(a, p0_types)
                    ):
                        check_type_fn(self, a, p0_exp, p0_name)
                    res = fn(a)
                    if res is None:
                        return res
                    check_type_fn(self, res, ret_exp, "return")
                    return res

            else:

                def template(self, a):
                    t = type(a)
                    if (
                        t is not p0_t0
                        and t is not p0_t1
                        and not isinstance(a, p0_types)
                    ):
                        check_type_fn(self, a, p0_exp, p0_name)
                    res = fn(a)
                    if (
                        type(res) is ret_t0
                        or type(res) is ret_t1
                        or isinstance(res, ret_types)
                    ):
                        return res
                    check_type_fn(self, res, ret_exp, "return")
                    return res

        return bind_parameter_names(template, param_names, defaults)

    elif n == 2:
        p0_name, p1_name = param_names
        p0_t0, p1_t0 = p_t0s
        p0_t1, p1_t1 = p_t1s
        p0_types, p1_types = p_types
        p0_exp, p1_exp = p_exps

        # Method case: param 0 is untyped (e.g. self)
        if p0_t0 is None and p1_t0 is not None:
            if p1_t1 is None:
                if ret_mode == 0:

                    def template(self, a, b):
                        if type(b) is not p1_t0 and not isinstance(b, p1_types):
                            check_type_fn(self, b, p1_exp, p1_name)
                        return fn(a, b)

                elif ret_mode == 1:

                    def template(self, a, b):
                        if type(b) is not p1_t0 and not isinstance(b, p1_types):
                            check_type_fn(self, b, p1_exp, p1_name)
                        res = fn(a, b)
                        if res is None:
                            return res
                        check_type_fn(self, res, ret_exp, "return")
                        return res

                else:

                    def template(self, a, b):
                        if type(b) is not p1_t0 and not isinstance(b, p1_types):
                            check_type_fn(self, b, p1_exp, p1_name)
                        res = fn(a, b)
                        if (
                            type(res) is ret_t0
                            or type(res) is ret_t1
                            or isinstance(res, ret_types)
                        ):
                            return res
                        check_type_fn(self, res, ret_exp, "return")
                        return res

            else:
                if ret_mode == 0:

                    def template(self, a, b):
                        t = type(b)
                        if (
                            t is not p1_t0
                            and t is not p1_t1
                            and not isinstance(b, p1_types)
                        ):
                            check_type_fn(self, b, p1_exp, p1_name)
                        return fn(a, b)

                elif ret_mode == 1:

                    def template(self, a, b):
                        t = type(b)
                        if (
                            t is not p1_t0
                            and t is not p1_t1
                            and not isinstance(b, p1_types)
                        ):
                            check_type_fn(self, b, p1_exp, p1_name)
                        res = fn(a, b)
                        if res is None:
                            return res
                        check_type_fn(self, res, ret_exp, "return")
                        return res

                else:

                    def template(self, a, b):
                        t = type(b)
                        if (
                            t is not p1_t0
                            and t is not p1_t1
                            and not isinstance(b, p1_types)
                        ):
                            check_type_fn(self, b, p1_exp, p1_name)
                        res = fn(a, b)
                        if (
                            type(res) is ret_t0
                            or type(res) is ret_t1
                            or isinstance(res, ret_types)
                        ):
                            return res
                        check_type_fn(self, res, ret_exp, "return")
                        return res

        elif p0_t0 is None and p1_t0 is None:
            if ret_mode == 0:

                def template(self, a, b):
                    return fn(a, b)

            elif ret_mode == 1:

                def template(self, a, b):
                    res = fn(a, b)
                    if res is None:
                        return res
                    check_type_fn(self, res, ret_exp, "return")
                    return res

            else:

                def template(self, a, b):
                    res = fn(a, b)
                    if (
                        type(res) is ret_t0
                        or type(res) is ret_t1
                        or isinstance(res, ret_types)
                    ):
                        return res
                    check_type_fn(self, res, ret_exp, "return")
                    return res

        elif p0_t0 is not None and p1_t0 is None:
            if p0_t1 is None:
                if ret_mode == 0:

                    def template(self, a, b):
                        if type(a) is not p0_t0 and not isinstance(a, p0_types):
                            check_type_fn(self, a, p0_exp, p0_name)
                        return fn(a, b)

                elif ret_mode == 1:

                    def template(self, a, b):
                        if type(a) is not p0_t0 and not isinstance(a, p0_types):
                            check_type_fn(self, a, p0_exp, p0_name)
                        res = fn(a, b)
                        if res is None:
                            return res
                        check_type_fn(self, res, ret_exp, "return")
                        return res

                else:

                    def template(self, a, b):
                        if type(a) is not p0_t0 and not isinstance(a, p0_types):
                            check_type_fn(self, a, p0_exp, p0_name)
                        res = fn(a, b)
                        if (
                            type(res) is ret_t0
                            or type(res) is ret_t1
                            or isinstance(res, ret_types)
                        ):
                            return res
                        check_type_fn(self, res, ret_exp, "return")
                        return res

            else:
                if ret_mode == 0:

                    def template(self, a, b):
                        t = type(a)
                        if (
                            t is not p0_t0
                            and t is not p0_t1
                            and not isinstance(a, p0_types)
                        ):
                            check_type_fn(self, a, p0_exp, p0_name)
                        return fn(a, b)

                elif ret_mode == 1:

                    def template(self, a, b):
                        t = type(a)
                        if (
                            t is not p0_t0
                            and t is not p0_t1
                            and not isinstance(a, p0_types)
                        ):
                            check_type_fn(self, a, p0_exp, p0_name)
                        res = fn(a, b)
                        if res is None:
                            return res
                        check_type_fn(self, res, ret_exp, "return")
                        return res

                else:

                    def template(self, a, b):
                        t = type(a)
                        if (
                            t is not p0_t0
                            and t is not p0_t1
                            and not isinstance(a, p0_types)
                        ):
                            check_type_fn(self, a, p0_exp, p0_name)
                        res = fn(a, b)
                        if (
                            type(res) is ret_t0
                            or type(res) is ret_t1
                            or isinstance(res, ret_types)
                        ):
                            return res
                        check_type_fn(self, res, ret_exp, "return")
                        return res

        else:
            # Both typed
            if ret_mode == 0:

                def template(self, a, b):
                    if (
                        type(a) is not p0_t0
                        and type(a) is not p0_t1
                        and not isinstance(a, p0_types)
                    ):
                        check_type_fn(self, a, p0_exp, p0_name)
                    if (
                        type(b) is not p1_t0
                        and type(b) is not p1_t1
                        and not isinstance(b, p1_types)
                    ):
                        check_type_fn(self, b, p1_exp, p1_name)
                    return fn(a, b)

            elif ret_mode == 1:

                def template(self, a, b):
                    if (
                        type(a) is not p0_t0
                        and type(a) is not p0_t1
                        and not isinstance(a, p0_types)
                    ):
                        check_type_fn(self, a, p0_exp, p0_name)
                    if (
                        type(b) is not p1_t0
                        and type(b) is not p1_t1
                        and not isinstance(b, p1_types)
                    ):
                        check_type_fn(self, b, p1_exp, p1_name)
                    res = fn(a, b)
                    if res is None:
                        return res
                    check_type_fn(self, res, ret_exp, "return")
                    return res

            else:

                def template(self, a, b):
                    if (
                        type(a) is not p0_t0
                        and type(a) is not p0_t1
                        and not isinstance(a, p0_types)
                    ):
                        check_type_fn(self, a, p0_exp, p0_name)
                    if (
                        type(b) is not p1_t0
                        and type(b) is not p1_t1
                        and not isinstance(b, p1_types)
                    ):
                        check_type_fn(self, b, p1_exp, p1_name)
                    res = fn(a, b)
                    if (
                        type(res) is ret_t0
                        or type(res) is ret_t1
                        or isinstance(res, ret_types)
                    ):
                        return res
                    check_type_fn(self, res, ret_exp, "return")
                    return res

        return bind_parameter_names(template, param_names, defaults)

    elif n == 3:
        p0_name, p1_name, p2_name = param_names
        p0_t0, p1_t0, p2_t0 = p_t0s
        p0_t1, p1_t1, p2_t1 = p_t1s
        p0_types, p1_types, p2_types = p_types
        p0_exp, p1_exp, p2_exp = p_exps

        if ret_mode == 0:

            def template(self, a, b, c):
                if p0_t0 is not None and (
                    type(a) is not p0_t0
                    and type(a) is not p0_t1
                    and not isinstance(a, p0_types)
                ):
                    check_type_fn(self, a, p0_exp, p0_name)
                if p1_t0 is not None and (
                    type(b) is not p1_t0
                    and type(b) is not p1_t1
                    and not isinstance(b, p1_types)
                ):
                    check_type_fn(self, b, p1_exp, p1_name)
                if p2_t0 is not None and (
                    type(c) is not p2_t0
                    and type(c) is not p2_t1
                    and not isinstance(c, p2_types)
                ):
                    check_type_fn(self, c, p2_exp, p2_name)
                return fn(a, b, c)

        elif ret_mode == 1:

            def template(self, a, b, c):
                if p0_t0 is not None and (
                    type(a) is not p0_t0
                    and type(a) is not p0_t1
                    and not isinstance(a, p0_types)
                ):
                    check_type_fn(self, a, p0_exp, p0_name)
                if p1_t0 is not None and (
                    type(b) is not p1_t0
                    and type(b) is not p1_t1
                    and not isinstance(b, p1_types)
                ):
                    check_type_fn(self, b, p1_exp, p1_name)
                if p2_t0 is not None and (
                    type(c) is not p2_t0
                    and type(c) is not p2_t1
                    and not isinstance(c, p2_types)
                ):
                    check_type_fn(self, c, p2_exp, p2_name)
                res = fn(a, b, c)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, a, b, c):
                if p0_t0 is not None and (
                    type(a) is not p0_t0
                    and type(a) is not p0_t1
                    and not isinstance(a, p0_types)
                ):
                    check_type_fn(self, a, p0_exp, p0_name)
                if p1_t0 is not None and (
                    type(b) is not p1_t0
                    and type(b) is not p1_t1
                    and not isinstance(b, p1_types)
                ):
                    check_type_fn(self, b, p1_exp, p1_name)
                if p2_t0 is not None and (
                    type(c) is not p2_t0
                    and type(c) is not p2_t1
                    and not isinstance(c, p2_types)
                ):
                    check_type_fn(self, c, p2_exp, p2_name)
                res = fn(a, b, c)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        return bind_parameter_names(template, param_names, defaults)

    elif n == 4:
        p0_name, p1_name, p2_name, p3_name = param_names
        p0_t0, p1_t0, p2_t0, p3_t0 = p_t0s
        p0_t1, p1_t1, p2_t1, p3_t1 = p_t1s
        p0_types, p1_types, p2_types, p3_types = p_types
        p0_exp, p1_exp, p2_exp, p3_exp = p_exps

        if ret_mode == 0:

            def template(self, a, b, c, d):
                if p0_t0 is not None and (
                    type(a) is not p0_t0
                    and type(a) is not p0_t1
                    and not isinstance(a, p0_types)
                ):
                    check_type_fn(self, a, p0_exp, p0_name)
                if p1_t0 is not None and (
                    type(b) is not p1_t0
                    and type(b) is not p1_t1
                    and not isinstance(b, p1_types)
                ):
                    check_type_fn(self, b, p1_exp, p1_name)
                if p2_t0 is not None and (
                    type(c) is not p2_t0
                    and type(c) is not p2_t1
                    and not isinstance(c, p2_types)
                ):
                    check_type_fn(self, c, p2_exp, p2_name)
                if p3_t0 is not None and (
                    type(d) is not p3_t0
                    and type(d) is not p3_t1
                    and not isinstance(d, p3_types)
                ):
                    check_type_fn(self, d, p3_exp, p3_name)
                return fn(a, b, c, d)

        elif ret_mode == 1:

            def template(self, a, b, c, d):
                if p0_t0 is not None and (
                    type(a) is not p0_t0
                    and type(a) is not p0_t1
                    and not isinstance(a, p0_types)
                ):
                    check_type_fn(self, a, p0_exp, p0_name)
                if p1_t0 is not None and (
                    type(b) is not p1_t0
                    and type(b) is not p1_t1
                    and not isinstance(b, p1_types)
                ):
                    check_type_fn(self, b, p1_exp, p1_name)
                if p2_t0 is not None and (
                    type(c) is not p2_t0
                    and type(c) is not p2_t1
                    and not isinstance(c, p2_types)
                ):
                    check_type_fn(self, c, p2_exp, p2_name)
                if p3_t0 is not None and (
                    type(d) is not p3_t0
                    and type(d) is not p3_t1
                    and not isinstance(d, p3_types)
                ):
                    check_type_fn(self, d, p3_exp, p3_name)
                res = fn(a, b, c, d)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, a, b, c, d):
                if p0_t0 is not None and (
                    type(a) is not p0_t0
                    and type(a) is not p0_t1
                    and not isinstance(a, p0_types)
                ):
                    check_type_fn(self, a, p0_exp, p0_name)
                if p1_t0 is not None and (
                    type(b) is not p1_t0
                    and type(b) is not p1_t1
                    and not isinstance(b, p1_types)
                ):
                    check_type_fn(self, b, p1_exp, p1_name)
                if p2_t0 is not None and (
                    type(c) is not p2_t0
                    and type(c) is not p2_t1
                    and not isinstance(c, p2_types)
                ):
                    check_type_fn(self, c, p2_exp, p2_name)
                if p3_t0 is not None and (
                    type(d) is not p3_t0
                    and type(d) is not p3_t1
                    and not isinstance(d, p3_types)
                ):
                    check_type_fn(self, d, p3_exp, p3_name)
                res = fn(a, b, c, d)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        return bind_parameter_names(template, param_names, defaults)

    elif n == 5:
        p0_name, p1_name, p2_name, p3_name, p4_name = param_names
        p0_t0, p1_t0, p2_t0, p3_t0, p4_t0 = p_t0s
        p0_t1, p1_t1, p2_t1, p3_t1, p4_t1 = p_t1s
        p0_types, p1_types, p2_types, p3_types, p4_types = p_types
        p0_exp, p1_exp, p2_exp, p3_exp, p4_exp = p_exps

        if ret_mode == 0:

            def template(self, a, b, c, d, e):
                if p0_t0 is not None and (
                    type(a) is not p0_t0
                    and type(a) is not p0_t1
                    and not isinstance(a, p0_types)
                ):
                    check_type_fn(self, a, p0_exp, p0_name)
                if p1_t0 is not None and (
                    type(b) is not p1_t0
                    and type(b) is not p1_t1
                    and not isinstance(b, p1_types)
                ):
                    check_type_fn(self, b, p1_exp, p1_name)
                if p2_t0 is not None and (
                    type(c) is not p2_t0
                    and type(c) is not p2_t1
                    and not isinstance(c, p2_types)
                ):
                    check_type_fn(self, c, p2_exp, p2_name)
                if p3_t0 is not None and (
                    type(d) is not p3_t0
                    and type(d) is not p3_t1
                    and not isinstance(d, p3_types)
                ):
                    check_type_fn(self, d, p3_exp, p3_name)
                if p4_t0 is not None and (
                    type(e) is not p4_t0
                    and type(e) is not p4_t1
                    and not isinstance(e, p4_types)
                ):
                    check_type_fn(self, e, p4_exp, p4_name)
                return fn(a, b, c, d, e)

        elif ret_mode == 1:

            def template(self, a, b, c, d, e):
                if p0_t0 is not None and (
                    type(a) is not p0_t0
                    and type(a) is not p0_t1
                    and not isinstance(a, p0_types)
                ):
                    check_type_fn(self, a, p0_exp, p0_name)
                if p1_t0 is not None and (
                    type(b) is not p1_t0
                    and type(b) is not p1_t1
                    and not isinstance(b, p1_types)
                ):
                    check_type_fn(self, b, p1_exp, p1_name)
                if p2_t0 is not None and (
                    type(c) is not p2_t0
                    and type(c) is not p2_t1
                    and not isinstance(c, p2_types)
                ):
                    check_type_fn(self, c, p2_exp, p2_name)
                if p3_t0 is not None and (
                    type(d) is not p3_t0
                    and type(d) is not p3_t1
                    and not isinstance(d, p3_types)
                ):
                    check_type_fn(self, d, p3_exp, p3_name)
                if p4_t0 is not None and (
                    type(e) is not p4_t0
                    and type(e) is not p4_t1
                    and not isinstance(e, p4_types)
                ):
                    check_type_fn(self, e, p4_exp, p4_name)
                res = fn(a, b, c, d, e)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, a, b, c, d, e):
                if p0_t0 is not None and (
                    type(a) is not p0_t0
                    and type(a) is not p0_t1
                    and not isinstance(a, p0_types)
                ):
                    check_type_fn(self, a, p0_exp, p0_name)
                if p1_t0 is not None and (
                    type(b) is not p1_t0
                    and type(b) is not p1_t1
                    and not isinstance(b, p1_types)
                ):
                    check_type_fn(self, b, p1_exp, p1_name)
                if p2_t0 is not None and (
                    type(c) is not p2_t0
                    and type(c) is not p2_t1
                    and not isinstance(c, p2_types)
                ):
                    check_type_fn(self, c, p2_exp, p2_name)
                if p3_t0 is not None and (
                    type(d) is not p3_t0
                    and type(d) is not p3_t1
                    and not isinstance(d, p3_types)
                ):
                    check_type_fn(self, d, p3_exp, p3_name)
                if p4_t0 is not None and (
                    type(e) is not p4_t0
                    and type(e) is not p4_t1
                    and not isinstance(e, p4_types)
                ):
                    check_type_fn(self, e, p4_exp, p4_name)
                res = fn(a, b, c, d, e)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        return bind_parameter_names(template, param_names, defaults)

    else:
        active_checkers = []
        for i in range(n):
            if p_t0s[i] is not None:
                active_checkers.append(
                    (
                        i,
                        param_names[i],
                        p_t0s[i],
                        p_t1s[i],
                        p_types[i],
                        p_exps[i],
                    )
                )
        active_tuple = tuple(active_checkers)

        if ret_mode == 0:

            def template(self, *args):
                for i, pn, t0, t1, tt, exp in active_tuple:
                    a = args[i]
                    if (
                        type(a) is not t0
                        and type(a) is not t1
                        and not isinstance(a, tt)
                    ):
                        check_type_fn(self, a, exp, pn)
                return fn(*args)

        elif ret_mode == 1:

            def template(self, *args):
                for i, pn, t0, t1, tt, exp in active_tuple:
                    a = args[i]
                    if (
                        type(a) is not t0
                        and type(a) is not t1
                        and not isinstance(a, tt)
                    ):
                        check_type_fn(self, a, exp, pn)
                res = fn(*args)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, *args):
                for i, pn, t0, t1, tt, exp in active_tuple:
                    a = args[i]
                    if (
                        type(a) is not t0
                        and type(a) is not t1
                        and not isinstance(a, tt)
                    ):
                        check_type_fn(self, a, exp, pn)
                res = fn(*args)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        return template


# --- Simple List 1-Arg Builders ---
def build_list_1arg(
    fn,
    param_names,
    defaults,
    check_type_fn,
    p_exp,
    elem_t0,
    elem_t1,
    elem_types,
    elem_set,
    sample_pct,
    get_sample_indices_fn,
    ret_mode,
    ret_t0=None,
    ret_t1=None,
    ret_types=None,
    ret_exp=None,
    has_self=False,
):
    param_name = param_names[-1]
    if sample_pct == 100:
        if elem_t1 is None:

            def check_list(self, a):
                if type(a) is list:
                    n = len(a)
                    if n <= 20:
                        for el in a:
                            if type(el) is not elem_t0 and not isinstance(
                                el, elem_types
                            ):
                                check_type_fn(self, a, p_exp, param_name)
                                break
                    else:
                        if not set(map(type, a)) <= elem_set:
                            check_type_fn(self, a, p_exp, param_name)
                else:
                    check_type_fn(self, a, p_exp, param_name)

        else:

            def check_list(self, a):
                if type(a) is list:
                    n = len(a)
                    if n <= 20:
                        for el in a:
                            t = type(el)
                            if (
                                t is not elem_t0
                                and t is not elem_t1
                                and not isinstance(el, elem_types)
                            ):
                                check_type_fn(self, a, p_exp, param_name)
                                break
                    else:
                        if not set(map(type, a)) <= elem_set:
                            check_type_fn(self, a, p_exp, param_name)
                else:
                    check_type_fn(self, a, p_exp, param_name)

    elif sample_pct == 0:
        if elem_t1 is None:

            def check_list(self, a):
                if type(a) is list:
                    if (
                        a
                        and type(a[0]) is not elem_t0
                        and not isinstance(a[0], elem_types)
                    ):
                        check_type_fn(self, a, p_exp, param_name)
                else:
                    check_type_fn(self, a, p_exp, param_name)

        else:

            def check_list(self, a):
                if type(a) is list:
                    if a:
                        t = type(a[0])
                        if (
                            t is not elem_t0
                            and t is not elem_t1
                            and not isinstance(a[0], elem_types)
                        ):
                            check_type_fn(self, a, p_exp, param_name)
                else:
                    check_type_fn(self, a, p_exp, param_name)

    else:

        def check_list(self, a):
            if type(a) is list:
                for idx in get_sample_indices_fn(self, len(a)):
                    el = a[idx]
                    t = type(el)
                    if (
                        t is not elem_t0
                        and t is not elem_t1
                        and not isinstance(el, elem_types)
                    ):
                        check_type_fn(self, a, p_exp, param_name)
                        break
            else:
                check_type_fn(self, a, p_exp, param_name)

    if not has_self:
        if ret_mode == 0:

            def template(self, a):
                check_list(self, a)
                return fn(a)

        elif ret_mode == 1:

            def template(self, a):
                check_list(self, a)
                res = fn(a)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, a):
                check_list(self, a)
                res = fn(a)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

    else:
        if ret_mode == 0:

            def template(self, s, a):
                check_list(self, a)
                return fn(s, a)

        elif ret_mode == 1:

            def template(self, s, a):
                check_list(self, a)
                res = fn(s, a)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, s, a):
                check_list(self, a)
                res = fn(s, a)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

    return bind_parameter_names(template, param_names, defaults)


# --- Simple Dict 1-Arg Builders ---
def build_dict_1arg(
    fn,
    param_names,
    defaults,
    check_type_fn,
    p_exp,
    k_t0,
    k_t1,
    k_types,
    k_set,
    v_t0,
    v_t1,
    v_types,
    v_set,
    sample_pct,
    get_sample_keys_fn,
    ret_mode,
    ret_t0=None,
    ret_t1=None,
    ret_types=None,
    ret_exp=None,
    has_self=False,
):
    param_name = param_names[-1]
    if sample_pct == 100:

        def check_dict(self, a):
            if type(a) is dict:
                n = len(a)
                if n <= 20:
                    for dk in a:
                        dv = a[dk]
                        if (
                            type(dk) is not k_t0
                            and type(dk) is not k_t1
                            and not isinstance(dk, k_types)
                        ) or (
                            type(dv) is not v_t0
                            and type(dv) is not v_t1
                            and not isinstance(dv, v_types)
                        ):
                            check_type_fn(self, a, p_exp, param_name)
                            break
                else:
                    if not (
                        set(map(type, a)) <= k_set
                        and set(map(type, a.values())) <= v_set
                    ):
                        check_type_fn(self, a, p_exp, param_name)
            else:
                check_type_fn(self, a, p_exp, param_name)

    elif sample_pct == 0:

        def check_dict(self, a):
            if type(a) is dict:
                if a:
                    for dk in a:
                        if type(dk) is not k_t0 or type(a[dk]) is not v_t0:
                            if (
                                type(dk) is not k_t0
                                and type(dk) is not k_t1
                                and not isinstance(dk, k_types)
                            ) or (
                                type(a[dk]) is not v_t0
                                and type(a[dk]) is not v_t1
                                and not isinstance(a[dk], v_types)
                            ):
                                check_type_fn(self, a, p_exp, param_name)
                        break
            else:
                check_type_fn(self, a, p_exp, param_name)

    else:

        def check_dict(self, a):
            if type(a) is dict:
                for dk in get_sample_keys_fn(self, list(a.keys())):
                    dv = a[dk]
                    if (
                        type(dk) is not k_t0
                        and type(dk) is not k_t1
                        and not isinstance(dk, k_types)
                    ) or (
                        type(dv) is not v_t0
                        and type(dv) is not v_t1
                        and not isinstance(dv, v_types)
                    ):
                        check_type_fn(self, a, p_exp, param_name)
                        break
            else:
                check_type_fn(self, a, p_exp, param_name)

    if not has_self:
        if ret_mode == 0:

            def template(self, a):
                check_dict(self, a)
                return fn(a)

        elif ret_mode == 1:

            def template(self, a):
                check_dict(self, a)
                res = fn(a)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, a):
                check_dict(self, a)
                res = fn(a)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

    else:
        if ret_mode == 0:

            def template(self, s, a):
                check_dict(self, a)
                return fn(s, a)

        elif ret_mode == 1:

            def template(self, s, a):
                check_dict(self, a)
                res = fn(s, a)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, s, a):
                check_dict(self, a)
                res = fn(s, a)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

    return bind_parameter_names(template, param_names, defaults)


# --- Simple Set 1-Arg Builders ---
def build_set_1arg(
    fn,
    param_names,
    defaults,
    check_type_fn,
    p_exp,
    elem_t0,
    elem_t1,
    elem_types,
    elem_set,
    sample_pct,
    get_sample_indices_fn,
    ret_mode,
    ret_t0=None,
    ret_t1=None,
    ret_types=None,
    ret_exp=None,
    has_self=False,
):
    param_name = param_names[-1]
    if sample_pct == 100:

        def check_set(self, a):
            if type(a) is set:
                n = len(a)
                if n <= 20:
                    for el in a:
                        t = type(el)
                        if (
                            t is not elem_t0
                            and t is not elem_t1
                            and not isinstance(el, elem_types)
                        ):
                            check_type_fn(self, a, p_exp, param_name)
                            break
                else:
                    if not set(map(type, a)) <= elem_set:
                        check_type_fn(self, a, p_exp, param_name)
            else:
                check_type_fn(self, a, p_exp, param_name)

    elif sample_pct == 0:

        def check_set(self, a):
            if type(a) is set:
                if a:
                    el = next(iter(a))
                    t = type(el)
                    if (
                        t is not elem_t0
                        and t is not elem_t1
                        and not isinstance(el, elem_types)
                    ):
                        check_type_fn(self, a, p_exp, param_name)
            else:
                check_type_fn(self, a, p_exp, param_name)

    else:

        def check_set(self, a):
            if type(a) is set:
                a_list = list(a)
                for idx in get_sample_indices_fn(self, len(a_list)):
                    el = a_list[idx]
                    t = type(el)
                    if (
                        t is not elem_t0
                        and t is not elem_t1
                        and not isinstance(el, elem_types)
                    ):
                        check_type_fn(self, a, p_exp, param_name)
                        break
            else:
                check_type_fn(self, a, p_exp, param_name)

    if not has_self:
        if ret_mode == 0:

            def template(self, a):
                check_set(self, a)
                return fn(a)

        elif ret_mode == 1:

            def template(self, a):
                check_set(self, a)
                res = fn(a)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, a):
                check_set(self, a)
                res = fn(a)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

    else:
        if ret_mode == 0:

            def template(self, s, a):
                check_set(self, a)
                return fn(s, a)

        elif ret_mode == 1:

            def template(self, s, a):
                check_set(self, a)
                res = fn(s, a)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, s, a):
                check_set(self, a)
                res = fn(s, a)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

    return bind_parameter_names(template, param_names, defaults)


# --- Simple Var Tuple 1-Arg Builders ---
def build_var_tuple_1arg(
    fn,
    param_names,
    defaults,
    check_type_fn,
    p_exp,
    elem_t0,
    elem_t1,
    elem_types,
    elem_set,
    sample_pct,
    get_sample_indices_fn,
    ret_mode,
    ret_t0=None,
    ret_t1=None,
    ret_types=None,
    ret_exp=None,
    has_self=False,
):
    param_name = param_names[-1]
    if sample_pct == 100:

        def check_tuple(self, a):
            if type(a) is tuple:
                n = len(a)
                if n <= 20:
                    for el in a:
                        t = type(el)
                        if (
                            t is not elem_t0
                            and t is not elem_t1
                            and not isinstance(el, elem_types)
                        ):
                            check_type_fn(self, a, p_exp, param_name)
                            break
                else:
                    if not set(map(type, a)) <= elem_set:
                        check_type_fn(self, a, p_exp, param_name)
            else:
                check_type_fn(self, a, p_exp, param_name)

    elif sample_pct == 0:

        def check_tuple(self, a):
            if type(a) is tuple:
                if a:
                    t = type(a[0])
                    if (
                        t is not elem_t0
                        and t is not elem_t1
                        and not isinstance(a[0], elem_types)
                    ):
                        check_type_fn(self, a, p_exp, param_name)
            else:
                check_type_fn(self, a, p_exp, param_name)

    else:

        def check_tuple(self, a):
            if type(a) is tuple:
                for idx in get_sample_indices_fn(self, len(a)):
                    el = a[idx]
                    t = type(el)
                    if (
                        t is not elem_t0
                        and t is not elem_t1
                        and not isinstance(el, elem_types)
                    ):
                        check_type_fn(self, a, p_exp, param_name)
                        break
            else:
                check_type_fn(self, a, p_exp, param_name)

    if not has_self:
        if ret_mode == 0:

            def template(self, a):
                check_tuple(self, a)
                return fn(a)

        elif ret_mode == 1:

            def template(self, a):
                check_tuple(self, a)
                res = fn(a)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, a):
                check_tuple(self, a)
                res = fn(a)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

    else:
        if ret_mode == 0:

            def template(self, s, a):
                check_tuple(self, a)
                return fn(s, a)

        elif ret_mode == 1:

            def template(self, s, a):
                check_tuple(self, a)
                res = fn(s, a)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, s, a):
                check_tuple(self, a)
                res = fn(s, a)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

    return bind_parameter_names(template, param_names, defaults)


# --- Simple List of Dict 1-Arg Builders ---
def build_list_of_dict_1arg(
    fn,
    param_names,
    defaults,
    check_type_fn,
    p_exp,
    sub_k_t0,
    sub_k_t1,
    sub_k_types,
    sub_k_set,
    sub_v_t0,
    sub_v_t1,
    sub_v_types,
    sub_v_set,
    sample_pct,
    ret_mode,
    ret_t0=None,
    ret_t1=None,
    ret_types=None,
    ret_exp=None,
    has_self=False,
):
    param_name = param_names[-1]
    if sample_pct == 100:

        def check_list_of_dict(self, a):
            if type(a) is list:
                invalid = False
                for d in a:
                    if type(d) is not dict:
                        invalid = True
                        break
                    if len(d) <= 20:
                        for dk in d:
                            dv = d[dk]
                            if (
                                type(dk) is not sub_k_t0
                                and type(dk) is not sub_k_t1
                                and not isinstance(dk, sub_k_types)
                            ) or (
                                type(dv) is not sub_v_t0
                                and type(dv) is not sub_v_t1
                                and not isinstance(dv, sub_v_types)
                            ):
                                invalid = True
                                break
                        if invalid:
                            break
                    else:
                        if not (
                            set(map(type, d)) <= sub_k_set
                            and set(map(type, d.values())) <= sub_v_set
                        ):
                            invalid = True
                            break
                if invalid:
                    check_type_fn(self, a, p_exp, param_name)
            else:
                check_type_fn(self, a, p_exp, param_name)

    elif sample_pct == 0:

        def check_list_of_dict(self, a):
            if type(a) is list:
                if a:
                    d = a[0]
                    if type(d) is dict:
                        if d:
                            for dk in d:
                                if (
                                    type(dk) is not sub_k_t0
                                    or type(d[dk]) is not sub_v_t0
                                ):
                                    if (
                                        type(dk) is not sub_k_t0
                                        and type(dk) is not sub_k_t1
                                        and not isinstance(dk, sub_k_types)
                                    ) or (
                                        type(d[dk]) is not sub_v_t0
                                        and type(d[dk]) is not sub_v_t1
                                        and not isinstance(d[dk], sub_v_types)
                                    ):
                                        check_type_fn(
                                            self, a, p_exp, param_name
                                        )
                                break
                    else:
                        check_type_fn(self, a, p_exp, param_name)
            else:
                check_type_fn(self, a, p_exp, param_name)

    else:

        def check_list_of_dict(self, a):
            if type(a) is not list:
                check_type_fn(self, a, p_exp, param_name)

    if not has_self:
        if ret_mode == 0:

            def template(self, a):
                check_list_of_dict(self, a)
                return fn(a)

        elif ret_mode == 1:

            def template(self, a):
                check_list_of_dict(self, a)
                res = fn(a)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, a):
                check_list_of_dict(self, a)
                res = fn(a)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

    else:
        if ret_mode == 0:

            def template(self, s, a):
                check_list_of_dict(self, a)
                return fn(s, a)

        elif ret_mode == 1:

            def template(self, s, a):
                check_list_of_dict(self, a)
                res = fn(s, a)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, s, a):
                check_list_of_dict(self, a)
                res = fn(s, a)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

    return bind_parameter_names(template, param_names, defaults)


# --- Simple List of List 1-Arg Builders ---
def build_list_of_list_1arg(
    fn,
    param_names,
    defaults,
    check_type_fn,
    p_exp,
    elem_t0,
    elem_t1,
    elem_types,
    elem_set,
    sample_pct,
    ret_mode,
    ret_t0=None,
    ret_t1=None,
    ret_types=None,
    ret_exp=None,
    has_self=False,
):
    param_name = param_names[-1]
    if sample_pct == 100:

        def check_list_of_list(self, a):
            if type(a) is list:
                invalid = False
                for sub_l in a:
                    if type(sub_l) is not list:
                        invalid = True
                        break
                    if len(sub_l) <= 20:
                        for el in sub_l:
                            t = type(el)
                            if (
                                t is not elem_t0
                                and t is not elem_t1
                                and not isinstance(el, elem_types)
                            ):
                                invalid = True
                                break
                        if invalid:
                            break
                    else:
                        if not set(map(type, sub_l)) <= elem_set:
                            invalid = True
                            break
                if invalid:
                    check_type_fn(self, a, p_exp, param_name)
            else:
                check_type_fn(self, a, p_exp, param_name)

    elif sample_pct == 0:

        def check_list_of_list(self, a):
            if type(a) is list:
                if a:
                    sub_l = a[0]
                    if type(sub_l) is list:
                        if sub_l:
                            t = type(sub_l[0])
                            if (
                                t is not elem_t0
                                and t is not elem_t1
                                and not isinstance(sub_l[0], elem_types)
                            ):
                                check_type_fn(self, a, p_exp, param_name)
                    else:
                        check_type_fn(self, a, p_exp, param_name)
            else:
                check_type_fn(self, a, p_exp, param_name)

    else:

        def check_list_of_list(self, a):
            if type(a) is not list:
                check_type_fn(self, a, p_exp, param_name)

    if not has_self:
        if ret_mode == 0:

            def template(self, a):
                check_list_of_list(self, a)
                return fn(a)

        elif ret_mode == 1:

            def template(self, a):
                check_list_of_list(self, a)
                res = fn(a)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, a):
                check_list_of_list(self, a)
                res = fn(a)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

    else:
        if ret_mode == 0:

            def template(self, s, a):
                check_list_of_list(self, a)
                return fn(s, a)

        elif ret_mode == 1:

            def template(self, s, a):
                check_list_of_list(self, a)
                res = fn(s, a)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, s, a):
                check_list_of_list(self, a)
                res = fn(s, a)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

    return bind_parameter_names(template, param_names, defaults)


# --- Simple Dict of List 1-Arg Builders ---
def build_dict_of_list_1arg(
    fn,
    param_names,
    defaults,
    check_type_fn,
    p_exp,
    k_t0,
    k_t1,
    k_types,
    k_set,
    v_elem_t0,
    v_elem_t1,
    v_elem_types,
    v_elem_set,
    sample_pct,
    ret_mode,
    ret_t0=None,
    ret_t1=None,
    ret_types=None,
    ret_exp=None,
    has_self=False,
):
    param_name = param_names[-1]
    if sample_pct == 100:

        def check_dict_of_list(self, a):
            if type(a) is dict:
                invalid = False
                for dk in a:
                    dv = a[dk]
                    if (
                        type(dk) is not k_t0
                        and type(dk) is not k_t1
                        and not isinstance(dk, k_types)
                    ):
                        invalid = True
                        break
                    if type(dv) is not list:
                        invalid = True
                        break
                    if len(dv) <= 20:
                        for el in dv:
                            t = type(el)
                            if (
                                t is not v_elem_t0
                                and t is not v_elem_t1
                                and not isinstance(el, v_elem_types)
                            ):
                                invalid = True
                                break
                        if invalid:
                            break
                    else:
                        if not set(map(type, dv)) <= v_elem_set:
                            invalid = True
                            break
                if invalid:
                    check_type_fn(self, a, p_exp, param_name)
            else:
                check_type_fn(self, a, p_exp, param_name)

    elif sample_pct == 0:

        def check_dict_of_list(self, a):
            if type(a) is dict:
                if a:
                    for dk in a:
                        if (
                            type(dk) is not k_t0
                            and type(dk) is not k_t1
                            and not isinstance(dk, k_types)
                        ):
                            check_type_fn(self, a, p_exp, param_name)
                            break
                        dv = a[dk]
                        if type(dv) is list:
                            if dv:
                                t = type(dv[0])
                                if (
                                    t is not v_elem_t0
                                    and t is not v_elem_t1
                                    and not isinstance(dv[0], v_elem_types)
                                ):
                                    check_type_fn(self, a, p_exp, param_name)
                        else:
                            check_type_fn(self, a, p_exp, param_name)
                        break
            else:
                check_type_fn(self, a, p_exp, param_name)

    else:

        def check_dict_of_list(self, a):
            if type(a) is not dict:
                check_type_fn(self, a, p_exp, param_name)

    if not has_self:
        if ret_mode == 0:

            def template(self, a):
                check_dict_of_list(self, a)
                return fn(a)

        elif ret_mode == 1:

            def template(self, a):
                check_dict_of_list(self, a)
                res = fn(a)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, a):
                check_dict_of_list(self, a)
                res = fn(a)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

    else:
        if ret_mode == 0:

            def template(self, s, a):
                check_dict_of_list(self, a)
                return fn(s, a)

        elif ret_mode == 1:

            def template(self, s, a):
                check_dict_of_list(self, a)
                res = fn(s, a)
                if res is None:
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

        else:

            def template(self, s, a):
                check_dict_of_list(self, a)
                res = fn(s, a)
                if (
                    type(res) is ret_t0
                    or type(res) is ret_t1
                    or isinstance(res, ret_types)
                ):
                    return res
                check_type_fn(self, res, ret_exp, "return")
                return res

    return bind_parameter_names(template, param_names, defaults)
