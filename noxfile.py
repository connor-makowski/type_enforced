import nox

nox.options.default_venv_backend = "uv"


@nox.session(python=["3.11", "3.12", "3.13", "3.14", "pypy3.11"])
def tests(session):
    # 1. Test compiled C++ extension build
    session.run_install("uv", "sync", "--extra", "dev", external=True)
    session.run("pytest", env={"TYPE_ENFORCED_REQUIRE_CPP": "1"})

    # 2. Test pure Python fallback build
    session.run_install(
        "uv",
        "sync",
        "--extra",
        "dev",
        "--reinstall-package",
        "type-enforced",
        external=True,
        env={"SKBUILD_CMAKE_ARGS": "-DSKIP_CPP_BUILD=ON"},
    )
    session.run("pytest", env={"TYPE_ENFORCED_SKIP_CPP": "1"})