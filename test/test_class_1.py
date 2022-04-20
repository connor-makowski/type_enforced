import type_enforced

class my_class:
    def __init__(self):
        self.a=10

    @type_enforced.Enforcer
    def my_fn(self, b:int):
        print(self.a, b)


mc=my_class()
mc.my_fn('a')
