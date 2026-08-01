# openbench v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build openbench v1 — a self-hostable Python API that resolves Australian neutral citations against an in-memory JSON index built from the Isaacus Open Australian Legal Corpus, returning verified / not-found / ambiguous / unsupported_format with full provenance.

**Architecture:** FastAPI service over a `IndexStore` interface backed by an in-memory dict loaded from a single JSON file at startup. Citation parsing is a pure function in `normalization.py`. The index is built by `index_builder.py` from a JSONL corpus snapshot, deduped on `(normalized_citation, case_name, date)`, and validated against `schemas/index.schema.json`. CLI (`openbench`) wraps build/serve/stats. Apache-2.0 for code; CC-BY-4.0 attribution for index data threaded through `DATA_SOURCES.md`, `/v1/au/index/metadata`, and every API response's `provenance` block.

**Tech Stack:** Python 3.12, `uv` (env + lockfile + build), FastAPI, Pydantic v2, `typer` (CLI), `jsonschema`, `pytest`, `httpx` (FastAPI `TestClient`), `ruff`, `mypy --strict`. GitHub Actions for CI and release.

**Spec:** [`../specs/2026-05-01-openbench-design.md`](../specs/2026-05-01-openbench-design.md). When this plan and the spec disagree, fix the disagreement before continuing — do not silently diverge.

**Working tree:** Plan was authored on `main` of an empty repo. Recommend creating a worktree `feat/v1` before executing tasks: `git worktree add ../openbench-v1 -b feat/v1`.

---

## File map

Files created during this plan (grouped by responsibility):

| File | Responsibility |
|---|---|
| `pyproject.toml` | Package metadata, dependencies, scripts, ruff/mypy config |
| `.python-version` | Pin to 3.12 |
| `.gitignore` | Standard Python + uv ignores |
| `LICENSE` | Apache-2.0 (code) |
| `LICENSE-DATA` | CC-BY-4.0 NOTICE for index artifacts |
| `README.md` | Quickstart, disclaimers, attribution, links |
| `DATA_SOURCES.md` | Source provenance + CC-BY-4.0 attribution text |
| `CODE_OF_CONDUCT.md` | Contributor Covenant 2.1 |
| `CONTRIBUTING.md` | Dev setup, test commands, PR rules |
| `SECURITY.md` | Disclosure contact + scope |
| `docs/api.md` | Endpoint reference |
| `docs/self-hosting.md` | Build index, configure env, run server |
| `schemas/index.schema.json` | JSON Schema for index files |
| `data/fixtures/corpus-fixture.jsonl` | ~6 corpus records used by builder tests |
| `data/fixtures/index.json` | ~50-case fixture index used by API tests / quickstart |
| `src/openbench/__init__.py` | Package version |
| `src/openbench/courts.py` | `court_code → (name, jurisdiction)` mapping |
| `src/openbench/normalization.py` | Pure citation parser/normaliser |
| `src/openbench/models.py` | Pydantic models for entries, responses, metadata |
| `src/openbench/index_store.py` | Load JSON, indexed lookup, metadata, stats |
| `src/openbench/index_builder.py` | Corpus JSONL → index dict (filter, dedup, validate) |
| `src/openbench/api.py` | FastAPI app + routes |
| `src/openbench/cli.py` | `openbench index build|stats`, `openbench serve` |
| `tests/unit/test_courts.py` | Court code mapping |
| `tests/unit/test_normalization.py` | Parser / normaliser cases |
| `tests/unit/test_models.py` | Pydantic round-trip + validation |
| `tests/unit/test_index_store.py` | Lookup, metadata, stats, error paths |
| `tests/unit/test_index_builder.py` | Filter, dedup, ambiguity, schema |
| `tests/integration/test_api_health.py` | `/health` |
| `tests/integration/test_api_lookup.py` | `/v1/au/citations/{...}` paths |
| `tests/integration/test_api_metadata.py` | `/v1/au/index/metadata`, `/v1/au/index/stats`, `index_unavailable` |
| `tests/integration/test_cli.py` | CLI build/stats/serve smoke |
| `.github/workflows/ci.yml` | Lint, type, test, build on push/PR |
| `.github/workflows/release.yml` | Build full index from corpus, attach to tag |
| `.github/ISSUE_TEMPLATE/data-error.md` | Wrong/missing case in index |
| `.github/ISSUE_TEMPLATE/source-request.md` | New source proposal |

---

## Task 1: Project scaffolding (uv, ruff, mypy, pytest)

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `.gitignore`
- Create: `src/openbench/__init__.py`
- Create: `src/openbench/py.typed`
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`

- [ ] **Step 1.1: Pin Python and ignore generated files**

`/Users/l0cka/Projects/openbench/.python-version`:
```
3.12
```

`/Users/l0cka/Projects/openbench/.gitignore`:
```
# Python
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# uv / build
.venv/
dist/
build/
*.whl
*.tar.gz

# Editor / OS
.DS_Store
.idea/
.vscode/

# Local index data (releases live as GitHub Release assets)
/index.json
/index-*.json
/index-*.json.zst

# Cached HF dataset downloads
/.cache/
```

- [ ] **Step 1.2: Write `pyproject.toml` with deps, scripts, lint/type config**

`/Users/l0cka/Projects/openbench/pyproject.toml`:
```toml
[project]
name = "openbench"
version = "0.1.0"
description = "Open Australian case-law citation lookup API"
readme = "README.md"
requires-python = ">=3.12"
license = { file = "LICENSE" }
authors = [{ name = "openbench contributors" }]
keywords = ["law", "australia", "citation", "case-law", "api"]
classifiers = [
  "Development Status :: 3 - Alpha",
  "Framework :: FastAPI",
  "License :: OSI Approved :: Apache Software License",
  "Programming Language :: Python :: 3.12",
  "Topic :: Internet :: WWW/HTTP",
  "Topic :: Sociology :: Law",
]

dependencies = [
  "fastapi>=0.115",
  "pydantic>=2.7",
  "typer>=0.12",
  "uvicorn>=0.30",
  "jsonschema>=4.22",
]

[project.optional-dependencies]
dev = [
  "pytest>=8",
  "httpx>=0.27",
  "mypy>=1.10",
  "ruff>=0.5",
  "twine>=5",
]

[project.scripts]
openbench = "openbench.cli:app"

[project.urls]
Homepage = "https://github.com/danielkurdi/openbench"
Issues = "https://github.com/danielkurdi/openbench/issues"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/openbench"]

[tool.ruff]
line-length = 100
target-version = "py312"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "PL", "RUF"]
ignore = ["PLR0913"]  # allow many args in fastapi handlers

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["PLR2004"]  # magic numbers in tests are fine

[tool.mypy]
python_version = "3.12"
strict = true
files = ["src/openbench"]
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q --strict-markers"
```

- [ ] **Step 1.3: Create the package and test scaffolding**

`/Users/l0cka/Projects/openbench/src/openbench/__init__.py`:
```python
"""openbench: open Australian case-law citation lookup API."""

__version__ = "0.1.0"
```

`/Users/l0cka/Projects/openbench/src/openbench/py.typed`: (empty file)

`/Users/l0cka/Projects/openbench/tests/__init__.py`: (empty)
`/Users/l0cka/Projects/openbench/tests/unit/__init__.py`: (empty)
`/Users/l0cka/Projects/openbench/tests/integration/__init__.py`: (empty)

- [ ] **Step 1.4: Sync env and confirm tools work**

```bash
cd /Users/l0cka/Projects/openbench
uv sync --extra dev
uv run python -c "import openbench; print(openbench.__version__)"
uv run ruff check .
uv run mypy
uv run pytest -q
```

Expected:
- `0.1.0` printed.
- ruff: `All checks passed!`
- mypy: `Success: no issues found` (no source files yet).
- pytest: `no tests ran` (zero failures).

- [ ] **Step 1.5: Commit**

```bash
git add pyproject.toml .python-version .gitignore src tests
git commit -m "chore: scaffold project (uv, ruff, mypy, pytest, src layout)"
```

---

## Task 2: Licence files (Apache-2.0 + CC-BY-4.0 NOTICE)

**Files:**
- Create: `LICENSE`
- Create: `LICENSE-DATA`

- [ ] **Step 2.1: Add Apache-2.0**

Download the official Apache-2.0 text and save it to `LICENSE`. Standard practice: copy from <https://www.apache.org/licenses/LICENSE-2.0.txt> verbatim. The first line of `LICENSE` must read exactly:
```
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/
```
Replace any `[yyyy]` and `[name of copyright owner]` placeholders in the file's APPENDIX section with `2026 openbench contributors`.

- [ ] **Step 2.2: Add CC-BY-4.0 NOTICE for data artifacts**

`/Users/l0cka/Projects/openbench/LICENSE-DATA`:
```
openbench Index Data — CC-BY-4.0 NOTICE
=======================================

This NOTICE applies to:
  - data/fixtures/index.json (in this repository)
  - any index-*.json or index-*.json.zst artifact published as a GitHub
    Release asset of the openbench project.

These index files are derived works of the Open Australian Legal Corpus by
Isaacus, available at:
  https://huggingface.co/datasets/isaacus/open-australian-legal-corpus

The Open Australian Legal Corpus is licensed under the Creative Commons
Attribution 4.0 International Licence (CC-BY-4.0):
  https://creativecommons.org/licenses/by/4.0/

Modifications by openbench:
  - Filtered to court decisions only.
  - Extracted metadata (citation, case name, court, jurisdiction, date,
    source URL) and discarded full judgment text.
  - Normalised neutral citations to canonical form.
  - Deduplicated records sharing (normalised_citation, case_name, date).
  - Compiled into a single JSON index file.

Attribution string (must accompany any redistribution of the index):
  "Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by openbench
  (metadata extraction, normalisation, deduplication)."

The openbench source code itself is licensed under Apache-2.0; see LICENSE.
```

- [ ] **Step 2.3: Commit**

```bash
git add LICENSE LICENSE-DATA
git commit -m "docs: add Apache-2.0 (code) and CC-BY-4.0 NOTICE (index data)"
```

---

## Task 3: Court code mapping

**Files:**
- Create: `src/openbench/courts.py`
- Test: `tests/unit/test_courts.py`

- [ ] **Step 3.1: Write failing tests**

`/Users/l0cka/Projects/openbench/tests/unit/test_courts.py`:
```python
from openbench.courts import resolve_court


def test_known_federal_court_resolves() -> None:
    assert resolve_court("HCA") == ("High Court of Australia", "cth")


def test_known_state_court_resolves() -> None:
    assert resolve_court("NSWSC") == ("Supreme Court of New South Wales", "nsw")


def test_unknown_court_returns_nones() -> None:
    assert resolve_court("ZZZZ") == (None, None)


def test_resolve_court_is_case_sensitive_on_input() -> None:
    # callers are expected to upper-case before calling; mapping is upper-case only
    assert resolve_court("hca") == (None, None)
```

- [ ] **Step 3.2: Run test, verify failure**

```bash
uv run pytest tests/unit/test_courts.py -v
```
Expected: `ModuleNotFoundError: No module named 'openbench.courts'`.

- [ ] **Step 3.3: Implement `courts.py`**

`/Users/l0cka/Projects/openbench/src/openbench/courts.py`:
```python
"""Static mapping from Australian court codes to (name, jurisdiction)."""

from __future__ import annotations

