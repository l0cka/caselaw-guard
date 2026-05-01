# openbench v1 — Design Spec

- **Date:** 2026-05-01
- **Status:** Draft (decisions confirmed in brainstorm 2026-05-01; pending final user review before plan)
- **Project:** `openbench` — open Australian case-law citation lookup API
- **Repo:** single repo, `openbench` (no organisation/multi-repo split in v1)
- **Owner:** danielkurdi0@gmail.com

## 1. Purpose

Provide a public, documented, self-hostable API that resolves Australian neutral citations against an open-licensed corpus and returns structured case metadata with explicit provenance.

The service verifies *"this citation is present in the configured open index"* — not *"this case is officially confirmed by a court"*. v1 makes that distinction visible in the API surface, the response payloads, the README, and the index metadata.

## 2. Goals

- Resolve exact Australian neutral citations (e.g. `[1992] HCA 23`) and common-variant inputs.
- Return stable JSON with case name, court, jurisdiction, date, source URL, source dataset, ambiguity status, candidates, and provenance.
- Publish the index build process and source provenance.
- Be easy to self-host: one Python package, one index file, one `serve` command.
- Keep licensing, attribution, and data provenance explicit in code, docs, and every API response.

## 3. Non-Goals (v1)

- No legal advice.
- No good-law / precedential-status analysis.
- No proposition-support checking against judgment text.
- No website scraping. Bulk corpus only.
- No claim of being an official court or government API.
- No full-text search.
- No reported-citation aliasing (e.g. `(1992) 175 CLR 1` → neutral). Deferred to Phase 3.
- No commercial provider integration.
- No public hosted deployment in v1 (deferred to Phase 2).
- No user accounts, API keys, or write endpoints.

## 4. Data Source

