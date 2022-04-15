import types
import functools

class Enforcer:
    def __init__(self, __fn__, *__args__, **__kwargs__):
        self.__doc__ = __fn__.__doc__
        self.__name__ = __fn__.__name__ + "_type_enforced"
        self.__annotations__ = __fn__.__annotations__
        self.__fn__ = __fn__
        self.__args__ = __args__
        self.__kwargs__ = __kwargs__
        self.__check_method_function__()

    def __get__(self, obj, objtype):
        return functools.partial(self.__call__, obj)

    def __check_method_function__(self):
        if not isinstance(self.__fn__, (types.MethodType, types.FunctionType)):
            raise Excpetion('A non function/method was passed to Enforcer. See the stack trace above for more information.')

    def __call__(self, *args, **kwargs):
        return self.__validate_types__(*args, **kwargs)

    def __check_type__(self, obj, types, key):
        # Force provided types to be a list of items
        if not isinstance(types, list):
            types = [types]
        # Special code to replace None with NoneType
        types = [i if i is not None else type(None) for i in types]
        if type(obj) not in types:
            raise Exception(
                f"Type mismatch for typed function ({self.__fn__.__name__}) with `{key}`. Expected one of the following `{str(types)}` but got `{type(obj)}` instead."
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
