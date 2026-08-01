from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path

import pytest
from scripts import eval_auslaw_benchmark as benchmark
from scripts.eval_auslaw_benchmark import (
    AusLawBenchmarkRow,
    add_generation_timestamp,
    compare_reports,
    download_benchmark,
    evaluate_rows,
    extract_gold_citation,
    extract_neutral_citation,
    verify_benchmark_file,
)


def test_extract_gold_citation_uses_final_angle_bracket_citation():
    output = (
        "The cited case supports the proposition. "
        "<Some Earlier Case [2001] NSWSC 1> "
        "<Collins v Urban [2014] NSWCATAP 17>"
    )

    assert extract_gold_citation(output) == "Collins v Urban [2014] NSWCATAP 17"


def test_extract_neutral_citation_returns_court_code():
    neutral = extract_neutral_citation("Collins v Urban [2014] NSWCATAP 17")

    assert neutral is not None
    assert neutral.citation == "[2014] NSWCATAP 17"
    assert neutral.court == "NSWCATAP"


def test_evaluate_rows_recognizes_well_formed_unknown_court_codes():
    rows = [
        AusLawBenchmarkRow(
            instruction="Predict the case.",
            input="Known citation.",
            output="The case is known. <Mabo v Queensland (No 2) [1992] HCA 23>",
        ),
        AusLawBenchmarkRow(
            instruction="Predict the case.",
            input="Missed citation.",
            output="The case is missed. <Collins v Urban [2014] XYZCA 17>",
        ),
        AusLawBenchmarkRow(
            instruction="Predict the case.",
            input="No citation.",
            output="No citation in angle brackets.",
        ),
    ]

    report = evaluate_rows(rows, max_examples=10)

    assert report["total_rows"] == 3
    assert report["gold_citation_parse_count"] == 2
    assert report["gold_neutral_citation_count"] == 2
    assert report["extractor_recognized_count"] == 2
    assert report["extractor_recognition_rate"] == 1.0
    assert report["missing_court_codes"] == []
    assert report["missed_examples"] == []


def test_evaluate_rows_without_au_index_keeps_extraction_only_report_shape():
    rows = [
        AusLawBenchmarkRow(
            instruction="Predict the case.",
            input="Known citation.",
            output="The case is known. <Mabo v Queensland (No 2) [1992] HCA 23>",
        )
    ]

    report = evaluate_rows(rows)

    assert "verification_status_counts" not in report
    assert "verification_verified_count" not in report
    assert "verification_not_found_count" not in report


def test_evaluate_rows_with_au_index_counts_verified_and_not_found_rows(tmp_path):
    index = tmp_path / "australia_index.json"
    index.write_text(
        json.dumps(
            [
                {
                    "citation": "Mabo v Queensland (No 2) [1992] HCA 23",
                    "normalized_citation": "[1992] HCA 23",
                    "case_name": "Mabo v Queensland (No 2)",
                    "court": "High Court of Australia",
                    "jurisdiction": "cth",
                    "date": "1992-06-03",
                    "source_url": "https://example.test/mabo",
                }
            ]
        ),
        encoding="utf-8",
    )
    rows = [
        AusLawBenchmarkRow(
            instruction="Predict the case.",
            input="Known citation.",
            output="The case is known. <Mabo v Queensland (No 2) [1992] HCA 23>",
        ),
        AusLawBenchmarkRow(
            instruction="Predict the case.",
            input="Missing citation.",
            output="The case is missing. <Applicant v Minister [2024] NSWSC 10>",
        ),
    ]

    report = evaluate_rows(rows, au_index=index, max_examples=10)

    assert report["extractor_recognized_count"] == 2
    assert report["verification_status_counts"] == {"verified": 1, "not_found": 1}
    assert report["verification_verified_count"] == 1
    assert report["verification_not_found_count"] == 1
    assert report["verification_ambiguous_count"] == 0
    assert report["verification_provider_error_count"] == 0
    assert report["verification_missed_examples"] == [
        {
            "row_index": 2,
            "gold_citation": "Applicant v Minister [2024] NSWSC 10",
            "neutral_citation": "[2024] NSWSC 10",
            "court": "NSWSC",
            "status": "not_found",
        }
    ]


def test_benchmark_digest_is_pinned_and_mismatches_are_rejected(tmp_path: Path):
    benchmark_path = tmp_path / "roc_test.json"
    benchmark_path.write_bytes(b"not the pinned benchmark")

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verify_benchmark_file(benchmark_path, expected_sha256="0" * 64)


