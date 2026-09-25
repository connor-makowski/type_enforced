#include "validators.hpp"
#include <vector>
#include <unordered_map>
#include <string>
#include <cstdlib>

namespace type_enforced {

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

static inline size_t compute_sample_count(size_t size, SampleStrategy strategy, double sample_pct_val) noexcept {
    if (size == 0) return 0;
    switch (strategy) {
        case SampleStrategy::FIRST:
        case SampleStrategy::LAST:
        case SampleStrategy::RANDOM_ONE:
            return 1;
        case SampleStrategy::BOOKEND:
            return (size > 1) ? 2 : 1;
        case SampleStrategy::BOOKEND_PLUS:
            return (size > 2) ? 3 : size;
        case SampleStrategy::LOG: {
            size_t c = calc_log_count(size);
            return c < 1 ? 1 : (c > size ? size : c);
        }
        case SampleStrategy::PERCENT: {
            size_t c = static_cast<size_t>((size * sample_pct_val + 99.0) / 100.0);
            return c < 1 ? 1 : (c > size ? size : c);
        }
        case SampleStrategy::COUNT: {
            size_t c = static_cast<size_t>(sample_pct_val);
            return c < 1 ? 1 : (c > size ? size : c);
        }
        case SampleStrategy::ALL:
        default:
            return size;
    }
}

// ----------------- FAST TYPE CHECKING PRIMITIVES -----------------

static inline bool check_single_type(PyObject* obj, PyTypeObject* expected) noexcept {
    if (__builtin_expect(!obj, 0)) return false;
    PyTypeObject* t = Py_TYPE(obj);
    if (__builtin_expect(t == expected, 1)) return true;
    return PyObject_TypeCheck(obj, expected) != 0;
}

static inline bool check_union2(PyObject* obj, PyTypeObject* t0, PyTypeObject* t1) noexcept {
    if (__builtin_expect(!obj, 0)) return false;
    uintptr_t t = (uintptr_t)Py_TYPE(obj);
    if (__builtin_expect((t == (uintptr_t)t0) | (t == (uintptr_t)t1), 1)) return true;
    return PyObject_TypeCheck(obj, t0) != 0 || PyObject_TypeCheck(obj, t1) != 0;
}

static inline bool check_union3(PyObject* obj, PyTypeObject* t0, PyTypeObject* t1, PyTypeObject* t2) noexcept {
    if (__builtin_expect(!obj, 0)) return false;
    uintptr_t t = (uintptr_t)Py_TYPE(obj);
    if (__builtin_expect((t == (uintptr_t)t0) | (t == (uintptr_t)t1) | (t == (uintptr_t)t2), 1)) return true;
    return PyObject_TypeCheck(obj, t0) != 0 || PyObject_TypeCheck(obj, t1) != 0 || PyObject_TypeCheck(obj, t2) != 0;
}

static inline bool check_items_single_all(PyObject* const* items, Py_ssize_t size, PyTypeObject* elem_type) noexcept {
    Py_ssize_t i = 0;
    for (; i + 3 < size; i += 4) {
        uintptr_t d = ((uintptr_t)Py_TYPE(items[i]) ^ (uintptr_t)elem_type)
                    | ((uintptr_t)Py_TYPE(items[i + 1]) ^ (uintptr_t)elem_type)
                    | ((uintptr_t)Py_TYPE(items[i + 2]) ^ (uintptr_t)elem_type)
                    | ((uintptr_t)Py_TYPE(items[i + 3]) ^ (uintptr_t)elem_type);
        if (__builtin_expect(d != 0, 0)) {
            for (Py_ssize_t k = i; k < i + 4; ++k) {
                if (Py_TYPE(items[k]) != elem_type && !PyObject_TypeCheck(items[k], elem_type)) return false;
            }
        }
    }
    for (; i < size; ++i) {
        if (__builtin_expect(Py_TYPE(items[i]) != elem_type, 0) && !PyObject_TypeCheck(items[i], elem_type)) return false;
    }
    return true;
}

static inline bool check_items_union2_all(PyObject* const* items, Py_ssize_t size, PyTypeObject* t0, PyTypeObject* t1) noexcept {
    Py_ssize_t i = 0;
    for (; i + 3 < size; i += 4) {
        PyTypeObject* it0 = Py_TYPE(items[i]);
        PyTypeObject* it1 = Py_TYPE(items[i + 1]);
        PyTypeObject* it2 = Py_TYPE(items[i + 2]);
        PyTypeObject* it3 = Py_TYPE(items[i + 3]);
        uintptr_t mismatch = ((it0 != t0 && it0 != t1) ? 1 : 0)
                           | ((it1 != t0 && it1 != t1) ? 1 : 0)
                           | ((it2 != t0 && it2 != t1) ? 1 : 0)
                           | ((it3 != t0 && it3 != t1) ? 1 : 0);
        if (__builtin_expect(mismatch != 0, 0)) {
            for (Py_ssize_t k = i; k < i + 4; ++k) {
                PyTypeObject* itk = Py_TYPE(items[k]);
                if (itk != t0 && itk != t1 && !PyObject_TypeCheck(items[k], t0) && !PyObject_TypeCheck(items[k], t1)) return false;
            }
        }
    }
    for (; i < size; ++i) {
        PyTypeObject* it = Py_TYPE(items[i]);
        if (__builtin_expect(it != t0 && it != t1, 0) && !PyObject_TypeCheck(items[i], t0) && !PyObject_TypeCheck(items[i], t1)) return false;
    }
    return true;
}

template <bool IsList>
static inline bool check_sequence_single_all(PyObject* obj, PyTypeObject* elem_type) noexcept {
    if constexpr (IsList) {
        if (__builtin_expect(!obj || !PyList_Check(obj), 0)) return false;
        Py_ssize_t size = PyList_GET_SIZE(obj);
        if (__builtin_expect(size == 0, 0)) return true;
        PyObject* const* items = PySequence_Fast_ITEMS(obj);
        return check_items_single_all(items, size, elem_type);
    } else {
        if (__builtin_expect(!obj || !PyTuple_Check(obj), 0)) return false;
        Py_ssize_t size = PyTuple_GET_SIZE(obj);
        if (__builtin_expect(size == 0, 0)) return true;
        PyObject* const* items = &PyTuple_GET_ITEM(obj, 0);
        return check_items_single_all(items, size, elem_type);
    }
}

static inline bool check_list_single_all(PyObject* obj, PyTypeObject* elem_type) noexcept {
    return check_sequence_single_all<true>(obj, elem_type);
}

static inline bool check_tuple_single_all(PyObject* obj, PyTypeObject* elem_type) noexcept {
    return check_sequence_single_all<false>(obj, elem_type);
}

static inline bool check_list_union2_all(PyObject* obj, PyTypeObject* t0, PyTypeObject* t1) noexcept {
    if (__builtin_expect(!obj || !PyList_Check(obj), 0)) return false;
    Py_ssize_t size = PyList_GET_SIZE(obj);
    if (__builtin_expect(size == 0, 0)) return true;
    PyObject* const* items = PySequence_Fast_ITEMS(obj);
    return check_items_union2_all(items, size, t0, t1);
}

static inline bool check_fixed_tuple2(PyObject* obj, PyTypeObject* t0, PyTypeObject* t1) noexcept {
    if (__builtin_expect(!obj || !PyTuple_Check(obj) || PyTuple_GET_SIZE(obj) != 2, 0)) return false;
    PyObject* const* items = &PyTuple_GET_ITEM(obj, 0);
    if (__builtin_expect(Py_TYPE(items[0]) != t0, 0) && !PyObject_TypeCheck(items[0], t0)) return false;
    if (__builtin_expect(Py_TYPE(items[1]) != t1, 0) && !PyObject_TypeCheck(items[1], t1)) return false;
    return true;
}

static inline bool check_fixed_tuple3(PyObject* obj, PyTypeObject* t0, PyTypeObject* t1, PyTypeObject* t2) noexcept {
    if (__builtin_expect(!obj || !PyTuple_Check(obj) || PyTuple_GET_SIZE(obj) != 3, 0)) return false;
    PyObject* const* items = &PyTuple_GET_ITEM(obj, 0);
    if (__builtin_expect(Py_TYPE(items[0]) != t0, 0) && !PyObject_TypeCheck(items[0], t0)) return false;
    if (__builtin_expect(Py_TYPE(items[1]) != t1, 0) && !PyObject_TypeCheck(items[1], t1)) return false;
    if (__builtin_expect(Py_TYPE(items[2]) != t2, 0) && !PyObject_TypeCheck(items[2], t2)) return false;
    return true;
}

static inline bool check_dict_single_all(PyObject* obj, PyTypeObject* kt, PyTypeObject* vt) noexcept {
    if (__builtin_expect(!obj || !PyDict_Check(obj), 0)) return false;
    Py_ssize_t size = PyDict_GET_SIZE(obj);
    if (__builtin_expect(size == 0, 0)) return true;
    Py_ssize_t pos = 0;
    PyObject *k, *v;
    while (PyDict_Next(obj, &pos, &k, &v)) {
        if (__builtin_expect(Py_TYPE(k) != kt, 0) && !PyObject_TypeCheck(k, kt)) return false;
        if (__builtin_expect(Py_TYPE(v) != vt, 0) && !PyObject_TypeCheck(v, vt)) return false;
    }
    return true;
}

static inline bool check_set_single_all(PyObject* obj, PyTypeObject* elem_type) noexcept {
    if (__builtin_expect(!obj || (!PySet_Check(obj) && !PyFrozenSet_Check(obj)), 0)) return false;
    Py_ssize_t size = PySet_GET_SIZE(obj);
    if (__builtin_expect(size == 0, 0)) return true;
    PySetObject* so = (PySetObject*)obj;
    setentry* table = so->table;
    Py_ssize_t mask = so->mask;
    Py_ssize_t found = 0;
    for (Py_ssize_t i = 0; i <= mask && found < size; ++i) {
        PyObject* item = table[i].key;
        if (item && table[i].hash != -1) {
            found++;
            if (__builtin_expect(Py_TYPE(item) != elem_type, 0) && !PyObject_TypeCheck(item, elem_type)) return false;
        }
    }
    return true;
}

enum class ParamCheckKind : uint8_t {
    PASS = 0,
    SINGLE_TYPE = 1,
    UNION2 = 2,
    UNION3 = 3,
    LIST_SINGLE_ALL = 4,
    LIST_UNION2_ALL = 5,
    VAR_TUPLE_SINGLE_ALL = 6,
    FIXED_TUPLE2 = 7,
    FIXED_TUPLE3 = 8,
    DICT_SINGLE_ALL = 9,
    SET_SINGLE_ALL = 10,
    NODE = 11
};

static inline bool validate_param(
    PyObject* obj,
    ParamCheckKind kind,
    PyTypeObject* t0,
    PyTypeObject* t1,
    PyTypeObject* t2,
    TypeValidatorNode* node
) noexcept {
    switch (kind) {
        case ParamCheckKind::PASS:
            return true;
        case ParamCheckKind::SINGLE_TYPE:
            return check_single_type(obj, t0);
        case ParamCheckKind::UNION2:
            return check_union2(obj, t0, t1);
        case ParamCheckKind::UNION3:
            return check_union3(obj, t0, t1, t2);
        case ParamCheckKind::LIST_SINGLE_ALL:
            return check_list_single_all(obj, t0);
        case ParamCheckKind::LIST_UNION2_ALL:
            return check_list_union2_all(obj, t0, t1);
        case ParamCheckKind::VAR_TUPLE_SINGLE_ALL:
            return check_tuple_single_all(obj, t0);
        case ParamCheckKind::FIXED_TUPLE2:
            return check_fixed_tuple2(obj, t0, t1);
        case ParamCheckKind::FIXED_TUPLE3:
            return check_fixed_tuple3(obj, t0, t1, t2);
        case ParamCheckKind::DICT_SINGLE_ALL:
            return check_dict_single_all(obj, t0, t1);
        case ParamCheckKind::SET_SINGLE_ALL:
            return check_set_single_all(obj, t0);
        case ParamCheckKind::NODE:
            return node != nullptr ? node->validate(obj) : true;
        default:
            return true;
    }
}

// ----------------- GENERIC VALIDATOR ENGINE -----------------

struct SubclassTypeValidatorNode : public TypeValidatorNode {
    PyTypeObject* expected_type;
    explicit SubclassTypeValidatorNode(PyTypeObject* t)
        : TypeValidatorNode(NodeKind::SUBCLASS_TYPE), expected_type(t) {}

