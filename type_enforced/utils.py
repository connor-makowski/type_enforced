import types, re, copy
from functools import update_wrapper
from typing import Union


class Partial:
    """
    A special class wrapper to allow for easy partial function wrappings and calls.
    """

    def __init__(
        self,
        __fn__,
        *__args__,
        **__kwargs__,
    ):
        update_wrapper(self, __fn__)
        self.__fn__ = __fn__
        self.__args__ = __args__
        self.__kwargs__ = __kwargs__
        self.__fnArity__ = self.__getFnArity__()
        self.__arity__ = self.__getArity__(__args__, __kwargs__)
        self.__get_fn_arg_default_keys__()

    def __exception__(self, message):
        pre_message = (
            f"({self.__fn__.__module__}.{self.__fn__.__qualname__}_partial): "
        )
        raise Exception(pre_message + message)

    def __call__(self, *args, **kwargs):
        new_args = self.__args__ + args
        new_kwargs = {**self.__kwargs__, **kwargs}
        # Create a comprehensive set of assigned variable names to determine arity
        assigned_vars = set(
            self.__fn_arg_default_keys__
            + self.__fn_arg_keys__[: len(new_args)]
            + list(new_kwargs.keys())
        )
        arity = self.__fnArity__ - len(assigned_vars)
        if arity < 0:
            self.__exception__("Too many arguments were supplied")
        if arity == 0:
            results = self.__fn__(*new_args, **new_kwargs)
            return results
        return Partial(
            self.__fn__,
            *new_args,
            **new_kwargs,
        )

    def __get_fn_arg_default_keys__(self):
        """
        Get the default values of the passed function or method and store them in `self.__fn_defaults__`.
        """
        self.__fn_var_keys__ = list(self.__fn__.__code__.co_varnames)
        self.__fn_arg_keys__ = self.__fn_var_keys__[
            : self.__fn__.__code__.co_argcount
        ]
        if self.__fn__.__defaults__ is not None:
            self.__fn_arg_default_keys__ = self.__fn_arg_keys__[
                -len(self.__fn__.__defaults__) :
            ]
        else:
            self.__fn_arg_default_keys__ = []
        if self.__fn__.__kwdefaults__ is not None:
            self.__fn_arg_default_keys__.extend(
                list(self.__fn__.__kwdefaults__.keys())
            )

    def __get__(self, instance, owner):
        def bind(*args, **kwargs):
            if instance is not None and self.__arity__ == self.__fnArity__:
                return self.__call__(instance, *args, **kwargs)
            else:
                return self.__call__(*args, **kwargs)

        return bind

    def __repr__(self):
        return f"<Partial {self.__fn__.__module__}.{self.__fn__.__qualname__} object at {hex(id(self))}>"

    def __getArity__(self, args, kwargs):
        return self.__fnArity__ - (len(args) + len(kwargs))

    def __getFnArity__(self):
        if not isinstance(self.__fn__, (types.MethodType, types.FunctionType)):
            self.__exception__(
                "A non function was passed as a function and does not have any arity. See the stack trace above for more information."
            )
        extra_method_input_count = (
            1 if isinstance(self.__fn__, (types.MethodType)) else 0
        )
        return self.__fn__.__code__.co_argcount - extra_method_input_count


class GenericConstraint:
    def __init__(self, constraints: dict):
        """
        Creates a generic constraint object that can be used to validate a value against a set of constraints.

        Required Arguments:

        - `constraints`:
            - What: A dictionary of constraint names and their associated functions.
            - Type: dict
            - Note: All values in the dictionary must be functions that take a single argument and return a boolean.
            - Note: The dictionary keys will be used to identify the failed constraints in the error messages.
        """
        assert all(
            hasattr(v, "__call__") for v in constraints.values()
        ), "All constraints must be functions."
        self.__constraint_checks__ = constraints

    def __validate__(self, varname, value):
        for check_name, check_func in self.__constraint_checks__.items():
            try:
                if not check_func(value):
                    return f"Constraint `{check_name}` not met with the provided value `{value}`"
            except Exception as e:
                return f"An exception was raised when checking the constraint `{check_name}` with the provided value `{value}`. Error: {e}"
        return True

    def __ror__(self, other):
        """
        Allows the use of | operator to combine GenericConstraints via a union.
        """
        return Union[other, self]