# Jurisdiction codes follow Australian conventions: cth, nsw, vic, qld, wa, sa, tas, act, nt.
COURTS: dict[str, tuple[str, str]] = {
    # Commonwealth
    "HCA": ("High Court of Australia", "cth"),
    "FCAFC": ("Full Court of the Federal Court of Australia", "cth"),
    "FCA": ("Federal Court of Australia", "cth"),
    "FCCA": ("Federal Circuit Court of Australia", "cth"),
    "FedCFamC1A": ("Federal Circuit and Family Court of Australia (Division 1) Appellate", "cth"),
    "FedCFamC1F": ("Federal Circuit and Family Court of Australia (Division 1)", "cth"),
    "FedCFamC2F": ("Federal Circuit and Family Court of Australia (Division 2)", "cth"),
    "FamCA": ("Family Court of Australia", "cth"),
    "FamCAFC": ("Full Court of the Family Court of Australia", "cth"),
    "AATA": ("Administrative Appeals Tribunal", "cth"),
    # New South Wales
    "NSWCA": ("Court of Appeal of New South Wales", "nsw"),
    "NSWCCA": ("Court of Criminal Appeal of New South Wales", "nsw"),
    "NSWSC": ("Supreme Court of New South Wales", "nsw"),
    "NSWDC": ("District Court of New South Wales", "nsw"),
    "NSWLC": ("Local Court of New South Wales", "nsw"),
    # Victoria
    "VSCA": ("Court of Appeal of Victoria", "vic"),
    "VSC": ("Supreme Court of Victoria", "vic"),
    "VCC": ("County Court of Victoria", "vic"),
    # Queensland
    "QCA": ("Court of Appeal of Queensland", "qld"),
    "QSC": ("Supreme Court of Queensland", "qld"),
    "QDC": ("District Court of Queensland", "qld"),
    # Western Australia
    "WASCA": ("Court of Appeal of Western Australia", "wa"),
    "WASC": ("Supreme Court of Western Australia", "wa"),
    # South Australia
    "SASCFC": ("Full Court of the Supreme Court of South Australia", "sa"),
    "SASC": ("Supreme Court of South Australia", "sa"),
    # Tasmania
    "TASFC": ("Full Court of the Supreme Court of Tasmania", "tas"),
    "TASSC": ("Supreme Court of Tasmania", "tas"),
    # ACT
    "ACTCA": ("Court of Appeal of the Australian Capital Territory", "act"),
    "ACTSC": ("Supreme Court of the Australian Capital Territory", "act"),
    # Northern Territory
    "NTCA": ("Court of Appeal of the Northern Territory", "nt"),
    "NTSC": ("Supreme Court of the Northern Territory", "nt"),
}


def resolve_court(court_code: str) -> tuple[str | None, str | None]:
    """Return (court_name, jurisdiction) for a court code, or (None, None) if unknown.

    The mapping is upper-case only. Callers should normalise input to upper-case
    before calling (the citation parser does this).
    """
    info = COURTS.get(court_code)
    if info is None:
        return (None, None)
    return info
```

- [ ] **Step 3.4: Run tests, verify pass**

```bash
uv run pytest tests/unit/test_courts.py -v
uv run mypy
uv run ruff check .
```
Expected: 4 passed; mypy and ruff clean.

- [ ] **Step 3.5: Commit**

```bash
git add src/openbench/courts.py tests/unit/test_courts.py
git commit -m "feat(courts): add court code -> (name, jurisdiction) mapping"
```

---

## Task 4: Citation normalisation

**Files:**
- Create: `src/openbench/normalization.py`
- Test: `tests/unit/test_normalization.py`

- [ ] **Step 4.1: Write failing tests covering every accepted form and rejection**

`/Users/l0cka/Projects/openbench/tests/unit/test_normalization.py`:
```python
import pytest

from openbench.normalization import (
    NormalizationResult,
    extract_case_name_and_citation,
    normalize_citation,
)


# Accepted forms — must all normalise to "[1992] HCA 23"
ACCEPTED = [
    "[1992] HCA 23",
    "(1992) HCA 23",
    "1992 HCA 23",
    "[1992]  HCA   23",
    "  [1992] HCA 23  ",
    "[1992] hca 23",
    "[1992] HCA 23 [10]",
    "[1992] HCA 23 at [10]",
    "[1992] HCA 23, [10]",
]


@pytest.mark.parametrize("raw", ACCEPTED)
def test_canonical_and_variants_normalise(raw: str) -> None:
    result = normalize_citation(raw)
    assert result.ok is True
    assert result.normalized == "[1992] HCA 23"
    assert result.year == 1992
    assert result.court_code == "HCA"
    assert result.number == 23


REJECTED = [
    "",
    "Mabo",
    "(1992) 175 CLR 1",  # reported citation rejected in v1
    "[abcd] HCA 23",
    "[1992] HCA",
    "[1992] HCA abc",
    "[1899] HCA 1",  # below year floor
    "[3000] HCA 1",  # above year ceiling
    "[1992] 23",     # missing court
    "HCA 23",        # missing year
]


@pytest.mark.parametrize("raw", REJECTED)
def test_invalid_inputs_rejected(raw: str) -> None:
    result = normalize_citation(raw)
    assert result.ok is False
    assert result.normalized is None


def test_extract_case_name_strips_neutral_citation() -> None:
    raw = "Mabo v Queensland (No 2) [1992] HCA 23"
    case_name, normalized = extract_case_name_and_citation(raw)
    assert case_name == "Mabo v Queensland (No 2)"
    assert normalized == "[1992] HCA 23"


def test_extract_case_name_handles_paren_year_form() -> None:
    case_name, normalized = extract_case_name_and_citation("Foo v Bar (1992) HCA 23")
    assert case_name == "Foo v Bar"
    assert normalized == "[1992] HCA 23"


def test_extract_case_name_returns_none_when_no_citation() -> None:
    case_name, normalized = extract_case_name_and_citation("Mabo")
    assert case_name is None
    assert normalized is None


def test_year_ceiling_uses_current_year_plus_one() -> None:
    from datetime import datetime
    next_year = datetime.now().year + 1
    res = normalize_citation(f"[{next_year}] HCA 1")
    assert res.ok is True
    too_far = normalize_citation(f"[{next_year + 1}] HCA 1")
    assert too_far.ok is False


def test_normalization_result_is_immutable_dataclass() -> None:
    res = normalize_citation("[1992] HCA 23")
    with pytest.raises((AttributeError, TypeError)):
        res.normalized = "[2000] HCA 1"  # type: ignore[misc]
```

- [ ] **Step 4.2: Run tests, verify failure**

```bash
uv run pytest tests/unit/test_normalization.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 4.3: Implement `normalization.py`**

`/Users/l0cka/Projects/openbench/src/openbench/normalization.py`:
```python
"""Australian neutral citation parser and normaliser.

Accepts canonical `[YYYY] COURT N` plus common variants:
  - paren-year: `(1992) HCA 23`
  - bare year: `1992 HCA 23`
  - extra whitespace, surrounding whitespace, lower-case court code
  - trailing pinpoint paragraph: `[1992] HCA 23 [10]`, `... at [10]`, `..., [10]`

Rejects everything else (including reported citations like
`(1992) 175 CLR 1`) with `ok=False`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

# Year [or (year), or bare year] + COURT (alpha) + N + optional pinpoint.
_CITATION_RE = re.compile(
    r"""
    ^\s*
    (?:\[(?P<y1>\d{4})\] | \((?P<y2>\d{4})\) | (?P<y3>\d{4}))
    \s+
    (?P<court>[A-Za-z]+)
    \s+
    (?P<num>\d+)
    (?:                              # optional pinpoint
        \s*[, ]?\s*
        (?:at\s+)?
        \[\d+\]
    )?
    \s*$
    """,
    re.VERBOSE,
)

_YEAR_FLOOR = 1900


@dataclass(frozen=True)
class NormalizationResult:
    """Outcome of `normalize_citation`. `ok=False` means the rest is `None`."""

    ok: bool
    normalized: str | None = None
    year: int | None = None
    court_code: str | None = None
    number: int | None = None
    raw: str = field(default="")


def _year_ceiling() -> int:
    return datetime.now().year + 1


def normalize_citation(raw: str) -> NormalizationResult:
    """Parse and normalise an Australian neutral citation.

    Returns NormalizationResult(ok=True, normalized="[YYYY] COURT N", ...) on success,
    NormalizationResult(ok=False, raw=raw) on any rejection.
    """
    if not isinstance(raw, str) or not raw.strip():
        return NormalizationResult(ok=False, raw=raw)

    m = _CITATION_RE.match(raw)
    if m is None:
        return NormalizationResult(ok=False, raw=raw)

    year_str = m.group("y1") or m.group("y2") or m.group("y3")
    year = int(year_str)
    if year < _YEAR_FLOOR or year > _year_ceiling():
        return NormalizationResult(ok=False, raw=raw)

    court_code = m.group("court").upper()
    number = int(m.group("num"))
    normalized = f"[{year}] {court_code} {number}"

    return NormalizationResult(
        ok=True,
        normalized=normalized,
        year=year,
        court_code=court_code,
        number=number,
        raw=raw,
    )


# Match a neutral citation appearing inside a longer string (e.g. corpus citation field).
_CITATION_INSIDE_RE = re.compile(
    r"""
    (?:\[(?P<y1>\d{4})\] | \((?P<y2>\d{4})\))
    \s+
    (?P<court>[A-Za-z]+)
    \s+
    (?P<num>\d+)
    """,
    re.VERBOSE,
)


def extract_case_name_and_citation(raw: str) -> tuple[str | None, str | None]:
    """Split `Mabo v Queensland (No 2) [1992] HCA 23` into (case_name, normalised).

    Returns (None, None) if no neutral citation is found in the string.
    Pinpoint suffixes after the citation, if any, are dropped.
    """
    if not isinstance(raw, str):
        return (None, None)

    m = _CITATION_INSIDE_RE.search(raw)
    if m is None:
        return (None, None)

    year_str = m.group("y1") or m.group("y2")
    year = int(year_str)
    if year < _YEAR_FLOOR or year > _year_ceiling():
        return (None, None)

    court_code = m.group("court").upper()
    number = int(m.group("num"))
    normalized = f"[{year}] {court_code} {number}"

    case_name = raw[: m.start()].strip()
    case_name = re.sub(r"\s+", " ", case_name)
    if not case_name:
        return (None, normalized)
    return (case_name, normalized)
```

- [ ] **Step 4.4: Run tests, verify pass**

```bash
uv run pytest tests/unit/test_normalization.py -v
uv run mypy
uv run ruff check .
```
Expected: all pass; clean.

- [ ] **Step 4.5: Commit**

```bash
git add src/openbench/normalization.py tests/unit/test_normalization.py
git commit -m "feat(normalization): parse and normalise Australian neutral citations"
```

---

## Task 5: Pydantic models for entries, responses, metadata

**Files:**
- Create: `src/openbench/models.py`
- Test: `tests/unit/test_models.py`

- [ ] **Step 5.1: Write failing tests**

