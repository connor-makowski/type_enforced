#include "validators.hpp"
#include <vector>
#include <unordered_map>
#include <string>
#include <cstdlib>

namespace type_enforced {

static inline bool check_item_union(PyObject* item, PyTypeObject* const* exp_types, size_t num_types) {
    PyTypeObject* item_type = Py_TYPE(item);
    for (size_t j = 0; j < num_types; ++j) {
        if (item_type == exp_types[j]) return true;
    }
    for (size_t j = 0; j < num_types; ++j) {
        if (PyObject_TypeCheck(item, exp_types[j])) return true;
    }
    return false;
}

static inline size_t fast_quasi_rand(size_t bound) noexcept {
    if (bound == 0) return 0;
    static thread_local uint32_t weyl_counter = 0;
    weyl_counter += 0x9E3779B9u;
    return (static_cast<uint64_t>(weyl_counter) * bound) >> 32;
}

static inline size_t calc_log_count(size_t len) noexcept {
    if (len == 0) return 0;
    if (len == 1) return 1;
    return static_cast<size_t>(64 - __builtin_clzll(static_cast<unsigned long long>(len - 1)));
}

// ----------------- GENERIC VALIDATOR ENGINE -----------------

struct SubclassTypeValidatorNode : public TypeValidatorNode {
    PyTypeObject* expected_type;
    explicit SubclassTypeValidatorNode(PyTypeObject* t)
        : TypeValidatorNode(NodeKind::SUBCLASS_TYPE), expected_type(t) {}

    bool validate(PyObject* obj) const noexcept override {
        if (!obj) return false;
        PyTypeObject* t = Py_TYPE(obj);
        if (__builtin_expect(t == expected_type, 1)) return true;
        return PyObject_TypeCheck(obj, expected_type) != 0;
    }
};

struct UnionTypeValidatorNode : public TypeValidatorNode {
    std::vector<PyTypeObject*> types;
    explicit UnionTypeValidatorNode(std::vector<PyTypeObject*> ts)
        : TypeValidatorNode(NodeKind::UNION_TYPE), types(std::move(ts)) {}

    bool validate(PyObject* obj) const noexcept override {
        if (!obj) return false;
        PyTypeObject* t = Py_TYPE(obj);
        for (auto* exp : types) {
            if (t == exp) return true;
        }
        for (auto* exp : types) {
            if (PyObject_TypeCheck(obj, exp)) return true;
        }
        return false;
    }
};

struct ComplexUnionValidatorNode : public TypeValidatorNode {
    std::vector<std::shared_ptr<TypeValidatorNode>> branches;
    explicit ComplexUnionValidatorNode(std::vector<std::shared_ptr<TypeValidatorNode>> bs)
        : TypeValidatorNode(NodeKind::COMPLEX_UNION), branches(std::move(bs)) {}

    bool validate(PyObject* obj) const noexcept override {
        if (!obj) return false;
        for (const auto& b : branches) {
            if (b->validate(obj)) return true;
        }
        return false;
    }
};

template <bool IsList>
struct SequenceValidatorNode : public TypeValidatorNode {
    std::shared_ptr<TypeValidatorNode> elem_val;
    SampleStrategy strategy;
    double sample_pct_val;
    PyTypeObject* single_type;
    const std::vector<PyTypeObject*>* union_types;

    SequenceValidatorNode(std::shared_ptr<TypeValidatorNode> el, SampleStrategy strat, double val = 0.0)
        : TypeValidatorNode(IsList ? NodeKind::LIST : NodeKind::VAR_TUPLE),
          elem_val(std::move(el)), strategy(strat), sample_pct_val(val),
          single_type(nullptr), union_types(nullptr) {
        if (elem_val) {
            if (elem_val->kind == NodeKind::SUBCLASS_TYPE) {
                single_type = static_cast<SubclassTypeValidatorNode*>(elem_val.get())->expected_type;
            } else if (elem_val->kind == NodeKind::UNION_TYPE) {
                union_types = &static_cast<UnionTypeValidatorNode*>(elem_val.get())->types;
            }
        }
    }

    inline bool check_elem(PyObject* item) const noexcept {
        if (single_type) {
            PyTypeObject* t = Py_TYPE(item);
            if (__builtin_expect(t == single_type, 1)) return true;
            return PyObject_TypeCheck(item, single_type) != 0;
        }
        if (union_types) {
            PyTypeObject* t = Py_TYPE(item);
            for (auto* exp : *union_types) {
                if (t == exp) return true;
            }
            for (auto* exp : *union_types) {
                if (PyObject_TypeCheck(item, exp)) return true;
            }
            return false;
        }
        return elem_val->validate(item);
    }

