# CaseLaw Guard 0.3.0 implementation plan

**Date:** 2 August 2026

**Status:** Proposed for approval

**Theme:** trust and usability

**Estimate:** 4 to 6 engineering days

## Goal

Release CaseLaw Guard 0.3.0 with measurable Australian citation coverage,
MCP Python SDK v2 support and safe installation of versioned Australian
indexes.

Version 0.3.0 remains a citation-existence verifier. It does not assess whether
a case supports a proposition or remains good law.

## Success definition

A new user can complete this flow in less than 5 minutes:

```bash
python3 -m pip install "caselaw-guard[mcp]==0.3.0"
caselaw-guard au-index fetch 2026-08-01 --output australia-index.json
printf '[2014] HCA 9 at [10]\n' \
  | caselaw-guard verify - --no-courtlistener --au-index australia-index.json
caselaw-guard-mcp
```

The flow must:

1. install from the public wheel;
2. verify the downloaded index before making it available;
3. return a verified citation with complete provenance;
4. expose the same result through MCP; and
5. link to reproducible coverage evidence for the installed index.

## Baseline

| Item | Current state |
| --- | --- |
| Python package | `caselaw-guard==0.2.0` is public on PyPI |
| Package release | `v0.2.0` is public but is not GitHub's current “Latest” release |
| Australian index | `australian-index-2026-08-01`, 183,804 entries |
| Source revision | `ef45e3fec41a960919a31149eee6dab9aa39f725` |
| Benchmark | manual AusLaw extraction and verification harness |
| MCP | `mcp>=1,<2`; SDK v1 is in maintenance mode |
| Dependency work | Dependabot PR #15 fails because SDK v2 removed `mcp.server.fastmcp` |
| Index installation | manual download, checksum check, decompression and configuration |
| Public feedback | zero open user issues as at 2 August 2026 |

## Sources

