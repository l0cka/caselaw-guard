# CaseLaw Guard × openbench: library integration

**Date:** 2026-08-01
**Status:** Draft for review
**Repos:** `caselaw-guard` (primary), `openbench` (secondary)

## Problem

`caselaw-guard` and `openbench` independently build and query an Australian
case-law citation index derived from the same source (the Open Australian Legal
Corpus by Isaacus). The duplication is not symmetric — `openbench` does the job
substantially better:

| Concern | caselaw-guard today | openbench today |
| --- | --- | --- |
| Neutral citation normalization | whitespace collapse only (`adapters/australia.py`) | full parser: paren/bare years, pinpoints, court codes, year bounds (`normalization.py`) |
| Index builder | `australia_index.py`, flat JSON array, no schema | `index_builder.py` + JSON Schema + dedup + provenance |
| Index format | untyped array of objects | versioned `IndexFile` with metadata, licence, record counts |
| Court metadata | none | `courts.py` court-code table |
| Data licensing | none | `LICENSE-DATA` (CC-BY-4.0) + `DATA_SOURCES.md` |

`caselaw-guard` also carries the weaker implementation in its published package,
so users of the PyPI release get the worse matcher.

## Decision

`caselaw-guard` depends on `openbench` **as a Python library**, not as an HTTP
service. The Australian adapter calls `normalize_citation()` and `IndexStore`
in-process. `openbench` keeps its own repository, CLI, REST API, and data
licensing unchanged.

### Why library and not HTTP

An HTTP adapter was considered and rejected for now:

- It requires a second process in every Australian workflow, including the
  offline smoke test in the README.
- It raises questions (batch endpoint, auth, retry/backoff, response caching)
  that only matter once a hosted `openbench` exists.
- It is strictly more work than the library path for identical v0 behaviour.

### Why this is reversible

`src/caselaw_guard/adapters/base.py` already defines the seam — `CitationAdapter`
with `supports()` and `lookup()`, 28 lines. Both futures plug into it without
touching `verifier.py`, the CLI, the REST API, or the MCP server:

- **If `openbench` becomes a hosted product:** add `OpenbenchHTTPAdapter`
  alongside the library adapter and select on config. Nothing is undone.
- **If `openbench` is not worth a separate repo:** move `normalization.py`,
  `index_builder.py`, `index_store.py`, `courts.py`, and `models.py`'s index
  types into `caselaw-guard`, drop the dependency, archive the repo. Nothing is
  undone.

The decision this spec defers is *where openbench lives*, not *what
caselaw-guard's Australian verification does*.

## Scope

### openbench changes

1. **Lower `requires-python` to `>=3.11`.** `caselaw-guard` supports `>=3.11`;
   `openbench` currently declares `>=3.12`. Verified: the source uses no
   3.12-only syntax — no PEP 695 type parameters, no `type` statements.
   `Self` (`index_store.py`) and `StrEnum` (`models.py`) are both 3.11.

   Files: `pyproject.toml` (`requires-python`, `[tool.ruff] target-version`,
   `[tool.mypy] python_version`), `.python-version`, `.github/workflows/ci.yml`
   (`uv python install`).

2. **Publish `openbench` 0.1.0 to PyPI**, reusing the trusted-publishing
   workflow pattern already proven in `caselaw-guard` (commit `d9bf45e`).

No changes to `openbench`'s API, index format, schema, CLI, or licensing.

### caselaw-guard changes

3. **Add an optional extra:** `au = ["openbench>=0.1"]`. Australian support
   becomes opt-in via `pip install "caselaw-guard[au]"`. US-only users are
   unaffected, and `openbench` does not become a core dependency.

4. **Rewrite `src/caselaw_guard/adapters/australia.py`** to wrap `openbench`:

   - `AustralianCorpusAdapter.__init__(index_path)` loads via
     `IndexStore.load(index_path)`, translating `IndexLoadError` into a clear
     configuration error at startup.
   - `lookup()` calls `normalize_citation(citation.text)`. On `ok=False`, return
     `UNSUPPORTED_FORMAT`. Otherwise call `store.lookup(normalized)`.
   - The `openbench` import is deferred to `__init__` so that `caselaw-guard`
     installed without the `[au]` extra still imports cleanly and raises an
     actionable message only when Australian support is actually configured.

5. **Delete** `src/caselaw_guard/australia_index.py`, the `au-index` Typer
   sub-app in `cli.py`, and their tests. `openbench index build` replaces
   `caselaw-guard au-index build`.

6. **Replace** `examples/australia_index.sample.json` with a copy of
   `openbench`'s `data/fixtures/index.json`, which is already in `IndexFile`
   format and already contains *Mabo v Queensland (No 2)* — so the README's
   no-network smoke test still passes as a single command.

7. **Update docs:** README (`Adapters` → Australia section, `Benchmarks`, the
   quickstart table, the MCP environment table) and `CHANGELOG.md`.

### Non-goals

