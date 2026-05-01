# Release Checklist

CaseLaw Guard v0.1 is intentionally narrow: citation existence verification only. Do not add proposition-support checks, good-law analysis, or new jurisdiction coverage as part of the release process.

## Local Validation

Run from a clean checkout:

```bash
.venv/bin/python -m pytest -q
rm -rf dist
.venv/bin/python -m build
.venv/bin/python -m twine check dist/*
```

Smoke test the built wheel in fresh virtual environments:

```bash
set -euo pipefail

WHEEL=$(.venv/bin/python - <<'PY'
from pathlib import Path

print(next(Path("dist").glob("caselaw_guard-*.whl")))
PY
)

.venv/bin/python -m venv /tmp/caselaw-guard-base
/tmp/caselaw-guard-base/bin/python -m pip install --upgrade pip
/tmp/caselaw-guard-base/bin/python -m pip install "$WHEEL"
/tmp/caselaw-guard-base/bin/caselaw-guard --help
/tmp/caselaw-guard-base/bin/python - <<'PY'
from caselaw_guard.verifier import verify_text

report = verify_text("No citations here.")
assert report.pass_ is True
assert report.results == []
PY

.venv/bin/python -m venv /tmp/caselaw-guard-mcp
/tmp/caselaw-guard-mcp/bin/python -m pip install --upgrade pip
/tmp/caselaw-guard-mcp/bin/python -m pip install "${WHEEL}[mcp]"
/tmp/caselaw-guard-mcp/bin/python - <<'PY'
from importlib.metadata import entry_points

scripts = {entry_point.name for entry_point in entry_points(group="console_scripts")}
assert "caselaw-guard" in scripts
assert "caselaw-guard-mcp" in scripts

from caselaw_guard.mcp_server import create_mcp_server

server = create_mcp_server()
assert type(server).__name__ == "FastMCP"
PY
```

## GitHub Release

After validation:

```bash
git status --short
git tag v0.1.0
git push origin v0.1.0
```

Create the GitHub release from tag `v0.1.0` using the `0.1.0` changelog entries.

## PyPI Publishing

Publishing is intentionally manual until the first release path is proven. Prefer PyPI Trusted Publishing with a dedicated GitHub environment named `pypi`, `id-token: write`, and `pypa/gh-action-pypi-publish@release/v1`.

Do not publish from an unclean checkout or with failing local validation.
