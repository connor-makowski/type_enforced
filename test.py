import type_enforced

@type_enforced.Enforcer
def my_fn(x: tuple[int, ...] | tuple[str]) -> None:
    pass

my_fn((1, 1, 1))  # Passes