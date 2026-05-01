from __future__ import annotations

import argparse
import json
import re
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from caselaw_guard.extractors import extract_citations


BENCHMARK_URL = "https://huggingface.co/datasets/auslawbench/AusLaw-Citation-Benchmark/raw/main/roc_test.json"
DEFAULT_CACHE_PATH = Path(".cache/caselaw-guard/auslaw-citation-benchmark/roc_test.json")
ANGLE_CITATION_RE = re.compile(r"<([^<>]+)>")
NEUTRAL_CITATION_RE = re.compile(
    r"\[(?P<year>\d{4})\]\s+(?P<court>[A-Za-z][A-Za-z0-9]{1,12})\s+(?P<number>\d{1,5})"
)


@dataclass(frozen=True)
class AusLawBenchmarkRow:
    instruction: str
    input: str
    output: str


@dataclass(frozen=True)
class NeutralCitation:
    citation: str
    court: str


def extract_gold_citation(output: str) -> str | None:
    matches = ANGLE_CITATION_RE.findall(output)
    return matches[-1].strip() if matches else None


def extract_neutral_citation(citation: str) -> NeutralCitation | None:
    match = NEUTRAL_CITATION_RE.search(citation)
    if not match:
        return None
    normalized = f"[{match.group('year')}] {match.group('court')} {match.group('number')}"
    return NeutralCitation(citation=normalized, court=match.group("court"))


def evaluate_rows(rows: list[AusLawBenchmarkRow], *, max_examples: int = 20) -> dict[str, Any]:
    missing_courts: Counter[str] = Counter()
    missed_examples: list[dict[str, Any]] = []
    gold_citation_parse_count = 0
    gold_neutral_citation_count = 0
    extractor_recognized_count = 0

    for row_index, row in enumerate(rows, start=1):
        gold_citation = extract_gold_citation(row.output)
        if not gold_citation:
            continue
        gold_citation_parse_count += 1

        neutral_citation = extract_neutral_citation(gold_citation)
        if not neutral_citation:
            continue
        gold_neutral_citation_count += 1

        extracted = extract_citations(gold_citation)
        if any(match.jurisdiction_guess == "au" and match.text == neutral_citation.citation for match in extracted):
            extractor_recognized_count += 1
            continue

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

    recognition_rate = (
        extractor_recognized_count / gold_neutral_citation_count if gold_neutral_citation_count else 0.0
    )

    return {
        "dataset": "auslawbench/AusLaw-Citation-Benchmark",
        "split": "test",
        "total_rows": len(rows),
        "gold_citation_parse_count": gold_citation_parse_count,
        "gold_neutral_citation_count": gold_neutral_citation_count,
        "extractor_recognized_count": extractor_recognized_count,
        "extractor_recognition_rate": recognition_rate,
        "missing_court_codes": [
            {"court": court, "count": count} for court, count in missing_courts.most_common()
        ],
        "missed_examples": missed_examples,
    }


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
        return input_path
    if refresh or not cache_path.exists():
        download_benchmark(cache_path)
    return cache_path


def download_benchmark(cache_path: Path) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(BENCHMARK_URL, timeout=60) as response:
        cache_path.write_bytes(response.read())


def print_summary(report: dict[str, Any]) -> None:
    rate = report["extractor_recognition_rate"] * 100
    print("AusLaw Citation Benchmark extraction eval")
    print(f"Rows: {report['total_rows']}")
    print(f"Gold citations parsed: {report['gold_citation_parse_count']}")
    print(f"Gold neutral citations: {report['gold_neutral_citation_count']}")
    print(f"Extractor recognized: {report['extractor_recognized_count']} ({rate:.1f}%)")
    if report["missing_court_codes"]:
        print("Top missing court codes:")
        for item in report["missing_court_codes"][:10]:
            print(f"  {item['court']}: {item['count']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate Australian neutral citation extraction against the AusLaw Citation Benchmark test split."
    )
    parser.add_argument("--input", type=Path, help="Path to a local roc_test.json file.")
    parser.add_argument("--refresh", action="store_true", help="Redownload the cached Hugging Face test split.")
    parser.add_argument("--output", type=Path, help="Optional path to write the JSON report.")
    parser.add_argument(
        "--max-examples",
        type=int,
        default=20,
        help="Maximum missed examples to include in the JSON report.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    input_path = resolve_input_path(args.input, refresh=args.refresh)
    report = evaluate_rows(load_rows(input_path), max_examples=args.max_examples)
    print_summary(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
