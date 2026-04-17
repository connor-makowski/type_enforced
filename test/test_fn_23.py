import type_enforced


# Default (100%) — all items checked
@type_enforced.Enforcer
def full_check(a: list[int]) -> None:
    return None


# Sampling at 50% — bookends always checked
@type_enforced.Enforcer(iterable_sample_pct=50)
def sampled_check(a: list[int]) -> None:
    return None


# Sampling on a dict
@type_enforced.Enforcer(iterable_sample_pct=50)
def sampled_dict(a: dict[str, int]) -> None:
    return None


# Sampling on a variable-length tuple
@type_enforced.Enforcer(iterable_sample_pct=50)
def sampled_tuple(a: tuple[int, ...]) -> None:
    return None


# --- Test 1: Default 100% catches type errors anywhere in the list ---
success_1 = True
try:
    full_check(a=[1, 2, 3, 4, 5])  # Valid
except:
    success_1 = False

try:
    full_check(a=[1, 2, "bad", 4, 5])  # Middle item is wrong type
    success_1 = False  # Should have raised
except TypeError:
    pass  # Expected

# --- Test 2: Sampled check — valid list passes ---
success_2 = True
try:
    sampled_check(a=list(range(100)))  # All ints, should pass
except:
    success_2 = False

# --- Test 3: Sampled check — first item (bookend) always caught ---
success_3 = False
try:
    sampled_check(a=["bad"] + list(range(1, 100)))  # First item wrong type
    success_3 = False
except TypeError:
    success_3 = True

# --- Test 4: Sampled check — last item (bookend) always caught ---
success_4 = False
try:
    sampled_check(a=list(range(99)) + ["bad"])  # Last item wrong type
    success_4 = False
except TypeError:
    success_4 = True

# --- Test 5: Sampled dict — valid dict passes ---
success_5 = True
try:
    sampled_dict(a={str(i): i for i in range(100)})  # All valid
except:
    success_5 = False

# --- Test 6: Sampled dict — first key bookend caught ---
success_6 = False
try:
    d = {str(i): i for i in range(100)}
    first_key = list(d.keys())[0]
    d[first_key] = "bad_value"  # First value is wrong type
    sampled_dict(a=d)
    success_6 = False
except TypeError:
    success_6 = True

# --- Test 7: Sampled tuple — valid tuple passes ---
success_7 = True
try:
    sampled_tuple(a=tuple(range(100)))  # All ints
except:
    success_7 = False

# --- Test 8: Sampled tuple — first item (bookend) always caught ---
success_8 = False
try:
    sampled_tuple(a=("bad",) + tuple(range(1, 100)))
    success_8 = False
except TypeError:
    success_8 = True

# --- Test 9: Short list (<=3) — all items checked even with sampling ---
success_9 = False
try:
    sampled_check(a=[1, "bad", 3])  # Middle of 3-item list must be caught
    success_9 = False
except TypeError:
    success_9 = True


# pct=0: only first item checked
@type_enforced.Enforcer(iterable_sample_pct=0)
def zero_pct_check(a: list[int]) -> None:
    return None


# --- Test 10: pct=0 — first item caught ---
success_10 = False
try:
    zero_pct_check(a=["bad", 2, 3, 4, 5])  # First item wrong type
    success_10 = False
except TypeError:
    success_10 = True

# --- Test 11: pct=0 — last item not checked ---
success_11 = True
try:
    zero_pct_check(a=[1, 2, 3, 4, "bad"])  # Last item wrong but not checked
except TypeError:
    success_11 = False

# --- Test 12: pct=0 — empty list passes ---
success_12 = True
try:
    zero_pct_check(a=[])
except:
    success_12 = False

all_passed = all(
    [
        success_1,
        success_2,
        success_3,
        success_4,
        success_5,
        success_6,
        success_7,
        success_8,
        success_9,
        success_10,
        success_11,
        success_12,
    ]
)

if all_passed:
    print("test_fn_23.py passed")
else:
    results = [
        success_1,
        success_2,
        success_3,
        success_4,
        success_5,
        success_6,
        success_7,
        success_8,
        success_9,
        success_10,
        success_11,
        success_12,
    ]
    failed = [i + 1 for i, r in enumerate(results) if not r]
    print(f"test_fn_23.py failed (tests {failed} failed)")