- [CaseLaw Guard 0.2.0 release](https://github.com/l0cka/caselaw-guard/releases/tag/v0.2.0)
- [Australian index 2026-08-01](https://github.com/l0cka/caselaw-guard/releases/tag/australian-index-2026-08-01)
- [AusLaw Citation Benchmark](https://huggingface.co/datasets/auslawbench/AusLaw-Citation-Benchmark)
- [MCP Python SDK v2 release](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0)
- [MCP Python SDK v2 migration guide](https://py.sdk.modelcontextprotocol.io/migration/)

## Decisions

### 1. Measure trust before adding legal capabilities

Version 0.3.0 turns the existing AusLaw benchmark into a reproducible release
gate. It also publishes the results. The gate tests the full index, not only
the repository fixture.

The benchmark input is:

| Field | Value |
| --- | --- |
| Dataset | `auslawbench/AusLaw-Citation-Benchmark` |
| Split | `test` |
| Rows | 1,000 |
| Licence | Apache-2.0 |
| Revision | `fabee289f2a5bbfb3c6476be55084abe426f6f18` |
| File | `roc_test.json` |
| SHA-256 | `154d272792778df49c01814d9e864121fcca3828df5f23c6ace90e992effb005` |

Routine unit tests remain offline. The release workflow may download this
exact file and must reject any digest mismatch.

### 2. Adopt MCP Python SDK v2 directly

CaseLaw Guard will require `mcp>=2,<3` for its MCP extra. It will not carry a
dual SDK import shim.

SDK v2 serves modern and earlier protocol revisions. Tests must exercise both
eras through stdio. Tests must assert protocol behaviour, not the server's
Python class name.

### 3. Fetch only explicit index versions

The new command is:

```bash
caselaw-guard au-index fetch VERSION --output PATH
```

The command derives the tag and asset names from a strict `YYYY-MM-DD` version.
It downloads only from `l0cka/caselaw-guard` GitHub releases.

Version 0.3.0 does not support `latest`, arbitrary URLs or silent updates. These
options weaken reproducibility and increase the trust surface.

### 4. Keep code and index releases independent

The package release does not republish an unchanged Australian index. Future
index releases run the coverage gate and publish its report with the data
assets.

## Scope

Version 0.3.0 includes:

- reproducible extraction and verification coverage reports;
- regression gates for full-index publication;
- MCP Python SDK v2 support;
- safe, explicit index download and installation;
- release-history and documentation repairs; and
- a clean public-wheel acceptance test.

## Non-goals

Version 0.3.0 does not include:

- proposition-support checking;
- good-law or precedential-status analysis;
- reported-citation aliases such as CLR or FCR;
- PDF or DOCX parsing;
- a hosted API, authentication or usage telemetry;
- new jurisdictions or providers;
- automatic index updates; or
- removal of legacy index loading.

## Release gates

| Gate | Required evidence |
| --- | --- |
| Coverage | pinned benchmark report and no regression from the approved baseline |
| Data | schema, provenance, attribution, checksum and decompression checks pass |
| MCP | modern and 2025-era stdio sessions list and call the verification tool |
| Packaging | clean base and MCP-extra wheel installations pass |
| Usability | clean wheel fetches an explicit index and verifies a real citation offline |
| Publication | CI is green and the user approves the tag and PyPI mutation |

## Execution model

- Create a clean `feat/v0.3.0` worktree from current `origin/main`.
- Keep the existing `.DS_Store` outside every commit.
- Write failing contract tests before changing production code.
- Use one bounded commit for each task below.
- Use separate Codex threads for parallel work. Do not spawn sub-agents.
- Keep one integration thread responsible for shared files and release gates.
- Stop at the final publication boundary for explicit approval.

## File map

| File | Change |
| --- | --- |
| `scripts/eval_auslaw_benchmark.py` | pin inputs, record provenance and compare baselines |
| `benchmarks/auslaw-citation-baseline.json` | approved per-row benchmark baseline |
| `benchmarks/reports/australian-index-2026-08-01.json` | first public full-index report |
| `tests/test_auslaw_benchmark_eval.py` | digest, provenance and regression contracts |
| `.github/workflows/publish-australian-index.yml` | run the coverage gate before publication |
| `scripts/build_release_index.py` | include the coverage report in release checksums |
| `tests/test_release_index.py` | release-asset checksum contract |
| `src/caselaw_guard/mcp_server.py` | SDK v2 server implementation |
| `tests/test_mcp_server.py` | modern and earlier protocol behaviour |
| `.github/workflows/ci.yml` | dedicated MCP-extra job |
| `src/caselaw_guard/australia/index_fetcher.py` | trusted index download and atomic installation |
| `src/caselaw_guard/cli.py` | `au-index fetch` command |
| `tests/test_australia_index_fetch.py` | network, integrity, limits and replacement contracts |
| `pyproject.toml` | version, MCP v2 and Zstandard dependencies |
| `README.md` | 5-minute setup and coverage links |
| `docs/self-hosting.md` | fetch, pin and update operations |
| `DATA_SOURCES.md` | benchmark source, revision and licence |
| `CHANGELOG.md` | close 0.2.0 history and describe 0.3.0 |
| `RELEASE.md` | general 0.3.0 release and rollback checklist |

## Task 1: establish a clean baseline

**Files:** none

- [ ] Fetch `origin/main` and confirm its current commit.
- [ ] Create `feat/v0.3.0` in a new worktree.
- [ ] Confirm the worktree has no inherited changes or untracked files.
- [ ] Record the current test, lint, format, type and package results.
- [ ] Confirm `v0.2.0`, the full index and their public assets remain available.
- [ ] Leave PR #15 open until Task 5 supersedes it.

Run:

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m build
python -m twine check dist/*
```

**Gate:** the branch starts from a green, current `main`.

## Task 2: repair release history and controls

**Files:**

- modify `CHANGELOG.md`;
- modify `RELEASE.md`; and
- modify `.github/workflows/publish.yml`.

- [ ] Add a dated `0.2.0` changelog section for the already shipped work.
- [ ] Restore an empty `Unreleased` section above it.
- [ ] Generalise the release checklist for 0.3.0.
- [ ] Update the publish workflow's default tag only during the final version bump.
- [ ] Record that GitHub's “Latest” marker belongs to the package release.
- [ ] Record that index publication requires a separate approval.

**Gate:** the documentation matches the public 0.2.0 state before new feature
work begins.

## Task 3: make the benchmark reproducible

**Files:**

- modify `scripts/eval_auslaw_benchmark.py`;
- modify `tests/test_auslaw_benchmark_eval.py`;
- create `benchmarks/auslaw-citation-baseline.json`;
- create `benchmarks/reports/australian-index-2026-08-01.json`; and
- modify `DATA_SOURCES.md`.

### Contract tests

- [ ] Reject a benchmark file that does not match the pinned SHA-256.
- [ ] Record dataset, revision, split, file digest and licence in every report.
- [ ] Record the loaded index's complete provenance in verification reports.
- [ ] Preserve stable per-row results, not only aggregate counts.
- [ ] Compare extraction and verification results against an approved baseline.
- [ ] Fail if a previously extracted citation becomes unrecognised.
- [ ] Fail if a previously verified citation becomes non-verified.
- [ ] Allow a previous `not_found` result to improve to `verified`.
- [ ] Produce deterministic JSON apart from an explicit generation timestamp.

### Implementation

- [ ] Replace the moving `main` benchmark URL with the pinned revision URL.
- [ ] Verify downloaded bytes before caching them.
- [ ] Download to a temporary file and replace the cache only after validation.
- [ ] Add `--baseline` and `--fail-on-regression` options.
- [ ] Include aggregate metrics and complete per-row outcomes in the report.
- [ ] Run the harness against `australian-index-2026-08-01`.
- [ ] Review every regression and a sample of each non-verified status.
- [ ] Approve and commit the first baseline only after that review.

**Human gate:** approve the first baseline. Do not invent thresholds before the
report exists.

**Gate:** another machine can reproduce the same report from the pinned input
and published index.

## Task 4: gate future index releases on coverage

**Files:**

- modify `.github/workflows/publish-australian-index.yml`;
- modify `scripts/build_release_index.py`; and
- modify `tests/test_release_index.py`.

- [ ] Run the pinned benchmark against the newly built index.
- [ ] Compare it with the approved baseline before publishing assets.
- [ ] Stop publication on any benchmark or digest failure.
- [ ] Add `australian-index-VERSION.verification.json` to workflow artifacts.
- [ ] Include the report in the release checksum manifest.
- [ ] Publish JSON, Zstandard, report and checksum assets together.
- [ ] Retain the exact source dataset revision and builder version.
- [ ] Keep the workflow manual because the source update cadence is irregular.

**Gate:** a failing coverage comparison cannot create or update a public index
release.

## Task 5: migrate the MCP server to SDK v2

**Files:**

- modify `pyproject.toml`;
- modify `src/caselaw_guard/mcp_server.py`;
- modify `tests/test_mcp_server.py`;
- modify `.github/workflows/ci.yml`; and
- modify `.github/workflows/package.yml`.

### Contract tests

- [ ] The base package imports without the MCP extra.
- [ ] A missing MCP extra produces the current actionable installation message.
- [ ] A modern 2026-07-28 stdio client lists `verify_case_law_text`.
- [ ] A 2025-era stdio client lists and calls the same tool.
- [ ] The tool returns the existing public verification report shape.
- [ ] The server emits no non-protocol output on stdout.
- [ ] A clean wheel installation starts and stops the server normally.

Use the SDK's supported test transport where it can select the protocol
revision. Use a minimal raw JSON-RPC harness only for a revision the helper
cannot exercise.

### Implementation

- [ ] Change the MCP extra to `mcp>=2,<3`.
- [ ] Replace the removed v1 import and server construction with supported v2 APIs.
- [ ] Preserve the tool name, arguments, instructions and JSON result.
- [ ] Remove the package test that asserts the concrete `FastMCP` class name.
- [ ] Add one dedicated `.[dev,mcp]` CI job on Python 3.12.
- [ ] Retain the clean-wheel MCP smoke test.
- [ ] Close PR #15 as superseded only after these checks pass.

**Gate:** both protocol eras pass through stdio from a built wheel.

## Task 6: add safe index fetching

**Files:**

- create `src/caselaw_guard/australia/index_fetcher.py`;
- create `tests/test_australia_index_fetch.py`;
- modify `src/caselaw_guard/cli.py`; and
- modify `pyproject.toml`.

### Command contract

```bash
caselaw-guard au-index fetch 2026-08-01 --output australia-index.json
```

On success, print JSON containing:

- the resolved output path;
- index version and source revision;
- record count, licence and attribution; and
- SHA-256 values for the compressed and JSON assets.

### Safety contract

- [ ] Accept only `YYYY-MM-DD` versions.
- [ ] Derive fixed release URLs from the version.
- [ ] Download the `.json.zst` and `.json.sha256` assets.
- [ ] Stream downloads and decompression rather than buffering them in memory.
- [ ] Limit compressed input to 256 MiB and decompressed output to 1 GiB.
- [ ] Verify the compressed digest before decompression.
- [ ] Verify the JSON digest after decompression.
- [ ] Load and validate the canonical index before installation.
- [ ] Require matching index version, CC-BY-4.0 and canonical attribution.
- [ ] Write temporary files in the output directory.
- [ ] Replace the output atomically only after every check passes.
- [ ] Refuse existing files unless the user supplies `--force`.
- [ ] Refuse to replace a symbolic link.
- [ ] Remove only temporary files created by the failed invocation.
- [ ] Preserve an existing valid output on every failure path.
- [ ] Use bounded connect, read and total timeouts.

### Tests

- [ ] Mock all network responses with `httpx.MockTransport`.
- [ ] Cover missing assets, HTTP errors, timeouts and truncated downloads.
- [ ] Cover malformed manifests and digest mismatches.
- [ ] Cover compressed and decompressed size limits.
- [ ] Cover invalid JSON, schema, version, licence and attribution.
- [ ] Cover existing output, `--force`, symbolic links and atomic replacement.
- [ ] Confirm test failures leave no partial installed index.

Add `zstandard>=0.22` to the base dependencies. Australian verification remains
offline after installation; the network is used only by the explicit fetch
command.

**Gate:** corrupt, oversized or untrusted data never becomes the configured
index.

## Task 7: integrate the 0.3.0 user journey

**Files:**

- modify `README.md`;
- modify `docs/self-hosting.md`;
- modify `docs/australian-api.md`;
- modify `DATA_SOURCES.md`;
- modify `CHANGELOG.md`;
- modify `RELEASE.md`;
- modify `pyproject.toml`;
- modify `src/caselaw_guard/api.py`;
- modify `src/caselaw_guard/australia/index_builder.py`; and
- update version-specific tests.

- [ ] Put the install, fetch and verify flow near the top of the README.
- [ ] Link the published coverage report and explain its limits.
- [ ] Explain that checksums protect integrity, not repository compromise.
- [ ] Document explicit updates and rollback to a previous index file.
- [ ] Keep the warning that `not_found` means absent from the snapshot only.
- [ ] Document MCP v2 and older-client compatibility.
- [ ] Update all runtime, builder, workflow and test versions to 0.3.0.
- [ ] Preserve the public CLI, REST and MCP report schemas.
- [ ] Preserve canonical and legacy index loading.

**Gate:** a reviewer can follow the README from a clean virtual environment
without repository source files.

## Task 8: release and verify 0.3.0

### Source checks

- [ ] Run the full suite on Python 3.11, 3.12 and 3.13.
- [ ] Run lint, formatting and typing checks.
- [ ] Validate the fixture and benchmark baseline schemas.
- [ ] Build the wheel and source distribution.
- [ ] Run Twine checks.
- [ ] Confirm neither distribution contains or depends on OpenBench.

### Clean-wheel checks

- [ ] Install the base wheel in a new Python 3.11 environment.
- [ ] Install the MCP extra in a second new environment.
- [ ] Fetch `australian-index-2026-08-01` through the new command.
- [ ] Verify `[2014] HCA 9 at [10]` offline.
- [ ] Call the same verification through a real MCP stdio session.
- [ ] Confirm the fetched index reports the published provenance.

### Publication boundary

- [ ] Present the exact tag, commit, release notes and PyPI effect.
- [ ] Obtain explicit approval.
- [ ] Create and push `v0.3.0`.
- [ ] Create the GitHub package release and mark it “Latest”.
- [ ] Publish through PyPI Trusted Publishing.
- [ ] Install `caselaw-guard[mcp]==0.3.0` from PyPI in a new environment.
- [ ] Repeat fetch, offline verification and MCP checks from the public wheel.
- [ ] Do not publish a new index unless the upstream dataset revision changed.

**Gate:** every public artifact passes the same checks as its candidate.

## Acceptance criteria

Version 0.3.0 is complete when:

1. the benchmark input is pinned by repository, revision and SHA-256;
2. the approved full-index baseline is reproducible;
3. future index publication fails closed on coverage regression;
4. each future index release includes its verification report;
5. MCP SDK v2 works with modern and earlier protocol revisions;
6. the MCP tool's name, arguments and result schema remain stable;
7. `au-index fetch` installs only verified, canonical index data;
8. fetch failures never damage an existing index;
9. clean PyPI installation, fetch, offline verification and MCP all pass;
10. GitHub identifies the package release as “Latest”; and
11. the repository records 0.2.0 and 0.3.0 accurately.

## Rollback

- A failed fetch preserves the prior index and exits non-zero.
- Users can point `CASELAW_GUARD_AU_INDEX` to any previously verified index.
- The release workflow never replaces an existing index asset after a failed gate.
- Do not rewrite or delete a published package version. Publish a patch release.
- Do not mutate a verified historical index to repair code. Publish a new index
  version with its own source revision and report.

## Deferred sequence

After 0.3.0, dogfood the release in real drafting workflows for 1 to 2 weeks.
Record false positives, unsupported formats, source gaps and setup failures.

Use that evidence to decide whether 0.4.0 should add reported-citation aliases.
Do not start proposition-support or good-law work without a separate evidence
model, specification and approval.
