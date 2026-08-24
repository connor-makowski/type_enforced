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

__NoneType__ = type(None)
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
        self.__types_parsed__ = False
        self.__flat_subtypes__ = {}
        self.__keys_tuples__ = {}
        # Validate iterable_sample_pct
        if self.__iterable_sample_pct__ not in ("first", "last", "log"):
            if (
                not isinstance(self.__iterable_sample_pct__, int)
                or isinstance(self.__iterable_sample_pct__, bool)
                or not (0 <= self.__iterable_sample_pct__ <= 100)
            ):
                self.__exception__(
                    f"Invalid iterable_sample_pct `{self.__iterable_sample_pct__}`. Expected 'first', 'last', 'log', or an integer between 0 and 100.",
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
                    and all(isinstance(k, type) for k in expected.keys())
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
                    isinstance(k, type) for k in self.__return_type__.keys()
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

        # Handle Callable types
        if annotation == Callable:
            return {
                staticmethod: None,
                classmethod: None,
                FunctionType: None,
                BuiltinFunctionType: None,
                MethodType: None,
                BuiltinMethodType: None,
                GeneratorType: None,
            }

        if annotation == Any:
            return {
                object: None,
            }

        # Handle Constraints
        if isinstance(annotation, GenericConstraint):
            return {"__extra__": {"__constraints__": [annotation]}}

        # Handle typing.Type (unsubscripted)
        if annotation is Type:
            return {type: None}

        # Handle standard types
        if isinstance(annotation, type):
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

    def __get__(self, obj, objtype):
        """
        Overwrite standard __get__ method to return bound MethodType instead of wrapper function.
        """
        if obj is None:
            return self
        return MethodType(self, obj)

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
        argcount = code.co_argcount
        kwonlyargcount = code.co_kwonlyargcount
        flags = code.co_flags
        has_varargs = bool(flags & __CO_VARARGS__)
        has_varkw = bool(flags & __CO_VARKEYWORDS__)

        if has_varargs or has_varkw or kwonlyargcount > 0:
            return

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
            elif is_simple_type(self.__return_type__):
                ret_mode = 2
                ret_types = tuple(self.__return_type__.keys())
                ret_t0 = ret_types[0]
                ret_t1 = ret_types[1] if len(ret_types) > 1 else None
            else:
                return

        defaults = self.__fn_defaults_tuple__
        check_fn = FunctionMethodEnforcer.__check_type__

        param_names = []
        param_exps = []
        for i in range(argcount):
            pn = self.__fn_varnames__[i]
            exp = self.__checkable_types__.get(pn)
            if not can_specialize_type(exp):
                return
            param_names.append(pn)
            param_exps.append(exp)

        call_method = build_specialized_call(
            self.__fn__,
            tuple(param_names),
            defaults,
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
                if set(map(type, obj)) <= flat_set:
                    return True
        return False

    def __check_type__(self, obj, expected, key):
        """
        Raises an exception if the type of a passed `obj` (parameter) is not in the list of supplied `acceptable_types` for the argument.
        """
        # Special case for None
        if obj is None and __NoneType__ in expected:
            return
        extra = expected.get("__extra__")

        if isinstance(obj, type):
            # An uninitialized class is passed, we need to check if the type is in the expected types using Type[obj]
            obj_type = Type[obj]
            is_present = obj_type in expected or type in expected
        else:
            obj_type = type(obj)
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
            # Resolve key dynamically if it is a tuple (lazy f-string alternative)
            if isinstance(key, tuple):

                def flatten_key(k):
                    if isinstance(k, tuple):
                        return "".join(flatten_key(x) for x in k)
                    return str(k)

                key = flatten_key(key)

            # Allow for literals to be used to bypass type checks if present
            literal = extra.get("__literal__", ()) if extra is not None else ()
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
                )
            )
        else:
            return FunctionMethodEnforcer(
                __fn__=clsFnMethod,
                __strict__=strict,
                __clean_traceback__=clean_traceback,
                __iterable_sample_pct__=iterable_sample_pct,
                __only_typed__=only_typed,
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
                    ),
                )
        return clsFnMethod
    else:
        raise Exception(
            "Enforcer can only be used on classes, methods, or functions."
        )
