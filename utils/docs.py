import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).parent.parent
type_enforced = root / "type_enforced" / "__init__.py"

VERSION = "2.11.0"
OLD_DOC_VERSIONS = ["2.10.1", "2.9.0", "2.8.1", "2.7.0", "2.6.0", "2.5.0", "2.4.0", "2.3.0", "2.2.3", "2.1.0", "2.0.0", "1.10.2", "1.9.0", "1.8.1", "1.7.0", "1.6.0", "1.5.0", "1.4.0", "1.3.0", "1.2.0", "1.1.1", "0.0.16"]

env = {
    **os.environ,
    "version_options": " ".join([VERSION] + OLD_DOC_VERSIONS),
}


def generate_docs(version):
    out_dir = str(root / "docs" / version)
    template_dir = str(root / "doc_template")

    if version != "./" and version != VERSION:
        # Use an isolated environment per old version so their (older)
        # dependencies don't clobber the current venv.
        tarball = str(root / "dist" / f"type_enforced-{version}.tar.gz")
        subprocess.run(
            [
                "uv", "run", "--isolated",
                "--with", tarball,
                "--with", "pdoc",
                "pdoc", "-o", out_dir, "-t", template_dir, "type_enforced",
            ],
            check=True,
            env=env,
            cwd=str(root),
        )
    else:
        subprocess.run(
            [sys.executable, "-m", "pdoc", "-o", out_dir, "-t", template_dir, "type_enforced"],
            check=True,
            env=env,
        )


# Build __init__.py from README
readme = (root / "README.md").read_text()
type_enforced.write_text(f'"""\n{readme}\n"""\n\nfrom .enforcer import Enforcer, FastEnforcer, FunctionMethodEnforcer\nfrom .module import ModuleEnforcer, FastModuleEnforcer\nfrom .utils import has_cpp\n')

generate_docs("./")
generate_docs(VERSION)
for version in OLD_DOC_VERSIONS:
    generate_docs(version)