`/Users/l0cka/Projects/openbench/tests/unit/test_models.py`:
```python
from datetime import date

import pytest
from pydantic import ValidationError

from openbench.models import (
    Candidate,
    IndexEntry,
    IndexFile,
    IndexMetadata,
    LookupResponse,
    Status,
)


def test_index_entry_round_trip() -> None:
    entry = IndexEntry(
        normalized_citation="[1992] HCA 23",
        citation="Mabo v Queensland (No 2) [1992] HCA 23",
        case_name="Mabo v Queensland (No 2)",
        court="High Court of Australia",
        court_code="HCA",
        jurisdiction="cth",
        date=date(1992, 6, 3),
        source_urls=["https://example.org/mabo"],
        source="open-australian-legal-corpus",
        source_record_ids=["abc"],
        indexed_at=date(2026, 5, 1),
        license="CC-BY-4.0",
    )
    dumped = entry.model_dump(mode="json")
    assert dumped["normalized_citation"] == "[1992] HCA 23"
    assert dumped["date"] == "1992-06-03"
    again = IndexEntry.model_validate(dumped)
    assert again == entry


def test_index_entry_requires_at_least_one_source_url() -> None:
    with pytest.raises(ValidationError):
        IndexEntry(
            normalized_citation="[1992] HCA 23",
            citation="x",
            case_name="x",
            court_code="HCA",
            date=date(1992, 6, 3),
            source_urls=[],  # invalid
            source="open-australian-legal-corpus",
            source_record_ids=["abc"],
            indexed_at=date(2026, 5, 1),
            license="CC-BY-4.0",
        )


def test_lookup_response_verified_serialises() -> None:
    resp = LookupResponse(
        citation="[1992] HCA 23",
        normalized_citation="[1992] HCA 23",
        status=Status.verified,
        case_name="Mabo v Queensland (No 2)",
        court="High Court of Australia",
        court_code="HCA",
        jurisdiction="cth",
        date=date(1992, 6, 3),
        source_urls=["https://example.org/mabo"],
        sources=["open-australian-legal-corpus"],
        confidence=1.0,
        candidates=[],
    )
    j = resp.model_dump(mode="json", exclude_none=True)
    assert j["status"] == "verified"
    assert j["confidence"] == 1.0
    assert j["candidates"] == []


def test_lookup_response_ambiguous_omits_top_level_case_fields() -> None:
    resp = LookupResponse(
        citation="[2024] NSWSC 9999",
        normalized_citation="[2024] NSWSC 9999",
        status=Status.ambiguous,
        confidence=0.5,
        candidates=[
            Candidate(
                case_name="First",
                court="Supreme Court of New South Wales",
                court_code="NSWSC",
                jurisdiction="nsw",
                date=date(2024, 1, 1),
                source_urls=["https://example.org/1"],
            ),
            Candidate(
                case_name="Second",
                court="Supreme Court of New South Wales",
                court_code="NSWSC",
                jurisdiction="nsw",
                date=date(2024, 1, 15),
                source_urls=["https://example.org/2"],
            ),
        ],
    )
    j = resp.model_dump(mode="json", exclude_none=True)
    assert "case_name" not in j
    assert "court" not in j
    assert "date" not in j
    assert len(j["candidates"]) == 2


def test_lookup_response_unsupported_format_minimal() -> None:
    resp = LookupResponse(
        citation="Mabo",
        status=Status.unsupported_format,
        confidence=0.0,
        candidates=[],
    )
    j = resp.model_dump(mode="json", exclude_none=True)
    assert j["status"] == "unsupported_format"
    assert "normalized_citation" not in j


def test_index_file_with_single_and_array_entries() -> None:
    f = IndexFile.model_validate(
        {
            "index_version": "2026-05-01",
            "generated_at": "2026-05-01T00:00:00Z",
            "builder_version": "0.1.0",
            "source": "open-australian-legal-corpus",
            "license": "CC-BY-4.0",
            "record_count": 2,
            "entries": {
                "[1992] HCA 23": {
                    "normalized_citation": "[1992] HCA 23",
                    "citation": "Mabo v Queensland (No 2) [1992] HCA 23",
                    "case_name": "Mabo v Queensland (No 2)",
                    "court": "High Court of Australia",
                    "court_code": "HCA",
                    "jurisdiction": "cth",
                    "date": "1992-06-03",
                    "source_urls": ["https://example.org/mabo"],
                    "source": "open-australian-legal-corpus",
                    "source_record_ids": ["abc"],
                    "indexed_at": "2026-05-01",
                    "license": "CC-BY-4.0",
                },
                "[2024] NSWSC 9999": [
                    {
                        "normalized_citation": "[2024] NSWSC 9999",
                        "citation": "First [2024] NSWSC 9999",
                        "case_name": "First",
                        "court_code": "NSWSC",
                        "court": "Supreme Court of New South Wales",
                        "jurisdiction": "nsw",
                        "date": "2024-01-01",
                        "source_urls": ["https://example.org/1"],
                        "source": "open-australian-legal-corpus",
                        "source_record_ids": ["a"],
                        "indexed_at": "2026-05-01",
                        "license": "CC-BY-4.0",
                    },
                    {
                        "normalized_citation": "[2024] NSWSC 9999",
                        "citation": "Second [2024] NSWSC 9999",
                        "case_name": "Second",
                        "court_code": "NSWSC",
                        "court": "Supreme Court of New South Wales",
                        "jurisdiction": "nsw",
                        "date": "2024-01-15",
                        "source_urls": ["https://example.org/2"],
                        "source": "open-australian-legal-corpus",
                        "source_record_ids": ["b"],
                        "indexed_at": "2026-05-01",
                        "license": "CC-BY-4.0",
                    },
                ],
            },
        }
    )
    assert f.record_count == 2
    assert isinstance(f.entries["[1992] HCA 23"], IndexEntry)
    assert isinstance(f.entries["[2024] NSWSC 9999"], list)


def test_index_metadata_round_trip() -> None:
    md = IndexMetadata(
        index_version="2026-05-01",
        generated_at="2026-05-01T00:00:00Z",
        record_count=42,
        sources=["open-australian-legal-corpus"],
        license="CC-BY-4.0",
        builder_version="0.1.0",
        attribution="...",
        dataset="isaacus/open-australian-legal-corpus",
        dataset_version="abc123",
    )
    j = md.model_dump(mode="json")
    assert IndexMetadata.model_validate(j) == md
```

- [ ] **Step 5.2: Run tests, verify failure**

```bash
uv run pytest tests/unit/test_models.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 5.3: Implement `models.py`**

`/Users/l0cka/Projects/openbench/src/openbench/models.py`:
```python
"""Pydantic models for the openbench API and index file."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

ATTRIBUTION = (
    "Open Australian Legal Corpus by Isaacus, CC-BY-4.0, "
    "modified by openbench (metadata extraction)."
)


class Status(str, Enum):
    verified = "verified"
    not_found = "not_found"
    ambiguous = "ambiguous"
    unsupported_format = "unsupported_format"
    index_unavailable = "index_unavailable"
    provider_error = "provider_error"


class IndexEntry(BaseModel):
    """A single deduplicated case entry in the index."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    normalized_citation: str
    citation: str
    case_name: str
    court: str | None = None
    court_code: str
    jurisdiction: str | None = None
    date: date
    source_urls: Annotated[list[str], Field(min_length=1)]
    source: str
    source_record_ids: Annotated[list[str], Field(min_length=1)]
    indexed_at: date
    license: str


class Candidate(BaseModel):
    """A candidate entry returned for ambiguous lookups."""

    model_config = ConfigDict(extra="forbid")

    case_name: str
    court: str | None = None
    court_code: str
    jurisdiction: str | None = None
    date: date
    source_urls: list[str]


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index_version: str | None = None
    source: str | None = None
    license: str | None = None
    dataset: str | None = None
    attribution: str | None = None


class LookupResponse(BaseModel):
    """Response from /v1/au/citations/{citation}."""

    model_config = ConfigDict(extra="forbid")

    citation: str
    normalized_citation: str | None = None
    status: Status
    case_name: str | None = None
    court: str | None = None
    court_code: str | None = None
    jurisdiction: str | None = None
    date: date | None = None
    source_urls: list[str] | None = None
    sources: list[str] | None = None
    confidence: float
    candidates: list[Candidate]
    provenance: Provenance | None = None


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    index_loaded: bool


class IndexMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index_version: str
    generated_at: str
    record_count: int
    sources: list[str]
    license: str
    builder_version: str
    attribution: str
    dataset: str
    dataset_version: str


class IndexStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_count: int
    ambiguous_count: int
    by_court: dict[str, int]
    by_year: dict[str, int]
    earliest_date: date | None
    latest_date: date | None


class IndexFile(BaseModel):
    """Top-level structure of a serialised index file on disk."""

    model_config = ConfigDict(extra="forbid")

    index_version: str
    generated_at: str
    builder_version: str
    source: str
    license: str
    record_count: int
    entries: dict[str, IndexEntry | list[IndexEntry]]
```

- [ ] **Step 5.4: Run tests, verify pass**

```bash
uv run pytest tests/unit/test_models.py -v
uv run mypy
uv run ruff check .
```
Expected: 7 passed; clean.

- [ ] **Step 5.5: Commit**

```bash
git add src/openbench/models.py tests/unit/test_models.py
git commit -m "feat(models): add pydantic models for entries, responses, metadata"
```

---

## Task 6: JSON Schema for index files

**Files:**
- Create: `schemas/index.schema.json`
- Test: extend `tests/unit/test_models.py` (no new file)

- [ ] **Step 6.1: Write the JSON Schema**

`/Users/l0cka/Projects/openbench/schemas/index.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/danielkurdi/openbench/schemas/index.schema.json",
  "title": "openbench index file",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "index_version",
    "generated_at",
    "builder_version",
    "source",
    "license",
    "record_count",
    "entries"
  ],
  "properties": {
    "index_version": { "type": "string" },
    "generated_at": { "type": "string", "format": "date-time" },
    "builder_version": { "type": "string" },
    "source": { "type": "string" },
    "license": { "type": "string" },
    "record_count": { "type": "integer", "minimum": 0 },
    "entries": {
      "type": "object",
      "additionalProperties": {
        "oneOf": [
          { "$ref": "#/$defs/entry" },
          { "type": "array", "minItems": 2, "items": { "$ref": "#/$defs/entry" } }
        ]
      }
    }
  },
  "$defs": {
    "entry": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "normalized_citation",
        "citation",
        "case_name",
        "court_code",
        "date",
        "source_urls",
        "source",
        "source_record_ids",
        "indexed_at",
        "license"
      ],
      "properties": {
        "normalized_citation": { "type": "string", "pattern": "^\\[\\d{4}\\] [A-Z]+ \\d+$" },
        "citation": { "type": "string" },
        "case_name": { "type": "string" },
        "court": { "type": ["string", "null"] },
        "court_code": { "type": "string" },
        "jurisdiction": { "type": ["string", "null"] },
        "date": { "type": "string", "format": "date" },
        "source_urls": { "type": "array", "items": { "type": "string", "format": "uri" }, "minItems": 1 },
        "source": { "type": "string" },
        "source_record_ids": { "type": "array", "items": { "type": "string" }, "minItems": 1 },
        "indexed_at": { "type": "string", "format": "date" },
        "license": { "type": "string" }
      }
    }
  }
}
```

- [ ] **Step 6.2: Add a test that the schema accepts a valid file and rejects an invalid one**

Append to `/Users/l0cka/Projects/openbench/tests/unit/test_models.py`:
```python
import json
from pathlib import Path

import jsonschema


SCHEMA_PATH = Path(__file__).parent.parent.parent / "schemas" / "index.schema.json"


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def test_schema_accepts_minimal_valid_index() -> None:
    schema = _load_schema()
    valid = {
        "index_version": "2026-05-01",
        "generated_at": "2026-05-01T00:00:00Z",
        "builder_version": "0.1.0",
        "source": "open-australian-legal-corpus",
        "license": "CC-BY-4.0",
        "record_count": 1,
        "entries": {
            "[1992] HCA 23": {
                "normalized_citation": "[1992] HCA 23",
                "citation": "Mabo v Queensland (No 2) [1992] HCA 23",
                "case_name": "Mabo v Queensland (No 2)",
                "court": "High Court of Australia",
                "court_code": "HCA",
                "jurisdiction": "cth",
                "date": "1992-06-03",
                "source_urls": ["https://example.org/mabo"],
                "source": "open-australian-legal-corpus",
                "source_record_ids": ["abc"],
                "indexed_at": "2026-05-01",
                "license": "CC-BY-4.0"
            }
        }
    }
    jsonschema.validate(valid, schema)


