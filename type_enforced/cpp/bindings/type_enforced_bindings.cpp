#include <nanobind/nanobind.h>
#include "../src/validators.hpp"

namespace nb = nanobind;

NB_MODULE(cpp, m) {
    m.doc() = "C++ accelerated type validators for type_enforced";

    // 100% list
    m.def("validate_list_single", &type_enforced::validate_list_single,
          nb::arg("obj"), nb::arg("exp_type"));
    m.def("validate_list_union", &type_enforced::validate_list_union,
          nb::arg("obj"), nb::arg("exp_types"));

    // Sampled list
    m.def("validate_list_first", &type_enforced::validate_list_first,
          nb::arg("obj"), nb::arg("exp_type"));
    m.def("validate_list_first_union", &type_enforced::validate_list_first_union,
          nb::arg("obj"), nb::arg("exp_types"));
    m.def("validate_list_last", &type_enforced::validate_list_last,
          nb::arg("obj"), nb::arg("exp_type"));
    m.def("validate_list_last_union", &type_enforced::validate_list_last_union,
          nb::arg("obj"), nb::arg("exp_types"));
    m.def("validate_list_bookend", &type_enforced::validate_list_bookend,
          nb::arg("obj"), nb::arg("exp_type"));
    m.def("validate_list_bookend_union", &type_enforced::validate_list_bookend_union,
          nb::arg("obj"), nb::arg("exp_types"));
    m.def("validate_list_bookend_plus", &type_enforced::validate_list_bookend_plus,
          nb::arg("obj"), nb::arg("exp_type"));
    m.def("validate_list_bookend_plus_union", &type_enforced::validate_list_bookend_plus_union,
          nb::arg("obj"), nb::arg("exp_types"));
    m.def("validate_list_sample", &type_enforced::validate_list_sample,
          nb::arg("obj"), nb::arg("exp_type"), nb::arg("count"));
    m.def("validate_list_sample_union", &type_enforced::validate_list_sample_union,
          nb::arg("obj"), nb::arg("exp_types"), nb::arg("count"));

    // Set
    m.def("validate_set_single", &type_enforced::validate_set_single,
          nb::arg("obj"), nb::arg("exp_type"));
    m.def("validate_set_union", &type_enforced::validate_set_union,
          nb::arg("obj"), nb::arg("exp_types"));
    m.def("validate_set_sample", &type_enforced::validate_set_sample,
          nb::arg("obj"), nb::arg("exp_type"), nb::arg("count"));
    m.def("validate_set_sample_union", &type_enforced::validate_set_sample_union,
          nb::arg("obj"), nb::arg("exp_types"), nb::arg("count"));

    // Tuple
    m.def("validate_tuple_single", &type_enforced::validate_tuple_single,
          nb::arg("obj"), nb::arg("exp_type"));
    m.def("validate_tuple_union", &type_enforced::validate_tuple_union,
          nb::arg("obj"), nb::arg("exp_types"));
    m.def("validate_tuple_first", &type_enforced::validate_tuple_first,
          nb::arg("obj"), nb::arg("exp_type"));
    m.def("validate_tuple_first_union", &type_enforced::validate_tuple_first_union,
          nb::arg("obj"), nb::arg("exp_types"));
    m.def("validate_tuple_last", &type_enforced::validate_tuple_last,
          nb::arg("obj"), nb::arg("exp_type"));
    m.def("validate_tuple_last_union", &type_enforced::validate_tuple_last_union,
          nb::arg("obj"), nb::arg("exp_types"));
    m.def("validate_tuple_bookend", &type_enforced::validate_tuple_bookend,
          nb::arg("obj"), nb::arg("exp_type"));
    m.def("validate_tuple_bookend_union", &type_enforced::validate_tuple_bookend_union,
          nb::arg("obj"), nb::arg("exp_types"));
    m.def("validate_tuple_bookend_plus", &type_enforced::validate_tuple_bookend_plus,
          nb::arg("obj"), nb::arg("exp_type"));
    m.def("validate_tuple_bookend_plus_union", &type_enforced::validate_tuple_bookend_plus_union,
          nb::arg("obj"), nb::arg("exp_types"));
    m.def("validate_tuple_sample", &type_enforced::validate_tuple_sample,
          nb::arg("obj"), nb::arg("exp_type"), nb::arg("count"));
    m.def("validate_tuple_sample_union", &type_enforced::validate_tuple_sample_union,
          nb::arg("obj"), nb::arg("exp_types"), nb::arg("count"));
    m.def("validate_tuple_fixed", &type_enforced::validate_tuple_fixed,
          nb::arg("obj"), nb::arg("exp_types"));

    // Dict
    m.def("validate_dict_single", &type_enforced::validate_dict_single,
          nb::arg("obj"), nb::arg("key_type"), nb::arg("val_type"));
    m.def("validate_dict_unions", &type_enforced::validate_dict_unions,
          nb::arg("obj"), nb::arg("key_types"), nb::arg("val_types"));
    m.def("validate_dict_sample", &type_enforced::validate_dict_sample,
          nb::arg("obj"), nb::arg("key_type"), nb::arg("val_type"), nb::arg("count"));
    m.def("validate_dict_sample_unions", &type_enforced::validate_dict_sample_unions,
          nb::arg("obj"), nb::arg("key_types"), nb::arg("val_types"), nb::arg("count"));

    // Nested
    m.def("validate_list_list", &type_enforced::validate_list_list,
          nb::arg("obj"), nb::arg("exp_type"));
    m.def("validate_list_dict", &type_enforced::validate_list_dict,
          nb::arg("obj"), nb::arg("key_type"), nb::arg("val_type"));
    m.def("validate_dict_list", &type_enforced::validate_dict_list,
          nb::arg("obj"), nb::arg("key_type"), nb::arg("val_type"));
    m.def("validate_list_tuple_fixed", &type_enforced::validate_list_tuple_fixed,
          nb::arg("obj"), nb::arg("exp_types"));
}