    bool validate(PyObject* obj) const noexcept override {
        return check_single_type(obj, expected_type);
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
    std::vector<TypeValidatorNode*> raw_branches;
    explicit ComplexUnionValidatorNode(std::vector<std::shared_ptr<TypeValidatorNode>> bs)
        : TypeValidatorNode(NodeKind::COMPLEX_UNION), branches(std::move(bs)) {
        raw_branches.reserve(branches.size());
        for (const auto& b : branches) {
            raw_branches.push_back(b.get());
        }
    }

    bool validate(PyObject* obj) const noexcept override {
        if (!obj) return false;
        for (auto* b : raw_branches) {
            if (b->validate(obj)) return true;
        }
        return false;
    }
};

struct CallableValidatorNode : public TypeValidatorNode {
    CallableValidatorNode() : TypeValidatorNode(NodeKind::CALLABLE) {}
    bool validate(PyObject* obj) const noexcept override {
        return obj && PyCallable_Check(obj) != 0;
    }
};

struct UninitializedClassValidatorNode : public TypeValidatorNode {
    PyTypeObject* target_type;
    explicit UninitializedClassValidatorNode(PyTypeObject* t)
        : TypeValidatorNode(NodeKind::UNINITIALIZED_CLASS), target_type(t) {}
    bool validate(PyObject* obj) const noexcept override {
        if (!obj || !PyType_Check(obj)) return false;
        if (!target_type || target_type == (PyTypeObject*)&PyType_Type || target_type == (PyTypeObject*)&PyBaseObject_Type) return true;
        return obj == (PyObject*)target_type;
    }
};

struct FastTypeCheck {
    PyTypeObject* single_type = nullptr;
    PyTypeObject* union_t0 = nullptr;
    PyTypeObject* union_t1 = nullptr;
    PyTypeObject* union_t2 = nullptr;
    std::shared_ptr<TypeValidatorNode> validator = nullptr;
    TypeValidatorNode* raw_validator = nullptr;

    FastTypeCheck() = default;

    void init(std::shared_ptr<TypeValidatorNode> v) {
        validator = std::move(v);
        raw_validator = validator.get();
        if (validator) {
            if (validator->kind == NodeKind::SUBCLASS_TYPE) {
                single_type = static_cast<SubclassTypeValidatorNode*>(validator.get())->expected_type;
            } else if (validator->kind == NodeKind::UNION_TYPE) {
                const auto& ts = static_cast<UnionTypeValidatorNode*>(validator.get())->types;
                if (ts.size() == 2) {
                    union_t0 = ts[0];
                    union_t1 = ts[1];
                } else if (ts.size() == 3) {
                    union_t0 = ts[0];
                    union_t1 = ts[1];
                    union_t2 = ts[2];
                }
            }
        }
    }

    inline bool has_check() const noexcept {
        return single_type != nullptr || union_t0 != nullptr || validator != nullptr;
    }

    inline bool check(PyObject* obj) const noexcept {
        if (single_type) {
            return check_single_type(obj, single_type);
        }
        if (union_t0) {
            if (union_t2) {
                return check_union3(obj, union_t0, union_t1, union_t2);
            }
            return check_union2(obj, union_t0, union_t1);
        }
        return raw_validator ? raw_validator->validate(obj) : true;
    }
};

template <bool IsList>
struct SequenceValidatorNode : public TypeValidatorNode {
    FastTypeCheck elem_check;
    PyTypeObject* elem_single_type = nullptr;
    SampleStrategy strategy;
    double sample_pct_val;

    SequenceValidatorNode(std::shared_ptr<TypeValidatorNode> el, SampleStrategy strat, double val = 0.0)
        : TypeValidatorNode(IsList ? NodeKind::LIST : NodeKind::VAR_TUPLE),
          strategy(strat), sample_pct_val(val) {
        elem_check.init(std::move(el));
        elem_single_type = elem_check.single_type;
    }

    inline bool check_elem(PyObject* item) const noexcept {
        return elem_check.check(item);
    }

    inline bool check_single_elem(PyObject* item) const noexcept {
        return check_single_type(item, elem_single_type);
    }

    inline bool check_elem_fast(PyObject* item) const noexcept {
        if (elem_single_type) return check_single_elem(item);
        return check_elem(item);
    }

    inline bool validate_all(PyObject* const* items, Py_ssize_t size) const noexcept {
        if (elem_single_type) {
            return check_items_single_all(items, size, elem_single_type);
        }
        if (elem_check.union_t0) {
            if (elem_check.union_t2) {
                PyTypeObject* t0 = elem_check.union_t0;
                PyTypeObject* t1 = elem_check.union_t1;
                PyTypeObject* t2 = elem_check.union_t2;
                for (Py_ssize_t i = 0; i < size; ++i) {
                    if (__builtin_expect(!check_union3(items[i], t0, t1, t2), 0)) return false;
                }
                return true;
            } else {
                return check_items_union2_all(items, size, elem_check.union_t0, elem_check.union_t1);
            }
        }
        if (elem_check.raw_validator) {
            TypeValidatorNode* v = elem_check.raw_validator;
            for (Py_ssize_t i = 0; i < size; ++i) {
                if (__builtin_expect(!v->validate(items[i]), 0)) return false;
            }
            return true;
        }
        return true;
    }

