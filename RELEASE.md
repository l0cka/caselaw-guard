# Release checklist

CaseLaw Guard 0.3.0 remains a citation-existence verifier. It adds reproducible
Australian coverage evidence, MCP Python SDK v2 support and explicit fetching of
versioned Australian indexes. It does not add proposition-support checks,
good-law analysis or a hosted citation API.

Publishing the Python package and publishing an Australian index are separate
approval gates. GitHub's “Latest” marker belongs to the package release and
must not be moved by an index release. OpenBench archival is outside this
release's scope.

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
python -m build --outdir dist-0.3.0
python -m twine check dist-0.3.0/*
```

The package workflow performs the authoritative content check. Before
publishing, confirm that:

- the wheel contains `caselaw_guard`, not `openbench`;
- its metadata has no `openbench` dependency and the MCP extra requires
  `mcp>=2,<3`;
- the source distribution contains `LICENSE-DATA`, `DATA_SOURCES.md` and the
  attributed fixture; and
- a clean wheel installation fetches an explicit index version and verifies
  `[2014] HCA 9 at [10]` offline.

## 3. Publish CaseLaw Guard 0.3.0

After the validation and package workflows pass, present the exact tag, commit,
release notes and PyPI effect for approval. Only after approval, create and push
`v0.3.0`, run the manual `publish.yml` workflow for that exact tag, and mark
the GitHub package release as “Latest”. PyPI Trusted Publishing uses the `pypi`
GitHub environment.

Verify a clean installation from PyPI:

```bash
python3 -m venv /tmp/caselaw-guard-pypi-0.3.0
/tmp/caselaw-guard-pypi-0.3.0/bin/python -m pip install "caselaw-guard[mcp]==0.3.0"
/tmp/caselaw-guard-pypi-0.3.0/bin/caselaw-guard --help
```

## 4. Publish an Australian index

Run `publish-australian-index.yml` manually only after its pinned benchmark
passes against the newly built index and matches the approved baseline. This is
a separate explicit approval from package publication. Use an immutable source
dataset revision, an index version and an index-specific release tag. The
workflow builds and schema-validates the JSON, produces the verification report,
compresses it with Zstandard and publishes the JSON, `.zst`, report and SHA-256
files as release assets.

Check the release metadata records:

- the exact dataset revision, or `unknown` if one was not supplied;
- `CC-BY-4.0` and the canonical Isaacus attribution;
- the index and builder versions; and
- a matching SHA-256 digest; and
- the exact benchmark dataset revision and approved baseline comparison.

## 5. Rollback and scope controls

Failed index fetches must preserve the existing output. Users can roll back by
pointing `CASELAW_GUARD_AU_INDEX` at a previously verified index file. Do not
rewrite or delete a published package or mutate a verified historical index;
publish a new version with its own evidence instead.

Do not add reported-citation aliases, proposition-support checks, good-law
analysis, new jurisdictions, hosted services, telemetry or automatic index
updates as part of this release.
