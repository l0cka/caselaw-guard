# Release checklist

CaseLaw Guard 0.2.0 consolidates OpenBench's Australian citation-index code into
one package. It does not add proposition-support checks, good-law analysis or a
hosted citation API.

Publishing the Python package, publishing an Australian index and archiving the
OpenBench repository are three separate approval gates.

## 1. Validate the source tree

Run these checks from a clean checkout on Python 3.11, 3.12 and 3.13:

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

Validate the attributed fixture against the canonical schema:

```bash
python - <<'PY'
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

schema = json.loads(Path("schemas/australia-index.schema.json").read_text())
fixture = json.loads(Path("examples/australia_index.sample.json").read_text())
Draft202012Validator(schema, format_checker=FormatChecker()).validate(fixture)
PY
```

## 2. Build and inspect the distributions

Build into a new, empty output directory:

```bash
python -m build --outdir dist-0.2.0
python -m twine check dist-0.2.0/*
```

The package workflow performs the authoritative content check. Before
publishing, confirm that:

- the wheel contains `caselaw_guard`, not `openbench`;
- its metadata has no `openbench` dependency;
- the source distribution contains `LICENSE-DATA`, `DATA_SOURCES.md` and the
  attributed fixture; and
- a clean wheel installation verifies `[1992] HCA 23 at [10]` offline.

## 3. Publish CaseLaw Guard 0.2.0

After the validation and package workflows pass, create and push `v0.2.0`, then
run the manual `publish.yml` workflow for that exact tag. PyPI Trusted
Publishing uses the `pypi` GitHub environment.

Verify a clean installation from PyPI:

```bash
python3 -m venv /tmp/caselaw-guard-pypi-0.2.0
/tmp/caselaw-guard-pypi-0.2.0/bin/python -m pip install "caselaw-guard[mcp]==0.2.0"
/tmp/caselaw-guard-pypi-0.2.0/bin/caselaw-guard --help
```

## 4. Publish an Australian index

Run `publish-australian-index.yml` manually with an immutable source dataset
revision, an index version and an index-specific release tag. The workflow
builds and schema-validates the JSON, compresses it with Zstandard and publishes
the JSON, `.zst` and SHA-256 files as release assets.

Check the release metadata records:

- the exact dataset revision, or `unknown` if one was not supplied;
- `CC-BY-4.0` and the canonical Isaacus attribution;
- the index and builder versions; and
- a matching SHA-256 digest.

## 5. OpenBench archive gate

Do not archive OpenBench until the published 0.2.0 wheel and published index
pass clean-install and offline-lookup checks. Archiving also requires separate
approval and the migration notice described in the approved consolidation
specification.
