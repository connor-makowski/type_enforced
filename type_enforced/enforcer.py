import collections.abc
import typing
from types import (
    FunctionType,
    MethodType,
    GeneratorType,
    BuiltinFunctionType,
    BuiltinMethodType,
    UnionType,
)
from typing import Type, Union, Sized, Literal, Callable, get_type_hints, Any
from functools import update_wrapper
from type_enforced.utils import (
    Partial,
    GenericConstraint,
    iterable_types,
    merge_type_dicts,
    has_cpp,
)
from type_enforced.specialized import (
    create_specialized_class,
    build_specialized_call,
    can_specialize_type,
    is_simple_type,
)
import sys
import traceback
import random
from itertools import islice
from pathlib import Path

if has_cpp():
    import type_enforced.cpp as _cpp
else:
    _cpp = None

__NoneType__ = type(None)


class __SelfType__:
    pass


class __NeverType__:
    pass


__package_path__ = Path(__file__).parent.resolve()
__CO_VARARGS__ = 0x04
__CO_VARKEYWORDS__ = 0x08
__NO_DEFAULT__ = object()


class FunctionMethodEnforcer:
    __slots__ = (
        "__fn__",
        "__strict__",
        "__clean_traceback__",
        "__iterable_sample_pct__",
        "__only_typed__",
        "__self_type__",
        "__fn_defaults__",
        "__fn_defaults_tuple__",
        "__fn_varnames__",
        "__types_parsed__",
        "__checkable_types__",
        "__return_type__",
        "__simple_return_type__",
        "__simple_return_t0__",
        "__has_none_return__",
        "__flat_subtypes__",
        "__keys_tuples__",
        "__simple_pos_params__",
        "__simple_kwonly_params__",
        "__complex_pos_params__",
        "__complex_kwonly_params__",
        "__has_complex_params__",
        "__has_simple_params__",
        "__single_simple_pos__",
        "__wrapped__",
        "__name__",
        "__qualname__",
        "__doc__",
        "__dict__",
    )

    def __init__(
        self,
        __fn__,
        __strict__=False,
        __clean_traceback__=True,
        __iterable_sample_pct__=100,
        __only_typed__=False,
        self_type=None,
    ):
        """
        Initialize a FunctionMethodEnforcer class object as a wrapper for a passed function `__fn__`.

        Requires:

            - `__fn__`:
                - What: The function to enforce
                - Type: function | method | class

        Optional:

            - `__strict__`:
                - What: A boolean to enable or disable exceptions. If True, exceptions will be raised
                    when type checking fails. If False, exceptions will not be raised but instead a warning
                    will be printed to the console.
                - Type: bool
                - Default: False
            - `__clean_traceback__`:
                - What: A boolean to enable or disable cleaning of tracebacks when raising exceptions.
                - Type: bool
                - Default: True
            - `__iterable_sample_pct__`:
                - What: Control how many items in iterables are checked during type enforcement.
                    Supports 'first' (first element), 'last' (last element), 'log' (sample of log n items),
                    0 (1 random sample), or an integer percentage 1..100 (rounding up).
                - Type: int | str
                - Default: 100
            - `__only_typed__`:
                - What: A boolean to enable or disable raising exceptions on untyped function/method parameters.
                - Type: bool
                - Default: False
        """
        update_wrapper(self, __fn__)
        self.__fn__ = __fn__
        self.__strict__ = __strict__
        self.__clean_traceback__ = __clean_traceback__
        self.__iterable_sample_pct__ = __iterable_sample_pct__
        self.__only_typed__ = __only_typed__
        self.__self_type__ = self_type
        self.__types_parsed__ = False
        self.__flat_subtypes__ = {}
        self.__keys_tuples__ = {}
        # Validate iterable_sample_pct
        if self.__iterable_sample_pct__ not in (
            "first",
            "last",
            "bookend",
            "bookend_plus",
            "log",
        ):
            if (
                not isinstance(self.__iterable_sample_pct__, int)
                or isinstance(self.__iterable_sample_pct__, bool)
                or not (0 <= self.__iterable_sample_pct__ <= 100)
            ):
                self.__exception__(
                    f"Invalid iterable_sample_pct `{self.__iterable_sample_pct__}`. Expected 'first', 'last', 'bookend', 'bookend_plus', 'log', or an integer between 0 and 100.",
                    raise_exception=True,
                )
        # Validate that the passed function or method is a method or function
        self.__check_method_function__()
        # Check only_typed if enabled
        if self.__only_typed__:
            self.__check_only_typed__()
        # Get input defaults for the function or method
        self.__get_defaults__()

    def __check_only_typed__(self):
        """
        Validate that all parameters and return of the wrapped function/method have type annotations.
        """
        type_hints = get_type_hints(self.__fn__)
        code = self.__fn__.__code__
        total_args = code.co_argcount + code.co_kwonlyargcount
        param_names = list(code.co_varnames[:total_args])
        # If the function accepts *args, include its variable name
        if code.co_flags & __CO_VARARGS__:
            param_names.append(code.co_varnames[total_args])
            total_args += 1
        # If the function accepts **kwargs, include its variable name
        if code.co_flags & __CO_VARKEYWORDS__:
            param_names.append(code.co_varnames[total_args])

        for name in param_names:
            if name in ("self", "cls"):
                continue
            if name not in type_hints:
                self.__exception__(
                    f"Untyped variable `{name}` found in function/method `{self.__fn__.__qualname__}`.",
                    raise_exception=True,
                )
        if "return" not in type_hints:
            self.__exception__(
                f"Untyped return value found in function/method `{self.__fn__.__qualname__}`.",
                raise_exception=True,
            )

    def __get_defaults__(self):
        """
        Processes default parameter values for the wrapped function/method.
        """
        self.__fn_varnames__ = self.__fn__.__code__.co_varnames
        self.__fn_defaults_tuple__ = self.__fn__.__defaults__
        self.__fn_defaults__ = {}
        if self.__fn__.__defaults__ is not None:
            # Get the names of all provided default values for args
            default_varnames = list(self.__fn_varnames__)[
                : self.__fn__.__code__.co_argcount
            ][-len(self.__fn__.__defaults__) :]
            # Update the output dictionary with the default values
            self.__fn_defaults__.update(
                dict(zip(default_varnames, self.__fn__.__defaults__))
            )
        if self.__fn__.__kwdefaults__ is not None:
            # Update the output dictionary with the keyword default values
            self.__fn_defaults__.update(self.__fn__.__kwdefaults__)

    def __get_sample_indices__(self, length):
        """
        Get sampled indices for sequence validation based on iterable_sample_pct.
        """
        if length == 0:
            return []
        pct = self.__iterable_sample_pct__
        if pct == "first":
            return [0]
        if pct == "last":
            return [length - 1]
        if pct == "bookend":
            if length <= 2:
                return list(range(length))
            return [0, length - 1]
        if pct == "bookend_plus":
            if length <= 3:
                return list(range(length))
            return [0, length - 1, random.randrange(1, length - 1)]
        if pct == 0:
            return [random.randrange(length)]
        if pct == "log":
            count = max(1, (length - 1).bit_length())
        else:
            count = max(1, (length * pct + 99) // 100)
        if count >= length:
            return range(length)
        if count == 1:
            return [0]
        if count == 2:
            return [0, length - 1]
        step = max(1, (length - 1) // (count - 1))
        return [0, length - 1] + list(range(step, length - 1, step))

    def __get_sample_keys__(self, keys):
        """
        Get sampled keys for dict validation based on iterable_sample_pct.
        """
        if isinstance(keys, dict):
            if not keys:
                return []
            l = len(keys)
            pct = self.__iterable_sample_pct__
            if pct == "first" or l == 1:
                return [next(iter(keys))]
            if pct == "last":
                return [next(reversed(keys))]
            if pct == "bookend":
                return list(islice(keys.keys(), 2))
            if pct == "bookend_plus":
                return list(islice(keys.keys(), 3))
            if pct == 0:
                return [next(islice(keys, random.randrange(l), None))]
            if pct == "log":
                count = max(1, (l - 1).bit_length())
            else:
                count = max(1, (l * pct + 99) // 100)
            if count >= l:
                return list(keys.keys())
            if count == 1:
                return [next(iter(keys))]
            if count == 2:
                return [next(iter(keys)), next(reversed(keys))]
            return [next(iter(keys)), next(reversed(keys))] + list(
                islice(keys, 1, count - 1)
            )
        elif len(keys) == 0:
            return []
        else:
            l = len(keys)
            pct = self.__iterable_sample_pct__
            if pct == "first" or l == 1:
                return [keys[0]]
            if pct == "last":
                return [keys[-1]]
            if pct == "bookend":
                if l <= 2:
                    return list(keys) if isinstance(keys, set) else keys
                if isinstance(keys, set):
                    it = iter(keys)
                    k0 = next(it)
                    klast = None
                    for klast in it:
                        pass
                    return [k0, klast]
                return [keys[0], keys[-1]]
            if pct == "bookend_plus":
                if l <= 3:
                    return list(keys) if isinstance(keys, set) else keys
                if isinstance(keys, set):
                    it = iter(keys)
                    k0 = next(it)
                    mid_idx = random.randrange(1, l - 1)
                    kmid = None
                    klast = None
                    for idx, cur in enumerate(it, 1):
                        if idx == mid_idx:
                            kmid = cur
                        klast = cur
                    return [k0, klast, kmid]
                return [keys[0], keys[-1], keys[random.randrange(1, l - 1)]]
            if pct == 0:
                return [keys[random.randrange(l)]]
            if pct == "log":
                count = max(1, (l - 1).bit_length())
            else:
                count = max(1, (l * pct + 99) // 100)
            if count >= l:
                return keys
            if count == 1:
                return [keys[0]]
            if count == 2:
                return [keys[0], keys[-1]]
            return [keys[0], keys[-1]] + list(islice(keys, 1, count - 1))

    def __get_checkable_types__(self):
        """
        Creates class attributes for validation.
        """
        if not self.__types_parsed__:
            self.__checkable_types__ = {
                key: self.__get_checkable_type__(value)
                for key, value in get_type_hints(self.__fn__).items()
            }
            self.__return_type__ = self.__checkable_types__.pop("return", None)

            # Pre-classify parameters into simple vs complex positional/keyword-only list configurations
            self.__simple_pos_params__ = []
            self.__simple_kwonly_params__ = []
            self.__complex_pos_params__ = []
            self.__complex_kwonly_params__ = []

            co_argcount = self.__fn__.__code__.co_argcount
            co_kwonlyargcount = self.__fn__.__code__.co_kwonlyargcount

            for key, expected in self.__checkable_types__.items():
                if key not in self.__fn_varnames__:
                    continue
                idx = self.__fn_varnames__.index(key)
                is_pos = (idx < co_argcount) or (
                    idx >= co_argcount + co_kwonlyargcount
                )

                is_simple = (
                    "__extra__" not in expected
                    and all(v is None for v in expected.values())
                    and all(
                        isinstance(k, type)
                        and k not in (__SelfType__, __NeverType__)
                        for k in expected.keys()
                    )
                )

                if is_simple:
                    types_tuple = tuple(expected.keys())
                    t0 = types_tuple[0]
                    if is_pos:
                        self.__simple_pos_params__.append(
                            (key, idx, types_tuple, t0)
                        )
                    else:
                        self.__simple_kwonly_params__.append(
                            (key, types_tuple, t0)
                        )
                else:
                    if is_pos:
                        self.__complex_pos_params__.append((key, idx, expected))
                    else:
                        self.__complex_kwonly_params__.append((key, expected))

            self.__has_complex_params__ = bool(
                self.__complex_pos_params__ or self.__complex_kwonly_params__
            )
            self.__has_simple_params__ = bool(
                self.__simple_pos_params__ or self.__simple_kwonly_params__
            )

            if (
                not self.__has_complex_params__
                and len(self.__simple_pos_params__) == 1
                and not self.__simple_kwonly_params__
            ):
                self.__single_simple_pos__ = self.__simple_pos_params__[0]
            else:
                self.__single_simple_pos__ = None

            # Same classification for return type
            if self.__return_type__ is not None and (
                "__extra__" not in self.__return_type__
                and all(v is None for v in self.__return_type__.values())
                and all(
                    isinstance(k, type)
                    and k not in (__SelfType__, __NeverType__)
                    for k in self.__return_type__.keys()
                )
            ):
                self.__simple_return_type__ = tuple(self.__return_type__.keys())
                self.__simple_return_t0__ = self.__simple_return_type__[0]
            else:
                self.__simple_return_type__ = None
                self.__simple_return_t0__ = None
            self.__types_parsed__ = True

    def __get_checkable_type__(self, annotation):
        """
        Parses a type annotation and returns a nested dict structure
        representing the checkable type(s) for validation.
        """
        if annotation is None:
            return {__NoneType__: None}

        if annotation is Any:
            return {object: None}

        # Handle typing.Self (PEP 673)
        self_type_obj = getattr(typing, "Self", None)
        if (
            self_type_obj is not None and annotation is self_type_obj
        ) or annotation == "Self":
            return {__SelfType__: None}

        # Handle typing.NoReturn and typing.Never (PEP 484 / PEP 654)
        never_types = tuple(
            t
            for t in (
                getattr(typing, "NoReturn", None),
                getattr(typing, "Never", None),
            )
            if t is not None
        )
        if annotation in never_types:
            return {__NeverType__: None}

        # Handle typing.LiteralString (PEP 675)
        lit_str_obj = getattr(typing, "LiteralString", None)
        if lit_str_obj is not None and annotation is lit_str_obj:
            return {str: None}

        # Handle PEP 695 TypeAliasType (Python 3.12+)
        if (
            hasattr(annotation, "__value__")
            and type(annotation).__name__ == "TypeAliasType"
        ):
            return self.__get_checkable_type__(annotation.__value__)

        # Handle NewType (PEP 484)
        if hasattr(annotation, "__supertype__"):
            return self.__get_checkable_type__(annotation.__supertype__)

        # Handle TypeVar (PEP 484 / PEP 695 generic parameters)
        if isinstance(annotation, typing.TypeVar):
            if annotation.__bound__ is not None:
                return self.__get_checkable_type__(annotation.__bound__)
            elif annotation.__constraints__:
                combined_types = {}
                for constraint in annotation.__constraints__:
                    merge_type_dicts(
                        combined_types,
                        self.__get_checkable_type__(constraint),
                    )
                return combined_types
            else:
                return {object: None}

        # Handle ParamSpec and TypeVarTuple
        param_specs = tuple(
            p
            for p in (
                getattr(typing, "ParamSpec", None),
                getattr(typing, "TypeVarTuple", None),
            )
            if p is not None
        )
        if param_specs and isinstance(annotation, param_specs):
            return {object: None}

        # Handle TypedDict (PEP 589)
        if getattr(typing, "is_typeddict", lambda x: False)(annotation):
            td_hints = get_type_hints(annotation)
            fields = {
                k: self.__get_checkable_type__(v) for k, v in td_hints.items()
            }
            req_keys = getattr(
                annotation,
                "__required_keys__",
                frozenset(
                    annotation.__annotations__.keys()
                    if getattr(annotation, "__total__", True)
                    else ()
                ),
            )
            return {
                "__extra__": {
                    "__typeddict__": {
                        "cls": annotation,
                        "fields": fields,
                        "required": req_keys,
                    }
                },
                dict: None,
            }

        # Handle `int | str` syntax (Python 3.10+) and Unions
        if (
            isinstance(annotation, UnionType)
            or getattr(annotation, "__origin__", None) == Union
        ):
            combined_types = {}
            for sub_type in annotation.__args__:
                merge_type_dicts(
                    combined_types,
                    self.__get_checkable_type__(sub_type),
                )
            return combined_types

        # Handle typing.Literal
        if getattr(annotation, "__origin__", None) == Literal:
            return {"__extra__": {"__literal__": list(annotation.__args__)}}

        # Handle generic collections
        origin = getattr(annotation, "__origin__", None)
        args = getattr(annotation, "__args__", ())

        # Handle TypeGuard (PEP 647) and TypeIs (PEP 742)
        type_guards = tuple(
            tg
            for tg in (
                getattr(typing, "TypeGuard", None),
                getattr(typing, "TypeIs", None),
            )
            if tg is not None
        )
        if origin is not None and origin in type_guards:
            return {bool: None}

        if origin == list:
            if len(args) != 1:
                self.__exception__(
                    f"List must have a single type argument, got: {args}",
                    raise_exception=True,
                )
            return {list: self.__get_checkable_type__(args[0])}

        if origin == dict:
            if len(args) != 2:
                self.__exception__(
                    f"Dict must have two type arguments, got: {args}",
                    raise_exception=True,
                )
            key_type = self.__get_checkable_type__(args[0])
            value_type = self.__get_checkable_type__(args[1])
            return {dict: (key_type, value_type)}

        if origin == tuple:
            if len(args) > 2 or len(args) == 1:
                if Ellipsis in args:
                    self.__exception__(
                        "Tuple with Ellipsis must have exactly two type arguments and the second must be Ellipsis.",
                        raise_exception=True,
                    )
            if len(args) == 2:
                if args[0] is Ellipsis:
                    self.__exception__(
                        "Tuple with Ellipsis must have exactly two type arguments and the first must not be Ellipsis.",
                        raise_exception=True,
                    )
                if args[1] is Ellipsis:
                    return {tuple: (self.__get_checkable_type__(args[0]), True)}
            return {
                tuple: (
                    tuple(self.__get_checkable_type__(arg) for arg in args),
                    False,
                )
            }

        if origin == set:
            if len(args) != 1:
                self.__exception__(
                    f"Set must have a single type argument, got: {args}",
                    raise_exception=True,
                )
            return {set: self.__get_checkable_type__(args[0])}

        # Handle Sized types
        if annotation == Sized:
            return {
                list: None,
                tuple: None,
                dict: None,
                set: None,
                str: None,
                bytes: None,
                bytearray: None,
                memoryview: None,
                range: None,
            }

        # Handle Callable types (unsubscripted or subscripted: Callable[[int, str], bool], Callable[..., int], etc.)
        if annotation is Callable or origin in (
            Callable,
            getattr(collections.abc, "Callable", None),
        ):
            return {
                staticmethod: None,
                classmethod: None,
                FunctionType: None,
                BuiltinFunctionType: None,
                MethodType: None,
                BuiltinMethodType: None,
                GeneratorType: None,
                FunctionMethodEnforcer: None,
                "__extra__": {"__callable__": True},
            }

        # Handle Constraints
        if isinstance(annotation, GenericConstraint):
            return {"__extra__": {"__constraints__": [annotation]}}

        # Handle typing.Type (unsubscripted)
        if annotation is Type:
            return {type: None}

        # Handle standard types
        if isinstance(annotation, type) and annotation is not Type:
            return {annotation: None}

        # Handle typing.Type and type[T] (for uninitialized classes)
        if origin is type and len(args) == 1:
            target = args[0]
            if target is Any or target is object:
                return {type: None}
            if (
                isinstance(target, UnionType)
                or getattr(target, "__origin__", None) == Union
            ):
                combined_types = {}
                for sub_type in target.__args__:
                    if sub_type is Any or sub_type is object:
                        combined_types[type] = None
                    else:
                        combined_types[Type[sub_type]] = None
                return combined_types
            return {Type[target]: None}

        self.__exception__(
            f"Unsupported type hint: {annotation}", raise_exception=True
        )

    def __exception__(self, message, raise_exception=False):
        """
        Usage:

        - Creates a class based exception message

        Requires:

        - `message`:
            - Type: str
            - What: The message to warn users with

        Optional:

        - `raise_exception`:
            - Type: bool
            - What: Forces an exception to be raised regardless of the `self.__strict__` setting.
            - Default: False
        """
        if self.__strict__ or raise_exception:
            msg = f"TypeEnforced Exception ({self.__fn__.__qualname__}): {message}"
            if self.__clean_traceback__:
                package_path = __package_path__
                frame = sys._getframe()
                relevant_tb_count = 0
                while frame is not None:
                    frame_file = Path(frame.f_code.co_filename).resolve()
                    try:
                        frame_file.relative_to(package_path)
                    except ValueError:
                        relevant_tb_count += 1
                    frame = frame.f_back
                original_excepthook = sys.excepthook

                def excepthook(type, value, tb):
                    traceback.print_exception(
                        type, value, tb, limit=relevant_tb_count
                    )
                    sys.excepthook = original_excepthook

                sys.excepthook = excepthook
            raise TypeError(msg)
        else:
            print(
                f"TypeEnforced Warning ({self.__fn__.__qualname__}): {message}"
            )

    def __get__(self, obj, objtype=None, _mt=MethodType):
        """
        Overwrite standard __get__ method to return bound MethodType instead of wrapper function.
        """
        if self.__self_type__ is None and objtype is not None:
            self.__self_type__ = objtype
        if obj is None:
            return self
        return _mt(self, obj)

    def __check_method_function__(self):
        """
        Validate that `self.__fn__` is a method or function
        """
        if not isinstance(self.__fn__, (MethodType, FunctionType)):
            raise Exception(
                f"A non function/method was passed to Enforcer. See the stack trace above for more information."
            )

    def __specialize__(self):
        """
        Dynamically constructs and binds a specialized subclass based on the function's signature
        and type annotations to achieve maximum validation performance without code generation.
        """
        code = self.__fn__.__code__
        posonly_count = code.co_posonlyargcount
        arg_count = code.co_argcount
        kwonly_count = code.co_kwonlyargcount
        flags = code.co_flags
        has_varargs = bool(flags & __CO_VARARGS__)
        has_varkw = bool(flags & __CO_VARKEYWORDS__)

        posonly_names = tuple(self.__fn_varnames__[:posonly_count])
        pos_names = tuple(self.__fn_varnames__[posonly_count:arg_count])
        kwonly_names = tuple(
            self.__fn_varnames__[arg_count : arg_count + kwonly_count]
        )

        idx = arg_count + kwonly_count
        vararg_name = self.__fn_varnames__[idx] if has_varargs else None
        if has_varargs:
            idx += 1
        kwarg_name = self.__fn_varnames__[idx] if has_varkw else None

        ret_mode = 0
        ret_t0 = None
        ret_t1 = None
        ret_types = None
        ret_exp = None

        if self.__return_type__ is not None:
            ret_exp = self.__return_type__
            if (
                len(self.__return_type__) == 1
                and __NoneType__ in self.__return_type__
                and self.__return_type__[__NoneType__] is None
            ):
                ret_mode = 1
            elif (
                len(self.__return_type__) == 1
                and __SelfType__ in self.__return_type__
                and (posonly_names or pos_names)
            ):
                ret_mode = 3
            elif (
                isinstance(self.__return_type__, dict)
                and "__extra__" in self.__return_type__
                and bool(self.__return_type__["__extra__"].get("__callable__"))
            ):
                ret_mode = 5
            elif is_simple_type(self.__return_type__):
                ret_mode = 2
                ret_types = tuple(self.__return_type__.keys())
                ret_t0 = ret_types[0]
                ret_t1 = ret_types[1] if len(ret_types) > 1 else None
            elif can_specialize_type(self.__return_type__):
                ret_mode = 6
            else:
                return

        param_exps = {}
        for pn in posonly_names + pos_names + kwonly_names:
            exp = self.__checkable_types__.get(pn)
            if not can_specialize_type(exp):
                return
            if exp is not None:
                param_exps[pn] = exp

        if vararg_name is not None and vararg_name in self.__checkable_types__:
            raw_exp = self.__checkable_types__[vararg_name]
            if not can_specialize_type(raw_exp):
                return
            param_exps[vararg_name] = {tuple: (raw_exp, True)}

        if kwarg_name is not None and kwarg_name in self.__checkable_types__:
            raw_exp = self.__checkable_types__[kwarg_name]
            if not can_specialize_type(raw_exp):
                return
            param_exps[kwarg_name] = {dict: ({str: None}, raw_exp)}

        defaults = self.__fn_defaults_tuple__
        kwdefaults = getattr(self.__fn__, "__kwdefaults__", None)
        check_fn = FunctionMethodEnforcer.__check_type__

        call_method = build_specialized_call(
            self.__fn__,
            posonly_names,
            pos_names,
            kwonly_names,
            vararg_name,
            kwarg_name,
            defaults,
            kwdefaults,
            param_exps,
            check_fn,
            self.__iterable_sample_pct__,
            FunctionMethodEnforcer.__get_sample_indices__,
            FunctionMethodEnforcer.__get_sample_keys__,
            ret_mode,
            ret_t0,
            ret_t1,
            ret_types,
            ret_exp,
        )
        if call_method is not None:
            self.__class__ = create_specialized_class(
                FunctionMethodEnforcer,
                self.__fn__.__qualname__,
                call_method,
            )
            return

    def __call__(self, *args, **kwargs):
        """
        This method is used to validate the passed inputs and return the output of the wrapped function or method.
        """
        if not self.__types_parsed__:
            self.__get_checkable_types__()
            self.__specialize__()
            return self(*args, **kwargs)

        if self.__self_type__ is None and args:
            first_arg = args[0]
            self.__self_type__ = (
                first_arg
                if isinstance(first_arg, type)
                else first_arg.__class__
            )

        if self.__has_complex_params__:
            for key, idx, expected in self.__complex_pos_params__:
                if idx < len(args):
                    obj = args[idx]
                elif key in kwargs:
                    obj = kwargs[key]
                else:
                    obj = self.__fn_defaults__.get(key)
                self.__check_type__(obj, expected, key)

            for key, expected in self.__complex_kwonly_params__:
                if key in kwargs:
                    obj = kwargs[key]
                else:
                    obj = self.__fn_defaults__.get(key)
                self.__check_type__(obj, expected, key)

        if self.__has_simple_params__:
            for key, idx, types_tuple, t0 in self.__simple_pos_params__:
                if idx < len(args):
                    obj = args[idx]
                elif key in kwargs:
                    obj = kwargs[key]
                else:
                    obj = self.__fn_defaults__.get(key)
                if type(obj) is not t0 and not isinstance(obj, types_tuple):
                    self.__check_type__(obj, self.__checkable_types__[key], key)

            for key, types_tuple, t0 in self.__simple_kwonly_params__:
                if key in kwargs:
                    obj = kwargs[key]
                else:
                    obj = self.__fn_defaults__.get(key)
                if type(obj) is not t0 and not isinstance(obj, types_tuple):
                    self.__check_type__(obj, self.__checkable_types__[key], key)

        return_value = self.__fn__(*args, **kwargs)

        if self.__return_type__ is not None:
            if (
                self.__self_type__ is None
                and __SelfType__ in self.__return_type__
                and args
            ):
                first_arg = args[0]
                self.__self_type__ = (
                    first_arg
                    if isinstance(first_arg, type)
                    else first_arg.__class__
                )

            if self.__simple_return_type__ is not None:
                if type(
                    return_value
                ) is not self.__simple_return_t0__ and not isinstance(
                    return_value, self.__simple_return_type__
                ):
                    self.__check_type__(
                        return_value, self.__return_type__, "return"
                    )
            else:
                self.__check_type__(
                    return_value, self.__return_type__, "return"
                )
        return return_value

    def __quick_check__(self, subtype, obj):
        subtype_id = id(subtype)
        if subtype_id not in self.__flat_subtypes__:
            # First call for this subtype: compute and cache
            if all(v is None for v in subtype.values()):
                keys_tuple = tuple(subtype.keys())
                keys_set = frozenset(subtype.keys())
                single_type = keys_tuple[0] if len(keys_tuple) == 1 else None
                self.__flat_subtypes__[subtype_id] = (
                    keys_set,
                    keys_tuple,
                    single_type,
                )
            else:
                self.__flat_subtypes__[subtype_id] = None
        cached = self.__flat_subtypes__[subtype_id]
        if cached is not None:
            flat_set, flat_tuple, single_type = cached
            n = len(obj)
            if n <= 10:
                if single_type is not None:
                    for x in obj:
                        if type(x) is not single_type:
                            return False
                    return True
                else:
                    for x in obj:
                        t = type(x)
                        if t not in flat_set:
                            return False
                    return True
            else:
                return flat_set.issuperset(map(type, obj))
        return False

    def __is_valid_item__(self, item, expected):
        """
        Check whether item satisfies expected type dict without raising exceptions.
        """
        if item is None and __NoneType__ in expected:
            return True
        if __NeverType__ in expected:
            return False
        extra = expected.get("__extra__")

        if isinstance(item, type):
            obj_type = Type[item]
            is_present = obj_type in expected or type in expected
        else:
            obj_type = type(item)
            if __SelfType__ in expected:
                target_cls = getattr(self, "__self_type__", None)
                if target_cls is not None and isinstance(item, target_cls):
                    is_present = True
                else:
                    is_present = False
            else:
                expected_id = id(expected)
                keys_tuple = self.__keys_tuples__.get(expected_id)
                if keys_tuple is None:
                    keys_tuple = tuple(
                        k
                        for k in expected.keys()
                        if k != "__extra__" and isinstance(k, type)
                    )
                    self.__keys_tuples__[expected_id] = keys_tuple
                is_present = obj_type in expected or (
                    bool(keys_tuple) and isinstance(item, keys_tuple)
                )

        if not is_present:
            if (
                extra is not None
                and extra.get("__callable__")
                and callable(item)
            ):
                is_present = True

        if not is_present:
            literal = extra.get("__literal__", ()) if extra is not None else ()
            if literal and item in literal:
                pass
            else:
                return False

        if extra is not None and "__typeddict__" in extra:
            td_info = extra["__typeddict__"]
            if not isinstance(item, dict):
                return False
            req_keys = td_info["required"]
            fields = td_info["fields"]
            if req_keys - set(item.keys()):
                return False
            for fk, fval in item.items():
                if fk in fields and not self.__is_valid_item__(
                    fval, fields[fk]
                ):
                    return False

        if obj_type in iterable_types:
            subtype = expected.get(obj_type, None)
            if subtype is not None:
                if isinstance(subtype, list):
                    if not any(
                        self.__validate_collection_variant__(item, obj_type, v)
                        for v in subtype
                    ):
                        return False
                else:
                    if not self.__validate_collection_variant__(
                        item, obj_type, subtype
                    ):
                        return False

        if extra is not None:
            constraints = extra.get("__constraints__", ())
            for constraint in constraints:
                if constraint.__validate__("", item) is not True:
                    return False
        return True

    def __validate_collection_variant__(self, obj, obj_type, variant):
        """
        Check whether an iterable object matches a specific collection schema variant.
        """
        sample_pct = self.__iterable_sample_pct__

        if obj_type == list:
            if isinstance(variant, dict) and all(
                v is None for v in variant.values()
            ):
                tt = tuple(variant.keys())
                if sample_pct == 100:
                    if _cpp is not None:
                        if len(tt) == 1:
                            return _cpp.validate_list_single(obj, tt[0])
                        return _cpp.validate_list_union(obj, tt)
                elif sample_pct == "first":
                    if _cpp is not None:
                        if len(tt) == 1:
                            return _cpp.validate_list_first(obj, tt[0])
                        return _cpp.validate_list_first_union(obj, tt)
                elif sample_pct == "last":
                    if _cpp is not None:
                        if len(tt) == 1:
                            return _cpp.validate_list_last(obj, tt[0])
                        return _cpp.validate_list_last_union(obj, tt)
                elif sample_pct == "bookend":
                    if _cpp is not None:
                        if len(tt) == 1:
                            return _cpp.validate_list_bookend(obj, tt[0])
                        return _cpp.validate_list_bookend_union(obj, tt)
                elif sample_pct == "bookend_plus":
                    if _cpp is not None:
                        if len(tt) == 1:
                            return _cpp.validate_list_bookend_plus(obj, tt[0])
                        return _cpp.validate_list_bookend_plus_union(obj, tt)
                elif isinstance(sample_pct, int) and sample_pct > 0:
                    count = max(1, (len(obj) * sample_pct + 99) // 100)
                    if _cpp is not None:
                        if len(tt) == 1:
                            return _cpp.validate_list_sample(obj, tt[0], count)
                        return _cpp.validate_list_sample_union(obj, tt, count)
                elif sample_pct == "log":
                    count = max(1, (len(obj) - 1).bit_length())
                    if _cpp is not None:
                        if len(tt) == 1:
                            return _cpp.validate_list_sample(obj, tt[0], count)
                        return _cpp.validate_list_sample_union(obj, tt, count)
            elif (
                _cpp is not None
                and sample_pct == 100
                and isinstance(variant, dict)
                and len(variant) == 1
            ):
                vk = next(iter(variant))
                vv = variant[vk]
                if vk is list and is_simple_type(vv) and len(vv) == 1:
                    return _cpp.validate_list_list(obj, tuple(vv.keys())[0])
                elif (
                    vk is dict
                    and isinstance(vv, tuple)
                    and len(vv) == 2
                    and is_simple_type(vv[0])
                    and len(vv[0]) == 1
                    and is_simple_type(vv[1])
                    and len(vv[1]) == 1
                ):
                    return _cpp.validate_list_dict(
                        obj, tuple(vv[0].keys())[0], tuple(vv[1].keys())[0]
                    )
                elif (
                    vk is tuple
                    and isinstance(vv, tuple)
                    and len(vv) == 2
                    and vv[1] is False
                    and isinstance(vv[0], tuple)
                    and all(is_simple_type(a) and len(a) == 1 for a in vv[0])
                ):
                    return _cpp.validate_list_tuple_fixed(
                        obj, tuple(tuple(a.keys())[0] for a in vv[0])
                    )

            if sample_pct != 100:
                for idx in self.__get_sample_indices__(len(obj)):
                    if not self.__is_valid_item__(obj[idx], variant):
                        return False
                return True
            if self.__quick_check__(variant, obj):
                return True
            for item in obj:
                if not self.__is_valid_item__(item, variant):
                    return False
            return True

        elif obj_type == dict:
            key_type, val_type = variant
            if (
                isinstance(key_type, dict)
                and all(v is None for v in key_type.values())
                and isinstance(val_type, dict)
                and all(v is None for v in val_type.values())
            ):
                k_tt = tuple(key_type.keys())
                v_tt = tuple(val_type.keys())
                if sample_pct == 100:
                    if _cpp is not None:
                        if len(k_tt) == 1 and len(v_tt) == 1:
                            return _cpp.validate_dict_single(
                                obj, k_tt[0], v_tt[0]
                            )
                        return _cpp.validate_dict_unions(obj, k_tt, v_tt)
                elif sample_pct != 0 and sample_pct != "last":
                    count = (
                        1
                        if sample_pct == "first"
                        else (
                            2
                            if sample_pct == "bookend"
                            else (
                                3
                                if sample_pct == "bookend_plus"
                                else (
                                    max(1, (len(obj) - 1).bit_length())
                                    if sample_pct == "log"
                                    else max(
                                        1, (len(obj) * sample_pct + 99) // 100
                                    )
                                )
                            )
                        )
                    )
                    if _cpp is not None:
                        if len(k_tt) == 1 and len(v_tt) == 1:
                            return _cpp.validate_dict_sample(
                                obj, k_tt[0], v_tt[0], count
                            )
                        return _cpp.validate_dict_sample_unions(
                            obj, k_tt, v_tt, count
                        )
            elif (
                _cpp is not None
                and sample_pct == 100
                and is_simple_type(key_type)
                and len(key_type) == 1
                and isinstance(val_type, dict)
                and len(val_type) == 1
                and list in val_type
                and is_simple_type(val_type[list])
                and len(val_type[list]) == 1
            ):
                return _cpp.validate_dict_list(
                    obj,
                    tuple(key_type.keys())[0],
                    tuple(val_type[list].keys())[0],
                )

            if sample_pct != 100:
                sampled_keys = self.__get_sample_keys__(obj)
                if not isinstance(sampled_keys, list):
                    sampled_keys = list(sampled_keys)
                for dk in sampled_keys:
                    if not self.__is_valid_item__(dk, key_type):
                        return False
                    if not self.__is_valid_item__(obj[dk], val_type):
                        return False
                return True
            for dk, dv in obj.items():
                if not self.__is_valid_item__(dk, key_type):
                    return False
                if not self.__is_valid_item__(dv, val_type):
                    return False
            return True

        elif obj_type == tuple:
            expected_args, is_ellipsis = variant
            if is_ellipsis:
                if isinstance(expected_args, dict) and all(
                    v is None for v in expected_args.values()
                ):
                    tt = tuple(expected_args.keys())
                    if sample_pct == 100:
                        if _cpp is not None:
                            if len(tt) == 1:
                                return _cpp.validate_tuple_single(obj, tt[0])
                            return _cpp.validate_tuple_union(obj, tt)
                    elif sample_pct == "first":
                        if _cpp is not None:
                            if len(tt) == 1:
                                return _cpp.validate_tuple_first(obj, tt[0])
                            return _cpp.validate_tuple_first_union(obj, tt)
                    elif sample_pct == "last":
                        if _cpp is not None:
                            if len(tt) == 1:
                                return _cpp.validate_tuple_last(obj, tt[0])
                            return _cpp.validate_tuple_last_union(obj, tt)
                    elif sample_pct == "bookend":
                        if _cpp is not None:
                            if len(tt) == 1:
                                return _cpp.validate_tuple_bookend(obj, tt[0])
                            return _cpp.validate_tuple_bookend_union(obj, tt)
                    elif sample_pct == "bookend_plus":
                        if _cpp is not None:
                            if len(tt) == 1:
                                return _cpp.validate_tuple_bookend_plus(
                                    obj, tt[0]
                                )
                            return _cpp.validate_tuple_bookend_plus_union(
                                obj, tt
                            )
                    elif isinstance(sample_pct, int) and sample_pct > 0:
                        count = max(1, (len(obj) * sample_pct + 99) // 100)
                        if _cpp is not None:
                            if len(tt) == 1:
                                return _cpp.validate_tuple_sample(
                                    obj, tt[0], count
                                )
                            return _cpp.validate_tuple_sample_union(
                                obj, tt, count
                            )
                    elif sample_pct == "log":
                        count = max(1, (len(obj) - 1).bit_length())
                        if _cpp is not None:
                            if len(tt) == 1:
                                return _cpp.validate_tuple_sample(
                                    obj, tt[0], count
                                )
                            return _cpp.validate_tuple_sample_union(
                                obj, tt, count
                            )

                if sample_pct != 100:
                    for idx in self.__get_sample_indices__(len(obj)):
                        if not self.__is_valid_item__(obj[idx], expected_args):
                            return False
                    return True
                if self.__quick_check__(expected_args, obj):
                    return True
                for item in obj:
                    if not self.__is_valid_item__(item, expected_args):
                        return False
                return True
            else:
                if len(obj) != len(expected_args):
                    return False
                if _cpp is not None and all(
                    isinstance(a, dict)
                    and len(a) == 1
                    and all(v is None for v in a.values())
                    for a in expected_args
                ):
                    types_tuple = tuple(
                        tuple(a.keys())[0] for a in expected_args
                    )
                    return _cpp.validate_tuple_fixed(obj, types_tuple)
                for idx in range(len(expected_args)):
                    if not self.__is_valid_item__(obj[idx], expected_args[idx]):
                        return False
                return True

        elif obj_type == set:
            if isinstance(variant, dict) and all(
                v is None for v in variant.values()
            ):
                tt = tuple(variant.keys())
                if sample_pct == 100:
                    if _cpp is not None:
                        if len(tt) == 1:
                            return _cpp.validate_set_single(obj, tt[0])
                        return _cpp.validate_set_union(obj, tt)
                elif sample_pct != 0:
                    count = (
                        1
                        if sample_pct in ("first", "last")
                        else (
                            2
                            if sample_pct == "bookend"
                            else (
                                3
                                if sample_pct == "bookend_plus"
                                else (
                                    max(1, (len(obj) - 1).bit_length())
                                    if sample_pct == "log"
                                    else max(
                                        1, (len(obj) * sample_pct + 99) // 100
                                    )
                                )
                            )
                        )
                    )
                    if _cpp is not None:
                        if len(tt) == 1:
                            return _cpp.validate_set_sample(obj, tt[0], count)
                        return _cpp.validate_set_sample_union(obj, tt, count)

            if sample_pct != 100:
                if sample_pct == "first":
                    if len(obj) > 0:
                        return self.__is_valid_item__(next(iter(obj)), variant)
                    return True
                elif sample_pct == "last":
                    if len(obj) > 0:
                        item = None
                        for item in obj:
                            pass
                        return self.__is_valid_item__(item, variant)
                    return True
                elif sample_pct == "bookend":
                    for item in islice(obj, 2):
                        if not self.__is_valid_item__(item, variant):
                            return False
                    return True
                elif sample_pct == "bookend_plus":
                    for item in islice(obj, 3):
                        if not self.__is_valid_item__(item, variant):
                            return False
                    return True
                elif sample_pct == 0:
                    if len(obj) > 0:
                        item = next(
                            islice(obj, random.randrange(len(obj)), None)
                        )
                        return self.__is_valid_item__(item, variant)
                    return True
                elif sample_pct == "log":
                    count = max(1, (len(obj) - 1).bit_length())
                    for item in islice(obj, count):
                        if not self.__is_valid_item__(item, variant):
                            return False
                    return True
                else:
                    count = max(
                        1,
                        (len(obj) * sample_pct + 99) // 100,
                    )
                    for item in islice(obj, count):
                        if not self.__is_valid_item__(item, variant):
                            return False
                    return True
            if self.__quick_check__(variant, obj):
                return True
            for item in obj:
                if not self.__is_valid_item__(item, variant):
                    return False
            return True

        return False

    def __check_type__(self, obj, expected, key):
        """
        Raises an exception if the type of a passed `obj` (parameter) is not in the list of supplied `acceptable_types` for the argument.
        """
        # Special case for None
        if obj is None and __NoneType__ in expected:
            return
        if __NeverType__ in expected:
            if isinstance(key, tuple):

                def flatten_key(k):
                    if isinstance(k, tuple):
                        return "".join(flatten_key(x) for x in k)
                    return str(k)

                key = flatten_key(key)
            self.__exception__(
                f"Type mismatch for typed variable `{key}`. Expected `NoReturn` / `Never` but got `{type(obj)}` with value `{obj}` instead."
            )
            return

        extra = expected.get("__extra__")

        if isinstance(obj, type):
            # An uninitialized class is passed, we need to check if the type is in the expected types using Type[obj]
            obj_type = Type[obj]
            is_present = obj_type in expected or type in expected
        else:
            obj_type = type(obj)
            if __SelfType__ in expected:
                target_cls = getattr(self, "__self_type__", None)
                if target_cls is not None and isinstance(obj, target_cls):
                    is_present = True
                else:
                    is_present = False
            else:
                expected_id = id(expected)
                keys_tuple = self.__keys_tuples__.get(expected_id)
                if keys_tuple is None:
                    keys_tuple = tuple(
                        k
                        for k in expected.keys()
                        if k != "__extra__" and isinstance(k, type)
                    )
                    self.__keys_tuples__[expected_id] = keys_tuple
                is_present = obj_type in expected or (
                    bool(keys_tuple) and isinstance(obj, keys_tuple)
                )

        if not is_present:
            if (
                extra is not None
                and extra.get("__callable__")
                and callable(obj)
            ):
                is_present = True

        if not is_present:
            # Resolve key dynamically if it is a tuple (lazy f-string alternative)
            if isinstance(key, tuple):

                def flatten_key(k):
                    if isinstance(k, tuple):
                        return "".join(flatten_key(x) for x in k)
                    return str(k)

                key = flatten_key(key)

            # Allow for literals to be used to bypass type checks if present
            literal = extra.get("__literal__", ()) if extra is not None else ()
            if __SelfType__ in expected:
                target_cls = getattr(self, "__self_type__", None)
                expected_keys = (
                    [target_cls] if target_cls is not None else ["Self"]
                )
            else:
                expected_keys = [k for k in expected if k != "__extra__"]
            if literal:
                if obj not in literal:
                    self.__exception__(
                        f"Type mismatch for typed variable `{key}`. Expected one of the following `{expected_keys}` or a literal value in `{literal}` but got type `{obj_type}` with value `{obj}` instead."
                    )
            # Raise an exception if the type is not in the expected types
            else:
                self.__exception__(
                    f"Type mismatch for typed variable `{key}`. Expected one of the following `{expected_keys}` but got `{obj_type}` with value `{obj}` instead."
                )
        # If the object_type is in the expected types, we can proceed with validation
        elif obj_type in iterable_types:
            subtype = expected.get(obj_type, None)
            if subtype is None:
                pass
            elif isinstance(subtype, list):
                # Multi-variant collection union: obj must match at least one variant
                if not any(
                    self.__validate_collection_variant__(obj, obj_type, v)
                    for v in subtype
                ):
                    if isinstance(key, tuple):

                        def flatten_key(k):
                            if isinstance(k, tuple):
                                return "".join(flatten_key(x) for x in k)
                            return str(k)

                        key = flatten_key(key)
                    self.__exception__(
                        f"Type mismatch for typed variable `{key}`. Value `{obj}` did not match any of the expected `{obj_type.__name__}` variants."
                    )
            # Recursive validation
            elif obj_type == list:
                if self.__iterable_sample_pct__ != 100:
                    for idx in self.__get_sample_indices__(len(obj)):
                        self.__check_type__(
                            obj[idx], subtype, (key, "[", idx, "]")
                        )
                # If the subtype does not contain iterables with typing, we can validate the items directly.
                elif not self.__quick_check__(subtype, obj):
                    for idx, item in enumerate(obj):
                        self.__check_type__(item, subtype, (key, "[", idx, "]"))
            elif obj_type == dict:
                key_type, val_type = subtype
                if self.__iterable_sample_pct__ != 100:
                    sampled_keys = self.__get_sample_keys__(obj)
                    if not isinstance(sampled_keys, list):
                        sampled_keys = list(sampled_keys)
                    if not self.__quick_check__(key_type, sampled_keys):
                        for dk in sampled_keys:
                            self.__check_type__(
                                dk, key_type, (key, ".key[", repr(dk), "]")
                            )
                    if not self.__quick_check__(
                        val_type, [obj[dk] for dk in sampled_keys]
                    ):
                        for dk in sampled_keys:
                            self.__check_type__(
                                obj[dk], val_type, (key, "[", repr(dk), "]")
                            )
                else:
                    if not self.__quick_check__(key_type, obj.keys()):
                        for dk in obj.keys():
                            self.__check_type__(
                                dk, key_type, (key, ".key[", repr(dk), "]")
                            )
                    if not self.__quick_check__(val_type, obj.values()):
                        for dk, value in obj.items():
                            self.__check_type__(
                                value, val_type, (key, "[", repr(dk), "]")
                            )
            elif obj_type == tuple:
                expected_args, is_ellipsis = subtype
                if is_ellipsis:
                    if self.__iterable_sample_pct__ != 100:
                        for idx in self.__get_sample_indices__(len(obj)):
                            self.__check_type__(
                                obj[idx],
                                expected_args,
                                (key, "[", idx, "]"),
                            )
                    elif not self.__quick_check__(expected_args, obj):
                        for idx, item in enumerate(obj):
                            self.__check_type__(
                                item, expected_args, (key, "[", idx, "]")
                            )
                else:
                    if len(obj) != len(expected_args):
                        if isinstance(key, tuple):

                            def flatten_key(k):
                                if isinstance(k, tuple):
                                    return "".join(flatten_key(x) for x in k)
                                return str(k)

                            key = flatten_key(key)
                        self.__exception__(
                            f"Tuple length mismatch for `{key}`. Expected length {len(expected_args)}, got {len(obj)}"
                        )
                    for idx in range(len(expected_args)):
                        self.__check_type__(
                            obj[idx], expected_args[idx], (key, "[", idx, "]")
                        )
            elif obj_type == set:
                if self.__iterable_sample_pct__ != 100:
                    if self.__iterable_sample_pct__ == "first":
                        if len(obj) > 0:
                            item = next(iter(obj))
                            self.__check_type__(
                                item, subtype, (key, "[", repr(item), "]")
                            )
                    elif self.__iterable_sample_pct__ == "last":
                        if len(obj) > 0:
                            item = None
                            for item in obj:
                                pass
                            self.__check_type__(
                                item, subtype, (key, "[", repr(item), "]")
                            )
                    elif self.__iterable_sample_pct__ == "bookend":
                        for item in islice(obj, 2):
                            self.__check_type__(
                                item, subtype, (key, "[", repr(item), "]")
                            )
                    elif self.__iterable_sample_pct__ == "bookend_plus":
                        for item in islice(obj, 3):
                            self.__check_type__(
                                item, subtype, (key, "[", repr(item), "]")
                            )
                    elif self.__iterable_sample_pct__ == 0:
                        if len(obj) > 0:
                            item = next(
                                islice(obj, random.randrange(len(obj)), None)
                            )
                            self.__check_type__(
                                item, subtype, (key, "[", repr(item), "]")
                            )
                    elif self.__iterable_sample_pct__ == "log":
                        count = max(1, (len(obj) - 1).bit_length())
                        for item in islice(obj, count):
                            self.__check_type__(
                                item, subtype, (key, "[", repr(item), "]")
                            )
                    else:
                        count = max(
                            1,
                            (len(obj) * self.__iterable_sample_pct__ + 99)
                            // 100,
                        )
                        for item in islice(obj, count):
                            self.__check_type__(
                                item, subtype, (key, "[", repr(item), "]")
                            )
                elif not self.__quick_check__(subtype, obj):
                    for item in obj:
                        self.__check_type__(
                            item, subtype, (key, "[", repr(item), "]")
                        )

        # Validate TypedDict if present in extra
        if extra is not None and "__typeddict__" in extra:
            td_info = extra["__typeddict__"]
            req_keys = td_info["required"]
            fields = td_info["fields"]
            missing = req_keys - set(obj.keys())
            if missing:
                if isinstance(key, tuple):

                    def flatten_key(k):
                        if isinstance(k, tuple):
                            return "".join(flatten_key(x) for x in k)
                        return str(k)

                    key = flatten_key(key)

                missing_str = ", ".join(repr(k) for k in sorted(missing))
                self.__exception__(
                    f"TypedDict `{td_info['cls'].__name__}` validation error for variable `{key}`: missing required key(s): {missing_str}."
                )
            for fk, fval in obj.items():
                if fk in fields:
                    self.__check_type__(
                        fval, fields[fk], (key, "[", repr(fk), "]")
                    )

        # Validate constraints if any are present
        if extra is not None:
            constraints = extra.get("__constraints__", ())
            for constraint in constraints:
                if isinstance(key, tuple):

                    def flatten_key(k):
                        if isinstance(k, tuple):
                            return "".join(flatten_key(x) for x in k)
                        return str(k)

                    key = flatten_key(key)
                constraint_validation_output = constraint.__validate__(key, obj)
                if constraint_validation_output is not True:
                    self.__exception__(
                        f"Constraint validation error for variable `{key}` with value `{obj}`. {constraint_validation_output}"
                    )

    def __repr__(self):
        return f"<type_enforced {self.__fn__.__module__}.{self.__fn__.__qualname__} object at {hex(id(self))}>"


@Partial
def Enforcer(
    clsFnMethod,
    enabled=True,
    strict=True,
    clean_traceback=True,
    iterable_sample_pct=100,
    only_typed=False,
    self_type=None,
):
    """
    A wrapper to enforce types within a function, method, or class.

    Each wrapped callable is converted into a `FunctionMethodEnforcer` object.
    When applied to a class, all methods are wrapped individually.

    Requires:

    - `clsFnMethod`:
        - What: The class, function, or method that should have types enforced.
        - Type: function | method | class

    Optional:

    - `enabled`:
        - What: A boolean to enable or disable the enforcer
        - Type: bool
        - Default: True
    - `strict`:
        - What: A boolean to enable or disable exceptions. If True, exceptions will be raised when type checking fails. If False, exceptions will not be raised but instead a warning will be printed to the console.
        - Type: bool
        - Default: True
    - `clean_traceback`:
        - What: A boolean to enable or disable cleaning of tracebacks when raising exceptions.
        - If True, modifies the excepthook temporarily such that only the relevant stack (not in the type_enforced package) is shown.
        - Type: bool
        - Default: True
    - `iterable_sample_pct`:
        - What: Control how many items in iterables are checked during type enforcement.
            Supports 'first' (first element), 'last' (last element), 'log' (sample of log n items),
            0 (1 random sample), or an integer percentage 1..100 (rounding up).
        - Type: int | str
        - Default: 100
    - `only_typed`:
        - What: A boolean to enable or disable raising exceptions on untyped function/method parameters.
        - Type: bool
        - Default: False


    Example Use:
    ```
    >>> import type_enforced
    >>> @type_enforced.Enforcer
    ... def my_fn(a: int , b: int | str =2, c: int =3) -> None:
    ...     pass
    ...
    >>> my_fn(a=1, b=2, c=3)
    >>> my_fn(a=1, b='2', c=3)
    >>> my_fn(a='a', b=2, c=3)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      ...
    TypeError: TypeEnforced Exception (my_fn): Type mismatch for typed variable `a`. Expected one of the following `[<class 'int'>]` but got `<class 'str'>` with value `a` instead.
    ```
    """
    if not hasattr(clsFnMethod, "__type_enforced_enabled__"):
        # Special try except clause to handle cases when the object is immutable
        try:
            clsFnMethod.__type_enforced_enabled__ = enabled
        except:
            return clsFnMethod
    if not clsFnMethod.__type_enforced_enabled__:
        return clsFnMethod
    if isinstance(
        clsFnMethod, (staticmethod, classmethod, FunctionType, MethodType)
    ):
        # Only apply the enforcer if type_hints are present, unless only_typed is True
        # Add try except clause to better handle forward refs.
        try:
            if not only_typed and get_type_hints(clsFnMethod) == {}:
                return clsFnMethod
        except:
            pass
        if isinstance(clsFnMethod, staticmethod):
            return staticmethod(
                FunctionMethodEnforcer(
                    __fn__=clsFnMethod.__func__,
                    __strict__=strict,
                    __clean_traceback__=clean_traceback,
                    __iterable_sample_pct__=iterable_sample_pct,
                    __only_typed__=only_typed,
                    self_type=self_type,
                )
            )
        elif isinstance(clsFnMethod, classmethod):
            return classmethod(
                FunctionMethodEnforcer(
                    __fn__=clsFnMethod.__func__,
                    __strict__=strict,
                    __clean_traceback__=clean_traceback,
                    __iterable_sample_pct__=iterable_sample_pct,
                    __only_typed__=only_typed,
                    self_type=self_type,
                )
            )
        else:
            return FunctionMethodEnforcer(
                __fn__=clsFnMethod,
                __strict__=strict,
                __clean_traceback__=clean_traceback,
                __iterable_sample_pct__=iterable_sample_pct,
                __only_typed__=only_typed,
                self_type=self_type,
            )
    elif hasattr(clsFnMethod, "__dict__"):
        for key, value in clsFnMethod.__dict__.items():
            # Skip the __annotate__ method if present in __dict__ as it deletes itself upon invocation
            # Skip any previously wrapped methods if they are already a FunctionMethodEnforcer
            if key == "__annotate__" or isinstance(
                value, FunctionMethodEnforcer
            ):
                continue
            if hasattr(value, "__call__") or isinstance(
                value, (classmethod, staticmethod)
            ):
                setattr(
                    clsFnMethod,
                    key,
                    Enforcer(
                        value,
                        enabled=enabled,
                        strict=strict,
                        clean_traceback=clean_traceback,
                        iterable_sample_pct=iterable_sample_pct,
                        only_typed=only_typed,
                        self_type=clsFnMethod,
                    ),
                )
        return clsFnMethod
    else:
        raise Exception(
            "Enforcer can only be used on classes, methods, or functions."
        )


FAST_SAMPLE_OPTIONS = frozenset(
    {"first", "last", "bookend", "bookend_plus", "log", 0}
)


@Partial
def FastEnforcer(
    clsFnMethod,
    enabled=True,
    strict=True,
    clean_traceback=True,
    iterable_sample_pct="first",
    only_typed=False,
    self_type=None,
):
    """
    A fast wrapper to enforce types within a function, method, or class with fast sampling by default.

    Validates scalar types strictly and samples collections in constant or logarithmic time (checking the first item by default).

    Allowed iterable_sample_pct values: 'first', 'last', 'bookend', 'bookend_plus', 'log', 0.

    Requires:

    - `clsFnMethod`:
        - What: The class, function, or method that should have types enforced.
        - Type: function | method | class

    Optional:

    - `enabled`:
        - What: A boolean to enable or disable the enforcer
        - Type: bool
        - Default: True
    - `strict`:
        - What: A boolean to enable or disable exceptions. If True, exceptions will be raised when type checking fails. If False, exceptions will not be raised but instead a warning will be printed to the console.
        - Type: bool
        - Default: True
    - `clean_traceback`:
        - What: A boolean to enable or disable cleaning of tracebacks when raising exceptions.
        - Type: bool
        - Default: True
    - `iterable_sample_pct`:
        - What: Control how many items in iterables are checked during type enforcement.
            FastEnforcer strictly supports 'first' (first element), 'last' (last element),
            'bookend' (first and last), 'bookend_plus' (first, last, plus one random),
            'log' (sample of log n items), or 0 (1 random sample).
        - Type: int | str
        - Default: 'first'
    - `only_typed`:
        - What: A boolean to enable or disable raising exceptions on untyped function/method parameters.
        - Type: bool
        - Default: False
    """
    if iterable_sample_pct not in FAST_SAMPLE_OPTIONS or isinstance(
        iterable_sample_pct, bool
    ):
        raise TypeError(
            f"Invalid iterable_sample_pct `{iterable_sample_pct}` for FastEnforcer. "
            f"FastEnforcer only supports fast sampling options: 'first', 'last', 'bookend', 'bookend_plus', 'log', or 0."
        )
    return Enforcer(
        clsFnMethod,
        enabled=enabled,
        strict=strict,
        clean_traceback=clean_traceback,
        iterable_sample_pct=iterable_sample_pct,
        only_typed=only_typed,
        self_type=self_type,
    )
