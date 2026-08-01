from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from caselaw_guard.adapters.australia import AustralianCorpusAdapter
from caselaw_guard.api import create_app
from caselaw_guard.cli import app
from caselaw_guard.extractors import extract_citations
from caselaw_guard.models import CitationMatch, VerificationStatus
from caselaw_guard.verifier import verify_text

FIXTURE_INDEX = Path(__file__).parent / "fixtures" / "australia_index.json"


@pytest.mark.parametrize(
    "citation",
    [
        "[1992] HCA 23",
        "(1992) HCA 23",
        "1992 HCA 23",
        "[1992]  HCA   23",
        "[1992] hca 23",
        "[1992] HCA 23 [10]",
        "[1992] HCA 23 at [10]",
        "[1992] HCA 23, [10]",
        "[2024] FedCFamC1A 7",
    ],
)
def test_every_accepted_form_is_extracted_once_with_its_exact_span(citation: str) -> None:
    prefix = "See authority: "
    text = f"{prefix}{citation}."

    australian = [match for match in extract_citations(text) if match.jurisdiction_guess == "au"]

    assert len(australian) == 1
    assert australian[0].text == citation
    assert (australian[0].start_index, australian[0].end_index) == (len(prefix), len(prefix) + len(citation))


@pytest.mark.parametrize(
    "citation",
    [
        "[1992] HCA 23",
        "(1992) HCA 23",
        "1992 HCA 23",
        "[1992]  HCA   23",
        "[1992] hca 23",
        "[1992] HCA 23 [10]",
        "[1992] HCA 23 at [10]",
        "[1992] HCA 23, [10]",
    ],
)
def test_accepted_form_cannot_silently_produce_an_empty_passing_report(citation: str) -> None:
    report = verify_text(citation, adapters=[AustralianCorpusAdapter(FIXTURE_INDEX)])

    assert len(report.results) == 1
    assert report.results[0].status is VerificationStatus.VERIFIED
    assert report.results[0].normalized_citation == "[1992] HCA 23"


def test_future_citation_is_extracted_and_fails_closed() -> None:
    report = verify_text("Invented: [2099] HCA 999.", adapters=[AustralianCorpusAdapter(FIXTURE_INDEX)])

    assert len(report.results) == 1
    assert report.pass_ is False
    assert report.results[0].status is VerificationStatus.NOT_FOUND


def test_reported_citation_is_not_classified_as_an_australian_neutral_citation() -> None:
    matches = extract_citations("Mabo v Queensland (No 2) (1992) 175 CLR 1.")

    assert [match for match in matches if match.jurisdiction_guess == "au"] == []


def test_malformed_suffix_is_not_partially_extracted_and_verified() -> None:
    matches = extract_citations("Invented: [1992] HCA 23abc.")

    assert [match for match in matches if match.jurisdiction_guess == "au"] == []


def test_adapter_maps_authority_candidates_statuses_and_provenance(tmp_path: Path) -> None:
    index = tmp_path / "canonical.json"
    index.write_text(json.dumps(_canonical_index()), encoding="utf-8")
    adapter = AustralianCorpusAdapter(index)

    verified = adapter.lookup(_match("(1992) hca 23"))
    ambiguous = adapter.lookup(_match("[2024] NSWSC 9"))
    missing = adapter.lookup(_match("[2001] HCA 1"))
    malformed = adapter.lookup(_match("not a citation"))

    assert verified.status is VerificationStatus.VERIFIED
    assert verified.authority is not None
    assert verified.authority.model_dump() == {
        "case_name": "Mabo v Queensland (No 2)",
        "court": "High Court of Australia",
        "date": "1992-06-03",
        "docket_number": None,
        "source_url": "https://example.test/mabo",
        "metadata": {
            "court_code": "HCA",
            "jurisdiction": "cth",
            "source_urls": ["https://example.test/mabo", "https://example.test/mabo-alt"],
            "source": "open-australian-legal-corpus",
            "license": "CC-BY-4.0",
        },
    }
    assert ambiguous.status is VerificationStatus.AMBIGUOUS
    assert ambiguous.authority is None
    assert [candidate.case_name for candidate in ambiguous.candidates] == ["First", "Second"]
    assert missing.status is VerificationStatus.NOT_FOUND
    assert malformed.status is VerificationStatus.UNSUPPORTED_FORMAT
    for result in (verified, ambiguous, missing, malformed):
        assert result.provider_metadata == {
            "index_version": "acceptance-1",
            "generated_at": "2026-08-01T00:00:00Z",
            "source": "open-australian-legal-corpus",
            "dataset_revision": "abc123",
            "license": "CC-BY-4.0",
            "attribution": (
                "Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by CaseLaw "
                "Guard (metadata extraction, normalisation and deduplication)."
            ),
            "index_format": "canonical",
        }


