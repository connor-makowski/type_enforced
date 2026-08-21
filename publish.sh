uv run python -m build
uv run python -m twine upload dist/* --skip-existing
