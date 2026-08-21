import type_enforced

type_enforced.ModuleEnforcer()  # submodules=True by default


def root_fn(a: int) -> int:
    return a * 10
