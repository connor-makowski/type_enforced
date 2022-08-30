import type_enforced

@type_enforced.Enforcer
class my_class:
    def __init__(self):
        self.a=10

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
    print('test_class_2.py passed')
else:
    print('test_class_2.py failed')
