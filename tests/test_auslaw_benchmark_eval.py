import json

from scripts.eval_auslaw_benchmark import (
    AusLawBenchmarkRow,
    evaluate_rows,
    extract_gold_citation,
    extract_neutral_citation,
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


def test_evaluate_rows_counts_recognized_and_missing_court_codes():
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
    assert report["extractor_recognized_count"] == 1
    assert report["extractor_recognition_rate"] == 0.5
    assert report["missing_court_codes"] == [{"court": "XYZCA", "count": 1}]
    assert report["missed_examples"] == [
        {
            "row_index": 2,
            "gold_citation": "Collins v Urban [2014] XYZCA 17",
            "neutral_citation": "[2014] XYZCA 17",
            "court": "XYZCA",
        }
    ]


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
