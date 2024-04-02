import re
from type_enforced.exception import ConstraintError


class __Constraint:
    def __init__(self, **kwargs):
        tmp = [(k, v) for k, v in kwargs.items() if v is not None]
        _f = dict(
            pattern=(lambda x, param: bool(re.findall(x, param)), "match pattern"),
            gt=(lambda x, param: param > x, "be greater than"),
            lt=(lambda x, param: param < x, "be less than"),
            ge=(lambda x, param: param >= x, "be greater or equal to"),
            le=(lambda x, param: param <= x, "be less than or equal to"),
            eq=(lambda x, param: param == x, "be equal to"),
            ne=(lambda x, param: param != x, "be not equal to"),
        )
        self.evaluate = [(*_f.get(k), k, v) for k, v in tmp if callable(_f.get(k)[0])]

    def __call__(self, varname, value, param_type) -> bool:
        for func, curr_msg, k, v in self.evaluate:
            if not func(v, value):
                reason = f"Expected {varname} to {curr_msg} '{v}' but got `{value}` instead."
                msg = f"Constraint error for typed variable `{varname}` ({param_type}). {reason}"
                raise ConstraintError(msg)
        return True


def Constraint(**kwargs):
    return __Constraint(**kwargs)
