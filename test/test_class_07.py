import type_enforced
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


def test_class_07():
    docstring = pydoc.render_doc(Foo)
    for phrase in ["Multiply Docs Here", "Subtract Docs Here", "Add Docs Here"]:
        assert phrase in docstring
