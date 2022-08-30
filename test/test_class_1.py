import type_enforced

class my_class:
    def __init__(self):
        self.a=10

    @type_enforced.Enforcer
    def my_fn(self, b:int):
        print(self.a, b)


mc=my_class()

success=False
try:
    mc.my_fn('a')
except Exception as e:
    if 'Type mismatch' in str(e):
        success=True

if success:
    print('test_class_1.py passed')
else:
    print('test_class_1.py failed')
