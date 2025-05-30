import type_enforced, sys


try:
    success = True

    @type_enforced.Enforcer
    def my_fn(x: list[str | int] | list[list[int]]) -> None:
        pass

    @type_enforced.Enforcer
    def inv_my_fn(x: list[int] | list[str] | list[list[int]]) -> None:
        pass

except:
    success = False

try:
    my_fn([1, 2, 3])  # Passes
    my_fn(["a", "b", "c"])  # Passes
    my_fn([[1, 2], [3, 4]])  # Passes

    inv_my_fn([1, 2, 3])  # Passes
    inv_my_fn(["a", "b", "c"])  # Passes
    inv_my_fn([[1, 2], [3, 4]])  # Passes
except:
    success = False

# TODO: In the next major version, add support to enforce
#       multiple different types of nested lists but not mixed types
# try:
#     my_fn([1, "a", 3])
#     success = False
# except:
#     pass


if success:
    print(f"test_fn_17.py passed")
else:
    print(f"test_fn_17.py failed")
