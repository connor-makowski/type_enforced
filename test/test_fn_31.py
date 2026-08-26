import pytest
import type_enforced


# Custom classes for inheritance tests
class Animal:
    pass


class Dog(Animal):
    pass


class Puppy(Dog):
    pass


class Cat(Animal):
    pass


class MyList(list):
    pass


class MyDict(dict):
    pass


# 1. Nested list of lists
@type_enforced.Enforcer
def fn_nested_list_list(data: list[list[int]]) -> int:
    return sum(sum(row) for row in data)


# 2. Nested list of fixed tuples
@type_enforced.Enforcer
def fn_nested_list_tuple(data: list[tuple[int, str, float]]) -> int:
    return len(data)


# 3. Nested dict of lists
@type_enforced.Enforcer
def fn_nested_dict_list(data: dict[str, list[int]]) -> int:
    return sum(len(v) for v in data.values())


# 4. Deeply nested 4-level structure
@type_enforced.Enforcer
def fn_deeply_nested(data: list[dict[str, list[dict[str, int]]]]) -> int:
    return len(data)


# 5. Inheritance in collections
@type_enforced.Enforcer
def fn_animal_list(data: list[Animal]) -> int:
    return len(data)


@type_enforced.Enforcer
def fn_animal_dict(data: dict[str, Animal]) -> int:
    return len(data)


@type_enforced.Enforcer
def fn_animal_tuple(data: tuple[Animal, ...]) -> int:
    return len(data)


# 6. Sampled validation functions
@type_enforced.Enforcer(iterable_sample_pct="first")
def fn_sample_first_list(data: list[int]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct="last")
def fn_sample_last_list(data: list[int]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct="first")
def fn_sample_first_dict(data: dict[str, int]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct="last")
def fn_sample_last_dict(data: dict[str, int]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct="first")
def fn_sample_first_tuple(data: tuple[int, ...]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct="last")
def fn_sample_last_tuple(data: tuple[int, ...]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct=10)
def fn_sample_10pct_list(data: list[int]) -> int:
    return len(data)


@type_enforced.Enforcer(iterable_sample_pct="log")
def fn_sample_log_list(data: list[int]) -> int:
    return len(data)


# 7. Unions with None
@type_enforced.Enforcer
def fn_union_none_list(data: list[int | None]) -> int:
    return len(data)


@type_enforced.Enforcer
def fn_union_none_dict(data: dict[str | int, float | None]) -> int:
    return len(data)


def test_nested_list_of_lists():
    assert fn_nested_list_list([[1, 2], [3, 4, 5]]) == 15
    assert fn_nested_list_list([]) == 0
    assert fn_nested_list_list([[]]) == 0

    with pytest.raises(TypeError):
        fn_nested_list_list([[1, "two"], [3, 4]])

    with pytest.raises(TypeError):
        fn_nested_list_list(["not a list"])


def test_nested_list_of_tuples_fixed():
    assert fn_nested_list_tuple([(1, "a", 1.5), (2, "b", 2.5)]) == 2
    assert fn_nested_list_tuple([]) == 0

    with pytest.raises(TypeError):
        fn_nested_list_tuple([(1, "a", "bad_float")])

    with pytest.raises(TypeError):
        fn_nested_list_tuple([(1, "a")])  # wrong length tuple


def test_nested_dict_of_lists():
    assert fn_nested_dict_list({"a": [1, 2], "b": [3, 4, 5]}) == 5
    assert fn_nested_dict_list({}) == 0

    with pytest.raises(TypeError):
        fn_nested_dict_list({"a": [1, "two"]})

    with pytest.raises(TypeError):
        fn_nested_dict_list({123: [1, 2]})  # int key instead of str


def test_deeply_nested_structure():
    valid_data = [
        {"key1": [{"sub1": 1}, {"sub2": 2}]},
        {"key2": [{"sub3": 3}]},
    ]
    assert fn_deeply_nested(valid_data) == 2
    assert fn_deeply_nested([]) == 0

    invalid_data = [{"key1": [{"sub1": "not_an_int"}]}]
    with pytest.raises(TypeError):
        fn_deeply_nested(invalid_data)


def test_inheritance_in_collections():
    # Dog and Puppy inherit from Animal
    animals = [Animal(), Dog(), Puppy()]
    assert fn_animal_list(animals) == 3
    assert fn_animal_dict({"a": Dog(), "b": Puppy()}) == 2
    assert fn_animal_tuple((Puppy(), Dog())) == 2

    # Cat also inherits from Animal
    assert fn_animal_list([Cat()]) == 1

    # Non-animal should fail
    with pytest.raises(TypeError):
        fn_animal_list([Animal(), "not an animal"])

    with pytest.raises(TypeError):
        fn_animal_dict({"a": "not an animal"})


def test_custom_subclassed_collections():
    # Subclasses of list and dict should pass list/dict type checks
    my_list = MyList([1, 2, 3])
    my_dict = MyDict({"a": [1, 2]})

    assert fn_sample_first_list(my_list) == 3
    assert fn_nested_dict_list(my_dict) == 2


def test_sampled_validation_first_and_last():
    # "first" checks only the first item
    assert fn_sample_first_list([1, "bad", "bad"]) == 3
    with pytest.raises(TypeError):
        fn_sample_first_list(["bad", 1, 2])

    # "last" checks only the last item
    assert fn_sample_last_list(["bad", "bad", 1]) == 3
    with pytest.raises(TypeError):
        fn_sample_last_list([1, 2, "bad"])

    # Dict first / last
    assert fn_sample_first_dict({"valid": 1, 123: "bad"}) == 2
    with pytest.raises(TypeError):
        fn_sample_first_dict({123: "bad", "valid": 1})

    assert fn_sample_last_dict({123: "bad", "valid": 1}) == 2
    with pytest.raises(TypeError):
        fn_sample_last_dict({"valid": 1, 123: "bad"})

    # Tuple first / last
    assert fn_sample_first_tuple((1, "bad", "bad")) == 3
    with pytest.raises(TypeError):
        fn_sample_first_tuple(("bad", 1, 2))

    assert fn_sample_last_tuple(("bad", "bad", 1)) == 3
    with pytest.raises(TypeError):
        fn_sample_last_tuple((1, 2, "bad"))


def test_sampled_validation_strided():
    # 10% sampling on 100 items
    valid_100 = list(range(100))
    assert fn_sample_10pct_list(valid_100) == 100
    assert fn_sample_log_list(valid_100) == 100

    # Bad element at index 0 (always checked in sampled mode)
    bad_first = ["bad"] + list(range(1, 100))
    with pytest.raises(TypeError):
        fn_sample_10pct_list(bad_first)

    # Bad element at last index (always checked in sampled mode)
    bad_last = list(range(99)) + ["bad"]
    with pytest.raises(TypeError):
        fn_sample_10pct_list(bad_last)


def test_unions_with_none():
    assert fn_union_none_list([1, None, 2, None, 3]) == 5
    assert fn_union_none_list([]) == 0

    with pytest.raises(TypeError):
        fn_union_none_list([1, "bad", None])

    assert fn_union_none_dict({"a": 1.5, 2: None, "c": None}) == 3
    with pytest.raises(TypeError):
        fn_union_none_dict({"a": "bad"})
