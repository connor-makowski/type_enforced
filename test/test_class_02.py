import type_enforced


@type_enforced.Enforcer
class my_class:
    def __init__(self):
        self.a = 10

    def my_fn(self, b: int):
        pass


mc = my_class()

success = False
try:
    mc.my_fn("a")
except Exception as e:
    if "Type mismatch" in str(e):
        success = True

if success:
    print("test_class_02.py passed")
else:
    print("test_class_02.py failed")
