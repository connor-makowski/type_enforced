uv run python -m build --sdist
uv run python -m twine upload dist/* --skip-existing