class _Response:
    def __init__(self, payload: bytes):
        self._stream = BytesIO(payload)

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)


def test_download_validates_before_replacing_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cache_path = tmp_path / "roc_test.json"
    cache_path.write_bytes(b"known-good-cache")
    payload = b"downloaded benchmark"
    expected_sha256 = hashlib.sha256(payload).hexdigest()
    monkeypatch.setattr(benchmark.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response(payload))

    download_benchmark(cache_path, url="https://example.test/roc_test.json", expected_sha256=expected_sha256)

    assert cache_path.read_bytes() == payload
    assert list(tmp_path.iterdir()) == [cache_path]


def test_download_digest_failure_preserves_existing_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cache_path = tmp_path / "roc_test.json"
    cache_path.write_bytes(b"known-good-cache")
    monkeypatch.setattr(benchmark.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response(b"bad"))

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        download_benchmark(cache_path, url="https://example.test/roc_test.json", expected_sha256="0" * 64)

    assert cache_path.read_bytes() == b"known-good-cache"
    assert list(tmp_path.iterdir()) == [cache_path]


def test_report_records_pinned_benchmark_and_complete_index_provenance(tmp_path: Path):
    index_path = Path("examples/australia_index.sample.json")
    rows = [
        AusLawBenchmarkRow(
            instruction="Predict the case.",
            input="Known citation.",
            output="The case is known. <Mabo v Queensland (No 2) [1992] HCA 23>",
        ),
        AusLawBenchmarkRow(
            instruction="Predict the case.",
            input="Missing citation.",
            output="The case is missing. <Applicant v Minister [2024] NSWSC 10>",
        ),
    ]

    report = evaluate_rows(rows, au_index=index_path)

    assert report["benchmark"] == {
        "dataset": benchmark.BENCHMARK_DATASET,
        "revision": benchmark.BENCHMARK_REVISION,
        "split": benchmark.BENCHMARK_SPLIT,
        "file": benchmark.BENCHMARK_FILE,
        "sha256": benchmark.BENCHMARK_SHA256,
        "license": benchmark.BENCHMARK_LICENSE,
    }
    assert report["index_provenance"] == {
        "index_version": "sample-2026-08-01",
        "generated_at": "2026-08-01T00:00:00Z",
        "source": "open-australian-legal-corpus",
        "dataset_revision": "unknown",
        "license": "CC-BY-4.0",
        "attribution": (
            "Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by CaseLaw Guard "
            "(metadata extraction, normalisation and deduplication)."
        ),
        "index_format": "canonical",
    }
    assert [row["verification_status"] for row in report["row_results"]] == ["verified", "not_found"]
    assert [row["verification_result_count"] for row in report["row_results"]] == [1, 1]


def test_row_results_are_deterministic_and_timestamp_is_explicit(tmp_path: Path):
    rows = [
        AusLawBenchmarkRow(
            instruction="Predict the case.",
            input="Known citation.",
            output="The case is known. <Mabo v Queensland (No 2) [1992] HCA 23>",
        )
    ]

    first = evaluate_rows(rows)
    second = evaluate_rows(rows)

    assert first == second
    first_with_time = add_generation_timestamp(first, generated_at="2026-08-02T00:00:00Z")
    second_with_time = add_generation_timestamp(second, generated_at="2026-08-02T00:00:01Z")
    first_with_time.pop("generated_at")
    second_with_time.pop("generated_at")
    assert first_with_time == second_with_time


def test_compare_reports_fails_closed_for_lost_extraction_or_verification():
    baseline = {
        "row_results": [
            {"row_index": 1, "extraction_status": "recognized", "verification_status": "verified"},
            {"row_index": 2, "extraction_status": "recognized", "verification_status": "not_found"},
            {"row_index": 3, "extraction_status": "recognized", "verification_status": "verified"},
        ]
    }
    current = {
        "row_results": [
            {"row_index": 1, "extraction_status": "unrecognized", "verification_status": None},
            {"row_index": 2, "extraction_status": "recognized", "verification_status": "verified"},
            {"row_index": 3, "extraction_status": "recognized", "verification_status": "not_found"},
        ]
    }

    assert compare_reports(baseline, current) == [
        {
            "row_index": 1,
            "kind": "extraction_regression",
            "baseline": "recognized",
            "current": "unrecognized",
        },
        {
            "row_index": 3,
            "kind": "verification_regression",
            "baseline": "verified",
            "current": "not_found",
        },
    ]