**Primary (and only) source for v1:** [Isaacus Open Australian Legal Corpus](https://huggingface.co/datasets/isaacus/open-australian-legal-corpus) on HuggingFace.

- **Licence:** CC-BY-4.0. Permits use, sharing, adaptation, distribution, reproduction, including derived works (such as a metadata-only index), with attribution and indication of changes.
- **Update cadence:** irregular. The index is treated as a snapshot; freshness is surfaced explicitly in `/v1/au/index/metadata`.
- **Filtering:** decisions only (judgments). Non-decision documents (legislation, secondary materials) are excluded from the citation index.
- **Field extraction:** only metadata fields needed to satisfy the index schema (§7) are extracted. Full judgment text is **not** stored in the public index.

**Attribution:** wherever index data derived from the corpus is exposed — the in-repo fixture index, any published full-index release artifact, every API response's `provenance` block, `DATA_SOURCES.md`, and `/v1/au/index/metadata` — openbench must credit Isaacus, link the upstream dataset, link CC-BY-4.0, and note that openbench has modified the data (extracted metadata, normalised citations, deduplicated).

## 5. Citation Parsing

v1 accepts the following input forms and normalises to canonical `[YYYY] COURT N`:

| Accepted input                       | Normalised to       |
| ------------------------------------ | ------------------- |
| `[1992] HCA 23`                      | `[1992] HCA 23`     |
| `(1992) HCA 23`                      | `[1992] HCA 23`     |
| `1992 HCA 23`                        | `[1992] HCA 23`     |
| `[1992]  HCA   23` (extra whitespace) | `[1992] HCA 23`     |
| `[1992] hca 23` (case-insensitive court code) | `[1992] HCA 23` |
| `[1992] HCA 23 [10]` (pinpoint paragraph) | `[1992] HCA 23` |
| `[1992] HCA 23 at [10]`              | `[1992] HCA 23`     |
| `[1992] HCA 23, [10]`                | `[1992] HCA 23`     |

Anything that does not match the underlying pattern `\[?YYYY\]?\s+COURT\s+N(\s+(at\s+)?\[\d+\])?` after whitespace normalisation returns `status: unsupported_format` (no lookup attempted).

Year range: `1900` ≤ YYYY ≤ current calendar year + 1 (allows for citations dated to next year that appear in late-year judgments). Outside this range → `unsupported_format`.

Court codes: any non-empty uppercase alphabetic token (`HCA`, `FCAFC`, `NSWSC`, `VSCA`, etc.). v1 does **not** maintain a closed list of valid court codes — the index is the source of truth. Unknown court codes pass parsing and simply fail to match in the index, returning `not_found`.

Reported-citation forms (`(1992) 175 CLR 1`) are rejected with `unsupported_format` in v1. They are documented as a Phase 3 feature.

## 6. Ambiguity & Dedup Policy

During index build, source records are grouped by `normalized_citation`. Within a group, records are merged into a single index entry when they share `(normalized_citation, case_name, date)`. The merged entry retains all distinct `source_url`s in a `source_urls` array and all distinct source record IDs in `source_record_ids`.

After dedup:

- **Exactly one entry** for a citation → API returns `status: verified`, `confidence: 1.0`, `candidates: []`.
- **Two or more entries** for a citation (i.e. the corpus contained genuinely different case names or dates under the same citation) → API returns `status: ambiguous`, `confidence: 0.5`, `candidates: [...]` listing each distinct entry. The top-level `case_name`/`court`/`date` fields are omitted in this case.
- **Zero entries** → `status: not_found`, `confidence: 0.0`, `candidates: []`.

Case-name comparison for dedup is exact-match on the trimmed string after collapsing internal whitespace. Punctuation differences (e.g. `(No 2)` vs `(No. 2)`) intentionally do **not** merge in v1 — they surface as `ambiguous` so the data quality issue is visible rather than silently flattened. Improving this is a future-phase concern.

## 7. Index Schema

Each index entry:

```json
{
  "normalized_citation": "[1992] HCA 23",
  "citation": "Mabo v Queensland (No 2) [1992] HCA 23",
  "case_name": "Mabo v Queensland (No 2)",
  "court": "High Court of Australia",
  "court_code": "HCA",
  "jurisdiction": "cth",
  "date": "1992-06-03",
  "source_urls": ["https://..."],
  "source": "open-australian-legal-corpus",
  "source_record_ids": ["..."],
  "indexed_at": "2026-05-01",
  "license": "CC-BY-4.0",
  "provenance": {
    "dataset": "isaacus/open-australian-legal-corpus",
    "dataset_version": "<HF revision or commit hash>",
    "builder_version": "0.1.0"
  }
}
```

Top-level index file:

```json
{
  "index_version": "2026-05-01",
  "generated_at": "2026-05-01T00:00:00Z",
  "builder_version": "0.1.0",
  "source": "open-australian-legal-corpus",
  "license": "CC-BY-4.0",
  "record_count": 0,
  "entries": { "[1992] HCA 23": { /* entry */ } }
}
```

`entries` is keyed by `normalized_citation` for O(1) lookup at startup. When ambiguity exists, the value is an array of entries; otherwise a single entry object. The API layer normalises both shapes into a `candidates` list internally.

Court name (`court`) and `jurisdiction` are derived from `court_code` via a static mapping table (e.g. `HCA` → `("High Court of Australia", "cth")`, `NSWSC` → `("Supreme Court of New South Wales", "nsw")`). The mapping table is part of the codebase, not the corpus. Court codes not in the mapping have `court: null` and `jurisdiction: null` and are still indexed.

## 8. API Contract

Base URL when self-hosted: `http://127.0.0.1:8000`.

### Endpoints

```text
GET /health
GET /v1/au/citations/{citation}
GET /v1/au/index/metadata
GET /v1/au/index/stats
```

### Statuses

- `verified` — exactly one matching entry after dedup.
- `not_found` — input parsed cleanly but no matching entry.
- `ambiguous` — multiple distinct entries under the same citation.
- `unsupported_format` — input did not parse.
- `index_unavailable` — server started without an index file or index failed to load. Returns HTTP 503.
- `provider_error` — reserved for future remote-source adapters; not emitted in v1.

### Response shapes

**Verified:**

```json
{
  "citation": "[1992] HCA 23",
  "normalized_citation": "[1992] HCA 23",
  "status": "verified",
  "case_name": "Mabo v Queensland (No 2)",
  "court": "High Court of Australia",
  "court_code": "HCA",
  "jurisdiction": "cth",
  "date": "1992-06-03",
  "source_urls": ["https://..."],
  "sources": ["open-australian-legal-corpus"],
  "confidence": 1.0,
  "candidates": [],
  "provenance": {
    "index_version": "2026-05-01",
    "source": "open-australian-legal-corpus",
    "license": "CC-BY-4.0",
    "dataset": "isaacus/open-australian-legal-corpus",
    "attribution": "Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by openbench (metadata extraction)."
  }
}
```

**Not found:**

```json
{
  "citation": "[2099] HCA 999",
  "normalized_citation": "[2099] HCA 999",
  "status": "not_found",
  "confidence": 0.0,
  "candidates": [],
  "provenance": {
    "index_version": "2026-05-01",
    "source": "open-australian-legal-corpus"
  }
}
```

**Ambiguous:**

```json
{
  "citation": "[2024] NSWSC 10",
  "normalized_citation": "[2024] NSWSC 10",
  "status": "ambiguous",
  "confidence": 0.5,
  "candidates": [
    {
      "case_name": "First Case",
      "court": "Supreme Court of New South Wales",
      "court_code": "NSWSC",
      "jurisdiction": "nsw",
      "date": "2024-01-01",
      "source_urls": ["https://..."]
    },
    {
      "case_name": "Second Case",
      "court": "Supreme Court of New South Wales",
      "court_code": "NSWSC",
      "jurisdiction": "nsw",
      "date": "2024-01-15",
      "source_urls": ["https://..."]
    }
  ],
  "provenance": {
    "index_version": "2026-05-01",
    "source": "open-australian-legal-corpus"
  }
}
```

**Unsupported format:**

```json
{
  "citation": "Mabo",
  "status": "unsupported_format",
  "confidence": 0.0,
  "candidates": []
}
```

HTTP status codes:

- `200` for `verified`, `not_found`, `ambiguous`, `unsupported_format`.
- `503` with `status: index_unavailable` for `/v1/au/citations/{...}`, `/v1/au/index/metadata`, and `/v1/au/index/stats` when no index is loaded.
- `/health` always returns `200` and reports `index_loaded: true|false` in its body, so liveness probes are decoupled from index state.
- Future `provider_error` will use `502`.

### Operational endpoints

`GET /health` → `{"status": "ok", "index_loaded": true}`.

`GET /v1/au/index/metadata`:

```json
{
  "index_version": "2026-05-01",
  "generated_at": "2026-05-01T00:00:00Z",
  "record_count": 123456,
  "sources": ["open-australian-legal-corpus"],
  "license": "CC-BY-4.0",
  "builder_version": "0.1.0",
  "attribution": "Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by openbench (metadata extraction).",
  "dataset": "isaacus/open-australian-legal-corpus",
  "dataset_version": "<HF revision>"
}
```

`GET /v1/au/index/stats`:

```json
{
  "record_count": 123456,
  "ambiguous_count": 42,
  "by_court": { "HCA": 1234, "FCAFC": 5678, "NSWSC": 9012 },
  "by_year": { "1992": 1500, "...": 0 },
  "earliest_date": "1903-10-12",
  "latest_date": "2024-12-20"
}
```

## 9. Distribution Model

- **Fixture index in repo:** `data/fixtures/index.json` containing ≈50 leading Australian cases (must include `[1992] HCA 23` to satisfy the success criterion; representative spread across HCA, FCAFC, FCA, state Supreme Courts, and at least one ambiguous-by-construction entry for tests). Used for `pytest`, smoke tests, and the `--index data/fixtures/index.json` quickstart in the README.
- **Full index as GitHub Release artifact:** each tagged release of openbench publishes `index-<index_version>.json.zst` as a release asset. Self-hosters download it and point `AUS_CASE_INDEX` at it.
- **No PyPI publishing in v1.** PyPI publishing is a Phase 2 task once the API surface has been used by at least one external consumer.

## 10. Storage

- v1 storage is a single JSON file loaded fully into memory at server startup. The index is keyed on `normalized_citation` for O(1) lookup. Aggregates needed by `/v1/au/index/stats` (`by_court`, `by_year`, `earliest_date`, `latest_date`, `ambiguous_count`) are computed once at startup and cached on the in-memory store.
- The `index_store` module exposes a small interface (`load(path) -> IndexStore`, `lookup(normalized_citation) -> list[Entry]`, `metadata() -> Metadata`, `stats() -> Stats`) so the storage backend can be replaced in a later phase without touching the API layer.
- SQLite is **not** introduced in v1. Trigger for the migration is when full-index startup memory exceeds ~512MB or when the API needs partial-match queries (e.g. case-name search, deferred to Phase 3).

## 11. Project Structure

```
openbench/
├── README.md
├── LICENSE                       # Apache-2.0 (code)
├── LICENSE-DATA                  # CC-BY-4.0 notice for index artifacts
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── SECURITY.md
├── DATA_SOURCES.md
├── pyproject.toml
├── uv.lock
├── .python-version
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                # lint + test on push/PR
│   │   └── release.yml           # build release index, attach to tag
│   └── ISSUE_TEMPLATE/
│       ├── data-error.md
│       └── source-request.md
├── docs/
│   ├── api.md
│   ├── self-hosting.md
│   └── superpowers/specs/2026-05-01-openbench-design.md
├── data/
│   └── fixtures/
│       ├── index.json            # 50-case fixture
│       └── corpus-fixture.jsonl  # tiny corpus slice for index_builder tests
├── schemas/
│   └── index.schema.json
├── src/openbench/
│   ├── __init__.py
│   ├── normalization.py
│   ├── courts.py                 # court_code → (name, jurisdiction)
│   ├── models.py                 # Pydantic response models
│   ├── index_store.py
│   ├── index_builder.py
│   ├── api.py                    # FastAPI app + routes
│   └── cli.py                    # `openbench index build|stats`, `openbench serve`
└── tests/
    ├── unit/
    │   ├── test_normalization.py
    │   ├── test_courts.py
    │   ├── test_index_store.py
    │   └── test_index_builder.py
    └── integration/
        ├── test_api_health.py
        ├── test_api_lookup.py
        └── test_api_metadata.py
```

The CLI entry point name `openbench` is registered via `pyproject.toml` `[project.scripts]`. The plan's earlier `aus-case-api` name is replaced — single source of truth is the project name `openbench`.

## 12. Tooling

- **Python:** 3.12 minimum.
- **Package/env manager:** `uv` (locked via `uv.lock`).
- **Lint/format:** `ruff` (single tool, format + lint).
- **Type checking:** `mypy` in strict mode for `src/openbench/`.
- **Web framework:** FastAPI + Pydantic v2.
- **ASGI server:** `uvicorn` (development); production deployment choice is deferred to Phase 2.
- **Testing:** `pytest`, `httpx` (FastAPI `TestClient`).
- **CI:** GitHub Actions, two workflows:
  - `ci.yml`: ruff, mypy, pytest, schema validation, build sdist+wheel via `uv build`, `twine check`.
  - `release.yml`: on tag push, build the full index from the upstream corpus, validate against `schemas/index.schema.json`, compress with zstd, attach to the GitHub Release.

## 13. Testing Scope (v1)

**Unit tests:**

- Citation normalisation: every accepted form in §5, plus rejected forms.
- Court code → name/jurisdiction mapping (known + unknown).
- Index loading: well-formed file, malformed JSON, missing required fields, schema mismatch.
- Index builder: empty corpus, single record, duplicate records that should merge, distinct records that should produce ambiguity, non-decision records that should be filtered out.

**Integration tests** (FastAPI `TestClient` with the fixture index):

- `GET /health` → 200 + `index_loaded: true`.
- `GET /v1/au/citations/[1992] HCA 23` → `verified` with `Mabo v Queensland (No 2)`.
- `GET /v1/au/citations/[2099] HCA 999` → `not_found`.
- `GET /v1/au/citations/<ambiguous-by-construction fixture citation>` → `ambiguous` with ≥2 candidates. The fixture must contain one such constructed entry (e.g. a synthetic `[2024] NSWSC 9999` with two distinct case names); the exact citation chosen is an implementation-plan concern.
- `GET /v1/au/citations/Mabo` → `unsupported_format`.
- `GET /v1/au/citations/[1992] HCA 23 [10]` → `verified` for `[1992] HCA 23` (pinpoint stripped).
- `GET /v1/au/citations/(1992) 175 CLR 1` → `unsupported_format` (reported citations rejected in v1).
- `GET /v1/au/index/metadata` → fixture metadata.
- `GET /v1/au/index/stats` → fixture stats.
- Server start without `AUS_CASE_INDEX` → 503 + `index_unavailable` on lookup; `/health` reports `index_loaded: false`.

**Release checks** (run in CI on tag):

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/openbench
uv run pytest -q
uv build
uvx twine check dist/*
```

## 14. Licensing

- `LICENSE` — Apache-2.0, applies to all source code, schemas, tests, and documentation in this repo.
- `LICENSE-DATA` — CC-BY-4.0 notice and attribution text, applies to the published index artifacts (release assets) and the in-repo fixture index.
- `DATA_SOURCES.md` — explicit credit to Isaacus, link to the corpus, link to CC-BY-4.0, statement that openbench has modified the data by extracting metadata, normalising citations, and deduplicating.
- Every API response's `provenance` block carries `license` and `attribution` fields that recreate the upstream credit at the point of use.

## 15. v1 Definition of Done

v1 ships when **all** of the following are true:

1. `uv run openbench index build <path-to-corpus> --output index.json` produces a valid `index.json` from a corpus snapshot.
2. `uv run openbench serve --index data/fixtures/index.json` starts a FastAPI server on `127.0.0.1:8000`.
3. `curl "http://127.0.0.1:8000/v1/au/citations/%5B1992%5D%20HCA%2023"` returns a `verified` response for *Mabo v Queensland (No 2)* against the fixture index.
4. All unit and integration tests in §13 pass in CI.
5. Schema validation of `data/fixtures/index.json` against `schemas/index.schema.json` passes in CI.
6. README documents installation, building the index, running the server, the disclaimer language from §16, and the attribution required by CC-BY-4.0.
7. A signed/tagged release exists with the source artifacts. (Index release artifact attachment is allowed to be added in the first patch release if upstream-corpus download from CI is not yet wired up — that wire-up is part of v1, but the first end-to-end CI run can use a fixture-only release.)

## 16. Disclaimers (must appear in README, `/v1/au/index/metadata`, and project description)

- openbench is **not** an official court or government API.
- openbench does **not** provide legal advice.
- openbench results reflect the configured open index only.
- Absence of a citation from the index does **not** prove the case does not exist.
- Users must verify important matters against authorised sources (court websites, AustLII, JADE, etc.).

## 17. Deferred (explicitly not in v1)

- Public hosted API, rate limiting, monitoring (Phase 2).
- PyPI publishing (Phase 2).
- SQLite backend (Phase 3, only if needed).
- Reported-citation aliasing (Phase 3).
- Case-name search (Phase 3).
- Court-code normalisation across reporting variants (Phase 3).
- Python client library, MCP server, GitHub Action, dataset-release repo (Phase 4).
