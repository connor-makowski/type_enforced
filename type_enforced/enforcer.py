from types import FunctionType, MethodType
from typing import Type as typingType
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
        self.__check_method_function__()

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
        # Determine assigned variables as they were passed in
        # See https://stackoverflow.com/a/71884467/12014156
        if self.__fn__.__defaults__ is not None:
            kwarg_defaults = dict(
                zip(
                    self.__fn__.__code__.co_varnames[-len(self.__fn__.__defaults__) :],
                    self.__fn__.__defaults__,
                )
            )
        else:
            kwarg_defaults = {}
        # Create a compreshensive dictionary of assigned variables
        assigned_vars = {
            **dict(zip(self.__fn__.__code__.co_varnames[: len(args)], args)),
            **kwarg_defaults,
            **kwargs,
        }
        # Create a shallow copy dictionary to preserve annotations at object root
        annotations = dict(self.__annotations__)
        # Validate all listed annotations vs the assigned_vars dictionary
        for key, value in annotations.items():
            if key in assigned_vars:
                self.__check_type__(assigned_vars.get(key), value, key)
        # Execute the function callable
        return_value = self.__fn__(*args, **kwargs)
        # If a return type was passed, validate the returned object
        if "return" in annotations:
            self.__check_type__(return_value, annotations["return"], "return")
        return return_value

    def __check_type__(self, obj, types, key):
        """
        Raises an exception the type of a passed `obj` (parameter) is not in the list of supplied `types` for the argument.
        """
        # Force provided types to be a list of items
        if not isinstance(types, list):
            types = [types]
        # Special code to replace None with NoneType
        types = [i if i is not None else type(None) for i in types]
        if isinstance(obj, type):
            passed_type = typingType[obj]
        else:
            passed_type = type(obj)
        if passed_type not in types:
            self.__exception__(
                f"Type mismatch for typed variable `{key}`. Expected one of the following `{str(types)}` but got `{passed_type}` instead."
            )

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
    if isinstance(clsFnMethod, (staticmethod, classmethod, FunctionType, MethodType)):
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
            if hasattr(value, "__call__") or isinstance(value, (classmethod, staticmethod)):
                setattr(clsFnMethod, key, Enforcer(value))
        return clsFnMethod