- No HTTP adapter, no hosted `openbench`, no batch endpoint.
- No change to `CASELAW_GUARD_AU_INDEX` or `--au-index` names.
- No change to the CourtListener adapter, extraction, or fail-closed semantics.
- No change to `openbench`'s REST API or index schema.
- No merging of the two repositories.

## Interface

The adapter contract is unchanged (`adapters/base.py`):

```python
class CitationAdapter:
    name: str
    jurisdictions: frozenset[str]
    def supports(self, citation: CitationMatch) -> bool: ...
    def lookup(self, citation: CitationMatch) -> LookupResult: ...
```

### Status mapping

`openbench` returns entries, not statuses, at the library level; the adapter
derives status from the result of `normalize_citation` and `IndexStore.lookup`:

| Condition | `VerificationStatus` | Confidence |
| --- | --- | --- |
| `normalize_citation(...).ok is False` | `UNSUPPORTED_FORMAT` | 0.0 |
| `store.lookup(...)` returns `[]` | `NOT_FOUND` | 0.0 |
| returns exactly one entry | `VERIFIED` | 1.0 |
| returns more than one entry | `AMBIGUOUS` | 0.5 |

This preserves current `caselaw-guard` behaviour exactly. Only `VERIFIED`
contributes to a passing report — fail-closed is unchanged.

### `IndexEntry` → `Authority` mapping

| `Authority` field | Source |
| --- | --- |
| `case_name` | `entry.case_name` |
| `court` | `entry.court` |
| `date` | `entry.date.isoformat()` |
| `source_url` | `entry.source_urls[0]` (schema guarantees `min_length=1`) |
| `metadata` | `court_code`, `jurisdiction`, full `source_urls`, `source`, `license` |

Carrying `license` and `source` into `metadata` keeps the CC-BY-4.0 attribution
visible in `caselaw-guard`'s JSON output, which the current adapter does not do.

`AMBIGUOUS` results map every entry through the same function into `candidates`.

## Breaking change

`--au-index` and `CASELAW_GUARD_AU_INDEX` keep their names but require an
`openbench`-format index file. Indexes built by `caselaw-guard au-index build`
stop working and must be rebuilt with `openbench index build`.

This is acceptable: `caselaw-guard` is 0.1.2, `Development Status :: 3 - Alpha`,
and the only index file in the repository is the sample, which is regenerated as
part of this work. `IndexStore.load` already raises `IndexLoadError` on a
non-conforming file, so the failure is loud rather than silent — the adapter
surfaces it with a message naming `openbench index build`.

Released as 0.2.0 with a `CHANGELOG.md` entry under a `Changed` heading.

## Testing

1. **openbench:** existing suite runs green under Python 3.11
   (`uv python install 3.11 && uv run --python 3.11 pytest -q`). No new tests —
   the change is metadata only.
2. **caselaw-guard:** rewrite `tests/` for the Australian adapter against the
   copied fixture index at `examples/australia_index.sample.json`. Cover all
   four statuses in the mapping table, plus the
   `IndexLoadError` path and the missing-`[au]`-extra import error.
3. **Regression:** `Mabo v Queensland (No 2) [1992] HCA 23` verifies end-to-end
   through the CLI with no network.
4. **New coverage the current adapter lacks:** pinpoint suffixes
   (`[1992] HCA 23 at [10]`), paren years (`(1992) HCA 23`), lower-case court
   codes (`[1992] hca 23`) all resolve to the same entry.

## Assumptions

- `openbench`'s test suite passes on Python 3.11. Unverified locally — only
  3.13 is installed on this machine. Step 1 of implementation verifies it, and
  if it fails, the fallback is raising `caselaw-guard` to `>=3.12` instead.
- Publishing `openbench` to PyPI is acceptable. If not, a git dependency works
  for local use but blocks `caselaw-guard`'s own PyPI releases of the `[au]`
  extra.
- `openbench`'s library surface (`normalize_citation`, `IndexStore.load`,
  `IndexStore.lookup`, `IndexEntry`) is stable enough to depend on. It is
  already the internal contract its own REST API uses, so this adds no new
  obligation.

## Risks

- **Two-repo release coupling.** A breaking change to `openbench`'s library
  surface requires a coordinated `caselaw-guard` release. Mitigated by pinning
  `openbench>=0.1` and by the small, already-stable surface area.
- **Attribution drift.** The CC-BY-4.0 obligation now travels through two
  packages. Mitigated by carrying `license` and `source` in `Authority.metadata`
  so it appears in output, not just in a repository file.

## Verification

Done when:

1. `openbench` tests pass on Python 3.11 and it is installable from PyPI.
2. `pip install "caselaw-guard[au]"` pulls `openbench`.
3. `caselaw-guard verify - --no-courtlistener --au-index examples/australia_index.sample.json`
   with `Mabo v Queensland (No 2) [1992] HCA 23` on stdin exits 0, no network.
4. The same command with `[1992] HCA 23 at [10]` also exits 0 (new behaviour;
   fails today).
5. `grep -r "au-index build\|australia_index" src/ tests/ README.md` returns
   nothing.
6. `caselaw-guard` test suite passes.
