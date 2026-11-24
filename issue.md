Thanks for creating an issue. Great to have you contributing! 

TLDR: The fallback python engine did not work the same as the AST inline engine. When a fallback happened for things like Collections, the framework would not operate as intended.

# Fixes for main issue:

- Added a test to ensure this is caught in the future
- Added logic to python fallback to properly handle this

## Reference Commit: 

375979434fa37ba1f4ccc148d125fddc39c56bf2


## Secondary issue:

A secondary related issue is apparent. Why is this failing over from AST to python fallback?



Some Notes for Project Use: 

- In PEP 484 and Python's data model, an annotation val: Collection means val must satisfy the Collection protocol (__iter__, __len__, and __contains__), which means isinstance(val, Collection) must be True.
- Python's EnumMeta implements __iter__, __len__, and __contains__, making any Enum class an instance of collections.abc.Collection. Static type checkers (such as mypy and pyright) accept an Enum class passed where  Collection is expected.
- Previously, type_enforced's dynamic runtime fallback path had an incorrect internal assumption: whenever isinstance(obj, type) was True, it assumed the parameter could only be checked against type[T] or type, ignoring whether the class itself is an instance of the annotated type. The fix restores standard Python type checking semantics.
- The AST inlined path (specialized.py) was already doing isinstance(val, Collection) and accepting SomeEnum. 
    - The issue was purely an internal discrepancy where dataclasses (which generate their methods in memory and cannot be AST-inlined from disk) fell back to FunctionMethodEnforcer.__check_type__, which had the bug.
- The fix simply brings the runtime fallback path into parity with the inlined engine
