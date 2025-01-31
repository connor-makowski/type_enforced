from __future__ import annotations
import type_enforced


@type_enforced.Enforcer
class my_class:
    def __init__(self):
        self.a = 10

    @type_enforced.Enforcer
    def my_fn(self, b: int):
        pass


mc = my_class()

mc.my_fn(1)

success = True

try:
    mc.my_fn(1)
except Exception as e:
    success = False

try:
    mc.my_fn("a")
    success = False
except Exception as e:
    if "Type mismatch" not in str(e):
        success = False

if success:
    print("test_class_13.py passed")
else:
    print("test_class_13.py failed")
