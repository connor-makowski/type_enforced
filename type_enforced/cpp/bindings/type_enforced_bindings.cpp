#include <nanobind/nanobind.h>
#include "../src/validators.hpp"

namespace nb = nanobind;

NB_MODULE(cpp, m) {
    m.doc() = "C++ accelerated type validators for type_enforced";

    // Generic Validator class & factory
    type_enforced::init_validator_type(m.ptr());
    type_enforced::init_fast_call_type(m.ptr());

    m.def("create_validator", &type_enforced::create_validator,
          nb::arg("spec"), nb::arg("sample_pct") = nb::none());

    m.def("create_fast_call", &type_enforced::create_fast_call,
          nb::arg("self_enforcer"), nb::arg("fn"), nb::arg("param_names"),
          nb::arg("param_specs"), nb::arg("param_exps"),
          nb::arg("ret_spec").none() = nb::none(),
          nb::arg("ret_exp").none() = nb::none(),
          nb::arg("check_fn"),
          nb::arg("sample_pct").none() = nb::none());
}

