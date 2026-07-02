---
name: changing-code
description: Modify code for type enforced. Use when asked to change code, refactor, or implement new functionality.
---

# Changing Code

If you are asked to change code, refactor, or implement new functionality, use this skill. It is intended for modifying existing code in the `type_enforced` package, not for writing tests (see [add-test](../add-test/SKILL.md)) or running tests (see [test](../test/SKILL.md)).

[ ] Identify the relevant file(s) in the `type_enforced/` package
[ ] Make all necessary changes
[ ] Ensure that the code adheres to the project's conventions and style guidelines
[ ] Determine if making a new test is necessary and if so, create it using the [add-test](../add-test/SKILL.md) skill
[ ] Run the test suite using the `test` skill aiming for a quick first pass to check for obvious issues
[ ] If the tests pass
    [ ] Use the `benchmark` skill to run the benchmark tests and compare the results with the previous benchmarks
    [ ] If the benchmarks are worse, consider optimizing the code or reverting changes. If noticibly different, report the issue to the user and provide relevant information.
    [ ] Run the linter using the `lint` skill to ensure code formatting is correct
    [ ] Run a complete test suite with `test` skill to ensure all tests pass across all supported Python versions.
    [ ] If the tests pass return to the user with a summary of the changes made and any relevant information about the implementation.
[ ] If the tests fail, diagnose if the issue is with any new tests, with the code changes, or with existing tests.
    [ ] If you find yourself stuck in a loop of failing tests, report the issue to the user and provide any relevant information about the failure.
    [ ] If the issue is with new tests, move back to the Making the necessary changes step and continue from there.
    [ ] If the issue is with code changes, fix them and rerun the test suite. 
    [ ] If the issue is with existing tests, report it to the user and provide any relevant information about the failure.

