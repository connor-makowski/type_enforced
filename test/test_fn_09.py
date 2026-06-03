import pytest
import type_enforced
from typing import List, Set, Dict, Tuple


@type_enforced.Enforcer
def my_fn(
    a: List[int], b: Set[str], c: Dict[str, int], d: Tuple[str, int]
) -> None:
    return None


def test_fn_09():
    my_fn(
        a=[1, 2, 3],
        b={"a", "b", "c"},
        c={"a": 1, "b": 2, "c": 3},
        d=("a", 1),
    )

    with pytest.raises(TypeError, match="Type mismatch"):
        my_fn(
            a=[1, 2, 3],
            b={"a", "b", "c"},
            c={"a": 1, "b": 2, "c": 3},
            d=("a", 1.5),
        )
    with pytest.raises(TypeError, match="TypeEnforced"):
        my_fn(
            a=[1, 2, 3],
            b={"a", "b", "c"},
            c={"a": 1, "b": 2, "c": 3},
            d=("a", 1, 1),
        )
