from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


NEUTRAL_RE = re.compile(r"\[(?P<year>\d{4})\]\s+(?P<court>[A-Z][A-Z0-9]{1,9})\s+(?P<number>\d{1,5})")


@dataclass(slots=True)
class AustralianIndexBuildStats:
    records_written: int = 0
    skipped_non_decision: int = 0
    skipped_missing_citation: int = 0
    skipped_malformed: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def build_australian_index(corpus_jsonl: str | Path, output_path: str | Path) -> AustralianIndexBuildStats:
    corpus_path = Path(corpus_jsonl)
    output = Path(output_path)
    stats = AustralianIndexBuildStats()
    records: list[dict[str, str | None]] = []

    with corpus_path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                stats.skipped_malformed += 1
                continue

            if not isinstance(row, dict):
                stats.skipped_malformed += 1
                continue
            if row.get("type") != "decision":
                stats.skipped_non_decision += 1
                continue

            citation = _clean(row.get("citation"))
            neutral = _extract_neutral(citation or "")
            if not citation or not neutral:
                stats.skipped_missing_citation += 1
                continue

            records.append(_compact_record(row, citation, neutral))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    stats.records_written = len(records)
    return stats


def _compact_record(row: dict[str, Any], citation: str, neutral: str) -> dict[str, str | None]:
    return {
        "citation": citation,
        "normalized_citation": _normalize(neutral),
        "case_name": _case_name_from_citation(citation, neutral),
        "court": _clean(row.get("source")),
        "jurisdiction": _clean(row.get("jurisdiction")),
        "date": _clean(row.get("date")),
        "source_url": _clean(row.get("url")),
    }


def _extract_neutral(citation: str) -> str | None:
    match = NEUTRAL_RE.search(citation)
    return match.group(0) if match else None


def _case_name_from_citation(citation: str, neutral: str) -> str:
    before_neutral = citation.split(neutral, 1)[0]
    return before_neutral.strip(" ,;:-") or citation


def _clean(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None


def _normalize(citation: str) -> str:
    return " ".join(citation.strip().split())
