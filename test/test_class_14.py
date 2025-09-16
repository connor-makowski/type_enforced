from __future__ import annotations
import type_enforced

import os, sys


###########################################
# Copied from:
# https://stackoverflow.com/questions/8391411/how-to-block-calls-to-print
class HiddenPrints:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, "w")

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout


###########################################


@type_enforced.Enforcer(strict=True)
class my_class:
    def __init__(self):
        pass

    def fn_1(self, a: int):
        pass

    @type_enforced.Enforcer(strict=False)
    def fn_2(self, a: int):
        pass


@type_enforced.Enforcer(strict=False)
class my_class_2:
    def __init__(self):
        pass

    def fn_1(self, a: int):
        pass

    @type_enforced.Enforcer(strict=True)
    def fn_2(self, a: int):
        pass


mc = my_class()
mc_2 = my_class_2()

success = True

try:
    with HiddenPrints():
        mc.fn_2("a")
        mc_2.fn_1("a")
except Exception as e:
    success = False
try:
    mc.fn_1("a")
    success = False
except Exception as e:
    pass

try:
    mc_2.fn_2("a")
    success = False
except Exception as e:
    pass

if success:
    print("test_class_14.py passed")
else:
    print("test_class_14.py failed")
