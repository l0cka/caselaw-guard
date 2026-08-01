# CaseLaw Guard: consolidate OpenBench

**Date:** 1 August 2026

**Status:** Approved for implementation

**Decision:** one repository and one Python distribution

**Target repository:** `caselaw-guard`

## Decision

Move OpenBench's Australian citation index capability into `caselaw-guard`.
Publish one Python distribution named `caselaw-guard`. Do not publish an
`openbench` dependency or retain a separate OpenBench code repository.

Keep the Australian index data outside the Python wheel. Publish full indexes
as versioned release artifacts with their provenance and CC-BY-4.0 attribution.

Archive the `openbench` repository only after the consolidated package passes
its release checks. The archived repository must direct users to
`caselaw-guard`.

## Context

`caselaw-guard` and `openbench` independently build and query an Australian
case-law citation index derived from the Open Australian Legal Corpus by
Isaacus. OpenBench has the stronger implementation:

| Concern | `caselaw-guard` | `openbench` |
| --- | --- | --- |
| Citation normalization | Collapses whitespace | Parses variants and pinpoints |
| Index builder | Writes a flat JSON array | Deduplicates records and records provenance |
| Index validation | Performs row-level checks | Uses typed models and JSON Schema |
| Court metadata | Has an extraction allowlist | Maps court codes to courts and jurisdictions |
| Data licensing | Does not carry attribution in results | Includes CC-BY-4.0 data notices |

The projects do not have separate ownership or demonstrated release
lifecycles. They began on the same date and have the same sole human author.
As at 1 August 2026, OpenBench has no hosted deployment or independent package
distribution.

