"""
# Type Enforced
[![PyPI version](https://badge.fury.io/py/type_enforced.svg)](https://badge.fury.io/py/type_enforced)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI Downloads](https://img.shields.io/pypi/dm/type_enforced.svg?label=PyPI%20downloads)](https://pypi.org/project/type_enforced/)

A pure python (no special compiler required) type enforcer for type annotations. Enforce types in python functions and methods.

# Setup

Make sure you have Python 3.11.x (or higher) installed on your system. You can download it [here](https://www.python.org/downloads/).

- Unsupported python versions can be used, however newer features will not be available.
    - For 3.7: use type_enforced==0.0.16 (only very basic type checking is supported)
    - For 3.8: use type_enforced==0.0.16 (only very basic type checking is supported)
    - For 3.9: use type_enforced<=1.9.0 (`staticmethod`, union with `|` and `from __future__ import annotations` typechecking are not supported)
    - For 3.10: use type_enforced<=10.2.0 (`from __future__ import annotations` may cause errors (EG: when using staticmethods and classmethods))

### Installation

```
pip install type_enforced
```

## Basic Usage
```py
import type_enforced

@type_enforced.Enforcer(enabled=True)
def my_fn(a: int , b: int | str =2, c: int =3) -> None:
    pass
```
- Note: `enabled=True` by default if not specified. You can set `enabled=False` to disable type checking for a specific function, method, or class. This is useful for a production vs debugging environment or for undecorating a single method in a larger wrapped class.

## Getting Started

`type_enforcer` contains a basic `Enforcer` wrapper that can be used to enforce many basic python typing hints. [Technical Docs Here](https://connor-makowski.github.io/type_enforced/type_enforced/enforcer.html).

`type_enforcer` currently supports many single and multi level python types. This includes class instances and classes themselves. For example, you can force an input to be an `int`, a number `int | float`, an instance of the self defined `MyClass`, or a even a vector with `list[int]`. Items like `typing.List`, `typing.Dict`, `typing.Union` and `typing.Optional` are supported.

You can pass union types to validate one of multiple types. For example, you could validate an input was an int or a float with `int | float` or `typing.Union[int, float]`.

Nesting is allowed as long as the nested items are iterables (e.g. `typing.List`, `dict`, ...). For example, you could validate that a list is a vector with `list[int]` or possibly `typing.List[int]`.

Variables without an annotation for type are not enforced.

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
    - Support for elipsis (`...`) is supported if you only specify two types and the second is the elipsis type.
        - For example, `tuple[int, ...]` or `tuple[int|str, ...]` are valid types.
    - Note: Unions between two tuples are not supported.
        - For example, `tuple[int, str] | tuple[str, int]` will not work.
- Constraints and Literals can now be stacked with unions.
    - For example, `int | Constraint(ge=0) | Constraint(le=5)` will require any passed values to be integers that are greater than or equal to `0` and less than or equal to `5`.
    - For example, `Literal['a', 'b'] | Literal[1, 2]` will require any passed values that are equal (`==`) to `'a'`, `'b'`, `1` or `2`.
- Literals now evaluate during the same time as type checking and operate as OR checks.
    - For example, `int | Literal['a', 'b']` will validate that the type is an int or the value is equal to `'a'` or `'b'`.
- Constraints are still are evaluated after type checking and operate independently of the type checking.

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
        - Support for elipsis (`...`) is supported if you only specify two types and the second is the elipsis type
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
    - This is useful for validating that a passed input is within a certain range or meets a certain criteria.
    - Note: Constraints stack when used with unions.
        - e.g. `int | Constraint(ge=0) | Constraint(le=5)` will require any passed values to be integers that are greater than or equal to `0` and less than or equal to `5`.
    - Note: The constraint is checked after type checking occurs and operates independently of the type checking.
        - This operates differently than other checks (like `Literal`) and is evaluated post type checking.
        - For example, if you have an annotation of `str | Constraint(ge=0)`, this will always raise an exception since if you pass a string, it will raise on the constraint check and if you pass an integer, it will raise on the type check.
    - Note: See the example below or technical [constraint](https://connor-makowski.github.io/type_enforced/type_enforced/utils.html#Constraint) and [generic constraint](https://connor-makowski.github.io/type_enforced/type_enforced/utils.html#GenericConstraint) docs for more information.
    ```

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
  File "<python-input-2>", line 1, in <module>
    my_fn(a='a', b=2, c=3)
    ~~~~~^^^^^^^^^^^^^^^^^
  File "/app/type_enforced/enforcer.py", line 233, in __call__
    self.__check_type__(assigned_vars.get(key), value, key)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/type_enforced/enforcer.py", line 266, in __check_type__
    self.__exception__(
    ~~~~~~~~~~~~~~~~~~^
        f"Type mismatch for typed variable `{key}`. Expected one of the following `{list(expected.keys())}` but got `{obj_type}` with value `{obj}` instead."
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/app/type_enforced/enforcer.py", line 188, in __exception__
    raise TypeError(f"TypeEnforced Exception ({self.__fn__.__qualname__}): {message}")
TypeError: TypeEnforced Exception (my_fn): Type mismatch for typed variable `a`. Expected one of the following `[<class 'int'>]` but got `<class 'str'>` with value `a` instead.
```

## Nested Examples
```py
import type_enforced
import typing

@type_enforced.Enforcer
def my_fn(
    a: dict[str,dict[str, int|float]], # Note: dict keys are not validated, only values
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

## Validate classes with inheritance

A special helper utility is provided to get all the subclasses of a class (with delayed evaluation - so you can validate subclasses even if they were defined later or in other files).

See: [WithSubclasses](https://connor-makowski.github.io/type_enforced/type_enforced/utils.html#WithSubclasses) for more information.

```py
import type_enforced
from type_enforced.utils import WithSubclasses

class Foo:
    pass

class Bar(Foo):
    pass

class Baz:
    pass

@type_enforced.Enforcer
def my_fn(custom_class: WithSubclasses(Foo)):
    pass

my_fn(Foo()) # Passes as expected
my_fn(Bar()) # Passes as expected
my_fn(Baz()) # Raises TypeError as expected
```

# Development
## Running Tests, Prettifying Code, and Updating Docs

Make sure Docker is installed and running.

- Create a docker container and drop into a shell
    - `./run.sh`
- Run all tests (see ./utils/test.sh)
    - `./run.sh test`
- Prettify the code (see ./utils/prettify.sh)
    - `./run.sh prettify`
- Update the docs (see ./utils/docs.sh)
    - `./run.sh docs`

- Note: You can and should modify the `Dockerfile` to test different python versions.
"""

from .enforcer import Enforcer, FunctionMethodEnforcer