def test_schema_rejects_bad_normalized_citation() -> None:
    schema = _load_schema()
    bad = {
        "index_version": "2026-05-01",
        "generated_at": "2026-05-01T00:00:00Z",
        "builder_version": "0.1.0",
        "source": "open-australian-legal-corpus",
        "license": "CC-BY-4.0",
        "record_count": 1,
        "entries": {
            "(1992) 175 CLR 1": {
                "normalized_citation": "(1992) 175 CLR 1",
                "citation": "Mabo (1992) 175 CLR 1",
                "case_name": "Mabo",
                "court_code": "HCA",
                "date": "1992-06-03",
                "source_urls": ["https://example.org/mabo"],
                "source": "open-australian-legal-corpus",
                "source_record_ids": ["abc"],
                "indexed_at": "2026-05-01",
                "license": "CC-BY-4.0"
            }
        }
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)
```

- [ ] **Step 6.3: Run, expect pass**

```bash
uv run pytest tests/unit/test_models.py -v
```
Expected: original 7 + 2 new = 9 passed.

- [ ] **Step 6.4: Commit**

```bash
git add schemas/index.schema.json tests/unit/test_models.py
git commit -m "feat(schema): add JSON Schema for index files + validation tests"
```

---

## Task 7: Fixture corpus + fixture index

**Files:**
- Create: `data/fixtures/corpus-fixture.jsonl`
- Create: `data/fixtures/index.json`

The fixture index is hand-written and is the source of truth for API integration tests. The fixture corpus is a slice used by the index-builder tests; the builder must turn it into something equivalent to the fixture index for the cases they share.

- [ ] **Step 7.1: Write the corpus fixture**

`/Users/l0cka/Projects/openbench/data/fixtures/corpus-fixture.jsonl` (one JSON object per line):
```jsonl
{"type":"decision","citation":"Mabo v Queensland (No 2) [1992] HCA 23","url":"https://example.org/mabo","jurisdiction":"commonwealth","date":"1992-06-03","source":"hca","id":"hca-1992-23"}
{"type":"decision","citation":"Mabo v Queensland (No 2) [1992] HCA 23","url":"https://example.org/mabo-mirror","jurisdiction":"commonwealth","date":"1992-06-03","source":"austlii-mirror","id":"austlii-mabo"}
{"type":"decision","citation":"First Synthetic Case [2024] NSWSC 9999","url":"https://example.org/first","jurisdiction":"new_south_wales","date":"2024-01-01","source":"nswsc","id":"nswsc-2024-9999-a"}
{"type":"decision","citation":"Second Synthetic Case [2024] NSWSC 9999","url":"https://example.org/second","jurisdiction":"new_south_wales","date":"2024-01-15","source":"nswsc","id":"nswsc-2024-9999-b"}
{"type":"decision","citation":"Commonwealth v Tasmania [1983] HCA 21","url":"https://example.org/tasdam","jurisdiction":"commonwealth","date":"1983-07-01","source":"hca","id":"hca-1983-21"}
{"type":"primary_legislation","citation":"Acts Interpretation Act 1901","url":"https://example.org/aia","jurisdiction":"commonwealth","date":"1901-07-01","source":"comlaw","id":"aia-1901"}
```

(Two records share `[1992] HCA 23` with identical case_name+date and should *merge*. Two records share `[2024] NSWSC 9999` with different case_name+date and should produce *ambiguity*. The legislation row must be filtered out.)

- [ ] **Step 7.2: Write the API fixture index**

The fixture index is the test bed for `tests/integration/test_api_*.py`. It is intentionally curated. Include the three real decisions above plus eight more leading cases.

`/Users/l0cka/Projects/openbench/data/fixtures/index.json`:
```json
{
  "index_version": "fixture-2026-05-01",
  "generated_at": "2026-05-01T00:00:00Z",
  "builder_version": "0.1.0",
  "source": "open-australian-legal-corpus",
  "license": "CC-BY-4.0",
  "record_count": 11,
  "entries": {
    "[1992] HCA 23": {
      "normalized_citation": "[1992] HCA 23",
      "citation": "Mabo v Queensland (No 2) [1992] HCA 23",
      "case_name": "Mabo v Queensland (No 2)",
      "court": "High Court of Australia",
      "court_code": "HCA",
      "jurisdiction": "cth",
      "date": "1992-06-03",
      "source_urls": ["https://example.org/mabo", "https://example.org/mabo-mirror"],
      "source": "open-australian-legal-corpus",
      "source_record_ids": ["hca-1992-23", "austlii-mabo"],
      "indexed_at": "2026-05-01",
      "license": "CC-BY-4.0"
    },
    "[1983] HCA 21": {
      "normalized_citation": "[1983] HCA 21",
      "citation": "Commonwealth v Tasmania [1983] HCA 21",
      "case_name": "Commonwealth v Tasmania",
      "court": "High Court of Australia",
      "court_code": "HCA",
      "jurisdiction": "cth",
      "date": "1983-07-01",
      "source_urls": ["https://example.org/tasdam"],
      "source": "open-australian-legal-corpus",
      "source_record_ids": ["hca-1983-21"],
      "indexed_at": "2026-05-01",
      "license": "CC-BY-4.0"
    },
    "[1951] HCA 5": {
      "normalized_citation": "[1951] HCA 5",
      "citation": "Australian Communist Party v Commonwealth [1951] HCA 5",
      "case_name": "Australian Communist Party v Commonwealth",
      "court": "High Court of Australia",
      "court_code": "HCA",
      "jurisdiction": "cth",
      "date": "1951-03-09",
      "source_urls": ["https://example.org/acp"],
      "source": "open-australian-legal-corpus",
      "source_record_ids": ["hca-1951-5"],
      "indexed_at": "2026-05-01",
      "license": "CC-BY-4.0"
    },
    "[1996] HCA 56": {
      "normalized_citation": "[1996] HCA 56",
      "citation": "Lange v Australian Broadcasting Corporation [1996] HCA 56",
      "case_name": "Lange v Australian Broadcasting Corporation",
      "court": "High Court of Australia",
      "court_code": "HCA",
      "jurisdiction": "cth",
      "date": "1996-12-13",
      "source_urls": ["https://example.org/lange"],
      "source": "open-australian-legal-corpus",
      "source_record_ids": ["hca-1996-56"],
      "indexed_at": "2026-05-01",
      "license": "CC-BY-4.0"
    },
    "[2013] HCA 23": {
      "normalized_citation": "[2013] HCA 23",
      "citation": "Monis v The Queen [2013] HCA 4",
      "case_name": "Monis v The Queen",
      "court": "High Court of Australia",
      "court_code": "HCA",
      "jurisdiction": "cth",
      "date": "2013-02-27",
      "source_urls": ["https://example.org/monis"],
      "source": "open-australian-legal-corpus",
      "source_record_ids": ["hca-2013-23"],
      "indexed_at": "2026-05-01",
      "license": "CC-BY-4.0"
    },
    "[2002] FCAFC 250": {
      "normalized_citation": "[2002] FCAFC 250",
      "citation": "Roadshow Films v iiNet [2002] FCAFC 250",
      "case_name": "Roadshow Films v iiNet",
      "court": "Full Court of the Federal Court of Australia",
      "court_code": "FCAFC",
      "jurisdiction": "cth",
      "date": "2002-08-30",
      "source_urls": ["https://example.org/iinet"],
      "source": "open-australian-legal-corpus",
      "source_record_ids": ["fcafc-2002-250"],
      "indexed_at": "2026-05-01",
      "license": "CC-BY-4.0"
    },
    "[2018] FCA 1450": {
      "normalized_citation": "[2018] FCA 1450",
      "citation": "Australian Competition and Consumer Commission v Pirovic Enterprises Pty Ltd [2018] FCA 1450",
      "case_name": "Australian Competition and Consumer Commission v Pirovic Enterprises Pty Ltd",
      "court": "Federal Court of Australia",
      "court_code": "FCA",
      "jurisdiction": "cth",
      "date": "2018-09-26",
      "source_urls": ["https://example.org/pirovic"],
      "source": "open-australian-legal-corpus",
      "source_record_ids": ["fca-2018-1450"],
      "indexed_at": "2026-05-01",
      "license": "CC-BY-4.0"
    },
    "[2020] NSWCA 1": {
      "normalized_citation": "[2020] NSWCA 1",
      "citation": "Smith v Jones [2020] NSWCA 1",
      "case_name": "Smith v Jones",
      "court": "Court of Appeal of New South Wales",
      "court_code": "NSWCA",
      "jurisdiction": "nsw",
      "date": "2020-02-04",
      "source_urls": ["https://example.org/smith"],
      "source": "open-australian-legal-corpus",
      "source_record_ids": ["nswca-2020-1"],
      "indexed_at": "2026-05-01",
      "license": "CC-BY-4.0"
    },
    "[2019] VSCA 50": {
      "normalized_citation": "[2019] VSCA 50",
      "citation": "Doe v Roe [2019] VSCA 50",
      "case_name": "Doe v Roe",
      "court": "Court of Appeal of Victoria",
      "court_code": "VSCA",
      "jurisdiction": "vic",
      "date": "2019-04-12",
      "source_urls": ["https://example.org/doe"],
      "source": "open-australian-legal-corpus",
      "source_record_ids": ["vsca-2019-50"],
      "indexed_at": "2026-05-01",
      "license": "CC-BY-4.0"
    },
    "[2017] QCA 100": {
      "normalized_citation": "[2017] QCA 100",
      "citation": "Brown v Greene [2017] QCA 100",
      "case_name": "Brown v Greene",
      "court": "Court of Appeal of Queensland",
      "court_code": "QCA",
      "jurisdiction": "qld",
      "date": "2017-05-19",
      "source_urls": ["https://example.org/brown"],
      "source": "open-australian-legal-corpus",
      "source_record_ids": ["qca-2017-100"],
      "indexed_at": "2026-05-01",
      "license": "CC-BY-4.0"
    },
    "[2024] NSWSC 9999": [
      {
        "normalized_citation": "[2024] NSWSC 9999",
        "citation": "First Synthetic Case [2024] NSWSC 9999",
        "case_name": "First Synthetic Case",
        "court": "Supreme Court of New South Wales",
        "court_code": "NSWSC",
        "jurisdiction": "nsw",
        "date": "2024-01-01",
        "source_urls": ["https://example.org/first"],
        "source": "open-australian-legal-corpus",
        "source_record_ids": ["nswsc-2024-9999-a"],
        "indexed_at": "2026-05-01",
        "license": "CC-BY-4.0"
      },
      {
        "normalized_citation": "[2024] NSWSC 9999",
        "citation": "Second Synthetic Case [2024] NSWSC 9999",
        "case_name": "Second Synthetic Case",
        "court": "Supreme Court of New South Wales",
        "court_code": "NSWSC",
        "jurisdiction": "nsw",
        "date": "2024-01-15",
        "source_urls": ["https://example.org/second"],
        "source": "open-australian-legal-corpus",
        "source_record_ids": ["nswsc-2024-9999-b"],
        "indexed_at": "2026-05-01",
        "license": "CC-BY-4.0"
      }
    ]
  }
}
```

Note: `[2013] HCA 23` uses the `citation` field `"... [2013] HCA 4"` intentionally (a real-corpus mismatch can happen; the index is the source of truth and uses `normalized_citation`). Tests must not rely on `citation` matching `normalized_citation` exactly.

- [ ] **Step 7.3: Validate the fixture against the schema**

```bash
uv run python -c '
import json, jsonschema, pathlib
schema = json.loads(pathlib.Path("schemas/index.schema.json").read_text())
data = json.loads(pathlib.Path("data/fixtures/index.json").read_text())
jsonschema.validate(data, schema)
print("OK")
'
```
Expected: `OK`.

- [ ] **Step 7.4: Commit**

```bash
git add data/fixtures/corpus-fixture.jsonl data/fixtures/index.json
git commit -m "test(fixtures): add corpus and index fixtures (Mabo + 9 more, 1 ambiguous)"
```

---

## Task 8: Index store (load + lookup + metadata + stats)

**Files:**
- Create: `src/openbench/index_store.py`
- Test: `tests/unit/test_index_store.py`

- [ ] **Step 8.1: Write failing tests**

`/Users/l0cka/Projects/openbench/tests/unit/test_index_store.py`:
```python
import json
from pathlib import Path

import pytest

from openbench.index_store import IndexLoadError, IndexStore

FIXTURE = Path(__file__).parent.parent.parent / "data" / "fixtures" / "index.json"


def test_load_fixture_index() -> None:
    store = IndexStore.load(FIXTURE)
    assert store.metadata().record_count == 11


def test_lookup_verified_case() -> None:
    store = IndexStore.load(FIXTURE)
    entries = store.lookup("[1992] HCA 23")
    assert len(entries) == 1
    assert entries[0].case_name == "Mabo v Queensland (No 2)"
    assert entries[0].source_urls == [
        "https://example.org/mabo",
        "https://example.org/mabo-mirror",
    ]