def test_rest_lookup_and_adapter_have_status_normalization_and_provenance_parity() -> None:
    adapter = AustralianCorpusAdapter(FIXTURE_INDEX)
    client = TestClient(create_app(adapters=[adapter]))

    verification = client.post("/verify", json={"text": "Known: (1992) HCA 23 at [10]."}).json()["results"][0]
    lookup = client.get(f"/v1/au/citations/{quote('(1992) HCA 23 at [10]', safe='')}").json()

    assert lookup["status"] == verification["status"] == "verified"
    assert lookup["normalized_citation"] == verification["normalized_citation"] == "[1992] HCA 23"
    assert lookup["provenance"] == verification["provider_metadata"]


def test_rest_metadata_stats_health_and_unavailable_index() -> None:
    loaded = TestClient(create_app(adapters=[AustralianCorpusAdapter(FIXTURE_INDEX)]))
    unavailable = TestClient(create_app(adapters=[]))

    assert loaded.get("/health").json() == {"status": "ok", "index_loaded": True}
    assert loaded.get("/v1/au/index/metadata").json()["index_format"] == "legacy"
    assert loaded.get("/v1/au/index/stats").json()["record_count"] == 2
    response = unavailable.get(f"/v1/au/citations/{quote('[1992] HCA 23', safe='')}")
    assert response.status_code == 503
    assert response.json() == {"status": "index_unavailable"}


def test_rest_honours_explicit_index_when_other_adapters_are_supplied() -> None:
    client = TestClient(create_app(adapters=[], index_path=FIXTURE_INDEX))

    assert client.get("/health").json() == {"status": "ok", "index_loaded": True}
    response = client.get(f"/v1/au/citations/{quote('[1992] HCA 23', safe='')}")
    assert response.status_code == 200
    assert response.json()["status"] == "verified"


def test_au_index_stats_and_migrate_keep_command_names(tmp_path: Path) -> None:
    migrated = tmp_path / "migrated.json"
    runner = CliRunner()

    stats = runner.invoke(app, ["au-index", "stats", str(FIXTURE_INDEX)])
    migration = runner.invoke(
        app,
        ["au-index", "migrate", str(FIXTURE_INDEX), "--output", str(migrated)],
    )

    assert stats.exit_code == 0
    assert json.loads(stats.stdout)["record_count"] == 2
    assert migration.exit_code == 0
    assert migrated.is_file()
    assert isinstance(json.loads(migrated.read_text(encoding="utf-8"))["entries"], dict)


def _match(citation: str) -> CitationMatch:
    return CitationMatch(
        text=citation,
        start_index=0,
        end_index=len(citation),
        jurisdiction_guess="au",
    )


def _canonical_index() -> dict[str, object]:
    return {
        "index_version": "acceptance-1",
        "generated_at": "2026-08-01T00:00:00Z",
        "builder_version": "0.2.0",
        "source": "open-australian-legal-corpus",
        "dataset_revision": "abc123",
        "license": "CC-BY-4.0",
        "attribution": (
            "Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by CaseLaw "
            "Guard (metadata extraction, normalisation and deduplication)."
        ),
        "record_count": 2,
        "entries": {
            "[1992] HCA 23": _entry(
                "[1992] HCA 23",
                "Mabo v Queensland (No 2)",
                "1992-06-03",
                ["https://example.test/mabo", "https://example.test/mabo-alt"],
                "HCA",
                "High Court of Australia",
                "cth",
            ),
            "[2024] NSWSC 9": [
                _entry(
                    "[2024] NSWSC 9",
                    "First",
                    "2024-01-01",
                    ["https://example.test/first"],
                    "NSWSC",
                    "Supreme Court of New South Wales",
                    "nsw",
                ),
                _entry(
                    "[2024] NSWSC 9",
                    "Second",
                    "2024-01-02",
                    ["https://example.test/second"],
                    "NSWSC",
                    "Supreme Court of New South Wales",
                    "nsw",
                ),
            ],
        },
    }


def _entry(
    citation: str,
    case_name: str,
    decision_date: str,
    source_urls: list[str],
    court_code: str,
    court: str,
    jurisdiction: str,
) -> dict[str, object]:
    return {
        "normalized_citation": citation,
        "citation": f"{case_name} {citation}",
        "case_name": case_name,
        "court": court,
        "court_code": court_code,
        "jurisdiction": jurisdiction,
        "date": decision_date,
        "source_urls": source_urls,
        "source": "open-australian-legal-corpus",
        "source_record_ids": [url.rsplit("/", 1)[-1] for url in source_urls],
        "indexed_at": "2026-08-01",
        "license": "CC-BY-4.0",
    }
