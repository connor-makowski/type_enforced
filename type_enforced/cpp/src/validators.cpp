#include "validators.hpp"
#include <vector>
#include <cstdlib>

namespace type_enforced {

template <size_t N = 16>
struct UnpackedTypes {
    PyTypeObject* buf[N];
    std::vector<PyTypeObject*> dynamic_buf;
    PyTypeObject* const* types;
    size_t count;

    inline explicit UnpackedTypes(const nb::tuple& tup) {
        count = tup.size();
        if (count <= N) {
            types = buf;
            PyObject* tup_ptr = tup.ptr();
            for (size_t i = 0; i < count; ++i) {
                buf[i] = (PyTypeObject*)PyTuple_GET_ITEM(tup_ptr, i);
            }
        } else {
            dynamic_buf.resize(count);
            PyObject* tup_ptr = tup.ptr();
            for (size_t i = 0; i < count; ++i) {
                dynamic_buf[i] = (PyTypeObject*)PyTuple_GET_ITEM(tup_ptr, i);
            }
            types = dynamic_buf.data();
        }
    }
};

static inline bool check_item_type(PyObject* item, PyTypeObject* exp_type) {
    PyTypeObject* item_type = Py_TYPE(item);
    if (item_type == exp_type) {
        return true;
    }
    return PyObject_TypeCheck(item, exp_type) != 0;
}

static inline bool check_item_union(PyObject* item, PyTypeObject* const* exp_types, size_t num_types) {
    PyTypeObject* item_type = Py_TYPE(item);
    for (size_t j = 0; j < num_types; ++j) {
        PyTypeObject* exp_type = exp_types[j];
        if (item_type == exp_type || PyObject_TypeCheck(item, exp_type)) {
            return true;
        }
    }
    return false;
}

struct SingleTypeChecker {
    PyTypeObject* exp_type;
    inline explicit SingleTypeChecker(PyTypeObject* t) : exp_type(t) {}
    inline bool operator()(PyObject* item) const {
        return check_item_type(item, exp_type);
    }
};

struct UnionTypeChecker {
    PyTypeObject* const* types;
    size_t count;
    inline explicit UnionTypeChecker(const UnpackedTypes<>& u) : types(u.types), count(u.count) {}
    inline bool operator()(PyObject* item) const {
        return check_item_union(item, types, count);
    }
};

// ----------------- LIST -----------------

template <typename Checker>
inline bool validate_list_all_impl(PyObject* ptr, Checker&& checker) {
    if (!PyList_Check(ptr)) return false;
    PyObject** items = PySequence_Fast_ITEMS(ptr);
    Py_ssize_t size = PyList_GET_SIZE(ptr);
    for (Py_ssize_t i = 0; i < size; ++i) {
        if (!checker(items[i])) return false;
    }
    return true;
}

template <typename Checker>
inline bool validate_list_first_impl(PyObject* ptr, Checker&& checker) {
    if (!PyList_Check(ptr)) return false;
    Py_ssize_t size = PyList_GET_SIZE(ptr);
    if (size == 0) return true;
    PyObject** items = PySequence_Fast_ITEMS(ptr);
    return checker(items[0]);
}

template <typename Checker>
inline bool validate_list_last_impl(PyObject* ptr, Checker&& checker) {
    if (!PyList_Check(ptr)) return false;
    Py_ssize_t size = PyList_GET_SIZE(ptr);
    if (size == 0) return true;
    PyObject** items = PySequence_Fast_ITEMS(ptr);
    return checker(items[size - 1]);
}

template <typename Checker>
inline bool validate_list_bookend_impl(PyObject* ptr, Checker&& checker) {
    if (!PyList_Check(ptr)) return false;
    Py_ssize_t size = PyList_GET_SIZE(ptr);
    if (size == 0) return true;
    PyObject** items = PySequence_Fast_ITEMS(ptr);
    if (!checker(items[0])) return false;
    if (size > 1 && !checker(items[size - 1])) return false;
    return true;
}

template <typename Checker>
inline bool validate_list_bookend_plus_impl(PyObject* ptr, Checker&& checker) {
    if (!PyList_Check(ptr)) return false;
    Py_ssize_t size = PyList_GET_SIZE(ptr);
    if (size == 0) return true;
    PyObject** items = PySequence_Fast_ITEMS(ptr);
    if (!checker(items[0])) return false;
    if (size > 1 && !checker(items[size - 1])) return false;
    if (size > 2) {
        Py_ssize_t mid = 1 + (std::rand() % (size - 2));
        if (!checker(items[mid])) return false;
    }
    return true;
}

template <typename Checker>
inline bool validate_list_sample_impl(PyObject* ptr, Checker&& checker, size_t count) {
    if (!PyList_Check(ptr)) return false;
    Py_ssize_t size = PyList_GET_SIZE(ptr);
    if (size == 0) return true;
    PyObject** items = PySequence_Fast_ITEMS(ptr);
    if (count >= (size_t)size) {
        for (Py_ssize_t i = 0; i < size; ++i) {
            if (!checker(items[i])) return false;
        }
        return true;
    }
    if (!checker(items[0])) return false;
    if (count > 1 && !checker(items[size - 1])) return false;
    if (count > 2 && size > 2) {
        Py_ssize_t step = (size - 1) / (count - 1);
        if (step < 1) step = 1;
        for (Py_ssize_t i = step; i < size - 1; i += step) {
            if (!checker(items[i])) return false;
        }
    }
    return true;
}

bool validate_list_single(nb::handle obj, nb::handle exp_type) {
    return validate_list_all_impl(obj.ptr(), SingleTypeChecker((PyTypeObject*)exp_type.ptr()));
}

bool validate_list_union(nb::handle obj, nb::tuple exp_types) {
    return validate_list_all_impl(obj.ptr(), UnionTypeChecker(UnpackedTypes<>(exp_types)));
}

bool validate_list_first(nb::handle obj, nb::handle exp_type) {
    return validate_list_first_impl(obj.ptr(), SingleTypeChecker((PyTypeObject*)exp_type.ptr()));
}

bool validate_list_first_union(nb::handle obj, nb::tuple exp_types) {
    return validate_list_first_impl(obj.ptr(), UnionTypeChecker(UnpackedTypes<>(exp_types)));
}

bool validate_list_last(nb::handle obj, nb::handle exp_type) {
    return validate_list_last_impl(obj.ptr(), SingleTypeChecker((PyTypeObject*)exp_type.ptr()));
}

bool validate_list_last_union(nb::handle obj, nb::tuple exp_types) {
    return validate_list_last_impl(obj.ptr(), UnionTypeChecker(UnpackedTypes<>(exp_types)));
}

bool validate_list_bookend(nb::handle obj, nb::handle exp_type) {
    return validate_list_bookend_impl(obj.ptr(), SingleTypeChecker((PyTypeObject*)exp_type.ptr()));
}

bool validate_list_bookend_union(nb::handle obj, nb::tuple exp_types) {
    return validate_list_bookend_impl(obj.ptr(), UnionTypeChecker(UnpackedTypes<>(exp_types)));
}

bool validate_list_bookend_plus(nb::handle obj, nb::handle exp_type) {
    return validate_list_bookend_plus_impl(obj.ptr(), SingleTypeChecker((PyTypeObject*)exp_type.ptr()));
}

bool validate_list_bookend_plus_union(nb::handle obj, nb::tuple exp_types) {
    return validate_list_bookend_plus_impl(obj.ptr(), UnionTypeChecker(UnpackedTypes<>(exp_types)));
}

bool validate_list_sample(nb::handle obj, nb::handle exp_type, size_t count) {
    return validate_list_sample_impl(obj.ptr(), SingleTypeChecker((PyTypeObject*)exp_type.ptr()), count);
}

bool validate_list_sample_union(nb::handle obj, nb::tuple exp_types, size_t count) {
    return validate_list_sample_impl(obj.ptr(), UnionTypeChecker(UnpackedTypes<>(exp_types)), count);
}

// ----------------- SET -----------------

template <typename Checker>
inline bool validate_set_all_impl(PyObject* ptr, Checker&& checker) {
    if (!PySet_Check(ptr) && !PyFrozenSet_Check(ptr)) return false;
    PyObject* it = PyObject_GetIter(ptr);
    if (!it) return false;
    PyObject* key;
    while ((key = PyIter_Next(it)) != nullptr) {
        bool ok = checker(key);
        Py_DECREF(key);
        if (!ok) {
            Py_DECREF(it);
            return false;
        }
    }
    Py_DECREF(it);
    return true;
}

template <typename Checker>
inline bool validate_set_sample_impl(PyObject* ptr, Checker&& checker, size_t count) {
    if (!PySet_Check(ptr) && !PyFrozenSet_Check(ptr)) return false;
    PyObject* it = PyObject_GetIter(ptr);
    if (!it) return false;
    PyObject* key;
    size_t checked = 0;
    while ((key = PyIter_Next(it)) != nullptr) {
        bool ok = checker(key);
        Py_DECREF(key);
        if (!ok) {
            Py_DECREF(it);
            return false;
        }
        if (++checked >= count) break;
    }
    Py_DECREF(it);
    return true;
}

bool validate_set_single(nb::handle obj, nb::handle exp_type) {
    return validate_set_all_impl(obj.ptr(), SingleTypeChecker((PyTypeObject*)exp_type.ptr()));
}

bool validate_set_union(nb::handle obj, nb::tuple exp_types) {
    return validate_set_all_impl(obj.ptr(), UnionTypeChecker(UnpackedTypes<>(exp_types)));
}

bool validate_set_sample(nb::handle obj, nb::handle exp_type, size_t count) {
    return validate_set_sample_impl(obj.ptr(), SingleTypeChecker((PyTypeObject*)exp_type.ptr()), count);
}

bool validate_set_sample_union(nb::handle obj, nb::tuple exp_types, size_t count) {
    return validate_set_sample_impl(obj.ptr(), UnionTypeChecker(UnpackedTypes<>(exp_types)), count);
}

// ----------------- TUPLE -----------------

template <typename Checker>
inline bool validate_tuple_all_impl(PyObject* ptr, Checker&& checker) {
    if (!PyTuple_Check(ptr)) return false;
    Py_ssize_t size = PyTuple_GET_SIZE(ptr);
    for (Py_ssize_t i = 0; i < size; ++i) {
        if (!checker(PyTuple_GET_ITEM(ptr, i))) return false;
    }
    return true;
}

template <typename Checker>
inline bool validate_tuple_first_impl(PyObject* ptr, Checker&& checker) {
    if (!PyTuple_Check(ptr)) return false;
    Py_ssize_t size = PyTuple_GET_SIZE(ptr);
    if (size == 0) return true;
    return checker(PyTuple_GET_ITEM(ptr, 0));
}

template <typename Checker>
inline bool validate_tuple_last_impl(PyObject* ptr, Checker&& checker) {
    if (!PyTuple_Check(ptr)) return false;
    Py_ssize_t size = PyTuple_GET_SIZE(ptr);
    if (size == 0) return true;
    return checker(PyTuple_GET_ITEM(ptr, size - 1));
}

template <typename Checker>
inline bool validate_tuple_bookend_impl(PyObject* ptr, Checker&& checker) {
    if (!PyTuple_Check(ptr)) return false;
    Py_ssize_t size = PyTuple_GET_SIZE(ptr);
    if (size == 0) return true;
    if (!checker(PyTuple_GET_ITEM(ptr, 0))) return false;
    if (size > 1 && !checker(PyTuple_GET_ITEM(ptr, size - 1))) return false;
    return true;
}

template <typename Checker>
inline bool validate_tuple_bookend_plus_impl(PyObject* ptr, Checker&& checker) {
    if (!PyTuple_Check(ptr)) return false;
    Py_ssize_t size = PyTuple_GET_SIZE(ptr);
    if (size == 0) return true;
    if (!checker(PyTuple_GET_ITEM(ptr, 0))) return false;
    if (size > 1 && !checker(PyTuple_GET_ITEM(ptr, size - 1))) return false;
    if (size > 2) {
        Py_ssize_t mid = 1 + (std::rand() % (size - 2));
        if (!checker(PyTuple_GET_ITEM(ptr, mid))) return false;
    }
    return true;
}

template <typename Checker>
inline bool validate_tuple_sample_impl(PyObject* ptr, Checker&& checker, size_t count) {
    if (!PyTuple_Check(ptr)) return false;
    Py_ssize_t size = PyTuple_GET_SIZE(ptr);
    if (size == 0) return true;
    if (count >= (size_t)size) {
        for (Py_ssize_t i = 0; i < size; ++i) {
            if (!checker(PyTuple_GET_ITEM(ptr, i))) return false;
        }
        return true;
    }
    if (!checker(PyTuple_GET_ITEM(ptr, 0))) return false;
    if (count > 1 && !checker(PyTuple_GET_ITEM(ptr, size - 1))) return false;
    if (count > 2 && size > 2) {
        Py_ssize_t step = (size - 1) / (count - 1);
        if (step < 1) step = 1;
        for (Py_ssize_t i = step; i < size - 1; i += step) {
            if (!checker(PyTuple_GET_ITEM(ptr, i))) return false;
        }
    }
    return true;
}

bool validate_tuple_single(nb::handle obj, nb::handle exp_type) {
    return validate_tuple_all_impl(obj.ptr(), SingleTypeChecker((PyTypeObject*)exp_type.ptr()));
}

bool validate_tuple_union(nb::handle obj, nb::tuple exp_types) {
    return validate_tuple_all_impl(obj.ptr(), UnionTypeChecker(UnpackedTypes<>(exp_types)));
}

bool validate_tuple_first(nb::handle obj, nb::handle exp_type) {
    return validate_tuple_first_impl(obj.ptr(), SingleTypeChecker((PyTypeObject*)exp_type.ptr()));
}

bool validate_tuple_first_union(nb::handle obj, nb::tuple exp_types) {
    return validate_tuple_first_impl(obj.ptr(), UnionTypeChecker(UnpackedTypes<>(exp_types)));
}

bool validate_tuple_last(nb::handle obj, nb::handle exp_type) {
    return validate_tuple_last_impl(obj.ptr(), SingleTypeChecker((PyTypeObject*)exp_type.ptr()));
}

bool validate_tuple_last_union(nb::handle obj, nb::tuple exp_types) {
    return validate_tuple_last_impl(obj.ptr(), UnionTypeChecker(UnpackedTypes<>(exp_types)));
}

bool validate_tuple_bookend(nb::handle obj, nb::handle exp_type) {
    return validate_tuple_bookend_impl(obj.ptr(), SingleTypeChecker((PyTypeObject*)exp_type.ptr()));
}

bool validate_tuple_bookend_union(nb::handle obj, nb::tuple exp_types) {
    return validate_tuple_bookend_impl(obj.ptr(), UnionTypeChecker(UnpackedTypes<>(exp_types)));
}

bool validate_tuple_bookend_plus(nb::handle obj, nb::handle exp_type) {
    return validate_tuple_bookend_plus_impl(obj.ptr(), SingleTypeChecker((PyTypeObject*)exp_type.ptr()));
}

bool validate_tuple_bookend_plus_union(nb::handle obj, nb::tuple exp_types) {
    return validate_tuple_bookend_plus_impl(obj.ptr(), UnionTypeChecker(UnpackedTypes<>(exp_types)));
}

bool validate_tuple_sample(nb::handle obj, nb::handle exp_type, size_t count) {
    return validate_tuple_sample_impl(obj.ptr(), SingleTypeChecker((PyTypeObject*)exp_type.ptr()), count);
}

bool validate_tuple_sample_union(nb::handle obj, nb::tuple exp_types, size_t count) {
    return validate_tuple_sample_impl(obj.ptr(), UnionTypeChecker(UnpackedTypes<>(exp_types)), count);
}

bool validate_tuple_fixed(nb::handle obj, nb::tuple exp_types) {
    PyObject* ptr = obj.ptr();
    if (!PyTuple_Check(ptr)) return false;
    UnpackedTypes<> types(exp_types);
    if ((size_t)PyTuple_GET_SIZE(ptr) != types.count) return false;
    for (size_t i = 0; i < types.count; ++i) {
        if (!check_item_type(PyTuple_GET_ITEM(ptr, i), types.types[i])) return false;
    }
    return true;
}

// ----------------- DICT -----------------

template <typename KeyChecker, typename ValChecker>
inline bool validate_dict_all_impl(PyObject* ptr, KeyChecker&& kc, ValChecker&& vc) {
    if (!PyDict_Check(ptr)) return false;
    Py_ssize_t pos = 0;
    PyObject* key;
    PyObject* value;
    while (PyDict_Next(ptr, &pos, &key, &value)) {
        if (!kc(key) || !vc(value)) return false;
    }
    return true;
}

template <typename KeyChecker, typename ValChecker>
inline bool validate_dict_sample_impl(PyObject* ptr, KeyChecker&& kc, ValChecker&& vc, size_t count) {
    if (!PyDict_Check(ptr)) return false;
    Py_ssize_t pos = 0;
    PyObject* key;
    PyObject* value;
    size_t checked = 0;
    while (PyDict_Next(ptr, &pos, &key, &value)) {
        if (!kc(key) || !vc(value)) return false;
        if (++checked >= count) break;
    }
    return true;
}

bool validate_dict_single(nb::handle obj, nb::handle key_type, nb::handle val_type) {
    return validate_dict_all_impl(
        obj.ptr(),
        SingleTypeChecker((PyTypeObject*)key_type.ptr()),
        SingleTypeChecker((PyTypeObject*)val_type.ptr())
    );
}

bool validate_dict_unions(nb::handle obj, nb::tuple key_types, nb::tuple val_types) {
    return validate_dict_all_impl(
        obj.ptr(),
        UnionTypeChecker(UnpackedTypes<>(key_types)),
        UnionTypeChecker(UnpackedTypes<>(val_types))
    );
}

bool validate_dict_sample(nb::handle obj, nb::handle key_type, nb::handle val_type, size_t count) {
    return validate_dict_sample_impl(
        obj.ptr(),
        SingleTypeChecker((PyTypeObject*)key_type.ptr()),
        SingleTypeChecker((PyTypeObject*)val_type.ptr()),
        count
    );
}

bool validate_dict_sample_unions(nb::handle obj, nb::tuple key_types, nb::tuple val_types, size_t count) {
    return validate_dict_sample_impl(
        obj.ptr(),
        UnionTypeChecker(UnpackedTypes<>(key_types)),
        UnionTypeChecker(UnpackedTypes<>(val_types)),
        count
    );
}

// ----------------- NESTED -----------------

bool validate_list_list(nb::handle obj, nb::handle exp_type_handle) {
    PyObject* ptr = obj.ptr();
    if (!PyList_Check(ptr)) return false;
    PyObject** items = PySequence_Fast_ITEMS(ptr);
    Py_ssize_t size = PyList_GET_SIZE(ptr);
    PyTypeObject* exp = (PyTypeObject*)exp_type_handle.ptr();

    for (Py_ssize_t i = 0; i < size; ++i) {
        PyObject* sub_list = items[i];
        if (!PyList_Check(sub_list)) return false;
        PyObject** sub_items = PySequence_Fast_ITEMS(sub_list);
        Py_ssize_t sub_size = PyList_GET_SIZE(sub_list);
        for (Py_ssize_t j = 0; j < sub_size; ++j) {
            if (!check_item_type(sub_items[j], exp)) return false;
        }
    }
    return true;
}

bool validate_list_dict(nb::handle obj, nb::handle key_type_handle, nb::handle val_type_handle) {
    PyObject* ptr = obj.ptr();
    if (!PyList_Check(ptr)) return false;
    PyObject** items = PySequence_Fast_ITEMS(ptr);
    Py_ssize_t size = PyList_GET_SIZE(ptr);
    PyTypeObject* k_type = (PyTypeObject*)key_type_handle.ptr();
    PyTypeObject* v_type = (PyTypeObject*)val_type_handle.ptr();

    for (Py_ssize_t i = 0; i < size; ++i) {
        PyObject* dict_obj = items[i];
        if (!PyDict_Check(dict_obj)) return false;
        Py_ssize_t pos = 0;
        PyObject* key;
        PyObject* value;
        while (PyDict_Next(dict_obj, &pos, &key, &value)) {
            if (!check_item_type(key, k_type) || !check_item_type(value, v_type)) return false;
        }
    }
    return true;
}

bool validate_dict_list(nb::handle obj, nb::handle key_type_handle, nb::handle val_type_handle) {
    PyObject* ptr = obj.ptr();
    if (!PyDict_Check(ptr)) return false;
    PyTypeObject* k_type = (PyTypeObject*)key_type_handle.ptr();
    PyTypeObject* v_type = (PyTypeObject*)val_type_handle.ptr();
    Py_ssize_t pos = 0;
    PyObject* key;
    PyObject* value;

    while (PyDict_Next(ptr, &pos, &key, &value)) {
        if (!check_item_type(key, k_type)) return false;
        if (!PyList_Check(value)) return false;
        PyObject** sub_items = PySequence_Fast_ITEMS(value);
        Py_ssize_t sub_size = PyList_GET_SIZE(value);
        for (Py_ssize_t j = 0; j < sub_size; ++j) {
            if (!check_item_type(sub_items[j], v_type)) return false;
        }
    }
    return true;
}

bool validate_list_tuple_fixed(nb::handle obj, nb::tuple exp_types) {
    PyObject* ptr = obj.ptr();
    if (!PyList_Check(ptr)) return false;
    PyObject** items = PySequence_Fast_ITEMS(ptr);
    Py_ssize_t size = PyList_GET_SIZE(ptr);
    UnpackedTypes<> types(exp_types);

    for (Py_ssize_t i = 0; i < size; ++i) {
        PyObject* tup = items[i];
        if (!PyTuple_Check(tup) || (size_t)PyTuple_GET_SIZE(tup) != types.count) return false;
        for (size_t j = 0; j < types.count; ++j) {
            PyObject* item = PyTuple_GET_ITEM(tup, j);
            if (!check_item_type(item, types.types[j])) return false;
        }
    }
    return true;
}

} // namespace type_enforced
