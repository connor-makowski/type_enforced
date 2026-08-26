#include "validators.hpp"

namespace type_enforced {

static inline bool check_item_type(PyObject* item, PyTypeObject* exp_type) {
    PyTypeObject* item_type = Py_TYPE(item);
    if (item_type == exp_type) {
        return true;
    }
    return PyObject_TypeCheck(item, exp_type) != 0;
}

static inline bool check_item_union(PyObject* item, const nb::tuple& exp_types, size_t num_types) {
    PyTypeObject* item_type = Py_TYPE(item);
    for (size_t j = 0; j < num_types; ++j) {
        PyTypeObject* exp_type = (PyTypeObject*)exp_types[j].ptr();
        if (item_type == exp_type || PyObject_TypeCheck(item, exp_type)) {
            return true;
        }
    }
    return false;
}

// ----------------- LIST -----------------

bool validate_list_single(nb::handle obj, nb::handle exp_type_handle) {
    PyObject* ptr = obj.ptr();
    if (!PyList_Check(ptr)) return false;
    PyObject** items = PySequence_Fast_ITEMS(ptr);
    Py_ssize_t size = PyList_GET_SIZE(ptr);
    PyTypeObject* exp_type = (PyTypeObject*)exp_type_handle.ptr();

    for (Py_ssize_t i = 0; i < size; ++i) {
        if (!check_item_type(items[i], exp_type)) return false;
    }
    return true;
}

bool validate_list_union(nb::handle obj, nb::tuple exp_types) {
    PyObject* ptr = obj.ptr();
    if (!PyList_Check(ptr)) return false;
    PyObject** items = PySequence_Fast_ITEMS(ptr);
    Py_ssize_t size = PyList_GET_SIZE(ptr);
    size_t num_types = exp_types.size();

    for (Py_ssize_t i = 0; i < size; ++i) {
        if (!check_item_union(items[i], exp_types, num_types)) return false;
    }
    return true;
}

bool validate_list_first(nb::handle obj, nb::handle exp_type_handle) {
    PyObject* ptr = obj.ptr();
    if (!PyList_Check(ptr)) return false;
    Py_ssize_t size = PyList_GET_SIZE(ptr);
    if (size == 0) return true;
    PyObject** items = PySequence_Fast_ITEMS(ptr);
    return check_item_type(items[0], (PyTypeObject*)exp_type_handle.ptr());
}

bool validate_list_first_union(nb::handle obj, nb::tuple exp_types) {
    PyObject* ptr = obj.ptr();
    if (!PyList_Check(ptr)) return false;
    Py_ssize_t size = PyList_GET_SIZE(ptr);
    if (size == 0) return true;
    PyObject** items = PySequence_Fast_ITEMS(ptr);
    return check_item_union(items[0], exp_types, exp_types.size());
}

bool validate_list_last(nb::handle obj, nb::handle exp_type_handle) {
    PyObject* ptr = obj.ptr();
    if (!PyList_Check(ptr)) return false;
    Py_ssize_t size = PyList_GET_SIZE(ptr);
    if (size == 0) return true;
    PyObject** items = PySequence_Fast_ITEMS(ptr);
    return check_item_type(items[size - 1], (PyTypeObject*)exp_type_handle.ptr());
}

bool validate_list_last_union(nb::handle obj, nb::tuple exp_types) {
    PyObject* ptr = obj.ptr();
    if (!PyList_Check(ptr)) return false;
    Py_ssize_t size = PyList_GET_SIZE(ptr);
    if (size == 0) return true;
    PyObject** items = PySequence_Fast_ITEMS(ptr);
    return check_item_union(items[size - 1], exp_types, exp_types.size());
}

bool validate_list_sample(nb::handle obj, nb::handle exp_type_handle, size_t count) {
    PyObject* ptr = obj.ptr();
    if (!PyList_Check(ptr)) return false;
    Py_ssize_t size = PyList_GET_SIZE(ptr);
    if (size == 0) return true;
    PyObject** items = PySequence_Fast_ITEMS(ptr);
    PyTypeObject* exp = (PyTypeObject*)exp_type_handle.ptr();

    if ((size_t)size <= count || (size_t)size <= 3) {
        for (Py_ssize_t i = 0; i < size; ++i) {
            if (!check_item_type(items[i], exp)) return false;
        }
        return true;
    }
    if (!check_item_type(items[0], exp) || !check_item_type(items[size - 1], exp)) {
        return false;
    }
    size_t mid_count = (count > 2) ? count - 2 : 1;
    Py_ssize_t step = (size - 1) / (mid_count + 1);
    if (step < 1) step = 1;
    for (Py_ssize_t i = step; i < size - 1; i += step) {
        if (!check_item_type(items[i], exp)) return false;
    }
    return true;
}

bool validate_list_sample_union(nb::handle obj, nb::tuple exp_types, size_t count) {
    PyObject* ptr = obj.ptr();
    if (!PyList_Check(ptr)) return false;
    Py_ssize_t size = PyList_GET_SIZE(ptr);
    if (size == 0) return true;
    PyObject** items = PySequence_Fast_ITEMS(ptr);
    size_t num_types = exp_types.size();

    if ((size_t)size <= count || (size_t)size <= 3) {
        for (Py_ssize_t i = 0; i < size; ++i) {
            if (!check_item_union(items[i], exp_types, num_types)) return false;
        }
        return true;
    }
    if (!check_item_union(items[0], exp_types, num_types) || !check_item_union(items[size - 1], exp_types, num_types)) {
        return false;
    }
    size_t mid_count = (count > 2) ? count - 2 : 1;
    Py_ssize_t step = (size - 1) / (mid_count + 1);
    if (step < 1) step = 1;
    for (Py_ssize_t i = step; i < size - 1; i += step) {
        if (!check_item_union(items[i], exp_types, num_types)) return false;
    }
    return true;
}

// ----------------- SET -----------------

bool validate_set_single(nb::handle obj, nb::handle exp_type_handle) {
    PyObject* ptr = obj.ptr();
    if (!PySet_Check(ptr) && !PyFrozenSet_Check(ptr)) return false;
    PyTypeObject* exp_type = (PyTypeObject*)exp_type_handle.ptr();
    Py_ssize_t pos = 0;
    PyObject* key;
    Py_hash_t hash;

    while (_PySet_NextEntry(ptr, &pos, &key, &hash)) {
        if (!check_item_type(key, exp_type)) return false;
    }
    return true;
}

bool validate_set_union(nb::handle obj, nb::tuple exp_types) {
    PyObject* ptr = obj.ptr();
    if (!PySet_Check(ptr) && !PyFrozenSet_Check(ptr)) return false;
    size_t num_types = exp_types.size();
    Py_ssize_t pos = 0;
    PyObject* key;
    Py_hash_t hash;

    while (_PySet_NextEntry(ptr, &pos, &key, &hash)) {
        if (!check_item_union(key, exp_types, num_types)) return false;
    }
    return true;
}

bool validate_set_sample(nb::handle obj, nb::handle exp_type_handle, size_t count) {
    PyObject* ptr = obj.ptr();
    if (!PySet_Check(ptr) && !PyFrozenSet_Check(ptr)) return false;
    PyTypeObject* exp_type = (PyTypeObject*)exp_type_handle.ptr();
    Py_ssize_t pos = 0;
    PyObject* key;
    Py_hash_t hash;
    size_t checked = 0;

    while (_PySet_NextEntry(ptr, &pos, &key, &hash)) {
        if (!check_item_type(key, exp_type)) return false;
        if (++checked >= count) break;
    }
    return true;
}

bool validate_set_sample_union(nb::handle obj, nb::tuple exp_types, size_t count) {
    PyObject* ptr = obj.ptr();
    if (!PySet_Check(ptr) && !PyFrozenSet_Check(ptr)) return false;
    size_t num_types = exp_types.size();
    Py_ssize_t pos = 0;
    PyObject* key;
    Py_hash_t hash;
    size_t checked = 0;

    while (_PySet_NextEntry(ptr, &pos, &key, &hash)) {
        if (!check_item_union(key, exp_types, num_types)) return false;
        if (++checked >= count) break;
    }
    return true;
}

// ----------------- TUPLE -----------------

bool validate_tuple_single(nb::handle obj, nb::handle exp_type_handle) {
    PyObject* ptr = obj.ptr();
    if (!PyTuple_Check(ptr)) return false;
    Py_ssize_t size = PyTuple_GET_SIZE(ptr);
    PyTypeObject* exp_type = (PyTypeObject*)exp_type_handle.ptr();

    for (Py_ssize_t i = 0; i < size; ++i) {
        PyObject* item = PyTuple_GET_ITEM(ptr, i);
        if (!check_item_type(item, exp_type)) return false;
    }
    return true;
}

bool validate_tuple_union(nb::handle obj, nb::tuple exp_types) {
    PyObject* ptr = obj.ptr();
    if (!PyTuple_Check(ptr)) return false;
    Py_ssize_t size = PyTuple_GET_SIZE(ptr);
    size_t num_types = exp_types.size();

    for (Py_ssize_t i = 0; i < size; ++i) {
        PyObject* item = PyTuple_GET_ITEM(ptr, i);
        if (!check_item_union(item, exp_types, num_types)) return false;
    }
    return true;
}

bool validate_tuple_first(nb::handle obj, nb::handle exp_type_handle) {
    PyObject* ptr = obj.ptr();
    if (!PyTuple_Check(ptr)) return false;
    Py_ssize_t size = PyTuple_GET_SIZE(ptr);
    if (size == 0) return true;
    return check_item_type(PyTuple_GET_ITEM(ptr, 0), (PyTypeObject*)exp_type_handle.ptr());
}

bool validate_tuple_first_union(nb::handle obj, nb::tuple exp_types) {
    PyObject* ptr = obj.ptr();
    if (!PyTuple_Check(ptr)) return false;
    Py_ssize_t size = PyTuple_GET_SIZE(ptr);
    if (size == 0) return true;
    return check_item_union(PyTuple_GET_ITEM(ptr, 0), exp_types, exp_types.size());
}

bool validate_tuple_last(nb::handle obj, nb::handle exp_type_handle) {
    PyObject* ptr = obj.ptr();
    if (!PyTuple_Check(ptr)) return false;
    Py_ssize_t size = PyTuple_GET_SIZE(ptr);
    if (size == 0) return true;
    return check_item_type(PyTuple_GET_ITEM(ptr, size - 1), (PyTypeObject*)exp_type_handle.ptr());
}

bool validate_tuple_last_union(nb::handle obj, nb::tuple exp_types) {
    PyObject* ptr = obj.ptr();
    if (!PyTuple_Check(ptr)) return false;
    Py_ssize_t size = PyTuple_GET_SIZE(ptr);
    if (size == 0) return true;
    return check_item_union(PyTuple_GET_ITEM(ptr, size - 1), exp_types, exp_types.size());
}

bool validate_tuple_sample(nb::handle obj, nb::handle exp_type_handle, size_t count) {
    PyObject* ptr = obj.ptr();
    if (!PyTuple_Check(ptr)) return false;
    Py_ssize_t size = PyTuple_GET_SIZE(ptr);
    if (size == 0) return true;
    PyTypeObject* exp = (PyTypeObject*)exp_type_handle.ptr();

    if ((size_t)size <= count || (size_t)size <= 3) {
        for (Py_ssize_t i = 0; i < size; ++i) {
            if (!check_item_type(PyTuple_GET_ITEM(ptr, i), exp)) return false;
        }
        return true;
    }
    if (!check_item_type(PyTuple_GET_ITEM(ptr, 0), exp) || !check_item_type(PyTuple_GET_ITEM(ptr, size - 1), exp)) {
        return false;
    }
    size_t mid_count = (count > 2) ? count - 2 : 1;
    Py_ssize_t step = (size - 1) / (mid_count + 1);
    if (step < 1) step = 1;
    for (Py_ssize_t i = step; i < size - 1; i += step) {
        if (!check_item_type(PyTuple_GET_ITEM(ptr, i), exp)) return false;
    }
    return true;
}

bool validate_tuple_sample_union(nb::handle obj, nb::tuple exp_types, size_t count) {
    PyObject* ptr = obj.ptr();
    if (!PyTuple_Check(ptr)) return false;
    Py_ssize_t size = PyTuple_GET_SIZE(ptr);
    if (size == 0) return true;
    size_t num_types = exp_types.size();

    if ((size_t)size <= count || (size_t)size <= 3) {
        for (Py_ssize_t i = 0; i < size; ++i) {
            if (!check_item_union(PyTuple_GET_ITEM(ptr, i), exp_types, num_types)) return false;
        }
        return true;
    }
    if (!check_item_union(PyTuple_GET_ITEM(ptr, 0), exp_types, num_types) || !check_item_union(PyTuple_GET_ITEM(ptr, size - 1), exp_types, num_types)) {
        return false;
    }
    size_t mid_count = (count > 2) ? count - 2 : 1;
    Py_ssize_t step = (size - 1) / (mid_count + 1);
    if (step < 1) step = 1;
    for (Py_ssize_t i = step; i < size - 1; i += step) {
        if (!check_item_union(PyTuple_GET_ITEM(ptr, i), exp_types, num_types)) return false;
    }
    return true;
}

bool validate_tuple_fixed(nb::handle obj, nb::tuple exp_types) {
    PyObject* ptr = obj.ptr();
    if (!PyTuple_Check(ptr)) return false;
    Py_ssize_t size = PyTuple_GET_SIZE(ptr);
    if ((size_t)size != exp_types.size()) return false;

    for (Py_ssize_t i = 0; i < size; ++i) {
        PyObject* item = PyTuple_GET_ITEM(ptr, i);
        PyTypeObject* exp_type = (PyTypeObject*)exp_types[i].ptr();
        if (!check_item_type(item, exp_type)) return false;
    }
    return true;
}

// ----------------- DICT -----------------

bool validate_dict_single(nb::handle obj, nb::handle key_type_handle, nb::handle val_type_handle) {
    PyObject* ptr = obj.ptr();
    if (!PyDict_Check(ptr)) return false;
    PyTypeObject* k_type = (PyTypeObject*)key_type_handle.ptr();
    PyTypeObject* v_type = (PyTypeObject*)val_type_handle.ptr();
    Py_ssize_t pos = 0;
    PyObject* key;
    PyObject* value;

    while (PyDict_Next(ptr, &pos, &key, &value)) {
        if (!check_item_type(key, k_type) || !check_item_type(value, v_type)) return false;
    }
    return true;
}

bool validate_dict_unions(nb::handle obj, nb::tuple key_types, nb::tuple val_types) {
    PyObject* ptr = obj.ptr();
    if (!PyDict_Check(ptr)) return false;
    size_t num_k_types = key_types.size();
    size_t num_v_types = val_types.size();
    Py_ssize_t pos = 0;
    PyObject* key;
    PyObject* value;

    while (PyDict_Next(ptr, &pos, &key, &value)) {
        if (!check_item_union(key, key_types, num_k_types) || !check_item_union(value, val_types, num_v_types)) return false;
    }
    return true;
}

bool validate_dict_first(nb::handle obj, nb::handle key_type_handle, nb::handle val_type_handle) {
    PyObject* ptr = obj.ptr();
    if (!PyDict_Check(ptr)) return false;
    Py_ssize_t pos = 0;
    PyObject* key;
    PyObject* value;

    if (PyDict_Next(ptr, &pos, &key, &value)) {
        if (!check_item_type(key, (PyTypeObject*)key_type_handle.ptr()) ||
            !check_item_type(value, (PyTypeObject*)val_type_handle.ptr())) {
            return false;
        }
    }
    return true;
}

bool validate_dict_first_unions(nb::handle obj, nb::tuple key_types, nb::tuple val_types) {
    PyObject* ptr = obj.ptr();
    if (!PyDict_Check(ptr)) return false;
    Py_ssize_t pos = 0;
    PyObject* key;
    PyObject* value;

    if (PyDict_Next(ptr, &pos, &key, &value)) {
        if (!check_item_union(key, key_types, key_types.size()) ||
            !check_item_union(value, val_types, val_types.size())) {
            return false;
        }
    }
    return true;
}

bool validate_dict_last(nb::handle obj, nb::handle key_type_handle, nb::handle val_type_handle) {
    PyObject* ptr = obj.ptr();
    if (!PyDict_Check(ptr)) return false;
    PyTypeObject* k_type = (PyTypeObject*)key_type_handle.ptr();
    PyTypeObject* v_type = (PyTypeObject*)val_type_handle.ptr();
    Py_ssize_t pos = 0;
    PyObject* key;
    PyObject* value;
    PyObject* last_k = nullptr;
    PyObject* last_v = nullptr;

    while (PyDict_Next(ptr, &pos, &key, &value)) {
        last_k = key;
        last_v = value;
    }
    if (last_k != nullptr) {
        if (!check_item_type(last_k, k_type) || !check_item_type(last_v, v_type)) return false;
    }
    return true;
}

bool validate_dict_last_unions(nb::handle obj, nb::tuple key_types, nb::tuple val_types) {
    PyObject* ptr = obj.ptr();
    if (!PyDict_Check(ptr)) return false;
    Py_ssize_t pos = 0;
    PyObject* key;
    PyObject* value;
    PyObject* last_k = nullptr;
    PyObject* last_v = nullptr;

    while (PyDict_Next(ptr, &pos, &key, &value)) {
        last_k = key;
        last_v = value;
    }
    if (last_k != nullptr) {
        if (!check_item_union(last_k, key_types, key_types.size()) ||
            !check_item_union(last_v, val_types, val_types.size())) {
            return false;
        }
    }
    return true;
}

bool validate_dict_sample(nb::handle obj, nb::handle key_type_handle, nb::handle val_type_handle, size_t count) {
    PyObject* ptr = obj.ptr();
    if (!PyDict_Check(ptr)) return false;
    PyTypeObject* k_type = (PyTypeObject*)key_type_handle.ptr();
    PyTypeObject* v_type = (PyTypeObject*)val_type_handle.ptr();
    Py_ssize_t pos = 0;
    PyObject* key;
    PyObject* value;
    size_t checked = 0;

    while (PyDict_Next(ptr, &pos, &key, &value)) {
        if (!check_item_type(key, k_type) || !check_item_type(value, v_type)) return false;
        if (++checked >= count) break;
    }
    return true;
}

bool validate_dict_sample_unions(nb::handle obj, nb::tuple key_types, nb::tuple val_types, size_t count) {
    PyObject* ptr = obj.ptr();
    if (!PyDict_Check(ptr)) return false;
    size_t num_k_types = key_types.size();
    size_t num_v_types = val_types.size();
    Py_ssize_t pos = 0;
    PyObject* key;
    PyObject* value;
    size_t checked = 0;

    while (PyDict_Next(ptr, &pos, &key, &value)) {
        if (!check_item_union(key, key_types, num_k_types) || !check_item_union(value, val_types, num_v_types)) return false;
        if (++checked >= count) break;
    }
    return true;
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
    size_t tup_len = exp_types.size();

    for (Py_ssize_t i = 0; i < size; ++i) {
        PyObject* tup = items[i];
        if (!PyTuple_Check(tup) || (size_t)PyTuple_GET_SIZE(tup) != tup_len) return false;
        for (size_t j = 0; j < tup_len; ++j) {
            PyObject* item = PyTuple_GET_ITEM(tup, j);
            if (!check_item_type(item, (PyTypeObject*)exp_types[j].ptr())) return false;
        }
    }
    return true;
}

} // namespace type_enforced