    inline bool validate_all(PyObject* const* items, Py_ssize_t size) const noexcept {
        if (single_type) {
            Py_ssize_t i = 0;
            for (; i + 3 < size; i += 4) {
                if (__builtin_expect(Py_TYPE(items[i]) != single_type, 0) && !PyObject_TypeCheck(items[i], single_type)) return false;
                if (__builtin_expect(Py_TYPE(items[i + 1]) != single_type, 0) && !PyObject_TypeCheck(items[i + 1], single_type)) return false;
                if (__builtin_expect(Py_TYPE(items[i + 2]) != single_type, 0) && !PyObject_TypeCheck(items[i + 2], single_type)) return false;
                if (__builtin_expect(Py_TYPE(items[i + 3]) != single_type, 0) && !PyObject_TypeCheck(items[i + 3], single_type)) return false;
            }
            for (; i < size; ++i) {
                if (__builtin_expect(Py_TYPE(items[i]) != single_type, 0) && !PyObject_TypeCheck(items[i], single_type)) return false;
            }
            return true;
        }
        if (union_types) {
            const auto& ut = *union_types;
            size_t u_count = ut.size();
            PyTypeObject* const* u_arr = ut.data();
            if (u_count == 2) {
                PyTypeObject* t0 = u_arr[0];
                PyTypeObject* t1 = u_arr[1];
                Py_ssize_t i = 0;
                for (; i + 3 < size; i += 4) {
                    PyTypeObject* it0 = Py_TYPE(items[i]);
                    if (__builtin_expect(it0 != t0 && it0 != t1, 0)) {
                        if (!PyObject_TypeCheck(items[i], t0) && !PyObject_TypeCheck(items[i], t1)) return false;
                    }
                    PyTypeObject* it1 = Py_TYPE(items[i + 1]);
                    if (__builtin_expect(it1 != t0 && it1 != t1, 0)) {
                        if (!PyObject_TypeCheck(items[i + 1], t0) && !PyObject_TypeCheck(items[i + 1], t1)) return false;
                    }
                    PyTypeObject* it2 = Py_TYPE(items[i + 2]);
                    if (__builtin_expect(it2 != t0 && it2 != t1, 0)) {
                        if (!PyObject_TypeCheck(items[i + 2], t0) && !PyObject_TypeCheck(items[i + 2], t1)) return false;
                    }
                    PyTypeObject* it3 = Py_TYPE(items[i + 3]);
                    if (__builtin_expect(it3 != t0 && it3 != t1, 0)) {
                        if (!PyObject_TypeCheck(items[i + 3], t0) && !PyObject_TypeCheck(items[i + 3], t1)) return false;
                    }
                }
                for (; i < size; ++i) {
                    PyTypeObject* it = Py_TYPE(items[i]);
                    if (__builtin_expect(it != t0 && it != t1, 0)) {
                        if (!PyObject_TypeCheck(items[i], t0) && !PyObject_TypeCheck(items[i], t1)) return false;
                    }
                }
                return true;
            }
            if (u_count == 3) {
                PyTypeObject* t0 = u_arr[0];
                PyTypeObject* t1 = u_arr[1];
                PyTypeObject* t2 = u_arr[2];
                Py_ssize_t i = 0;
                for (; i + 3 < size; i += 4) {
                    PyTypeObject* it0 = Py_TYPE(items[i]);
                    if (__builtin_expect(it0 != t0 && it0 != t1 && it0 != t2, 0)) {
                        if (!PyObject_TypeCheck(items[i], t0) && !PyObject_TypeCheck(items[i], t1) && !PyObject_TypeCheck(items[i], t2)) return false;
                    }
                    PyTypeObject* it1 = Py_TYPE(items[i + 1]);
                    if (__builtin_expect(it1 != t0 && it1 != t1 && it1 != t2, 0)) {
                        if (!PyObject_TypeCheck(items[i + 1], t0) && !PyObject_TypeCheck(items[i + 1], t1) && !PyObject_TypeCheck(items[i + 1], t2)) return false;
                    }
                    PyTypeObject* it2 = Py_TYPE(items[i + 2]);
                    if (__builtin_expect(it2 != t0 && it2 != t1 && it2 != t2, 0)) {
                        if (!PyObject_TypeCheck(items[i + 2], t0) && !PyObject_TypeCheck(items[i + 2], t1) && !PyObject_TypeCheck(items[i + 2], t2)) return false;
                    }
                    PyTypeObject* it3 = Py_TYPE(items[i + 3]);
                    if (__builtin_expect(it3 != t0 && it3 != t1 && it3 != t2, 0)) {
                        if (!PyObject_TypeCheck(items[i + 3], t0) && !PyObject_TypeCheck(items[i + 3], t1) && !PyObject_TypeCheck(items[i + 3], t2)) return false;
                    }
                }
                for (; i < size; ++i) {
                    PyTypeObject* it = Py_TYPE(items[i]);
                    if (__builtin_expect(it != t0 && it != t1 && it != t2, 0)) {
                        if (!PyObject_TypeCheck(items[i], t0) && !PyObject_TypeCheck(items[i], t1) && !PyObject_TypeCheck(items[i], t2)) return false;
                    }
                }
                return true;
            }
            Py_ssize_t i = 0;
            for (; i + 3 < size; i += 4) {
                if (!check_item_union(items[i], u_arr, u_count) ||
                    !check_item_union(items[i + 1], u_arr, u_count) ||
                    !check_item_union(items[i + 2], u_arr, u_count) ||
                    !check_item_union(items[i + 3], u_arr, u_count)) return false;
            }
            for (; i < size; ++i) {
                if (!check_item_union(items[i], u_arr, u_count)) return false;
            }
            return true;
        }
        Py_ssize_t i = 0;
        for (; i + 3 < size; i += 4) {
            if (!elem_val->validate(items[i]) ||
                !elem_val->validate(items[i + 1]) ||
                !elem_val->validate(items[i + 2]) ||
                !elem_val->validate(items[i + 3])) return false;
        }
        for (; i < size; ++i) {
            if (!elem_val->validate(items[i])) return false;
        }
        return true;
    }

    inline bool validate_items(PyObject* const* items, Py_ssize_t size) const noexcept {
        switch (strategy) {
            case SampleStrategy::FIRST:
                return check_elem(items[0]);
            case SampleStrategy::LAST:
                return check_elem(items[size - 1]);
            case SampleStrategy::BOOKEND: {
                if (!check_elem(items[0])) return false;
                if (size > 1 && !check_elem(items[size - 1])) return false;
                return true;
            }
            case SampleStrategy::BOOKEND_PLUS: {
                if (!check_elem(items[0])) return false;
                if (size > 1 && !check_elem(items[size - 1])) return false;
                if (size > 2) {
                    size_t mid = 1 + fast_quasi_rand(static_cast<size_t>(size - 2));
                    if (!check_elem(items[mid])) return false;
                }
                return true;
            }
            case SampleStrategy::RANDOM_ONE: {
                size_t idx = fast_quasi_rand(static_cast<size_t>(size));
                return check_elem(items[idx]);
            }
            case SampleStrategy::LOG:
            case SampleStrategy::PERCENT:
            case SampleStrategy::COUNT: {
                size_t count = 1;
                if (strategy == SampleStrategy::LOG) {
                    count = calc_log_count(static_cast<size_t>(size));
                } else if (strategy == SampleStrategy::PERCENT) {
                    count = static_cast<size_t>((size * sample_pct_val + 99.0) / 100.0);
                } else {
                    count = static_cast<size_t>(sample_pct_val);
                }
                if (count < 1) count = 1;
                if (count >= static_cast<size_t>(size)) {
                    return validate_all(items, size);
                }
                if (!check_elem(items[0])) return false;
                if (count > 1 && !check_elem(items[size - 1])) return false;
                if (count > 2 && size > 2) {
                    Py_ssize_t step = (size - 1) / (count - 1);
                    if (step < 1) step = 1;
                    for (Py_ssize_t i = step; i < size - 1; i += step) {
                        if (!check_elem(items[i])) return false;
                    }
                }
                return true;
            }
            case SampleStrategy::ALL:
            default:
                return validate_all(items, size);
        }
    }

    bool validate(PyObject* obj) const noexcept override {
        if (!obj) return false;
        if constexpr (IsList) {
            if (!PyList_Check(obj)) return false;
            Py_ssize_t size = PyList_GET_SIZE(obj);
            if (size == 0) return true;
            PyObject** items = PySequence_Fast_ITEMS(obj);
            return validate_items(items, size);
        } else {
            if (!PyTuple_Check(obj)) return false;
            Py_ssize_t size = PyTuple_GET_SIZE(obj);
            if (size == 0) return true;
            PyObject* const* items = &PyTuple_GET_ITEM(obj, 0);
            return validate_items(items, size);
        }
    }
};

using ListValidatorNode = SequenceValidatorNode<true>;
using VariableTupleValidatorNode = SequenceValidatorNode<false>;

struct DictValidatorNode : public TypeValidatorNode {
    std::shared_ptr<TypeValidatorNode> key_val;
    std::shared_ptr<TypeValidatorNode> val_val;
    SampleStrategy strategy;
    double sample_pct_val;
    PyTypeObject* single_k_type;
    PyTypeObject* single_v_type;
    const std::vector<PyTypeObject*>* union_k_types;
    const std::vector<PyTypeObject*>* union_v_types;