    inline bool validate_items(PyObject* const* items, Py_ssize_t size) const noexcept {
        switch (strategy) {
            case SampleStrategy::FIRST:
                return check_elem_fast(items[0]);
            case SampleStrategy::LAST:
                return check_elem_fast(items[size - 1]);
            case SampleStrategy::BOOKEND:
                if (!check_elem_fast(items[0])) return false;
                if (size > 1 && !check_elem_fast(items[size - 1])) return false;
                return true;
            case SampleStrategy::BOOKEND_PLUS:
                if (!check_elem_fast(items[0])) return false;
                if (size > 1 && !check_elem_fast(items[size - 1])) return false;
                if (size > 2) {
                    size_t mid = 1 + fast_quasi_rand(static_cast<size_t>(size - 2));
                    if (!check_elem_fast(items[mid])) return false;
                }
                return true;
            case SampleStrategy::RANDOM_ONE: {
                size_t idx = fast_quasi_rand(static_cast<size_t>(size));
                return check_elem_fast(items[idx]);
            }
            case SampleStrategy::LOG:
            case SampleStrategy::PERCENT:
            case SampleStrategy::COUNT: {
                size_t count = compute_sample_count(static_cast<size_t>(size), strategy, sample_pct_val);
                if (count >= static_cast<size_t>(size)) {
                    return validate_all(items, size);
                }
                Py_ssize_t step = size / count;
                if (step < 1) step = 1;
                Py_ssize_t start = static_cast<Py_ssize_t>(fast_quasi_rand(static_cast<size_t>(step)));
                if (elem_single_type) {
                    for (Py_ssize_t i = start; i < size; i += step) {
                        if (__builtin_expect(Py_TYPE(items[i]) != elem_single_type, 0) && !PyObject_TypeCheck(items[i], elem_single_type)) return false;
                    }
                    return true;
                }
                for (Py_ssize_t i = start; i < size; i += step) {
                    if (!check_elem(items[i])) return false;
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
    FastTypeCheck key_check;
    FastTypeCheck val_check;
    PyTypeObject* key_single_type = nullptr;
    PyTypeObject* val_single_type = nullptr;
    SampleStrategy strategy;
    double sample_pct_val;

    DictValidatorNode(std::shared_ptr<TypeValidatorNode> k, std::shared_ptr<TypeValidatorNode> v,
                      SampleStrategy strat, double pct_val = 0.0)
        : TypeValidatorNode(NodeKind::DICT), strategy(strat), sample_pct_val(pct_val) {
        key_check.init(std::move(k));
        val_check.init(std::move(v));
        key_single_type = key_check.single_type;
        val_single_type = val_check.single_type;
    }

    inline bool check_pair(PyObject* key, PyObject* val) const noexcept {
        return key_check.check(key) && val_check.check(val);
    }

    inline bool check_entry(PyObject* key, PyObject* val) const noexcept {
        if (key_single_type && val_single_type) {
            return check_single_type(key, key_single_type) && check_single_type(val, val_single_type);
        }
        if (key_single_type) {
            if (__builtin_expect(!check_single_type(key, key_single_type), 0)) return false;
            return val_check.check(val);
        }
        if (val_single_type) {
            if (__builtin_expect(!check_single_type(val, val_single_type), 0)) return false;
            return key_check.check(key);
        }
        return check_pair(key, val);
    }

    bool validate(PyObject* obj) const noexcept override {
        if (!obj || !PyDict_Check(obj)) return false;
        Py_ssize_t size = PyDict_GET_SIZE(obj);
        if (size == 0) return true;

        switch (strategy) {
            case SampleStrategy::FIRST:
            case SampleStrategy::LAST:
            case SampleStrategy::RANDOM_ONE: {
                Py_ssize_t pos = 0;
                PyObject *key, *value;
                if (!PyDict_Next(obj, &pos, &key, &value)) return true;
                return check_entry(key, value);
            }
            case SampleStrategy::BOOKEND: {
                Py_ssize_t pos = 0;
                PyObject *key, *value;
                if (!PyDict_Next(obj, &pos, &key, &value)) return true;
                if (!check_entry(key, value)) return false;
                if (size > 1) {
                    if (!PyDict_Next(obj, &pos, &key, &value)) return true;
                    if (!check_entry(key, value)) return false;
                }
                return true;
            }
            case SampleStrategy::BOOKEND_PLUS: {
                Py_ssize_t pos = 0;
                PyObject *key, *value;
                if (!PyDict_Next(obj, &pos, &key, &value)) return true;
                if (!check_entry(key, value)) return false;
                if (size > 1) {
                    if (!PyDict_Next(obj, &pos, &key, &value)) return true;
                    if (!check_entry(key, value)) return false;
                }
                if (size > 2) {
                    if (!PyDict_Next(obj, &pos, &key, &value)) return true;
                    if (!check_entry(key, value)) return false;
                }
                return true;
            }
            case SampleStrategy::LOG:
            case SampleStrategy::PERCENT:
            case SampleStrategy::COUNT: {
                size_t count = compute_sample_count(static_cast<size_t>(size), strategy, sample_pct_val);
                if (count >= static_cast<size_t>(size)) {
                    return validate_all(obj);
                }
                Py_ssize_t pos = 0;
                PyObject *key, *value;
                for (size_t checked = 0; checked < count; ++checked) {
                    if (!PyDict_Next(obj, &pos, &key, &value)) break;
                    if (!check_entry(key, value)) return false;
                }
                return true;
            }
            case SampleStrategy::ALL:
            default:
                return validate_all(obj);
        }
    }

    inline bool validate_all(PyObject* obj) const noexcept {
        if (key_single_type && val_single_type) {
            return check_dict_single_all(obj, key_single_type, val_single_type);
        }
        Py_ssize_t pos = 0;
        if (key_single_type && val_check.raw_validator) {
            PyTypeObject* kt = key_single_type;
            TypeValidatorNode* vv = val_check.raw_validator;
            PyObject *k, *v;
            while (PyDict_Next(obj, &pos, &k, &v)) {
                if (__builtin_expect(!check_single_type(k, kt), 0)) return false;
                if (__builtin_expect(!vv->validate(v), 0)) return false;
            }
            return true;
        }
        PyObject *k, *v;
        while (PyDict_Next(obj, &pos, &k, &v)) {
            if (!check_pair(k, v)) return false;
        }
        return true;
    }
};

struct SetValidatorNode : public TypeValidatorNode {
    FastTypeCheck elem_check;
    PyTypeObject* elem_single_type = nullptr;
    SampleStrategy strategy;
    double sample_pct_val;

    SetValidatorNode(std::shared_ptr<TypeValidatorNode> el, SampleStrategy strat, double val = 0.0)
        : TypeValidatorNode(NodeKind::SET), strategy(strat), sample_pct_val(val) {
        elem_check.init(std::move(el));
        elem_single_type = elem_check.single_type;
    }

    inline bool check_elem(PyObject* item) const noexcept {
        return elem_check.check(item);
    }

    bool validate(PyObject* obj) const noexcept override {
        if (!obj || (!PySet_Check(obj) && !PyFrozenSet_Check(obj))) return false;
        Py_ssize_t size = PySet_GET_SIZE(obj);
        if (size == 0) return true;

        PySetObject* so = (PySetObject*)obj;
        setentry* table = so->table;
        Py_ssize_t mask = so->mask;

        switch (strategy) {
            case SampleStrategy::FIRST:
            case SampleStrategy::LAST:
            case SampleStrategy::RANDOM_ONE: {
                for (Py_ssize_t i = 0; i <= mask; ++i) {
                    PyObject* item = table[i].key;
                    if (item && table[i].hash != -1) {
                        if (elem_single_type) {
                            return check_single_type(item, elem_single_type);
                        }
                        return check_elem(item);
                    }
                }
                return true;
            }
            case SampleStrategy::BOOKEND: {
                Py_ssize_t count = 0;
                Py_ssize_t to_check = (size > 1) ? 2 : 1;
                for (Py_ssize_t i = 0; i <= mask; ++i) {
                    PyObject* item = table[i].key;
                    if (item && table[i].hash != -1) {
                        if (elem_single_type) {
                            if (__builtin_expect(!check_single_type(item, elem_single_type), 0)) return false;
                        } else {
                            if (__builtin_expect(!check_elem(item), 0)) return false;
                        }
                        if (++count >= to_check) break;
                    }
                }
                return true;
            }
            case SampleStrategy::BOOKEND_PLUS: {
                Py_ssize_t count = 0;
                Py_ssize_t to_check = (size > 2) ? 3 : size;
                for (Py_ssize_t i = 0; i <= mask; ++i) {
                    PyObject* item = table[i].key;
                    if (item && table[i].hash != -1) {
                        if (elem_single_type) {
                            if (__builtin_expect(!check_single_type(item, elem_single_type), 0)) return false;
                        } else {
                            if (__builtin_expect(!check_elem(item), 0)) return false;
                        }
                        if (++count >= to_check) break;
                    }
                }
                return true;
            }
            case SampleStrategy::LOG:
            case SampleStrategy::PERCENT:
            case SampleStrategy::COUNT: {
                size_t to_check = compute_sample_count(static_cast<size_t>(size), strategy, sample_pct_val);
                if (to_check >= static_cast<size_t>(size)) goto validate_all_items;
                size_t count = 0;
                for (Py_ssize_t i = 0; i <= mask; ++i) {
                    PyObject* item = table[i].key;
                    if (item && table[i].hash != -1) {
                        if (elem_single_type) {
                            if (__builtin_expect(!check_single_type(item, elem_single_type), 0)) return false;
                        } else {
                            if (__builtin_expect(!check_elem(item), 0)) return false;
                        }
                        if (++count >= to_check) break;
                    }
                }
                return true;
            }
            case SampleStrategy::ALL:
            default:
            validate_all_items:
                if (elem_single_type) {
                    return check_set_single_all(obj, elem_single_type);
                }
                Py_ssize_t found = 0;
                for (Py_ssize_t i = 0; i <= mask && found < size; ++i) {
                    PyObject* item = table[i].key;
                    if (item && table[i].hash != -1) {
                        found++;
                        if (__builtin_expect(!check_elem(item), 0)) return false;
                    }
                }
                return true;
        }
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
            if (count == 2) {
                return check_fixed_tuple2(obj, single_types[0], single_types[1]);
            }
            if (count == 3) {
                return check_fixed_tuple3(obj, single_types[0], single_types[1], single_types[2]);
            }
            for (size_t i = 0; i < count; ++i) {
                PyTypeObject* exp = single_types[i];
                if (__builtin_expect(!check_single_type(items[i], exp), 0)) return false;
            }
            return true;
        }
        for (size_t i = 0; i < count; ++i) {
            if (!elem_vals[i]->validate(items[i])) return false;
        }
        return true;
    }
};

struct TypedDictField {
    PyObject* key_unicode = nullptr;
    FastTypeCheck type_check;
    bool is_required = true;

    TypedDictField() = default;

    TypedDictField(PyObject* k, std::shared_ptr<TypeValidatorNode> v, bool req)
        : key_unicode(k), is_required(req) {
        if (key_unicode) Py_INCREF(key_unicode);
        type_check.init(std::move(v));
    }

    TypedDictField(const TypedDictField& o)
        : key_unicode(o.key_unicode), type_check(o.type_check), is_required(o.is_required) {
        if (key_unicode) Py_INCREF(key_unicode);
    }

    TypedDictField(TypedDictField&& o) noexcept
        : key_unicode(o.key_unicode), type_check(std::move(o.type_check)), is_required(o.is_required) {
        o.key_unicode = nullptr;
    }

    TypedDictField& operator=(const TypedDictField& o) {
        if (this != &o) {
            Py_XDECREF(key_unicode);
            key_unicode = o.key_unicode;
            if (key_unicode) Py_INCREF(key_unicode);
            type_check = o.type_check;
            is_required = o.is_required;
        }
        return *this;
    }

    TypedDictField& operator=(TypedDictField&& o) noexcept {
        if (this != &o) {
            Py_XDECREF(key_unicode);
            key_unicode = o.key_unicode;
            o.key_unicode = nullptr;
            type_check = std::move(o.type_check);
            is_required = o.is_required;
        }
        return *this;
    }

    ~TypedDictField() {
        Py_XDECREF(key_unicode);
    }
};

struct TypedDictValidatorNode : public TypeValidatorNode {
    std::vector<TypedDictField> fields;

    explicit TypedDictValidatorNode(std::vector<TypedDictField> flds)
        : TypeValidatorNode(NodeKind::TYPED_DICT), fields(std::move(flds)) {}

    bool validate(PyObject* obj) const noexcept override {
        if (!obj || !PyDict_Check(obj)) return false;
        for (const auto& f : fields) {
            PyObject* val = PyDict_GetItemWithError(obj, f.key_unicode);
            if (!val) {
                if (PyErr_Occurred()) PyErr_Clear();
                if (f.is_required) return false;
                continue;
            }
            if (__builtin_expect(!f.type_check.check(val), 0)) return false;
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

static inline bool is_type_origin(PyObject* obj, PyTypeObject** out_target) {
    if (!obj) return false;
    if (obj == (PyObject*)&PyType_Type) {
        if (out_target) *out_target = (PyTypeObject*)&PyType_Type;
        return true;
    }
    PyObject* origin = PyObject_GetAttrString(obj, "__origin__");
    if (!origin) {
        PyErr_Clear();
        return false;
    }
    bool is_type = (origin == (PyObject*)&PyType_Type);
    Py_DECREF(origin);
    if (!is_type) return false;
    PyObject* args = PyObject_GetAttrString(obj, "__args__");
    if (!args) {
        PyErr_Clear();
        if (out_target) *out_target = (PyTypeObject*)&PyType_Type;
        return true;
    }
    if (PyTuple_Check(args) && PyTuple_GET_SIZE(args) == 1) {
        PyObject* arg0 = PyTuple_GET_ITEM(args, 0);
        if (PyType_Check(arg0)) {
            if (out_target) *out_target = (PyTypeObject*)arg0;
            Py_DECREF(args);
            return true;
        }
    }
    Py_DECREF(args);
    if (out_target) *out_target = (PyTypeObject*)&PyType_Type;
    return true;
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

static std::shared_ptr<TypeValidatorNode> build_node(nb::handle spec, SampleStrategy strategy, double sample_val);

static std::shared_ptr<TypeValidatorNode> build_single_mapping(PyObject* key, PyObject* value, SampleStrategy strategy, double sample_val) {
    if (value == Py_None) {
        PyTypeObject* tgt = nullptr;
        if (is_type_origin(key, &tgt)) {
            return std::make_shared<UninitializedClassValidatorNode>(tgt);
        }
        if (is_plain_type(key)) {
            return std::make_shared<SubclassTypeValidatorNode>((PyTypeObject*)key);
        }
        return nullptr;
    }

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
            return (branches.size() == 1) ? branches[0] : std::make_shared<ComplexUnionValidatorNode>(std::move(branches));
        }
        return build_one(val);
    };

    if (key == (PyObject*)&PyList_Type) {
        return build_variants(value, [&](PyObject* item) -> std::shared_ptr<TypeValidatorNode> {
            auto elem = build_node(nb::handle(item), strategy, sample_val);
            return elem ? std::make_shared<ListValidatorNode>(std::move(elem), strategy, sample_val) : nullptr;
        });
    }
    if (key == (PyObject*)&PySet_Type) {
        return build_variants(value, [&](PyObject* item) -> std::shared_ptr<TypeValidatorNode> {
            auto elem = build_node(nb::handle(item), strategy, sample_val);
            return elem ? std::make_shared<SetValidatorNode>(std::move(elem), strategy, sample_val) : nullptr;
        });
    }
    if (key == (PyObject*)&PyDict_Type) {
        return build_variants(value, [&](PyObject* d_spec) -> std::shared_ptr<TypeValidatorNode> {
            if (!PyTuple_Check(d_spec) || PyTuple_GET_SIZE(d_spec) != 2) return nullptr;
            auto k_node = build_node(nb::handle(PyTuple_GET_ITEM(d_spec, 0)), strategy, sample_val);
            auto v_node = build_node(nb::handle(PyTuple_GET_ITEM(d_spec, 1)), strategy, sample_val);
            return (k_node && v_node) ? std::make_shared<DictValidatorNode>(std::move(k_node), std::move(v_node), strategy, sample_val) : nullptr;
        });
    }
    if (key == (PyObject*)&PyTuple_Type) {
        return build_variants(value, [&](PyObject* tup_spec) -> std::shared_ptr<TypeValidatorNode> {
            if (PyTuple_Check(tup_spec) && PyTuple_GET_SIZE(tup_spec) == 2 && PyTuple_GET_ITEM(tup_spec, 1) == Py_True) {
                auto elem = build_node(nb::handle(PyTuple_GET_ITEM(tup_spec, 0)), strategy, sample_val);
                return elem ? std::make_shared<VariableTupleValidatorNode>(std::move(elem), strategy, sample_val) : nullptr;
            }
            PyObject* items_tup = (PyTuple_Check(tup_spec) && PyTuple_GET_SIZE(tup_spec) == 2 && PyTuple_GET_ITEM(tup_spec, 1) == Py_False && PyTuple_Check(PyTuple_GET_ITEM(tup_spec, 0)))
                ? PyTuple_GET_ITEM(tup_spec, 0) : tup_spec;
            if (PyTuple_Check(items_tup)) {
                Py_ssize_t t_size = PyTuple_GET_SIZE(items_tup);
                std::vector<std::shared_ptr<TypeValidatorNode>> elem_nodes;
                elem_nodes.reserve(t_size);
                for (Py_ssize_t j = 0; j < t_size; ++j) {
                    auto sub = build_node(nb::handle(PyTuple_GET_ITEM(items_tup, j)), strategy, sample_val);
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

static std::shared_ptr<TypeValidatorNode> build_node(nb::handle spec, SampleStrategy strategy, double sample_val) {
    if (spec.is_none()) {
        return nullptr;
    }

    PyObject* ptr = spec.ptr();
    if (is_plain_type(ptr)) {
        return std::make_shared<SubclassTypeValidatorNode>((PyTypeObject*)ptr);
    }
    PyTypeObject* origin_target = nullptr;
    if (is_type_origin(ptr, &origin_target)) {
        return std::make_shared<UninitializedClassValidatorNode>(origin_target);
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
        PyObject* extra = PyDict_GetItemString(ptr, "__extra__");
        if (extra != nullptr) {
            if (PyDict_Check(extra)) {
                PyObject* cb = PyDict_GetItemString(extra, "__callable__");
                if (cb && cb == Py_True) {
                    return std::make_shared<CallableValidatorNode>();
                }
                PyObject* td = PyDict_GetItemString(extra, "__typeddict__");
                if (td != nullptr && PyDict_Check(td)) {
                    PyObject* fields_dict = PyDict_GetItemString(td, "fields");
                    PyObject* req_set = PyDict_GetItemString(td, "required");
                    if (fields_dict && PyDict_Check(fields_dict)) {
                        std::vector<TypedDictField> td_fields;
                        Py_ssize_t f_pos = 0;
                        PyObject *f_key, *f_val;
                        while (PyDict_Next(fields_dict, &f_pos, &f_key, &f_val)) {
                            auto field_node = build_node(nb::handle(f_val), strategy, sample_val);
                            if (!field_node) return nullptr;
                            int contains = 1;
                            if (req_set) {
                                contains = PySequence_Contains(req_set, f_key);
                                if (contains < 0) {
                                    PyErr_Clear();
                                    contains = 0;
                                }
                            }
                            td_fields.emplace_back(f_key, std::move(field_node), contains != 0);
                        }
                        return std::make_shared<TypedDictValidatorNode>(std::move(td_fields));
                    }
                }
            }
            return nullptr;
        }
        Py_ssize_t size = PyDict_GET_SIZE(ptr);
        if (size == 0) return nullptr;

        bool all_none = true;
        bool all_keys_are_types = true;
        bool has_uninit_type = false;
        Py_ssize_t pos = 0;
        PyObject *key, *value;
        while (PyDict_Next(ptr, &pos, &key, &value)) {
            if (value != Py_None) all_none = false;
            if (!is_plain_type(key)) {
                PyTypeObject* tgt = nullptr;
                if (is_type_origin(key, &tgt)) {
                    has_uninit_type = true;
                } else {
                    all_keys_are_types = false;
                }
            }
        }

        if (all_none && all_keys_are_types) {
            if (size == 1) {
                pos = 0;
                PyDict_Next(ptr, &pos, &key, &value);
                PyTypeObject* tgt = nullptr;
                if (is_type_origin(key, &tgt)) {
                    return std::make_shared<UninitializedClassValidatorNode>(tgt);
                }
                return std::make_shared<SubclassTypeValidatorNode>((PyTypeObject*)key);
            }
            if (!has_uninit_type) {
                std::vector<PyTypeObject*> types;
                types.reserve(size);
                pos = 0;
                while (PyDict_Next(ptr, &pos, &key, &value)) {
                    types.push_back((PyTypeObject*)key);
                }
                return std::make_shared<UnionTypeValidatorNode>(std::move(types));
            }
        }

        if (size == 1) {
            pos = 0;
            PyDict_Next(ptr, &pos, &key, &value);
            return build_single_mapping(key, value, strategy, sample_val);
        }

        std::vector<std::shared_ptr<TypeValidatorNode>> branches;
        branches.reserve(size);
        pos = 0;
        while (PyDict_Next(ptr, &pos, &key, &value)) {
            auto sub_node = build_single_mapping(key, value, strategy, sample_val);
            if (!sub_node) return nullptr;
            branches.push_back(std::move(sub_node));
        }
        return (branches.size() == 1) ? branches[0] : std::make_shared<ComplexUnionValidatorNode>(std::move(branches));
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

static void classify_param_node(
    const std::shared_ptr<TypeValidatorNode>& node,
    SampleStrategy strategy,
    ParamCheckKind& out_kind,
    PyTypeObject*& out_t0,
    PyTypeObject*& out_t1,
    PyTypeObject*& out_t2,
    TypeValidatorNode*& out_node
) noexcept {
    out_kind = ParamCheckKind::PASS;
    out_t0 = nullptr;
    out_t1 = nullptr;
    out_t2 = nullptr;
    out_node = nullptr;

    if (!node) {
        return;
    }

    out_node = node.get();

    if (node->kind == NodeKind::SUBCLASS_TYPE) {
        out_kind = ParamCheckKind::SINGLE_TYPE;
        out_t0 = static_cast<SubclassTypeValidatorNode*>(node.get())->expected_type;
        return;
    }

    if (node->kind == NodeKind::UNION_TYPE) {
        const auto& types = static_cast<UnionTypeValidatorNode*>(node.get())->types;
        if (types.size() == 2) {
            out_kind = ParamCheckKind::UNION2;
            out_t0 = types[0];
            out_t1 = types[1];
            return;
        }
        if (types.size() == 3) {
            out_kind = ParamCheckKind::UNION3;
            out_t0 = types[0];
            out_t1 = types[1];
            out_t2 = types[2];
            return;
        }
        out_kind = ParamCheckKind::NODE;
        return;
    }

    if (node->kind == NodeKind::LIST) {
        auto* ln = static_cast<ListValidatorNode*>(node.get());
        if (strategy == SampleStrategy::ALL) {
            if (ln->elem_single_type) {
                out_kind = ParamCheckKind::LIST_SINGLE_ALL;
                out_t0 = ln->elem_single_type;
                return;
            }
            if (ln->elem_check.union_t0 && !ln->elem_check.union_t2) {
                out_kind = ParamCheckKind::LIST_UNION2_ALL;
                out_t0 = ln->elem_check.union_t0;
                out_t1 = ln->elem_check.union_t1;
                return;
            }
        }
        out_kind = ParamCheckKind::NODE;
        return;
    }

    if (node->kind == NodeKind::VAR_TUPLE) {
        auto* tn = static_cast<VariableTupleValidatorNode*>(node.get());
        if (strategy == SampleStrategy::ALL && tn->elem_single_type) {
            out_kind = ParamCheckKind::VAR_TUPLE_SINGLE_ALL;
            out_t0 = tn->elem_single_type;
            return;
        }
        out_kind = ParamCheckKind::NODE;
        return;
    }

    if (node->kind == NodeKind::FIXED_TUPLE) {
        auto* ftn = static_cast<FixedTupleValidatorNode*>(node.get());
        if (ftn->all_single_types) {
            if (ftn->single_types.size() == 2) {
                out_kind = ParamCheckKind::FIXED_TUPLE2;
                out_t0 = ftn->single_types[0];
                out_t1 = ftn->single_types[1];
                return;
            }
            if (ftn->single_types.size() == 3) {
                out_kind = ParamCheckKind::FIXED_TUPLE3;
                out_t0 = ftn->single_types[0];
                out_t1 = ftn->single_types[1];
                out_t2 = ftn->single_types[2];
                return;
            }
        }
        out_kind = ParamCheckKind::NODE;
        return;
    }

    if (node->kind == NodeKind::DICT) {
        auto* dn = static_cast<DictValidatorNode*>(node.get());
        if (strategy == SampleStrategy::ALL && dn->key_single_type && dn->val_single_type) {
            out_kind = ParamCheckKind::DICT_SINGLE_ALL;
            out_t0 = dn->key_single_type;
            out_t1 = dn->val_single_type;
            return;
        }
        out_kind = ParamCheckKind::NODE;
        return;
    }

    if (node->kind == NodeKind::SET) {
        auto* sn = static_cast<SetValidatorNode*>(node.get());
        if (strategy == SampleStrategy::ALL && sn->elem_single_type) {
            out_kind = ParamCheckKind::SET_SINGLE_ALL;
            out_t0 = sn->elem_single_type;
            return;
        }
        out_kind = ParamCheckKind::NODE;
        return;
    }

    out_kind = ParamCheckKind::NODE;
}

// ----------------- PyValidatorObject (VALIDATOR) -----------------

struct PyValidatorObject {
    PyObject_HEAD
    vectorcallfunc vectorcall;
    ParamCheckKind fast_kind;
    uint8_t _pad[7];
    PyTypeObject* t0;
    PyTypeObject* t1;
    PyTypeObject* t2;
    TypeValidatorNode* raw_root;
    std::shared_ptr<TypeValidatorNode> root;
};

static PyObject* validator_vectorcall(PyObject* self, PyObject* const* args, size_t nargsf, PyObject* kwnames) {
    if (__builtin_expect(kwnames == nullptr && PyVectorcall_NARGS(nargsf) == 1, 1)) {
        PyValidatorObject* v = (PyValidatorObject*)self;
        if (__builtin_expect(validate_param(args[0], v->fast_kind, v->t0, v->t1, v->t2, v->raw_root), 1)) {
            Py_RETURN_TRUE;
        } else {
            Py_RETURN_FALSE;
        }
    }
    Py_ssize_t nargs = PyVectorcall_NARGS(nargsf);
    if (__builtin_expect(nargs != 1 || kwnames != nullptr, 0)) {
        PyErr_SetString(PyExc_TypeError, "validator takes exactly 1 positional argument");
        return nullptr;
    }
    PyValidatorObject* v = (PyValidatorObject*)self;
    if (validate_param(args[0], v->fast_kind, v->t0, v->t1, v->t2, v->raw_root)) {
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
    PyObject* arg = PyTuple_GET_ITEM(args, 0);
    return v->vectorcall(self, &arg, 1, nullptr);
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
        obj->raw_root = obj->root.get();
        obj->vectorcall = validator_vectorcall;
        classify_param_node(obj->root, strategy, obj->fast_kind, obj->t0, obj->t1, obj->t2, obj->raw_root);
        return nb::steal(reinterpret_cast<PyObject*>(obj));
    }
    return nb::none();
}

// ----------------- FAST CALL DISPATCHER -----------------

enum class RetCheckKind : uint8_t {
    NO_CHECK = 0,
    NONE_RETURN = 1,
    SELF_RETURN = 2,
    TYPE_CHECK = 3
};

struct FastParamInfo {
    FastTypeCheck type_check;
    PyObject* exp = nullptr;
    PyObject* name_str = nullptr;

    FastParamInfo() = default;
    FastParamInfo(const FastParamInfo&) = delete;
    FastParamInfo& operator=(const FastParamInfo&) = delete;
    FastParamInfo(FastParamInfo&& o) noexcept
        : type_check(std::move(o.type_check)), exp(o.exp), name_str(o.name_str) {
        o.exp = nullptr;
        o.name_str = nullptr;
    }
    FastParamInfo& operator=(FastParamInfo&& o) noexcept {
        if (this != &o) {
            type_check = std::move(o.type_check);
            Py_XDECREF(exp);
            Py_XDECREF(name_str);
            exp = o.exp;
            name_str = o.name_str;
            o.exp = nullptr;
            o.name_str = nullptr;
        }
        return *this;
    }
    ~FastParamInfo() {
        Py_XDECREF(exp);
        Py_XDECREF(name_str);
    }
};

struct PyFastCallObject {
    PyObject_HEAD
    vectorcallfunc vectorcall;
    PyObject* fn;
    vectorcallfunc fn_vectorcall;
    RetCheckKind ret_kind;
    uint8_t num_pos;
    bool has_varargs;
    bool has_varkw;
    bool all_pos_single_types;
    ParamCheckKind pos_kinds[8];
    uint8_t _pad[3];
    PyTypeObject* ret_single_type;
    PyTypeObject* pos_types[8];
    PyTypeObject* pos_types_extra[8];
    PyTypeObject* pos_types_extra2[8];
    TypeValidatorNode* pos_nodes[8];
    PyTypeObject* ret_union_t0;
    PyTypeObject* ret_union_t1;
    PyTypeObject* ret_union_t2;
    FastTypeCheck pos_checks[8];

    // Cold fields below (only accessed on error path, fallback, kwargs, or destruction)
    PyObject* self_enforcer;
    PyObject* check_fn;
    PyObject* ret_exp;
    PyObject* ret_str;
    FastTypeCheck ret_check;
    FastParamInfo varargs_info;
    FastParamInfo varkw_info;
    std::vector<FastParamInfo> pos_params;
    std::vector<FastParamInfo> kwonly_params;
    std::unordered_map<std::string, std::pair<bool, size_t>> kw_to_param;
};

[[gnu::noinline]] static bool handle_type_error_cold(PyObject* check_fn, PyObject* self_enforcer, PyObject* arg, PyObject* exp, PyObject* name) noexcept {
    PyObject* check_args[4] = {self_enforcer, arg, exp, name};
    PyObject* check_res = PyObject_Vectorcall(check_fn, check_args, 4, nullptr);
    if (!check_res) return false;
    Py_DECREF(check_res);
    return true;
}

static inline bool handle_type_error(PyObject* check_fn, PyObject* self_enforcer, PyObject* arg, PyObject* exp, PyObject* name) noexcept {
    return handle_type_error_cold(check_fn, self_enforcer, arg, exp, name);
}

[[gnu::noinline]] static bool handle_return_error(const PyFastCallObject* fc, PyObject* self, PyObject* res) noexcept {
    PyObject* enforcer = fc->self_enforcer ? fc->self_enforcer : self;
    return handle_type_error(fc->check_fn, enforcer, res, fc->ret_exp, fc->ret_str);
}

[[gnu::noinline]] static bool handle_return_check(const PyFastCallObject* fc, PyObject* self, PyObject* res, PyObject* const* fn_args, size_t fn_nargs) noexcept {
    switch (fc->ret_kind) {
        case RetCheckKind::NONE_RETURN:
            if (__builtin_expect(res == Py_None, 1)) return true;
            break;
        case RetCheckKind::SELF_RETURN: {
            if (__builtin_expect(fn_nargs > 0, 1)) {
                PyTypeObject* self_cls = Py_TYPE(fn_args[0]);
                if (__builtin_expect(Py_TYPE(res) == self_cls, 1)) return true;
                if (PyObject_TypeCheck(res, self_cls)) return true;
            } else {
                return true;
            }
            break;
        }
        case RetCheckKind::TYPE_CHECK:
            if (__builtin_expect(fc->ret_check.check(res), 1)) return true;
            break;
        case RetCheckKind::NO_CHECK:
        default:
            return true;
    }
    return handle_return_error(fc, self, res);
}

static inline PyObject* call_target(const PyFastCallObject* fc, PyObject* const* args, size_t nargsf, PyObject* kwnames = nullptr) noexcept {
    if (__builtin_expect(fc->fn_vectorcall != nullptr, 1)) {
        return fc->fn_vectorcall(fc->fn, args, nargsf, kwnames);
    }
    return PyObject_Vectorcall(fc->fn, args, nargsf, kwnames);
}

static PyObject* fast_call_general_vectorcall(PyObject* self, PyObject* const* args, size_t nargsf, PyObject* kwnames) {
    PyFastCallObject* fc = (PyFastCallObject*)self;
    if (__builtin_expect(fc->fn == nullptr, 0)) {
        PyObject* meth = PyObject_GetAttrString(self, "__fallback_call__");
        if (!meth) return nullptr;
        PyObject* res = PyObject_Vectorcall(meth, args, nargsf, kwnames);
        Py_DECREF(meth);
        return res;
    }

    PyObject* self_enforcer = fc->self_enforcer ? fc->self_enforcer : self;
    size_t fn_nargs = PyVectorcall_NARGS(nargsf);
    size_t num_pos = fc->num_pos;
    size_t check_pos_count = (fn_nargs < num_pos) ? fn_nargs : num_pos;
    const auto* p_arr = fc->pos_params.data();

    for (size_t i = 0; i < check_pos_count; ++i) {
        bool ok = (i < 8)
            ? validate_param(args[i], fc->pos_kinds[i], fc->pos_types[i], fc->pos_types_extra[i], fc->pos_types_extra2[i], fc->pos_nodes[i])
            : p_arr[i].type_check.check(args[i]);
        if (__builtin_expect(!ok, 0)) {
            if (!handle_type_error(fc->check_fn, self_enforcer, args[i], p_arr[i].exp, p_arr[i].name_str)) return nullptr;
        }
    }

    if (fc->has_varargs && fn_nargs > num_pos && fc->varargs_info.type_check.has_check()) {
        for (size_t i = num_pos; i < fn_nargs; ++i) {
            if (__builtin_expect(!fc->varargs_info.type_check.check(args[i]), 0)) {
                if (!handle_type_error(fc->check_fn, self_enforcer, args[i], fc->varargs_info.exp, fc->varargs_info.name_str)) return nullptr;
            }
        }
    }

    if (kwnames != nullptr) {
        size_t n_kwargs = PyTuple_GET_SIZE(kwnames);
        PyObject* const* kw_values = args + fn_nargs;
        for (size_t j = 0; j < n_kwargs; ++j) {
            PyObject* key_obj = PyTuple_GET_ITEM(kwnames, j);
            const char* key_cstr = PyUnicode_AsUTF8(key_obj);
            if (key_cstr) {
                auto it = fc->kw_to_param.find(key_cstr);
                if (it != fc->kw_to_param.end()) {
                    const auto& [is_kwonly, idx] = it->second;
                    const auto& p = is_kwonly ? fc->kwonly_params[idx] : fc->pos_params[idx];
                    if (__builtin_expect(!p.type_check.check(kw_values[j]), 0)) {
                        if (!handle_type_error(fc->check_fn, self_enforcer, kw_values[j], p.exp, p.name_str)) return nullptr;
                    }
                } else if (fc->has_varkw && fc->varkw_info.type_check.has_check()) {
                    if (__builtin_expect(!fc->varkw_info.type_check.check(kw_values[j]), 0)) {
                        if (!handle_type_error(fc->check_fn, self_enforcer, kw_values[j], fc->varkw_info.exp, key_obj)) return nullptr;
                    }
                }
            }
        }
    }

    PyObject* res = call_target(fc, args, nargsf, kwnames);
    if (__builtin_expect(!res, 0)) return nullptr;

    if (fc->ret_kind != RetCheckKind::NO_CHECK) {
        if (__builtin_expect(!handle_return_check(fc, self, res, args, fn_nargs), 0)) {
            Py_DECREF(res);
            return nullptr;
        }
    }
    return res;
}

enum class ArgPattern : uint8_t {
    SINGLE_TYPES = 0,               // 0..8 args, each with single_type in pos_types[i] (or null if unvalidated)
    POS1_UNION2 = 1,                // 1 arg union of 2 types
    POS1_LIST_SINGLE_ALL = 2,       // 1 arg list of single type (all)
    POS1_DICT_SINGLE_ALL = 3,       // 1 arg dict of single types (all)
    POS1_SET_SINGLE_ALL = 4,        // 1 arg set of single type (all)
    POS1_VAR_TUPLE_SINGLE_ALL = 5,  // 1 arg var tuple of single type (all)
    POS1_FIXED_TUPLE2 = 6,          // 1 arg fixed tuple of 2 single types
    POS1_FAST = 7,                  // 1 arg general validate_param
    FAST_PARAMS = 8                 // 0..8 args with fast param kinds
};

enum class RetPattern : uint8_t {
    NO_CHECK = 0,
    NONE = 1,
    SELF = 2,
    SINGLE_TYPE = 3,
    UNION_TYPE = 4,
    GENERAL = 5
};

template <size_t N_POS, ArgPattern ARG_PAT, RetPattern RET_PAT>
static PyObject* fast_vectorcall(PyObject* self, PyObject* const* args, size_t nargsf, PyObject* kwnames) {
    if (__builtin_expect(kwnames == nullptr && PyVectorcall_NARGS(nargsf) == N_POS, 1)) {
        PyFastCallObject* fc = (PyFastCallObject*)self;

        if constexpr (ARG_PAT == ArgPattern::SINGLE_TYPES) {
            for (size_t i = 0; i < N_POS; ++i) {
                PyTypeObject* exp_t = fc->pos_types[i];
                if (exp_t) {
                    PyObject* a = args[i];
                    if (__builtin_expect(Py_TYPE(a) != exp_t, 0) && !PyObject_TypeCheck(a, exp_t)) {
                        PyObject* enforcer = fc->self_enforcer ? fc->self_enforcer : self;
                        if (!handle_type_error(fc->check_fn, enforcer, a, fc->pos_params[i].exp, fc->pos_params[i].name_str)) return nullptr;
                    }
                }
            }
        } else if constexpr (ARG_PAT == ArgPattern::POS1_UNION2) {
            PyObject* a0 = args[0];
            if (__builtin_expect(!check_union2(a0, fc->pos_types[0], fc->pos_types_extra[0]), 0)) {
                PyObject* enforcer = fc->self_enforcer ? fc->self_enforcer : self;
                if (!handle_type_error(fc->check_fn, enforcer, a0, fc->pos_params[0].exp, fc->pos_params[0].name_str)) return nullptr;
            }
        } else if constexpr (ARG_PAT == ArgPattern::POS1_LIST_SINGLE_ALL) {
            PyObject* a0 = args[0];
            if (__builtin_expect(!check_list_single_all(a0, fc->pos_types[0]), 0)) {
                PyObject* enforcer = fc->self_enforcer ? fc->self_enforcer : self;
                if (!handle_type_error(fc->check_fn, enforcer, a0, fc->pos_params[0].exp, fc->pos_params[0].name_str)) return nullptr;
            }
        } else if constexpr (ARG_PAT == ArgPattern::POS1_DICT_SINGLE_ALL) {
            PyObject* a0 = args[0];
            if (__builtin_expect(!check_dict_single_all(a0, fc->pos_types[0], fc->pos_types_extra[0]), 0)) {
                PyObject* enforcer = fc->self_enforcer ? fc->self_enforcer : self;
                if (!handle_type_error(fc->check_fn, enforcer, a0, fc->pos_params[0].exp, fc->pos_params[0].name_str)) return nullptr;
            }
        } else if constexpr (ARG_PAT == ArgPattern::POS1_SET_SINGLE_ALL) {
            PyObject* a0 = args[0];
            if (__builtin_expect(!check_set_single_all(a0, fc->pos_types[0]), 0)) {
                PyObject* enforcer = fc->self_enforcer ? fc->self_enforcer : self;
                if (!handle_type_error(fc->check_fn, enforcer, a0, fc->pos_params[0].exp, fc->pos_params[0].name_str)) return nullptr;
            }
        } else if constexpr (ARG_PAT == ArgPattern::POS1_VAR_TUPLE_SINGLE_ALL) {
            PyObject* a0 = args[0];
            if (__builtin_expect(!check_tuple_single_all(a0, fc->pos_types[0]), 0)) {
                PyObject* enforcer = fc->self_enforcer ? fc->self_enforcer : self;
                if (!handle_type_error(fc->check_fn, enforcer, a0, fc->pos_params[0].exp, fc->pos_params[0].name_str)) return nullptr;
            }
        } else if constexpr (ARG_PAT == ArgPattern::POS1_FIXED_TUPLE2) {
            PyObject* a0 = args[0];
            if (__builtin_expect(!check_fixed_tuple2(a0, fc->pos_types[0], fc->pos_types_extra[0]), 0)) {
                PyObject* enforcer = fc->self_enforcer ? fc->self_enforcer : self;
                if (!handle_type_error(fc->check_fn, enforcer, a0, fc->pos_params[0].exp, fc->pos_params[0].name_str)) return nullptr;
            }
        } else if constexpr (ARG_PAT == ArgPattern::POS1_FAST) {
            PyObject* a0 = args[0];
            if (__builtin_expect(!validate_param(a0, fc->pos_kinds[0], fc->pos_types[0], fc->pos_types_extra[0], fc->pos_types_extra2[0], fc->pos_nodes[0]), 0)) {
                PyObject* enforcer = fc->self_enforcer ? fc->self_enforcer : self;
                if (!handle_type_error(fc->check_fn, enforcer, a0, fc->pos_params[0].exp, fc->pos_params[0].name_str)) return nullptr;
            }
        } else if constexpr (ARG_PAT == ArgPattern::FAST_PARAMS) {
            for (size_t i = 0; i < N_POS; ++i) {
                if (__builtin_expect(!validate_param(args[i], fc->pos_kinds[i], fc->pos_types[i], fc->pos_types_extra[i], fc->pos_types_extra2[i], fc->pos_nodes[i]), 0)) {
                    PyObject* enforcer = fc->self_enforcer ? fc->self_enforcer : self;
                    if (!handle_type_error(fc->check_fn, enforcer, args[i], fc->pos_params[i].exp, fc->pos_params[i].name_str)) return nullptr;
                }
            }
        }

        if constexpr (RET_PAT == RetPattern::NO_CHECK) {
            return call_target(fc, args, nargsf);
        }

        PyObject* res = call_target(fc, args, nargsf);
        if (__builtin_expect(!res, 0)) return nullptr;

        if constexpr (RET_PAT == RetPattern::NONE) {
            if (__builtin_expect(res != Py_None, 0)) {
                if (!handle_return_error(fc, self, res)) {
                    Py_DECREF(res);
                    return nullptr;
                }
            }
            return res;
        } else if constexpr (RET_PAT == RetPattern::SELF) {
            if constexpr (N_POS > 0) {
                PyTypeObject* self_cls = Py_TYPE(args[0]);
                if (__builtin_expect(Py_TYPE(res) != self_cls, 0) && !PyObject_TypeCheck(res, self_cls)) {
                    if (!handle_return_error(fc, self, res)) {
                        Py_DECREF(res);
                        return nullptr;
                    }
                }
            }
            return res;
        } else if constexpr (RET_PAT == RetPattern::SINGLE_TYPE) {
            PyTypeObject* rt = fc->ret_single_type;
            if (__builtin_expect(Py_TYPE(res) != rt, 0) && !PyObject_TypeCheck(res, rt)) {
                if (!handle_return_error(fc, self, res)) {
                    Py_DECREF(res);
                    return nullptr;
                }
            }
            return res;
        } else if constexpr (RET_PAT == RetPattern::UNION_TYPE) {
            uintptr_t rt = (uintptr_t)Py_TYPE(res);
            PyTypeObject* rt0 = fc->ret_union_t0;
            PyTypeObject* rt1 = fc->ret_union_t1;
            PyTypeObject* rt2 = fc->ret_union_t2;
            if (rt2) {
                if (__builtin_expect((rt != (uintptr_t)rt0) & (rt != (uintptr_t)rt1) & (rt != (uintptr_t)rt2), 0)) {
                    if (!PyObject_TypeCheck(res, rt0) && !PyObject_TypeCheck(res, rt1) && !PyObject_TypeCheck(res, rt2)) {
                        if (!handle_return_error(fc, self, res)) {
                            Py_DECREF(res);
                            return nullptr;
                        }
                    }
                }
            } else {
                if (__builtin_expect((rt != (uintptr_t)rt0) & (rt != (uintptr_t)rt1), 0)) {
                    if (!PyObject_TypeCheck(res, rt0) && !PyObject_TypeCheck(res, rt1)) {
                        if (!handle_return_error(fc, self, res)) {
                            Py_DECREF(res);
                            return nullptr;
                        }
                    }
                }
            }
            return res;
        } else {
            if (__builtin_expect(!handle_return_check(fc, self, res, args, N_POS), 0)) {
                Py_DECREF(res);
                return nullptr;
            }
            return res;
        }
    }
    return fast_call_general_vectorcall(self, args, nargsf, kwnames);
}

template <size_t N, ArgPattern A>
static inline vectorcallfunc select_vectorcall(RetPattern R) {
    switch (R) {
        case RetPattern::NO_CHECK: return fast_vectorcall<N, A, RetPattern::NO_CHECK>;
        case RetPattern::NONE: return fast_vectorcall<N, A, RetPattern::NONE>;
        case RetPattern::SELF: return fast_vectorcall<N, A, RetPattern::SELF>;
        case RetPattern::SINGLE_TYPE: return fast_vectorcall<N, A, RetPattern::SINGLE_TYPE>;
        case RetPattern::UNION_TYPE: return fast_vectorcall<N, A, RetPattern::UNION_TYPE>;
        case RetPattern::GENERAL:
        default: return fast_vectorcall<N, A, RetPattern::GENERAL>;
    }
}

template <ArgPattern A>
static inline vectorcallfunc select_vectorcall_n(size_t n, RetPattern r) {
    switch (n) {
        case 0: return select_vectorcall<0, A>(r);
        case 1: return select_vectorcall<1, A>(r);
        case 2: return select_vectorcall<2, A>(r);
        case 3: return select_vectorcall<3, A>(r);
        case 4: return select_vectorcall<4, A>(r);
        case 5: return select_vectorcall<5, A>(r);
        case 6: return select_vectorcall<6, A>(r);
        case 7: return select_vectorcall<7, A>(r);
        case 8: return select_vectorcall<8, A>(r);
        default: return nullptr;
    }
}

static PyObject* fast_call_tp_call(PyObject* self, PyObject* args, PyObject* kwargs) {
    PyFastCallObject* fc = (PyFastCallObject*)self;
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
        PyObject* res = fc->vectorcall(self, stack.data(), nargs, kwnames);
        Py_DECREF(kwnames);
        return res;
    }
    return fc->vectorcall(self, fastargs, nargs, nullptr);
}

static void fast_call_dealloc(PyObject* self) {
    PyFastCallObject* fc = (PyFastCallObject*)self;
    Py_XDECREF(fc->self_enforcer);
    Py_XDECREF(fc->fn);
    Py_XDECREF(fc->check_fn);
    Py_XDECREF(fc->ret_exp);
    Py_XDECREF(fc->ret_str);

    for (size_t i = 0; i < 8; ++i) {
        fc->pos_checks[i].~FastTypeCheck();
    }
    fc->pos_params.~vector();
    fc->kwonly_params.~vector();
    fc->kw_to_param.~unordered_map();
    fc->varargs_info.~FastParamInfo();
    fc->varkw_info.~FastParamInfo();
    fc->ret_check.~FastTypeCheck();

    Py_TYPE(self)->tp_free(self);
}

static PyObject* fast_call_new(PyTypeObject* type, PyObject* args, PyObject* kwargs) {
    PyFastCallObject* self = (PyFastCallObject*)type->tp_alloc(type, 0);
    if (self) {
        self->vectorcall = fast_call_general_vectorcall;
        self->self_enforcer = nullptr;
        self->fn = nullptr;
        self->fn_vectorcall = nullptr;
        self->check_fn = nullptr;
        self->ret_exp = nullptr;
        self->ret_str = nullptr;
        self->ret_kind = RetCheckKind::NO_CHECK;
        self->ret_single_type = nullptr;
        self->ret_union_t0 = nullptr;
        self->ret_union_t1 = nullptr;
        self->ret_union_t2 = nullptr;
        self->num_pos = 0;
        self->all_pos_single_types = true;
        for (size_t i = 0; i < 8; ++i) {
            self->pos_kinds[i] = ParamCheckKind::PASS;
            self->pos_types[i] = nullptr;
            self->pos_types_extra[i] = nullptr;
            self->pos_types_extra2[i] = nullptr;
            self->pos_nodes[i] = nullptr;
            new (&self->pos_checks[i]) FastTypeCheck();
        }
        self->has_varargs = false;
        self->has_varkw = false;
        new (&self->pos_params) std::vector<FastParamInfo>();
        new (&self->kwonly_params) std::vector<FastParamInfo>();
        new (&self->kw_to_param) std::unordered_map<std::string, std::pair<bool, size_t>>();
        new (&self->varargs_info) FastParamInfo();
        new (&self->varkw_info) FastParamInfo();
        new (&self->ret_check) FastTypeCheck();
    }
    return (PyObject*)self;
}

static PyType_Slot fast_call_slots[] = {
    {Py_tp_new, (void*)fast_call_new},
    {Py_tp_call, (void*)fast_call_tp_call},
    {Py_tp_dealloc, (void*)fast_call_dealloc},
    {0, nullptr}
};

static PyType_Spec fast_call_type_spec = {
    "type_enforced.cpp.FastCall",
    sizeof(PyFastCallObject),
    0,
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_VECTORCALL | Py_TPFLAGS_BASETYPE,
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

static bool setup_fast_param(FastParamInfo& p, nb::handle name_handle, nb::handle spec_handle, nb::handle exp_handle, SampleStrategy strategy, double val) {
    if (name_handle.is_valid() && !name_handle.is_none()) {
        p.name_str = name_handle.ptr();
        Py_INCREF(p.name_str);
    }
    if (exp_handle.is_valid() && !exp_handle.is_none()) {
        p.exp = exp_handle.ptr();
        Py_INCREF(p.exp);
    }
    if (spec_handle.is_valid() && !spec_handle.is_none()) {
        auto node = build_node(spec_handle, strategy, val);
        if (!node) return false;
        p.type_check.init(std::move(node));
    }
    return true;
}

static bool setup_fast_call_internal(
    PyFastCallObject* obj,
    nb::handle self_enforcer,
    nb::handle fn,
    nb::handle pos_param_names,
    nb::handle pos_param_specs,
    nb::handle pos_param_exps,
    nb::handle ret_spec,
    nb::handle ret_exp,
    nb::handle check_fn,
    nb::handle sample_pct,
    bool has_varargs,
    nb::handle varargs_name,
    nb::handle varargs_spec,
    nb::handle varargs_exp,
    bool has_varkw,
    nb::handle varkw_name,
    nb::handle varkw_spec,
    nb::handle varkw_exp,
    bool ret_is_self,
    nb::handle kwonly_param_names,
    nb::handle kwonly_param_specs,
    nb::handle kwonly_param_exps
) {
    auto [strategy, val] = parse_strategy(sample_pct);

    Py_XDECREF(obj->self_enforcer);
    if (self_enforcer.is_valid() && self_enforcer.ptr() != (PyObject*)obj) {
        obj->self_enforcer = self_enforcer.ptr();
        Py_XINCREF(obj->self_enforcer);
    } else {
        obj->self_enforcer = nullptr;
    }

    Py_XDECREF(obj->fn);
    obj->fn = fn.ptr();
    Py_XINCREF(obj->fn);
    obj->fn_vectorcall = PyVectorcall_Function(obj->fn);

    Py_XDECREF(obj->check_fn);
    obj->check_fn = check_fn.ptr();
    Py_XINCREF(obj->check_fn);

    obj->pos_params.clear();
    obj->kwonly_params.clear();
    obj->kw_to_param.clear();
    obj->num_pos = 0;
    obj->all_pos_single_types = true;
    for (size_t i = 0; i < 8; ++i) {
        obj->pos_kinds[i] = ParamCheckKind::PASS;
        obj->pos_types[i] = nullptr;
        obj->pos_types_extra[i] = nullptr;
        obj->pos_types_extra2[i] = nullptr;
        obj->pos_nodes[i] = nullptr;
        obj->pos_checks[i] = FastTypeCheck();
    }
    obj->ret_kind = RetCheckKind::NO_CHECK;
    obj->ret_single_type = nullptr;
    obj->ret_union_t0 = nullptr;
    obj->ret_union_t1 = nullptr;
    obj->ret_union_t2 = nullptr;
    Py_XDECREF(obj->ret_exp);
    obj->ret_exp = nullptr;
    Py_XDECREF(obj->ret_str);
    obj->ret_str = nullptr;

    if (pos_param_names.is_valid() && !pos_param_names.is_none()) {
        auto names_seq = nb::borrow<nb::sequence>(pos_param_names);
        auto specs_seq = nb::borrow<nb::sequence>(pos_param_specs);
        auto exps_seq = nb::borrow<nb::sequence>(pos_param_exps);
        size_t n = nb::len(names_seq);

        for (size_t i = 0; i < n; ++i) {
            FastParamInfo p;
            if (!setup_fast_param(p, names_seq[i], specs_seq[i], exps_seq[i], strategy, val)) {
                return false;
            }
            const char* name_cstr = PyUnicode_AsUTF8(p.name_str);
            if (name_cstr) {
                obj->kw_to_param[std::string(name_cstr)] = {false, i};
            }
            if (i < 8) {
                classify_param_node(
                    p.type_check.validator,
                    strategy,
                    obj->pos_kinds[i],
                    obj->pos_types[i],
                    obj->pos_types_extra[i],
                    obj->pos_types_extra2[i],
                    obj->pos_nodes[i]
                );
                obj->pos_checks[i] = p.type_check;
            }
            obj->pos_params.push_back(std::move(p));
        }
    }

    if (kwonly_param_names.is_valid() && !kwonly_param_names.is_none()) {
        auto names_seq = nb::borrow<nb::sequence>(kwonly_param_names);
        auto specs_seq = nb::borrow<nb::sequence>(kwonly_param_specs);
        auto exps_seq = nb::borrow<nb::sequence>(kwonly_param_exps);
        size_t n = nb::len(names_seq);

        for (size_t i = 0; i < n; ++i) {
            FastParamInfo p;
            if (!setup_fast_param(p, names_seq[i], specs_seq[i], exps_seq[i], strategy, val)) {
                return false;
            }
            const char* name_cstr = PyUnicode_AsUTF8(p.name_str);
            if (name_cstr) {
                obj->kw_to_param[std::string(name_cstr)] = {true, i};
            }
            obj->kwonly_params.push_back(std::move(p));
        }
    }

    obj->has_varargs = has_varargs;
    if (has_varargs) {
        if (!setup_fast_param(obj->varargs_info, varargs_name, varargs_spec, varargs_exp, strategy, val)) {
            return false;
        }
    }

    obj->has_varkw = has_varkw;
    if (has_varkw) {
        if (!setup_fast_param(obj->varkw_info, varkw_name, varkw_spec, varkw_exp, strategy, val)) {
            return false;
        }
    }

    if (ret_is_self) {
        obj->ret_kind = RetCheckKind::SELF_RETURN;
        obj->ret_str = PyUnicode_FromString("return");
        if (ret_exp.is_valid() && !ret_exp.is_none()) {
            obj->ret_exp = ret_exp.ptr();
            Py_INCREF(obj->ret_exp);
        }
    } else if (ret_spec.is_valid() && !ret_spec.is_none()) {
        obj->ret_str = PyUnicode_FromString("return");
        if (ret_exp.is_valid() && !ret_exp.is_none()) {
            obj->ret_exp = ret_exp.ptr();
            Py_INCREF(obj->ret_exp);
        }

        if (nb::isinstance<nb::dict>(ret_spec) && nb::len(ret_spec) == 1) {
            auto ret_dict = nb::borrow<nb::dict>(ret_spec);
            for (auto item : ret_dict) {
                if (item.first.ptr() == (PyObject*)Py_TYPE(Py_None) && item.second.is_none()) {
                    obj->ret_kind = RetCheckKind::NONE_RETURN;
                }
            }
        }
        if (obj->ret_kind == RetCheckKind::NO_CHECK) {
            auto ret_node = build_node(ret_spec, strategy, val);
            if (!ret_node) {
                return false;
            }
            obj->ret_check.init(std::move(ret_node));
            obj->ret_kind = RetCheckKind::TYPE_CHECK;
        }
    }

    obj->ret_single_type = obj->ret_check.single_type;
    obj->ret_union_t0 = obj->ret_check.union_t0;
    obj->ret_union_t1 = obj->ret_check.union_t1;
    obj->ret_union_t2 = obj->ret_check.union_t2;
    obj->num_pos = obj->pos_params.size();

    RetPattern ret_pat = RetPattern::GENERAL;
    if (obj->ret_kind == RetCheckKind::NO_CHECK) {
        ret_pat = RetPattern::NO_CHECK;
    } else if (obj->ret_kind == RetCheckKind::NONE_RETURN) {
        ret_pat = RetPattern::NONE;
    } else if (obj->ret_kind == RetCheckKind::SELF_RETURN) {
        ret_pat = RetPattern::SELF;
    } else if (obj->ret_kind == RetCheckKind::TYPE_CHECK && obj->ret_single_type != nullptr) {
        ret_pat = RetPattern::SINGLE_TYPE;
    } else if (obj->ret_kind == RetCheckKind::TYPE_CHECK && obj->ret_check.union_t0 != nullptr) {
        ret_pat = RetPattern::UNION_TYPE;
    } else {
        ret_pat = RetPattern::GENERAL;
    }

    bool all_single_types = true;
    for (size_t i = 0; i < obj->num_pos; ++i) {
        if (obj->pos_kinds[i] != ParamCheckKind::SINGLE_TYPE && obj->pos_kinds[i] != ParamCheckKind::PASS) {
            all_single_types = false;
            break;
        }
    }
    obj->all_pos_single_types = all_single_types;

    obj->vectorcall = fast_call_general_vectorcall;
    if (!has_varargs && !has_varkw && obj->kwonly_params.empty() && obj->num_pos <= 8) {
        if (all_single_types) {
            obj->vectorcall = select_vectorcall_n<ArgPattern::SINGLE_TYPES>(obj->num_pos, ret_pat);
        } else if (obj->num_pos == 1) {
            switch (obj->pos_kinds[0]) {
                case ParamCheckKind::UNION2:
                    obj->vectorcall = select_vectorcall<1, ArgPattern::POS1_UNION2>(ret_pat);
                    break;
                case ParamCheckKind::LIST_SINGLE_ALL:
                    obj->vectorcall = select_vectorcall<1, ArgPattern::POS1_LIST_SINGLE_ALL>(ret_pat);
                    break;
                case ParamCheckKind::DICT_SINGLE_ALL:
                    obj->vectorcall = select_vectorcall<1, ArgPattern::POS1_DICT_SINGLE_ALL>(ret_pat);
                    break;
                case ParamCheckKind::SET_SINGLE_ALL:
                    obj->vectorcall = select_vectorcall<1, ArgPattern::POS1_SET_SINGLE_ALL>(ret_pat);
                    break;
                case ParamCheckKind::VAR_TUPLE_SINGLE_ALL:
                    obj->vectorcall = select_vectorcall<1, ArgPattern::POS1_VAR_TUPLE_SINGLE_ALL>(ret_pat);
                    break;
                case ParamCheckKind::FIXED_TUPLE2:
                    obj->vectorcall = select_vectorcall<1, ArgPattern::POS1_FIXED_TUPLE2>(ret_pat);
                    break;
                default:
                    obj->vectorcall = select_vectorcall<1, ArgPattern::POS1_FAST>(ret_pat);
                    break;
            }
        } else {
            obj->vectorcall = select_vectorcall_n<ArgPattern::FAST_PARAMS>(obj->num_pos, ret_pat);
        }
    }

    return true;
}

bool setup_fast_call(
    nb::handle self,
    nb::handle fn,
    nb::handle pos_param_names,
    nb::handle pos_param_specs,
    nb::handle pos_param_exps,
    nb::handle ret_spec,
    nb::handle ret_exp,
    nb::handle check_fn,
    nb::handle sample_pct,
    bool has_varargs,
    nb::handle varargs_name,
    nb::handle varargs_spec,
    nb::handle varargs_exp,
    bool has_varkw,
    nb::handle varkw_name,
    nb::handle varkw_spec,
    nb::handle varkw_exp,
    bool ret_is_self,
    nb::handle kwonly_param_names,
    nb::handle kwonly_param_specs,
    nb::handle kwonly_param_exps
) {
    if (!PyFastCall_Type || !PyObject_TypeCheck(self.ptr(), PyFastCall_Type)) return false;
    PyFastCallObject* obj = (PyFastCallObject*)self.ptr();
    return setup_fast_call_internal(
        obj, self, fn, pos_param_names, pos_param_specs, pos_param_exps,
        ret_spec, ret_exp, check_fn, sample_pct,
        has_varargs, varargs_name, varargs_spec, varargs_exp,
        has_varkw, varkw_name, varkw_spec, varkw_exp,
        ret_is_self, kwonly_param_names, kwonly_param_specs, kwonly_param_exps
    );
}

nb::object create_fast_call(
    nb::handle self_enforcer,
    nb::handle fn,
    nb::handle pos_param_names,
    nb::handle pos_param_specs,
    nb::handle pos_param_exps,
    nb::handle ret_spec,
    nb::handle ret_exp,
    nb::handle check_fn,
    nb::handle sample_pct,
    bool has_varargs,
    nb::handle varargs_name,
    nb::handle varargs_spec,
    nb::handle varargs_exp,
    bool has_varkw,
    nb::handle varkw_name,
    nb::handle varkw_spec,
    nb::handle varkw_exp,
    bool ret_is_self,
    nb::handle kwonly_param_names,
    nb::handle kwonly_param_specs,
    nb::handle kwonly_param_exps
) {
    if (!PyFastCall_Type) return nb::none();

    PyFastCallObject* obj = (PyFastCallObject*)fast_call_new(PyFastCall_Type, nullptr, nullptr);
    if (!obj) return nb::none();

    if (!setup_fast_call_internal(
        obj, self_enforcer, fn, pos_param_names, pos_param_specs, pos_param_exps,
        ret_spec, ret_exp, check_fn, sample_pct,
        has_varargs, varargs_name, varargs_spec, varargs_exp,
        has_varkw, varkw_name, varkw_spec, varkw_exp,
        ret_is_self, kwonly_param_names, kwonly_param_specs, kwonly_param_exps
    )) {
        Py_DECREF((PyObject*)obj);
        return nb::none();
    }

    return nb::steal(reinterpret_cast<PyObject*>(obj));
}

} // namespace type_enforced
