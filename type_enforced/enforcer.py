from types import FunctionType, MethodType, GenericAlias, UnionType
from typing import Type, Union
from functools import update_wrapper, wraps


class FunctionMethodEnforcer:
    def __init__(self, __fn__):
        """
        Initialize a FunctionMethodEnforce class object as a wrapper for a passed function `__fn__`.

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
        # Get a dictionary of all annotations as checkable types
        self.__checkable_types__ = {
            key: self.__get_checkable_type__(value)
            for key, value in self.__annotations__.items()
        }
        self.__return_type__ = self.__checkable_types__.pop("return", None)

    def __get_defaults__(self):
        """
        Get the default values of the passed function or method and store them in `self.__fn_defaults__`.
        """
        # Determine assigned variables as they were passed in
        # See https://stackoverflow.com/a/71884467/12014156
        if self.__fn__.__kwdefaults__ is not None:
            # __defaults__ are not used if *args are present necessitating this line
            self.__fn_defaults__ = self.__fn__.__kwdefaults__
        elif self.__fn__.__defaults__ is not None:
            # Get the list of variable names (omittiting **kwargs var if present)
            varnames = list(self.__fn__.__code__.co_varnames)[
                : self.__fn__.__code__.co_argcount
            ]
            # Create a dictionary of default values
            self.__fn_defaults__ = dict(
                zip(
                    varnames[-len(self.__fn__.__defaults__) :],
                    self.__fn__.__defaults__,
                )
            )
        else:
            self.__fn_defaults__ = {}

    def __get_checkable_type__(self, item_annotation):
        """
        Gets the checkable type as a nested dict for a passed annotation.
        """
        valid_types = {}
        if not isinstance(item_annotation, (list, tuple)):
            item_annotation = [item_annotation]
        for valid_type in item_annotation:
            # Special code to replace None with NoneType
            if valid_type is None:
                valid_types[type(None)] = None
                continue
            elif hasattr(valid_type, "__origin__"):
                # Special code for iterable types (e.g. list, tuple, dict, set) including typing iterables
                if valid_type.__origin__ in [list, tuple, dict, set]:
                    valid_types[
                        valid_type.__origin__
                    ] = self.__get_checkable_type__(valid_type.__args__)
                # Handle any generic aliases
                elif isinstance(valid_type, GenericAlias):
                    valid_types[valid_type.__origin__] = None
                # Handle Union Types (e.g. Union, Optional, ...)
                elif valid_type.__origin__ == Union:
                    valid_types.update(
                        self.__get_checkable_type__(valid_type.__args__)
                    )
                # Handle uninitialized class type objects (e.g. MyCustomClass)
                else:
                    valid_types[valid_type] = None
            # Handle special '|' syntax for Union Types
            elif isinstance(valid_type, UnionType):
                valid_types.update(
                    self.__get_checkable_type__(valid_type.__args__)
                )
            else:
                valid_types[valid_type] = None
        return valid_types

    def __exception__(self, message):
        """
        Usage:

        - Creates a class based exception message

        Requires:

        - `message`:
            - Type: str
            - What: The message to warn users with
        """
        raise TypeError(f"({self.__fn__.__qualname__}): {message}")

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

    def __check_type__(self, obj, acceptable_types, key):
        """
        Raises an exception the type of a passed `obj` (parameter) is not in the list of supplied `acceptable_types` for the argument.
        """
        if isinstance(obj, type):
            passed_type = Type[obj]
        else:
            passed_type = type(obj)
        if passed_type not in acceptable_types:
            self.__exception__(
                f"Type mismatch for typed variable `{key}`. Expected one of the following `{str(list(acceptable_types.keys()))}` but got `{passed_type}` instead."
            )
        sub_type = acceptable_types.get(passed_type)
        if sub_type is not None:
            if passed_type == dict:
                for sub_key, value in obj.items():
                    self.__check_type__(value, sub_type, f"{key}[{sub_key}]")
            else:
                for sub_key, value in enumerate(obj):
                    self.__check_type__(value, sub_type, f"{key}[{sub_key}]")

    def __repr__(self):
        return f"<type_enforced {self.__fn__.__module__}.{self.__fn__.__qualname__} object at {hex(id(self))}>"


def Enforcer(clsFnMethod):
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
    if isinstance(
        clsFnMethod, (staticmethod, classmethod, FunctionType, MethodType)
    ):
        # Only apply the enforcer if annotations are specified
        if getattr(clsFnMethod, "__annotations__", {}) == {}:
            return clsFnMethod
        elif isinstance(clsFnMethod, staticmethod):
            return staticmethod(FunctionMethodEnforcer(clsFnMethod.__func__))
        elif isinstance(clsFnMethod, classmethod):
            return classmethod(FunctionMethodEnforcer(clsFnMethod.__func__))
        elif isinstance(clsFnMethod, (FunctionType, MethodType)):
            return FunctionMethodEnforcer(clsFnMethod)
    else:
        for key, value in clsFnMethod.__dict__.items():
            if hasattr(value, "__call__") or isinstance(
                value, (classmethod, staticmethod)
            ):
                setattr(clsFnMethod, key, Enforcer(value))
        return clsFnMethod
