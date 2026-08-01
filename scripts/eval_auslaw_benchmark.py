from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from caselaw_guard.adapters.australia import AustralianCorpusAdapter
from caselaw_guard.extractors import extract_citations
from caselaw_guard.models import VerificationStatus
from caselaw_guard.verifier import verify_text

BENCHMARK_DATASET = "auslawbench/AusLaw-Citation-Benchmark"
BENCHMARK_SPLIT = "test"
BENCHMARK_FILE = "roc_test.json"
BENCHMARK_REVISION = "fabee289f2a5bbfb3c6476be55084abe426f6f18"
BENCHMARK_SHA256 = "154d272792778df49c01814d9e864121fcca3828df5f23c6ace90e992effb005"
BENCHMARK_LICENSE = "Apache-2.0"
BENCHMARK_URL = (
    f"https://huggingface.co/datasets/{BENCHMARK_DATASET}/resolve/{BENCHMARK_REVISION}/{BENCHMARK_FILE}?download=true"
)
DEFAULT_CACHE_PATH = Path(".cache/caselaw-guard/auslaw-citation-benchmark/roc_test.json")
ANGLE_CITATION_RE = re.compile(r"<([^<>]+)>")
NEUTRAL_CITATION_RE = re.compile(r"\[(?P<year>\d{4})\]\s+(?P<court>[A-Za-z][A-Za-z0-9]{1,12})\s+(?P<number>\d{1,5})")


@dataclass(frozen=True)
class AusLawBenchmarkRow:
    instruction: str
    input: str
    output: str


@dataclass(frozen=True)
class NeutralCitation:
    citation: str
    court: str


def benchmark_provenance() -> dict[str, str]:
    return {
        "dataset": BENCHMARK_DATASET,
        "revision": BENCHMARK_REVISION,
        "split": BENCHMARK_SPLIT,
        "file": BENCHMARK_FILE,
        "sha256": BENCHMARK_SHA256,
        "license": BENCHMARK_LICENSE,
    }


def extract_gold_citation(output: str) -> str | None:
    matches = ANGLE_CITATION_RE.findall(output)
    return matches[-1].strip() if matches else None


