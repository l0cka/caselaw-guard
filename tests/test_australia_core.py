from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from caselaw_guard.australia import (
    ATTRIBUTION,
    AustralianCitationService,
    AustralianLookupStatus,
    IndexLoadError,
    IndexStore,
    build_index,
    migrate_index,
)
from caselaw_guard.australia.courts import canonical_court_code, resolve_court
from caselaw_guard.australia.normalization import normalize_citation


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("[1992] HCA 23", "[1992] HCA 23"),
        ("(1992) HCA 23", "[1992] HCA 23"),
        ("1992 HCA 23", "[1992] HCA 23"),
        ("[1992]  hca   23", "[1992] HCA 23"),
        ("[1992] HCA 23 [10]", "[1992] HCA 23"),
        ("[1992] HCA 23 at [10]", "[1992] HCA 23"),
        ("[1992] HCA 23, [10]", "[1992] HCA 23"),
        ("[2024] fedcfamc1a 7", "[2024] FedCFamC1A 7"),
        ("[2024] NswCatAp 7", "[2024] NSWCATAP 7"),
        ("[2024] NEW2COURT 7", "[2024] NEW2COURT 7"),
    ],
)
def test_normalizer_accepts_all_supported_forms(raw: str, expected: str) -> None:
    result = normalize_citation(raw)
    assert result.ok is True
    assert result.normalized == expected


def test_normalizer_rejects_reported_citations_and_invalid_years() -> None:
    assert normalize_citation("(1992) 175 CLR 1").ok is False
    assert normalize_citation("[1899] HCA 1").ok is False


def test_court_mapping_is_case_insensitive_and_preserves_known_spelling() -> None:
    assert canonical_court_code("fedcfamc1a") == "FedCFamC1A"
    assert resolve_court("nSwSc") == ("Supreme Court of New South Wales", "nsw")
    assert resolve_court("NEW2COURT") == (None, None)


def test_canonical_and_legacy_indexes_have_honest_provenance(tmp_path: Path) -> None:
    canonical_path = tmp_path / "canonical.json"
    canonical_path.write_text(json.dumps(_canonical_index()), encoding="utf-8")
    canonical = IndexStore.load(canonical_path)
    assert canonical.provenance().index_format == "canonical"
    assert canonical.provenance().attribution == ATTRIBUTION

    legacy_path = tmp_path / "legacy.json"
    legacy_path.write_text(json.dumps([_legacy_row()]), encoding="utf-8")
    legacy = IndexStore.load(legacy_path)
    assert legacy.provenance().index_format == "legacy"
    assert legacy.provenance().dataset_revision == "unknown"
    assert legacy.lookup("[1992] HCA 23")[0].court_code == "HCA"


def test_service_statuses_and_provenance_are_consistent(tmp_path: Path) -> None:
    path = tmp_path / "index.json"
    data = _canonical_index()
    data["entries"]["[2024] NSWSC 9"] = [
        _entry("[2024] NSWSC 9", "First", "2024-01-01", "https://example.test/first"),
        _entry("[2024] NSWSC 9", "Second", "2024-01-02", "https://example.test/second"),
    ]
    data["record_count"] = 2
    path.write_text(json.dumps(data), encoding="utf-8")
    service = AustralianCitationService.load(path)

    verified = service.lookup("(1992) hca 23")
    assert verified.status is AustralianLookupStatus.VERIFIED
    assert verified.normalized_citation == "[1992] HCA 23"
    assert verified.confidence == 1.0
    assert verified.provenance.index_format == "canonical"

    ambiguous = service.lookup("[2024] nswsc 9")
    assert ambiguous.status is AustralianLookupStatus.AMBIGUOUS
    assert len(ambiguous.entries) == 2
    assert ambiguous.confidence == 0.5

    missing = service.lookup("[2001] HCA 1")
    future = service.lookup("[2099] HCA 999")
    malformed = service.lookup("(1992) 175 CLR 1")
    assert missing.status is AustralianLookupStatus.NOT_FOUND
    assert future.status is AustralianLookupStatus.NOT_FOUND
    assert malformed.status is AustralianLookupStatus.UNSUPPORTED_FORMAT
    results = (verified, ambiguous, missing, future, malformed)
    assert all(result.provenance.attribution == ATTRIBUTION for result in results)


def test_builder_records_supplied_dataset_revision_and_migration_is_non_destructive(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        "\n".join(
            [
                json.dumps(_corpus_row("https://example.test/a", "a")),
                json.dumps(_corpus_row("https://example.test/b", "b")),
                json.dumps({"type": "legislation", "citation": "Ignored"}),
            ]
        ),
        encoding="utf-8",
    )
    index = build_index(corpus, index_version="test", indexed_at=date(2026, 8, 1), dataset_revision="abc123")
    assert index.dataset_revision == "abc123"
    assert index.record_count == 1
    mabo = index.entries["[1992] HCA 23"]
    assert mabo.source_urls == ["https://example.test/a", "https://example.test/b"]  # type: ignore[union-attr]

    legacy = tmp_path / "legacy.json"
    legacy.write_text(json.dumps([_legacy_row()]), encoding="utf-8")
    before = legacy.read_text(encoding="utf-8")
    migrated_path = tmp_path / "migrated.json"
    migrated = migrate_index(legacy, migrated_path)
    assert legacy.read_text(encoding="utf-8") == before
    assert migrated_path.is_file()
    assert migrated.attribution == "unknown"
    assert IndexStore.load(migrated_path).provenance().index_format == "canonical"


def test_invalid_index_raises_a_single_load_boundary_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"entries": {}}', encoding="utf-8")
    with pytest.raises(IndexLoadError, match="failed validation"):
        IndexStore.load(bad)


def _canonical_index() -> dict[str, object]:
    return {
        "index_version": "fixture-1",
        "generated_at": "2026-08-01T00:00:00Z",
        "builder_version": "0.2.0",
        "source": "open-australian-legal-corpus",
        "dataset_revision": "abc123",
        "license": "CC-BY-4.0",
        "attribution": ATTRIBUTION,
        "record_count": 1,
        "entries": {
            "[1992] HCA 23": _entry(
                "[1992] HCA 23", "Mabo v Queensland (No 2)", "1992-06-03", "https://example.test/mabo"
            )
        },
    }


def _entry(citation: str, case_name: str, decision_date: str, source_url: str) -> dict[str, object]:
    court_code = citation.split()[1]
    court, jurisdiction = resolve_court(court_code)
    return {
        "normalized_citation": citation,
        "citation": f"{case_name} {citation}",
        "case_name": case_name,
        "court": court,
        "court_code": court_code,
        "jurisdiction": jurisdiction,
        "date": decision_date,
        "source_urls": [source_url],
        "source": "open-australian-legal-corpus",
        "source_record_ids": [source_url.rsplit("/", 1)[-1]],
        "indexed_at": "2026-08-01",
        "license": "CC-BY-4.0",
    }


def _legacy_row() -> dict[str, str]:
    return {
        "citation": "Mabo v Queensland (No 2) [1992] HCA 23",
        "normalized_citation": "[1992] HCA 23",
        "case_name": "Mabo v Queensland (No 2)",
        "court": "High Court of Australia",
        "date": "1992-06-03",
        "source_url": "https://example.test/mabo",
    }


def _corpus_row(url: str, record_id: str) -> dict[str, str]:
    return {
        "type": "decision",
        "citation": "Mabo v Queensland (No 2) [1992] HCA 23",
        "url": url,
        "id": record_id,
        "date": "1992-06-03",
    }
