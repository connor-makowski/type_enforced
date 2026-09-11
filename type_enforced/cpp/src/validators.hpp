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
    nb::handle param_names,
    nb::handle param_specs,
    nb::handle param_exps,
    nb::handle ret_spec,
    nb::handle ret_exp,
    nb::handle check_fn,
    nb::handle sample_pct
);

} // namespace type_enforced
