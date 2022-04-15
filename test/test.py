import type_enforced

@type_enforced.Enforcer
def my_fn(a: int , b: [int, str] =2, c: int =3) -> None:
    pass

my_fn(a=1, b=2, c=3) # No Error
my_fn(a=1, b='2', c=3) # No Error (b can take int or str)
my_fn(a='a', b=2, c=3) # Error (a can only accept int)
