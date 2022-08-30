import types
import functools


class FunctionMethodEnforcer:
    def __init__(self, __fn__, *__args__, **__kwargs__):
        functools.update_wrapper(self, __fn__)
        self.__name__ = __fn__.__name__ + "_type_enforced"
        self.__fn__ = __fn__
        self.__args__ = __args__
        self.__kwargs__ = __kwargs__
        self.__check_method_function__()

    def __exception__(self, message, depth=0):
        """
        Usage:

        - Creates a class based exception message

        Requires:

        - `message`:
            - Type: str
            - What: The message to warn users with
            - Note: Messages with `{{class_name}}` and `{{method_name}}` in them are formatted appropriately

        Optional:

        - `depth`:
            - Type: int
            - What: The depth of the nth call below the top of the method stack
            - Note: Depth starts at 0 (indicating the current method in the stack)
            - Default: 0

        """
        raise Exception(f"({self.__fn__.__qualname__}): {message}")

    def __get__(self, obj, objtype):
        new_fn = functools.partial(self.__call__, obj)
        functools.update_wrapper(new_fn, self)
        return new_fn

    def __check_method_function__(self):
        if not isinstance(self.__fn__, (types.MethodType, types.FunctionType)):
            raise Exception(
                f"A non function/method was passed to Enforcer. See the stack trace above for more information."
            )

    def __call__(self, *args, **kwargs):
        return self.__validate_types__(*args, **kwargs)

    def __check_type__(self, obj, types, key):
        # Force provided types to be a list of items
        if not isinstance(types, list):
            types = [types]
        # Special code to replace None with NoneType
        types = [i if i is not None else type(None) for i in types]
        if type(obj) not in types:
            self.__exception__(
                f"Type mismatch for typed variable `{key}`. Expected one of the following `{str(types)}` but got `{type(obj)}` instead."
            )

    def __validate_types__(self, *args, **kwargs):
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

    def __repr__(self):
        return f"<type_enforced {self.__fn__.__module__}.{self.__fn__.__qualname__} object at {hex(id(self))}>"


def Enforcer(clsFnMethod):
    if isinstance(clsFnMethod, (types.FunctionType, types.MethodType)):
        return FunctionMethodEnforcer(clsFnMethod)
    else:
        for key, value in clsFnMethod.__dict__.items():
            if hasattr(value, "__call__"):
                setattr(clsFnMethod, key, Enforcer(value))
        return clsFnMethod
