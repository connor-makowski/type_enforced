import subprocess
import sys
from pathlib import Path

root = Path(__file__).parent.parent

subprocess.run(
    [
        sys.executable, "-m", "autoflake",
        "--in-place",
        "--remove-all-unused-imports",
        "--ignore-init-module-imports",
        "-r",
        str(root / "type_enforced"),
    ],
    check=True,
)
subprocess.run(
    [sys.executable, "-m", "black", "--config", str(root / "pyproject.toml"), str(root / "type_enforced")],
    check=True,
)
subprocess.run(
    [sys.executable, "-m", "black", "--config", str(root / "pyproject.toml"), str(root / "test")],
    check=True,
)
