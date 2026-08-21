import type_enforced

type_enforced.ModuleEnforcer()


def subtract(a: int, b: int) -> int:
    return a - b


class Divider:

    def divide(self, a: int, b: int) -> int:
        return a // b