def test_lookup_ambiguous_case_returns_multiple() -> None:
    store = IndexStore.load(FIXTURE)
    entries = store.lookup("[2024] NSWSC 9999")
    assert len(entries) == 2
    assert {e.case_name for e in entries} == {"First Synthetic Case", "Second Synthetic Case"}


def test_lookup_unknown_returns_empty() -> None:
    store = IndexStore.load(FIXTURE)
    assert store.lookup("[2099] HCA 999") == []


def test_stats_aggregates_by_court_and_year() -> None:
    store = IndexStore.load(FIXTURE)
    stats = store.stats()
    assert stats.record_count == 11
    assert stats.ambiguous_count == 1
    assert stats.by_court["HCA"] >= 1
    assert "1992" in stats.by_year
    assert stats.earliest_date is not None
    assert stats.latest_date is not None
    assert stats.earliest_date <= stats.latest_date


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(IndexLoadError):
        IndexStore.load(tmp_path / "does-not-exist.json")


def test_load_malformed_json_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    with pytest.raises(IndexLoadError):
        IndexStore.load(bad)


def test_load_schema_violation_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad-shape.json"
    bad.write_text(json.dumps({"hello": "world"}))
    with pytest.raises(IndexLoadError):
        IndexStore.load(bad)
```

- [ ] **Step 8.2: Run, verify failure**

```bash
uv run pytest tests/unit/test_index_store.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 8.3: Implement `index_store.py`**

`/Users/l0cka/Projects/openbench/src/openbench/index_store.py`:
```python
"""In-memory JSON-backed index store with O(1) citation lookup."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Self

from pydantic import ValidationError

from openbench.models import (
    ATTRIBUTION,
    IndexEntry,
    IndexFile,
    IndexMetadata,
    IndexStats,
)


class IndexLoadError(RuntimeError):
    """Raised when an index file is missing, malformed, or fails validation."""


class IndexStore:
    """Read-only in-memory store of `IndexEntry` objects keyed by `normalized_citation`."""

    def __init__(
        self,
        entries_by_citation: Mapping[str, list[IndexEntry]],
        index_version: str,
        generated_at: str,
        builder_version: str,
        source: str,
        license: str,  # noqa: A002 — matches schema
        dataset: str = "isaacus/open-australian-legal-corpus",
        dataset_version: str = "unknown",
    ) -> None:
        self._entries: dict[str, list[IndexEntry]] = {
            k: list(v) for k, v in entries_by_citation.items()
        }
        self._index_version = index_version
        self._generated_at = generated_at
        self._builder_version = builder_version
        self._source = source
        self._license = license
        self._dataset = dataset
        self._dataset_version = dataset_version
        self._stats = self._compute_stats()

    @classmethod
    def load(cls, path: Path | str) -> Self:
        p = Path(path)
        if not p.exists() or not p.is_file():
            raise IndexLoadError(f"index file not found: {p}")
        try:
            raw = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            raise IndexLoadError(f"index file is not valid JSON: {e}") from e
        try:
            parsed = IndexFile.model_validate(raw)
        except ValidationError as e:
            raise IndexLoadError(f"index file failed schema validation: {e}") from e

        normalised: dict[str, list[IndexEntry]] = {}
        for citation, value in parsed.entries.items():
            normalised[citation] = value if isinstance(value, list) else [value]

        return cls(
            entries_by_citation=normalised,
            index_version=parsed.index_version,
            generated_at=parsed.generated_at,
            builder_version=parsed.builder_version,
            source=parsed.source,
            license=parsed.license,
        )

    def lookup(self, normalized_citation: str) -> list[IndexEntry]:
        return list(self._entries.get(normalized_citation, ()))

    def metadata(self) -> IndexMetadata:
        return IndexMetadata(
            index_version=self._index_version,
            generated_at=self._generated_at,
            record_count=self._stats.record_count,
            sources=[self._source],
            license=self._license,
            builder_version=self._builder_version,
            attribution=ATTRIBUTION,
            dataset=self._dataset,
            dataset_version=self._dataset_version,
        )

    def stats(self) -> IndexStats:
        return self._stats

    @property
    def index_version(self) -> str:
        return self._index_version

    @property
    def source(self) -> str:
        return self._source

    @property
    def license(self) -> str:
        return self._license

    def _compute_stats(self) -> IndexStats:
        record_count = 0
        ambiguous_count = 0
        by_court: Counter[str] = Counter()
        by_year: Counter[str] = Counter()
        earliest = None
        latest = None
        for entries in self._entries.values():
            if len(entries) > 1:
                ambiguous_count += 1
            for e in entries:
                record_count += 1
                by_court[e.court_code] += 1
                by_year[str(e.date.year)] += 1
                earliest = e.date if earliest is None or e.date < earliest else earliest
                latest = e.date if latest is None or e.date > latest else latest
        return IndexStats(
            record_count=record_count,
            ambiguous_count=ambiguous_count,
            by_court=dict(by_court),
            by_year=dict(by_year),
            earliest_date=earliest,
            latest_date=latest,
        )


__all__ = ["IndexStore", "IndexLoadError", "defaultdict"]
```

(`defaultdict` is exported only to keep the public-import surface stable for tests; remove if never imported externally — see Step 8.5.)

- [ ] **Step 8.4: Run, verify pass**

```bash
uv run pytest tests/unit/test_index_store.py -v
uv run mypy
```
Expected: 8 passed; mypy clean.

- [ ] **Step 8.5: Tighten `__all__` and re-run**

Replace the last line of `index_store.py` with:
```python
__all__ = ["IndexStore", "IndexLoadError"]
```
Remove the unused `from collections import ... defaultdict` import too.

```bash
uv run ruff check . --fix
uv run pytest -q
uv run mypy
```
Expected: clean.

- [ ] **Step 8.6: Commit**

```bash
git add src/openbench/index_store.py tests/unit/test_index_store.py
git commit -m "feat(index_store): in-memory loader, lookup, metadata, stats"
```

---

## Task 9: Index builder (corpus JSONL → index dict)

**Files:**
- Create: `src/openbench/index_builder.py`
- Test: `tests/unit/test_index_builder.py`

- [ ] **Step 9.1: Write failing tests**

`/Users/l0cka/Projects/openbench/tests/unit/test_index_builder.py`:
```python
import json
from pathlib import Path

import jsonschema

from openbench.index_builder import build_index

CORPUS = Path(__file__).parent.parent.parent / "data" / "fixtures" / "corpus-fixture.jsonl"
SCHEMA = Path(__file__).parent.parent.parent / "schemas" / "index.schema.json"


def test_builder_filters_non_decisions() -> None:
    out = build_index(CORPUS, index_version="test")
    # legislation row must not appear
    assert "Acts Interpretation Act 1901" not in json.dumps(out)


def test_builder_dedups_matching_records() -> None:
    out = build_index(CORPUS, index_version="test")
    mabo = out["entries"]["[1992] HCA 23"]
    assert isinstance(mabo, dict)
    assert sorted(mabo["source_urls"]) == [
        "https://example.org/mabo",
        "https://example.org/mabo-mirror",
    ]
    assert sorted(mabo["source_record_ids"]) == ["austlii-mabo", "hca-1992-23"]


def test_builder_emits_array_for_genuine_ambiguity() -> None:
    out = build_index(CORPUS, index_version="test")
    nswsc = out["entries"]["[2024] NSWSC 9999"]
    assert isinstance(nswsc, list)
    assert len(nswsc) == 2
    names = {e["case_name"] for e in nswsc}
    assert names == {"First Synthetic Case", "Second Synthetic Case"}


def test_builder_resolves_court_name_and_jurisdiction() -> None:
    out = build_index(CORPUS, index_version="test")
    mabo = out["entries"]["[1992] HCA 23"]
    assert mabo["court"] == "High Court of Australia"
    assert mabo["jurisdiction"] == "cth"


def test_builder_record_count_excludes_filtered() -> None:
    out = build_index(CORPUS, index_version="test")
    # 5 decision rows in fixture (Mabo dedups to 1, NSWSC stays as 2, Tasmania is 1) → 4 distinct entries, 5 records
    assert out["record_count"] == 4  # entries-after-dedup
    assert len(out["entries"]) == 3  # distinct citation keys (NSWSC value is a list)


def test_builder_output_validates_against_schema() -> None:
    out = build_index(CORPUS, index_version="test")
    schema = json.loads(SCHEMA.read_text())
    jsonschema.validate(out, schema)


def test_builder_skips_records_with_unparseable_citation(tmp_path: Path) -> None:
    p = tmp_path / "junk.jsonl"
    p.write_text(
        '{"type":"decision","citation":"Junk no citation here","url":"https://x","date":"2020-01-01","id":"x","jurisdiction":"commonwealth"}\n'
        '{"type":"decision","citation":"Real Case [2020] HCA 1","url":"https://y","date":"2020-01-01","id":"y","jurisdiction":"commonwealth"}\n'
    )
    out = build_index(p, index_version="test")
    assert list(out["entries"].keys()) == ["[2020] HCA 1"]
```

- [ ] **Step 9.2: Run, verify failure**

