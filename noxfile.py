import nox

nox.options.default_venv_backend = "uv"


@nox.session(python=["3.11", "3.12", "3.13", "3.14"])
def tests(session):
    session.run_install(
        "uv",
        "sync",
        "--extra",
        "dev",
        external=True,
    )
    session.run("pytest")