The proposed PyPI dependency is also unavailable. The
[`openbench`](https://pypi.org/project/openbench/) distribution name belongs to
an unrelated LLM evaluation project. A dependency such as `openbench>=0.1`
would install the wrong software.

The durable boundary is between code and index data. It is not between 2 code
repositories.

## Goals

This consolidation must:

1. make OpenBench's stronger Australian lookup implementation the only
   implementation in `caselaw-guard`;
2. preserve offline verification, the CLI, REST API and MCP server;
3. detect the Australian citation variants that the normalizer accepts;
4. expose index provenance for successful and unsuccessful lookups; and
5. preserve OpenBench's Git history and give existing index users a migration
   path.

## Non-goals

This work does not:

- host a public citation API;
- add authentication, retries, response caching or a batch endpoint;
- change the CourtListener adapter or US citation verification;
- add proposition-support or good-law analysis; or
- include the full Australian index in the Python wheel.

## Target architecture

### Repository and distribution

`caselaw-guard` becomes the sole code repository and Python distribution.
Australian support remains built in. Users do not install an `[au]` extra or a
second package.

The merged Australian modules add no required runtime dependency. CaseLaw
Guard already depends on FastAPI, Pydantic, Typer and Uvicorn. Runtime index
validation continues to use Pydantic. JSON Schema remains a development and
release check.

### Package structure

```text
src/caselaw_guard/
├── australia/
│   ├── __init__.py
│   ├── courts.py
│   ├── index_builder.py
│   ├── index_store.py
│   ├── models.py
│   ├── normalization.py
│   └── service.py
├── adapters/
│   ├── australia.py
│   ├── base.py
│   └── courtlistener.py
├── api.py
├── cli.py
├── extractors.py
└── mcp_server.py
```

`australia/service.py` is the single application-level lookup interface. The
Australian adapter and Australian REST routes call this service. They do not
reimplement normalization, status mapping or provenance handling.

### Lookup flow

Australian verification follows one path:

```text
source text
  -> extract Australian citation candidate
  -> normalize and classify the candidate
  -> query the configured index
  -> return a typed Australian lookup result
  -> map it to CaseLaw Guard's LookupResult
  -> expose the same result through CLI, REST and MCP
```

The extractor must recognize every citation form that the normalizer accepts.
An accepted citation-like string must not disappear and produce an empty,
passing verification report.

## Australian lookup contract

### Service interface

The service owns an `IndexStore` and returns a typed result. The exact class
names may follow the existing code style, but the contract must contain:

```python
class AustralianLookupResult:
    raw_citation: str
    normalized_citation: str | None
    status: AustralianLookupStatus
    entries: tuple[IndexEntry, ...]
    provenance: IndexProvenance
    rejection_reason: str | None


class AustralianCitationService:
    @classmethod
    def load(cls, index_path: str | Path) -> Self: ...

    def lookup(self, raw_citation: str) -> AustralianLookupResult: ...
```

`IndexLoadError` remains the boundary for missing, malformed or invalid index
files. Adapter construction converts it into a clear configuration error that
names the index path and the corrective command.

### Accepted citation forms

The extractor and normalizer accept these forms and normalize them to the same
key:

| Input | Normalized citation |
| --- | --- |
| `[1992] HCA 23` | `[1992] HCA 23` |
| `(1992) HCA 23` | `[1992] HCA 23` |
| `1992 HCA 23` | `[1992] HCA 23` |
| `[1992]  HCA   23` | `[1992] HCA 23` |
| `[1992] hca 23` | `[1992] HCA 23` |
| `[1992] HCA 23 [10]` | `[1992] HCA 23` |
| `[1992] HCA 23 at [10]` | `[1992] HCA 23` |
| `[1992] HCA 23, [10]` | `[1992] HCA 23` |

Reported citations such as `(1992) 175 CLR 1` remain outside this Australian
neutral-citation parser.

### Court codes

The parser accepts court codes that start with a letter and then contain
letters or numbers. This covers codes such as `HCA`, `NSWCATAP` and
`FedCFamC1A`.

Court-code matching is case-insensitive. The court table supplies the canonical
spelling for known codes. Unknown codes normalize to uppercase and remain
eligible for index lookup. The index, rather than a closed extractor allowlist,
decides whether a well-formed code exists.

The consolidated court table must include the union of the current
`caselaw-guard` extraction allowlist and OpenBench court metadata. This avoids
regressing the AusLaw benchmark court codes.

### Status mapping

The service applies one status policy across the adapter and REST routes:

| Condition | Status | Confidence |
| --- | --- | --- |
| malformed neutral-citation syntax | `UNSUPPORTED_FORMAT` | 0.0 |
| well-formed citation with a rejected year | `NOT_FOUND` | 0.0 |
| zero index entries | `NOT_FOUND` | 0.0 |
| exactly one index entry | `VERIFIED` | 1.0 |
| more than one index entry | `AMBIGUOUS` | 0.5 |

This keeps the current treatment of citation-shaped future years. Only
`VERIFIED` contributes to a passing CaseLaw Guard report.

End-to-end tests must assert the extracted result count. An exit code of zero
does not prove that the extractor saw the citation.

### Authority mapping

The adapter maps one `IndexEntry` to `Authority` as follows:

| `Authority` field | Source |
| --- | --- |
| `case_name` | `entry.case_name` |
| `court` | `entry.court` |
| `date` | `entry.date.isoformat()` |
| `source_url` | first item in `entry.source_urls` |
| `metadata.court_code` | `entry.court_code` |
| `metadata.jurisdiction` | `entry.jurisdiction` |
| `metadata.source_urls` | all `entry.source_urls` values |
| `metadata.source` | `entry.source` |
| `metadata.license` | `entry.license` |

Ambiguous results map each entry into `candidates`. They do not select a
preferred authority.

## Index format and provenance

### Canonical format

OpenBench's typed `IndexFile` becomes the canonical CaseLaw Guard Australian
index format. Move its Pydantic models and JSON Schema into `caselaw-guard`.

The top-level index metadata records:

- index version and generation time;
- builder version and source dataset;
- dataset revision, or the explicit value `unknown`;
- data licence and the canonical attribution statement; and
- the number of normalized citation keys.

The builder must record the upstream dataset revision when the caller supplies
it. It must use `unknown` when the revision is unavailable. It must not invent
or infer a revision.

The canonical attribution statement is:

> Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by CaseLaw
> Guard (metadata extraction, normalisation and deduplication).

Define this statement once in code. Reuse it in the fixture, API responses,
release metadata and `DATA_SOURCES.md`.

### Result provenance

Every attempted Australian lookup includes these values in
`LookupResult.provider_metadata`:

- `index_version`;
- `generated_at`;
- `source` and `dataset_revision`;
- `license` and `attribution`; and
- `index_format`, including whether the loader used legacy compatibility.

This metadata appears for `VERIFIED`, `NOT_FOUND`, `AMBIGUOUS` and
`UNSUPPORTED_FORMAT`. `Authority.metadata` continues to carry entry-level
provenance for verified and ambiguous results.

### Legacy index compatibility

Version 0.2.0 accepts both:

1. the current CaseLaw Guard flat-array index; and
2. the canonical typed index inherited from OpenBench.

The loader converts a flat-array index in memory. It does not rewrite the
user's file. Results from a legacy index include `index_format: legacy` and
honestly mark unavailable provenance as `unknown`.

`caselaw-guard au-index build` writes only the canonical format. Add
`caselaw-guard au-index migrate INPUT --output OUTPUT` for users who want to
convert an existing file.

Document legacy support as transitional. A later design decision must approve
its removal. This specification does not set an automatic removal version.

## User interfaces

### CLI

Keep these existing names:

- `caselaw-guard verify`;
- `caselaw-guard au-index build`;
- `--au-index`; and
- `CASELAW_GUARD_AU_INDEX`.

Add `caselaw-guard au-index stats` and `caselaw-guard au-index migrate` from the
merged OpenBench capability. Do not install an `openbench` console script.

### REST API

Keep `POST /verify`. Move OpenBench's read-only Australian routes into the same
FastAPI application:

- `GET /health`;
- `GET /v1/au/citations/{citation}`;
- `GET /v1/au/index/metadata`; and
- `GET /v1/au/index/stats`.

The Australian lookup route calls `AustralianCitationService.lookup()`. Its
status and provenance must match the Australian adapter for the same citation
and index.

### MCP

The MCP server keeps one `verify_case_law_text` tool and the existing response
shape. Australian results gain the normalized citation, authority metadata and
provider metadata defined in this specification.

The MCP server does not expose index-building or migration tools.

## Repository consolidation

### Preserve Git history

Import the OpenBench repository on a dedicated integration branch. Use
`git subtree` without `--squash` under a temporary `openbench-import/` prefix.
Then move the required files into their target locations.

Do not copy the files into CaseLaw Guard as unrelated new files. The integration
branch must retain OpenBench's commits and authorship.

### Move map

| OpenBench source | CaseLaw Guard target |
| --- | --- |
| `src/openbench/normalization.py` | `src/caselaw_guard/australia/normalization.py` |
| `src/openbench/index_builder.py` | `src/caselaw_guard/australia/index_builder.py` |
| `src/openbench/index_store.py` | `src/caselaw_guard/australia/index_store.py` |
| `src/openbench/courts.py` | `src/caselaw_guard/australia/courts.py` |
| index types from `src/openbench/models.py` | `src/caselaw_guard/australia/models.py` |
| lookup logic from `src/openbench/api.py` | `src/caselaw_guard/australia/service.py` |
| `schemas/index.schema.json` | `schemas/australia-index.schema.json` |
| `LICENSE-DATA` and `DATA_SOURCES.md` | repository root |
| fixtures and relevant tests | CaseLaw Guard fixture and test directories |
| release-index workflow and script | CaseLaw Guard workflow and script directories |

Remove the temporary import tree after every required file, test, document and
workflow has a mapped destination.

### Archive gate

Archive `l0cka/openbench` only after all acceptance criteria pass against the
published CaseLaw Guard release. Before archiving:

1. replace its README with a short migration notice;
2. link to the consolidated repository and new commands;
3. keep its licence, tags and Git history available;
4. close or transfer any open work; and
5. mark the GitHub repository as archived.

Archiving is a separate, approved repository mutation. Implementation of this
specification does not itself authorize that action.

## Release and data distribution

Release the consolidated code as `caselaw-guard` 0.2.0. The release notes must
describe the repository consolidation, new index format and legacy support.

Do not publish any package named `openbench`. The `caselaw-guard` wheel must not
declare an OpenBench dependency or contain an `openbench` import package.

Publish the full Australian index separately from the wheel. Use index-specific
release tags and assets so data can update without forcing a Python package
release. Each asset must include its index version, dataset revision, licence,
attribution and SHA-256 digest.

Keep a small attributed fixture index in the repository and source distribution
for offline tests and the README smoke test.

## Testing

### Unit and contract tests

The consolidated suite covers:

1. normalization, including whitespace, case, pinpoints, years and
   alphanumeric court codes;
2. extraction of every accepted form, with exact spans and one result per
   citation;
3. canonical and legacy index loading, validation, deduplication and migration;
4. status, authority, candidate and provenance mapping; and
5. parity between the adapter and Australian REST route.

### End-to-end tests

Run the CLI against the fixture index with these inputs:

| Input | Expected extracted results | Expected status |
| --- | ---: | --- |
| `[1992] HCA 23` | 1 | `VERIFIED` |
| `[1992] HCA 23 at [10]` | 1 | `VERIFIED` |
| `(1992) HCA 23` | 1 | `VERIFIED` |
| `1992 HCA 23` | 1 | `VERIFIED` |
| `[1992] hca 23` | 1 | `VERIFIED` |
| `[2099] HCA 999` | 1 | `NOT_FOUND` |
| `(1992) 175 CLR 1` | 0 Australian neutral citations | unchanged reported-citation handling |

Also verify the same canonical citation through `POST /verify`, the Australian
lookup route and the MCP tool.

### CI and packaging

CI must:

- run tests on Python 3.11, 3.12 and 3.13;
- run lint, formatting, typing and static schema validation;
- build the source distribution and wheel;
- smoke-test the wheel in a clean environment; and
- confirm that neither distribution contains or depends on `openbench`.

## Rollout sequence

### Phase 1: establish the contract

Add failing extraction and lookup contract tests before moving production code.
Record the current fixture outputs for canonical and legacy indexes.

### Phase 2: import and consolidate

Import OpenBench's history. Move the modules, create the single lookup service
and switch the Australian adapter to it. Keep all work on the integration
branch until the consolidated suite passes.

### Phase 3: preserve interfaces

Wire the CLI, REST API and MCP server to the consolidated service. Add legacy
loading and migration. Update the README, changelog, data notices, release guide
and self-hosting instructions.

### Phase 4: release and retire

Publish CaseLaw Guard 0.2.0 and an attributed index artifact. Verify installation
and offline lookup from the published wheel. Ask for separate approval, then
replace the OpenBench README and archive its repository.

## Risks and controls

| Risk | Control |
| --- | --- |
| History is lost during consolidation | import with `git subtree` without `--squash` and verify ancestry |
| Accepted variants still bypass verification | assert extraction count, span and status in end-to-end tests |
| Court coverage regresses | merge both court-code sets and test benchmark and alphanumeric codes |
| Attribution disappears on unsuccessful lookups | populate `provider_metadata` from the loaded index for every status |
| Existing indexes stop working | load the legacy format and provide an explicit migration command |

## Acceptance criteria

The consolidation is complete when:

1. one `caselaw-guard` source tree owns Australian extraction, normalization,
   index building, lookup, API and provenance logic;
2. a clean `pip install caselaw-guard==0.2.0` supports the offline Australian
   smoke test without installing or importing `openbench`;
3. every end-to-end input in this specification produces the expected result
   count and status on Python 3.11, 3.12 and 3.13;
4. canonical and legacy indexes return matching authorities, with honest
   provider metadata and complete attribution; and
5. the published wheel, source distribution and index artifact pass their
   release checks before any OpenBench archival action.
