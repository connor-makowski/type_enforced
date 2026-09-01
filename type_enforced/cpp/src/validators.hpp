#pragma once

#include <nanobind/nanobind.h>

namespace nb = nanobind;

namespace type_enforced {

// List validation
bool validate_list_single(nb::handle obj, nb::handle exp_type);
bool validate_list_union(nb::handle obj, nb::tuple exp_types);
bool validate_list_first(nb::handle obj, nb::handle exp_type);
bool validate_list_first_union(nb::handle obj, nb::tuple exp_types);
bool validate_list_last(nb::handle obj, nb::handle exp_type);
bool validate_list_last_union(nb::handle obj, nb::tuple exp_types);
bool validate_list_bookend(nb::handle obj, nb::handle exp_type);
bool validate_list_bookend_union(nb::handle obj, nb::tuple exp_types);
bool validate_list_bookend_plus(nb::handle obj, nb::handle exp_type);
bool validate_list_bookend_plus_union(nb::handle obj, nb::tuple exp_types);
bool validate_list_sample(nb::handle obj, nb::handle exp_type, size_t count);
bool validate_list_sample_union(nb::handle obj, nb::tuple exp_types, size_t count);

// Set validation
bool validate_set_single(nb::handle obj, nb::handle exp_type);
bool validate_set_union(nb::handle obj, nb::tuple exp_types);
bool validate_set_sample(nb::handle obj, nb::handle exp_type, size_t count);
bool validate_set_sample_union(nb::handle obj, nb::tuple exp_types, size_t count);

// Tuple validation (variable length)
bool validate_tuple_single(nb::handle obj, nb::handle exp_type);
bool validate_tuple_union(nb::handle obj, nb::tuple exp_types);
bool validate_tuple_first(nb::handle obj, nb::handle exp_type);
bool validate_tuple_first_union(nb::handle obj, nb::tuple exp_types);
bool validate_tuple_last(nb::handle obj, nb::handle exp_type);
bool validate_tuple_last_union(nb::handle obj, nb::tuple exp_types);
bool validate_tuple_bookend(nb::handle obj, nb::handle exp_type);
bool validate_tuple_bookend_union(nb::handle obj, nb::tuple exp_types);
bool validate_tuple_bookend_plus(nb::handle obj, nb::handle exp_type);
bool validate_tuple_bookend_plus_union(nb::handle obj, nb::tuple exp_types);
bool validate_tuple_sample(nb::handle obj, nb::handle exp_type, size_t count);
bool validate_tuple_sample_union(nb::handle obj, nb::tuple exp_types, size_t count);

// Fixed-length tuple validation
bool validate_tuple_fixed(nb::handle obj, nb::tuple exp_types);

// Dict validation
bool validate_dict_single(nb::handle obj, nb::handle key_type, nb::handle val_type);
bool validate_dict_unions(nb::handle obj, nb::tuple key_types, nb::tuple val_types);
bool validate_dict_sample(nb::handle obj, nb::handle key_type, nb::handle val_type, size_t count);
bool validate_dict_sample_unions(nb::handle obj, nb::tuple key_types, nb::tuple val_types, size_t count);

// Nested structures
bool validate_list_list(nb::handle obj, nb::handle exp_type);
bool validate_list_dict(nb::handle obj, nb::handle key_type, nb::handle val_type);
bool validate_dict_list(nb::handle obj, nb::handle key_type, nb::handle val_type);
bool validate_list_tuple_fixed(nb::handle obj, nb::tuple exp_types);

} // namespace type_enforced
