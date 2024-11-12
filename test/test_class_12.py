from test_class_12_utils.bar import Bar, foo
from test_class_12_utils.baz import Baz

passed = True

# Special Test for delayed class inheritance binding

try:
    foo(Baz())
    foo(Bar())
except:
    passed = False

try:
    foo(1)
    passed = False
except:
    pass

if passed:
    print("test_class_12.py passed")
else:
    print("test_class_12.py failed")
