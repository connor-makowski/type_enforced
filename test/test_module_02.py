import pytest
from test_module_02_utils import pkg_root
from test_module_02_utils.pkg_root import subpkg


def test_module_02():
    # pkg_root has enforcement applied
    assert pkg_root.root_fn(2) == 20
    with pytest.raises(TypeError, match="Type mismatch"):
        pkg_root.root_fn("2")

    # subpkg was recursively enforced because submodules=True by default
    assert subpkg.subpkg_fn(2) == 200
    with pytest.raises(TypeError, match="Type mismatch"):
        subpkg.subpkg_fn("2")
