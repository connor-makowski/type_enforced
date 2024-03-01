import type_enforced
@type_enforced.Enforcer
class Foo:
    def bar(self, a: int) -> None:
        pass
        
    @type_enforced.EnforcerIgnore
    def baz(self, a: int) -> None:
        pass

try:        
    foo = Foo()
    foo.bar(a=1) #=> No Exception
    foo.baz(a='a') #=> No Exception
    print("test_class_10.py passed")
except:
    print("test_class_10.py failed")
