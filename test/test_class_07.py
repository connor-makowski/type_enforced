import type_enforced
import sys

import pydoc


@type_enforced.Enforcer
class Foo:
    @classmethod
    def add(self, a: int, b: int) -> int:
        """
        Add Docs Here
        """
        return a + b

    @staticmethod
    def subtract(a: int, b: int) -> int:
        """
        Subtract Docs Here
        """
        return a - b

    def multiply(self, a: int, b: int) -> int:
        """
        Multiply Docs Here
        """
        return a * b


docstring = pydoc.render_doc(Foo)

docstring_checks = ["Multiply Docs Here", "Subtract Docs Here", "Add Docs Here"]

if any([i not in docstring for i in docstring_checks]):
    print("test_class_07.py failed")
else:
    print("test_class_07.py passed")
