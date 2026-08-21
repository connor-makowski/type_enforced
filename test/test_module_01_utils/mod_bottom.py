import type_enforced


def add(a: int, b: int) -> int:
    return a + b


class Calculator:

    def multiply(self, a: int, b: int) -> int:
        return a * b


type_enforced.ModuleEnforcer()
