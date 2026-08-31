import type_enforced

type_enforced.FastModuleEnforcer(iterable_sample_pct="last")


def check_last(items: list[int]) -> int:
    return len(items)
