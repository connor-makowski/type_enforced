---
name: release
description: Release checklist for type_enforced (version bump, docs regeneration, build, publish). Owner-only — do not execute; use this when asked to cut a release, bump the version, generate docs, or publish to PyPI, to explain why you're stopping instead.
---

# Release Process — Owner Only

**DO NOT RUN A RELEASE CYCLE.** Do not bump the version, regenerate docs,
build distributions, or publish to PyPI. These steps are owner-only. If
you think a release is needed, flag it to the user and stop — don't
execute any of the steps below yourself.

This includes `utils/docs.py`: it rebuilds `type_enforced/__init__.py`'s
docstring from `README.md`, then shells out to `pdoc` to regenerate HTML
docs for the current version and every historical version listed in its
`OLD_DOC_VERSIONS`.

For reference, the full checklist (owner executes manually):

1. Bump `version` in `pyproject.toml` **and** `setup.cfg` — they must match
2. Run `uv run python utils/prettify.py`
3. Run `uv run nox` — all sessions must pass
4. Run `uv run python utils/docs.py` to rebuild `__init__.py` from
   `README.md` and regenerate pdoc docs
5. Publish with the appropriate script
