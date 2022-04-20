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

`type_enforcer` contains a basic `Enforcer` wrapper that can be used to enforce most basic python typing hints.

`type_enforcer` currently supports all single level python types and single level class instances. For example, you can force an input to be an `int` or a self defined `MyClass`, but not a vector of the format `list(int)`. In this case, when using `type_enforcer`, you would only pass the format `list` and would not validate that the content of the list was indeed integers.

You can pass multiple types in brackets to validate one of multiple types. For example, you could validate an input was an int or a float with `[int, float]`.

Non specified types for variables are not enforced. 

Input and return typing are both supported.

## Basic Usage
```py
import type_enforced

@type_enforced.Enforcer
def my_fn(a: int , b: [int, str] =2, c: int =3) -> None:
    pass

```

## Interactive Example

```py
>>> import type_enforced
>>> @type_enforced.Enforcer
... def my_fn(a: int , b: [int, str] =2, c: int =3) -> None:
...     pass
...
>>> my_fn(a=1, b=2, c=3)
>>> my_fn(a=1, b='2', c=3)
>>> my_fn(a='a', b=2, c=3)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/home/conmak/development/personal/type_enforced/type_enforced/enforcer.py", line 47, in __call__
    return self.__validate_types__(*args, **kwargs)
  File "/home/conmak/development/personal/type_enforced/type_enforced/enforcer.py", line 83, in __validate_types__
    self.__check_type__(assigned_vars.get(key), value, key)
  File "/home/conmak/development/personal/type_enforced/type_enforced/enforcer.py", line 56, in __check_type__
    self.__exception__(
  File "/home/conmak/development/personal/type_enforced/type_enforced/enforcer.py", line 37, in __exception__
    raise Exception(f"({self.__fn__.__qualname__}): {message}")
Exception: (my_fn): Type mismatch for typed function (my_fn) with `a`. Expected one of the following `[<class 'int'>]` but got `<class 'str'>` instead.
```

## Class and Method Use

Type enforcer can be applied to methods individually:

```py
import type_enforced

class my_class:
    @type_enforced.Enforcer
    def my_fn(self, b:int):
        pass
```

You can also enforce all typing for all methods in a class by decorating the class itself.

```py
import type_enforced

@type_enforced.Enforcer
class my_class:
    def my_fn(self, b:int):
        pass

    def my_other_fn(self, a: int, b: [int, str]):
      pass
```
