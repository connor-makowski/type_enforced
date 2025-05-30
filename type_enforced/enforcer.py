from types import (
    FunctionType,
    MethodType,
    GeneratorType,
    BuiltinFunctionType,
    BuiltinMethodType,
    UnionType,
)
from typing import Type, Union, Sized, Literal, Callable, get_type_hints
from functools import update_wrapper, wraps
from type_enforced.utils import (
    Partial,
    GenericConstraint,
    DeepMerge,
    WithSubclasses,
)


class FunctionMethodEnforcer:
    def __init__(self, __fn__):
        """
        Initialize a FunctionMethodEnforcer class object as a wrapper for a passed function `__fn__`.

        Requires:

            - `__fn__`:
                - What: The function to enforce
                - Type: function | method | class
        """
        update_wrapper(self, __fn__)
        self.__fn__ = __fn__
        self.__outer_self__ = None
        # Validate that the passed function or method is a method or function
        self.__check_method_function__()
        # Get input defaults for the function or method
        self.__get_defaults__()

    def __get_defaults__(self):
        """
        Get the default values of the passed function or method and store them in `self.__fn_defaults__`.
        """
        self.__fn_defaults__ = {}
        if self.__fn__.__defaults__ is not None:
            # Get the names of all provided default values for args
            default_varnames = list(self.__fn__.__code__.co_varnames)[
                : self.__fn__.__code__.co_argcount
            ][-len(self.__fn__.__defaults__) :]
            # Update the output dictionary with the default values
            self.__fn_defaults__.update(
                dict(zip(default_varnames, self.__fn__.__defaults__))
            )
        if self.__fn__.__kwdefaults__ is not None:
            # Update the output dictionary with the keyword default values
            self.__fn_defaults__.update(self.__fn__.__kwdefaults__)

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
        if not hasattr(self, "__checkable_types__"):
            self.__checkable_types__ = {
                key: self.__get_checkable_type__(value)
                for key, value in get_type_hints(self.__fn__).items()
            }
            self.__return_type__ = self.__checkable_types__.pop("return", None)

    def __get_checkable_type__(self, annotation):
        """
        Parses a type annotation and returns a nested dict structure
        representing the checkable type(s) for validation.
        """

        if annotation is None:
            return {type(None): None}

        # Handle `int | str` syntax (Python 3.10+) and Unions
        if (
            isinstance(annotation, UnionType)
            or getattr(annotation, "__origin__", None) == Union
        ):
            combined_types = {}
            for sub_type in annotation.__args__:
                combined_types = DeepMerge(
                    combined_types, self.__get_checkable_type__(sub_type)
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
                raise TypeError(
                    f"List must have a single type argument, got: {args}"
                )
            return {list: self.__get_checkable_type__(args[0])}

        if origin == dict:
            if len(args) != 2:
                raise TypeError(
                    f"Dict must have two type arguments, got: {args}"
                )
            key_type = self.__get_checkable_type__(args[0])
            value_type = self.__get_checkable_type__(args[1])
            return {dict: (key_type, value_type)}

        if origin == tuple:
            if len(args) > 2 or len(args) == 1:
                if Ellipsis in args:
                    raise TypeError(
                        "Tuple with Ellipsis must have exactly two type arguments and the second must be Ellipsis."
                    )
            if len(args) == 2:
                if args[0] is Ellipsis:
                    raise TypeError(
                        "Tuple with Ellipsis must have exactly two type arguments and the first must not be Ellipsis."
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
                raise TypeError(
                    f"Set must have a single type argument, got: {args}"
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

        # Handle WithSubclasses
        if isinstance(annotation, WithSubclasses):
            return {subclass: None for subclass in annotation.get_subclasses()}

        # Handle Constraints
        if isinstance(annotation, GenericConstraint):
            return {"__extra__": {"__constraints__": [annotation]}}

        # Handle standard types
        if isinstance(annotation, type):
            return {annotation: None}

        # Hanldle typing.Type (for uninitialized classes)
        if origin is type and len(args) == 1:
            return {annotation: None}

        raise TypeError(f"Unsupported type hint: {annotation}")

    def __exception__(self, message):
        """
        Usage:

        - Creates a class based exception message

        Requires:

        - `message`:
            - Type: str
            - What: The message to warn users with
        """
        raise TypeError(
            f"TypeEnforced Exception ({self.__fn__.__qualname__}): {message}"
        )

    def __get__(self, obj, objtype):
        """
        Overwrite standard __get__ method to return __call__ instead for wrapped class methods.

        Also stores the calling (__get__) `obj` to be passed as an initial argument for `__call__` such that methods can pass `self` correctly.
        """

        @wraps(self.__fn__)
        def __get_fn__(*args, **kwargs):
            return self.__call__(*args, **kwargs)

        self.__outer_self__ = obj
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
        # Create a compreshensive dictionary of assigned variables (order matters)
        assigned_vars = {
            **self.__fn_defaults__,
            **dict(zip(self.__fn__.__code__.co_varnames[: len(args)], args)),
            **kwargs,
        }
        # Validate all listed annotations vs the assigned_vars dictionary
        for key, value in self.__checkable_types__.items():
            self.__check_type__(assigned_vars.get(key), value, key)
        # Execute the function callable
        return_value = self.__fn__(*args, **kwargs)
        # If a return type was passed, validate the returned object
        if self.__return_type__ is not None:
            self.__check_type__(return_value, self.__return_type__, "return")
        return return_value

    def __check_type__(self, obj, expected, key):
        """
        Raises an exception the type of a passed `obj` (parameter) is not in the list of supplied `acceptable_types` for the argument.
        """
        # Special case for None
        if obj is None and type(None) in expected:
            return
        extra = expected.get("__extra__", {})
        expected = {k: v for k, v in expected.items() if k != "__extra__"}

        if isinstance(obj, type):
            obj_type = Type[obj]
        else:
            obj_type = type(obj)

        if obj_type not in expected:
            # Allow for literals to be used to bypass type checks if present
            literal = extra.get("__literal__", ())
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
        else:
            subtype = expected[obj_type]

            # Recursive validation
            if obj_type == list and subtype:
                for idx, item in enumerate(obj):
                    self.__check_type__(item, subtype, f"{key}[{idx}]")
            elif obj_type == dict and subtype:
                key_type, val_type = subtype
                for k, v in obj.items():
                    self.__check_type__(k, key_type, f"{key}.key[{repr(k)}]")
                    self.__check_type__(v, val_type, f"{key}[{repr(k)}]")
            elif obj_type == tuple and subtype:
                expected_args, is_ellipsis = subtype
                if is_ellipsis:
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
            elif obj_type == set and subtype:
                for item in obj:
                    self.__check_type__(item, subtype, f"{key}[{repr(item)}]")

        constraints = extra.get("__constraints__", [])
        for constraint in constraints:
            constraint_validation_output = constraint.__validate__(key, obj)
            if constraint_validation_output is not True:
                self.__exception__(
                    f"Constraint validation error for variable `{key}` with value `{obj}`. {constraint_validation_output}"
                )

    def __repr__(self):
        return f"<type_enforced {self.__fn__.__module__}.{self.__fn__.__qualname__} object at {hex(id(self))}>"


def Enforcer(clsFnMethod, enabled):
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
        if get_type_hints(clsFnMethod) == {}:
            return clsFnMethod
        elif isinstance(clsFnMethod, staticmethod):
            return staticmethod(FunctionMethodEnforcer(clsFnMethod.__func__))
        elif isinstance(clsFnMethod, classmethod):
            return classmethod(FunctionMethodEnforcer(clsFnMethod.__func__))
        else:
            return FunctionMethodEnforcer(clsFnMethod)
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
                setattr(clsFnMethod, key, Enforcer(value, enabled=enabled))
        return clsFnMethod
    else:
        raise Exception(
            "Enforcer can only be used on classes, methods, or functions."
        )


Enforcer = Partial(Enforcer, enabled=True)
