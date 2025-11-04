# Type Enforced
[![PyPI version](https://badge.fury.io/py/type_enforced.svg)](https://badge.fury.io/py/type_enforced)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI Downloads](https://img.shields.io/pypi/dm/type_enforced.svg?label=PyPI%20downloads)](https://pypi.org/project/type_enforced/)
[![DOI](https://joss.theoj.org/papers/10.21105/joss.08832/status.svg)](https://doi.org/10.21105/joss.08832)
<!-- [![PyPI Downloads](https://pepy.tech/badge/type_enforced)](https://pypi.org/project/type_enforced/) -->

A pure python runtime type enforcer for type annotations. Enforce types in python functions and methods.

# Setup

Make sure you have Python 3.11.x (or higher) installed on your system. You can download it [here](https://www.python.org/downloads/).

- Unsupported python versions can be used, however newer features will not be available.
    - For 3.7: use type_enforced==0.0.16 (only very basic type checking is supported)
    - For 3.8: use type_enforced==0.0.16 (only very basic type checking is supported)
    - For 3.9: use type_enforced<=1.9.0 (`staticmethod`, union with `|` and `from __future__ import annotations` typechecking are not supported)
    - For 3.10: use type_enforced<=1.10.2 (`from __future__ import annotations` may cause errors (EG: when using staticmethods and classmethods))

## Installation

```
pip install type_enforced
```

## Basic Usage
```py
import type_enforced

@type_enforced.Enforcer(enabled=True, strict=True, clean_traceback=True)
def my_fn(a: int , b: int | str =2, c: int =3) -> None:
    pass
```
- Note: `enabled=True` by default if not specified. You can set `enabled=False` to disable type checking for a specific function, method, or class. This is useful for a production vs debugging environment or for undecorating a single method in a larger wrapped class.
- Note: `strict=True` by default if not specified. You can set `strict=False` to disable exceptions being raised when type checking fails. Instead, a warning will be printed to the console.
- Note: `clean_traceback=True` by default if not specified. This modifies the excepthook temporarily when a type exception is raised such that only the relevant stack (stack items not from type_enforced) is shown.

## Getting Started

`type_enforcer` contains a basic `Enforcer` wrapper that can be used to enforce many basic python typing hints. [Technical Docs Here](https://connor-makowski.github.io/type_enforced/type_enforced/enforcer.html).

`Enforcer` can be used as a decorator for functions, methods, and classes. It will enforce the type hints on the function or method inputs and outputs. It takes in the following optional arguments:

- `enabled` (True): A boolean to enable or disable type checking. If `True`, type checking will be enforced. If `False`, type checking will be disabled.
- `strict` (True): A boolean to enable or disable type mismatch exceptions. If `True` exceptions will be raised when type checking fails. If `False`, exceptions will not be raised but instead a warning will be printed to the console.

`type_enforcer` currently supports many single and multi level python types. This includes class instances and classes themselves. For example, you can force an input to be an `int`, a number `int | float`, an instance of the self defined `MyClass`, or a even a vector with `list[int]`. Items like `typing.List`, `typing.Dict`, `typing.Union` and `typing.Optional` are supported.

You can pass union types to validate one of multiple types. For example, you could validate an input was an int or a float with `int | float` or `typing.Union[int, float]`.

Nesting is allowed as long as the nested items are iterables (e.g. `typing.List`, `dict`, ...). For example, you could validate that a list is a vector with `list[int]` or possibly `typing.List[int]`.

Variables without an annotation for type are not enforced.

## Why use Type Enforced?

- `type_enforced` is a pure python type enforcer that does not require any special compiler or preprocessor to work.
- `type_enforced` uses the standard python typing hints and enforces them at runtime.
    - This means that you can use it in any python environment (3.11+) without any special setup.
- `type_enforced` is designed to be lightweight and easy to use, making it a great choice for both small and large projects.
- `type_enforced` supports complex (nested) typing hints, union types, and many of the standard python typing functions.
- `type_enforced` is designed to be fast and efficient, with minimal overhead.
- `type_enforced` offers the fastest performance for enforcing large objects of complex types
    - Note: See the [benchmarks](https://github.com/connor-makowski/type_enforced/blob/main/benchmark.md) for more information on the performance of each type checker.

## Supported Type Checking Features:

- Function/Method Input Typing
- Function/Method Return Typing
- Dataclass Typing
- All standard python types (`str`, `list`, `int`, `dict`, ...)
- Union types
    - typing.Union
    - `|` separated items (e.g. `int | float`)
- Nested types (e.g. `dict[str, int]` or `list[int|float]`)
    - Note: Each parent level must be an iterable
        - Specifically a variant of `list`, `set`, `tuple` or `dict`
    - Note: `dict` requires two types to be specified (unions count as a single type)
        - The first type is the key type and the second type is the value type
        - e.g. `dict[str, int|float]` or `dict[int, float]`
    - Note: `list` and `set` require a single type to be specified (unions count as a single type)
        - e.g. `list[int]`, `set[str]`, `list[float|str]`
    - Note: `tuple` Allows for `N` types to be specified
        - Each item refers to the positional type of each item in the tuple
        - Support for ellipsis (`...`) is supported if you only specify two types and the second is the ellipsis type
            - e.g. `tuple[int, ...]` or `tuple[int|str, ...]`
        - Note: Unions between two tuples are not supported
            - e.g. `tuple[int, str] | tuple[str, int]` will not work
    - Deeply nested types are supported too:
        - `dict[dict[int]]`
        - `list[set[str]]`
- Many of the `typing` (package) functions and methods including:
    - Standard typing functions:
        - `List`
        - `Set`
        - `Dict`
        - `Tuple`
    - `Union`
    - `Optional`
    - `Any`
    - `Sized`
        - Essentially creates a union of:
            - `list`, `tuple`, `dict`, `set`, `str`, `bytes`, `bytearray`, `memoryview`, `range`
        - Note: Can not have a nested type
            - Because this does not always meet the criteria for `Nested types` above
    - `Literal`
        - Only allow certain values to be passed. Operates slightly differently than other checks.
        - e.g. `Literal['a', 'b']` will require any passed values that are equal (`==`) to `'a'` or `'b'`.
            - This compares the value of the passed input and not the type of the passed input.
        - Note: Multiple types can be passed in the same `Literal` as acceptable values.
            - e.g. Literal['a', 'b', 1, 2] will require any passed values that are equal (`==`) to `'a'`, `'b'`, `1` or `2`.
        - Note: If type is a `str | Literal['a', 'b']`
            - The check will validate that the type is a string or the value is equal to `'a'` or `'b'`.
            - This means that an input of `'c'` will pass the check since it matches the string type, but an input of `1` will fail.
        - Note: If type is a `int | Literal['a', 'b']`
            - The check will validate that the type is an int or the value is equal to `'a'` or `'b'`.
            - This means that an input of `'c'` will fail the check, but an input of `1` will pass.
        - Note: Literals stack when used with unions.
            - e.g. `Literal['a', 'b'] | Literal[1, 2]` will require any passed values that are equal (`==`) to `'a'`, `'b'`, `1` or `2`.
    - `Callable`
        - Essentially creates a union of:
            - `staticmethod`, `classmethod`, `types.FunctionType`, `types.BuiltinFunctionType`, `types.MethodType`, `types.BuiltinMethodType`, `types.GeneratorType`
    - Note: Other functions might have support, but there are not currently tests to validate them
        - Feel free to create an issue (or better yet a PR) if you want to add tests/support
- `Constraint` validation.
    - This is a special type of validation that allows passed input to be validated.
        - Standard and custom constraints are supported.
    - Constraints are not actually types. They are type_enforced specific validators and may cause issues with other runtime or static type checkers like `mypy`.
    - This is useful for validating that a passed input is within a certain range or meets a certain criteria.
    - Note: Constraints stack when used with unions.
        - e.g. `int | Constraint(ge=0) | Constraint(le=5)` will require any passed values to be integers that are greater than or equal to `0` and less than or equal to `5`.
    - Note: The constraint is checked after type checking occurs and operates independently of the type checking.
        - This operates differently than other checks (like `Literal`) and is evaluated post type checking.
        - For example, if you have an annotation of `str | Constraint(ge=0)`, this will always raise an exception since if you pass a string, it will raise on the constraint check and if you pass an integer, it will raise on the type check.
    - Note: See the example below or technical [constraint](https://connor-makowski.github.io/type_enforced/type_enforced/utils.html#Constraint) and [generic constraint](https://connor-makowski.github.io/type_enforced/type_enforced/utils.html#GenericConstraint) docs for more information.

## Interactive Example

```py
>>> import type_enforced
>>> @type_enforced.Enforcer
... def my_fn(a: int , b: int|str =2, c: int =3) -> None:
...     pass
...
>>> my_fn(a=1, b=2, c=3)
>>> my_fn(a=1, b='2', c=3)
>>> my_fn(a='a', b=2, c=3)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
TypeError: TypeEnforced Exception (my_fn): Type mismatch for typed variable `a`. Expected one of the following `[<class 'int'>]` but got `<class 'str'>` with value `a` instead.

```

## Nested Examples
```py
import type_enforced
import typing

@type_enforced.Enforcer
def my_fn(
    a: dict[str,dict[str, int|float]], # Note: For dicts, the key is the first type and the value is the second type
    b: list[typing.Set[str]] # Could also just use set
) -> None:
    return None

my_fn(a={'i':{'j':1}}, b=[{'x'}]) # Success

my_fn(a={'i':{'j':'k'}}, b=[{'x'}]) # Error =>
# TypeError: TypeEnforced Exception (my_fn): Type mismatch for typed variable `a['i']['j']`. Expected one of the following `[<class 'int'>, <class 'float'>]` but got `<class 'str'>` with value `k` instead.
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

    def my_other_fn(self, a: int, b: int | str):
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
    def my_other_fn(a: int, b: int | str):
      pass
```

Dataclasses are suported too.

```py
import type_enforced
from dataclasses import dataclass

@type_enforced.Enforcer
@dataclass
class my_class:
    foo: int
    bar: str
```

You can skip enforcement if you add the argument `enabled=False` in the `Enforcer` call.
- This is useful for a production vs debugging environment.
- This is also useful for undecorating a single method in a larger wrapped class.
- Note: You can set `enabled=False` for an entire class or simply disable a specific method in a larger wrapped class.
- Note: Method level wrapper `enabled` values take precedence over class level wrappers.
```py
import type_enforced
@type_enforced.Enforcer
class my_class:
    def my_fn(self, a: int) -> None:
        pass

    @type_enforced.Enforcer(enabled=False)
    def my_other_fn(self, a: int) -> None:
        pass
```

## Validate with Constraints
Type enforcer can enforce constraints for passed variables. These constraints are validated after any type checks are made.

To enforce basic input values are integers greater than or equal to zero, you can use the [Constraint](https://connor-makowski.github.io/type_enforced/type_enforced/utils.html#Constraint) class like so:
```py
import type_enforced
from type_enforced.utils import Constraint

@type_enforced.Enforcer()
def positive_int_test(value: int |Constraint(ge=0)) -> bool:
    return True

positive_int_test(1) # Passes
positive_int_test(-1) # Fails
positive_int_test(1.0) # Fails
```

To enforce a [GenericConstraint](https://connor-makowski.github.io/type_enforced/type_enforced/utils.html#GenericConstraint):
```py
import type_enforced
from type_enforced.utils import GenericConstraint

CustomConstraint = GenericConstraint(
    {
        'in_rgb': lambda x: x in ['red', 'green', 'blue'],
    }
)

@type_enforced.Enforcer()
def rgb_test(value: str | CustomConstraint) -> bool:
    return True

rgb_test('red') # Passes
rgb_test('yellow') # Fails
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

By default, type_enforced will check for subclasses of a class when validating types. This means that if you pass a subclass of the expected class, it will pass the type check.

Note: Uninitialized class objects that are passed are not checked for subclasses.

```py
import type_enforced

class Foo:
    pass

class Bar(Foo):
    pass

class Baz:
    pass

@type_enforced.Enforcer
def my_fn(custom_class: Foo):
    pass

my_fn(Foo()) # Passes as expected
my_fn(Bar()) # Passes as expected
my_fn(Baz()) # Raises TypeError as expected
```

## What changed in 2.0.0?
The main changes in version 2.0.0 revolve around migrating towards the standard python typing hint process and away from the original type_enfoced type hints (as type enforced was originally created before the `|` operator was added to python).
- Support for python3.10 has been dropped.
- List based union types are no longer supported.
    - For example `[int, float]` is no longer a supported type hint.
    - Use `int|float` or `typing.Union[int, float]` instead.
- Dict types now require two types to be specified.
    - The first type is the key type and the second type is the value type.
    - For example, `dict[str, int|float]` or `dict[int, float]` are valid types.
- Tuple types now allow for `N` types to be specified.
    - Each item refers to the positional type of each item in the tuple.
    - Support for ellipsis (`...`) is supported if you only specify two types and the second is the ellipsis type.
        - For example, `tuple[int, ...]` or `tuple[int|str, ...]` are valid types.
    - Note: Unions between two tuples are not supported.
        - For example, `tuple[int, str] | tuple[str, int]` will not work.
- Constraints and Literals can now be stacked with unions.
    - For example, `int | Constraint(ge=0) | Constraint(le=5)` will require any passed values to be integers that are greater than or equal to `0` and less than or equal to `5`.
    - For example, `Literal['a', 'b'] | Literal[1, 2]` will require any passed values that are equal (`==`) to `'a'`, `'b'`, `1` or `2`.
- Literals now evaluate during the same time as type checking and operate as OR checks.
    - For example, `int | Literal['a', 'b']` will validate that the type is an int or the value is equal to `'a'` or `'b'`.
- Constraints are still are evaluated after type checking and operate independently of the type checking.

# Support

## Bug Reports and Feature Requests

If you find a bug or are looking for a new feature, please open an issue on GitHub.

## Need Help?

If you need help, please open an issue on GitHub.

# Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Development

To avoid extra development overhead, we expect all developers to use a unix based environment (Linux or Mac). If you use Windows, please use WSL2.

For development, we test using Docker so we can lock system deps and swap out python versions easily. However, you can also use a virtual environment if you prefer. We provide a test script and a prettify script to help with development.

## Making Changes

1) Fork the repo and clone it locally.
2) Make your modifications.
3) Use Docker or a virtual environment to run tests and make sure they pass.
4) Prettify your code.
5) **DO NOT GENERATE DOCS**.
    - We will generate the docs and update the version number when we are ready to release a new version.
6) Only commit relevant changes and add clear commit messages.
    - Atomic commits are preferred.
7) Submit a pull request.

## Docker

Make sure Docker is installed and running.

- Create a docker container and drop into a shell
    - `./run.sh`
- Run all tests (see ./utils/test.sh)
    - `./run.sh test`
- Prettify the code (see ./utils/prettify.sh)
    - `./run.sh prettify`

- Note: You can and should modify the `Dockerfile` to test different python versions.

## Virtual Environment

- Create a virtual environment
    - `python3.XX -m venv venv`
        - Replace `3.XX` with your python version (3.11 or higher)
- Activate the virtual environment
    - `source venv/bin/activate`
- Install the development requirements
    - `pip install -r requirements/dev.txt`
- Run Tests
    - `./utils/test.sh`
- Prettify Code
    - `./utils/prettify.sh`