```bash
uv run pytest tests/unit/test_index_builder.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 9.3: Implement `index_builder.py`**

`/Users/l0cka/Projects/openbench/src/openbench/index_builder.py`:
```python
"""Build an openbench index dict from a corpus JSONL file.

Input format: one JSON object per line, with at least the fields
  type (str), citation (str), url (str), date (str ISO),
  jurisdiction (str), id (str)

Behaviour:
  - filters records where type != "decision"
  - extracts neutral citation + case name via openbench.normalization
  - groups records by normalized_citation
  - merges records sharing (normalized_citation, case_name, date) into one entry
    (with a deduplicated list of source_urls and source_record_ids)
  - emits a top-level dict matching schemas/index.schema.json
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openbench import __version__ as openbench_version
from openbench.courts import resolve_court
from openbench.normalization import extract_case_name_and_citation

SOURCE_NAME = "open-australian-legal-corpus"
LICENSE = "CC-BY-4.0"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _parse_date(s: str) -> date | None:
    try:
        return date.fromisoformat(s[:10])
    except (TypeError, ValueError):
        return None


def build_index(
    corpus_path: Path | str,
    *,
    index_version: str | None = None,
    indexed_at: date | None = None,
) -> dict[str, Any]:
    rows = _read_jsonl(Path(corpus_path))
    today = indexed_at or date.today()
    version = index_version or today.isoformat()

    # group: normalized_citation -> dedup_key -> merged entry (mutable dict)
    grouped: dict[str, dict[tuple[str, str], dict[str, Any]]] = defaultdict(dict)

    for row in rows:
        if row.get("type") != "decision":
            continue
        case_name, normalized = extract_case_name_and_citation(row.get("citation") or "")
        if normalized is None or case_name is None:
            continue
        d = _parse_date(row.get("date") or "")
        if d is None:
            continue

        court_code = normalized.split()[1]
        court_name, jurisdiction = resolve_court(court_code)
        url = row.get("url") or ""
        record_id = row.get("id") or url

        dedup_key = (case_name, d.isoformat())
        bucket = grouped[normalized]
        if dedup_key in bucket:
            entry = bucket[dedup_key]
            if url and url not in entry["source_urls"]:
                entry["source_urls"].append(url)
            if record_id and record_id not in entry["source_record_ids"]:
                entry["source_record_ids"].append(record_id)
        else:
            bucket[dedup_key] = {
                "normalized_citation": normalized,
                "citation": row.get("citation") or "",
                "case_name": case_name,
                "court": court_name,
                "court_code": court_code,
                "jurisdiction": jurisdiction,
                "date": d.isoformat(),
                "source_urls": [url] if url else [],
                "source": SOURCE_NAME,
                "source_record_ids": [record_id] if record_id else [],
                "indexed_at": today.isoformat(),
                "license": LICENSE,
            }

    entries: dict[str, Any] = {}
    record_count = 0
    for citation, bucket in grouped.items():
        merged = list(bucket.values())
        record_count += len(merged)
        entries[citation] = merged[0] if len(merged) == 1 else merged

    return {
        "index_version": version,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "builder_version": openbench_version,
        "source": SOURCE_NAME,
        "license": LICENSE,
        "record_count": record_count,
        "entries": entries,
    }
```

- [ ] **Step 9.4: Run, verify pass**

```bash
uv run pytest tests/unit/test_index_builder.py -v
uv run mypy
uv run ruff check .
```
Expected: 7 passed; clean.

- [ ] **Step 9.5: Commit**

```bash
git add src/openbench/index_builder.py tests/unit/test_index_builder.py
git commit -m "feat(index_builder): build dedup'd index from corpus JSONL"
```

---

## Task 10: FastAPI app + routes

**Files:**
- Create: `src/openbench/api.py`
- Test: `tests/integration/test_api_health.py`
- Test: `tests/integration/test_api_lookup.py`
- Test: `tests/integration/test_api_metadata.py`

- [ ] **Step 10.1: Write failing health test**

`/Users/l0cka/Projects/openbench/tests/integration/test_api_health.py`:
```python
from pathlib import Path

from fastapi.testclient import TestClient

from openbench.api import create_app

FIXTURE = Path(__file__).parent.parent.parent / "data" / "fixtures" / "index.json"


def test_health_with_index_loaded() -> None:
    app = create_app(index_path=FIXTURE)
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body == {"status": "ok", "index_loaded": True}


def test_health_with_no_index() -> None:
    app = create_app(index_path=None)
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "index_loaded": False}
```

- [ ] **Step 10.2: Write failing lookup tests**

`/Users/l0cka/Projects/openbench/tests/integration/test_api_lookup.py`:
```python
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient

from openbench.api import create_app

FIXTURE = Path(__file__).parent.parent.parent / "data" / "fixtures" / "index.json"


def _client() -> TestClient:
    app = create_app(index_path=FIXTURE)
    return TestClient(app)


def _get(citation: str) -> dict:
    with _client() as client:
        r = client.get(f"/v1/au/citations/{quote(citation, safe='')}")
    assert r.status_code == 200, r.text
    return r.json()


def test_lookup_verified_mabo() -> None:
    body = _get("[1992] HCA 23")
    assert body["status"] == "verified"
    assert body["normalized_citation"] == "[1992] HCA 23"
    assert body["case_name"] == "Mabo v Queensland (No 2)"
    assert body["court"] == "High Court of Australia"
    assert body["jurisdiction"] == "cth"
    assert body["confidence"] == 1.0
    assert body["candidates"] == []
    assert body["sources"] == ["open-australian-legal-corpus"]
    assert body["provenance"]["license"] == "CC-BY-4.0"


def test_lookup_pinpoint_stripped() -> None:
    body = _get("[1992] HCA 23 [10]")
    assert body["status"] == "verified"
    assert body["normalized_citation"] == "[1992] HCA 23"


def test_lookup_paren_year_form() -> None:
    body = _get("(1992) HCA 23")
    assert body["status"] == "verified"
    assert body["normalized_citation"] == "[1992] HCA 23"


def test_lookup_not_found() -> None:
    body = _get("[2099] HCA 999")
    assert body["status"] == "not_found"
    assert body["confidence"] == 0.0
    assert body["candidates"] == []


def test_lookup_unsupported_format_plain_text() -> None:
    body = _get("Mabo")
    assert body["status"] == "unsupported_format"
    assert body["confidence"] == 0.0


def test_lookup_unsupported_reported_citation() -> None:
    body = _get("(1992) 175 CLR 1")
    assert body["status"] == "unsupported_format"


def test_lookup_ambiguous() -> None:
    body = _get("[2024] NSWSC 9999")
    assert body["status"] == "ambiguous"
    assert body["confidence"] == 0.5
    assert "case_name" not in body or body["case_name"] is None
    assert len(body["candidates"]) == 2
    names = {c["case_name"] for c in body["candidates"]}
    assert names == {"First Synthetic Case", "Second Synthetic Case"}


def test_response_includes_provenance_attribution_for_verified() -> None:
    body = _get("[1992] HCA 23")
    assert "Isaacus" in body["provenance"]["attribution"]
```

- [ ] **Step 10.3: Write failing metadata/stats/unavailable tests**

`/Users/l0cka/Projects/openbench/tests/integration/test_api_metadata.py`:
```python
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient

from openbench.api import create_app

FIXTURE = Path(__file__).parent.parent.parent / "data" / "fixtures" / "index.json"


def test_metadata() -> None:
    app = create_app(index_path=FIXTURE)
    with TestClient(app) as client:
        r = client.get("/v1/au/index/metadata")
    assert r.status_code == 200
    body = r.json()
    assert body["index_version"] == "fixture-2026-05-01"
    assert body["sources"] == ["open-australian-legal-corpus"]
    assert body["license"] == "CC-BY-4.0"
    assert "Isaacus" in body["attribution"]


def test_stats() -> None:
    app = create_app(index_path=FIXTURE)
    with TestClient(app) as client:
        r = client.get("/v1/au/index/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["record_count"] == 11
    assert body["ambiguous_count"] == 1
    assert body["by_court"]["HCA"] >= 1


def test_lookup_returns_503_when_no_index() -> None:
    app = create_app(index_path=None)
    with TestClient(app) as client:
        r = client.get(f"/v1/au/citations/{quote('[1992] HCA 23')}")
    assert r.status_code == 503
    assert r.json()["status"] == "index_unavailable"


def test_metadata_returns_503_when_no_index() -> None:
    app = create_app(index_path=None)
    with TestClient(app) as client:
        r = client.get("/v1/au/index/metadata")
    assert r.status_code == 503


def test_stats_returns_503_when_no_index() -> None:
    app = create_app(index_path=None)
    with TestClient(app) as client:
        r = client.get("/v1/au/index/stats")
    assert r.status_code == 503
```

- [ ] **Step 10.4: Run all three integration test files, verify failure**

```bash
uv run pytest tests/integration -v
```
Expected: import errors / `create_app` missing.

- [ ] **Step 10.5: Implement `api.py`**

`/Users/l0cka/Projects/openbench/src/openbench/api.py`:
```python
"""FastAPI application exposing the openbench citation lookup API."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path as PathParam
from fastapi.responses import JSONResponse

from openbench import __version__
from openbench.index_store import IndexLoadError, IndexStore
from openbench.models import (
    ATTRIBUTION,
    Candidate,
    HealthResponse,
    IndexEntry,
    IndexMetadata,
    IndexStats,
    LookupResponse,
    Provenance,
    Status,
)
from openbench.normalization import normalize_citation

INDEX_ENV = "AUS_CASE_INDEX"


def _try_load(index_path: Path | str | None) -> IndexStore | None:
    if index_path is None:
        return None
    try:
        return IndexStore.load(index_path)
    except IndexLoadError:
        return None


def create_app(*, index_path: Path | str | None = None) -> FastAPI:
    """Create a FastAPI app, optionally pre-loading an index file.

    If `index_path` is None, the app starts in `index_unavailable` mode and
    `/health` reports `index_loaded: false`. Lookup/metadata/stats return 503.
    """
    if index_path is None:
        index_path = os.environ.get(INDEX_ENV)
    store = _try_load(index_path)

    app = FastAPI(
        title="openbench",
        version=__version__,
        description=(
            "Open Australian case-law citation lookup. Verifies citation presence "
            "in an open index. Not an official court or government API; not legal advice."
        ),
    )
    app.state.store = store

    def get_store() -> IndexStore:
        s: IndexStore | None = app.state.store
        if s is None:
            raise HTTPException(
                status_code=503,
                detail={"status": Status.index_unavailable.value},
            )
        return s

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", index_loaded=app.state.store is not None)

    @app.get("/v1/au/citations/{citation:path}", response_model=LookupResponse)
    def lookup(
        citation: Annotated[str, PathParam(...)],
        store: Annotated[IndexStore, Depends(get_store)],
    ) -> LookupResponse:
        result = normalize_citation(citation)
        if not result.ok or result.normalized is None:
            return LookupResponse(
                citation=citation,
                status=Status.unsupported_format,
                confidence=0.0,
                candidates=[],
            )

        entries: list[IndexEntry] = store.lookup(result.normalized)
        provenance = Provenance(
            index_version=store.index_version,
            source=store.source,
            license=store.license,
            dataset="isaacus/open-australian-legal-corpus",
            attribution=ATTRIBUTION,
        )
        if not entries:
            return LookupResponse(
                citation=citation,
                normalized_citation=result.normalized,
                status=Status.not_found,
                confidence=0.0,
                candidates=[],
                provenance=provenance,
            )
        if len(entries) == 1:
            e = entries[0]
            return LookupResponse(
                citation=citation,
                normalized_citation=result.normalized,
                status=Status.verified,
                case_name=e.case_name,
                court=e.court,
                court_code=e.court_code,
                jurisdiction=e.jurisdiction,
                date=e.date,
                source_urls=list(e.source_urls),
                sources=[e.source],
                confidence=1.0,
                candidates=[],
                provenance=provenance,
            )
        # ambiguous
        candidates = [
            Candidate(
                case_name=e.case_name,
                court=e.court,
                court_code=e.court_code,
                jurisdiction=e.jurisdiction,
                date=e.date,
                source_urls=list(e.source_urls),
            )
            for e in entries
        ]
        return LookupResponse(
            citation=citation,
            normalized_citation=result.normalized,
            status=Status.ambiguous,
            confidence=0.5,
            candidates=candidates,
            provenance=provenance,
        )

    @app.get("/v1/au/index/metadata", response_model=IndexMetadata)
    def metadata(store: Annotated[IndexStore, Depends(get_store)]) -> IndexMetadata:
        return store.metadata()

    @app.get("/v1/au/index/stats", response_model=IndexStats)
    def stats(store: Annotated[IndexStore, Depends(get_store)]) -> IndexStats:
        return store.stats()

    @app.exception_handler(HTTPException)
    async def _http_exc(_req, exc: HTTPException) -> JSONResponse:  # type: ignore[no-untyped-def]
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return app
```

- [ ] **Step 10.6: Run integration tests, verify pass**

```bash
uv run pytest tests/integration -v
uv run mypy
uv run ruff check .
```
Expected: all integration tests pass; clean.

- [ ] **Step 10.7: Commit**

```bash
git add src/openbench/api.py tests/integration
git commit -m "feat(api): FastAPI routes for /health, /v1/au/citations, metadata, stats"
```

---

## Task 11: CLI (`openbench index build|stats`, `openbench serve`)

**Files:**
- Create: `src/openbench/cli.py`
- Test: `tests/integration/test_cli.py`

- [ ] **Step 11.1: Write failing CLI tests**

`/Users/l0cka/Projects/openbench/tests/integration/test_cli.py`:
```python
import json
from pathlib import Path

from typer.testing import CliRunner

from openbench.cli import app

CORPUS = Path(__file__).parent.parent.parent / "data" / "fixtures" / "corpus-fixture.jsonl"
FIXTURE = Path(__file__).parent.parent.parent / "data" / "fixtures" / "index.json"

runner = CliRunner()


def test_index_build_writes_valid_index(tmp_path: Path) -> None:
    out = tmp_path / "index.json"
    result = runner.invoke(app, ["index", "build", str(CORPUS), "--output", str(out)])
    assert result.exit_code == 0, result.stdout
    data = json.loads(out.read_text())
    assert "[1992] HCA 23" in data["entries"]


def test_index_stats_prints_counts(tmp_path: Path) -> None:
    result = runner.invoke(app, ["index", "stats", str(FIXTURE)])
    assert result.exit_code == 0, result.stdout
    assert "record_count" in result.stdout
    assert "11" in result.stdout


def test_serve_help_lists_index_option() -> None:
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--index" in result.stdout
```

- [ ] **Step 11.2: Run, verify failure**

```bash
uv run pytest tests/integration/test_cli.py -v
```
Expected: import error.

- [ ] **Step 11.3: Implement `cli.py`**

`/Users/l0cka/Projects/openbench/src/openbench/cli.py`:
```python
"""openbench CLI: build indexes, inspect stats, run the API."""