def extract_neutral_citation(citation: str) -> NeutralCitation | None:
    match = NEUTRAL_CITATION_RE.search(citation)
    if not match:
        return None
    normalized = f"[{match.group('year')}] {match.group('court')} {match.group('number')}"
    return NeutralCitation(citation=normalized, court=match.group("court"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify_benchmark_file(path: Path, *, expected_sha256: str = BENCHMARK_SHA256) -> str:
    if not path.is_file():
        raise ValueError(f"benchmark file not found: {path}")
    actual_sha256 = _sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise ValueError(f"benchmark file SHA-256 mismatch for {path}: expected {expected_sha256}, got {actual_sha256}")
    return actual_sha256


def evaluate_rows(
    rows: list[AusLawBenchmarkRow], *, max_examples: int = 20, au_index: Path | None = None
) -> dict[str, Any]:
    missing_courts: Counter[str] = Counter()
    missed_examples: list[dict[str, Any]] = []
    verification_statuses: Counter[str] = Counter()
    verification_missed_examples: list[dict[str, Any]] = []
    gold_citation_parse_count = 0
    gold_neutral_citation_count = 0
    extractor_recognized_count = 0
    adapter = AustralianCorpusAdapter(index_path=au_index) if au_index is not None else None
    row_results: list[dict[str, Any]] = []

    for row_index, row in enumerate(rows, start=1):
        gold_citation = extract_gold_citation(row.output)
        row_result: dict[str, Any] = {
            "row_index": row_index,
            "gold_citation": gold_citation,
            "neutral_citation": None,
            "court": None,
            "extraction_status": "no_gold_citation",
            "extracted_result_count": 0,
            "verification_status": None,
            "verification_result_count": 0,
            "verification_normalized_citation": None,
            "verification_error": None,
        }
        if not gold_citation:
            row_results.append(row_result)
            continue
        gold_citation_parse_count += 1

        neutral_citation = extract_neutral_citation(gold_citation)
        if not neutral_citation:
            row_result["extraction_status"] = "unsupported_gold_citation"
            row_results.append(row_result)
            continue
        gold_neutral_citation_count += 1
        row_result["neutral_citation"] = neutral_citation.citation
        row_result["court"] = neutral_citation.court

        extracted = extract_citations(gold_citation)
        row_result["extracted_result_count"] = len(extracted)
        recognized = any(
            match.jurisdiction_guess == "au" and match.text == neutral_citation.citation for match in extracted
        )
        if recognized:
            row_result["extraction_status"] = "recognized"
            extractor_recognized_count += 1
            if adapter is not None:
                report = verify_text(gold_citation, adapters=[adapter])
                row_result["verification_result_count"] = len(report.results)
                matching_results = [
                    result
                    for result in report.results
                    if result.jurisdiction_guess == "au" and result.normalized_citation == neutral_citation.citation
                ]
                result = (
                    matching_results[0] if matching_results else report.results[0] if len(report.results) == 1 else None
                )
                status = result.status.value if result is not None else VerificationStatus.UNSUPPORTED_FORMAT.value
                row_result["verification_status"] = status
                row_result["verification_normalized_citation"] = result.normalized_citation if result else None
                row_result["verification_error"] = (
                    result.error_message if result else "verification result count did not identify the gold citation"
                )
                verification_statuses[status] += 1
                if status != VerificationStatus.VERIFIED.value and len(verification_missed_examples) < max_examples:
                    verification_missed_examples.append(
                        {
                            "row_index": row_index,
                            "gold_citation": gold_citation,
                            "neutral_citation": neutral_citation.citation,
                            "court": neutral_citation.court,
                            "status": status,
                        }
                    )
            row_results.append(row_result)
            continue

        row_result["extraction_status"] = "unrecognized"
        row_results.append(row_result)
        missing_courts[neutral_citation.court] += 1
        if len(missed_examples) < max_examples:
            missed_examples.append(
                {
                    "row_index": row_index,
                    "gold_citation": gold_citation,
                    "neutral_citation": neutral_citation.citation,
                    "court": neutral_citation.court,
                }
            )

    recognition_rate = extractor_recognized_count / gold_neutral_citation_count if gold_neutral_citation_count else 0.0

    report = {
        "schema_version": 1,
        "benchmark": benchmark_provenance(),
        "dataset": BENCHMARK_DATASET,
        "split": BENCHMARK_SPLIT,
        "total_rows": len(rows),
        "gold_citation_parse_count": gold_citation_parse_count,
        "gold_neutral_citation_count": gold_neutral_citation_count,
        "extractor_recognized_count": extractor_recognized_count,
        "extractor_recognition_rate": recognition_rate,
        "missing_court_codes": [{"court": court, "count": count} for court, count in missing_courts.most_common()],
        "missed_examples": missed_examples,
        "row_results": row_results,
    }
    if adapter is not None:
        report.update(
            {
                "index_provenance": adapter.service.store.provenance().model_dump(mode="json"),
                "verification_status_counts": dict(sorted(verification_statuses.items())),
                "verification_missed_examples": verification_missed_examples,
            }
        )
        for status in VerificationStatus:
            report[f"verification_{status.value}_count"] = verification_statuses[status.value]
    return report


def load_rows(path: Path) -> list[AusLawBenchmarkRow]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("AusLaw benchmark JSON must be a list of rows.")

    rows: list[AusLawBenchmarkRow] = []
    for index, row in enumerate(data):
        if not isinstance(row, dict):
            raise ValueError(f"AusLaw benchmark row {index} must be an object.")
        try:
            rows.append(
                AusLawBenchmarkRow(
                    instruction=str(row["instruction"]),
                    input=str(row["input"]),
                    output=str(row["output"]),
                )
            )
        except KeyError as error:
            raise ValueError(f"AusLaw benchmark row {index} is missing {error.args[0]}.") from error
    return rows


def resolve_input_path(input_path: Path | None, *, refresh: bool, cache_path: Path = DEFAULT_CACHE_PATH) -> Path:
    if input_path is not None:
        verify_benchmark_file(input_path)
        return input_path
    if refresh or not cache_path.exists():
        download_benchmark(cache_path)
    else:
        verify_benchmark_file(cache_path)
    return cache_path


def download_benchmark(
    cache_path: Path,
    *,
    url: str = BENCHMARK_URL,
    expected_sha256: str = BENCHMARK_SHA256,
) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{cache_path.name}.", suffix=".download", dir=cache_path.parent
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        digest = hashlib.sha256()
        with urllib.request.urlopen(url, timeout=60) as response, temporary_path.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
                output.write(chunk)
        actual_sha256 = digest.hexdigest()
        if actual_sha256 != expected_sha256:
            raise ValueError(f"benchmark file SHA-256 mismatch: expected {expected_sha256}, got {actual_sha256}")
        os.replace(temporary_path, cache_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def add_generation_timestamp(report: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    result = dict(report)
    result["generated_at"] = generated_at or datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    return result


def compare_reports(baseline: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    baseline_rows = {row["row_index"]: row for row in baseline.get("row_results", [])}
    current_rows = {row["row_index"]: row for row in current.get("row_results", [])}
    regressions: list[dict[str, Any]] = []
    for row_index in sorted(baseline_rows):
        baseline_row = baseline_rows[row_index]
        current_row = current_rows.get(row_index, {})
        baseline_extraction = baseline_row.get("extraction_status")
        current_extraction = current_row.get("extraction_status")
        if baseline_extraction == "recognized" and current_extraction != "recognized":
            regressions.append(
                {
                    "row_index": row_index,
                    "kind": "extraction_regression",
                    "baseline": baseline_extraction,
                    "current": current_extraction,
                }
            )
            continue

        baseline_verification = baseline_row.get("verification_status")
        current_verification = current_row.get("verification_status")
        if (
            baseline_verification == VerificationStatus.VERIFIED.value
            and current_verification != VerificationStatus.VERIFIED.value
        ):
            regressions.append(
                {
                    "row_index": row_index,
                    "kind": "verification_regression",
                    "baseline": baseline_verification,
                    "current": current_verification,
                }
            )
    return regressions


def load_report(path: Path) -> dict[str, Any]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"could not load benchmark report {path}: {error}") from error
    if not isinstance(report, dict):
        raise ValueError(f"benchmark report {path} must be a JSON object")
    return report


def print_summary(report: dict[str, Any]) -> None:
    rate = report["extractor_recognition_rate"] * 100
    print("AusLaw Citation Benchmark extraction eval")
    print(f"Rows: {report['total_rows']}")
    print(f"Gold citations parsed: {report['gold_citation_parse_count']}")
    print(f"Gold neutral citations: {report['gold_neutral_citation_count']}")
    print(f"Extractor recognized: {report['extractor_recognized_count']} ({rate:.1f}%)")
    if "verification_status_counts" in report:
        print("Verification statuses:")
        for status, count in report["verification_status_counts"].items():
            print(f"  {status}: {count}")
    if report["missing_court_codes"]:
        print("Top missing court codes:")
        for item in report["missing_court_codes"][:10]:
            print(f"  {item['court']}: {item['count']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate Australian neutral citation extraction against the AusLaw Citation Benchmark test split."
    )
    parser.add_argument("--input", type=Path, help="Path to a local roc_test.json file.")
    parser.add_argument("--refresh", action="store_true", help="Redownload the pinned Hugging Face test split.")
    parser.add_argument("--output", type=Path, help="Optional path to write the JSON report.")
    parser.add_argument(
        "--au-index",
        type=Path,
        help="Optional compact Australian index JSON path for end-to-end verification metrics.",
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=20,
        help="Maximum missed examples to include in the JSON report.",
    )
    parser.add_argument("--baseline", type=Path, help="Approved per-row benchmark report for regression comparison.")
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit non-zero when extraction or previously verified results regress against --baseline.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.fail_on_regression and args.baseline is None:
        raise SystemExit("--fail-on-regression requires --baseline")
    input_path = resolve_input_path(args.input, refresh=args.refresh)
    report = evaluate_rows(load_rows(input_path), max_examples=args.max_examples, au_index=args.au_index)
    regressions: list[dict[str, Any]] = []
    if args.baseline is not None:
        regressions = compare_reports(load_report(args.baseline), report)
        report["baseline_comparison"] = {
            "regression_count": len(regressions),
            "regressions": regressions,
        }
    report = add_generation_timestamp(report)
    print_summary(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.fail_on_regression and regressions:
        print(f"Benchmark regressions: {len(regressions)}", file=sys.stderr)
        for regression in regressions:
            print(json.dumps(regression, sort_keys=True), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