    DictValidatorNode(std::shared_ptr<TypeValidatorNode> k, std::shared_ptr<TypeValidatorNode> v,
                      SampleStrategy strat, double pct_val = 0.0)
        : TypeValidatorNode(NodeKind::DICT), key_val(std::move(k)), val_val(std::move(v)),
          strategy(strat), sample_pct_val(pct_val),
          single_k_type(nullptr), single_v_type(nullptr),
          union_k_types(nullptr), union_v_types(nullptr) {
        if (key_val) {
            if (key_val->kind == NodeKind::SUBCLASS_TYPE) {
                single_k_type = static_cast<SubclassTypeValidatorNode*>(key_val.get())->expected_type;
            } else if (key_val->kind == NodeKind::UNION_TYPE) {
                union_k_types = &static_cast<UnionTypeValidatorNode*>(key_val.get())->types;
            }
        }
        if (val_val) {
            if (val_val->kind == NodeKind::SUBCLASS_TYPE) {
                single_v_type = static_cast<SubclassTypeValidatorNode*>(val_val.get())->expected_type;
            } else if (val_val->kind == NodeKind::UNION_TYPE) {
                union_v_types = &static_cast<UnionTypeValidatorNode*>(val_val.get())->types;
            }
        }
    }

    inline bool check_key(PyObject* key) const noexcept {
        if (single_k_type) {
            PyTypeObject* t = Py_TYPE(key);
            if (__builtin_expect(t == single_k_type, 1)) return true;
            return PyObject_TypeCheck(key, single_k_type) != 0;
        }
        if (union_k_types) {
            PyTypeObject* t = Py_TYPE(key);
            for (auto* exp : *union_k_types) {
                if (t == exp) return true;
            }
            for (auto* exp : *union_k_types) {
                if (PyObject_TypeCheck(key, exp)) return true;
            }
            return false;
        }
        return key_val->validate(key);
    }

    inline bool check_val(PyObject* val) const noexcept {
        if (single_v_type) {
            PyTypeObject* t = Py_TYPE(val);
            if (__builtin_expect(t == single_v_type, 1)) return true;
            return PyObject_TypeCheck(val, single_v_type) != 0;
        }
        if (union_v_types) {
            PyTypeObject* t = Py_TYPE(val);
            for (auto* exp : *union_v_types) {
                if (t == exp) return true;
            }
            for (auto* exp : *union_v_types) {
                if (PyObject_TypeCheck(val, exp)) return true;
            }
            return false;
        }
        return val_val->validate(val);
    }

    inline bool check_pair(PyObject* key, PyObject* val) const noexcept {
        return check_key(key) && check_val(val);
    }

    bool validate(PyObject* obj) const noexcept override {
        if (!obj || !PyDict_Check(obj)) return false;
        Py_ssize_t size = PyDict_GET_SIZE(obj);
        if (size == 0) return true;

        switch (strategy) {
            case SampleStrategy::FIRST:
            case SampleStrategy::LAST: {
                Py_ssize_t pos = 0;
                PyObject* key;
                PyObject* value;
                if (!PyDict_Next(obj, &pos, &key, &value)) return true;
                return check_pair(key, value);
            }
            case SampleStrategy::BOOKEND: {
                Py_ssize_t pos = 0;
                PyObject* key;
                PyObject* value;
                if (!PyDict_Next(obj, &pos, &key, &value)) return true;
                if (!check_pair(key, value)) return false;
                if (PyDict_Next(obj, &pos, &key, &value)) {
                    return check_pair(key, value);
                }
                return true;
            }
            case SampleStrategy::BOOKEND_PLUS: {
                Py_ssize_t pos = 0;
                PyObject* key;
                PyObject* value;
                if (!PyDict_Next(obj, &pos, &key, &value)) return true;
                if (!check_pair(key, value)) return false;
                if (size == 2) {
                    if (PyDict_Next(obj, &pos, &key, &value)) {
                        return check_pair(key, value);
                    }
                    return true;
                }
                if (size > 2) {
                    if (!PyDict_Next(obj, &pos, &key, &value)) return true;
                    if (!check_pair(key, value)) return false;
                    size_t remaining = static_cast<size_t>(size - 2);
                    size_t skip = fast_quasi_rand(remaining);
                    for (size_t s = 0; s < skip; ++s) {
                        if (!PyDict_Next(obj, &pos, &key, &value)) return true;
                    }
                    if (PyDict_Next(obj, &pos, &key, &value)) {
                        return check_pair(key, value);
                    }
                }
                return true;
            }
            case SampleStrategy::RANDOM_ONE: {
                Py_ssize_t pos = 0;
                PyObject* key;
                PyObject* value;
                size_t skip = fast_quasi_rand(static_cast<size_t>(size));
                for (size_t s = 0; s < skip; ++s) {
                    if (!PyDict_Next(obj, &pos, &key, &value)) return true;
                }
                if (PyDict_Next(obj, &pos, &key, &value)) {
                    return check_pair(key, value);
                }
                return true;
            }
            case SampleStrategy::LOG:
            case SampleStrategy::PERCENT:
            case SampleStrategy::COUNT: {
                size_t count = 1;
                if (strategy == SampleStrategy::LOG) {
                    count = calc_log_count(static_cast<size_t>(size));
                } else if (strategy == SampleStrategy::PERCENT) {
                    count = static_cast<size_t>((size * sample_pct_val + 99.0) / 100.0);
                } else {
                    count = static_cast<size_t>(sample_pct_val);
                }
                if (count < 1) count = 1;
                if (count >= static_cast<size_t>(size)) {
                    return validate_all(obj);
                }
                Py_ssize_t pos = 0;
                PyObject* key;
                PyObject* value;
                size_t checked = 0;
                while (PyDict_Next(obj, &pos, &key, &value)) {
                    if (!check_pair(key, value)) return false;
                    if (++checked >= count) break;
                }
                return true;
            }
            case SampleStrategy::ALL:
            default:
                return validate_all(obj);
        }
    }

    inline bool validate_all(PyObject* obj) const noexcept {
        Py_ssize_t pos = 0;
        PyObject* key;
        PyObject* value;
        if (single_k_type && single_v_type) {
            while (PyDict_Next(obj, &pos, &key, &value)) {
                if (__builtin_expect(Py_TYPE(key) != single_k_type, 0) && !PyObject_TypeCheck(key, single_k_type)) return false;
                if (__builtin_expect(Py_TYPE(value) != single_v_type, 0) && !PyObject_TypeCheck(value, single_v_type)) return false;
            }
            return true;
        }
        if (single_k_type && union_v_types && union_v_types->size() == 2) {
            PyTypeObject* vt0 = (*union_v_types)[0];
            PyTypeObject* vt1 = (*union_v_types)[1];
            while (PyDict_Next(obj, &pos, &key, &value)) {
                if (__builtin_expect(Py_TYPE(key) != single_k_type, 0) && !PyObject_TypeCheck(key, single_k_type)) return false;
                PyTypeObject* vt = Py_TYPE(value);
                if (__builtin_expect(vt != vt0 && vt != vt1, 0)) {
                    if (!PyObject_TypeCheck(value, vt0) && !PyObject_TypeCheck(value, vt1)) return false;
                }
            }
            return true;
        }
        while (PyDict_Next(obj, &pos, &key, &value)) {
            if (!check_pair(key, value)) return false;
        }
        return true;
    }
};

struct SetValidatorNode : public TypeValidatorNode {
    std::shared_ptr<TypeValidatorNode> elem_val;
    SampleStrategy strategy;
    double sample_pct_val;
    PyTypeObject* single_type;
    const std::vector<PyTypeObject*>* union_types;

