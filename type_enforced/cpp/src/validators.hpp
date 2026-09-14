#pragma once

#include <nanobind/nanobind.h>
#include <memory>
#include <vector>
#include <utility>

namespace nb = nanobind;

namespace type_enforced {

enum class SampleStrategy : uint8_t {
    ALL,
    FIRST,
    LAST,
    BOOKEND,
    BOOKEND_PLUS,
    RANDOM_ONE,
    PERCENT,
    COUNT,
    LOG
};

enum class NodeKind : uint8_t {
    SUBCLASS_TYPE,
    UNION_TYPE,
    COMPLEX_UNION,
    LIST,
    DICT,
    SET,
    VAR_TUPLE,
    FIXED_TUPLE
};

struct TypeValidatorNode {
    NodeKind kind;
    explicit TypeValidatorNode(NodeKind k) : kind(k) {}
    virtual ~TypeValidatorNode() = default;
    virtual bool validate(PyObject* obj) const noexcept = 0;
};

class Validator {
public:
    std::shared_ptr<TypeValidatorNode> root;
    Validator() = default;
    explicit Validator(std::shared_ptr<TypeValidatorNode> r) : root(std::move(r)) {}

    bool validate(nb::handle obj) const noexcept {
        return root ? root->validate(obj.ptr()) : true;
    }
};

void init_validator_type(PyObject* m);
void init_fast_call_type(PyObject* m);
nb::object create_validator(nb::handle spec, nb::handle sample_pct);
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
    bool has_varargs = false,
    nb::handle varargs_name = nb::none(),
    nb::handle varargs_spec = nb::none(),
    nb::handle varargs_exp = nb::none(),
    bool has_varkw = false,
    nb::handle varkw_name = nb::none(),
    nb::handle varkw_spec = nb::none(),
    nb::handle varkw_exp = nb::none(),
    bool ret_is_self = false,
    nb::handle kwonly_param_names = nb::none(),
    nb::handle kwonly_param_specs = nb::none(),
    nb::handle kwonly_param_exps = nb::none()
);

} // namespace type_enforced
