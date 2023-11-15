# Type Enforced
[![PyPI version](https://badge.fury.io/py/type_enforced.svg)](https://badge.fury.io/py/type_enforced)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A pure python (no special compiler required) type enforcer for type annotations. Enforce types in python functions and methods.

# Setup

Make sure you have Python 3.7.x (or higher) installed on your system. You can download it [here](https://www.python.org/downloads/).

- Note: Certain features are only available on newer python versions
    - EG: Staticmethod typechecking requires `python>=3.10`

### Installation

```
pip install type_enforced
```

# Getting Started

`type_enforcer` contains a basic `Enforcer` wrapper that can be used to enforce many basic python typing hints. [Technical Docs Here](https://connor-makowski.github.io/type_enforced/type_enforced/enforcer.html).

`type_enforcer` currently supports many single and multi level python types. This includes class instances and classes themselves. For example, you can force an input to be an `int`, a number `[int, float]`, an instance of the self defined `MyClass`, or a even a vector with `list[int]`. Items like `typing.List`, `typing.Dict`, `typing.Union` and `typing.Optional` are supported.

You can pass union types to validate one of multiple types. For example, you could validate an input was an int or a float with `[int, str]`, `[int | float]` or even `typing.Union[int,str]`.

Nesting is allowed as long as the nested items are iterables (e.g. `typing.List`, `dict`, ...). For examle, you could validate that a list is a vector with `list[int]` or possibly `typing.List[int]`.

Variables without an annotation for type are not enforced.

## Supported Type Checking Features:

- Function/Method Input Typing
- Function/Method Return Typing
- All standard python types (`str`, `list`, `int`, `dict`, ...)
- Union types
    - typing.Union
    - `,` separated list (e.g. `[int, float]`)
    - `|` separated list (e.g. `[int | float]`)
- Nested types (e.g. `dict[str]` or `list[int,float]`)
    - Note: Each parent level must be an iterable
        - Specifically a variant of `list`, `set`, `tuple` or `dict`
    - Note: `dict` keys are not validated, only values
    - Deeply nested types are supported too:
        - `dict[dict[int]]`
        - `list[set[]]`
- Many of the `typing` (package) functions including:
    - Standard generics:
        - `List`, `Set`, `Dict`, `Tuple`
    - `Union`
    - `Optional`
    - `Sized`
        - Essentially creates a union of: 
            - `list`, `tuple`, `dict`, `set`, `str`, `bytes`, `bytearray`, `memoryview`, `range`
        - Note: Can not have a nested type
            - Because this does not always meet the criteria for `Nested types` above
    - Note: Other functions might have support, but there are not currently tests to validate them
        - Feel free to create an issue (or better yet a PR) if you want to add tests/support

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

## Nested Examples
```py
import type_enforced
import typing

@type_enforced.Enforcer
def my_fn(
    a: dict[dict[int, float]], # Note: dict keys are not validated, only values
    b: list[typing.Set[str]] # Could also just use set
) -> None:
    return None

my_fn(a={'i':{'j':1}}, b=[{'x'}]) # Success

my_fn(a={'i':{'j':'k'}}, b=[{'x'}]) # Error:
# TypeError: (my_fn): Type mismatch for typed variable `a[i][j]`. Expected one of the following `[<class 'int'>]` but got `<class 'str'>` instead. 
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

Type enforcer can enforce class instances and classes. There are a few caveats between the two.

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