class Constraint(GenericConstraint):
    def __init__(
        self,
        pattern: str | None = None,
        includes: list | tuple | set | None = None,
        excludes: list | tuple | set | None = None,
        gt: float | int | None = None,
        lt: float | int | None = None,
        ge: float | int | None = None,
        le: float | int | None = None,
        eq: float | int | None = None,
        ne: float | int | None = None,
    ):
        """
        Creates a constraint object that can be used to validate a value against a set of constraints.

        Optional Arguments:

        - `pattern`:
            - What: A regex pattern that the value must match.
            - Type: str or None
            - Default: None
        - `includes`:
            - What: A list of values that the value must be in.
            - Type: list, tuple, set or None
            - Default: None
        - `excludes`:
            - What: A list of values that the value must not be in.
            - Type: list, tuple, set or None
            - Default: None
        - `gt`:
            - What: The value must be greater than this value.
            - Type: float, int or None
            - Default: None
        - `lt`:
            - What: The value must be less than this value.
            - Type: float, int or None
            - Default: None
        - `ge`:
            - What: The value must be greater than or equal to this value.
            - Type: float, int or None
            - Default: None
        - `le`:
            - What: The value must be less than or equal to this value.
            - Type: float, int or None
            - Default: None
        - `eq`:
            - What: The value must be equal to this value.
            - Type: float, int or None
            - Default: None
        - `ne`:
            - What: The value must not be equal to this value.
            - Type: float, int or None
            - Default: None
        """
        assert any(
            v is not None
            for v in [pattern, gt, lt, ge, le, eq, ne, includes, excludes]
        ), "At least one constraint must be provided."
        assert isinstance(
            includes, (list, tuple, set, type(None))
        ), "Includes must be a list, tuple, set or None."
        assert isinstance(
            excludes, (list, tuple, set, type(None))
        ), "Excludes must be a list, tuple, set or None."
        assert isinstance(
            pattern, (str, type(None))
        ), "Pattern must be a string or None."
        assert isinstance(
            gt, (float, int, type(None))
        ), "Greater than constraint must be a float, int or None."
        assert isinstance(
            lt, (float, int, type(None))
        ), "Less than constraint must be a float, int or None."
        assert isinstance(
            ge, (float, int, type(None))
        ), "Greater or equal to constraint must be a float, int or None."
        assert isinstance(
            le, (float, int, type(None))
        ), "Less than or equal to constraint must be a float, int or None."
        assert isinstance(
            eq, (float, int, type(None))
        ), "Equal to constraint must be a float, int or None."
        assert isinstance(
            ne, (float, int, type(None))
        ), "Not equal to constraint must be a float, int or None."
        self.__constraint_checks__ = {}
        if pattern is not None:
            self.__constraint_checks__["be a string"] = lambda x: isinstance(
                x, str
            )
            self.__constraint_checks__["Regex Pattern Match"] = lambda x: bool(
                re.findall(pattern, x)
            )
        if includes is not None:
            self.__constraint_checks__[f"Includes"] = lambda x: x in includes
        if excludes is not None:
            self.__constraint_checks__["Excludes"] = lambda x: x not in excludes
        if gt is not None:
            self.__constraint_checks__[f"Greater Than ({gt})"] = (
                lambda x: x > gt
            )
        if lt is not None:
            self.__constraint_checks__[f"Less Than ({lt})"] = lambda x: x < lt
        if ge is not None:
            self.__constraint_checks__[f"Greater Than Or Equal To ({ge})"] = (
                lambda x: x >= ge
            )
        if le is not None:
            self.__constraint_checks__[f"Less Than Or Equal To ({le})"] = (
                lambda x: x <= le
            )
        if eq is not None:
            self.__constraint_checks__[f"Equal To ({eq})"] = lambda x: x == eq
        if ne is not None:
            self.__constraint_checks__[f"Not Equal To ({ne})"] = (
                lambda x: x != ne
            )


def DeepMerge(original: dict, update: dict):
    """
    Merge two dictionaries together, recursively merging any nested dictionaries and extending any nested lists.

    Required Arguments:

    - `original`:
        - What: The original dictionary to merge the update into.
        - Type: dict
    - `update`:
        - What: The dictionary to merge into the original dictionary.
        - Type: dict
    """
    original = copy.deepcopy(original)
    for key, value in update.items():
        if (
            key in original
            and isinstance(original[key], dict)
            and isinstance(value, dict)
        ):
            original[key] = DeepMerge(original[key], value)
        elif (
            key in original
            and isinstance(original[key], list)
            and isinstance(value, list)
        ):
            original[key].extend(value)
        else:
            original[key] = value
    return original


def WithSubclasses(cls):
    """
    A utility class to preserve backwards compatibility
    with the older versions of type_enforced.

    By default subclasses of all classes are now enforced by type_enforced.

    It is slated to be removed in the next major version.
    """
    # TODO: Remove this in the next major version of type_enforced
    return cls


iterable_types = set([list, tuple, set, dict])
