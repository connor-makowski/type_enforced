import type_enforced

@type_enforced.Enforcer
def my_fn(a: int , b: [int, str] =2, c: int =3) -> None:
    return 1

my_fn(a=1, b=2, c=3) # Error (return is not None)