from __future__ import annotations

import json
from pathlib import Path

import typer
import uvicorn

from openbench.api import create_app
from openbench.index_builder import build_index
from openbench.index_store import IndexStore

app = typer.Typer(no_args_is_help=True, add_completion=False)
index_app = typer.Typer(no_args_is_help=True, help="Build and inspect openbench indexes.")
app.add_typer(index_app, name="index")


@index_app.command("build")
def index_build(
    corpus: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    output: Path = typer.Option(Path("index.json"), "--output", "-o"),
    index_version: str | None = typer.Option(None, "--index-version"),
) -> None:
    """Build an index from a JSONL corpus file."""
    data = build_index(corpus, index_version=index_version)
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    typer.echo(f"wrote {output} ({data['record_count']} records)")


@index_app.command("stats")
def index_stats(
    index: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
) -> None:
    """Print stats for an index file."""
    store = IndexStore.load(index)
    typer.echo(json.dumps(store.stats().model_dump(mode="json"), indent=2))


@app.command("serve")
def serve(
    index: Path = typer.Option(..., "--index", exists=True, dir_okay=False, readable=True),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """Run the openbench API server."""
    application = create_app(index_path=index)
    uvicorn.run(application, host=host, port=port)


if __name__ == "__main__":  # pragma: no cover
    app()
```

- [ ] **Step 11.4: Run, verify pass**

```bash
uv run pytest tests/integration/test_cli.py -v
uv run mypy
uv run ruff check .
```
Expected: 3 passed; clean.

- [ ] **Step 11.5: Smoke-run the binary against the fixture**

```bash
uv run openbench index stats data/fixtures/index.json
uv run openbench index build data/fixtures/corpus-fixture.jsonl --output /tmp/openbench-test.json
```
Expected: prints stats; writes `/tmp/openbench-test.json`. Open it and confirm `entries` is a dict.

- [ ] **Step 11.6: Commit**

```bash
git add src/openbench/cli.py tests/integration/test_cli.py
git commit -m "feat(cli): typer-based openbench cli (index build/stats, serve)"
```

---

## Task 12: README + DATA_SOURCES

**Files:**
- Create: `README.md`
- Create: `DATA_SOURCES.md`

- [ ] **Step 12.1: Write `README.md`**

`/Users/l0cka/Projects/openbench/README.md`:
````markdown
# openbench

Open Australian case-law citation lookup API.

> **openbench is not an official court or government API. openbench does not provide legal advice. Results reflect only the configured open index — absence of a citation is not proof a case does not exist. Always verify important matters against authorised sources (court websites, AustLII, JADE).**

openbench resolves Australian neutral citations (e.g. `[1992] HCA 23`) against an index built from the [Open Australian Legal Corpus](https://huggingface.co/datasets/isaacus/open-australian-legal-corpus) by Isaacus, and returns structured metadata with explicit provenance.

## Quickstart

```bash
git clone https://github.com/danielkurdi/openbench
cd openbench
uv sync --extra dev
uv run openbench serve --index data/fixtures/index.json
```

In another terminal:

```bash
curl "http://127.0.0.1:8000/v1/au/citations/%5B1992%5D%20HCA%2023" | jq
```

You should see a `verified` response for *Mabo v Queensland (No 2)*.

## API

| Endpoint | Description |
|---|---|
| `GET /health` | Liveness + `index_loaded` flag |
| `GET /v1/au/citations/{citation}` | Resolve a single citation |
| `GET /v1/au/index/metadata` | Index version, source, attribution |
| `GET /v1/au/index/stats` | Record counts by court, year, ambiguity |

Statuses: `verified`, `not_found`, `ambiguous`, `unsupported_format`, `index_unavailable`. Full reference: [`docs/api.md`](docs/api.md).

## Building your own index

Download the Isaacus corpus, transform to JSONL with the fields openbench expects, then:

```bash
uv run openbench index build path/to/corpus.jsonl --output index.json
AUS_CASE_INDEX=$(pwd)/index.json uv run openbench serve --index $(pwd)/index.json
```

See [`docs/self-hosting.md`](docs/self-hosting.md) for the full process.

## Licensing & attribution

- Code: Apache-2.0 (see `LICENSE`).
- Index data (`data/fixtures/index.json` and any released `index-*.json` artifact): CC-BY-4.0, derived from the Open Australian Legal Corpus by Isaacus. See `LICENSE-DATA` and `DATA_SOURCES.md`.

  > Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by openbench (metadata extraction, normalisation, deduplication).

## Status

v1: local MVP. No public hosted API yet. See `docs/superpowers/specs/2026-05-01-openbench-design.md` for scope.
````

- [ ] **Step 12.2: Write `DATA_SOURCES.md`**

`/Users/l0cka/Projects/openbench/DATA_SOURCES.md`:
```markdown
# Data sources

## Primary source

**Open Australian Legal Corpus** by Isaacus.

- Dataset: <https://huggingface.co/datasets/isaacus/open-australian-legal-corpus>
- Licence: CC-BY-4.0 — <https://creativecommons.org/licenses/by/4.0/>
- Update cadence: irregular. openbench treats each build as a snapshot and surfaces freshness via `/v1/au/index/metadata` (`generated_at`, `dataset_version`).

### Modifications by openbench

- Filtered to records where `type == "decision"`.
- Extracted neutral citation, case name, court, jurisdiction, date, and source URL — discarded full judgment text.
- Normalised neutral citations to canonical `[YYYY] COURT N` form.
- Deduplicated records sharing `(normalized_citation, case_name, date)`.

### Required attribution

Any redistribution of an openbench index must include:

> Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by openbench (metadata extraction, normalisation, deduplication).

This attribution is automatically embedded in every API response's `provenance.attribution` field and in `/v1/au/index/metadata`.

## Disclaimers

- openbench is not affiliated with any court, government, or the Isaacus team.
- openbench does not provide legal advice. Use authorised sources for substantive matters.
- A `not_found` response only proves the citation is not present in the configured index.
```

- [ ] **Step 12.3: Commit**

```bash
git add README.md DATA_SOURCES.md
git commit -m "docs: README quickstart and DATA_SOURCES with CC-BY attribution"
```

---

## Task 13: Other docs and templates

**Files:**
- Create: `CODE_OF_CONDUCT.md`
- Create: `CONTRIBUTING.md`
- Create: `SECURITY.md`
- Create: `docs/api.md`
- Create: `docs/self-hosting.md`
- Create: `.github/ISSUE_TEMPLATE/data-error.md`
- Create: `.github/ISSUE_TEMPLATE/source-request.md`

- [ ] **Step 13.1: `CODE_OF_CONDUCT.md`**

Use Contributor Covenant 2.1 verbatim. Replace any `[INSERT CONTACT METHOD]` with `conduct@openbench.invalid` (a placeholder address — replace later with a real one in a follow-up commit if/when the project gets a contact alias).

- [ ] **Step 13.2: `CONTRIBUTING.md`**

`/Users/l0cka/Projects/openbench/CONTRIBUTING.md`:
````markdown
# Contributing to openbench

Thanks for your interest. openbench is small and intentionally focused.

## Dev setup

Requires `uv` and Python 3.12+.

```bash
git clone https://github.com/danielkurdi/openbench
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
````

- [ ] **Step 13.3: `SECURITY.md`**

`/Users/l0cka/Projects/openbench/SECURITY.md`:
```markdown
# Security policy

## Supported versions

Only the latest tagged release receives security fixes during v1.

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Instead, email
security@openbench.invalid with:

- a description of the issue
- steps to reproduce
- the openbench version (`uv run openbench --version` once available, or commit SHA)

We will respond within 7 days. Once a fix is ready we will coordinate disclosure.

## Scope

In scope:
- The openbench API and CLI source code in this repository.
- Index file handling and parsing.

Out of scope:
- The upstream Open Australian Legal Corpus (report to Isaacus).
- Self-hosted deployments not maintained by this project.
- Issues that require an attacker with local file write access.
```

- [ ] **Step 13.4: `docs/api.md`**

`/Users/l0cka/Projects/openbench/docs/api.md`:
````markdown
# openbench API reference

Base URL when self-hosted: `http://127.0.0.1:8000`.

All responses are JSON. Encode the citation in the path with standard URL encoding.

## `GET /health`

```json
{"status": "ok", "index_loaded": true}
```

`200` always. `index_loaded: false` means lookup/metadata/stats will return `503`.

## `GET /v1/au/citations/{citation}`

### Verified

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
  "source_urls": ["https://example.org/mabo"],
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

### Not found

```json
{
  "citation": "[2099] HCA 999",
  "normalized_citation": "[2099] HCA 999",
  "status": "not_found",
  "confidence": 0.0,
  "candidates": []
}
```

### Ambiguous

```json
{
  "citation": "[2024] NSWSC 9999",
  "normalized_citation": "[2024] NSWSC 9999",
  "status": "ambiguous",
  "confidence": 0.5,
  "candidates": [
    {"case_name": "First Synthetic Case", "court_code": "NSWSC", "court": "Supreme Court of New South Wales", "jurisdiction": "nsw", "date": "2024-01-01", "source_urls": ["https://example.org/first"]},
    {"case_name": "Second Synthetic Case", "court_code": "NSWSC", "court": "Supreme Court of New South Wales", "jurisdiction": "nsw", "date": "2024-01-15", "source_urls": ["https://example.org/second"]}
  ]
}
```

### Unsupported format

```json
{
  "citation": "Mabo",
  "status": "unsupported_format",
  "confidence": 0.0,
  "candidates": []
}
```

### Index unavailable (503)

```json
{"status": "index_unavailable"}
```

## Accepted citation forms

| Input | Normalised |
|---|---|
| `[1992] HCA 23` | `[1992] HCA 23` |
| `(1992) HCA 23` | `[1992] HCA 23` |
| `1992 HCA 23` | `[1992] HCA 23` |
| `[1992] HCA 23 [10]` (pinpoint) | `[1992] HCA 23` |
| `[1992] HCA 23 at [10]` | `[1992] HCA 23` |
| `(1992) 175 CLR 1` (reported) | rejected as `unsupported_format` in v1 |

## `GET /v1/au/index/metadata`

```json
{
  "index_version": "fixture-2026-05-01",
  "generated_at": "2026-05-01T00:00:00Z",
  "record_count": 11,
  "sources": ["open-australian-legal-corpus"],
  "license": "CC-BY-4.0",
  "builder_version": "0.1.0",
  "attribution": "Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by openbench (metadata extraction).",
  "dataset": "isaacus/open-australian-legal-corpus",
  "dataset_version": "unknown"
}
```

## `GET /v1/au/index/stats`

```json
{
  "record_count": 11,
  "ambiguous_count": 1,
  "by_court": {"HCA": 5, "FCAFC": 1, "FCA": 1, "NSWCA": 1, "NSWSC": 2, "VSCA": 1, "QCA": 1},
  "by_year": {"1951": 1, "1983": 1, "1992": 1, "1996": 1, "2002": 1, "2013": 1, "2017": 1, "2018": 1, "2019": 1, "2020": 1, "2024": 2},
  "earliest_date": "1951-03-09",
  "latest_date": "2024-01-15"
}
```
````

- [ ] **Step 13.5: `docs/self-hosting.md`**

`/Users/l0cka/Projects/openbench/docs/self-hosting.md`:
````markdown
# Self-hosting openbench

openbench is read-only and stateless apart from the index file. Self-hosting boils down to: get an `index.json`, point `--index` at it, run `uvicorn`.

## 1. Get an index file

You have two options.

### Option A: download a release artifact

Once openbench publishes tagged releases, each one will include `index-<version>.json.zst`. Decompress and use:

```bash
zstd -d index-2026-05-01.json.zst -o index.json
```

### Option B: build from the upstream corpus

Download the Open Australian Legal Corpus from HuggingFace and convert it to a JSONL with the fields openbench expects:

- `type` — must be `"decision"` for inclusion
- `citation` — full citation string, e.g. `Mabo v Queensland (No 2) [1992] HCA 23`
- `url` — source URL
- `date` — ISO date `YYYY-MM-DD`
- `jurisdiction` — string (any value; openbench rederives jurisdiction from the court code)
- `id` — stable record id

Then:

```bash
uv run openbench index build /path/to/corpus.jsonl --output index.json
```

## 2. Run the server

```bash
uv run openbench serve --index $(pwd)/index.json --host 0.0.0.0 --port 8000
```

Or via the env var:

```bash
export AUS_CASE_INDEX=$(pwd)/index.json
uv run uvicorn 'openbench.api:create_app' --factory --host 0.0.0.0 --port 8000
```

## 3. Health checks

`GET /health` always returns 200 with `{"status":"ok","index_loaded":true|false}`. Use the body to alert on `false`.

## 4. Updating the index

Stop the server, replace `index.json`, restart. There is no hot reload in v1.

## 5. Disclaimers

You are responsible for displaying the CC-BY-4.0 attribution wherever you expose openbench results. The attribution is included in every API response's `provenance.attribution` and in `/v1/au/index/metadata.attribution`.
````

- [ ] **Step 13.6: Issue templates**

`/Users/l0cka/Projects/openbench/.github/ISSUE_TEMPLATE/data-error.md`:
```markdown
---
name: Data error
about: Report an incorrect or missing case in the index
labels: data
---

**Citation:**
[YYYY] COURT N

**Expected (with source):**
- Case name:
- Court:
- Date:
- Source URL (court website, AustLII, JADE):

**What openbench returned:**
Paste the JSON response.

**Index version:**
The `index_version` from `/v1/au/index/metadata`.
```

`/Users/l0cka/Projects/openbench/.github/ISSUE_TEMPLATE/source-request.md`:
```markdown
---
name: Source request
about: Propose a new open data source for openbench
labels: source-request
---

**Source name:**

**Homepage / dataset URL:**

**Licence:**

**Why it fits openbench v1+ scope:**
(Refer to non-goals in the spec — no scraping, no proprietary data, no
commercial-only sources without explicit terms.)

**Coverage:**
- Jurisdictions:
- Date range:
- Approximate record count:

**Update cadence:**
```

- [ ] **Step 13.7: Commit**

```bash
git add CODE_OF_CONDUCT.md CONTRIBUTING.md SECURITY.md docs .github/ISSUE_TEMPLATE
git commit -m "docs: add CoC, contributing, security, api/self-hosting docs, issue templates"
```

---

## Task 14: CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 14.1: Write the workflow**

`/Users/l0cka/Projects/openbench/.github/workflows/ci.yml`:
```yaml
name: ci

on:
  push:
    branches: [main]
  pull_request:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Lint
        run: |
          uv run ruff check .
          uv run ruff format --check .

      - name: Type check
        run: uv run mypy

      - name: Validate fixture index against schema
        run: |
          uv run python -c "
          import json, jsonschema, pathlib
          schema = json.loads(pathlib.Path('schemas/index.schema.json').read_text())
          data = json.loads(pathlib.Path('data/fixtures/index.json').read_text())
          jsonschema.validate(data, schema)
          print('fixture index OK')
          "

      - name: Test
        run: uv run pytest -q

      - name: Build sdist + wheel
        run: uv build

      - name: Twine check
        run: uv run twine check dist/*
```

- [ ] **Step 14.2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: lint, type, schema-validate, test, build, twine check"
```

---

## Task 15: Release workflow (build + attach full index)

**Files:**
- Create: `.github/workflows/release.yml`
- Create: `scripts/build_release_index.py`

The release workflow downloads the Isaacus HF corpus, converts it to JSONL with the fields openbench expects, runs `openbench index build`, validates against the schema, compresses with `zstd`, and attaches the artifact to the GitHub Release that was just published.

- [ ] **Step 15.1: Add `huggingface-hub` and `zstandard` as optional release deps**

Edit `/Users/l0cka/Projects/openbench/pyproject.toml` to add a new optional group:
```toml
[project.optional-dependencies]
dev = [
  "pytest>=8",
  "httpx>=0.27",
  "mypy>=1.10",
  "ruff>=0.5",
  "twine>=5",
]
release = [
  "huggingface-hub>=0.23",
  "datasets>=2.20",
  "zstandard>=0.22",
]
```

- [ ] **Step 15.2: Write the release script**

`/Users/l0cka/Projects/openbench/scripts/build_release_index.py`:
```python
"""Build a release-grade openbench index from the Isaacus HF corpus.

Usage:
    uv run --extra release python scripts/build_release_index.py \
        --output index.json --index-version 2026-05-01

Steps:
  1. Stream the Isaacus dataset, keeping only `decision` records.
  2. Project to the JSONL fields openbench expects.
  3. Pipe to `openbench.index_builder.build_index`.
  4. Validate against `schemas/index.schema.json`.
  5. Write `index.json` and `index.json.zst`.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import jsonschema
import zstandard as zstd
from datasets import load_dataset

from openbench.index_builder import build_index

DATASET = "isaacus/open-australian-legal-corpus"
SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "index.schema.json"


def _stream_decisions_to_jsonl(out_path: Path) -> int:
    ds = load_dataset(DATASET, split="train", streaming=True)
    n = 0
    with out_path.open("w") as f:
        for row in ds:
            if row.get("type") != "decision":
                continue
            projection = {
                "type": "decision",
                "citation": row.get("citation") or "",
                "url": row.get("url") or "",
                "date": (row.get("date") or "")[:10],
                "jurisdiction": row.get("jurisdiction") or "",
                "id": row.get("id") or row.get("url") or "",
            }
            f.write(json.dumps(projection, ensure_ascii=False) + "\n")
            n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--index-version", required=True)
    args = ap.parse_args()

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
        jsonl_path = Path(tmp.name)
    print(f"streaming {DATASET} → {jsonl_path}")
    n = _stream_decisions_to_jsonl(jsonl_path)
    print(f"wrote {n} decision records")

    print("building index")
    data = build_index(jsonl_path, index_version=args.index_version)

    print("validating against schema")
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(data, schema)

    print(f"writing {args.output}")
    args.output.write_text(json.dumps(data, ensure_ascii=False))

    zst_path = args.output.with_suffix(args.output.suffix + ".zst")
    print(f"compressing {zst_path}")
    cctx = zstd.ZstdCompressor(level=19)
    zst_path.write_bytes(cctx.compress(args.output.read_bytes()))
    print(
        f"done: {args.output.stat().st_size} bytes raw, "
        f"{zst_path.stat().st_size} bytes zst"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 15.3: Write the release workflow**

`/Users/l0cka/Projects/openbench/.github/workflows/release.yml`:
```yaml
name: release

on:
  release:
    types: [published]

permissions:
  contents: write

jobs:
  build-index:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - run: uv python install 3.12

      - run: uv sync --extra dev --extra release

      - name: Build release index
        run: |
          uv run python scripts/build_release_index.py \
            --output index-${{ github.event.release.tag_name }}.json \
            --index-version ${{ github.event.release.tag_name }}

      - name: Upload index artifact to release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            index-${{ github.event.release.tag_name }}.json
            index-${{ github.event.release.tag_name }}.json.zst
```

- [ ] **Step 15.4: Local dry-run is optional**

Streaming the full HF dataset is slow and bandwidth-heavy. The release workflow itself is the integration test for this script — do not gate the merge on a local successful run. Confirm the script imports cleanly:

```bash
uv sync --extra dev --extra release
uv run python -c "import scripts.build_release_index"  # may fail if scripts/ not on path; that's OK, script is invoked by file path
```

- [ ] **Step 15.5: Commit**

```bash
git add scripts/build_release_index.py .github/workflows/release.yml pyproject.toml
git commit -m "ci(release): build full index from Isaacus corpus and attach to tag"
```

---

## Task 16: End-to-end smoke and v0.1.0 tag

- [ ] **Step 16.1: Full local check**

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -q
uv build
uv run twine check dist/*
```
Expected: all green.

- [ ] **Step 16.2: Smoke the binary**

```bash
uv run openbench serve --index data/fixtures/index.json &
SERVER_PID=$!
sleep 1
curl -fsS "http://127.0.0.1:8000/health" | grep '"index_loaded":true'
curl -fsS "http://127.0.0.1:8000/v1/au/citations/%5B1992%5D%20HCA%2023" | grep '"verified"'
curl -fsS "http://127.0.0.1:8000/v1/au/citations/Mabo" | grep '"unsupported_format"'
curl -fsS "http://127.0.0.1:8000/v1/au/citations/%5B2024%5D%20NSWSC%209999" | grep '"ambiguous"'
curl -fsS "http://127.0.0.1:8000/v1/au/index/metadata" | grep '"CC-BY-4.0"'
kill $SERVER_PID
```
Expected: every grep matches.

- [ ] **Step 16.3: Tag v0.1.0**

```bash
git tag -a v0.1.0 -m "openbench v0.1.0 — local MVP"
git log --oneline | head
```

- [ ] **Step 16.4: Push (when ready)**

The user pushes when they're satisfied. Do not push without explicit user instruction.

---

## Self-review

- Spec §1 Purpose → covered by README disclaimer + provenance threading (Tasks 12, 5, 10).
- Spec §2 Goals → all five goals map to Tasks 4, 5, 8, 9, 10, 11, 12.
- Spec §3 Non-Goals → enforced by absence in plan + explicit rejection of `(1992) 175 CLR 1` in Tasks 4 and 10.
- Spec §4 Data source → Task 7 (fixture provenance), Task 12 (DATA_SOURCES), Task 15 (release pipeline).
- Spec §5 Citation parsing → Task 4 (every accepted/rejected form has a test).
- Spec §6 Ambiguity & dedup → Task 9 fixture-driven tests (`test_builder_dedups_matching_records`, `test_builder_emits_array_for_genuine_ambiguity`).
- Spec §7 Index schema → Task 6 (JSON Schema + tests), Task 5 (Pydantic mirror).
- Spec §8 API contract → Tasks 5, 10, 13 (api.md mirrors response shapes).
- Spec §9 Distribution → Task 7 (fixture in repo), Task 15 (release artifact).
- Spec §10 Storage → Task 8 (in-memory JSON, IndexStore interface, stats precomputed at startup).
- Spec §11 Project structure → Tasks 1, 12, 13.
- Spec §12 Tooling → Task 1 (`pyproject.toml`), Task 14 (CI invocations).
- Spec §13 Testing scope → Tasks 4, 8, 9, 10, 11 cover every listed unit/integration/release check.
- Spec §14 Licensing → Task 2 (LICENSE files), Task 12 (DATA_SOURCES + README), Task 5 (`ATTRIBUTION` constant), Task 10 (provenance threading).
- Spec §15 Definition of Done → Task 16 verifies items 1–4 and 7; items 5 (schema validation) covered by CI in Task 14; item 6 (README) by Task 12.
- Spec §16 Disclaimers → README (Task 12), DATA_SOURCES (Task 12), `/v1/au/index/metadata` attribution (Task 5/10).
- Spec §17 Deferred → CONTRIBUTING reiterates (Task 13).

Placeholder scan: no `TBD`/`TODO`/"implement later" remain in the plan. Every code-bearing step has full code.

Type-name consistency: `IndexEntry`, `Candidate`, `LookupResponse`, `Status`, `IndexStore`, `IndexLoadError`, `build_index`, `normalize_citation`, `extract_case_name_and_citation`, `resolve_court`, `create_app`, `ATTRIBUTION` — all referenced consistently across Tasks 3–11. CLI command names (`openbench index build`, `openbench index stats`, `openbench serve`) match the spec §15 and the typer definitions in Task 11.

Single open assumption flagged for the executing engineer: the Isaacus corpus's actual record schema (field names like `type`, `citation`, `url`, `date`, `jurisdiction`, `id`) is the contract `index_builder` expects from JSONL input. If the upstream HF schema differs, `scripts/build_release_index.py` is the single point that needs to remap; the rest of openbench is unaffected.
