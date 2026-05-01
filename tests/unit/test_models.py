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
