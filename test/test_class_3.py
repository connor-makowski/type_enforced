import type_enforced

class Foo():
    def __init__(self) -> None:
        pass

class Bar(Foo):
    def __init__(self) -> None:
        super().__init__()

@type_enforced.Enforcer
class Baz():
    def __init__(self, use_class: Foo) -> None:
        self.object = use_class

success=True
try:
    x=Baz(Foo())
except:
    success=False

try:
    y=Baz(Bar())
    success=False
except:
    pass

if success:
    print('test_class_3.py passed')
else:
    print('test_class_3.py failed')
