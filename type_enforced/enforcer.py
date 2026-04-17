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
import sys, traceback, random
from pathlib import Path

_NoneType = type(None)
_package_path = Path(__file__).parent.resolve()


class FunctionMethodEnforcer:
    __slots__ = (
        "__fn__",
        "__strict__",
        "__clean_traceback__",
        "__iterable_sample_pct__",
        "__outer_self__",
        "__fn_defaults__",
        "__fn_varnames__",
        "__types_parsed__",
        "__checkable_types__",
        "__return_type__",
        "__simple_types__",
        "__complex_types__",
        "__simple_return_type__",
        "__param_indices__",
        "__flat_subtypes__",
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
                - What: The percentage of items to sample when validating iterables. If 100, all items
                    are validated. If less than 100, the first and last items are always validated
                    plus a random sample of the remaining items up to the specified percentage.
                - Type: int | float
                - Default: 100
        """
        update_wrapper(self, __fn__)
        self.__fn__ = __fn__
        self.__strict__ = __strict__
        self.__clean_traceback__ = __clean_traceback__
        self.__iterable_sample_pct__ = __iterable_sample_pct__
        self.__outer_self__ = None
        self.__types_parsed__ = False
        self.__flat_subtypes__ = {}
        # Validate that the passed function or method is a method or function
        self.__check_method_function__()
        # Get input defaults for the function or method
        self.__get_defaults__()

    def __get_defaults__(self):
        """
        Get the default values of the passed function or method and store them in `self.__fn_defaults__`.
        Also caches the function's variable names for use in `__call__`.
        """
        self.__fn_varnames__ = self.__fn__.__code__.co_varnames
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
        Get a sorted list of indices to sample for iterable validation.

        If iterable_sample_pct is 0, only the first item (index 0) is checked.
        Otherwise, always includes the first (0) and last (length-1) indices.
        If length > 3, samples additional middle indices up to the
        iterable_sample_pct percentage.
        Only called when self.__iterable_sample_pct__ < 100.
        """
        if length == 0:
            return []
        if self.__iterable_sample_pct__ == 0:
            return [0]
        if length <= 3:
            return range(length)
        n = max(3, int(length * self.__iterable_sample_pct__ / 100))
        if n >= length:
            return range(length)
        middle_sample = random.sample(range(1, length - 1), n - 2)
        return sorted([0] + middle_sample + [length - 1])

    def __get_sample_keys__(self, keys):
        """
        Get a sampled list of dict keys for iterable validation.

        If iterable_sample_pct is 0, only the first key is returned.
        Otherwise, always includes the first key plus a random sample of
        the remaining keys up to the iterable_sample_pct percentage.
        Only called when self.__iterable_sample_pct__ < 100.
        """
        if len(keys) == 0:
            return []
        if self.__iterable_sample_pct__ == 0 or len(keys) == 1:
            return [keys[0]]
        n = max(1, int(len(keys) * self.__iterable_sample_pct__ / 100))
        if n >= len(keys):
            return keys
        return [keys[0]] + random.sample(keys[1:], n - 1)

    def __get_checkable_types__(self):
        """
        Creates two class attributes:

        - `self.__checkable_types__`:
            - What: A dictionary of all annotations as checkable types
            - Type: dict

        - `self.__return_type__`:
            - What: The return type of the function or method
            - Type: dict | None
        """
        if not self.__types_parsed__:
            self.__checkable_types__ = {
                key: self.__get_checkable_type__(value)
                for key, value in get_type_hints(self.__fn__).items()
            }
            self.__return_type__ = self.__checkable_types__.pop("return", None)
            # Classify params: simple types can use a single
            # isinstance call, skipping __check_type__ entirely.
            self.__simple_types__ = {}
            self.__complex_types__ = {}
            for key, expected in self.__checkable_types__.items():
                if (
                    "__extra__" not in expected
                    and all(v is None for v in expected.values())
                    and all(isinstance(k, type) for k in expected.keys())
                ):
                    self.__simple_types__[key] = tuple(expected.keys())
                else:
                    self.__complex_types__[key] = expected
            # Same classification for return type
            if self.__return_type__ is not None and (
                "__extra__" not in self.__return_type__
                and all(v is None for v in self.__return_type__.values())
                and all(
                    isinstance(k, type) for k in self.__return_type__.keys()
                )
            ):
                self.__simple_return_type__ = tuple(self.__return_type__.keys())
            else:
                self.__simple_return_type__ = None
            # Pre-compute param index in co_varnames for
            # direct arg lookup (skips assigned_vars dict).
            self.__param_indices__ = {
                name: i
                for i, name in enumerate(self.__fn_varnames__)
                if name in self.__checkable_types__
            }
            self.__types_parsed__ = True

    def __get_checkable_type__(self, annotation):
        """
        Parses a type annotation and returns a nested dict structure
        representing the checkable type(s) for validation.
        """

        if annotation is None:
            return {_NoneType: None}

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

        # Handle standard types
        if isinstance(annotation, type):
            return {annotation: None}

        # Hanldle typing.Type (for uninitialized classes)
        if origin is type and len(args) == 1:
            return {annotation: None}

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
                package_path = _package_path
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
        Overwrite standard __get__ method to return __call__ instead for wrapped class methods.

        Also stores the calling (__get__) `obj` to be passed as an initial argument for `__call__` such that methods can pass `self` correctly.
        """
        self.__outer_self__ = obj

        def __get_fn__(*args, **kwargs):
            return self.__call__(*args, **kwargs)

        __get_fn__.__name__ = self.__fn__.__name__
        __get_fn__.__qualname__ = self.__fn__.__qualname__
        __get_fn__.__doc__ = self.__fn__.__doc__
        return __get_fn__

    def __check_method_function__(self):
        """
        Validate that `self.__fn__` is a method or function
        """
        if not isinstance(self.__fn__, (MethodType, FunctionType)):
            raise Exception(
                f"A non function/method was passed to Enforcer. See the stack trace above for more information."
            )

    def __call__(self, *args, **kwargs):
        """
        This method is used to validate the passed inputs and return the output of the wrapped function or method.
        """
        # Special code to pass self as an initial argument
        # for validation purposes in methods
        # See: self.__get__
        if self.__outer_self__ is not None:
            args = (self.__outer_self__, *args)
        # Get a dictionary of all annotations as checkable types
        # Note: This is only done once at first call to avoid redundant calculations
        self.__get_checkable_types__()
        # Fast path: simple types use direct index lookup
        for key, types_tuple in self.__simple_types__.items():
            idx = self.__param_indices__[key]
            if idx < len(args):
                obj = args[idx]
            elif key in kwargs:
                obj = kwargs[key]
            else:
                obj = self.__fn_defaults__.get(key)
            if not isinstance(obj, types_tuple):
                # Fall back to full check for error reporting
                self.__check_type__(obj, self.__checkable_types__[key], key)
        # Full validation for complex types (nested, extras, Type[X])
        if self.__complex_types__:
            assigned_vars = {
                **self.__fn_defaults__,
                **dict(zip(self.__fn_varnames__[: len(args)], args)),
                **kwargs,
            }
            for key, value in self.__complex_types__.items():
                self.__check_type__(assigned_vars.get(key), value, key)
        # Execute the function callable
        return_value = self.__fn__(*args, **kwargs)
        # If a return type was passed, validate the returned object
        if self.__return_type__ is not None:
            if self.__simple_return_type__ is not None:
                if not isinstance(return_value, self.__simple_return_type__):
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
                self.__flat_subtypes__[subtype_id] = frozenset(subtype.keys())
            else:
                self.__flat_subtypes__[subtype_id] = None
        flat_keys = self.__flat_subtypes__[subtype_id]
        if flat_keys is not None:
            values = {type(v) for v in obj}
            if values.issubset(flat_keys):
                return True
        return False

    def __check_type__(self, obj, expected, key):
        """
        Raises an exception the type of a passed `obj` (parameter) is not in the list of supplied `acceptable_types` for the argument.
        """
        # Special case for None
        if obj is None and _NoneType in expected:
            return
        if "__extra__" in expected:
            extra = expected["__extra__"]
            expected = {k: v for k, v in expected.items() if k != "__extra__"}
        else:
            extra = None

        if isinstance(obj, type):
            # An uninitialized class is passed, we need to check if the type is in the expected types using Type[obj]
            obj_type = Type[obj]
            is_present = obj_type in expected
        else:
            obj_type = type(obj)
            is_present = obj_type in expected or isinstance(
                obj, tuple(expected.keys())
            )

        if not is_present:
            # Allow for literals to be used to bypass type checks if present
            literal = extra.get("__literal__", ()) if extra is not None else ()
            if literal:
                if obj not in literal:
                    self.__exception__(
                        f"Type mismatch for typed variable `{key}`. Expected one of the following `{list(expected.keys())}` or a literal value in `{literal}` but got type `{obj_type}` with value `{obj}` instead."
                    )
            # Raise an exception if the type is not in the expected types
            else:
                self.__exception__(
                    f"Type mismatch for typed variable `{key}`. Expected one of the following `{list(expected.keys())}` but got `{obj_type}` with value `{obj}` instead."
                )
        # If the object_type is in the expected types, we can proceed with validation
        elif obj_type in iterable_types:
            subtype = expected.get(obj_type, None)
            if subtype is None:
                pass
            # Recursive validation
            elif obj_type == list:
                if self.__iterable_sample_pct__ < 100:
                    for idx in self.__get_sample_indices__(len(obj)):
                        self.__check_type__(obj[idx], subtype, f"{key}[{idx}]")
                # If the subtype does not contain iterables with typing, we can validate the items directly.
                elif not self.__quick_check__(subtype, obj):
                    for idx, item in enumerate(obj):
                        self.__check_type__(item, subtype, f"{key}[{idx}]")
            elif obj_type == dict:
                key_type, val_type = subtype
                if self.__iterable_sample_pct__ < 100:
                    sampled_keys = self.__get_sample_keys__(list(obj.keys()))
                    if not self.__quick_check__(key_type, sampled_keys):
                        for dk in sampled_keys:
                            self.__check_type__(
                                dk, key_type, f"{key}.key[{repr(dk)}]"
                            )
                    if not self.__quick_check__(
                        val_type, [obj[dk] for dk in sampled_keys]
                    ):
                        for dk in sampled_keys:
                            self.__check_type__(
                                obj[dk], val_type, f"{key}[{repr(dk)}]"
                            )
                else:
                    if not self.__quick_check__(key_type, obj.keys()):
                        for key in obj.keys():
                            self.__check_type__(
                                key, key_type, f"{key}.key[{repr(key)}]"
                            )
                    if not self.__quick_check__(val_type, obj.values()):
                        for key, value in obj.items():
                            self.__check_type__(
                                value, val_type, f"{key}[{repr(key)}]"
                            )
            elif obj_type == tuple:
                expected_args, is_ellipsis = subtype
                if is_ellipsis:
                    if self.__iterable_sample_pct__ < 100:
                        for idx in self.__get_sample_indices__(len(obj)):
                            self.__check_type__(
                                obj[idx], expected_args, f"{key}[{idx}]"
                            )
                    elif not self.__quick_check__(expected_args, obj):
                        for idx, item in enumerate(obj):
                            self.__check_type__(
                                item, expected_args, f"{key}[{idx}]"
                            )
                else:
                    if len(obj) != len(expected_args):
                        self.__exception__(
                            f"Tuple length mismatch for `{key}`. Expected length {len(expected_args)}, got {len(obj)}"
                        )
                    for idx, (item, ex) in enumerate(zip(obj, expected_args)):
                        self.__check_type__(item, ex, f"{key}[{idx}]")
            elif obj_type == set:
                if self.__iterable_sample_pct__ < 100:
                    obj_list = list(obj)
                    for idx in self.__get_sample_indices__(len(obj_list)):
                        item = obj_list[idx]
                        self.__check_type__(
                            item, subtype, f"{key}[{repr(item)}]"
                        )
                elif not self.__quick_check__(subtype, obj):
                    for item in obj:
                        self.__check_type__(
                            item, subtype, f"{key}[{repr(item)}]"
                        )

        # Validate constraints if any are present
        if extra is not None:
            constraints = extra.get("__constraints__", ())
            for constraint in constraints:
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
):
    """
    A wrapper to enforce types within a function or method given argument annotations.

    Each wrapped item is converted into a special `FunctionMethodEnforcer` class object that validates the passed parameters for the function or method when it is called. If a function or method that is passed does not have any annotations, it is not converted into a `FunctionMethodEnforcer` class as no validation is possible.

    If wrapping a class, all methods in the class that meet any of the following criteria will be wrapped individually:

    - Methods with `__call__`
    - Methods wrapped with `staticmethod` (if python >= 3.10)
    - Methods wrapped with `classmethod` (if python >= 3.10)

    Requires:

    - `clsFnMethod`:
        - What: The class, function or method that should have input types enforced
        - Type: function | method | class

    Optional:

    - `enabled`:
        - What: A boolean to enable or disable the enforcer
        - Type: bool
        - Default: True
    - `strict`:
        - What: A boolean to enable or disable exceptions. If True, exceptions will be raised when type checking fails. If False, exceptions will not be raised but instead a warning will be printed to the console.
        - Type: bool
        - Default: False
        - Note: Type hints that are wrapped with the type enforcer and are invalid will still raise an exception.
    - `clean_traceback`:
        - What: A boolean to enable or disable cleaning of tracebacks when raising exceptions.
        - If True, modifies the excepthook temporarily such that only the relevant stack (not in the type_enforced package) is shown.
        - Type: bool
        - Default: True
    - `iterable_sample_pct`:
        - What: The percentage (0-100) of items to validate when checking typed iterables (list,
            dict, set, variable-length tuple). At 100 (default) every item is checked. Below 100,
            the first and last items are always checked; if the collection has more than 3 items,
            additional items are randomly sampled so that the total checked is at least 3.
        - Type: int | float
        - Default: 100


    Example Use:
    ```
    >>> import type_enforced
    >>> @type_enforced.Enforcer
    ... def my_fn(a: int , b: [int, str] =2, c: int =3) -> None:
    ...     pass
    ...
    >>> my_fn(a=1, b=2, c=3)
    >>> my_fn(a=1, b='2', c=3)
    >>> my_fn(a='a', b=2, c=3)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/home/conmak/development/personal/type_enforced/type_enforced/enforcer.py", line 85, in __call__
        self.__check_type__(assigned_vars.get(key), value, key)
      File "/home/conmak/development/personal/type_enforced/type_enforced/enforcer.py", line 107, in __check_type__
        self.__exception__(
      File "/home/conmak/development/personal/type_enforced/type_enforced/enforcer.py", line 34, in __exception__
        raise Exception(f"({self.__fn__.__qualname__}): {message}")
    Exception: (my_fn): Type mismatch for typed variable `a`. Expected one of the following `[<class 'int'>]` but got `<class 'str'>` instead.
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
        # Only apply the enforcer if type_hints are present
        # Add try except clause to better handle forward refs.
        try:
            if get_type_hints(clsFnMethod) == {}:
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
                )
            )
        elif isinstance(clsFnMethod, classmethod):
            return classmethod(
                FunctionMethodEnforcer(
                    __fn__=clsFnMethod.__func__,
                    __strict__=strict,
                    __clean_traceback__=clean_traceback,
                    __iterable_sample_pct__=iterable_sample_pct,
                )
            )
        else:
            return FunctionMethodEnforcer(
                __fn__=clsFnMethod,
                __strict__=strict,
                __clean_traceback__=clean_traceback,
                __iterable_sample_pct__=iterable_sample_pct,
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
                    ),
                )
        return clsFnMethod
    else:
        raise Exception(
            "Enforcer can only be used on classes, methods, or functions."
        )
