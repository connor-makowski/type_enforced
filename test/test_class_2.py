import type_enforced

@type_enforced.Enforcer
class my_class:
    def __init__(self):
        self.a=10

    def my_fn(self, b:int):
        print(self.a, b)


mc=my_class()
mc.my_fn('a')
