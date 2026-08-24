import sys, inspect
from types import FunctionType, ModuleType
from type_enforced.utils import Partial


def __should_enforce_in_module__(obj, module_name):
    return getattr(obj, "__module__", None) == module_name


def __get_caller_module__():
    frame = inspect.currentframe()
    while frame is not None:
        frame = frame.f_back
        if frame is None:
            break
        module_name = frame.f_globals.get("__name__")
        if (
            module_name is not None
            and not module_name.startswith("type_enforced")
            and module_name in sys.modules
        ):
            return sys.modules[module_name]
    return None


class __ModuleEnforcer__(Partial):
    def __call__(self, *args, **kwargs):
        if not args and not self.__args__:
            caller_module = __get_caller_module__()
            if caller_module is not None:
                args = (caller_module,)
        return super().__call__(*args, **kwargs)


@__ModuleEnforcer__
def ModuleEnforcer(
    module,
    enabled=True,
    strict=True,
    clean_traceback=True,
    iterable_sample_pct=100,
    submodules=True,
    only_typed=False,
):
    """
    Enforce types on all functions and classes defined in a module.

    Can be called within a module (e.g. `ModuleEnforcer()`),
    or directly on an imported module object or module name.

    Requires (or resolves to caller module if omitted):

    - `module`:
        - What: The module or module name to enforce.
        - Type: types.ModuleType | str

    Optional:

    - `enabled`:
        - What: A boolean to enable or disable the enforcer.
        - Type: bool
        - Default: True
    - `strict`:
        - What: A boolean to enable or disable exceptions. If True, exceptions will be raised
            when type checking fails. If False, exceptions will not be raised but instead a warning
            will be printed to the console.
        - Type: bool
        - Default: True
    - `clean_traceback`:
        - What: A boolean to enable or disable cleaning of tracebacks when raising exceptions.
        - Type: bool
        - Default: True
    - `iterable_sample_pct`:
        - What: Control how many items in iterables are checked during type enforcement.
            Supports 'first' (first element), 'last' (last element), 'log' (sample of log n items),
            0 (1 random sample), or an integer percentage 1..100 (rounding up).
        - Type: int | str
        - Default: 100
    - `submodules`:
        - What: A boolean to enable or disable recursive enforcement on submodules under the
            same package namespace.
        - Type: bool
        - Default: True
    - `only_typed`:
        - What: A boolean to enable or disable raising exceptions on untyped function/method parameters.
        - Type: bool
        - Default: False
    """
    from type_enforced.enforcer import Enforcer

    if isinstance(module, str):
        module = sys.modules.get(module)
    elif not isinstance(module, ModuleType):
        raise Exception(
            f"Expected a module or module name string, but got {type(module)}"
        )

    if module is None:
        raise Exception("Could not resolve module to enforce.")

    def _apply_enforcement(target_module):
        module_name = target_module.__name__
        for key, value in list(target_module.__dict__.items()):
            if key.startswith("__") and key.endswith("__"):
                continue
            if isinstance(
                value, (FunctionType, type)
            ) and __should_enforce_in_module__(value, module_name):
                wrapped = Enforcer(
                    value,
                    enabled=enabled,
                    strict=strict,
                    clean_traceback=clean_traceback,
                    iterable_sample_pct=iterable_sample_pct,
                    only_typed=only_typed,
                )
                setattr(target_module, key, wrapped)
            elif submodules and isinstance(value, ModuleType):
                if value.__name__.startswith(module_name + "."):
                    ModuleEnforcer(
                        value,
                        enabled=enabled,
                        strict=strict,
                        clean_traceback=clean_traceback,
                        iterable_sample_pct=iterable_sample_pct,
                        submodules=submodules,
                        only_typed=only_typed,
                    )

        if submodules:
            prefix = module_name + "."
            for sub_name, sub_mod in list(sys.modules.items()):
                if (
                    sub_name.startswith(prefix)
                    and isinstance(sub_mod, ModuleType)
                    and not getattr(sub_mod, "__type_enforced_lazy__", False)
                ):
                    ModuleEnforcer(
                        sub_mod,
                        enabled=enabled,
                        strict=strict,
                        clean_traceback=clean_traceback,
                        iterable_sample_pct=iterable_sample_pct,
                        submodules=submodules,
                        only_typed=only_typed,
                    )

    # Immediately enforce any functions/classes already present
    _apply_enforcement(module)

    # If already wrapped with lazy proxy, return module
    if getattr(module, "__type_enforced_lazy__", False):
        return module

    original_class = module.__class__

    class LazyEnforcedModule(original_class):
        def __getattribute__(self, name):
            if not object.__getattribute__(self, "__dict__").get(
                "__type_enforced_initialized__", False
            ):
                object.__setattr__(self, "__type_enforced_initialized__", True)
                _apply_enforcement(self)
            attr = super().__getattribute__(name)
            if submodules and isinstance(attr, ModuleType):
                module_name = object.__getattribute__(self, "__name__")
                if attr.__name__.startswith(module_name + "."):
                    ModuleEnforcer(
                        attr,
                        enabled=enabled,
                        strict=strict,
                        clean_traceback=clean_traceback,
                        iterable_sample_pct=iterable_sample_pct,
                        submodules=submodules,
                        only_typed=only_typed,
                    )
            return attr

    module.__dict__["__type_enforced_lazy__"] = True
    module.__dict__["__type_enforced_initialized__"] = False
    module.__class__ = LazyEnforcedModule
    return module
