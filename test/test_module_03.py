import pytest
from test_module_03_utils import pkg_root
from test_module_03_utils.pkg_root import subpkg


def test_module_03():
    # pkg_root has enforcement applied
    assert pkg_root.root_fn(2) == 20
    with pytest.raises(TypeError, match="Type mismatch"):
        pkg_root.root_fn("2")

    # subpkg was NOT enforced because submodules=False
    assert subpkg.subpkg_fn("2") == "2" * 100
