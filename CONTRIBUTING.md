# Contributing to openbench

Thanks for your interest. openbench is small and intentionally focused.

## Dev setup

Requires `uv` and Python 3.12+.

```bash
git clone https://github.com/l0cka/openbench
cd openbench
uv sync --extra dev
```

Run the test suite:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -q
```

## What we accept in v1

- Bug reports and fixes for citation parsing or index loading.
- Improvements to the fixture index (additional leading cases, with sources).
- Better docs.
- New court codes for `src/openbench/courts.py` (with sources).

## What we don't accept yet

Anything in the "Deferred" list of `docs/superpowers/specs/2026-05-01-openbench-design.md` (reported-citation aliasing, case-name search, SQLite, hosted deployment, MCP server, Python client, etc.). Open an issue first.

## Commit style

Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`. Keep commits small and focused.

## Pull requests

- Add or update tests for any behaviour change.
- Run the full check suite (above).
- Reference the relevant spec section in your PR description.