    SetValidatorNode(std::shared_ptr<TypeValidatorNode> el, SampleStrategy strat, double val = 0.0)
        : TypeValidatorNode(NodeKind::SET), elem_val(std::move(el)), strategy(strat), sample_pct_val(val),
          single_type(nullptr), union_types(nullptr) {
        if (elem_val) {
            if (elem_val->kind == NodeKind::SUBCLASS_TYPE) {
                single_type = static_cast<SubclassTypeValidatorNode*>(elem_val.get())->expected_type;
            } else if (elem_val->kind == NodeKind::UNION_TYPE) {
                union_types = &static_cast<UnionTypeValidatorNode*>(elem_val.get())->types;
            }
        }
    }

    inline bool check_elem(PyObject* item) const noexcept {
        if (single_type) {
            PyTypeObject* t = Py_TYPE(item);
            if (__builtin_expect(t == single_type, 1)) return true;
            return PyObject_TypeCheck(item, single_type) != 0;
        }
        if (union_types) {
            PyTypeObject* t = Py_TYPE(item);
            for (auto* exp : *union_types) {
                if (t == exp) return true;
            }
            for (auto* exp : *union_types) {
                if (PyObject_TypeCheck(item, exp)) return true;
            }
            return false;
        }
        return elem_val->validate(item);
    }

    bool validate(PyObject* obj) const noexcept override {
        if (!obj || (!PySet_Check(obj) && !PyFrozenSet_Check(obj))) return false;
        Py_ssize_t size = PySet_GET_SIZE(obj);
        if (size == 0) return true;

        if (strategy == SampleStrategy::ALL) {
            PyObject* it = PyObject_GetIter(obj);
            if (!it) return false;
            PyObject* item;
            bool valid = true;
            if (single_type) {
                while ((item = PyIter_Next(it)) != NULL) {
                    if (__builtin_expect(Py_TYPE(item) != single_type, 0) && !PyObject_TypeCheck(item, single_type)) {
                        valid = false;
                        Py_DECREF(item);
                        break;
                    }
                    Py_DECREF(item);
                }
            } else if (union_types && union_types->size() == 2) {
                PyTypeObject* t0 = (*union_types)[0];
                PyTypeObject* t1 = (*union_types)[1];
                while ((item = PyIter_Next(it)) != NULL) {
                    PyTypeObject* t = Py_TYPE(item);
                    if (__builtin_expect(t != t0 && t != t1, 0)) {
                        if (!PyObject_TypeCheck(item, t0) && !PyObject_TypeCheck(item, t1)) {
                            valid = false;
                            Py_DECREF(item);
                            break;
                        }
                    }
                    Py_DECREF(item);
                }
            } else {
                while ((item = PyIter_Next(it)) != NULL) {
                    if (!check_elem(item)) {
                        valid = false;
                        Py_DECREF(item);
                        break;
                    }
                    Py_DECREF(item);
                }
            }
            Py_DECREF(it);
            return valid;
        }

        size_t count = 1;
        if (strategy == SampleStrategy::FIRST || strategy == SampleStrategy::LAST || strategy == SampleStrategy::RANDOM_ONE) {
            count = 1;
        } else if (strategy == SampleStrategy::BOOKEND) {
            count = 2;
        } else if (strategy == SampleStrategy::BOOKEND_PLUS) {
            count = 3;
        } else if (strategy == SampleStrategy::LOG) {
            count = calc_log_count(static_cast<size_t>(size));
        } else if (strategy == SampleStrategy::PERCENT) {
            count = static_cast<size_t>((size * sample_pct_val + 99.0) / 100.0);
        } else if (strategy == SampleStrategy::COUNT) {
            count = static_cast<size_t>(sample_pct_val);
        }
        if (count < 1) count = 1;

        PyObject* it = PyObject_GetIter(obj);
        if (!it) return false;
        PyObject* item;
        size_t checked = 0;
        bool valid = true;
        while ((item = PyIter_Next(it)) != NULL) {
            if (valid && !check_elem(item)) {
                valid = false;
            }
            Py_DECREF(item);
            if (!valid || ++checked >= count) break;
        }
        Py_DECREF(it);
        return valid;
    }
};

struct FixedTupleValidatorNode : public TypeValidatorNode {
    std::vector<std::shared_ptr<TypeValidatorNode>> elem_vals;
    std::vector<PyTypeObject*> single_types;
    bool all_single_types;

    explicit FixedTupleValidatorNode(std::vector<std::shared_ptr<TypeValidatorNode>> els)
        : TypeValidatorNode(NodeKind::FIXED_TUPLE), elem_vals(std::move(els)), all_single_types(true) {
        single_types.reserve(elem_vals.size());
        for (const auto& e : elem_vals) {
            if (e && e->kind == NodeKind::SUBCLASS_TYPE) {
                single_types.push_back(static_cast<SubclassTypeValidatorNode*>(e.get())->expected_type);
            } else {
                all_single_types = false;
            }
        }
    }

