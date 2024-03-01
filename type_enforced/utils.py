import types
from functools import update_wrapper


def WithSubclasses(obj):
    """
    A special helper function to allow a class type to be passed and also allow all subclasses of that type.

    Requires:

    - `obj`:
        - What: An uninitialized class that should also be considered type correct if a subclass is passed.
        - Type: Any Uninitialized class

    Returns:

    - `out`:
        - What: A list of all of the subclasses (recursively parsed)
        - Type: list of strs


    Notes:

    - From a functional perspective, this recursively gets the subclasses for an uninitialised class (type).
    """
    out = [obj]
    for i in obj.__subclasses__():
        out += WithSubclasses(i)
    return out


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

    def __exception__(self, message):
        pre_message = (
            f"({self.__fn__.__module__}.{self.__fn__.__qualname__}_partial): "
        )
        raise Exception(pre_message + message)

    def __call__(self, *args, **kwargs):
        new_args = self.__args__ + args
        new_kwargs = {**self.__kwargs__, **kwargs}
        self.__arity__ = self.__getArity__(new_args, new_kwargs)
        if self.__arity__ < 0:
            self.__exception__("Too many arguments were supplied")
        if self.__arity__ == 0:
            results = self.__fn__(*new_args, **new_kwargs)
            return results
        return Partial(
            self.__fn__,
            *new_args,
            **new_kwargs,
        )

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
