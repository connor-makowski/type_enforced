Type Enforced
==========
Enforce types in python functions

Setup
----------

Make sure you have Python 3.6.x (or higher) installed on your system. You can download it [here](https://www.python.org/downloads/).

### Installation

```
pip install type_enforced
```

# Getting Started

## Basic Usage
```py
import type_enforced

@type_enforced.Enforcer
def my_fn(a: int , b: [int, str] =2, c: int =3) -> None:
    pass

my_fn(a=1, b=2, c=3) # No Error
my_fn(a=1, b='2', c=3) # No Error (b can take int or str)
my_fn(a='a', b=2, c=3) # Error (a can only accept int)
# Exception: Type mismatch for typed function (my_fn) with `a`. Expected one of the following `[<class 'int'>]` but got `<class 'str'>` instead.
```