    bool validate(PyObject* obj) const noexcept override {
        if (!obj || !PyTuple_Check(obj)) return false;
        size_t count = elem_vals.size();
        if (static_cast<size_t>(PyTuple_GET_SIZE(obj)) != count) return false;
        if (count == 0) return true;
        PyObject* const* items = &PyTuple_GET_ITEM(obj, 0);
        if (all_single_types) {
            for (size_t i = 0; i < count; ++i) {
                PyTypeObject* exp = single_types[i];
                if (__builtin_expect(Py_TYPE(items[i]) != exp, 0) && !PyObject_TypeCheck(items[i], exp)) return false;
            }
            return true;
        }
        for (size_t i = 0; i < count; ++i) {
            if (!elem_vals[i]->validate(items[i])) return false;
        }
        return true;
    }
};

static std::pair<SampleStrategy, double> parse_strategy(nb::handle sample_pct) {
    if (sample_pct.is_none()) {
        return {SampleStrategy::ALL, 100.0};
    }
    PyObject* ptr = sample_pct.ptr();
    if (PyUnicode_Check(ptr)) {
        const char* s = PyUnicode_AsUTF8(ptr);
        if (s) {
            if (strcmp(s, "first") == 0) return {SampleStrategy::FIRST, 0.0};
            if (strcmp(s, "last") == 0) return {SampleStrategy::LAST, 0.0};
            if (strcmp(s, "bookend") == 0) return {SampleStrategy::BOOKEND, 0.0};
            if (strcmp(s, "bookend_plus") == 0) return {SampleStrategy::BOOKEND_PLUS, 0.0};
            if (strcmp(s, "log") == 0) return {SampleStrategy::LOG, 0.0};
        }
    }
    if (PyBool_Check(ptr)) {
        if (ptr == Py_True) return {SampleStrategy::ALL, 100.0};
        return {SampleStrategy::RANDOM_ONE, 0.0};
    }
    if (PyLong_Check(ptr)) {
        long val = PyLong_AsLong(ptr);
        if (val == 0) return {SampleStrategy::RANDOM_ONE, 0.0};
        if (val == 100) return {SampleStrategy::ALL, 100.0};
        return {SampleStrategy::PERCENT, static_cast<double>(val)};
    }
    if (PyFloat_Check(ptr)) {
        double val = PyFloat_AsDouble(ptr);
        if (val == 0.0) return {SampleStrategy::RANDOM_ONE, 0.0};
        if (val == 100.0) return {SampleStrategy::ALL, 100.0};
        return {SampleStrategy::PERCENT, val};
    }
    return {SampleStrategy::ALL, 100.0};
}

static inline bool is_plain_type(PyObject* obj) {
    if (!obj || !PyType_Check(obj)) return false;
    PyTypeObject* t = (PyTypeObject*)obj;
    const char* name = t->tp_name;
    if (name) {
        if (strcmp(name, "__SelfType__") == 0 ||
            strcmp(name, "__NeverType__") == 0) {
            return false;
        }
    }
    PyObject* dict = t->tp_dict;
    if (dict && PyDict_Check(dict)) {
        if (PyDict_GetItemString(dict, "__required_keys__") ||
            PyDict_GetItemString(dict, "__optional_keys__") ||
            PyDict_GetItemString(dict, "__total__") ||
            PyDict_GetItemString(dict, "__origin__")) {
            return false;
        }
    }
    return true;
}

static std::shared_ptr<TypeValidatorNode> build_node(nb::handle spec, SampleStrategy strategy, double sample_val) {
    if (spec.is_none()) {
        return nullptr;
    }

    PyObject* ptr = spec.ptr();
    if (is_plain_type(ptr)) {
        return std::make_shared<SubclassTypeValidatorNode>((PyTypeObject*)ptr);
    }

    if (PyList_Check(ptr)) {
        Py_ssize_t l_size = PyList_GET_SIZE(ptr);
        if (l_size == 0) return nullptr;
        std::vector<std::shared_ptr<TypeValidatorNode>> branches;
        branches.reserve(l_size);
        bool all_simple_types = true;
        std::vector<PyTypeObject*> simple_types;
        for (Py_ssize_t i = 0; i < l_size; ++i) {
            PyObject* item = PyList_GET_ITEM(ptr, i);
            auto sub = build_node(nb::handle(item), strategy, sample_val);
            if (!sub) return nullptr;
            if (sub->kind == NodeKind::SUBCLASS_TYPE) {
                simple_types.push_back(static_cast<SubclassTypeValidatorNode*>(sub.get())->expected_type);
            } else if (sub->kind == NodeKind::UNION_TYPE) {
                for (auto* t : static_cast<UnionTypeValidatorNode*>(sub.get())->types) {
                    simple_types.push_back(t);
                }
            } else {
                all_simple_types = false;
            }
            branches.push_back(std::move(sub));
        }
        if (branches.size() == 1) return branches[0];
        if (all_simple_types) {
            return std::make_shared<UnionTypeValidatorNode>(std::move(simple_types));
        }
        return std::make_shared<ComplexUnionValidatorNode>(std::move(branches));
    }

    if (PyDict_Check(ptr)) {
        if (PyDict_GetItemString(ptr, "__extra__") != nullptr) {
            return nullptr;
        }
        Py_ssize_t size = PyDict_GET_SIZE(ptr);
        if (size == 0) return nullptr;

        bool all_none = true;
        bool all_keys_are_types = true;
        Py_ssize_t pos = 0;
        PyObject *key, *value;
        while (PyDict_Next(ptr, &pos, &key, &value)) {
            if (value != Py_None) all_none = false;
            if (!is_plain_type(key)) all_keys_are_types = false;
        }

        if (all_none) {
            if (!all_keys_are_types) return nullptr;
            if (size == 1) {
                pos = 0;
                PyDict_Next(ptr, &pos, &key, &value);
                return std::make_shared<SubclassTypeValidatorNode>((PyTypeObject*)key);
            }
            std::vector<PyTypeObject*> types;
            types.reserve(size);
            pos = 0;
            while (PyDict_Next(ptr, &pos, &key, &value)) {
                types.push_back((PyTypeObject*)key);
            }
            return std::make_shared<UnionTypeValidatorNode>(std::move(types));
        }

        if (size == 1) {
            pos = 0;
            PyDict_Next(ptr, &pos, &key, &value);

            auto build_variants = [&](PyObject* val, auto build_one) -> std::shared_ptr<TypeValidatorNode> {
                if (PyList_Check(val)) {
                    Py_ssize_t l_size = PyList_GET_SIZE(val);
                    if (l_size == 0) return nullptr;
                    std::vector<std::shared_ptr<TypeValidatorNode>> branches;
                    branches.reserve(l_size);
                    for (Py_ssize_t i = 0; i < l_size; ++i) {
                        auto sub = build_one(PyList_GET_ITEM(val, i));
                        if (!sub) return nullptr;
                        branches.push_back(std::move(sub));
                    }
                    if (branches.size() == 1) return branches[0];
                    return std::make_shared<ComplexUnionValidatorNode>(std::move(branches));
                }
                return build_one(val);
            };

            if (key == (PyObject*)&PyList_Type) {
                return build_variants(value, [&](PyObject* item) -> std::shared_ptr<TypeValidatorNode> {
                    auto elem = build_node(nb::handle(item), strategy, sample_val);
                    if (!elem) return nullptr;
                    return std::make_shared<ListValidatorNode>(std::move(elem), strategy, sample_val);
                });
            }
            if (key == (PyObject*)&PySet_Type) {
                return build_variants(value, [&](PyObject* item) -> std::shared_ptr<TypeValidatorNode> {
                    auto elem = build_node(nb::handle(item), strategy, sample_val);
                    if (!elem) return nullptr;
                    return std::make_shared<SetValidatorNode>(std::move(elem), strategy, sample_val);
                });
            }
            if (key == (PyObject*)&PyDict_Type) {
                return build_variants(value, [&](PyObject* d_spec) -> std::shared_ptr<TypeValidatorNode> {
                    if (!PyTuple_Check(d_spec) || PyTuple_GET_SIZE(d_spec) != 2) return nullptr;
                    PyObject* k_spec = PyTuple_GET_ITEM(d_spec, 0);
                    PyObject* v_spec = PyTuple_GET_ITEM(d_spec, 1);
                    auto k_node = build_node(nb::handle(k_spec), strategy, sample_val);
                    auto v_node = build_node(nb::handle(v_spec), strategy, sample_val);
                    if (!k_node || !v_node) return nullptr;
                    return std::make_shared<DictValidatorNode>(std::move(k_node), std::move(v_node), strategy, sample_val);
                });
            }
            if (key == (PyObject*)&PyTuple_Type) {
                return build_variants(value, [&](PyObject* tup_spec) -> std::shared_ptr<TypeValidatorNode> {
                    if (PyTuple_Check(tup_spec) && PyTuple_GET_SIZE(tup_spec) == 2) {
                        PyObject* t_spec = PyTuple_GET_ITEM(tup_spec, 0);
                        PyObject* is_var = PyTuple_GET_ITEM(tup_spec, 1);
                        if (is_var == Py_True) {
                            auto elem = build_node(nb::handle(t_spec), strategy, sample_val);
                            if (!elem) return nullptr;
                            return std::make_shared<VariableTupleValidatorNode>(std::move(elem), strategy, sample_val);
                        } else if (is_var == Py_False && PyTuple_Check(t_spec)) {
                            Py_ssize_t t_size = PyTuple_GET_SIZE(t_spec);
                            std::vector<std::shared_ptr<TypeValidatorNode>> elem_nodes;
                            elem_nodes.reserve(t_size);
                            for (Py_ssize_t j = 0; j < t_size; ++j) {
                                auto sub = build_node(nb::handle(PyTuple_GET_ITEM(t_spec, j)), strategy, sample_val);
                                if (!sub) return nullptr;
                                elem_nodes.push_back(std::move(sub));
                            }
                            return std::make_shared<FixedTupleValidatorNode>(std::move(elem_nodes));
                        }
                    } else if (PyTuple_Check(tup_spec)) {
                        Py_ssize_t t_size = PyTuple_GET_SIZE(tup_spec);
                        std::vector<std::shared_ptr<TypeValidatorNode>> elem_nodes;
                        elem_nodes.reserve(t_size);
                        for (Py_ssize_t j = 0; j < t_size; ++j) {
                            auto sub = build_node(nb::handle(PyTuple_GET_ITEM(tup_spec, j)), strategy, sample_val);
                            if (!sub) return nullptr;
                            elem_nodes.push_back(std::move(sub));
                        }
                        return std::make_shared<FixedTupleValidatorNode>(std::move(elem_nodes));
                    }
                    return nullptr;
                });
            }
            return nullptr;
        }

        bool all_subclass = true;
        std::vector<PyTypeObject*> plain_types;
        plain_types.reserve(size);
        pos = 0;
        while (PyDict_Next(ptr, &pos, &key, &value)) {
            if (value == Py_None && is_plain_type(key)) {
                plain_types.push_back((PyTypeObject*)key);
            } else {
                all_subclass = false;
                break;
            }
        }
        if (all_subclass) {
            if (plain_types.size() == 1) {
                return std::make_shared<SubclassTypeValidatorNode>(plain_types[0]);
            }
            return std::make_shared<UnionTypeValidatorNode>(std::move(plain_types));
        }

        std::vector<std::shared_ptr<TypeValidatorNode>> branches;
        branches.reserve(size);
        pos = 0;
        while (PyDict_Next(ptr, &pos, &key, &value)) {
            if (value == Py_None) {
                if (!is_plain_type(key)) return nullptr;
                branches.push_back(std::make_shared<SubclassTypeValidatorNode>((PyTypeObject*)key));
            } else {
                if (key != (PyObject*)&PyList_Type &&
                    key != (PyObject*)&PySet_Type &&
                    key != (PyObject*)&PyDict_Type &&
                    key != (PyObject*)&PyTuple_Type) {
                    return nullptr;
                }
                nb::dict sub_dict;
                sub_dict[nb::handle(key)] = nb::handle(value);
                auto sub_node = build_node(sub_dict, strategy, sample_val);
                if (!sub_node) return nullptr;
                branches.push_back(std::move(sub_node));
            }
        }
        if (branches.size() == 1) return branches[0];
        return std::make_shared<ComplexUnionValidatorNode>(std::move(branches));
    }

    if (PyTuple_Check(ptr)) {
        Py_ssize_t t_size = PyTuple_GET_SIZE(ptr);
        std::vector<std::shared_ptr<TypeValidatorNode>> elem_nodes;
        elem_nodes.reserve(t_size);
        for (Py_ssize_t i = 0; i < t_size; ++i) {
            auto sub = build_node(nb::handle(PyTuple_GET_ITEM(ptr, i)), strategy, sample_val);
            if (!sub) return nullptr;
            elem_nodes.push_back(std::move(sub));
        }
        return std::make_shared<FixedTupleValidatorNode>(std::move(elem_nodes));
    }

    return nullptr;
}

struct PyValidatorObject {
    PyObject_HEAD
    std::shared_ptr<TypeValidatorNode> root;
    vectorcallfunc vectorcall;
};

static PyObject* validator_vectorcall(PyObject* self, PyObject* const* args, size_t nargsf, PyObject* kwnames) {
    Py_ssize_t nargs = PyVectorcall_NARGS(nargsf);
    if (__builtin_expect(nargs != 1 || kwnames != nullptr, 0)) {
        PyErr_SetString(PyExc_TypeError, "validator takes exactly 1 positional argument");
        return nullptr;
    }
    PyValidatorObject* v = (PyValidatorObject*)self;
    if (__builtin_expect(v->root && v->root->validate(args[0]), 1)) {
        Py_RETURN_TRUE;
    } else {
        Py_RETURN_FALSE;
    }
}

static PyObject* validator_tp_call(PyObject* self, PyObject* args, PyObject* kwargs) {
    if (kwargs != nullptr && PyDict_Size(kwargs) != 0) {
        PyErr_SetString(PyExc_TypeError, "validator takes no keyword arguments");
        return nullptr;
    }
    if (PyTuple_GET_SIZE(args) != 1) {
        PyErr_SetString(PyExc_TypeError, "validator takes exactly 1 positional argument");
        return nullptr;
    }
    PyValidatorObject* v = (PyValidatorObject*)self;
    if (__builtin_expect(v->root && v->root->validate(PyTuple_GET_ITEM(args, 0)), 1)) {
        Py_RETURN_TRUE;
    } else {
        Py_RETURN_FALSE;
    }
}

static void validator_dealloc(PyObject* self) {
    PyValidatorObject* v = (PyValidatorObject*)self;
    v->root.~shared_ptr();
    Py_TYPE(self)->tp_free(self);
}

static PyMethodDef validator_methods[] = {
    {"validate", (PyCFunction)validator_tp_call, METH_VARARGS | METH_KEYWORDS, "Validate object"},
    {nullptr, nullptr, 0, nullptr}
};

static PyType_Slot validator_slots[] = {
    {Py_tp_call, (void*)validator_tp_call},
    {Py_tp_dealloc, (void*)validator_dealloc},
    {Py_tp_methods, (void*)validator_methods},
    {0, nullptr}
};

static PyType_Spec validator_type_spec = {
    "type_enforced.cpp.Validator",
    sizeof(PyValidatorObject),
    0,
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_VECTORCALL,
    validator_slots
};

static PyTypeObject* PyValidator_Type = nullptr;

void init_validator_type(PyObject* m) {
    if (!PyValidator_Type) {
        PyValidator_Type = (PyTypeObject*)PyType_FromSpec(&validator_type_spec);
        if (PyValidator_Type) {
            PyValidator_Type->tp_vectorcall_offset = offsetof(PyValidatorObject, vectorcall);
            Py_INCREF(PyValidator_Type);
            PyModule_AddObject(m, "Validator", (PyObject*)PyValidator_Type);
        }
    }
}

nb::object create_validator(nb::handle spec, nb::handle sample_pct) {
    auto [strategy, val] = parse_strategy(sample_pct);
    auto node = build_node(spec, strategy, val);
    if (!node) return nb::none();

    if (PyValidator_Type) {
        PyValidatorObject* obj = PyObject_New(PyValidatorObject, PyValidator_Type);
        if (!obj) return nb::none();
        new (&obj->root) std::shared_ptr<TypeValidatorNode>(std::move(node));
        obj->vectorcall = validator_vectorcall;
        return nb::steal(reinterpret_cast<PyObject*>(obj));
    }
    return nb::none();
}

// ----------------- FAST CALL DISPATCHER -----------------

struct FastParamInfo {
    std::shared_ptr<TypeValidatorNode> validator;
    PyTypeObject* single_type;
    const std::vector<PyTypeObject*>* union_types;
    PyObject* exp;
    PyObject* name_str;
    std::string name;
};

struct PyFastCallObject {
    PyObject_HEAD
    vectorcallfunc vectorcall;
    PyObject* self_enforcer;
    PyObject* fn;
    PyObject* check_fn;
    std::vector<FastParamInfo> pos_params;
    std::unordered_map<std::string, size_t> kw_to_param_idx;
    std::shared_ptr<TypeValidatorNode> ret_validator;
    PyTypeObject* ret_single_type;
    const std::vector<PyTypeObject*>* ret_union_types;
    PyObject* ret_exp;
    PyObject* ret_str;
    bool has_return;
    bool ret_is_none;
};

static inline bool check_arg_fast(PyObject* arg, const FastParamInfo& p) noexcept {
    if (p.single_type) {
        PyTypeObject* t = Py_TYPE(arg);
        if (__builtin_expect(t == p.single_type, 1)) return true;
        return p.validator->validate(arg);
    }
    if (p.union_types) {
        PyTypeObject* t = Py_TYPE(arg);
        for (auto* exp : *p.union_types) {
            if (__builtin_expect(t == exp, 1)) return true;
        }
        for (auto* exp : *p.union_types) {
            if (PyObject_TypeCheck(arg, exp)) return true;
        }
        return false;
    }
    if (p.validator) {
        return p.validator->validate(arg);
    }
    return true;
}

static inline bool check_ret_fast(PyObject* res, const PyFastCallObject* fc) noexcept {
    if (fc->ret_is_none) {
        return __builtin_expect(res == Py_None, 1);
    }
    if (fc->ret_single_type) {
        PyTypeObject* t = Py_TYPE(res);
        if (__builtin_expect(t == fc->ret_single_type, 1)) return true;
        return fc->ret_validator->validate(res);
    }
    if (fc->ret_union_types) {
        PyTypeObject* t = Py_TYPE(res);
        for (auto* exp : *fc->ret_union_types) {
            if (__builtin_expect(t == exp, 1)) return true;
        }
        for (auto* exp : *fc->ret_union_types) {
            if (PyObject_TypeCheck(res, exp)) return true;
        }
        return false;
    }
    if (fc->ret_validator) {
        return fc->ret_validator->validate(res);
    }
    return true;
}

static PyObject* fast_call_vectorcall(PyObject* self, PyObject* const* args, size_t nargsf, PyObject* kwnames) {
    PyFastCallObject* fc = (PyFastCallObject*)self;
    PyObject* self_enforcer = fc->self_enforcer;
    size_t fn_nargs = PyVectorcall_NARGS(nargsf);
    PyObject* const* fn_args = args;
    size_t num_pos = fc->pos_params.size();

    // Fast-path: single positional argument and no kwargs
    if (__builtin_expect(kwnames == nullptr && fn_nargs == 1 && num_pos == 1, 1)) {
        const auto& p0 = fc->pos_params[0];
        if (__builtin_expect(!check_arg_fast(fn_args[0], p0), 0)) {
            PyObject* check_args[4] = {self_enforcer, fn_args[0], p0.exp, p0.name_str};
            PyObject* check_res = _PyObject_Vectorcall(fc->check_fn, check_args, 4, nullptr);
            if (!check_res) return nullptr;
            Py_DECREF(check_res);
        }
        PyObject* res = _PyObject_Vectorcall(fc->fn, fn_args, nargsf, nullptr);
        if (__builtin_expect(!res, 0)) return nullptr;
        if (fc->has_return) {
            if (__builtin_expect(!check_ret_fast(res, fc), 0)) {
                PyObject* check_args[4] = {self_enforcer, res, fc->ret_exp, fc->ret_str};
                PyObject* check_res = _PyObject_Vectorcall(fc->check_fn, check_args, 4, nullptr);
                if (!check_res) {
                    Py_DECREF(res);
                    return nullptr;
                }
                Py_DECREF(check_res);
            }
        }
        return res;
    }

    size_t check_pos_count = (fn_nargs < num_pos) ? fn_nargs : num_pos;
    for (size_t i = 0; i < check_pos_count; ++i) {
        const auto& p = fc->pos_params[i];
        if (__builtin_expect(!check_arg_fast(fn_args[i], p), 0)) {
            PyObject* check_args[4] = {self_enforcer, fn_args[i], p.exp, p.name_str};
            PyObject* check_res = _PyObject_Vectorcall(fc->check_fn, check_args, 4, nullptr);
            if (!check_res) return nullptr;
            Py_DECREF(check_res);
        }
    }

    if (__builtin_expect(kwnames != nullptr, 0)) {
        size_t n_kwargs = PyTuple_GET_SIZE(kwnames);
        PyObject* const* kw_values = fn_args + fn_nargs;
        for (size_t j = 0; j < n_kwargs; ++j) {
            PyObject* key_obj = PyTuple_GET_ITEM(kwnames, j);
            const char* key_cstr = PyUnicode_AsUTF8(key_obj);
            if (key_cstr) {
                auto it = fc->kw_to_param_idx.find(key_cstr);
                if (it != fc->kw_to_param_idx.end()) {
                    const auto& p = fc->pos_params[it->second];
                    if (__builtin_expect(!check_arg_fast(kw_values[j], p), 0)) {
                        PyObject* check_args[4] = {self_enforcer, kw_values[j], p.exp, p.name_str};
                        PyObject* check_res = _PyObject_Vectorcall(fc->check_fn, check_args, 4, nullptr);
                        if (!check_res) return nullptr;
                        Py_DECREF(check_res);
                    }
                }
            }
        }
    }

    PyObject* res = _PyObject_Vectorcall(fc->fn, fn_args, nargsf, kwnames);
    if (__builtin_expect(!res, 0)) return nullptr;

    if (fc->has_return) {
        if (__builtin_expect(!check_ret_fast(res, fc), 0)) {
            PyObject* check_args[4] = {self_enforcer, res, fc->ret_exp, fc->ret_str};
            PyObject* check_res = _PyObject_Vectorcall(fc->check_fn, check_args, 4, nullptr);
            if (!check_res) {
                Py_DECREF(res);
                return nullptr;
            }
            Py_DECREF(check_res);
        }
    }
    return res;
}

static PyObject* fast_call_tp_call(PyObject* self, PyObject* args, PyObject* kwargs) {
    size_t nargs = PyTuple_GET_SIZE(args);
    PyObject* const* fastargs = nargs > 0 ? &PyTuple_GET_ITEM(args, 0) : nullptr;
    if (kwargs && PyDict_Size(kwargs) > 0) {
        size_t n_kwargs = PyDict_Size(kwargs);
        PyObject* kwnames = PyTuple_New(n_kwargs);
        std::vector<PyObject*> stack(nargs + n_kwargs);
        for (size_t i = 0; i < nargs; ++i) {
            stack[i] = PyTuple_GET_ITEM(args, i);
        }
        PyObject *key, *value;
        Py_ssize_t pos = 0, idx = 0;
        while (PyDict_Next(kwargs, &pos, &key, &value)) {
            Py_INCREF(key);
            PyTuple_SET_ITEM(kwnames, idx, key);
            stack[nargs + idx] = value;
            idx++;
        }
        PyObject* res = fast_call_vectorcall(self, stack.data(), nargs, kwnames);
        Py_DECREF(kwnames);
        return res;
    }
    return fast_call_vectorcall(self, fastargs, nargs, nullptr);
}

static void fast_call_dealloc(PyObject* self) {
    PyFastCallObject* fc = (PyFastCallObject*)self;
    Py_XDECREF(fc->self_enforcer);
    Py_XDECREF(fc->fn);
    Py_XDECREF(fc->check_fn);
    for (auto& p : fc->pos_params) {
        Py_XDECREF(p.exp);
        Py_XDECREF(p.name_str);
    }
    fc->pos_params.~vector();
    fc->kw_to_param_idx.~unordered_map();
    fc->ret_validator.~shared_ptr();
    Py_XDECREF(fc->ret_exp);
    Py_XDECREF(fc->ret_str);
    Py_TYPE(self)->tp_free(self);
}

static PyType_Slot fast_call_slots[] = {
    {Py_tp_call, (void*)fast_call_tp_call},
    {Py_tp_dealloc, (void*)fast_call_dealloc},
    {0, nullptr}
};

static PyType_Spec fast_call_type_spec = {
    "type_enforced.cpp.FastCall",
    sizeof(PyFastCallObject),
    0,
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_VECTORCALL,
    fast_call_slots
};

static PyTypeObject* PyFastCall_Type = nullptr;

void init_fast_call_type(PyObject* m) {
    if (!PyFastCall_Type) {
        PyFastCall_Type = (PyTypeObject*)PyType_FromSpec(&fast_call_type_spec);
        if (PyFastCall_Type) {
            PyFastCall_Type->tp_vectorcall_offset = offsetof(PyFastCallObject, vectorcall);
            Py_INCREF(PyFastCall_Type);
            PyModule_AddObject(m, "FastCall", (PyObject*)PyFastCall_Type);
        }
    }
}

nb::object create_fast_call(
    nb::handle self_enforcer,
    nb::handle fn,
    nb::handle param_names,
    nb::handle param_specs,
    nb::handle param_exps,
    nb::handle ret_spec,
    nb::handle ret_exp,
    nb::handle check_fn,
    nb::handle sample_pct
) {
    if (!PyFastCall_Type) return nb::none();

    auto [strategy, val] = parse_strategy(sample_pct);

    PyFastCallObject* obj = PyObject_New(PyFastCallObject, PyFastCall_Type);
    if (!obj) return nb::none();

    obj->self_enforcer = nullptr;
    obj->fn = nullptr;
    obj->check_fn = nullptr;
    obj->ret_exp = nullptr;
    obj->ret_str = nullptr;
    obj->has_return = false;
    obj->ret_is_none = false;
    obj->ret_single_type = nullptr;
    obj->ret_union_types = nullptr;

    new (&obj->pos_params) std::vector<FastParamInfo>();
    new (&obj->kw_to_param_idx) std::unordered_map<std::string, size_t>();
    new (&obj->ret_validator) std::shared_ptr<TypeValidatorNode>(nullptr);

    obj->vectorcall = fast_call_vectorcall;
    obj->self_enforcer = self_enforcer.ptr();
    Py_INCREF(obj->self_enforcer);
    obj->fn = fn.ptr();
    Py_INCREF(obj->fn);
    obj->check_fn = check_fn.ptr();
    Py_INCREF(obj->check_fn);

    if (param_names.is_valid() && !param_names.is_none()) {
        auto names_seq = nb::borrow<nb::sequence>(param_names);
        auto specs_seq = nb::borrow<nb::sequence>(param_specs);
        auto exps_seq = nb::borrow<nb::sequence>(param_exps);
        size_t n = nb::len(names_seq);
        for (size_t i = 0; i < n; ++i) {
            FastParamInfo p;
            p.validator = nullptr;
            p.single_type = nullptr;
            p.union_types = nullptr;
            p.exp = nullptr;
            p.name_str = nullptr;

            auto name_handle = names_seq[i];
            p.name_str = name_handle.ptr();
            Py_INCREF(p.name_str);
            const char* name_cstr = PyUnicode_AsUTF8(p.name_str);
            if (name_cstr) {
                p.name = name_cstr;
                obj->kw_to_param_idx[p.name] = i;
            }

            auto spec_handle = specs_seq[i];
            if (spec_handle.is_valid() && !spec_handle.is_none()) {
                p.validator = build_node(spec_handle, strategy, val);
                if (!p.validator) {
                    Py_DECREF((PyObject*)obj);
                    return nb::none();
                }
                if (p.validator->kind == NodeKind::SUBCLASS_TYPE) {
                    p.single_type = static_cast<SubclassTypeValidatorNode*>(p.validator.get())->expected_type;
                } else if (p.validator->kind == NodeKind::UNION_TYPE) {
                    p.union_types = &static_cast<UnionTypeValidatorNode*>(p.validator.get())->types;
                }
            }
            auto exp_handle = exps_seq[i];
            if (exp_handle.is_valid() && !exp_handle.is_none()) {
                p.exp = exp_handle.ptr();
                Py_INCREF(p.exp);
            }

            obj->pos_params.push_back(std::move(p));
        }
    }

    if (ret_spec.is_valid() && !ret_spec.is_none()) {
        obj->has_return = true;
        obj->ret_str = PyUnicode_FromString("return");
        auto exp_handle = ret_exp;
        if (exp_handle.is_valid() && !exp_handle.is_none()) {
            obj->ret_exp = exp_handle.ptr();
            Py_INCREF(obj->ret_exp);
        }

        if (nb::isinstance<nb::dict>(ret_spec) && nb::len(ret_spec) == 1) {
            auto ret_dict = nb::borrow<nb::dict>(ret_spec);
            for (auto item : ret_dict) {
                if (item.first.ptr() == (PyObject*)Py_TYPE(Py_None) && item.second.is_none()) {
                    obj->ret_is_none = true;
                }
            }
        }
        if (!obj->ret_is_none) {
            obj->ret_validator = build_node(ret_spec, strategy, val);
            if (!obj->ret_validator) {
                Py_DECREF((PyObject*)obj);
                return nb::none();
            }
            if (obj->ret_validator->kind == NodeKind::SUBCLASS_TYPE) {
                obj->ret_single_type = static_cast<SubclassTypeValidatorNode*>(obj->ret_validator.get())->expected_type;
            } else if (obj->ret_validator->kind == NodeKind::UNION_TYPE) {
                obj->ret_union_types = &static_cast<UnionTypeValidatorNode*>(obj->ret_validator.get())->types;
            }
        }
    }

    return nb::steal(reinterpret_cast<PyObject*>(obj));
}

} // namespace type_enforced
