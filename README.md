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

`type_enforcer` contains a basic `Enforcer` wrapper that can be used to enforce most basic python typing hints. [Technical Docs Here](https://connor-makowski.github.io/type_enforced/enforcer.html).

`type_enforcer` currently supports all single level python types, single level class instances and classes themselves. For example, you can force an input to be an `int` or an instance of the self defined `MyClass`, but not a vector of the format `list(int)`. In this case, when using `type_enforcer`, you would only pass the format `list` and would not validate that the content of the list was indeed integers.

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
  File "/home/conmak/development/personal/type_enforced/type_enforced/enforcer.py", line 85, in __call__
    self.__check_type__(assigned_vars.get(key), value, key)
  File "/home/conmak/development/personal/type_enforced/type_enforced/enforcer.py", line 107, in __check_type__
    self.__exception__(
  File "/home/conmak/development/personal/type_enforced/type_enforced/enforcer.py", line 34, in __exception__
    raise TypeError(f"({self.__fn__.__qualname__}): {message}")
TypeError: (my_fn): Type mismatch for typed variable `a`. Expected one of the following `[<class 'int'>]` but got `<class 'str'>` instead.
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

You can also enforce types on `staticmethod`s and `classmethod`s if you are using `python >= 3.10`. If you are using a python version less than this, `classmethod`s and `staticmethod`s methods will not have their types enforced.
- NOTE: There is a known issue where classmethod docstrings are broken when a classmethod is type enforced.

```py
import type_enforced

@type_enforced.Enforcer
class my_class:
    @classmethod
    def my_fn(self, b:int):
        pass

    @staticmethod
    def my_other_fn(a: int, b: [int, str]):
      pass
```

## Validate class instances and classes

Type enforcer can enforce class instances and classes easily. There are a few caveats between the two.

To enforce a class instance, simply pass the class itself as a type hint:
```py
import type_enforced

class Foo():
    def __init__(self) -> None:
        pass

@type_enforced.Enforcer
class my_class():
    def __init__(self, object: Foo) -> None:
        self.object = object

x=my_class(Foo()) # Works great!
y=my_class(Foo) # Fails!
```

Notice how an initialized class instance `Foo()` must be passed for the enforcer to not raise an exception.

To enforce an uninitialized class object use `typing.Type[classHere]` on the class to enforce inputs to be an uninitialized class:
```py
import type_enforced
import typing

class Foo():
    def __init__(self) -> None:
        pass

@type_enforced.Enforcer
class my_class():
    def __init__(self, object_class: typing.Type[Foo]) -> None:
        self.object = object_class()

y=my_class(Foo) # Works great!
x=my_class(Foo()) # Fails
```
